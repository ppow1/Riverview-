"""Loopback Comms5 MCP compatibility endpoint.

File Revision: 1.1.0
Component: COMMS5-CAMRUI-ADAPTER
Authority: OAuth is validated at the Ionoge ingress; this service accepts only
           the Caddy-injected principal marker and a separate protected hop token.
Purpose: Preserve the historical Comms5 tool contract while incrementally
         mapping tools to current Camrui services.
History: New file; no predecessor existed.
"""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_HERE = Path(__file__).resolve().parent
_CATALOG = json.loads((_HERE / "tool_catalog.json").read_text(encoding="utf-8"))
_TOOLS = {tool["name"]: tool for tool in _CATALOG["tools"]}
_PAYLOADS = _CATALOG["read_only_payloads"]
_IMPLEMENTED = {
    "comms5_contract_info",
    "comms5_help",
    "comms5_capabilities",
    "comms5_describe_operation",
    "comms5_examples",
}


def _tool_payload(request_id: Any, value: dict[str, Any], *, is_error: bool = False):
    return {
        "jsonrpc": "2.0", "id": request_id,
        "result": {
            "content": [{"type": "text", "text": json.dumps(value, separators=(",", ":"))}],
            "structuredContent": value,
            "isError": is_error,
        },
    }


def _error(code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}}


def _valid(schema: dict[str, Any], value: Any) -> bool:
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            return False
        if any(key not in value for key in schema.get("required", [])):
            return False
        properties = schema.get("properties", {})
        if any(key not in properties for key in value):
            return False
        return all(_valid(properties[key], item) for key, item in value.items())
    if kind == "array":
        return isinstance(value, list) and all(_valid(schema.get("items", {}), item) for item in value)
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    return True


class Comms5Application:
    """Transport-neutral MCP request handler used by HTTP and isolated tests."""

    def __init__(self, backend_token: str, *, backend=None, protocol_versions: tuple[str, ...] = (
        "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"
    )) -> None:
        if not backend_token or len(backend_token) < 32:
            raise ValueError("comms5_backend_token_invalid")
        self._backend_token = backend_token
        self.backend = backend
        self.protocol_versions = protocol_versions

    @property
    def implemented_tools(self):
        dynamic = getattr(self.backend, "supported_tools", ()) if self.backend else ()
        return frozenset(_IMPLEMENTED | set(dynamic))

    def implementation_status(self, name):
        backend_status = getattr(self.backend, "IMPLEMENTATION_STATUS", {})
        if name in backend_status and name in self.implemented_tools:
            return backend_status[name]
        return "IMPLEMENTED" if name in self.implemented_tools else "NOT_IMPLEMENTED"

    def authenticated(self, headers: Any) -> bool:
        marker = headers.get("X-Riverview-Comms5", "")
        principal = headers.get("X-Riverview-Comms5-Principal", "")
        authorization = headers.get("Authorization", "")
        scheme, _, supplied = authorization.partition(" ")
        return (
            marker == "1"
            and principal == "steward"
            and scheme.lower() == "bearer"
            and bool(supplied)
            and hmac.compare_digest(supplied, self._backend_token)
        )

    def handle(self, request: Any) -> dict[str, Any] | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return _error(-32600, "Invalid Request")
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params") or {}
        if not isinstance(params, dict):
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Invalid params"}}

        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "initialize":
            version = params.get("protocolVersion")
            if version not in self.protocol_versions:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Unsupported protocol version"}}
            return {
                "jsonrpc": "2.0", "id": request_id,
                "result": {
                    "protocolVersion": version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "Riverview Comms5", "version": "5.0-camrui.2"},
                    "instructions": "Comms5 compatibility endpoint. Tool contracts are preserved; unsupported backend operations return NOT_IMPLEMENTED and do not execute.",
                },
            }
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": _CATALOG["tools"]}}
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            tool = _TOOLS.get(name) if isinstance(name, str) else None
            if tool is None:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Unknown tool"}}
            if not _valid(tool["inputSchema"], arguments):
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Arguments do not match the published tool schema"}}
            if name not in self.implemented_tools:
                result_value = {
                    "status": "NOT_IMPLEMENTED", "executed": False,
                    "tool": name,
                    "reason": "Historical operation is retained in the MCP catalog but its current Camrui backend contract has not yet been verified.",
                }
                return {
                    "jsonrpc": "2.0", "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result_value, separators=(",", ":"))}],
                        "structuredContent": result_value,
                        "isError": True,
                    },
                }
            if self.backend and name in getattr(self.backend, "supported_tools", ()):
                try:
                    value = self.backend.call(name, arguments)
                except ValueError:
                    return {"jsonrpc": "2.0", "id": request_id,
                            "error": {"code": -32602, "message": "Arguments do not match the bounded operation contract"}}
                except Exception as exc:
                    from .dashboard_backend import DashboardBackendUnavailable
                    error_value = {
                        "status": ("BACKEND_UNAVAILABLE" if isinstance(exc, DashboardBackendUnavailable)
                                   else "BACKEND_FAILURE"),
                        "executed": False, "tool": name,
                        "reason": (str(exc) if isinstance(exc, DashboardBackendUnavailable)
                                   else "backend_internal_failure"),
                    }
                    if not isinstance(exc, DashboardBackendUnavailable):
                        error_value["failure_type"] = type(exc).__name__
                    return _tool_payload(request_id, error_value, is_error=True)
                value = {**value, "implementation_status": self.implementation_status(name)}
                return _tool_payload(request_id, value)
            if name == "comms5_describe_operation":
                operation = arguments["operation"]
                value = _PAYLOADS.get("describe:" + operation)
                if value is None:
                    value = {"error": {"code": "RIV-COMMS5-0004", "reason": "operation is unknown"}}
            else:
                value = _PAYLOADS[name]
            value = json.loads(json.dumps(value))
            if name == "comms5_capabilities":
                for operation in value.get("operations", []):
                    tool_name = "comms5_" + operation.get("name", "")
                    operation["camrui_implementation_status"] = (
                    self.implementation_status(tool_name)
                    )
            elif name == "comms5_help":
                value["camrui_migration_notice"] = {
                    "implemented_tools": sorted(self.implemented_tools),
                    "not_implemented_tool_count": len(_TOOLS) - len(self.implemented_tools),
                    "partially_implemented_tools": sorted(
                        name for name in self.implemented_tools
                        if self.implementation_status(name) == "PARTIALLY_IMPLEMENTED"),
                    "stub_behavior": "MCP tool error; status NOT_IMPLEMENTED; executed false; no backend operation",
                }
            elif name == "comms5_describe_operation" and "error" not in value:
                value["camrui_implementation_status"] = (
                    self.implementation_status("comms5_" + operation)
                )
            elif name == "comms5_examples":
                value["camrui_execution_note"] = (
                    "Examples preserve the historical contract. An operation marked NOT_IMPLEMENTED "
                    "in capabilities returns an MCP tool error and performs no action."
                )
            return {
                "jsonrpc": "2.0", "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(value, separators=(",", ":"))}],
                    "structuredContent": value,
                    "isError": False,
                },
            }
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}


def _load_backend_token() -> str:
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "")
    credential_path = Path(credential_dir) / "backend-auth" if credential_dir else Path(os.environ.get("RIVERVIEW_COMMS5_BACKEND_TOKEN_FILE", ""))
    if not str(credential_path) or not credential_path.is_file():
        raise RuntimeError("comms5_backend_credential_missing")
    token = credential_path.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("comms5_backend_credential_empty")
    return token


def create_handler(app: Comms5Application) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, fmt: str, *args: Any) -> None:
            # Never log request headers, bearer values, JSON arguments, or URLs.
            return

        def _send(self, status: int, payload: dict[str, Any] | None, *, empty: bool = False) -> None:
            body = b"" if empty else json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/healthz":
                self._send(200, {"status": "ok", "service": "riverview-comms5-camrui"})
            elif path == "/mcp":
                if not app.authenticated(self.headers):
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Bearer realm="Riverview Comms5"')
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self.send_response(405)
                    self.send_header("Allow", "POST, OPTIONS")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
            else:
                self._send(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/mcp":
                self._send(404, {"error": "not_found"})
                return
            if not app.authenticated(self.headers):
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Bearer realm="Riverview Comms5"')
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            accept = self.headers.get("Accept", "")
            if "application/json" not in accept:
                self._send(406, _error(-32600, "Accept must include application/json"))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send(400, _error(-32700, "Invalid Content-Length"))
                return
            if length <= 0 or length > 262144:
                self._send(413, _error(-32700, "Request body exceeds limit"))
                return
            try:
                value = json.loads(self.rfile.read(length))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send(400, _error(-32700, "Parse error"))
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self._send(415, _error(-32700, "Content-Type must be application/json"))
                return
            if isinstance(value, list):
                self._send(400, _error(-32600, "JSON-RPC batch requests are not supported"))
                return
            if (
                isinstance(value, dict)
                and value.get("method") != "initialize"
                and self.headers.get("MCP-Protocol-Version", "") not in app.protocol_versions
            ):
                self._send(400, _error(-32600, "A supported MCP-Protocol-Version header is required"))
                return
            response = app.handle(value)
            if response is None:
                self._send(202, None, empty=True)
            else:
                self._send(200, response)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Allow", "GET, POST, OPTIONS")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_DELETE(self) -> None:
            self.send_response(405)
            self.send_header("Allow", "POST, OPTIONS")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler


def main() -> None:
    token = _load_backend_token()
    from .dashboard_backend import DashboardReadBackend
    backend = DashboardReadBackend()
    host = os.environ.get("RIVERVIEW_COMMS5_HOST", "127.0.0.1")
    port = int(os.environ.get("RIVERVIEW_COMMS5_PORT", "11826"))
    if host != "127.0.0.1":
        raise RuntimeError("comms5_listener_must_be_loopback")
    server = ThreadingHTTPServer((host, port), create_handler(Comms5Application(token, backend=backend)))
    server.daemon_threads = True
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
