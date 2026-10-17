#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW CONTROLLED SOURCE
# File: scripts/rotate_comms5_steward_credential.py
# Component: COMMS5-OAUTH-IONOGE
# Revision: 1.0.0
# Purpose: Safely validate or rotate the shared Comms5 Steward login credential
# Execution Model: Explicit privileged operator CLI
# Observability: Sanitized status output and exit code; never emits credential
# Dependencies: Python 3.10+; systemd; curl; root-owned Ionoge environment files
# Authority: Root-only; changes only two named Comms5 credential entries and restarts their services
# Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-001 | Initial controlled provision/rotation utility
# Contracts: docs/components/COMMS5_OAUTH_TROUBLESHOOTING.md
# Tests: tests/test_comms5_steward_credential.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Safely validate or replace the Comms5 Steward credential on Ionoge.

The replacement is read only from stdin, must be 43-128 base64url characters,
and is never passed in argv or printed to logs/reports. Its durable copies are
the two root-only service environment files. The utility updates them as one
guarded operation, then restarts only those two services. A failed check
restores protected predecessors and attempts to recover the previous services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


CLIENT_KEY = "RIVERVIEW_COMMS5_CLIENT_SECRET"
CADDY_ENV = Path("/etc/caddy/riverview-comms5.env")
OAUTH_ENV = Path("/etc/riverview/comms5-oauth.env")
BACKUP_ROOT = Path("/var/backups/riverview")
SERVICES = ("riverview-comms5-oauth.service", "caddy.service")
URLSAFE_SECRET = re.compile(r"^[A-Za-z0-9_-]{43,128}$")


class CredentialError(RuntimeError):
    """A sanitized, operator-actionable provisioning failure."""


def _read_assignments(path: Path) -> tuple[bytes, list[tuple[int, str]]]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CredentialError("credential_environment_file_unreadable") from exc
    matches: list[tuple[int, str]] = []
    for index, line in enumerate(text.splitlines(keepends=True)):
        if line.startswith(CLIENT_KEY + "="):
            matches.append((index, line))
    if len(matches) != 1:
        raise CredentialError("credential_environment_entry_missing_or_duplicated")
    return raw, matches


def _value_from_line(line: str) -> str:
    value = line.split("=", 1)[1].rstrip("\r\n")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    if not value or any(char in value for char in "\r\n\x00"):
        raise CredentialError("credential_environment_entry_invalid")
    return value


def inspect_configuration(
    caddy_env: Path = CADDY_ENV,
    oauth_env: Path = OAUTH_ENV,
    *,
    expected_uid: int = 0,
) -> dict[str, object]:
    """Validate files and return only nonsecret facts needed for safe rotation."""
    values: list[str] = []
    for path in (caddy_env, oauth_env):
        try:
            info = path.lstat()
        except OSError as exc:
            raise CredentialError("credential_environment_file_missing") from exc
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise CredentialError("credential_environment_file_type_invalid")
        if info.st_uid != expected_uid or stat.S_IMODE(info.st_mode) != 0o600:
            raise CredentialError("credential_environment_file_owner_or_mode_invalid")
        _, assignments = _read_assignments(path)
        values.append(_value_from_line(assignments[0][1]))
    if values[0] != values[1]:
        raise CredentialError("credential_environment_values_do_not_match")
    return {
        "files_valid": True,
        "credential_shared_by_caddy_and_oauth": True,
        "credential_nonempty": bool(values[0]),
    }


def _unit_reads_environment(
    service: str,
    path: Path,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> bool:
    if run is None:
        run = _run
    result = run(["systemctl", "show", service, "-p", "EnvironmentFiles", "--value"], timeout=10)
    if result.returncode != 0:
        return False
    return any(line.strip().startswith(str(path) + " ") or line.strip() == str(path) for line in result.stdout.splitlines())


def _validate_live_wiring(run: Callable[..., subprocess.CompletedProcess[str]] | None = None) -> None:
    if not _unit_reads_environment("caddy.service", CADDY_ENV, run):
        raise CredentialError("caddy_environment_file_not_attached")
    if not _unit_reads_environment("riverview-comms5-oauth.service", OAUTH_ENV, run):
        raise CredentialError("oauth_environment_file_not_attached")


def _require_services_active(run: Callable[..., subprocess.CompletedProcess[str]] | None = None) -> None:
    if run is None:
        run = _run
    for service in SERVICES:
        result = run(["systemctl", "is-active", "--quiet", service], timeout=10)
        if result.returncode != 0:
            raise CredentialError("target_service_not_active_at_preflight")


def _replace_value(raw: bytes, new_value: str) -> bytes:
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.startswith(CLIENT_KEY + "=")]
    if len(indices) != 1:
        raise CredentialError("credential_environment_entry_missing_or_duplicated")
    line = lines[indices[0]]
    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    lines[indices[0]] = CLIENT_KEY + "=" + new_value + ending
    return "".join(lines).encode("utf-8")


def _atomic_write(path: Path, content: bytes, *, owner_uid: int = 0) -> None:
    fd, temp_name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    temp = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        if os.geteuid() == owner_uid:
            os.fchown(fd, owner_uid, os.getegid())
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _backup_files(
    paths: tuple[Path, Path], backup_root: Path, *, owner_uid: int = 0
) -> tuple[Path, dict[str, str]]:
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o755)
    root_info = backup_root.lstat()
    if not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode) or root_info.st_uid != owner_uid:
        raise CredentialError("protected_backup_root_invalid")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = backup_root / ("comms5-steward-credential-" + stamp)
    directory.mkdir(parents=True, mode=0o700)
    os.chmod(directory, 0o700)
    if os.geteuid() == owner_uid:
        os.chown(directory, owner_uid, os.getegid())
    hashes: dict[str, str] = {}
    try:
        for source in paths:
            destination = directory / ("caddy.env" if source == paths[0] else "oauth.env")
            shutil.copy2(source, destination)
            if os.geteuid() == owner_uid:
                os.chown(destination, owner_uid, os.getegid())
            os.chmod(destination, 0o600)
            original = source.read_bytes()
            if destination.read_bytes() != original:
                raise CredentialError("protected_predecessor_verification_failed")
            hashes[str(source)] = hashlib.sha256(original).hexdigest()
        manifest = {
            "task_id": "RV-COMMS5-STEWARD-CREDENTIAL-001",
            "created_utc": stamp,
            "files": hashes,
            "restore": "restore caddy.env and oauth.env to their respective original paths, then restart only the two listed services",
            "services": list(SERVICES),
        }
        manifest_path = directory / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if os.geteuid() == owner_uid:
            os.chown(manifest_path, owner_uid, os.getegid())
        os.chmod(manifest_path, 0o600)
        return directory, hashes
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def _run(command: list[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)


def _restart_and_health(run: Callable[..., subprocess.CompletedProcess[str]] = _run) -> bool:
    for service in SERVICES:
        result = run(["systemctl", "restart", service], timeout=45)
        if result.returncode != 0:
            return False
    for service in SERVICES:
        result = run(["systemctl", "is-active", "--quiet", service], timeout=10)
        if result.returncode != 0:
            return False
    checks = (
        ["curl", "--silent", "--show-error", "--fail", "--max-time", "5", "http://127.0.0.1:11827/healthz", "--output", "/dev/null"],
        ["curl", "--silent", "--show-error", "--fail", "--max-time", "8", "https://riverview-comms.ionoge.com/.well-known/oauth-authorization-server", "--output", "/dev/null"],
        ["curl", "--silent", "--show-error", "--max-time", "8", "-o", "/dev/null", "-w", "%{http_code}", "https://riverview-comms.ionoge.com/comms5/mcp"],
    )
    for index, command in enumerate(checks):
        result = run(command, timeout=15)
        expected = result.returncode == 0
        if index == 2:
            expected = result.returncode == 0 and result.stdout.strip() == "401"
        if not expected:
            return False
    return True


def install_from_stdin(
    *,
    caddy_env: Path = CADDY_ENV,
    oauth_env: Path = OAUTH_ENV,
    backup_root: Path = BACKUP_ROOT,
    secret_input: bytes | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] = _run,
    require_root: bool = True,
) -> dict[str, object]:
    """Replace the shared credential transactionally; never return its value."""
    if require_root and os.geteuid() != 0:
        raise CredentialError("root_required")
    expected_uid = 0 if require_root else os.geteuid()
    inspect_configuration(caddy_env, oauth_env, expected_uid=expected_uid)
    if require_root:
        _validate_live_wiring(run)
        _require_services_active(run)
    if secret_input is None:
        secret_input = sys.stdin.buffer.read(258)
    if secret_input.endswith(b"\r\n"):
        secret_input = secret_input[:-2]
    elif secret_input.endswith(b"\n"):
        secret_input = secret_input[:-1]
    try:
        new_value = secret_input.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CredentialError("replacement_credential_format_invalid") from exc
    if not URLSAFE_SECRET.fullmatch(new_value):
        raise CredentialError("replacement_credential_format_invalid")

    paths = (caddy_env, oauth_env)
    protected_backup, _ = _backup_files(paths, backup_root, owner_uid=expected_uid)
    originals = [path.read_bytes() for path in paths]
    updated = [_replace_value(raw, new_value) for raw in originals]
    try:
        for path, content in zip(paths, updated):
            _atomic_write(path, content, owner_uid=expected_uid)
        if not _restart_and_health(run):
            raise CredentialError("service_restart_or_health_check_failed")
    except Exception as exc:
        for path, content in zip(paths, originals):
            try:
                _atomic_write(path, content, owner_uid=expected_uid)
            except Exception:
                raise CredentialError(
                    "credential_rollback_failed_manual_recovery_required; protected_predecessor="
                    + str(protected_backup)
                ) from None
        try:
            recovered = _restart_and_health(run)
        except Exception:
            recovered = False
        if isinstance(exc, CredentialError):
            code = str(exc)
        else:
            code = "credential_rotation_failed"
        raise CredentialError(code + ("; predecessor_restored" if recovered else "; predecessor_files_restored_service_recovery_unverified")) from None
    return {
        "status": "credential_installed",
        "secret_value_emitted": False,
        "protected_predecessor": str(protected_backup),
        "services_restarted": list(SERVICES),
        "health_checks": ["OAuth loopback health", "public authorization metadata", "anonymous MCP rejected with HTTP 401"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate live files and service wiring without changing anything")
    mode.add_argument("--install-from-stdin", action="store_true", help="replace the credential using a base64url value read from stdin")
    args = parser.parse_args(argv)
    try:
        if os.geteuid() != 0:
            raise CredentialError("root_required")
        if args.check:
            result = inspect_configuration()
            _validate_live_wiring()
            _require_services_active()
            print(json.dumps({"status": "PASS", **result}))
            return 0
        result = install_from_stdin()
        print(json.dumps(result, sort_keys=True))
        return 0
    except (CredentialError, OSError, subprocess.TimeoutExpired) as exc:
        message = str(exc) if isinstance(exc, CredentialError) else "credential_operation_failed"
        print(json.dumps({"status": "FAIL", "error": message}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
