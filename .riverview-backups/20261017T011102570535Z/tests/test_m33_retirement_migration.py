# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_m33_retirement_migration.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.3
# Purpose: Verify the fixed M33 retirement migration applies alone and preserves state
# Execution Model: Disposable PostgreSQL schemas
# Observability: unittest assertions for preflight, ledger, ACLs, and row preservation
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL 16; Psycopg 3
# Authority: Creates and drops only a unique rvtest_* schema
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Add narrow-migration regression suite
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Cover checksum drift and unexpected ledger entries
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Run against the configured disposable database name
# Changed: 2026-10-17 UTC | RV-M33-MIGRATION-CHAIN-0008-0009 | Verify the complete authority migration chain and exact 0008 seed state
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
        from riverview_core.postgres_migrations import apply_migrations

        self.psycopg, self.sql = psycopg, sql
        self.database = psycopg.conninfo.conninfo_to_dict(DSN).get("dbname", "riverview")
        self.apply = apply_m33_retirement_migration
        self.check = check_m33_retirement_migration
        self.apply_migrations = apply_migrations
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.tmp = tempfile.TemporaryDirectory(prefix="rv-m33-migration-test-")
        self.prior_dir = Path(self.tmp.name) / "prior"
        self.full_dir = Path(self.tmp.name) / "full"
        self.prior_dir.mkdir()
        self.full_dir.mkdir()
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name.startswith("0009_"):
                shutil.copyfile(path, self.full_dir / path.name)
            else:
                shutil.copyfile(path, self.full_dir / path.name)
                if path.name < "0009_worker_registration_retirement_event.sql":
                    shutil.copyfile(path, self.prior_dir / path.name)
        self.apply_migrations(DSN, schema=self.schema, migrations_dir=self.prior_dir)
        self.connection = psycopg.connect(DSN, autocommit=True)

    def tearDown(self):
        self.connection.close()
        self.admin.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(self.sql.Identifier(self.schema)))
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
                "capability_catalog": 18,
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
