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
import re
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

    SCHEMA_VERSION = "0017_reusable_scoped_grants"
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
                 AND grant_kind='direct' AND revoked_at IS NULL AND valid_from<=clock_timestamp()
                 AND (valid_until IS NULL OR valid_until>clock_timestamp())
               ORDER BY created_at DESC LIMIT 1 FOR SHARE""",
            (principal["principal_id"], action, scope_ref))
        if cur.fetchone() is None:
            raise AuthorityDenied("no active direct grant for exact action and scope")
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

    @staticmethod
    def _validate_delegation_scope(scope_ref):
        import re
        if not isinstance(scope_ref, str):
            raise ValueError("delegated grants require a registered project, issue, or host scope")
        if re.fullmatch(r"project:[A-Za-z0-9._-]{1,128}", scope_ref):
            return
        if re.fullmatch(r"issue:[A-Za-z0-9._-]{1,128}/[A-Za-z0-9._-]{1,128}", scope_ref):
            return
        if re.fullmatch(r"host:[a-z][a-z0-9-]{1,62}", scope_ref):
            return
        raise ValueError("scope must be project:<id>, issue:<project-id>/<issue-id>, or host:<registered-host-id>")

    def _insert_delegated_grant(self, cur, actor_id, principal_id, action, scope_ref, *,
                                proposal_ref, proposal_digest, approval_ref, policy_ref,
                                grant_id=None, max_uses=None, valid_until=None,
                                expires_24h_after_activation=False):
        grant_id = grant_id or "grant:" + uuid4().hex
        cur.execute("SELECT 1 FROM institutional_principals WHERE principal_id=%s AND status='active'",
                    (principal_id,))
        if cur.fetchone() is None:
            raise IdentityConflict("grant subject is not an active principal")
        cur.execute("""INSERT INTO authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref,
             valid_until,max_uses,grant_kind,approval_ref,proposal_ref,
             proposal_digest,approved_by,approved_at)
            VALUES (%s,%s,%s,%s,%s,%s,
                CASE WHEN %s THEN clock_timestamp()+interval '24 hours' ELSE %s END,
                %s,'delegated',%s,%s,%s,%s,clock_timestamp()) RETURNING valid_until""",
            (grant_id, principal_id, action, scope_ref, actor_id, policy_ref,
             expires_24h_after_activation, valid_until, max_uses, approval_ref,
             proposal_ref, proposal_digest, actor_id))
        activated_expiry = cur.fetchone()["valid_until"]
        self._event(cur,event_type="authority_granted",actor_id=actor_id,
            subject_id=principal_id,grant_id=grant_id,
            payload={"action":action,"scope_ref":scope_ref,"policy_ref":policy_ref,
                "grant_kind":"delegated","max_uses":max_uses,
                "valid_until":activated_expiry.isoformat() if activated_expiry else None,
                "proposal_ref":proposal_ref,"proposal_digest":proposal_digest,
                "approval_ref":approval_ref,"approved_by":actor_id})
        return grant_id

    @staticmethod
    def _validate_delegated_grant_values(principal_id, action, scope_ref, *,
                                         proposal_ref, proposal_digest, approval_ref,
                                         policy_ref, max_uses, valid_until):
        AuthorityRegistry._validate_delegation_scope(scope_ref)
        AuthorityRegistry._validate_expiry(valid_until)
        if not all((principal_id, action, proposal_ref, approval_ref, policy_ref)):
            raise ValueError("principal, action, proposal, approval and policy references are required")
        if (not isinstance(action,str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}",action) or
                action in {"authority.grant","identity.manage","office.manage"}):
            raise ValueError("delegated action must be a specific non-management operation")
        if not isinstance(proposal_digest, str) or len(proposal_digest) != 64 or any(c not in "0123456789abcdef" for c in proposal_digest):
            raise ValueError("proposal_digest must be a lowercase SHA-256 hex digest")
        if max_uses is not None and (type(max_uses) is not int or not 1<=max_uses<=1_000_000):
            raise ValueError("max_uses must be between 1 and 1000000")
        if max_uses is None and valid_until is None:
            raise ValueError("delegated grants must have a use limit, an expiry, or both")
        for name, value in (("approval_ref",approval_ref),("proposal_ref",proposal_ref)):
            if not isinstance(value,str) or not value.strip() or len(value)>256:
                raise ValueError(f"{name} must be a bounded non-empty reference")
        if not isinstance(policy_ref,str) or not policy_ref.strip() or len(policy_ref)>256:
            raise ValueError("policy_ref must be a bounded non-empty reference")

    def approve_delegated_grant(self, steward_token, principal_id, action, scope_ref, *,
                                proposal_ref, proposal_digest, approval_ref, policy_ref,
                                grant_id=None, max_uses=None, valid_until=None):
        """Create an exact delegated grant after authenticated Steward approval."""
        self._validate_delegated_grant_values(principal_id,action,scope_ref,
            proposal_ref=proposal_ref,proposal_digest=proposal_digest,
            approval_ref=approval_ref,policy_ref=policy_ref,
            max_uses=max_uses,valid_until=valid_until)
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor=self._require(cur,steward_token,"authority.grant","institution")
                    if actor["principal_kind"]!="steward":
                        raise AuthorityDenied("delegated grant activation requires an authenticated Steward")
                    grant_id=self._insert_delegated_grant(cur,actor["principal_id"],principal_id,
                        action,scope_ref,proposal_ref=proposal_ref,proposal_digest=proposal_digest,
                        approval_ref=approval_ref,policy_ref=policy_ref,grant_id=grant_id,
                        max_uses=max_uses,valid_until=valid_until)
            return grant_id
        except (AuthorityDenied,IdentityConflict,ValueError):
            raise
        except psycopg.errors.UniqueViolation as exc:
            raise IdentityConflict("grant identity already exists") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    @staticmethod
    def _delegation_request_digest(values):
        encoded=json.dumps(values,sort_keys=True,separators=(",",":"),default=lambda v:v.isoformat() if isinstance(v,datetime) else v)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _require_steward_identity(cur, principal_id):
        cur.execute("SELECT principal_kind,status FROM institutional_principals WHERE principal_id=%s FOR UPDATE",
                    (principal_id,))
        row=cur.fetchone()
        if row is None or row["status"]!="active" or row["principal_kind"]!="steward":
            raise AuthorityDenied("authenticated active Steward context is required")

    def _create_delegation_request(self, *, request_kind, requester_id, principal_id,
                                   action, scope_ref, policy_ref, request_ref,
                                   max_uses, valid_until, idempotency_key,
                                   change_grant_id=None):
        self._validate_delegation_scope(scope_ref)
        self._validate_expiry(valid_until)
        if (not isinstance(action,str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}",action) or
                action in {"authority.grant","identity.manage","office.manage"}):
            raise ValueError("delegated action must be a specific non-management operation")
        if not isinstance(policy_ref,str) or not policy_ref.startswith("policy:") or len(policy_ref)>256:
            raise ValueError("policy_ref is invalid")
        if not isinstance(request_ref,str) or not request_ref.strip() or len(request_ref)>256:
            raise ValueError("request_ref must be a bounded non-empty reference")
        if max_uses is not None and (type(max_uses) is not int or not 1<=max_uses<=1_000_000):
            raise ValueError("max_uses must be between 1 and 1000000")
        if max_uses is None and valid_until is None:
            raise ValueError("delegated grants must have a use limit or expiry")
        if action == "comms5.operations.non_destructive.v1" and (
                scope_ref != "project:Riverview" or policy_ref != "policy:delegation.v1"
                or max_uses is not None):
            raise AuthorityDenied("broad Comms5 delegation requires Riverview scope and unlimited use")
        if not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=200:
            raise ValueError("idempotency_key must be bounded")
        payload={"request_kind":request_kind,"requester_id":requester_id,
            "principal_id":principal_id,"action":action,"scope_ref":scope_ref,
            "policy_ref":policy_ref,"request_ref":request_ref,"max_uses":max_uses,
            "valid_until":valid_until}
        digest=self._delegation_request_digest(payload)
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    self._require_steward_identity(cur,requester_id)
                    cur.execute("SELECT 1 FROM institutional_principals WHERE principal_id=%s AND status='active'",
                                (principal_id,))
                    if cur.fetchone() is None:
                        raise IdentityConflict("grant subject is not an active principal")
                    if change_grant_id:
                        cur.execute("""SELECT principal_id,grant_kind,revoked_at FROM authority_grants
                            WHERE grant_id=%s FOR SHARE""",(change_grant_id,))
                        old=cur.fetchone()
                        if old is None or old["grant_kind"]!="delegated" or old["revoked_at"] is not None:
                            raise IdentityConflict("active delegated grant for change was not found")
                        if old["principal_id"]!=principal_id:
                            raise AuthorityDenied("replacement must retain the existing grant grantee")
                    cur.execute("""SELECT request_id,request_sha256,status FROM delegated_grant_requests
                        WHERE requester_id=%s AND request_kind=%s AND idempotency_key=%s FOR UPDATE""",
                        (requester_id,request_kind,idempotency_key))
                    existing=cur.fetchone()
                    if existing:
                        if existing["request_sha256"]!=digest:
                            raise IdentityConflict("idempotency key conflicts with a different delegation request")
                        return {"status":existing["status"],"request_id":existing["request_id"],
                                "request_sha256":existing["request_sha256"]}
                    request_id="delegation-request:"+uuid4().hex
                    cur.execute("""INSERT INTO delegated_grant_requests
                        (request_id,request_kind,requester_id,grantee_id,change_grant_id,
                         action,scope_ref,policy_ref,request_ref,max_uses,valid_until,
                         request_sha256,idempotency_key,status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
                        (request_id,request_kind,requester_id,principal_id,change_grant_id,
                         action,scope_ref,policy_ref,request_ref,max_uses,valid_until,digest,idempotency_key))
                    self._event(cur,event_type="authority_delegation_request_created",
                        actor_id=requester_id,subject_id=principal_id,
                        payload={"request_id":request_id,"request_kind":request_kind,
                            "request_sha256":digest,"action":action,"scope_ref":scope_ref,
                            "request_ref":request_ref,"change_grant_id":change_grant_id})
            return {"status":"pending","request_id":request_id,"request_sha256":digest}
        except (AuthorityDenied,IdentityConflict,ValueError):
            raise
        except psycopg.errors.UniqueViolation as exc:
            raise IdentityConflict("delegation request identity conflicts") from exc
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def request_grant(self, *, requester_id, principal_id, action, scope_ref,
                      policy_ref, request_ref, max_uses=None, valid_until=None,
                      idempotency_key):
        return self._create_delegation_request(request_kind="grant",
            requester_id=requester_id,principal_id=principal_id,action=action,
            scope_ref=scope_ref,policy_ref=policy_ref,request_ref=request_ref,
            max_uses=max_uses,valid_until=valid_until,idempotency_key=idempotency_key)

    def request_change(self, *, requester_id, grant_id, action, scope_ref,
                       policy_ref, request_ref, max_uses=None, valid_until=None,
                       idempotency_key):
        with self.db.transaction():
            with self.db.cursor() as cur:
                self._path(cur)
                cur.execute("SELECT principal_id FROM authority_grants WHERE grant_id=%s",
                            (grant_id,))
                existing=cur.fetchone()
                if existing is None:
                    raise IdentityConflict("grant for change was not found")
                principal_id=existing["principal_id"]
        return self._create_delegation_request(request_kind="change",
            requester_id=requester_id,principal_id=principal_id,action=action,
            scope_ref=scope_ref,policy_ref=policy_ref,request_ref=request_ref,
            max_uses=max_uses,valid_until=valid_until,idempotency_key=idempotency_key,
            change_grant_id=grant_id)

    def list_active_delegated_grants(self, credential, action, scope_ref):
        """Read the caller's own active exact-scope delegated grants without consuming them."""
        self._validate_delegation_scope(scope_ref)
        if not isinstance(action, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", action):
            raise ValueError("delegated action is invalid")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    principal = self._authenticate(cur, credential)
                    if principal.get("principal_id") != "steward:camrui" or principal.get("principal_kind") != "steward":
                        raise AuthorityDenied("delegated GPU permission view requires the authenticated Steward principal")
                    cur.execute("""SELECT grant_id,action,scope_ref,policy_ref,valid_until
                        FROM authority_grants
                        WHERE principal_id=%s AND action=%s AND scope_ref=%s
                          AND grant_kind='delegated' AND revoked_at IS NULL
                          AND valid_from<=clock_timestamp()
                          AND (valid_until IS NULL OR valid_until>clock_timestamp())
                        ORDER BY approved_at DESC,grant_id""",
                        (principal["principal_id"], action, scope_ref))
                    return [{key:(value.isoformat() if isinstance(value,datetime) else value)
                             for key,value in dict(row).items()} for row in cur.fetchall()]
        except (AuthorityDenied, IdentityConflict, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def get_status(self, *, requester_id, request_id=None, grant_id=None):
        if (request_id is None)==(grant_id is None):
            raise ValueError("exactly one request_id or grant_id is required")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    cur.execute("SELECT principal_kind,status FROM institutional_principals WHERE principal_id=%s",
                                (requester_id,))
                    principal=cur.fetchone()
                    is_steward=bool(principal and principal["status"]=="active"
                                    and principal["principal_kind"]=="steward")
                    if request_id is not None:
                        cur.execute("""SELECT request_id,request_kind,requester_id,grantee_id,
                            change_grant_id,action,scope_ref,policy_ref,request_ref,max_uses,
                            valid_until,request_sha256,status,decision,decision_by,decision_at,
                            approval_ref,grant_id FROM delegated_grant_requests WHERE request_id=%s
                              AND (%s OR requester_id=%s OR grantee_id=%s)""",
                            (request_id,is_steward,requester_id,requester_id))
                        row=cur.fetchone()
                        if row is None:
                            raise IdentityConflict("delegation request was not found")
                        return {key:(value.isoformat() if isinstance(value,datetime) else value)
                                for key,value in dict(row).items()}
                    cur.execute("""SELECT grant_id,principal_id,action,scope_ref,policy_ref,
                        valid_until,max_uses,used_count,grant_kind,proposal_ref,proposal_digest,
                        approved_by,approved_at,approval_ref,revoked_at FROM authority_grants
                        WHERE grant_id=%s AND grant_kind='delegated'
                          AND (%s OR principal_id=%s)""",(grant_id,is_steward,requester_id))
                    row=cur.fetchone()
                    if row is None:
                        raise IdentityConflict("delegated grant was not found")
                    result={key:(value.isoformat() if isinstance(value,datetime) else value)
                            for key,value in dict(row).items()}
                    result["status"]=("revoked" if row["revoked_at"] else
                        "expired" if row["valid_until"] and row["valid_until"]<=datetime.now(timezone.utc) else "active")
                    return result
        except (AuthorityDenied,IdentityConflict,ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def decide_request(self, *, steward_token, request_id, decision,
                       expected_request_sha256, idempotency_key, approval_ref=None):
        if decision not in {"approve","reject"} or not re.fullmatch(r"[0-9a-f]{64}",str(expected_request_sha256)):
            raise ValueError("delegation decision binding is invalid")
        if not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=200:
            raise ValueError("idempotency key is invalid")
        if decision=="approve" and (not isinstance(approval_ref,str) or not approval_ref.strip() or len(approval_ref)>256):
            raise ValueError("approval_ref is required for approval")
        if decision=="reject" and approval_ref is not None:
            raise ValueError("rejection must not include approval_ref")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor=self._require(cur,steward_token,"authority.grant","institution")
                    if actor["principal_kind"]!="steward":
                        raise AuthorityDenied("delegation decision requires an authenticated Steward")
                    cur.execute("SELECT * FROM delegated_grant_requests WHERE request_id=%s FOR UPDATE",
                                (request_id,))
                    request=cur.fetchone()
                    if request is None:
                        raise IdentityConflict("delegation request was not found")
                    if request["request_sha256"]!=expected_request_sha256:
                        raise IdentityConflict("delegation request changed since review")
                    if request["status"]!="pending":
                        if (request["decision"]==decision and
                                request["decision_idempotency_key"]==idempotency_key and
                                request["approval_ref"]==approval_ref):
                            return {"status":request["status"],"request_id":request_id,
                                    "request_sha256":request["request_sha256"],"grant_id":request["grant_id"]}
                        raise IdentityConflict("delegation request has already been decided")
                    grant_id=None
                    if decision=="approve":
                        grant_id=self._insert_delegated_grant(cur,actor["principal_id"],
                            request["grantee_id"],request["action"],request["scope_ref"],
                            proposal_ref=request["request_ref"],proposal_digest=request["request_sha256"],
                            approval_ref=approval_ref,policy_ref=request["policy_ref"],
                            max_uses=request["max_uses"],valid_until=request["valid_until"],
                            expires_24h_after_activation=(
                                request["action"] == "comms5.operations.non_destructive.v1"))
                        if request["request_kind"]=="change":
                            cur.execute("""UPDATE authority_grants SET revoked_at=clock_timestamp()
                                WHERE grant_id=%s AND revoked_at IS NULL RETURNING grant_id""",
                                (request["change_grant_id"],))
                            if cur.fetchone() is None:
                                raise IdentityConflict("grant changed while replacement was pending")
                            cur.execute("""UPDATE delegated_grant_reservations SET status='released',
                                reason_code='grant_replaced',updated_at=clock_timestamp()
                                WHERE grant_id=%s AND status='reserved' RETURNING reservation_id""",
                                (request["change_grant_id"],))
                            for item in cur.fetchall():
                                self._reservation_event(cur,event_type="authority_grant_reservation_released",
                                    actor_id=actor["principal_id"],grant_id=request["change_grant_id"],
                                    reservation_id=item["reservation_id"],payload={"reason_code":"grant_replaced"})
                            self._event(cur,event_type="authority_revoked",actor_id=actor["principal_id"],
                                subject_id=request["grantee_id"],grant_id=request["change_grant_id"],
                                payload={"reason_code":"steward_replaced"})
                    status="approved" if decision=="approve" else "rejected"
                    cur.execute("""UPDATE delegated_grant_requests SET status=%s,decision=%s,
                        decision_by=%s,decision_at=clock_timestamp(),decision_idempotency_key=%s,
                        approval_ref=%s,grant_id=%s,updated_at=clock_timestamp()
                        WHERE request_id=%s""",
                        (status,decision,actor["principal_id"],idempotency_key,approval_ref,grant_id,request_id))
                    self._event(cur,event_type="authority_delegation_request_decided",
                        actor_id=actor["principal_id"],subject_id=request["grantee_id"],grant_id=grant_id,
                        payload={"request_id":request_id,"request_sha256":expected_request_sha256,
                            "decision":decision,"approval_ref":approval_ref,
                            "idempotency_key":idempotency_key})
            return {"status":status,"request_id":request_id,
                    "request_sha256":expected_request_sha256,"grant_id":grant_id}
        except (AuthorityDenied,IdentityConflict,ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def surrender_grant(self, *, grantee_id, grant_id, reason_code="grantee_surrendered",
                        idempotency_key):
        if (not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=200 or
                not isinstance(reason_code,str) or not re.fullmatch(r"[a-z0-9_]{1,64}",reason_code)):
            raise ValueError("surrender identity or reason is invalid")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    cur.execute("SELECT principal_kind,status FROM institutional_principals WHERE principal_id=%s",
                                (grantee_id,))
                    principal=cur.fetchone()
                    if principal is None or principal["status"]!="active":
                        raise AuthorityDenied("active grantee identity is required")
                    cur.execute("""SELECT principal_id,grant_kind,revoked_at,surrender_idempotency_key,
                        surrender_reason_code,action,scope_ref FROM authority_grants WHERE grant_id=%s FOR UPDATE""",(grant_id,))
                    grant=cur.fetchone()
                    if grant is None or grant["grant_kind"]!="delegated" or grant["principal_id"]!=grantee_id:
                        raise AuthorityDenied("only the grantee may surrender this delegated grant")
                    if grant["revoked_at"] is not None:
                        if (grant["surrender_idempotency_key"]==idempotency_key and
                                grant["surrender_reason_code"]==reason_code):
                            return {"status":"surrendered","grant_id":grant_id}
                        raise IdentityConflict("delegated grant is already inactive")
                    cur.execute("""UPDATE authority_grants SET revoked_at=clock_timestamp(),
                        surrender_idempotency_key=%s,surrender_reason_code=%s,surrendered_by=%s,
                        surrendered_at=clock_timestamp() WHERE grant_id=%s""",
                        (idempotency_key,reason_code,grantee_id,grant_id))
                    cur.execute("""UPDATE delegated_grant_reservations SET status='released',
                        reason_code='grant_surrendered',updated_at=clock_timestamp()
                        WHERE grant_id=%s AND status='reserved' RETURNING reservation_id""",(grant_id,))
                    for item in cur.fetchall():
                        self._reservation_event(cur,event_type="authority_grant_reservation_released",
                            actor_id=grantee_id,grant_id=grant_id,reservation_id=item["reservation_id"],
                            payload={"reason_code":"grant_surrendered"})
                    self._event(cur,event_type="authority_grant_surrendered",actor_id=grantee_id,
                        subject_id=grantee_id,grant_id=grant_id,
                        payload={"action":grant["action"],"scope_ref":grant["scope_ref"],
                            "reason_code":reason_code,"idempotency_key":idempotency_key})
            return {"status":"surrendered","grant_id":grant_id}
        except (AuthorityDenied,IdentityConflict,ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def _reservation_event(self, cur, *, event_type, actor_id, grant_id,
                           reservation_id, payload=None):
        body = dict(payload or {})
        body["reservation_id"] = str(reservation_id)
        self._event(cur, event_type=event_type, actor_id=actor_id,
                    subject_id=actor_id, grant_id=grant_id, payload=body)

    def authorize_delegated_principal_operation(self, principal_id, action, scope_ref,
                                                policy_ref, operation_ref):
        """Authorize and audit one operation for an OAuth-attested principal.

        This manager-only path accepts an already authenticated principal ID
        from the protected Comms5 ingress. It supports only unlimited delegated
        grants; finite grants must use the reservation/consume/release API.
        """
        self._validate_delegation_scope(scope_ref)
        if (not all(isinstance(value, str) and value for value in
                    (principal_id, action, policy_ref, operation_ref)) or
                len(operation_ref) > 256):
            raise ValueError("delegated operation identity is invalid")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    cur.execute("""SELECT principal_kind,status FROM institutional_principals
                        WHERE principal_id=%s FOR SHARE""", (principal_id,))
                    principal = cur.fetchone()
                    if principal is None or principal["status"] != "active":
                        raise AuthorityDenied("OAuth principal is not active in AuthorityRegistry")
                    cur.execute("""SELECT grant_id,valid_until,max_uses,used_count
                        FROM authority_grants
                        WHERE principal_id=%s AND action=%s AND scope_ref=%s
                          AND policy_ref=%s AND grant_kind='delegated' AND revoked_at IS NULL
                          AND valid_from<=clock_timestamp()
                          AND (valid_until IS NULL OR valid_until>clock_timestamp())
                          AND max_uses IS NULL
                        ORDER BY approved_at DESC, grant_id
                          LIMIT 1 FOR UPDATE""", (principal_id, action, scope_ref, policy_ref))
                    grant = cur.fetchone()
                    if grant is None:
                        raise AuthorityDenied("no active unlimited delegated grant covers this operation")
                    self._event(cur, event_type="authority_grant_used",
                        actor_id=principal_id, subject_id=principal_id,
                        grant_id=grant["grant_id"], payload={
                            "action": action, "scope_ref": scope_ref,
                            "policy_ref": policy_ref, "operation_ref": operation_ref,
                            "valid_until": grant["valid_until"].isoformat()
                                if grant["valid_until"] else None,
                            "use_limit": "unlimited"})
            return {"grant_id": grant["grant_id"], "principal_id": principal_id,
                    "action": action, "scope_ref": scope_ref,
                    "valid_until": grant["valid_until"].isoformat()
                        if grant["valid_until"] else None,
                    "status": "authorized", "use_limit": "unlimited"}
        except (AuthorityDenied, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def reserve_delegated_grant(self, grantee_token, grant_id, action, scope_ref, operation_ref, *, idempotency_key):
        """Atomically reserve a use for one exact promotion/work-order operation."""
        self._validate_delegation_scope(scope_ref)
        if (not all((grant_id,action,operation_ref,idempotency_key)) or
                not isinstance(operation_ref,str) or len(operation_ref)>256 or
                not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=200):
            raise ValueError("grant, action, operation reference and bounded idempotency key are required")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    grantee = self._authenticate(cur, grantee_token)
                    cur.execute("""SELECT grant_id,principal_id,action,scope_ref,proposal_ref,
                                          grant_kind,max_uses,used_count,valid_from,valid_until,revoked_at
                        FROM authority_grants WHERE grant_id=%s AND principal_id=%s
                        FOR UPDATE""", (grant_id, grantee["principal_id"]))
                    grant = cur.fetchone()
                    if grant is None or grant["grant_kind"] != "delegated":
                        raise AuthorityDenied("delegated grant is not assigned to this grantee")
                    if grant["action"] != action or grant["scope_ref"] != scope_ref:
                        raise AuthorityDenied("operation and scope do not match the approved grant")
                    cur.execute("""SELECT reservation_id,status,action,scope_ref,operation_ref,
                                          generation,lease_expires_at,result_ref,reason_code
                        FROM delegated_grant_reservations
                        WHERE grant_id=%s AND grantee_id=%s AND idempotency_key=%s
                        ORDER BY generation DESC LIMIT 1 FOR UPDATE""",
                        (grant_id, grantee["principal_id"], idempotency_key))
                    existing = cur.fetchone()
                    if existing is not None:
                        if (existing["action"] != action or existing["scope_ref"] != scope_ref or
                                existing["operation_ref"] != operation_ref):
                            raise AuthorityDenied("idempotency key was already used for different request data")
                        if existing["status"] == "reserved" and existing["lease_expires_at"] <= datetime.now(timezone.utc):
                            cur.execute("""UPDATE delegated_grant_reservations SET status='expired',updated_at=clock_timestamp()
                                WHERE reservation_id=%s RETURNING reservation_id""", (existing["reservation_id"],))
                            self._reservation_event(cur, event_type="authority_grant_reservation_expired",
                                actor_id=grantee["principal_id"], grant_id=grant_id,
                                reservation_id=existing["reservation_id"], payload={"cause":"lease_expired"})
                            existing["status"] = "expired"
                        if existing["status"] in {"reserved","consumed"}:
                            return {"reservation_id": str(existing["reservation_id"]),
                                    "status": existing["status"],
                                    "lease_expires_at": existing["lease_expires_at"].isoformat(),
                                    "result_ref": existing["result_ref"],
                                    "reason_code": existing["reason_code"],
                                    "generation": existing["generation"]}
                        inactive=(grant["revoked_at"] is not None or
                            (grant["valid_until"] is not None and grant["valid_until"]<=datetime.now(timezone.utc)))
                        if inactive:
                            return {"reservation_id":str(existing["reservation_id"]),
                                    "status":existing["status"],
                                    "lease_expires_at":existing["lease_expires_at"].isoformat(),
                                    "result_ref":existing["result_ref"],
                                    "reason_code":existing["reason_code"],
                                    "generation":existing["generation"]}
                        next_generation = existing["generation"] + 1
                    else:
                        next_generation = 1
                    if grant["revoked_at"] is not None or grant["valid_from"] > datetime.now(timezone.utc) or (
                            grant["valid_until"] is not None and grant["valid_until"] <= datetime.now(timezone.utc)):
                        raise AuthorityDenied("delegated grant is not currently active")
                    cur.execute("""UPDATE delegated_grant_reservations SET status='expired',updated_at=clock_timestamp()
                        WHERE grant_id=%s AND status='reserved' AND lease_expires_at<=clock_timestamp()
                        RETURNING reservation_id,grantee_id""", (grant_id,))
                    for expired in cur.fetchall():
                        self._reservation_event(cur, event_type="authority_grant_reservation_expired",
                            actor_id=expired["grantee_id"], grant_id=grant_id,
                            reservation_id=expired["reservation_id"], payload={"cause":"lease_expired"})
                    cur.execute("""SELECT count(*) AS live_count FROM delegated_grant_reservations
                        WHERE grant_id=%s AND status='reserved' AND lease_expires_at>clock_timestamp()""",
                        (grant_id,))
                    live_count = cur.fetchone()["live_count"]
                    if grant["max_uses"] is not None and grant["used_count"] + live_count >= grant["max_uses"]:
                        raise AuthorityDenied("delegated grant use limit is reserved or exhausted")
                    reservation_id = uuid4()
                    cur.execute("""INSERT INTO delegated_grant_reservations
                        (reservation_id,grant_id,grantee_id,idempotency_key,generation,operation_ref,
                         action,scope_ref,proposal_ref,status,lease_expires_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'reserved',
                            CASE WHEN %s::timestamptz IS NULL THEN clock_timestamp()+interval '300 seconds'
                                 ELSE LEAST(clock_timestamp()+interval '300 seconds',%s::timestamptz) END)
                        RETURNING lease_expires_at""",
                        (reservation_id,grant_id,grantee["principal_id"],idempotency_key,next_generation,
                         operation_ref,action,scope_ref,grant["proposal_ref"],grant["valid_until"],grant["valid_until"]))
                    lease_expires_at = cur.fetchone()["lease_expires_at"]
                    self._reservation_event(cur, event_type="authority_grant_reserved",
                        actor_id=grantee["principal_id"], grant_id=grant_id,
                        reservation_id=reservation_id,
                        payload={"action": action, "scope_ref": scope_ref,
                                 "proposal_ref": grant["proposal_ref"],
                                 "operation_ref": operation_ref,
                                 "idempotency_key": idempotency_key,
                                 "generation": next_generation,
                                 "lease_expires_at": lease_expires_at.isoformat()})
            return {"reservation_id": str(reservation_id), "status":"reserved",
                    "lease_expires_at": lease_expires_at.isoformat(),
                    "result_ref": None, "reason_code": None,
                    "generation": next_generation}
        except (AuthorityDenied, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def consume_delegated_grant(self, grantee_token, reservation_id, result_ref):
        """Consume a reserved use after success; same result replay is idempotent."""
        if not result_ref or len(result_ref) > 512:
            raise ValueError("result_ref must be a bounded non-empty reference")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    grantee = self._authenticate(cur, grantee_token)
                    cur.execute("SELECT grant_id FROM delegated_grant_reservations WHERE reservation_id=%s",
                                (reservation_id,))
                    reference = cur.fetchone()
                    if reference is None:
                        raise AuthorityDenied("delegated reservation was not found")
                    cur.execute("""SELECT grant_id,principal_id,max_uses,used_count,revoked_at
                        FROM authority_grants WHERE grant_id=%s FOR UPDATE""", (reference["grant_id"],))
                    grant = cur.fetchone()
                    cur.execute("""SELECT * FROM delegated_grant_reservations
                        WHERE reservation_id=%s FOR UPDATE""", (reservation_id,))
                    reservation = cur.fetchone()
                    if reservation["grantee_id"] != grantee["principal_id"]:
                        raise AuthorityDenied("reservation belongs to another grantee")
                    if reservation["status"] == "consumed":
                        if reservation["result_ref"] != result_ref:
                            raise AuthorityDenied("consumed reservation replay changed result reference")
                        return {"reservation_id":str(reservation_id),"status":"consumed","result_ref":result_ref}
                    if reservation["status"] != "reserved":
                        return {"reservation_id":str(reservation_id),"status":reservation["status"],
                                "result_ref":reservation["result_ref"],"reason_code":reservation["reason_code"]}
                    if reservation["lease_expires_at"] <= datetime.now(timezone.utc) or grant["revoked_at"] is not None:
                        cur.execute("""UPDATE delegated_grant_reservations SET status='expired',updated_at=clock_timestamp()
                            WHERE reservation_id=%s""", (reservation_id,))
                        self._reservation_event(cur,event_type="authority_grant_reservation_expired",
                            actor_id=grantee["principal_id"],grant_id=grant["grant_id"],
                            reservation_id=reservation_id,payload={"cause":"lease_or_revocation"})
                        return {"reservation_id":str(reservation_id),"status":"expired"}
                    cur.execute("""UPDATE authority_grants SET used_count=used_count+1
                        WHERE grant_id=%s AND (max_uses IS NULL OR used_count<max_uses)
                        RETURNING used_count,max_uses""", (grant["grant_id"],))
                    usage = cur.fetchone()
                    if usage is None:
                        raise AuthorityDenied("delegated grant use limit is exhausted")
                    cur.execute("""UPDATE delegated_grant_reservations SET status='consumed',result_ref=%s,
                        updated_at=clock_timestamp() WHERE reservation_id=%s""", (result_ref,reservation_id))
                    self._reservation_event(cur,event_type="authority_grant_used",
                        actor_id=grantee["principal_id"],grant_id=grant["grant_id"],
                        reservation_id=reservation_id,
                        payload={"result_ref":result_ref,"used_count":usage["used_count"],
                                 "max_uses":usage["max_uses"],
                                 "operation_ref":reservation["operation_ref"],
                                 "idempotency_key":reservation["idempotency_key"],
                                 "generation":reservation["generation"]})
            return {"reservation_id":str(reservation_id),"status":"consumed","result_ref":result_ref}
        except (AuthorityDenied, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def release_delegated_grant(self, grantee_token, reservation_id, reason_code):
        """Release a failed operation's reservation; repeated same release is safe."""
        if not reason_code or len(reason_code) > 64:
            raise ValueError("reason_code must be a bounded non-empty code")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    grantee = self._authenticate(cur, grantee_token)
                    cur.execute("SELECT grant_id FROM delegated_grant_reservations WHERE reservation_id=%s",
                                (reservation_id,))
                    reference = cur.fetchone()
                    if reference is None:
                        raise AuthorityDenied("delegated reservation was not found")
                    cur.execute("SELECT grant_id FROM authority_grants WHERE grant_id=%s FOR UPDATE",
                                (reference["grant_id"],))
                    grant = cur.fetchone()
                    cur.execute("SELECT * FROM delegated_grant_reservations WHERE reservation_id=%s FOR UPDATE",
                                (reservation_id,))
                    reservation = cur.fetchone()
                    if reservation["grantee_id"] != grantee["principal_id"]:
                        raise AuthorityDenied("reservation belongs to another grantee")
                    if reservation["status"] == "released":
                        if reservation["reason_code"] != reason_code:
                            raise AuthorityDenied("release replay changed reason code")
                        return {"reservation_id":str(reservation_id),"status":"released","reason_code":reason_code}
                    if reservation["status"] != "reserved":
                        return {"reservation_id":str(reservation_id),"status":reservation["status"]}
                    cur.execute("""UPDATE delegated_grant_reservations SET status='released',reason_code=%s,
                        updated_at=clock_timestamp() WHERE reservation_id=%s""", (reason_code,reservation_id))
                    self._reservation_event(cur,event_type="authority_grant_reservation_released",
                        actor_id=grantee["principal_id"],grant_id=grant["grant_id"],
                        reservation_id=reservation_id,payload={"reason_code":reason_code})
            return {"reservation_id":str(reservation_id),"status":"released","reason_code":reason_code}
        except (AuthorityDenied, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def audit_expired_delegated_grants(self, steward_token):
        """Record expired delegated grants and reservation leases exactly once."""
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    actor = self._require(cur, steward_token, "authority.grant", "institution")
                    if actor["principal_kind"] != "steward":
                        raise AuthorityDenied("expiry audit requires an authenticated Steward")
                    cur.execute("""UPDATE authority_grants SET expired_audited_at=clock_timestamp()
                        WHERE grant_kind='delegated' AND revoked_at IS NULL
                          AND valid_until IS NOT NULL AND valid_until<=clock_timestamp()
                          AND expired_audited_at IS NULL
                        RETURNING grant_id,principal_id,action,scope_ref""")
                    expired = cur.fetchall()
                    for grant in expired:
                        self._event(cur,event_type="authority_grant_expired",actor_id=actor["principal_id"],
                            subject_id=grant["principal_id"],grant_id=grant["grant_id"],
                            payload={"action":grant["action"],"scope_ref":grant["scope_ref"]})
                    cur.execute("""UPDATE delegated_grant_reservations r
                        SET status='expired',updated_at=clock_timestamp()
                        FROM authority_grants g
                        WHERE r.grant_id=g.grant_id AND r.status='reserved'
                          AND (r.lease_expires_at<=clock_timestamp() OR
                               (g.valid_until IS NOT NULL AND g.valid_until<=clock_timestamp()))
                        RETURNING r.grant_id,r.reservation_id""")
                    reservations = cur.fetchall()
                    for reservation in reservations:
                        self._reservation_event(cur,event_type="authority_grant_reservation_expired",
                            actor_id=actor["principal_id"],grant_id=reservation["grant_id"],
                            reservation_id=reservation["reservation_id"],payload={"cause":"expiry_sweep"})
            return {"expired_grants":len(expired),"expired_reservations":len(reservations)}
        except AuthorityDenied:
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def surrender_delegated_grant(self, grantee_token, grant_id, *, reason_code="grantee_surrendered"):
        if not reason_code or len(reason_code) > 64:
            raise ValueError("reason_code must be a bounded non-empty code")
        try:
            with self.db.transaction():
                with self.db.cursor() as cur:
                    self._path(cur)
                    grantee = self._authenticate(cur, grantee_token)
                    cur.execute("""UPDATE authority_grants SET revoked_at=clock_timestamp()
                        WHERE grant_id=%s AND principal_id=%s AND grant_kind='delegated'
                          AND revoked_at IS NULL
                        RETURNING principal_id,action,scope_ref""",
                        (grant_id, grantee["principal_id"]))
                    grant = cur.fetchone()
                    if grant is None:
                        raise AuthorityDenied("only the authorized grantee may surrender an active delegated grant")
                    cur.execute("""UPDATE delegated_grant_reservations SET status='released',
                        reason_code='grant_surrendered',updated_at=clock_timestamp()
                        WHERE grant_id=%s AND status='reserved'
                        RETURNING reservation_id""",(grant_id,))
                    for reservation in cur.fetchall():
                        self._reservation_event(cur,event_type="authority_grant_reservation_released",
                            actor_id=grantee["principal_id"],grant_id=grant_id,
                            reservation_id=reservation["reservation_id"],
                            payload={"reason_code":"grant_surrendered"})
                    self._event(cur,event_type="authority_grant_surrendered",
                        actor_id=grantee["principal_id"],subject_id=grantee["principal_id"],
                        grant_id=grant_id,payload={"action":grant["action"],
                            "scope_ref":grant["scope_ref"],"reason_code":reason_code})
        except (AuthorityDenied, ValueError):
            raise
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None


    def issue_grace_autonomy_experiment_grant(self, *, actor_id, grant_id, scope_ref,
                                               valid_until):
        """Issue only the fixed Grace experiment grant for a transport-authenticated Steward."""
        self._validate_expiry(valid_until)
        if (not isinstance(actor_id, str) or not isinstance(grant_id, str) or
                not isinstance(scope_ref, str)):
            raise ValueError("experiment grant identity is invalid")
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                cur.execute("SELECT set_config('search_path', %s, true)", (self.schema,))
                cur.execute(psycopg.sql.SQL(
                    "SELECT {}.issue_grace_autonomy_experiment_grant(%s,%s,%s,%s)"
                ).format(psycopg.sql.Identifier(self.schema)),
                    (actor_id, grant_id, scope_ref, valid_until))
                row = cur.fetchone()
                if row is None:
                    raise AuthorityDenied("experiment authority was not issued")
                return row[0] if not hasattr(row, "values") else next(iter(row.values()))
        except (AuthorityDenied, ValueError):
            raise
        except psycopg.Error as exc:
            # Do not return SQL or connection details through the caller.
            if getattr(exc, "sqlstate", None) == "P0001":
                raise AuthorityDenied("authenticated Steward grant rejected") from None
            raise RegistryUnavailable(type(exc).__name__) from None
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None

    def active_grace_luna_escalation_grant(self):
        """Return only Grace's active Luna escalation grant through a fixed DB boundary."""
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                cur.execute("SELECT set_config('search_path', %s, true)", (self.schema,))
                cur.execute(psycopg.sql.SQL(
                    "SELECT {}.active_grace_luna_escalation_grant()"
                ).format(psycopg.sql.Identifier(self.schema)))
                row = cur.fetchone()
                grant_id = row[0] if row is not None and not hasattr(row, "values") else (
                    next(iter(row.values())) if row is not None else None)
                if not grant_id:
                    raise AuthorityDenied("Grace Luna escalation grant is not active")
                return {"principal_id": "resident:grace", "grant_id": grant_id}
        except AuthorityDenied:
            raise
        except psycopg.Error as exc:
            if getattr(exc, "sqlstate", None) == "P0001":
                raise AuthorityDenied("Grace Luna escalation grant is not active") from None
            raise RegistryUnavailable(type(exc).__name__) from None

    def issue_grace_supervisory_luna_grant(self, *, actor_id, grant_id, valid_until=None):
        """Issue the fixed supervisory Luna grant for ingress-attested Steward approval."""
        self._validate_expiry(valid_until)
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                cur.execute("SELECT set_config('search_path', %s, true)", (self.schema,))
                cur.execute(psycopg.sql.SQL(
                    "SELECT {}.issue_grace_supervisory_luna_grant(%s,%s,%s)"
                ).format(psycopg.sql.Identifier(self.schema)), (actor_id, grant_id, valid_until))
                row = cur.fetchone()
                if row is None:
                    raise AuthorityDenied("supervisory authority was not issued")
                return row[0] if not hasattr(row, "values") else next(iter(row.values()))
        except (AuthorityDenied, ValueError):
            raise
        except psycopg.Error as exc:
            if getattr(exc, "sqlstate", None) == "P0001":
                raise AuthorityDenied("authenticated Steward grant rejected") from None
            raise RegistryUnavailable(type(exc).__name__) from None
        except Exception as exc:
            raise RegistryUnavailable(type(exc).__name__) from None
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
