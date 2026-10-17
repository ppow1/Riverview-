# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_external_reasoning_mcp.py
# Component: EXTERNAL-REASONING-MCP-TRANSPORT
# Revision: 1.0.3
# Purpose: Exercise MCP Streamable HTTP and bearer identity mapping independently
# Execution Model: Local ephemeral HTTP server; stdlib client independent of adapter dispatch
# Observability: HTTP status, protocol negotiation, tool names and sanitized denials
# Dependencies: Python standard library; external_reasoning_mcp module
# Authority: Synthetic tokens and exchange fixture; no production database or route
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Initial protocol/client tests
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Include finite provider-token expiry in independent client fixtures
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Allocate an ephemeral test port without weakening runtime port validation
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Verify 2025 version-header fallback and authentication on disabled GET stream
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Independent HTTP-client tests for the stateless MCP Streamable HTTP surface."""

import hashlib
import http.client
import json
import socket
import threading
import unittest
from types import SimpleNamespace

from riverview_core.resident_execution.external_reasoning import DurableExternalReasoningExchange
from riverview_core.resident_execution.external_reasoning_mcp import (
    ExternalReasoningMCPAdapter, MCPConfigurationError, ProviderTokenMap,
    create_server,
)


TOKEN = "synthetic-provider-token-for-independent-mcp-test-0001"
PROVIDER = "test:provider"
PRINCIPAL = "test:provider"


class _FixtureExchange(DurableExternalReasoningExchange):
    def __init__(self):
        self.router = SimpleNamespace(providers={PROVIDER: SimpleNamespace(provider_id=PROVIDER,
            exchange_principal_id=PRINCIPAL)})


class IndependentMCPClientTests(unittest.TestCase):
    def setUp(self):
        self.tokens = ProviderTokenMap.from_document({
            "schema_version": ProviderTokenMap.SCHEMA,
            "tokens": [{"token_sha256": hashlib.sha256(TOKEN.encode()).hexdigest(),
                "provider_id": PROVIDER, "principal_id": PRINCIPAL,
                "scopes": ["reasoning:exchange"],
                "expires_at": "2099-01-01T00:00:00Z"}]})
        self.adapter = ExternalReasoningMCPAdapter(_FixtureExchange(), self.tokens)
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        self.server = create_server(self.adapter, host="127.0.0.1", port=port,
            resource_url="https://mcp.example.test/mcp",
            authorization_server_url="https://identity.example.test/")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _request(self, method, message=None, *, token=TOKEN, protocol=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {"Host": "127.0.0.1", "Accept": "application/json, text/event-stream"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if protocol:
            headers["MCP-Protocol-Version"] = protocol
        if method:
            headers["Mcp-Method"] = method
        body = b"" if message is None else json.dumps(message).encode()
        headers["Content-Type"] = "application/json"
        connection.request("POST", "/mcp", body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        result = (response.status, dict(response.getheaders()),
                  json.loads(raw) if raw else None)
        connection.close()
        return result

    def test_independent_client_initializes_discovers_and_receives_auth_denial(self):
        status, headers, body = self._request("initialize", {
            "jsonrpc": "2.0", "id": "init-1", "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "independent-stdlib-client", "version": "1.0"}}})
        self.assertEqual(status, 200)
        self.assertEqual(body["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(body["result"]["serverInfo"]["name"],
                         "Riverview External Reasoning Exchange")
        status, _, body = self._request("notifications/initialized", {
            "jsonrpc": "2.0", "method": "notifications/initialized"},
            protocol="2025-11-25")
        self.assertEqual(status, 202)
        status, _, body = self._request("tools/list", {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            protocol="2025-11-25")
        self.assertEqual(status, 200)
        names = [tool["name"] for tool in body["result"]["tools"]]
        self.assertEqual(names, ["reasoning_exchange_list_requests",
            "reasoning_exchange_claim_request", "reasoning_exchange_submit_response",
            "reasoning_exchange_status"])
        self.assertNotIn("reasoning_exchange_consume", names)
        status, _, body = self._request("tools/list", {
            "jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}},
            protocol=None)
        self.assertEqual(status, 200)
        self.assertEqual(body["id"], 4)
        status, headers, body = self._request("tools/list", {
            "jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            token="x" * 48, protocol="2025-11-25")
        self.assertEqual(status, 401)
        self.assertIn("resource_metadata=", headers["WWW-Authenticate"])
        self.assertEqual(body["error"], "unauthorized")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("GET", "/mcp", headers={"Host": "127.0.0.1"})
        response = connection.getresponse()
        self.assertEqual(response.status, 401)
        connection.close()

    def test_protected_resource_metadata_and_dns_rebinding_guards(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("GET", "/.well-known/oauth-protected-resource/mcp",
            headers={"Host": "127.0.0.1"})
        response = connection.getresponse()
        metadata = json.loads(response.read())
        self.assertEqual(response.status, 200)
        self.assertEqual(metadata["resource"], "https://mcp.example.test/mcp")
        self.assertEqual(metadata["authorization_servers"], ["https://identity.example.test/"])
        connection.close()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("GET", "/mcp", headers={"Host": "attacker.example"})
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        connection.close()

    def test_untrusted_tool_arguments_cannot_select_provider_identity(self):
        identity = self.tokens.resolve(TOKEN)
        with self.assertRaises(ValueError):
            self.adapter.call_tool(identity, "reasoning_exchange_list_requests",
                                   {"provider_id": "attacker:provider"})
        with self.assertRaises(MCPConfigurationError):
            bad = ProviderTokenMap.from_document({
                "schema_version": ProviderTokenMap.SCHEMA,
                "tokens": [{"token_sha256": hashlib.sha256(TOKEN.encode()).hexdigest(),
                    "provider_id": PROVIDER, "principal_id": "other:principal",
                    "scopes": ["reasoning:exchange"],
                    "expires_at": "2099-01-01T00:00:00Z"}]})
            ExternalReasoningMCPAdapter(_FixtureExchange(), bad)


if __name__ == "__main__":
    unittest.main()
