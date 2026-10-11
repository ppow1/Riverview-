# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/service.py
# Component: WORKER-ADAPTER
# Revision: 1.0.0
# Purpose: Validate systemd worker credentials and idempotent registry state
# Execution Model: Shared startup preflight for supervised executor/verifier units
# Observability: Safe identity/configuration errors without bearer disclosure
# Dependencies: Python 3.10+; Psycopg; systemd credentials
# Authority: Service identity and exact scope remain Steward-grant controlled
# Changed: 2026-10-11 UTC | RV-M3.3-WORKER-SERVICE | Initial systemd service preflight
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_service.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Safe systemd credential and registry setup shared by worker processes."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import pwd
import stat
import sys

from .adapter import PostgresWorkerAdapter, WorkerAdapterError


class WorkerServiceConfigurationError(RuntimeError):
    """A required service identity, credential or pin does not match policy."""


def _read_systemd_credential(name: str, service_unit: str) -> bytes:
    if name not in {"pgpass", "worker-token", "verifier-token"}:
        raise WorkerServiceConfigurationError("credential_name_invalid")
    if service_unit not in {"riverview-m33-worker.service", "riverview-m33-verifier.service"}:
        raise WorkerServiceConfigurationError("credential_unit_invalid")
    expected = Path("/run/credentials") / service_unit
    configured = os.environ.get("CREDENTIALS_DIRECTORY")
    path = expected / name
    try:
        if configured is None or Path(configured) != expected:
            raise WorkerServiceConfigurationError("credential_directory_mismatch")
        if expected.resolve() != expected.absolute() or path.resolve() != path.absolute():
            raise WorkerServiceConfigurationError("credential_symlink_rejected")
        directory = expected.lstat()
        info = path.lstat()
        if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != 0 or
                stat.S_IMODE(directory.st_mode) != 0o550):
            raise WorkerServiceConfigurationError("credential_directory_invalid")
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
                stat.S_IMODE(info.st_mode) != 0o440 or not 1 <= info.st_size <= 4096):
            raise WorkerServiceConfigurationError("credential_file_invalid")
        if not os.access(path, os.R_OK, effective_ids=True):
            raise WorkerServiceConfigurationError("credential_unreadable")
        return path.read_bytes()
    except OSError:
        raise WorkerServiceConfigurationError("credential_unavailable") from None


def prepare_database_credential(service_unit: str) -> str:
    if any(os.environ.get(name) for name in
           ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
        raise WorkerServiceConfigurationError("ambient_database_override")
    source_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if not source_dir:
        raise WorkerServiceConfigurationError("credential_directory_missing")
    source = Path(source_dir) / "pgpass"
    data = _read_systemd_credential("pgpass", service_unit)
    if not data.endswith(b"\n") or b"\n" in data[:-1] or b"\x00" in data:
        raise WorkerServiceConfigurationError("database_credential_format_invalid")
    identity = pwd.getpwnam("riverview")
    if identity.pw_uid == 0 or os.geteuid() != identity.pw_uid:
        raise WorkerServiceConfigurationError("runtime_identity_mismatch")
    runtime = Path("/run") / service_unit.removesuffix(".service")
    destination = runtime / "pgpass"
    scripts_path = str(Path(__file__).resolve().parents[3] / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    from runtime_baseline import copy_systemd_credential, systemd_credential_path
    systemd_credential_path(source, service_unit=service_unit)
    copy_systemd_credential(source, destination, identity.pw_uid)
    os.environ["PGPASSFILE"] = str(destination)
    return str(destination)


def read_worker_credential(service_unit: str, credential_name: str) -> str:
    try:
        raw = _read_systemd_credential(credential_name, service_unit)
        token = raw.decode("ascii")
    except UnicodeDecodeError:
        raise WorkerServiceConfigurationError("worker_credential_format_invalid") from None
    if not 32 <= len(token) <= 512 or any(character.isspace() for character in token):
        raise WorkerServiceConfigurationError("worker_credential_format_invalid")
    return token


def ensure_registered(adapter: PostgresWorkerAdapter, worker_id: str, token: str,
                      capabilities: tuple[str, ...], scope_ref: str) -> None:
    if not worker_id or not scope_ref or not capabilities:
        raise WorkerServiceConfigurationError("worker_configuration_invalid")
    candidate = hashlib.sha256(token.encode("utf-8")).digest()
    with adapter.ledger.db.transaction():
        with adapter.ledger.db.cursor() as cur:
            adapter.ledger._set_search_path(cur)
            cur.execute("SELECT credential_sha256,capabilities,scope_ref,active FROM worker_registry WHERE worker_id=%s FOR SHARE",
                        (worker_id,))
            row = cur.fetchone()
    if row is None:
        adapter.register_worker(worker_id, capabilities, scope_ref, credential=token)
        return
    if (not row["active"] or row["scope_ref"] != scope_ref or
            sorted(row["capabilities"]) != sorted(capabilities) or
            not hmac.compare_digest(bytes(row["credential_sha256"]), candidate)):
        raise WorkerServiceConfigurationError("registered_worker_mismatch")


def load_runtime_config(service_unit: str, credential_name: str):
    from psycopg.conninfo import conninfo_to_dict
    dsn = os.environ.get("RIVERVIEW_PG_DSN", "")
    if not dsn or "password" in conninfo_to_dict(dsn):
        raise WorkerServiceConfigurationError("database_dsn_invalid")
    schema = os.environ.get("RIVERVIEW_PG_SCHEMA", "riverview_dev")
    authority_schema = os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority")
    worker_id = os.environ.get("RIVERVIEW_WORKER_ID", "")
    scope_ref = os.environ.get("RIVERVIEW_WORKER_SCOPE", "")
    token = read_worker_credential(service_unit, credential_name)
    prepare_database_credential(service_unit)
    return dsn, schema, authority_schema, worker_id, scope_ref, token
