# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/operational_context.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.0
# Purpose: Provide a bounded, read-only, provenance-bearing Grace operations snapshot
# Execution Model: Request-driven projection adapter
# Observability: Snapshot status, timestamp, source revision and stable capability identity
# Dependencies: Existing DashboardProjection read models
# Authority: Read-only; filters private payloads and creates no action authority
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-TOOLBOX-001 | Adapt existing projections as bounded operations context
# Contracts: docs/components/STATUS_DASHBOARD.md; docs/components/RESIDENT_CONVERSATION.md
# Tests: tests/test_grace_operational_context.py; tests/test_resident_conversation.py
# History: Git and revision/backup manifest
# =============================================================================
"""Bounded institutional snapshot for grounding Grace's operational reasoning."""

from __future__ import annotations

import re
from datetime import UTC, datetime


CAPABILITY_ID = "grace.operations.snapshot.read.v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
_SAFE_STATUS = re.compile(r"^[a-z][a-z0-9_.:-]{0,63}$")
_SAFE_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T[^\s]{1,48}$")
_MAX_ITEMS = 8


def _safe_id(value):
    return value if isinstance(value, str) and _SAFE_ID.fullmatch(value) else None


def _safe_status(value):
    return value if isinstance(value, str) and _SAFE_STATUS.fullmatch(value) else "unknown"


def _safe_timestamp(value):
    return value if isinstance(value, str) and _SAFE_TIMESTAMP.fullmatch(value) else None


class GraceOperationalContext:
    """Collect safe summaries only; projection remains the sole database reader."""

    def __init__(self, projection):
        self.projection = projection

    def snapshot(self):
        observed_at = datetime.now(UTC).isoformat()
        try:
            status = self.projection.status()
            assignments = self.projection.assignments(limit=_MAX_ITEMS)
            objectives = self.projection.objectives(limit=_MAX_ITEMS)
            attention = self.projection.attention(limit=_MAX_ITEMS)
            workers = self.projection.workers(limit=_MAX_ITEMS)
        except Exception as exc:
            return {"schema_version": "rv.grace.operations-context.v1",
                    "capability_id": CAPABILITY_ID, "status": "unavailable",
                    "observed_at": observed_at, "failure_type": type(exc).__name__}

        projection = status.get("projection_status", "unknown")
        source = status.get("source", {})
        safe_source = {key: _safe_id(source.get(key)) for key in
                       ("database", "schema", "source_commit", "deployment_id")}
        items = assignments.get("items", []) if assignments.get("status") == "available" else []
        objective_items = objectives.get("items", []) if objectives.get("status") == "available" else []
        attention_items = attention.get("items", []) if attention.get("status") == "available" else []
        worker_items = workers.get("items", []) if workers.get("status") == "available" else []
        return {
            "schema_version": "rv.grace.operations-context.v1",
            "capability_id": CAPABILITY_ID,
            "status": "current" if projection == "healthy" else _safe_status(projection),
            "observed_at": observed_at,
            "source_observed_at": _safe_timestamp(status.get("observed_at")),
            "evidence_classification": "authoritative_database_projection",
            "source": safe_source,
            "cme": _select(status.get("cme", {}),
                ("status", "service_id", "last_heartbeat_at", "heartbeat_age_seconds",
                 "last_scan_at", "assignments_observed", "workers_registered", "workers_enabled")),
            "assignment_counts": _safe_counts(status.get("assignment_counts", {})),
            "grace_execution": _select(status.get("grace_execution", {}),
                ("status", "service_id", "last_heartbeat_at", "heartbeat_age_seconds",
                 "last_cycle_at", "last_error_type", "cycles_completed")),
            "assignments": [_assignment(item) for item in items[:_MAX_ITEMS]],
            "assignments_status": _safe_status(assignments.get("status")),
            "objectives": [_objective(item) for item in objective_items[:_MAX_ITEMS]],
            "objectives_status": _safe_status(objectives.get("status")),
            "attention": [_attention(item) for item in attention_items[:_MAX_ITEMS]],
            "attention_status": _safe_status(attention.get("status")),
            "workers": [_worker(item) for item in worker_items[:_MAX_ITEMS]],
            "workers_status": _safe_status(workers.get("status")),
            "diagnostics": _select(status.get("diagnostics", {}),
                ("component", "workflow", "graph")),
            "redaction": "assignment/objective request text, payloads, artifacts and conversation content excluded",
        }


def _select(value, keys):
    if not isinstance(value, dict):
        return {"status": "unknown"}
    result = {}
    for key in keys:
        if key not in value:
            continue
        item = value[key]
        if key == "status":
            result[key] = _safe_status(item)
        elif key.endswith("_at"):
            result[key] = _safe_timestamp(item)
        elif key in {"service_id", "instance_id", "component", "workflow", "graph"}:
            result[key] = _safe_id(item)
        elif isinstance(item, (bool, int, float)) and (not isinstance(item, (int, float))
                                                       or item >= 0):
            result[key] = item
        else:
            result[key] = None
    return result


def _safe_counts(value):
    if not isinstance(value, dict):
        return {}
    return {key: count for key, count in value.items()
            if _safe_id(key) and isinstance(count, int) and count >= 0}


def _assignment(value):
    fields = ("assignment_id", "owner", "workflow_id", "workflow_step",
              "process_graph_id", "process_node_id", "correlation_id")
    result = {key: _safe_id(value.get(key)) for key in fields if key in value}
    if "state" in value:
        result["state"] = _safe_status(value.get("state"))
    if "updated_at" in value:
        result["updated_at"] = _safe_timestamp(value.get("updated_at"))
    version = value.get("version")
    if isinstance(version, int) and version >= 0:
        result["version"] = version
    return result


def _objective(value):
    verification = value.get("verification") or {}
    return {"objective_id": _safe_id(value.get("objective_id")),
            "status": _safe_status(value.get("status")),
            "assignment_id": _safe_id(value.get("assignment_id")),
            "assignment_state": _safe_status(value.get("assignment_state")),
            "verification_decision": _safe_status(verification.get("decision"))
                if verification.get("decision") is not None else None,
            "revision": value.get("revision") if isinstance(value.get("revision"), int)
                and value.get("revision") >= 0 else None,
            "updated_at": _safe_timestamp(value.get("updated_at"))}


def _attention(value):
    return {"event_id": _safe_id(value.get("event_id")),
            "event_type": _safe_status(value.get("event_type")),
            "assignment_id": _safe_id(value.get("assignment_id")),
            "recorded_at": _safe_timestamp(value.get("recorded_at")),
            "failure_type": _safe_id(value.get("failure_type"))}


def _worker(value):
    return {key: (_safe_id(value.get(key)) if key == "worker_id"
                  else _safe_status(value.get(key)) if key == "health"
                  else _safe_timestamp(value.get(key)) if key == "heartbeat_at"
                  else value.get(key))
        for key in ("worker_id", "active", "health", "heartbeat_at",
                    "heartbeat_age_seconds", "active_leases") if key in value
        and (key not in {"active", "heartbeat_age_seconds", "active_leases"}
             or isinstance(value.get(key), (bool, int, float))
             and (not isinstance(value.get(key), (int, float))
                  or value.get(key) >= 0))}
