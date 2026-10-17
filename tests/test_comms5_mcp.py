"""Comms5 Camrui compatibility adapter tests.

File Revision: 1.0.0
Component: COMMS5-CAMRUI-ADAPTER-TESTS
History: New file; no predecessor existed.
"""

import hashlib
import json
import threading
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


def test_historical_catalog_is_complete_and_contract_metadata_works():
    catalog = json.loads(CATALOG.read_text())
    canonical = json.dumps(catalog["tools"], separators=(",", ":"), ensure_ascii=False).encode()
    assert hashlib.sha256(canonical).hexdigest() == "d13698b1ad415d152f481c1a5360166ef1519b4ebd74944f0836f3341701a807"
    result = app().handle(rpc("tools/list"))["result"]["tools"]
    assert len(result) == 21
    assert [tool["name"] for tool in result] == [tool["name"] for tool in catalog["tools"]]
    assert all(tool["securitySchemes"] == [{"type": "oauth2", "scopes": ["comms5"]}] for tool in result)
    call = app().handle(rpc("tools/call", {"name": "comms5_contract_info", "arguments": {}}))
    payload = json.loads(call["result"]["content"][0]["text"])
    assert payload["contract"] == "riverview-comms-contract:5.0"
    assert call["result"]["isError"] is False


def test_help_and_describe_are_real_read_only_operations():
    application = app()
    help_result = application.handle(rpc("tools/call", {"name": "comms5_help", "arguments": {}}))
    help_value = json.loads(help_result["result"]["content"][0]["text"])
    assert help_value["contract"]["contract"] == "riverview-comms-contract:5.0"
    assert help_value["camrui_migration_notice"]["not_implemented_tool_count"] == 16
    capabilities = application.handle(rpc("tools/call", {"name": "comms5_capabilities", "arguments": {}}))
    capability_value = json.loads(capabilities["result"]["content"][0]["text"])
    assert sum(op["camrui_implementation_status"] == "IMPLEMENTED" for op in capability_value["operations"]) == 5
    describe = application.handle(rpc("tools/call", {"name": "comms5_describe_operation", "arguments": {"operation": "submit_steward_seed"}}))
    value = json.loads(describe["result"]["content"][0]["text"])
    assert value["authorization"] == "DRAFT_WRITE"
    assert value["camrui_implementation_status"] == "NOT_IMPLEMENTED"


def test_unimplemented_write_is_explicit_tool_error_and_no_executor_exists():
    result = app().handle(rpc("tools/call", {"name": "comms5_submit_steward_seed", "arguments": {
        "seed_text": "not persisted", "idempotency_key": "test", "client_id": "x",
        "client_type": "x", "client_name": "x", "authenticated_principal": "steward",
    }}))
    tool_result = result["result"]
    assert tool_result["isError"] is True
    value = json.loads(tool_result["content"][0]["text"])
    assert tool_result["structuredContent"] == value
    assert value == {
        "status": "NOT_IMPLEMENTED", "executed": False,
        "tool": "comms5_submit_steward_seed",
        "reason": "Historical operation is retained in the MCP catalog but its current Camrui backend contract has not yet been verified.",
    }
    implementation = Path(__import__("riverview_core.comms5.server", fromlist=["__file__"]).__file__).read_text()
    assert "psycopg" not in implementation and "connect(" not in implementation


def test_schema_validation_rejects_extra_and_missing_arguments():
    application = app()
    missing = application.handle(rpc("tools/call", {"name": "comms5_describe_operation", "arguments": {}}))
    extra = application.handle(rpc("tools/call", {"name": "comms5_contract_info", "arguments": {"unexpected": True}}))
    assert missing["error"]["code"] == -32602
    assert extra["error"]["code"] == -32602


def test_initialization_versions_and_notifications():
    application = app()
    current = application.handle(rpc("initialize", {"protocolVersion": "2025-11-25"}))
    assert current["result"]["protocolVersion"] == "2025-11-25"
    init = application.handle(rpc("initialize", {"protocolVersion": "2025-03-26"}))
    assert init["result"]["serverInfo"]["name"] == "Riverview Comms5"
    assert application.handle(rpc("initialize", {"protocolVersion": "2099-01-01"}))["error"]["code"] == -32602
    assert application.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_backend_accepts_only_caddy_attested_hop_and_exact_token():
    application = app()

    class Headers(dict):
        pass

    good = Headers({
        "X-Riverview-Comms5": "1", "X-Riverview-Comms5-Principal": "steward",
        "Authorization": "Bearer " + "x" * 48,
    })
    assert application.authenticated(good)
    assert not application.authenticated(Headers({**good, "X-Riverview-Comms5": "0"}))
    assert not application.authenticated(Headers({**good, "X-Riverview-Comms5-Principal": "operator"}))
    assert not application.authenticated(Headers({**good, "Authorization": "Bearer wrong"}))


def test_real_http_mcp_path_rejects_unauthenticated_and_serves_tool_list():
    application = Comms5Application("x" * 48)
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(application))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/mcp"
    payload = json.dumps(rpc("tools/list")).encode()
    try:
        request = Request(base, data=payload, headers={"Content-Type": "application/json"})
        try:
            urlopen(request, timeout=2)
            assert False, "unauthenticated MCP request was accepted"
        except HTTPError as error:
            assert error.code == 401
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
            assert response.status == 200
            assert len(result["result"]["tools"]) == 21
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
