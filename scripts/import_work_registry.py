# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/import_work_registry.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Add explicit identity-mapped, read-only import for legacy session status JSON.
# Purpose: Import supplied session records without inventing identities or changing source files
# Execution Model: One-shot request-driven migration tool
# Observability: Safe summary of imported counts and explicit unknown status
# Dependencies: Python 3.10+; riverview_core.work_registry
# Authority: Import does not dispatch work or change the current control board
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: tests/test_work_registry.py
# =============================================================================
"""Import caller-mapped session status files into an additive registry snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from riverview_core.work_registry import SCHEMA_VERSION, WorkRegistry  # noqa: E402


_SENSITIVE = re.compile(r"(?i)(?:bearer\s+\S+|(?:password|secret|api[_ -]?key)\s*[:=]\s*\S+|sk-[A-Za-z0-9_-]{12,})")
_STATUS = {"RUNNING": "active", "WAITING": "queued", "WAITING_FOR_EVIDENCE": "blocked",
           "BLOCKED": "blocked", "COMPLETE": "completed", "COMPLETED": "completed",
           "FAILED": "failed", "CANCELLED": "cancelled", "UNKNOWN": "unknown"}


def _clean_text(value, *, limit, nullable=True):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or len(value) > limit or _SENSITIVE.search(value):
        raise ValueError("source text is invalid or contains credential-like content")
    return value or None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def import_map(mapping_path: Path, registry_path: Path):
    mapping_path = Path(mapping_path)
    if mapping_path.is_symlink():
        raise ValueError("mapping symlinks are not accepted")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if (not isinstance(mapping, dict) or mapping.get("schema_version") != "rv.work-registry.import-map.v1"
            or not isinstance(mapping.get("records"), list)):
        raise ValueError("an rv.work-registry.import-map.v1 mapping with records is required")
    registry = WorkRegistry(registry_path)
    current = registry._read_unlocked()
    workers = dict(current["workers"])
    sessions = dict(current["sessions"])
    work_orders = dict(current["work_orders"])
    imported_sessions = 0
    imported_work_orders = 0
    for entry in mapping["records"]:
        required = {"source", "worker_id", "session_id", "hostname", "os"}
        if not isinstance(entry, dict) or required - set(entry):
            raise ValueError("each mapping record requires source, worker_id, session_id, hostname, and os")
        if set(entry) - (required | {"worker_type", "capabilities", "model_identity", "endpoint_ref",
                "lifecycle", "started_at", "last_heartbeat_at", "last_activity_at",
                "owner_label", "ownership_state", "repository", "branch", "pull_request"}):
            raise ValueError("mapping record contains unsupported fields")
        source_path = Path(entry["source"])
        if not source_path.is_absolute():
            source_path = (mapping_path.parent / source_path).resolve()
        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError("mapped source must be an existing regular file")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(source, dict):
            raise ValueError("mapped source must be a JSON object")
        worker_id, session_id = entry["worker_id"], entry["session_id"]
        if worker_id not in workers:
            workers[worker_id] = {"worker_id": worker_id,
                "worker_type": entry.get("worker_type", "codex"),
                "hostname": entry["hostname"], "os": entry["os"],
                "capabilities": entry.get("capabilities", []),
                "model_identity": entry.get("model_identity"),
                "endpoint_ref": entry.get("endpoint_ref"), "registered_at": _now()}
        if session_id in sessions:
            continue
        session = {"session_id": session_id, "worker_id": worker_id,
            "hostname": entry["hostname"], "os": entry["os"],
            "repository": entry.get("repository"),
            "branch": entry.get("branch", source.get("branch")),
            "pull_request": entry.get("pull_request", source.get("pr_url")),
            "model_identity": entry.get("model_identity"),
            "endpoint_ref": entry.get("endpoint_ref"),
            "lifecycle": entry.get("lifecycle", "unknown"), "activity_state": "unknown",
            "current_work_order_id": None, "started_at": entry.get("started_at"),
            "last_heartbeat_at": entry.get("last_heartbeat_at"),
            "last_activity_at": entry.get("last_activity_at"), "ended_at": None}
        registry._validate_session(session)
        work_orders_for_session = [item for item in work_orders.values()
                                   if item["session_id"] == session_id]
        stable_key = str(source_path.resolve()) + "#" + session_id
        work_id = "work:import:" + uuid5(NAMESPACE_URL, stable_key).hex
        if work_orders_for_session:
            session["current_work_order_id"] = next((item["work_order_id"] for item in
                work_orders_for_session if item["status"] in {"active", "queued", "blocked"}), None)
        sessions[session_id] = session
        imported_sessions += 1
        if not any(item["work_order_id"] == work_id for item in work_orders.values()):
            raw_status = source.get("status")
            status = _STATUS.get(raw_status if isinstance(raw_status, str) else "", "unknown")
            evidence = source.get("evidence")
            if isinstance(evidence, str):
                evidence = [evidence] if evidence else []
            if evidence is None:
                evidence = []
            if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
                raise ValueError("source evidence must be a string or list of strings")
            title = _clean_text(source.get("task"), limit=160, nullable=False)
            detail = _clean_text(source.get("detail"), limit=2000)
            blocker = _clean_text(source.get("blocker") or None, limit=2000)
            next_action = _clean_text(source.get("next_action") or None, limit=1000)
            evidence = [_clean_text(item, limit=256, nullable=False) for item in evidence]
            updated_at = source.get("updated_at")
            imported_at = _now()
            work = {"work_order_id": work_id, "session_id": session_id,
            "worker_id": worker_id, "owner_label": entry.get("owner_label"),
            "ownership_state": entry.get("ownership_state", "assigned"),
            "title": title, "detail": detail,
                "status": status, "milestone": source.get("milestone"),
                "milestones_total": source.get("milestones_total"), "milestones": [],
                "dependencies": [], "blocker": blocker, "next_action": next_action,
                "evidence": evidence, "outcome": None,
                "repository": entry.get("repository"),
                "branch": entry.get("branch", source.get("branch")),
                "pull_request": entry.get("pull_request", source.get("pr_url")),
                "deliverable": None, "local_ai_job": None,
                "created_at": imported_at, "updated_at": updated_at or imported_at,
                "started_at": source.get("started_at"),
                "completed_at": source.get("completed_at") or
                    (updated_at if status in {"completed", "failed", "cancelled"} else None)}
            registry._validate_work_order(work)
            work_orders[work_id] = work
            imported_work_orders += 1
            if status == "active":
                sessions[session_id]["current_work_order_id"] = work_id
    document = {"schema_version": SCHEMA_VERSION, "workers": workers,
                "sessions": sessions, "work_orders": work_orders}
    registry.import_document(document)
    return {"status": "imported", "workers": len(workers),
            "sessions_added": imported_sessions,
            "work_orders_added": imported_work_orders,
            "source_files_unchanged": True,
            "unknown_heartbeat_preserved": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping", type=Path,
        help="Explicit rv.work-registry.import-map.v1 JSON; session and worker IDs are mandatory")
    parser.add_argument("--registry", type=Path, default=Path.home() / ".local/state/riverview/work-registry.json")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(import_map(args.mapping, args.registry), sort_keys=True))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "code": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
