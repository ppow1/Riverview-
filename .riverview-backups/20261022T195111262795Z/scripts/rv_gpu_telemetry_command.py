#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/rv_gpu_telemetry_command.py
# Component: OCTOMINER1-RESTRICTED-GPU-TELEMETRY
# Revision: 1.0.1
# Purpose: Return bounded NVIDIA readings through an SSH forced command
# Execution Model: Request-driven; invoked only by the restricted telemetry SSH identity
# Observability: rv.gpu-host-telemetry.v1 JSON; stderr contains only stable failure codes
# Dependencies: Python standard library, nvidia-smi, systemctl read-only queries
# Inputs/Outputs: No arguments/stdin; device metrics and allowlisted service labels only
# Authority: Read-only NVIDIA/systemd queries; no shell, model control, or arbitrary command path
# Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Accept NVIDIA bracketed N/A values without dropping P100 rows
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_resource_telemetry.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Read-only JSON command installed behind a forced SSH authorized_keys entry."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import json
import os
import re
import subprocess
import sys


SCHEMA_VERSION = "rv.gpu-host-telemetry.v1"
MAX_OUTPUT_BYTES = 64 * 1024
_DEVICE_FIELDS = (
    "name,index,uuid,utilization.gpu,memory.used,memory.total,"
    "temperature.gpu,power.draw,fan.speed"
)
_SERVICE_LABELS = {
    "llama-server.service": "grace-reasoning-80b",
    "grace-vision.service": "grace-vision-30b",
}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._+() -]{1,100}$")


def _run(command: list[str], *, timeout: float = 2.0) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True,
                               timeout=timeout, env={"LC_ALL": "C"})
    if len(completed.stdout.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("telemetry_output_too_large")
    return completed.stdout


def _integer(value: str) -> int | None:
    value = value.strip()
    if value in {"", "N/A", "[N/A]", "Not Supported", "[Not Supported]"}:
        return None
    number = int(value)
    return number if number >= 0 else None


def _number(value: str) -> float | None:
    value = value.strip()
    if value in {"", "N/A", "Not Supported", "[Not Supported]"}:
        return None
    number = float(value)
    return number if 0 <= number <= 10000 else None


def collect() -> dict:
    if os.environ.get("SSH_ORIGINAL_COMMAND") != "resource-telemetry":
        raise PermissionError("restricted_command_required")
    gpu_rows = list(csv.reader(io.StringIO(_run([
        "/usr/bin/nvidia-smi", f"--query-gpu={_DEVICE_FIELDS}",
        "--format=csv,noheader,nounits",
    ]))))
    app_rows = list(csv.reader(io.StringIO(_run([
        "/usr/bin/nvidia-smi", "--query-compute-apps=gpu_uuid,pid",
        "--format=csv,noheader,nounits",
    ]))))
    service_pids: dict[int, str] = {}
    for unit, label in _SERVICE_LABELS.items():
        output = _run(["/usr/bin/systemctl", "show", "--property=MainPID", "--value", unit])
        match = re.fullmatch(r"\s*(\d+)\s*", output)
        if match and int(match.group(1)) > 0:
            service_pids[int(match.group(1))] = label
    services_by_uuid: dict[str, set[str]] = {}
    for row in app_rows:
        if len(row) < 2:
            continue
        gpu_uuid, pid_text = (field.strip() for field in row[:2])
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        label = service_pids.get(pid)
        if label:
            services_by_uuid.setdefault(gpu_uuid, set()).add(label)
    devices = []
    for row in gpu_rows:
        if len(row) != 9:
            continue
        name, index, uuid, utilization, used, total, temperature, power, fan = (x.strip() for x in row)
        try:
            device_index = int(index)
            memory_used = _integer(used)
            memory_total = _integer(total)
            utilization_value = _integer(utilization)
            temperature_value = _integer(temperature)
            name_value = name if _SAFE_NAME.fullmatch(name) else "Unknown GPU"
            if memory_used is not None:
                memory_used *= 1024 * 1024
            if memory_total is not None:
                memory_total *= 1024 * 1024
            if utilization_value is not None and utilization_value > 100:
                utilization_value = None
            if temperature_value is not None and temperature_value > 200:
                temperature_value = None
            fan_value = _integer(fan)
            if fan_value is not None and fan_value > 100:
                fan_value = None
            devices.append({
                "index": device_index,
                "name": name_value,
                "memory_used_bytes": memory_used,
                "memory_total_bytes": memory_total,
                "utilization_percent": utilization_value,
                "temperature_celsius": temperature_value,
                "power_watts": _number(power),
                "fan_percent": fan_value,
                "active_services": sorted(services_by_uuid.get(uuid, set())),
            })
        except (ValueError, OverflowError):
            continue
    if not devices:
        raise ValueError("gpu_inventory_unavailable")
    return {"schema_version": SCHEMA_VERSION,
            "observed_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "devices": devices}


def main() -> int:
    try:
        report = collect()
        payload = json.dumps(report, separators=(",", ":"), sort_keys=True)
        if len(payload.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ValueError("telemetry_output_too_large")
        print(payload)
        return 0
    except PermissionError:
        print("restricted_command_required", file=sys.stderr)
        return 77
    except (OSError, subprocess.SubprocessError, ValueError, csv.Error, json.JSONDecodeError):
        print("gpu_telemetry_unavailable", file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
