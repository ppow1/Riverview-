# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_postgres_ledger.py
# Component: POSTGRES-LEDGER
# Revision: 1.1.3
# Purpose: Verify migration safety and durable PostgreSQL assignment/event behavior
# Execution Model: Request-driven tests against isolated disposable schemas
# Observability: unittest results and PostgreSQL records
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL test database
# Authority: Creates and drops only uniquely named rvtest_* schemas
# Changed: 2026-10-10 UTC | RV-M1.2-001 | Exercise versioned schema and contract metadata
# Contracts: docs/components/POSTGRES_LEDGER.md; docs/architecture/EVENT_AND_ASSIGNMENT_CONTRACT_v0.1.md
# Tests: This file
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""PostgreSQL integration tests; never target the commissioned app schema."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class PostgresLedgerTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.postgres_migrations import apply_migrations

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        from psycopg import sql
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.migrations = apply_migrations(DSN, schema=self.schema)
        self.ledger = PostgresLedger(DSN, schema=self.schema)

    def tearDown(self):
        from psycopg import sql
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def create(self, assignment_id="521", *, owner="engineering", key=None,
               authority="grant:engineering", objective="objective:521", actor="resident:codex",
               correlation=None):
        return self.ledger.create(
            assignment_id, owner, key or f"create-{assignment_id}",
            authority_ref=authority, objective_ref=objective, actor_id=actor,
            contract_ref="contract:first-slice", workflow_id="workflow:first-slice",
            workflow_step="intake", correlation_id=correlation)

    def test_versioned_migration_is_idempotent_and_rejects_drift(self):
        from riverview_core.postgres_migrations import MigrationError, apply_migrations

        self.assertEqual(self.migrations, ["0001_assignment_event_ledger"])
        self.assertEqual(apply_migrations(DSN, schema=self.schema), [])
        original = Path(__file__).resolve().parents[1] / "src/riverview_core/migrations"
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp)
            shutil.copy(original / "0001_assignment_event_ledger.sql", copied)
            migration = copied / "0001_assignment_event_ledger.sql"
            migration.write_text(migration.read_text() + "\n-- changed after application\n")
            with self.assertRaisesRegex(MigrationError, "checksum mismatch"):
                apply_migrations(DSN, schema=self.schema, migrations_dir=copied)

    def test_migrations_reject_missing_target_schema(self):
        from riverview_core.postgres_migrations import MigrationError, apply_migrations
        missing = self.schema + "_missing"
        with self.assertRaisesRegex(MigrationError, "target schema does not exist"):
            apply_migrations(DSN, schema=missing)

    def test_assignment_event_contract_atomicity_and_reconnect(self):
        created = self.create()
        self.assertEqual(created["authority_ref"], "grant:engineering")
        self.assertEqual(created["objective_ref"], "objective:521")
        self.assertEqual(created["workflow_id"], "workflow:first-slice")
        self.assertEqual(len(self.ledger.events()), 1)

        self.ledger.transition("521", "ready", "dispatch", "ready-521", actor_id="worker:one")
        self.ledger.transition("521", "running", "execute", "run-521", actor_id="worker:one")
        self.ledger.close()
        from riverview_core.postgres_ledger import PostgresLedger
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        assignment = self.ledger.get("521")
        events = self.ledger.events()
        self.assertEqual(assignment["state"], "running")
        self.assertEqual(assignment["version"], 3)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["schema"], "rv.event.v1")
        self.assertEqual(events[0]["authority_ref"], "grant:engineering")
        self.assertEqual(events[0]["correlation_id"], "521")
        self.assertIsNone(events[0]["causation_id"])
        self.assertEqual(events[1]["causation_id"], events[0]["event_id"])
        self.assertEqual(events[2]["causation_id"], events[1]["event_id"])

    def test_exact_idempotency_and_duplicate_transition_rejection(self):
        self.create()
        self.create()
        self.assertEqual(len(self.ledger.events()), 1)
        from riverview_core.ledger import TransitionError
        with self.assertRaisesRegex(TransitionError, "collision"):
            self.create(owner="research")
        with self.assertRaisesRegex(TransitionError, "collision"):
            self.create(actor="resident:other")
        self.ledger.transition("521", "ready", "dispatch", "ready-521", actor_id="worker:one")
        self.ledger.transition("521", "ready", "dispatch", "ready-521", actor_id="worker:one")
        self.assertEqual(len(self.ledger.events()), 2)
        with self.assertRaisesRegex(TransitionError, "invalid transition"):
            self.ledger.transition("521", "ready", "dispatch", "ready-duplicate", actor_id="worker:one")
        with self.assertRaisesRegex(TransitionError, "collision"):
            self.ledger.transition("521", "ready", "different-step", "ready-521", actor_id="worker:one")

    def test_illegal_transition_and_failed_event_roll_back_state(self):
        self.create()
        from riverview_core.ledger import TransitionError
        with self.assertRaises(TransitionError):
            self.ledger.transition("521", "completed", "done", "illegal", actor_id="worker:one", verified=True)
        before = self.ledger.get("521")
        with self.ledger.db.cursor() as cur:
            cur.execute("""CREATE FUNCTION reject_transition_event() RETURNS trigger AS $$
                         BEGIN IF NEW.event_type = 'assignment.transitioned' THEN
                           RAISE EXCEPTION 'injected event failure'; END IF; RETURN NEW; END;
                         $$ LANGUAGE plpgsql""")
            cur.execute("""CREATE TRIGGER reject_transition BEFORE INSERT ON events
                         FOR EACH ROW EXECUTE FUNCTION reject_transition_event()""")
        import psycopg
        with self.assertRaises(psycopg.Error):
            self.ledger.transition("521", "ready", "dispatch", "triggered-failure", actor_id="worker:one")
        self.assertEqual(self.ledger.get("521")["state"], before["state"])
        self.assertEqual(self.ledger.get("521")["version"], before["version"])
        self.assertEqual(len(self.ledger.events()), 1)

    def test_two_assignments_progress_independently(self):
        self.create("521")
        self.create("522", authority="grant:research", objective="objective:522")
        self.ledger.transition("521", "ready", "dispatch", "ready-521", actor_id="worker:one")
        self.ledger.transition("521", "running", "execute", "run-521", actor_id="worker:one")
        self.assertEqual(self.ledger.get("522")["state"], "queued")
        self.assertEqual(len(self.ledger.list_assignments()), 2)
        for state, step in [("ready", "dispatch"), ("running", "execute"),
                            ("awaiting_verification", "verify")]:
            self.ledger.transition("522", state, step, f"522-{state}", actor_id="worker:two")
        self.ledger.transition("522", "completed", "done", "522-done",
                               actor_id="worker:two", verified=True)
        self.assertEqual(self.ledger.get("522")["state"], "completed")
        self.assertTrue(self.ledger.events()[-1]["payload"]["verified_claim"])


if __name__ == "__main__":
    unittest.main()
