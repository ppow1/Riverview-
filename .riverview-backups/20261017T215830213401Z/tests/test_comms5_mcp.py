"""Comms5 Camrui compatibility adapter tests.

File Revision: 1.0.0
Component: COMMS5-CAMRUI-ADAPTER-TESTS
History: New file; no predecessor existed.
"""

import hashlib
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from riverview_core.comms5.server import Comms5Application, create_handler

CATALOG = Path(__file__).parents[1] / "src/riverview_core/comms5/tool_catalog.json"


def app():
    return Comms5Application("x" * 48)


def rpc(method, params=None, request_id=1):
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


class Comms5MCPTests(unittest.TestCase):
    def test_historical_catalog_is_complete_and_contract_metadata_works(self):
        catalog = json.loads(CATALOG.read_text())
        canonical = json.dumps(catalog["tools"], separators=(",", ":"), ensure_ascii=False).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), "d13698b1ad415d152f481c1a5360166ef1519b4ebd74944f0836f3341701a807")
        result = app().handle(rpc("tools/list"))["result"]["tools"]
        self.assertEqual(len(result), 21)
        self.assertEqual([tool["name"] for tool in result], [tool["name"] for tool in catalog["tools"]])
        self.assertTrue(all(tool["securitySchemes"] == [{"type": "oauth2", "scopes": ["comms5"]}] for tool in result))
        call = app().handle(rpc("tools/call", {"name": "comms5_contract_info", "arguments": {}}))
        payload = json.loads(call["result"]["content"][0]["text"])
        self.assertEqual(payload["contract"], "riverview-comms-contract:5.0")
        self.assertFalse(call["result"]["isError"])

    def test_help_and_describe_are_real_read_only_operations(self):
        application = app()
        help_result = application.handle(rpc("tools/call", {"name": "comms5_help", "arguments": {}}))
        help_value = json.loads(help_result["result"]["content"][0]["text"])
        self.assertEqual(help_value["contract"]["contract"], "riverview-comms-contract:5.0")
        self.assertEqual(help_value["camrui_migration_notice"]["not_implemented_tool_count"], 16)
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
                self.assertEqual(len(result["result"]["tools"]), 21)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
