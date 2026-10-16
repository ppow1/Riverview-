#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/retire_revoked_m33_worker_registrations.py
# Component: WORKER-ADAPTER / INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Retire the two registrations belonging to one revoked M33 run
# Execution Model: Root-local explicit operation; no application startup side effects
# Observability: Redacted JSON result and append-only authority events
# Dependencies: PostgreSQL riverview; protected M33 state, Steward token, manager passfile; systemd
# Authority: Fixed run and IDs; active Steward identity.manage; stopped services; revoked authority; no executable work
# Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Initial guarded M33 registration retirement
# Contracts: docs/components/WORKER_ADAPTER_COOKBOOK.md; docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# Tests: tests/test_worker_registration_retirement.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Root-local guarded retirement of the exact revoked M33 worker registrations."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

from riverview_core.institutional_authority import AuthorityRegistry
from riverview_core.worker_adapter.retirement import (
    RUN_ID, SCOPE, WORKER_IDS, WorkerRetirementError,
    retire_revoked_m33_registrations,
)

AUTHORITY_DIR = Path("/etc/riverview/authority")
WORKER_DIR = Path("/etc/riverview/worker")
STEWARD_FILE = AUTHORITY_DIR / "steward.token"
MANAGER_PASSFILE = AUTHORITY_DIR / "manager.pgpass"
STATE_FILE = WORKER_DIR / "m33-commissioning.json"
MANAGER_DSN = "host=127.0.0.1 port=5432 dbname=riverview user=riverview_authority_manager"
AUTHORITY_SCHEMA = "riverview_authority"


class RetirementCommandError(RuntimeError):
    """A protected local precondition failed."""


def _private_regular(path: Path, maximum: int = 4096) -> bytes:
    try:
        info = path.stat(follow_symlinks=False)
    except OSError:
        raise RetirementCommandError("protected_file_unavailable") from None
    if (path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
            stat.S_IMODE(info.st_mode) != 0o600 or not 1 <= info.st_size <= maximum):
        raise RetirementCommandError("protected_file_metadata_invalid")
    return path.read_bytes()


def _state_preflight() -> None:
    try:
        state = json.loads(_private_regular(STATE_FILE).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise RetirementCommandError("commissioning_state_invalid") from None
    if (state.get("record_schema") != "rv.m33-commissioning.v1" or
            state.get("run_id") != RUN_ID or state.get("scope_ref") != SCOPE or
            state.get("status") != "revoked" or
            state.get("worker_principal") != WORKER_IDS[0] or
            state.get("verifier_principal") != WORKER_IDS[1]):
        raise RetirementCommandError("commissioning_run_not_exactly_revoked")


def execute() -> dict:
    if os.geteuid() != 0:
        raise RetirementCommandError("root_local_operation_required")
    _state_preflight()
    steward_token = _private_regular(STEWARD_FILE).decode("ascii").strip()
    if not 32 <= len(steward_token) <= 512 or any(ch.isspace() for ch in steward_token):
        raise RetirementCommandError("steward_credential_invalid")
    _private_regular(MANAGER_PASSFILE)
    os.environ["PGPASSFILE"] = str(MANAGER_PASSFILE)
    registry = AuthorityRegistry(MANAGER_DSN, schema=AUTHORITY_SCHEMA)
    try:
        return retire_revoked_m33_registrations(registry, steward_token)
    finally:
        registry.close()


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "--apply":
        print(json.dumps({"status": "ERROR", "failure_code": "explicit_apply_required"}))
        return 2
    try:
        result = execute()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        code = str(exc) if isinstance(exc, (RetirementCommandError, WorkerRetirementError)) else type(exc).__name__
        print(json.dumps({"status": "ERROR", "failure_code": code}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
