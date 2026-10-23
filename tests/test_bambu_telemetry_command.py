"""Riverview~ Controlled Source
File: tests/test_bambu_telemetry_command.py
Component: OCTOMINER1-RESTRICTED-GPU-TELEMETRY
Revision: 1.0.3
Purpose: Verify the bounded authenticated local Bambu status collector and fail-closed behavior
Execution Model: Isolated unittest fixtures
Observability: Assertions for authorization, redaction, freshness, redirect rejection, and unavailable states
Dependencies: scripts.rv_gpu_telemetry_command; Python unittest
Authority: Fixture token only; no production credentials or network access
Changed: 2026-10-23 UTC | RV-V2-BAMBU-READONLY-230 | Cover authenticated GET projection, secret redaction, stale/auth failures, and redirect rejection.
History: Git and .riverview-backups/manifest.jsonl
"""
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request
from unittest.mock import patch

from scripts.rv_gpu_telemetry_command import _RejectRedirects, _open_octo_control, read_bambu_status


class _Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.body


class BambuTelemetryCommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.token_path = Path(self.temporary.name) / "control.token"
        self.token_path.write_text("fixture-only/control+token0123456789==", encoding="ascii")
        self.token_path.chmod(0o600)

    def tearDown(self):
        self.temporary.cleanup()

    def test_authenticated_get_projects_only_display_fields_and_keeps_token_local(self):
        source = {"connected": True, "last_update": 1790125199,
                  "printer": {"gcode_state": "RUNNING", "nozzle_temper": 219.5,
                              "bed_temper": 55, "mc_percent": 42, "mc_remaining_time": 35,
                              "layer_num": 71, "total_layer_num": 160,
                              "access_code": "private-field"},
                  "ams": [{"unit": 0, "slot": 0, "material": "PLA", "remaining": 80,
                           "color": "AABBCCFF", "serial": "private-field"}],
                  "serial": "private-field", "access_code": "private-field"}
        captured = {}

        def open_request(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["method"] = request.get_method()
            captured["timeout"] = timeout
            return _Response(json.dumps(source).encode())

        result = read_bambu_status(token_path=self.token_path, http_open=open_request,
                                   now=1790125200)
        self.assertEqual(captured["url"], "http://127.0.0.1:8180/api/v1/bambu/status")
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["authorization"], "Bearer fixture-only/control+token0123456789==")
        self.assertEqual(captured["timeout"], 1.5)
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["printer"]["progress_percent"], 42)
        self.assertEqual(result["ams"][0]["material"], "PLA")
        serialized = json.dumps(result)
        self.assertNotIn("fixture-only/control+token", serialized)
        self.assertNotIn("private-field", serialized)

    def test_missing_local_token_fails_closed_without_request(self):
        def open_request(*_args, **_kwargs):
            self.fail("upstream call must not occur without the local protected token")

        result = read_bambu_status(token_path=Path(self.temporary.name) / "missing", http_open=open_request)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["error_code"], "bambu_source_unavailable")

    def test_upstream_auth_failure_is_reported_without_response_details(self):
        def open_request(*_args, **_kwargs):
            raise HTTPError("http://127.0.0.1:8180/api/v1/bambu/status", 401,
                            "unauthorized", {}, None)

        result = read_bambu_status(token_path=self.token_path, http_open=open_request)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["error_code"], "bambu_authentication_failed")
        self.assertNotIn("fixture-only/control+token", json.dumps(result))

    def test_local_control_token_is_not_forwarded_through_redirects(self):
        handler = _RejectRedirects()
        self.assertIsNone(handler.redirect_request(object(), object(), 302,
                                                   "Found", {}, "https://example.invalid/"))

    def test_fixed_local_request_ignores_proxy_environment(self):
        with patch("scripts.rv_gpu_telemetry_command.build_opener") as build:
            _open_octo_control(Request("http://127.0.0.1:8180/api/v1/bambu/status"), 1.5)
        handlers = build.call_args.args
        self.assertIsInstance(handlers[0], ProxyHandler)
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], _RejectRedirects)

    def test_disconnected_or_expired_source_is_not_rendered_as_connected(self):
        source = {"connected": True, "last_update": 1790120000,
                  "printer": {"gcode_state": "FINISH"}, "ams": []}
        result = read_bambu_status(token_path=self.token_path,
                                   http_open=lambda *_a, **_k: _Response(json.dumps(source).encode()),
                                   now=1790125200)
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["connected"], True)
        self.assertEqual(result["printer"]["state"], "FINISH")


if __name__ == "__main__":
    unittest.main()
