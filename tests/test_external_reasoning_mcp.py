# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_external_reasoning_mcp.py
# Component: EXTERNAL-REASONING-MCP-TRANSPORT
# Revision: 1.0.8
# Purpose: Exercise MCP Streamable HTTP and OAuth provider identity mapping independently
# Execution Model: Local ephemeral HTTP server; stdlib client independent of adapter dispatch
# Observability: HTTP status, protocol negotiation, tool names and sanitized denials
# Dependencies: Python standard library; PyJWT; cryptography; external_reasoning_mcp module
# Authority: Synthetic tokens and exchange fixture; no production database or route
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Initial protocol/client tests
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Include finite provider-token expiry in independent client fixtures
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Allocate an ephemeral test port without weakening runtime port validation
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Verify 2025 version-header fallback and authentication on disabled GET stream
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Reject Streamable HTTP POST without both required Accept media types
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Verify quality-value denial and consume response on host rejection
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-MCP | Verify bounded exact-proposal exposure and digest-bound provider response submission
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Independent HTTP-client tests for the stateless MCP Streamable HTTP surface."""

import hashlib
import http.client
import json
import socket
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from riverview_core.resident_execution.external_reasoning import DurableExternalReasoningExchange
from riverview_core.resident_execution.external_reasoning_mcp import (
    ExternalReasoningMCPAdapter, MCPAuthenticationError, MCPConfigurationError,
    OAuthProviderTokenMap, ProviderTokenMap,
    create_server,
)


TOKEN = "synthetic-provider-token-for-independent-mcp-test-0001"
PROVIDER = "test:provider"
PRINCIPAL = "test:provider"


class _FixtureExchange(DurableExternalReasoningExchange):
    def __init__(self):
        self.router = SimpleNamespace(providers={PROVIDER: SimpleNamespace(provider_id=PROVIDER,
            exchange_principal_id=PRINCIPAL)})

    def eligible_requests(self, provider_id, *, principal_id, limit):
        return []


class _ReviewFixtureExchange(_FixtureExchange):
    def __init__(self, subject):
        super().__init__()
        self.subject = subject
        self.submitted = []
        self.request_id = "00000000-0000-4000-8000-000000000101"
        self.correlation_id = "00000000-0000-4000-8000-000000000102"

    def eligible_requests(self, provider_id, *, principal_id, limit):
        return [{"request_id": self.request_id, "correlation_id": self.correlation_id,
            "objective_id": "objective-1", "conversation_id": self.correlation_id,
            "message_sequence": 1,
            "proposal_id": self.subject["subject_id"] if self.subject else None,
            "proposal_revision": self.subject["revision"] if self.subject else None,
            "request_schema": "rv.external-reasoning.request.v1",
            "classification": "institutional", "context_sha256": "a" * 64,
            "deadline_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "delivery_state": "awaiting_external_claim", "request_payload": {"reason": "review"},
            **({"review_subject": self.subject} if self.subject else {})}]

    def provider_status(self, request_id, correlation_id, *, provider_id, principal_id):
        if (request_id != self.request_id or correlation_id != self.correlation_id
                or provider_id != PROVIDER or principal_id != PRINCIPAL):
            raise ValueError("exchange_identity_mismatch")
        status = {"request_id": request_id, "correlation_id": correlation_id,
            "provider_id": provider_id, "classification": "institutional",
            "delivery_state": "awaiting_response"}
        if self.subject:
            status["review_subject_sha256"] = self.subject["sha256"]
        return status

    def submit_response(self, request_id, correlation_id, **kwargs):
        self.submitted.append((request_id, correlation_id, kwargs))
        return "b" * 64


def _review_subject():
    digest_body = {"subject_id": "proposal-1", "revision": 2,
        "proposal": {"summary": "Harmless synthetic review", "steps": ["inspect fixture"]}}
    digest = hashlib.sha256(json.dumps(digest_body, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {"schema_version": "rv.grace.proposal-review-subject.v1",
        **digest_body, "sha256": digest}


class _JWKFixture:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        jwt.get_unverified_header(token)
        return SimpleNamespace(key=self.key)


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
                "clientInfo": {"name": "independent-stdlib-client", "version": "1.0"}}},
            token=None)
        self.assertEqual(status, 200)
        self.assertEqual(body["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(body["result"]["serverInfo"]["name"],
                         "Riverview External Reasoning Exchange")
        status, _, body = self._request("notifications/initialized", {
            "jsonrpc": "2.0", "method": "notifications/initialized"},
            protocol="2025-11-25", token=None)
        self.assertEqual(status, 202)
        status, _, body = self._request("tools/list", {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            protocol="2025-11-25", token=None)
        self.assertEqual(status, 200)
        names = [tool["name"] for tool in body["result"]["tools"]]
        self.assertEqual(names, ["reasoning_exchange_list_requests",
            "reasoning_exchange_claim_request", "reasoning_exchange_submit_response",
            "reasoning_exchange_status"])
        submit_schema = next(tool["inputSchema"] for tool in body["result"]["tools"]
            if tool["name"] == "reasoning_exchange_submit_response")
        self.assertEqual(submit_schema["properties"]["review_subject_sha256"]["pattern"],
                         "^[0-9a-f]{64}$")
        self.assertNotIn("reasoning_exchange_consume", names)
        self.assertTrue(all(tool["securitySchemes"] == [{"type": "oauth2",
            "scopes": ["reasoning:exchange", "reasoning:exchange:confidential"]}]
            for tool in body["result"]["tools"]))
        status, _, body = self._request("tools/list", {
            "jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}},
            protocol=None)
        self.assertEqual(status, 200)
        self.assertEqual(body["id"], 4)
        status, _, body = self._request("tools/call", {
            "jsonrpc": "2.0", "id": "unauth-call", "method": "tools/call",
            "params": {"name": "reasoning_exchange_list_requests", "arguments": {}}},
            token=None, protocol="2025-11-25")
        self.assertEqual(status, 401)
        result = body["result"]
        self.assertTrue(result["isError"])
        challenge = result["_meta"]["mcp/www_authenticate"][0]
        self.assertIn("resource_metadata=", challenge)
        self.assertIn('error="invalid_token"', challenge)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("GET", "/mcp", headers={"Host": "127.0.0.1"})
        response = connection.getresponse()
        self.assertEqual(response.status, 405)
        response.read()
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
        response.read()
        connection.close()

    def test_post_requires_json_and_sse_accept_types(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        body = json.dumps({"jsonrpc": "2.0", "id": 9, "method": "ping"})
        connection.request("POST", "/mcp", body=body, headers={
            "Host": "127.0.0.1", "Authorization": "Bearer " + TOKEN,
            "Content-Type": "application/json", "Accept": "application/json"})
        response = connection.getresponse()
        self.assertEqual(response.status, 406)
        self.assertEqual(json.loads(response.read())["error"], "not_acceptable")
        connection.close()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("POST", "/mcp", body=body, headers={
            "Host": "127.0.0.1", "Authorization": "Bearer " + TOKEN,
            "Content-Type": "application/json",
            "Accept": "application/json;q=0, text/event-stream"})
        response = connection.getresponse()
        self.assertEqual(response.status, 406)
        self.assertEqual(json.loads(response.read())["error"], "not_acceptable")
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

    def test_exact_review_subject_is_provider_visible_and_digest_bound(self):
        exchange = _ReviewFixtureExchange(_review_subject())
        adapter = ExternalReasoningMCPAdapter(exchange, self.tokens)
        identity = self.tokens.resolve(TOKEN)
        listed = adapter.call_tool(identity, "reasoning_exchange_list_requests", {})
        request = listed["requests"][0]
        self.assertEqual(request["review_subject"], exchange.subject)
        self.assertEqual(request["review_subject_sha256"], exchange.subject["sha256"])

        base_arguments = {"request_id": exchange.request_id,
            "correlation_id": exchange.correlation_id, "claim_token": "c" * 36,
            "fence": 1, "idempotency_key": "review-response-1", "response": {"advisory": "ok"}}
        with self.assertRaisesRegex(ValueError, "review_subject_digest_mismatch"):
            adapter.call_tool(identity, "reasoning_exchange_submit_response", base_arguments)
        wrong = {**base_arguments, "review_subject_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "review_subject_digest_mismatch"):
            adapter.call_tool(identity, "reasoning_exchange_submit_response", wrong)
        correct = {**base_arguments,
            "review_subject_sha256": exchange.subject["sha256"]}
        result = adapter.call_tool(identity, "reasoning_exchange_submit_response", correct)
        self.assertEqual(result, {"response_sha256": "b" * 64, "state": "response_received"})
        self.assertEqual(len(exchange.submitted), 1)
        self.assertEqual(exchange.submitted[0][2]["review_subject_sha256"],
                         exchange.subject["sha256"])

        wrong_correlation = {**correct,
            "correlation_id": "00000000-0000-4000-8000-000000000199"}
        with self.assertRaisesRegex(ValueError, "exchange_identity_mismatch"):
            adapter.call_tool(identity, "reasoning_exchange_submit_response", wrong_correlation)
        self.assertEqual(len(exchange.submitted), 1)

    def test_legacy_advisory_submission_does_not_require_subject_digest(self):
        exchange = _ReviewFixtureExchange(None)
        adapter = ExternalReasoningMCPAdapter(exchange, self.tokens)
        identity = self.tokens.resolve(TOKEN)
        arguments = {"request_id": exchange.request_id,
            "correlation_id": exchange.correlation_id, "claim_token": "c" * 36,
            "fence": 1, "idempotency_key": "legacy-response-1", "response": {"advisory": "ok"}}
        result = adapter.call_tool(identity, "reasoning_exchange_submit_response", arguments)
        self.assertEqual(result["state"], "response_received")
        self.assertNotIn("review_subject_sha256", exchange.submitted[0][2])

    def test_review_subject_digest_size_and_shape_are_checked(self):
        subject = _review_subject()
        self.assertEqual(ExternalReasoningMCPAdapter._review_subject({}, {"review_subject": subject}),
                         subject)
        with self.assertRaisesRegex(ValueError, "review_subject_digest_or_size_invalid"):
            ExternalReasoningMCPAdapter._review_subject({}, {"review_subject": {
                **subject, "sha256": "0" * 64}})
        with self.assertRaisesRegex(ValueError, "review_subject_invalid"):
            ExternalReasoningMCPAdapter._review_subject({}, {"review_subject": {
                **subject, "revision": True}})
        with self.assertRaisesRegex(ValueError, "review_subject_conflict"):
            ExternalReasoningMCPAdapter._review_subject(
                {"review_subject": {**subject, "revision": 3}},
                {"review_subject": subject})


class OAuthProviderTokenMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.issuer = "https://identity.example.test/"
        cls.audience = "https://mcp.example.test/mcp"
        cls.subject = "steward-subject-01"
        cls.client_id = "https://chatgpt.com/oauth/client.json"
        cls.metadata = {"issuer": cls.issuer,
            "authorization_endpoint": cls.issuer + "authorize",
            "token_endpoint": cls.issuer + "token",
            "jwks_uri": cls.issuer + "jwks",
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "client_id_metadata_document_supported": True}
        cls.mapping = {"schema_version": OAuthProviderTokenMap.SCHEMA,
            "providers": [{"provider_id": "test:oauth-provider",
                "principal_id": "test:oauth-principal", "subjects": [cls.subject],
                "client_ids": [cls.client_id], "scopes": ["reasoning:exchange"]}]}

    def setUp(self):
        self.auth = OAuthProviderTokenMap.from_document(self.mapping,
            issuer=self.issuer, audience=self.audience, metadata=self.metadata,
            jwks_client=_JWKFixture(self.private_key.public_key()))

    def token(self, **overrides):
        claims = {"iss": self.issuer, "aud": self.audience,
            "sub": self.subject, "client_id": self.client_id,
            "scope": "reasoning:exchange", "iat": int(time.time()),
            "exp": int(time.time()) + 120}
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256",
                          headers={"kid": "fixture-key"})

    def test_valid_signed_token_maps_to_fixed_advisory_provider(self):
        principal = self.auth.resolve(self.token())
        self.assertEqual(principal.provider_id, "test:oauth-provider")
        self.assertEqual(principal.principal_id, "test:oauth-principal")
        self.assertEqual(principal.scopes, frozenset({"reasoning:exchange"}))
        self.assertEqual(len(principal.token_sha256), 64)

    def test_wrong_issuer_audience_subject_client_scope_or_expiry_rejected(self):
        for claims in (
                {"iss": "https://attacker.example/"},
                {"aud": "https://other.example/mcp"},
                {"aud": [self.audience, "https://other.example/mcp"]},
                {"sub": "unmapped-subject"},
                {"client_id": "unregistered-client"},
                {"exp": int(time.time()) - 1}):
            with self.subTest(claims=sorted(claims)):
                with self.assertRaises(MCPAuthenticationError):
                    self.auth.resolve(self.token(**claims))
        principal = self.auth.resolve(self.token(scope="profile"))
        self.assertNotIn("reasoning:exchange", principal.scopes)

    def test_bad_signature_and_missing_pkce_provider_metadata_fail_closed(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        auth = OAuthProviderTokenMap.from_document(self.mapping,
            issuer=self.issuer, audience=self.audience, metadata=self.metadata,
            jwks_client=_JWKFixture(other.public_key()))
        with self.assertRaises(MCPAuthenticationError):
            auth.resolve(self.token())
        metadata = dict(self.metadata)
        metadata["code_challenge_methods_supported"] = ["plain"]
        with self.assertRaises(MCPConfigurationError):
            OAuthProviderTokenMap.from_document(self.mapping,
                issuer=self.issuer, audience=self.audience, metadata=metadata,
                jwks_client=_JWKFixture(self.private_key.public_key()))

    def test_non_https_oauth_endpoint_and_incompatible_client_auth_method_rejected(self):
        for metadata in (
                {**self.metadata, "authorization_endpoint": "http://identity.example.test/authorize"},
                {**self.metadata, "token_endpoint_auth_methods_supported": ["client_secret_basic"]}):
            with self.subTest(metadata=metadata):
                with self.assertRaises(MCPConfigurationError):
                    OAuthProviderTokenMap.from_document(self.mapping,
                        issuer=self.issuer, audience=self.audience, metadata=metadata,
                        jwks_client=_JWKFixture(self.private_key.public_key()))

    def test_valid_oauth_identity_passes_through_mcp_tool_auth_boundary(self):
        exchange = _FixtureExchange()
        exchange.router.providers = {provider_id: SimpleNamespace(provider_id=provider_id,
            exchange_principal_id=principal_id)
            for provider_id, principal_id in self.auth.registrations.items()}
        adapter = ExternalReasoningMCPAdapter(exchange, self.auth)
        principal = self.auth.resolve(self.token())
        result = adapter.handle_rpc(principal, {
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "reasoning_exchange_list_requests", "arguments": {}}},
            "2025-11-25")
        self.assertEqual(result["result"]["content"][0]["text"],
                         '{"count":0,"requests":[]}')

    def test_real_http_handler_accepts_signed_oauth_jwt_and_rejects_missing_token(self):
        exchange = _FixtureExchange()
        exchange.router.providers = {provider_id: SimpleNamespace(provider_id=provider_id,
            exchange_principal_id=principal_id)
            for provider_id, principal_id in self.auth.registrations.items()}
        adapter = ExternalReasoningMCPAdapter(exchange, self.auth)
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        server = create_server(adapter, host="127.0.0.1", port=port,
            resource_url=self.audience, authorization_server_url=self.issuer)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            message = {"jsonrpc": "2.0", "id": "oauth-http", "method": "tools/call",
                "params": {"name": "reasoning_exchange_list_requests", "arguments": {}}}
            cases = ((None, 401), (self.token(), 200),
                     (self.token(scope="profile"), 403))
            for token, expected_status in cases:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
                headers = {"Host": "127.0.0.1",
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": "2025-11-25"}
                if token is not None:
                    headers["Authorization"] = "Bearer " + token
                connection.request("POST", "/mcp", body=json.dumps(message), headers=headers)
                response = connection.getresponse()
                payload = json.loads(response.read())
                connection.close()
                self.assertEqual(response.status, expected_status)
                if expected_status == 200:
                    self.assertFalse(payload["result"]["isError"])
                    self.assertEqual(json.loads(payload["result"]["content"][0]["text"]),
                                     {"count": 0, "requests": []})
                else:
                    self.assertTrue(payload["result"]["isError"])
                    self.assertIn("mcp/www_authenticate", payload["result"]["_meta"])
                    self.assertIn("WWW-Authenticate", response.headers)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
