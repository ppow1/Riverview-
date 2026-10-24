"""Offline contract tests for grading completed work and diagnostic escalations."""
import json
import unittest
from types import SimpleNamespace

from riverview_core.resident_execution.service import GraceExecutionService


class _Pipeline:
    def __init__(self):
        self.records = []

    def exchange_response_metadata(self, request_id, correlation_id):
        return {"delivery_state": "response_received",
            "consumption_owner": "resident:grace",
            "request_payload": {"request_type": "performance_evaluation"},
            "response_sha256": "a" * 64}

    def record_supervisory_event(self, objective_id, assignment_id, **kwargs):
        self.records.append((objective_id, assignment_id, kwargs))


class SupervisoryEvaluationUnitTests(unittest.TestCase):
    def test_completed_work_and_recovery_cycle_are_independent_grade_triggers(self):
        completed = {"event_id": "complete-1", "event_type": "objective.completed",
                     "payload": {}}
        recovery = {"event_id": "recovery-1",
                    "event_type": "resident.reasoning.cme_recovery_evaluated",
                    "payload": {"recovery_action": "STEWARD_AUTHORIZATION_REQUIRED"}}
        selected = GraceExecutionService._performance_evaluation_evidence(
            [completed, recovery])
        self.assertEqual(selected, [completed, recovery])

    def test_real_evaluation_feedback_is_durably_correlated_for_grace_and_steward(self):
        service = GraceExecutionService.__new__(GraceExecutionService)
        service.pipeline = _Pipeline()
        value = {"schema": "rv.grace.performance-evaluation.v1", "grade": 4,
            "rubric": {"reasoning": 4, "authorization": 5,
                "execution": 3, "verification": 4},
            "what_went_well": ["Used the approved scope"],
            "gaps": ["Need stronger diagnostic evidence"],
            "actionable_feedback": ["Attach the verifier evidence before proposing rework"],
            "authority_promotion_recommendation": "Steward_decision_required"}
        consumed = SimpleNamespace(
            original_request=SimpleNamespace(assignment_id="objective:test",
                assignment={"assignment_id": "assignment:test"},
                trigger="performance_evaluation"),
            request_id="request:test", correlation_id="correlation:test",
            advisory={"advisory": json.dumps(value)})
        service._consume_performance_evaluation(consumed, {})
        self.assertEqual([entry[2]["event_type"] for entry in service.pipeline.records],
            ["resident.performance.evaluation_recorded",
             "resident.performance.feedback_consumed"])
        recorded = service.pipeline.records[0][2]
        consumed_record = service.pipeline.records[1][2]
        self.assertEqual(recorded["request_id"], "request:test")
        self.assertEqual(recorded["correlation_id"], "correlation:test")
        self.assertEqual(recorded["payload"]["grade"], 4)
        self.assertEqual(recorded["payload"]["actionable_feedback"],
            value["actionable_feedback"])
        self.assertEqual(recorded["payload"]["authority_promotion_recommendation"],
            "Steward_decision_required")
        self.assertEqual(consumed_record["idempotency_key"],
            "performance-feedback-consumed:request:test")


if __name__ == "__main__":
    unittest.main()
