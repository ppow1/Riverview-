# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_deferred_retry_acl.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.0
# Purpose: Verify bounded deferred retry permissions using the restricted runtime identity
# Execution Model: Disposable PostgreSQL schema and SET ROLE riverview_core
# Observability: Exact allowed and denied database operations
# Dependencies: Psycopg 3; private RIVERVIEW_TEST_PG_DSN
# Authority: Creates only a unique disposable schema and a test role if absent
# Changed: 2026-10-18 UTC | RV-C3-GRACE-REASONING-RELIABILITY-001 | Cover migration 0013 runtime ACL
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# Tests: python3 -m unittest tests.test_resident_deferred_retry_acl
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Exercise the migration 0013 table ACL as the actual restricted runtime role."""

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
class DeferredRetryRuntimeAclTests(unittest.TestCase):
    def setUp(self):
        self.schema = "rvretryacl_" + uuid4().hex
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
        for component in (None, "assignment_scheduler", "worker_adapter",
                          "institutional_authority", "resident_execution"):
            kwargs = {"schema": self.schema}
            if component:
                kwargs["migrations_dir"] = ROOT / component / "migrations"
            apply_migrations(DSN, **kwargs)

    def tearDown(self):
        if hasattr(self, "admin"):
            self.admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                sql.Identifier(self.schema)))
            if getattr(self, "created_runtime_role", False):
                self.admin.execute("DROP ROLE IF EXISTS riverview_core")
            self.admin.close()

    def test_runtime_can_claim_record_and_read_retry_state_but_cannot_delete(self):
        request_id = uuid4()
        table = sql.Identifier(self.schema, "resident_deferred_retry_state")
        with psycopg.connect(DSN) as runtime:
            runtime.execute("SET ROLE riverview_core")
            runtime.execute(sql.SQL("""INSERT INTO {} (request_id,attempt_count)
                VALUES (%s,1)
                ON CONFLICT (request_id) DO UPDATE SET
                    attempt_count=resident_deferred_retry_state.attempt_count+1,
                    next_attempt_at=NULL,
                    updated_at=clock_timestamp()""").format(table), (request_id,))
            runtime.execute(sql.SQL("""UPDATE {} SET
                attempt_count=attempt_count+1,
                next_attempt_at=clock_timestamp()+interval '1 second',
                last_error_code='provider_timeout',
                updated_at=clock_timestamp()
                WHERE request_id=%s""").format(table), (request_id,))
            state = runtime.execute(sql.SQL("""SELECT attempt_count,last_error_code,
                next_attempt_at IS NOT NULL FROM {} WHERE request_id=%s""").format(table),
                (request_id,)).fetchone()
            self.assertEqual(state, (2, "provider_timeout", True))
            runtime.execute("SAVEPOINT deny_identity_update")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                runtime.execute(sql.SQL("UPDATE {} SET request_id=%s WHERE request_id=%s").format(
                    table), (uuid4(), request_id))
            runtime.execute("ROLLBACK TO SAVEPOINT deny_identity_update")
            runtime.execute("SAVEPOINT deny_delete")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                runtime.execute(sql.SQL("DELETE FROM {} WHERE request_id=%s").format(table),
                                (request_id,))
            runtime.execute("ROLLBACK TO SAVEPOINT deny_delete")
            runtime.rollback()

        privileges = self.admin.execute(sql.SQL("""SELECT
            has_table_privilege('riverview_core', {}::regclass, 'SELECT'),
            has_table_privilege('riverview_core', {}::regclass, 'INSERT'),
            has_column_privilege('riverview_core', {}::regclass, 'attempt_count', 'UPDATE'),
            has_column_privilege('riverview_core', {}::regclass, 'request_id', 'UPDATE'),
            has_table_privilege('riverview_core', {}::regclass, 'DELETE'),
            has_table_privilege('riverview_core', {}::regclass, 'TRUNCATE')""").format(
                *([sql.Literal(f"{self.schema}.resident_deferred_retry_state")] * 6))).fetchone()
        self.assertEqual(privileges, (True, True, True, False, False, False))


if __name__ == "__main__":
    unittest.main()
