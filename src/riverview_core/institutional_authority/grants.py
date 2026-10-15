# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/grants.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.3
# Purpose: Resolve exact grants and apply an active resident profile as an additional policy gate
# Execution Model: Request-driven query on the caller's active PostgreSQL transaction
# Observability: Safe allow/deny status and exact grant ID; no credential is logged
# Dependencies: Python 3.10+; Psycopg 3; migration 0002 and DBA-applied boundary
# Authority: Missing, invalid, unavailable, or ambiguous authority denies the operation
# Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Authorize linked authenticated principals through exact grants
# Changed: 2026-10-14 UTC | RV-RESIDENT-PERMISSIONS-001 | Enforce active resident profile policy after exact grant
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_institutional_authority_boundary.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Narrow runtime access to the database-enforced exact-grant decision."""

import hashlib
import re
from dataclasses import dataclass

import psycopg
from psycopg import sql


_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")


@dataclass(frozen=True)
class InstitutionalPrincipal:
    """A principal identity established by another authenticated Riverview subsystem."""

    principal_id: str


class GrantDenied(RuntimeError):
    """No active credential has the exact requested action and scope."""


class GrantCheckUnavailable(RuntimeError):
    """The protected registry did not produce a trustworthy answer."""


class ExactGrantAuthorizer:
    """Call only the owner-controlled authorization function on an existing cursor."""

    FUNCTION = "authorize_exact_grant"
    PRINCIPAL_FUNCTION = "authorize_exact_principal_grant"
    PROFILE_FUNCTION = "evaluate_resident_permission"

    def __init__(self, schema):
        if not isinstance(schema, str) or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid authority schema")
        self.schema = schema

    def require(self, cursor, credential, action, scope_ref):
        if (not isinstance(credential, str) or len(credential) < 32
                or not isinstance(action, str) or not action
                or not isinstance(scope_ref, str) or not scope_ref):
            raise GrantDenied("credential, action, and exact scope are required")
        digest = hashlib.sha256(credential.encode("utf-8")).digest()
        query = sql.SQL(
            "SELECT principal_id,grant_id FROM {}.{}(%s,%s,%s)"
        ).format(sql.Identifier(self.schema), sql.Identifier(self.FUNCTION))
        try:
            cursor.execute(query, (digest, action, scope_ref))
            row = cursor.fetchone()
        except psycopg.Error:
            raise GrantCheckUnavailable("protected authority query failed") from None
        if row is None:
            raise GrantDenied("no active exact-scope grant")
        try:
            principal_id = row["principal_id"]
            grant_id = row["grant_id"]
        except (KeyError, TypeError):
            principal_id, grant_id = row[0], row[1]
        self._require_profile_policy(cursor, principal_id, action, scope_ref)
        return {"principal_id": principal_id, "grant_id": grant_id}

    def require_principal(self, cursor, principal_id, action, scope_ref):
        """Check grants for a principal already authenticated by a linked subsystem.

        This does not authenticate the principal. Callers must only supply an identity
        obtained from a current, server-validated account session.
        """
        if (not isinstance(principal_id, str) or not principal_id or len(principal_id) > 256
                or not isinstance(action, str) or not action
                or not isinstance(scope_ref, str) or not scope_ref):
            raise GrantDenied("principal, action, and exact scope are required")
        query = sql.SQL("SELECT principal_id,grant_id FROM {}.{}(%s,%s,%s)").format(
            sql.Identifier(self.schema), sql.Identifier(self.PRINCIPAL_FUNCTION))
        try:
            cursor.execute(query, (principal_id, action, scope_ref))
            row = cursor.fetchone()
        except psycopg.Error:
            raise GrantCheckUnavailable("protected authority query failed") from None
        if row is None:
            raise GrantDenied("no active exact-scope grant")
        try:
            authorized_principal, grant_id = row["principal_id"], row["grant_id"]
        except (KeyError, TypeError):
            authorized_principal, grant_id = row[0], row[1]
        self._require_profile_policy(cursor, authorized_principal, action, scope_ref)
        return {"principal_id": authorized_principal, "grant_id": grant_id}

    def _require_profile_policy(self, cursor, principal_id, action, scope_ref):
        """An active resident profile can narrow, never replace, an exact grant."""
        level = _access_level(action)
        query = sql.SQL("SELECT {}.{}(%s,%s,%s,%s,%s,%s)").format(
            sql.Identifier(self.schema), sql.Identifier(self.PROFILE_FUNCTION))
        try:
            cursor.execute(query, (principal_id, action, scope_ref, level,
                                   "internal", False))
            row = cursor.fetchone()
        except psycopg.Error:
            raise GrantCheckUnavailable("resident permission profile query failed") from None
        if row is None:
            raise GrantCheckUnavailable("resident permission profile returned no decision")
        decision = row[0] if not hasattr(row, "keys") else next(iter(row.values()))
        if isinstance(decision, str):
            import json
            decision = json.loads(decision)
        if not isinstance(decision, dict) or decision.get("allowed") is not True:
            raise GrantDenied("resident permission profile denied the exact grant action")
        if decision.get("approval_required"):
            raise GrantDenied("resident permission profile requires a separate approval")


def _access_level(action):
    """Map institutional action verbs to a minimum profile access level."""
    lowered = action.lower()
    if lowered.endswith((".read", ".view", ".inspect", ".status")):
        return "read"
    if lowered.endswith((".manage", ".administer")):
        return "administer"
    if lowered.endswith((".delegate", ".grant")):
        return "delegate"
    if lowered.endswith((".write", ".submit", ".create", ".update", ".cancel")):
        return "write"
    return "execute"
