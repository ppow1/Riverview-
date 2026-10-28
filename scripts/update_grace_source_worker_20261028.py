#!/usr/bin/env python3
# Riverview~ controlled source
# File: scripts/update_grace_source_worker_20261028.py
# Revision: 1.0.1 | 2026-10-28
# Task: GRACE-SOURCE-WORKER-APPROVED-UPDATE-20261028
# Authority: PR #369 approved source-worker repo pin and allowlist reconciliation only
# =============================================================================
"""Guarded operator update for Grace's existing source-worker drop-in only.

Default mode is --dry-run. --apply/--rollback require root, the exact observed
predecessor configuration, active owner-session health, and an idle owner
ControlGroup containing only its stable MainPID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import time


UNIT = "riverview-grace-execution-owner-session.service"
CGROUP_ROOT = Path("/sys/fs/cgroup")
STARTUP_TIMEOUT_SECONDS = 40
STARTUP_STABLE_SECONDS = 5
STARTUP_POLL_SECONDS = 1
CONFIG = Path("/etc/systemd/system/riverview-grace-execution-owner-session.service.d/~~~~~~~~~~~~~~~~rv-source-worker.conf")
BASELINE_CONFIG_SHA256 = "f72a87d7f559372f6d8332a1fc3be4c1eb6e0fda8c6b6f3a16a0d48e798080d6"
ENGINEERING_REPO = Path("/home/admin1/.local/share/riverview/engineering/Riverview")
RELEASES = Path("/opt/riverview-engineering-source-worker/releases")
OLD_REVISION = "4391e3f1283277ee0582000e7170c497d791f7f2"
OLD_RELEASE = RELEASES / OLD_REVISION
TARGET_REVISION = "9f56cb72f3bd2961babf2527a26bd843526e18ce"
TARGET_RELEASE = RELEASES / TARGET_REVISION
REPOSITORY_REF = "repo://ppow1/Riverview-"
WORKER_ID = "worker:grace-engineering-source-change"
APPROVED_PATHS = (
    "tests/test_local_reasoning_provider.py",
    "src/riverview_core/resident_execution/pipeline.py",
    "src/riverview_core/resident_execution/service.py",
    "tests/test_grace_execution.py",
)
RELEASE_MANIFEST_PATHS = (
    "docs/components/WORKER_ADAPTER.md",
    "src/riverview_core/worker_adapter/adapter.py",
    "src/riverview_core/worker_adapter/continuous.py",
    "src/riverview_core/worker_adapter/knowledge_provider_v1/contract.py",
    "src/riverview_core/worker_adapter/repository_knowledge.py",
)
MUTABLE_KEYS = {
    "RIVERVIEW_SOURCE_CODEX_REPOSITORY_PATH": str(TARGET_RELEASE),
    "RIVERVIEW_SOURCE_CODEX_REPOSITORY_REVISION": TARGET_REVISION,
    "RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS": json.dumps(APPROVED_PATHS, separators=(",", ":")),
}
SOURCE_KEYS = (
    "RIVERVIEW_SOURCE_WORKER_ENABLED",
    "RIVERVIEW_SOURCE_WORKER_ID",
    "RIVERVIEW_SOURCE_WORKER_PRINCIPAL",
    "RIVERVIEW_SOURCE_CODEX_REPOSITORY_PATH",
    "RIVERVIEW_SOURCE_CODEX_REPOSITORY_REF",
    "RIVERVIEW_SOURCE_CODEX_REPOSITORY_REVISION",
    "RIVERVIEW_SOURCE_CODEX_WORKSPACE_DIR",
    "RIVERVIEW_SOURCE_CODEX_ARTIFACT_DIR",
    "RIVERVIEW_SOURCE_TEST_PYTHON",
    "RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS",
)
BASELINE_EXPECTED = {
    "RIVERVIEW_SOURCE_WORKER_ENABLED": "1",
    "RIVERVIEW_SOURCE_WORKER_ID": WORKER_ID,
    "RIVERVIEW_SOURCE_WORKER_PRINCIPAL": WORKER_ID,
    "RIVERVIEW_SOURCE_CODEX_REPOSITORY_PATH": str(OLD_RELEASE),
    "RIVERVIEW_SOURCE_CODEX_REPOSITORY_REF": REPOSITORY_REF,
    "RIVERVIEW_SOURCE_CODEX_REPOSITORY_REVISION": OLD_REVISION,
    "RIVERVIEW_SOURCE_CODEX_WORKSPACE_DIR": "/var/lib/riverview-grace-owner-session/source-worker/workspaces",
    "RIVERVIEW_SOURCE_CODEX_ARTIFACT_DIR": "/var/lib/riverview-grace-owner-session/source-worker/artifacts",
    "RIVERVIEW_SOURCE_TEST_PYTHON": "/usr/bin/python3",
    "RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS": '["tests/test_local_reasoning_provider.py"]',
}
BACKUP = CONFIG.with_name(CONFIG.name + ".pre-" + BASELINE_CONFIG_SHA256)
RECEIPT = CONFIG.with_name(CONFIG.name + ".update-20261028.json")


class GuardFailure(RuntimeError):
    """Bounded safe failure code; never carries command output or secrets."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _systemd_unquote(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
        value = value.replace('\\"', '"').replace('\\\\', '\\')
    return value


def parse_dropin_environment(data: bytes) -> dict[str, str]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeError:
        raise GuardFailure("dropin_encoding_invalid") from None
    found: dict[str, str] = {}
    for line in lines:
        if not line.startswith("Environment="):
            continue
        assignment = _systemd_unquote(line[len("Environment="):])
        key, sep, value = assignment.partition("=")
        if sep and key in SOURCE_KEYS:
            if key in found:
                raise GuardFailure("dropin_source_key_duplicate")
            found[key] = value
    if set(found) != set(SOURCE_KEYS):
        raise GuardFailure("dropin_source_keys_incomplete")
    return found


def render_dropin(data: bytes) -> bytes:
    """Replace exactly the approved source path, pin, and allowlist entries."""
    current = parse_dropin_environment(data)
    if current != BASELINE_EXPECTED:
        raise GuardFailure("dropin_source_baseline_mismatch")
    replacements = {
        "RIVERVIEW_SOURCE_CODEX_REPOSITORY_PATH": str(TARGET_RELEASE),
        "RIVERVIEW_SOURCE_CODEX_REPOSITORY_REVISION": TARGET_REVISION,
        "RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS": json.dumps(
            list(APPROVED_PATHS), separators=(",", ":")),
    }
    lines = data.decode("utf-8").splitlines(keepends=True)
    counts = {key: 0 for key in replacements}
    result = []
    for line in lines:
        if not line.startswith("Environment="):
            result.append(line)
            continue
        assignment = _systemd_unquote(line[len("Environment="):].rstrip("\r\n"))
        key, sep, _value = assignment.partition("=")
        if sep and key in replacements:
            counts[key] += 1
            value = replacements[key]
            if key == "RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS":
                encoded = json.dumps(value, ensure_ascii=False)
                result.append(f'Environment="{key}={encoded[1:-1]}"\n')
            else:
                result.append(f"Environment={key}={value}\n")
        else:
            result.append(line)
    if any(count != 1 for count in counts.values()):
        raise GuardFailure("dropin_mutable_key_count_invalid")
    updated = "".join(result).encode("utf-8")
    new_values = parse_dropin_environment(updated)
    expected = {**BASELINE_EXPECTED, **replacements}
    if new_values != expected:
        raise GuardFailure("dropin_render_validation_failed")
    return updated


def parse_loaded_environment(raw: str, keys: tuple[str, ...] = SOURCE_KEYS) -> dict[str, str]:
    """Select only named source settings; unrelated environment values are discarded."""
    selected: dict[str, str] = {}
    wanted = set(keys)
    try:
        tokens = shlex.split(raw)
    except ValueError:
        raise GuardFailure("loaded_environment_parse_failed") from None
    for token in tokens:
        key, sep, value = token.partition("=")
        if sep and key in wanted:
            # systemd concatenates Environment= assignments from the unit and
            # drop-ins; the last assignment is the effective value.
            selected[key] = value
    if set(selected) != wanted:
        raise GuardFailure("loaded_source_keys_incomplete")
    return selected


def atomic_replace(path: Path, data: bytes, *, mode: int, uid: int, gid: int) -> None:
    """Atomically replace one file, retaining its existing owner/group/mode."""
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    temp = Path(name)
    try:
        os.fchown(fd, uid, gid)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        temp.unlink(missing_ok=True)
        raise


def create_backup(path: Path, backup: Path, original: bytes, info: os.stat_result) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(backup, flags, info.st_mode & 0o7777)
    try:
        os.fchown(fd, info.st_uid, info.st_gid)
        os.fchmod(fd, stat.S_IMODE(info.st_mode))
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        backup.unlink(missing_ok=True)
        raise


def transition_with_rollback(path: Path, original: bytes, candidate: bytes,
                             info: os.stat_result, activate, restore_activation) -> None:
    """Apply one config file and restore its exact predecessor if health fails."""
    try:
        atomic_replace(path, candidate, mode=stat.S_IMODE(info.st_mode),
                       uid=info.st_uid, gid=info.st_gid)
        activate()
    except Exception:
        current = path.read_bytes()
        if current == original:
            raise GuardFailure("apply_config_write_failed_no_change") from None
        if current != candidate:
            raise GuardFailure("candidate_config_changed_during_rollback") from None
        try:
            atomic_replace(path, original, mode=stat.S_IMODE(info.st_mode),
                           uid=info.st_uid, gid=info.st_gid)
            restore_activation()
        except Exception:
            raise GuardFailure("apply_failed_automatic_rollback_incomplete") from None
        raise GuardFailure("apply_postcheck_failed_rolled_back") from None


def _git(repo: Path, *args: str, timeout: int = 30) -> str:
    command = ["/usr/bin/git", "-c", f"safe.directory={repo}", "-C", str(repo), *args]
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, timeout=timeout, check=False, close_fds=True)
    if result.returncode:
        raise GuardFailure("git_preflight_failed")
    return result.stdout.strip()


def verify_checkout(repo: Path, revision: str) -> None:
    if _git(repo, "rev-parse", "--show-toplevel") != str(repo.resolve()):
        raise GuardFailure("checkout_root_mismatch")
    if _git(repo, "rev-parse", "HEAD") != revision:
        raise GuardFailure("checkout_revision_mismatch")
    status = _git(repo, "status", "--porcelain", "--untracked-files=all")
    untracked = set()
    tracked_changes = []
    for line in status.splitlines():
        if line.startswith("?? "):
            untracked.add(line[3:])
        else:
            tracked_changes.append(line)
    if tracked_changes or untracked != {"PACKAGE_SHA256SUMS", "SOURCE_COMMIT"}:
        raise GuardFailure("checkout_not_clean")
    _verify_release_manifest(repo, revision)


def verify_commit_paths(repo: Path, revision: str) -> None:
    for relative in (*APPROVED_PATHS, *RELEASE_MANIFEST_PATHS):
        _git(repo, "cat-file", "-e", f"{revision}:{relative}")


def _verify_release_manifest(root: Path, revision: str) -> None:
    try:
        marker = (root / "SOURCE_COMMIT").read_text(encoding="ascii")
        rows = (root / "PACKAGE_SHA256SUMS").read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        raise GuardFailure("release_package_metadata_unavailable") from None
    if marker != revision + "\n":
        raise GuardFailure("release_source_marker_mismatch")
    expected = (*RELEASE_MANIFEST_PATHS, "SOURCE_COMMIT")
    if len(rows) != len(expected):
        raise GuardFailure("release_manifest_membership_invalid")
    for row, relative in zip(rows, expected):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", row)
        if not match or match.group(2) != relative:
            raise GuardFailure("release_manifest_membership_invalid")
        path = root / relative
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or path.is_symlink() or sha256(path.read_bytes()) != match.group(1):
                raise GuardFailure("release_manifest_digest_mismatch")
        except OSError:
            raise GuardFailure("release_manifest_digest_mismatch") from None


def _write_release_manifest(root: Path, revision: str) -> None:
    marker = (revision + "\n").encode("ascii")
    (root / "SOURCE_COMMIT").write_bytes(marker)
    rows = []
    for relative in RELEASE_MANIFEST_PATHS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise GuardFailure("release_manifest_source_missing")
        rows.append(f"{sha256(path.read_bytes())}  {relative}")
    rows.append(f"{sha256(marker)}  SOURCE_COMMIT")
    (root / "PACKAGE_SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="ascii")


def stage_exact_checkout(source: Path, destination: Path, revision: str,
                         predecessor: os.stat_result | None = None) -> bool:
    """Clone only committed Git objects, checkout exact commit, optionally seal release."""
    if destination.exists():
        verify_checkout(destination, revision)
        return False
    if _git(source, "cat-file", "-e", revision + "^{commit}"):
        raise GuardFailure("unexpected_git_object_output")
    parent = destination.parent
    if not parent.is_dir():
        raise GuardFailure("release_parent_missing")
    temp = Path(tempfile.mkdtemp(prefix="." + revision + ".staging-", dir=parent))
    shutil.rmtree(temp)
    try:
        cmd = ["/usr/bin/git", "-c", f"safe.directory={source}", "clone", "--quiet",
               "--no-hardlinks", "--no-checkout", "--no-recurse-submodules", str(source), str(temp)]
        result = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=180, check=False, close_fds=True)
        if result.returncode:
            raise GuardFailure("immutable_clone_failed")
        _git(temp, "checkout", "--quiet", "--detach", revision)
        _git(temp, "remote", "remove", "origin")
        _write_release_manifest(temp, revision)
        verify_checkout(temp, revision)
        for relative in APPROVED_PATHS:
            if not (temp / relative).is_file():
                raise GuardFailure("approved_target_path_missing")
        if predecessor is not None:
            _seal_release(temp, predecessor.st_uid, predecessor.st_gid)
        os.rename(temp, destination)
        return True
    except Exception:
        _make_writable(temp)
        shutil.rmtree(temp, ignore_errors=True)
        raise


def _seal_release(root: Path, uid: int, gid: int) -> None:
    entries = [root, *root.rglob("*")]
    for path in sorted(entries, key=lambda p: len(p.parts), reverse=True):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            continue
        os.chown(path, uid, gid, follow_symlinks=False)
        mode = stat.S_IMODE(info.st_mode) & ~0o222
        os.chmod(path, mode, follow_symlinks=False)


def _make_writable(root: Path) -> None:
    if not root.exists():
        return
    for path in [root, *root.rglob("*")]:
        try:
            if not path.is_symlink():
                os.chmod(path, stat.S_IMODE(path.lstat().st_mode) | 0o700)
        except OSError:
            pass


def _run(argv: list[str], code: str, *, timeout: int = 20) -> str:
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, timeout=timeout, check=False, close_fds=True)
    except (OSError, subprocess.SubprocessError):
        raise GuardFailure(code) from None
    if result.returncode:
        raise GuardFailure(code)
    return result.stdout.strip()


def systemd_property(name: str) -> str:
    try:
        result = subprocess.run(["/usr/bin/systemctl", "show", UNIT,
            "--property=" + name, "--value"], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20,
            check=False, close_fds=True)
    except (OSError, subprocess.SubprocessError):
        raise GuardFailure("systemd_property_unavailable") from None
    if result.returncode:
        reason = "systemd_bus_unavailable" if "Failed to connect to bus" in result.stderr else "systemd_property_unavailable"
        raise GuardFailure(reason)
    return result.stdout.strip()


def systemd_source_values() -> dict[str, str]:
    raw = systemd_property("Environment")
    return parse_loaded_environment(raw)


def verify_loaded(expected: dict[str, str]) -> None:
    dropins = systemd_property("DropInPaths").split()
    if str(CONFIG) not in dropins:
        raise GuardFailure("source_dropin_not_loaded")
    if systemd_property("NeedDaemonReload").lower() != "no":
        raise GuardFailure("systemd_reload_pending")
    if systemd_source_values() != expected:
        raise GuardFailure("loaded_source_environment_mismatch")


def _unit_active() -> bool:
    return systemd_property("ActiveState") == "active" and int(systemd_property("MainPID") or "0") > 1


def _control_group_processes(control_group: str,
                             cgroup_root: Path = CGROUP_ROOT) -> set[int]:
    try:
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
        pids: set[int] = set()
        for process_file in process_files:
            if not process_file.exists():
                raise GuardFailure("unit_cgroup_state_unavailable")
            resolved = process_file.resolve(strict=True)
            if group not in resolved.parents:
                raise GuardFailure("unit_cgroup_state_unavailable")
            for line in process_file.read_text(encoding="ascii").splitlines():
                if not line.isdecimal() or int(line) <= 1:
                    raise GuardFailure("unit_cgroup_state_unavailable")
                pids.add(int(line))
        if not pids:
            raise GuardFailure("unit_cgroup_state_unavailable")
        return pids
    except GuardFailure:
        raise
    except (OSError, UnicodeError, ValueError):
        raise GuardFailure("unit_cgroup_state_unavailable") from None


def _check_idle_cgroup(expected_pid: str, cgroup_root: Path = CGROUP_ROOT) -> None:
    """Require a stable owner MainPID and no other process in its cgroup."""
    try:
        if (systemd_property("ActiveState") != "active" or
                systemd_property("MainPID") != expected_pid or
                int(expected_pid) <= 1):
            raise GuardFailure("owner_session_pid_unstable")
        control_group = systemd_property("ControlGroup")
        pids = _control_group_processes(control_group, cgroup_root)
        if pids != {int(expected_pid)}:
            raise GuardFailure("owner_session_cgroup_busy")
        if (systemd_property("ControlGroup") != control_group or
                systemd_property("MainPID") != expected_pid or
                systemd_property("ActiveState") != "active"):
            raise GuardFailure("owner_session_pid_unstable")
    except (TypeError, ValueError):
        raise GuardFailure("owner_session_pid_unstable") from None


def _journal_startup_state(started: str) -> tuple[bool, bool]:
    if not started:
        raise GuardFailure("unit_start_timestamp_unavailable")
    raw = _run(["/usr/bin/journalctl", "--unit", UNIT, "--since", started,
                "--output=cat", "--no-pager"], "service_journal_unavailable", timeout=30)
    return ('"event": "grace_execution_service_started"' in raw,
            '"event": "source_change_worker_unavailable"' in raw)


def _journal_has_source_failure(started: str) -> bool:
    return _journal_startup_state(started)[1]


def verify_service_health(expected: dict[str, str], previous_pid: str | None = None) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    ready_since: float | None = None
    stable_pid: str | None = None
    started = ""
    while time.monotonic() < deadline:
        try:
            if _unit_active():
                pid = systemd_property("MainPID")
                if previous_pid is not None and pid == previous_pid:
                    time.sleep(STARTUP_POLL_SECONDS)
                    continue
                if stable_pid is None:
                    stable_pid = pid
                elif pid != stable_pid:
                    raise GuardFailure("owner_session_pid_unstable")
                verify_loaded(expected)
                if not started:
                    started = systemd_property("ExecMainStartTimestamp")
                service_started, source_failed = _journal_startup_state(started)
                if source_failed:
                    raise GuardFailure("source_worker_startup_unavailable")
                if service_started:
                    if ready_since is None:
                        ready_since = time.monotonic()
                    elif time.monotonic() - ready_since >= STARTUP_STABLE_SECONDS:
                        # This confirms stable service startup/configuration only;
                        # an actual source-worker task remains the acceptance check.
                        return
        except GuardFailure as exc:
            if str(exc) not in {"systemd_property_unavailable"}:
                raise
        time.sleep(STARTUP_POLL_SECONDS)
    reason = "owner_session_startup_signal_missing" if ready_since is None else "owner_session_health_not_stable"
    raise GuardFailure(reason)


def _preflight() -> tuple[bytes, bytes, os.stat_result, dict[str, str], str]:
    if CONFIG.is_symlink() or not CONFIG.is_file():
        raise GuardFailure("source_dropin_not_regular")
    original = CONFIG.read_bytes()
    if sha256(original) != BASELINE_CONFIG_SHA256:
        raise GuardFailure("source_dropin_baseline_hash_mismatch")
    baseline = parse_dropin_environment(original)
    if baseline != BASELINE_EXPECTED:
        raise GuardFailure("source_dropin_baseline_values_mismatch")
    desired = render_dropin(original)
    desired_values = {**baseline, **MUTABLE_KEYS}
    info = CONFIG.stat(follow_symlinks=False)
    verify_checkout(OLD_RELEASE, OLD_REVISION)
    source_commit = _git(ENGINEERING_REPO, "show", "-s", "--format=%H", TARGET_REVISION)
    if source_commit != TARGET_REVISION:
        raise GuardFailure("target_commit_unavailable")
    verify_commit_paths(ENGINEERING_REPO, TARGET_REVISION)
    state = systemd_property("ActiveState")
    main_pid = systemd_property("MainPID")
    if state != "active" or int(main_pid or "0") <= 1:
        raise GuardFailure("owner_session_not_active")
    _check_idle_cgroup(main_pid)
    if systemd_property("NeedDaemonReload").lower() != "no":
        raise GuardFailure("systemd_baseline_reload_pending")
    verify_loaded(baseline)
    started = systemd_property("ExecMainStartTimestamp")
    if _journal_has_source_failure(started):
        raise GuardFailure("source_worker_baseline_unavailable")
    if BACKUP.exists() or RECEIPT.exists():
        raise GuardFailure("update_backup_already_exists")
    return original, desired, info, desired_values, main_pid


def _systemctl_action(action: str) -> None:
    _run(["/usr/bin/systemctl", action], "systemd_action_failed")


def _atomic_receipt(value: dict) -> None:
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    atomic_replace(RECEIPT, data, mode=0o600, uid=0, gid=0)


def apply_update() -> dict:
    original, desired, info, desired_values, old_pid = _preflight()
    if not TARGET_RELEASE.exists():
        created = stage_exact_checkout(ENGINEERING_REPO, TARGET_RELEASE, TARGET_REVISION,
                                       OLD_RELEASE.stat(follow_symlinks=False))
    else:
        verify_checkout(TARGET_RELEASE, TARGET_REVISION)
        created = False
    # Staging can take time. Reconfirm the same owner process is alone before
    # creating rollback evidence or touching the protected drop-in.
    _check_idle_cgroup(old_pid)
    if not BACKUP.exists():
        create_backup(CONFIG, BACKUP, original, info)
    receipt = {"schema": "grace.source-worker.update.v1", "config": str(CONFIG),
        "backup": str(BACKUP), "old_sha256": BASELINE_CONFIG_SHA256,
        "new_sha256": sha256(desired), "prior_active_state": "active",
        "prior_main_pid": old_pid, "target_revision": TARGET_REVISION,
        "repository_reference": REPOSITORY_REF}
    _atomic_receipt(receipt)
    def activate_candidate():
        _systemctl_action("daemon-reload")
        verify_loaded(desired_values)
        _check_idle_cgroup(old_pid)
        _run(["/usr/bin/systemctl", "restart", UNIT], "owner_session_restart_failed", timeout=90)
        verify_service_health(desired_values, old_pid)

    def restore_predecessor():
        _systemctl_action("daemon-reload")
        _run(["/usr/bin/systemctl", "restart", UNIT],
             "automatic_rollback_restart_failed", timeout=90)
        verify_service_health(BASELINE_EXPECTED)

    transition_with_rollback(CONFIG, original, desired, info,
                             activate_candidate, restore_predecessor)
    return {"status": "UPDATED", "unit": UNIT, "worker": WORKER_ID,
        "repository_reference": REPOSITORY_REF, "revision": TARGET_REVISION,
        "repository_path": str(TARGET_RELEASE), "allowlist": list(APPROVED_PATHS),
        "old_config_sha256": BASELINE_CONFIG_SHA256,
        "new_config_sha256": sha256(desired), "backup": str(BACKUP),
        "backup_sha256": sha256(original), "release_created": created,
        "other_workers_or_grants_changed": False}


def rollback_update() -> dict:
    if not CONFIG.is_file() or CONFIG.is_symlink() or not BACKUP.is_file() or not RECEIPT.is_file():
        raise GuardFailure("rollback_evidence_missing")
    current = CONFIG.read_bytes()
    backup = BACKUP.read_bytes()
    try:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise GuardFailure("rollback_receipt_invalid") from None
    if (receipt.get("schema") != "grace.source-worker.update.v1" or
            receipt.get("config") != str(CONFIG) or receipt.get("backup") != str(BACKUP) or
            receipt.get("old_sha256") != BASELINE_CONFIG_SHA256 or
            receipt.get("new_sha256") != sha256(current) or
            sha256(backup) != BASELINE_CONFIG_SHA256 or
            receipt.get("prior_active_state") != "active"):
        raise GuardFailure("rollback_hash_or_receipt_mismatch")
    desired_values = parse_dropin_environment(current)
    verify_loaded(desired_values)
    main_pid = systemd_property("MainPID")
    _check_idle_cgroup(main_pid)
    info = CONFIG.stat(follow_symlinks=False)
    atomic_replace(CONFIG, backup, mode=stat.S_IMODE(info.st_mode),
                   uid=info.st_uid, gid=info.st_gid)
    try:
        _systemctl_action("daemon-reload")
        verify_loaded(BASELINE_EXPECTED)
        _check_idle_cgroup(main_pid)
        _run(["/usr/bin/systemctl", "restart", UNIT], "rollback_restart_failed", timeout=90)
        verify_service_health(BASELINE_EXPECTED)
    except Exception:
        # Restore the candidate config if predecessor activation cannot be verified.
        try:
            atomic_replace(CONFIG, current, mode=stat.S_IMODE(info.st_mode),
                           uid=info.st_uid, gid=info.st_gid)
            _systemctl_action("daemon-reload")
        except Exception:
            raise GuardFailure("rollback_failed_and_candidate_restore_incomplete") from None
        raise GuardFailure("rollback_postcheck_failed_candidate_config_restored") from None
    return {"status": "ROLLED_BACK", "unit": UNIT,
        "restored_config_sha256": sha256(backup), "prior_active_state": "active",
        "backup_retained": True, "release_retained_immutable": True}


def dry_run() -> dict:
    original, desired, _info, desired_values, _pid = _preflight()
    target_exists = TARGET_RELEASE.exists()
    if target_exists:
        verify_checkout(TARGET_RELEASE, TARGET_REVISION)
    return {"status": "DRY_RUN_OK", "unit": UNIT, "worker": WORKER_ID,
        "config_sha256": sha256(original), "candidate_config_sha256": sha256(desired),
        "repository_reference": REPOSITORY_REF, "revision": TARGET_REVISION,
        "repository_path": str(TARGET_RELEASE), "target_release_exists": target_exists,
        "allowlist": list(APPROVED_PATHS), "loaded_source_values_match": True,
        "no_files_or_services_changed": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    args = parser.parse_args(argv)
    selected = "apply" if args.apply else "rollback" if args.rollback else "dry-run"
    try:
        if selected != "dry-run" and os.geteuid() != 0:
            raise GuardFailure("root_required_for_protected_update")
        result = dry_run() if selected == "dry-run" else apply_update() if selected == "apply" else rollback_update()
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except GuardFailure as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    except (OSError, subprocess.SubprocessError, UnicodeError):
        print(json.dumps({"status": "BLOCKED", "reason": "operator_update_io_failed"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
