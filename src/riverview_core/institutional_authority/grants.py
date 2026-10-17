# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/grants.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.4
# Purpose: Resolve exact grants and apply an active resident profile as an additional policy gate
# Execution Model: Request-driven query on the caller's active PostgreSQL transaction
# Observability: Safe allow/deny status and exact grant ID; no credential is logged
# Dependencies: Python 3.10+; Psycopg 3; migration 0002 and DBA-applied boundary
# Authority: Missing, invalid, unavailable, or ambiguous authority denies the operation
# Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Authorize linked authenticated principals through exact grants
# Changed: 2026-10-14 UTC | RV-RESIDENT-PERMISSIONS-001 | Enforce active resident profile policy after exact grant
# Changed: 2026-10-15 UTC | RV-AUTH-LEGACY-PROFILE-COMPAT | Preserve exact-grant authorization before migration 0008 without weakening installed profile enforcement
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_institutional_authority_boundary.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Narrow runtime access to the database-enforced exact-grant decision."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

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
        """Apply profiles when fully installed; legacy schemas retain exact grants."""
        if not self._profile_registry_installed(cursor):
            # Migration 0008 is additive and transactional. Older authority schemas
            # have neither profile object; exact grants remain their complete policy.
            return
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
            try:
                decision = json.loads(decision)
            except (TypeError, ValueError):
                raise GrantCheckUnavailable("resident permission profile returned malformed data") from None
        if not isinstance(decision, dict) or type(decision.get("allowed")) is not bool:
            raise GrantCheckUnavailable("resident permission profile returned malformed data")
        if decision.get("allowed") is not True:
            raise GrantDenied("resident permission profile denied the exact grant action")
        if decision.get("mode") == "legacy_exact_grant_only":
            if decision.get("profile_revision") is not None or "approval_required" in decision:
                raise GrantCheckUnavailable("resident permission profile returned inconsistent legacy data")
            return
        if type(decision.get("approval_required")) is not bool:
            raise GrantCheckUnavailable("resident permission profile returned malformed approval data")
        if decision["approval_required"]:
            raise GrantDenied("resident permission profile requires a separate approval")

    def _profile_registry_installed(self, cursor):
        """Detect migration 0008 by paired runtime objects, without ledger access.

        The deployed runtime is deliberately denied SELECT on schema_migrations,
        so catalog capability discovery is required. A partial pair, wrong
        relation/function shape, or visible contradictory ledger record fails
        closed.
        """
        relation = f"{self.schema}.resident_permission_profiles"
        signature = (f"{self.schema}.{self.PROFILE_FUNCTION}"
                     "(text,text,text,text,text,boolean)")
        try:
            cursor.execute(
                "SELECT (SELECT relkind FROM pg_catalog.pg_class "
                "WHERE oid=pg_catalog.to_regclass(%s)) AS relation_kind, "
                "pg_catalog.to_regprocedure(%s) IS NOT NULL AS exact_function, "
                "(SELECT count(*) FROM pg_catalog.pg_proc p "
                "JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace "
                "WHERE n.nspname=%s AND p.proname=%s) AS function_count",
                (relation, signature, self.schema, self.PROFILE_FUNCTION),
            )
            row = cursor.fetchone()
        except psycopg.Error:
            raise GrantCheckUnavailable("resident permission capability check failed") from None
        if row is None:
            raise GrantCheckUnavailable("resident permission capability check returned no state")
        if hasattr(row, "keys"):
            relation_kind = row["relation_kind"]
            exact_function = row["exact_function"]
            function_count = row["function_count"]
        else:
            relation_kind, exact_function, function_count = row

        if relation_kind is None and function_count == 0 and exact_function is False:
            installed = False
        elif relation_kind in ("r", "p") and function_count == 1 and exact_function is True:
            installed = True
        else:
            raise GrantCheckUnavailable("resident permission migration is partial or inconsistent")

        # If the role already has ledger read access, detect recorded-but-missing
        # migration objects and visible migration checksum drift. No access is
        # granted here; deployed runtime roles continue to have no ledger SELECT.
        try:
            cursor.execute(
                "SELECT pg_catalog.has_table_privilege(current_user,%s,'SELECT')",
                (f"{self.schema}.schema_migrations",),
            )
            privilege_row = cursor.fetchone()
            if privilege_row is None:
                raise GrantCheckUnavailable("authority migration visibility check returned no state")
            can_read_ledger = (privilege_row[0] if not hasattr(privilege_row, "keys")
                               else next(iter(privilege_row.values())))
            if can_read_ledger:
                query = sql.SQL(
                    "SELECT checksum FROM {}.schema_migrations WHERE version=%s"
                ).format(sql.Identifier(self.schema))
                cursor.execute(query, ("0008_resident_permission_profiles",))
                ledger_row = cursor.fetchone()
                ledger_present = ledger_row is not None
                if ledger_present != installed:
                    raise GrantCheckUnavailable("resident permission migration ledger disagrees with runtime objects")
                if ledger_present:
                    migration_path = (Path(__file__).with_name("migrations") /
                                      "0008_resident_permission_profiles.sql")
                    try:
                        expected_checksum = hashlib.sha256(migration_path.read_bytes()).hexdigest()
                    except OSError:
                        raise GrantCheckUnavailable("resident permission migration source unavailable") from None
                    checksum = (ledger_row[0] if not hasattr(ledger_row, "keys")
                                else next(iter(ledger_row.values())))
                    if checksum != expected_checksum:
                        raise GrantCheckUnavailable("resident permission migration checksum mismatch")
        except GrantCheckUnavailable:
            raise
        except psycopg.Error:
            raise GrantCheckUnavailable("authority migration consistency check failed") from None
        return installed


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
