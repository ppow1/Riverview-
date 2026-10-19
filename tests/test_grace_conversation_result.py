# Riverview~ controlled test
# File: tests/test_grace_conversation_result.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.5
# Purpose: Verify 80B result review is authorized, bounded and idempotently linked to chat
# Changed: 2026-10-19 UTC | RV-GRACE-REREVIEW-PG-QUALIFICATION | Assert expanded typed review never invokes continuation handler
# Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-GENERATIONS-001 | Cover bounded evidence revision generations and per-generation idempotency
# Changed: 2026-10-16 UTC | RV-GRACE-STRUCTURED-REVIEW-001 | Cover typed completion decisions and same-scope continuation handoff
# Changed: 2026-10-16 UTC | RV-GRACE-RESULT-RETURN-DIAGNOSTICS-001 | Verify deferred result-review diagnostics are bounded and content-free
# Execution Model: Deterministic in-memory adapters; no database or inference endpoint
# Observability: Assert source identity, provider provenance and single durable response
# Authority: Fakes exact-grant decisions; live authority remains PostgreSQL enforced
"""Isolated tests for Grace's verified Engineering result return path."""

import unittest
import hashlib
import json
from types import SimpleNamespace

from riverview_core.resident_execution.conversation import ResidentConversationService
from riverview_core.resident_execution.conversation import ConversationUnavailable
from riverview_core.resident_execution.model_router import GraceModelRouter
from riverview_core.resident_execution.model_router import ReasoningDeferred
from riverview_core.resident_execution.service import GraceExecutionService


class FakeStore:
    def __init__(self):
        self.responses = {}

    def has_assistant_response(self, request_id):
        return str(request_id) in self.responses

    def assistant_response_receipt(self, request_id):
        row = self.responses.get(str(request_id))
        return row.get("receipt") if row else None

    def finish_work_order_review(self, conversation_id, request_id, **fields):
        key = str(request_id)
        if key in self.responses:
            return False
        self.responses[key] = {"conversation_id": conversation_id, **fields,
            "receipt": {"provider_id": fields["metadata"]["final_served_provider"],
                "served_model": fields["model_id"],
                "implementation_id": fields["implementation"]["implementation_id"],
                "completion_cycle": fields["metadata"]["completion_cycle"],
                "review_generation": fields["metadata"].get("review_generation", "1"),
                "review_evidence_revision": fields["metadata"].get(
                    "review_evidence_revision", ""),
                "review_evidence_sha256": fields["metadata"].get(
                    "review_evidence_sha256", ""),
                "review_decision": fields["metadata"].get("review_decision")}}
        return True


class FakeRegistry:
    def __init__(self, binding):
        self.binding = binding

    def authorize_office_state(self, _credential, _office_id):
        return dict(self.binding)


class FakeRouter:
    provider_id = GraceModelRouter.provider_id
    model = "grace-readiness-router"
    model_sha256 = "r" * 64

    def __init__(self):
        self.calls = []
        self.on_complete = None
        self.failure = None

    def supports_capability(self, capability):
        return capability == "grace.reasoning.80b"

    def complete_chat(self, messages, *, max_tokens, expected_revision, required_capability):
        self.calls.append((messages, max_tokens, expected_revision, required_capability))
        if self.failure is not None:
            raise self.failure
        if self.on_complete is not None:
            self.on_complete()
        return SimpleNamespace(content=getattr(self, "content", json_complete()),
            served_model="Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf",
            reasoning_stage="reasoning", finish_reason="stop", provider_attempts=(),
            provider_id="local.inference.v1")


def valid_context():
    return {"objective_id":"objective:grace-conversation:demo",
        "assignment_id":"assignment:grace:demo",
        "request":"Create a short engineering report.",
        "acceptance_criteria":["The report is readable."],
        "proposal":{"summary":"Create report", "steps":[]},
        "submitter_id":"steward:test",
        "origin":{"conversation_id":"12345678-1234-5678-1234-567812345678",
            "source_sequence":1},
        "completion_cycle":1,
        "completion":{"decision":"ACCEPTED", "assignment_id":"assignment:grace:demo",
            "verifier_revision":"1.0.0", "evidence_references":["urn:test:verified"],
            "artifact":{"artifact_path":"/approved/work/report.md",
                "artifact_sha256":"a" * 64}}}


class GraceConversationResultTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        self.router = FakeRouter()
        self.service = object.__new__(ResidentConversationService)
        self.service.store = self.store
        self.service.registry = FakeRegistry({"binding_revision":9,
            "implementation_kind":"model", "implementation_id":"implementation:router",
            "implementation_revision":self.router.model_sha256,
            "provider_ref":self.router.provider_id, "occupant_id":"occupant:grace"})
        self.service.office_id = "office:grace"
        self.service._resident_credential = "resident-credential"
        self.service.providers = {self.router.provider_id:self.router}
        self.service.max_response_tokens = 128
        self.service.continuation_handler = None
        self.actions = []
        self.service._authorize = lambda credential, action: self.actions.append((credential, action))
        self.service._registry_lock = __import__("threading").RLock()

    def test_verified_result_uses_80b_and_persists_once_to_original_conversation(self):
        context = valid_context()
        result = self.service.review_verified_work_order(context)
        self.assertEqual(result["status"], "published")
        self.assertEqual(result["served_model"], "Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf")
        self.assertEqual(self.actions, [("resident-credential", "resident.conversation.send")])
        self.assertEqual(self.router.calls[0][3], "grace.reasoning.80b")
        request_id = result["request_id"]
        row = self.store.responses[request_id]
        self.assertEqual(row["conversation_id"], context["origin"]["conversation_id"])
        self.assertEqual(row["source_sequence"], context["origin"]["source_sequence"])
        self.assertEqual(row["principal_id"], context["submitter_id"])
        self.assertEqual(row["metadata"]["verification_decision"], "ACCEPTED")
        self.assertEqual(row["metadata"]["artifact"], context["completion"]["artifact"])
        repeated = self.service.review_verified_work_order(context)
        self.assertEqual(repeated["status"], "already_published")
        self.assertEqual(repeated["review_decision"], row["metadata"]["review_decision"])
        self.assertEqual(len(self.router.calls), 1)
        self.assertEqual(len(self.store.responses), 1)

    def test_unverified_or_wrong_scope_result_never_reaches_provider(self):
        context = valid_context()
        context["completion"]["decision"] = "REJECTED"
        with self.assertRaises(ValueError):
            self.service.review_verified_work_order(context)
        self.assertEqual(self.router.calls, [])
        self.assertEqual(self.store.responses, {})

    def test_deferred_result_review_logs_only_sanitized_provider_attempt_metadata(self):
        self.router.failure = ReasoningDeferred("UNAVAILABLE", attempts=({
            "selected_provider": "local.inference.v1",
            "selected_model": "Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf",
            "reasoning_stage": "reasoning", "outcome": "failed",
            "error_code": "response_incomplete", "finish_reason": "length",
            "completion_tokens": 128, "completion_token_limit": 128,
            "prompt": "PRIVATE-PROMPT", "response": "PRIVATE-COMPLETION",
            "credential": "PRIVATE-CREDENTIAL"},))
        with self.assertLogs("riverview_core.resident_execution.conversation",
                             level="WARNING") as captured:
            with self.assertRaises(ReasoningDeferred):
                self.service.review_verified_work_order(valid_context())
        diagnostic = "\n".join(captured.output)
        self.assertIn('"event": "grace_result_review_deferred"', diagnostic)
        self.assertIn('"readiness_state": "UNAVAILABLE"', diagnostic)
        self.assertIn('"error_code": "response_incomplete"', diagnostic)
        self.assertIn('"finish_reason": "length"', diagnostic)
        self.assertIn('"completion_tokens": 128', diagnostic)
        self.assertNotIn("PRIVATE-PROMPT", diagnostic)
        self.assertNotIn("PRIVATE-COMPLETION", diagnostic)
        self.assertNotIn("PRIVATE-CREDENTIAL", diagnostic)
        self.assertEqual(self.store.responses, {})

    def test_smaller_direct_model_cannot_review_substantive_result(self):
        small = SimpleNamespace(model="qwen3-0.6b", model_sha256="r" * 64)
        self.service.providers = {self.router.provider_id:small}
        with self.assertRaisesRegex(ConversationUnavailable, "80B result review capability unavailable"):
            self.service.review_verified_work_order(valid_context())
        self.assertEqual(self.store.responses, {})

    def test_structured_in_scope_continuation_is_sent_to_existing_pipeline_handler(self):
        import json
        self.router.content = json.dumps({"decision":"ENGINEERING_STEP_PROPOSED",
            "rationale":"A bounded follow-up improves the accepted deliverable.",
            "additional_evidence":[], "proposed_step":{"step_id":"followup",
                "objective":"Refine the accepted report", "acceptance_criteria":[
                    "The report is readable."], "depends_on":[]}})
        handled = []
        self.service.continuation_handler = lambda context, step: handled.append(
            (context["objective_id"], step.step_id, step.acceptance_criteria))
        result = self.service.review_verified_work_order(valid_context())
        self.assertEqual(handled, [("objective:grace-conversation:demo", "followup",
                                    ("The report is readable.",))])
        row = self.store.responses[result["request_id"]]
        self.assertEqual(row["metadata"]["review_decision"], "ENGINEERING_STEP_PROPOSED")
        self.assertEqual(row["metadata"]["continuation_status"],
                         "persisted_for_existing_authorized_dispatch")

    def test_out_of_scope_continuation_becomes_steward_authorization_decision(self):
        import json
        self.router.content = json.dumps({"decision":"ENGINEERING_STEP_PROPOSED",
            "rationale":"I want to add a new requirement.", "additional_evidence":[],
            "proposed_step":{"step_id":"expanded", "objective":"Expand scope",
                "acceptance_criteria":["Create an unrelated application"], "depends_on":[]}})
        handled = []
        self.service.continuation_handler = lambda *_args: handled.append(True)
        result = self.service.review_verified_work_order(valid_context())
        self.assertEqual(handled, [])
        row = self.store.responses[result["request_id"]]
        self.assertEqual(row["metadata"]["review_decision"], "STEWARD_AUTHORIZATION_REQUIRED")
        self.assertEqual(result["review_decision"], "STEWARD_AUTHORIZATION_REQUIRED")
        self.assertIsNone(row["metadata"]["proposed_step"])
        self.assertEqual(row["metadata"]["continuation_status"], "not_requested")

    def test_new_evidence_revision_gets_one_bounded_durable_review_generation(self):
        import json
        self.router.content = json.dumps({"decision":"ADDITIONAL_EVIDENCE_REQUIRED",
            "rationale":"More evidence is still required.",
            "additional_evidence":["A second independent source."], "proposed_step":None})
        context = valid_context()
        context.update({"review_generation":2,
            "review_evidence_revision":"steward-evidence-rev-1",
            "review_evidence":["Read-only historical assignment aggregates were shared."],
            "review_evidence_sha256":hashlib.sha256(json.dumps({
                "evidence_revision":"steward-evidence-rev-1",
                "evidence":["Read-only historical assignment aggregates were shared."]},
                ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
        first = self.service.review_verified_work_order(context)
        self.assertEqual(first["status"], "published")
        self.assertEqual(first["review_generation"], "2")
        self.assertNotEqual(first["request_id"], str(__import__("uuid").uuid5(
            __import__("uuid").NAMESPACE_URL,
            "riverview:grace-engineering-review:" + context["objective_id"] + ":1")))
        request_messages = self.router.calls[0][0][1]["content"]
        self.assertIn("steward-evidence-rev-1", request_messages)
        self.assertIn("Read-only historical assignment aggregates were shared.", request_messages)
        self.assertEqual(self.store.responses[first["request_id"]]["metadata"]["review_decision"],
                         "ADDITIONAL_EVIDENCE_REQUIRED")
        self.assertEqual(len(self.store.responses), 1)

        repeated = self.service.review_verified_work_order(context)
        self.assertEqual(repeated["status"], "already_published")
        self.assertEqual(repeated["request_id"], first["request_id"])
        self.assertEqual(len(self.router.calls), 1)
        self.assertEqual(len(self.store.responses), 1)

        changed_same_generation = dict(context)
        changed_same_generation["review_evidence"] = ["Different evidence in same generation."]
        changed_same_generation["review_evidence_sha256"] = hashlib.sha256(json.dumps({
            "evidence_revision":"steward-evidence-rev-1",
            "evidence":changed_same_generation["review_evidence"]}, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with self.assertRaisesRegex(ConversationUnavailable, "already used"):
            self.service.review_verified_work_order(changed_same_generation)
        self.assertEqual(len(self.router.calls), 1)

    def test_re_review_requires_durable_revision_and_generation_is_bounded(self):
        context = valid_context()
        context["review_generation"] = 2
        with self.assertRaisesRegex(ValueError, "evidence revision"):
            self.service.review_verified_work_order(context)
        context.update({"review_evidence_revision":"rev-1",
            "review_evidence":["Additional sourced evidence."],
            "review_evidence_sha256":"f" * 64})
        with self.assertRaisesRegex(ValueError, "digest"):
            self.service.review_verified_work_order(context)
        context["review_generation"] = 5
        with self.assertRaisesRegex(ValueError, "generation"):
            self.service.review_verified_work_order(context)
        self.assertEqual(self.router.calls, [])
        self.assertEqual(self.store.responses, {})

    def test_binding_change_during_reasoning_blocks_continuation_mutation(self):
        import json
        self.router.content = json.dumps({"decision":"ENGINEERING_STEP_PROPOSED",
            "rationale":"A bounded follow-up is useful.", "additional_evidence":[],
            "proposed_step":{"step_id":"followup", "objective":"Refine accepted report",
                "acceptance_criteria":["The report is readable."], "depends_on":[]}})
        handled = []
        self.service.continuation_handler = lambda *_args: handled.append(True)
        self.router.on_complete = lambda: self.service.registry.binding.update(binding_revision=10)
        with self.assertRaisesRegex(ConversationUnavailable, "binding changed"):
            self.service.review_verified_work_order(valid_context())
        self.assertEqual(handled, [])
        self.assertEqual(self.store.responses, {})

    def test_persistent_outbox_acknowledges_only_after_chat_publisher_receipt(self):
        class Pipeline:
            def __init__(self):
                self.receipts = []

            def pending_conversation_results(self, *, limit):
                return [{"objective_id": "objective:outbox-1"}]

            def record_conversation_result_published(self, objective_id, receipt):
                self.receipts.append((objective_id, receipt))

        pipeline = Pipeline()
        service = object.__new__(GraceExecutionService)
        service.pipeline = pipeline
        service.conversation_result_publisher = lambda _context: {
            "status": "published", "request_id": "request-1",
            "provider_id": "local.inference.v1", "served_model": "qwen-80b",
            "implementation_id": "implementation:grace:router", "completion_cycle": "1"}
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(pipeline.receipts, [("objective:outbox-1", {
            "request_id": "request-1", "provider_id": "local.inference.v1",
            "served_model": "qwen-80b", "implementation_id": "implementation:grace:router",
            "completion_cycle": "1"})])

    def test_failed_result_publisher_leaves_durable_outbox_unacknowledged(self):
        class Pipeline:
            def __init__(self):
                self.acks = 0

            def pending_conversation_results(self, *, limit):
                return [{"objective_id": "objective:retry-1"}]

            def record_conversation_result_published(self, *_args):
                self.acks += 1

        pipeline = Pipeline()
        service = object.__new__(GraceExecutionService)
        service.pipeline = pipeline

        def unavailable(_context):
            raise RuntimeError("model unavailable")

        service.conversation_result_publisher = unavailable
        self.assertEqual(service.publish_conversation_results(), 0)
        self.assertEqual(pipeline.acks, 0)


if __name__ == "__main__":
    unittest.main()


def json_complete():
    import json
    return json.dumps({"decision":"OBJECTIVE_COMPLETE",
        "rationale":"The verified file is ready at the recorded path.",
        "additional_evidence":[], "proposed_step":None})
