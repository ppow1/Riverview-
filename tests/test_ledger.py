# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_ledger.py
# Component: CORE-LEDGER
# Revision: 1.0.0
# Purpose: Regression tests for SQLite development ledger
# Execution Model: Request-driven tests
# Observability: unittest results and exit code
# Dependencies: Python 3; sqlite3; riverview_core
# Authority: Temporary test databases only
# Changed: 2026-10-09 UTC | ENG-REV-004 | Initial controlled header migration
# Contracts: docs/architecture/EVENT_AND_ASSIGNMENT_CONTRACT_v0.1.md
# Tests: This file
# History: Git commit 6810e00374f50a81820be5f4e7714b329965ea66 and staged predecessor manifest
# =============================================================================

"""Run with python -m unittest discover -s tests -v (PYTHONPATH=src)."""
import tempfile
import unittest
from pathlib import Path
from riverview_core import Ledger, TransitionError

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "core.db"
        self.ledger = Ledger(self.path)

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def test_independent_assignments_and_reopen(self):
        self.ledger.create("521", "engineering", "create-521")
        self.ledger.create("522", "research", "create-522")
        self.ledger.transition("521", "ready", "dispatch", "ready-521")
        self.ledger.transition("521", "running", "execution", "run-521")
        self.assertEqual(self.ledger.get("522")["state"], "queued")
        self.ledger.close()
        self.ledger = Ledger(self.path)
        self.assertEqual(self.ledger.get("521")["state"], "running")
        self.assertEqual(len(self.ledger.events()), 4)

    def test_idempotent_event_and_illegal_transition(self):
        self.ledger.create("521", "engineering", "create-521")
        self.ledger.create("521", "engineering", "create-521")
        self.assertEqual(len(self.ledger.events()), 1)
        with self.assertRaises(TransitionError):
            self.ledger.transition("521", "completed", "done", "bad-complete", verified=True)
        self.assertEqual(self.ledger.get("521")["state"], "queued")

    def test_completion_requires_verification_flag(self):
        self.ledger.create("521", "engineering", "create-521")
        for state, step in [("ready", "dispatch"), ("running", "execute"), ("awaiting_verification", "verify")]:
            self.ledger.transition("521", state, step, state)
        with self.assertRaises(TransitionError):
            self.ledger.transition("521", "completed", "done", "complete")
        self.ledger.transition("521", "completed", "done", "complete", verified=True)
        self.assertEqual(self.ledger.get("521")["state"], "completed")

if __name__ == "__main__":
    unittest.main()
