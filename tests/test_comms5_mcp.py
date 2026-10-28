"""Comms5 Camrui compatibility adapter tests.

File Revision: 1.1.7
Component: COMMS5-CAMRUI-ADAPTER-TESTS
History: New file; no predecessor existed.
Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Verify authenticated internal operation routing for full objective status and submission listing.
Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Verify transport probes return caller and dashboard correlation evidence and reject unauthenticated direct use.
Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Verify the Steward queue request uses the attested dashboard operation bridge and preserves its truthful queued state.
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Verify the 25-tool catalog, preserved legacy catalog, and authenticated reasoning bridge dispatch.
Changed: 2026-10-28 UTC | GRACE-FRESH-INTAKE-CONTROL-GAP-20261028 | Verify registered objective cancellation is dispatched only through the attested Steward bridge.
"""

import hashlib
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from riverview_core.comms5.server import Comms5Application, create_handler
from riverview_core.comms5.dashboard_backend import (
    DashboardBackendUnavailable, DashboardReadBackend, DashboardRecordNotFound,
)

CATALOG = Path(__file__).parents[1] / "src/riverview_core/comms5/tool_catalog.json"


def app():
    return Comms5Application("x" * 48)


def rpc(method, params=None, request_id=1):
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


class Comms5MCPTests(unittest.TestCase):
    def test_historical_catalog_is_complete_and_contract_metadata_works(self):
        catalog = json.loads(CATALOG.read_text())
        canonical = json.dumps(catalog["tools"][:21], separators=(",", ":"), ensure_ascii=False).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), "d13698b1ad415d152f481c1a5360166ef1519b4ebd74944f0836f3341701a807")
        result = app().handle(rpc("tools/list"))["result"]["tools"]
        self.assertEqual(len(result), 33)
        self.assertIn("comms5_authorize_grace_experiment", [tool["name"] for tool in result])
        self.assertIn("comms5_cancel_objective", [tool["name"] for tool in result])
        self.assertEqual([tool["name"] for tool in result], [tool["name"] for tool in catalog["tools"]])
        exchange_names = ["reasoning_exchange_list_requests", "reasoning_exchange_claim_request",
            "reasoning_exchange_submit_response", "reasoning_exchange_status"]
        by_name = {tool["name"]: tool for tool in result}
        self.assertTrue(all(tool["securitySchemes"] == [{"type": "oauth2", "scopes": ["comms5"]}] for tool in result))
        from riverview_core.resident_execution.external_reasoning_mcp import ExternalReasoningMCPAdapter
        shared = {tool["name"]: tool["inputSchema"] for tool in ExternalReasoningMCPAdapter.tools()}
        self.assertEqual({name: by_name[name]["inputSchema"] for name in exchange_names}, shared)
        call = app().handle(rpc("tools/call", {"name": "comms5_contract_info", "arguments": {}}))
        payload = json.loads(call["result"]["content"][0]["text"])
        self.assertEqual(payload["contract"], "riverview-comms-contract:5.0")
        self.assertFalse(call["result"]["isError"])

    def test_reasoning_tools_dispatch_only_through_authenticated_steward_backend(self):
        class ReviewBackend:
            supported_tools = {"reasoning_exchange_status"}

            def call_authenticated(self, name, arguments, *, principal=None):
                if principal != "steward":
                    raise PermissionError("steward required")
                return {"request_id": arguments["request_id"],
                        "correlation_id": arguments["correlation_id"],
                        "delivery_state": "awaiting_response"}

        application = Comms5Application("x" * 48, backend=ReviewBackend())
        args = {"request_id": "00000000-0000-4000-8000-000000000001",
                "correlation_id": "00000000-0000-4000-8000-000000000002"}
        result = application.handle(rpc("tools/call", {
            "name": "reasoning_exchange_status", "arguments": args}), principal="steward")
        self.assertEqual(result["result"]["structuredContent"]["delivery_state"], "awaiting_response")
        denied = application.handle(rpc("tools/call", {
            "name": "reasoning_exchange_status", "arguments": args}), principal="provider")
        self.assertTrue(denied["result"]["isError"])
        self.assertEqual(denied["result"]["structuredContent"]["status"], "NOT_AUTHORIZED")

    def test_help_and_describe_are_real_read_only_operations(self):
        application = app()
        help_result = application.handle(rpc("tools/call", {"name": "comms5_help", "arguments": {}}))
        help_value = json.loads(help_result["result"]["content"][0]["text"])
        self.assertEqual(help_value["contract"]["contract"], "riverview-comms-contract:5.0")
        self.assertEqual(help_value["camrui_migration_notice"]["not_implemented_tool_count"], 23)
        capabilities = application.handle(rpc("tools/call", {"name": "comms5_capabilities", "arguments": {}}))
        capability_value = json.loads(capabilities["result"]["content"][0]["text"])
        self.assertEqual(sum(op["camrui_implementation_status"] == "IMPLEMENTED" for op in capability_value["operations"]), 5)
        describe = application.handle(rpc("tools/call", {"name": "comms5_describe_operation", "arguments": {"operation": "submit_steward_seed"}}))
        value = json.loads(describe["result"]["content"][0]["text"])
        self.assertEqual(value["authorization"], "DRAFT_WRITE")
        self.assertEqual(value["camrui_implementation_status"], "NOT_IMPLEMENTED")

    def test_unimplemented_write_is_explicit_tool_error_and_no_executor_exists(self):
        result = app().handle(rpc("tools/call", {"name": "comms5_submit_steward_seed", "arguments": {
            "seed_text": "not persisted", "idempotency_key": "test", "client_id": "x",
            "client_type": "x", "client_name": "x", "authenticated_principal": "steward",
        }}))
        tool_result = result["result"]
        self.assertTrue(tool_result["isError"])
        value = json.loads(tool_result["content"][0]["text"])
        self.assertEqual(tool_result["structuredContent"], value)
        self.assertEqual(value, {
            "status": "NOT_IMPLEMENTED", "executed": False,
            "tool": "comms5_submit_steward_seed",
            "reason": "Historical operation is retained in the MCP catalog but its current Camrui backend contract has not yet been verified.",
        })
        implementation = Path(__import__("riverview_core.comms5.server", fromlist=["__file__"]).__file__).read_text()
        self.assertNotIn("psycopg", implementation)
        self.assertNotIn("connect(", implementation)

    def test_schema_validation_rejects_extra_and_missing_arguments(self):
        application = app()
        missing = application.handle(rpc("tools/call", {"name": "comms5_describe_operation", "arguments": {}}))
        extra = application.handle(rpc("tools/call", {"name": "comms5_contract_info", "arguments": {"unexpected": True}}))
        self.assertEqual(missing["error"]["code"], -32602)
        self.assertEqual(extra["error"]["code"], -32602)

    def test_initialization_versions_and_notifications(self):
        application = app()
        current = application.handle(rpc("initialize", {"protocolVersion": "2025-11-25"}))
        self.assertEqual(current["result"]["protocolVersion"], "2025-11-25")
        init = application.handle(rpc("initialize", {"protocolVersion": "2025-03-26"}))
        self.assertEqual(init["result"]["serverInfo"]["name"], "Riverview Comms5")
        self.assertEqual(application.handle(rpc("initialize", {"protocolVersion": "2099-01-01"}))["error"]["code"], -32602)
        self.assertIsNone(application.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_dashboard_backend_uses_attested_internal_operation_for_objective_status(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("a" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(
                base_url="http://127.0.0.1:8767", credential_file=credential)
            application = Comms5Application("x" * 48, backend=backend)
            objective = {"status": "available", "executed": True,
                "objective": {"objective_id": "objective:test-1", "state": "COMPLETED"},
                "assignment": {"id": "assignment:test-1", "state": "completed"}}
            with patch.object(backend, "_post_operation", return_value=objective) as operation:
                result = application.handle(rpc("tools/call", {
                    "name": "comms5_objective_status",
                    "arguments": {"objective_id": "objective:test-1"},
                }), principal="steward")
            value = result["result"]["structuredContent"]
            self.assertEqual(value["objective"]["state"], "COMPLETED")
            self.assertEqual(value["implementation_status"], "IMPLEMENTED")
            operation.assert_called_once_with("comms5_objective_status", {"objective_id": "objective:test-1"})

    def test_dashboard_backend_routes_queue_request_only_for_attested_steward(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("a" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            request = {"objective_id": "objective:approved", "stage_id": "step:one",
                       "authority_id": "grant:objective-submit", "explicit_steward_confirmation": True}
            result = {"status": "queued_for_cme", "executed": True,
                      "work_order_created": False, "dispatched": False}
            with patch.object(backend, "_post_operation", return_value=result) as operation:
                self.assertEqual(backend.call_authenticated("comms5_form_and_queue_work",
                    request, principal="steward"), result)
                operation.assert_called_once_with("comms5_form_and_queue_work", request)
            with self.assertRaisesRegex(PermissionError, "Steward"):
                backend.call_authenticated("comms5_form_and_queue_work", request,
                                           principal="resident:grace")

    def test_dashboard_backend_routes_objective_cancellation_only_for_attested_steward(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("a" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            request = {"objective_id": "objective:stale-dev", "reason": "Replace stale request",
                       "explicit_steward_confirmation": True}
            result = {"status": "CANCELLED", "executed": True,
                      "objective_id": "objective:stale-dev", "revision": 3}
            with patch.object(backend, "_post_operation", return_value=result) as operation:
                self.assertEqual(backend.call_authenticated("comms5_cancel_objective",
                    request, principal="steward"), result)
                operation.assert_called_once_with("comms5_cancel_objective", request)
            with self.assertRaisesRegex(PermissionError, "Steward"):
                backend.call_authenticated("comms5_cancel_objective", request,
                                           principal="resident:grace")

    def test_objective_lookup_uses_exact_id_route_and_reports_missing_record(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("e" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            with patch.object(backend, "_post_operation", return_value={
                    "status": "not_found", "objective_id": "objective:absent"}) as get:
                result = backend.call_authenticated("comms5_objective_status",
                    {"objective_id": "objective:absent"}, principal="steward")
            get.assert_called_once_with("comms5_objective_status", {"objective_id": "objective:absent"})
            self.assertEqual(result["status"], "not_found")
            with self.assertRaises(PermissionError):
                backend.call_authenticated("comms5_objective_status",
                    {"objective_id": "objective:absent"}, principal="resident")

    def test_dashboard_cme_status_returns_authoritative_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("b" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            application = Comms5Application("x" * 48, backend=backend)
            projection = {"projection_status": "healthy", "observed_at": "2026-10-17T00:00:00Z",
                          "cme": {"status": "healthy", "workers_registered": 2,
                                  "workers_enabled": 1, "last_error_type": None}}
            with patch.object(backend, "_get", return_value=projection):
                result = application.handle(rpc("tools/call", {
                    "name": "comms5_cme_status", "arguments": {},
                }))
            self.assertFalse(result["result"]["isError"])
            self.assertEqual(result["result"]["structuredContent"]["cme"], projection["cme"])

    def test_transport_probe_reports_only_the_path_it_actually_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("f" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            application = Comms5Application("x" * 48, backend=backend)
            with patch.object(backend, "_get_response", return_value=({
                "projection_status": "healthy", "observed_at": "2026-10-17T00:00:00Z",
            }, "dash-probe-1")):
                result = application.handle(rpc("tools/call", {
                    "name": "comms5_transport_probe", "arguments": {"probe_id": "probe:smoke-1"},
                }), principal="steward")
            value = result["result"]["structuredContent"]
            self.assertEqual(value["status"], "available")
            self.assertEqual(value["probe_id"], "probe:smoke-1")
            self.assertEqual(value["correlation_id"], "probe:smoke-1")
            self.assertEqual(value["dashboard_request_id"], "dash-probe-1")
            self.assertEqual(value["implementation_status"], "IMPLEMENTED")
            self.assertEqual(value["verified_path"], ["authenticated_comms5_request",
                "camrui_comms5_adapter", "dashboard_loopback_read_api"])

    def test_dashboard_failure_is_visible_and_non_successful(self):
        class Backend:
            supported_tools = {"comms5_cme_status"}

            def call(self, name, arguments):
                raise DashboardBackendUnavailable("dashboard_unavailable")

        result = Comms5Application("x" * 48, backend=Backend()).handle(rpc("tools/call", {
            "name": "comms5_cme_status", "arguments": {},
        }))
        self.assertTrue(result["result"]["isError"])
        self.assertEqual(result["result"]["structuredContent"], {
            "status": "BACKEND_UNAVAILABLE", "executed": False,
            "tool": "comms5_cme_status", "reason": "dashboard_unavailable",
        })

    def test_dashboard_backend_rejects_non_loopback_and_reports_partial_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("c" * 48)
            credential.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "loopback"):
                DashboardReadBackend(base_url="http://example.com:8767", credential_file=credential)
            application = Comms5Application(
                "x" * 48, backend=DashboardReadBackend(credential_file=credential))
            result = application.handle(rpc("tools/call", {
                "name": "comms5_capabilities", "arguments": {},
            }))
            operations = result["result"]["structuredContent"]["operations"]
            statuses = {"comms5_" + item["name"]: item["camrui_implementation_status"]
                        for item in operations}
            self.assertEqual(statuses["comms5_cme_status"], "IMPLEMENTED")
            self.assertEqual(statuses["comms5_objective_status"], "IMPLEMENTED")
            self.assertEqual(statuses["comms5_recent_steward_submissions"], "IMPLEMENTED")
            self.assertEqual(statuses["comms5_transport_probe"], "IMPLEMENTED")
            self.assertEqual(statuses["comms5_seed_status"], "IMPLEMENTED")
            self.assertEqual(statuses["comms5_submit_steward_seed"], "IMPLEMENTED")
            self.assertEqual(statuses["comms5_confirm_and_promote_seed"], "IMPLEMENTED")
            self.assertEqual(statuses["comms5_cancel_objective"], "IMPLEMENTED")

    def test_dashboard_backend_rejects_noncanonical_objective_list_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("g" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            for path in (
                "/api/v1/objectives?limit=1&unexpected=1",
                "/api/v1/objectives?limit=0",
                "/api/v1/objectives?limit=1000",
                "/api/v1/objectives?limit=1/../status",
            ):
                with self.subTest(path=path), self.assertRaisesRegex(
                        DashboardBackendUnavailable, "path_not_allowlisted"):
                    backend._get(path)

    def test_dashboard_backend_sends_only_authenticated_fixed_read_request(self):
        class Response:
            status = 200
            headers = type("Headers", (), {"get_content_type": lambda self: "application/json",
                "get": lambda self, key: None})()
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b'{"projection_status":"healthy","cme":{"status":"healthy"}}'

        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("d" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            captured = {}
            def fake_urlopen(request):
                captured["request"] = request
                return Response()
            with patch.object(backend, "_open", fake_urlopen):
                result = backend.call("comms5_cme_status", {})
            request = captured["request"]
            self.assertEqual(request.full_url, "http://127.0.0.1:8767/api/v1/status")
            self.assertEqual(request.get_method(), "GET")
            self.assertTrue(request.get_header("Authorization").startswith("Bearer "))
            self.assertEqual(backend.timeout, 3.0)
            self.assertEqual(result["cme"]["status"], "healthy")

    def test_transport_probe_correlates_authenticated_mcp_to_dashboard_request(self):
        class Headers:
            def get_content_type(self): return "application/json"
            def get(self, key): return "d1f00d12ab34" if key == "X-Request-ID" else None

        class Response:
            status = 200
            headers = Headers()
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size):
                return b'{"projection_status":"healthy","observed_at":"2026-10-17T00:00:00Z"}'

        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("e" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            captured = {}
            def fake_open(request):
                captured["request"] = request
                return Response()
            with patch.object(backend, "_open", fake_open):
                result = backend.call_authenticated(
                    "comms5_transport_probe", {"probe_id": "probe:accepted-1"},
                    principal="steward")
            self.assertEqual(captured["request"].full_url,
                             "http://127.0.0.1:8767/api/v1/status")
            self.assertEqual(result["status"], "available")
            self.assertTrue(result["executed"])
            self.assertEqual(result["implementation_status"], "IMPLEMENTED")
            self.assertEqual(result["correlation_id"], "probe:accepted-1")
            self.assertEqual(result["dashboard_request_id"], "d1f00d12ab34")
            self.assertEqual(result["verified_path"], [
                "authenticated_comms5_request", "camrui_comms5_adapter",
                "dashboard_loopback_read_api"])
            with self.assertRaisesRegex(PermissionError, "Steward"):
                backend.call_authenticated("comms5_transport_probe",
                    {"probe_id": "probe:unauthenticated"}, principal=None)

    def test_backend_accepts_only_caddy_attested_hop_and_exact_token(self):
        application = app()

        class Headers(dict):
            pass

        good = Headers({
            "X-Riverview-Comms5": "1", "X-Riverview-Comms5-Principal": "steward",
            "Authorization": "Bearer " + "x" * 48,
        })
        self.assertTrue(application.authenticated(good))
        self.assertFalse(application.authenticated(Headers({**good, "X-Riverview-Comms5": "0"})))
        self.assertFalse(application.authenticated(Headers({**good, "X-Riverview-Comms5-Principal": "operator"})))
        self.assertFalse(application.authenticated(Headers({**good, "Authorization": "Bearer wrong"})))

    def test_real_http_mcp_path_rejects_unauthenticated_and_serves_tool_list(self):
        application = Comms5Application("x" * 48)
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(application))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/mcp"
        payload = json.dumps(rpc("tools/list")).encode()
        try:
            request = Request(base, data=payload, headers={"Content-Type": "application/json"})
            with self.assertRaises(HTTPError) as failure:
                urlopen(request, timeout=2)
            self.assertEqual(failure.exception.code, 401)
            request = Request(base, data=payload, headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-03-26",
                "X-Riverview-Comms5": "1",
                "X-Riverview-Comms5-Principal": "steward",
                "Authorization": "Bearer " + "x" * 48,
            })
            with urlopen(request, timeout=2) as response:
                result = json.loads(response.read())
                self.assertEqual(response.status, 200)
            self.assertEqual(len(result["result"]["tools"]), 33)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
