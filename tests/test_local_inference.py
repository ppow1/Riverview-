# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_local_inference.py
# Component: LOCAL-INFERENCE-WORKER
# Revision: 1.0.1
# Purpose: Verify loopback policy, bounded request handling, and safe result parsing
# Execution Model: Unit tests against a disposable loopback HTTP fixture
# Observability: Assertions over status and sanitized error codes
# Dependencies: Python 3.10+; standard library
# Authority: Local ephemeral port only; no model or external service required
# Changed: 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Cover sensitive-content rejection and served-model provenance
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Contract checks for the loopback-only OpenAI-compatible worker action."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest

from riverview_core.worker_adapter.local_inference import (
    LocalInferenceAction, LocalInferenceError)


class LocalInferenceActionTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.status = 200

        class Handler(BaseHTTPRequestHandler):
            def do_POST(handler_self):
                size = int(handler_self.headers.get("Content-Length", "0"))
                owner.requests.append(json.loads(handler_self.rfile.read(size)))
                body = json.dumps({
                    "model": "fixture-model-v1",
                    "choices": [{"message": {"content": " auth "},
                                 "finish_reason": "stop"}]
                }).encode()
                handler_self.send_response(owner.status)
                handler_self.send_header("Content-Type", "application/json")
                handler_self.send_header("Content-Length", str(len(body)))
                handler_self.end_headers()
                handler_self.wfile.write(body)

            def log_message(self, *_args):
                return

        owner = self
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/v1"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_loopback_call_returns_bounded_provenance_artifact(self):
        action = LocalInferenceAction(self.endpoint, "fixture-model-v1")
        result = action({"id": "a"}, type("Grounded", (), {"value": "classify this"})())
        self.assertEqual(result, {"provider": "llama.cpp-compatible",
                                  "requested_model": "fixture-model-v1",
                                  "served_model": "fixture-model-v1",
                                  "model_revision": None, "model_sha256": None,
                                  "output": "auth",
                                  "finish_reason": "stop"})
        request = self.requests[0]
        self.assertEqual(request["model"], "fixture-model-v1")
        self.assertEqual(request["messages"][0]["content"], "classify this")
        self.assertEqual(request["temperature"], 0)
        self.assertFalse(request["stream"])

    def test_rejects_non_loopback_or_credential_bearing_endpoint(self):
        for endpoint in ("http://example.com/v1", "https://127.0.0.1/v1",
                         "http://user:secret@127.0.0.1/v1",
                         "http://127.0.0.1/v1?redirect=1"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    LocalInferenceAction(endpoint, "model")

    def test_failure_is_sanitized_and_oversized_prompt_is_rejected(self):
        self.status = 503
        action = LocalInferenceAction(self.endpoint, "fixture-model-v1")
        with self.assertRaisesRegex(LocalInferenceError, "endpoint_http_503") as error:
            action({}, type("Grounded", (), {"value": "private prompt"})())
        self.assertNotIn("private prompt", str(error.exception))
        bounded = LocalInferenceAction(self.endpoint, "fixture-model-v1", max_prompt_bytes=2)
        with self.assertRaisesRegex(LocalInferenceError, "prompt_size_invalid"):
            bounded({}, type("Grounded", (), {"value": "too long"})())
        safe = LocalInferenceAction(self.endpoint, "fixture-model-v1")
        with self.assertRaisesRegex(LocalInferenceError, "prompt_sensitive_content"):
            safe({}, type("Grounded", (),
                         {"value": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz"})())

    def test_incomplete_response_is_not_returned_as_success(self):
        class IncompleteHandler(BaseHTTPRequestHandler):
            def do_POST(handler_self):
                body = b'{"model":"fixture-model-v1","choices":[{"message":{"content":"truncated"},"finish_reason":"length"}]}'
                handler_self.send_response(200)
                handler_self.send_header("Content-Length", str(len(body)))
                handler_self.end_headers()
                handler_self.wfile.write(body)

            def log_message(self, *_args):
                return

        self.server.shutdown()
        self.server.server_close()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), IncompleteHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        endpoint = f"http://127.0.0.1:{self.server.server_port}/v1"
        action = LocalInferenceAction(endpoint, "fixture-model-v1")
        with self.assertRaisesRegex(LocalInferenceError, "response_incomplete"):
            action({}, type("Grounded", (), {"value": "prompt"})())


if __name__ == "__main__":
    unittest.main()
