# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/assignment_intake_http.py
# Component: ASSIGNMENT-INTAKE
# Revision: 1.0.0
# Purpose: Expose grant-gated assignment creation as a bounded loopback API
# Execution Model: Threaded request server; isolated PostgreSQL connection per call
# Observability: Structured request IDs and safe authorization/error codes
# Dependencies: Python 3.10+; Psycopg; AuthorizedAssignmentIntake
# Authority: Exact assignment.create grant required; no implicit actor or scope
# Changed: 2026-10-11 UTC | RV-M3.3-GOVERNED-INTAKE-ROUTE | Initial HTTP adapter
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_assignment_intake_http.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Small loopback-only HTTP adapter for exact-grant assignment intake."""

from __future__ import annotations

import ipaddress
import json
import logging
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .assignment_intake import (AssignmentIntakeDenied,
                                AssignmentIntakeUnavailable,
                                AuthorizedAssignmentIntake)
from .institutional_authority import ExactGrantAuthorizer
from .postgres_ledger import PostgresLedger

LOG = logging.getLogger("riverview.assignment_intake")
MAX_REQUEST_BYTES = 16 * 1024
FIELDS = {
    "assignment_id", "owner", "idempotency_key", "authority_ref",
    "objective_ref", "contract_ref", "workflow_id", "workflow_step",
    "occupant_id", "correlation_id",
}


def _safe_assignment(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("request_shape_invalid")
    required = {"assignment_id", "owner", "idempotency_key", "authority_ref", "objective_ref"}
    if not required.issubset(value) or value.keys() - FIELDS:
        raise ValueError("request_fields_invalid")
    for key, item in value.items():
        if item is not None and (not isinstance(item, str) or not item or len(item) > 4096):
            raise ValueError("request_value_invalid")
    if len(value["assignment_id"]) > 256 or len(value["authority_ref"]) > 512:
        raise ValueError("request_value_invalid")
    return value


class AssignmentIntakeHTTPServer(ThreadingHTTPServer):
    """Construct a fresh ledger/intake for each request; reject non-loopback binds."""

    daemon_threads = True
    request_queue_size = 16

    def __init__(self, address, handler, *, dsn, schema, authority_schema):
        host, _ = address
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError("assignment intake must bind to a literal loopback address")
        self.dsn = dsn
        self.schema = schema
        self.authority_schema = authority_schema
        super().__init__(address, handler)

    def build_intake(self):
        ledger = PostgresLedger(self.dsn, schema=self.schema)
        try:
            return ledger, AuthorizedAssignmentIntake(
                ledger, ExactGrantAuthorizer(self.authority_schema))
        except BaseException:
            ledger.close()
            raise


class AssignmentIntakeHandler(BaseHTTPRequestHandler):
    server: AssignmentIntakeHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args):
        # BaseHTTPRequestHandler includes raw paths; intentionally emit no payload or bearer.
        return

    def _json(self, status: int, document: dict[str, Any], request_id: str):
        body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-ID", request_id)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        request_id = secrets.token_hex(12)
        if self.path != "/api/v1/assignments":
            self._json(404, {"error": "not_found", "request_id": request_id}, request_id)
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "content_type_required", "request_id": request_id}, request_id)
            return
        length = self.headers.get("Content-Length", "")
        if not length.isascii() or not length.isdecimal() or int(length) > MAX_REQUEST_BYTES:
            self._json(413, {"error": "request_size_invalid", "request_id": request_id}, request_id)
            return
        auth = self.headers.get("Authorization", "")
        scheme, separator, credential = auth.partition(" ")
        if scheme.lower() != "bearer" or not separator or not credential or len(credential) > 512:
            self._json(401, {"error": "credential_required", "request_id": request_id}, request_id)
            return
        try:
            raw = self.rfile.read(int(length))
            payload = _safe_assignment(json.loads(raw))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
            self._json(400, {"error": "request_invalid", "request_id": request_id}, request_id)
            return
        ledger = None
        try:
            ledger, intake = self.server.build_intake()
            assignment = intake.create(
                payload["assignment_id"], payload["owner"], payload["idempotency_key"],
                credential=credential, authority_ref=payload["authority_ref"],
                objective_ref=payload["objective_ref"],
                contract_ref=payload.get("contract_ref"),
                workflow_id=payload.get("workflow_id", "assignment.v1"),
                workflow_step=payload.get("workflow_step", "intake"),
                occupant_id=payload.get("occupant_id"),
                correlation_id=payload.get("correlation_id"))
            self._json(200, {"request_id": request_id, "assignment": {
                "assignment_id": assignment["id"], "state": assignment["state"],
                "workflow_id": assignment["workflow_id"],
                "workflow_step": assignment["workflow_step"],
                "correlation_id": assignment["correlation_id"],
                "version": assignment["version"]}}, request_id)
            LOG.info(json.dumps({"event": "assignment_intake_accepted",
                                 "request_id": request_id,
                                 "assignment_id": assignment["id"]}, sort_keys=True))
        except AssignmentIntakeDenied:
            self._json(403, {"error": "assignment_create_denied", "request_id": request_id}, request_id)
        except AssignmentIntakeUnavailable:
            self._json(503, {"error": "authority_unavailable", "request_id": request_id}, request_id)
        except Exception as exc:
            try:
                import psycopg
            except ImportError:
                psycopg = None
            if psycopg is not None and isinstance(exc, psycopg.Error):
                sqlstate = getattr(exc, "sqlstate", None)
                self._json(503, {"error": "persistence_unavailable", "request_id": request_id}, request_id)
                LOG.warning(json.dumps({"event": "assignment_intake_failed",
                                       "request_id": request_id,
                                       "failure": "database_unavailable",
                                       "sqlstate": sqlstate}, sort_keys=True))
            else:
                self._json(409, {"error": "assignment_not_created", "request_id": request_id}, request_id)
                LOG.warning(json.dumps({"event": "assignment_intake_failed",
                                       "request_id": request_id,
                                       "failure": "persistence_or_validation"}, sort_keys=True))
        finally:
            if ledger is not None:
                ledger.close()


def serve(*, host="127.0.0.1", port=8710, dsn, schema="riverview_dev",
          authority_schema="riverview_authority", server_class=AssignmentIntakeHTTPServer):
    server = server_class((host, port), AssignmentIntakeHandler, dsn=dsn,
                          schema=schema, authority_schema=authority_schema)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
