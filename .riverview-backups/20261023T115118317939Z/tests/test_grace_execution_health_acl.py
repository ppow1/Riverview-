# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_execution_health_acl.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Reproduce restricted-role service failure and verify narrow objective/health ACLs
# Execution Model: Isolated PostgreSQL schema and temporary NOLOGIN runtime role
# Observability: Sanitized failure log and persisted heartbeat metadata
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL; Psycopg 3
# Authority: Creates and drops only one unique schema and one unique test role
# Changed: 2026-10-15 UTC | RV-GRACE-HEALTH-WRITER-ACL-001 | Cover least-privilege health writes
# Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Exercise Grace's actual heartbeat method as a restricted database role."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql

from riverview_core.postgres_migrations import apply_migrations
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.resident_execution.service import GraceExecutionService


DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1] / "src/riverview_core"


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class GraceExecutionHealthAclTests(unittest.TestCase):
    def setUp(self):
        self.schema = "rvhealth_" + uuid4().hex
        self.role = "rvhealth_" + uuid4().hex
        if not re.fullmatch(r"rvhealth_[0-9a-f]{32}", self.role):
            raise AssertionError("generated test role is not a valid fixed identifier")
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION CURRENT_USER").format(
            sql.Identifier(self.schema)))
        self.admin.execute(sql.SQL(
            "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
        ).format(sql.Identifier(self.role)))

        apply_migrations(DSN, schema=self.schema)
        self.migration_dir = tempfile.TemporaryDirectory(prefix="rv-health-base-migrations-")
        base_dir = Path(self.migration_dir.name)
        for migration in (ROOT / "resident_execution/migrations").glob("*.sql"):
            if migration.name.startswith("0007_"):
                continue
            shutil.copyfile(migration, base_dir / migration.name)
        apply_migrations(DSN, schema=self.schema, migrations_dir=base_dir)

        self.admin.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
            sql.Identifier(self.schema), sql.Identifier(self.role)))
        self.admin.execute(sql.SQL("GRANT SELECT ON {}.grace_execution_health TO {}").format(
            sql.Identifier(self.schema), sql.Identifier(self.role)))
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.ledger.db.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.role)))

        self.service = GraceExecutionService.__new__(GraceExecutionService)
        self.service.pipeline = type("Pipeline", (), {"ledger": self.ledger})()
        self.service.instance_id = uuid4()

    def tearDown(self):
        if hasattr(self, "ledger"):
            self.ledger.close()
        if hasattr(self, "admin"):
            self.admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                sql.Identifier(self.schema)))
            self.admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(
                sql.Identifier(self.role)))
            self.admin.close()
        if hasattr(self, "migration_dir"):
            self.migration_dir.cleanup()

    def test_runtime_role_denial_is_fixed_by_column_scoped_health_grant(self):
        with self.assertLogs("riverview.grace_execution", level="WARNING") as captured:
            self.service._heartbeat("healthy")
        self.assertTrue(any("InsufficientPrivilege" in row for row in captured.output))
        self.assertEqual(self.admin.execute(sql.SQL(
            "SELECT count(*) FROM {}.grace_execution_health"
        ).format(sql.Identifier(self.schema))).fetchone()[0], 0)
        self.service.pipeline = type("Pipeline", (), {"ledger": self.ledger})()
        self.service.authority_ref = "work-order:engineering"
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.service._proposed()

        grant = (ROOT / "resident_execution/migrations/0007_grace_runtime_objective_and_health_acl.sql").read_text()
        self.assertIn("SELECT (objective_id, request, scope_ref", grant)
        self.assertIn("INSERT (objective_id, request", grant)
        self.assertIn("INSERT (service_id, instance_id, status", grant)
        self.assertIn("GRANT USAGE ON SEQUENCE", grant)
        self.assertNotIn("GRANT ALL", grant)
        self.assertNotIn("schema_migrations", grant)
        self.assertNotIn("riverview_authority", grant)

        test_migration = grant.replace("'riverview_core'", f"'{self.role}'")
        with tempfile.TemporaryDirectory(prefix="rv-health-writer-migration-") as temp:
            (Path(temp) / "0007_grace_runtime_objective_and_health_acl.sql").write_text(test_migration)
            self.assertEqual(apply_migrations(DSN, schema=self.schema,
                                              migrations_dir=temp),
                             ["0007_grace_runtime_objective_and_health_acl"])

        self.assertEqual(self.service._proposed(), [])
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""INSERT INTO grace_objectives
                (objective_id,request,scope_ref,submitter_id,acceptance_criteria,status)
                VALUES ('objective:acl-test','bounded synthetic task','work-order:engineering',
                        'steward:test','[]'::jsonb,'RECEIVED')""")
            cur.execute("""INSERT INTO grace_objective_events
                (objective_id,event_type,idempotency_key,actor_id,payload)
                VALUES ('objective:acl-test','objective.received','acl-test:event',
                        'steward:test','{}'::jsonb)""")
            cur.execute("""UPDATE grace_objectives SET status='GROUNDED',evidence='{}'::jsonb,
                source_revision=%s,source_sha256=%s,revision=revision+1,updated_at=clock_timestamp()
                WHERE objective_id='objective:acl-test' AND status='RECEIVED'""",
                ('a' * 40, 'b' * 64))
            self.assertEqual(cur.rowcount, 1)
            cur.execute("""SELECT objective_id,request,source_revision,source_sha256,revision
                FROM grace_objectives WHERE objective_id='objective:acl-test'""")
            objective = cur.fetchone()
            self.assertEqual(objective['request'], 'bounded synthetic task')
            self.assertEqual(objective['revision'], 2)
            cur.execute("""SELECT event_type,idempotency_key,payload,sequence FROM grace_objective_events
                WHERE objective_id='objective:acl-test' ORDER BY sequence""")
            event = cur.fetchone()
            self.assertEqual(event['idempotency_key'], 'acl-test:event')

        self.service._heartbeat("healthy")
        self.service._heartbeat("degraded", "SyntheticProviderFailure")
        row = self.admin.execute(sql.SQL(
            "SELECT status,last_error_type,cycles_completed FROM {}.grace_execution_health "
            "WHERE service_id='grace.execution.v1'"
        ).format(sql.Identifier(self.schema))).fetchone()
        self.assertEqual(tuple(row), ("degraded", "SyntheticProviderFailure", 2))

        checks = self.admin.execute(
            "SELECT has_column_privilege(%s,%s,'service_id','INSERT'), "
            "has_column_privilege(%s,%s,'cycles_completed','UPDATE'), "
            "has_column_privilege(%s,%s,'service_id','UPDATE'), "
            "has_column_privilege(%s,%s,'request','SELECT'), "
            "has_column_privilege(%s,%s,'status','UPDATE'), "
            "has_column_privilege(%s,%s,'objective_id','UPDATE'), "
            "has_column_privilege(%s,%s,'payload','SELECT'), "
            "has_column_privilege(%s,%s,'payload','INSERT'), "
            "has_column_privilege(%s,%s,'payload','UPDATE'), "
            "has_table_privilege(%s,%s,'DELETE'), "
            "has_table_privilege(%s,%s,'DELETE'), "
            "has_table_privilege(%s,%s,'UPDATE'), "
            "has_table_privilege(%s,%s,'INSERT')",
            (self.role, f"{self.schema}.grace_execution_health",
             self.role, f"{self.schema}.grace_execution_health",
             self.role, f"{self.schema}.grace_execution_health",
             self.role, f"{self.schema}.grace_objectives",
             self.role, f"{self.schema}.grace_objectives",
             self.role, f"{self.schema}.grace_objectives",
             self.role, f"{self.schema}.grace_objective_events",
             self.role, f"{self.schema}.grace_objective_events",
             self.role, f"{self.schema}.grace_objective_events",
             self.role, f"{self.schema}.grace_execution_health",
             self.role, f"{self.schema}.grace_objective_events",
             self.role, f"{self.schema}.grace_objective_events",
             self.role, f"{self.schema}.grace_objectives"),
        ).fetchone()
        self.assertEqual(tuple(checks),
                         (True, True, False, True, True, False, True, True, False,
                          False, False, False, False))

        restricted = psycopg.connect(DSN, autocommit=True)
        try:
            restricted.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.role)))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                restricted.execute(sql.SQL(
                    "UPDATE {}.grace_execution_health SET service_id='forged' "
                    "WHERE service_id='grace.execution.v1'"
                ).format(sql.Identifier(self.schema)))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                restricted.execute(sql.SQL(
                    "DELETE FROM {}.grace_objective_events WHERE idempotency_key='acl-test:event'"
                ).format(sql.Identifier(self.schema)))
        finally:
            restricted.close()


if __name__ == "__main__":
    unittest.main()
