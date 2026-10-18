# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_supervised_codex_dispatch.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.2
# Purpose: Verify the supervised Codex cycle remains pinned to one proposed objective
# Execution Model: In-memory contract fixtures; no database or account credentials
# Observability: Assertions inspect objective, assignment, verifier, and completion calls
# Dependencies: Python 3; unittest
# Authority: No live service or institutional grant is created
# Changed: 2026-10-13 UTC | RV-SUPERVISED-CODEX-DISPATCH-001 | Add exact-objective cycle contract checks
# Changed: 2026-10-13 UTC | RV-SUPERVISED-CODEX-DISPATCH-001 | Assert the database claim carries the selected assignment identity
# Changed: 2026-10-16 UTC | RV-GRACE-SCHEDULER-PROBE-COMPAT | Model the optional resident-schema probe before inspecting the claim filter
# Contracts: src/riverview_core/resident_execution/service.py
# Tests: python3 -m unittest tests.test_supervised_codex_dispatch -v
# History: Git
# =============================================================================
"""Unit checks for the explicitly selected supervised Engineering assignment."""

from __future__ import annotations

import hashlib
import unittest
from unittest.mock import Mock

from riverview_core.resident_execution.service import GraceExecutionService
from riverview_core.assignment_scheduler.scheduler import PostgresAssignmentScheduler


class SupervisedCodexDispatchTests(unittest.TestCase):
    def make_service(self, objective):
        assignment_id = "assignment:grace:" + hashlib.sha256(
            objective["objective_id"].encode("utf-8")).hexdigest()[:40]
        service = object.__new__(GraceExecutionService)
        service.authority_ref = "work-order:engineering"
        service.pipeline = Mock()
        service.pipeline.get_objective.side_effect = [
            objective,
            {**objective, "status": "WORK_ORDER_CREATED", "assignment_id": assignment_id},
        ]
        service.pipeline.ledger.get.return_value = {"id": assignment_id, "state": "ready"}
        service.worker = Mock()
        service.worker.run_once.return_value = {"status": "AWAITING_VERIFICATION"}
        service.dispatch_proposed = Mock(return_value=1)
        service.verify_one = Mock(return_value=True)
        service.reconcile_completions = Mock(return_value=1)
        service._heartbeat = Mock()
        return service, assignment_id

    def test_execution_dispatch_and_verification_are_pinned_to_selected_objective(self):
        objective_id = "objective:supervised-test"
        service, assignment_id = self.make_service({
            "objective_id": objective_id,
            "scope_ref": "work-order:engineering",
            "status": "PROPOSED",
            "proposal": {"summary": "A bounded task"},
        })

        result = service.execute_supervised_objective(objective_id)

        self.assertEqual(result["status"], "COMPLETED")
        service.dispatch_proposed.assert_called_once_with(objective_id)
        service.worker.run_once.assert_called_once_with(assignment_id=assignment_id)
        service.verify_one.assert_called_once_with(assignment_id)
        service.reconcile_completions.assert_called_once_with(objective_id=objective_id)

    def test_other_scope_is_not_dispatched(self):
        objective_id = "objective:other-scope"
        service, _ = self.make_service({
            "objective_id": objective_id,
            "scope_ref": "work-order:other",
            "status": "PROPOSED",
            "proposal": {"summary": "Out of scope"},
        })

        result = service.execute_supervised_objective(objective_id)

        self.assertEqual(result["status"], "WAITING_FOR_PROPOSAL")
        service.dispatch_proposed.assert_not_called()
        service.worker.run_once.assert_not_called()

    def test_invalid_objective_identity_is_rejected(self):
        service = object.__new__(GraceExecutionService)
        with self.assertRaises(ValueError):
            service.execute_supervised_objective("assignment:wrong-kind")

    def test_scheduler_claim_query_carries_exact_assignment_filter(self):
        class Cursor:
            calls = []
            rows = [{"available": False}, None]

            def execute(self, query, params):
                self.calls.append((query, params))

            def fetchone(self):
                return self.rows.pop(0)

        cursor = Cursor()
        PostgresAssignmentScheduler._claim_candidate(cursor, "worker:test", 30,
            scope_ref="work-order:engineering", assignment_id="assignment:one")

        self.assertIn("to_regclass(current_schema() || '.grace_objectives')", cursor.calls[0][0])
        self.assertEqual(cursor.calls[0][1], ())
        self.assertIn("(%s::text IS NULL OR a.id=%s)", cursor.calls[1][0])
        self.assertEqual(cursor.calls[1][1], ("work-order:engineering",
            "work-order:engineering", "assignment:one", "assignment:one"))


if __name__ == "__main__":
    unittest.main()
