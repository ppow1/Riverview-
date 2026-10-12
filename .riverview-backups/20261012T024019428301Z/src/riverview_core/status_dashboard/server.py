# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/server.py
# Component: STEWARD-DASHBOARD
# Revision: 1.1.1
# Purpose: Serve authenticated operational projections, objective intake, and resident conversation
# Execution Model: Request-driven, independent of CME assignment execution
# Observability: Structured request IDs, HTTP health/error codes, PostgreSQL projection
# Dependencies: Python 3.10+; standard library; status_dashboard.projection
# Authority: Dashboard credential protects views; objective API also requires exact objective.submit grant
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-ERROR-SEMANTICS | Preserve conflict/dependency failure distinction
# Changed: 2026-10-11 UTC | RV-M3.2-001 | Enforce the notification-specific maximum page size
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Add exact-grant resident conversation API and restart reconciliation
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_status_dashboard.py
# History: Git and revision/backup manifest
# =============================================================================
"""Loopback-only Steward dashboard with read projections and receipt-only writes."""

from __future__ import annotations

import hmac
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
_CONVERSATION_STATUS = re.compile(
    r"^/api/v1/resident/conversations/([0-9a-fA-F-]{36})/responses/([0-9a-fA-F-]{36})$")
_MAX_CHAT_BODY = 12 * 1024
_MAX_OBJECTIVE_BODY = 16 * 1024

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
                 objective_pipeline, conversation_service, static_dir):
        self._token = token
        self._projection = projection
        self._notification_service = notification_service
        self._objective_pipeline = objective_pipeline
        self._conversation_service = conversation_service
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
            notification_write = (_NOTICE_WRITE.fullmatch(parsed.path)
                                  if self.command == "POST" else None)
            objective_submit = (parsed.path == "/api/v1/objectives" and
                                self.command == "POST")
            objective_proposal = (_OBJECTIVE_PROPOSAL.fullmatch(parsed.path)
                                  if self.command == "POST" else None)
            objective_cancel = (_OBJECTIVE_CANCEL.fullmatch(parsed.path)
                                if self.command == "POST" else None)
            conversation_send = (parsed.path == "/api/v1/resident/conversations"
                                 and self.command == "POST")
            if not self._host_ok():
                self._error(400, "invalid_host", request_id)
                return
            if (self.command not in {"GET", "HEAD"} and not notification_write
                    and not objective_submit and not objective_proposal and not objective_cancel
                    and not conversation_send):
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
                        result = service.list_conversations(
                            self.headers.get("X-Riverview-Authority", ""))
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
                            self.headers.get("X-Riverview-Authority", ""),
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
                            self.headers.get("X-Riverview-Authority", ""),
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
                            self.headers.get("X-Riverview-Authority", ""),
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
                    selected["execution_position"] = {
                        "status": "unknown",
                        "reason": "The assignment ledger does not currently persist a graph node identity; no node is highlighted.",
                    }
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
                 conversation_service=None):
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
    notification_service = NotificationService(
        dsn, schema=os.environ.get("RIVERVIEW_DATABASE_SCHEMA", "riverview_dev"))
    from riverview_core.assignment_intake import AuthorizedAssignmentIntake
    from riverview_core.institutional_authority import ExactGrantAuthorizer
    from riverview_core.postgres_ledger import PostgresLedger
    from riverview_core.resident_execution import GraceExecutionPipeline
    from riverview_core.worker_adapter.knowledge import UnavailableKnowledgeProvider
    from riverview_core.worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider
    import psycopg
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
                                 conversation_service=conversation_service)
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
