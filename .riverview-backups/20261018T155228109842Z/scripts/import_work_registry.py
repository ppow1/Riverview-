# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/import_work_registry.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.2
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Add explicit identity-mapped, read-only import for legacy session status JSON.
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-CONTROL-BOARD-001 | Add dry-run and newer-report reconciliation for local and SSH v4 sources.
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-CONTROL-BOARD-001 | Validate mapped hosts, reject symlink sources, and bound SSH source reads.
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
import subprocess
import sys
from uuid import NAMESPACE_URL, uuid5
from urllib.parse import urlsplit

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


def _parsed_time(value):
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    except ValueError:
        return None


def _read_source(source_value, mapping_path):
    """Read a local v4 record or an explicitly mapped read-only SSH source."""
    if not isinstance(source_value, str):
        raise ValueError("source must be a local path or ssh URL")
    if source_value.startswith("ssh://"):
        parsed = urlsplit(source_value)
        if (parsed.scheme != "ssh" or not parsed.hostname
                or not re.fullmatch(r"[A-Za-z0-9._-]+", parsed.hostname)
                or parsed.username
                or parsed.password or parsed.port or parsed.query or parsed.fragment
                or not parsed.path.startswith("/")
                or not re.fullmatch(r"/[A-Za-z0-9._/-]+", parsed.path)):
            raise ValueError("SSH source must be an explicit host and safe absolute path")
        try:
            result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                                     parsed.hostname, "cat", "--", parsed.path],
                                    check=False, capture_output=True, timeout=10)
        except subprocess.TimeoutExpired:
            raise ValueError("mapped SSH source timed out") from None
        if result.returncode:
            raise ValueError("mapped SSH source is unavailable")
        raw = result.stdout.decode("utf-8")
    else:
        source_path = Path(source_value)
        if not source_path.is_absolute():
            source_path = mapping_path.parent / source_path
        if source_path.is_symlink():
            raise ValueError("mapped source symlinks are not accepted")
        source_path = source_path.resolve()
        if not source_path.is_file():
            raise ValueError("mapped source must be an existing regular file")
        raw = source_path.read_text(encoding="utf-8")
    source = json.loads(raw)
    if not isinstance(source, dict):
        raise ValueError("mapped source must be a JSON object")
    return source


def import_map(mapping_path: Path, registry_path: Path, *, dry_run=False):
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
    updated_work_orders = 0
    non_newer_source_updates_ignored = 0
    omitted_long_evidence = 0
    omitted_structured_evidence = 0
    work_order_updates = []
    for entry in mapping["records"]:
        required = {"source", "worker_id", "session_id", "hostname", "os"}
        if not isinstance(entry, dict) or required - set(entry):
            raise ValueError("each mapping record requires source, worker_id, session_id, hostname, and os")
        if set(entry) - (required | {"worker_type", "capabilities", "model_identity", "endpoint_ref",
                "lifecycle", "started_at", "last_heartbeat_at", "last_activity_at",
                "identity_state", "owner_label", "ownership_state", "repository", "branch", "pull_request",
                "assignment_title", "source_evidence"}):
            raise ValueError("mapping record contains unsupported fields")
        source = _read_source(entry["source"], mapping_path)
        worker_id, session_id = entry["worker_id"], entry["session_id"]
        if worker_id not in workers:
            workers[worker_id] = {"worker_id": worker_id,
                "worker_type": entry.get("worker_type", "codex"),
                "hostname": entry["hostname"], "os": entry["os"],
                "capabilities": entry.get("capabilities", []),
                "model_identity": entry.get("model_identity"),
                "endpoint_ref": entry.get("endpoint_ref"), "registered_at": _now()}
        if session_id not in sessions:
            session = {"session_id": session_id, "worker_id": worker_id,
            "hostname": entry["hostname"], "os": entry["os"],
            "repository": entry.get("repository"),
            "branch": entry.get("branch") or source.get("branch") or None,
            "pull_request": entry.get("pull_request") or source.get("pr_url") or None,
            "model_identity": entry.get("model_identity"),
            "endpoint_ref": entry.get("endpoint_ref"),
            "lifecycle": entry.get("lifecycle", "unknown"), "activity_state": "unknown",
            "identity_state": entry.get("identity_state", "verified"),
            "current_work_order_id": None, "started_at": entry.get("started_at") or None,
            "last_heartbeat_at": entry.get("last_heartbeat_at") or None,
            "last_activity_at": entry.get("last_activity_at") or None, "ended_at": None}
            registry._validate_session(session)
            sessions[session_id] = session
            imported_sessions += 1
        elif sessions[session_id]["worker_id"] != worker_id:
            raise ValueError("mapped session alias conflicts with its existing worker")

        raw_status = source.get("status")
        status = _STATUS.get(raw_status if isinstance(raw_status, str) else "", "unknown")
        evidence = source.get("evidence")
        if isinstance(evidence, str):
            evidence = [evidence] if evidence else []
        if evidence is None:
            evidence = []
        if not isinstance(evidence, list):
            evidence = []
            omitted_structured_evidence += 1
        else:
            textual_evidence = [item for item in evidence if isinstance(item, str)]
            omitted_structured_evidence += len(evidence) - len(textual_evidence)
            evidence = textual_evidence
        title = _clean_text(entry.get("assignment_title") or source.get("task"),
                            limit=160, nullable=False)
        detail = _clean_text(source.get("detail"), limit=2000)
        blocker = _clean_text(source.get("blocker") or None, limit=2000)
        if status == "queued" and blocker:
            status = "blocked"
        next_action = _clean_text(source.get("next_action") or None, limit=1000)
        safe_evidence = []
        for item in evidence:
            if len(item) > 256:
                omitted_long_evidence += 1
                continue
            safe_evidence.append(_clean_text(item, limit=256, nullable=False))
        evidence = safe_evidence
        source_ref = entry.get("source_evidence")
        if source_ref:
            evidence.append(_clean_text(source_ref, limit=256, nullable=False))
        updated_at = source.get("updated_at") or None
        imported_at = _now()
        stable_key = str(entry["source"]) + "#" + session_id
        work_id = "work:import:" + uuid5(NAMESPACE_URL, stable_key).hex
        existing = work_orders.get(work_id)
        if existing is not None and existing["title"] != title:
            # Preserve the old assignment as history when a legacy slot's task changes.
            stable_key += "#" + title
            work_id = "work:import:" + uuid5(NAMESPACE_URL, stable_key).hex
        work = {"work_order_id": work_id, "session_id": session_id,
            "worker_id": worker_id, "owner_label": entry.get("owner_label"),
            "ownership_state": entry.get("ownership_state", "assigned"),
            "title": title, "detail": detail,
                "status": status, "milestone": source.get("milestone"),
                "milestones_total": source.get("milestones_total"), "milestones": [],
                "dependencies": [], "blocker": blocker, "next_action": next_action,
                "evidence": evidence, "outcome": None,
                "repository": entry.get("repository"),
                "branch": entry.get("branch") or source.get("branch") or None,
                "pull_request": entry.get("pull_request") or source.get("pr_url") or None,
                "deliverable": None, "local_ai_job": None,
                "created_at": imported_at, "updated_at": updated_at or imported_at,
                "started_at": source.get("started_at") or None,
                "completed_at": source.get("completed_at") or None}
        registry._validate_work_order(work)
        existing = work_orders.get(work_id)
        if existing is None:
            work_orders[work_id] = work
            imported_work_orders += 1
            if status == "active" and sessions[session_id]["lifecycle"] == "unknown":
                sessions[session_id]["current_work_order_id"] = work_id
        elif (updated_at and _parsed_time(updated_at)
                and _parsed_time(updated_at) > _parsed_time(existing.get("updated_at"))):
            event = f"v4 status transition: {existing['status']} -> {status} at {updated_at}"
            new_evidence = list(existing["evidence"])
            new_evidence.extend(item for item in evidence if item not in new_evidence)
            new_evidence.append(_clean_text(event, limit=256, nullable=False))
            fields = {key: value for key, value in work.items()
                      if key not in {"work_order_id", "created_at", "updated_at"}}
            fields["evidence"] = new_evidence[-64:]
            work_order_updates.append((work_id, fields, _parsed_time(updated_at)))
            updated_work_orders += 1
        elif updated_at:
            non_newer_source_updates_ignored += 1
    document = {"schema_version": SCHEMA_VERSION,
        "workers": {key: value for key, value in workers.items() if key not in current["workers"]},
        "sessions": {key: value for key, value in sessions.items() if key not in current["sessions"]},
        "work_orders": {key: value for key, value in work_orders.items() if key not in current["work_orders"]}}
    if not dry_run:
        registry.import_document(document)
        for work_id, fields, source_time in work_order_updates:
            registry.update_work_order(work_id, at=source_time, **fields)
    return {"status": "dry_run" if dry_run else "imported", "workers": len(workers),
            "sessions_added": imported_sessions,
            "work_orders_added": imported_work_orders,
            "work_orders_updated": updated_work_orders,
            "non_newer_source_updates_ignored": non_newer_source_updates_ignored,
            "long_evidence_items_not_copied": omitted_long_evidence,
            "structured_evidence_items_not_copied": omitted_structured_evidence,
            "source_files_unchanged": True,
            "unknown_heartbeat_preserved": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping", type=Path,
        help="Explicit rv.work-registry.import-map.v1 JSON; session and worker IDs are mandatory")
    parser.add_argument("--registry", type=Path, default=Path.home() / ".local/state/riverview/work-registry.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count records without changing the registry")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(import_map(args.mapping, args.registry, dry_run=args.dry_run), sort_keys=True))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "code": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
