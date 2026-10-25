# Revision: 1.0.1
"""Read-only derived operational status over authoritative persisted evidence."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


_TERMINAL = {
    "COMPLETED": ("completed", "Completed"),
    "CANCELLED": ("cancelled", "Cancelled"),
    "FAILED": ("failed", "Failed"),
}

_LABELS = {
    "awaiting_authorization": "Awaiting authorization",
    "reasoning_in_progress": "Reasoning in progress",
    "proposal_criteria_blocked": "Blocked — proposal criteria binding",
    "recovery_approval_pending": "Recovery approval pending",
    "recovery_in_progress": "Recovery in progress",
    "engineering_executing": "Engineering executing",
    "unknown": "Unknown",
    "status_unavailable": "Status unavailable",
}


def _time(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value


def _same_revision(value: Any, revision: int) -> bool:
    """Compare persisted JSON revision values without accepting coercive junk."""
    return (type(value) is int and value == revision) or (
        isinstance(value, str) and value.isdecimal() and int(value) == revision)


def derive_operational_status(*, lifecycle_status: str, revision: int,
                              assignment_state: str | None,
                              latest_event: dict | None,
                              lifecycle_updated_at: datetime | None = None,
                              assignment_updated_at: datetime | None = None,
                              criteria_failure: dict | None = None,
                              recovery_approval: dict | None = None,
                              supervisor_recovery: dict | None = None,
                              external_reasoning: dict | None = None,
                              now: datetime,
                              active_attempt_seconds: int = 30) -> dict[str, Any]:
    """Return a separate operational label; never alter the canonical lifecycle.

    Active evidence is restricted to live leases/requests or a fresh unmatched
    reasoning start. A stale start is reported Unknown rather than treated as
    indefinitely active. Terminal lifecycle records always dominate old activity.
    """
    canonical = str(lifecycle_status or "").upper()
    if canonical in _TERMINAL:
        code, label = _TERMINAL[canonical]
        terminal_event_type = {"COMPLETED": "objective.completed",
                               "CANCELLED": "objective.cancelled"}.get(canonical)
        event = latest_event or {}
        event_matches = event.get("event_type") == terminal_event_type
        return {"code": code, "label": label, "source": "grace_objectives.status",
                "occurred_at": (lifecycle_updated_at.isoformat()
                                if _time(lifecycle_updated_at) else None),
                "event_type": terminal_event_type if event_matches else None,
                "event_id": event.get("event_id") if event_matches else None}

    state = str(assignment_state or "").lower()
    if state == "running":
        return {"code": "engineering_executing", "label": _LABELS["engineering_executing"],
                "source": "assignments.state",
                "occurred_at": (assignment_updated_at.isoformat()
                                if _time(assignment_updated_at) else None),
                "event_type": None, "event_id": None}
    if state in {"queued", "ready", "awaiting_verification", "rework_required", "completed"}:
        return {"code": "unknown", "label": _LABELS["unknown"],
                "source": "assignments.state", "occurred_at": None,
                "event_type": None, "event_id": None}

    candidates: list[tuple[datetime, int, str, dict]] = []
    lifecycle_time = _time(lifecycle_updated_at)

    def add(code: str, evidence: dict | None, priority: int = 0) -> None:
        if not isinstance(evidence, dict):
            return
        timestamp = _time(evidence.get("occurred_at"))
        if timestamp is None or timestamp > now:
            return
        candidates.append((timestamp, priority, code, evidence))

    approval = recovery_approval or {}
    if (approval.get("status") == "pending" and
            _time(approval.get("expires_at")) is not None and
            approval["expires_at"] > now and
            (lifecycle_time is None or (_time(approval.get("occurred_at")) is not None
                                        and approval["occurred_at"] >= lifecycle_time)) and
            _same_revision(approval.get("objective_revision"), revision)):
        add("recovery_approval_pending", approval, 80)

    supervisor = supervisor_recovery or {}
    if (lifecycle_time is None or (_time(supervisor.get("occurred_at")) is not None
                                   and supervisor["occurred_at"] >= lifecycle_time)):
        add("recovery_in_progress", supervisor, 90)

    exchange = external_reasoning or {}
    if (exchange.get("active") is True and
            (_time(exchange.get("deadline_at")) is None or exchange["deadline_at"] > now) and
            (lifecycle_time is None or (_time(exchange.get("occurred_at")) is not None
                                       and exchange["occurred_at"] >= lifecycle_time))):
        add("reasoning_in_progress", exchange, 60)

    activity = latest_event or {}
    event_type = activity.get("event_type")
    event_time = _time(activity.get("occurred_at"))
    stale_attempt_time = None
    if event_type == "execution.reasoning_attempted" and event_time is not None:
        if (timedelta(0) <= now - event_time <= timedelta(seconds=max(1, active_attempt_seconds)) and
                (lifecycle_time is None or event_time >= lifecycle_time)):
            add("reasoning_in_progress", activity, 60)
        elif now - event_time > timedelta(seconds=max(1, active_attempt_seconds)):
            stale_attempt_time = event_time

    failure = criteria_failure or {}
    if (failure.get("detail_code") == "PROPOSAL_CRITERIA_BINDING_REJECTED" and
            failure.get("status") == "BLOCKED" and
            (lifecycle_time is None or (_time(failure.get("occurred_at")) is not None
                                        and failure["occurred_at"] >= lifecycle_time)) and
            _same_revision(failure.get("objective_revision"), revision)):
        add("proposal_criteria_blocked", failure, 70)

    # A proposal/work-order request that remains grounded and has no current
    # active request is the only positive evidence for an authorization wait.
    if (assignment_state is None and canonical in {"GROUNDED", "PROPOSED"} and
            (lifecycle_time is None or (event_time is not None and event_time >= lifecycle_time)) and
            event_type in {"objective.grounded", "work_order.proposed"}):
        add("awaiting_authorization", activity, 10)

    if not candidates:
        return {"code": "unknown", "label": _LABELS["unknown"],
                "source": "insufficient_or_stale_evidence", "occurred_at": None,
                "event_type": None, "event_id": None}

    newest = max(item[0] for item in candidates)
    if stale_attempt_time is not None and stale_attempt_time >= newest:
        return {"code": "unknown", "label": _LABELS["unknown"],
                "source": "grace_objective_events", "occurred_at": stale_attempt_time.isoformat(),
                "event_type": event_type, "event_id": activity.get("event_id")}
    current = [item for item in candidates if item[0] == newest]
    codes = {item[2] for item in current}
    if len(codes) > 1:
        return {"code": "unknown", "label": _LABELS["unknown"],
                "source": "contradictory_current_evidence", "occurred_at": newest.isoformat(),
                "event_type": None, "event_id": None}
    _, _, code, evidence = max(current, key=lambda item: item[1])
    return {"code": code, "label": _LABELS[code],
            "source": evidence.get("source", "persisted_activity"),
            "occurred_at": evidence.get("occurred_at").isoformat(),
            "event_type": evidence.get("event_type"),
            "event_id": evidence.get("event_id")}
