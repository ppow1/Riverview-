# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/grants.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Resolve exact credential/action/scope grants through the protected SQL function
# Execution Model: Request-driven query on the caller's active PostgreSQL transaction
# Observability: Safe allow/deny status and exact grant ID; no credential is logged
# Dependencies: Python 3.10+; Psycopg 3; migration 0002 and DBA-applied boundary
# Authority: Missing, invalid, unavailable, or ambiguous authority denies the operation
# Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT | Initial exact-grant runtime adapter
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_institutional_authority_boundary.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Narrow runtime access to the database-enforced exact-grant decision."""

import hashlib
import re

import psycopg
from psycopg import sql


_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")


class GrantDenied(RuntimeError):
    """No active credential has the exact requested action and scope."""


class GrantCheckUnavailable(RuntimeError):
    """The protected registry did not produce a trustworthy answer."""


class ExactGrantAuthorizer:
    """Call only the owner-controlled authorization function on an existing cursor."""

    FUNCTION = "authorize_exact_grant"

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
        return {"principal_id": principal_id, "grant_id": grant_id}
