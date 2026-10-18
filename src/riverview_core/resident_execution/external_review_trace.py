# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/external_review_trace.py
# Component: EXTERNAL-REVIEW-OBSERVABILITY
# Revision: 1.0.1
# Purpose: Build a redacted, read-only trace for exact external proposal reviews
# Execution Model: Pure projection of bounded metadata; no network or database access
# Observability: Correlated stage state, hashes, timestamps and sanitized blockers
# Dependencies: Python standard library
# Authority: Observational only; cannot authorize, deliver, consume, or finalize work
# Changed: 2026-10-18 UTC | RV-P0-W1-INTEGRATION-EVIDENCE | Align exact C3 successor and office actor mapping
# Tests: tests/test_external_review_trace.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Redacted operator projection for one or more exact external-review rounds.

The input is a bounded metadata snapshot assembled by an authorized read-only
operator. This module intentionally has no database, provider, browser, or
service client and never copies arbitrary input fields into its result.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any
from uuid import UUID


SCHEMA_VERSION = "rv.external-review-trace-input.v1"
REPORT_SCHEMA_VERSION = "rv.external-review-trace-report.v1"
MAX_INPUT_BYTES = 256 * 1024
MAX_ROUNDS = 12
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_CODE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_DOORBELL_CODE = re.compile(r"^RIV-PLY-\d{4}$")
_STATES = {
    "exchange": {"eligible", "awaiting_delivery", "awaiting_external_claim",
                  "awaiting_response", "response_received", "grace_consumed",
                  "expired", "failed", "unknown"},
    "doorbell": {"not_attempted", "submitted", "ambiguous", "failed", "unknown"},
    "provider": {"not_seen", "listed", "claimed", "response_received", "rejected", "unknown"},
    "decision": {"revise", "accept", "reject", "blocked"},
}


class TraceInputError(ValueError):
    """Metadata bundle is malformed or outside the bounded trace contract."""


def _text(value: Any, field: str, *, required: bool = False, max_length: int = 256):
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value) or len(value) > max_length:
        raise TraceInputError(f"invalid_{field}")
    if any(ord(char) < 32 for char in value):
        raise TraceInputError(f"invalid_{field}")
    return value


def _uuid(value: Any, field: str):
    text = _text(value, field, required=True, max_length=36)
    try:
        return str(UUID(text))
    except (ValueError, TypeError, AttributeError):
        raise TraceInputError(f"invalid_{field}") from None


def _digest(value: Any, field: str, *, required: bool = False):
    if value is None and not required:
        return None
    text = _text(value, field, required=True, max_length=64)
    if not _SHA256.fullmatch(text):
        raise TraceInputError(f"invalid_{field}")
    return text


def _timestamp(value: Any, field: str):
    text = _text(value, field, max_length=40)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise TraceInputError(f"invalid_{field}") from None
    if parsed.tzinfo is None:
        raise TraceInputError(f"invalid_{field}")
    return parsed.isoformat()


def _state(value: Any, stage: str):
    value = _text(value, f"{stage}_state", required=True, max_length=40)
    if value not in _STATES[stage]:
        raise TraceInputError(f"invalid_{stage}_state")
    return value


def _provider_state(provider: dict[str, Any], exchange_state: str):
    raw = provider.get("state", provider.get("delivery_state", exchange_state))
    raw = _text(raw, "provider_state", required=True, max_length=40)
    aliases = {
        "eligible": "not_seen",
        "awaiting_delivery": "not_seen",
        "awaiting_external_claim": "listed",
        "awaiting_response": "claimed",
        "response_received": "response_received",
        "grace_consumed": "response_received",
        "expired": "unknown",
        "failed": "unknown",
    }
    state = aliases.get(raw, raw)
    if state not in _STATES["provider"]:
        raise TraceInputError("invalid_provider_state")
    return state


def _provider_event_metadata(exchange: dict[str, Any]):
    events = exchange.get("events", [])
    if not isinstance(events, list) or len(events) > 2000:
        raise TraceInputError("invalid_exchange_events")
    result = {}
    for event in events:
        if not isinstance(event, dict):
            raise TraceInputError("invalid_exchange_event")
        event_type = event.get("event_type")
        if not isinstance(event_type, str):
            raise TraceInputError("invalid_exchange_event_type")
        if event_type not in {"claimed", "response_received"}:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise TraceInputError("invalid_exchange_event_payload")
        if event_type == "claimed":
            result["claimed_at"] = event.get("occurred_at")
        else:
            result["response_received_at"] = event.get("occurred_at")
            result["response_sha256"] = payload.get("response_sha256")
    return result


def _safe_code(value: Any):
    if value is None:
        return None
    text = _text(value, "safe_error_code", max_length=64)
    if not (_SAFE_CODE.fullmatch(text) or _DOORBELL_CODE.fullmatch(text)):
        raise TraceInputError("invalid_safe_error_code")
    return text


def _retry_after(value: Any):
    if value is None:
        return None
    if type(value) is int and 0 <= value <= 86400:
        return value
    return _timestamp(value, "doorbell_retry_after")


def _doorbell_from_exchange_events(exchange: dict[str, Any], request_id: str,
                                   correlation_id: str, doorbell_owner_id: str,
                                   exchange_state: str):
    """Project only the existing fenced exchange delivery events."""
    events = exchange.get("events", [])
    if not isinstance(events, list) or len(events) > 2000:
        raise TraceInputError("invalid_exchange_events")
    result = {"request_id": request_id, "correlation_id": correlation_id,
              "outcome": "not_attempted", "actor_id": doorbell_owner_id,
              "source_mismatch": False}
    unattributed_receipt = False
    attributed_receipt = False
    for event in events:
        if not isinstance(event, dict):
            raise TraceInputError("invalid_exchange_event")
        event_type = event.get("event_type")
        if not isinstance(event_type, str):
            raise TraceInputError("invalid_exchange_event_type")
        if event_type not in {"delivery_claimed", "doorbell_claimed", "delivery_started",
                              "doorbell_attempted", "delivered", "delivery_acknowledged",
                              "delivery_failed", "doorbell_receipt",
                              "doorbell_receipt_recorded"}:
            continue
        if event.get("actor_id") != doorbell_owner_id:
            if event_type in {"delivered", "delivery_acknowledged", "delivery_failed", "doorbell_receipt",
                              "doorbell_receipt_recorded"}:
                unattributed_receipt = True
            continue
        if event_type in {"delivered", "delivery_acknowledged", "delivery_failed", "doorbell_receipt",
                          "doorbell_receipt_recorded"}:
            attributed_receipt = True
        occurred_at = _timestamp(event.get("occurred_at"), "event_occurred_at")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise TraceInputError("invalid_exchange_event_payload")
        if event_type in {"delivery_claimed", "doorbell_claimed"}:
            result["claimed_at"] = occurred_at
        elif event_type in {"delivery_started", "doorbell_attempted"}:
            result["attempted_at"] = occurred_at
            attempt = payload.get("attempt_id")
            if attempt is not None:
                result["attempt_id"] = _text(attempt, "doorbell_attempt_id", max_length=128)
        elif event_type in {"delivered", "delivery_acknowledged"}:
            result["outcome"] = "submitted"
            result["recorded_at"] = occurred_at
            attempt = payload.get("delivery_attempt")
            if type(attempt) is int and attempt > 0:
                result["attempt_id"] = f"delivery-{attempt}"
            elif payload.get("attempt_id") is not None:
                result["attempt_id"] = _text(payload.get("attempt_id"), "doorbell_attempt_id", max_length=128)
        elif event_type == "delivery_failed":
            result["outcome"] = "failed"
            result["recorded_at"] = occurred_at
            result["safe_error_code"] = payload.get("error_code")
            retryable = payload.get("retryable")
            if type(retryable) is not bool:
                raise TraceInputError("invalid_delivery_retryable")
            result["retryable"] = retryable
        else:
            outcome = payload.get("outcome")
            if not isinstance(outcome, str) or outcome not in {"submitted", "ambiguous", "failed"}:
                raise TraceInputError("invalid_doorbell_outcome")
            result["outcome"] = outcome
            result["recorded_at"] = occurred_at
            result["attempt_id"] = _text(payload.get("attempt_id"), "doorbell_attempt_id", max_length=128)
            result["safe_error_code"] = payload.get("safe_error_code")
            retryable = payload.get("retryable")
            if retryable is None:
                retryable = outcome == "failed" and exchange_state == "awaiting_delivery"
            if type(retryable) is not bool:
                raise TraceInputError("invalid_delivery_retryable")
            result["retryable"] = retryable
    result["source_mismatch"] = unattributed_receipt and not attributed_receipt
    return result


def _grace_event_metadata(grace: dict[str, Any], exchange: dict[str, Any],
                          request_id: str, correlation_id: str, subject_id: str,
                          subject_revision: int, subject_sha256: str):
    """Map C3's allowlisted Grace events and exchange consumption event."""
    result = dict(grace)
    events = grace.get("events", [])
    if not isinstance(events, list) or len(events) > 2000:
        raise TraceInputError("invalid_grace_events")
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("event_type"), str):
            raise TraceInputError("invalid_grace_event")
        if event["event_type"] not in {
                "resident.reasoning.external_proposal_reviewed",
                "resident.reasoning.external_proposal_revised",
                "resident.reasoning.external_proposal_review_blocked"}:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise TraceInputError("invalid_grace_event_payload")
        if payload.get("request_id") != request_id or payload.get("correlation_id") != correlation_id:
            continue
        actor = event.get("actor_id")
        if not isinstance(actor, str) or not actor.startswith("office:"):
            result["event_actor_mismatch"] = True
            continue
        result["evaluated_at"] = event.get("occurred_at")
        if event["event_type"].endswith("revised"):
            # C3's revised event identifies the successor subject in subject_id,
            # revision and subject_sha256; the request/correlation still bind
            # the evaluation to this parent review.
            result["reviewed_revision"] = subject_revision
            result["review_sha256"] = subject_sha256
            result["decision"] = "revise"
            result["revised_version"] = payload.get("revision")
            result["revised_sha256"] = payload.get("subject_sha256")
            result["successor_request_id"] = payload.get("successor_request_id")
            result["successor_correlation_id"] = payload.get("successor_correlation_id")
        else:
            if (payload.get("subject_id") != subject_id or
                    payload.get("revision") != subject_revision or
                    payload.get("subject_sha256") != subject_sha256):
                result["event_subject_mismatch"] = True
                continue
            decision = "blocked" if event["event_type"].endswith("review_blocked") else payload.get("decision")
            result["reviewed_revision"] = payload.get("revision")
            result["review_sha256"] = payload.get("subject_sha256")
            result["decision"] = "accept" if decision == "finish" else decision
    exchange_events = exchange.get("events", [])
    if not isinstance(exchange_events, list) or len(exchange_events) > 2000:
        raise TraceInputError("invalid_exchange_events")
    for event in exchange_events:
        if (isinstance(event, dict) and event.get("event_type") == "grace_consumed"
                and event.get("request_id", request_id) == request_id
                and event.get("correlation_id", correlation_id) == correlation_id):
            result["consumed_at"] = event.get("occurred_at")
    return result


def _round(item: Any, index: int):
    if not isinstance(item, dict):
        raise TraceInputError("invalid_round")
    subject = item.get("review_subject")
    exchange = item.get("exchange")
    provider = item.get("provider")
    grace = item.get("grace")
    if not all(isinstance(value, dict) for value in (subject, exchange, provider, grace)):
        raise TraceInputError("round_metadata_required")

    review_id = _text(subject.get("subject_id"), "subject_id", required=True, max_length=160)
    version = subject.get("revision")
    if type(version) is not int or version < 1:
        raise TraceInputError("invalid_review_version")
    subject_hash = _digest(subject.get("sha256"), "review_sha256", required=True)
    request_id = _uuid(exchange.get("request_id"), "request_id")
    correlation_id = _uuid(exchange.get("correlation_id"), "correlation_id")
    exchange_state = _state(exchange.get("state", exchange.get("delivery_state")), "exchange")
    grace = _grace_event_metadata(grace, exchange, request_id, correlation_id,
                                  review_id, version, subject_hash)
    doorbell_owner_id = _text(item.get("doorbell_owner_id"), "doorbell_owner_id",
                              required=True, max_length=160)
    doorbell = item.get("doorbell")
    if doorbell is None:
        doorbell = _doorbell_from_exchange_events(exchange, request_id, correlation_id,
                                                  doorbell_owner_id, exchange_state)
    if not isinstance(doorbell, dict):
        raise TraceInputError("invalid_doorbell_metadata")
    if doorbell.get("actor_id") != doorbell_owner_id:
        # Never infer the wake source from a generic exchange delivery receipt.
        doorbell = {"request_id": request_id, "correlation_id": correlation_id,
                    "actor_id": doorbell_owner_id, "outcome": "not_attempted",
                    "source_mismatch": True}

    def correlated(source, name):
        source_request = source.get("request_id")
        source_correlation = source.get("correlation_id")
        if source_request is not None and _uuid(source_request, f"{name}_request_id") != request_id:
            raise TraceInputError(f"{name}_request_mismatch")
        if source_correlation is not None and _uuid(source_correlation, f"{name}_correlation_id") != correlation_id:
            raise TraceInputError(f"{name}_correlation_mismatch")

    correlated(doorbell, "doorbell")
    correlated(provider, "provider")
    correlated(grace, "grace")

    doorbell_state = _state(doorbell.get("outcome"), "doorbell")
    provider_events = _provider_event_metadata(exchange)
    provider_state = _provider_state(provider, exchange_state)
    provider_hash = _digest(provider.get("review_subject_sha256"), "provider_review_subject_sha256")
    response_hash = _digest(provider.get("response_sha256", exchange.get(
        "response_sha256", provider_events.get("response_sha256"))), "response_sha256")
    grace_hash = _digest(grace.get("review_sha256"), "grace_review_sha256")
    reviewed_revision = grace.get("reviewed_revision")
    if reviewed_revision is not None and (type(reviewed_revision) is not int or reviewed_revision < 1):
        raise TraceInputError("invalid_grace_reviewed_revision")
    decision = grace.get("decision")
    if decision is not None and (not isinstance(decision, str) or decision not in _STATES["decision"]):
        raise TraceInputError("invalid_grace_decision")

    blockers = []
    if exchange_state in {"expired", "failed"}:
        blockers.append(exchange_state)
    if doorbell_state == "failed" and doorbell.get("retryable") is not True:
        blockers.append("doorbell_failed")
    if doorbell.get("source_mismatch") is True:
        blockers.append("doorbell_owner_mismatch")
    if provider_state == "rejected":
        blockers.append("provider_response_rejected")
    if provider_hash is not None and provider_hash != subject_hash:
        blockers.append("provider_review_subject_mismatch")
    provenance = provider.get("response_provenance")
    provenance_received_at = provenance.get("received_at") if isinstance(provenance, dict) else None
    claimed_at = provider.get("claimed_at", provider_events.get("claimed_at"))
    response_received_at = provider.get("response_received_at",
                                       provenance_received_at or provider_events.get("response_received_at"))
    if provider_state == "response_received" and (provider_hash != subject_hash or
            response_hash is None or response_received_at is None or claimed_at is None):
        blockers.append("provider_response_evidence_incomplete")
    if grace_hash is not None and grace_hash != subject_hash:
        blockers.append("grace_review_subject_mismatch")
    if reviewed_revision is not None and reviewed_revision != version:
        blockers.append("grace_review_revision_mismatch")
    if grace.get("event_subject_mismatch") is True:
        blockers.append("grace_review_subject_id_mismatch")
    if grace.get("event_actor_mismatch") is True:
        blockers.append("grace_event_actor_unverified")

    evaluated_at = _timestamp(grace.get("evaluated_at"), "evaluated_at")
    consumed_at = _timestamp(grace.get("consumed_at"), "consumed_at")
    revised_hash = _digest(grace.get("revised_sha256"), "revised_sha256")
    revised_version = grace.get("revised_version")
    if revised_version is not None and (type(revised_version) is not int or revised_version <= version):
        raise TraceInputError("invalid_revised_version")

    evaluation_matches = decision is not None and grace_hash == subject_hash and evaluated_at is not None
    if exchange_state == "grace_consumed" and not evaluation_matches:
        blockers.append("grace_consumed_without_evaluation")
    if doorbell_state == "submitted" and (doorbell.get("attempt_id") is None or
            doorbell.get("recorded_at") is None):
        blockers.append("doorbell_receipt_evidence_incomplete")
    if decision == "accept" and (not evaluation_matches or consumed_at is None or
                                  exchange_state != "grace_consumed" or
                                  doorbell_state != "submitted" or
                                  provider_state != "response_received"):
        blockers.append("acceptance_not_durably_consumed")
    if decision == "revise" and (not evaluation_matches or consumed_at is None or
                                  exchange_state != "grace_consumed" or
                                  doorbell_state != "submitted" or
                                  provider_state != "response_received"):
        blockers.append("revision_not_durably_consumed")
    if decision == "revise" and (revised_hash is None or revised_version is None):
        blockers.append("revision_not_recorded")
    if decision == "revise" and (grace.get("successor_request_id") is None or
                                  grace.get("successor_correlation_id") is None):
        blockers.append("revision_successor_identity_missing")
    if decision in {"reject", "blocked"}:
        blockers.append(f"grace_{decision}")

    doorbell_claimed_at = _timestamp(doorbell.get("claimed_at"), "doorbell_claimed_at")
    eligible_at = _timestamp(exchange.get("eligible_at"), "mailbox_eligible_at")

    if blockers:
        state = "blocked"
    elif provider_state == "response_received" and not evaluation_matches:
        state = "response_received"
    elif decision == "accept" and evaluation_matches and consumed_at is not None:
        state = "accepted"
    elif decision == "revise" and evaluation_matches:
        state = "revised"
    elif provider_state == "claimed":
        state = "claimed"
    elif doorbell_state == "submitted":
        state = "wake_submitted"
    elif doorbell_state == "ambiguous":
        state = "wake_ambiguous"
    elif doorbell_state == "failed" and doorbell.get("retryable") is True:
        state = "delivery_retry_pending"
    elif doorbell_state == "not_attempted":
        state = "doorbell_claimed" if doorbell_claimed_at else (
            "eligible" if exchange_state == "eligible" else "unknown")
    elif exchange_state in {"eligible", "awaiting_delivery", "awaiting_external_claim", "awaiting_response"}:
        state = "eligible"
    else:
        state = "unknown"
    next_action = {
        "eligible": "doorbell_worker_may_claim",
        "doorbell_claimed": "await_or_reconcile_durable_wake_receipt",
        "wake_submitted": "await_provider_claim_and_review",
        "wake_ambiguous": "operator_reconcile_before_any_retry",
        "delivery_retry_pending": "allow_existing_bounded_retry",
        "claimed": "await_provider_response_or_claim_lease_expiry",
        "response_received": "Grace_must_evaluate_exact_subject",
        "revised": "new_exact_subject_requires_fresh_review",
        "accepted": "review_recorded_consumed",
        "blocked": "operator_review_blocker",
        "unknown": "reconcile_missing_metadata",
    }[state]

    # An acceptance is terminal only for the exact final reviewed subject. A
    # later round with a different subject is required after any revision.
    result = {
        "round": index,
        "review_id": review_id,
        "review_version": version,
        "review_sha256": subject_hash,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "doorbell_owner_id": doorbell_owner_id,
        "exchange_state": exchange_state,
        "mailbox_eligible": (exchange.get("eligible") is True or exchange_state == "eligible" or
                              eligible_at is not None or doorbell_claimed_at is not None),
        "mailbox_eligible_at": eligible_at,
        "doorbell_outcome": doorbell_state,
        "doorbell_source_mismatch": doorbell.get("source_mismatch") is True,
        "doorbell_attempt_id": _text(doorbell.get("attempt_id"), "doorbell_attempt_id", max_length=128),
        "doorbell_claimed_at": doorbell_claimed_at,
        "doorbell_attempted_at": _timestamp(doorbell.get("attempted_at"), "doorbell_attempted_at"),
        "doorbell_receipt_at": _timestamp(doorbell.get("recorded_at"), "doorbell_recorded_at"),
        "doorbell_retry_after": _retry_after(doorbell.get("retry_after")),
        "doorbell_error_code": _safe_code(doorbell.get("safe_error_code")),
        "provider_state": provider_state,
        "provider_id": _text(provider.get("provider_id"), "provider_id", max_length=160),
        "provider_claimed_at": _timestamp(claimed_at, "provider_claimed_at"),
        "response_received_at": _timestamp(response_received_at, "response_received_at"),
        "response_sha256": response_hash,
        "grace_evaluated_at": evaluated_at,
        "grace_decision": decision,
        "grace_review_sha256": grace_hash,
        "grace_reviewed_revision": reviewed_revision,
        "grace_consumed_at": consumed_at,
        "revised_version": revised_version,
        "revised_sha256": revised_hash,
        "successor_request_id": _uuid(grace.get("successor_request_id"), "successor_request_id")
                               if grace.get("successor_request_id") is not None else None,
        "successor_correlation_id": _uuid(grace.get("successor_correlation_id"), "successor_correlation_id")
                                    if grace.get("successor_correlation_id") is not None else None,
        "state": state,
        "next_action": next_action,
        "blockers": blockers,
    }
    return result


def build_report(bundle: Any) -> dict[str, Any]:
    """Return only allowlisted lineage metadata; private input fields are omitted."""
    if not isinstance(bundle, dict) or bundle.get("schema_version") != SCHEMA_VERSION:
        raise TraceInputError("unsupported_schema_version")
    rounds = bundle.get("rounds")
    if not isinstance(rounds, list) or not rounds or len(rounds) > MAX_ROUNDS:
        raise TraceInputError("invalid_round_count")
    execution_kind = bundle.get("execution_kind")
    if not isinstance(execution_kind, str) or execution_kind not in {"synthetic", "external", "unknown"}:
        raise TraceInputError("invalid_execution_kind")
    rendered = [_round(item, index + 1) for index, item in enumerate(rounds)]
    seen_requests, seen_correlations = set(), set()
    for index, current_round in enumerate(rendered):
        if (current_round["request_id"] in seen_requests or
                current_round["correlation_id"] in seen_correlations):
            raise TraceInputError("duplicate_review_round_identity")
        seen_requests.add(current_round["request_id"])
        seen_correlations.add(current_round["correlation_id"])
        if index and rendered[index - 1]["state"] == "revised":
            previous = rendered[index - 1]
            if (current_round["review_version"] != previous["revised_version"] or
                    current_round["review_sha256"] != previous["revised_sha256"]):
                raise TraceInputError("revision_successor_subject_mismatch")
            if (current_round["request_id"] != previous["successor_request_id"] or
                    current_round["correlation_id"] != previous["successor_correlation_id"]):
                raise TraceInputError("revision_successor_identity_mismatch")
    current = rendered[-1]
    if any(item["state"] == "accepted" for item in rendered[:-1]):
        # Acceptance followed by another round is contradictory unless the old
        # input was accidentally concatenated from separate review lineages.
        raise TraceInputError("accepted_review_has_successor_round")
    if current["state"] == "accepted":
        outcome = "complete"
    elif current["state"] == "blocked":
        outcome = "blocked"
    elif current["state"] == "revised":
        outcome = "review_required"
    else:
        outcome = "in_progress"
    safe = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "execution_kind": execution_kind,
        "execution_kind_verified": False,
        "evidence_level": ("synthetic_metadata_only" if execution_kind == "synthetic"
                           else "external_metadata_unverified" if execution_kind == "external"
                           else "execution_kind_unknown"),
        "outcome": outcome,
        "complete": outcome == "complete",
        "round_count": len(rendered),
        "rounds": rendered,
        "current_review_sha256": current["review_sha256"],
        "next_review_sha256": current["revised_sha256"] if current["state"] == "revised" else None,
    }
    safe["report_sha256"] = hashlib.sha256(json.dumps(
        safe, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    return safe


def parse_bundle(raw: bytes) -> dict[str, Any]:
    """Parse a size-bounded UTF-8 JSON bundle without exposing parse contents."""
    if not isinstance(raw, bytes) or len(raw) > MAX_INPUT_BYTES:
        raise TraceInputError("input_too_large")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise TraceInputError("invalid_json") from None
    return build_report(value)
