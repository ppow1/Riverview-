# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_internal_tools.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.3
# Changed: 2026-10-17 UTC | RV-GRACE-PERSISTENT-AUTONOMY-001 | Verify Grace current-status tool call policy.
# Purpose: Verify Grace-originated bounded Comms5 tool calls return and retain structured results
# Execution Model: Isolated provider and Comms5 backend HTTP contract fixture
# Observability: Assertions over operation result envelopes and follow-up model consumption
# Dependencies: GraceInternalTools; GraceModelRouter; Comms5Application; DashboardReadBackend
# Authority: Read-only projection operations only
# Tests: python3 -m unittest tests.test_grace_internal_tools
# History: Git and revision/backup manifest
# =============================================================================
"""Focused internal tool round-trip tests for Grace."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from riverview_core.local_reasoning_provider import ChatCompletion, ProviderReadiness
from riverview_core.resident_execution.internal_tools import GraceInternalTools
from riverview_core.resident_execution.model_router import GraceModelRouter
from riverview_core.comms5.dashboard_backend import DashboardReadBackend


class Response:
    status = 200
    headers = type("Headers", (), {"get_content_type": lambda self: "application/json"})()

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, _size):
        return json.dumps({"projection_status": "healthy",
            "observed_at": "2026-10-17T12:00:00Z",
            "cme": {"status": "healthy", "workers_enabled": 2}}).encode()


class Provider:
    def __init__(self, model, answers=()):
        self.model = model
        self.model_sha256 = "a" * 64
        self.provider_id = "test." + model
        self.answers = list(answers)
        self.calls = []

    def readiness(self):
        return ProviderReadiness("READY", self.model, "ready")

    def complete_chat(self, messages, *, max_tokens, expected_revision, timeout_seconds=120):
        self.calls.append(messages)
        return ChatCompletion(self.answers.pop(0), self.model, 10, 8, "stop",
                              provider_id=self.provider_id)


class GraceInternalToolTests(unittest.TestCase):
    def test_grace_originated_call_returns_real_projection_result_and_consumes_it(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("d" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            with patch.object(backend, "_open", lambda _request: Response()):
                tools = GraceInternalTools(backend)
                self._assert_grace_tool_roundtrip(tools)

    def _assert_grace_tool_roundtrip(self, tools):
        names = {tool["name"] for tool in tools.catalog()}
        self.assertTrue({"comms5_cme_status", "comms5_objective_status",
                         "comms5_recent_steward_submissions", "comms5_transport_probe"}
                        <= names)
        self.assertTrue({"comms5_submit_steward_seed", "comms5_store_specification",
                         "comms5_confirm_and_promote_seed"} <= names)
        self.assertTrue({"comms5_get_notification_settings",
                         "comms5_set_notification_settings"} <= names)
        request = '<rv-tool-call>{"name":"comms5_cme_status","arguments":{}}</rv-tool-call>'
        cpu = Provider("0.6B", ["ack"])
        vision = Provider("30B", ["interim"])
        reasoning = Provider("80B", [request, "CME is healthy with two workers enabled."])
        router = GraceModelRouter(autonomic=cpu, vision=vision, reasoning=reasoning,
                                  internal_tools=tools)
        result = router.complete_chat([{"role": "user", "content": "Check CME status."}],
            max_tokens=96, expected_revision=router.model_sha256,
            required_capability="grace.reasoning.80b")
        self.assertEqual(result.content, "CME is healthy with two workers enabled.")
        self.assertEqual(result.internal_tool_results, ({
            "schema_version": "rv.grace.tool-result.v1", "status": "ok",
            "tool": "comms5_cme_status", "result": {
                "status": "available", "source": "riverview_dashboard_status_projection",
                "cme": {"status": "healthy", "workers_enabled": 2},
                "observed_at": "2026-10-17T12:00:00Z",
                "implementation_status": "IMPLEMENTED"}},))
        consumed = reasoning.calls[1]
        self.assertIn('"workers_enabled":2', " ".join(x["content"] for x in consumed))
        system_messages = [item for item in reasoning.calls[0] if item["role"] == "system"]
        self.assertEqual(len(system_messages), 1)
        tool_instructions = system_messages[0]["content"]
        self.assertIn("you MUST call the matching tool before answering", tool_instructions)
        self.assertIn("<rv-tool-call>", tool_instructions)

    def test_unknown_tools_and_invalid_arguments_are_structured_errors(self):
        class Backend:
            supported_tools = frozenset({"comms5_cme_status"})
            def call(self, name, args): raise AssertionError("unsupported call executed")
        tools = GraceInternalTools(Backend())
        self.assertEqual(tools.call("not_registered", {})["error"]["code"],
                         "tool_not_available")
        self.assertEqual(tools.call("comms5_cme_status", {"extra": True})["error"]["code"],
                         "tool_arguments_invalid")

    def test_required_current_lookup_retries_for_model_originated_tool_call(self):
        call = '<rv-tool-call>{"name":"comms5_cme_status","arguments":{}}</rv-tool-call>'

        class Tools:
            def __init__(self): self.calls = []
            def catalog(self):
                return [{"name": "comms5_cme_status", "inputSchema": {
                    "type": "object", "properties": {}, "additionalProperties": False}}]
            def call(self, name, arguments):
                self.calls.append((name, arguments))
                return {"schema_version": "rv.grace.tool-result.v1", "status": "ok",
                        "tool": name, "result": {"cme": {"status": "healthy"}}}

        tools = Tools()
        reasoning = Provider("80B", ["The CME is healthy from the dashboard snapshot.",
            call, "The current CME tool result reports healthy."])
        router = GraceModelRouter(autonomic=Provider("0.6B", ["ack"]),
            vision=Provider("30B", ["interim"]), reasoning=reasoning,
            internal_tools=tools)
        result = router.complete_chat([{"role": "user", "content":
            "Use your current internal Comms5 tool catalog and call comms5_cme_status "
            "to report actual CME worker status."}], max_tokens=96,
            expected_revision=router.model_sha256,
            required_capability="grace.reasoning.80b")

        self.assertEqual(len(reasoning.calls), 3)
        self.assertIn("emit only one valid tool call", reasoning.calls[1][-1]["content"].lower())
        self.assertEqual(tools.calls, [("comms5_cme_status", {})])
        self.assertEqual(result.internal_tool_results[0]["result"]["cme"]["status"], "healthy")
        self.assertEqual(result.content, "The current CME tool result reports healthy.")

    def test_required_current_lookup_fails_closed_if_model_still_omits_call(self):
        class Tools:
            def catalog(self):
                return [{"name": "comms5_cme_status", "inputSchema": {"type": "object"}}]
            def call(self, *_args): raise AssertionError("no tool call was emitted")

        reasoning = Provider("80B", ["The CME is healthy.", "The CME is healthy."])
        router = GraceModelRouter(autonomic=Provider("0.6B", ["ack"]),
            vision=Provider("30B", ["interim"]), reasoning=reasoning,
            internal_tools=Tools())
        result = router.complete_chat([{"role": "user", "content": "Check CME status."}],
            max_tokens=96, expected_revision=router.model_sha256,
            required_capability="grace.reasoning.80b")

        self.assertEqual(len(reasoning.calls), 2)
        self.assertIn("couldn't complete the requested current lookup", result.content)
        self.assertEqual(result.internal_tool_results[0]["status"], "error")
        self.assertEqual(result.internal_tool_results[0]["error"]["code"],
                         "required_tool_call_not_emitted")


if __name__ == "__main__":
    unittest.main()
