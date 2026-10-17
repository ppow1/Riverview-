# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/provision_m33_runtime_credentials.py
# Component: M33-COMMISSIONING
# Revision: 1.0.0
# Purpose: Provision or revoke one exact-scope M3.3 commissioning identity set
# Execution Model: Root-local use of the existing AuthorityRegistry only
# Observability: Redacted run marker; no bearer values or credential digests
# Dependencies: Python 3.10+; Psycopg; protected authority registry credentials
# Authority: Fixed Camrui database, principal kinds, actions, files, and bounded grant lifetime
# Changed: 2026-10-11 UTC | RV-M33-GOVERNED-COMMISSIONING | Initial exact-scope worker credential lifecycle
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_m33_commissioning.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Root-only, fixed-path M3.3 worker credential provisioning and revocation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from uuid import uuid4

from riverview_core.institutional_authority import (
    AuthorityDenied, AuthorityRegistry, IdentityConflict,
)


RELEASE = Path("/opt/riverview-m33/current")
SERVICE_DIR = Path("/etc/riverview/worker")
AUTHORITY_DIR = Path("/etc/riverview/authority")
STEWARD_FILE = AUTHORITY_DIR / "steward.token"
MANAGER_PASSFILE = AUTHORITY_DIR / "manager.pgpass"
STATE_FILE = SERVICE_DIR / "m33-commissioning.json"
WORKER_TOKEN_FILE = SERVICE_DIR / "m33-worker.credential"
VERIFIER_TOKEN_FILE = SERVICE_DIR / "m33-verifier.credential"
WORKER_ENV_FILE = Path("/etc/riverview/m33-worker.env")
VERIFIER_ENV_FILE = Path("/etc/riverview/m33-verifier.env")
MANAGER_DSN = "host=127.0.0.1 port=5432 dbname=riverview user=riverview_authority_manager"
AUTHORITY_SCHEMA = "riverview_authority"
POLICY_REF = "rv.policy:m33-live-engineering-test.v1"
GRANT_LIFETIME = timedelta(hours=8)
SERVICE_UNITS = (
    "riverview-assignment-intake.service",
    "riverview-m33-worker.service",
    "riverview-m33-verifier.service",
)


class CommissioningError(RuntimeError):
    """A fixed M3.3 provisioning precondition failed."""


def _private_regular(path: Path, *, maximum: int = 4096) -> bytes:
    if path.is_symlink():
        raise CommissioningError("protected_file_symlink")
    info = path.stat(follow_symlinks=False)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
            stat.S_IMODE(info.st_mode) != 0o600 or not 1 <= info.st_size <= maximum):
        raise CommissioningError("protected_file_metadata_invalid")
    return path.read_bytes()


def _token_file(path: Path) -> str:
    try:
        token = _private_regular(path).decode("ascii").strip()
    except (OSError, UnicodeError):
        raise CommissioningError("protected_credential_unavailable") from None
    if not 32 <= len(token) <= 512 or any(ch.isspace() for ch in token):
        raise CommissioningError("protected_credential_invalid")
    return token


def _write_secret(path: Path, token: str, *, replace: bool = False) -> None:
    if path.parent != SERVICE_DIR:
        raise CommissioningError("credential_destination_invalid")
    if path.exists() and not replace:
        raise CommissioningError("credential_destination_exists")
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        payload = (token + "\n").encode("ascii")
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, 0, 0)
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path, follow_symlinks=False)
            temporary.unlink()
        directory_fd = os.open(SERVICE_DIR, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, document: dict) -> None:
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    payload = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(temporary, 0, 0)
    os.replace(temporary, path)
    directory_fd = os.open(SERVICE_DIR, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _validate_directories() -> None:
    if not SERVICE_DIR.exists():
        SERVICE_DIR.mkdir(mode=0o700)
    for path in (AUTHORITY_DIR, SERVICE_DIR):
        info = path.stat(follow_symlinks=False)
        if (path.is_symlink() or not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or
                stat.S_IMODE(info.st_mode) != 0o700):
            raise CommissioningError("secret_directory_metadata_invalid")


def _release_commit() -> str:
    try:
        root = RELEASE.resolve(strict=True)
        info = root.stat(follow_symlinks=False)
        commit = (root / "SOURCE_COMMIT").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        raise CommissioningError("immutable_release_unavailable") from None
    if (not root.is_dir() or info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o022 or
            not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit)):
        raise CommissioningError("immutable_release_invalid")
    return commit


def _new_state(commit: str) -> dict:
    run_id = uuid4().hex
    suffix = run_id[:16]
    expiry = datetime.now(timezone.utc) + GRANT_LIFETIME
    return {
        "record_schema": "rv.m33-commissioning.v1",
        "run_id": run_id,
        "source_commit": commit,
        "scope_ref": "work-order:m33-live-" + suffix,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "valid_until": expiry.isoformat(),
        "status": "provisioning",
        "worker_principal": "worker:m33:executor:" + suffix,
        "verifier_principal": "worker:m33:verifier:" + suffix,
        "grant_ids": {
            "assignment.create": "rv-m33:" + suffix + ":assignment-create",
            "worker.register.executor": "rv-m33:" + suffix + ":executor-register",
            "assignment.execute": "rv-m33:" + suffix + ":assignment-execute",
            "worker.register.verifier": "rv-m33:" + suffix + ":verifier-register",
            "assignment.verify": "rv-m33:" + suffix + ":assignment-verify",
        },
    }


def _read_state(commit: str) -> dict:
    if STATE_FILE.is_symlink():
        raise CommissioningError("commissioning_state_symlink")
    if STATE_FILE.exists():
        try:
            state = json.loads(_private_regular(STATE_FILE, maximum=16384))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise CommissioningError("commissioning_state_invalid") from None
        if (state.get("record_schema") != "rv.m33-commissioning.v1" or
                state.get("source_commit") != commit or state.get("status") == "revoked"):
            raise CommissioningError("commissioning_state_conflict")
        return state
    for path in (WORKER_TOKEN_FILE, VERIFIER_TOKEN_FILE, WORKER_ENV_FILE, VERIFIER_ENV_FILE):
        if path.exists() or path.is_symlink():
            raise CommissioningError("partial_credential_state_requires_review")
    state = _new_state(commit)
    _atomic_json(STATE_FILE, state)
    return state


def _principal_state(registry: AuthorityRegistry, principal_id: str):
    with registry.db.transaction():
        with registry.db.cursor() as cur:
            registry._path(cur)
            cur.execute("SELECT principal_kind,status FROM institutional_principals WHERE principal_id=%s",
                        (principal_id,))
            return cur.fetchone()


def _credential_record(registry: AuthorityRegistry, principal_id: str, token: str):
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    with registry.db.transaction():
        with registry.db.cursor() as cur:
            registry._path(cur)
            cur.execute("""SELECT credential_id,expires_at,revoked_at
                           FROM principal_credentials
                           WHERE principal_id=%s AND credential_sha256=%s""",
                        (principal_id, digest))
            return cur.fetchone()


def _ensure_principal_credential(registry, steward_token, state, principal_key, token_path,
                                 expiry):
    principal_id = state[principal_key]
    row = _principal_state(registry, principal_id)
    if row is None:
        token = registry.create_principal(steward_token, principal_id, "worker")
        _write_secret(token_path, token)
    elif row["principal_kind"] != "worker" or row["status"] != "active":
        raise CommissioningError("commissioning_principal_conflict")
    if token_path.exists():
        token = _token_file(token_path)
        credential = _credential_record(registry, principal_id, token)
        if credential and credential["revoked_at"] is None and credential["expires_at"] == expiry:
            return token
        replacement = registry.issue_credential(steward_token, principal_id, expires_at=expiry)
        _write_secret(token_path, replacement, replace=True)
        if credential and credential["revoked_at"] is None:
            registry.revoke_credential(steward_token, credential["credential_id"],
                                       reason_code="m33_commissioning_rotation")
        return replacement
    token = registry.issue_credential(steward_token, principal_id, expires_at=expiry)
    _write_secret(token_path, token)
    return token


def _grant_if_absent(registry, steward_token, credential, principal_id, action, scope, grant_id, expiry):
    try:
        registry.authorize(credential, action, scope)
        return "EXISTING"
    except AuthorityDenied:
        registry.grant(steward_token, principal_id, action, scope, grant_id=grant_id,
                       policy_ref=POLICY_REF, valid_until=expiry)
        return "CREATED"


def _write_env(path: Path, worker_id: str, scope: str, commit: str) -> None:
    payload = (f"RIVERVIEW_WORKER_ID={worker_id}\n"
               f"RIVERVIEW_WORKER_SCOPE={scope}\n"
               f"RIVERVIEW_KNOWLEDGE_COMMIT={commit}\n").encode("ascii")
    if path.exists():
        if _private_regular(path, maximum=2048) != payload:
            raise CommissioningError("service_configuration_conflict")
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(path, 0, 0)


def provision() -> dict:
    if os.geteuid() != 0:
        raise CommissioningError("root_local_operation_required")
    _validate_directories()
    commit = _release_commit()
    state = _read_state(commit)
    expiry = datetime.fromisoformat(state["valid_until"])
    if expiry <= datetime.now(timezone.utc):
        raise CommissioningError("commissioning_grants_expired")
    steward_token = _token_file(STEWARD_FILE)
    os.environ["PGPASSFILE"] = str(MANAGER_PASSFILE)
    _private_regular(MANAGER_PASSFILE)
    registry = AuthorityRegistry(MANAGER_DSN, schema=AUTHORITY_SCHEMA)
    try:
        _grant_if_absent(registry, steward_token, steward_token, "steward:camrui",
                         "assignment.create", state["scope_ref"],
                         state["grant_ids"]["assignment.create"], expiry)
        executor = _ensure_principal_credential(
            registry, steward_token, state, "worker_principal", WORKER_TOKEN_FILE, expiry)
        _grant_if_absent(registry, steward_token, executor, state["worker_principal"],
                         "worker.register", state["scope_ref"],
                         state["grant_ids"]["worker.register.executor"], expiry)
        _grant_if_absent(registry, steward_token, executor, state["worker_principal"],
                         "assignment.execute", state["scope_ref"],
                         state["grant_ids"]["assignment.execute"], expiry)
        verifier = _ensure_principal_credential(
            registry, steward_token, state, "verifier_principal", VERIFIER_TOKEN_FILE, expiry)
        _grant_if_absent(registry, steward_token, verifier, state["verifier_principal"],
                         "worker.register", state["scope_ref"],
                         state["grant_ids"]["worker.register.verifier"], expiry)
        _grant_if_absent(registry, steward_token, verifier, state["verifier_principal"],
                         "assignment.verify", state["scope_ref"],
                         state["grant_ids"]["assignment.verify"], expiry)
        _write_env(WORKER_ENV_FILE, state["worker_principal"], state["scope_ref"], commit)
        _write_env(VERIFIER_ENV_FILE, state["verifier_principal"], state["scope_ref"], commit)
        state["status"] = "provisioned"
        state["provisioned_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_json(STATE_FILE, state)
        return {"status": "PROVISIONED", "run_id": state["run_id"],
                "source_commit": commit, "scope_ref": state["scope_ref"],
                "valid_until": state["valid_until"], "state_file": str(STATE_FILE)}
    finally:
        registry.close()


def revoke() -> dict:
    if os.geteuid() != 0:
        raise CommissioningError("root_local_operation_required")
    _validate_directories()
    try:
        state = json.loads(_private_regular(STATE_FILE, maximum=16384))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise CommissioningError("commissioning_state_invalid") from None
    if state.get("record_schema") != "rv.m33-commissioning.v1":
        raise CommissioningError("commissioning_state_invalid")
    for unit in SERVICE_UNITS:
        if subprocess.run(["/usr/bin/systemctl", "is-active", "--quiet", unit],
                          check=False, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            raise CommissioningError("stop_exact_m33_services_before_revocation")
    os.environ["PGPASSFILE"] = str(MANAGER_PASSFILE)
    steward_token = _token_file(STEWARD_FILE)
    _private_regular(MANAGER_PASSFILE)
    registry = AuthorityRegistry(MANAGER_DSN, schema=AUTHORITY_SCHEMA)
    try:
        # Revoke only grant IDs recorded by this exact commissioning run.
        with registry.db.transaction():
            with registry.db.cursor() as cur:
                registry._path(cur)
                cur.execute("SELECT grant_id,principal_id,action,scope_ref,revoked_at FROM authority_grants WHERE grant_id=ANY(%s)",
                            (list(state["grant_ids"].values()),))
                grants = cur.fetchall()
        expected = {
            state["grant_ids"]["assignment.create"]: ("steward:camrui", "assignment.create"),
            state["grant_ids"]["worker.register.executor"]: (state["worker_principal"], "worker.register"),
            state["grant_ids"]["assignment.execute"]: (state["worker_principal"], "assignment.execute"),
            state["grant_ids"]["worker.register.verifier"]: (state["verifier_principal"], "worker.register"),
            state["grant_ids"]["assignment.verify"]: (state["verifier_principal"], "assignment.verify"),
        }
        for grant in grants:
            if (expected.get(grant["grant_id"]) != (grant["principal_id"], grant["action"]) or
                    grant["scope_ref"] != state["scope_ref"]):
                raise CommissioningError("grant_record_mismatch")
            if grant["revoked_at"] is None:
                registry.revoke_grant(steward_token, grant["grant_id"],
                                      reason_code="m33_commissioning_complete")
        # Revoke all active credentials attached to these two run-specific worker identities.
        with registry.db.transaction():
            with registry.db.cursor() as cur:
                registry._path(cur)
                cur.execute("""SELECT c.credential_id,c.principal_id FROM principal_credentials c
                               WHERE c.principal_id=ANY(%s) AND c.revoked_at IS NULL""",
                            ([state["worker_principal"], state["verifier_principal"]],))
                credentials = cur.fetchall()
        for credential in credentials:
            registry.revoke_credential(steward_token, credential["credential_id"],
                                       reason_code="m33_commissioning_complete")
        for path in (WORKER_TOKEN_FILE, VERIFIER_TOKEN_FILE, WORKER_ENV_FILE, VERIFIER_ENV_FILE):
            if path.exists() or path.is_symlink():
                if path.is_symlink():
                    raise CommissioningError("service_file_symlink")
                path.unlink()
        state["status"] = "revoked"
        state["revoked_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_json(STATE_FILE, state)
        return {"status": "REVOKED", "run_id": state["run_id"],
                "scope_ref": state["scope_ref"], "state_file": str(STATE_FILE)}
    finally:
        registry.close()


def main() -> int:
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] != "--revoke"):
        print(json.dumps({"status": "ERROR", "failure_code": "arguments_not_allowed"}))
        return 2
    try:
        result = revoke() if len(sys.argv) == 2 else provision()
        print(json.dumps(result, sort_keys=True))
        return 0
    except (CommissioningError, AuthorityDenied, IdentityConflict, OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "failure_code": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
