# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/notifications/policy.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.0
# Purpose: Classify and filter durable attention notices using persisted Steward preferences
# Authority: Pure policy evaluation; no notification or authorization side effects
# =============================================================================
"""Notification-level and quiet-hours policy shared by the API and dispatcher."""

from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


LEVELS = ("all", "important", "critical_only", "paused")
EVENT_SEVERITY = {
    "assignment_stalled": "important",
    "assignment_attention": "important",
    "attention_resolved": "normal",
    "deadline_missed": "critical",
    "recovery_requested": "critical",
    "monitor_failed": "critical",
}


def validate_settings(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != {"level", "quiet_hours"}:
        raise ValueError("settings must include level and quiet_hours")
    level = value["level"]
    quiet = value["quiet_hours"]
    if level not in LEVELS or not isinstance(quiet, dict):
        raise ValueError("invalid notification settings")
    if set(quiet) != {"enabled", "start", "end", "timezone"}:
        raise ValueError("quiet_hours must include enabled, start, end, and timezone")
    if not isinstance(quiet["enabled"], bool):
        raise ValueError("quiet_hours.enabled must be boolean")
    try:
        start = time.fromisoformat(quiet["start"])
        end = time.fromisoformat(quiet["end"])
        ZoneInfo(quiet["timezone"])
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise ValueError("invalid quiet hours time or timezone") from None
    if start.tzinfo or end.tzinfo or start.second or end.second:
        raise ValueError("quiet hours use HH:MM local times")
    return {"level": level, "quiet_hours": {
        "enabled": quiet["enabled"], "start": start.strftime("%H:%M"),
        "end": end.strftime("%H:%M"), "timezone": quiet["timezone"]}}


def quiet_now(quiet: dict, now: datetime | None = None) -> bool:
    if not quiet["enabled"]:
        return False
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(quiet["timezone"])).time().replace(tzinfo=None)
    start = time.fromisoformat(quiet["start"])
    end = time.fromisoformat(quiet["end"])
    if start == end:
        return True  # Equal endpoints mean quiet all day.
    if start < end:
        return start <= local < end
    return local >= start or local < end


def allowed(event_type: str, settings: dict, now: datetime | None = None) -> tuple[bool, str | None]:
    severity = EVENT_SEVERITY.get(event_type)
    if severity is None:
        raise ValueError("unclassified notification event")
    level = settings["level"]
    critical = severity == "critical"
    if level == "paused" and not critical:
        return False, "paused"
    if level == "critical_only" and not critical:
        return False, "level"
    if level == "important" and severity == "normal":
        return False, "level"
    if quiet_now(settings["quiet_hours"], now) and not critical:
        return False, "quiet_hours"
    # Critical notices always pass Paused and quiet hours.
    return True, None
