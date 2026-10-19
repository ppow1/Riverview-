# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/external_review_readiness.py
# Component: EXTERNAL-REVIEW-READINESS
# Revision: 1.0.3
# Purpose: Produce a privacy-safe operator readiness projection for Grace's external review exchange
# Execution Model: Request-driven pure projection
# Observability: Versioned, bounded state object; identifiers and private content omitted
# Dependencies: Python standard library; C2 doorbell status/trigger health; C3 exchange; C4 provider result
# Authority: Read-only metadata projection; grants, review decisions, and execution remain with owning services
# Changed: 2026-10-18 UTC | RV-C1-EXTERNAL-REVIEW-READINESS-001 | Initial bounded readiness contract
# Changed: 2026-10-18 UTC | RV-C1-EXTERNAL-REVIEW-READINESS-001 | Add deadline visibility and fail closed on incomplete wake lineage
# Changed: 2026-10-18 UTC | RV-C1-EXTERNAL-REVIEW-READINESS-001 | Treat explicit degraded/blocked doorbell state as non-ready
# Changed: 2026-10-18 UTC | RV-C1-EXTERNAL-REVIEW-READINESS-001 | Do not equate Grace mailbox consumption with an evaluation decision
# Contracts: docs/components/EXTERNAL_REVIEW_READINESS.md
# Tests: tests/test_external_review_readiness.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Privacy-safe operator projection for the Grace external-review lifecycle.

This module consumes metadata projections from the durable exchange, doorbell,
and provider adapter. It never reads a review subject or response body and does
not make or authorize a review decision.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


SCHEMA_VERSION = "rv.grace.external-review-readiness.v1"
DOORBELL_SCHEMA_VERSION = "rv.chatgpt-doorbell.status.v1"

_EXCHANGE_STATES = {
    "awaiting_delivery", "awaiting_external_claim", "awaiting_response",
    "response_received", "grace_consumed", "expired", "failed",
}
_DOORBELL_STATUS = {"healthy", "degraded", "stale", "blocked", "failed",
                    "unavailable", "not_initialized"}
_BROWSER_HEALTH = {"healthy", "degraded", "unavailable", "unknown"}
_AUTH = {"composer_ready", "login_required", "unknown"}
_TARGET = {"exact_match", "unresolved", "unknown"}
_RECEIPT_OUTCOMES = {"submitted", "ambiguous", "failed"}
_PROVIDER_OUTCOMES = {"accepted", "rejected"}


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _now(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("now must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _report(*, readiness: str, state: str, failure_code: str | None,
            retryable: bool, next_action: str, sources: Mapping[str, bool],
            now: datetime, deadline_seconds_remaining: int | None = None) -> dict[str, Any]:
    """Return only allowlisted labels and source-presence/freshness booleans."""
    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": now.isoformat(),
        "readiness": readiness,
        "state": state,
        "failure_code": failure_code,
        "retryable": retryable,
        "next_action": next_action,
        "deadline_seconds_remaining": deadline_seconds_remaining,
        "evidence": dict(sources),
    }


def project_external_review_readiness(
    exchange_status: Mapping[str, Any] | None,
    doorbell_status: Mapping[str, Any] | None,
    *,
    wake_receipt: Mapping[str, Any] | None = None,
    provider_submission: Mapping[str, Any] | None = None,
    trigger_status: str | None = None,
    now: datetime | None = None,
    max_status_age: timedelta = timedelta(minutes=5),
) -> dict[str, Any]:
    """Project current review/doorbell readiness without exposing review data.

    ``exchange_status`` is the existing exchange ``status()`` projection.
    ``doorbell_status`` is C2's ``rv.chatgpt-doorbell.status.v1`` readiness
    metadata. Optional receipt and provider results use the C3/C4 agreed
    metadata-only contracts. Correlation fields, when both present, are checked
    for consistency but never copied to the returned object.

    Unknown, stale, malformed, expired, or mismatched evidence fails closed.
    The function performs no network, persistence, browser, or authorization
    operation; consumers must obtain each input from its owning service.
    ``trigger_status`` is the C2 owner's runtime health label; absent or unknown
    trigger status does not produce an overall ready result.
    """
    observed = _now(now)
    if (not isinstance(max_status_age, timedelta)
            or max_status_age <= timedelta(0)
            or max_status_age > timedelta(hours=1)):
        raise ValueError("max_status_age must be positive and no greater than one hour")

    evidence = {
        "exchange_available": isinstance(exchange_status, Mapping),
        "doorbell_available": isinstance(doorbell_status, Mapping),
        "doorbell_fresh": False,
        "browser_ready": False,
        "authentication_known": False,
        "target_resolved": False,
        "wake_receipt_present": isinstance(wake_receipt, Mapping),
        "provider_submission_present": isinstance(provider_submission, Mapping),
    }

    if not isinstance(exchange_status, Mapping):
        return _report(readiness="unavailable", state="mailbox_unavailable",
            failure_code="mailbox_unavailable", retryable=True,
            next_action="retry_exchange_status", sources=evidence, now=observed)

    exchange_state = exchange_status.get("delivery_state")
    deadline = _timestamp(exchange_status.get("deadline_at"))
    if exchange_state not in _EXCHANGE_STATES or deadline is None:
        return _report(readiness="blocked", state="invalid_exchange_status",
            failure_code="malformed_exchange_status", retryable=False,
            next_action="inspect_exchange_owner", sources=evidence, now=observed)

    def emit(**fields: Any) -> dict[str, Any]:
        remaining = None
        if exchange_state == "expired":
            remaining = 0
        elif exchange_state in {"awaiting_delivery", "awaiting_external_claim", "awaiting_response"}:
            remaining = max(0, int((deadline - observed).total_seconds()))
        return _report(**fields, sources=evidence, now=observed,
                       deadline_seconds_remaining=remaining)

    if deadline <= observed and exchange_state not in {
            "response_received", "grace_consumed", "expired", "failed"}:
        return emit(readiness="blocked", state="review_expired",
            failure_code="review_expired", retryable=False,
            next_action="record_expiry")
    if exchange_state == "expired":
        return emit(readiness="blocked", state="review_expired",
            failure_code="review_expired", retryable=False,
            next_action="record_expiry")
    if exchange_state == "failed":
        return emit(readiness="blocked", state="exchange_failed",
            failure_code="exchange_failed", retryable=False,
            next_action="inspect_exchange_owner")
    if exchange_state == "grace_consumed":
        return emit(readiness="ready", state="grace_consumed",
            failure_code=None, retryable=False, next_action="inspect_grace_decision",
            )
    if exchange_state == "response_received":
        if isinstance(provider_submission, Mapping):
            outcome = provider_submission.get("outcome")
            if outcome == "rejected":
                return emit(readiness="blocked", state="response_rejected",
                    failure_code="response_rejected", retryable=False,
                    next_action="request_valid_provider_response")
            if outcome != "accepted":
                return emit(readiness="blocked", state="invalid_provider_status",
                    failure_code="malformed_provider_status", retryable=False,
                    next_action="inspect_provider_owner")
        return emit(readiness="ready", state="response_received",
            failure_code=None, retryable=False, next_action="grace_consume_and_evaluate",
            )

    if isinstance(wake_receipt, Mapping):
        req, corr = exchange_status.get("request_id"), exchange_status.get("correlation_id")
        receipt_req, receipt_corr = wake_receipt.get("request_id"), wake_receipt.get("correlation_id")
        if (not isinstance(req, str) or not isinstance(corr, str)
                or receipt_req != req or receipt_corr != corr):
            return emit(readiness="blocked", state="correlation_mismatch",
                failure_code="correlation_mismatch", retryable=False,
                next_action="inspect_exchange_owner")
        outcome = wake_receipt.get("outcome")
        if outcome not in _RECEIPT_OUTCOMES:
            return emit(readiness="blocked", state="invalid_wake_receipt",
                failure_code="malformed_wake_receipt", retryable=False,
                next_action="inspect_doorbell_owner")
        if outcome in {"ambiguous", "failed"}:
            return emit(readiness="degraded", state="retry_recovery",
                failure_code="doorbell_delivery_ambiguous" if outcome == "ambiguous"
                    else "doorbell_delivery_failed",
                retryable=True, next_action="retry_doorbell_with_same_request")
        return emit(readiness="ready", state="wake_submitted_waiting_for_claim",
            failure_code=None, retryable=False, next_action="await_provider_claim")

    if exchange_state in {"awaiting_external_claim", "awaiting_response"}:
        if exchange_state == "awaiting_external_claim":
            state, next_action = "awaiting_provider_claim", "await_provider_claim"
        else:
            state, next_action = "awaiting_external_response", "await_provider_response"
        return emit(readiness="ready", state=state, failure_code=None,
            retryable=False, next_action=next_action)

    if not isinstance(doorbell_status, Mapping):
        return emit(readiness="blocked", state="doorbell_status_unavailable",
            failure_code="doorbell_status_unavailable", retryable=True,
            next_action="restore_doorbell_status")
    if doorbell_status.get("schema_version") != DOORBELL_SCHEMA_VERSION:
            return emit(readiness="blocked", state="invalid_doorbell_status",
            failure_code="malformed_doorbell_status", retryable=False,
                next_action="inspect_doorbell_owner")
    doorbell_time = _timestamp(doorbell_status.get("observed_at"))
    if doorbell_time is None:
        return emit(readiness="blocked", state="invalid_doorbell_status",
            failure_code="malformed_doorbell_status", retryable=False,
            next_action="inspect_doorbell_owner")
    age = observed - doorbell_time
    if age < timedelta(seconds=-30) or age > max_status_age:
        return emit(readiness="stale", state="doorbell_status_stale",
            failure_code="doorbell_status_stale", retryable=True,
            next_action="refresh_doorbell_status")
    evidence["doorbell_fresh"] = True

    status = doorbell_status.get("status")
    health = doorbell_status.get("browser_health")
    cdp = (doorbell_status.get("cdp") or {}).get("status") if isinstance(
        doorbell_status.get("cdp"), Mapping) else None
    auth = doorbell_status.get("authentication_status")
    target = doorbell_status.get("target_resolution")
    freshness = doorbell_status.get("freshness")
    stale_after = freshness.get("stale_after_seconds") if isinstance(freshness, Mapping) else None
    if (status not in _DOORBELL_STATUS or health not in _BROWSER_HEALTH
            or cdp not in {"connected", "unavailable", "unknown"}
            or type(stale_after) is not int or not 1 <= stale_after <= 3600
            or type(doorbell_status.get("local_browser_ready")) is not bool
            or type(doorbell_status.get("fixed_action_available")) is not bool):
        return emit(readiness="blocked", state="invalid_doorbell_status",
            failure_code="malformed_doorbell_status", retryable=False,
            next_action="inspect_doorbell_owner")
    freshness_state = freshness.get("state")
    schema_age = timedelta(seconds=min(stale_after, int(max_status_age.total_seconds())))
    if freshness_state not in {"fresh", "stale", "unknown"}:
        return emit(readiness="blocked", state="invalid_doorbell_status",
            failure_code="malformed_doorbell_status", retryable=False,
            next_action="inspect_doorbell_owner")
    if status == "stale" or freshness_state != "fresh" or age > schema_age:
        return emit(readiness="stale", state="doorbell_status_stale",
            failure_code="doorbell_status_stale", retryable=True,
            next_action="refresh_doorbell_status")
    evidence["browser_ready"] = (
        doorbell_status.get("local_browser_ready") is True
        and health == "healthy" and cdp == "connected")
    evidence["authentication_known"] = auth in _AUTH and auth != "unknown"
    evidence["target_resolved"] = target == "exact_match"
    if auth != "composer_ready":
        return emit(readiness="blocked", state="browser_authentication_unknown",
            failure_code="browser_authentication_unavailable", retryable=True,
            next_action="restore_browser_authentication")
    if target != "exact_match":
        return emit(readiness="blocked", state="browser_target_unresolved",
            failure_code="browser_target_unresolved", retryable=False,
            next_action="resolve_designated_target")
    if not evidence["browser_ready"] or doorbell_status.get("fixed_action_available") is not True:
        return emit(readiness="unavailable", state="browser_unavailable",
            failure_code="browser_unavailable", retryable=True,
            next_action="restore_browser_runtime")
    if status == "blocked":
        return emit(readiness="blocked", state="doorbell_blocked",
            failure_code="doorbell_blocked", retryable=False,
            next_action="inspect_doorbell_owner")
    if status in {"failed", "unavailable", "not_initialized"}:
        return emit(readiness="unavailable", state="doorbell_unavailable",
            failure_code="doorbell_unavailable", retryable=True,
            next_action="restore_doorbell_runtime")
    if status == "degraded":
        return emit(readiness="degraded", state="doorbell_degraded",
            failure_code="doorbell_degraded", retryable=True,
            next_action="inspect_doorbell_owner")
    last_trigger = doorbell_status.get("last_trigger")
    if isinstance(last_trigger, Mapping):
        same_request = (last_trigger.get("request_id") == exchange_status.get("request_id")
                        and last_trigger.get("correlation_id") == exchange_status.get("correlation_id")
                        and exchange_status.get("request_id") is not None
                        and exchange_status.get("correlation_id") is not None)
        if same_request and last_trigger.get("status") == "failed":
            return emit(readiness="degraded", state="retry_recovery",
                failure_code="doorbell_delivery_failed", retryable=True,
                next_action="retry_doorbell_with_same_request")
        if (same_request and last_trigger.get("status") == "succeeded"
                and last_trigger.get("submit_verified") is True):
            return emit(readiness="ready", state="wake_submitted_waiting_for_claim",
                failure_code=None, retryable=False, next_action="await_provider_claim",
                )
        if same_request and last_trigger.get("status") not in {"failed", "succeeded"}:
            return emit(readiness="blocked", state="invalid_wake_status",
                failure_code="malformed_wake_status", retryable=False,
                next_action="inspect_doorbell_owner")
    if trigger_status != "ready":
        if trigger_status == "not_configured":
            return emit(readiness="blocked", state="doorbell_not_configured",
                failure_code="doorbell_not_configured", retryable=False,
                next_action="configure_authorized_trigger")
        if trigger_status == "unavailable":
            return emit(readiness="unavailable", state="doorbell_trigger_unavailable",
                failure_code="doorbell_trigger_unavailable", retryable=True,
                next_action="restore_doorbell_trigger")
        return emit(readiness="degraded", state="doorbell_trigger_unverified",
            failure_code="doorbell_trigger_unverified", retryable=False,
            next_action="verify_doorbell_trigger")
    if exchange_state == "awaiting_delivery":
        return emit(readiness="ready", state="ready_for_doorbell",
            failure_code=None, retryable=False, next_action="doorbell_owner_may_wake",
            )
    return emit(readiness="blocked", state="unsupported_exchange_state",
        failure_code="unsupported_exchange_state", retryable=False,
        next_action="inspect_exchange_owner")
