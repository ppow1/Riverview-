# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_model_router.py
# Component: RESIDENT-MODEL-ROUTER
# Revision: 1.0.4
# Purpose: Verify primary 80B routing, bounded fallback, and sanitized attempt provenance
# Execution Model: Deterministic provider doubles; no database or model endpoint
# Observability: Assert selected provider and served-model provenance
# Authority: Router selection does not authorize conversation or execution
# Contracts: src/riverview_core/resident_execution/model_router.py
# =============================================================================
"""Focused tests for Grace's readiness-aware three-stage router."""

import unittest
import json

from riverview_core.local_reasoning_provider import (ChatCompletion,
    LocalReasoningUnavailable, ProviderReadiness)
from riverview_core.resident_execution.model_router import GraceModelRouter, ReasoningDeferred


class _Provider:
    def __init__(self, model, ready=True):
        self.model = model
        self.provider_id = "test." + model
        self.model_sha256 = "a" * 64
        self.state = "READY" if ready else "UNAVAILABLE"
        self.calls = []
        self.timeout_values = []
        self.failure = None

    def readiness(self):
        return ProviderReadiness(self.state, self.model, self.state.lower())

    def complete_chat(self, messages, *, max_tokens, expected_revision, timeout_seconds=120):
        self.calls.append((messages, expected_revision))
        self.timeout_values.append(timeout_seconds)
        if self.failure:
            raise LocalReasoningUnavailable(self.failure)
        return ChatCompletion("bounded answer", self.model, 2, 3, "stop")


class GraceModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.cpu = _Provider("qwen-0.6b")
        self.vision = _Provider("huihui-30b")
        self.reasoner = _Provider("qwen-80b")
        self.router = GraceModelRouter(autonomic=self.cpu, vision=self.vision,
                                       reasoning=self.reasoner)

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
