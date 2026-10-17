# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_local_reasoning_provider.py
# Component: RESIDENT-REASONING
# Revision: 1.0.2
# Purpose: Verify local reasoning provider contract and fail-closed response handling
# Execution Model: Loopback HTTP fixture; no credentials, database or model required
# Observability: Typed proposals and sanitized unavailable/schema outcomes
# Dependencies: Python standard library
# Authority: Provider cannot authorize or execute proposals
# Contracts: src/riverview_core/local_reasoning_provider.py
# Changed: 2026-10-11 UTC | RV-M4.2-STRUCTURED-OUTPUT-BOUNDARY | Assert exact bounded structured-response request
# Tests: This file
# History: Git
# =============================================================================
"""Contract tests for the replaceable local reasoning provider."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch

from riverview_core.resident_reasoning import ReasoningRequest
from riverview_core.local_reasoning_provider import (
    LocalReasoningProvider, LocalReasoningUnavailable)


MODEL_SHA = "a" * 64


class LocalReasoningProviderTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.response_status = 200
        self.response_body = self._response()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(handler):
                size = int(handler.headers.get("Content-Length", "0"))
                owner.requests.append(json.loads(handler.rfile.read(size)))
                handler.send_response(owner.response_status)
                handler.send_header("Content-Type", "application/json")
                handler.send_header("Content-Length", str(len(owner.response_body)))
                handler.end_headers()
                handler.wfile.write(owner.response_body)

            def log_message(self, *_args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.provider = LocalReasoningProvider(
            f"http://127.0.0.1:{self.server.server_port}/v1", "fixture-model", MODEL_SHA)
        self.request = ReasoningRequest(
            request_id="request-1", office_id="office:grace", assignment_id="assignment-1",
            assignment_revision="7", binding_revision=1, implementation_revision=MODEL_SHA,
            trigger="initial", token_budget=64,
            assignment={"id": "assignment-1", "objective": "inspect controlled files"},
            verified_knowledge=({"status": "VERIFIED", "value": "header revision required"},),
            prior_plan=None)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

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
        self.assertIn("verified_knowledge", sent["messages"][1]["content"])
        self.assertNotIn("execute", sent["messages"][0]["content"].lower())

    def test_model_revision_mismatch_fails_before_network_call(self):
        request = ReasoningRequest(**{**self.request.__dict__,
                                     "implementation_revision": "b" * 64})
        self.assertIsNone(self.provider.propose(request))
        self.assertEqual(self.requests, [])

    def test_wrong_model_incomplete_response_or_usage_cannot_become_proposal(self):
        for body in (self._response(served="other"),
                     self._response(finish="length"),
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

    def test_non_loopback_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            LocalReasoningProvider("http://example.com/v1", "fixture-model", MODEL_SHA)


if __name__ == "__main__":
    unittest.main()
