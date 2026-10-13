# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/server.py
# Component: STEWARD-DASHBOARD
# Revision: 1.3.3
# Purpose: Serve account-authenticated operational projections and existing bounded APIs
# Execution Model: Request-driven, independent of CME assignment execution
# Observability: Structured request IDs, HTTP health/error codes, PostgreSQL projection
# Dependencies: Python 3.10+; standard library; status_dashboard.projection
# Authority: Dashboard credential protects views; objective API also requires exact objective.submit grant
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-ERROR-SEMANTICS | Preserve conflict/dependency failure distinction
# Changed: 2026-10-11 UTC | RV-M3.2-001 | Enforce the notification-specific maximum page size
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Add exact-grant resident conversation API and restart reconciliation
# Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Persist exact-grant browser access in a scoped HttpOnly cookie with revocation checks
# Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Restrict cookie issuance to URL-safe credentials to prevent response-header injection
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Add email enrollment, session auth and Steward account routes
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Add verified, challenge-bound Steward bootstrap completion
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Use nginx's overwritten client IP for source-based auth throttling
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Add account auth health and email readiness to status projection
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Stop dispatch after account-specific HTTP responses
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001-CSRF-PATH | Make the CSRF cookie readable to same-origin dashboard code
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Add password sessions, approval grants and Steward email configuration routes
# Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Bind authenticated Steward sessions to existing exact office grants
# Changed: 2026-10-13 UTC | RV-GRACE-TO-ENGINEERING | Add explicit conversation-to-objective intake gate
# Changed: 2026-10-13 UTC | RV-LEDGER-GRAPH-POSITION | Read live execution position only from persisted canonical ledger identity
# Changed: 2026-10-13 UTC | RV-GRACE-TO-ENGINEERING-DENIALS | Preserve conversation authorization and unavailable distinctions at promotion boundary
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Expose only the scoped verification endpoint for local bootstrap challenges
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_status_dashboard.py
# History: Git and revision/backup manifest
# =============================================================================
"""Loopback-only Steward dashboard with read projections and receipt-only writes."""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
import re
import secrets
import stat
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .markdown import render_markdown
from .projection import DashboardProjection, ProjectionUnavailable

_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}
_MAX_THREADS = 16
_MAX_PAGE = 100
_DOC_NAME = re.compile(r"^[A-Za-z0-9_-]+\.md$")
_NOTICE_WRITE = re.compile(
    r"^/api/v1/notifications/([0-9a-fA-F-]{36})/(delivered|acknowledge)$")
_OBJECTIVE_DETAIL = re.compile(r"^/api/v1/objectives/(objective:[A-Za-z0-9._:-]{1,120})$")
_OBJECTIVE_PROPOSAL = re.compile(r"^/api/v1/objectives/(objective:[A-Za-z0-9._:-]{1,120})/proposal$")
_OBJECTIVE_CANCEL = re.compile(r"^/api/v1/objectives/(objective:[A-Za-z0-9._:-]{1,120})/cancel$")
_CONVERSATION_ID = re.compile(r"^/api/v1/resident/conversations/([0-9a-fA-F-]{36})$")
_CONVERSATION_SESSION = "/api/v1/resident/conversation-session"
_CONVERSATION_COOKIE = "rv_grace_authority"
_CONVERSATION_COOKIE_MAX_AGE = 30 * 24 * 60 * 60
_COOKIE_CREDENTIAL = re.compile(r"^[A-Za-z0-9_-]{32,512}$")
_CONVERSATION_STATUS = re.compile(
    r"^/api/v1/resident/conversations/([0-9a-fA-F-]{36})/responses/([0-9a-fA-F-]{36})$")
_CONVERSATION_WORK_ORDER = re.compile(
    r"^/api/v1/resident/conversations/([0-9a-fA-F-]{36})/work-orders$")
_MAX_CHAT_BODY = 12 * 1024
_MAX_OBJECTIVE_BODY = 16 * 1024
_MAX_ACCOUNT_BODY = 8 * 1024
_ACCOUNT_SESSION_COOKIE = "rv_account_session"
_ACCOUNT_CSRF_COOKIE = "rv_account_csrf"
_ACCOUNT_COOKIE_TTL = 30 * 24 * 60 * 60
_PUBLIC_AUTH_POSTS = {
    "/api/v1/auth/enrollment", "/api/v1/auth/enrollment/verify",
    "/api/v1/auth/login", "/api/v1/auth/session", "/api/v1/auth/password-reset",
    "/api/v1/auth/password",
    "/api/v1/auth/steward-bootstrap/verify",
}
_ACCOUNT_ENROLLMENT_DECISION = re.compile(
    r"^/api/v1/account/enrollments/([0-9a-fA-F-]{36})/decision$")
_ACCOUNT_USER_PATH = re.compile(r"^/api/v1/account/users/([0-9a-fA-F-]{36})/(disable|roles|sessions|grant)$")

def _bounded_limit(value):
    try:
        return min(_MAX_PAGE, max(1, int(value)))
    except (TypeError, ValueError):
        return 25


def _read_token(path: str | Path) -> str:
    token_path = Path(path)
    if token_path.is_symlink():
        raise RuntimeError("dashboard token must not be a symbolic link")
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    systemd_credential = (credential_dir is not None and
                          token_path.parent.resolve() == Path(credential_dir).resolve() and
                          token_path.name == "dashboard-token")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(token_path, flags)
    except OSError:
        raise RuntimeError("dashboard token must be a regular protected credential") from None
    with os.fdopen(descriptor, "r", encoding="ascii") as terminal:
        metadata = os.fstat(terminal.fileno())
        mode = metadata.st_mode & 0o777
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("dashboard token must be a regular protected credential")
        if systemd_credential:
            secure_mode = mode in {0o400, 0o440}
        else:
            secure_mode = (mode & 0o077) == 0
        if not secure_mode:
            raise RuntimeError("dashboard token must be a regular owner-only or non-writable protected credential")
        token = terminal.read().strip()
    if not _TOKEN_PATTERN.fullmatch(token):
        raise RuntimeError("dashboard token credential has invalid format")
    return token


class _BoundedHTTPServer(HTTPServer):
    """Bound concurrent requests; saturation fails fast instead of growing threads."""
    request_queue_size = 64

    def __init__(self, address, handler, *, token, projection, notification_service,
                 objective_pipeline, conversation_service, account_auth_service, static_dir):
        self._token = token
        self._projection = projection
        self._notification_service = notification_service
        self._objective_pipeline = objective_pipeline
        self._conversation_service = conversation_service
        self._account_auth_service = account_auth_service
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

        def _json(self, status: int, data, request_id: str, extra_headers=()):
            body = json.dumps(data, separators=(",", ":"), ensure_ascii=True,
                              default=str).encode("utf-8")
            if len(body) > 256 * 1024:
                status, body = 500, b'{"error":"response_too_large"}'
            self._send(status, body, "application/json; charset=utf-8", request_id,
                       extra_headers=extra_headers)

        def _conversation_authority(self):
            """Use authenticated linked Steward identity or the retained legacy credential."""
            explicit = self.headers.get("X-Riverview-Authority")
            if explicit is not None:
                return explicit
            identity = getattr(self, "_account_identity", None)
            if (getattr(self, "_account_cookie_authenticated", False) and identity
                    and "steward" in identity.get("roles", ())
                    and identity.get("authority_principal_id")):
                from riverview_core.institutional_authority.grants import InstitutionalPrincipal
                return InstitutionalPrincipal(identity["authority_principal_id"])
            raw = self.headers.get("Cookie", "")
            if len(raw) > 8192:
                return ""
            values = []
            for item in raw.split(";"):
                key, sep, value = item.strip().partition("=")
                if sep and key == _CONVERSATION_COOKIE:
                    values.append(value)
            return values[0] if len(values) == 1 and 32 <= len(values[0]) <= 512 else ""

        @staticmethod
        def _conversation_cookie(value, *, clear=False):
            age = 0 if clear else _CONVERSATION_COOKIE_MAX_AGE
            content = "" if clear else value
            return (f"{_CONVERSATION_COOKIE}={content}; Max-Age={age}; "
                    "Path=/api/v1/resident/conversations; Secure; HttpOnly; SameSite=Strict")

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
            if supplied.startswith("Bearer ") and hmac.compare_digest(supplied[7:], self.server._token):
                self._account_identity = None
                self._account_cookie_authenticated = False
                return True
            raw_cookie = self.headers.get("Cookie", "")
            if len(raw_cookie) > 8192 or self.server._account_auth_service is None:
                return False
            values = []
            for item in raw_cookie.split(";"):
                key, sep, value = item.strip().partition("=")
                if sep and key == _ACCOUNT_SESSION_COOKIE:
                    values.append(value)
            if len(values) != 1:
                return False
            csrf = self.headers.get("X-Riverview-CSRF")
            try:
                self._account_identity = self.server._account_auth_service.authenticate(
                    values[0], csrf_token=csrf,
                    state_changing=self.command not in {"GET", "HEAD"})
            except Exception as exc:
                self._account_identity = None
                self._account_cookie_authenticated = True
                from riverview_core.account_auth import AuthDenied
                self._account_auth_denied = isinstance(exc, AuthDenied)
                self._account_auth_failed = not self._account_auth_denied
                return False
            self._account_auth_failed = False
            self._account_cookie_authenticated = self._account_identity is not None
            return self._account_cookie_authenticated

        @staticmethod
        def _account_cookie(value, *, clear=False):
            content = "" if clear else value
            age = 0 if clear else _ACCOUNT_COOKIE_TTL
            return (f"{_ACCOUNT_SESSION_COOKIE}={content}; Max-Age={age}; Path=/api/v1; "
                    "Secure; HttpOnly; SameSite=Lax")

        @staticmethod
        def _csrf_cookie(value, *, clear=False):
            content = "" if clear else value
            age = 0 if clear else _ACCOUNT_COOKIE_TTL
            return (f"{_ACCOUNT_CSRF_COOKIE}={content}; Max-Age={age}; Path=/; "
                    "Secure; SameSite=Strict")

        def _account_token_cookie(self):
            raw_cookie = self.headers.get("Cookie", "")
            if len(raw_cookie) > 8192:
                return ""
            values = [part.strip().partition("=")[2] for part in raw_cookie.split(";")
                      if part.strip().partition("=")[0] == _ACCOUNT_SESSION_COOKIE]
            return values[0] if len(values) == 1 else ""

        def _account_public_origin_ok(self):
            origin = self.headers.get("Origin")
            if not origin:
                return True
            allowed = {value.strip().rstrip("/") for value in
                       os.environ.get("RIVERVIEW_PUBLIC_ORIGINS",
                                      "https://192.168.1.155,https://riverview.ionoge.com").split(",")}
            return origin.rstrip("/") in allowed

        def _request_source_key(self):
            source = self.client_address[0]
            if source in {"127.0.0.1", "::1"}:
                forwarded = self.headers.get("X-Real-IP", "")
                try:
                    if len(forwarded) <= 45:
                        source = str(ipaddress.ip_address(forwarded))
                except ValueError:
                    pass
            return source

        def _json_body(self, maximum):
            if self.headers.get("Transfer-Encoding") or not self.headers.get("Content-Length", "").isdigit():
                raise ValueError("request_length_required")
            length = int(self.headers["Content-Length"])
            if not 1 <= length <= maximum:
                raise OverflowError("request_too_large")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("invalid_request_shape")
            return data

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
            notification_write = (_NOTICE_WRITE.fullmatch(parsed.path)
                                  if self.command == "POST" else None)
            objective_submit = (parsed.path == "/api/v1/objectives" and
                                self.command == "POST")
            objective_proposal = (_OBJECTIVE_PROPOSAL.fullmatch(parsed.path)
                                  if self.command == "POST" else None)
            objective_cancel = (_OBJECTIVE_CANCEL.fullmatch(parsed.path)
                                if self.command == "POST" else None)
            account_decision = (_ACCOUNT_ENROLLMENT_DECISION.fullmatch(parsed.path)
                                if self.command == "POST" else None)
            account_user = (_ACCOUNT_USER_PATH.fullmatch(parsed.path)
                            if self.command == "POST" else None)
            public_auth = parsed.path in _PUBLIC_AUTH_POSTS and self.command == "POST"
            auth_logout = parsed.path == "/api/v1/auth/session" and self.command == "DELETE"
            account_queue = parsed.path == "/api/v1/account/enrollments" and self.command == "GET"
            account_users = parsed.path == "/api/v1/account/users" and self.command == "GET"
            account_email_settings = parsed.path == "/api/v1/account/email-settings" and self.command == "GET"
            account_email_save = parsed.path == "/api/v1/account/email-settings" and self.command == "PUT"
            account_email_test = parsed.path == "/api/v1/account/email-settings/test" and self.command == "POST"
            conversation_send = (parsed.path == "/api/v1/resident/conversations"
                                 and self.command == "POST")
            conversation_work_order = (_CONVERSATION_WORK_ORDER.fullmatch(parsed.path)
                                       if self.command == "POST" else None)
            conversation_session = (parsed.path == _CONVERSATION_SESSION
                                     and self.command in {"POST", "DELETE"})
            if not self._host_ok():
                self._error(400, "invalid_host", request_id)
                return
            if (self.command not in {"GET", "HEAD"} and not notification_write
                    and not objective_submit and not objective_proposal and not objective_cancel
                    and not conversation_send and not conversation_session and not public_auth
                    and not conversation_work_order
                    and not auth_logout and not account_decision and not account_user
                    and not account_email_save and not account_email_test):
                self._error(405, "read_only_method", request_id)
                return
            if parsed.path == "/":
                path = self.server._static_dir / "index.html"
                try:
                    self._send(200, path.read_bytes(), "text/html; charset=utf-8", request_id)
                except OSError:
                    self._error(503, "ui_unavailable", request_id)
                return
            if parsed.path in {"/assets/app.js", "/assets/app.css", "/assets/workflow.js"}:
                name = parsed.path.rsplit("/", 1)[-1]
                kind = "text/javascript" if name.endswith(".js") else "text/css"
                try:
                    self._send(200, (self.server._static_dir / name).read_bytes(),
                               kind + "; charset=utf-8", request_id)
                except OSError:
                    self._error(503, "asset_unavailable", request_id)
                return
            doc_match = re.fullmatch(r"/docs/components/([A-Za-z0-9_-]+\.md)", unquote(parsed.path))
            if doc_match and _DOC_NAME.fullmatch(doc_match.group(1)):
                name = doc_match.group(1)
                release_root = Path(__file__).resolve().parents[3]
                doc_path = release_root / "docs" / "components" / name
                try:
                    if doc_path.is_symlink() or not doc_path.is_file():
                        raise FileNotFoundError
                    source = doc_path.read_text(encoding="utf-8")
                    body = render_markdown(source, document=f"docs/components/{name}",
                                           title=name.removesuffix(".md").replace("_", " ").title())
                    self._send(200, body, "text/html; charset=utf-8", request_id)
                except (OSError, UnicodeError):
                    self._error(404, "diagnostic_reference_unavailable", request_id)
                return
            if not parsed.path.startswith("/api/v1/"):
                self._error(404, "not_found", request_id)
                return
            if public_auth:
                if self.server._account_auth_service is None:
                    self._error(503, "account_auth_unavailable", request_id)
                    return
                if not self._account_public_origin_ok():
                    self._error(403, "cross_origin_request_denied", request_id)
                    return
                try:
                    data = self._json_body(_MAX_ACCOUNT_BODY)
                    service = self.server._account_auth_service
                    if parsed.path == "/api/v1/auth/enrollment":
                        if set(data) != {"email"}:
                            raise ValueError("invalid_request_shape")
                        source = self._request_source_key()
                        result = service.request_access(data["email"], source_key=source)
                        self._json(202, result, request_id)
                    elif parsed.path == "/api/v1/auth/enrollment/verify":
                        if set(data) != {"challenge_id", "token"}:
                            raise ValueError("invalid_request_shape")
                        self._json(200, service.verify_enrollment(data["challenge_id"], data["token"]), request_id)
                    elif parsed.path == "/api/v1/auth/steward-bootstrap/verify":
                        if set(data) != {"challenge_id", "token"}:
                            raise ValueError("invalid_request_shape")
                        result = service.verify_steward_bootstrap(
                            data["challenge_id"], data["token"],
                            authority_principal_id="steward:camrui")
                        self._json(200, result, request_id)
                    elif parsed.path == "/api/v1/auth/password-reset":
                        if set(data)!={"email"}:
                            raise ValueError("invalid_request_shape")
                        self._json(202,service.request_password_reset(
                            data["email"],source_key=self._request_source_key()),request_id)
                    elif parsed.path == "/api/v1/auth/password":
                        if set(data)!={"challenge_id","token","password"}:
                            raise ValueError("invalid_request_shape")
                        self._json(200,service.set_password(data["challenge_id"],
                            data["token"],data["password"]),request_id)
                    else:
                        if set(data)!={"email","password"}:
                            raise ValueError("invalid_request_shape")
                        session = service.authenticate_password(data["email"],data["password"],
                            source_key=self._request_source_key())
                        identity = {"account_id": session.account_id, "email": session.email,
                                    "roles": session.roles, "expires_in": session.expires_in}
                        self._json(200, {"status": "authenticated", "identity": identity}, request_id,
                            extra_headers=(
                                ("Set-Cookie", self._account_cookie(session.session_token)),
                                ("Set-Cookie", self._csrf_cookie(session.csrf_token)),))
                except OverflowError:
                    self._error(413, "request_too_large", request_id)
                except ValueError:
                    self._error(400, "invalid_account_request", request_id)
                except Exception as exc:
                    self._account_error(exc, request_id)
                return
            if not self._authorized():
                if getattr(self, "_account_auth_denied", False):
                    self._error(403, "csrf_or_session_check_failed", request_id)
                    return
                if getattr(self, "_account_auth_failed", False):
                    self._error(503, "account_auth_unavailable", request_id)
                    return
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
                if parsed.path == "/api/v1/auth/session" and self.command in {"GET", "HEAD"}:
                    if not self._account_identity:
                        self._error(401, "authentication_required", request_id)
                    else:
                        identity = {key:self._account_identity[key] for key in
                                    ("account_id", "email", "roles") if key in self._account_identity}
                        self._json(200, {"status": "authenticated", "identity": identity}, request_id)
                    return
                elif auth_logout:
                    if not self._account_public_origin_ok():
                        self._error(403, "cross_origin_request_denied", request_id)
                        return
                    service = self.server._account_auth_service
                    if service is None:
                        self._error(503, "account_auth_unavailable", request_id)
                        return
                    service.logout(self._account_token_cookie())
                    self._json(200, {"status": "logged_out"}, request_id,
                               extra_headers=(
                                   ("Set-Cookie", self._account_cookie("", clear=True)),
                                   ("Set-Cookie", self._csrf_cookie("", clear=True))))
                    return
                elif account_queue:
                    identity = getattr(self, "_account_identity", None)
                    if not identity:
                        self._error(403, "steward_account_required", request_id)
                        return
                    page = self.server._account_auth_service.review_enrollments(
                        identity, limit=_bounded_limit(query.get("limit", [50])[0]))
                    self._json(200, {"items": page, "status": "available"}, request_id)
                    return
                elif account_users:
                    identity = getattr(self, "_account_identity", None)
                    if not identity:
                        self._error(403, "steward_account_required", request_id)
                        return
                    page = self.server._account_auth_service.list_accounts(
                        identity, limit=_bounded_limit(query.get("limit", [50])[0]))
                    self._json(200, {"items": page, "status": "available"}, request_id)
                    return
                elif account_email_settings:
                    identity=getattr(self,"_account_identity",None)
                    if not identity:
                        self._error(403,"steward_account_required",request_id)
                        return
                    result=self.server._account_auth_service.email_settings(identity)
                    self._json(200,result,request_id)
                    return
                elif account_email_save or account_email_test:
                    identity=getattr(self,"_account_identity",None)
                    if not identity:
                        self._error(403,"steward_account_required",request_id)
                        return
                    service=self.server._account_auth_service
                    if account_email_save:
                        data=self._json_body(_MAX_ACCOUNT_BODY)
                        credential_dir=os.environ.get("CREDENTIALS_DIRECTORY","")
                        key_path=Path(credential_dir)/"account-email-config-key"
                        result=service.save_email_settings(identity,data,key_path=key_path)
                    else:
                        if self.headers.get("Content-Length","0") not in {"0",""}:
                            raise ValueError("invalid_request_shape")
                        credential_dir=os.environ.get("CREDENTIALS_DIRECTORY","")
                        result=service.test_email_settings(identity,
                            key_path=Path(credential_dir)/"account-email-config-key",
                            public_origin=os.environ.get("RIVERVIEW_PUBLIC_ORIGIN","https://192.168.1.155"))
                    self._json(200,result,request_id)
                    return
                elif account_decision or account_user:
                    identity = getattr(self, "_account_identity", None)
                    if not identity:
                        self._error(403, "steward_account_required", request_id)
                        return
                    data = self._json_body(_MAX_ACCOUNT_BODY)
                    service = self.server._account_auth_service
                    if account_decision:
                        if set(data) != {"decision","role","grant_type"}:
                            raise ValueError("invalid_request_shape")
                        result = service.decide_enrollment(identity, account_decision.group(1),
                            data["decision"],role=data["role"],grant_type=data["grant_type"])
                    else:
                        account_id, action = account_user.groups()
                        if action == "disable":
                            if set(data) != {"disabled"}:
                                raise ValueError("invalid_request_shape")
                            result = service.set_account_state(identity, account_id, disabled=data["disabled"])
                        elif action == "roles":
                            if set(data) != {"role", "grant"}:
                                raise ValueError("invalid_request_shape")
                            result = service.change_role(identity, account_id, data["role"], grant=data["grant"])
                        elif action == "grant":
                            if set(data)!={"revoked"} or data["revoked"] is not True:
                                raise ValueError("grant_revocation_required")
                            result=service.revoke_access_grant(identity,account_id)
                        else:
                            if data:
                                raise ValueError("invalid_request_shape")
                            result = service.revoke_sessions(identity, account_id)
                    self._json(200, result, request_id)
                    return
                elif self._account_cookie_authenticated and self.command not in {"GET", "HEAD"}:
                    self.server._account_auth_service.require_role(
                        self._account_identity, "operator", "steward")
                    if not self._account_public_origin_ok():
                        self._error(403, "cross_origin_request_denied", request_id)
                        return
                if parsed.path == _CONVERSATION_SESSION and self.command == "POST":
                    service = self.server._conversation_service
                    if service is None:
                        self._error(503, "resident_conversation_unavailable", request_id)
                        return
                    if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Length", "0") != "0":
                        self._error(400, "conversation_session_body_not_allowed", request_id)
                        return
                    try:
                        account_identity = getattr(self, "_account_identity", None)
                        if account_identity is not None and "X-Riverview-Authority" not in self.headers:
                            from riverview_core.institutional_authority.grants import InstitutionalPrincipal
                            if ("steward" not in account_identity.get("roles", ())
                                    or not account_identity.get("authority_principal_id")):
                                self._error(403, "resident_conversation_not_authorized", request_id)
                                return
                            identity = service.authorize_browser_session(
                                InstitutionalPrincipal(account_identity["authority_principal_id"]))
                            self._json(200, {"schema_version":"rv.resident.conversation-session.v1",
                                             **identity, "transport":"authenticated_account_session"}, request_id)
                            return
                        credential = self.headers.get("X-Riverview-Authority", "")
                        if not _COOKIE_CREDENTIAL.fullmatch(credential):
                            self._error(403, "resident_conversation_not_authorized", request_id)
                            return
                        identity = service.authorize_browser_session(credential)
                    except Exception as exc:
                        self._conversation_error(exc, request_id)
                        return
                    cookie = self._conversation_cookie(credential)
                    self._json(200, {"schema_version":"rv.resident.conversation-session.v1",
                                     **identity, "expires_in_seconds":_CONVERSATION_COOKIE_MAX_AGE},
                               request_id, extra_headers=(("Set-Cookie", cookie),))
                elif parsed.path == _CONVERSATION_SESSION and self.command == "DELETE":
                    self._json(200, {"schema_version":"rv.resident.conversation-session.v1",
                                     "status":"disconnected"}, request_id,
                               extra_headers=(("Set-Cookie", self._conversation_cookie("", clear=True)),))
                elif parsed.path == "/api/v1/status":
                    status = self.server._projection.status()
                    if self.server._account_auth_service is not None:
                        status["account_auth"] = self.server._account_auth_service.status()
                    self._json(200, status, request_id)
                elif parsed.path == "/api/v1/assignments":
                    page = self.server._projection.assignments(
                        after=query.get("after", [None])[0],
                        limit=_bounded_limit(query.get("limit", [25])[0]))
                    self._json(200, page, request_id)
                elif parsed.path == "/api/v1/workers":
                    page = self.server._projection.workers(
                        after=query.get("after", [None])[0],
                        limit=_bounded_limit(query.get("limit", [25])[0]))
                    self._json(200, page, request_id)
                elif parsed.path == "/api/v1/events":
                    after_seq = query.get("after_seq", [None])[0]
                    before_seq = query.get("before_seq", [None])[0]
                    page = self.server._projection.events(after_seq=after_seq, before_seq=before_seq,
                                                          limit=_bounded_limit(query.get("limit", [25])[0]))
                    self._json(200, page, request_id)
                elif parsed.path == "/api/v1/attention":
                    page = self.server._projection.attention(limit=_bounded_limit(query.get("limit", [25])[0]))
                    self._json(200, page, request_id)
                elif parsed.path == "/api/v1/objectives" and self.command in {"GET", "HEAD"}:
                    self._json(200, self.server._projection.objectives(
                        limit=_bounded_limit(query.get("limit", [25])[0])), request_id)
                elif conversation_work_order:
                    # Only an explicit authenticated Steward action can promote a
                    # specific persisted Grace user message. Ordinary chat stays chat.
                    identity = getattr(self, "_account_identity", None)
                    service = self.server._conversation_service
                    pipeline = self.server._objective_pipeline
                    if (not getattr(self, "_account_cookie_authenticated", False)
                            or not identity or "steward" not in identity.get("roles", ())):
                        self._error(403, "steward_account_session_required", request_id)
                        return
                    if service is None or pipeline is None:
                        self._error(503, "work_order_intake_unavailable", request_id)
                        return
                    try:
                        data = self._json_body(_MAX_CHAT_BODY)
                        if set(data) != {"source_sequence", "acceptance_criteria"}:
                            raise ValueError("invalid work order shape")
                        sequence = data["source_sequence"]
                        criteria = data["acceptance_criteria"]
                        if (type(sequence) is not int or sequence < 1 or
                                not isinstance(criteria, list) or not criteria or len(criteria) > 20):
                            raise ValueError("invalid source sequence or criteria")
                        conversation_id = conversation_work_order.group(1)
                        principal_id = identity.get("authority_principal_id")
                        if not isinstance(principal_id, str) or not principal_id:
                            self._error(403, "institutional_principal_required", request_id)
                            return
                        # history() checks the exact resident.conversation.read grant and
                        # owner. The selected event must be a user-authored message from
                        # this same authenticated principal.
                        service.history(self._conversation_authority(), conversation_id)
                        with service.store.db.cursor() as cur:
                            service.store._path(cur)
                            cur.execute("""SELECT body,actor_kind,actor_id FROM
                                resident_conversation_events WHERE conversation_id=%s
                                AND sequence=%s AND event_type='user_message'""",
                                (conversation_id, sequence))
                            source = cur.fetchone()
                        if (source is None or source["actor_kind"] != "principal" or
                                source["actor_id"] != principal_id):
                            self._error(404, "conversation_message_not_found", request_id)
                            return
                        from uuid import uuid4
                        from riverview_core.institutional_authority.grants import InstitutionalPrincipal
                        objective_id = "objective:grace-conversation:" + str(uuid4())
                        origin = {"conversation_id": conversation_id,
                                  "source_sequence": sequence}
                        result = pipeline.submit_objective(
                            objective_id, source["body"], criteria,
                            scope_ref="work-order:engineering",
                            principal=InstitutionalPrincipal(principal_id), origin=origin)
                        grounded = pipeline.ground_objective(objective_id)
                        self._json(202, {"objective_id": objective_id,
                            "status": grounded["status"],
                            "source_revision": grounded["source_revision"]}, request_id)
                    except Exception as exc:
                        from riverview_core.resident_execution import ObjectiveNotAuthorized, ObjectiveStateError
                        from riverview_core.institutional_authority import GrantCheckUnavailable
                        from riverview_core.resident_execution.conversation import (
                            ConversationDenied, ConversationNotFound, ConversationUnavailable)
                        if isinstance(exc, ObjectiveNotAuthorized):
                            self._error(403, "engineering_work_order_submission_not_authorized", request_id)
                        elif isinstance(exc, ConversationDenied):
                            self._error(403, "resident_conversation_not_authorized", request_id)
                        elif isinstance(exc, ConversationNotFound):
                            self._error(404, "resident_conversation_not_found", request_id)
                        elif isinstance(exc, GrantCheckUnavailable):
                            self._error(503, "authority_unavailable", request_id)
                        elif isinstance(exc, ConversationUnavailable):
                            self._error(503, "resident_conversation_unavailable", request_id)
                        elif isinstance(exc, (ValueError, TypeError)):
                            self._error(400, "invalid_work_order_request", request_id)
                        elif isinstance(exc, ObjectiveStateError):
                            self._error(409, "work_order_conflict", request_id)
                        else:
                            self._error(503, "work_order_intake_unavailable", request_id)
                elif objective_submit:
                    pipeline = self.server._objective_pipeline
                    if pipeline is None:
                        self._error(503, "objective_intake_not_initialized", request_id)
                        return
                    if self.headers.get("Transfer-Encoding") or not self.headers.get("Content-Length", "").isdigit():
                        self._error(400, "objective_request_length_required", request_id)
                        return
                    length = int(self.headers["Content-Length"])
                    if not 1 <= length <= _MAX_OBJECTIVE_BODY:
                        self._error(413, "objective_request_too_large", request_id)
                        return
                    try:
                        data = json.loads(self.rfile.read(length))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        self._error(400, "invalid_objective_json", request_id)
                        return
                    if not isinstance(data, dict) or set(data) != {
                            "objective_id", "request", "acceptance_criteria", "scope_ref"}:
                        self._error(400, "invalid_objective_shape", request_id)
                        return
                    authority = self.headers.get("X-Riverview-Authority", "")
                    try:
                        pipeline.submit_objective(data["objective_id"], data["request"],
                            data["acceptance_criteria"], credential=authority,
                            scope_ref=data["scope_ref"])
                    except Exception as exc:
                        from riverview_core.resident_execution import ObjectiveNotAuthorized, ObjectiveStateError
                        if isinstance(exc, ObjectiveNotAuthorized):
                            self._error(403, "objective_submission_not_authorized", request_id)
                        elif isinstance(exc, (ValueError, TypeError)):
                            self._error(400, "invalid_objective", request_id)
                        elif isinstance(exc, ObjectiveStateError):
                            self._error(409, "objective_submission_conflict", request_id)
                        else:
                            self._error(503, "objective_submission_unavailable", request_id)
                        return
                    try:
                        result = pipeline.ground_objective(data["objective_id"])
                        self._json(202, {"objective_id": result["objective_id"],
                            "status": result["status"], "source_revision": result["source_revision"],
                            "source_sha256": result["source_sha256"]}, request_id)
                    except Exception:
                        result = pipeline.get_objective(data["objective_id"])
                        if result and result["status"] == "WAITING_FOR_EVIDENCE":
                            self._json(202, {"objective_id": result["objective_id"],
                                "status": result["status"], "evidence": {
                                    "status": result["evidence"].get("status"),
                                    "error_code": result["evidence"].get("error_code"),
                                    "source_references": result["evidence"].get("source_references", []),
                                    "source_revision": result["evidence"].get("source_revision"),
                                    "source_sha256": result["evidence"].get("source_sha256"),
                                    "retrieval_complete": result["evidence"].get("retrieval_complete")}}, request_id)
                        else:
                            self._error(503, "objective_grounding_unavailable", request_id)
                elif objective_proposal or objective_cancel:
                    pipeline = self.server._objective_pipeline
                    if pipeline is None:
                        self._error(503, "objective_intake_not_initialized", request_id)
                        return
                    if self.headers.get("Transfer-Encoding") or not self.headers.get("Content-Length", "").isdigit():
                        self._error(400, "objective_request_length_required", request_id)
                        return
                    length = int(self.headers["Content-Length"])
                    if not 1 <= length <= _MAX_OBJECTIVE_BODY:
                        self._error(413, "objective_request_too_large", request_id)
                        return
                    try:
                        data = json.loads(self.rfile.read(length))
                        if not isinstance(data, dict):
                            raise ValueError("object required")
                        objective_id = (objective_proposal or objective_cancel).group(1)
                        if objective_proposal:
                            from riverview_core.resident_reasoning import PlanProposal, PlanStep
                            if set(data) != {"summary", "steps", "tokens_used"} or not isinstance(data["steps"], list):
                                raise ValueError("invalid proposal shape")
                            steps = []
                            for step in data["steps"]:
                                if not isinstance(step, dict) or set(step) != {
                                        "step_id", "objective", "acceptance_criteria", "depends_on"}:
                                    raise ValueError("invalid proposal step")
                                steps.append(PlanStep(step["step_id"], step["objective"],
                                    tuple(step["acceptance_criteria"]), tuple(step["depends_on"])))
                            proposal = PlanProposal(data["summary"], tuple(steps), data["tokens_used"])
                            objective = pipeline.get_objective(objective_id)
                            if objective is None:
                                self._error(404, "objective_not_found", request_id)
                                return
                            with pipeline.ledger.db.transaction(), pipeline.ledger.db.cursor() as cur:
                                pipeline.ledger._set_search_path(cur)
                                actor = pipeline.authorizer.require(cur,
                                    self.headers.get("X-Riverview-Authority", ""),
                                    "assignment.create", objective["scope_ref"])
                            result = pipeline.record_proposal(objective_id, proposal,
                                                              actor_id=actor["principal_id"])
                            self._json(202, {"objective_id": objective_id,
                                "status": result["status"], "assignment_id": result["assignment_id"]}, request_id)
                        else:
                            if set(data) != {"scope_ref"}:
                                raise ValueError("invalid cancellation shape")
                            result = pipeline.cancel_work_order(objective_id,
                                credential=self.headers.get("X-Riverview-Authority", ""),
                                authority_ref=data["scope_ref"])
                            self._json(200, {"objective_id": objective_id,
                                "status": result["status"]}, request_id)
                    except Exception as exc:
                        from riverview_core.resident_execution import (
                            ObjectiveNotAuthorized, ObjectiveStateError)
                        from riverview_core.institutional_authority import GrantCheckUnavailable, GrantDenied
                        if isinstance(exc, (ObjectiveNotAuthorized, GrantDenied)):
                            self._error(403, "objective_action_not_authorized", request_id)
                        elif isinstance(exc, GrantCheckUnavailable):
                            self._error(503, "authority_unavailable", request_id)
                        elif isinstance(exc, (ValueError, TypeError, ObjectiveStateError)):
                            self._error(409 if isinstance(exc, ObjectiveStateError) else 400,
                                        "objective_transition_rejected", request_id)
                        else:
                            self._error(503, "objective_operation_unavailable", request_id)
                elif parsed.path == "/api/v1/notifications" and self.command in {"GET", "HEAD"}:
                    service = self.server._notification_service
                    page = (service.list_notifications(limit=min(50, _bounded_limit(query.get("limit", [25])[0])))
                            if service else {"schema_version": "rv.notifications.v1",
                                             "status": "not_initialized", "observed_at": None,
                                             "dispatcher": {"status": "not_initialized"},
                                             "items": [], "limit": 25})
                    self._json(200, page, request_id)
                elif parsed.path == "/api/v1/resident/conversations" and self.command in {"GET", "HEAD"}:
                    service = self.server._conversation_service
                    if service is None:
                        self._error(503, "resident_conversation_unavailable", request_id)
                        return
                    try:
                        result = service.list_conversations(self._conversation_authority())
                    except Exception as exc:
                        self._conversation_error(exc, request_id)
                        return
                    self._json(200, result, request_id)
                elif conversation_send:
                    service = self.server._conversation_service
                    if service is None:
                        self._error(503, "resident_conversation_unavailable", request_id)
                        return
                    if self.headers.get("Transfer-Encoding") or not self.headers.get("Content-Length", "").isdigit():
                        self._error(400, "conversation_request_length_required", request_id)
                        return
                    length = int(self.headers["Content-Length"])
                    if not 1 <= length <= _MAX_CHAT_BODY:
                        self._error(413, "conversation_request_too_large", request_id)
                        return
                    try:
                        data = json.loads(self.rfile.read(length))
                        if (not isinstance(data, dict)
                                or set(data) - {"conversation_id", "client_message_id", "message"}
                                or not isinstance(data.get("message"), str)):
                            raise ValueError("invalid conversation request")
                        result = service.send(
                            self._conversation_authority(),
                            message=data["message"], conversation_id=data.get("conversation_id"),
                            client_message_id=data.get("client_message_id"))
                        status = 201 if result.get("status") == "completed" else 503
                        self._json(status, result, request_id)
                    except Exception as exc:
                        self._conversation_error(exc, request_id)
                elif (conversation_match := _CONVERSATION_STATUS.fullmatch(parsed.path)):
                    service = self.server._conversation_service
                    if service is None:
                        self._error(503, "resident_conversation_unavailable", request_id)
                        return
                    try:
                        result = service.response_status(
                            self._conversation_authority(),
                            conversation_match.group(1), conversation_match.group(2))
                    except Exception as exc:
                        self._conversation_error(exc, request_id)
                        return
                    self._json(200, result, request_id)
                elif (conversation_match := _CONVERSATION_ID.fullmatch(parsed.path)):
                    service = self.server._conversation_service
                    if service is None:
                        self._error(503, "resident_conversation_unavailable", request_id)
                        return
                    try:
                        result = service.history(
                            self._conversation_authority(),
                            conversation_match.group(1))
                    except Exception as exc:
                        self._conversation_error(exc, request_id)
                        return
                    self._json(200, result, request_id)
                elif notification_write:
                    if (self.headers.get("Content-Length", "0") != "0" or
                            self.headers.get("Transfer-Encoding")):
                        self._error(400, "notification_receipt_body_not_allowed", request_id)
                        return
                    service = self.server._notification_service
                    if service is None:
                        self._error(503, "notifications_not_initialized", request_id)
                        return
                    notice_id, action = notification_write.groups()
                    result = (service.confirm_delivery(notice_id) if action == "delivered"
                              else service.acknowledge_receipt(notice_id))
                    self._json(200, result, request_id)
                elif parsed.path == "/api/v1/snapshot":
                    self._json(200, self.server._projection.snapshot(), request_id)
                elif parsed.path == "/api/v1/graphs":
                    root = Path(__file__).resolve().parents[3] / "process_graphs"
                    items = []
                    for graph_path in sorted(root.glob("*/*.json")):
                        if graph_path.parent.name in {"generated", "schema"} or graph_path.is_symlink():
                            continue
                        try:
                            graph = json.loads(graph_path.read_text(encoding="utf-8"))
                        except (OSError, UnicodeError, json.JSONDecodeError):
                            continue
                        if isinstance(graph, dict) and isinstance(graph.get("graph_id"), str):
                            items.append({"graph_id": graph["graph_id"],
                                          "component_id": graph.get("component_id"),
                                          "workflow_id": graph.get("workflow_id"),
                                          "graph_revision": graph.get("graph_revision"),
                                          "node_count": len(graph.get("nodes", [])),
                                          "edge_count": len(graph.get("edges", []))})
                    self._json(200, {"schema_version": "rv.dashboard.graph-index.v1",
                                     "status": "available", "items": items}, request_id)
                elif parsed.path.startswith("/api/v1/graphs/"):
                    graph_id = unquote(parsed.path.removeprefix("/api/v1/graphs/"), errors="strict")
                    root = Path(__file__).resolve().parents[3] / "process_graphs"
                    selected = None
                    for graph_path in root.glob("*/*.json"):
                        if graph_path.parent.name in {"generated", "schema"} or graph_path.is_symlink():
                            continue
                        try:
                            graph = json.loads(graph_path.read_text(encoding="utf-8"))
                        except (OSError, UnicodeError, json.JSONDecodeError):
                            continue
                        if isinstance(graph, dict) and graph.get("graph_id") == graph_id:
                            selected = graph
                            break
                    if selected is None:
                        self._error(404, "process_graph_not_found", request_id)
                        return
                    position_reader = getattr(self.server._projection,
                                              "graph_execution_position", None)
                    selected["execution_position"] = (position_reader(graph_id)
                        if callable(position_reader) else {
                            "status": "unknown",
                            "reason": "The active projection does not expose recorded graph-node identity.",
                        })
                    self._json(200, {"schema_version": "rv.dashboard.graph.v1",
                                     "status": "available", "graph": selected}, request_id)
                elif parsed.path.startswith("/api/v1/assignments/"):
                    assignment_id = unquote(parsed.path.removeprefix("/api/v1/assignments/"), errors="strict")
                    result = self.server._projection.assignment_detail(assignment_id)
                    self._json(200, result, request_id) if result else self._error(404, "assignment_not_found", request_id)
                elif (match := _OBJECTIVE_DETAIL.fullmatch(parsed.path)) and self.command in {"GET", "HEAD"}:
                    rows = self.server._projection.objectives(
                        limit=1, objective_id=match.group(1)).get("items", [])
                    item = next((entry for entry in rows if entry["objective_id"] == match.group(1)), None)
                    self._json(200, item, request_id) if item else self._error(404, "objective_not_found", request_id)
                else:
                    self._error(404, "not_found", request_id)
            except ValueError:
                self._error(400, "invalid_query", request_id)
            except ProjectionUnavailable:
                self._error(503, "projection_unavailable", request_id)
            except Exception as exc:
                from riverview_core.account_auth import AuthDenied, AuthUnavailable
                if isinstance(exc, AuthDenied):
                    self._error(403, "not_authorized", request_id)
                    return
                if isinstance(exc, AuthUnavailable):
                    self._error(503, "account_auth_unavailable", request_id)
                    return
                from riverview_core.notifications import (NotificationConflict,
                    NotificationNotFound, NotificationUnavailable)
                if isinstance(exc, NotificationNotFound):
                    self._error(404, "notification_not_found", request_id)
                    return
                if isinstance(exc, NotificationConflict):
                    self._error(409, "notification_receipt_conflict", request_id)
                    return
                if isinstance(exc, NotificationUnavailable):
                    self._error(503, "notifications_unavailable", request_id)
                    return
                # Error class is logged; exception text may contain driver details and is excluded.
                print(json.dumps({"event": "dashboard_request_failed", "request_id": request_id,
                                  "error_type": type(exc).__name__}), flush=True)
                self._error(500, "projection_failed", request_id)

        def _account_error(self, exc, request_id):
            from riverview_core.account_auth import (
                AccountAuthError, AuthDenied, AuthUnavailable, ChallengeInvalid,
                EmailTransportUnavailable)
            if isinstance(exc, AuthDenied):
                self._error(403, "not_authorized", request_id)
            elif isinstance(exc, ChallengeInvalid):
                self._error(400, "challenge_invalid_or_expired", request_id)
            elif isinstance(exc, EmailTransportUnavailable):
                self._error(503, "email_delivery_unavailable", request_id)
            elif isinstance(exc, AuthUnavailable):
                self._error(503, "account_auth_unavailable", request_id)
            elif isinstance(exc, AccountAuthError):
                self._error(503, exc.code, request_id)
            elif isinstance(exc, (ValueError, TypeError)):
                self._error(400, "invalid_account_request", request_id)
            else:
                self._error(503, "account_auth_unavailable", request_id)

        def _conversation_error(self, exc, request_id):
            from riverview_core.resident_execution.conversation import (
                ConversationContextTooLarge, ConversationDenied,
                ConversationNotFound, ConversationUnavailable)
            if isinstance(exc, ConversationDenied):
                self._error(403, "resident_conversation_not_authorized", request_id)
            elif isinstance(exc, ConversationNotFound):
                self._error(404, "resident_conversation_not_found", request_id)
            elif isinstance(exc, ConversationContextTooLarge):
                self._error(413, "resident_context_too_large", request_id)
            elif isinstance(exc, ValueError):
                self._error(400, "invalid_conversation_request", request_id)
            elif isinstance(exc, ConversationUnavailable):
                self._error(503, "resident_conversation_unavailable", request_id)
            else:
                self._error(503, "resident_conversation_failed", request_id)

    return Handler


class DashboardHTTPServer(_BoundedHTTPServer):
    """Validated loopback listener with a mandatory owner-only bearer credential."""

    def __init__(self, host: str, port: int, token_file: str | Path,
                 projection: DashboardProjection, static_dir: str | Path | None = None,
                 notification_service=None, objective_pipeline=None,
                 conversation_service=None, account_auth_service=None):
        if host not in {"127.0.0.1", "::1"}:
            raise ValueError("dashboard bind host must be a loopback IP literal")
        if not isinstance(port, int) or not 8700 <= port <= 8799:
            raise ValueError("dashboard port must be reserved in 8700-8799")
        credential = _read_token(token_file)
        if static_dir is None:
            static_dir = Path(__file__).with_name("static")
        super().__init__((host, port), make_handler(), token=credential,
                         projection=projection, notification_service=notification_service,
                         objective_pipeline=objective_pipeline,
                         conversation_service=conversation_service,
                         account_auth_service=account_auth_service,
                         static_dir=static_dir)


def _release_commit() -> str:
    release_root = Path(__file__).resolve().parents[3]
    return release_root.name if re.fullmatch(r"[0-9a-f]{40,64}", release_root.name) else "unknown"


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
        source_commit=os.environ.get("RIVERVIEW_SOURCE_COMMIT", _release_commit()),
        deployment_id=os.environ.get("RIVERVIEW_DEPLOYMENT_ID", "unconfigured"),
        heartbeat_stale_seconds=int(os.environ.get("RIVERVIEW_STALE_AFTER_SECONDS", "30")))
    from riverview_core.notifications import NotificationService
    from riverview_core.account_auth import (
        AccountAuthService, DisabledEmailTransport, FileDevelopmentEmailTransport)
    from riverview_core.email_delivery import ConfiguredEmailTransport
    notification_service = NotificationService(
        dsn, schema=os.environ.get("RIVERVIEW_DATABASE_SCHEMA", "riverview_dev"))
    from riverview_core.assignment_intake import AuthorizedAssignmentIntake
    from riverview_core.institutional_authority import ExactGrantAuthorizer
    from riverview_core.postgres_ledger import PostgresLedger
    from riverview_core.resident_execution import GraceExecutionPipeline
    from riverview_core.worker_adapter.knowledge import UnavailableKnowledgeProvider
    from riverview_core.worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider
    import psycopg
    email_transport = DisabledEmailTransport()
    if os.environ.get("RIVERVIEW_EMAIL_DEVELOPMENT_MAILBOX"):
        email_transport = FileDevelopmentEmailTransport(
            os.environ["RIVERVIEW_EMAIL_DEVELOPMENT_MAILBOX"])
    else:
        credential_directory=os.environ.get("CREDENTIALS_DIRECTORY","")
        config_key=Path(credential_directory)/"account-email-config-key"
        if credential_directory and config_key.is_file():
            email_transport=ConfiguredEmailTransport(
                lambda:psycopg.connect(dsn,connect_timeout=2),
                schema=os.environ.get("RIVERVIEW_ACCOUNT_SCHEMA","riverview_accounts"),
                key_path=config_key,
                public_origin=os.environ.get("RIVERVIEW_PUBLIC_ORIGIN","https://192.168.1.155"))
    account_auth_service = AccountAuthService(
        lambda: psycopg.connect(dsn, connect_timeout=2), email_transport,
        schema=os.environ.get("RIVERVIEW_ACCOUNT_SCHEMA", "riverview_accounts"),
        public_origin=os.environ.get("RIVERVIEW_PUBLIC_ORIGIN","https://192.168.1.155"))
    repository_root = Path(os.environ.get("RIVERVIEW_KNOWLEDGE_ROOT", "/opt/riverview-core"))
    pinned_commit = os.environ.get("RIVERVIEW_SOURCE_COMMIT", _release_commit())
    objective_ledger = None
    objective_pipeline = None
    conversation_service = None
    conversation_store = None
    authority_registry = None
    schema = os.environ.get("RIVERVIEW_DATABASE_SCHEMA", "riverview_dev")
    try:
        with psycopg.connect(dsn, connect_timeout=2) as probe, probe.cursor() as cur:
            cur.execute("SELECT to_regclass(%s) IS NOT NULL AS present",
                        (f"{schema}.grace_objectives",))
            objective_schema_present = cur.fetchone()[0]
        if objective_schema_present:
            try:
                knowledge = TaskRelevantRepositoryKnowledgeProvider(repository_root, pinned_commit)
            except (OSError, ValueError, RuntimeError):
                knowledge = UnavailableKnowledgeProvider()
            objective_ledger = PostgresLedger(dsn, schema=schema)
            objective_authorizer = ExactGrantAuthorizer(
                os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority"))
            objective_pipeline = GraceExecutionPipeline(objective_ledger, objective_authorizer,
                AuthorizedAssignmentIntake(objective_ledger, objective_authorizer), knowledge)
    except psycopg.Error:
        objective_pipeline = None
    resident_token_path = Path(os.environ.get("CREDENTIALS_DIRECTORY", "")) / "resident-token"
    chat_office_id = os.environ.get("RIVERVIEW_GRACE_OFFICE_ID", "")
    chat_endpoint = os.environ.get("RIVERVIEW_GRACE_MODEL_ENDPOINT", "")
    chat_model = os.environ.get("RIVERVIEW_GRACE_MODEL_ID", "")
    chat_model_sha = os.environ.get("RIVERVIEW_GRACE_MODEL_SHA256", "")
    if chat_office_id and chat_endpoint and chat_model and chat_model_sha and resident_token_path.is_file():
        try:
            from riverview_core.institutional_authority import AuthorityRegistry, ExactGrantAuthorizer
            from riverview_core.local_reasoning_provider import LocalReasoningProvider
            from riverview_core.resident_execution.conversation import (
                ConversationStore, ResidentConversationService)
            authority_schema = os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority")
            authority_registry = AuthorityRegistry(dsn, schema=authority_schema, runtime_safe=True)
            conversation_store = ConversationStore(dsn, schema=schema)
            resident_token = resident_token_path.read_text(encoding="ascii").strip()
            provider = LocalReasoningProvider(chat_endpoint, chat_model, chat_model_sha,
                timeout_seconds=25,
                chat_prefix=os.environ.get("RIVERVIEW_GRACE_CHAT_PREFIX", ""))
            conversation_service = ResidentConversationService(
                store=conversation_store, registry=authority_registry,
                authorizer=ExactGrantAuthorizer(authority_schema), office_id=chat_office_id,
                resident_credential=resident_token,
                providers={provider.provider_id: provider})
            conversation_store.recover_pending()
        except Exception as exc:
            print(json.dumps({"event": "resident_conversation_start_failed",
                              "error_type": type(exc).__name__}), flush=True)
            if conversation_store is not None:
                conversation_store.close()
                conversation_store = None
            if authority_registry is not None:
                authority_registry.close()
                authority_registry = None
            conversation_service = None
    host = os.environ.get("RIVERVIEW_DASHBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("RIVERVIEW_DASHBOARD_PORT", "8766"))
    server = DashboardHTTPServer(host, port, token_path, projection,
                                 notification_service=notification_service,
                                 objective_pipeline=objective_pipeline,
                                 conversation_service=conversation_service,
                                 account_auth_service=account_auth_service)
    print(json.dumps({"event": "dashboard_started", "host": host, "port": port,
                      "source_commit": projection.source_commit,
                      "deployment_id": projection.deployment_id}), flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        if objective_ledger is not None:
            objective_ledger.close()
        if conversation_store is not None:
            conversation_store.close()
        if authority_registry is not None:
            authority_registry.close()


if __name__ == "__main__":
    main()
