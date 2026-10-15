# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_authorizer_profile_legacy_compatibility.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.1
# Purpose: Verify exact-grant behavior before and after migration 0008
# Execution Model: Disposable PostgreSQL schema and restricted runtime principal
# Observability: Authorization allow/deny and fail-closed migration state
# Dependencies: PostgreSQL test DSN; Riverview authority migrations 0000-0008
# Authority: Uses only uniquely named test schemas and roles; never production
# Changed: 2026-10-15 UTC | RV-AUTH-LEGACY-PROFILE-COMPAT | Add unexpected catalog database failure regression
# History: New file
# =============================================================================
"""PostgreSQL coverage for legacy exact grants and resident-profile gating."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from uuid import uuid4

from psycopg import sql
from psycopg.rows import dict_row

from riverview_core.institutional_authority.grants import (
    ExactGrantAuthorizer,
    GrantCheckUnavailable,
    GrantDenied,
)


DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
MIGRATIONS = (Path(__file__).resolve().parents[1]
              / "src/riverview_core/institutional_authority/migrations")


class ProfileDecisionValidationTests(unittest.TestCase):
    def test_malformed_profile_decision_fails_closed(self):
        class Cursor:
            def __init__(self):
                self.rows = iter((
                    ("resident:test", "grant:test"),
                    ("r", True, 1),
                    (False,),
                    ("not-json",),
                ))

            def execute(self, *_args):
                return None

            def fetchone(self):
                return next(self.rows)

        with self.assertRaises(GrantCheckUnavailable):
            ExactGrantAuthorizer("authority_test").require(
                Cursor(), "a" * 32, "assignment.execute", "work-order:test")

    def test_unexpected_database_error_during_capability_check_fails_closed(self):
        import psycopg

        class Cursor:
            def __init__(self):
                self.calls = 0

            def execute(self, *_args):
                self.calls += 1
                if self.calls == 2:
                    raise psycopg.OperationalError("synthetic catalog failure")

            def fetchone(self):
                return {"principal_id": "resident:test", "grant_id": "grant:test"}

        with self.assertRaises(GrantCheckUnavailable):
            ExactGrantAuthorizer("authority_test").require(
                Cursor(), "a" * 32, "assignment.execute", "work-order:test")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class ExactGrantProfileCompatibilityPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg.conninfo import make_conninfo
        from riverview_core.postgres_migrations import apply_migrations

        self.psycopg = psycopg
        self.apply_migrations = apply_migrations
        self.schema = "rvgrantcompat_" + uuid4().hex
        self.runtime_role = "rvgrantcompat_" + uuid4().hex[:20]
        self.runtime_password = uuid4().hex + uuid4().hex
        self.token = uuid4().hex + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.runtime_dsn = make_conninfo(
            DSN, user=self.runtime_role, password=self.runtime_password)
        self.admin.execute(sql.SQL(
            "CREATE ROLE {} LOGIN NOINHERIT PASSWORD {} NOSUPERUSER NOCREATEDB "
            "NOCREATEROLE NOBYPASSRLS"
        ).format(sql.Identifier(self.runtime_role), sql.Literal(self.runtime_password)))
        self.admin.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION CURRENT_USER").format(
            sql.Identifier(self.schema)))
        self._apply_without_profile_migration()
        self._seed_identity_and_exact_grant()
        self._grant_runtime_functions(profile=False)

    def tearDown(self):
        try:
            self.admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                sql.Identifier(self.schema)))
            self.admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(
                sql.Identifier(self.runtime_role)))
        finally:
            self.admin.close()

    def _apply_without_profile_migration(self):
        with tempfile.TemporaryDirectory(prefix="rv-authority-0007-") as temp:
            target = Path(temp)
            for path in MIGRATIONS.glob("*.sql"):
                if path.name.startswith("0008_"):
                    continue
                shutil.copyfile(path, target / path.name)
            self.apply_migrations(DSN, schema=self.schema, migrations_dir=target)

    def _apply_profile_migration(self):
        with tempfile.TemporaryDirectory(prefix="rv-authority-0008-") as temp:
            shutil.copyfile(
                MIGRATIONS / "0008_resident_permission_profiles.sql",
                Path(temp) / "0008_resident_permission_profiles.sql")
            self.apply_migrations(DSN, schema=self.schema, migrations_dir=temp)
        self._grant_runtime_functions(profile=True)

    def _seed_identity_and_exact_grant(self):
        schema = sql.Identifier(self.schema)
        self.admin.execute(sql.SQL(
            "INSERT INTO {}.institutional_offices(office_id,office_role) "
            "VALUES ('office:compat-test','resident test')"
        ).format(schema))
        self.admin.execute(sql.SQL(
            "INSERT INTO {}.institutional_principals(principal_id,principal_kind,office_id) "
            "VALUES ('resident:compat-test','resident','office:compat-test'), "
            "('steward:compat-test','steward',NULL)"
        ).format(schema))
        self.admin.execute(sql.SQL(
            "INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256) "
            "VALUES (%s,'resident:compat-test',%s)"
        ).format(schema), (uuid4(), hashlib.sha256(self.token.encode()).digest()))
        self.admin.execute(sql.SQL(
            "INSERT INTO {}.authority_grants "
            "(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) "
            "VALUES ('compat-exact-grant','resident:compat-test','assignment.execute',"
            "'work-order:engineering','steward:compat-test','rv.policy:compat-test')"
        ).format(schema))

    def _grant_runtime_functions(self, *, profile):
        schema = sql.Identifier(self.schema)
        self.admin.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
            schema, sql.Identifier(self.runtime_role)))
        for function, signature in (
                ("authorize_exact_grant", "bytea,text,text"),
                ("authorize_exact_principal_grant", "text,text,text")):
            self.admin.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {}.{}({}) TO {}").format(
                schema, sql.Identifier(function), sql.SQL(signature),
                sql.Identifier(self.runtime_role)))
        if profile:
            self.admin.execute(sql.SQL(
                "GRANT EXECUTE ON FUNCTION {}.evaluate_resident_permission "
                "(text,text,text,text,text,boolean) TO {}"
            ).format(schema, sql.Identifier(self.runtime_role)))

    def _authorized(self, action="assignment.execute", scope="work-order:engineering"):
        authorizer = ExactGrantAuthorizer(self.schema)
        with self.psycopg.connect(self.runtime_dsn, row_factory=dict_row) as runtime:
            with runtime.cursor() as cursor:
                return authorizer.require(cursor, self.token, action, scope)

    def _seed_profile_catalog(self, effect="allow", *, expires_sql=None, revoked=False):
        schema = sql.Identifier(self.schema)
        self.admin.execute(sql.SQL(
            "INSERT INTO {}.resident_permission_profiles "
            "(principal_id,office_id,tier_id,status,revision,classification_ceiling,export_mode,"
            "created_by,approved_by,approved_at) VALUES "
            "('resident:compat-test','office:compat-test','observer','active',1,'restricted','deny',"
            "'steward:compat-test','steward:compat-test',clock_timestamp())"
        ).format(schema))
        expiry = sql.SQL("NULL") if expires_sql is None else sql.SQL(expires_sql)
        revoked_at = sql.SQL("clock_timestamp()") if revoked else sql.SQL("NULL")
        self.admin.execute(sql.SQL(
            "INSERT INTO {}.resident_permission_rules "
            "(rule_id,principal_id,capability_id,resource_id,effect,access_level,approval_required,"
            "data_classification,export_mode,provenance_ref,valid_until,revoked_at) VALUES "
            "(%s,'resident:compat-test','engineering.assignment.execute','work-order:engineering',%s,'execute',false,"
            "'internal','deny','test:steward-review',{},{})"
        ).format(schema, expiry, revoked_at), (uuid4(), effect))

    def test_exact_grant_allows_when_migration_0008_is_absent_and_runtime_cannot_read_ledger(self):
        with self.psycopg.connect(self.runtime_dsn, autocommit=True) as runtime:
            self.assertFalse(runtime.execute(
                "SELECT has_table_privilege(current_user,%s,'SELECT')",
                (f"{self.schema}.schema_migrations",)).fetchone()[0])
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                runtime.execute(sql.SQL("SELECT count(*) FROM {}.schema_migrations").format(
                    sql.Identifier(self.schema))).fetchone()
        self.assertEqual(self._authorized()["grant_id"], "compat-exact-grant")

    def test_missing_exact_grant_still_denies_when_migration_0008_is_absent(self):
        with self.assertRaises(GrantDenied):
            self._authorized(action="assignment.verify")

    def test_migration_0008_without_active_profile_preserves_legacy_exact_grant(self):
        self._apply_profile_migration()
        self.assertEqual(self._authorized()["grant_id"], "compat-exact-grant")

    def test_active_profile_allow_adds_to_exact_grant(self):
        self._apply_profile_migration()
        self._seed_profile_catalog("allow")
        self.assertEqual(self._authorized()["grant_id"], "compat-exact-grant")

    def test_active_profile_deny_rejects_an_otherwise_valid_exact_grant(self):
        self._apply_profile_migration()
        self._seed_profile_catalog("deny")
        with self.assertRaises(GrantDenied):
            self._authorized()

    def test_expired_and_revoked_exact_grants_are_denied(self):
        schema = sql.Identifier(self.schema)
        self.admin.execute(sql.SQL(
            "UPDATE {}.authority_grants SET valid_from=clock_timestamp()-interval '2 seconds', "
            "valid_until=clock_timestamp()-interval '1 second' "
            "WHERE grant_id='compat-exact-grant'"
        ).format(schema))
        with self.assertRaises(GrantDenied):
            self._authorized()
        self.admin.execute(sql.SQL(
            "UPDATE {}.authority_grants SET valid_until=NULL,valid_from=clock_timestamp(), "
            "revoked_at=clock_timestamp() "
            "WHERE grant_id='compat-exact-grant'"
        ).format(schema))
        with self.assertRaises(GrantDenied):
            self._authorized()

    def test_expired_or_revoked_profile_rule_denies(self):
        self._apply_profile_migration()
        self._seed_profile_catalog("allow", expires_sql="clock_timestamp()-interval '1 second'")
        with self.assertRaises(GrantDenied):
            self._authorized()
        schema = sql.Identifier(self.schema)
        self.admin.execute(sql.SQL(
            "UPDATE {}.resident_permission_rules SET valid_until=NULL,revoked_at=clock_timestamp()"
        ).format(schema))
        with self.assertRaises(GrantDenied):
            self._authorized()

    def test_profile_table_without_evaluator_is_rejected_as_partial_migration(self):
        self.admin.execute(sql.SQL(
            "CREATE TABLE {}.resident_permission_profiles(principal_id text)"
        ).format(sql.Identifier(self.schema)))
        with self.assertRaises(GrantCheckUnavailable):
            self._authorized()

    def test_evaluator_without_profile_table_is_rejected_as_partial_migration(self):
        self.admin.execute(sql.SQL(
            "CREATE FUNCTION {}.evaluate_resident_permission(text,text,text,text,text,boolean) "
            "RETURNS jsonb LANGUAGE sql AS 'SELECT ''{{}}''::jsonb'"
        ).format(sql.Identifier(self.schema)))
        with self.assertRaises(GrantCheckUnavailable):
            self._authorized()

    def test_visible_ledger_mismatch_is_rejected(self):
        schema = sql.Identifier(self.schema)
        self.admin.execute(sql.SQL(
            "INSERT INTO {}.schema_migrations(version,checksum) VALUES "
            "('0008_resident_permission_profiles',repeat('0',64))"
        ).format(schema))
        self.admin.execute(sql.SQL("GRANT SELECT ON {}.schema_migrations TO {}").format(
            schema, sql.Identifier(self.runtime_role)))
        with self.assertRaises(GrantCheckUnavailable):
            self._authorized()

    def test_profile_function_database_error_fails_closed(self):
        self._apply_profile_migration()
        schema = sql.Identifier(self.schema)
        self.admin.execute(sql.SQL(
            "REVOKE EXECUTE ON FUNCTION {}.evaluate_resident_permission "
            "(text,text,text,text,text,boolean) FROM {}"
        ).format(schema, sql.Identifier(self.runtime_role)))
        with self.assertRaises(GrantCheckUnavailable):
            self._authorized()


if __name__ == "__main__":
    unittest.main()
