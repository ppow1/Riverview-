# =============================================================================
# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/install_grace_owner_session.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Install the reviewed Grace owner-session unit and exact non-secret runtime configuration
# Execution Model: Root-local staged install; never enables or starts the service
# Observability: Redacted JSON reports file identities and systemd validation outcome
# Dependencies: systemd-analyze; approved immutable source release; provisioned protected credentials
# Authority: Fixed unit/config paths; explicit --apply; preserves existing files and supports file rollback
# Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PROVISIONER-001 | Initial repeatable install and restore utility
# Contracts: docs/components/GRACE_ENGINEERING_DEMO_COMMISSIONING.md; docs/components/GRACE_EXECUTION_COOKBOOK.md
# Tests: tests/test_grace_engineering_demo_provisioning.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Stage the persistent owner-session unit without enabling or starting it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys


UNIT_NAME = "riverview-grace-execution-owner-session.service"
SERVICE_ROOT = Path("/opt/riverview-grace-execution/current")
UNIT_DEST = Path("/etc/systemd/system") / UNIT_NAME
ENV_DEST = Path("/etc/riverview/grace-execution.env")
ENV_TEMPLATE = "deploy/grace-execution.env.example"
UNIT_SOURCE = "deploy/systemd/riverview-grace-execution-owner-session.service"
PLACEHOLDER = "replace-with-approved-full-lowercase-commit-id"


class InstallError(RuntimeError):
    """A strict install or rollback precondition failed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_environment(template: str, source_commit: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source_commit):
        raise InstallError("source_commit_invalid")
    if template.count(PLACEHOLDER) != 1:
        raise InstallError("environment_template_invalid")
    return template.replace(PLACEHOLDER, source_commit).encode("utf-8")


def _atomic_create(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise InstallError("destination_exists_requires_review")
    temp = path.with_name(path.name + ".tmp-" + os.urandom(6).hex())
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), mode)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if os.geteuid() == 0:
            os.chown(temp, 0, 0)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def stage_files(root: Path, unit_data: bytes, env_data: bytes) -> dict:
    unit_path = root / UNIT_DEST.relative_to("/")
    env_path = root / ENV_DEST.relative_to("/")
    created = []
    try:
        if unit_path.exists() or unit_path.is_symlink():
            raise InstallError("unit_destination_exists_requires_review")
        if env_path.exists() or env_path.is_symlink():
            raise InstallError("environment_destination_exists_requires_review")
        _atomic_create(unit_path, unit_data, 0o644)
        created.append(unit_path)
        _atomic_create(env_path, env_data, 0o640)
        created.append(env_path)
        return {"unit_sha256": _sha(unit_path), "environment_sha256": _sha(env_path),
                "created": [str(p) for p in created]}
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise


def restore_files(root: Path, *, unit_sha256: str, environment_sha256: str) -> dict:
    removed = []
    expected = {
        root / UNIT_DEST.relative_to("/"): unit_sha256,
        root / ENV_DEST.relative_to("/"): environment_sha256,
    }
    destinations = (root / ENV_DEST.relative_to("/"), root / UNIT_DEST.relative_to("/"))
    # Validate every target before deleting any file, so a mismatch cannot leave
    # a partial rollback.
    for dest in destinations:
        if dest.is_symlink():
            raise InstallError("rollback_symlink_refused")
        if dest.exists():
            info = dest.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
                raise InstallError("rollback_file_metadata_invalid")
            if not re.fullmatch(r"[0-9a-f]{64}", expected[dest]) or _sha(dest) != expected[dest]:
                raise InstallError("rollback_digest_mismatch")
    for dest in destinations:
        if dest.exists():
            dest.unlink()
            removed.append(str(dest))
    return {"removed": removed, "service_state_changed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", nargs=2, metavar=("UNIT_SHA256", "ENV_SHA256"))
    args = parser.parse_args()
    try:
        if args.rollback:
            if os.geteuid() != 0:
                raise InstallError("root_local_operation_required")
            active = subprocess.run(["systemctl", "is-active", "--quiet", UNIT_NAME],
                                    check=False, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL).returncode == 0
            if active:
                raise InstallError("stop_owner_session_before_file_rollback")
            result = restore_files(Path("/"), unit_sha256=args.rollback[0],
                                   environment_sha256=args.rollback[1])
            subprocess.run(["systemctl", "daemon-reload"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(json.dumps(result, sort_keys=True))
            return 0
        source = Path(__file__).resolve().parents[1]
        unit = (source / UNIT_SOURCE).read_bytes()
        template = (source / ENV_TEMPLATE).read_text(encoding="utf-8")
        release = SERVICE_ROOT.resolve(strict=True)
        source_commit = (release / "SOURCE_COMMIT").read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source_commit):
            raise InstallError("immutable_release_identity_invalid")
        env_data = render_environment(template, source_commit)
        if shutil.which("systemd-analyze"):
            check = subprocess.run(["systemd-analyze", "verify", "--", str(source / UNIT_SOURCE)],
                                   capture_output=True, text=True, check=False)
            if check.returncode:
                raise InstallError("systemd_unit_validation_failed")
        else:
            raise InstallError("systemd_analyzer_unavailable")
        if args.check:
            print(json.dumps({"status": "READY_TO_STAGE", "source_commit": source_commit,
                "unit_sha256": hashlib.sha256(unit).hexdigest(),
                "environment_sha256": hashlib.sha256(env_data).hexdigest(),
                "service_enabled_or_started": False}, sort_keys=True))
            return 0
        if os.geteuid() != 0:
            raise InstallError("root_local_operation_required")
        result = stage_files(Path("/"), unit, env_data)
        try:
            subprocess.run(["systemctl", "daemon-reload"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.SubprocessError:
            restore_files(Path("/"), unit_sha256=result["unit_sha256"],
                          environment_sha256=result["environment_sha256"])
            subprocess.run(["systemctl", "daemon-reload"], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            raise InstallError("systemd_reload_failed_files_rolled_back") from None
        print(json.dumps({"status": "STAGED_NOT_ACTIVATED", **result,
                          "service_enabled_or_started": False}, sort_keys=True))
        return 0
    except (InstallError, OSError, subprocess.SubprocessError, UnicodeError) as exc:
        print(json.dumps({"status": "ERROR", "failure_code": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
