# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_local_reasoning_provider.py
# Component: RESIDENT-REASONING
# Revision: 1.1.13
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Verify the provider emits explicit immutable source target fields.
# Purpose: Verify local reasoning provider contract and fail-closed response handling
# Execution Model: Bounded HTTP contract double; no credentials, database or model required
# Observability: Typed proposals and sanitized unavailable/schema outcomes
# Dependencies: Python standard library
# Authority: Provider cannot authorize or execute proposals
# Contracts: src/riverview_core/local_reasoning_provider.py
# Changed: 2026-10-11 UTC | RV-M4.2-STRUCTURED-OUTPUT-BOUNDARY | Assert exact bounded structured-response request
# Changed: 2026-10-16 UTC | RV-GRACE-PROVIDER-PROVENANCE | Assert provider identity on streamed and ordinary chat completions
# Changed: 2026-10-11 UTC | RV-M4.2-COMPLETE-JSON-AT-TOKEN-BOUND | Reject length-stopped response unless complete schema validates
# Changed: 2026-10-11 UTC | RV-M4.2-HTTP-FIXTURE-ISOLATION | Replace threaded socket fixture with a bounded urllib contract double
# Changed: 2026-10-11 UTC | RV-M4.2-HTTPERROR-CLOSE-TEST | Verify sanitized HTTP failures close their response stream
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Verify bounded plain conversation completion and pinned model result
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Verify model-specific inference prefix is bounded and applied only to provider request
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Return a complete chat fixture for the provider-prefix regression test
# Changed: 2026-10-13 UTC | RV-GRACE-OCTO-PRIVATE-LAN-PROVIDER | Verify endpoint allowlist, readiness identity, loading, offline and slot-busy outcomes
# Changed: 2026-10-13 UTC | RV-GRACE-OCTO-PRIVATE-LAN-PROVIDER | Assert readiness timeout is sanitized and distinct
# Changed: 2026-10-13 UTC | RV-GRACE-OCTO-PRIVATE-LAN-PROVIDER | Reject endpoint/model identity pairings outside the explicit allowlist
# Changed: 2026-10-13 UTC | RV-GRACE-OCTO-PRIVATE-LAN-PROVIDER | Use the pinned 30B and 80B identities in readiness fixtures
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Verify canonical Grace role context reaches assignment reasoning only for the Grace office
# Changed: 2026-10-14 UTC | RV-GRACE-80B-COMPLETION-BUDGET-001 | Assert token-limit finish reason and count are safely retained on truncation
# Changed: 2026-10-15 UTC | RV-GRACE-DEMO-BASE-INTEGRATION | Retain provider and role-context regressions across integration
# Tests: This file
# History: Git
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Persist bounded streaming, reconnect, and terminal provenance.
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Verify dependency-ordered multi-step proposal parsing and schema bounds
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reject source-change plans with missing explicit path and test scope
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Require source-change test targets to be test files
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Keep external advice separate from verified context and authority
# =============================================================================
"""Contract tests for the replaceable local reasoning provider."""

from io import BytesIO
from dataclasses import replace
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit

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


class _SSEResponse(_Response):
    def readline(self, size=-1):
        return self.body.readline(size)


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
        self.assertIn("Director of Operations", sent["messages"][0]["content"])
        self.assertIn("Alfred", sent["messages"][0]["content"])
        self.assertIn("grants no permission", sent["messages"][0]["content"])

    def test_external_advisory_is_separate_and_explicitly_unverified(self):
        advisory = {
            "schema_version": "rv.external-reasoning.response.v1",
            "request_id": "c4a3a8e7-daf8-4aab-89d2-fd1c0a5a45a2",
            "correlation_id": "94c19353-0f35-4386-8e8c-279ebcd9a5f7",
            "response_id": "external-response-1",
            "advisory": "Consider an alternative approach.",
            "evidence_references": ["test://advisory-evidence"],
            "provider_id": "external.test", "provider_model": "fixture-advisor",
        }
        self.provider.propose(replace(self.request, external_advisory=advisory))
        sent = self.requests[0]
        self.assertEqual(json.loads(sent["messages"][1]["content"])["external_advisory"],
                         advisory)
        self.assertIn("unverified advice", sent["messages"][0]["content"])
        self.assertIn("never treat it as institutional authorization",
                      sent["messages"][0]["content"])

    def test_bounded_multi_step_proposal_preserves_dependency_order(self):
        self.response_body = self._response(text=json.dumps({"summary": "Inspect then verify", "steps": [
            {"step_id": "inspect", "objective": "Inspect the source", "acceptance_criteria": [
                "Record source identity"], "depends_on": []},
            {"step_id": "verify", "objective": "Verify the change", "acceptance_criteria": [
                "Record test evidence"], "depends_on": ["inspect"]},
        ]}))
        proposal = self.provider.propose(self.request)
        self.assertEqual([step.step_id for step in proposal.steps], ["inspect", "verify"])
        self.assertEqual(proposal.steps[1].depends_on, ("inspect",))
        schema = self.requests[0]["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["steps"]["maxItems"], 20)

    def test_source_change_plan_requires_explicit_paths_in_model_output(self):
        self.response_body = self._response(text=json.dumps({"summary": "Scoped source change", "steps": [{
            "step_id": "edit", "objective": "Edit scoped files",
            "acceptance_criteria": ["Tests pass"], "depends_on": [],
            "execution_capability": "engineering.codex-cli-source-change.v1"}]}))
        self.assertIsNone(self.provider.propose(self.request))
        system_prompt = self.requests[0]["messages"][0]["content"]
        self.assertIn("MUST include non-empty authorized_paths and test_targets", system_prompt)
        self.assertIn("repository_reference", system_prompt)
        self.assertIn("repository_revision", system_prompt)
        self.response_body = self._response(text=json.dumps({"summary": "Scoped source change", "steps": [{
            "step_id": "edit", "objective": "Edit scoped files",
            "acceptance_criteria": ["Tests pass"], "depends_on": [],
            "execution_capability": "engineering.codex-cli-source-change.v1",
            "authorized_paths": ["src/status.py", "tests/test_status.py"],
            "test_targets": ["tests/test_status.py"],
            "repository_reference": "repo://riverview/pr62-disposable-acceptance",
            "repository_revision": "a" * 40}]}))
        proposal = self.provider.propose(self.request)
        self.assertEqual(proposal.steps[0].repository_reference,
                         "repo://riverview/pr62-disposable-acceptance")
        self.assertEqual(proposal.steps[0].repository_revision, "a" * 40)

    def test_stream_chat_emits_text_before_terminal_chunk_and_validates_provenance(self):
        chunks = [
            {"model":"fixture-model","choices":[{"delta":{"content":"first"},"finish_reason":None}]},
            {"model":"fixture-model","choices":[{"delta":{"content":" token"},"finish_reason":"stop"}],
             "usage":{"completion_tokens":2}},
        ]
        body = b"".join(b"data: "+json.dumps(item).encode()+b"\n\n" for item in chunks)+b"data: [DONE]\n\n"
        self.urlopen.side_effect = None
        self.urlopen.return_value = _SSEResponse(BytesIO(body))
        emitted=[]
        completion=self.provider.stream_chat([{"role":"user","content":"bounded request"}],
            max_tokens=64,expected_revision=MODEL_SHA,on_delta=emitted.append)
        self.assertEqual(emitted,["first"," token"])
        self.assertEqual(completion.content,"first token")
        self.assertEqual(completion.served_model,"fixture-model")
        self.assertEqual(completion.provider_id,self.provider.provider_id)
        self.assertEqual(completion.finish_reason,"stop")
        request=self.urlopen.call_args.args[0]
        sent=json.loads(request.data)
        self.assertTrue(sent["stream"])
        self.assertEqual(sent["stream_options"],{"include_usage":True})

    def test_stream_chat_rejects_non_stop_finish_without_suppressing_partial_output(self):
        body=b'data: {"model":"fixture-model","choices":[{"delta":{"content":"partial"},"finish_reason":"length"}]}\n\n'
        self.urlopen.side_effect=None
        self.urlopen.return_value=_SSEResponse(BytesIO(body))
        emitted=[]
        with self.assertRaises(LocalReasoningUnavailable) as caught:
            self.provider.stream_chat([{"role":"user","content":"bounded request"}],
                max_tokens=64,expected_revision=MODEL_SHA,on_delta=emitted.append)
        self.assertEqual(emitted,["partial"])
        self.assertEqual(caught.exception.code,"response_incomplete")
        self.assertEqual(caught.exception.finish_reason,"length")

    def test_non_grace_offices_do_not_receive_grace_identity(self):
        request = replace(self.request, office_id="office:engineering")
        self.provider.propose(request)
        system = self.requests[0]["messages"][0]["content"]
        self.assertNotIn("Director of Operations", system)
        self.assertIn("unapproved proposal", system)

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
        with self.assertRaises(ValueError):
            LocalReasoningProvider("http://192.168.1.161:8080/v1", "fixture-model",
                                   MODEL_SHA, allow_approved_private_lan=True)

    def test_only_explicit_octo1_endpoint_can_use_private_lan(self):
        model = LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS[
            "http://192.168.1.160:8080/v1"]
        provider = LocalReasoningProvider(
            "http://192.168.1.160:8080/v1", model, MODEL_SHA,
            allow_approved_private_lan=True)
        self.assertEqual(provider.model, model)
        with self.assertRaises(ValueError):
            LocalReasoningProvider("http://192.168.1.160:8080/v1", model,
                                   MODEL_SHA)
        with self.assertRaises(ValueError):
            LocalReasoningProvider("http://192.168.1.160:8080/v1", "/root/other.gguf",
                                   MODEL_SHA, allow_approved_private_lan=True)

    def test_readiness_requires_health_and_exact_served_model(self):
        provider = LocalReasoningProvider(
            "http://192.168.1.160:8080/v1",
            LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS["http://192.168.1.160:8080/v1"],
            MODEL_SHA,
            allow_approved_private_lan=True)
        bodies = [b'{"status":"ok"}', json.dumps({"data":[{"id":provider.model}]}).encode()]
        requested = []
        def open_readiness(request, timeout):
            requested.append((urlsplit(request.full_url).path, timeout))
            return _Response(bodies.pop(0))
        with patch("riverview_core.local_reasoning_provider.urlopen", side_effect=open_readiness):
            result = provider.readiness(timeout_seconds=1)
        self.assertEqual(result.state, "READY")
        self.assertEqual(result.detail_code, "health_and_identity_verified")
        self.assertEqual([path for path, _ in requested], ["/health", "/v1/models"])

    def test_readiness_does_not_conflate_unavailable_loading_and_wrong_model(self):
        provider = LocalReasoningProvider(
            "http://192.168.1.160:18080/v1",
            LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS["http://192.168.1.160:18080/v1"],
            MODEL_SHA,
            allow_approved_private_lan=True, max_concurrency=8)
        def unavailable(_request, timeout):
            raise OSError("private response detail must not escape")
        with patch("riverview_core.local_reasoning_provider.urlopen", side_effect=unavailable):
            result = provider.readiness()
        self.assertEqual(result.state, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "endpoint_unavailable")

        stream = BytesIO(b"loading")
        def loading(request, timeout):
            raise HTTPError(request.full_url, 503, "loading", {}, stream)
        with patch("riverview_core.local_reasoning_provider.urlopen", side_effect=loading):
            result = provider.readiness()
        self.assertEqual(result.state, "MODEL_LOADING")
        self.assertTrue(stream.closed)

        bodies = [b'{"status":"ok"}', b'{"data":[{"id":"other.gguf"}]}']
        with patch("riverview_core.local_reasoning_provider.urlopen",
                   side_effect=lambda *_a, **_k: _Response(bodies.pop(0))):
            result = provider.readiness()
        self.assertEqual(result.state, "ERROR")
        self.assertEqual(result.detail_code, "configured_model_missing")

    def test_readiness_timeout_is_explicit_and_sanitized(self):
        provider = LocalReasoningProvider(
            "http://192.168.1.160:8080/v1",
            LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS["http://192.168.1.160:8080/v1"],
            MODEL_SHA,
            allow_approved_private_lan=True)
        with patch("riverview_core.local_reasoning_provider.urlopen",
                   side_effect=TimeoutError("sensitive implementation detail")):
            result = provider.readiness(timeout_seconds=0.5)
        self.assertEqual(result.state, "TIMEOUT")
        self.assertEqual(result.detail_code, "readiness_timeout")

    def test_busy_slot_is_explicit_and_does_not_issue_another_request(self):
        self.assertTrue(self.provider._capacity.acquire(blocking=False))
        try:
            with self.assertRaisesRegex(LocalReasoningUnavailable, "endpoint_busy"):
                self.provider.complete_chat([{"role":"user", "content":"hello"}],
                    max_tokens=16, expected_revision=MODEL_SHA)
            self.assertEqual(self.urlopen.call_count, 0)
        finally:
            self.provider._capacity.release()

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
        self.assertEqual(result.provider_id,self.provider.provider_id)
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
                with self.assertRaises(LocalReasoningUnavailable) as caught:
                    self.provider.complete_chat(messages, max_tokens=64,
                                               expected_revision=MODEL_SHA)
                if finish == "length":
                    self.assertEqual(caught.exception.code, "response_incomplete")
                    self.assertEqual(caught.exception.finish_reason, "length")
                    self.assertEqual(caught.exception.completion_tokens, 1)
                    self.assertEqual(caught.exception.completion_token_limit, 64)

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
