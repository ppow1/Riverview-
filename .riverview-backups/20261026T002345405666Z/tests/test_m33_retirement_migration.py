# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_m33_retirement_migration.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.2.3
# Changed: 2026-10-25 UTC | RV-FULL-CHECKOUT-M33-PROFILE | Verify only the five functions belonging to migration 0008 in the prerequisite case.
# Purpose: Verify 0008 commits atomically with the runtime function ACL boundary
# Execution Model: Disposable PostgreSQL schemas
# Observability: unittest assertions for preflight, ledger, ACLs, and row preservation
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL 16; Psycopg 3
# Authority: Creates and drops only a unique rvtest_* schema
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Add narrow-migration regression suite
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Cover checksum drift and unexpected ledger entries
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Run against the configured disposable database name
# Changed: 2026-10-17 UTC | RV-M33-MIGRATION-CHAIN-0008-0009 | Verify the complete authority migration chain and exact 0008 seed state
# Changed: 2026-10-17 UTC | RV-M33-MIGRATION-CHAIN-0008-0009 | Exercise the production 0008-only check/apply path on disposable PostgreSQL
# Changed: 2026-10-17 UTC | M33-0008-ATOMIC-RUNTIME-ACL | Cover five-function effective grants, PUBLIC denial, and transaction rollback
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Isolated integration coverage for the M33 event-type migration procedure."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "src/riverview_core/institutional_authority/migrations"


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class M33RetirementMigrationTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.institutional_authority.m33_retirement_migration import (
            apply_m33_retirement_migration, check_m33_retirement_migration,
        )
        from riverview_core.institutional_authority.db_boundary import provision_authority_boundary
        from riverview_core.postgres_migrations import apply_migrations

        self.psycopg, self.sql = psycopg, sql
        self.database = psycopg.conninfo.conninfo_to_dict(DSN).get("dbname", "riverview")
        suffix = uuid4().hex[:12]
        self.runtime_role = "rv_runtime_" + suffix
        self.manager_role = "rv_manager_" + suffix
        self.owner_role = "rv_owner_" + suffix
        self.guest_role = "rv_guest_" + suffix
        self.role_kwargs = {"runtime_role": self.runtime_role,
                            "manager_role": self.manager_role,
                            "owner_role": self.owner_role}
        self.apply = lambda connection, directory, **kwargs: apply_m33_retirement_migration(
            connection, directory, **self.role_kwargs, **kwargs)
        self.check = lambda connection, directory, **kwargs: check_m33_retirement_migration(
            connection, directory, **self.role_kwargs, **kwargs)
        self.apply_migrations = apply_migrations
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL(
            "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
        ).format(sql.Identifier(self.runtime_role)))
        self.admin.execute(sql.SQL(
            "CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
        ).format(sql.Identifier(self.manager_role)))
        self.admin.execute(sql.SQL(
            "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
        ).format(sql.Identifier(self.owner_role)))
        self.admin.execute(sql.SQL(
            "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
        ).format(sql.Identifier(self.guest_role)))
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.tmp = tempfile.TemporaryDirectory(prefix="rv-m33-migration-test-")
        self.prior_dir = Path(self.tmp.name) / "prior"
        self.full_dir = Path(self.tmp.name) / "full"
        self.prior_dir.mkdir()
        self.full_dir.mkdir()
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name <= "0009_worker_registration_retirement_event.sql":
                shutil.copyfile(path, self.full_dir / path.name)
                if path.name < "0009_worker_registration_retirement_event.sql":
                    shutil.copyfile(path, self.prior_dir / path.name)
        self.apply_migrations(DSN, schema=self.schema, migrations_dir=self.prior_dir)
        self.connection = psycopg.connect(DSN, autocommit=True)
        provision_authority_boundary(
            self.connection, schema=self.schema, runtime_role=self.runtime_role,
            manager_role=self.manager_role, owner_role=self.owner_role, apply=True)

    def tearDown(self):
        self.connection.close()
        self.admin.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(self.sql.Identifier(self.schema)))
        for role in (self.runtime_role, self.manager_role,
                     self.owner_role, self.guest_role):
            self.admin.execute(self.sql.SQL("DROP ROLE IF EXISTS {}").format(
                self.sql.Identifier(role)))
        self.admin.close()
        self.tmp.cleanup()

    def _seed_event(self):
        self.admin.execute(self.sql.SQL(
            "INSERT INTO {}.institutional_principals(principal_id,principal_kind) "
            "VALUES ('steward:migration-fixture','steward')"
        ).format(self.sql.Identifier(self.schema)))
        self.admin.execute(self.sql.SQL(
            "INSERT INTO {}.institutional_authority_events "
            "(event_id,event_type,actor_id,subject_id) "
            "VALUES (%s,'steward_bootstrapped','steward:migration-fixture','steward:migration-fixture')"
        ).format(self.sql.Identifier(self.schema)), (uuid4(),))

    def _apply_pre_0008_boundary_fixture(self, schema):
        """Mirror the deployed 0000-0007 function-only boundary for this schema."""
        from riverview_core.institutional_authority.db_boundary import (
            AUTHORIZATION_FUNCTION, AUTHORITY_TABLES, EVENT_TRIGGER_FUNCTION,
            PRINCIPAL_AUTHORIZATION_FUNCTION, RUNTIME_OFFICE_FUNCTION_SIGNATURES,
        )
        ident = self.sql.Identifier(schema)
        self.admin.execute(self.sql.SQL(
            "REVOKE ALL ON SCHEMA {} FROM PUBLIC,{},{}"
        ).format(ident, self.sql.Identifier(self.runtime_role),
                 self.sql.Identifier(self.owner_role)))
        for role in (self.runtime_role, self.manager_role, self.owner_role):
            self.admin.execute(self.sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                ident, self.sql.Identifier(role)))
        for table in AUTHORITY_TABLES[:9]:
            self.admin.execute(self.sql.SQL("ALTER TABLE {}.{} OWNER TO {}").format(
                ident, self.sql.Identifier(table), self.sql.Identifier(self.owner_role)))
            self.admin.execute(self.sql.SQL(
                "REVOKE ALL PRIVILEGES ON TABLE {}.{} FROM PUBLIC,{},{}"
            ).format(ident, self.sql.Identifier(table),
                     self.sql.Identifier(self.runtime_role),
                     self.sql.Identifier(self.manager_role)))
            self.admin.execute(self.sql.SQL(
                "GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE {}.{} TO {}"
            ).format(ident, self.sql.Identifier(table),
                     self.sql.Identifier(self.manager_role)))
        function_specs = [
            (EVENT_TRIGGER_FUNCTION, "()", False),
            (AUTHORIZATION_FUNCTION, "(bytea,text,text)", True),
            (PRINCIPAL_AUTHORIZATION_FUNCTION, "(text,text,text)", True),
        ] + [(name, signature, True)
             for name, signature in RUNTIME_OFFICE_FUNCTION_SIGNATURES.items()]
        for name, signature, runtime_execute in function_specs:
            self.admin.execute(self.sql.SQL("ALTER FUNCTION {}.{}{} OWNER TO {}").format(
                ident, self.sql.Identifier(name), self.sql.SQL(signature),
                self.sql.Identifier(self.owner_role)))
            self.admin.execute(self.sql.SQL(
                "REVOKE ALL PRIVILEGES ON FUNCTION {}.{}{} FROM PUBLIC,{},{}"
            ).format(ident, self.sql.Identifier(name), self.sql.SQL(signature),
                     self.sql.Identifier(self.runtime_role),
                     self.sql.Identifier(self.manager_role)))
            if runtime_execute:
                self.admin.execute(self.sql.SQL(
                    "GRANT EXECUTE ON FUNCTION {}.{}{} TO {}"
                ).format(ident, self.sql.Identifier(name), self.sql.SQL(signature),
                         self.sql.Identifier(self.runtime_role)))

    def test_complete_authority_chain_0000_through_0009(self):
        """Exercise every reviewed migration in order in a fresh isolated schema."""
        schema = "rvtestchain_" + uuid4().hex
        self.admin.execute(self.sql.SQL("CREATE SCHEMA {}").format(
            self.sql.Identifier(schema)))
        try:
            applied = self.apply_migrations(
                DSN, schema=schema, migrations_dir=MIGRATIONS
            )
            expected_versions = [path.stem for path in sorted(MIGRATIONS.glob("*.sql"))]
            self.assertEqual(applied, expected_versions)
            ledger = dict(self.admin.execute(self.sql.SQL(
                "SELECT version,checksum FROM {}.schema_migrations ORDER BY version"
            ).format(self.sql.Identifier(schema))).fetchall())
            self.assertEqual(set(ledger), set(expected_versions))
            import hashlib
            self.assertEqual(ledger, {
                path.stem: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(MIGRATIONS.glob("*.sql"))
            })

            expected_seed_counts = {
                "resident_permission_tiers": 4,
                "capability_catalog": 20,
                "resource_catalog": 11,
                "capability_resources": 26,
                "resident_permission_profiles": 0,
                "resident_permission_profile_drafts": 0,
                "resident_permission_tier_rules": 50,
                "resident_permission_rules": 0,
                "resident_permission_events": 0,
            }
            for table, expected_count in expected_seed_counts.items():
                actual = self.admin.execute(self.sql.SQL(
                    "SELECT count(*) FROM {}.{}"
                ).format(self.sql.Identifier(schema), self.sql.Identifier(table))).fetchone()[0]
                self.assertEqual(actual, expected_count, table)
            self.assertEqual(self.apply_migrations(
                DSN, schema=schema, migrations_dir=MIGRATIONS
            ), [])
            from riverview_core.institutional_authority.m33_retirement_migration import (
                RETIRED_EVENT_TYPES, _event_types,
            )
            with self.admin.cursor() as cur:
                self.assertEqual(_event_types(cur, schema), RETIRED_EVENT_TYPES)
            self.assertEqual(self.admin.execute(self.sql.SQL(
                "SELECT count(*) FROM {}.institutional_authority_events"
            ).format(self.sql.Identifier(schema))).fetchone()[0], 0)
        finally:
            self.admin.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(
                self.sql.Identifier(schema)))

    def test_0008_prerequisite_applies_alone_and_unlocks_0009_check(self):
        from riverview_core.institutional_authority.m33_retirement_migration import (
            apply_m33_retirement_prerequisite,
            check_m33_retirement_migration,
            check_m33_retirement_prerequisite,
        )
        schema = "rvtest0008_" + uuid4().hex
        self.admin.execute(self.sql.SQL("CREATE SCHEMA {}").format(
            self.sql.Identifier(schema)))
        only_0000_to_0007 = Path(self.tmp.name) / "only-0000-through-0007"
        only_0000_to_0007.mkdir()
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name < "0008_resident_permission_profiles.sql":
                shutil.copyfile(path, only_0000_to_0007 / path.name)
        self.apply_migrations(DSN, schema=schema,
                              migrations_dir=only_0000_to_0007)
        self._apply_pre_0008_boundary_fixture(schema)
        connection = self.psycopg.connect(DSN, autocommit=True)
        try:
            self.assertEqual(check_m33_retirement_prerequisite(
                connection, self.full_dir, schema=schema,
                expected_database=self.database, **self.role_kwargs)["status"], "READY")
            applied = apply_m33_retirement_prerequisite(
                connection, self.full_dir, schema=schema,
                expected_database=self.database, **self.role_kwargs)
            self.assertEqual(applied["status"], "APPLIED")
            self.assertEqual(applied["profile_records_created"], 0)
            self.assertEqual(applied["runtime_function_acl"],
                             "five profile functions only; PUBLIC denied")
            self.assertEqual(check_m33_retirement_prerequisite(
                connection, self.full_dir, schema=schema,
                expected_database=self.database, **self.role_kwargs)["status"], "ALREADY_APPLIED")
            self.assertEqual(check_m33_retirement_migration(
                connection, self.full_dir, schema=schema,
                expected_database=self.database, **self.role_kwargs)["status"], "READY")

            from riverview_core.institutional_authority.db_boundary import (
                PROFILE_RUNTIME_PERMISSION_SIGNATURES,
            )
            for function, signature in PROFILE_RUNTIME_PERMISSION_SIGNATURES.items():
                procedure = f"{schema}.{function}{signature}"
                privileges = self.admin.execute(
                    "SELECT has_function_privilege(%s,to_regprocedure(%s),'EXECUTE'), "
                    "has_function_privilege(%s,to_regprocedure(%s),'EXECUTE'), "
                    "EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                    "CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a "
                    "WHERE n.nspname=%s AND p.proname=%s AND a.grantee=0 "
                    "AND a.privilege_type='EXECUTE')",
                    (self.runtime_role, procedure, self.manager_role, procedure,
                     schema, function),
                ).fetchone()
                self.assertEqual(privileges, (True, False, False), function)
            evaluator = (f"{schema}.evaluate_resident_permission"
                         "(text,text,text,text,text,boolean)")
            with self.admin.transaction():
                self.admin.execute(self.sql.SQL("SET LOCAL ROLE {}").format(
                    self.sql.Identifier(self.runtime_role)))
                decision = self.admin.execute(self.sql.SQL(
                    "SELECT {}.evaluate_resident_permission(%s,%s,%s,%s,%s,%s)"
                ).format(self.sql.Identifier(schema)),
                    ("resident:legacy-test", "assignment.execute", "work-order:test",
                     "execute", "internal", False)).fetchone()[0]
                self.assertEqual(decision["mode"], "legacy_exact_grant_only")
            with self.admin.transaction():
                self.admin.execute(self.sql.SQL("SET LOCAL ROLE {}").format(
                    self.sql.Identifier(self.guest_role)))
                with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                    self.admin.execute(self.sql.SQL(
                        "SELECT {}.evaluate_resident_permission(%s,%s,%s,%s,%s,%s)"
                    ).format(self.sql.Identifier(schema)),
                        ("resident:legacy-test", "assignment.execute", "work-order:test",
                         "execute", "internal", False)).fetchone()
        finally:
            connection.close()
            self.admin.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(
                self.sql.Identifier(schema)))

    def test_0008_boundary_failure_rolls_back_schema_and_ledger(self):
        from riverview_core.institutional_authority.m33_retirement_migration import (
            apply_m33_retirement_prerequisite,
        )
        schema = "rvtestrollback_" + uuid4().hex
        self.admin.execute(self.sql.SQL("CREATE SCHEMA {}").format(
            self.sql.Identifier(schema)))
        prior_only = Path(self.tmp.name) / "rollback-0000-through-0007"
        prior_only.mkdir()
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name < "0008_resident_permission_profiles.sql":
                shutil.copyfile(path, prior_only / path.name)
        self.apply_migrations(DSN, schema=schema, migrations_dir=prior_only)
        broken_roles = dict(self.role_kwargs)
        broken_roles["manager_role"] = "rv_missing_manager_" + uuid4().hex[:12]
        try:
            with self.assertRaises(Exception):
                apply_m33_retirement_prerequisite(
                    self.connection, self.full_dir, schema=schema,
                    expected_database=self.database, **broken_roles)
            self.assertIsNone(self.admin.execute(
                "SELECT to_regclass(%s)",
                (f"{schema}.resident_permission_profiles",)).fetchone()[0])
            self.assertFalse(self.admin.execute(
                self.sql.SQL("SELECT EXISTS (SELECT 1 FROM {}.schema_migrations "
                             "WHERE version='0008_resident_permission_profiles')").format(
                    self.sql.Identifier(schema))).fetchone()[0])
        finally:
            self.admin.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(
                self.sql.Identifier(schema)))

    def test_check_is_read_only_and_apply_changes_only_constraint_and_ledger(self):
        from riverview_core.institutional_authority.m33_retirement_migration import (
            EXPECTED_MIGRATION_SHA256, MIGRATION_VERSION,
        )
        self._seed_event()
        self.admin.execute(self.sql.SQL(
            "REVOKE ALL ON {}.institutional_authority_events FROM PUBLIC"
        ).format(self.sql.Identifier(self.schema)))

        before_rows = self.admin.execute(self.sql.SQL(
            "SELECT event_id,event_type,actor_id,subject_id,payload,recorded_at "
            "FROM {}.institutional_authority_events ORDER BY event_id"
        ).format(self.sql.Identifier(self.schema))).fetchall()
        before_acl = self.admin.execute(
            "SELECT nspacl::text FROM pg_namespace WHERE nspname=%s", (self.schema,)
        ).fetchone()[0]
        before_table_acl = self.admin.execute(
            "SELECT relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname=%s AND c.relname='institutional_authority_events'",
            (self.schema,),
        ).fetchone()[0]

        preflight = self.check(self.connection, self.full_dir, schema=self.schema,
                               expected_database=self.database)
        self.assertEqual(preflight["status"], "READY")
        self.assertEqual(preflight["checksum"], EXPECTED_MIGRATION_SHA256)
        self.assertNotIn(MIGRATION_VERSION, dict(self.admin.execute(
            self.sql.SQL("SELECT version,checksum FROM {}.schema_migrations")
            .format(self.sql.Identifier(self.schema))).fetchall()))

        result = self.apply(self.connection, self.full_dir, schema=self.schema,
                            expected_database=self.database)
        self.assertEqual(result["status"], "APPLIED")
        self.assertEqual(result["authority_data_and_permissions"], "PRESERVED")
        rows_after = self.admin.execute(self.sql.SQL(
            "SELECT event_id,event_type,actor_id,subject_id,payload,recorded_at "
            "FROM {}.institutional_authority_events ORDER BY event_id"
        ).format(self.sql.Identifier(self.schema))).fetchall()
        self.assertEqual(rows_after, before_rows)
        self.assertEqual(self.admin.execute(
            "SELECT nspacl::text FROM pg_namespace WHERE nspname=%s", (self.schema,)
        ).fetchone()[0], before_acl)
        self.assertEqual(self.admin.execute(
            "SELECT relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname=%s AND c.relname='institutional_authority_events'",
            (self.schema,),
        ).fetchone()[0], before_table_acl)
        self.assertEqual(self.admin.execute(self.sql.SQL(
            "SELECT checksum FROM {}.schema_migrations WHERE version=%s"
        ).format(self.sql.Identifier(self.schema)), (MIGRATION_VERSION,)).fetchone()[0],
                         EXPECTED_MIGRATION_SHA256)
        self.assertEqual(self.apply(self.connection, self.full_dir, schema=self.schema,
                                    expected_database=self.database)["status"],
                         "ALREADY_APPLIED")

    def test_refuses_unrelated_migration_file(self):
        extra = self.full_dir / "0010_unrelated.sql"
        extra.write_text("SELECT 1;\n", encoding="utf-8")
        with self.assertRaisesRegex(Exception, "unrelated_or_missing_migrations_present"):
            self.check(self.connection, self.full_dir, schema=self.schema,
                       expected_database=self.database)

    def test_refuses_missing_or_drifted_prior_migration(self):
        self.admin.execute(self.sql.SQL(
            "DELETE FROM {}.schema_migrations WHERE version='0008_resident_permission_profiles'"
        ).format(self.sql.Identifier(self.schema)))
        with self.assertRaisesRegex(Exception, "prior_migrations_missing_or_unrelated_pending"):
            self.check(self.connection, self.full_dir, schema=self.schema,
                       expected_database=self.database)

    def test_refuses_drifted_prior_checksum(self):
        self.admin.execute(self.sql.SQL(
            "UPDATE {}.schema_migrations SET checksum=%s "
            "WHERE version='0007_audited_office_role_update'"
        ).format(self.sql.Identifier(self.schema)), ("0" * 64,))
        with self.assertRaisesRegex(Exception, "prior_migrations_missing_or_unrelated_pending"):
            self.check(self.connection, self.full_dir, schema=self.schema,
                       expected_database=self.database)

    def test_refuses_unrelated_applied_ledger_entry(self):
        self.admin.execute(self.sql.SQL(
            "INSERT INTO {}.schema_migrations(version,checksum) VALUES(%s,%s)"
        ).format(self.sql.Identifier(self.schema)), ("0010_unrelated", "1" * 64))
        with self.assertRaisesRegex(Exception, "prior_migrations_missing_or_unrelated_pending"):
            self.check(self.connection, self.full_dir, schema=self.schema,
                       expected_database=self.database)
