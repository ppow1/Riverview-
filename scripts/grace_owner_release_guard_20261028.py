# Riverview~ controlled source
# File: owner_release_guard.py
# Revision: 1.0.1 | 2026-10-28
"""Read-only owner-session idle guard shared by the staged release helper/tests."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

UPDATER_ROOT = Path("/home/admin1/.local/share/riverview/engineering/Riverview")
sys.path.insert(0, str(UPDATER_ROOT))
try:
    from scripts import update_grace_source_worker_20261028 as approved
except Exception:
    approved = None

CGROUP_ROOT = Path("/sys/fs/cgroup")


class GuardFailure(RuntimeError):
    pass


def _empty_process_set(control_group: str, cgroup_root: Path) -> None:
    try:
        # Inactive systemd units with MainPID=0 may have no cgroup at all.
        if control_group == "":
            return
        if not control_group.startswith("/") or ".." in Path(control_group).parts:
            raise GuardFailure("unit_cgroup_state_unavailable")
        root = cgroup_root.resolve(strict=True)
        group = (root / control_group.lstrip("/")).resolve(strict=True)
        if root not in group.parents or not group.is_dir():
            raise GuardFailure("unit_cgroup_state_unavailable")
        process_files = [group / "cgroup.procs"]
        for child in group.rglob("*"):
            if child.is_symlink():
                raise GuardFailure("unit_cgroup_state_unavailable")
            if child.is_dir():
                process_files.append(child / "cgroup.procs")
        for process_file in process_files:
            if not process_file.exists():
                raise GuardFailure("unit_cgroup_state_unavailable")
            resolved = process_file.resolve(strict=True)
            if group not in resolved.parents:
                raise GuardFailure("unit_cgroup_state_unavailable")
            if process_file.read_text(encoding="ascii").strip():
                raise GuardFailure("owner_session_cgroup_busy")
    except GuardFailure:
        raise
    except (OSError, UnicodeError, ValueError):
        raise GuardFailure("unit_cgroup_state_unavailable") from None


def check_owner_idle(*, allow_stopped: bool = False, get_property=None,
                     cgroup_root: Path = CGROUP_ROOT) -> str:
    """Return active/stopped after proving a stable empty-or-main-only cgroup."""
    if get_property is None:
        if approved is None:
            raise GuardFailure("idle_guard_unavailable")
        get_property = approved.systemd_property
    try:
        state = get_property("ActiveState")
        pid = get_property("MainPID")
        control_group = get_property("ControlGroup")
        if state == "active":
            if not pid.isdecimal() or int(pid) <= 1:
                raise GuardFailure("owner_session_pid_unstable")
            if approved is not None and get_property is approved.systemd_property:
                approved._check_idle_cgroup(pid, cgroup_root)
            else:
                processes = approved._control_group_processes(control_group, cgroup_root)
                if processes != {int(pid)}:
                    raise GuardFailure("owner_session_cgroup_busy")
                if (get_property("ActiveState") != "active" or
                        get_property("MainPID") != pid or
                        get_property("ControlGroup") != control_group):
                    raise GuardFailure("owner_session_pid_unstable")
            return "active"
        if allow_stopped and state in {"inactive", "failed"}:
            if pid != "0":
                raise GuardFailure("owner_session_pid_unstable")
            _empty_process_set(control_group, cgroup_root)
            if (get_property("ActiveState") != state or get_property("MainPID") != "0" or
                    get_property("ControlGroup") != control_group):
                raise GuardFailure("owner_session_pid_unstable")
            return "stopped"
        raise GuardFailure("owner_session_state_unavailable")
    except GuardFailure:
        raise
    except Exception as exc:
        if approved is not None and isinstance(exc, approved.GuardFailure):
            raise GuardFailure(str(exc)) from None
        raise GuardFailure("owner_session_state_unavailable") from None


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--allow-stopped", action="store_true")
    args = parser.parse_args()
    try:
        state = check_owner_idle(allow_stopped=args.allow_stopped)
    except GuardFailure as exc:
        print(f"BLOCKED:{exc}")
        return 2
    print(state.upper())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
