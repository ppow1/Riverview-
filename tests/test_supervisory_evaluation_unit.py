# RIVERVIEW~ CONTROLLED TEST SOURCE
# File: tests/test_supervisory_evaluation_unit.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.1
# Purpose: Verify durable supervisory grading and bounded Luna retry selection
# Execution Model: Offline unit tests
# Observability: unittest assertions and exit status
# Dependencies: Grace execution service
# Authority: Tests only; no live supervisory requests
# Changed: 2026-10-24 UTC | RV-GRACE-LUNA-SUPERVISORY-RETRY-20261024 | Assert bounded fallback and retry idempotency
# History: Git and .riverview-backups/manifest.jsonl
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
    def test_cme_uses_only_one_explicitly_amended_request_after_failed_transport_retries(self):
        event_id = "c7558b01-8004-4a44-8344-4bf0fe0ae27e"
        failed = {"delivery_state": "failed",
                  "last_error_code": "provider_response_submission_failed"}
        pending = {"delivery_state": "awaiting_response", "last_error_code": None}
        amendment = {"payload": {"additional_request_allocations": {
            "cme_diagnostic_recovery": 1, "performance_evaluation": 1}}}
        select = GraceExecutionService._select_cme_diagnostic_request
        self.assertEqual(select(event_id, None, None, None, 0),
            (1, "cme-recovery:" + event_id))
        self.assertEqual(select(event_id, failed, None, None, 0),
            (2, "cme-recovery:" + event_id + ":transport-retry-1"))
        self.assertEqual(select(event_id, failed, failed, amendment, 0),
            (3, "cme-recovery:" + event_id + ":authorized-amendment-diagnostic-1"))
        self.assertEqual(select(event_id, failed, failed, None, 0),
            (4, "cme-recovery:" + event_id + ":bounded-output-fallback-1"))
        self.assertEqual(select(event_id, failed, failed, amendment, 1),
            (4, "cme-recovery:" + event_id + ":bounded-output-fallback-1"))
        self.assertEqual(select(event_id, pending, failed, amendment, 0), (None, None))
        self.assertEqual(select(event_id, failed, pending, amendment, 0), (None, None))

    def test_completed_work_and_recovery_cycle_are_independent_grade_triggers(self):
        completed = {"event_id": "complete-1", "event_type": "objective.completed",
                     "payload": {}}
        recovery = {"event_id": "recovery-1",
                    "event_type": "resident.reasoning.cme_recovery_evaluated",
                    "payload": {"recovery_action": "STEWARD_AUTHORIZATION_REQUIRED"}}
        selected = GraceExecutionService._performance_evaluation_evidence(
            [completed, recovery])
        self.assertEqual(selected, [completed, recovery])

    def test_evaluation_retry_is_limited_to_one_proven_truncation(self):
        choose = GraceExecutionService._select_performance_evaluation_request
        trigger = "step-event"
        prior = {"request_id": "old-request", "delivery_state": "grace_consumed",
            "request_payload": {"max_tokens": 512}}
        retry_key = "performance-evaluation:step-event:bounded-output-retry-1"
        retry2_key = "performance-evaluation:step-event:bounded-output-retry-2"
        self.assertEqual(choose(trigger, None, None, set()),
            "performance-evaluation:step-event")
        self.assertEqual(choose(trigger, prior, None, {"old-request"}), retry_key)
        self.assertIsNone(choose(trigger, prior, None, set()))
        self.assertIsNone(choose(trigger, prior, {"request_id": "retry"}, {"old-request"}))
        failed_retry = {"request_id": "retry", "delivery_state": "failed",
            "last_error_code": "provider_response_submission_failed",
            "request_payload": {"max_tokens": 2048}}
        self.assertEqual(choose(trigger, prior, failed_retry, {"old-request"}), retry2_key)
        self.assertIsNone(choose(trigger, prior, failed_retry, {"old-request"},
            {"request_id": "retry-2"}))
        self.assertIsNone(choose(trigger, prior, {**failed_retry,
            "request_payload": {"max_tokens": 512}}, {"old-request"}))
        self.assertIsNone(choose(trigger, prior, {**failed_retry,
            "delivery_state": "grace_consumed"}, {"old-request"}))
        self.assertIsNone(choose(trigger, {**prior,
            "request_payload": {"max_tokens": 2048}}, None, {"old-request"}))
        self.assertIsNone(choose(trigger, {**prior,
            "delivery_state": "awaiting_response"}, None, {"old-request"}))

    def test_real_evaluation_feedback_is_durably_correlated_for_grace_and_steward(self):
        service = GraceExecutionService.__new__(GraceExecutionService)
        service.pipeline = _Pipeline()
        value = {"schema": "rv.grace.performance-evaluation.v1", "grade": 4,
            "grade_explanation": "Planning respected scope; the verifier evidence supports the result.",
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
        self.assertEqual(recorded["payload"]["grade_explanation"], value["grade_explanation"])
        self.assertEqual(recorded["payload"]["actionable_feedback"],
            value["actionable_feedback"])
        self.assertEqual(recorded["payload"]["authority_promotion_recommendation"],
            "Steward_decision_required")
        self.assertEqual(consumed_record["idempotency_key"],
            "performance-feedback-consumed:request:test")

    def test_partial_or_missing_grade_explanation_is_not_recorded(self):
        service = GraceExecutionService.__new__(GraceExecutionService)
        service.pipeline = _Pipeline()
        consumed = SimpleNamespace(
            original_request=SimpleNamespace(assignment_id="objective:test",
                assignment={"assignment_id": "assignment:test"},
                trigger="performance_evaluation"),
            request_id="request:partial", correlation_id="correlation:partial",
            advisory={"advisory": '{"schema":"rv.grace.performance-evaluation.v1",'
                '"grade":2,"rubric":{},"what_went_well":[],"gaps":[]}'})
        with self.assertRaises((json.JSONDecodeError, ValueError)):
            service._consume_performance_evaluation(consumed, {})
        self.assertEqual(service.pipeline.records, [])


if __name__ == "__main__":
    unittest.main()
