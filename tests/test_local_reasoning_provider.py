# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_local_reasoning_provider.py
# Component: RESIDENT-REASONING
# Revision: 1.1.19
# Changed: 2026-10-20 UTC | RV-GRACE-TYPED-PROPOSAL-SCHEMA | Require complete capability-specific structured proposal output
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Cover dynamic assignment artifacts, multi-file persistence, and independent contract verification
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Require dynamic artifact sets on bounded artifact proposals
# Changed: 2026-10-20 UTC | RV-GRACE-REASONING-PROPOSAL-RECOVERY-20261020 | Cover retry prompt and verbatim negative criteria
# Changed: 2026-10-20 UTC | RV-C4-GRACE-PROPOSAL-DIAGNOSTICS-20261020 | Assert sanitized proposal failure classes
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
# Changed: 2026-10-18 UTC | RV-C3-GRACE-REASONING-RELIABILITY-001 | Verify sanitized transient and deterministic HTTP status codes remain distinct.
# Tests: This file
# History: Git
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Persist bounded streaming, reconnect, and terminal provenance.
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Verify dependency-ordered multi-step proposal parsing and schema bounds
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reject source-change plans with missing explicit path and test scope
# Changed: 2026-10-18 UTC | RV-C3-EXACT-PROPOSAL-REVIEW-001 | Verify local provider receives exact review subject separately from advisory
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Require source-change test targets to be test files
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Keep external advice separate from verified context and authority
# Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Verify the typed external escalation decision is limited to configured providers
# Changed: 2026-10-18 UTC | RV-REASONING-ADAPTER-COMPAT-001 | Verify ordered local chat text and fail-closed tool/refusal/content handling
# =============================================================================
"""Contract tests for the replaceable local reasoning provider."""

from io import BytesIO
from dataclasses import replace
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit

from riverview_core.resident_reasoning import (ExternalEscalationIntent,
    ProposalValidationFailure, ReasoningRequest)
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
                "acceptance_criteria": ["Record its revision"], "depends_on": [],
                "execution_capability": "engineering.codex-cli-artifact.v1",
                "artifact_requirements": [{"name":"report", "path":"reports/inspection.txt",
                    "media_type":"text/plain", "acceptance_criteria":["Record its revision"]}]}]})
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

    def test_retry_prompt_repairs_prior_plan_omitting_negative_criterion(self):
        required = "Do not modify source files, repository contents, services, production configuration, or credentials."
        prior_plan = {"summary": "Document workflow", "steps": [{
            "step_id": "s1", "objective": "Map workflow", "acceptance_criteria": [
                "Produce the Markdown deliverable."], "depends_on": []}]}
        assignment = {"id": "assignment-1", "objective": "document workflow",
                      "acceptance_criteria": ["Produce the Markdown deliverable.", required]}
        self.request = replace(self.request, assignment=assignment, prior_plan=prior_plan)

        self.provider.propose(self.request)

        sent = self.requests[0]
        prompt = sent["messages"][0]["content"]
        context = json.loads(sent["messages"][1]["content"])
        self.assertIn("negative constraints or prohibitions", prompt)
        self.assertIn("beginning with 'Do not'", prompt)
        self.assertIn("prior_plan is an unaccepted earlier attempt, not approval", prompt)
        self.assertEqual(context["prior_plan"], prior_plan)
        self.assertEqual(context["assignment"]["acceptance_criteria"],
                         ["Produce the Markdown deliverable.", required])

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

    def test_exact_review_subject_reaches_local_reasoner_with_advisory(self):
        from riverview_core.resident_execution.external_reasoning import build_review_subject
        from riverview_core.resident_reasoning import PlanProposal, PlanStep
        from uuid import uuid4
        advisory = {
            "schema_version": "rv.external-reasoning.response.v1",
            "request_id": "c4a3a8e7-daf8-4aab-89d2-fd1c0a5a45a2",
            "correlation_id": "94c19353-0f35-4386-8e8c-279ebcd9a5f7",
            "response_id": "external-response-review-fixture",
            "advisory": "Synthetic review advice.",
            "evidence_references": ["test://review-fixture"],
            "provider_id": "external.test", "provider_model": "fixture-advisor",
        }
        subject = build_review_subject(str(uuid4()), 1, PlanProposal(
            "inspect one file", (PlanStep("inspect", "Inspect file",
                ("record the exact revision",)),), 4))
        self.provider.propose(replace(self.request, external_advisory=advisory,
                                      review_subject=subject))
        context = json.loads(self.requests[0]["messages"][1]["content"])
        self.assertEqual(context["review_subject"], json.loads(json.dumps(subject)))
        self.assertEqual(context["external_advisory"], advisory)
        self.assertIn("exact proposal", self.requests[0]["messages"][0]["content"])
        self.assertIn("do not claim that an unchanged proposal is approved",
                      self.requests[0]["messages"][0]["content"])

    def test_bounded_multi_step_proposal_preserves_dependency_order(self):
        self.response_body = self._response(text=json.dumps({"summary": "Inspect then verify", "steps": [
            {"step_id": "inspect", "objective": "Inspect the source", "acceptance_criteria": [
                "Record source identity"], "depends_on": [],
                "execution_capability": "engineering.codex-cli-artifact.v1",
                "artifact_requirements": [{
                    "name":"identity", "path":"reports/source.json", "media_type":"application/json",
                    "acceptance_criteria":["Record source identity"]}]},
            {"step_id": "verify", "objective": "Verify the change", "acceptance_criteria": [
                "Record test evidence"], "depends_on": ["inspect"],
                "execution_capability": "engineering.codex-cli-artifact.v1",
                "artifact_requirements": [{
                    "name":"tests", "path":"reports/test-results.csv", "media_type":"text/csv",
                    "acceptance_criteria":["Record test evidence"]}]},
        ]}))
        proposal = self.provider.propose(self.request)
        self.assertEqual([step.step_id for step in proposal.steps], ["inspect", "verify"])
        self.assertEqual(proposal.steps[1].depends_on, ("inspect",))
        schema = self.requests[0]["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["steps"]["maxItems"], 20)

    def test_external_escalation_is_explicit_and_limited_to_configured_provider(self):
        self.request = replace(self.request,
            external_reasoning_targets=("chatgpt:approved",))
        self.response_body = self._response(text=json.dumps({
            "summary": "Request second opinion", "steps": [{
                "step_id": "review", "objective": "Review verified facts",
                "acceptance_criteria": ["Return advisory evidence"], "depends_on": [],
                "execution_capability": "engineering.codex-cli-artifact.v1",
                "artifact_requirements": [{"name":"advisory", "path":"records/advisory.json",
                    "media_type":"application/json", "acceptance_criteria":["Return advisory evidence"]}]}],
            "external_escalation": {"reason": "capability_gap",
                                     "target_provider_id": "chatgpt:approved"}}))
        proposal = self.provider.propose(self.request)
        self.assertEqual(proposal.external_escalation,
                         ExternalEscalationIntent("capability_gap", "chatgpt:approved"))
        schema = self.requests[0]["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["external_escalation"]["properties"]
                         ["target_provider_id"]["enum"], ["chatgpt:approved"])
        self.request = replace(self.request, external_reasoning_targets=("chatgpt:approved",))
        self.response_body = self._response(text=json.dumps({
            "summary": "Request second opinion", "steps": [{
                "step_id": "review", "objective": "Review verified facts",
                "acceptance_criteria": ["Return advisory evidence"], "depends_on": [],
                "execution_capability": "engineering.codex-cli-artifact.v1",
                "artifact_requirements": [{"name":"advisory", "path":"records/advisory.json",
                    "media_type":"application/json", "acceptance_criteria":["Return advisory evidence"]}]}],
            "external_escalation": {"reason": "capability_gap",
                                     "target_provider_id": "chatgpt:other"}}))
        self.assertEqual(self.provider.propose(self.request).detail_code,
                         "PROPOSAL_SCHEMA_INVALID")

    def test_source_change_plan_requires_explicit_paths_in_model_output(self):
        self.response_body = self._response(text=json.dumps({"summary": "Scoped source change", "steps": [{
            "step_id": "edit", "objective": "Edit scoped files",
            "acceptance_criteria": ["Tests pass"], "depends_on": [],
            "execution_capability": "engineering.codex-cli-source-change.v1"}]}))
        self.assertEqual(self.provider.propose(self.request).detail_code,
                         "PROPOSAL_SCHEMA_INVALID")
        system_prompt = self.requests[0]["messages"][0]["content"]
        self.assertIn("MUST include non-empty authorized_paths and test_targets", system_prompt)

    def test_source_change_plan_preserves_pinned_repository_provenance(self):
        revision = "a" * 40
        self.response_body = self._response(text=json.dumps({"summary":"Scoped source change",
            "steps":[{"step_id":"edit", "objective":"Edit scoped source",
                "acceptance_criteria":["Independent verification passes"], "depends_on":[],
                "execution_capability":"engineering.codex-cli-source-change.v1",
                "authorized_paths":["src/example.py", "tests/test_example.py"],
                "test_targets":["tests/test_example.py"],
                "repository_reference":"repo://ppow1/Riverview-",
                "repository_revision":revision}]}))
        proposal = self.provider.propose(self.request)
        self.assertEqual(proposal.steps[0].repository_reference,
                         "repo://ppow1/Riverview-")
        self.assertEqual(proposal.steps[0].repository_revision, revision)
        schema = self.requests[0]["response_format"]["json_schema"]["schema"]
        step_properties = schema["properties"]["steps"]["items"]["oneOf"][1]["properties"]
        self.assertIn("repository_reference", step_properties)
        self.assertIn("repository_revision", step_properties)

    def test_smoke_artifact_proposal_requires_complete_typed_requirements(self):
        criteria = tuple("Acceptance criterion %d remains unchanged" % index
                         for index in range(1, 9))
        valid_step = {
            "step_id": "smoke-report",
            "objective": "Produce smoke evidence",
            "acceptance_criteria": list(criteria),
            "depends_on": [],
            "execution_capability": "engineering.codex-cli-artifact.v1",
            "artifact_requirements": [{
                "name": "smoke-evidence",
                "path": "reports/grace-smoke.md",
                "media_type": "text/markdown",
                "acceptance_criteria": list(criteria),
                "max_bytes": 8192,
            }],
        }
        self.request = replace(self.request, assignment={
            "id": "assignment-1", "objective": "Produce smoke evidence",
            "acceptance_criteria": list(criteria)})
        self.response_body = self._response(text=json.dumps({
            "summary": "Produce smoke evidence", "steps": [valid_step]}))

        proposal = self.provider.propose(self.request)

        self.assertEqual(proposal.steps[0].acceptance_criteria, criteria)
        self.assertEqual(proposal.steps[0].artifact_requirements[0].acceptance_criteria,
                         criteria)
        sent = self.requests[0]
        prompt = sent["messages"][0]["content"]
        self.assertIn("For artifact steps, include artifact_requirements", prompt)
        step_schema = sent["response_format"]["json_schema"]["schema"]
        variants = step_schema["properties"]["steps"]["items"]["oneOf"]
        artifact_schema, source_schema = variants
        self.assertIn("artifact_requirements", artifact_schema["required"])
        self.assertIn("execution_capability", artifact_schema["required"])
        self.assertNotIn("authorized_paths", artifact_schema["properties"])
        self.assertNotIn("artifact_requirements", source_schema["properties"])

        del valid_step["artifact_requirements"]
        self.response_body = self._response(text=json.dumps({
            "summary": "Produce smoke evidence", "steps": [valid_step]}))
        self.assertEqual(self.provider.propose(self.request).detail_code,
                         "PROPOSAL_SCHEMA_INVALID")

        valid_step["artifact_requirements"] = [{
            "name": "smoke-evidence", "path": "reports/grace-smoke.md",
            "media_type": "text/markdown", "acceptance_criteria": list(criteria)}]
        valid_step["authorized_paths"] = ["src/not-authorized.py"]
        self.response_body = self._response(text=json.dumps({
            "summary": "Produce smoke evidence", "steps": [valid_step]}))
        self.assertEqual(self.provider.propose(self.request).detail_code,
                         "PROPOSAL_SCHEMA_INVALID")

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
        failure = self.provider.propose(request)
        self.assertEqual(failure.detail_code, "PROPOSAL_PROVENANCE_INVALID")
        self.assertEqual(self.requests, [])

    def test_complete_schema_object_is_accepted_at_length_boundary(self):
        self.response_body = self._response(finish="length")
        proposal = self.provider.propose(self.request)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.tokens_used, 9)

    def test_wrong_model_incomplete_response_or_usage_has_sanitized_failure_code(self):
        truncated = self._response(text='{"summary":"partial"', finish="length")
        cases = (
            (self._response(served="other"), "PROPOSAL_PROVENANCE_INVALID"),
            (truncated, "PROPOSAL_JSON_PARSE_FAILED"),
            (json.dumps({"model": "fixture-model", "choices": [{
                "message": {"content": "{}"}, "finish_reason": "stop"}]}).encode(),
             "PROPOSAL_RESPONSE_SCHEMA_INVALID"),
            (self._response(text="not json"), "PROPOSAL_JSON_PARSE_FAILED"),
        )
        for body, expected in cases:
            with self.subTest(expected=expected):
                self.response_body = body
                result = self.provider.propose(self.request)
                self.assertIsInstance(result, ProposalValidationFailure)
                self.assertEqual(result.detail_code, expected)

    def test_outer_parse_schema_and_token_budget_failures_have_distinct_codes(self):
        cases = (
            (b"not-json", "PROPOSAL_RESPONSE_PARSE_FAILED"),
            (json.dumps({"choices": []}).encode(), "PROPOSAL_RESPONSE_SCHEMA_INVALID"),
            (self._response(tokens=1000), "PROPOSAL_TOKEN_BUDGET_EXCEEDED"),
        )
        for body, expected in cases:
            with self.subTest(expected=expected):
                self.response_body = body
                result = self.provider.propose(self.request)
                self.assertEqual(result.detail_code, expected)

    def test_endpoint_errors_are_sanitized(self):
        self.response_status = 503
        with self.assertRaisesRegex(LocalReasoningUnavailable, "endpoint_http_503") as err:
            self.provider.propose(self.request)
        self.assertNotIn("inspect controlled files", str(err.exception))
        self.assertTrue(self.error_stream.closed)

    def test_http_status_classes_are_preserved_as_safe_codes(self):
        for status in (400, 401, 403, 404, 408, 413, 422, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                self.response_status = status
                with self.assertRaises(LocalReasoningUnavailable) as caught:
                    self.provider.propose(self.request)
                self.assertEqual(caught.exception.code, f"endpoint_http_{status}")
                self.assertNotIn("inspect controlled files", str(caught.exception))
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

    def test_80b_chat_preserves_ordered_text_blocks_and_unknown_envelope_metadata(self):
        self.response_body = json.dumps({"model":"fixture-80b-model",
            "future_metadata":{"safe":True}, "choices":[{"message":{
                "content":[{"type":"text","text":"Valid "},
                            {"type":"text","text":"80B response."}],
                "future_annotation":"opaque"}, "finish_reason":"stop"}],
            "usage":{"prompt_tokens":4,"completion_tokens":3}}).encode()
        provider = LocalReasoningProvider("http://127.0.0.1:8767/v1",
            "fixture-80b-model", MODEL_SHA)
        result = provider.complete_chat([{"role":"user","content":"hello"}],
            max_tokens=64, expected_revision=MODEL_SHA)
        self.assertEqual(result.content, "Valid 80B response.")
        self.assertEqual(result.served_model, "fixture-80b-model")

    def test_chat_rejects_tool_call_semantics_even_when_text_is_present(self):
        messages = [{"role":"user","content":"hello"}]
        for semantics in ({"tool_calls": [{"id":"call-1"}]},
                          {"function_call": {"name":"lookup"}}):
            self.response_body = json.dumps({"model":"fixture-model", "choices":[{
                "message":{"content":"visible text", **semantics}, "finish_reason":"stop"}],
                "usage":{"prompt_tokens":4,"completion_tokens":2}}).encode()
            with self.subTest(semantics=semantics), self.assertRaises(
                    LocalReasoningUnavailable) as caught:
                self.provider.complete_chat(messages, max_tokens=64,
                    expected_revision=MODEL_SHA)
            self.assertEqual(caught.exception.code, "response_contract_invalid")

    def test_chat_rejects_multiple_choices_instead_of_discarding_content(self):
        self.response_body = json.dumps({"model":"fixture-model", "choices":[
            {"message":{"content":"first answer"}, "finish_reason":"stop"},
            {"message":{"content":"second answer"}, "finish_reason":"stop"}],
            "usage":{"prompt_tokens":4,"completion_tokens":2}}).encode()
        with self.assertRaises(LocalReasoningUnavailable) as caught:
            self.provider.complete_chat([{"role":"user","content":"hello"}],
                max_tokens=64, expected_revision=MODEL_SHA)
        self.assertEqual(caught.exception.code, "response_contract_invalid")

    def test_chat_rejects_non_text_blocks_and_unrepresented_block_fields(self):
        messages = [{"role":"user","content":"hello"}]
        invalid = [
            [{"type":"text","text":"visible"},
             {"type":"image_url","image_url":{"url":"fixture"}}],
            [{"type":"text","text":"visible", "tool_calls":[]}],
        ]
        for content in invalid:
            self.response_body = json.dumps({"model":"fixture-model", "choices":[{
                "message":{"content":content}, "finish_reason":"stop"}],
                "usage":{"prompt_tokens":4,"completion_tokens":2}}).encode()
            with self.subTest(content=content), self.assertRaises(
                    LocalReasoningUnavailable) as caught:
                self.provider.complete_chat(messages, max_tokens=64,
                    expected_revision=MODEL_SHA)
            self.assertEqual(caught.exception.code, "response_contract_invalid")

    def test_chat_rejects_mixed_refusal_and_text(self):
        self.response_body = json.dumps({"model":"fixture-model", "choices":[{
            "message":{"content":"visible text", "refusal":"declined"},
            "finish_reason":"stop"}],
            "usage":{"prompt_tokens":4,"completion_tokens":2}}).encode()
        with self.assertRaises(LocalReasoningUnavailable) as caught:
            self.provider.complete_chat([{"role":"user","content":"hello"}],
                max_tokens=64, expected_revision=MODEL_SHA)
        self.assertEqual(caught.exception.code, "response_contract_invalid")

    def test_chat_preserves_visible_text_without_exposing_reasoning_metadata(self):
        self.response_body = json.dumps({"model":"fixture-model", "choices":[{
            "message":{"content":"visible answer", "reasoning_content":"private reasoning"},
            "finish_reason":"stop"}],
            "usage":{"prompt_tokens":4,"completion_tokens":2}}).encode()
        result = self.provider.complete_chat([{"role":"user","content":"hello"}],
            max_tokens=64, expected_revision=MODEL_SHA)
        self.assertEqual(result.content, "visible answer")
        self.assertNotIn("private reasoning", result.content)

    def test_stream_chat_preserves_text_blocks_and_rejects_tool_and_refusal_deltas(self):
        messages = [{"role":"user","content":"bounded request"}]
        body = (b'data: {"model":"fixture-model","choices":[{"delta":{"content":['
            b'{"type":"text","text":"first "},{"type":"text","text":"second"}]},'
            b'"finish_reason":"stop"}]}' b'\n\ndata: [DONE]\n\n')
        self.urlopen.side_effect = None
        self.urlopen.return_value = _SSEResponse(BytesIO(body))
        emitted = []
        result = self.provider.stream_chat(messages, max_tokens=64,
            expected_revision=MODEL_SHA, on_delta=emitted.append)
        self.assertEqual(emitted, ["first second"])
        self.assertEqual(result.content, "first second")

        for key, value in (("tool_calls", [{"index":0}]), ("refusal", "declined")):
            event = {"model":"fixture-model", "choices":[{"delta":{
                "content":"visible text", key:value}, "finish_reason":"stop"}]}
            self.urlopen.return_value = _SSEResponse(BytesIO(
                b"data: " + json.dumps(event).encode() + b"\n\ndata: [DONE]\n\n"))
            with self.subTest(key=key), self.assertRaises(
                    LocalReasoningUnavailable) as caught:
                self.provider.stream_chat(messages, max_tokens=64,
                    expected_revision=MODEL_SHA, on_delta=lambda _text: None)
            self.assertEqual(caught.exception.code, "response_contract_invalid")


if __name__ == "__main__":
    unittest.main()
