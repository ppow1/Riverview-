# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/provision_grace_resident.py
# Component: GRACE-OPERATIONAL-INTEGRATION
# Revision: 1.0.1
# Purpose: Additively provision Grace's stable office, resident, occupant and local-model binding
# Execution Model: Root-local, idempotent authority-registry bootstrap
# Observability: Redacted status JSON; bearer values and credential hashes are never emitted
# Dependencies: PostgreSQL authority manager passfile; protected Steward credential; registered model metadata
# Authority: Fixed identities and exact office.state.write scope; no assignment or tool permission
# Changed: 2026-10-11 UTC | RV-M4.4-IDENTITY-BOOTSTRAP | Initial root-local Grace identity provisioner
# Changed: 2026-10-11 UTC | RV-M4.4-IDENTITY-BOOTSTRAP-REVIEW | Bound model hashing and rerun recovery; preserve provisioned state identity
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md; docs/components/RESIDENT_REASONING.md
# Tests: tests/test_grace_provisioning.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Safely create the stable Grace office and its first resident binding."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import uuid

from riverview_core.institutional_authority import (
    AuthorityDenied, AuthorityRegistry, IdentityConflict, RegistryUnavailable,
)

AUTHORITY_DIR = Path("/etc/riverview/authority")
GRACE_DIR = Path("/etc/riverview/grace")
STEWARD_FILE = AUTHORITY_DIR / "steward.token"
MANAGER_PASSFILE = AUTHORITY_DIR / "manager.pgpass"
RESIDENT_TOKEN_FILE = GRACE_DIR / "resident.credential"
STATE_FILE = GRACE_DIR / "provisioning.json"
MODEL_FILE = Path("/home/admin1/.cache/riverview/models/Qwen3-0.6B-Q8_0.gguf")
MANAGER_DSN = "host=127.0.0.1 port=5432 dbname=riverview user=riverview_authority_manager"
AUTHORITY_SCHEMA = "riverview_authority"
OFFICE_ID = "office:grace"
OFFICE_ROLE = "AI director of engineering"
PRINCIPAL_ID = "resident:grace"
OCCUPANT_ID = "occupant:grace:initial"
IMPLEMENTATION_ID = "implementation:grace:qwen3-0.6b-q8"
PROVIDER_REF = "local.inference.v1"
STATE_ACTION = "office.state.write"
STATE_SCOPE = "office:" + OFFICE_ID
GRANT_ID = "rv-grace:office-state-write:v1"
POLICY_REF = "rv.policy:grace-office-runtime-state.v1"


class ProvisioningError(RuntimeError):
    """A fixed Grace bootstrap precondition failed."""


def _private_regular(path: Path, *, maximum: int = 4096) -> bytes:
    if path.is_symlink():
        raise ProvisioningError("protected_file_symlink")
    info = path.stat(follow_symlinks=False)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o600 or not 1 <= info.st_size <= maximum):
        raise ProvisioningError("protected_file_metadata_invalid")
    return path.read_bytes()


def _ensure_directory(path: Path) -> None:
    if path.exists():
        info = path.stat(follow_symlinks=False)
        if (path.is_symlink() or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700):
            raise ProvisioningError("protected_directory_metadata_invalid")
        return
    path.mkdir(mode=0o700, parents=False)
    os.chown(path, 0, 0)
    os.chmod(path, 0o700)


def _write_secret(path: Path, value: str) -> None:
    if path != RESIDENT_TOKEN_FILE or path.parent != GRACE_DIR:
        raise ProvisioningError("credential_destination_invalid")
    raw = (value + "\n").encode("ascii")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        existing = _private_regular(path)
        if existing.decode("ascii").rstrip("\n") != value:
            raise ProvisioningError("credential_file_conflict") from None
        return
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(path, 0, 0)
        os.chmod(path, 0o600)
        directory_fd = os.open(GRACE_DIR, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _rows(registry, query, parameters):
    with registry.db.transaction():
        with registry.db.cursor() as cur:
            registry._path(cur)
            cur.execute(query, parameters)
            return cur.fetchall()


def _one(registry, query, parameters):
    rows = _rows(registry, query, parameters)
    return rows[0] if rows else None


def _ensure_office(registry, steward: str) -> None:
    row = _one(registry, "SELECT office_role FROM institutional_offices WHERE office_id=%s",
               (OFFICE_ID,))
    if row:
        if row["office_role"] != OFFICE_ROLE:
            raise ProvisioningError("office_identity_conflict")
        return
    registry.create_office(steward, OFFICE_ID, OFFICE_ROLE)


def _ensure_implementation(registry, steward: str, model_sha256: str) -> None:
    row = _one(registry, """SELECT kind,provider_ref,revision FROM resident_implementations
                            WHERE implementation_id=%s""", (IMPLEMENTATION_ID,))
    if row:
        if (row["kind"] != "model" or row["provider_ref"] != PROVIDER_REF
                or row["revision"] != model_sha256):
            raise ProvisioningError("implementation_identity_conflict")
        return
    registry.create_implementation(
        steward, IMPLEMENTATION_ID, kind="model",
        provider_ref=PROVIDER_REF, revision=model_sha256)


def _ensure_principal(registry, steward: str) -> str:
    row = _one(registry, """SELECT principal_kind,office_id,status FROM institutional_principals
                            WHERE principal_id=%s""", (PRINCIPAL_ID,))
    if row:
        if (row["principal_kind"] != "resident" or row["office_id"] != OFFICE_ID
                or row["status"] != "active"):
            raise ProvisioningError("resident_identity_conflict")
        if RESIDENT_TOKEN_FILE.exists() or RESIDENT_TOKEN_FILE.is_symlink():
            try:
                token = _private_regular(RESIDENT_TOKEN_FILE).decode("ascii").strip()
            except (OSError, UnicodeError):
                raise ProvisioningError("resident_credential_invalid") from None
            if not 32 <= len(token) <= 512 or any(ch.isspace() for ch in token):
                raise ProvisioningError("resident_credential_invalid")
            return token
        # Recovery path for a power loss after DB credential issuance but before
        # a protected token file became durable; issue and persist a fresh bearer.
        token = registry.issue_credential(steward, PRINCIPAL_ID)
        _write_secret(RESIDENT_TOKEN_FILE, token)
        return token
    token = registry.create_principal(steward, PRINCIPAL_ID, "resident", office_id=OFFICE_ID)
    _write_secret(RESIDENT_TOKEN_FILE, token)
    return token


def _ensure_occupant(registry, steward: str) -> None:
    row = _one(registry, "SELECT principal_id,retired_at FROM resident_occupants WHERE occupant_id=%s",
               (OCCUPANT_ID,))
    if row:
        if row["principal_id"] != PRINCIPAL_ID or row["retired_at"] is not None:
            raise ProvisioningError("occupant_identity_conflict")
        return
    registry.create_occupant(steward, OCCUPANT_ID, principal_id=PRINCIPAL_ID)


def _ensure_binding(registry, steward: str) -> None:
    snapshot = registry.office_snapshot(OFFICE_ID)
    if snapshot.get("occupant_id") or snapshot.get("implementation_id"):
        if (snapshot.get("occupant_id") != OCCUPANT_ID
                or snapshot.get("implementation_id") != IMPLEMENTATION_ID):
            raise ProvisioningError("office_binding_conflict")
        return
    registry.bind_office(steward, OFFICE_ID, OCCUPANT_ID, IMPLEMENTATION_ID)


def _ensure_state_grant(registry, steward: str, resident_token: str) -> None:
    try:
        grant = registry.authorize(resident_token, STATE_ACTION, STATE_SCOPE)
        if grant["principal_id"] != PRINCIPAL_ID:
            raise ProvisioningError("office_state_grant_principal_mismatch")
        return
    except AuthorityDenied:
        pass
    existing = _one(registry, """SELECT principal_id,action,scope_ref,revoked_at
                                FROM authority_grants WHERE grant_id=%s""", (GRANT_ID,))
    if existing:
        if (existing["principal_id"] != PRINCIPAL_ID or existing["action"] != STATE_ACTION
                or existing["scope_ref"] != STATE_SCOPE or existing["revoked_at"] is not None):
            raise ProvisioningError("office_state_grant_conflict")
        raise ProvisioningError("office_state_authorization_unavailable")
    registry.grant(steward, PRINCIPAL_ID, STATE_ACTION, STATE_SCOPE,
                   grant_id=GRANT_ID, policy_ref=POLICY_REF)


def _write_state(model_sha256: str) -> None:
    document = {
        "record_schema": "rv.grace-resident-provisioning.v1",
        "status": "IDENTITY_BOUND",
        "office_id": OFFICE_ID,
        "principal_id": PRINCIPAL_ID,
        "occupant_id": OCCUPANT_ID,
        "implementation_id": IMPLEMENTATION_ID,
        "provider_ref": PROVIDER_REF,
        "model_sha256": model_sha256,
        "state_grant_id": GRANT_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    payload = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode()
    temporary = STATE_FILE.with_name(STATE_FILE.name + "." + uuid.uuid4().hex + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, 0, 0)
        os.replace(temporary, STATE_FILE)
        directory_fd = os.open(GRACE_DIR, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def provision() -> dict:
    if os.geteuid() != 0:
        raise ProvisioningError("root_local_operation_required")
    _ensure_directory(GRACE_DIR)
    try:
        steward = _private_regular(STEWARD_FILE, maximum=512).decode("ascii").strip()
        _private_regular(MANAGER_PASSFILE, maximum=4096)
    except (OSError, UnicodeError):
        raise ProvisioningError("protected_authority_credential_unavailable") from None
    if not 32 <= len(steward) <= 512 or any(ch.isspace() for ch in steward):
        raise ProvisioningError("steward_credential_invalid")
    try:
        model_info = MODEL_FILE.stat(follow_symlinks=False)
        if not stat.S_ISREG(model_info.st_mode) or model_info.st_size < 1:
            raise ProvisioningError("model_file_unavailable")
        digest = hashlib.sha256()
        with MODEL_FILE.open("rb") as model:
            for block in iter(lambda: model.read(1024 * 1024), b""):
                digest.update(block)
        model_sha256 = digest.hexdigest()
    except OSError:
        raise ProvisioningError("model_file_unavailable") from None

    os.environ["PGPASSFILE"] = str(MANAGER_PASSFILE)
    registry = AuthorityRegistry(MANAGER_DSN, schema=AUTHORITY_SCHEMA)
    try:
        registry.authorize(steward, "office.manage", "institution")
        registry.authorize(steward, "identity.manage", "institution")
        registry.authorize(steward, "authority.grant", "institution")
        _ensure_office(registry, steward)
        _ensure_implementation(registry, steward, model_sha256)
        resident_token = _ensure_principal(registry, steward)
        _ensure_occupant(registry, steward)
        _ensure_binding(registry, steward)
        _ensure_state_grant(registry, steward, resident_token)
        snapshot = registry.office_snapshot(OFFICE_ID)
        if (snapshot.get("occupant_id") != OCCUPANT_ID
                or snapshot.get("implementation_id") != IMPLEMENTATION_ID):
            raise ProvisioningError("office_binding_verification_failed")
        registry.authorize(resident_token, STATE_ACTION, STATE_SCOPE)
        if STATE_FILE.exists() or STATE_FILE.is_symlink():
            previous = json.loads(_private_regular(STATE_FILE, maximum=16384))
            if (previous.get("record_schema") != "rv.grace-resident-provisioning.v1"
                    or previous.get("office_id") != OFFICE_ID):
                raise ProvisioningError("provisioning_record_conflict")
            _write_state(model_sha256)
            status = "ALREADY_PROVISIONED"
        else:
            _write_state(model_sha256)
            status = "PROVISIONED"
        return {"status": status, "office_id": OFFICE_ID,
                "principal_id": PRINCIPAL_ID, "occupant_id": OCCUPANT_ID,
                "implementation_id": IMPLEMENTATION_ID,
                "provider_ref": PROVIDER_REF, "model_sha256": model_sha256,
                "office_state_grant": STATE_ACTION + ":" + STATE_SCOPE}
    finally:
        registry.close()


def main() -> int:
    if len(sys.argv) != 1:
        print(json.dumps({"status": "ERROR", "failure_code": "arguments_not_allowed"}))
        return 2
    try:
        print(json.dumps(provision(), sort_keys=True))
        return 0
    except (ProvisioningError, AuthorityDenied, IdentityConflict, RegistryUnavailable,
            OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"status": "ERROR", "failure_code": str(exc)}, sort_keys=True))
        return 1
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "failure_code": type(exc).__name__}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# Revision history
# - 1.0.0: Initial fixed-scope root-local Grace identity provisioner.
# - 1.0.1: Stream model hashing, preserve immutable provisioning marker on rerun, and handle interrupted credential delivery safely.
