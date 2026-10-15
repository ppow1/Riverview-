# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_model_router.py
# Component: RESIDENT-MODEL-ROUTER
# Revision: 1.0.6
# Purpose: Verify primary 80B routing, capability-pinned recovery, bounded fallback and diagnostics
# Execution Model: Deterministic provider doubles; no database or model endpoint
# Observability: Assert selected provider and served-model provenance
# Authority: Router selection does not authorize conversation or execution
# Contracts: src/riverview_core/resident_execution/model_router.py
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-CAPABILITY-001 | Verify capability-pinned routing despite later simple history
# =============================================================================
"""Focused tests for Grace's readiness-aware three-stage router."""

import unittest
import json

from riverview_core.local_reasoning_provider import (ChatCompletion,
    LocalReasoningUnavailable, ProviderReadiness)
from riverview_core.resident_execution.model_router import GraceModelRouter, ReasoningDeferred
from riverview_core.resident_reasoning import PlanProposal, PlanStep, ReasoningRequest


class _Provider:
    def __init__(self, model, ready=True):
        self.model = model
        self.provider_id = "test." + model
        self.model_sha256 = "a" * 64
        self.state = "READY" if ready else "UNAVAILABLE"
        self.calls = []
        self.timeout_values = []
        self.failure = None
        self.proposal_requests = []

    def readiness(self):
        return ProviderReadiness(self.state, self.model, self.state.lower())

    def complete_chat(self, messages, *, max_tokens, expected_revision, timeout_seconds=120):
        self.calls.append((messages, expected_revision))
        self.timeout_values.append(timeout_seconds)
        if self.failure:
            raise LocalReasoningUnavailable(self.failure)
        return ChatCompletion("bounded answer", self.model, 2, 3, "stop")

    def propose(self, request):
        self.proposal_requests.append(request)
        if self.failure:
            raise LocalReasoningUnavailable(self.failure)
        return PlanProposal("Produce report", (PlanStep(
            "report", "Create a bounded report", ("Report is readable",)),), 8,
            provider_id=self.provider_id, served_model=self.model,
            model_revision=self.model_sha256, reasoning_stage="reasoning")


class GraceModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.cpu = _Provider("qwen-0.6b")
        self.vision = _Provider("huihui-30b")
        self.reasoner = _Provider("qwen-80b")
        self.router = GraceModelRouter(autonomic=self.cpu, vision=self.vision,
                                       reasoning=self.reasoner)

    def proposal_request(self, *, revision=None):
        return ReasoningRequest("request:1", "office:grace", "objective:1", "1",
            9, revision or self.router.model_sha256, "persistent_resident_cycle", 64,
            {"id":"objective:1"}, (), None)

    def test_persistent_reasoner_proposal_uses_only_ready_80b_and_records_served_model(self):
        result = self.router.propose(self.proposal_request())
        self.assertEqual(result.served_model, "qwen-80b")
        self.assertEqual(result.provider_id, "test.qwen-80b")
        self.assertEqual(result.model_revision, self.reasoner.model_sha256)
        self.assertEqual(result.reasoning_stage, "reasoning")
        self.assertEqual(self.reasoner.proposal_requests[0].implementation_revision,
                         self.reasoner.model_sha256)
        self.assertEqual(self.vision.proposal_requests, [])
        self.assertEqual(self.cpu.proposal_requests, [])

    def test_persistent_proposal_does_not_fallback_when_80b_is_unavailable(self):
        self.reasoner.state = "MODEL_BUSY"
        with self.assertRaises(LocalReasoningUnavailable):
            self.router.propose(self.proposal_request())
        self.assertEqual(self.reasoner.proposal_requests, [])
        self.assertEqual(self.vision.proposal_requests, [])
        self.assertEqual(self.cpu.proposal_requests, [])

    def test_persistent_proposal_rejects_router_binding_mismatch_before_model_call(self):
        self.assertIsNone(self.router.propose(self.proposal_request(revision="f" * 64)))
        self.assertEqual(self.reasoner.proposal_requests, [])

    def test_autonomic_greeting_uses_cpu_and_marks_provisional(self):
        result = self.router.complete_chat([{"role": "user", "content": "Hello."}],
            max_tokens=64, expected_revision=self.router.model_sha256)
        self.assertEqual(result.served_model, "qwen-0.6b")
        self.assertEqual(result.reasoning_stage, "autonomic")
        self.assertTrue(result.provisional)

    def test_substantive_unmatched_request_prefers_80b(self):
        result = self.router.complete_chat([{"role": "user", "content": "Tell me about yourself."}],
            max_tokens=64, expected_revision=self.router.model_sha256)
        self.assertEqual(result.served_model, "qwen-80b")
        self.assertEqual(result.reasoning_stage, "reasoning")
        self.assertFalse(result.provisional)

    def test_simple_turn_falls_back_to_autonomic_when_intermediate_unavailable(self):
        self.vision.state = "MODEL_LOADING"
        result = self.router.complete_chat([{"role": "user", "content": "Hello."}],
            max_tokens=64, expected_revision=self.router.model_sha256)
        self.assertEqual(result.served_model, "qwen-0.6b")
        self.assertEqual(result.reasoning_stage, "autonomic")
        self.assertTrue(result.provisional)

    def test_failed_30b_has_bounded_attempt_then_persistable_cpu_fallback(self):
        self.vision.failure = "endpoint_timeout"
        result = self.router.complete_chat([{"role": "user", "content": "What is a river?"}],
            max_tokens=64, expected_revision=self.router.model_sha256, timeout_seconds=120)
        self.assertEqual(result.served_model, "qwen-0.6b")
        self.assertEqual(self.vision.timeout_values, [15])
        self.assertEqual(self.cpu.timeout_values, [35])
        self.assertEqual([a["outcome"] for a in result.provider_attempts], ["failed", "succeeded"])
        self.assertEqual(result.provider_attempts[0]["error_code"], "endpoint_timeout")
        self.assertEqual(result.provider_attempts[0]["fallback_reason"], "interim_30b_provider_failure")
        self.assertEqual(result.provider_attempts[-1]["final_served_provider"], "test.qwen-0.6b")
        self.assertEqual(result.provider_attempts[0]["selected_model"], "huihui-30b")
        self.assertEqual(result.provider_attempts[-1]["final_served_model"], "qwen-0.6b")
        self.assertNotIn("content", json.dumps(result.provider_attempts))

    def test_simple_definition_uses_provisional_30b(self):
        result = self.router.complete_chat([{"role": "user", "content": "What is a river?"}],
            max_tokens=64, expected_revision=self.router.model_sha256)
        self.assertEqual(result.served_model, "huihui-30b")
        self.assertEqual(result.reasoning_stage, "interim_30b")
        self.assertTrue(result.provisional)

    def test_substantive_turn_requires_80b_and_defers_when_unready(self):
        self.reasoner.state = "MODEL_BUSY"
        with self.assertRaises(ReasoningDeferred) as caught:
            self.router.select([{"role": "user", "content": "Analyze the options."}])
        self.assertEqual(caught.exception.args[0], "MODEL_BUSY")
        self.assertEqual(self.cpu.calls, [])
        self.assertEqual(self.vision.calls, [])

    def test_substantive_turn_selects_80b_and_keeps_provenance(self):
        result = self.router.complete_chat([{"role": "user", "content": "Analyze the options."}],
            max_tokens=64, expected_revision=self.router.model_sha256)
        self.assertEqual(result.served_model, "qwen-80b")
        self.assertEqual(result.reasoning_stage, "reasoning")
        self.assertFalse(result.provisional)

    def test_deferred_80b_capability_overrides_later_simple_conversation_turn(self):
        messages = [
            {"role": "user", "content": "Analyze the original complex engineering objective."},
            {"role": "assistant", "content": "The request is deferred."},
            {"role": "user", "content": "What is 2 + 2?"},
            {"role": "assistant", "content": "4."},
            {"role": "user", "content": "Analyze the original complex engineering objective."},
        ]
        result = self.router.complete_chat(messages, max_tokens=64,
            expected_revision=self.router.model_sha256,
            required_capability="grace.reasoning.80b")
        self.assertEqual(result.reasoning_stage, "reasoning")
        self.assertEqual(result.served_model, "qwen-80b")
        self.assertEqual(len(self.reasoner.calls), 1)
        self.assertEqual(self.vision.calls, [])
        self.assertEqual(self.cpu.calls, [])

    def test_deferred_80b_does_not_fall_back_when_reasoner_is_unavailable(self):
        self.reasoner.state = "MODEL_BUSY"
        with self.assertRaises(ReasoningDeferred) as caught:
            self.router.complete_chat([
                {"role": "user", "content": "What is 2 + 2?"}],
                max_tokens=64, expected_revision=self.router.model_sha256,
                required_capability="grace.reasoning.80b")
        self.assertEqual(caught.exception.args[0], "MODEL_BUSY")
        self.assertEqual(caught.exception.attempts[0]["selected_model"], "qwen-80b")
        self.assertEqual(caught.exception.attempts[0]["outcome"], "deferred")
        self.assertEqual(self.reasoner.calls, [])
        self.assertEqual(self.vision.calls, [])
        self.assertEqual(self.cpu.calls, [])

    def test_router_binding_revision_is_mandatory(self):
        with self.assertRaises(LocalReasoningUnavailable):
            self.router.complete_chat([], max_tokens=32, expected_revision="wrong")

    def test_router_revision_changes_when_model_set_or_revision_changes(self):
        original = self.router.model_sha256
        replacement = _Provider("qwen-80b-replacement")
        other = GraceModelRouter(autonomic=self.cpu, vision=self.vision,
                                 reasoning=replacement)
        self.assertNotEqual(original, other.model_sha256)

    def test_all_unavailable_is_not_misreported_as_ready(self):
        self.cpu.state = self.vision.state = self.reasoner.state = "UNAVAILABLE"
        with self.assertRaises(ReasoningDeferred):
            self.router.select([{"role": "user", "content": "Hello."}])

    def test_cpu_fallback_does_not_answer_unverified_factual_question(self):
        self.vision.state = self.reasoner.state = "UNAVAILABLE"
        with self.assertRaises(ReasoningDeferred):
            self.router.select([{"role": "user", "content": "What is the weather?"}])
        self.assertEqual(self.cpu.calls, [])


if __name__ == "__main__":
    unittest.main()
