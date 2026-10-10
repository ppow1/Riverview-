# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_assignment_scheduler.py
# Component: ASSIGNMENT-SCHEDULER
# Revision: 1.0.0
# Purpose: Verify fair independent claims, lease expiry, and stale fencing
# Execution Model: PostgreSQL integration tests using isolated schemas
# Observability: unittest results and durable assignment/lease/event records
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL test database
# Authority: Creates and drops only unique rvtest_* schemas
# Changed: 2026-10-10 UTC | RV-M1.4-001 | Initial concurrent scheduler coverage
# Contracts: docs/development/M1.4-001_REVISION_RECORD.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""M1.4 PostgreSQL scheduling integration tests; never use the shared app schema."""

import os
import threading
import time
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class AssignmentSchedulerTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.postgres_migrations import apply_migrations
        from riverview_core.postgres_ledger import PostgresLedger

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        apply_migrations(DSN, schema=self.schema)
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        migrations = __import__("pathlib").Path(__file__).resolve().parents[1] / "src/riverview_core/assignment_scheduler/migrations"
        self.assertEqual(apply_migrations(DSN, schema=self.schema, migrations_dir=migrations),
                         ["0001_assignment_leases"])
        from riverview_core.assignment_scheduler import PostgresAssignmentScheduler
        self.scheduler = PostgresAssignmentScheduler(DSN, schema=self.schema)
        self.ids = []

    def tearDown(self):
        from psycopg import sql
        self.scheduler.close()
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def ready(self, assignment_id):
        self.ledger.create(assignment_id, "engineering", f"create-{assignment_id}",
                           authority_ref="grant:test", objective_ref=f"objective:{assignment_id}",
                           actor_id="resident:test")
        self.ledger.transition(assignment_id, "ready", "intake", f"ready-{assignment_id}",
                               actor_id="event-processor")
        self.ids.append(assignment_id)

    def test_active_lease_does_not_block_independent_assignment(self):
        self.ready("a-oldest")
        self.ready("b-next")
        first = self.scheduler.claim_next("worker:stalled", lease_seconds=60)
        second = self.scheduler.claim_next("worker:available", lease_seconds=60)
        self.assertEqual(first["assignment_id"], "a-oldest")
        self.assertEqual(second["assignment_id"], "b-next")
        self.assertIsNone(self.scheduler.claim_next("worker:empty"))

    def test_expiry_reclaim_increments_generation_and_fences_old_worker(self):
        from riverview_core.assignment_scheduler import StaleLeaseError

        self.ready("lease-target")
        first = self.scheduler.claim_next("worker:old", lease_seconds=0.05)
        time.sleep(0.10)
        replacement = self.scheduler.claim_next("worker:new", lease_seconds=10)
        self.assertEqual(replacement["assignment_id"], first["assignment_id"])
        self.assertEqual(replacement["generation"], first["generation"] + 1)
        with self.assertRaises(StaleLeaseError):
            self.scheduler.start_assignment("lease-target", "worker:old", first["generation"])
        with self.assertRaises(StaleLeaseError):
            self.scheduler.heartbeat("lease-target", "worker:old", first["generation"])
        running = self.scheduler.start_assignment("lease-target", "worker:new", replacement["generation"])
        self.assertEqual(running["state"], "running")
        events = self.ledger.events()
        self.assertEqual(len([event for event in events if event["event_type"] == "assignment.transitioned" and event["payload"].get("to") == "running"]), 1)

    def test_parallel_workers_claim_distinct_ready_assignments(self):
        self.ready("parallel-a")
        self.ready("parallel-b")
        barrier = threading.Barrier(2)
        claims, errors = [], []

        def claim(worker):
            from riverview_core.assignment_scheduler import PostgresAssignmentScheduler
            scheduler = PostgresAssignmentScheduler(DSN, schema=self.schema)
            try:
                barrier.wait(timeout=5)
                claims.append(scheduler.claim_next(worker, lease_seconds=10))
            except Exception as exc:  # surfaced in assertion on the test thread
                errors.append(exc)
            finally:
                scheduler.close()

        threads = [threading.Thread(target=claim, args=(f"worker:{n}",)) for n in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual({claim["assignment_id"] for claim in claims}, {"parallel-a", "parallel-b"})
        self.assertEqual(len({claim["generation"] for claim in claims}), 1)
