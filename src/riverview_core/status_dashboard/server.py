# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/server.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.0
# Purpose: Serve the authenticated, loopback-only status UI and versioned API
# Execution Model: Request-driven, independent of CME assignment execution
# Observability: Structured request IDs, HTTP health/error codes, PostgreSQL projection
# Dependencies: Python 3.10+; standard library; status_dashboard.projection
# Authority: Authenticated GET-only interface; no command or database write routes
# Changed: 2026-10-10 UTC | RV-M3.1-001 | Add bounded authenticated HTTP service
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_status_dashboard.py
# History: Git and revision/backup manifest
# =============================================================================
"""Loopback-only HTTP server for the read-only Steward status projection."""

from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .projection import DashboardProjection, ProjectionUnavailable

_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}
_MAX_THREADS = 16
_MAX_PAGE = 100

def _bounded_limit(value):
    try:
        return min(_MAX_PAGE, max(1, int(value)))
    except (TypeError, ValueError):
        return 25


def _read_token(path: str | Path) -> str:
    token_path = Path(path)
    if token_path.is_symlink():
        raise RuntimeError("dashboard token must not be a symbolic link")
    metadata = token_path.stat()
    if not token_path.is_file() or token_path.is_symlink() or metadata.st_mode & 0o077:
        raise RuntimeError("dashboard token must be a regular, owner-only credential")
    token = token_path.read_text(encoding="ascii").strip()
    if not _TOKEN_PATTERN.fullmatch(token):
        raise RuntimeError("dashboard token credential has invalid format")
    return token


class _BoundedHTTPServer(HTTPServer):
    """Bound concurrent requests; saturation fails fast instead of growing threads."""
    request_queue_size = 64

    def __init__(self, address, handler, *, token, projection, static_dir):
        self._token = token
        self._projection = projection
        self._static_dir = Path(static_dir)
        self._slots = threading.BoundedSemaphore(_MAX_THREADS)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            finally:
                self.shutdown_request(request)
            return
        thread = threading.Thread(target=self._process_bounded,
                                  args=(request, client_address), daemon=True)
        thread.start()

    def _process_bounded(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)
            self._slots.release()


def make_handler():
    class Handler(BaseHTTPRequestHandler):
        server_version = "RiverviewStatus/1"
        sys_version = ""

        def log_message(self, _format, *_args):
            # The access log omits URL, headers, query values, and body contents.
            return

        def _headers(self, request_id: str):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
                             "form-action 'self'; frame-ancestors 'none'")
            self.send_header("X-Request-ID", request_id)

        def _send(self, status: int, body: bytes, content_type: str,
                  request_id: str, extra_headers=()):
            self.send_response(status)
            self._headers(request_id)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for key, value in extra_headers:
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, data, request_id: str):
            body = json.dumps(data, separators=(",", ":"), ensure_ascii=True,
                              default=str).encode("utf-8")
            if len(body) > 256 * 1024:
                status, body = 500, b'{"error":"response_too_large"}'
            self._send(status, body, "application/json; charset=utf-8", request_id)

        def _error(self, status, code, request_id):
            self._json(status, {"error": code, "request_id": request_id}, request_id)

        def _host_ok(self):
            host_header = self.headers.get("Host", "").strip()
            host = host_header.rsplit(":", 1)[0] if ":" in host_header and not host_header.startswith("[") else host_header
            if host_header.startswith("["):
                host = host_header.split("]", 1)[0] + "]"
            return host.lower() in _LOOPBACK_HOSTS

        def _authorized(self):
            supplied = self.headers.get("Authorization", "")
            if not supplied.startswith("Bearer "):
                return False
            return hmac.compare_digest(supplied[7:], self.server._token)

        def do_GET(self):
            self._dispatch()

        def do_HEAD(self):
            self._dispatch()

        def do_POST(self):
            self._dispatch()

        def do_PUT(self):
            self._dispatch()

        def do_PATCH(self):
            self._dispatch()

        def do_DELETE(self):
            self._dispatch()

        def do_OPTIONS(self):
            self._dispatch()

        def _dispatch(self):
            request_id = secrets.token_hex(12)
            parsed = urlsplit(self.path)
            if not self._host_ok():
                self._error(400, "invalid_host", request_id)
                return
            if self.command not in {"GET", "HEAD"}:
                self._error(405, "read_only_method", request_id)
                return
            if parsed.path == "/":
                path = self.server._static_dir / "index.html"
                try:
                    self._send(200, path.read_bytes(), "text/html; charset=utf-8", request_id)
                except OSError:
                    self._error(503, "ui_unavailable", request_id)
                return
            if parsed.path in {"/assets/app.js", "/assets/app.css"}:
                name = "app.js" if parsed.path.endswith(".js") else "app.css"
                kind = "text/javascript" if name.endswith(".js") else "text/css"
                try:
                    self._send(200, (self.server._static_dir / name).read_bytes(),
                               kind + "; charset=utf-8", request_id)
                except OSError:
                    self._error(503, "asset_unavailable", request_id)
                return
            if parsed.path in {
                "/docs/components/CME_MONITOR_COOKBOOK.md",
                "/docs/components/STATUS_DASHBOARD_COOKBOOK.md",
            }:
                name = parsed.path.rsplit("/", 1)[-1]
                release_root = Path(__file__).resolve().parents[3]
                try:
                    body = (release_root / "docs/components" / name).read_bytes()
                    self._send(200, body, "text/markdown; charset=utf-8", request_id)
                except OSError:
                    self._error(404, "diagnostic_reference_unavailable", request_id)
                return
            if not parsed.path.startswith("/api/v1/"):
                self._error(404, "not_found", request_id)
                return
            if not self._authorized():
                self.send_response(401)
                self._headers(request_id)
                self.send_header("WWW-Authenticate", 'Bearer realm="Riverview dashboard"')
                self.send_header("Content-Type", "application/json; charset=utf-8")
                body = json.dumps({"error": "authentication_required", "request_id": request_id}).encode()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
                return
            try:
                query = parse_qs(parsed.query, keep_blank_values=False, max_num_fields=12)
                if parsed.path == "/api/v1/status":
                    self._json(200, self.server._projection.status(), request_id)
                elif parsed.path == "/api/v1/assignments":
                    page = self.server._projection.assignments(
                        after=query.get("after", [None])[0],
                        limit=_bounded_limit(query.get("limit", [25])[0]))
                    self._json(200 if page["status"] != "not_initialized" else 503, page, request_id)
                elif parsed.path == "/api/v1/events":
                    after_seq = query.get("after_seq", [None])[0]
                    before_seq = query.get("before_seq", [None])[0]
                    page = self.server._projection.events(after_seq=after_seq, before_seq=before_seq,
                                                          limit=_bounded_limit(query.get("limit", [25])[0]))
                    self._json(200 if page["status"] != "not_initialized" else 503, page, request_id)
                elif parsed.path == "/api/v1/attention":
                    page = self.server._projection.attention(limit=_bounded_limit(query.get("limit", [25])[0]))
                    self._json(200 if page["status"] != "not_initialized" else 503, page, request_id)
                elif parsed.path == "/api/v1/snapshot":
                    self._json(200, self.server._projection.snapshot(), request_id)
                elif parsed.path.startswith("/api/v1/assignments/"):
                    assignment_id = unquote(parsed.path.removeprefix("/api/v1/assignments/"), errors="strict")
                    result = self.server._projection.assignment_detail(assignment_id)
                    self._json(200, result, request_id) if result else self._error(404, "assignment_not_found", request_id)
                else:
                    self._error(404, "not_found", request_id)
            except ValueError:
                self._error(400, "invalid_query", request_id)
            except ProjectionUnavailable:
                self._error(503, "projection_unavailable", request_id)
            except Exception as exc:
                # Error class is logged; exception text may contain driver details and is excluded.
                print(json.dumps({"event": "dashboard_request_failed", "request_id": request_id,
                                  "error_type": type(exc).__name__}), flush=True)
                self._error(500, "projection_failed", request_id)

    return Handler


class DashboardHTTPServer(_BoundedHTTPServer):
    """Validated loopback listener with a mandatory owner-only bearer credential."""

    def __init__(self, host: str, port: int, token_file: str | Path,
                 projection: DashboardProjection, static_dir: str | Path | None = None):
        if host not in {"127.0.0.1", "::1"}:
            raise ValueError("dashboard bind host must be a loopback IP literal")
        if not isinstance(port, int) or not 8700 <= port <= 8799:
            raise ValueError("dashboard port must be reserved in 8700-8799")
        credential = _read_token(token_file)
        if static_dir is None:
            static_dir = Path(__file__).with_name("static")
        super().__init__((host, port), make_handler(), token=credential,
                         projection=projection, static_dir=static_dir)


def main():
    token_path = os.environ.get("CREDENTIALS_DIRECTORY", "")
    if not token_path:
        raise SystemExit("systemd dashboard credential directory is required")
    token_path = Path(token_path) / "dashboard-token"
    dsn = os.environ.get("RIVERVIEW_DATABASE_DSN", "")
    if not dsn:
        raise SystemExit("RIVERVIEW_DATABASE_DSN is required")
    projection = DashboardProjection(
        dsn, schema=os.environ.get("RIVERVIEW_DATABASE_SCHEMA", "riverview_dev"),
        source_commit=os.environ.get("RIVERVIEW_SOURCE_COMMIT", "unknown"),
        deployment_id=os.environ.get("RIVERVIEW_DEPLOYMENT_ID", "unconfigured"),
        heartbeat_stale_seconds=int(os.environ.get("RIVERVIEW_STALE_AFTER_SECONDS", "30")))
    host = os.environ.get("RIVERVIEW_DASHBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("RIVERVIEW_DASHBOARD_PORT", "8766"))
    server = DashboardHTTPServer(host, port, token_path, projection)
    print(json.dumps({"event": "dashboard_started", "host": host, "port": port,
                      "source_commit": projection.source_commit,
                      "deployment_id": projection.deployment_id}), flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
