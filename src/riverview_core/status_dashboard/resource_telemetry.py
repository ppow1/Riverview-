# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/resource_telemetry.py
# Component: STEWARD-DASHBOARD-RESOURCE-TELEMETRY
# Revision: 1.4.0
# Purpose: Build a read-only, timestamped projection from approved GPU, model, storage, printer, and optional host sources
# Execution Model: Request-driven; one bounded collection per authenticated GET
# Observability: rv.dashboard.resource-telemetry.v1 with per-source state, timestamps, and safe error codes
# Dependencies: Python standard library, systemd SSH credentials, restricted OCTOMINER1 telemetry key
# Inputs/Outputs: NVIDIA/storage JSON via forced-command SSH; local mountinfo; model APIs; redacted host projection
# Authority: Dashboard authentication is enforced by the parent API; fixed host and endpoint allowlists only
# Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Initial read-only telemetry projection
# Changed: 2026-10-22 UTC | RV-V2-HW-AI-ENHANCEMENTS-207 | Project bounded numeric per-slot context counters without task IDs or prompt data
# Changed: 2026-10-22 UTC | RV-V2-STORAGE-CAPACITY-001 | Add local and OCTO1 mounted-volume measurements to the existing resource projection
# Changed: 2026-10-22 UTC | ISSUE-231 | Add pinned optional OCTO2 and Windows development telemetry sources
# Changed: 2026-10-23 UTC | RV-V2-BAMBU-READONLY-230 | Project the sanitized OCTO Control Bambu status from the existing restricted host read
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_resource_telemetry.py; tests/test_status_dashboard.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Bounded telemetry reads for the authenticated V2 Hardware view.

This module has no cache, write, scheduling, or model-control path. Host access
uses a dedicated SSH key whose server-side authorized_keys entry forces one
read-only NVIDIA collector command. Model APIs are fixed private-LAN/loopback
URLs; only health, loaded model basename, active-slot count, and bounded numeric
slot context counters are projected. Slot task IDs, prompt text, token data, and
other raw fields are discarded. Queue depth and KV-cache allocation bytes remain
unavailable because the deployed llama.cpp build does not expose them.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .storage_inventory import collect_linux_storage, project_remote_volumes


SCHEMA_VERSION = "rv.dashboard.resource-telemetry.v1"
MAX_RESPONSE_BYTES = 64 * 1024
_MODEL_ID = re.compile(r"^[A-Za-z0-9._+() -]{1,128}$")
_GPU_NAME = re.compile(r"^[A-Za-z0-9._+() -]{1,100}$")
_PRINTER_TEXT = re.compile(r"^[A-Za-z0-9._+() /-]{1,64}$")
_BAMBU_ERRORS = frozenset({"bambu_source_unavailable", "bambu_source_status_invalid",
                           "bambu_source_response_too_large", "bambu_source_schema_invalid",
                           "bambu_authentication_failed", "printer_offline",
                           "printer_telemetry_stale"})
_SSH_HOST = "192.168.1.160"
_SSH_USER = "root"
_SSH_PORT = "22"
_SSH_REMOTE_COMMAND = "resource-telemetry"
_OPTIONAL_HOSTS = (
    {"host_id": "octominer2", "display_name": "OCTO2", "address": "192.168.1.162",
     "command": "resource-telemetry", "credential_prefix": "resource-telemetry-octo2",
     "identity_state": "documented_unverified"},
    {"host_id": "windows-development", "display_name": "Windows development machine",
     "address": "192.168.1.88", "command": "rv-windows-resource-telemetry",
     "credential_prefix": "resource-telemetry-windows",
     "identity_state": "documented_not_connected"},
)
_MODEL_SOURCES = (
    {
        "host_id": "camrui",
        "service_id": "grace-autonomic-0.6b",
        "display_name": "Grace autonomic 0.6B",
        "endpoint_id": "camrui-loopback-18796",
        "base_url": "http://127.0.0.1:18796",
    },
    {
        "host_id": "octominer1",
        "service_id": "grace-reasoning-80b",
        "display_name": "Grace reasoning 80B",
        "endpoint_id": "octominer1-llama-8080",
        "base_url": "http://192.168.1.160:8080",
    },
    {
        "host_id": "octominer1",
        "service_id": "grace-vision-30b",
        "display_name": "Grace vision 30B",
        "endpoint_id": "octominer1-vision-18080",
        "base_url": "http://192.168.1.160:18080",
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _bounded_text(value: object, pattern: re.Pattern[str], fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    candidate = value.rsplit("/", 1)[-1].strip()
    return candidate if pattern.fullmatch(candidate) else fallback


def _safe_integer(value: object) -> int | None:
    try:
        if isinstance(value, bool):
            return None
        number = int(value)
        return number if 0 <= number <= 2**63 - 1 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _safe_timestamp(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _project_bambu_status(raw: object) -> dict:
    """Return only the bounded display contract; discard all upstream identity/secrets."""
    empty_printer = {"state": None, "nozzle_temperature_c": None,
                     "bed_temperature_c": None, "progress_percent": None,
                     "remaining_minutes": None, "layer_number": None,
                     "total_layers": None}
    unavailable = {"schema_version": "rv.octo.bambu-status.v1", "status": "unavailable",
                   "connected": None, "observed_at": None, "last_seen_at": None,
                   "stale_after_seconds": 30, "printer": empty_printer, "ams": [],
                   "error_code": "bambu_source_unavailable"}
    if not isinstance(raw, dict) or raw.get("schema_version") != "rv.octo.bambu-status.v1":
        return unavailable
    status = raw.get("status")
    if not isinstance(status, str) or status not in {"healthy", "offline", "stale", "unavailable"}:
        return {**unavailable, "error_code": "bambu_source_schema_invalid"}
    connected = raw.get("connected") if type(raw.get("connected")) is bool else None
    printer_raw = raw.get("printer") if isinstance(raw.get("printer"), dict) else {}
    state = printer_raw.get("state")
    if not isinstance(state, str) or not re.fullmatch(r"[A-Za-z0-9 _-]{1,48}", state.strip()):
        state = None
    def number(name: str, low: float, high: float):
        value = printer_raw.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return value if low <= value <= high else None
    def integer(name: str):
        value = printer_raw.get(name)
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 1000000 else None
    slots = []
    raw_slots = raw.get("ams") if isinstance(raw.get("ams"), list) else []
    for item in raw_slots[:8]:
        if not isinstance(item, dict):
            continue
        material = item.get("material")
        if not isinstance(material, str) or not _PRINTER_TEXT.fullmatch(material.strip()):
            material = None
        remaining = item.get("remaining")
        if isinstance(remaining, bool) or not isinstance(remaining, (int, float)) or not -1 <= remaining <= 10000:
            remaining = None
        color = item.get("color_hex")
        if not isinstance(color, str) or not re.fullmatch(r"[0-9A-Fa-f]{8}", color):
            color = None
        slots.append({"unit": item.get("unit") if type(item.get("unit")) is int and 0 <= item["unit"] <= 32 else None,
                      "slot": item.get("slot") if type(item.get("slot")) is int and 0 <= item["slot"] <= 31 else None,
                      "material": material.strip() if isinstance(material, str) else None,
                      "remaining": remaining, "color_hex": color.upper() if color else None})
    error = raw.get("error_code")
    return {"schema_version": "rv.octo.bambu-status.v1", "status": status,
            "connected": connected,
            "observed_at": _safe_timestamp(raw.get("observed_at")),
            "last_seen_at": _safe_timestamp(raw.get("last_seen_at")),
            "stale_after_seconds": 30,
            "printer": {"state": state,
                        "nozzle_temperature_c": number("nozzle_temperature_c", 0, 500),
                        "bed_temperature_c": number("bed_temperature_c", 0, 200),
                        "progress_percent": number("progress_percent", 0, 100),
                        "remaining_minutes": integer("remaining_minutes"),
                        "layer_number": integer("layer_number"),
                        "total_layers": integer("total_layers")},
            "ams": slots,
            "error_code": error if isinstance(error, str) and error in _BAMBU_ERRORS else (None if status == "healthy" else "bambu_source_unavailable")}


def _credential_path(name: str) -> Path | None:
    directory = os.environ.get("CREDENTIALS_DIRECTORY", "")
    if not directory:
        return None
    root = Path(directory)
    path = root / name
    try:
        if path.is_symlink() or not path.is_file() or path.resolve().parent != root.resolve():
            return None
    except OSError:
        return None
    return path


class DashboardResourceTelemetry:
    """Collect safe GPU/model facts once per caller request."""

    def __init__(self, *, runner=subprocess.run, http_open=urlopen, credential_directory=None,
                 local_storage_reader=collect_linux_storage):
        self._runner = runner
        self._http_open = http_open
        self._credential_directory = Path(credential_directory) if credential_directory else None
        self._local_storage_reader = local_storage_reader

    def _local_storage_source(self, host_id: str) -> dict:
        try:
            result = self._local_storage_reader(host_id)
            if (not isinstance(result, dict) or result.get("state") not in {"healthy", "unavailable"}
                    or not isinstance(result.get("volumes"), list)):
                raise ValueError("storage_schema_invalid")
            return result
        except (OSError, TypeError, ValueError):
            return {"state": "unavailable", "observed_at": None, "volumes": [],
                    "error_code": "local_storage_source_unavailable"}

    def _credential(self, name: str) -> Path | None:
        if self._credential_directory is not None:
            root = self._credential_directory
            path = root / name
            try:
                if path.is_symlink() or not path.is_file() or path.resolve().parent != root.resolve():
                    return None
            except OSError:
                return None
            return path
        return _credential_path(name)

    def _credential_text(self, name: str) -> str | None:
        path = self._credential(name)
        if path is None:
            return None
        try:
            value = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return None
        return value if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value) else None

    def _optional_host_source(self, host: dict) -> dict:
        prefix = host["credential_prefix"]
        key = self._credential(prefix + "-key")
        known_hosts = self._credential(prefix + "-known-hosts")
        user = self._credential_text(prefix + "-user")
        failed = {"state": "unavailable", "observed_at": None, "devices": [],
                  "system_metrics": {"state": "unavailable", "observed_at": None,
                                     "cpu_utilization_percent": None, "cpu_name": "Unavailable",
                                     "memory_used_bytes": None, "memory_total_bytes": None,
                                     "error_code": "host_telemetry_unavailable"},
                  "storage": {"state": "unavailable", "observed_at": None, "volumes": [],
                              "error_code": "host_telemetry_unavailable"},
                  "error_code": "host_telemetry_credentials_unavailable"}
        if key is None or known_hosts is None or user is None:
            return failed
        command = ["/usr/bin/ssh", "-T", "-p", _SSH_PORT, "-i", str(key),
                   "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                   "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
                   "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={known_hosts}",
                   "-o", "GlobalKnownHostsFile=/dev/null", "-o", "ConnectTimeout=3",
                   "-o", "ServerAliveInterval=3", "-o", "ServerAliveCountMax=1",
                   "-o", "LogLevel=ERROR", f"{user}@{host['address']}", host["command"]]
        try:
            completed = self._runner(command, check=False, capture_output=True, text=True,
                                     timeout=5.0, env={"LC_ALL": "C"})
            if completed.returncode != 0 or len(completed.stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
                failed["error_code"] = "host_telemetry_unreachable"
                return failed
            payload = json.loads(completed.stdout)
            if (not isinstance(payload, dict) or
                    payload.get("schema_version") != "rv.gpu-host-telemetry.v1" or
                    not isinstance(payload.get("devices"), list) or len(payload["devices"]) > 32):
                failed["error_code"] = "host_telemetry_schema_invalid"
                return failed
            observed = payload.get("observed_at") if isinstance(payload.get("observed_at"), str) else None
            devices = []
            for raw in payload["devices"]:
                if not isinstance(raw, dict):
                    continue
                index = _safe_integer(raw.get("index"))
                if index is None:
                    continue
                used, total = _safe_integer(raw.get("memory_used_bytes")), _safe_integer(raw.get("memory_total_bytes"))
                if used is not None and total is not None and used > total:
                    used = total = None
                utilization = _safe_integer(raw.get("utilization_percent"))
                if utilization is not None and utilization > 100:
                    utilization = None
                temperature = _safe_integer(raw.get("temperature_celsius"))
                if temperature is not None and temperature > 200:
                    temperature = None
                power = raw.get("power_watts")
                if isinstance(power, bool) or not isinstance(power, (int, float)) or not 0 <= power <= 10000:
                    power = None
                fan = _safe_integer(raw.get("fan_percent"))
                if fan is not None and fan > 100:
                    fan = None
                devices.append({"index": index, "name": _bounded_text(raw.get("name"), _GPU_NAME, "Unknown GPU"),
                                "memory_used_bytes": used, "memory_total_bytes": total,
                                "utilization_percent": utilization, "temperature_celsius": temperature,
                                "power_watts": power, "fan_percent": fan, "active_services": [],
                                "observed_at": observed, "source": "nvidia-smi"})
            system_metrics = self._project_system_metrics(payload, observed)
            return {"state": "healthy" if observed and (devices or system_metrics["state"] == "healthy") else "unavailable",
                    "observed_at": observed, "devices": devices, "system_metrics": system_metrics,
                    "storage": project_remote_volumes(host["host_id"], payload), "error_code": None}
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, json.JSONDecodeError):
            failed["error_code"] = "host_telemetry_source_unavailable"
            return failed

    @staticmethod
    def _project_system_metrics(payload: dict, observed: str | None) -> dict:
        metrics = payload.get("host_metrics") if isinstance(payload.get("host_metrics"), dict) else {}
        cpu = metrics.get("cpu_utilization_percent")
        if isinstance(cpu, bool) or not isinstance(cpu, (int, float)) or not 0 <= cpu <= 100:
            cpu = None
        memory_total = _safe_integer(metrics.get("memory_total_bytes"))
        memory_used = _safe_integer(metrics.get("memory_used_bytes"))
        if memory_total is None or memory_total == 0 or memory_used is None or memory_used > memory_total:
            memory_total = memory_used = None
        metric_observed = metrics.get("observed_at") if isinstance(metrics.get("observed_at"), str) else observed
        available = cpu is not None or memory_total is not None
        return {"state": "healthy" if available else "unavailable", "observed_at": metric_observed,
                "cpu_utilization_percent": cpu,
                "cpu_name": _bounded_text(metrics.get("cpu_name"), _GPU_NAME, "Unavailable"),
                "memory_used_bytes": memory_used, "memory_total_bytes": memory_total,
                "error_code": None if available else "system_metrics_unavailable"}
    def _gpu_source(self) -> dict:
        observed = _utc_now()
        key = self._credential("resource-telemetry-key")
        known_hosts = self._credential("resource-telemetry-known-hosts")
        if key is None or known_hosts is None:
            return {"state": "unavailable", "observed_at": None,
                    "error_code": "telemetry_credentials_unavailable", "devices": [],
                    "system_metrics": self._project_system_metrics({}, None),
                    "storage": {"state": "unavailable", "observed_at": None,
                                "volumes": [], "error_code": "storage_credentials_unavailable"},
                    "bambu_printer": _project_bambu_status(None)}
        command = [
            "/usr/bin/ssh", "-T", "-p", _SSH_PORT,
            "-i", str(key),
            "-o", "IdentitiesOnly=yes",
            "-o", "BatchMode=yes",
            "-o", "PasswordAuthentication=no",
            "-o", "KbdInteractiveAuthentication=no",
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={known_hosts}",
            "-o", "GlobalKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=3",
            "-o", "ServerAliveInterval=3",
            "-o", "ServerAliveCountMax=1",
            "-o", "LogLevel=ERROR",
            f"{_SSH_USER}@{_SSH_HOST}", _SSH_REMOTE_COMMAND,
        ]
        try:
            completed = self._runner(command, check=False, capture_output=True,
                                     text=True, timeout=5.0, env={"LC_ALL": "C"})
            if completed.returncode != 0 or len(completed.stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
                return {"state": "unavailable", "observed_at": None,
                        "error_code": "gpu_source_unreachable", "devices": [],
                        "system_metrics": self._project_system_metrics({}, None),
                        "storage": {"state": "unavailable", "observed_at": None,
                                    "volumes": [], "error_code": "storage_source_unreachable"},
                        "bambu_printer": _project_bambu_status(None)}
            payload = json.loads(completed.stdout)
            bambu_printer = _project_bambu_status(payload.get("bambu_status") if isinstance(payload, dict) else None)
            if (not isinstance(payload, dict) or
                    payload.get("schema_version") != "rv.gpu-host-telemetry.v1" or
                    not isinstance(payload.get("devices"), list) or len(payload["devices"]) > 32):
                return {"state": "unavailable", "observed_at": None,
                        "error_code": "gpu_source_schema_invalid", "devices": [],
                        "system_metrics": self._project_system_metrics({}, None),
                        "storage": project_remote_volumes("octominer1", payload),
                        "bambu_printer": bambu_printer}
            devices = []
            for raw in payload["devices"]:
                if not isinstance(raw, dict):
                    continue
                index = _safe_integer(raw.get("index"))
                name = _bounded_text(raw.get("name"), _GPU_NAME, "Unknown GPU")
                memory_used = _safe_integer(raw.get("memory_used_bytes"))
                memory_total = _safe_integer(raw.get("memory_total_bytes"))
                utilization = _safe_integer(raw.get("utilization_percent"))
                temperature = _safe_integer(raw.get("temperature_celsius"))
                if utilization is not None and utilization > 100:
                    utilization = None
                if temperature is not None and temperature > 200:
                    temperature = None
                if (memory_used is not None and memory_total is not None
                        and memory_used > memory_total):
                    memory_used = None
                    memory_total = None
                power = raw.get("power_watts")
                if isinstance(power, bool) or not isinstance(power, (int, float)) or not 0 <= power <= 10000:
                    power = None
                fan = _safe_integer(raw.get("fan_percent"))
                if fan is not None and fan > 100:
                    fan = None
                services = raw.get("active_services", [])
                if not isinstance(services, list):
                    services = []
                services = sorted({item for item in services if item in {
                    "grace-reasoning-80b", "grace-vision-30b", "other"}})
                if index is None:
                    continue
                devices.append({
                    "device_id": f"gpu-{index}",
                    "index": index,
                    "name": name,
                    "utilization_percent": utilization,
                    "memory_used_bytes": memory_used,
                    "memory_total_bytes": memory_total,
                    "temperature_celsius": temperature,
                    "power_watts": power,
                    "fan_percent": fan,
                    "active_services": services,
                    "observed_at": payload.get("observed_at") if isinstance(payload.get("observed_at"), str) else None,
                    "source": "nvidia-smi",
                })
            source_time = payload.get("observed_at")
            if not isinstance(source_time, str):
                source_time = observed
            return {"state": "healthy" if devices else "unavailable",
                    "observed_at": source_time,
                    "error_code": None if devices else "gpu_inventory_empty",
                    "devices": devices,
                    "system_metrics": self._project_system_metrics(payload, source_time),
                    "storage": project_remote_volumes("octominer1", payload),
                    "bambu_printer": bambu_printer}
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, json.JSONDecodeError):
            return {"state": "unavailable", "observed_at": None,
                    "error_code": "gpu_source_unavailable", "devices": [],
                    "system_metrics": self._project_system_metrics({}, None),
                    "storage": {"state": "unavailable", "observed_at": None,
                                "volumes": [], "error_code": "storage_source_unavailable"},
                    "bambu_printer": _project_bambu_status(None)}

    def _read_json(self, url: str) -> object:
        request = Request(url, headers={"Accept": "application/json"}, method="GET")
        with self._http_open(request, timeout=1.5) as response:
            if response.status != 200:
                raise OSError("source_status_invalid")
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("source_response_too_large")
        return json.loads(body.decode("utf-8"))

    def _model_source(self, source: dict) -> dict:
        observed = _utc_now()
        base = source["base_url"]
        try:
            health = self._read_json(base + "/health")
            if not isinstance(health, dict) or health.get("status") != "ok":
                raise ValueError("health_schema_invalid")
            models = self._read_json(base + "/v1/models")
            entries = models.get("data") if isinstance(models, dict) else None
            if not isinstance(entries, list) or not entries:
                entries = models.get("models") if isinstance(models, dict) else None
            if not isinstance(entries, list) or not entries:
                raise ValueError("model_identity_unavailable")
            model_ids = sorted({
                _bounded_text(item.get("id") or item.get("name") or item.get("model"), _MODEL_ID, "")
                for item in entries if isinstance(item, dict)
            } - {""})
            if not model_ids:
                raise ValueError("model_identity_invalid")
            slots = self._read_json(base + "/slots")
            if not isinstance(slots, list) or len(slots) > 256:
                raise ValueError("slot_schema_invalid")
            active_slots = sum(1 for slot in slots
                               if isinstance(slot, dict) and slot.get("is_processing") is True)
            context_slots = []
            for slot in slots:
                if not isinstance(slot, dict):
                    continue
                slot_id = _safe_integer(slot.get("id"))
                if slot_id is None:
                    continue
                context_slots.append({
                    "slot_id": slot_id,
                    "processing": slot.get("is_processing") if type(slot.get("is_processing")) is bool else None,
                    "context_tokens": _safe_integer(slot.get("n_ctx")),
                    "prompt_tokens": _safe_integer(slot.get("n_prompt_tokens")),
                    "prompt_tokens_processed": _safe_integer(slot.get("n_prompt_tokens_processed")),
                    "prompt_tokens_cached": _safe_integer(slot.get("n_prompt_tokens_cache")),
                })
            has_context_measurement = any(
                any(slot[key] is not None for key in (
                    "context_tokens", "prompt_tokens", "prompt_tokens_processed",
                    "prompt_tokens_cached"))
                for slot in context_slots)
            observed = _utc_now()
            return {
                "service_id": source["service_id"],
                "display_name": source["display_name"],
                "endpoint_id": source["endpoint_id"],
                "state": "ready",
                "observed_at": observed,
                "readiness_source": "llama.cpp /health and /v1/models",
                "loaded_models": model_ids,
                "active_slots": {"state": "measured", "value": active_slots,
                                 "total": len(slots), "source": "llama.cpp /slots"},
                "slot_context": {
                    "state": "measured" if has_context_measurement else "unavailable",
                    "source": "llama.cpp /slots numeric fields",
                    "observed_at": observed,
                    "slots": context_slots,
                    "kv_cache_bytes": {"state": "unavailable", "value": None,
                                       "reason": "not_exposed_by_current_model_server"},
                },
                "queued_requests": {"state": "unavailable", "value": None,
                                     "reason": "queue_depth_not_exposed_by_current_server"},
                "error_code": None,
            }
        except (OSError, HTTPError, URLError, TimeoutError, ValueError, TypeError,
                json.JSONDecodeError):
            return {
                "service_id": source["service_id"],
                "display_name": source["display_name"],
                "endpoint_id": source["endpoint_id"],
                "state": "unavailable",
                "observed_at": observed,
                "readiness_source": "llama.cpp /health and /v1/models",
                "loaded_models": [],
                "active_slots": {"state": "unavailable", "value": None,
                                 "total": None, "source": "llama.cpp /slots"},
                "slot_context": {"state": "unavailable", "source": "llama.cpp /slots",
                                  "observed_at": None, "slots": [],
                                  "kv_cache_bytes": {"state": "unavailable", "value": None,
                                                      "reason": "model_server_unavailable"}},
                "queued_requests": {"state": "unavailable", "value": None,
                                     "reason": "queue_depth_not_exposed_by_current_server"},
                "error_code": "model_server_unavailable",
            }

    def read(self) -> dict:
        """Return the current result; failed sources are never filled from cache."""
        tasks = {}
        with ThreadPoolExecutor(max_workers=6, thread_name_prefix="rv-resource-read") as pool:
            tasks["gpu"] = pool.submit(self._gpu_source)
            for source in _MODEL_SOURCES:
                tasks[source["service_id"]] = pool.submit(self._model_source, source)
            for host in _OPTIONAL_HOSTS:
                tasks[host["host_id"]] = pool.submit(self._optional_host_source, host)
            results = {name: future.result(timeout=7.0) for name, future in tasks.items()}
        gpu = results["gpu"]
        camrui_storage = self._local_storage_source("camrui")
        optional_hosts = {host["host_id"]: {**host, **results[host["host_id"]]}
                          for host in _OPTIONAL_HOSTS}
        hosts = [
            {
                "host_id": "camrui",
                "display_name": "Camrui",
                "identity_state": "verified",
                "state": "healthy" if results["grace-autonomic-0.6b"]["state"] == "ready" else "degraded",
                "observed_at": results["grace-autonomic-0.6b"]["observed_at"],
                "gpu_inventory": {"state": "unavailable", "source": "not_configured",
                                  "observed_at": None, "devices": []},
                "inference_servers": [results["grace-autonomic-0.6b"]],
                "storage": camrui_storage,
            },
            {
                "host_id": "octominer1",
                "display_name": "OCTOMINER1",
                "identity_state": "verified",
                "state": "healthy" if gpu["state"] == "healthy" else "degraded",
                "observed_at": gpu["observed_at"],
                "gpu_inventory": {"state": gpu["state"], "source": "nvidia-smi via restricted SSH",
                                  "observed_at": gpu["observed_at"], "error_code": gpu["error_code"],
                                  "devices": gpu["devices"]},
                "system_metrics": gpu.get("system_metrics", self._project_system_metrics({}, gpu.get("observed_at"))),
                "inference_servers": [results["grace-reasoning-80b"], results["grace-vision-30b"]],
                "storage": gpu["storage"],
                "bambu_printer": gpu.get("bambu_printer", _project_bambu_status(None)),
            },
            {
                "host_id": "octominer2", "display_name": "OCTO2",
                "identity_state": "verified" if optional_hosts["octominer2"]["state"] == "healthy" else "documented_unverified",
                "state": optional_hosts["octominer2"]["state"],
                "observed_at": optional_hosts["octominer2"]["observed_at"],
                "gpu_inventory": {"state": "healthy" if optional_hosts["octominer2"]["devices"] else "unavailable",
                                  "source": "nvidia-smi via pinned read-only SSH" if optional_hosts["octominer2"]["devices"] else "not_observed",
                                  "observed_at": optional_hosts["octominer2"]["observed_at"],
                                  "devices": optional_hosts["octominer2"]["devices"],
                                  "error_code": optional_hosts["octominer2"]["error_code"]},
                "system_metrics": optional_hosts["octominer2"]["system_metrics"],
                "inference_servers": [], "storage": optional_hosts["octominer2"]["storage"],
            },
            {
                "host_id": "windows-development", "display_name": "Windows development machine",
                "identity_state": "verified" if optional_hosts["windows-development"]["state"] == "healthy" else "documented_not_connected",
                "state": optional_hosts["windows-development"]["state"],
                "observed_at": optional_hosts["windows-development"]["observed_at"],
                "gpu_inventory": {"state": "healthy" if optional_hosts["windows-development"]["devices"] else "unavailable",
                                  "source": "nvidia-smi via pinned read-only SSH" if optional_hosts["windows-development"]["devices"] else "not_observed",
                                  "observed_at": optional_hosts["windows-development"]["observed_at"],
                                  "devices": optional_hosts["windows-development"]["devices"],
                                  "error_code": optional_hosts["windows-development"]["error_code"]},
                "system_metrics": optional_hosts["windows-development"]["system_metrics"],
                "inference_servers": [], "storage": optional_hosts["windows-development"]["storage"],
            },
        ]
        sources = [host["state"] for host in hosts]
        status = "healthy" if all(value == "healthy" for value in sources) else "partial"
        if all(host["state"] == "unavailable" for host in hosts):
            status = "unavailable"
        storage_states = [host["storage"]["state"] for host in hosts]
        storage_status = ("healthy" if all(value == "healthy" for value in storage_states)
                          else "partial" if any(value == "healthy" for value in storage_states)
                          else "unavailable")
        return {
            "schema_version": SCHEMA_VERSION,
            "component_id": "STEWARD-DASHBOARD-RESOURCE-TELEMETRY",
            "status": status,
            "observed_at": _utc_now(),
            "freshness_window_seconds": 30,
            "collection_model": "request_driven_no_cache",
            "storage_status": storage_status,
            "storage_observed_at": _utc_now(),
            "hosts": hosts,
        }
