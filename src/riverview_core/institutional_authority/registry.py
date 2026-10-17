# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/registry.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.13
# Purpose: Persist separated offices, occupants, implementations and scoped grants
# Execution Model: Synchronous transactional PostgreSQL registry
# Observability: Append-only authority events and office binding revisions
# Dependencies: Python 3.10+; Psycopg 3; institutional_authority migration
# Authority: Exact active credential, principal, action and scope are required
# Changed: 2026-10-11 UTC | RV-M4.1-001 | Validate expiry timestamps and object-shaped office state
# Changed: 2026-10-11 UTC | RV-M4.1-BOOTSTRAP-WRITE-AHEAD | Allow trusted root caller to persist random token before bootstrap transaction
# Changed: 2026-10-11 UTC | RV-M4.1-BOUND-OCCUPANT-WRITE | Require the exact office-state writer to be the currently bound resident
# Changed: 2026-10-11 UTC | RV-M4.1-RUNTIME-OFFICE-API | Route restricted runtime office reads/writes through exact-grant database functions
# Changed: 2026-10-13 UTC | RV-GRACE-MULTISTAGE-ROUTING-001 | Add expected-revision audited implementation-only office rebind
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Verify only the current audited predecessor-to-successor binding transition
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Add Steward-only compare-and-swap office-role correction with durable audit event
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_institutional_authority.py
# History: .riverview-backups/manifest.jsonl and Git
"""Minimal persistent registry for institutional identities and grants.

The first Steward credential is created only by the trusted local provisioning
operation. All later identity, office-binding, and grant changes require an
active credential with the exact management action and scope.
"""

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row


class RegistryUnavailable(RuntimeError):
    """The registry cannot provide an authoritative answer."""


class AuthorityDenied(RuntimeError):
    """No active credential and exact action/scope grant authorize the request."""


class IdentityConflict(RuntimeError):
    """A durable identity or binding conflicts with existing state."""


class AuthorityRegistry:
    """Store identity separately from office role, occupant and implementation."""

    SCHEMA_VERSION = "0001_institutional_authority"
    MAX_STATE_BYTES = 65536
    BOOTSTRAP_GRANTS = (
        ("authority.grant", "institution"),
        ("identity.manage", "institution"),
        ("office.manage", "institution"),
    )

    def __init__(self, dsn, *, schema="public", runtime_safe=False):
        if not schema or not schema[0].isalpha() or not schema.replace("_", "").isalnum():
            raise ValueError("invalid schema")
        self.schema = schema
        self.runtime_safe = bool(runtime_safe)
        try:
            self.db = psycopg.connect(dsn, row_factory=dict_row, autocommit=True)
            if not self.runtime_safe:
                with self.db.cursor() as cur:
                    cur.execute("SELECT to_regclass(%s) AS registry",
                                (f"{schema}.institutional_principals",))
                    if cur.fetchone()["registry"] is None:
                        raise RegistryUnavailable("institutional authority migration is not applied")
        except Exception as exc:
            if hasattr(self, "db"):
                self.db.close()
            if isinstance(exc, RegistryUnavailable):
                raise
            raise RegistryUnavailable(type(exc).__name__) from None

    def close(self):
        self.db.close()

    def _path(self, cur):
        cur.execute("SELECT set_config('search_path', %s, false)", (self.schema,))

    @staticmethod
    def _digest(token):
        if not isinstance(token, str) or len(token) < 32:
            raise AuthorityDenied("invalid credential")
        return hashlib.sha256(token.encode("utf-8")).digest()

    @staticmethod
    def _validate_expiry(expires_at):
        if expires_at is not None and (
                not isinstance(expires_at, datetime) or expires_at.tzinfo is None or
                expires_at <= datetime.now(timezone.utc)):
            raise ValueError("expiry must be a future timezone-aware datetime")

    @staticmethod
    def _event(cur, *, event_type, actor_id, subject_id=None, grant_id=None,
               office_id=None, payload=None):
        cur.execute(
            """INSERT INTO institutional_authority_events
               (event_id,event_type,actor_id,subject_id,grant_id,office_id,payload)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (uuid4(), event_type, actor_id, subject_id, grant_id, office_id,
             json.dumps(payload or {}, sort_keys=True)))

    def _authenticate(self, cur, token):
        digest = self._digest(token)
        cur.execute(
            """SELECT p.principal_id,p.principal_kind,p.status
               FROM principal_credentials c
               JOIN institutional_principals p USING (principal_id)
               WHERE c.credential_sha256=%s AND c.revoked_at IS NULL
                 AND (c.expires_at IS NULL OR c.expires_at>clock_timestamp())
               FOR SHARE OF c,p""", (digest,))
        principal = cur.fetchone()
        if principal is None or principal["status"] != "active":
            raise AuthorityDenied("credential is unknown, expired, or revoked")
        return principal

    def _require(self, cur, token, action, scope_ref):
        principal = self._authenticate(cur, token)
        cur.execute(
            """SELECT grant_id FROM authority_grants
               WHERE principal_id=%s AND action=%s AND scope_ref=%s
                 AND revoked_at IS NULL AND valid_from<=clock_timestamp()
                 AND (valid_until IS NULL OR valid_until>clock_timestamp())
               ORDER BY created_at DESC LIMIT 1 FOR SHARE""",
            (principal["principal_id"], action, scope_ref))
        if cur.fetchone() is None:
            raise AuthorityDenied("no active grant for exact action and scope")
        return principal

    def _new_credential(self, cur, principal_id, *, expires_at=None):
        token = secrets.token_urlsafe(32)
        cur.execute("INSERT INTO principal_credentials(credential_id,principal_id,credential_sha256,expires_at) VALUES (%s,%s,%s,%s)",
                    (uuid4(), principal_id, self._digest(token), expires_at))
        return token

    def bootstrap_steward(self, principal_id="steward:camrui", *, token=None):
        """Create the first Steward from root-local setup, optionally with a
        pre-generated token that the caller has already persisted securely.

        Supplying a token enables write-ahead persistence: a protected local
        secret file can be durable before PostgreSQL commits. A failed
        transaction leaves an unusable token file that can safely be retried.
        """
        if os.geteuid() != 0:
            raise AuthorityDenied("initial Steward bootstrap requires trusted root-local setup")
        if not principal_id:
            raise ValueError("principal_id is required")
        if token is None:
            token = secrets.token_urlsafe(32)
        self._digest(token)
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                                (f"rv-authority-bootstrap:{self.schema}",))
                    cur.execute("SELECT 1 FROM institutional_principals WHERE principal_kind='steward' AND status='active' LIMIT 1")
                    if cur.fetchone():
                        raise IdentityConflict("active Steward is already provisioned")
                    cur.execute("INSERT INTO institutional_principals(principal_id,principal_kind) VALUES (%s,'steward')",
                                (principal_id,))
                    cur.execute("INSERT INTO principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)",
                                (uuid4(), principal_id, self._digest(token)))
                    for action, scope in self.BOOTSTRAP_GRANTS:
                        cur.execute("""INSERT INTO authority_grants
                            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                            VALUES (%s,%s,%s,%s,%s,%s)""",
                            (f"bootstrap:{action}", principal_id, action, scope,
                             principal_id, "rv.policy:bootstrap-steward.v1"))
                    self._event(cur, event_type="steward_bootstrapped", actor_id=principal_id,
                                subject_id=principal_id,
                                payload={"principal_kind": "steward", "token_persisted": False})
            return token
        except (AuthorityDenied, IdentityConflict, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def create_principal(self, steward_token, principal_id, principal_kind, *, office_id=None):
        allowed = {"resident", "service", "worker", "human"}
        if not principal_id or principal_kind not in allowed:
            raise ValueError("valid principal id and non-Steward kind are required")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "identity.manage", "institution")
                    cur.execute("""INSERT INTO institutional_principals
                        (principal_id,principal_kind,office_id) VALUES (%s,%s,%s)""",
                        (principal_id, principal_kind, office_id))
                    token = self._new_credential(cur, principal_id)
                    self._event(cur, event_type="principal_created", actor_id=actor["principal_id"],
                                subject_id=principal_id,
                                payload={"principal_kind": principal_kind, "office_id": office_id})
            return token
        except (AuthorityDenied, ValueError):
            raise
        except psycopg.errors.UniqueViolation as exc:
            raise IdentityConflict("principal identity already exists") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def issue_credential(self, steward_token, principal_id, *, expires_at=None):
        """Rotate or add one credential for an active principal; return it once."""
        self._validate_expiry(expires_at)
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "identity.manage", "institution")
                    cur.execute("SELECT status FROM institutional_principals WHERE principal_id=%s FOR UPDATE",
                                (principal_id,))
                    subject = cur.fetchone()
                    if subject is None or subject["status"] != "active":
                        raise IdentityConflict("credential subject is not active")
                    token = self._new_credential(cur, principal_id, expires_at=expires_at)
                    self._event(cur, event_type="credential_issued", actor_id=actor["principal_id"],
                                subject_id=principal_id,
                                payload={"expires_at": expires_at.isoformat() if expires_at else None})
            return token
        except (AuthorityDenied, IdentityConflict):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def revoke_credential(self, steward_token, credential_id, *, reason_code="steward_revoked"):
        """Revoke one bearer digest without invalidating the principal's identity."""
        if not reason_code or len(reason_code) > 64:
            raise ValueError("reason_code must be a bounded non-empty code")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "identity.manage", "institution")
                    cur.execute("""SELECT c.principal_id,p.principal_kind,
                            (SELECT count(*) FROM principal_credentials active
                             WHERE active.principal_id=c.principal_id AND active.revoked_at IS NULL
                               AND (active.expires_at IS NULL OR active.expires_at>clock_timestamp())) AS active_credentials
                        FROM principal_credentials c JOIN institutional_principals p USING (principal_id)
                        WHERE c.credential_id=%s AND c.revoked_at IS NULL FOR UPDATE OF c,p""",
                        (credential_id,))
                    row = cur.fetchone()
                    if row is None:
                        raise IdentityConflict("active credential was not found")
                    if row["principal_kind"] == "steward" and row["active_credentials"] <= 1:
                        raise IdentityConflict("cannot revoke the last active Steward credential")
                    cur.execute("UPDATE principal_credentials SET revoked_at=clock_timestamp() WHERE credential_id=%s",
                                (credential_id,))
                    self._event(cur, event_type="credential_revoked", actor_id=actor["principal_id"],
                                subject_id=row["principal_id"],
                                payload={"credential_id": str(credential_id),
                                         "reason_code": reason_code})
        except (AuthorityDenied, IdentityConflict, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def grant(self, steward_token, principal_id, action, scope_ref, *, grant_id=None,
              policy_ref, valid_until=None):
        self._validate_expiry(valid_until)
        if not all((principal_id, action, scope_ref, policy_ref)):
            raise ValueError("principal, action, scope and policy reference are required")
        grant_id = grant_id or "grant:" + uuid4().hex
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "authority.grant", "institution")
                    cur.execute("SELECT 1 FROM institutional_principals WHERE principal_id=%s AND status='active'",
                                (principal_id,))
                    if cur.fetchone() is None:
                        raise IdentityConflict("grant subject is not an active principal")
                    cur.execute("""INSERT INTO authority_grants
                        (grant_id,principal_id,action,scope_ref,granted_by,policy_ref,valid_until)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (grant_id, principal_id, action, scope_ref, actor["principal_id"], policy_ref, valid_until))
                    self._event(cur, event_type="authority_granted", actor_id=actor["principal_id"],
                                subject_id=principal_id, grant_id=grant_id,
                                payload={"action": action, "scope_ref": scope_ref,
                                         "policy_ref": policy_ref})
            return grant_id
        except (AuthorityDenied, IdentityConflict, ValueError):
            raise
        except psycopg.errors.UniqueViolation as exc:
            raise IdentityConflict("grant identity already exists") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def authorize(self, credential, action, scope_ref):
        if not action or not scope_ref:
            raise ValueError("action and scope_ref are required")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    principal = self._require(cur, credential, action, scope_ref)
                    return {"principal_id": principal["principal_id"],
                            "principal_kind": principal["principal_kind"],
                            "action": action, "scope_ref": scope_ref,
                            "verified_at": datetime.now(timezone.utc).isoformat()}
        except AuthorityDenied:
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def authorize_office_state(self, credential, office_id):
        """Authenticate the exact grant and require its principal to occupy the office."""
        if not isinstance(office_id, str) or not office_id:
            raise ValueError("office identity is required")
        if self.runtime_safe:
            try:
                with self.db.cursor() as cur:
                    query = psycopg.sql.SQL("SELECT {}.{}(%s,%s) AS snapshot").format(
                        psycopg.sql.Identifier(self.schema),
                        psycopg.sql.Identifier("read_authorized_office_state"))
                    cur.execute(query, (self._digest(credential), office_id))
                    row = cur.fetchone()
                if row is None or row["snapshot"] is None:
                    raise AuthorityDenied("credential is not the current office occupant")
                return dict(row["snapshot"])
            except AuthorityDenied:
                raise
            except Exception as exc:
                raise RegistryUnavailable(type(exc).__name__) from None
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    cur.execute("""SELECT o.office_id,o.office_role,b.occupant_id,
                        p.principal_id,p.principal_kind,i.implementation_id,i.kind AS implementation_kind,
                        i.provider_ref,i.revision AS implementation_revision,b.binding_revision,
                        s.state,s.revision AS state_revision,s.updated_at AS state_updated_at
                        FROM institutional_offices o
                        JOIN office_bindings b USING (office_id)
                        JOIN resident_occupants r USING (occupant_id)
                        JOIN institutional_principals p ON p.principal_id=r.principal_id
                        JOIN resident_implementations i USING (implementation_id)
                        JOIN office_runtime_state s ON s.office_id=o.office_id
                        WHERE o.office_id=%s FOR SHARE OF b""", (office_id,))
                    snapshot = cur.fetchone()
                    if snapshot is None:
                        raise IdentityConflict("office does not exist")
                    principal = self._require(
                        cur, credential, "office.state.write", "office:" + office_id)
                    if (principal["principal_kind"] != "resident"
                            or principal["principal_id"] != snapshot["principal_id"]
                            or not snapshot["occupant_id"] or not snapshot["implementation_id"]):
                        raise AuthorityDenied("credential principal is not the active office occupant")
                    snapshot["state"] = dict(snapshot["state"])
                    snapshot["state_updated_at"] = snapshot["state_updated_at"].isoformat()
                    return snapshot
        except (AuthorityDenied, IdentityConflict):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def revoke_grant(self, steward_token, grant_id, *, reason_code="steward_revoked"):
        if not reason_code or len(reason_code) > 64:
            raise ValueError("reason_code must be a bounded non-empty code")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "authority.grant", "institution")
                    cur.execute("UPDATE authority_grants SET revoked_at=clock_timestamp() WHERE grant_id=%s AND revoked_at IS NULL RETURNING principal_id,action,scope_ref",
                                (grant_id,))
                    row = cur.fetchone()
                    if row is None:
                        raise IdentityConflict("active grant was not found")
                    self._event(cur, event_type="authority_revoked", actor_id=actor["principal_id"],
                                subject_id=row["principal_id"], grant_id=grant_id,
                                payload={"reason_code": reason_code})
        except (AuthorityDenied, IdentityConflict, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def create_office(self, steward_token, office_id, office_role):
        if not office_id or not office_role:
            raise ValueError("office_id and office_role are required")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "office.manage", "institution")
                    cur.execute("INSERT INTO institutional_offices(office_id,office_role) VALUES (%s,%s)",
                                (office_id, office_role))
                    cur.execute("INSERT INTO office_runtime_state(office_id,state) VALUES (%s,'{}'::jsonb)", (office_id,))
                    self._event(cur, event_type="office_created", actor_id=actor["principal_id"],
                                office_id=office_id, payload={"office_role": office_role})
        except AuthorityDenied:
            raise
        except psycopg.errors.UniqueViolation as exc:
            raise IdentityConflict("office already exists") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def update_office_role(self, steward_token, office_id, office_role, *,
                           expected_office_role):
        """Correct stable office metadata under Steward authority without rebinding it."""
        if (not isinstance(office_id, str) or not office_id or len(office_id) > 256
                or not isinstance(office_role, str) or not office_role.strip()
                or len(office_role) > 256
                or not isinstance(expected_office_role, str)
                or not expected_office_role.strip() or len(expected_office_role) > 256):
            raise ValueError("office identity and bounded current and replacement roles are required")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "office.manage", "institution")
                    if actor.get("principal_kind") != "steward":
                        raise AuthorityDenied("office role correction requires Steward identity")
                    cur.execute("""SELECT office_role FROM institutional_offices
                        WHERE office_id=%s FOR UPDATE""", (office_id,))
                    current = cur.fetchone()
                    if current is None:
                        raise IdentityConflict("office does not exist")
                    if current["office_role"] != expected_office_role:
                        raise IdentityConflict("office role changed")
                    if office_role == expected_office_role:
                        return {"office_id": office_id, "office_role": office_role,
                                "changed": False}
                    cur.execute("""UPDATE institutional_offices SET office_role=%s
                        WHERE office_id=%s AND office_role=%s RETURNING office_role""",
                        (office_role.strip(), office_id, expected_office_role))
                    updated = cur.fetchone()
                    if updated is None:
                        raise IdentityConflict("office role changed")
                    self._event(cur, event_type="office_role_updated",
                        actor_id=actor["principal_id"], office_id=office_id,
                        payload={"previous_office_role": expected_office_role,
                                 "office_role": updated["office_role"]})
                    return {"office_id": office_id,
                            "office_role": updated["office_role"], "changed": True}
        except (AuthorityDenied, IdentityConflict, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def create_occupant(self, steward_token, occupant_id, *, principal_id):
        if not occupant_id or not principal_id:
            raise ValueError("occupant_id and principal_id are required")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "office.manage", "institution")
                    cur.execute("SELECT principal_kind FROM institutional_principals WHERE principal_id=%s AND status='active'",
                                (principal_id,))
                    principal = cur.fetchone()
                    if principal is None or principal["principal_kind"] not in {"resident", "human"}:
                        raise IdentityConflict("occupant must reference an active resident or human principal")
                    cur.execute("INSERT INTO resident_occupants(occupant_id,principal_id) VALUES (%s,%s)",
                                (occupant_id, principal_id))
                    self._event(cur, event_type="occupant_created", actor_id=actor["principal_id"],
                                subject_id=principal_id, payload={"occupant_id": occupant_id})
        except (AuthorityDenied, IdentityConflict):
            raise
        except psycopg.errors.UniqueViolation as exc:
            raise IdentityConflict("occupant already exists") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def create_implementation(self, steward_token, implementation_id, *, kind, provider_ref, revision):
        if not all((implementation_id, kind, provider_ref, revision)):
            raise ValueError("implementation id, kind, provider and revision are required")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "office.manage", "institution")
                    cur.execute("INSERT INTO resident_implementations(implementation_id,kind,provider_ref,revision) VALUES (%s,%s,%s,%s)",
                                (implementation_id, kind, provider_ref, revision))
                    self._event(cur, event_type="implementation_created", actor_id=actor["principal_id"],
                                payload={"implementation_id": implementation_id, "kind": kind,
                                         "provider_ref": provider_ref, "revision": revision})
        except AuthorityDenied:
            raise
        except psycopg.errors.UniqueViolation as exc:
            raise IdentityConflict("implementation already exists") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def bind_office(self, steward_token, office_id, occupant_id, implementation_id):
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "office.manage", "institution")
                    cur.execute("SELECT occupant_id,implementation_id FROM office_bindings WHERE office_id=%s FOR UPDATE",
                                (office_id,))
                    previous = cur.fetchone()
                    cur.execute("SELECT principal_id FROM resident_occupants WHERE occupant_id=%s",
                                (occupant_id,))
                    new_occupant = cur.fetchone()
                    if new_occupant is None:
                        raise IdentityConflict("office occupant does not exist")
                    revoked = []
                    if previous and previous["occupant_id"] != occupant_id:
                        cur.execute("""UPDATE authority_grants SET revoked_at=clock_timestamp()
                            WHERE principal_id=(SELECT principal_id FROM resident_occupants WHERE occupant_id=%s)
                              AND scope_ref=%s AND revoked_at IS NULL
                            RETURNING grant_id,principal_id,action""",
                            (previous["occupant_id"], f"office:{office_id}"))
                        revoked = cur.fetchall()
                        for grant in revoked:
                            self._event(cur, event_type="authority_revoked",
                                        actor_id=actor["principal_id"], subject_id=grant["principal_id"],
                                        grant_id=grant["grant_id"], office_id=office_id,
                                        payload={"reason_code": "office_occupant_replaced",
                                                 "action": grant["action"]})
                    cur.execute("""INSERT INTO office_bindings(office_id,occupant_id,implementation_id,binding_revision)
                        VALUES (%s,%s,%s,1) ON CONFLICT(office_id) DO UPDATE SET
                        occupant_id=excluded.occupant_id,implementation_id=excluded.implementation_id,
                        binding_revision=office_bindings.binding_revision+1,
                        updated_at=clock_timestamp() RETURNING binding_revision""",
                        (office_id, occupant_id, implementation_id))
                    rev = cur.fetchone()["binding_revision"]
                    self._event(cur, event_type="office_binding_replaced", actor_id=actor["principal_id"],
                                subject_id=new_occupant["principal_id"], office_id=office_id,
                                payload={"implementation_id": implementation_id,
                                         "binding_revision": rev,
                                         "previous_occupant_id": previous["occupant_id"] if previous else None,
                                         "previous_implementation_id": previous["implementation_id"] if previous else None,
                                         "revoked_office_grants": len(revoked)})
                    return rev
        except AuthorityDenied:
            raise
        except psycopg.errors.ForeignKeyViolation as exc:
            raise IdentityConflict("office, occupant or implementation does not exist") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def update_office_implementation(self, steward_token, office_id, implementation_id,
                                     *, expected_binding_revision,
                                     deferred_compatibility_capabilities=()):
        """Replace only an office's implementation using an audited CAS update.

        The occupant and office identity are invariant. The returned prior
        implementation can be restored through this same method using the new
        binding revision, so stale rollback attempts fail closed.
        """
        if not office_id or not implementation_id:
            raise ValueError("office and implementation identities are required")
        if type(expected_binding_revision) is not int or expected_binding_revision < 1:
            raise ValueError("expected binding revision must be a positive integer")
        if (not isinstance(deferred_compatibility_capabilities, (tuple, list))
                or any(capability != "grace.reasoning.80b"
                       for capability in deferred_compatibility_capabilities)
                or len(set(deferred_compatibility_capabilities)) !=
                   len(deferred_compatibility_capabilities)):
            raise ValueError("unsupported deferred compatibility capability")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "office.manage", "institution")
                    if (deferred_compatibility_capabilities
                            and actor.get("principal_kind") != "steward"):
                        raise AuthorityDenied("deferred continuity requires Steward authority")
                    cur.execute("""SELECT occupant_id,implementation_id,binding_revision
                        FROM office_bindings WHERE office_id=%s FOR UPDATE""", (office_id,))
                    previous = cur.fetchone()
                    if previous is None:
                        raise IdentityConflict("office has no active binding")
                    if previous["binding_revision"] != expected_binding_revision:
                        raise IdentityConflict("office binding revision changed")
                    cur.execute("""SELECT implementation_id,kind,provider_ref,revision
                        FROM resident_implementations WHERE implementation_id=%s""",
                        (implementation_id,))
                    target = cur.fetchone()
                    if target is None or target["kind"] != "model":
                        raise IdentityConflict("target model implementation is unavailable")
                    if (deferred_compatibility_capabilities
                            and target["provider_ref"] != "grace.readiness_router.v1"):
                        raise ValueError("deferred compatibility is limited to the Grace router")
                    cur.execute("""UPDATE office_bindings SET implementation_id=%s,
                        binding_revision=binding_revision+1,updated_at=clock_timestamp()
                        WHERE office_id=%s AND binding_revision=%s
                        RETURNING binding_revision""",
                        (implementation_id, office_id, expected_binding_revision))
                    updated = cur.fetchone()
                    if updated is None:
                        raise IdentityConflict("office binding revision changed")
                    cur.execute("SELECT principal_id FROM resident_occupants WHERE occupant_id=%s",
                                (previous["occupant_id"],))
                    occupant = cur.fetchone()
                    self._event(cur, event_type="office_model_implementation_changed",
                        actor_id=actor["principal_id"],
                        subject_id=occupant["principal_id"] if occupant else None,
                        office_id=office_id,
                        payload={"previous_implementation_id": previous["implementation_id"],
                            "implementation_id": implementation_id,
                            "previous_binding_revision": expected_binding_revision,
                            "binding_revision": updated["binding_revision"],
                            "provider_ref": target["provider_ref"],
                            "implementation_revision": target["revision"],
                            "deferred_compatibility_capabilities":
                                list(deferred_compatibility_capabilities)})
                    return {"office_id": office_id,
                        "occupant_id": previous["occupant_id"],
                        "previous_implementation_id": previous["implementation_id"],
                        "implementation_id": implementation_id,
                        "previous_binding_revision": expected_binding_revision,
                        "binding_revision": updated["binding_revision"]}
        except (AuthorityDenied, IdentityConflict, ValueError):
            raise
        except psycopg.errors.ForeignKeyViolation as exc:
            raise IdentityConflict("target implementation does not exist") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def set_office_state(self, credential, office_id, state, *, expected_revision=None):
        if not isinstance(state, dict):
            raise ValueError("office state must be a JSON object")
        encoded = json.dumps(state, sort_keys=True, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > self.MAX_STATE_BYTES:
            raise ValueError("office state exceeds the bounded state limit")
        if self.runtime_safe:
            try:
                with self.db.cursor() as cur:
                    query = psycopg.sql.SQL("SELECT {}.{}(%s,%s,%s::jsonb,%s) AS revision").format(
                        psycopg.sql.Identifier(self.schema),
                        psycopg.sql.Identifier("write_authorized_office_state"))
                    cur.execute(query, (self._digest(credential), office_id, encoded,
                                        expected_revision))
                    row = cur.fetchone()
                if row is None or row["revision"] is None:
                    raise AuthorityDenied("credential is not the current office occupant")
                return row["revision"]
            except (AuthorityDenied, ValueError):
                raise
            except psycopg.errors.SerializationFailure as exc:
                raise IdentityConflict("office state revision conflict") from exc
            except psycopg.Error as exc:
                if exc.sqlstate == "22023":
                    raise ValueError("office state is invalid or exceeds its bound") from None
                raise RegistryUnavailable(type(exc).__name__) from None
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    cur.execute("""SELECT p.principal_id FROM office_bindings b
                        JOIN resident_occupants r USING (occupant_id)
                        JOIN institutional_principals p ON p.principal_id=r.principal_id
                        WHERE b.office_id=%s FOR SHARE OF b""", (office_id,))
                    binding = cur.fetchone()
                    if binding is None:
                        raise AuthorityDenied("office has no active resident binding")
                    principal = self._require(cur, credential, "office.state.write", f"office:{office_id}")
                    if (principal["principal_kind"] != "resident"
                            or principal["principal_id"] != binding["principal_id"]):
                        raise AuthorityDenied("credential principal is not the active office occupant")
                    cur.execute("SELECT revision FROM office_runtime_state WHERE office_id=%s FOR UPDATE", (office_id,))
                    row = cur.fetchone()
                    if row is None:
                        raise IdentityConflict("office does not exist")
                    if expected_revision is not None and row["revision"] != expected_revision:
                        raise IdentityConflict("office state revision conflict")
                    cur.execute("UPDATE office_runtime_state SET state=%s::jsonb,revision=revision+1,updated_at=clock_timestamp() WHERE office_id=%s RETURNING revision",
                                (encoded, office_id))
                    rev = cur.fetchone()["revision"]
                    self._event(cur, event_type="office_state_updated", actor_id=principal["principal_id"],
                                office_id=office_id, payload={"revision": rev})
                    return rev
        except (AuthorityDenied, IdentityConflict, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def office_snapshot(self, office_id):
        try:
            with self.db.cursor() as cur:
                self._path(cur)
                cur.execute("""SELECT o.office_id,o.office_role,b.occupant_id,
                    p.principal_id,p.principal_kind,i.implementation_id,i.kind AS implementation_kind,
                    i.provider_ref,i.revision AS implementation_revision,b.binding_revision,
                    s.state,s.revision AS state_revision,s.updated_at AS state_updated_at
                    FROM institutional_offices o LEFT JOIN office_bindings b USING (office_id)
                    LEFT JOIN resident_occupants r USING (occupant_id)
                    LEFT JOIN institutional_principals p ON p.principal_id=r.principal_id
                    LEFT JOIN resident_implementations i USING (implementation_id)
                    JOIN office_runtime_state s ON s.office_id=o.office_id WHERE o.office_id=%s""", (office_id,))
                row=cur.fetchone()
                if row is None:
                    raise IdentityConflict("office does not exist")
                row["state"] = dict(row["state"])
                row["state_updated_at"] = row["state_updated_at"].isoformat()
                return row
        except IdentityConflict:
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def is_authorized_implementation_successor(self, credential, office_id, *,
            predecessor_id, predecessor_revision, successor_id, successor_revision,
            required_capability):
        """Accept only the direct predecessor recorded by the current audited CAS binding."""
        if not all(isinstance(value, str) and value for value in
                   (office_id, predecessor_id, predecessor_revision,
                    successor_id, successor_revision, required_capability)):
            return False
        try:
            with self.db.cursor() as cur:
                query = psycopg.sql.SQL("SELECT {}.{}(%s,%s,%s,%s,%s,%s,%s) AS allowed").format(
                    psycopg.sql.Identifier(self.schema),
                    psycopg.sql.Identifier("authorized_office_implementation_successor"))
                cur.execute(query, (self._digest(credential), office_id, predecessor_id,
                    predecessor_revision, successor_id, successor_revision,
                    required_capability))
                row = cur.fetchone()
            return bool(row and row["allowed"])
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None
