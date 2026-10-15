# =============================================================================
# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/provision_grace_engineering_demo.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Provision only the standing exact-scope authority and credentials for Grace's bounded Engineering demo
# Execution Model: Root-local, explicit apply; AuthorityRegistry API for all mutations
# Observability: Redacted JSON result with identities, grant actions/scopes, and outcome codes
# Dependencies: PostgreSQL AuthorityRegistry; protected Steward token and manager passfile
# Authority: Fixed identities/actions/scopes; no arbitrary arguments, expiry changes, or service activation
# Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PROVISIONER-001 | Initial bounded idempotent provisioning procedure
# Contracts: docs/components/GRACE_ENGINEERING_DEMO_COMMISSIONING.md; docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_grace_engineering_demo_provisioning.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Root-local provisioner for the explicitly authorized Grace Engineering demo."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys
from uuid import uuid4

from riverview_core.institutional_authority import (
    AuthorityDenied, AuthorityRegistry, IdentityConflict,
)


AUTHORITY_DIR = Path("/etc/riverview/authority")
WORKER_DIR = Path("/etc/riverview/worker")
GRACE_DIR = Path("/etc/riverview/grace")
STEWARD_FILE = AUTHORITY_DIR / "steward.token"
MANAGER_PASSFILE = AUTHORITY_DIR / "manager.pgpass"
RESIDENT_FILE = GRACE_DIR / "resident.credential"
STATE_FILE = WORKER_DIR / "grace-engineering-demo.json"
DISPATCH_ID = "service:grace-engineering-dispatch"
EXECUTOR_ID = "worker:grace-engineering"
VERIFIER_ID = "verifier:grace-engineering"
SCOPE = "work-order:engineering"
POLICY_REF = "rv.policy:grace-engineering-demo-standing.v1"
MANAGER_DSN = "host=127.0.0.1 port=5432 dbname=riverview user=riverview_authority_manager"
AUTHORITY_SCHEMA = "riverview_authority"
IDENTITIES = (
    (DISPATCH_ID, "service", WORKER_DIR / "grace-dispatch.credential"),
    (EXECUTOR_ID, "worker", WORKER_DIR / "grace-executor.credential"),
    (VERIFIER_ID, "worker", WORKER_DIR / "grace-verifier.credential"),
)
GRANTS = (
    ("steward:camrui", "objective.submit", SCOPE, "grace-demo:steward-objective-submit"),
    ("resident:grace", "resident.conversation.send", "office:office:grace",
     "grace-demo:resident-conversation-send"),
    (DISPATCH_ID, "assignment.create", SCOPE, "grace-demo:dispatch-assignment-create"),
    (EXECUTOR_ID, "worker.register", SCOPE, "grace-demo:executor-worker-register"),
    (EXECUTOR_ID, "assignment.execute", SCOPE, "grace-demo:executor-assignment-execute"),
    (VERIFIER_ID, "worker.register", SCOPE, "grace-demo:verifier-worker-register"),
    (VERIFIER_ID, "assignment.verify", SCOPE, "grace-demo:verifier-assignment-verify"),
)


class ProvisioningError(RuntimeError):
    """A fixed precondition or existing-record conflict prevents safe provisioning."""


def _private_file(path: Path, *, max_bytes: int = 4096) -> bytes:
    if path.is_symlink():
        raise ProvisioningError("protected_file_symlink")
    try:
        info = path.stat(follow_symlinks=False)
    except OSError:
        raise ProvisioningError("protected_file_unavailable") from None
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
            stat.S_IMODE(info.st_mode) != 0o600 or not 1 <= info.st_size <= max_bytes):
        raise ProvisioningError("protected_file_metadata_invalid")
    return path.read_bytes()


def _read_token(path: Path) -> str:
    try:
        token = _private_file(path).decode("ascii").strip()
    except (OSError, UnicodeError):
        raise ProvisioningError("protected_credential_invalid") from None
    if not 32 <= len(token) <= 512 or any(ch.isspace() for ch in token):
        raise ProvisioningError("protected_credential_invalid")
    return token


def _write_token(path: Path, token: str) -> None:
    if path.parent != WORKER_DIR or path.exists() or path.is_symlink():
        raise ProvisioningError("credential_destination_conflict")
    tmp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write((token + "\n").encode("ascii"))
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(tmp, 0, 0)
        os.link(tmp, path, follow_symlinks=False)
        tmp.unlink()
        dir_fd = os.open(WORKER_DIR, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        tmp.unlink(missing_ok=True)


def _record_for_credential(registry, principal_id: str, token: str):
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    with registry.db.transaction():
        with registry.db.cursor() as cur:
            registry._path(cur)
            cur.execute("""SELECT credential_id, revoked_at, expires_at
                           FROM principal_credentials
                           WHERE principal_id=%s AND credential_sha256=%s""",
                        (principal_id, digest))
            return cur.fetchone()


def _principal(registry, principal_id: str):
    with registry.db.transaction():
        with registry.db.cursor() as cur:
            registry._path(cur)
            cur.execute("SELECT principal_kind,status FROM institutional_principals WHERE principal_id=%s",
                        (principal_id,))
            return cur.fetchone()


def _ensure_token(registry, steward_token: str, principal_id: str,
                  kind: str, path: Path) -> str:
    row = _principal(registry, principal_id)
    if row is None:
        token = registry.create_principal(steward_token, principal_id, kind)
        _write_token(path, token)
        return token
    if row["principal_kind"] != kind or row["status"] != "active":
        raise ProvisioningError("principal_identity_conflict")
    if path.is_symlink():
        raise ProvisioningError("credential_file_symlink")
    if path.exists():
        token = _read_token(path)
        record = _record_for_credential(registry, principal_id, token)
        if record and record["revoked_at"] is None and (
                record["expires_at"] is None or record["expires_at"] > datetime.now(timezone.utc)):
            return token
        raise ProvisioningError("existing_credential_not_active_requires_review")
    token = registry.issue_credential(steward_token, principal_id)
    _write_token(path, token)
    return token


def _ensure_grant(registry, steward_token: str, credential: str,
                  principal_id: str, action: str, scope: str, grant_id: str) -> str:
    try:
        registry.authorize(credential, action, scope)
        return "EXISTING"
    except AuthorityDenied:
        pass
    with registry.db.transaction():
        with registry.db.cursor() as cur:
            registry._path(cur)
            cur.execute("""SELECT principal_id,action,scope_ref,revoked_at,valid_from,valid_until
                           FROM authority_grants WHERE grant_id=%s""",
                        (grant_id,))
            existing = cur.fetchone()
    if existing:
        if (existing["principal_id"], existing["action"], existing["scope_ref"]) != (
                principal_id, action, scope):
            raise ProvisioningError("grant_id_collision")
        if existing["revoked_at"] is not None:
            raise ProvisioningError("previously_revoked_grant_requires_steward_review")
        now = datetime.now(timezone.utc)
        if existing["valid_from"] > now or (existing["valid_until"] is not None and
                                               existing["valid_until"] <= now):
            raise ProvisioningError("existing_grant_not_current_requires_steward_review")
        return "EXISTING"
    registry.grant(steward_token, principal_id, action, scope,
                   grant_id=grant_id, policy_ref=POLICY_REF)
    registry.authorize(credential, action, scope)
    return "CREATED"


def _validate_directories() -> None:
    for path in (AUTHORITY_DIR, WORKER_DIR, GRACE_DIR):
        if path.is_symlink():
            raise ProvisioningError("credential_directory_symlink")
        info = path.stat(follow_symlinks=False)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or
                stat.S_IMODE(info.st_mode) != 0o700):
            raise ProvisioningError("credential_directory_metadata_invalid")


def provision() -> dict:
    if os.geteuid() != 0:
        raise ProvisioningError("root_local_operation_required")
    _validate_directories()
    _private_file(MANAGER_PASSFILE)
    steward_token = _read_token(STEWARD_FILE)
    resident_token = _read_token(RESIDENT_FILE)
    os.environ["PGPASSFILE"] = str(MANAGER_PASSFILE)
    registry = AuthorityRegistry(MANAGER_DSN, schema=AUTHORITY_SCHEMA)
    try:
        registry.authorize(steward_token, "authority.grant", "institution")
        registry.authorize(steward_token, "identity.manage", "institution")
        resident = registry.authorize_office_state(resident_token, "office:grace")
        if resident.get("occupant_id") != "occupant:grace:initial":
            raise ProvisioningError("grace_occupant_changed")
        tokens = {"steward:camrui": steward_token, "resident:grace": resident_token}
        for principal_id, kind, path in IDENTITIES:
            tokens[principal_id] = _ensure_token(registry, steward_token,
                                                 principal_id, kind, path)
        outcomes = []
        for principal_id, action, scope, grant_id in GRANTS:
            outcomes.append({"principal_id": principal_id, "action": action,
                "scope_ref": scope,
                "result": _ensure_grant(registry, steward_token, tokens[principal_id],
                    principal_id, action, scope, grant_id)})
        # Write only non-secret identity and grant metadata after all API calls succeed.
        document = {"record_schema": "rv.grace-engineering-demo-provisioning.v1",
            "policy_ref": POLICY_REF, "scope_ref": SCOPE,
            "identities": [item[0] for item in IDENTITIES],
            "grant_ids": [item[3] for item in GRANTS],
            "credentials_copied": False, "service_activated": False}
        payload = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode()
        if STATE_FILE.exists() or STATE_FILE.is_symlink():
            current = _private_file(STATE_FILE, max_bytes=32768)
            if json.loads(current) != document:
                raise ProvisioningError("provisioning_state_conflict")
        else:
            fd = os.open(STATE_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chown(STATE_FILE, 0, 0)
        return {"status": "READY", "scope_ref": SCOPE,
            "grants": outcomes, "service_activated": False,
            "credential_material_reported": False}
    finally:
        registry.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply the fixed grant/credential plan")
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps({"status": "NO_CHANGE", "required_flag": "--apply",
                          "scope_ref": SCOPE, "grant_count": len(GRANTS)}, sort_keys=True))
        return 0
    try:
        print(json.dumps(provision(), sort_keys=True))
        return 0
    except (ProvisioningError, AuthorityDenied, IdentityConflict, OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "failure_code": str(exc)}, sort_keys=True))
        return 1
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "failure_code": type(exc).__name__}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
