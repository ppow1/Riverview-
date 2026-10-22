"""Bounded, correlated application diagnostics for systemd journal collection."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_SAFE_SQLSTATE = re.compile(r"^[0-9A-Z]{5}$")
_SAFE_CLASS = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")
_ALLOWED_FIELDS = {
    "request_id", "conversation_id", "source_sequence", "objective_id",
    "failure_stage", "exception_type", "sqlstate", "backend_pid",
    "reason_code", "outcome", "retry_or_reuse",
}
_SAFE_LABEL = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,79}$")
_expiry_timer = None


def _restore_normal_logging():
    logging.getLogger().setLevel(logging.INFO)


def safe_sqlstate(exc):
    """Return PostgreSQL's public five-character error code, never its message."""
    value = getattr(exc, "sqlstate", None)
    return value if isinstance(value, str) and _SAFE_SQLSTATE.fullmatch(value) else None


def backend_pid(exc):
    """Extract backend PID only from psycopg diagnostic metadata."""
    diag = getattr(exc, "diag", None)
    value = getattr(diag, "server_process_id", None) if diag is not None else None
    return value if type(value) is int and 0 < value < 2**31 else None


def emit(logger, level, event, **fields):
    """Emit a compact allowlisted JSON event; omit values outside safe primitives."""
    record = {"event": event}
    for key, value in fields.items():
        if value is None or key not in _ALLOWED_FIELDS:
            continue
        if event in {"grace_work_order_auth_accepted", "grace_work_order_auth_denied"} and key not in {
                "request_id", "reason_code"}:
            continue
        if key in {"request_id", "conversation_id", "objective_id"}:
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                continue
        elif key == "sqlstate":
            if not isinstance(value, str) or not _SAFE_SQLSTATE.fullmatch(value):
                continue
        elif key == "exception_type":
            if not isinstance(value, str) or not _SAFE_CLASS.fullmatch(value):
                continue
        elif key in {"failure_stage", "reason_code", "outcome", "retry_or_reuse"}:
            if not isinstance(value, str) or not _SAFE_LABEL.fullmatch(value):
                continue
        elif key in {"backend_pid", "source_sequence"}:
            if type(value) is not int or value < 0:
                continue
        record[key] = value
    correlation = {key: record[key] for key in ("request_id", "objective_id")
                   if key in record}
    logger.log(level, json.dumps(record, sort_keys=True, separators=(",", ":")),
               extra=correlation)


class _ObjectiveRequestFilter(logging.Filter):
    def __init__(self, objective_id, request_id, expires_at=None):
        super().__init__()
        self.objective_id = objective_id
        self.request_id = request_id
        self.expires_at = expires_at

    def filter(self, record):
        if record.levelno != logging.DEBUG:
            return True
        if self.expires_at is not None and time.time() >= self.expires_at:
            logging.getLogger().setLevel(logging.INFO)
            return False
        if self.objective_id is None and self.request_id is None:
            return False
        return ((self.objective_id is not None and
                 getattr(record, "objective_id", None) == self.objective_id) or
                (self.request_id is not None and
                 getattr(record, "request_id", None) == self.request_id))


def configure_component_logging(*, environ=None, now=None):
    """Set NORMAL=INFO or expiring, correlation-filtered DEBUG on the root logger.

    DEBUG requires a future Unix expiry and an objective or request filter. Invalid,
    missing, or expired settings automatically resolve to NORMAL.
    """
    environ = os.environ if environ is None else environ
    now = time.time() if now is None else now
    global _expiry_timer
    if _expiry_timer is not None:
        _expiry_timer.cancel()
        _expiry_timer = None
    mode = environ.get("RIVERVIEW_DIAGNOSTICS_MODE", "NORMAL").upper()
    expiry = environ.get("RIVERVIEW_DIAGNOSTICS_EXPIRES_AT", "")
    objective_id = environ.get("RIVERVIEW_DIAGNOSTICS_OBJECTIVE_ID")
    request_id = environ.get("RIVERVIEW_DIAGNOSTICS_REQUEST_ID")
    try:
        expiry_at = float(expiry)
        valid_window = 0 < expiry_at - now <= 24 * 60 * 60
    except (TypeError, ValueError):
        expiry_at = None
        valid_window = False
    if mode != "DEBUG" or not valid_window or not (objective_id or request_id):
        mode = "NORMAL"
    level = logging.DEBUG if mode == "DEBUG" else logging.INFO
    logging.getLogger().setLevel(level)
    root = logging.getLogger()
    for handler in root.handlers:
        handler.filters[:] = [flt for flt in handler.filters
                              if not isinstance(flt, _ObjectiveRequestFilter)]
    correlation_filter = _ObjectiveRequestFilter(
        objective_id, request_id, expiry_at if mode == "DEBUG" else None)
    for handler in root.handlers:
        handler.addFilter(correlation_filter)
    if mode == "DEBUG":
        _expiry_timer = threading.Timer(max(0.01, expiry_at - now), _restore_normal_logging)
        _expiry_timer.daemon = True
        _expiry_timer.start()
    return mode
