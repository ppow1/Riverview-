# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/resource_telemetry.py
# Component: STEWARD-DASHBOARD-RESOURCE-TELEMETRY
# Revision: 1.3.0
# Purpose: Build a read-only, timestamped projection from approved GPU, model, and storage sources
# Execution Model: Request-driven; one bounded collection per authenticated GET
# Observability: rv.dashboard.resource-telemetry.v1 with per-source state, timestamps, and safe error codes
# Dependencies: Python standard library, systemd SSH credentials, restricted OCTOMINER1 telemetry key, read-only ComfyUI API
# Inputs/Outputs: NVIDIA/storage JSON via forced-command SSH; local mountinfo; model/ComfyUI APIs; redacted host projection
# Authority: Dashboard authentication is enforced by the parent API; fixed host and endpoint allowlists only
# Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Initial read-only telemetry projection
# Changed: 2026-10-22 UTC | RV-V2-HW-AI-ENHANCEMENTS-207 | Project bounded numeric per-slot context counters without task IDs or prompt data
# Changed: 2026-10-22 UTC | RV-V2-STORAGE-CAPACITY-001 | Add local and OCTO1 mounted-volume measurements to the existing resource projection
# Changed: 2026-10-26 UTC | RV-V2-COMFYUI-RUNTIME-READOUT-20261026 | Project bounded ComfyUI version, queue counts, device and VRAM without prompt data
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
_COMFYUI_DEVICE_NAME = re.compile(r"^[A-Za-z0-9._+(): -]{1,160}$")
_COMFYUI_BASE_URL = "http://192.168.1.160:8188"
_SSH_HOST = "192.168.1.160"
_SSH_USER = "root"
_SSH_PORT = "22"
_SSH_REMOTE_COMMAND = "resource-telemetry"
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

    def _gpu_source(self) -> dict:
        observed = _utc_now()
        key = self._credential("resource-telemetry-key")
        known_hosts = self._credential("resource-telemetry-known-hosts")
        if key is None or known_hosts is None:
            return {"state": "unavailable", "observed_at": None,
                    "error_code": "telemetry_credentials_unavailable", "devices": [],
                    "storage": {"state": "unavailable", "observed_at": None,
                                "volumes": [], "error_code": "storage_credentials_unavailable"}}
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
                        "storage": {"state": "unavailable", "observed_at": None,
                                    "volumes": [], "error_code": "storage_source_unreachable"}}
            payload = json.loads(completed.stdout)
            if (not isinstance(payload, dict) or
                    payload.get("schema_version") != "rv.gpu-host-telemetry.v1" or
                    not isinstance(payload.get("devices"), list) or len(payload["devices"]) > 32):
                return {"state": "unavailable", "observed_at": None,
                        "error_code": "gpu_source_schema_invalid", "devices": [],
                        "storage": project_remote_volumes("octominer1", payload)}
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
                    "storage": project_remote_volumes("octominer1", payload)}
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, json.JSONDecodeError):
            return {"state": "unavailable", "observed_at": None,
                    "error_code": "gpu_source_unavailable", "devices": [],
                    "storage": {"state": "unavailable", "observed_at": None,
                                "volumes": [], "error_code": "storage_source_unavailable"}}

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

    def _comfyui_source(self) -> dict:
        """Project ComfyUI service, queue counts, and device memory without queue contents."""
        observed = _utc_now()
        try:
            system_stats = self._read_json(_COMFYUI_BASE_URL + "/system_stats")
            queue = self._read_json(_COMFYUI_BASE_URL + "/queue")
            system = system_stats.get("system") if isinstance(system_stats, dict) else None
            devices = system_stats.get("devices") if isinstance(system_stats, dict) else None
            running = queue.get("queue_running") if isinstance(queue, dict) else None
            pending = queue.get("queue_pending") if isinstance(queue, dict) else None
            if (not isinstance(system, dict) or not isinstance(devices, list) or len(devices) > 32
                    or not isinstance(running, list) or not isinstance(pending, list)
                    or len(running) > 10000 or len(pending) > 10000):
                raise ValueError("comfyui_schema_invalid")
            version = system.get("comfyui_version")
            if not isinstance(version, str) or not _MODEL_ID.fullmatch(version):
                raise ValueError("comfyui_version_invalid")
            projected_devices = []
            for item in devices:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                device_type = item.get("type")
                index = _safe_integer(item.get("index"))
                total = _safe_integer(item.get("vram_total"))
                free = _safe_integer(item.get("vram_free"))
                if (not isinstance(name, str) or not _COMFYUI_DEVICE_NAME.fullmatch(name)
                        or device_type not in {"cuda", "cpu", "mps", "xpu"}
                        or index is None or total is None or free is None or free > total):
                    continue
                projected_devices.append({"name": name, "type": device_type, "index": index,
                                          "vram_total_bytes": total, "vram_free_bytes": free})
            return {"service_id": "riverview-comfyui", "display_name": "ComfyUI",
                    "state": "ready", "version": version, "observed_at": observed,
                    "devices": projected_devices,
                    "queue": {"state": "measured", "running": len(running),
                              "pending": len(pending)}, "error_code": None}
        except (OSError, HTTPError, URLError, TimeoutError, ValueError, TypeError,
                json.JSONDecodeError):
            return {"service_id": "riverview-comfyui", "display_name": "ComfyUI",
                    "state": "unavailable", "version": None, "observed_at": None,
                    "devices": [], "queue": {"state": "unavailable", "running": None,
                                                "pending": None},
                    "error_code": "comfyui_source_unavailable"}
    def read(self) -> dict:
        """Return the current result; failed sources are never filled from cache."""
        tasks = {}
        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="rv-resource-read") as pool:
            tasks["gpu"] = pool.submit(self._gpu_source)
            tasks["comfyui"] = pool.submit(self._comfyui_source)
            for source in _MODEL_SOURCES:
                tasks[source["service_id"]] = pool.submit(self._model_source, source)
            results = {name: future.result(timeout=7.0) for name, future in tasks.items()}
        gpu = results["gpu"]
        camrui_storage = self._local_storage_source("camrui")
        octominer2_storage = {"state": "unavailable", "observed_at": None,
                              "volumes": [], "error_code": "host_telemetry_not_configured"}
        windows_storage = {"state": "unavailable", "observed_at": None,
                           "volumes": [], "error_code": "host_telemetry_not_configured"}
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
                "inference_servers": [results["grace-reasoning-80b"], results["grace-vision-30b"]],
                "storage": gpu["storage"],
            },
            {
                "host_id": "octominer2",
                "display_name": "OctoMiner2",
                "identity_state": "documented_unverified",
                "state": "unavailable",
                "observed_at": None,
                "gpu_inventory": {"state": "unavailable", "source": "not_configured",
                                  "observed_at": None, "devices": [],
                                  "error_code": "host_identity_or_telemetry_not_verified"},
                "inference_servers": [],
                "storage": octominer2_storage,
            },
            {
                "host_id": "windows-development",
                "display_name": "Windows development machine",
                "identity_state": "documented_not_connected",
                "state": "unavailable",
                "observed_at": None,
                "gpu_inventory": {"state": "unavailable", "source": "not_configured",
                                  "observed_at": None, "devices": [],
                                  "error_code": "host_telemetry_not_configured"},
                "inference_servers": [],
                "storage": windows_storage,
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
            "comfyui": results["comfyui"],
            "hosts": hosts,
        }
