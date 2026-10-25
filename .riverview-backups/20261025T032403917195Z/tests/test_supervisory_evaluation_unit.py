# RIVERVIEW~ CONTROLLED TEST SOURCE
# File: tests/test_supervisory_evaluation_unit.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.8
# Changed: 2026-10-25 UTC | RV-GRACE-REWORK-CONTROLLER-AUTHORITY-20261024 | Prove persisted reviewer authorization stops are controller-checked and logged without another 80B call.
# Changed: 2026-10-24 UTC | RV-GRACE-REWORK-SCOPE-DIAGNOSTIC-20261024 | Confirm fixed scope-validation codes are operator-visible without model text.
# Changed: 2026-10-24 UTC | RV-GRACE-PIN-RUNTIME-RELEASE-ID-20261024 | Verify an active pipeline keeps its startup release identity after runtime pointer changes.
# Changed: 2026-10-24 UTC | RV-GRACE-REWORK-REVIEW-DIAGNOSTICS-20261024 | Assert safe reviewer failure detail is correlated and private text is excluded.
# Purpose: Verify durable supervisory grading and bounded Luna retry selection
# Execution Model: Offline unit tests
# Observability: unittest assertions and exit status
# Dependencies: Grace execution service
# Authority: Tests only; no live supervisory requests
# Changed: 2026-10-24 UTC | RV-GRACE-PERFORMANCE-MINIMAL-RETRY-20261024 | Verify exactly one minimal-evidence retry after repeated HTTP 400 input rejection.
# Changed: 2026-10-24 UTC | RV-GRACE-PERFORMANCE-INPUT-RETRY-20261024 | Assert input-field retry gating and compact evidence preservation.
# Changed: 2026-10-24 UTC | RV-GRACE-CME-ESCALATION-ID-FALLBACK-20261024 | Assert every bounded CME attempt uses a distinct escalation identity.
# Changed: 2026-10-24 UTC | RV-GRACE-LUNA-SUPERVISORY-RETRY-20261024 | Assert bounded fallback and retry idempotency
# History: Git and .riverview-backups/manifest.jsonl
"""Offline contract tests for grading completed work and diagnostic escalations."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

from riverview_core.resident_execution.service import GraceExecutionService
from riverview_core.resident_execution.conversation import ConversationUnavailable
from riverview_core.resident_execution.pipeline import AuthorizedAssignmentIntake, GraceExecutionPipeline


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
    def test_pipeline_pins_runtime_release_identity_at_construction(self):
        ledger = object()
        intake = object.__new__(AuthorizedAssignmentIntake)
        intake.ledger = ledger
        first_release = "a" * 40
        next_release = "b" * 40
        with patch.object(GraceExecutionPipeline, "_discover_runtime_release_id",
                          return_value=first_release):
            pipeline = GraceExecutionPipeline(ledger, object(), intake, object())
        with patch.object(GraceExecutionPipeline, "_discover_runtime_release_id",
                          return_value=next_release):
            self.assertEqual(pipeline.runtime_release_id(), first_release)

    def test_rejected_rework_failure_logs_allowlisted_detail_without_free_text(self):
        from types import SimpleNamespace

        objective_id = "objective:test:rejected-review"
        assignment_id = "assignment:test:rejected-review"
        context = {"objective_id": objective_id, "assignment_id": assignment_id,
            "origin": {"conversation_id": "00000000-0000-0000-0000-000000000001",
                       "source_sequence": 1},
            "completion": {"verification_id": "00000000-0000-0000-0000-000000000002"},
            "rework_attempt_count": 0}
        pending = []
        pipeline = SimpleNamespace(MAX_GOVERNED_REWORK_ATTEMPTS=3,
            pending_rejected_work_order_reviews=lambda **_kwargs: [context],
            record_rework_escalation_pending=lambda _context, reason: pending.append(reason))
        service = object.__new__(GraceExecutionService)
        service.pipeline = pipeline
        service.dispatch_credential = "synthetic"
        service.verifiers = {}
        service.rejected_work_order_publisher = lambda _context: (_ for _ in ()).throw(
            ConversationUnavailable("bound reasoning provider unavailable"))

        with self.assertLogs("riverview.grace_execution", level="WARNING") as captured:
            self.assertEqual(service.publish_rejected_work_order_reviews(), 0)

        log_line = captured.output[0]
        record = json.loads(log_line[log_line.index("{"):])
        self.assertEqual(record["objective_id"], objective_id)
        self.assertEqual(record["assignment_id"], assignment_id)
        self.assertEqual(record["failure_stage"], "resident_rework_review")
        self.assertEqual(record["failure_detail"], "bound reasoning provider unavailable")
        self.assertEqual(pending, ["review_provider_unavailable"])
        self.assertNotIn("synthetic", captured.output[0])
        from riverview_core.resident_execution.service import _safe_rework_review_failure_detail
        self.assertEqual(_safe_rework_review_failure_detail(
            ConversationUnavailable("private provider echo")), "conversation_unavailable")
        self.assertEqual(_safe_rework_review_failure_detail(ConversationUnavailable(
            "Grace rework decision exceeded the original assignment scope: criteria_to_address_out_of_scope")),
            "Grace rework decision exceeded the original assignment scope: criteria_to_address_out_of_scope")
        self.assertIsNone(_safe_rework_review_failure_detail(RuntimeError("private text")))

    def test_persisted_authorization_stop_is_controller_checked_without_80b_call(self):
        objective_id = "objective:test:controller-preflight"
        assignment_id = "assignment:test:controller-preflight"
        context = {"objective_id": objective_id, "assignment_id": assignment_id,
            "origin": None, "prior_review_decision": {
                "decision": "STEWARD_AUTHORIZATION_REQUIRED",
                "rationale": "Reviewer claimed authorization was missing.",
                "review_generation": 2}, "completion": {
                "verification_id": "verification-test"}, "rework_attempt_count": 0}
        validation = {"objective_id": objective_id, "assignment_id": assignment_id,
            "reviewer_decision": context["prior_review_decision"],
            "authorization_lookup": {"active": True,
                "action": "resident.reasoning.escalate",
                "scope_ref": "provider:gpt-6-luna", "grant_id": "grant:test"},
            "request_history": [{"request_id": "request-failed",
                "request_type": "performance_evaluation", "provider_attempt_count": 1,
                "http_status": "400", "provider_error_param": "input"}],
            "performance_evaluation_events": {"evaluation_recorded": 0,
                "feedback_consumed": 0},
            "validation_outcome": "reviewer_authorization_stop_rejected_active_exact_grant",
            "next_action": "retain_rework_required_without_80b_or_luna_retry",
            "reason": "Grant is active; evaluation failed and is not a grade.",
            "verification": {"decision": "REJECTED"}}
        calls = []
        pipeline = SimpleNamespace(MAX_GOVERNED_REWORK_ATTEMPTS=3,
            pending_rejected_work_order_reviews=lambda **_kwargs: [context],
            record_rework_controller_validation=lambda ctx, decision: validation)
        service = object.__new__(GraceExecutionService)
        service.pipeline = pipeline
        service.dispatch_credential = "synthetic"
        service.verifiers = {}
        service.rejected_work_order_publisher = lambda ctx: calls.append(ctx)

        with self.assertLogs("riverview.grace_execution", level="WARNING") as captured:
            self.assertEqual(service.publish_rejected_work_order_reviews(), 0)

        self.assertEqual(calls, [])
        record = json.loads(captured.output[0][captured.output[0].find("{"):])
        self.assertEqual(record["objective_id"], objective_id)
        self.assertEqual(record["assignment_id"], assignment_id)
        self.assertTrue(record["authorization_lookup"]["active"])
        self.assertEqual(record["request_history"][0]["http_status"], "400")
        self.assertEqual(record["validation_outcome"],
            "reviewer_authorization_stop_rejected_active_exact_grant")
        self.assertIn("not a grade", record["reason"])

    def test_cme_diagnostic_attempts_have_distinct_escalation_identities(self):
        event_id = "c7558b01-8004-4a44-8344-4bf0fe0ae27e"
        identify = GraceExecutionService._cme_diagnostic_escalation_id
        values = [identify(event_id, attempt) for attempt in range(1, 5)]
        self.assertEqual(len(set(values)), 4)
        self.assertEqual(values[3], str(uuid5(NAMESPACE_URL,
            "rv-cme-recovery-escalation:" + event_id + ":bounded-output-fallback-1")))
        with self.assertRaisesRegex(ValueError, "unsupported_cme_diagnostic_attempt"):
            identify(event_id, 5)

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

    def test_input_field_retry_is_exact_and_compacts_optional_history_once(self):
        choose = GraceExecutionService._select_performance_evaluation_request
        trigger = "step-event"
        prior = {"request_id": "old", "delivery_state": "grace_consumed",
            "request_payload": {"max_tokens": 512}}
        retry1 = {"request_id": "retry1", "delivery_state": "failed",
            "last_error_code": "provider_response_submission_failed",
            "request_payload": {"max_tokens": 2048}}
        retry2 = {"request_id": "retry2", "delivery_state": "failed",
            "last_error_code": "provider_response_submission_failed",
            "provider_http_status": 400, "provider_error_param": "input",
            "request_payload": {"max_tokens": 512}}
        retry3 = {"request_id": "retry3", "delivery_state": "failed",
            "last_error_code": "provider_response_submission_failed",
            "provider_http_status": 400, "provider_error_param": "input",
            "request_payload": {"max_tokens": 512}}
        key = "performance-evaluation:step-event:bounded-input-retry-1"
        self.assertEqual(choose(trigger, prior, retry1, {"old"}, retry2), key)
        self.assertIsNone(choose(trigger, prior, retry1, {"old"},
            {**retry2, "provider_error_param": "max_output_tokens"}))
        self.assertIsNone(choose(trigger, prior, retry1, {"old"},
            {**retry2, "provider_http_status": 429}))
        self.assertIsNone(choose(trigger, prior, retry1, {"old"}, retry2,
            {"request_id": "retry3"}))
        self.assertEqual(choose(trigger, prior, retry1, {"old"}, retry2, retry3),
            "performance-evaluation:step-event:bounded-input-retry-2")
        self.assertIsNone(choose(trigger, prior, retry1, {"old"}, retry2, retry3,
            {"request_id": "retry4"}))
        source = {"proposal": {"summary": "s" * 1000,
            "steps": [{"step_id": str(index), "objective": "o" * 300,
                "acceptance_criteria": ["c" * 200] * 5} for index in range(8)]},
            "evidence": [{"event_id": str(index)} for index in range(9)],
            "reasoning_history": [{"event_id": str(index)} for index in range(10)],
            "exchange_history": [{"event_id": str(index)} for index in range(10)],
            "reasoning_failure_count": 37}
        compact = GraceExecutionService._compact_performance_evaluation_assignment(source)
        self.assertEqual(len(compact["evidence"]), 6)
        self.assertEqual(len(compact["reasoning_history"]), 4)
        self.assertEqual(len(compact["exchange_history"]), 4)
        self.assertEqual(compact["reasoning_failure_count"], 37)
        self.assertEqual(len(compact["proposal"]["summary"]), 400)
        self.assertEqual(len(compact["proposal"]["steps"]), 5)
        self.assertEqual(len(compact["proposal"]["steps"][0]["objective"]), 180)
        minimal = GraceExecutionService._minimal_performance_evaluation_assignment(source | {
            "objective_id": "objective:test", "objective_revision": 8,
            "assignment_id": "assignment:test", "proposal_id": "proposal:test",
            "proposal_revision": 2, "evaluation_trigger_event_id": "event:test",
            "reasoning_attempt_count": 10})
        self.assertEqual(set(minimal), {"objective_id", "objective_revision", "assignment_id",
            "proposal_id", "proposal_revision", "evaluation_trigger_event_id",
            "reasoning_attempt_count", "reasoning_failure_count", "proposal", "evidence"})
        self.assertEqual(set(minimal["evidence"][0]["payload"]), set())

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
