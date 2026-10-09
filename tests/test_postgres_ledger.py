"""Run only when RIVERVIEW_TEST_PG_DSN is set.

Uses a unique schema for each test; no production tables are modified.
"""
import os
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")

@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class PostgresLedgerTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from riverview_core.postgres_ledger import PostgresLedger
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        from psycopg import sql
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.ledger = PostgresLedger(DSN, schema=self.schema)

    def tearDown(self):
        from psycopg import sql
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def test_persistence_and_independent_assignments(self):
        from riverview_core.postgres_ledger import PostgresLedger
        self.ledger.create("521", "engineering", "create-521")
        self.ledger.create("522", "research", "create-522")
        self.ledger.transition("521", "ready", "dispatch", "ready-521")
        self.ledger.transition("521", "running", "execution", "run-521")
        self.assertEqual(self.ledger.get("522")["state"], "queued")
        self.ledger.close()
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.assertEqual(self.ledger.get("521")["state"], "running")
        self.assertEqual(len(self.ledger.events()), 4)

    def test_idempotency_and_illegal_transition(self):
        from riverview_core.ledger import TransitionError
        self.ledger.create("521", "engineering", "create-521")
        self.ledger.create("521", "engineering", "create-521")
        self.assertEqual(len(self.ledger.events()), 1)
        with self.assertRaises(TransitionError):
            self.ledger.transition("521", "completed", "done", "bad-complete", verified=True)
        self.assertEqual(self.ledger.get("521")["state"], "queued")

    def test_completion_requires_verification_flag(self):
        from riverview_core.ledger import TransitionError
        self.ledger.create("521", "engineering", "create-521")
        for state, step in [("ready", "dispatch"), ("running", "execute"), ("awaiting_verification", "verify")]:
            self.ledger.transition("521", state, step, state)
        with self.assertRaises(TransitionError):
            self.ledger.transition("521", "completed", "done", "complete")
        self.ledger.transition("521", "completed", "done", "complete", verified=True)
        self.assertEqual(self.ledger.get("521")["state"], "completed")


if __name__ == "__main__":
    unittest.main()
