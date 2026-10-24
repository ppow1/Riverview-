"""Offline API-response parsing and exchange-submission tests; no provider calls."""
import hashlib
import json
import unittest
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from riverview_core.resident_execution import direct_luna
from riverview_core.resident_execution.external_reasoning import DurableExternalReasoningExchange


class _Exchange:
    RESPONSE_SCHEMA = DurableExternalReasoningExchange.RESPONSE_SCHEMA

    def __init__(self, *, request_type="cme_diagnostic_recovery", max_tokens=4096,
                 submit_error=None):
        self.request_id, self.correlation_id = uuid4(), uuid4()
        self.row = {"request_id": self.request_id, "correlation_id": self.correlation_id,
            "delivery_state": "awaiting_response",
            "request_payload": {"request_type": request_type, "max_tokens": max_tokens}}
        self.submit_error = submit_error
        self.submitted = []
        self.failures = []
        self.finished = []
        self.begin_args = None

    def eligible_requests(self, *_args, **_kwargs):
        return [self.row]

    def claim(self, *_args, **_kwargs):
        return SimpleNamespace(duplicate=False, claim_token="claim-token", fence=1)

    def begin_provider_attempt(self, *_args, **kwargs):
        self.begin_args = kwargs
        return True

    def finish_provider_attempt(self, *_args, **kwargs):
        self.finished.append(kwargs)

    def submit_response(self, request_id, correlation_id, **kwargs):
        self.submitted.append((request_id, correlation_id, kwargs))
        if self.submit_error:
            raise self.submit_error
        DurableExternalReasoningExchange._validate_response(
            kwargs["response"], request_id, correlation_id, direct_luna.PROVIDER_ID)
        return hashlib.sha256(b"fixture response").hexdigest()

    def fail_provider_response_submission(self, request_id, correlation_id, **kwargs):
        self.failures.append((request_id, correlation_id, kwargs))


class _HTTPResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.body


class DirectLunaAdapterUnitTests(unittest.TestCase):
    def _call(self, exchange, result):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _HTTPResponse(json.dumps(result).encode())

        with patch.object(direct_luna, "_api_key", return_value="synthetic-key"), \
             patch.object(direct_luna.urllib.request, "urlopen", side_effect=fake_urlopen):
            outcome = direct_luna.process_one(exchange)
        return outcome, captured

    def test_synthetic_luna_response_is_validated_and_submitted_once(self):
        exchange = _Exchange()
        advisory = json.dumps({"schema": "rv.grace.cme-recovery-advice.v1",
            "assessment": "evidence is incomplete", "recovery_action": "STEWARD_AUTHORIZATION_REQUIRED",
            "rationale": "the verifier rejected unsupported runtime claims",
            "correction_instruction": None, "criteria_to_address": []})
        outcome, captured = self._call(exchange, {"id": "resp_fixture_1", "model": "gpt-6-luna",
            "status": "completed", "incomplete_details": None,
            "output_text": advisory, "usage": {"input_tokens": 100, "output_tokens": 80,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens_details": {"reasoning_tokens": 20}}})
        self.assertEqual(outcome["status"], "RESPONSE_SUBMITTED")
        self.assertEqual(len(exchange.submitted), 1)
        request_id, correlation_id, args = exchange.submitted[0]
        self.assertEqual(request_id, exchange.request_id)
        self.assertEqual(correlation_id, exchange.correlation_id)
        self.assertEqual(args["idempotency_key"], "luna:" + str(exchange.request_id))
        self.assertEqual(args["response"]["advisory"], advisory)
        request_body = json.loads(captured["request"].data)
        self.assertEqual(request_body["max_output_tokens"], 4096)
        self.assertEqual(request_body["text"]["format"]["type"], "json_object")
        self.assertEqual(len(exchange.failures), 0)

    def test_submission_failure_records_sanitized_detail_and_does_not_retry(self):
        exchange = _Exchange(submit_error=TypeError(
            "can only concatenate str (not 'UUID') to str; api_key=sk-abcdefghijklmno"))
        outcome, _captured = self._call(exchange, {"id": "resp_fixture_2", "model": "gpt-6-luna",
            "status": "completed", "incomplete_details": None,
            "output_text": "{}", "usage": {"input_tokens": 100, "output_tokens": 80,
                "output_tokens_details": {"reasoning_tokens": 20}}})
        self.assertEqual(outcome["status"], "RESPONSE_SUBMISSION_FAILED")
        self.assertEqual(len(exchange.submitted), 1)
        self.assertEqual(len(exchange.failures), 1)
        detail = exchange.failures[0][2]["failure_detail"]
        self.assertIn("TypeError", detail)
        self.assertIn("UUID", detail)
        self.assertNotIn("sk-abcdefghijklmno", detail)

    def test_output_allowances_are_per_request_type_and_sent_to_responses(self):
        for request_type, limit in (("cme_diagnostic_recovery", 4096),
                                    ("performance_evaluation", 2048)):
            with self.subTest(request_type=request_type):
                exchange = _Exchange(request_type=request_type, max_tokens=limit)
                outcome, captured = self._call(exchange, {"id": "resp_fixture_limit",
                    "model": "gpt-6-luna", "status": "completed", "incomplete_details": None,
                    "output_text": "{}", "usage": {"input_tokens": 10, "output_tokens": 4,
                        "output_tokens_details": {"reasoning_tokens": 1}}})
                self.assertEqual(outcome["status"], "RESPONSE_SUBMITTED")
                body = json.loads(captured["request"].data)
                self.assertEqual(body["max_output_tokens"], limit)
                self.assertEqual(body["text"]["format"]["type"], "json_object")
                self.assertEqual(exchange.begin_args["reserved_cost"], 0.05)

    def test_over_limit_or_incomplete_response_is_never_submitted(self):
        oversized = _Exchange(request_type="performance_evaluation", max_tokens=2049)
        outcome, _captured = self._call(oversized, {"id": "unused", "model": "gpt-6-luna",
            "status": "completed", "output_text": "{}", "usage": {}})
        self.assertEqual(outcome["status"], "REQUEST_TOKEN_BUDGET_INVALID")
        self.assertEqual(oversized.submitted, [])

        incomplete = _Exchange(request_type="performance_evaluation", max_tokens=2048)
        outcome, _captured = self._call(incomplete, {"id": "resp_fixture_incomplete",
            "model": "gpt-6-luna", "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
            "output_text": '{"schema":"rv.grace.performance-evaluation.v1"',
            "usage": {"input_tokens": 100, "output_tokens": 2048,
                "output_tokens_details": {"reasoning_tokens": 700}}})
        self.assertEqual(outcome["status"], "INCOMPLETE_RESPONSE")
        self.assertEqual(outcome["incomplete_reason"], "max_output_tokens")
        self.assertEqual(incomplete.submitted, [])
        self.assertEqual(len(incomplete.failures), 1)
        self.assertEqual(incomplete.finished[0]["status"], "failed")
        self.assertEqual(incomplete.finished[0]["usage"]["output_tokens"], 2048)


if __name__ == "__main__":
    unittest.main()
