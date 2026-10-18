# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/external_reasoning.py
# Component: RESIDENT-REASONING
# Revision: 1.0.4
# Purpose: Persist and resume authorized external reasoning exchanges
# Execution Model: Request-driven PostgreSQL outbox, bounded leases, no polling loop
# Observability: Correlated state and sanitized append-only transition diagnostics
# Dependencies: Psycopg 3; PostgresLedger; ReasoningEscalationRouter
# Authority: Exact resident.reasoning.escalate grant; returned advice cannot authorize work
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Initial durable exchange contract
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Permit scoped pull/recovery of delivered provider requests
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Expose bounded response-received IDs for Grace's durable consumer
# Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Provide pending-objective guard and make retry identity independent of first-delivery deadline
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# Tests: tests/test_external_reasoning_exchange.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Durable, transport-neutral exchange for advisory external reasoning.

This component owns only the exchange envelope. Existing objective, proposal,
assignment, authorization and verification records remain authoritative. A
transport calls ``begin_delivery``/``mark_delivered``; an external claimant can
claim and submit one typed advisory; Grace leases and consumes it through the
same exact escalation grant. No method invokes a provider or blocks on one.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Mapping
from uuid import UUID, uuid4

from ..reasoning_escalation import (
    EscalationRequest, EscalationStatus, ReasoningEscalationRouter,
    context_fingerprint,
)
from ..resident_reasoning import ReasoningRequest


class ExchangeError(RuntimeError):
    """A durable exchange operation failed without changing authority."""


class ExchangeConflict(ExchangeError):
    """The requested transition conflicts with persisted exchange state."""


class ExchangeNotFound(ExchangeError):
    """No exchange exists for the supplied request/correlation pair."""


class ExchangeUnauthorized(ExchangeError):
    """The existing exact escalation authority check did not authorize access."""


class ExchangeExpired(ExchangeError):
    """The finite exchange deadline has passed."""


@dataclass(frozen=True)
class ExchangeReceipt:
    request_id: str
    correlation_id: str
    delivery_state: str
    context_sha256: str
    duplicate: bool = False


@dataclass(frozen=True)
class ExchangeClaim:
    request_id: str
    correlation_id: str
    claim_token: str
    fence: int
    lease_until: datetime
    duplicate: bool = False


@dataclass(frozen=True)
class ExchangeConsumption:
    request_id: str
    correlation_id: str
    consumption_key: str
    consumption_token: str
    fence: int
    lease_until: datetime
    advisory: Mapping[str, Any]
    original_request: ReasoningRequest
    duplicate: bool = False


_ALLOWED_CLASSIFICATIONS = {"institutional", "confidential"}
_SAFE_CODE = re.compile(r"^[a-z0-9_]{1,80}$")
_MAX_CONTEXT_BYTES = 32 * 1024
_MAX_RESPONSE_BYTES = 16 * 1024
_MAX_DELIVERY_ATTEMPTS = 5


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return value.astimezone(timezone.utc)


class DurableExternalReasoningExchange:
    """A bounded PostgreSQL exchange adapter around the existing escalation router."""

    REQUEST_SCHEMA = "rv.external-reasoning.request.v1"
    RESPONSE_SCHEMA = "rv.external-reasoning.response.v1"
    EVENT_SCHEMA = "rv.external-reasoning.event.v1"
    STATES = {
        "awaiting_delivery": "Awaiting delivery",
        "awaiting_external_claim": "Awaiting external claim",
        "awaiting_response": "Awaiting response",
        "response_received": "Response received",
        "grace_consumed": "Grace consumed",
        "expired": "Expired",
        "failed": "Failed",
    }

    def __init__(self, ledger, router: ReasoningEscalationRouter, *, actor_id="office:grace",
                 clock=lambda: datetime.now(timezone.utc)):
        if not isinstance(router, ReasoningEscalationRouter):
            raise TypeError("ReasoningEscalationRouter is required")
        if not isinstance(actor_id, str) or not actor_id or len(actor_id) > 256:
            raise ValueError("a bounded exchange actor identity is required")
        self.ledger = ledger
        self.router = router
        self.actor_id = actor_id
        self.clock = clock

    def _set_path(self, cur):
        self.ledger._set_search_path(cur)

    def _event(self, cur, row, event_type, key_suffix, actor, payload):
        payload = {"schema_version": self.EVENT_SCHEMA, **payload}
        key = f"external-reasoning:{row['request_id']}:{key_suffix}"
        cur.execute("""INSERT INTO external_reasoning_exchange_events
            (request_id,correlation_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb)
            ON CONFLICT (idempotency_key) DO NOTHING""",
            (row["request_id"], row["correlation_id"], event_type, key,
             actor, _json(payload)))
        cur.execute("""INSERT INTO grace_objective_events
            (objective_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,%s,%s,%s,%s::jsonb)
            ON CONFLICT (idempotency_key) DO NOTHING""",
            (row["objective_id"], "external_reasoning." + event_type,
             key, actor, _json({"request_id": str(row["request_id"]),
                "correlation_id": str(row["correlation_id"]), **payload})))

    def _authorize(self, envelope, original, principal_id, authorize):
        result = self.router.authorize_for_durable_exchange(
            envelope, original, principal_id=principal_id, authorize=authorize)
        if result.status is not EscalationStatus.AUTHORIZED_FOR_EXCHANGE:
            raise ExchangeUnauthorized(result.detail_code)

    def _require_provider_principal(self, provider_id, principal_id):
        provider = self.router.providers.get(provider_id)
        registered_id = getattr(provider, "provider_id", None)
        expected = getattr(provider, "exchange_principal_id", provider_id)
        if (provider is None or registered_id != provider_id or
                not isinstance(expected, str) or principal_id != expected):
            raise ExchangeUnauthorized("provider_principal_mismatch")

    @staticmethod
    def _validate_origin(original, *, originating_resident_id, objective_id,
                         conversation_id, message_sequence, proposal_id,
                         proposal_revision, classification):
        if (not isinstance(original, ReasoningRequest) or not isinstance(objective_id, str)
                or original.assignment_id != objective_id
                or not isinstance(originating_resident_id, str)
                or not originating_resident_id or len(originating_resident_id) > 256
                or type(message_sequence) is not int or message_sequence < 1
                or classification not in _ALLOWED_CLASSIFICATIONS):
            raise ValueError("exchange origin, objective correlation, or classification is invalid")
        try:
            UUID(str(conversation_id))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("conversation_id must be a UUID") from None
        if (proposal_id is None) != (proposal_revision is None):
            raise ValueError("proposal ID and exact revision must be supplied together")
        if proposal_id is not None and (not isinstance(proposal_id, str) or
                                        type(proposal_revision) is not int or proposal_revision < 1):
            raise ValueError("proposal reference is invalid")

    def submit(self, envelope: EscalationRequest, original: ReasoningRequest, *,
               principal_id: str, authorize, originating_resident_id: str,
               objective_id: str, conversation_id: str, message_sequence: int,
               idempotency_key: str, classification: str,
               deadline_at: datetime, proposal_id: str | None = None,
               proposal_revision: int | None = None,
               source_references: tuple[str, ...] = ()) -> ExchangeReceipt:
        """Authorize and durably enqueue before any delivery operation is possible."""
        self._validate_origin(original, originating_resident_id=originating_resident_id,
            objective_id=objective_id, conversation_id=conversation_id,
            message_sequence=message_sequence, proposal_id=proposal_id,
            proposal_revision=proposal_revision, classification=classification)
        if (not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 240
                or len(source_references) > 32 or any(not isinstance(x, str) or not x or len(x) > 512
                                                       for x in source_references)):
            raise ValueError("exchange idempotency key or source references exceed bounds")
        deadline = _utc(deadline_at)
        now = _utc(self.clock())
        if not timedelta(seconds=1) <= deadline - now <= timedelta(hours=24):
            raise ValueError("exchange deadline must be 1 second to 24 hours ahead")
        self._authorize(envelope, original, principal_id, authorize)
        if context_fingerprint(original) != envelope.context_sha256:
            raise ExchangeConflict("reasoning context changed before durable admission")
        request_payload = {
            "schema_version": self.REQUEST_SCHEMA,
            "original_request": asdict(original),
            "reason": envelope.reason,
            "max_tokens": envelope.max_tokens,
            "timeout_seconds": envelope.timeout_seconds,
            "source_references": list(source_references),
        }
        encoded = _json(request_payload).encode("utf-8")
        if len(encoded) > _MAX_CONTEXT_BYTES:
            raise ValueError("external reasoning request exceeds 32 KiB")
        immutable = {
            "originating_resident_id": originating_resident_id,
            "objective_id": objective_id,
            "conversation_id": str(conversation_id),
            "message_sequence": message_sequence,
            "proposal_id": proposal_id,
            "proposal_revision": proposal_revision,
            "reason": envelope.reason,
            "context_sha256": envelope.context_sha256,
            "classification": classification,
            "provider_id": envelope.target_provider_id,
            "request_payload": request_payload,
        }
        request_hash = _digest(immutable)
        request_id = UUID(envelope.escalation_id)
        correlation_id = uuid4()
        db = self.ledger.db
        with db.transaction():
            with db.cursor() as cur:
                self._set_path(cur)
                cur.execute("""INSERT INTO external_reasoning_exchanges
                    (request_id,correlation_id,original_request_id,originating_resident_id,
                     objective_id,conversation_id,message_sequence,proposal_id,proposal_revision,
                     request_schema,response_schema,reason,context_sha256,classification,
                     provider_id,idempotency_key,request_sha256,request_payload,delivery_state,
                     next_delivery_at,deadline_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,
                            'awaiting_delivery',%s,%s)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (request_id, correlation_id, original.request_id, originating_resident_id,
                     objective_id, conversation_id, message_sequence, proposal_id,
                     proposal_revision, self.REQUEST_SCHEMA, self.RESPONSE_SCHEMA,
                     envelope.reason, envelope.context_sha256, classification,
                     envelope.target_provider_id, idempotency_key, request_hash,
                     _json(request_payload), now, deadline))
                inserted = cur.rowcount == 1
                cur.execute("SELECT * FROM external_reasoning_exchanges WHERE idempotency_key=%s FOR UPDATE",
                            (idempotency_key,))
                row = cur.fetchone()
                if row is None or row["request_sha256"] != request_hash:
                    raise ExchangeConflict("idempotency key was reused for a different request")
                if inserted:
                    self._event(cur, row, "requested", "requested", originating_resident_id,
                        {"state": row["delivery_state"], "provider_id": row["provider_id"],
                         "context_sha256": row["context_sha256"],
                         "classification": row["classification"]})
        return ExchangeReceipt(str(row["request_id"]), str(row["correlation_id"]),
                               row["delivery_state"], row["context_sha256"], not inserted)

    def has_active_for_objective(self, objective_id: str) -> bool:
        """Prevent duplicate model escalation while an objective exchange is pending."""
        if not isinstance(objective_id, str) or not objective_id:
            raise ValueError("objective identity is required")
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            cur.execute("""SELECT 1 FROM external_reasoning_exchanges
                WHERE objective_id=%s AND delivery_state IN
                  ('awaiting_delivery','awaiting_external_claim','awaiting_response','response_received')
                LIMIT 1""", (objective_id,))
            return cur.fetchone() is not None

    def eligible_requests(self, provider_id: str, *, principal_id: str,
                          limit=10) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("eligible request limit must be between 1 and 50")
        self._require_provider_principal(provider_id, principal_id)
        now = _utc(self.clock())
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                cur.execute("""SELECT request_id FROM external_reasoning_exchanges
                    WHERE delivery_state NOT IN ('response_received','grace_consumed','expired','failed')
                      AND deadline_at<=%s ORDER BY deadline_at LIMIT 50 FOR UPDATE""", (now,))
                for expired in cur.fetchall():
                    row = self._lock(cur, expired["request_id"])
                    self._transition(cur, row, "expired", "request_expired", self.actor_id,
                                     "request_deadline_elapsed")
                cur.execute("""SELECT request_id,correlation_id,objective_id,conversation_id,
                    message_sequence,proposal_id,proposal_revision,request_schema,response_schema,
                    provider_id,classification,context_sha256,request_payload,requested_at,deadline_at,
                    delivery_state
                FROM external_reasoning_exchanges
                WHERE provider_id=%s AND deadline_at>%s AND (
                    (delivery_state='awaiting_delivery' AND next_delivery_at<=%s
                     AND (delivery_lease_until IS NULL OR delivery_lease_until<=%s))
                    OR delivery_state IN ('awaiting_external_claim','awaiting_response'))
                ORDER BY requested_at,request_id LIMIT %s""",
                (provider_id, now, now, now, limit))
                return [dict(row) for row in cur.fetchall()]

    def provider_status(self, request_id: str, correlation_id: str, *,
                        provider_id: str, principal_id: str) -> dict[str, Any]:
        """Return body-free status only to the authenticated owning provider."""
        self._require_provider_principal(provider_id, principal_id)
        status = self.status(request_id, correlation_id)
        if status["provider_id"] != provider_id:
            raise ExchangeNotFound("exchange identity not found")
        return status

    def begin_delivery(self, request_id: str, provider_id: str, *, owner_id: str,
                       lease_seconds=30) -> ExchangeClaim | None:
        if not 1 <= lease_seconds <= 120 or not owner_id or len(owner_id) > 256:
            raise ValueError("delivery owner or lease is invalid")
        now = _utc(self.clock())
        token = uuid4()
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id)
                if row["provider_id"] != provider_id:
                    raise ExchangeUnauthorized("provider_mismatch")
                self._expire_if_due(cur, row, now, owner_id)
                if row["delivery_state"] != "awaiting_delivery" or row["next_delivery_at"] > now:
                    return None
                if row["delivery_lease_until"] and row["delivery_lease_until"] > now:
                    if row["delivery_owner"] == owner_id:
                        return ExchangeClaim(str(row["request_id"]), str(row["correlation_id"]),
                            str(row["delivery_token"]), row["delivery_fence"],
                            row["delivery_lease_until"], True)
                    return None
                if row["delivery_attempts"] >= _MAX_DELIVERY_ATTEMPTS:
                    self._transition(cur, row, "failed", "delivery_attempt_limit", owner_id,
                                     "delivery_attempt_limit")
                    return None
                fence = row["delivery_fence"] + 1
                lease_until = min(row["deadline_at"], now + timedelta(seconds=lease_seconds))
                cur.execute("""UPDATE external_reasoning_exchanges SET delivery_attempts=delivery_attempts+1,
                    delivery_owner=%s,delivery_token=%s,delivery_fence=%s,delivery_lease_until=%s,
                    updated_at=%s WHERE request_id=%s""",
                    (owner_id, token, fence, lease_until, now, row["request_id"]))
                row.update(delivery_owner=owner_id, delivery_token=token,
                           delivery_fence=fence, delivery_lease_until=lease_until)
                self._event(cur, row, "delivery_claimed", f"delivery-claim-{fence}", owner_id,
                    {"state": row["delivery_state"], "fence": fence})
                return ExchangeClaim(str(row["request_id"]), str(row["correlation_id"]),
                    str(token), fence, lease_until)

    def mark_delivered(self, request_id: str, correlation_id: str, provider_id: str, *,
                       owner_id: str, delivery_token: str, fence: int) -> str:
        now = _utc(self.clock())
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                if row["provider_id"] != provider_id:
                    raise ExchangeUnauthorized("provider_mismatch")
                if row["delivery_state"] == "awaiting_external_claim":
                    return row["delivery_state"]
                self._require_delivery_lease(row, provider_id, owner_id, delivery_token, fence, now)
                if row["delivery_state"] != "awaiting_delivery":
                    raise ExchangeConflict("request is not awaiting delivery")
                cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state='awaiting_external_claim',
                    delivery_owner=NULL,delivery_token=NULL,delivery_lease_until=NULL,updated_at=%s
                    WHERE request_id=%s""", (now, row["request_id"]))
                row.update(delivery_state="awaiting_external_claim")
                self._event(cur, row, "delivered", f"delivered-{row['delivery_attempts']}", owner_id,
                            {"state": row["delivery_state"], "delivery_attempt": row["delivery_attempts"]})
                return row["delivery_state"]

    def fail_delivery(self, request_id: str, correlation_id: str, provider_id: str, *,
                      owner_id: str, delivery_token: str, fence: int, error_code: str,
                      retryable=True) -> str:
        if not _SAFE_CODE.fullmatch(error_code) or type(retryable) is not bool:
            raise ValueError("delivery diagnostic must be a sanitized code")
        now = _utc(self.clock())
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                self._require_delivery_lease(row, provider_id, owner_id, delivery_token, fence, now)
                terminal = (not retryable or row["delivery_attempts"] >= _MAX_DELIVERY_ATTEMPTS
                            or row["deadline_at"] <= now)
                state = "expired" if row["deadline_at"] <= now else ("failed" if terminal else "awaiting_delivery")
                delay = min(300, 2 ** min(row["delivery_attempts"], 8))
                cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state=%s,
                    next_delivery_at=%s,delivery_owner=NULL,delivery_token=NULL,delivery_lease_until=NULL,
                    last_error_code=%s,updated_at=%s WHERE request_id=%s""",
                    (state, now + timedelta(seconds=delay), error_code, now, row["request_id"]))
                row.update(delivery_state=state, last_error_code=error_code)
                self._event(cur, row, "delivery_failed", f"delivery-failure-{row['delivery_attempts']}",
                    owner_id, {"state": state, "error_code": error_code,
                               "retryable": retryable and state == "awaiting_delivery"})
                return state

    def claim(self, request_id: str, correlation_id: str, *, provider_id: str,
              principal_id: str, lease_seconds=120) -> ExchangeClaim:
        self._require_provider_principal(provider_id, principal_id)
        if not 1 <= lease_seconds <= 300:
            raise ExchangeUnauthorized("provider principal or lease is invalid")
        now = _utc(self.clock())
        new_token = uuid4()
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                if row["provider_id"] != provider_id:
                    raise ExchangeUnauthorized("provider_mismatch")
                if self._expire_if_due(cur, row, now, principal_id):
                    return None
                if row["delivery_state"] in ("response_received", "grace_consumed"):
                    if row["claim_owner"] == principal_id:
                        return ExchangeClaim(str(row["request_id"]), str(row["correlation_id"]),
                            str(row["claim_token"]), row["claim_fence"], row["claim_lease_until"], True)
                    raise ExchangeConflict("request already has a terminal response")
                if row["delivery_state"] not in ("awaiting_external_claim", "awaiting_response"):
                    raise ExchangeConflict("request is not available for external claim")
                if row["claim_lease_until"] and row["claim_lease_until"] > now:
                    if row["claim_owner"] == principal_id:
                        return ExchangeClaim(str(row["request_id"]), str(row["correlation_id"]),
                            str(row["claim_token"]), row["claim_fence"], row["claim_lease_until"], True)
                    raise ExchangeConflict("another external claim is active")
                fence = row["claim_fence"] + 1
                lease_until = min(row["deadline_at"], now + timedelta(seconds=lease_seconds))
                cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state='awaiting_response',
                    claim_owner=%s,claim_token=%s,claim_fence=%s,claim_lease_until=%s,
                    claim_attempts=claim_attempts+1,updated_at=%s WHERE request_id=%s""",
                    (principal_id, new_token, fence, lease_until, now, row["request_id"]))
                row.update(delivery_state="awaiting_response", claim_owner=principal_id,
                           claim_token=new_token, claim_fence=fence, claim_lease_until=lease_until,
                           claim_attempts=row["claim_attempts"] + 1)
                self._event(cur, row, "claimed", f"claim-{fence}", principal_id,
                    {"state": row["delivery_state"], "fence": fence,
                     "lease_until": lease_until.isoformat()})
                return ExchangeClaim(str(row["request_id"]), str(row["correlation_id"]),
                    str(new_token), fence, lease_until)

    def submit_response(self, request_id: str, correlation_id: str, *, provider_id: str,
                        principal_id: str, claim_token: str, fence: int,
                        idempotency_key: str, response: Mapping[str, Any]) -> str:
        clean = self._validate_response(response, request_id, correlation_id, provider_id)
        self._require_provider_principal(provider_id, principal_id)
        if (not isinstance(idempotency_key, str)
                or not 1 <= len(idempotency_key) <= 240):
            raise ExchangeUnauthorized("response principal or idempotency key is invalid")
        response_bytes = _json(clean).encode("utf-8")
        if len(response_bytes) > _MAX_RESPONSE_BYTES:
            raise ValueError("external reasoning response exceeds 16 KiB")
        digest = hashlib.sha256(response_bytes).hexdigest()
        now = _utc(self.clock())
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                if row["provider_id"] != provider_id:
                    raise ExchangeUnauthorized("provider_mismatch")
                if row["response_sha256"]:
                    if row["response_sha256"] == digest and row["response_idempotency_key"] == idempotency_key:
                        return row["response_sha256"]
                    raise ExchangeConflict("a different response is already durable")
                if self._expire_if_due(cur, row, now, principal_id):
                    return "expired"
                if row["delivery_state"] == "expired":
                    return "expired"
                if (row["delivery_state"] != "awaiting_response"
                        or row["claim_owner"] != principal_id
                        or str(row["claim_token"]) != claim_token
                        or row["claim_fence"] != fence
                        or row["claim_lease_until"] is None or row["claim_lease_until"] <= now):
                    raise ExchangeConflict("active response claim and fencing token required")
                provenance = {"schema_version": "rv.external-reasoning.provenance.v1",
                    "provider_id": provider_id, "provider_model": clean["provider_model"],
                    "response_id": clean["response_id"], "received_at": now.isoformat(),
                    "claim_fence": fence}
                cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state='response_received',
                    response_payload=%s::jsonb,response_sha256=%s,response_provenance=%s::jsonb,
                    response_idempotency_key=%s,response_received_at=%s,updated_at=%s WHERE request_id=%s""",
                    (_json(clean), digest, _json(provenance), idempotency_key, now, now, row["request_id"]))
                row.update(delivery_state="response_received", response_sha256=digest,
                           response_payload=clean, response_provenance=provenance)
                self._event(cur, row, "response_received", "response-received", principal_id,
                    {"state": row["delivery_state"], "response_sha256": digest,
                     "provider_id": provider_id, "provider_model": clean["provider_model"]})
        return digest

    def consume(self, request_id: str, correlation_id: str, *, principal_id: str,
                authorize, lease_seconds=60) -> ExchangeConsumption:
        if not 1 <= lease_seconds <= 300:
            raise ValueError("consumption lease is out of range")
        now = _utc(self.clock())
        token = uuid4()
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                if principal_id != row["originating_resident_id"]:
                    raise ExchangeUnauthorized("originating resident required")
                if row["delivery_state"] == "grace_consumed":
                    if row["consumption_key"] != f"external-reasoning-consumed:{row['request_id']}":
                        raise ExchangeUnauthorized("consumption owner mismatch")
                    self._authorize_stored(row, principal_id, authorize)
                    original = self._request_from_payload(row["request_payload"])
                    return ExchangeConsumption(str(row["request_id"]), str(row["correlation_id"]),
                        row["consumption_key"], "", row["consumption_fence"],
                        row["consumed_at"], row["response_payload"], original, True)
                if row["delivery_state"] != "response_received":
                    raise ExchangeConflict("no completed advisory response is available")
                self._authorize_stored(row, principal_id, authorize)
                active = row["consumption_lease_until"] and row["consumption_lease_until"] > now
                if active and row["consumption_owner"] != principal_id:
                    raise ExchangeConflict("another Grace consumer holds the active lease")
                fence = row["consumption_fence"] + (0 if active else 1)
                token = row["consumption_token"] if active else token
                lease_until = min(row["deadline_at"], now + timedelta(seconds=lease_seconds))
                consumption_key = row["consumption_key"] or f"external-reasoning-consumed:{row['request_id']}"
                cur.execute("""UPDATE external_reasoning_exchanges SET consumption_key=%s,
                    consumption_owner=%s,consumption_token=%s,consumption_fence=%s,
                    consumption_lease_until=%s,updated_at=%s WHERE request_id=%s""",
                    (consumption_key, principal_id, token, fence, lease_until, now, row["request_id"]))
                row.update(consumption_key=consumption_key, consumption_owner=principal_id,
                           consumption_token=token, consumption_fence=fence,
                           consumption_lease_until=lease_until)
                self._event(cur, row, "consumption_claimed", f"consume-claim-{fence}", principal_id,
                    {"state": row["delivery_state"], "fence": fence})
                response = row["response_payload"]
                original = self._request_from_payload(row["request_payload"])
                return ExchangeConsumption(str(row["request_id"]), str(row["correlation_id"]),
                    consumption_key, str(token), fence, lease_until, response, original, active)

    def acknowledge_consumed(self, request_id: str, correlation_id: str, *,
                             principal_id: str, consumption_key: str,
                             consumption_token: str, fence: int,
                             result_reference: str, authorize) -> str:
        if not isinstance(result_reference, str) or not 1 <= len(result_reference) <= 512:
            raise ValueError("durable Grace result reference is required")
        now = _utc(self.clock())
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                if row["delivery_state"] == "grace_consumed":
                    if (row["originating_resident_id"] == principal_id and
                            row["consumption_key"] == consumption_key):
                        return "grace_consumed"
                    raise ExchangeConflict("consumption already acknowledged under another key")
                if (row["delivery_state"] != "response_received"
                        or row["consumption_owner"] != principal_id
                        or row["consumption_key"] != consumption_key
                        or str(row["consumption_token"]) != consumption_token
                        or row["consumption_fence"] != fence
                        or row["consumption_lease_until"] is None
                        or row["consumption_lease_until"] <= now):
                    raise ExchangeConflict("active Grace consumption lease required")
                self._authorize_stored(row, principal_id, authorize)
                result = {"result_reference": result_reference,
                          "result_sha256": hashlib.sha256(result_reference.encode()).hexdigest(),
                          "advisory_sha256": row["response_sha256"]}
                cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state='grace_consumed',
                    consumed_at=%s,consumption_result=%s::jsonb,consumption_owner=NULL,
                    consumption_token=NULL,
                    consumption_lease_until=NULL,updated_at=%s WHERE request_id=%s""",
                    (now, _json(result), now, row["request_id"]))
                row.update(delivery_state="grace_consumed", consumed_at=now,
                           consumption_result=result)
                self._event(cur, row, "grace_consumed", "grace-consumed", principal_id,
                    {"state": "grace_consumed", "consumption_key": consumption_key,
                     **result})
                return "grace_consumed"

    def status(self, request_id: str, correlation_id: str) -> dict[str, Any]:
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            row = self._lock(cur, request_id, correlation_id, lock=False)
            return {"request_id": str(row["request_id"]),
                "correlation_id": str(row["correlation_id"]),
                "objective_id": row["objective_id"], "delivery_state": row["delivery_state"],
                "diagnostic_state": self.STATES[row["delivery_state"]],
                "provider_id": row["provider_id"], "classification": row["classification"],
                "context_sha256": row["context_sha256"],
                "requested_at": row["requested_at"].isoformat(),
                "deadline_at": row["deadline_at"].isoformat(),
                "delivery_attempts": row["delivery_attempts"],
                "claim_attempts": row["claim_attempts"],
                "response_sha256": row["response_sha256"],
                "response_provenance": row["response_provenance"],
                "consumption_key": row["consumption_key"],
                "consumed_at": row["consumed_at"].isoformat() if row["consumed_at"] else None,
                "last_error_code": row["last_error_code"]}

    def pending_responses(self, originating_resident_id: str, *, limit=10) -> list[dict[str, str]]:
        """List only response/correlation IDs awaiting the originating resident.

        Bodies remain available only through the exact-grant-checked ``consume``
        transition. The service cycle can call this without holding a transaction
        while the resident model reasons over a response.
        """
        if (not isinstance(originating_resident_id, str) or not originating_resident_id
                or len(originating_resident_id) > 256 or type(limit) is not int
                or not 1 <= limit <= 50):
            raise ValueError("resident identity and bounded response limit are required")
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            cur.execute("""SELECT request_id::text AS request_id,correlation_id::text AS correlation_id
                FROM external_reasoning_exchanges
                WHERE originating_resident_id=%s AND delivery_state='response_received'
                ORDER BY response_received_at,request_id LIMIT %s""",
                (originating_resident_id, limit))
            return cur.fetchall()

    def events(self, request_id: str, correlation_id: str) -> list[dict[str, Any]]:
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            self._lock(cur, request_id, correlation_id, lock=False)
            cur.execute("""SELECT sequence,event_id::text,event_type,idempotency_key,actor_id,
                    payload,occurred_at FROM external_reasoning_exchange_events
                WHERE request_id=%s ORDER BY sequence""", (request_id,))
            return [dict(row) for row in cur.fetchall()]

    def _authorize_stored(self, row, principal_id, authorize):
        payload = row["request_payload"]
        original = self._request_from_payload(payload)
        envelope = EscalationRequest(
            schema_version="rv.resident.escalation-request.v1",
            escalation_id=str(row["request_id"]), original_request_id=row["original_request_id"],
            office_id=original.office_id, assignment_id=original.assignment_id,
            assignment_revision=original.assignment_revision,
            binding_revision=original.binding_revision,
            implementation_revision=original.implementation_revision,
            context_sha256=row["context_sha256"], reason=row["reason"],
            target_provider_id=row["provider_id"], max_tokens=payload["max_tokens"],
            timeout_seconds=payload["timeout_seconds"])
        self._authorize(envelope, original, principal_id, authorize)

    @staticmethod
    def _request_from_payload(payload):
        original_doc = payload["original_request"]
        return ReasoningRequest(**{**original_doc,
            "verified_knowledge": tuple(original_doc.get("verified_knowledge", ()))})

    def _expire_if_due(self, cur, row, now, actor):
        if row["deadline_at"] <= now and row["delivery_state"] not in (
                "response_received", "grace_consumed", "expired", "failed"):
            self._transition(cur, row, "expired", "request_expired", actor,
                             "request_deadline_elapsed")
            return True
        return False

    def _transition(self, cur, row, state, event, actor, error_code=None):
        now = _utc(self.clock())
        cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state=%s,
            last_error_code=%s,delivery_owner=NULL,delivery_token=NULL,delivery_lease_until=NULL,
            claim_owner=NULL,claim_token=NULL,claim_lease_until=NULL,updated_at=%s
            WHERE request_id=%s""", (state, error_code, now, row["request_id"]))
        row.update(delivery_state=state, last_error_code=error_code)
        self._event(cur, row, event, event, actor,
                    {"state": state, "error_code": error_code} if error_code else {"state": state})

    def _lock(self, cur, request_id, correlation_id=None, *, lock=True):
        try:
            request_uuid = UUID(str(request_id))
            correlation_uuid = UUID(str(correlation_id)) if correlation_id is not None else None
        except (ValueError, TypeError, AttributeError):
            raise ExchangeNotFound("exchange identity not found") from None
        cur.execute("SELECT * FROM external_reasoning_exchanges WHERE request_id=%s" +
                    (" FOR UPDATE" if lock else ""), (request_uuid,))
        row = cur.fetchone()
        if row is None or (correlation_uuid is not None and row["correlation_id"] != correlation_uuid):
            raise ExchangeNotFound("exchange identity not found")
        return row

    @staticmethod
    def _require_delivery_lease(row, provider_id, owner_id, token, fence, now):
        if (row["provider_id"] != provider_id or row["delivery_owner"] != owner_id
                or str(row["delivery_token"]) != token or row["delivery_fence"] != fence
                or row["delivery_lease_until"] is None or row["delivery_lease_until"] <= now):
            raise ExchangeConflict("valid delivery fencing lease required")

    @staticmethod
    def _validate_response(response, request_id, correlation_id, provider_id):
        keys = {"schema_version", "request_id", "correlation_id", "response_id",
                "advisory", "evidence_references", "provider_id", "provider_model"}
        if not isinstance(response, Mapping) or set(response) != keys:
            raise ValueError("response does not match the versioned advisory schema")
        advisory = response["advisory"]
        refs = response["evidence_references"]
        if (response["schema_version"] != DurableExternalReasoningExchange.RESPONSE_SCHEMA
                or response["request_id"] != str(request_id)
                or response["correlation_id"] != str(correlation_id)
                or response["provider_id"] != provider_id
                or not isinstance(response["response_id"], str) or not response["response_id"]
                or len(response["response_id"]) > 160
                or not isinstance(advisory, str) or not advisory.strip() or len(advisory) > 8000
                or not isinstance(refs, list) or len(refs) > 32
                or any(not isinstance(ref, str) or not ref or len(ref) > 512 for ref in refs)
                or not isinstance(response["provider_model"], str)
                or not response["provider_model"] or len(response["provider_model"]) > 160):
            raise ValueError("response fields violate the bounded advisory contract")
        return dict(response)
