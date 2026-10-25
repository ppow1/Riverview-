# RIVERVIEW~ CONTROLLED TEST SOURCE
# File: tests/test_supervisory_evaluation_unit.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.15
# Changed: 2026-10-25 UTC | RV-GRACE-S4-EVAL-TRIGGER-20261025 | Distinguish S4 exhausted-rejection evaluation triggers from already-evaluated S3 verification evidence.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-REPLAY-CORRELATION-20261025 | Cover source-assignment replay, durable child membership, and revision-10 single-use admission.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-REWORK-EXCEPTION-20261025 | Require exact durable evaluation evidence before issuing an S4 exception.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-EVALUATION-RECOVERY-20261025 | Cover response alias normalization, consumed-response replay, diagnostics, and exhausted-rework CME suppression.
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Reject authorization requests outside the exact Steward-approved tuple.
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Cover exact event-authorized retry selection without changing ordinary retries.
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
        self.exchange_metadata = None

    def exchange_response_metadata(self, request_id, correlation_id):
        return self.exchange_metadata or {"delivery_state": "response_received",
            "consumption_owner": "resident:grace", "provider_id": "gpt-6-luna",
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
        values = [identify(event_id, attempt) for attempt in range(1, 6)]
        self.assertEqual(len(set(values)), 5)
        self.assertEqual(values[3], str(uuid5(NAMESPACE_URL,
            "rv-cme-recovery-escalation:" + event_id + ":bounded-output-fallback-1")))
        self.assertEqual(values[4], str(uuid5(NAMESPACE_URL,
            "rv-cme-recovery-escalation:" + event_id + ":steward-authorized-retry-1")))
        with self.assertRaisesRegex(ValueError, "unsupported_cme_diagnostic_attempt"):
            identify(event_id, 6)

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

    def test_event_scoped_s3_retry_requires_authorization_and_admission_denial(self):
        from riverview_core.resident_execution.service import GraceExecutionService

        event_id = "8671a141-da3c-47c5-960d-324e3c51eeef"
        failed = {"delivery_state": "failed",
                  "last_error_code": "provider_response_submission_failed"}
        denied_fallback = {"delivery_state": "failed",
                           "last_error_code": "provider_attempt_admission_blocked"}
        choose = GraceExecutionService._select_cme_diagnostic_request
        expected = (5, "cme-recovery:" + event_id + ":steward-authorized-retry-1")
        self.assertEqual(choose(event_id, failed, failed, None, 0,
            prior_bounded_fallback=denied_fallback,
            event_retry_authorized=True), expected)
        self.assertEqual(choose(event_id, failed, failed, None, 0,
            prior_bounded_fallback=denied_fallback,
            event_retry_authorized=False), (None, None))
        self.assertEqual(choose(event_id, failed, failed, None, 0,
            prior_bounded_fallback={"delivery_state": "failed",
                "last_error_code": "provider_response_submission_failed"},
            event_retry_authorized=True), (None, None))

    def test_s3_retry_authorization_rejects_scope_mismatch_before_database_access(self):
        from riverview_core.resident_execution.grace_supervisory_authorization import (
            GraceSupervisoryAuthorization,
        )

        authority = object.__new__(GraceSupervisoryAuthorization)
        with self.assertRaisesRegex(PermissionError, "cme_retry_exception_scope_mismatch"):
            authority.authorize_one_s3_cme_retry(
                actor_id="steward:camrui",
                authorization_id="556cfa24-0a55-5000-9b31-c11242d749a4",
                objective_id="objective:other", objective_revision=8,
                objective_assignment_id=("assignment:grace:de19cd78b86f1889d32cdf02c6d3fe51d4658834"),
                stall_event_id="8671a141-da3c-47c5-960d-324e3c51eeef",
                progress_sequence=223, explicit_steward_confirmation=True)

    def test_completed_work_and_recovery_cycle_are_independent_grade_triggers(self):
        completed = {"event_id": "complete-1", "event_type": "objective.completed",
                     "payload": {}}
        recovery = {"event_id": "recovery-1",
                    "event_type": "resident.reasoning.cme_recovery_evaluated",
                    "payload": {"recovery_action": "STEWARD_AUTHORIZATION_REQUIRED"}}
        selected = GraceExecutionService._performance_evaluation_evidence(
            [completed, recovery])
        self.assertEqual(selected, [completed, recovery])

    def test_s4_retry_limit_rejection_is_a_distinct_grade_trigger(self):
        s3 = {"event_id":"s3-verified","event_type":"execution.step_verified",
            "payload":{"assignment_id":"assignment:s3","step_id":"s3"}}
        s4_hold = {"event_id":"s4-rejection-hold",
            "event_type":"engineering.rework_escalation_pending",
            "payload":{"assignment_id":"assignment:s4","step_id":"s4",
                "decision":"ESCALATION_PENDING","reason_code":"retry_limit_exhausted",
                "verification_id":"54d1fb2f-411e-4771-a137-785d2b620de7"}}
        unrelated_hold = {"event_id":"other-hold",
            "event_type":"engineering.rework_escalation_pending",
            "payload":{"assignment_id":"assignment:other","step_id":"s4",
                "decision":"ESCALATION_PENDING","reason_code":"review_provider_unavailable"}}
        selected = GraceExecutionService._performance_evaluation_evidence(
            [s3, unrelated_hold, s4_hold])
        self.assertEqual(selected, [s3, s4_hold])
        self.assertEqual(GraceExecutionService._select_performance_evaluation_request(
            s4_hold["event_id"], None, None, set()),
            "performance-evaluation:s4-rejection-hold")

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

    def test_known_luna_schema_aliases_are_normalized_without_mutating_response(self):
        service = GraceExecutionService.__new__(GraceExecutionService)
        service.pipeline = _Pipeline()
        value = {"schema_version": "rv.grace.performance-evaluation.v1", "grade": 2,
            "grade_explanation": "The durable evidence is usable.",
            "rubric_scores": {"reasoning": 2, "authorization": 3,
                "execution": 2, "verification": 2},
            "what_went_well": ["The review used persisted evidence"],
            "gaps": ["The S4 artifact omitted the durable exchange reference"],
            "actionable_feedback": ["Reference the exact response and usage fields"],
            "authority_promotion_recommendation": "Steward_decision_required"}
        raw = json.dumps(value)
        consumed = SimpleNamespace(original_request=SimpleNamespace(
            assignment_id="objective:test", assignment={"assignment_id":"assignment:test",
                "evaluation_trigger_event_id":"trigger:test"}, trigger="performance_evaluation"),
            request_id="request:alias", correlation_id="correlation:alias",
            advisory={"advisory": raw})
        service._consume_performance_evaluation(consumed, {})
        self.assertEqual(json.loads(consumed.advisory["advisory"]), value)
        self.assertEqual(service.pipeline.records[0][2]["payload"]["rubric"],
            value["rubric_scores"])
        with self.assertRaisesRegex(ValueError, "supervisory_advisory_schema_invalid"):
            service._json_advisory(SimpleNamespace(advisory={"advisory": json.dumps(
                value | {"schema": value["schema_version"]})}),
                "rv.grace.performance-evaluation.v1",
                {"schema", "grade", "grade_explanation", "rubric", "what_went_well",
                 "gaps", "actionable_feedback", "authority_promotion_recommendation"})

    def test_already_consumed_exchange_is_accepted_only_with_matching_result_hash(self):
        service = GraceExecutionService.__new__(GraceExecutionService)
        service.pipeline = _Pipeline()
        service.pipeline.exchange_metadata = {"delivery_state":"grace_consumed",
            "consumption_owner":None,
            "consumption_key":"external-reasoning-consumed:request:replay",
            "consumption_result":{"advisory_sha256":"a"*64},
            "provider_id":"gpt-6-luna",
            "request_payload":{"request_type":"performance_evaluation"},
            "response_sha256":"a"*64}
        value = {"schema":"rv.grace.performance-evaluation.v1", "grade":2,
            "grade_explanation":"Persisted grade", "rubric":{"reasoning":2,
            "authorization":3,"execution":2,"verification":2},
            "what_went_well":[],"gaps":[],"actionable_feedback":[],
            "authority_promotion_recommendation":"Steward_decision_required"}
        consumed = SimpleNamespace(original_request=SimpleNamespace(
            assignment_id="objective:test", assignment={"assignment_id":"assignment:test",
                "evaluation_trigger_event_id":"event:test"}, trigger="performance_evaluation"),
            request_id="request:replay", correlation_id="correlation:replay",
            advisory={"advisory":json.dumps(value)})
        service._consume_performance_evaluation(consumed, {})
        self.assertEqual(len(service.pipeline.records), 2)
        service.pipeline.exchange_metadata["consumption_result"]["advisory_sha256"] = "b"*64
        with self.assertRaisesRegex(ValueError, "performance_exchange_response_correlation_invalid"):
            service._consume_performance_evaluation(consumed, {})

    def test_cme_diagnostics_stop_only_for_exhausted_rework_with_durable_hold(self):
        decide = GraceExecutionService._cme_rework_retry_exhausted
        self.assertTrue(decide({"attempts":3,"exhausted_hold":True},3))
        self.assertFalse(decide({"attempts":3,"exhausted_hold":False},3))
        self.assertFalse(decide({"attempts":2,"exhausted_hold":True},3))
        self.assertFalse(decide(None,3))

    def test_s4_exception_is_exact_expiring_and_single_use(self):
        from datetime import datetime, timedelta, timezone
        choose = GraceExecutionPipeline._available_s4_rework_exception
        from riverview_core.resident_execution.grace_supervisory_authorization import (
            S4_REWORK_ASSIGNMENT_ID,S4_REWORK_OBJECTIVE_ID,S4_REWORK_VERIFICATION_ID)
        event_id="event:s4-rework-grant"
        current_assignment="assignment:current-s4"
        grant={"event_id":event_id,"idempotency_key":
            "grace-s4-rework-authorized:"+S4_REWORK_VERIFICATION_ID,
            "event_type":"engineering.rework_retry_authorized","actor_id":"steward:camrui",
            "payload":{
                "schema":"rv.grace.rework-retry-exception.v1",
                "authorized_by":"steward:camrui","objective_id":S4_REWORK_OBJECTIVE_ID,
                "objective_revision":10,"objective_assignment_id":current_assignment,
                "assignment_id":S4_REWORK_ASSIGNMENT_ID,"step_id":"s4",
                "verification_id":S4_REWORK_VERIFICATION_ID,"additional_attempts":1,
                "evaluation_request_id":"a157f40f-03b1-4ea8-8f8e-13fa69a087d2",
                "evaluation_trigger_event_id":"254cf59d-34cb-4f44-aac3-867cc83f760d",
                "evaluation_response_sha256":"a"*64,
                "expires_at":(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()}}
        args=(S4_REWORK_OBJECTIVE_ID,S4_REWORK_ASSIGNMENT_ID,S4_REWORK_VERIFICATION_ID)
        self.assertIsNotNone(choose([grant],*args,objective_revision=10,
            objective_assignment_id=current_assignment))
        self.assertIsNone(choose([grant],*args,objective_revision=9,
            objective_assignment_id=current_assignment))
        self.assertIsNone(choose([grant],*args,objective_revision=10,
            objective_assignment_id="assignment:stale-pointer"))
        self.assertIsNone(choose([grant],"objective:other",*args[1:],
            objective_revision=10,objective_assignment_id=current_assignment))
        consumed={"event_id":"event:consumed","event_type":"engineering.rework_retry_consumed",
            "payload":{"grant_event_id":event_id}}
        self.assertIsNone(choose([grant,consumed],*args,objective_revision=10,
            objective_assignment_id=current_assignment))
        from riverview_core.resident_execution.grace_supervisory_authorization import (
            GraceSupervisoryAuthorization)
        authority=object.__new__(GraceSupervisoryAuthorization)
        with self.assertRaisesRegex(PermissionError,"s4_rework_exception_scope_mismatch"):
            authority.authorize_one_s4_rework_attempt(actor_id="steward:camrui",
                objective_id="objective:wrong",objective_revision=10,
                objective_assignment_id="assignment:wrong",assignment_id="assignment:wrong",
                verification_id=S4_REWORK_VERIFICATION_ID,assignment_credential="unused",
                explicit_steward_confirmation=True)

    def test_s4_rework_exception_requires_replayed_evaluation_evidence(self):
        from riverview_core.resident_execution.grace_supervisory_authorization import (
            GraceSupervisoryAuthorization,S4_REWORK_OBJECTIVE_ID,
            S4_REWORK_ASSIGNMENT_ID,S4_REWORK_VERIFICATION_ID)
        pipeline=SimpleNamespace(
            performance_evaluation_runtime_evidence_for_assignment=lambda *_args:None)
        authority=object.__new__(GraceSupervisoryAuthorization)
        authority.pipeline=pipeline
        authority.ledger=object()
        with self.assertRaisesRegex(PermissionError,
                "s4_durable_performance_evaluation_required"):
            authority.authorize_one_s4_rework_attempt(actor_id="steward:camrui",
                objective_id=S4_REWORK_OBJECTIVE_ID,
                objective_revision=10,
                objective_assignment_id=S4_REWORK_ASSIGNMENT_ID,
                assignment_id=S4_REWORK_ASSIGNMENT_ID,
                verification_id=S4_REWORK_VERIFICATION_ID,
                assignment_credential="unused",explicit_steward_confirmation=True)

    def test_supervisory_failure_code_excludes_arbitrary_exception_text(self):
        from riverview_core.resident_execution.service import _safe_supervisory_failure_code
        self.assertEqual(_safe_supervisory_failure_code(
            ValueError("performance_exchange_response_correlation_invalid")),
            "performance_exchange_response_correlation_invalid")
        self.assertEqual(_safe_supervisory_failure_code(
            RuntimeError("secret token and private payload")),
            "supervisory_consumer_failed")

    def test_consumed_evaluation_replay_records_without_provider_invocation(self):
        service=GraceExecutionService.__new__(GraceExecutionService)
        service.pipeline=_Pipeline()
        service.pipeline.pending_consumed_performance_evaluation_replays=lambda **_kwargs:[{
            "objective_id":"objective:test","assignment_id":"assignment:test",
            "request_id":"request:replay","correlation_id":"correlation:replay"}]
        service.pipeline.exchange_metadata={"delivery_state":"grace_consumed",
            "consumption_owner":None,
            "consumption_key":"external-reasoning-consumed:request:replay",
            "consumption_result":{"advisory_sha256":"a"*64},
            "provider_id":"gpt-6-luna",
            "request_payload":{"request_type":"performance_evaluation"},
            "response_sha256":"a"*64}
        value={"schema":"rv.grace.performance-evaluation.v1","grade":2,
            "grade_explanation":"Persisted response is valid.","rubric":{
                "reasoning":2,"authorization":3,"execution":2,"verification":2},
            "what_went_well":[],"gaps":[],"actionable_feedback":[],
            "authority_promotion_recommendation":"Steward_decision_required"}
        consumed=SimpleNamespace(duplicate=True,consumption_key=
            "external-reasoning-consumed:request:replay",consumption_token="",fence=1,
            request_id="request:replay",correlation_id="correlation:replay",
            advisory={"advisory":json.dumps(value)},original_request=SimpleNamespace(
                assignment_id="objective:test",trigger="performance_evaluation",
                assignment={"assignment_id":"assignment:test",
                    "evaluation_trigger_event_id":"trigger:test"}))
        class Exchange:
            calls=[]
            def pending_responses(_self,_principal,limit): return []
            def consume(_self,*args,**kwargs):
                self.assertEqual(args,("request:replay","correlation:replay"))
                _self.calls.append("consume")
                return consumed
            def acknowledge_consumed(_self,*args,**kwargs):
                _self.calls.append("ack")
                return "grace_consumed"
        exchange=Exchange(); service.external_reasoning_exchange=exchange
        service.resident_reasoner=object(); service.external_reasoning_principal="resident:grace"
        service.external_reasoning_authorize=lambda *_args,**_kwargs:True
        self.assertEqual(service.consume_external_reasoning(),1)
        self.assertEqual(exchange.calls,["consume","ack"])
        self.assertEqual([row[2]["event_type"] for row in service.pipeline.records],
            ["resident.performance.evaluation_recorded",
             "resident.performance.feedback_consumed"])

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
