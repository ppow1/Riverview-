# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/storage_inventory.py
# Component: STEWARD-DASHBOARD-RESOURCE-TELEMETRY
# Revision: 1.0.1
# Purpose: Read mounted storage capacity without counting duplicate bind mounts
# Changed: 2026-10-22 UTC | RV-V2-MOUNTED-STORAGE-001 | Add safe source projection details and verify live Camrui mount comparison.
# Execution Model: Request-driven helper called by the existing telemetry collector
# Observability: Returns per-host state, observed_at, volume facts, and stable error codes
# Dependencies: Linux /proc/self/mountinfo and os.statvfs
# Inputs/Outputs: Host ID and mountinfo path to bounded storage volume records
# Authority: Read-only capacity collection; no filesystem writes or mount changes
# Changed: 2026-10-22 UTC | RV-V2-STORAGE-CAPACITY-001 | Initial bounded storage projection
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_storage_inventory.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Bounded read-only Linux storage inventory for the existing resource API."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Callable


_VOLUME_FILESYSTEMS = frozenset({
    "ext2", "ext3", "ext4", "xfs", "btrfs", "vfat", "exfat", "ntfs", "ntfs3",
    "fuseblk", "zfs", "nfs", "nfs4", "cifs", "smb3",
})
_MAX_MOUNTS = 512
_MAX_TEXT = 256
_SAFE_HOST = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _unescape_mount(value: str) -> str:
    return (value.replace("\\040", " ").replace("\\011", "\t")
            .replace("\\012", "\n").replace("\\134", "\\"))


def _bounded(value: object, limit: int = _MAX_TEXT) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > limit or any(ord(char) < 32 for char in value):
        return None
    return value


def _volume_row(*, host_id: str, major_minor: str, fs_type: str, source: str,
                mount_point: str, statvfs: Callable[[str], os.statvfs_result]) -> dict | None:
    try:
        stats = statvfs(mount_point)
        fragment = int(stats.f_frsize or stats.f_bsize)
        blocks = int(stats.f_blocks)
        free_blocks = int(stats.f_bfree)
        available_blocks = int(stats.f_bavail)
        if fragment <= 0 or blocks <= 0 or not (0 <= available_blocks <= free_blocks <= blocks):
            return None
        total = blocks * fragment
        used = (blocks - free_blocks) * fragment
        available = available_blocks * fragment
    except (OSError, TypeError, ValueError, OverflowError):
        return None
    if total <= 0:
        return None
    is_network = fs_type in {"nfs", "nfs4", "cifs", "smb3"}
    stable_source = _bounded(source) or "source-unavailable"
    filesystem_id = (f"shared:{fs_type}:{stable_source}" if is_network
                     else f"{host_id}:{major_minor}:{fs_type}:{stable_source}")
    device_id = stable_source if stable_source.startswith("/dev/") or is_network else None
    return {
        "volume_id": f"{host_id}:{major_minor}:{fs_type}",
        "filesystem_id": filesystem_id[:384],
        "mount_point": mount_point[:_MAX_TEXT],
        "filesystem_type": fs_type,
        "device_id": device_id,
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "percent_used": round(used * 100.0 / total, 2),
    }


def collect_linux_storage(host_id: str, *, mountinfo_path: str | Path = "/proc/self/mountinfo",
                          statvfs: Callable[[str], os.statvfs_result] = os.statvfs) -> dict:
    """Collect supported mounted volumes; never turns an inaccessible mount into zero."""
    observed_at = _utc_now()
    if not isinstance(host_id, str) or not _SAFE_HOST.fullmatch(host_id):
        return {"state": "unavailable", "observed_at": None, "volumes": [],
                "error_code": "host_identity_invalid"}
    try:
        text = Path(mountinfo_path).read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > _MAX_MOUNTS:
            return {"state": "unavailable", "observed_at": observed_at, "volumes": [],
                    "error_code": "mount_inventory_too_large"}
    except OSError:
        return {"state": "unavailable", "observed_at": None, "volumes": [],
                "error_code": "mount_inventory_unavailable"}

    volumes: dict[str, dict] = {}
    aliases: dict[str, set[str]] = {}
    for line in lines:
        before, separator, after = line.partition(" - ")
        if not separator:
            continue
        fields, tail = before.split(), after.split()
        if len(fields) < 5 or len(tail) < 2:
            continue
        major_minor, mount_point = fields[2], _unescape_mount(fields[4])
        fs_type, source = tail[0], _unescape_mount(tail[1])
        if fs_type not in _VOLUME_FILESYSTEMS:
            continue
        row = _volume_row(host_id=host_id, major_minor=major_minor, fs_type=fs_type,
                          source=source, mount_point=mount_point, statvfs=statvfs)
        if row is None:
            continue
        key = row["filesystem_id"]
        aliases.setdefault(key, set()).add(row["mount_point"])
        existing = volumes.get(key)
        if existing is None or (len(row["mount_point"]), row["mount_point"]) < (
                len(existing["mount_point"]), existing["mount_point"]):
            volumes[key] = row
    if not volumes:
        return {"state": "unavailable", "observed_at": observed_at, "volumes": [],
                "error_code": "no_supported_mounted_volumes"}
    result = []
    for key, row in sorted(volumes.items(), key=lambda item: (item[1]["mount_point"], item[0])):
        mount_aliases = sorted(aliases[key] - {row["mount_point"]})
        if mount_aliases:
            row["also_mounted_at"] = mount_aliases[:16]
        row["observed_at"] = observed_at
        row["source"] = "linux mountinfo + statvfs"
        result.append(row)
    return {"state": "healthy", "observed_at": observed_at, "volumes": result,
            "error_code": None}


def project_remote_volumes(host_id: str, raw: object) -> dict:
    """Validate optional remote collector volume rows without trusting remote text."""
    observed_at = _utc_now()
    if not isinstance(raw, dict) or not isinstance(raw.get("storage_volumes"), list):
        return {"state": "unavailable", "observed_at": None, "volumes": [],
                "error_code": "storage_source_not_reporting"}
    volumes = []
    seen = set()
    for item in raw["storage_volumes"][:64]:
        if not isinstance(item, dict):
            continue
        fs_type = item.get("filesystem_type")
        major_minor = item.get("major_minor")
        source = _bounded(item.get("source"))
        mount_point = _bounded(item.get("mount_point"))
        if (fs_type not in _VOLUME_FILESYSTEMS or not isinstance(major_minor, str)
                or not re.fullmatch(r"\d{1,5}:\d{1,5}", major_minor)
                or not source or not mount_point):
            continue
        key = (fs_type, major_minor, source)
        if key in seen:
            continue
        seen.add(key)
        try:
            total, used, available = (item[name] for name in
                                      ("total_bytes", "used_bytes", "available_bytes"))
            if any(type(value) is not int or value < 0 for value in (total, used, available)):
                continue
            if total <= 0 or used > total or available > total:
                continue
            percent = round(used * 100.0 / total, 2)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        is_network = fs_type in {"nfs", "nfs4", "cifs", "smb3"}
        filesystem_id = (f"shared:{fs_type}:{source}" if is_network
                         else f"{host_id}:{major_minor}:{fs_type}:{source}")
        volumes.append({
            "volume_id": f"{host_id}:{major_minor}:{fs_type}",
            "filesystem_id": filesystem_id[:384],
            "mount_point": mount_point,
            "filesystem_type": fs_type,
            "device_id": source if source.startswith("/dev/") or is_network else None,
            "total_bytes": total,
            "used_bytes": used,
            "available_bytes": available,
            "percent_used": percent,
            "observed_at": _bounded(item.get("observed_at")) or _bounded(raw.get("observed_at")) or observed_at,
            "source": "OCTO1 restricted storage telemetry",
        })
    if not volumes:
        return {"state": "unavailable", "observed_at": _bounded(raw.get("observed_at")),
                "volumes": [], "error_code": "storage_inventory_empty_or_invalid"}
    return {"state": "healthy", "observed_at": _bounded(raw.get("observed_at")) or observed_at,
            "volumes": volumes, "error_code": None}
