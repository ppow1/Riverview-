#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/rv_gpu_telemetry_command.py
# Component: OCTOMINER1-RESTRICTED-GPU-TELEMETRY
# Revision: 1.1.1
# Purpose: Return bounded NVIDIA and mounted-storage readings through an SSH forced command
# Execution Model: Request-driven; invoked only by the restricted telemetry SSH identity
# Observability: rv.gpu-host-telemetry.v1 JSON with optional storage_volumes; stable failure codes
# Dependencies: Python standard library, nvidia-smi, systemctl read-only queries
# Inputs/Outputs: No arguments/stdin; device metrics, allowlisted service labels, mounted-volume capacity
# Authority: Read-only NVIDIA/systemd queries; no shell, model control, or arbitrary command path
# Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Accept NVIDIA bracketed N/A values without dropping P100 rows
# Changed: 2026-10-23 UTC | RV-COMFYUI-GPU-POOL-20261023 | Expose stable GPU UUID, compute capability, and active compute-process count without PIDs
# Changed: 2026-10-22 UTC | RV-V2-STORAGE-CAPACITY-001 | Include deduplicated read-only mount capacity in existing telemetry response
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
from pathlib import Path
import re
import subprocess
import sys


SCHEMA_VERSION = "rv.gpu-host-telemetry.v1"
MAX_OUTPUT_BYTES = 64 * 1024
_DEVICE_FIELDS = (
    "name,index,uuid,compute_cap,utilization.gpu,memory.used,memory.total,"
    "temperature.gpu,power.draw,fan.speed"
)
_SERVICE_LABELS = {
    "llama-server.service": "grace-reasoning-80b",
    "grace-vision.service": "grace-vision-30b",
    "riverview-comfyui.service": "riverview-comfyui",
}
_GPU_UUID = re.compile(r"^GPU-(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$")
_COMPUTE_CAPABILITY = re.compile(r"^[1-9][0-9]?\.[0-9]{1,2}$")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._+() -]{1,100}$")
_VOLUME_FILESYSTEMS = frozenset({
    "ext2", "ext3", "ext4", "xfs", "btrfs", "vfat", "exfat", "ntfs", "ntfs3",
    "fuseblk", "zfs", "nfs", "nfs4", "cifs", "smb3",
})


def _unescape_mount(value: str) -> str:
    return (value.replace("\\040", " ").replace("\\011", "\t")
            .replace("\\012", "\n").replace("\\134", "\\"))


def _storage_volumes(mountinfo_path: str = "/proc/self/mountinfo") -> list[dict]:
    """Return mounted physical/network volumes; ignore pseudo filesystems and bind duplicates."""
    lines = Path(mountinfo_path).read_text(encoding="utf-8").splitlines()
    if len(lines) > 512:
        raise ValueError("mount_inventory_too_large")
    found = {}
    aliases = {}
    for line in lines:
        before, sep, after = line.partition(" - ")
        fields, tail = before.split(), after.split()
        if not sep or len(fields) < 5 or len(tail) < 2:
            continue
        major_minor = fields[2]
        if not re.fullmatch(r"\d{1,5}:\d{1,5}", major_minor):
            continue
        mount_point, fs_type, source = _unescape_mount(fields[4]), tail[0], _unescape_mount(tail[1])
        if fs_type not in _VOLUME_FILESYSTEMS:
            continue
        try:
            stats = os.statvfs(mount_point)
            fragment = int(stats.f_frsize or stats.f_bsize)
            blocks, free, available = int(stats.f_blocks), int(stats.f_bfree), int(stats.f_bavail)
            if fragment <= 0 or blocks <= 0 or not 0 <= available <= free <= blocks:
                continue
        except (OSError, TypeError, ValueError, OverflowError):
            continue
        total, used, available_bytes = blocks * fragment, (blocks - free) * fragment, available * fragment
        if total <= 0 or len(source) > 256 or any(ord(char) < 32 for char in source):
            continue
        network = fs_type in {"nfs", "nfs4", "cifs", "smb3"}
        key = (major_minor, fs_type, source)
        row = {"major_minor": major_minor, "filesystem_type": fs_type,
               "source": source, "mount_point": mount_point,
               "total_bytes": total, "used_bytes": used,
               "available_bytes": available_bytes, "observed_at": None}
        aliases.setdefault(key, set()).add(mount_point)
        previous = found.get(key)
        if previous is None or (len(mount_point), mount_point) < (len(previous["mount_point"]), previous["mount_point"]):
            found[key] = row
    result = []
    for key, row in sorted(found.items(), key=lambda item: (item[1]["mount_point"], item[0])):
        row["also_mounted_at"] = sorted(aliases[key] - {row["mount_point"]})[:16]
        result.append(row)
    return result


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
        try:
            output = _run(["/usr/bin/systemctl", "show", "--property=MainPID", "--value", unit])
        except (OSError, subprocess.SubprocessError):
            # Optional service labels must not suppress otherwise valid GPU telemetry.
            continue
        match = re.fullmatch(r"\s*(\d+)\s*", output)
        if match and int(match.group(1)) > 0:
            service_pids[int(match.group(1))] = label
    services_by_uuid: dict[str, set[str]] = {}
    process_count_by_uuid: dict[str, int] = {}
    for row in app_rows:
        if len(row) < 2:
            continue
        gpu_uuid, pid_text = (field.strip() for field in row[:2])
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        process_count_by_uuid[gpu_uuid] = process_count_by_uuid.get(gpu_uuid, 0) + 1
        label = service_pids.get(pid)
        if label:
            services_by_uuid.setdefault(gpu_uuid, set()).add(label)
    devices = []
    for row in gpu_rows:
        if len(row) != 10:
            continue
        name, index, uuid, compute_cap, utilization, used, total, temperature, power, fan = (x.strip() for x in row)
        try:
            device_index = int(index)
            if not _GPU_UUID.fullmatch(uuid):
                continue
            compute_capability = compute_cap if _COMPUTE_CAPABILITY.fullmatch(compute_cap) else None
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
                "uuid": uuid,
                "name": name_value,
                "compute_capability": compute_capability,
                "memory_used_bytes": memory_used,
                "memory_total_bytes": memory_total,
                "utilization_percent": utilization_value,
                "temperature_celsius": temperature_value,
                "power_watts": _number(power),
                "fan_percent": fan_value,
                "active_services": sorted(services_by_uuid.get(uuid, set())),
                "active_compute_process_count": process_count_by_uuid.get(uuid, 0),
            })
        except (ValueError, OverflowError):
            continue
    if not devices:
        raise ValueError("gpu_inventory_unavailable")
    try:
        storage_volumes = _storage_volumes()
    except (OSError, ValueError, TypeError):
        # Storage is optional; a mount-table error must not suppress healthy GPU telemetry.
        storage_volumes = []
    return {"schema_version": SCHEMA_VERSION,
            "observed_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "devices": devices,
            "storage_volumes": storage_volumes}


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
