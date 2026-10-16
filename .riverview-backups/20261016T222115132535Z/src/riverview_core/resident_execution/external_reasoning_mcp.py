# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/external_reasoning_mcp.py
# Component: EXTERNAL-REASONING-MCP-TRANSPORT
# Revision: 1.0.3
# Purpose: Expose the durable advisory exchange through authenticated MCP Streamable HTTP
# Execution Model: Request-driven, sessionless HTTP JSON-RPC adapter
# Observability: Sanitized request outcomes; authoritative exchange state remains PostgreSQL
# Dependencies: Python standard library; DurableExternalReasoningExchange
# Authority: Provider-scoped advisory exchange only; no Grace consumption or execution tools
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Initial provider-scoped MCP transport
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Require expiring credential mappings and reject side-effecting JSON-RPC notifications
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Accept protocol header fallback and authenticate every MCP endpoint method
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Bound request sockets and strictly validate configured Host/Origin allowlists
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# Tests: tests/test_external_reasoning_mcp.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Bounded MCP Streamable HTTP adapter for Riverview's durable advisory exchange.

The transport is stateless; request, delivery, claim and response state remain in
PostgreSQL. Bearer credentials are represented in a protected credential file by
SHA-256 digest and map to fixed provider principals. No tool argument can choose
or override an authenticated provider identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import threading
from typing import Any, Mapping
from urllib.parse import urlsplit

from .external_reasoning import (
    DurableExternalReasoningExchange, ExchangeConflict, ExchangeError,
    ExchangeExpired, ExchangeNotFound, ExchangeUnauthorized,
)


MCP_PATH = "/mcp"
PROTECTED_RESOURCE_PATH = "/.well-known/oauth-protected-resource/mcp"
SUPPORTED_PROTOCOL_VERSIONS = frozenset({"2025-03-26", "2025-06-18", "2025-11-25"})
MAX_HTTP_BODY_BYTES = 64 * 1024
MAX_CONTEXT_RETURN_BYTES = 32 * 1024
MAX_TOKENS = 16
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HOSTNAME = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\.?$")
_ALLOWED_SCOPES = {"reasoning:exchange", "reasoning:exchange:confidential"}
_ALLOWED_CLASSIFICATIONS = {"institutional", "confidential"}


class MCPConfigurationError(ValueError):
    """The protected provider identity or transport configuration is invalid."""


class MCPAuthenticationError(ValueError):
    """A bearer credential did not map to one provider principal."""


@dataclass(frozen=True)
class ProviderPrincipal:
    provider_id: str
    principal_id: str
    scopes: frozenset[str]
    token_sha256: str
    expires_at: datetime

    def permits(self, classification: str) -> bool:
        if classification == "institutional":
            return "reasoning:exchange" in self.scopes
        if classification == "confidential":
            return "reasoning:exchange:confidential" in self.scopes
        return False


class ProviderTokenMap:
    """Resolve opaque high-entropy bearer tokens to fixed provider identities."""

    SCHEMA = "rv.external-reasoning.provider-auth.v1"

    def __init__(self, entries):
        if not isinstance(entries, tuple) or not 1 <= len(entries) <= MAX_TOKENS:
            raise MCPConfigurationError("provider_token_map_invalid")
        digests = [entry.token_sha256 for entry in entries]
        if len(set(digests)) != len(digests):
            raise MCPConfigurationError("provider_token_map_duplicate")
        self._entries = entries

    @classmethod
    def from_document(cls, document: Any):
        if (not isinstance(document, dict) or set(document) != {"schema_version", "tokens"}
                or document.get("schema_version") != cls.SCHEMA
                or not isinstance(document.get("tokens"), list)):
            raise MCPConfigurationError("provider_token_map_invalid")
        entries = []
        for item in document["tokens"]:
            if not isinstance(item, dict) or set(item) != {
                    "token_sha256", "provider_id", "principal_id", "scopes", "expires_at"}:
                raise MCPConfigurationError("provider_token_entry_invalid")
            digest, provider_id, principal_id, scopes = (
                item.get("token_sha256"), item.get("provider_id"),
                item.get("principal_id"), item.get("scopes"))
            expires_at = item.get("expires_at")
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expiry.tzinfo is None:
                    raise ValueError
                expiry = expiry.astimezone(timezone.utc)
            except (AttributeError, TypeError, ValueError):
                raise MCPConfigurationError("provider_token_entry_invalid") from None
            if (not isinstance(digest, str) or not _SHA256.fullmatch(digest)
                    or not isinstance(provider_id, str) or not _IDENTITY.fullmatch(provider_id)
                    or not isinstance(principal_id, str) or not _IDENTITY.fullmatch(principal_id)
                    or not isinstance(scopes, list) or not scopes
                    or any(not isinstance(scope, str) or scope not in _ALLOWED_SCOPES
                           for scope in scopes)
                    or len(set(scopes)) != len(scopes)
                    or "reasoning:exchange" not in scopes):
                raise MCPConfigurationError("provider_token_entry_invalid")
            entries.append(ProviderPrincipal(provider_id, principal_id,
                frozenset(scopes), digest, expiry))
        return cls(tuple(entries))

    @classmethod
    def load(cls, path: str | os.PathLike[str]):
        """Load a systemd credential; reject symlinks and group/world-readable files."""
        candidate = Path(path)
        try:
            if candidate.is_symlink():
                raise MCPConfigurationError("provider_token_credential_invalid")
            info = candidate.stat()
            if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) not in {0o400, 0o440, 0o600}
                    or info.st_uid not in {0, os.geteuid()} or info.st_size > 16 * 1024):
                raise MCPConfigurationError("provider_token_credential_invalid")
            raw = candidate.read_bytes()
            document = json.loads(raw.decode("utf-8"))
        except MCPConfigurationError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise MCPConfigurationError("provider_token_credential_invalid") from None
        return cls.from_document(document)

    def resolve(self, token: str) -> ProviderPrincipal:
        if not isinstance(token, str) or not 32 <= len(token) <= 4096 or any(c.isspace() for c in token):
            raise MCPAuthenticationError("invalid_token")
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        matched = None
        # Compare every configured digest to avoid disclosing which provider entry matched.
        for entry in self._entries:
            if hmac.compare_digest(digest, entry.token_sha256):
                matched = entry
        if matched is None or matched.expires_at <= datetime.now(timezone.utc):
            raise MCPAuthenticationError("invalid_token")
        return matched

    @property
    def registrations(self):
        """Return one immutable provider/principal registration per provider."""
        registrations = {}
        for entry in self._entries:
            prior = registrations.setdefault(entry.provider_id, entry.principal_id)
            if prior != entry.principal_id:
                raise MCPConfigurationError("provider_principal_mapping_conflict")
        return dict(registrations)


class ExternalProviderRegistration:
    """Identity-only marker; this MCP surface cannot invoke external inference."""

    def __init__(self, provider_id: str, principal_id: str):
        if (not isinstance(provider_id, str) or not _IDENTITY.fullmatch(provider_id)
                or not isinstance(principal_id, str) or not _IDENTITY.fullmatch(principal_id)):
            raise MCPConfigurationError("provider_registration_invalid")
        self.provider_id = provider_id
        self.exchange_principal_id = principal_id

    def propose(self, _request):
        raise RuntimeError("external_provider_is_mcp_only")


def exchange_runtime_readiness(ledger):
    """Read-only startup check for migration presence and the required narrow ACL."""
    schema = ledger.schema
    exchange = f"{schema}.external_reasoning_exchanges"
    events = f"{schema}.external_reasoning_exchange_events"
    sequence = f"{schema}.external_reasoning_exchange_events_sequence_seq"
    with ledger.db.cursor() as cursor:
        cursor.execute("""SELECT to_regclass(%s) AS exchanges,
            to_regclass(%s) AS events,
            has_table_privilege(current_user,%s,'SELECT') AS exchange_select,
            has_table_privilege(current_user,%s,'INSERT') AS exchange_insert,
            has_column_privilege(current_user,%s,'delivery_state','UPDATE') AS delivery_update,
            has_column_privilege(current_user,%s,'response_payload','UPDATE') AS response_update,
            has_table_privilege(current_user,%s,'SELECT') AS event_select,
            has_table_privilege(current_user,%s,'INSERT') AS event_insert,
            has_sequence_privilege(current_user,%s,'USAGE') AS event_sequence_usage""",
            (exchange, events, exchange, exchange, exchange, exchange,
             events, events, sequence))
        row = cursor.fetchone()
    if not row or not row["exchanges"] or not row["events"]:
        return {"status": "not_initialized", "error_code": "exchange_migration_missing"}
    required = ("exchange_select", "exchange_insert", "delivery_update", "response_update",
                "event_select", "event_insert", "event_sequence_usage")
    if not all(row[name] for name in required):
        return {"status": "blocked", "error_code": "exchange_runtime_privilege_missing"}
    return {"status": "healthy", "error_code": None}


class ExternalReasoningMCPAdapter:
    """Expose only provider-scoped list, claim, submit and body-free status tools."""

    COMPONENT_ID = "external-reasoning-mcp"
    VERSION = "1.0.0"

    def __init__(self, exchange: DurableExternalReasoningExchange,
                 token_map: ProviderTokenMap):
        if not isinstance(exchange, DurableExternalReasoningExchange):
            raise TypeError("DurableExternalReasoningExchange is required")
        if not isinstance(token_map, ProviderTokenMap):
            raise TypeError("ProviderTokenMap is required")
        for provider_id, principal_id in token_map.registrations.items():
            provider = exchange.router.providers.get(provider_id)
            if (provider is None or getattr(provider, "provider_id", None) != provider_id
                    or getattr(provider, "exchange_principal_id", provider_id) != principal_id):
                raise MCPConfigurationError("provider_not_registered")
        self.exchange = exchange
        self.token_map = token_map

    @staticmethod
    def tools() -> list[dict[str, Any]]:
        return [
            {"name": "reasoning_exchange_list_requests",
             "description": "List bounded advisory requests assigned to this authenticated provider. Request context is visible only to its selected provider.",
             "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 10}}, "additionalProperties": False}},
            {"name": "reasoning_exchange_claim_request",
             "description": "Claim one assigned request with a finite lease and fencing identity.",
             "inputSchema": {"type": "object", "required": ["request_id", "correlation_id"], "properties": {"request_id": {"type": "string", "format": "uuid"}, "correlation_id": {"type": "string", "format": "uuid"}, "lease_seconds": {"type": "integer", "minimum": 1, "maximum": 300}}, "additionalProperties": False}},
            {"name": "reasoning_exchange_submit_response",
             "description": "Submit one bounded structured advisory for the active correlated claim. Advice grants no approval or execution authority.",
             "inputSchema": {"type": "object", "required": ["request_id", "correlation_id", "claim_token", "fence", "idempotency_key", "response"], "properties": {"request_id": {"type": "string", "format": "uuid"}, "correlation_id": {"type": "string", "format": "uuid"}, "claim_token": {"type": "string", "minLength": 36, "maxLength": 36}, "fence": {"type": "integer", "minimum": 1}, "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 240}, "response": {"type": "object"}}, "additionalProperties": False}},
            {"name": "reasoning_exchange_status",
             "description": "Read state, sanitized diagnostics, provenance and digests for this provider's exchange; response contents are never returned.",
             "inputSchema": {"type": "object", "required": ["request_id", "correlation_id"], "properties": {"request_id": {"type": "string", "format": "uuid"}, "correlation_id": {"type": "string", "format": "uuid"}}, "additionalProperties": False}},
        ]

    @staticmethod
    def _require_scope(principal: ProviderPrincipal, classification="institutional"):
        if not principal.permits(classification):
            raise ExchangeUnauthorized("provider_scope_denied")

    @staticmethod
    def _json(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)

    def _owned_status(self, principal, request_id, correlation_id):
        status = self.exchange.provider_status(request_id, correlation_id,
            provider_id=principal.provider_id, principal_id=principal.principal_id)
        self._require_scope(principal, status.get("classification", "institutional"))
        return status

    def call_tool(self, principal: ProviderPrincipal, name: str,
                  arguments: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, Mapping):
            raise ValueError("tool_arguments_invalid")
        if name == "reasoning_exchange_list_requests":
            if set(arguments) - {"limit"}:
                raise ValueError("tool_arguments_invalid")
            limit = arguments.get("limit", 10)
            if type(limit) is not int or not 1 <= limit <= 10:
                raise ValueError("tool_arguments_invalid")
            rows = self.exchange.eligible_requests(principal.provider_id,
                principal_id=principal.principal_id, limit=limit)
            result = []
            for row in rows:
                classification = row.get("classification")
                if not principal.permits(classification):
                    continue
                if row.get("delivery_state") == "awaiting_delivery":
                    owner_id = "mcp:" + principal.principal_id
                    lease = self.exchange.begin_delivery(row["request_id"],
                        principal.provider_id, owner_id=owner_id, lease_seconds=30)
                    if lease is None:
                        continue
                    self.exchange.mark_delivered(row["request_id"], row["correlation_id"],
                        principal.provider_id, owner_id=owner_id,
                        delivery_token=lease.claim_token, fence=lease.fence)
                payload = row["request_payload"]
                encoded = self._json(payload)
                if len(encoded.encode("utf-8")) > MAX_CONTEXT_RETURN_BYTES:
                    continue
                result.append({"request_id": str(row["request_id"]),
                    "correlation_id": str(row["correlation_id"]),
                    "objective_id": row["objective_id"],
                    "conversation_id": str(row["conversation_id"]),
                    "message_sequence": row["message_sequence"],
                    "proposal_id": row["proposal_id"],
                    "proposal_revision": row["proposal_revision"],
                    "schema_version": row["request_schema"],
                    "classification": classification,
                    "context_sha256": row["context_sha256"],
                    "deadline_at": row["deadline_at"].isoformat(),
                    "delivery_state": ("awaiting_external_claim"
                        if row.get("delivery_state") == "awaiting_delivery"
                        else row["delivery_state"]),
                    "request": payload})
            return {"requests": result, "count": len(result)}
        if name == "reasoning_exchange_claim_request":
            self._exact_keys(arguments, {"request_id", "correlation_id"},
                             {"lease_seconds"})
            lease_seconds = arguments.get("lease_seconds", 120)
            if type(lease_seconds) is not int or not 1 <= lease_seconds <= 300:
                raise ValueError("tool_arguments_invalid")
            status = self._owned_status(principal, arguments["request_id"],
                                        arguments["correlation_id"])
            claim = self.exchange.claim(arguments["request_id"], arguments["correlation_id"],
                provider_id=principal.provider_id, principal_id=principal.principal_id,
                lease_seconds=lease_seconds)
            if claim is None:
                return {"state": status["delivery_state"], "claimed": False}
            return {"request_id": claim.request_id, "correlation_id": claim.correlation_id,
                "claim_token": claim.claim_token, "fence": claim.fence,
                "lease_until": claim.lease_until.isoformat(), "duplicate": claim.duplicate}
        if name == "reasoning_exchange_submit_response":
            self._exact_keys(arguments,
                {"request_id", "correlation_id", "claim_token", "fence", "idempotency_key", "response"})
            if type(arguments["fence"]) is not int or arguments["fence"] < 1:
                raise ValueError("tool_arguments_invalid")
            self._owned_status(principal, arguments["request_id"], arguments["correlation_id"])
            digest = self.exchange.submit_response(arguments["request_id"],
                arguments["correlation_id"], provider_id=principal.provider_id,
                principal_id=principal.principal_id, claim_token=arguments["claim_token"],
                fence=arguments["fence"], idempotency_key=arguments["idempotency_key"],
                response=arguments["response"])
            return {"response_sha256": digest, "state": "response_received"}
        if name == "reasoning_exchange_status":
            self._exact_keys(arguments, {"request_id", "correlation_id"})
            return self._owned_status(principal, arguments["request_id"],
                                      arguments["correlation_id"])
        raise KeyError("tool_not_found")

    @staticmethod
    def _exact_keys(arguments, required, optional=frozenset()):
        keys = set(arguments)
        if not required <= keys or keys - required - set(optional):
            raise ValueError("tool_arguments_invalid")

    def handle_rpc(self, principal: ProviderPrincipal, message: Any,
                   protocol_version: str | None = None):
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return self._rpc_error(message.get("id") if isinstance(message, dict) else None,
                                   -32600, "Invalid Request")
        method = message.get("method")
        request_id = message.get("id")
        is_notification = "id" not in message
        if not isinstance(method, str) or (not is_notification and
                (isinstance(request_id, bool) or not isinstance(request_id, (str, int)))):
            return self._rpc_error(request_id, -32600, "Invalid Request")
        if is_notification:
            # Never execute a tool or other request method from a JSON-RPC
            # notification; only the two protocol notifications are accepted.
            return None
        if method == "initialize":
            params = message.get("params")
            client_info = params.get("clientInfo") if isinstance(params, dict) else None
            capabilities = params.get("capabilities") if isinstance(params, dict) else None
            if (not isinstance(params, dict) or set(params) - {"protocolVersion", "capabilities", "clientInfo", "_meta"}
                    or not isinstance(params.get("protocolVersion"), str)
                    or not isinstance(capabilities, dict)
                    or not isinstance(client_info, dict)
                    or not isinstance(client_info.get("name"), str)
                    or not isinstance(client_info.get("version"), str)):
                return self._rpc_error(request_id, -32602, "Invalid params")
            requested = params["protocolVersion"]
            if requested not in SUPPORTED_PROTOCOL_VERSIONS:
                return self._rpc_error(request_id, -32602, "Unsupported protocol version")
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "protocolVersion": requested,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "Riverview External Reasoning Exchange", "version": self.VERSION},
                "instructions": "Advisory reasoning only. Responses do not authorize or execute institutional work."}}
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
            return self._rpc_error(request_id, -32600, "Protocol version required")
        if method == "tools/list":
            params = message.get("params", {})
            if (not isinstance(params, dict) or set(params) - {"cursor"}
                    or params.get("cursor") not in (None, "")):
                return self._rpc_error(request_id, -32602, "Invalid params")
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"tools": self.tools()}}
        if method == "tools/call":
            params = message.get("params")
            if (not isinstance(params, dict) or set(params) - {"name", "arguments", "_meta"}
                    or not isinstance(params.get("name"), str)
                    or not isinstance(params.get("arguments", {}), dict)):
                return self._rpc_error(request_id, -32602, "Invalid params")
            try:
                result = self.call_tool(principal, params["name"], params.get("arguments", {}))
                content = [{"type": "text", "text": self._json(result)}]
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": content, "isError": False}}
            except KeyError:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "tool_not_found"}], "isError": True}}
            except ExchangeUnauthorized:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "provider_scope_denied"}], "isError": True}}
            except ExchangeNotFound:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "exchange_not_found"}], "isError": True}}
            except ExchangeExpired:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "exchange_expired"}], "isError": True}}
            except ExchangeConflict:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "exchange_conflict"}], "isError": True}}
            except (ValueError, TypeError):
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "tool_arguments_invalid"}], "isError": True}}
            except ExchangeError:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "exchange_unavailable"}], "isError": True}}
        if is_notification:
            return None
        return self._rpc_error(request_id, -32601, "Method not found")

    @staticmethod
    def _rpc_error(request_id, code, message):
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": code, "message": message}}


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Bound concurrent request threads and queue depth for the local adapter."""
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address, handler, *, max_handlers=16):
        self._handler_slots = threading.BoundedSemaphore(max_handlers)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self._handler_slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._handler_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._handler_slots.release()


def make_handler(adapter: ExternalReasoningMCPAdapter, *, resource_url: str,
                 authorization_server_url: str, allowed_hosts=(), allowed_origins=()):
    """Create a stateless Streamable HTTP handler with per-request bearer auth."""
    resource, issuer = _https_url(resource_url), _https_url(authorization_server_url)
    hosts = frozenset(_configured_host(host) for host in
                      (allowed_hosts or ("127.0.0.1", "localhost")))
    origins = frozenset(allowed_origins)
    for origin in origins:
        parsed_origin = urlsplit(origin) if isinstance(origin, str) else None
        if (parsed_origin is None or parsed_origin.scheme not in {"https", "http"}
                or not parsed_origin.netloc or parsed_origin.path not in {"", "/"}
                or parsed_origin.query or parsed_origin.fragment
                or parsed_origin.username or parsed_origin.password):
            raise MCPConfigurationError("origin_allowlist_invalid")
    protected_resource = {"resource": resource,
        "authorization_servers": [issuer],
        "scopes_supported": sorted(_ALLOWED_SCOPES),
        "bearer_methods_supported": ["header"]}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "RiverviewMCP/1.0"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, _format, *_args):
            # BaseHTTPRequestHandler's default log includes client-supplied paths.
            return

        def _send(self, status, body=None, headers=None):
            payload = b"" if body is None else json.dumps(body, ensure_ascii=False,
                sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if body is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)

        def _host_allowed(self):
            raw_host = self.headers.get("Host", "")
            try:
                host = _canonical_host(urlsplit("//" + raw_host).hostname or "")
            except ValueError:
                host = ""
            if host not in hosts:
                self._send(403, {"error": "host_not_allowed"})
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in origins:
                self._send(403, {"error": "origin_not_allowed"})
                return False
            return True

        def do_GET(self):
            if not self._host_allowed():
                return
            if self.path == PROTECTED_RESOURCE_PATH:
                self._send(200, protected_resource)
                return
            if self.path == "/healthz":
                try:
                    ready = exchange_runtime_readiness(adapter.exchange.ledger)
                    healthy = ready["status"] == "healthy"
                    self._send(200 if healthy else 503, {"component_id": adapter.COMPONENT_ID,
                        "component_version": adapter.VERSION, **ready})
                except Exception:
                    self._send(503, {"component_id": adapter.COMPONENT_ID,
                        "component_version": adapter.VERSION, "status": "unavailable"})
                return
            if self.path == MCP_PATH:
                token = self._provider_token()
                if token is None:
                    self._unauthorized(resource)
                    return
                self._send(405, {"error": "method_not_allowed"}, {"Allow": "POST"})
                return
            self._send(404, {"error": "not_found"})

        def do_DELETE(self):
            if not self._host_allowed():
                return
            if self.path != MCP_PATH:
                self._send(404, {"error": "not_found"})
                return
            if self._provider_token() is None:
                self._unauthorized(resource)
                return
            self._send(405, {"error": "method_not_allowed"}, {"Allow": "GET, POST"})

        def do_POST(self):
            if not self._host_allowed():
                return
            if self.path != MCP_PATH:
                self._send(404, {"error": "not_found"})
                return
            principal = self._provider_token()
            if principal is None:
                self._unauthorized(resource)
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            accept = {item.split(";", 1)[0].strip().lower()
                      for item in self.headers.get("Accept", "").split(",")}
            if content_type != "application/json" or "application/json" not in accept:
                self._send(415, {"error": "unsupported_media_type"})
                return
            raw_length = self.headers.get("Content-Length")
            try:
                length = int(raw_length)
            except (TypeError, ValueError):
                self._send(411, {"error": "content_length_required"})
                return
            if not 0 <= length <= MAX_HTTP_BODY_BYTES:
                self._send(413, {"error": "request_too_large"})
                return
            try:
                message = json.loads(self.rfile.read(length).decode("utf-8"),
                                     parse_constant=_reject_json_constant)
            except (UnicodeError, json.JSONDecodeError, ValueError):
                self._send(400, ExternalReasoningMCPAdapter._rpc_error(None, -32700, "Parse error"))
                return
            protocol = self.headers.get("MCP-Protocol-Version")
            if protocol is not None and protocol not in SUPPORTED_PROTOCOL_VERSIONS:
                self._send(400, ExternalReasoningMCPAdapter._rpc_error(
                    message.get("id") if isinstance(message, dict) else None,
                    -32600, "Unsupported protocol version"))
                return
            if isinstance(message, dict) and message.get("method") != "initialize":
                protocol = protocol or "2025-03-26"
                if protocol not in SUPPORTED_PROTOCOL_VERSIONS:
                    self._send(400, ExternalReasoningMCPAdapter._rpc_error(
                        message.get("id"), -32600, "Protocol version required"))
                    return
                if self.headers.get("Mcp-Method") not in (None, message.get("method")):
                    self._send(400, ExternalReasoningMCPAdapter._rpc_error(
                        message.get("id"), -32600, "MCP method header mismatch"))
                    return
                if message.get("method") == "tools/call":
                    tool_name = message.get("params", {}).get("name") if isinstance(message.get("params"), dict) else None
                    if self.headers.get("Mcp-Name") not in (None, tool_name):
                        self._send(400, ExternalReasoningMCPAdapter._rpc_error(
                            message.get("id"), -32600, "MCP name header mismatch"))
                        return
            try:
                response = adapter.handle_rpc(principal, message, protocol)
            except Exception as exc:
                # Do not log input, provider credentials, SQL text, or exception messages.
                import logging
                logging.getLogger("riverview.external_reasoning_mcp").error(
                    "request_failed error_type=%s", type(exc).__name__)
                response = ExternalReasoningMCPAdapter._rpc_error(
                    message.get("id") if isinstance(message, dict) else None,
                    -32603, "Internal error")
            if response is None:
                self._send(202)
            else:
                self._send(200, response)

        def _unauthorized(self, protected_resource_url):
            metadata_url = resource + PROTECTED_RESOURCE_PATH
            challenge = ('Bearer resource_metadata="' + metadata_url +
                         '", scope="reasoning:exchange"')
            self._send(401, {"error": "unauthorized"}, {"WWW-Authenticate": challenge})

        def _provider_token(self):
            auth = self.headers.get("Authorization", "")
            scheme, _, token = auth.partition(" ")
            if scheme.lower() != "bearer" or not token:
                return None
            try:
                return adapter.token_map.resolve(token)
            except MCPAuthenticationError:
                return None

    return Handler


def create_server(adapter, *, host="127.0.0.1", port=11827,
                  resource_url: str, authorization_server_url: str,
                  allowed_hosts=(), allowed_origins=(), max_handlers=16):
    """Create the loopback-only default server; TLS belongs to the approved proxy."""
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise MCPConfigurationError("listener_must_be_loopback")
    if type(port) is not int or not 1 <= port <= 65535:
        raise MCPConfigurationError("listener_port_invalid")
    return BoundedThreadingHTTPServer((host, port),
        make_handler(adapter, resource_url=resource_url,
            authorization_server_url=authorization_server_url,
            allowed_hosts=allowed_hosts, allowed_origins=allowed_origins),
        max_handlers=max_handlers)


def _https_url(value):
    if not isinstance(value, str) or len(value) > 512:
        raise MCPConfigurationError("oauth_resource_metadata_invalid")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise MCPConfigurationError("oauth_resource_metadata_invalid")
    return value


def _reject_json_constant(_value):
    raise ValueError("invalid_json_number")


def _canonical_host(value):
    if not isinstance(value, str) or not value:
        raise MCPConfigurationError("listener_allowlist_invalid")
    try:
        return ipaddress.ip_address(value).compressed.lower()
    except ValueError:
        normalized = value.lower()
        if not _HOSTNAME.fullmatch(normalized) or ".." in normalized:
            raise MCPConfigurationError("listener_allowlist_invalid") from None
        return normalized.rstrip(".")


def _configured_host(value):
    if not isinstance(value, str) or not value or value == "*":
        raise MCPConfigurationError("listener_allowlist_invalid")
    try:
        parsed = urlsplit("//" + value)
        if (parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                or parsed.port is not None):
            raise MCPConfigurationError("listener_allowlist_invalid")
        return _canonical_host(parsed.hostname or "")
    except ValueError:
        raise MCPConfigurationError("listener_allowlist_invalid") from None
