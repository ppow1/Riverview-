# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/server.py
# Component: STEWARD-DASHBOARD
# Revision: 1.3.34
# Changed: 2026-10-21 UTC | RV-W4-GRACE-OPTIONAL-CRITERIA-20261021 | Permit normal Grace derivation when work-order criteria are omitted.
# Changed: 2026-10-21 UTC | RV-GRACE-DASHBOARD-KNOWLEDGE-PIN-001 | Separate knowledge source commit from dashboard code identity.
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Accept typed artifact contracts in authenticated proposal submission
# Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Preserve production behavior while integrating the authenticated bounded re-review caller.
# Changed: 2026-10-19 UTC | RV-C1-PR152-SCOPE-PROVENANCE-001 | Enforce Steward/global or exact account-owned conversation scope for objective projections
# Changed: 2026-10-19 UTC | RV-GRACE-REREVIEW-OPERATOR-CALLER-001 | Add authenticated exact-objective rereview request route through the existing pipeline.
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Accept typed repository target provenance in source-change proposal intake.
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Filter durable Engineering progress by authenticated conversation origin
# Purpose: Serve account-authenticated operational, proposal, capability and snapshot APIs
# Execution Model: Request-driven, independent of CME assignment execution
# Observability: Structured request IDs, HTTP health/error codes, PostgreSQL projection
# Dependencies: Python 3.10+; standard library; status_dashboard.projection
# Authority: Dashboard credential protects views; objective API also requires exact objective.submit grant
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Add capability registry and canonical workflow inventory APIs while preserving PR #65 proposal routes
# Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Route authenticated current-runtime Comms5 proposal/status operations through the existing service layer.
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Attach the isolated durable exchange adapter to the existing authenticated Comms5 internal operation route.
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
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Preserve separately authorized per-step source paths and test targets in typed dashboard proposals
# Changed: 2026-10-13 UTC | RV-LEDGER-GRAPH-POSITION | Read live execution position only from persisted canonical ledger identity
# Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RETRY-003 | Reuse immutable same-origin objective criteria on authorized retries
# Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RETRY-003 | Return a distinct safe code for conflicting objective origins
# Changed: 2026-10-13 UTC | RV-GRACE-OCTO-PRIVATE-LAN-PROVIDER | Permit only explicit allowlisted OCTO1 model URLs when an opt-in service flag is set
# Changed: 2026-10-13 UTC | RV-GRACE-MULTISTAGE-ROUTING-001 | Add opt-in readiness router and deferred-turn resumption loop
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Fail startup closed unless deferred compatibility and claim migrations are ready
# Changed: 2026-10-13 UTC | RV-GRACE-ROUTER-ACL-READINESS-001 | Check resident migration and authorized active binding without reading the protected authority ledger
# Changed: 2026-10-13 UTC | RV-GRACE-TO-ENGINEERING-DENIALS | Preserve conversation authorization and unavailable distinctions at promotion boundary
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Expose only the scoped verification endpoint for local bootstrap challenges
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-TOOLBOX-001 | Inject existing read-only dashboard projections into Grace's request context
# Changed: 2026-10-14 UTC | RV-RESIDENT-PERMISSIONS-001 | Add authenticated Steward resident profile registry routes
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_status_dashboard.py
# History: Git and revision/backup manifest
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Persist bounded streaming, reconnect, and terminal provenance.
# Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RECOVERY-001 | Ground against the active immutable release and make conversation intake recoverable/idempotent.
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Add authenticated revision decisions, explicit conversational commands, and existing-pipeline promotion API
# Changed: 2026-10-17 UTC | RV-GRACE-COMMS5-CHAT-WIRING | Attach the existing internal Comms5 read tools to the dashboard Grace router
# Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Add authenticated live GPU and inference status projection.
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
import time
from uuid import NAMESPACE_URL, UUID, uuid5
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from psycopg import sql

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
_OBJECTIVE_REREVIEW = re.compile(r"^/api/v1/objectives/(objective:[A-Za-z0-9._:-]{1,120})/result-rereview$")
_CONVERSATION_ID = re.compile(r"^/api/v1/resident/conversations/([0-9a-fA-F-]{36})$")
_CONVERSATION_SESSION = "/api/v1/resident/conversation-session"
_CONVERSATION_COOKIE = "rv_grace_authority"
_CONVERSATION_COOKIE_MAX_AGE = 30 * 24 * 60 * 60
_COOKIE_CREDENTIAL = re.compile(r"^[A-Za-z0-9_-]{32,512}$")
_CONVERSATION_STATUS = re.compile(
    r"^/api/v1/resident/conversations/([0-9a-fA-F-]{36})/responses/([0-9a-fA-F-]{36})$")
_CONVERSATION_STREAM = re.compile(
    r"^/api/v1/resident/conversations/([0-9a-fA-F-]{36})/responses/([0-9a-fA-F-]{36})/stream$")
_CONVERSATION_WORK_ORDER = re.compile(
    r"^/api/v1/resident/conversations/([0-9a-fA-F-]{36})/work-orders$")
_PROPOSAL_COLLECTION = "/api/v1/institutional-proposals"
_PROPOSAL_ITEM = re.compile(r"^/api/v1/institutional-proposals/(proposal:[0-9a-f-]{36})$")
_PROPOSAL_DECISION = re.compile(r"^/api/v1/institutional-proposals/(proposal:[0-9a-f-]{36})/decision$")
_PROPOSAL_WORK_ORDERS = re.compile(r"^/api/v1/institutional-proposals/(proposal:[0-9a-f-]{36})/work-orders$")
_PROPOSAL_COMMAND = "/api/v1/institutional-proposals/conversational-command"
_COMMS5_OPERATION = "/api/v1/internal/comms5/operation"


class WorkOrderOriginConflict(Exception):
    """A selected conversation source is already bound to a different objective."""


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
_RESIDENT_PERMISSION_PATH = re.compile(r"^/api/v1/resident-permissions/([^/]+)/(approve|revoke)$")
_RESIDENT_PERMISSION_PROFILE = re.compile(r"^/api/v1/resident-permissions/([^/]+)$")
_INSTITUTIONAL_PRINCIPAL_ID = re.compile(r"^[A-Za-z0-9:._-]{1,256}$")

def _bounded_limit(value):
    try:
        return min(_MAX_PAGE, max(1, int(value)))
    except (TypeError, ValueError):
        return 25


def _build_grace_model_router(*, autonomic, vision, reasoning, internal_tools=None):
    """Build the same Grace router with its bounded internal operations surface."""
    from riverview_core.resident_execution.internal_tools import GraceInternalTools
    from riverview_core.resident_execution.model_router import GraceModelRouter
    tools = GraceInternalTools() if internal_tools is None else internal_tools
    return GraceModelRouter(autonomic=autonomic, vision=vision, reasoning=reasoning,
                            internal_tools=tools)


def _verify_grace_router_startup_readiness(connection, *, schema, registry,
                                           resident_credential, office_id, router):
    """Verify runtime-readable conversation state and the effective authority binding.

    The dashboard role can read its own resident-execution migration ledger but
    intentionally cannot inspect the authority schema ledger. Authority
    readiness is therefore established through the existing, exact-grant
    SECURITY DEFINER office-state API, including the active router binding.
    The protected authority migration itself is checksum-verified by the
    deployment runner before activation, never by granting runtime ledger access.
    """
    if (not isinstance(schema, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", schema)
            or not office_id or not resident_credential):
        raise ValueError("invalid Grace router readiness identity")
    with connection.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT version FROM {}.schema_migrations WHERE version=ANY(%s)").format(
                sql.Identifier(schema)),
            (["0004_deferred_conversation_responses",
              "0006_deferred_execution_claims",
              "0008_resident_conversation_stream_delivery"],))
        rows = cur.fetchall()
        versions = {row["version"] if hasattr(row, "keys") else row[0]
                    for row in rows}
        if versions != {
                "0004_deferred_conversation_responses",
                "0006_deferred_execution_claims",
                "0008_resident_conversation_stream_delivery"}:
            raise RuntimeError("resident deferred-resumption migrations are not applied")
        cur.execute("""SELECT to_regclass(%s) AS table_name,
            has_table_privilege(current_user,%s,'SELECT') AS can_select,
            has_table_privilege(current_user,%s,'INSERT') AS can_insert,
            has_table_privilege(current_user,%s,'UPDATE') AS can_update""",
            tuple([schema+".resident_conversation_streams"]*4))
        capability=cur.fetchone()
        if hasattr(capability,"keys"):
            values=(capability["table_name"],capability["can_select"],
                    capability["can_insert"],capability["can_update"])
        else:
            values=tuple(capability) if capability else ()
        if not values or not values[0] or not all(bool(v) for v in values[1:]):
            raise RuntimeError("resident streaming database capability is not ready")

    binding = registry.authorize_office_state(resident_credential, office_id)
    if (not isinstance(binding, dict)
            or binding.get("implementation_kind") != "model"
            or binding.get("provider_ref") != router.provider_id
            or binding.get("implementation_revision") != router.model_sha256):
        raise RuntimeError("authorized Grace router binding is not ready")
    # Exercise the narrowly granted decision API without accepting a
    # predecessor relationship. A missing function privilege/API fails startup.
    registry.is_authorized_implementation_successor(
        resident_credential, office_id,
        predecessor_id=binding["implementation_id"],
        predecessor_revision=binding["implementation_revision"],
        successor_id=binding["implementation_id"],
        successor_revision=binding["implementation_revision"],
        required_capability="grace.reasoning.80b")
    return binding


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
                 objective_pipeline, conversation_service, account_auth_service,
                 permission_store, static_dir, proposal_registry,
                 steward_review_exchange=None, resource_telemetry=None):
        self._token = token
        self._projection = projection
        self._notification_service = notification_service
        self._objective_pipeline = objective_pipeline
        self._conversation_service = conversation_service
        self._account_auth_service = account_auth_service
        self._permission_store = permission_store
        self._proposal_registry = proposal_registry
        self._proposal_lifecycle = None
        if proposal_registry is not None and objective_pipeline is not None:
            from riverview_core.resident_execution.proposal_lifecycle import ProposalLifecycle
            self._proposal_lifecycle = ProposalLifecycle(proposal_registry, objective_pipeline)
        self._comms5_operations = None
        if proposal_registry is not None or steward_review_exchange is not None:
            from riverview_core.resident_execution.comms5_operations import Comms5Operations
            from riverview_core.resident_execution.external_reasoning_mcp import StewardReviewBridge
            self._comms5_operations = Comms5Operations(
                proposal_registry, self._proposal_lifecycle, objective_pipeline,
                steward_review_bridge=(StewardReviewBridge(steward_review_exchange)
                    if steward_review_exchange is not None else None))
        self._static_dir = Path(static_dir)
        self._resource_telemetry = resource_telemetry
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
        protocol_version = "HTTP/1.1"
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

        def _stream_sse(self, service, conversation_id, response_id, after_sequence,
                        request_id):
            """Replay durable, authorized stream events with bounded SSE framing."""
            self.send_response(200)
            self._headers(request_id)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            def write(payload):
                chunk=f"{len(payload):X}\r\n".encode()+payload+b"\r\n"
                self.wfile.write(chunk)
                self.wfile.flush()

            cursor=after_sequence
            deadline=time.monotonic()+180
            last_heartbeat=time.monotonic()
            try:
                write(b": riverview stream connected\n\n")
                while time.monotonic()<deadline:
                    snapshot=service.stream_snapshot(self._conversation_authority(),
                        conversation_id,response_id,after_sequence=cursor)
                    for item in snapshot["events"]:
                        cursor=item["sequence"]
                        payload=json.dumps(item,separators=(",",":"),ensure_ascii=True).encode()
                        write(b"id: "+str(cursor).encode()+b"\nevent: "+item["event_type"].encode()+
                              b"\ndata: "+payload+b"\n\n")
                    if snapshot["status"] in {"completed","failed","interrupted"}:
                        break
                    now=time.monotonic()
                    if now-last_heartbeat>=10:
                        write(b": keepalive\n\n")
                        last_heartbeat=now
                    time.sleep(0.35)
                if time.monotonic()>=deadline:
                    write(b"event: reconnect\ndata: {\"status\":\"pending\"}\n\n")
            except (BrokenPipeError, ConnectionResetError, OSError):
                # Generation is independent of the browser socket and continues durably.
                return
            except Exception:
                # A grant revoked after headers were sent closes the stream; the
                # next reconnect receives a normal authenticated denial response.
                return
            finally:
                try:
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                except OSError:
                    pass

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

        def _objective_account_identity(self):
            """Resolve an account session for sensitive objective projections.

            The dashboard bearer authenticates the general API but carries no
            account role. When a browser sends that bearer and its account
            cookie together, validate the cookie independently for this route.
            """
            if self._account_cookie_authenticated and self._account_identity:
                return self._account_identity
            service = self.server._account_auth_service
            raw_cookie = self.headers.get("Cookie", "")
            if service is None or len(raw_cookie) > 8192:
                return None
            values = []
            for item in raw_cookie.split(";"):
                key, sep, value = item.strip().partition("=")
                if sep and key == _ACCOUNT_SESSION_COOKIE:
                    values.append(value)
            if len(values) != 1:
                return None
            from riverview_core.account_auth import AuthDenied
            try:
                return service.authenticate(values[0],
                    csrf_token=self.headers.get("X-Riverview-CSRF"),
                    state_changing=False)
            except AuthDenied:
                return None

        def _authorize_objective_conversation(self, identity, conversation_id):
            """Apply the existing conversation read grant and owner check."""
            from riverview_core.institutional_authority.grants import InstitutionalPrincipal
            from riverview_core.resident_execution.conversation import (
                ConversationDenied, ConversationNotFound, ConversationUnavailable)
            service = self.server._conversation_service
            if service is None:
                raise ConversationUnavailable("conversation ownership check unavailable")
            principal_id = identity.get("authority_principal_id")
            if not isinstance(principal_id, str) or not principal_id.strip():
                raise ConversationDenied("account has no institutional principal")
            try:
                service.history(InstitutionalPrincipal(principal_id), conversation_id)
            except (ConversationDenied, ConversationNotFound, ConversationUnavailable):
                raise
            except Exception as exc:
                raise ConversationUnavailable("conversation ownership check unavailable") from exc

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
            objective_rereview = (_OBJECTIVE_REREVIEW.fullmatch(parsed.path)
                                  if self.command == "POST" else None)
            account_decision = (_ACCOUNT_ENROLLMENT_DECISION.fullmatch(parsed.path)
                                if self.command == "POST" else None)
            account_user = (_ACCOUNT_USER_PATH.fullmatch(parsed.path)
                            if self.command == "POST" else None)
            public_auth = parsed.path in _PUBLIC_AUTH_POSTS and self.command == "POST"
            auth_logout = parsed.path == "/api/v1/auth/session" and self.command == "DELETE"
            account_queue = parsed.path == "/api/v1/account/enrollments" and self.command == "GET"
            account_users = parsed.path == "/api/v1/account/users" and self.command == "GET"
            permission_list = parsed.path == "/api/v1/resident-permissions" and self.command == "GET"
            permission_profile = (_RESIDENT_PERMISSION_PROFILE.fullmatch(parsed.path)
                                  if self.command == "PUT" else None)
            permission_transition = (_RESIDENT_PERMISSION_PATH.fullmatch(parsed.path)
                                     if self.command == "POST" else None)
            account_email_settings = parsed.path == "/api/v1/account/email-settings" and self.command == "GET"
            account_email_save = parsed.path == "/api/v1/account/email-settings" and self.command == "PUT"
            account_email_test = parsed.path == "/api/v1/account/email-settings/test" and self.command == "POST"
            conversation_send = (parsed.path == "/api/v1/resident/conversations"
                                 and self.command == "POST")
            conversation_stream_send = (parsed.path == "/api/v1/resident/conversations/stream"
                                        and self.command == "POST")
            conversation_work_order = (_CONVERSATION_WORK_ORDER.fullmatch(parsed.path)
                                       if self.command == "POST" else None)
            proposal_create = (parsed.path == _PROPOSAL_COLLECTION and self.command == "POST")
            proposal_search = (parsed.path == _PROPOSAL_COLLECTION and self.command in {"GET", "HEAD"})
            proposal_item = (_PROPOSAL_ITEM.fullmatch(parsed.path)
                             if self.command in {"GET", "HEAD"} else None)
            proposal_revision = (_PROPOSAL_ITEM.fullmatch(parsed.path)
                                 if self.command == "PUT" else None)
            proposal_decision = (_PROPOSAL_DECISION.fullmatch(parsed.path)
                                 if self.command == "POST" else None)
            proposal_work_orders = (_PROPOSAL_WORK_ORDERS.fullmatch(parsed.path)
                                    if self.command == "POST" else None)
            proposal_command = (parsed.path == _PROPOSAL_COMMAND and self.command == "POST")
            comms5_operation = parsed.path == _COMMS5_OPERATION and self.command == "POST"
            conversation_session = (parsed.path == _CONVERSATION_SESSION
                                     and self.command in {"POST", "DELETE"})
            if not self._host_ok():
                self._error(400, "invalid_host", request_id)
                return
            if (self.command not in {"GET", "HEAD"} and not notification_write
                    and not objective_submit and not objective_proposal and not objective_cancel
                    and not objective_rereview
                    and not conversation_send and not conversation_stream_send and not conversation_session and not public_auth
                    and not conversation_work_order and not proposal_create
                    and not proposal_revision and not proposal_decision
                    and not proposal_work_orders and not proposal_command
                    and not comms5_operation
                    and not auth_logout and not account_decision and not account_user
                    and not permission_profile and not permission_transition
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
            if parsed.path in {"/assets/app.js", "/assets/app.css", "/assets/workflow.js", "/assets/resident-permissions.js", "/assets/diagnostic-snapshot.js",
                               "/assets/institutional-proposals.js"}:
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
                if comms5_operation:
                    if (self.headers.get("X-Riverview-Comms5") != "1"
                            or self.headers.get("X-Riverview-Comms5-Principal") != "steward"):
                        self._error(403, "comms5_transport_attestation_required", request_id)
                        return
                    if self.server._comms5_operations is None:
                        self._error(503, "comms5_operations_unavailable", request_id)
                        return
                    data = self._json_body(_MAX_CHAT_BODY)
                    if (set(data) != {"tool", "arguments"}
                            or not isinstance(data["tool"], str)
                            or not isinstance(data["arguments"], dict)):
                        self._error(400, "invalid_comms5_operation", request_id)
                        return
                    try:
                        result = self.server._comms5_operations.execute(
                            data["tool"], data["arguments"], principal_id="steward:camrui")
                        self._json(200, result, request_id)
                    except PermissionError:
                        self._error(403, "comms5_operation_not_authorized", request_id)
                    except Exception as exc:
                        from riverview_core.resident_execution.proposals import (
                            ProposalConflict, ProposalNotFound, ProposalValidationError)
                        from riverview_core.resident_execution.pipeline import ObjectiveNotAuthorized
                        from riverview_core.resident_execution.comms5_operations import Comms5OperationNotFound
                        from riverview_core.resident_execution.external_reasoning import (
                            ExchangeConflict, ExchangeNotFound, ExchangeUnauthorized)
                        if isinstance(exc, ProposalNotFound):
                            self._error(404, "proposal_not_found", request_id)
                        elif isinstance(exc, Comms5OperationNotFound):
                            self._error(404, "objective_not_found", request_id)
                        elif isinstance(exc, ExchangeNotFound):
                            self._error(404, "reasoning_exchange_not_found", request_id)
                        elif isinstance(exc, ExchangeUnauthorized):
                            self._error(403, "reasoning_exchange_not_authorized", request_id)
                        elif isinstance(exc, ExchangeConflict):
                            self._error(409, "reasoning_exchange_conflict", request_id)
                        elif isinstance(exc, ObjectiveNotAuthorized):
                            self._error(403, "objective_submission_not_authorized", request_id)
                        elif isinstance(exc, ProposalConflict):
                            self._error(409, "proposal_lifecycle_conflict", request_id)
                        elif isinstance(exc, (ValueError, TypeError, ProposalValidationError)):
                            self._error(400, "invalid_comms5_operation", request_id)
                        else:
                            self._error(503, "comms5_operation_unavailable", request_id)
                    return
                elif parsed.path == "/api/v1/auth/session" and self.command in {"GET", "HEAD"}:
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
                elif permission_list or permission_profile or permission_transition:
                    identity = getattr(self, "_account_identity", None)
                    if (not identity or "steward" not in identity.get("roles", ())
                            or not identity.get("authority_principal_id")):
                        self._error(403, "steward_account_required", request_id)
                        return
                    store = self.server._permission_store
                    if store is None:
                        self._error(503, "resident_permission_registry_unavailable", request_id)
                        return
                    if self.command != "GET" and not self._account_public_origin_ok():
                        self._error(403, "cross_origin_request_denied", request_id)
                        return
                    if permission_list:
                        result = store.list_profiles(identity["authority_principal_id"])
                    elif permission_profile:
                        data = self._json_body(_MAX_ACCOUNT_BODY)
                        if (set(data) != {"expected_revision", "profile"} or
                                not isinstance(data["expected_revision"], int) or
                                isinstance(data["expected_revision"], bool) or
                                data["expected_revision"] < 0):
                            raise ValueError("invalid_permission_profile_request")
                        resident_id = unquote(permission_profile.group(1), errors="strict")
                        if not _INSTITUTIONAL_PRINCIPAL_ID.fullmatch(resident_id):
                            raise ValueError("invalid_permission_profile_request")
                        ResidentPermissionStore._validate_profile(data["profile"])
                        result = store.save_profile(identity["authority_principal_id"],
                            resident_id, data["expected_revision"], data["profile"])
                    else:
                        data = self._json_body(_MAX_ACCOUNT_BODY)
                        if (set(data) != {"expected_revision"} or
                                not isinstance(data["expected_revision"], int) or
                                isinstance(data["expected_revision"], bool) or
                                data["expected_revision"] < 0):
                            raise ValueError("invalid_permission_profile_request")
                        method = (store.approve_profile if permission_transition.group(2) == "approve"
                                  else store.revoke_profile)
                        resident_id = unquote(permission_transition.group(1), errors="strict")
                        if not _INSTITUTIONAL_PRINCIPAL_ID.fullmatch(resident_id):
                            raise ValueError("invalid_permission_profile_request")
                        result = method(identity["authority_principal_id"],
                                        resident_id,
                                        data["expected_revision"])
                    self._json(200, result, request_id)
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
                elif parsed.path == "/api/v1/resources/telemetry":
                    if self.command not in {"GET", "HEAD"}:
                        self._error(405, "method_not_allowed", request_id)
                    elif self.server._resource_telemetry is None:
                        self._json(200, {
                            "schema_version": "rv.dashboard.resource-telemetry.v1",
                            "component_id": "STEWARD-DASHBOARD-RESOURCE-TELEMETRY",
                            "status": "unavailable", "observed_at": None,
                            "freshness_window_seconds": 30,
                            "collection_model": "request_driven_no_cache",
                            "hosts": [], "error_code": "telemetry_not_configured",
                        }, request_id)
                    else:
                        self._json(200, self.server._resource_telemetry.read(), request_id)
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
                    if (set(query) - {"limit", "conversation_id"} or
                            any(len(values) != 1 for values in query.values())):
                        self._error(400, "invalid_query", request_id)
                        return
                    conversation_id = query.get("conversation_id", [None])[0]
                    if conversation_id is not None:
                        conversation_id = str(UUID(conversation_id))
                    try:
                        identity = self._objective_account_identity()
                    except Exception:
                        self._error(503, "account_auth_unavailable", request_id)
                        return
                    if not identity:
                        self._error(403, "account_session_required", request_id)
                        return
                    roles = identity.get("roles", ())
                    is_steward = isinstance(roles, (list, tuple, set)) and "steward" in roles
                    owner_principal_id = None
                    progress_only = conversation_id is not None
                    if not is_steward:
                        owner_principal_id = identity.get("authority_principal_id")
                        if (not conversation_id or not isinstance(owner_principal_id, str)
                                or not owner_principal_id.strip()):
                            self._error(403, "steward_or_owned_conversation_required", request_id)
                            return
                        try:
                            self._authorize_objective_conversation(identity, conversation_id)
                        except Exception as exc:
                            from riverview_core.resident_execution.conversation import (
                                ConversationDenied, ConversationNotFound, ConversationUnavailable)
                            if isinstance(exc, ConversationDenied):
                                self._error(403, "conversation_read_not_authorized", request_id)
                            elif isinstance(exc, ConversationNotFound):
                                self._error(404, "conversation_not_found", request_id)
                            elif isinstance(exc, ConversationUnavailable):
                                self._error(503, "conversation_owner_check_unavailable", request_id)
                            else:
                                self._error(503, "conversation_owner_check_unavailable", request_id)
                            return
                    self._json(200, self.server._projection.objectives(
                        limit=_bounded_limit(query.get("limit", [25])[0]),
                        conversation_id=conversation_id,
                        owner_principal_id=owner_principal_id,
                        progress_only=progress_only), request_id)
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
                        if set(data) not in ({"source_sequence"}, {"source_sequence", "acceptance_criteria"}):
                            raise ValueError("invalid work order shape")
                        sequence = data["source_sequence"]
                        criteria = data.get("acceptance_criteria", [])
                        if (type(sequence) is not int or sequence < 1 or
                                not isinstance(criteria, list) or len(criteria) > 20 or
                                any(not isinstance(item, str) or not item.strip() or len(item) > 1000
                                    for item in criteria)):
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
                        from riverview_core.institutional_authority.grants import InstitutionalPrincipal
                        origin = {"conversation_id": conversation_id,
                                  "source_sequence": sequence}
                        from riverview_core.resident_execution import ObjectiveStateError
                        existing = _find_conversation_objective(
                            pipeline, conversation_id, sequence)
                        if existing is not None:
                            # The first receipt is durable even when grounding is
                            # unavailable. A same-origin retry resumes that exact
                            # objective; its accepted criteria are immutable. The
                            # current form may be empty or differently normalized,
                            # so retries retain the original criteria instead of
                            # treating a second submission as a new objective.
                            if (existing.get("scope_ref") != "work-order:engineering"
                                    or existing.get("submitter_id") != principal_id
                                    or existing.get("request", "").strip() != source["body"].strip()):
                                raise WorkOrderOriginConflict(
                                    "conversation source conflicts with its recorded objective")
                            pipeline.authorize_objective_submission(
                                principal_id, "work-order:engineering")
                            grounded = (_ground_conversation_objective(pipeline, existing["objective_id"])
                                if existing["status"] in {"RECEIVED", "WAITING_FOR_EVIDENCE"}
                                else existing)
                            reused_existing = True
                        else:
                            # Deterministic origin identity closes the concurrent
                            # double-submit race without a new migration or grant.
                            suffix = uuid5(NAMESPACE_URL,
                                f"riverview:grace-conversation-objective:{conversation_id}:{sequence}")
                            objective_id = "objective:grace-conversation:" + str(suffix)
                            try:
                                accepted = pipeline.submit_objective(
                                    objective_id, source["body"], criteria,
                                    scope_ref="work-order:engineering",
                                    principal=InstitutionalPrincipal(principal_id), origin=origin,
                                    criteria_source=("steward_supplied" if criteria else "grace_derived"))
                            except ObjectiveStateError:
                                # A simultaneous request may have committed the
                                # same deterministic ID while this request waited.
                                existing = _find_conversation_objective(
                                    pipeline, conversation_id, sequence)
                                if existing is None:
                                    raise WorkOrderOriginConflict(
                                        "conversation source conflicts with its recorded objective")
                                if (existing.get("scope_ref") != "work-order:engineering"
                                        or existing.get("submitter_id") != principal_id
                                        or existing.get("request", "").strip() != source["body"].strip()):
                                    raise
                                pipeline.authorize_objective_submission(
                                    principal_id, "work-order:engineering")
                                accepted = existing
                                reused_existing = True
                            else:
                                reused_existing = False
                            grounded = _ground_conversation_objective(
                                pipeline, accepted["objective_id"])
                        self._json(202, _conversation_objective_response(
                            grounded, reused_existing=reused_existing), request_id)
                    except Exception as exc:
                        from riverview_core.resident_execution import ObjectiveNotAuthorized, ObjectiveStateError
                        from riverview_core.institutional_authority import GrantCheckUnavailable
                        from riverview_core.resident_execution.conversation import (
                            ConversationDenied, ConversationNotFound, ConversationUnavailable)
                        if isinstance(exc, ObjectiveNotAuthorized):
                            self._error(403, "engineering_work_order_submission_not_authorized", request_id)
                        elif isinstance(exc, WorkOrderOriginConflict):
                            self._error(409, "work_order_origin_conflict", request_id)
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
                elif (proposal_create or proposal_search or proposal_item or proposal_revision
                      or proposal_decision or proposal_work_orders or proposal_command):
                    identity = getattr(self, "_account_identity", None)
                    if (not getattr(self, "_account_cookie_authenticated", False)
                            or not identity or "steward" not in identity.get("roles", ())
                            or not identity.get("authority_principal_id")):
                        self._error(403, "steward_account_session_required", request_id)
                        return
                    registry = self.server._proposal_registry
                    if registry is None:
                        self._error(503, "institutional_proposal_registry_unavailable", request_id)
                        return
                    lifecycle = self.server._proposal_lifecycle
                    if proposal_decision or proposal_work_orders or proposal_command:
                        if lifecycle is None:
                            self._error(503, "proposal_work_order_lifecycle_unavailable", request_id)
                            return
                        try:
                            principal_id = identity["authority_principal_id"]
                            data = self._json_body(_MAX_CHAT_BODY)
                            if proposal_decision:
                                allowed = {"revision", "decision", "reason", "idempotency_key",
                                           "content_sha256", "approved_purpose", "accepted_conditions"}
                                if (set(data) - allowed or not {"revision", "decision", "reason",
                                        "idempotency_key", "content_sha256"} <= set(data)
                                        or type(data["revision"]) is not int
                                        or not isinstance(data["idempotency_key"], str)):
                                    raise ValueError("invalid proposal decision request")
                                if ((data["decision"] == "APPROVE") !=
                                        (isinstance(data.get("approved_purpose"), str)
                                         and bool(data["approved_purpose"].strip()))):
                                    raise ValueError("approval requires a purpose; other decisions do not take one")
                                result = lifecycle.decide(unquote(proposal_decision.group(1)),
                                    data["revision"], decision=data["decision"], actor_id=principal_id,
                                    reason=data["reason"], idempotency_key=data["idempotency_key"],
                                    content_sha256=data["content_sha256"],
                                    approved_purpose=data.get("approved_purpose"),
                                    accepted_conditions=data.get("accepted_conditions", []),
                                    authority_reference=(f"account-auth-session:{identity['account_id']}:steward"))
                                self._json(200, result, request_id)
                            elif proposal_work_orders:
                                if set(data) != {"revision"} or type(data["revision"]) is not int:
                                    raise ValueError("invalid proposal promotion request")
                                result = lifecycle.promote(unquote(proposal_work_orders.group(1)),
                                    data["revision"], actor_id=principal_id)
                                self._json(202, result, request_id)
                            else:
                                if set(data) != {"conversation_id", "source_sequence"}:
                                    raise ValueError("invalid proposal conversational command request")
                                conversation_id = data["conversation_id"]
                                sequence = data["source_sequence"]
                                if (not isinstance(conversation_id, str)
                                        or not re.fullmatch(r"[0-9a-fA-F-]{36}", conversation_id)
                                        or type(sequence) is not int or sequence < 1):
                                    raise ValueError("invalid conversational command source")
                                service = self.server._conversation_service
                                if service is None:
                                    self._error(503, "resident_conversation_unavailable", request_id)
                                    return
                                service.history(self._conversation_authority(), conversation_id)
                                with service.store.db.cursor() as cur:
                                    service.store._path(cur)
                                    cur.execute("""SELECT body,actor_kind,actor_id FROM resident_conversation_events
                                        WHERE conversation_id=%s AND sequence=%s AND event_type='user_message'""",
                                        (conversation_id, sequence))
                                    source = cur.fetchone()
                                if (source is None or source["actor_kind"] != "principal"
                                        or source["actor_id"] != principal_id):
                                    self._error(404, "conversation_message_not_found", request_id)
                                    return
                                from riverview_core.resident_execution.proposal_lifecycle import parse_steward_command
                                parsed_command = parse_steward_command(source["body"])
                                if parsed_command and parsed_command["action"] == "decision":
                                    pid = parsed_command["proposal_id"]
                                    revision = parsed_command["revision"]
                                    idem = f"conversation-proposal-decision:{conversation_id}:{sequence}"
                                    current_content = registry.get(pid, revision=revision)["revision"]
                                    result = lifecycle.decide(pid, revision,
                                        decision=parsed_command["decision"],
                                        actor_id=principal_id,
                                        reason=(parsed_command["reason"] +
                                            f"; source {conversation_id}:{sequence}"),
                                        idempotency_key=idem,
                                        content_sha256=current_content["content_sha256"],
                                        approved_purpose=parsed_command.get("approved_purpose"),
                                        authority_reference=(f"account-auth-session:{identity['account_id']}:steward"))
                                    self._json(200, {"status": "proposal_decision_recorded", "result": result}, request_id)
                                elif parsed_command and parsed_command["action"] == "promote":
                                    result = lifecycle.promote(parsed_command["proposal_id"],
                                        parsed_command["revision"], actor_id=principal_id)
                                    self._json(202, {"status": "work_order_intake", "result": result}, request_id)
                                else:
                                    self._json(200, {"status": "no_authorization_action",
                                        "message": "Use an explicit proposal ID, revision, and purpose; conversational agreement is not authorization."}, request_id)
                        except Exception as exc:
                            from riverview_core.resident_execution.proposals import (
                                ProposalConflict, ProposalNotFound, ProposalValidationError)
                            from riverview_core.resident_execution.pipeline import (
                                ObjectiveNotAuthorized, ObjectiveStateError)
                            if isinstance(exc, PermissionError):
                                self._error(403, "steward_authority_required", request_id)
                            elif isinstance(exc, ProposalNotFound):
                                self._error(404, "proposal_not_found", request_id)
                            elif isinstance(exc, (ProposalConflict, ObjectiveStateError)):
                                self._error(409, "proposal_lifecycle_conflict", request_id)
                            elif isinstance(exc, ObjectiveNotAuthorized):
                                self._error(403, "objective_submission_not_authorized", request_id)
                            elif isinstance(exc, (ValueError, TypeError, ProposalValidationError)):
                                self._error(400, "invalid_proposal_lifecycle_request", request_id)
                            else:
                                self._error(503, "proposal_lifecycle_unavailable", request_id)
                        return
                    if proposal_search:
                        try:
                            result = registry.search(query.get("q", [""])[0],
                                status=query.get("status", [None])[0],
                                tag=query.get("tag", [None])[0],
                                limit=_bounded_limit(query.get("limit", [25])[0]))
                            self._json(200, result, request_id)
                        except Exception as exc:
                            from riverview_core.resident_execution.proposals import ProposalValidationError
                            if isinstance(exc, ProposalValidationError):
                                self._error(400, "invalid_proposal_search", request_id)
                            else:
                                self._error(503, "institutional_proposal_registry_unavailable", request_id)
                        return
                    if proposal_item:
                        try:
                            proposal_id = unquote(proposal_item.group(1))
                            revision_values = query.get("revision", [])
                            if len(revision_values) > 1:
                                raise ValueError("proposal revision query is ambiguous")
                            revision = None
                            if revision_values:
                                if not re.fullmatch(r"[1-9][0-9]{0,5}", revision_values[0]):
                                    raise ValueError("invalid proposal revision")
                                revision = int(revision_values[0])
                            result = registry.get(proposal_id, revision=revision)
                            if lifecycle is not None:
                                result = lifecycle.status(proposal_id,
                                    result["revision"]["revision"])
                            self._json(200, result, request_id)
                        except Exception as exc:
                            from riverview_core.resident_execution.proposals import ProposalNotFound
                            if isinstance(exc, ProposalNotFound):
                                self._error(404, "proposal_not_found", request_id)
                            elif isinstance(exc, (ValueError, TypeError)):
                                self._error(400, "invalid_proposal_revision_query", request_id)
                            else:
                                self._error(503, "institutional_proposal_registry_unavailable", request_id)
                        return
                    if proposal_revision:
                        try:
                            data = self._json_body(_MAX_CHAT_BODY)
                            if (set(data) != {"expected_revision", "content"}
                                    or type(data["expected_revision"]) is not int
                                    or data["expected_revision"] < 1):
                                raise ValueError("invalid proposal revision request")
                            revised = registry.revise(unquote(proposal_revision.group(1)),
                                data["expected_revision"], data["content"],
                                actor_id=identity["authority_principal_id"])
                            self._json(200, revised, request_id)
                        except Exception as exc:
                            from riverview_core.resident_execution.proposals import (
                                ProposalConflict, ProposalNotFound, ProposalValidationError)
                            if isinstance(exc, ProposalNotFound):
                                self._error(404, "proposal_not_found", request_id)
                            elif isinstance(exc, ProposalConflict):
                                self._error(409, "proposal_revision_conflict", request_id)
                            elif isinstance(exc, (ValueError, TypeError, ProposalValidationError)):
                                self._error(400, "invalid_proposal_revision", request_id)
                            else:
                                self._error(503, "institutional_proposal_registry_unavailable", request_id)
                        return
                    service = self.server._conversation_service
                    if service is None:
                        self._error(503, "resident_conversation_unavailable", request_id)
                        return
                    try:
                        data = self._json_body(_MAX_CHAT_BODY)
                        if (set(data) - {"conversation_id", "source_sequences", "instruction", "idempotency_key"}
                                or not {"conversation_id", "source_sequences", "idempotency_key"} <= set(data)
                                or not isinstance(data["conversation_id"], str)
                                or not re.fullmatch(r"[0-9a-fA-F-]{36}", data["conversation_id"])
                                or not isinstance(data["source_sequences"], list)
                                or not isinstance(data["idempotency_key"], str)):
                            raise ValueError("invalid proposal draft request")
                        principal_id = identity["authority_principal_id"]
                        existing = registry.get_by_idempotency_key(
                            data["idempotency_key"], created_by=principal_id)
                        expected_sources = sorted(data["source_sequences"])
                        if existing is not None:
                            provenance = existing["revision"]["provenance"]
                            refs = existing["revision"]["source_references"]
                            if (provenance.get("source_conversation_id") != data["conversation_id"]
                                    or provenance.get("source_sequences") != expected_sources
                                    or not refs):
                                self._error(409, "proposal_idempotency_conflict", request_id)
                            else:
                                self._json(200, {"status": "draft_saved", **existing}, request_id)
                            return
                        from riverview_core.institutional_authority.grants import InstitutionalPrincipal
                        draft = service.draft_institutional_proposal(
                            InstitutionalPrincipal(principal_id), data["conversation_id"],
                            data["source_sequences"],
                            instruction=data.get("instruction", "Formalize the selected discussion"))
                        if draft["status"] == "clarification_required":
                            self._json(200, draft, request_id)
                            return
                        provenance = {**draft["reasoning"],
                            "source_conversation_id": data["conversation_id"],
                            "source_sequences": expected_sources,
                            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                        saved = self.server._comms5_operations.create_draft_record(
                            draft["content"], actor_id=principal_id,
                            origin_kind="grace_conversation",
                            source_references=draft["source_references"], provenance=provenance,
                            idempotency_key=data["idempotency_key"])
                        self._json(201, {"status": "draft_saved", **saved}, request_id)
                    except Exception as exc:
                        from riverview_core.resident_execution.conversation import (
                            ConversationDenied, ConversationNotFound, ConversationUnavailable)
                        from riverview_core.resident_execution.proposals import (
                            ProposalConflict, ProposalError, ProposalValidationError)
                        if isinstance(exc, ConversationDenied):
                            self._error(403, "resident_conversation_not_authorized", request_id)
                        elif isinstance(exc, ConversationNotFound):
                            self._error(404, "resident_conversation_not_found", request_id)
                        elif isinstance(exc, ProposalConflict):
                            self._error(409, "proposal_idempotency_conflict", request_id)
                        elif isinstance(exc, (ValueError, TypeError, ProposalValidationError)):
                            self._error(400, "invalid_proposal_draft_request", request_id)
                        elif isinstance(exc, (ConversationUnavailable, ProposalError)):
                            self._error(503, "proposal_drafting_unavailable", request_id)
                        else:
                            self._error(503, "institutional_proposal_registry_unavailable", request_id)
                    return
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
                elif objective_rereview:
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
                        required = {"completion_cycle", "evidence_revision", "evidence", "idempotency_key"}
                        if not isinstance(data, dict) or set(data) != required:
                            raise ValueError("invalid review request shape")
                        result = pipeline.request_conversation_result_rereview(
                            objective_rereview.group(1), data["completion_cycle"],
                            evidence_revision=data["evidence_revision"], evidence=data["evidence"],
                            credential=self.headers.get("X-Riverview-Authority", ""),
                            idempotency_key=data["idempotency_key"])
                        self._json(202, {"schema_version": "rv.grace.result-review-request.v1",
                            "status": "reused" if result["reused"] else "requested",
                            "objective_id": objective_rereview.group(1), **result}, request_id)
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
                        self._error(400, "invalid_objective_review_request", request_id)
                    except Exception as exc:
                        from riverview_core.resident_execution import ObjectiveNotAuthorized, ObjectiveStateError
                        from riverview_core.institutional_authority import GrantCheckUnavailable, GrantDenied
                        if isinstance(exc, (ObjectiveNotAuthorized, GrantDenied)):
                            self._error(403, "objective_review_not_authorized", request_id)
                        elif isinstance(exc, GrantCheckUnavailable):
                            self._error(503, "authority_unavailable", request_id)
                        elif isinstance(exc, ObjectiveStateError):
                            self._error(409, "objective_review_rejected", request_id)
                        else:
                            self._error(503, "objective_review_unavailable", request_id)
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
                            from riverview_core.resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep
                            if set(data) != {"summary", "steps", "tokens_used"} or not isinstance(data["steps"], list):
                                raise ValueError("invalid proposal shape")
                            steps = []
                            for step in data["steps"]:
                                required = {"step_id", "objective", "acceptance_criteria", "depends_on"}
                                allowed = required | {"execution_capability", "authorized_paths", "test_targets",
                                                     "repository_reference", "repository_revision",
                                                     "artifact_requirements"}
                                if (not isinstance(step, dict) or not required <= set(step) or
                                        not set(step) <= allowed):
                                    raise ValueError("invalid proposal step")
                                artifact_requirements = tuple(ArtifactRequirement(
                                    item["name"], item["path"], item["media_type"],
                                    tuple(item["acceptance_criteria"]), item.get("max_bytes", 32768))
                                    for item in step.get("artifact_requirements", []))
                                steps.append(PlanStep(step["step_id"], step["objective"],
                                    tuple(step["acceptance_criteria"]), tuple(step["depends_on"]),
                                    step.get("execution_capability",
                                        "engineering.codex-cli-artifact.v1"),
                                    tuple(step.get("authorized_paths", ())),
                                    tuple(step.get("test_targets", ())),
                                    step.get("repository_reference"),
                                    step.get("repository_revision"), artifact_requirements))
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
                        status = (201 if result.get("status") == "completed" else
                                  202 if result.get("status") == "deferred" else 503)
                        self._json(status, result, request_id)
                    except Exception as exc:
                        self._conversation_error(exc, request_id)
                elif conversation_stream_send:
                    service=self.server._conversation_service
                    if service is None:
                        self._error(503,"resident_conversation_unavailable",request_id)
                        return
                    try:
                        data=self._json_body(_MAX_CHAT_BODY)
                        if (set(data)-{"conversation_id","client_message_id","message"}
                                or not isinstance(data.get("message"),str)):
                            raise ValueError("invalid conversation request")
                        result=service.submit_stream(self._conversation_authority(),
                            message=data["message"],conversation_id=data.get("conversation_id"),
                            client_message_id=data.get("client_message_id"))
                        self._json(202,result,request_id)
                    except Exception as exc:
                        self._conversation_error(exc,request_id)
                elif (stream_match := _CONVERSATION_STREAM.fullmatch(parsed.path)):
                    service=self.server._conversation_service
                    if service is None:
                        self._error(503,"resident_conversation_unavailable",request_id)
                        return
                    try:
                        after=query.get("after",["0"])[0]
                        if not after.isdigit() or len(after)>12:
                            raise ValueError("invalid stream cursor")
                        service.stream_snapshot(self._conversation_authority(),
                            stream_match.group(1),stream_match.group(2),after_sequence=int(after))
                        self._stream_sse(service,stream_match.group(1),stream_match.group(2),
                                         int(after),request_id)
                    except Exception as exc:
                        self._conversation_error(exc,request_id)
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
                elif parsed.path == "/api/v1/capabilities":
                    capability_path = self.server._static_dir / "capabilities.json"
                    if capability_path.is_symlink() or not capability_path.is_file():
                        self._error(503, "capability_registry_unavailable", request_id)
                        return
                    try:
                        registry = json.loads(capability_path.read_text(encoding="utf-8"))
                        self._json(200, registry, request_id)
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        self._error(503, "capability_registry_unavailable", request_id)
                elif parsed.path == "/api/v1/snapshot/workflow-index":
                    root = Path(__file__).resolve().parents[3] / "process_graphs"
                    items, errors = [], []
                    for graph_path in sorted(root.glob("*/*.json")):
                        if graph_path.parent.name in {"generated", "schema"}:
                            continue
                        relative = graph_path.relative_to(root.parent).as_posix()
                        if graph_path.is_symlink() or not graph_path.is_file():
                            errors.append({"source_file": relative, "code": "canonical_file_not_regular"})
                            continue
                        try:
                            graph = json.loads(graph_path.read_text(encoding="utf-8"))
                        except (OSError, UnicodeError, json.JSONDecodeError):
                            errors.append({"source_file": relative, "code": "canonical_file_unreadable"})
                            continue
                        if not isinstance(graph, dict) or not isinstance(graph.get("graph_id"), str):
                            errors.append({"source_file": relative, "code": "canonical_definition_invalid"})
                            continue
                        items.append({"graph_id": graph["graph_id"],
                                      "component_id": graph.get("component_id"),
                                      "workflow_id": graph.get("workflow_id"),
                                      "graph_revision": graph.get("graph_revision"),
                                      "source_file": relative,
                                      "node_count": len(graph.get("nodes", [])),
                                      "edge_count": len(graph.get("edges", []))})
                    self._json(200, {"schema_version": "rv.website.workflow-index.v1",
                                     "status": "available" if not errors else "partial",
                                     "inventory_count": len(items), "items": items,
                                     "errors": errors}, request_id)
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
                    if query:
                        self._error(400, "invalid_query", request_id)
                        return
                    try:
                        identity = self._objective_account_identity()
                    except Exception:
                        self._error(503, "account_auth_unavailable", request_id)
                        return
                    if not identity:
                        self._error(403, "account_session_required", request_id)
                        return
                    roles = identity.get("roles", ())
                    is_steward = isinstance(roles, (list, tuple, set)) and "steward" in roles
                    owner_principal_id = None if is_steward else identity.get("authority_principal_id")
                    if not is_steward and (not isinstance(owner_principal_id, str)
                                           or not owner_principal_id.strip()):
                        self._error(403, "steward_or_owned_conversation_required", request_id)
                        return
                    rows = self.server._projection.objectives(limit=1,
                        objective_id=match.group(1), owner_principal_id=owner_principal_id,
                        progress_only=not is_steward).get("items", [])
                    item = next((entry for entry in rows if entry["objective_id"] == match.group(1)), None)
                    if item is not None and not is_steward:
                        conversation_id = (item.get("origin") or {}).get("conversation_id")
                        if not conversation_id:
                            item = None
                        else:
                            try:
                                self._authorize_objective_conversation(identity, conversation_id)
                            except Exception as exc:
                                from riverview_core.resident_execution.conversation import (
                                    ConversationDenied, ConversationNotFound, ConversationUnavailable)
                                if isinstance(exc, (ConversationDenied, ConversationNotFound)):
                                    item = None
                                elif isinstance(exc, ConversationUnavailable):
                                    self._error(503, "conversation_owner_check_unavailable", request_id)
                                    return
                                else:
                                    self._error(503, "conversation_owner_check_unavailable", request_id)
                                    return
                    self._json(200, item, request_id) if item else self._error(404, "objective_not_found", request_id)
                else:
                    self._error(404, "not_found", request_id)
            except ValueError:
                self._error(400, "invalid_query", request_id)
            except ProjectionUnavailable:
                self._error(503, "projection_unavailable", request_id)
            except Exception as exc:
                from riverview_core.account_auth import AuthDenied, AuthUnavailable
                if isinstance(exc, PermissionError):
                    self._error(403, "resident_permission_change_not_authorized", request_id)
                    return
                if isinstance(exc, RuntimeError) and str(exc) == "permission_profile_revision_conflict":
                    self._error(409, "resident_permission_revision_conflict", request_id)
                    return
                if isinstance(exc, RuntimeError) and str(exc).startswith("resident_permission_registry_unavailable"):
                    self._error(503, "resident_permission_registry_unavailable", request_id)
                    return
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
                 conversation_service=None, account_auth_service=None,
                 permission_store=None, proposal_registry=None,
                 steward_review_exchange=None, resource_telemetry=None):
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
                         permission_store=permission_store,
                         static_dir=static_dir, proposal_registry=proposal_registry,
                         steward_review_exchange=steward_review_exchange,
                         resource_telemetry=resource_telemetry)


def _release_commit() -> str:
    release_root = _release_root()
    return release_root.name if re.fullmatch(r"[0-9a-f]{40,64}", release_root.name) else "unknown"


def _release_root() -> Path:
    """Return the immutable package root that owns this loaded dashboard module."""
    return Path(__file__).resolve().parents[3]


def _knowledge_root(*, release_root=None, configured=None) -> Path:
    """Use an explicit knowledge root or this package's verified release files.

    The legacy shared core symlink can lag the dashboard release. In a packaged
    dashboard, the module's own release contains the matching SOURCE_COMMIT and
    PACKAGE_SHA256SUMS used by RepositoryKnowledgeProvider. Development checkouts
    without those package markers retain the legacy default.
    """
    explicit = os.environ.get("RIVERVIEW_KNOWLEDGE_ROOT") if configured is None else configured
    if explicit:
        return Path(explicit)
    root = Path(release_root) if release_root is not None else _release_root()
    if (root / "SOURCE_COMMIT").is_file() and (root / "PACKAGE_SHA256SUMS").is_file():
        return root
    return Path("/opt/riverview-core")


def _knowledge_commit(*, configured=None, dashboard_source_commit=None, release_commit=None) -> str:
    """Resolve the knowledge pin independently from dashboard code provenance."""
    if configured is None:
        configured = os.environ.get("RIVERVIEW_KNOWLEDGE_COMMIT")
    if configured:
        return configured
    if dashboard_source_commit is None:
        dashboard_source_commit = os.environ.get("RIVERVIEW_SOURCE_COMMIT")
    if dashboard_source_commit:
        return dashboard_source_commit
    return _release_commit() if release_commit is None else release_commit


def _find_conversation_objective(pipeline, conversation_id, source_sequence):
    """Find the durable objective already bound to one authenticated source message."""
    with pipeline.ledger.db.cursor() as cur:
        pipeline.ledger._set_search_path(cur)
        cur.execute("""SELECT DISTINCT objective_id FROM grace_objective_events
            WHERE event_type='objective.received'
              AND payload->'origin'->>'conversation_id'=%s
              AND payload->'origin'->>'source_sequence'=%s
            ORDER BY objective_id""", (conversation_id, str(source_sequence)))
        rows = cur.fetchall()
    if len(rows) > 1:
        raise WorkOrderOriginConflict("conversation source already has conflicting objectives")
    return pipeline.get_objective(rows[0]["objective_id"]) if rows else None


def _ground_conversation_objective(pipeline, objective_id):
    """Return durable wait/progress state after grounding, without mislabeling it conflict."""
    from riverview_core.resident_execution import ObjectiveStateError
    try:
        return pipeline.ground_objective(objective_id)
    except ObjectiveStateError:
        current = pipeline.get_objective(objective_id)
        if current and current.get("status") in {
                "WAITING_FOR_EVIDENCE", "GROUNDED", "PROPOSED",
                "WORK_ORDER_CREATED", "COMPLETED"}:
            return current
        raise


def _conversation_objective_response(objective, *, reused_existing=False):
    """Build a bounded intake receipt that never returns request or evidence content."""
    result = {"objective_id": objective["objective_id"], "status": objective["status"]}
    result["reused_existing_objective"] = bool(reused_existing)
    result["acceptance_criteria_source"] = objective.get(
        "acceptance_criteria_source", "steward_supplied" if objective.get("acceptance_criteria")
        else "grace_derived")
    result["acceptance_criteria"] = list(objective.get("acceptance_criteria", ()))
    if objective.get("source_revision"):
        result["source_revision"] = objective["source_revision"]
    if objective["status"] == "WAITING_FOR_EVIDENCE":
        evidence = objective.get("evidence") or {}
        result["evidence"] = {key: evidence.get(key) for key in (
            "status", "error_code", "source_references", "source_revision",
            "source_sha256", "retrieval_complete")}
    return result


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
    from riverview_core.status_dashboard.resource_telemetry import DashboardResourceTelemetry
    resource_telemetry = DashboardResourceTelemetry()
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
    from riverview_core.institutional_authority.permission_profiles import ResidentPermissionStore
    permission_store = ResidentPermissionStore(
        lambda: psycopg.connect(dsn, connect_timeout=2),
        schema=os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority"))
    repository_root = _knowledge_root()
    pinned_commit = _knowledge_commit()
    objective_ledger = None
    steward_review_ledger = None
    steward_review_exchange = None
    objective_pipeline = None
    conversation_service = None
    conversation_store = None
    authority_registry = None
    proposal_registry = None
    schema = os.environ.get("RIVERVIEW_DATABASE_SCHEMA", "riverview_dev")
    try:
        with psycopg.connect(dsn, connect_timeout=2) as proposal_probe, proposal_probe.cursor() as cur:
            cur.execute("SELECT to_regclass(%s) IS NOT NULL", (f"{schema}.institutional_proposals",))
            if cur.fetchone()[0]:
                from riverview_core.resident_execution.proposals import ProposalRegistry
                proposal_registry = ProposalRegistry(dsn, schema=schema)
    except Exception as exc:
        print(json.dumps({"event": "institutional_proposal_registry_unavailable",
                          "error_type": type(exc).__name__}), flush=True)
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
    try:
        with psycopg.connect(dsn, connect_timeout=2) as exchange_probe, exchange_probe.cursor() as cur:
            cur.execute("SELECT to_regclass(%s) IS NOT NULL AND to_regclass(%s) IS NOT NULL",
                (f"{schema}.external_reasoning_exchanges",
                 f"{schema}.external_reasoning_exchange_events"))
            exchange_schema_present = cur.fetchone()[0]
        if exchange_schema_present:
            from riverview_core.reasoning_escalation import ReasoningEscalationRouter
            from riverview_core.resident_execution.external_reasoning import DurableExternalReasoningExchange
            from riverview_core.postgres_ledger import PostgresLedger
            steward_review_ledger = PostgresLedger(dsn, schema=schema)
            # Steward operations derive the provider route from each durable row;
            # this router is intentionally empty and creates no provider identity.
            steward_review_exchange = DurableExternalReasoningExchange(
                steward_review_ledger, ReasoningEscalationRouter({}),
                actor_id="comms5:steward-review")
    except Exception as exc:
        if steward_review_ledger is not None:
            steward_review_ledger.close()
            steward_review_ledger = None
        steward_review_exchange = None
        print(json.dumps({"event": "comms5_steward_review_exchange_unavailable",
                          "error_type": type(exc).__name__}), flush=True)
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
            from riverview_core.resident_execution.operational_context import GraceOperationalContext
            authority_schema = os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority")
            authority_registry = AuthorityRegistry(dsn, schema=authority_schema, runtime_safe=True)
            conversation_store = ConversationStore(dsn, schema=schema)
            resident_token = resident_token_path.read_text(encoding="ascii").strip()
            provider = LocalReasoningProvider(chat_endpoint, chat_model, chat_model_sha,
                timeout_seconds=25,
                chat_prefix=os.environ.get("RIVERVIEW_GRACE_CHAT_PREFIX", ""),
                allow_approved_private_lan=(
                    os.environ.get("RIVERVIEW_GRACE_ALLOW_APPROVED_OCTO1") == "1"))
            providers = {provider.provider_id: provider}
            routed = os.environ.get("RIVERVIEW_GRACE_ENABLE_MODEL_ROUTER") == "1"
            if routed:
                if os.environ.get("RIVERVIEW_GRACE_ALLOW_APPROVED_OCTO1") != "1":
                    raise ValueError("model router requires the existing explicit OCTO1 opt-in")
                authority_schema = os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority")
                from riverview_core.resident_execution.model_router import GraceModelRouter
                reasoning = LocalReasoningProvider(
                    "http://192.168.1.160:8080/v1",
                    "/root/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf",
                    os.environ["RIVERVIEW_GRACE_80B_MODEL_SHA256"], timeout_seconds=25,
                    allow_approved_private_lan=True)
                vision = LocalReasoningProvider(
                    "http://192.168.1.160:18080/v1",
                    "/mnt/model-storage/vision/Qwen3-VL-30B-A3B/Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated.i1-IQ3_XS.gguf",
                    os.environ["RIVERVIEW_GRACE_30B_MODEL_SHA256"], timeout_seconds=25,
                    allow_approved_private_lan=True)
                router = _build_grace_model_router(autonomic=provider, vision=vision,
                    reasoning=reasoning)
                with psycopg.connect(dsn, connect_timeout=2) as migration_probe:
                    _verify_grace_router_startup_readiness(
                        migration_probe, schema=schema, registry=authority_registry,
                        resident_credential=resident_token, office_id=chat_office_id,
                        router=router)
                providers = {router.provider_id: router}
            conversation_service = ResidentConversationService(
                store=conversation_store, registry=authority_registry,
                authorizer=ExactGrantAuthorizer(authority_schema), office_id=chat_office_id,
                resident_credential=resident_token,
                providers=providers,
                operational_context=GraceOperationalContext(projection))
            conversation_store.recover_pending()
            conversation_service.resume_streams(limit=20)
            if routed:
                def resume_deferred():
                    while True:
                        try:
                            conversation_service.resume_deferred(limit=10)
                        except Exception as exc:
                            print(json.dumps({"event": "grace_deferred_resume_cycle_failed",
                                              "error_type": type(exc).__name__}), flush=True)
                        threading.Event().wait(5)
                threading.Thread(target=resume_deferred,
                                 name="grace-deferred-resumption", daemon=True).start()
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
                                 account_auth_service=account_auth_service,
                                 permission_store=permission_store,
                                 proposal_registry=proposal_registry,
                                 steward_review_exchange=steward_review_exchange,
                                 resource_telemetry=resource_telemetry)
    print(json.dumps({"event": "dashboard_started", "host": host, "port": port,
                      "source_commit": projection.source_commit,
                      "deployment_id": projection.deployment_id}), flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        if objective_ledger is not None:
            objective_ledger.close()
        if steward_review_ledger is not None:
            steward_review_ledger.close()
        if conversation_store is not None:
            conversation_store.close()
        if authority_registry is not None:
            authority_registry.close()


if __name__ == "__main__":
    main()
