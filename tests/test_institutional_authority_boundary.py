# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_institutional_authority_boundary.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.10
# Purpose: Verify isolated M4.1 ownership separation denies runtime SQL bypass
# Execution Model: PostgreSQL integration test using unique rvtest schema and roles
# Observability: Protected object owners, runtime denial, manager registry authorization
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL superuser test database; Psycopg 3
# Authority: Disposable schema and random LOGIN roles only; never shared schema
# Changed: 2026-10-11 UTC | RV-M4.1-DB-BOUNDARY | Verify registry manager/runtime table isolation
# Changed: 2026-10-11 UTC | RV-M4.1-BOUNDARY-TESTS | Model distinct schema owner and reject runtime schema ownership
# Changed: 2026-10-11 UTC | RV-M4.1-BOUNDARY-TEST-FIX | Keep fixture schema owner distinct during baseline preflight
# Changed: 2026-10-11 UTC | RV-M4.1-BOUNDARY-TEST-FIX | Avoid Psycopg placeholder collision in catalog assertion
# Changed: 2026-10-11 UTC | RV-M4.1-SCHEMA-OWNER-PROOF | Reproduce schema-owner DROP bypass in disposable schema
# Changed: 2026-10-11 UTC | RV-M4.1-SCHEMA-OWNER-PROOF-FIX | Regrant fixture schema usage after owner transition and use dict result key
# Changed: 2026-10-11 UTC | RV-M4.1-SCHEMA-OWNER-PROOF-ORDER | Verify transferred owners before isolated DROP-CASCADE experiment
# Changed: 2026-10-11 UTC | RV-M4.1-LEAST-PRIVILEGE | Verify isolated authority schema, scoped manager DML, and no owner/DDL inheritance
# Changed: 2026-10-11 UTC | RV-M4.1-ROLE-SCOPE-REVIEW-FIX | Correct fixture ledger setup for the dedicated authority schema
# Changed: 2026-10-11 UTC | RV-M4.1-NOINHERIT-MANAGER-TEST | Model a NOINHERIT manager login in the boundary fixture
# Changed: 2026-10-11 UTC | RV-M4.1-DEDICATED-SCHEMA-FUNCTION-TEST | Reject unrelated schema functions before privilege changes
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Isolated PostgreSQL tests for the database-enforced authority table boundary."""

import hashlib
import os
import secrets
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class InstitutionalAuthorityBoundaryTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row
        from riverview_core.postgres_migrations import apply_migrations

        self.psycopg = psycopg
        self.sql = sql
        self.make_conninfo = make_conninfo
        self.schema = "rvtest_" + uuid4().hex
        self.owner_role = "rvtest_owner_" + uuid4().hex[:20]
        self.runtime_role = "rvtest_runtime_" + uuid4().hex[:20]
        self.manager_role = "rvtest_manager_" + uuid4().hex[:20]
        self.runtime_password = secrets.token_urlsafe(32)
        self.manager_password = secrets.token_urlsafe(32)
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.registry = None
        try:
            identity = self.admin.execute(
                "SELECT r.rolsuper FROM pg_roles r WHERE r.rolname=current_user").fetchone()
            if not identity or not identity["rolsuper"]:
                self.skipTest("isolated test DSN needs CREATE ROLE authority for role-boundary test")
            self.admin.execute(sql.SQL(
                "CREATE ROLE {} LOGIN NOINHERIT PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
            ).format(sql.Identifier(self.runtime_role), sql.Literal(self.runtime_password)))
            self.admin.execute(sql.SQL(
                "CREATE ROLE {} LOGIN NOINHERIT PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
            ).format(sql.Identifier(self.manager_role), sql.Literal(self.manager_password)))
            self.admin.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION CURRENT_USER").format(
                sql.Identifier(self.schema)))
            self.admin.execute(sql.SQL("""CREATE TABLE {}.schema_migrations(
            version text PRIMARY KEY, checksum text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT clock_timestamp())""").format(
                sql.Identifier(self.schema)))
            migration_dir = (__import__("pathlib").Path(__file__).resolve().parents[1]
                             / "src/riverview_core/institutional_authority/migrations")
            apply_migrations(DSN, schema=self.schema, migrations_dir=migration_dir)
            self.steward_token = secrets.token_urlsafe(32)
            self.worker_token = secrets.token_urlsafe(32)
            with self.admin.transaction():
                self.admin.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,'steward')").format(sql.Identifier(self.schema)),
                                   ("steward:boundary-test",))
                self.admin.execute(sql.SQL("INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)").format(sql.Identifier(self.schema)),
                                   (uuid4(), "steward:boundary-test", hashlib.sha256(self.steward_token.encode()).digest()))
                self.admin.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,'worker')").format(sql.Identifier(self.schema)),
                                   ("worker:boundary-test",))
                self.admin.execute(sql.SQL("INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)").format(sql.Identifier(self.schema)),
                                   (uuid4(), "worker:boundary-test", hashlib.sha256(self.worker_token.encode()).digest()))
                self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
                    (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                    VALUES ('boundary-test-grant','worker:boundary-test','assignment.execute',
                            'assignment:boundary-test','steward:boundary-test','rv.policy:test.v1')""").format(
                                sql.Identifier(self.schema)))
            self.manager_dsn = make_conninfo(
                DSN, user=self.manager_role, password=self.manager_password)
            self.runtime_dsn = make_conninfo(
                DSN, user=self.runtime_role, password=self.runtime_password)
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        if getattr(self, "registry", None) is not None:
            self.registry.close()
            self.registry = None
        if getattr(self, "admin", None) is not None:
            for schema_attr in ("schema",):
                name = getattr(self, schema_attr, None)
                if name:
                    self.admin.execute(self.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        self.sql.Identifier(name)))
            for role_attr in ("manager_role", "runtime_role", "owner_role"):
                name = getattr(self, role_attr, None)
                if name:
                    self.admin.execute(self.sql.SQL("DROP ROLE IF EXISTS {}").format(
                        self.sql.Identifier(name)))
            self.admin.close()

    def test_runtime_cannot_read_or_mutate_authority_tables_and_schema_owner_is_distinct(self):
        from psycopg.errors import InsufficientPrivilege
        from riverview_core.institutional_authority.db_boundary import (
            BoundaryPreflightError, provision_authority_boundary)

        # The authority registry gets a dedicated schema. Reject a target that
        # contains unrelated application objects before any privilege changes.
        self.admin.execute(self.sql.SQL("CREATE TABLE {}.unrelated_probe(id integer)").format(
            self.sql.Identifier(self.schema)))
        with self.assertRaisesRegex(BoundaryPreflightError, "non-authority objects"):
            provision_authority_boundary(
                self.admin, schema=self.schema, runtime_role=self.runtime_role,
                manager_role=self.manager_role, owner_role=self.owner_role, apply=False)
        self.admin.execute(self.sql.SQL("DROP TABLE {}.unrelated_probe").format(
            self.sql.Identifier(self.schema)))
        self.admin.execute(self.sql.SQL(
            "CREATE FUNCTION {}.unrelated_probe() RETURNS integer LANGUAGE SQL AS 'SELECT 1'"
        ).format(self.sql.Identifier(self.schema)))
        with self.assertRaisesRegex(BoundaryPreflightError, "non-authority functions"):
            provision_authority_boundary(
                self.admin, schema=self.schema, runtime_role=self.runtime_role,
                manager_role=self.manager_role, owner_role=self.owner_role, apply=False)
        self.admin.execute(self.sql.SQL("DROP FUNCTION {}.unrelated_probe()").format(
            self.sql.Identifier(self.schema)))

        self.admin.execute(self.sql.SQL("GRANT USAGE,CREATE ON SCHEMA {} TO {}").format(
            self.sql.Identifier(self.schema), self.sql.Identifier(self.runtime_role)))
        preview = provision_authority_boundary(
            self.admin, schema=self.schema, runtime_role=self.runtime_role,
            manager_role=self.manager_role, owner_role=self.owner_role, apply=False)
        self.assertEqual(preview["status"], "PREFLIGHT_PASS")
        self.assertTrue(preview["apply_required"])
        applied = provision_authority_boundary(
            self.admin, schema=self.schema, runtime_role=self.runtime_role,
            manager_role=self.manager_role, owner_role=self.owner_role, apply=True)
        self.assertEqual(applied["status"], "APPLIED")
        self.assertEqual(len(applied["authority_tables"]), 9)

        # Repeated application must be safe and report the protected state.
        repeated = provision_authority_boundary(
            self.admin, schema=self.schema, runtime_role=self.runtime_role,
            manager_role=self.manager_role, owner_role=self.owner_role, apply=True)
        self.assertEqual(repeated["status"], "APPLIED")

        with self.admin.cursor() as cur:
            cur.execute("""SELECT pg_has_role(%s,%s,'MEMBER') AS manager_is_owner,
                                  has_schema_privilege(%s,%s,'USAGE') AS runtime_usage,
                                  has_schema_privilege(%s,%s,'CREATE') AS runtime_create,
                                  has_schema_privilege(%s,%s,'USAGE') AS manager_usage,
                                  has_schema_privilege(%s,%s,'CREATE') AS manager_create""",
                        (self.manager_role, self.owner_role,
                         self.runtime_role, self.schema, self.runtime_role, self.schema,
                         self.manager_role, self.schema, self.manager_role, self.schema))
            access = cur.fetchone()
        self.assertFalse(access["manager_is_owner"])
        self.assertFalse(access["runtime_usage"])
        self.assertFalse(access["runtime_create"])
        self.assertTrue(access["manager_usage"])
        self.assertFalse(access["manager_create"])
        self.admin.execute(self.sql.SQL("GRANT {} TO {}").format(
            self.sql.Identifier(self.owner_role), self.sql.Identifier(self.manager_role)))
        with self.assertRaisesRegex(BoundaryPreflightError, "manager role can assume"):
            provision_authority_boundary(
                self.admin, schema=self.schema, runtime_role=self.runtime_role,
                manager_role=self.manager_role, owner_role=self.owner_role, apply=False)
        self.admin.execute(self.sql.SQL("REVOKE {} FROM {}").format(
            self.sql.Identifier(self.owner_role), self.sql.Identifier(self.manager_role)))

        self.admin.execute(self.sql.SQL("ALTER SCHEMA {} OWNER TO {}").format(
            self.sql.Identifier(self.schema), self.sql.Identifier(self.runtime_role)))
        with self.assertRaisesRegex(BoundaryPreflightError, "must not own"):
            provision_authority_boundary(
                self.admin, schema=self.schema, runtime_role=self.runtime_role,
                manager_role=self.manager_role, owner_role=self.owner_role, apply=False)
        self.admin.execute(self.sql.SQL("ALTER SCHEMA {} OWNER TO CURRENT_USER").format(
            self.sql.Identifier(self.schema)))
        self.admin.execute(self.sql.SQL("GRANT USAGE,CREATE ON SCHEMA {} TO {}").format(
            self.sql.Identifier(self.schema), self.sql.Identifier(self.runtime_role)))

        with self.psycopg.connect(self.runtime_dsn) as runtime:
            with self.assertRaises(InsufficientPrivilege):
                runtime.execute(self.sql.SQL("SELECT count(*) FROM {}.institutional_principals").format(
                    self.sql.Identifier(self.schema))).fetchone()
        with self.psycopg.connect(self.runtime_dsn) as runtime:
            with self.assertRaises(InsufficientPrivilege):
                runtime.execute(self.sql.SQL("""INSERT INTO {}.institutional_authority_events
                    (event_id,event_type,actor_id) VALUES (%s,'principal_created','worker:boundary-test')""").format(
                        self.sql.Identifier(self.schema)), (uuid4(),))
        with self.psycopg.connect(self.runtime_dsn) as runtime:
            with self.assertRaises(InsufficientPrivilege):
                runtime.execute(self.sql.SQL("DROP TABLE {}.authority_grants").format(
                    self.sql.Identifier(self.schema)))
        with self.psycopg.connect(self.manager_dsn) as manager:
            manager.execute("SELECT count(*) FROM {}.institutional_principals".format(self.schema)).fetchone()
            with self.assertRaises(InsufficientPrivilege):
                manager.execute(self.sql.SQL("DROP TABLE {}.authority_grants").format(
                    self.sql.Identifier(self.schema)))

        from riverview_core.institutional_authority import AuthorityRegistry
        self.registry = AuthorityRegistry(self.manager_dsn, schema=self.schema)
        decision = self.registry.authorize(
            self.worker_token, "assignment.execute", "assignment:boundary-test")
        self.assertEqual(decision["principal_id"], "worker:boundary-test")
        self.assertEqual(decision["scope_ref"], "assignment:boundary-test")

        owners = self.admin.execute("""SELECT tablename,tableowner FROM pg_tables
            WHERE schemaname=%s AND tablename=ANY(%s)""",
                                   (self.schema, list(__import__(
                                       "riverview_core.institutional_authority.db_boundary",
                                       fromlist=["AUTHORITY_TABLES"]).AUTHORITY_TABLES))).fetchall()
        self.assertEqual(len(owners), 9)
        self.assertTrue(all(row["tableowner"] == self.owner_role for row in owners))

        # Demonstrate why the schema-owner gate is mandatory. This is a unique
        # rvtest schema; the same operation must never target shared state.
        self.admin.execute(self.sql.SQL("ALTER SCHEMA {} OWNER TO {}").format(
            self.sql.Identifier(self.schema), self.sql.Identifier(self.runtime_role)))
        with self.psycopg.connect(self.runtime_dsn) as runtime:
            runtime.execute(self.sql.SQL("DROP TABLE {}.authority_grants CASCADE").format(
                self.sql.Identifier(self.schema)))
        relation = self.admin.execute("SELECT to_regclass(%s) AS relation",
                                       (self.schema + ".authority_grants",)).fetchone()["relation"]
        self.assertIsNone(relation)
