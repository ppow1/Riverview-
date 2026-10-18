# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/doorbell/dispatcher.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.1
# Purpose: Wake the fixed ChatGPT browser target for one durably claimed review
# Inputs/Outputs: Provider-scoped metadata claim / metadata-only durable receipt
# Execution Model: One bounded poll cycle called by the existing resident owner loop
# Observability: Request/correlation IDs, attempt ID, outcome, stable safe error code
# Dependencies: DurableExternalReasoningExchange contract; BrowserBridgeRunner
# Authority: No mailbox bodies, no browser response reads, no new requests or identities
# Changed: 2026-10-18 UTC | RV-C2-CHATGPT-DOORBELL-DISPATCH-001 | Initial implementation
# Contracts: docs/components/CHATGPT_DOORBELL_DISPATCH.md
# Tests: tests/test_external_reasoning_doorbell_dispatcher.py
# History: Git and .riverview-revisions.json

"""One-cycle, wake-only adapter from the durable Grace exchange to its browser doorbell."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol
from uuid import UUID

from .browser_bridge import BrowserBridgeRunner, DoorbellRequest

_SAFE_ERROR = re.compile(r"^RIV-PLY-\d{4}$")
_RETRYABLE_PRE_SEND = frozenset({
    "RIV-PLY-0002", "RIV-PLY-0005", "RIV-PLY-0006",
    "RIV-PLY-0007", "RIV-PLY-0008", "RIV-PLY-0010", "RIV-PLY-0011",
    "RIV-PLY-0012", "RIV-PLY-0013", "RIV-PLY-0015", "RIV-PLY-0016",
})


class DoorbellExchange(Protocol):
    """The existing durable exchange API; implementations own all state and retry rules."""

    def claim_next_doorbell_request(
        self, provider_id: str, owner_id: str, lease_seconds: int
    ) -> Any | None: ...

    def record_doorbell_receipt(
        self, request_id: str, correlation_id: str, provider_id: str,
        owner_id: str, attempt_id: str, lease_token: str, fence: int,
        outcome: str, safe_error_code: str | None,
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class DoorbellWorkerConfig:
    provider_id: str
    owner_id: str
    designated_conversation_id: str
    lease_seconds: int = 90
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("provider_id must be supplied by the approved provider configuration")
        if not isinstance(self.owner_id, str) or not self.owner_id.strip() or len(self.owner_id) > 256:
            raise ValueError("owner_id must be the configured internal worker identity")
        try:
            UUID(self.designated_conversation_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("designated conversation must be a UUID") from exc
        if type(self.lease_seconds) is not int or not 1 <= self.lease_seconds <= 120:
            raise ValueError("doorbell lease is outside the bounded range")
        if type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 110:
            raise ValueError("doorbell timeout is outside the bounded range")
        if self.lease_seconds < self.timeout_seconds + 10:
            raise ValueError("delivery lease must exceed bridge timeout and completion margin")


@dataclass(frozen=True, slots=True)
class DoorbellCycleResult:
    status: str
    trigger_status: str
    request_id: str | None = None
    correlation_id: str | None = None
    attempt_id: str | None = None
    outcome: str | None = None
    safe_error_code: str | None = None
    receipt_recorded: bool = False


def _claim_value(claim: Any, name: str) -> Any:
    if isinstance(claim, Mapping):
        return claim.get(name)
    return getattr(claim, name, None)


def _validated_claim(claim: Any, expected_provider: str,
                     minimum_lease_seconds: int) -> tuple[UUID, UUID, str, str, int]:
    """Read only claim metadata and require enough fenced-lease time to finish a wake."""
    try:
        request_id = UUID(str(_claim_value(claim, "request_id")))
        correlation_id = UUID(str(_claim_value(claim, "correlation_id")))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("claim_identity_invalid") from exc
    provider_id = _claim_value(claim, "provider_id")
    attempt_id = _claim_value(claim, "attempt_id")
    lease_token = _claim_value(claim, "lease_token")
    fence = _claim_value(claim, "fence")
    if provider_id != expected_provider:
        raise ValueError("claim_provider_mismatch")
    if not isinstance(attempt_id, str) or not attempt_id or len(attempt_id) > 128:
        raise ValueError("claim_attempt_invalid")
    if not isinstance(lease_token, str) or not lease_token or len(lease_token) > 256:
        raise ValueError("claim_lease_invalid")
    if type(fence) is not int or fence < 1:
        raise ValueError("claim_fence_invalid")
    lease_until = _claim_value(claim, "lease_until")
    if isinstance(lease_until, str):
        try:
            lease_until = datetime.fromisoformat(lease_until.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("claim_lease_expiry_invalid") from exc
    if (not isinstance(lease_until, datetime) or lease_until.tzinfo is None
            or lease_until <= datetime.now(timezone.utc) + timedelta(seconds=minimum_lease_seconds)):
        raise ValueError("claim_lease_expiry_invalid")
    return request_id, correlation_id, attempt_id, lease_token, fence


def _bridge_outcome(result: Any) -> tuple[str, str | None]:
    status = getattr(result, "status", None)
    if status in {"succeeded", "already_succeeded"}:
        return "submitted", None
    raw_code = getattr(result, "failure_class", None)
    code = raw_code if isinstance(raw_code, str) and _SAFE_ERROR.fullmatch(raw_code) else "doorbell_failure"
    # A timeout, malformed response, or lost lineage may follow a real click. Never resend
    # those automatically. Only known failures before the fixed action are retry candidates.
    if code in _RETRYABLE_PRE_SEND:
        return "failed", code
    return "ambiguous", code


class DoorbellWakeWorker:
    """Claim at most one existing review and send only the established fixed wake."""

    def __init__(self, exchange: DoorbellExchange, bridge: BrowserBridgeRunner,
                 config: DoorbellWorkerConfig) -> None:
        self.exchange = exchange
        self.bridge = bridge
        self.config = config

    def run_once(self) -> DoorbellCycleResult:
        """Execute one short owner-loop cycle; never logs or returns exchange payloads."""
        try:
            claim = self.exchange.claim_next_doorbell_request(
                self.config.provider_id, self.config.owner_id, self.config.lease_seconds
            )
        except Exception:
            return DoorbellCycleResult(
                "exchange_unavailable", "unavailable", safe_error_code="exchange_claim_failed"
            )
        if claim is None:
            return DoorbellCycleResult("idle", "ready")

        try:
            request_id, correlation_id, attempt_id, lease_token, fence = _validated_claim(
                claim, self.config.provider_id, self.config.timeout_seconds + 5
            )
        except ValueError:
            # Leave an invalid claim to its durable lease expiry; never ring an unbound request.
            return DoorbellCycleResult(
                "invalid_claim", "blocked", safe_error_code="claim_metadata_invalid"
            )

        try:
            wake = self.bridge.ring(
                DoorbellRequest(request_id, correlation_id, self.config.timeout_seconds),
                self.config.designated_conversation_id,
            )
            outcome, error_code = _bridge_outcome(wake)
        except Exception:
            # An unexpected bridge exception has unknown send state and is not auto-retried.
            outcome, error_code = "ambiguous", "doorbell_exception"

        try:
            self.exchange.record_doorbell_receipt(
                str(request_id), str(correlation_id), self.config.provider_id,
                self.config.owner_id, attempt_id, lease_token, fence, outcome, error_code,
            )
        except Exception:
            # The durable claim remains authoritative and will recover by lease expiry.
            return DoorbellCycleResult(
                "receipt_unavailable", "unavailable", str(request_id), str(correlation_id), attempt_id,
                outcome, "receipt_write_failed", False,
            )
        return DoorbellCycleResult(
            "recorded", "ready" if outcome == "submitted" else "blocked",
            str(request_id), str(correlation_id), attempt_id,
            outcome, error_code, True,
        )
