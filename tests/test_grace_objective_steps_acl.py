# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_objective_steps_acl.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Verify the persistent worker receives only column-scoped step-table access
# Execution Model: Disposable PostgreSQL schema and restricted runtime-role catalog checks
# Observability: Grant assertions; no production database access
# Dependencies: Isolated PostgreSQL DSN
# Authority: Test-only database privileges
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Verify migration 0009 runtime ACL
# Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md
# Tests: Isolated PostgreSQL migration integration
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
from __future__ import annotations

import os
import unittest
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from riverview_core.postgres_migrations import apply_migrations


DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1] / "src/riverview_core"


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class GraceObjectiveStepsAclTests(unittest.TestCase):
    def setUp(self):
        self.schema = "rvsteps_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION CURRENT_USER").format(
            sql.Identifier(self.schema)))
        exists = self.admin.execute(
            "SELECT 1 FROM pg_roles WHERE rolname='riverview_core'").fetchone()
        self.created_runtime_role = not exists
        if self.created_runtime_role:
            self.admin.execute("CREATE ROLE riverview_core NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
        self.admin.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO riverview_core").format(
            sql.Identifier(self.schema)))
        apply_migrations(DSN, schema=self.schema)
        for component in ("assignment_scheduler", "worker_adapter",
                          "institutional_authority", "resident_execution"):
            apply_migrations(DSN, schema=self.schema,
                             migrations_dir=ROOT / component / "migrations")

    def tearDown(self):
        if hasattr(self, "admin"):
            self.admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                sql.Identifier(self.schema)))
            if getattr(self, "created_runtime_role", False):
                self.admin.execute("DROP ROLE IF EXISTS riverview_core")
            self.admin.close()
    def test_runtime_acl_is_column_scoped_and_excludes_delete(self):
        table = sql.Literal(f"{self.schema}.grace_objective_steps")
        read = self.admin.execute(sql.SQL(
            "SELECT has_column_privilege('riverview_core', {}::regclass, 'step_id', 'SELECT'), "
            "has_column_privilege('riverview_core', {}::regclass, 'status', 'UPDATE'), "
            "has_column_privilege('riverview_core', {}::regclass, 'status', 'INSERT'), "
            "has_table_privilege('riverview_core', {}::regclass, 'DELETE'), "
            "has_table_privilege('riverview_core', {}::regclass, 'TRUNCATE')").format(
                table, table, table, table, table)).fetchone()
        self.assertEqual(read, (True, True, True, False, False))


if __name__ == "__main__":
    unittest.main()
