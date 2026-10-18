# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/record_work_assignment.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-DISPATCH-BRIDGE-001 | Add an explicit alias-to-work-order event bridge for v4 status records.
# Purpose: Record an operator/session-reported assignment event in the registry and compatible local v4 JSON
# Execution Model: One-shot, opt-in command; never polls or launches a session
# Observability: Canonical work-order state plus unchanged v4 status schema
# Dependencies: Python 3.10+; riverview_core.work_registry
# Authority: Receipt records acknowledgment only; it grants no execution, wake, polling, or commissioning authority
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: tests/test_work_assignment_bridge.py
# =============================================================================
"""Explicitly reconcile one canonical work order to a historical v4 alias."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from riverview_core.work_registry import SCHEMA_VERSION, WorkRegistry  # noqa: E402


MAPPING = ROOT / "docs/operations/CONTROL_BOARD_V4_IMPORT_MAP.json"
_EVENTS = {
    "acknowledged": ("queued", "WAITING"),
    "in_progress": ("active", "RUNNING"),
    "blocked": ("blocked", "BLOCKED"),
    "completed": ("completed", "COMPLETE"),
}
_SOURCE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/\d+(?:#issuecomment-\d+)?$")
_SENSITIVE = re.compile(r"(?i)(?:bearer\s+\S+|(?:password|secret|api[_ -]?key|access[_ -]?token)\s*[:=]\s*\S+|sk-[A-Za-z0-9_-]{12,}|system\s+prompt|private\s+reasoning)")


def capabilities():
    """Return verified limits of this request-driven bridge."""
    return {
        "automatic_github_polling": False,
        "existing_session_wake": False,
        "automatic_assignment_dispatch": False,
        "shared_windows_camrui_registry_verified": False,
        "registration_or_receipt_grants_authority": False,
        "reason": "No GitHub event consumer, authorized existing-session transport, or verified shared Windows-Camrui atomic registry path is configured.",
    }


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_text(value: str, field: str, *, maximum=512):
    if not isinstance(value, str) or not value or len(value) > maximum or _SENSITIVE.search(value):
        raise ValueError(f"{field}_invalid")
    return value


def _mapping_entry(mapping_path: Path, alias: str):
    try:
        doc = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("mapping_unreadable") from None
    if doc.get("schema_version") != "rv.work-registry.import-map.v1" or not isinstance(doc.get("records"), list):
        raise ValueError("mapping_contract_invalid")
    matches = [item for item in doc["records"]
               if item.get("worker_id") == alias and item.get("session_id") == alias]
    if len(matches) != 1:
        raise ValueError("alias_mapping_missing_or_ambiguous")
    return matches[0]


def _status_path(entry, mapping_path: Path, override: Path | None):
    if override is not None:
        target = override.expanduser()
    else:
        source = entry.get("source")
        if not isinstance(source, str) or source.startswith("ssh://"):
            raise ValueError("remote_alias_requires_explicit_local_status_path")
        source_path = Path(source)
        target = source_path if source_path.is_absolute() else mapping_path.parent / source_path
    if target.is_symlink():
        raise ValueError("status_path_symlink_rejected")
    target = target.resolve()
    if not target.is_file():
        raise ValueError("status_file_missing")
    return target


@contextmanager
def _status_lock(path: Path):
    lock = path.with_name(path.name + ".bridge.lock")
    deadline = time.monotonic() + 15
    while True:
        try:
            lock.mkdir()
            (lock / "owner").write_text(f"pid={os.getpid()}\n", encoding="ascii")
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ValueError("status_lock_timeout") from None
            time.sleep(0.025)
    try:
        yield
    finally:
        shutil.rmtree(lock, ignore_errors=True)


def _read_v4(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("status_json_unreadable") from None
    if not isinstance(data, dict) or not all(isinstance(data.get(key), str)
            for key in ("task", "status", "updated_at")):
        raise ValueError("status_v4_contract_invalid")
    return data


def _write_atomic(path: Path, data):
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def record_event(*, registry_path: Path, mapping_path: Path, alias: str,
                 work_order_id: str, event: str, source: str,
                 status_json: Path | None = None, milestone: int | None = None,
                 milestones_total: int | None = None, blocker: str | None = None,
                 outcome: str | None = None, detail: str | None = None,
                 next_action: str | None = None):
    if event not in _EVENTS:
        raise ValueError("event_unsupported")
    if not _SOURCE.fullmatch(source):
        raise ValueError("source_must_be_a_github_issue_or_pr_reference")
    if (milestone is None) != (milestones_total is None):
        raise ValueError("milestone_and_total_must_be_supplied_together")
    if milestone is not None and (milestone < 0 or milestones_total < 1 or milestone > milestones_total):
        raise ValueError("milestone_invalid")
    if event == "blocked" and not blocker:
        raise ValueError("blocker_required")
    if event == "completed" and not outcome:
        raise ValueError("outcome_required")
    if blocker is not None:
        _safe_text(blocker, "blocker", maximum=1000)
    if outcome is not None:
        _safe_text(outcome, "outcome", maximum=1000)
    if detail is not None:
        _safe_text(detail, "detail", maximum=2000)
    if next_action is not None:
        _safe_text(next_action, "next_action", maximum=1000)

    mapping_path = mapping_path.expanduser().resolve()
    entry = _mapping_entry(mapping_path, alias)
    target = _status_path(entry, mapping_path, status_json)
    registry = WorkRegistry(registry_path)
    snapshot = registry.snapshot()
    workers = {row["worker_id"]: row for row in snapshot["workers"]}
    sessions = {row["session_id"]: row for row in snapshot["sessions"]}
    orders = {row["work_order_id"]: row for row in snapshot["work_orders"]}
    worker = workers.get(alias)
    session = sessions.get(alias)
    order = orders.get(work_order_id)
    if not worker or not session or session["worker_id"] != alias:
        raise ValueError("registered_alias_not_found")
    if not order:
        raise ValueError("work_order_not_found")
    if order.get("worker_id") not in {None, alias} or order.get("session_id") not in {None, alias}:
        raise ValueError("work_order_owner_conflict")
    if event == "acknowledged" and order["status"] not in {"unknown", "queued"}:
        raise ValueError("acknowledgment_requires_unstarted_work_order")
    if event == "in_progress" and order["status"] not in {"unknown", "queued", "active"}:
        raise ValueError("start_requires_queued_work_order")
    if event == "blocked" and order["status"] not in {"unknown", "queued", "active", "blocked"}:
        raise ValueError("block_requires_nonterminal_work_order")
    if event == "completed" and order["status"] not in {"active", "blocked", "completed"}:
        raise ValueError("completion_requires_started_work_order")

    status_value, v4_status = _EVENTS[event]
    instant = _now()
    receipt = _safe_text(
        f"assignment event={event}; alias={alias}; work_order_id={work_order_id}; source={source}",
        "event_evidence", maximum=256)
    evidence = list(order.get("evidence") or [])
    if receipt not in evidence:
        evidence.append(receipt)
    changes = {
        "worker_id": alias,
        "session_id": alias,
        "owner_label": entry.get("owner_label") or f"Historical alias {alias}; session identity unverified",
        "ownership_state": "acknowledged",
        "status": status_value,
        "evidence": evidence[-64:],
        "blocker": blocker if event == "blocked" else None,
        "next_action": next_action or {
            "acknowledged": "Acknowledged receipt only; no session launch or wake was performed.",
            "in_progress": "Continue the explicitly acknowledged work and report the next milestone.",
            "blocked": "Resolve the recorded blocker before continuing.",
            "completed": "Review the recorded outcome and deliverable.",
        }[event],
    }
    if detail is not None:
        changes["detail"] = detail
    if event == "completed":
        changes["outcome"] = outcome
    if milestone is not None:
        changes["milestone"] = milestone
        changes["milestones_total"] = milestones_total
    with _status_lock(target):
        v4 = _read_v4(target)
        old_evidence = v4.get("evidence", "")
        if not isinstance(old_evidence, str):
            raise ValueError("status_evidence_must_be_text")
        expected_status = {
            "acknowledged": {"unknown", "queued"},
            "in_progress": {"unknown", "queued", "active"},
            "blocked": {"unknown", "queued", "active", "blocked"},
            "completed": {"active", "blocked", "completed"},
        }[event]
        updated_order = registry.update_work_order(work_order_id,
            expected_status=expected_status, **changes)
        v4["task"] = updated_order["title"]
        v4["status"] = v4_status
        v4["updated_at"] = instant
        v4["detail"] = detail or updated_order.get("detail") or f"Explicit work-order event recorded: {event}."
        v4["blocker"] = blocker if event == "blocked" else ""
        v4["next_action"] = changes["next_action"]
        if milestone is not None:
            v4["milestone"] = milestone
            v4["milestones_total"] = milestones_total
        elif updated_order.get("milestone") is not None:
            v4["milestone"] = updated_order["milestone"]
            v4["milestones_total"] = updated_order.get("milestones_total")
        if updated_order.get("branch"):
            v4["branch"] = updated_order["branch"]
        if updated_order.get("pull_request"):
            v4["pr_url"] = updated_order["pull_request"]
        if receipt not in old_evidence:
            v4["evidence"] = (old_evidence + (" | " if old_evidence else "") + receipt)
        _write_atomic(target, v4)

    current = registry.snapshot()
    current_session = next(item for item in current["sessions"] if item["session_id"] == alias)
    return {
        "recorded": True,
        "event": event,
        "work_order_id": work_order_id,
        "alias": alias,
        "identity_state": current_session["identity_state"],
        "session_lifecycle": current_session["lifecycle"],
        "session_activity": current_session["activity_state"],
        "last_heartbeat_at": current_session["last_heartbeat_at"],
        "work_order_status": updated_order["status"],
        "ownership_state": updated_order["ownership_state"],
        **capabilities(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities", help="Report whether this bridge can poll GitHub or wake existing sessions")
    record = sub.add_parser("record", help="Record one explicit assignment event; does not launch or wake Codex")
    record.add_argument("--registry", type=Path, required=True)
    record.add_argument("--mapping", type=Path, default=MAPPING)
    record.add_argument("--alias", required=True)
    record.add_argument("--work-order-id", required=True)
    record.add_argument("--event", choices=tuple(_EVENTS), required=True)
    record.add_argument("--source", required=True, help="GitHub issue or PR URL establishing the event")
    record.add_argument("--status-json", type=Path, help="Required for aliases mapped to remote SSH records")
    record.add_argument("--milestone", type=int)
    record.add_argument("--milestones-total", type=int)
    record.add_argument("--blocker")
    record.add_argument("--outcome")
    record.add_argument("--detail")
    record.add_argument("--next-action")
    args = parser.parse_args(argv)
    try:
        if args.command == "capabilities":
            print(json.dumps(capabilities(), sort_keys=True))
            return 0
        result = record_event(registry_path=args.registry, mapping_path=args.mapping,
            alias=args.alias, work_order_id=args.work_order_id, event=args.event,
            source=args.source, status_json=args.status_json, milestone=args.milestone,
            milestones_total=args.milestones_total, blocker=args.blocker,
            outcome=args.outcome, detail=args.detail, next_action=args.next_action)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"recorded": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
