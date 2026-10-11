# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_local_reasoning_provider.py
# Component: RESIDENT-REASONING
# Revision: 1.0.8
# Purpose: Verify local reasoning provider contract and fail-closed response handling
# Execution Model: Bounded HTTP contract double; no credentials, database or model required
# Observability: Typed proposals and sanitized unavailable/schema outcomes
# Dependencies: Python standard library
# Authority: Provider cannot authorize or execute proposals
# Contracts: src/riverview_core/local_reasoning_provider.py
# Changed: 2026-10-11 UTC | RV-M4.2-STRUCTURED-OUTPUT-BOUNDARY | Assert exact bounded structured-response request
# Changed: 2026-10-11 UTC | RV-M4.2-COMPLETE-JSON-AT-TOKEN-BOUND | Reject length-stopped response unless complete schema validates
# Changed: 2026-10-11 UTC | RV-M4.2-HTTP-FIXTURE-ISOLATION | Replace threaded socket fixture with a bounded urllib contract double
# Changed: 2026-10-11 UTC | RV-M4.2-HTTPERROR-CLOSE-TEST | Verify sanitized HTTP failures close their response stream
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Verify bounded plain conversation completion and pinned model result
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Verify model-specific inference prefix is bounded and applied only to provider request
# Tests: This file
# History: Git
# =============================================================================
"""Contract tests for the replaceable local reasoning provider."""

from io import BytesIO
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from riverview_core.resident_reasoning import ReasoningRequest
from riverview_core.local_reasoning_provider import (
    LocalReasoningProvider, LocalReasoningUnavailable)


MODEL_SHA = "a" * 64


class _Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def read(self, size=-1):
        return self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class LocalReasoningProviderTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.response_status = 200
        self.response_body = self._response()
        self.error_stream = None
        self.request_calls = []
        self.urlopen_patch = patch(
            "riverview_core.local_reasoning_provider.urlopen",
            side_effect=self._open_request)
        self.urlopen = self.urlopen_patch.start()
        self.addCleanup(self.urlopen_patch.stop)
        self.provider = LocalReasoningProvider(
            "http://127.0.0.1:8767/v1", "fixture-model", MODEL_SHA)
        self.request = ReasoningRequest(
            request_id="request-1", office_id="office:grace", assignment_id="assignment-1",
            assignment_revision="7", binding_revision=1, implementation_revision=MODEL_SHA,
            trigger="initial", token_budget=64,
            assignment={"id": "assignment-1", "objective": "inspect controlled files"},
            verified_knowledge=({"status": "VERIFIED", "value": "header revision required"},),
            prior_plan=None)

    def _open_request(self, request, timeout):
        self.request_calls.append((request, timeout))
        self.requests.append(json.loads(request.data))
        if self.response_status != 200:
            self.error_stream = BytesIO(self.response_body)
            raise HTTPError(request.full_url, self.response_status,
                            "fixture failure", {}, self.error_stream)
        return _Response(self.response_body)

    @staticmethod
    def _response(*, served="fixture-model", finish="stop", tokens=9, text=None):
        if text is None:
            text = json.dumps({"summary": "Inspect and report.", "steps": [{
                "step_id": "inspect", "objective": "Inspect one file",
                "acceptance_criteria": ["Record its revision"], "depends_on": []}]})
        return json.dumps({"model": served, "choices": [{"message": {"content": text},
                          "finish_reason": finish}],
                          "usage": {"completion_tokens": tokens}}).encode()

    def test_verified_context_produces_typed_unapproved_proposal(self):
        proposal = self.provider.propose(self.request)
        self.assertEqual(proposal.summary, "Inspect and report.")
        self.assertEqual(proposal.tokens_used, 9)
        sent = self.requests[0]
        self.assertEqual(sent["model"], "fixture-model")
        self.assertEqual(sent["max_tokens"], 64)
        self.assertFalse(sent["stream"])
        self.assertEqual(sent["response_format"]["type"], "json_schema")
        self.assertEqual(sent["response_format"]["json_schema"]["name"],
                         "resident_plan_proposal")
        self.assertEqual(self.request_calls[0][1], self.provider.timeout_seconds)
        self.assertIn("verified_knowledge", sent["messages"][1]["content"])
        self.assertNotIn("execute", sent["messages"][0]["content"].lower())

    def test_model_revision_mismatch_fails_before_network_call(self):
        request = ReasoningRequest(**{**self.request.__dict__,
                                     "implementation_revision": "b" * 64})
        self.assertIsNone(self.provider.propose(request))
        self.assertEqual(self.requests, [])

    def test_complete_schema_object_is_accepted_at_length_boundary(self):
        self.response_body = self._response(finish="length")
        proposal = self.provider.propose(self.request)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.tokens_used, 9)

    def test_wrong_model_incomplete_response_or_usage_cannot_become_proposal(self):
        truncated = self._response(text='{"summary":"partial"', finish="length")
        for body in (self._response(served="other"),
                     truncated,
                     json.dumps({"model": "fixture-model", "choices": [{
                         "message": {"content": "{}"}, "finish_reason": "stop"}]}).encode(),
                     self._response(text="not json")):
            with self.subTest(body=body):
                self.response_body = body
                self.assertIsNone(self.provider.propose(self.request))

    def test_endpoint_errors_are_sanitized(self):
        self.response_status = 503
        with self.assertRaisesRegex(LocalReasoningUnavailable, "endpoint_http_503") as err:
            self.provider.propose(self.request)
        self.assertNotIn("inspect controlled files", str(err.exception))
        self.assertTrue(self.error_stream.closed)

    def test_non_loopback_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            LocalReasoningProvider("http://example.com/v1", "fixture-model", MODEL_SHA)

    def test_bounded_chat_uses_existing_pinned_loopback_endpoint(self):
        self.response_body = json.dumps({"model":"fixture-model","choices":[{
            "message":{"content":"Hello from the bound resident."},
            "finish_reason":"stop"}],"usage":{"prompt_tokens":31,"completion_tokens":8}}).encode()
        result = self.provider.complete_chat([
            {"role":"system","content":"Do not promote conversation to work."},
            {"role":"user","content":"Hello."}], max_tokens=64,
            expected_revision=MODEL_SHA, timeout_seconds=120)
        self.assertEqual(result.content, "Hello from the bound resident.")
        self.assertEqual(result.served_model, "fixture-model")
        self.assertEqual((result.prompt_tokens, result.completion_tokens), (31, 8))
        self.assertEqual(self.requests[0]["model"], "fixture-model")
        self.assertEqual(self.requests[0]["max_tokens"], 64)
        self.assertEqual(self.request_calls[0][1], 120)
        self.assertFalse(self.requests[0]["stream"])

    def test_chat_rejects_binding_mismatch_wrong_model_and_incomplete_output(self):
        messages = [{"role":"user","content":"hello"}]
        with self.assertRaises(LocalReasoningUnavailable):
            self.provider.complete_chat(messages, max_tokens=64, expected_revision="b" * 64)
        for served, finish in (("other-model", "stop"), ("fixture-model", "length")):
            self.response_body = json.dumps({"model":served,"choices":[{
                "message":{"content":"hello"},"finish_reason":finish}],
                "usage":{"prompt_tokens":2,"completion_tokens":1}}).encode()
            with self.subTest(served=served, finish=finish):
                with self.assertRaises(LocalReasoningUnavailable):
                    self.provider.complete_chat(messages, max_tokens=64,
                                               expected_revision=MODEL_SHA)

    def test_chat_prefix_changes_only_the_inference_copy(self):
        self.response_body = json.dumps({"model":"fixture-model","choices":[{
            "message":{"content":"hello"}, "finish_reason":"stop"}],
            "usage":{"prompt_tokens":4,"completion_tokens":1}}).encode()
        provider = LocalReasoningProvider(
            "http://127.0.0.1:8767/v1", "fixture-model", MODEL_SHA,
            chat_prefix="/no_think\n")
        original = [{"role":"user", "content":"hello"}]
        provider.complete_chat(original, max_tokens=64, expected_revision=MODEL_SHA)
        self.assertEqual(original[0]["content"], "hello")
        self.assertEqual(self.requests[-1]["messages"][-1]["content"],
                         "/no_think\nhello")
        with self.assertRaises(ValueError):
            LocalReasoningProvider("http://127.0.0.1:8767/v1", "fixture-model",
                                   MODEL_SHA, chat_prefix="x" * 65)


if __name__ == "__main__":
    unittest.main()
