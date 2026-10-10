# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_worker_adapter.py
# Component: WORKER-ADAPTER
# Revision: 1.0.1
# Purpose: Verify worker scope, capabilities, durable attempts/results, and loss visibility
# Execution Model: PostgreSQL integration tests using isolated schemas
# Observability: unittest output and durable worker/attempt/result rows
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL test database
# Authority: Creates and drops only unique rvtest_* schemas
# Changed: 2026-10-10 UTC | RV-M2.1-001 | Initial worker adapter coverage
# Contracts: docs/development/M2.1-001_REVISION_RECORD.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""M2.1 PostgreSQL integration tests; never target the shared app schema."""

import hashlib
import os
import unittest
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class WorkerAdapterTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.postgres_migrations import apply_migrations

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        root = Path(__file__).resolve().parents[1] / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=root / "assignment_scheduler/migrations")
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=root / "worker_adapter/migrations")
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        from riverview_core.assignment_scheduler import PostgresAssignmentScheduler
        from riverview_core.worker_adapter import PostgresWorkerAdapter
        self.scheduler = PostgresAssignmentScheduler(DSN, schema=self.schema)
        self.worker = PostgresWorkerAdapter(DSN, schema=self.schema)
        self.assignment = "worker-task-" + uuid4().hex
        self.worker_id = "worker-local-" + uuid4().hex
        self.scope = "grant:local-task"
        self.ledger.create(self.assignment, "engineering", f"create-{self.assignment}",
                           authority_ref=self.scope, objective_ref="objective:sha256",
                           actor_id="resident:test")
        self.ledger.transition(self.assignment, "ready", "intake", f"ready-{self.assignment}",
                               actor_id="event-processor")
        self.lease = self.scheduler.claim_next(self.worker_id, lease_seconds=60)
        self.scheduler.start_assignment(self.assignment, self.worker_id,
                                        self.lease["generation"])

    def tearDown(self):
        from psycopg import sql
        self.worker.close()
        self.scheduler.close()
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def register(self, capabilities=None, scope=None):
        return self.worker.register_worker(
            self.worker_id,
            capabilities or ["deterministic.sha256.v1"],
            scope or self.scope)

    def test_scoped_authenticated_execution_persists_attributed_idempotent_result(self):
        token = self.register()
        payload = "deterministic local task"
        first = self.worker.execute_sha256(
            self.assignment, self.worker_id, token, self.lease["generation"],
            "attempt:one", payload)
        self.assertEqual(first["status"], "succeeded")
        self.assertEqual(first["result"]["sha256"], hashlib.sha256(payload.encode()).hexdigest())
        replay = self.worker.execute_sha256(
            self.assignment, self.worker_id, token, self.lease["generation"],
            "attempt:one", payload)
        self.assertEqual(replay["attempt_id"], first["attempt_id"])
        self.assertEqual(replay["result"], first["result"])
        with self.worker.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT credential_sha256 FROM worker_registry WHERE worker_id=%s",
                        (self.worker_id,))
            saved_credential = bytes(cur.fetchone()["credential_sha256"])
            self.assertNotEqual(saved_credential, token.encode())
            cur.execute("SELECT worker_id,lease_generation,status FROM worker_attempts WHERE attempt_id=%s",
                        (first["attempt_id"],))
            attempt = cur.fetchone()
            self.assertEqual((attempt["worker_id"], attempt["lease_generation"], attempt["status"]),
                             (self.worker_id, self.lease["generation"], "succeeded"))
            cur.execute("SELECT result,result_sha256 FROM worker_results WHERE attempt_id=%s",
                        (first["attempt_id"],))
            result = cur.fetchone()
            self.assertEqual(result["result"], first["result"])
            self.assertEqual(result["result_sha256"], first["result_sha256"])
        self.assertEqual(self.worker.incomplete_attempts(), [])

    def test_wrong_credential_capability_and_scope_are_rejected(self):
        from riverview_core.worker_adapter import WorkerAuthorizationError
        token = self.register(capabilities=["other.capability.v1"])
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.execute_sha256(self.assignment, self.worker_id, token,
                                       self.lease["generation"], "bad-cap", "x")
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.execute_sha256(self.assignment, self.worker_id, "wrong-token",
                                       self.lease["generation"], "bad-token", "x")
        other_id = "worker-other-" + uuid4().hex
        other_token = self.worker.register_worker(
            other_id, ["deterministic.sha256.v1"], "grant:other")
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.execute_sha256(self.assignment, other_id, other_token,
                                       self.lease["generation"], "bad-scope", "x")

    def test_interrupted_attempt_is_durably_visible_for_worker_loss_detection(self):
        token = self.register()
        with self.worker.ledger.db.transaction():
            with self.worker.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO worker_attempts
                    (attempt_id,assignment_id,worker_id,lease_generation,capability,
                     idempotency_key,input_sha256,status)
                    VALUES (%s,%s,%s,%s,'deterministic.sha256.v1','attempt:interrupted',%s,'running')""",
                    (uuid4(), self.assignment, self.worker_id, self.lease["generation"],
                     hashlib.sha256(b"interrupted").hexdigest()))
        incomplete = self.worker.incomplete_attempts()
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0]["worker_id"], self.worker_id)
        self.assertEqual(incomplete[0]["assignment_id"], self.assignment)
        self.assertEqual(len(token), 43)
