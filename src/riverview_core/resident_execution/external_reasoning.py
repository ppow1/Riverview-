# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/external_reasoning.py
# Component: RESIDENT-REASONING
# Revision: 1.1.9
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Bind atomic retry consumption to root assignment and S3 step identity.
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Consume the exact S3 retry exception atomically with provider admission.
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025-HOTFIX | Avoid row locking on append-only grant events; unique consumption remains the concurrency fence.
# Changed: 2026-10-24 UTC | RV-GRACE-PERFORMANCE-INPUT-RETRY-20261024 | Expose only the last provider error status and input parameter for bounded retry selection.
# Changed: 2026-10-24 UTC | RV-GRACE-LUNA-DENIAL-TERMINALIZATION-20261024 | Terminalize a fenced provider request when authorization blocks it before any paid attempt.
# Changed: 2026-10-24 UTC | RV-GRACE-EVALUATION-BOUNDED-OUTPUT-RETRY | Expose durable request payload metadata to the bounded evaluation retry gate.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Bind system-owned lifecycle criteria into exact external review subjects
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Accept sanitized C2 bridge exception codes as terminal ambiguous receipts.
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Bind duplicate receipt replay to a one-way lease-token digest.
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Import namespace UUID function for stable doorbell attempt identity.
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Wrap doorbell claims and receipts in existing fenced exchange lifecycle.
# Purpose: Persist and resume authorized external reasoning exchanges
# Execution Model: Request-driven PostgreSQL outbox, bounded leases, no polling loop
# Observability: Correlated state and sanitized append-only transition diagnostics
# Dependencies: Psycopg 3; PostgresLedger; ReasoningEscalationRouter
# Authority: Exact resident.reasoning.escalate grant; returned advice cannot authorize work
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Initial durable exchange contract
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Permit scoped pull/recovery of delivered provider requests
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Expose bounded response-received IDs for Grace's durable consumer
# Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Provide pending-objective guard and make retry identity independent of first-delivery deadline
# Changed: 2026-10-18 UTC | RV-C3-EXACT-PROPOSAL-REVIEW-001 | Persist immutable review subject and expose its digest in provider status
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Add explicit Steward-originated list/claim/response/status operations with durable actor provenance and review-subject digest binding
# Changed: 2026-10-19 UTC | RV-P0-W3-PR150-COMBINED-CI-CORRECTION | Preserve C3 conflict semantics for provider reviews and C4 unauthorized semantics for Steward digest failures.
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Validate typed per-step artifact requirements in immutable review subjects
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
from decimal import Decimal
import hashlib
import json
import os
import re
from typing import Any, Mapping
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

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
    review_subject: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DoorbellDeliveryClaim:
    """Body-free fenced wake claim returned to the local browser dispatcher."""
    request_id: str
    correlation_id: str
    provider_id: str
    attempt_id: str
    lease_token: str
    fence: int
    lease_until: datetime
    deadline_at: datetime


_ALLOWED_CLASSIFICATIONS = {"institutional", "confidential"}
_SAFE_CODE = re.compile(r"^[a-z0-9_]{1,80}$")
_DOORBELL_ERROR = re.compile(r"^(?:RIV-PLY-\d{4}|doorbell_(?:failure|exception))$")
_DOORBELL_RETRYABLE = frozenset({
    "RIV-PLY-0002", "RIV-PLY-0005", "RIV-PLY-0006", "RIV-PLY-0007",
    "RIV-PLY-0008", "RIV-PLY-0010", "RIV-PLY-0011", "RIV-PLY-0012",
    "RIV-PLY-0013", "RIV-PLY-0015", "RIV-PLY-0016",
})
_MAX_CONTEXT_BYTES = 32 * 1024
_MAX_RESPONSE_BYTES = 16 * 1024
_MAX_DELIVERY_ATTEMPTS = 5
REVIEW_SUBJECT_SCHEMA = "rv.grace.proposal-review-subject.v1"
MAX_REVIEW_REVISIONS = 3


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def proposal_review_content(proposal):
    """Return execution-relevant proposal content, excluding model telemetry."""
    from dataclasses import is_dataclass
    from ..resident_reasoning import (ArtifactRequirement, PlanProposal, PlanStep,
                                      lifecycle_evidence_event)
    if is_dataclass(proposal):
        proposal = asdict(proposal)
    if not isinstance(proposal, Mapping):
        raise ValueError("review proposal must be an object")
    summary, steps = proposal.get("summary"), proposal.get("steps")
    system_owned = proposal.get("system_owned_criteria", ())
    if (not isinstance(summary, str) or not summary.strip() or len(summary) > 4000
            or not isinstance(steps, (list, tuple)) or not 1 <= len(steps) <= 20
            or not isinstance(system_owned, (list, tuple))
            or any(not isinstance(item, str) or lifecycle_evidence_event(item) is None
                   for item in system_owned)):
        raise ValueError("review proposal content is invalid")
    normalized_steps = []
    allowed_step_keys = set(PlanStep.__dataclass_fields__)
    for step in steps:
        if is_dataclass(step):
            step = asdict(step)
        if not isinstance(step, Mapping) or frozenset(step) not in {
                frozenset(allowed_step_keys), frozenset(allowed_step_keys - {"artifact_requirements"})}:
            raise ValueError("review proposal step is invalid")
        data = dict(step)
        data.setdefault("artifact_requirements", [])
        for key in ("acceptance_criteria", "depends_on", "authorized_paths", "test_targets",
                    "artifact_requirements"):
            if not isinstance(data[key], (tuple, list)):
                raise ValueError("review proposal arrays are invalid")
            if key == "artifact_requirements":
                data[key] = tuple(ArtifactRequirement(
                    item["name"], item["path"], item["media_type"],
                    tuple(item["acceptance_criteria"]), item.get("max_bytes", 32768))
                    if isinstance(item, Mapping) else item for item in data[key])
            else:
                data[key] = tuple(data[key])
        normalized_steps.append(PlanStep(**data))
    normalized = PlanProposal(summary, tuple(normalized_steps), 0,
                              system_owned_criteria=tuple(system_owned))
    content = {"summary": normalized.summary,
               "steps": [asdict(step) for step in normalized.steps]}
    if normalized.system_owned_criteria:
        content["system_owned_criteria"] = list(normalized.system_owned_criteria)
    return content


def build_review_subject(subject_id, revision, proposal):
    content = proposal_review_content(proposal)
    value = {"subject_id": str(subject_id), "revision": revision, "proposal": content}
    return validate_review_subject({"schema_version": REVIEW_SUBJECT_SCHEMA,
                                    **value, "sha256": _digest(value)})


def validate_review_subject(value):
    """Validate exact immutable proposal bytes and the C2/C4 digest contract."""
    if (not isinstance(value, Mapping) or set(value) != {
            "schema_version", "subject_id", "revision", "proposal", "sha256"}
            or value.get("schema_version") != REVIEW_SUBJECT_SCHEMA
            or type(value.get("revision")) is not int
            or not 1 <= value["revision"] <= MAX_REVIEW_REVISIONS
            or not isinstance(value.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"])):
        raise ValueError("review subject fields are invalid")
    try:
        UUID(str(value["subject_id"]))
        content = proposal_review_content(value["proposal"])
        expected = _digest({"subject_id": str(value["subject_id"]),
                            "revision": value["revision"], "proposal": content})
        if len(_json(value).encode("utf-8")) > 16 * 1024:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("review subject content is invalid") from None
    if expected != value["sha256"]:
        raise ValueError("review subject digest mismatch")
    return {"schema_version": REVIEW_SUBJECT_SCHEMA,
            "subject_id": str(value["subject_id"]), "revision": value["revision"],
            "sha256": expected, "proposal": content}


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

    def begin_provider_attempt(self, request_id, correlation_id, *, principal_id,
                               reserved_cost, additional_limit, baseline_total, total_credit):
        """Reserve one bounded API attempt durably; a started request is never replayed."""
        if (principal_id != "service:provider-gpt-6-luna" or reserved_cost not in {0.01, 0.05} or
                baseline_total != 0.04104010 or total_credit != 5.0 or
                additional_limit != round(total_credit - baseline_total, 8)):
            raise ExchangeUnauthorized("provider_attempt_policy_invalid")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                if row["provider_id"] != "gpt-6-luna" or row["claim_owner"] != principal_id:
                    raise ExchangeUnauthorized("provider_attempt_route_mismatch")
                cur.execute("""SELECT event_type FROM external_reasoning_exchange_events
                    WHERE request_id=%s AND event_type='provider_attempt_started'""", (request_id,))
                if cur.fetchone():
                    return False
                authorization = self._reserve_supervisory_luna_call(cur, row, reserved_cost)
                if authorization is None and not self._is_supervisory_request(row):
                    legacy_id = self._reserve_experiment_luna_call(cur, row, reserved_cost)
                    authorization = ("experiment", legacy_id) if legacy_id else None
                elif authorization is not None:
                    authorization = ("supervisory", authorization)
                if authorization is None:
                    return False
                self._event(cur, row, "provider_attempt_started", "luna-api-attempt-started",
                    principal_id, {"provider_id": "gpt-6-luna", "provider_model": "gpt-6-luna",
                        "reserved_cost_usd": reserved_cost, "attempt": 1,
                        "authorization_kind": authorization[0],
                        "authorization_id": authorization[1]})
                return True

    @staticmethod
    def _is_supervisory_request(row):
        payload = row.get("request_payload")
        return isinstance(payload, dict) and payload.get("request_type") in {
            "cme_diagnostic_recovery", "performance_evaluation"}

    def _reserve_supervisory_luna_call(self, cur, row, reserved_cost):
        """Debit the shared no-count-cap budget for only the two supervisory request types."""
        if not self._is_supervisory_request(row) or reserved_cost != 0.05:
            return None
        from psycopg import sql
        request_type = row["request_payload"]["request_type"]
        auth = None
        cur.execute("""SELECT * FROM grace_supervisory_authorizations
            WHERE status='active' AND activated_at<=clock_timestamp()
              AND (valid_until IS NULL OR valid_until>clock_timestamp())
            ORDER BY activated_at DESC LIMIT 1 FOR UPDATE""")
        auth = cur.fetchone()
        if auth is None:
            return None
        authority_schema = os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority")
        cur.execute(sql.SQL("SELECT {}.active_grace_supervisory_luna_grant(%s) AS grant_id").format(
            sql.Identifier(authority_schema)), (auth["authority_grant_id"],))
        grant = cur.fetchone()
        if grant is None or grant["grant_id"] != auth["authority_grant_id"]:
            return None
        if reserved_cost > float(auth["per_request_limit_usd"]):
            return None
        payload = row.get("request_payload", {})
        assignment = payload.get("assignment") if isinstance(payload, dict) else None
        if not isinstance(assignment, dict) and isinstance(payload, dict):
            original_request = payload.get("original_request")
            assignment = (original_request.get("assignment")
                if isinstance(original_request, dict) else None)
        assignment = assignment if isinstance(assignment, dict) else {}
        assignment_id = assignment.get("assignment_id")
        progress_seq = assignment.get("cme_progress_seq")
        stall_event_id = assignment.get("cme_event_id")
        retry_grant = None
        if request_type == "cme_diagnostic_recovery" and assignment_id is not None:
            progress = str(progress_seq) if progress_seq is not None else None
            cur.execute("""SELECT 1 FROM grace_supervisory_authorization_events e
                WHERE e.authorization_id=%s AND e.event_type='luna_reserved'
                  AND e.objective_id=%s AND e.payload->>'request_type'=%s
                  AND (
                    (e.payload->>'assignment_id'=%s AND
                     e.payload->>'cme_progress_seq' IS NOT DISTINCT FROM %s)
                    OR EXISTS (
                        SELECT 1 FROM external_reasoning_exchanges x
                        WHERE x.request_id=e.request_id
                          AND x.request_payload->'original_request'->'assignment'->>'assignment_id'=%s
                          AND x.request_payload->'original_request'->'assignment'->>'cme_progress_seq'
                              IS NOT DISTINCT FROM %s)) LIMIT 1""",
                (auth["authorization_id"], row.get("objective_id"), request_type,
                 str(assignment_id), progress, str(assignment_id), progress))
            if cur.fetchone():
                if not isinstance(stall_event_id, str) or type(progress_seq) is not int:
                    return None
                # Authorization events are append-only and the runtime role has no
                # UPDATE privilege. The unique consumption idempotency key below
                # atomically arbitrates concurrent use without locking this row.
                cur.execute("""SELECT event_id,payload FROM grace_supervisory_authorization_events g
                    WHERE g.authorization_id=%s AND g.event_type='cme_retry_authorized'
                      AND g.objective_id=%s AND g.payload->>'request_type'=%s
                      AND g.payload->>'assignment_id'=%s
                      AND g.payload->>'objective_assignment_id'=%s
                      AND g.payload->>'step_id'=%s
                      AND g.payload->>'stall_event_id'=%s
                      AND (g.payload->>'progress_sequence')::integer=%s
                      AND (g.payload->>'objective_revision')::integer=%s
                      AND (g.payload->>'expires_at')::timestamptz>clock_timestamp()
                      AND (g.payload->>'max_attempts')::integer=1
                      AND NOT EXISTS (SELECT 1 FROM grace_supervisory_authorization_events c
                        WHERE c.authorization_id=g.authorization_id
                          AND c.event_type='cme_retry_consumed'
                          AND c.payload->>'grant_event_id'=g.event_id::text)
                    """, (auth["authorization_id"], row.get("objective_id"),
                        request_type, str(assignment_id),
                        str(assignment.get("objective_assignment_id")),
                        str(assignment.get("step_id")), stall_event_id, progress_seq,
                        int(assignment.get("objective_revision", -1))))
                retry_grant = cur.fetchone()
                if retry_grant is None:
                    return None
        cur.execute("""SELECT
            COALESCE(sum((payload->>'cost_usd')::numeric)
                FILTER (WHERE event_type='luna_settled'),0) AS spent,
            COALESCE(sum((payload->>'reserved_cost_usd')::numeric)
                FILTER (WHERE event_type='luna_reserved' AND NOT EXISTS (
                    SELECT 1 FROM grace_supervisory_authorization_events settled
                    WHERE settled.authorization_id=grace_supervisory_authorization_events.authorization_id
                      AND settled.event_type='luna_settled'
                      AND settled.request_id=grace_supervisory_authorization_events.request_id)),0) AS outstanding
            FROM grace_supervisory_authorization_events WHERE authorization_id=%s""",
            (auth["authorization_id"],))
        usage = cur.fetchone()
        if usage["spent"] + usage["outstanding"] + Decimal(str(reserved_cost)) > auth["total_budget_usd"]:
            return None
        authorization_id = str(auth["authorization_id"])
        request_id = str(row["request_id"])
        cur.execute("""INSERT INTO grace_supervisory_authorization_events
            (authorization_id,event_type,idempotency_key,objective_id,request_id,payload)
            VALUES (%s,'luna_reserved',%s,%s,%s,%s::jsonb)
            ON CONFLICT (idempotency_key) DO NOTHING""",
            (auth["authorization_id"], f"grace-supervision:{authorization_id}:luna:{request_id}",
             row.get("objective_id"), row["request_id"], _json({
                "request_type": request_type, "reserved_cost_usd": reserved_cost,
                "provider_id": "gpt-6-luna", "assignment_id": assignment_id,
                "cme_progress_seq": progress_seq,
                **({"cme_retry_grant_event_id": str(retry_grant["event_id"])}
                    if retry_grant is not None else {})})))
        if retry_grant is not None:
            cur.execute("""INSERT INTO grace_supervisory_authorization_events
                (authorization_id,event_type,idempotency_key,objective_id,request_id,payload)
                VALUES (%s,'cme_retry_consumed',%s,%s,%s,%s::jsonb)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING event_id""",
                (auth["authorization_id"],
                 "grace-supervision:cme-retry-consumed:" + stall_event_id,
                 row.get("objective_id"), row["request_id"], _json({
                    "schema": "rv.grace.cme-retry-consumption.v1",
                    "grant_event_id": str(retry_grant["event_id"]),
                    "objective_id": row.get("objective_id"),
                    "assignment_id": assignment_id,
                    "objective_assignment_id": assignment.get("objective_assignment_id"),
                    "step_id": assignment.get("step_id"),
                    "stall_event_id": stall_event_id,
                    "progress_sequence": progress_seq,
                    "request_id": str(row["request_id"]),
                    "provider_id": "gpt-6-luna",
                    "reserved_cost_usd": reserved_cost})))
            if cur.fetchone() is None:
                raise RuntimeError("cme_retry_exception_already_consumed")
        return authorization_id

    def finish_provider_attempt(self, request_id, correlation_id, *, status,
                                failure_type=None, usage=None):
        if status not in {"failed", "settled"}:
            raise ValueError("provider attempt status is invalid")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                payload = {"status": status, **({"failure_type": failure_type}
                    if failure_type else {}), **({"usage": usage} if usage else {})}
                self._event(cur, row, "provider_attempt_settled", "luna-api-attempt-settled",
                    "service:provider-gpt-6-luna", payload)
                self._settle_experiment_luna_call(cur, row, usage, status)

    def _reserve_experiment_luna_call(self, cur, row, reserved_cost):
        """Reserve one Luna request under the exact active experiment grant."""
        from psycopg import sql
        from .grace_experiment_authorization import GraceExperimentAuthorization
        objective_id, revision = row.get("objective_id"), row.get("proposal_revision")
        if not isinstance(objective_id, str) or type(revision) is not int:
            return None
        scope_ref = GraceExperimentAuthorization.scope_ref(objective_id, revision)
        cur.execute("""SELECT * FROM grace_experiment_authorizations
            WHERE objective_id=%s AND objective_revision=%s AND status='active'
              AND activated_at<=clock_timestamp() AND expires_at>clock_timestamp()
            ORDER BY activated_at DESC LIMIT 1 FOR UPDATE""", (objective_id, revision))
        auth = cur.fetchone()
        if auth is None:
            return None
        cur.execute("""SELECT occurred_at,payload FROM grace_experiment_authorization_events
            WHERE authorization_id=%s AND event_type='amended'
            ORDER BY occurred_at,event_id LIMIT 1""", (auth["authorization_id"],))
        amendment = cur.fetchone()
        request_type = (row.get("request_payload", {}).get("request_type")
            if isinstance(row.get("request_payload"), dict) else None)
        if amendment is not None:
            allocations = amendment["payload"].get("additional_request_allocations", {})
            allocation = allocations.get(request_type, 0) if isinstance(allocations, dict) else 0
            if type(allocation) is not int or allocation < 1:
                return None
            cur.execute("""SELECT count(*) AS used FROM grace_experiment_authorization_events
                WHERE authorization_id=%s AND event_type='luna_reserved'
                  AND occurred_at>%s AND payload->>'request_type'=%s""",
                (auth["authorization_id"], amendment["occurred_at"], request_type))
            if int(cur.fetchone()["used"]) >= allocation:
                return None
        authority_schema = os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority")
        cur.execute(sql.SQL("SELECT {}.active_grace_autonomy_experiment_grant(%s,%s) AS grant_id").format(
            sql.Identifier(authority_schema)), (auth["authority_grant_id"], scope_ref))
        experiment_grant = cur.fetchone()
        cur.execute(sql.SQL("SELECT {}.active_grace_luna_escalation_grant() AS grant_id").format(
            sql.Identifier(authority_schema)))
        luna_grant = cur.fetchone()
        if (experiment_grant is None or experiment_grant["grant_id"] != auth["authority_grant_id"] or
                luna_grant is None or luna_grant["grant_id"] != auth["luna_authority_grant_id"]):
            return None
        cur.execute("""SELECT count(*) AS used FROM grace_experiment_authorization_events
            WHERE authorization_id=%s AND event_type='luna_reserved'""", (auth["authorization_id"],))
        if int(cur.fetchone()["used"]) >= int(auth["max_luna_requests"]):
            return None
        cur.execute("""SELECT
            COALESCE(sum((payload->>'cost_usd')::numeric),0) AS settled,
            COALESCE((SELECT sum((reserved.payload->>'reserved_cost_usd')::numeric)
                FROM grace_experiment_authorization_events reserved
                WHERE reserved.authorization_id=%s AND reserved.event_type='luna_reserved'
                  AND NOT EXISTS (SELECT 1 FROM grace_experiment_authorization_events paid
                    WHERE paid.authorization_id=reserved.authorization_id
                      AND paid.event_type='luna_settled' AND paid.request_id=reserved.request_id)),0)
                AS outstanding
            FROM grace_experiment_authorization_events
            WHERE authorization_id=%s AND event_type='luna_settled'""",
            (auth["authorization_id"], auth["authorization_id"]))
        spend = cur.fetchone()
        if (float(auth["prior_spend_usd"]) + float(spend["settled"]) +
                float(spend["outstanding"]) + reserved_cost > float(auth["total_budget_usd"])):
            return None
        auth_id = str(auth["authorization_id"])
        cur.execute("""INSERT INTO grace_experiment_authorization_events
            (authorization_id,event_type,idempotency_key,objective_id,request_id,payload)
            VALUES (%s,'luna_reserved',%s,%s,%s,%s::jsonb)
            ON CONFLICT (idempotency_key) DO NOTHING""",
            (auth["authorization_id"], f"grace-experiment:{auth_id}:luna:{row['request_id']}",
             objective_id, row["request_id"], _json({"reserved_cost_usd": reserved_cost,
                "provider_id": "gpt-6-luna", "proposal_revision": revision,
                **({"request_type": request_type} if amendment is not None else {})})))
        return auth_id

    def _settle_experiment_luna_call(self, cur, row, usage, status):
        objective_id, revision = row.get("objective_id"), row.get("proposal_revision")
        if not isinstance(objective_id, str) or type(revision) is not int:
            return
        cur.execute("""SELECT authorization_id,total_budget_usd,per_request_limit_usd
            FROM grace_supervisory_authorizations auth
            WHERE EXISTS (SELECT 1 FROM grace_supervisory_authorization_events e
                WHERE e.authorization_id=auth.authorization_id AND e.event_type='luna_reserved'
                  AND e.request_id=%s) LIMIT 1""", (row["request_id"],))
        supervisory = cur.fetchone()
        if supervisory is not None:
            cost = (usage or {}).get("cost_usd") if isinstance(usage, dict) else None
            exact_cost = Decimal(str(cost)) if isinstance(cost, (int, float)) else supervisory["per_request_limit_usd"]
            payload = {"status": status, "cost_usd": str(exact_cost),
                "cost_is_reserved_estimate": not isinstance(cost, (int, float)),
                "per_request_limit_usd": str(supervisory["per_request_limit_usd"]),
                "usage": usage if isinstance(usage, dict) else {}}
            auth_id = str(supervisory["authorization_id"])
            cur.execute("""INSERT INTO grace_supervisory_authorization_events
                (authorization_id,event_type,idempotency_key,objective_id,request_id,payload)
                VALUES (%s,'luna_settled',%s,%s,%s,%s::jsonb)
                ON CONFLICT (idempotency_key) DO NOTHING""",
                (supervisory["authorization_id"],
                 f"grace-supervision:{auth_id}:luna-settled:{row['request_id']}",
                 objective_id, row["request_id"], _json(payload)))
            cur.execute("""SELECT COALESCE(sum((payload->>'cost_usd')::numeric),0) AS spent
                FROM grace_supervisory_authorization_events
                WHERE authorization_id=%s AND event_type='luna_settled'""",
                (supervisory["authorization_id"],))
            if cur.fetchone()["spent"] >= supervisory["total_budget_usd"]:
                cur.execute("UPDATE grace_supervisory_authorizations SET status='exhausted' WHERE authorization_id=%s AND status='active'",
                            (supervisory["authorization_id"],))
            return
        cur.execute("""SELECT authorization_id FROM grace_experiment_authorizations
            WHERE objective_id=%s AND objective_revision=%s AND experiment_key='grace-autonomy-luna-r2'
            ORDER BY activated_at DESC LIMIT 1""", (objective_id, revision))
        auth = cur.fetchone()
        if auth is None:
            return
        cost = (usage or {}).get("cost_usd") if isinstance(usage, dict) else None
        exact_cost = cost if isinstance(cost, (int, float)) else 0.01
        auth_id = str(auth["authorization_id"])
        payload = {"status": status, "cost_usd": exact_cost,
            "cost_is_reserved_estimate": not isinstance(cost, (int, float)),
            "usage": usage if isinstance(usage, dict) else {}}
        cur.execute("""INSERT INTO grace_experiment_authorization_events
            (authorization_id,event_type,idempotency_key,objective_id,request_id,payload)
            VALUES (%s,'luna_settled',%s,%s,%s,%s::jsonb)
            ON CONFLICT (idempotency_key) DO NOTHING""",
            (auth["authorization_id"], f"grace-experiment:{auth_id}:luna-settled:{row['request_id']}",
             objective_id, row["request_id"], _json(payload)))

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
                         proposal_revision, classification, source_kind,
                         request_type):
        if (not isinstance(original, ReasoningRequest) or not isinstance(objective_id, str)
                or original.assignment_id != objective_id
                or not isinstance(originating_resident_id, str)
                or not originating_resident_id or len(originating_resident_id) > 256
                or classification not in _ALLOWED_CLASSIFICATIONS):
            raise ValueError("exchange origin, objective correlation, or classification is invalid")
        allowed = {"objective_reasoning": "conversation", "proposal_review": "conversation",
                   "cme_diagnostic_recovery": "cme_diagnostic_recovery",
                   "performance_evaluation": "performance_evaluation"}
        if (request_type not in allowed or source_kind != allowed[request_type] or
                (request_type in {"cme_diagnostic_recovery", "performance_evaluation"} and
                 original.trigger != request_type)):
            raise ValueError("exchange request type and source kind do not match")
        if source_kind == "conversation":
            try:
                UUID(str(conversation_id))
            except (ValueError, TypeError, AttributeError):
                raise ValueError("conversation_id must be a UUID") from None
            if type(message_sequence) is not int or message_sequence < 1:
                raise ValueError("conversation message sequence must be positive")
        elif conversation_id is not None or message_sequence is not None:
            raise ValueError("event-origin exchange cannot claim a conversation")
        if (proposal_id is None) != (proposal_revision is None):
            raise ValueError("proposal ID and exact revision must be supplied together")
        if proposal_id is not None and (not isinstance(proposal_id, str) or
                                        type(proposal_revision) is not int or proposal_revision < 1):
            raise ValueError("proposal reference is invalid")

    def submit(self, envelope: EscalationRequest, original: ReasoningRequest, *,
               principal_id: str, authorize, originating_resident_id: str,
               objective_id: str, conversation_id: str | None = None,
               message_sequence: int | None = None,
               idempotency_key: str, classification: str,
               deadline_at: datetime, proposal_id: str | None = None,
               proposal_revision: int | None = None,
               source_references: tuple[str, ...] = (),
               review_subject: Mapping[str, Any] | None = None,
               review_parent: Mapping[str, Any] | None = None,
               source_kind: str = "conversation",
               request_type: str = "objective_reasoning") -> ExchangeReceipt:
        """Authorize and durably enqueue before any delivery operation is possible."""
        self._validate_origin(original, originating_resident_id=originating_resident_id,
            objective_id=objective_id, conversation_id=conversation_id,
            message_sequence=message_sequence, proposal_id=proposal_id,
            proposal_revision=proposal_revision, classification=classification,
            source_kind=source_kind, request_type=request_type)
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
        if review_subject is not None:
            review_subject = validate_review_subject(review_subject)
        if review_parent is not None and (not isinstance(review_parent, Mapping)
                or set(review_parent) != {"request_id", "correlation_id", "response_sha256"}
                or not all(isinstance(review_parent[k], str) and review_parent[k]
                           for k in review_parent)
                or not re.fullmatch(r"[0-9a-f]{64}", review_parent["response_sha256"])):
            raise ValueError("review parent correlation is invalid")
        request_payload = {
            "schema_version": self.REQUEST_SCHEMA,
            "original_request": asdict(original),
            "reason": envelope.reason,
            "max_tokens": envelope.max_tokens,
            "timeout_seconds": envelope.timeout_seconds,
            "source_references": list(source_references),
            **({"review_subject": review_subject} if review_subject is not None else {}),
            **({"review_parent": dict(review_parent)} if review_parent is not None else {}),
        }
        if source_kind != "conversation":
            request_payload.update({"request_type": request_type, "source_kind": source_kind})
        encoded = _json(request_payload).encode("utf-8")
        if len(encoded) > _MAX_CONTEXT_BYTES:
            raise ValueError("external reasoning request exceeds 32 KiB")
        immutable = {
            "originating_resident_id": originating_resident_id,
            "objective_id": objective_id,
            "conversation_id": str(conversation_id) if conversation_id is not None else None,
            "message_sequence": message_sequence,
            "proposal_id": proposal_id,
            "proposal_revision": proposal_revision,
            "reason": envelope.reason,
            "context_sha256": envelope.context_sha256,
            "classification": classification,
            "provider_id": envelope.target_provider_id,
            "request_payload": request_payload,
        }
        if source_kind != "conversation":
            immutable["source_kind"] = source_kind
        request_hash = _digest(immutable)
        request_id = UUID(envelope.escalation_id)
        correlation_id = uuid4()
        db = self.ledger.db
        with db.transaction():
            with db.cursor() as cur:
                self._set_path(cur)
                cur.execute("""INSERT INTO external_reasoning_exchanges
                    (request_id,correlation_id,original_request_id,originating_resident_id,
                     objective_id,source_kind,conversation_id,message_sequence,proposal_id,proposal_revision,
                     request_schema,response_schema,reason,context_sha256,classification,
                     provider_id,idempotency_key,request_sha256,request_payload,delivery_state,
                     next_delivery_at,deadline_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,
                            'awaiting_delivery',%s,%s)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (request_id, correlation_id, original.request_id, originating_resident_id,
                     objective_id, source_kind, conversation_id, message_sequence, proposal_id,
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

    def request_for_idempotency(self, idempotency_key: str):
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            cur.execute("""SELECT x.request_id::text AS request_id,
                    x.correlation_id::text AS correlation_id,x.delivery_state,x.last_error_code,
                    x.request_payload,
                    (SELECT e.payload->'usage'->>'provider_error_param'
                       FROM external_reasoning_exchange_events e
                      WHERE e.request_id=x.request_id AND e.event_type='provider_attempt_settled'
                      ORDER BY e.sequence DESC LIMIT 1) AS provider_error_param,
                    (SELECT (e.payload->'usage'->>'http_status')::integer
                       FROM external_reasoning_exchange_events e
                      WHERE e.request_id=x.request_id AND e.event_type='provider_attempt_settled'
                      ORDER BY e.sequence DESC LIMIT 1) AS provider_http_status
                FROM external_reasoning_exchanges x WHERE x.idempotency_key=%s""",
                (idempotency_key,))
            row = cur.fetchone()
        return dict(row) if row else None

    def provider_attempt_is_settled(self, request_id):
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            cur.execute("""SELECT 1 FROM external_reasoning_exchange_events
                WHERE request_id=%s AND event_type='provider_attempt_settled' LIMIT 1""",
                (request_id,))
            return cur.fetchone() is not None

    def fail_provider_response_submission(self, request_id, correlation_id, *,
            provider_id, principal_id, claim_token, fence,
            failure_type=None, failure_detail=None):
        """Terminally fence a paid attempt whose response could not be submitted."""
        if failure_type is not None and (not isinstance(failure_type, str) or
                not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", failure_type)):
            raise ValueError("provider submission failure type is invalid")
        if failure_detail is not None and (not isinstance(failure_detail, str) or
                len(failure_detail) > 240 or re.search(r"[\r\n\t]", failure_detail)):
            raise ValueError("provider submission failure detail is invalid")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                self._require_provider_principal(provider_id, principal_id)
                cur.execute("""SELECT 1 FROM external_reasoning_exchange_events
                    WHERE request_id=%s AND event_type='provider_attempt_settled' LIMIT 1""",
                    (request_id,))
                if (row["provider_id"] != provider_id or row["delivery_state"] != "awaiting_response"
                        or row["response_payload"] is not None or row["claim_owner"] != principal_id
                        or str(row["claim_token"]) != str(claim_token) or row["claim_fence"] != fence
                        or cur.fetchone() is None):
                    raise ExchangeConflict("settled provider response cannot be safely fenced")
                cur.execute("""UPDATE external_reasoning_exchanges
                    SET delivery_state='failed',last_error_code='provider_response_submission_failed',
                        claim_owner=NULL,claim_token=NULL,claim_lease_until=NULL,
                        updated_at=clock_timestamp() WHERE request_id=%s""", (row["request_id"],))
                row.update(delivery_state="failed", last_error_code="provider_response_submission_failed")
                self._event(cur, row, "provider_response_submission_failed",
                    "provider-response-submission-failed", principal_id,
                    {"state": "failed", "error_code": "provider_response_submission_failed",
                     "provider_id": provider_id, "fence": fence,
                     **({"failure_type": failure_type} if failure_type else {}),
                     **({"failure_detail": failure_detail} if failure_detail else {})})
        return True

    def fail_provider_attempt_admission(self, request_id, correlation_id, *,
            provider_id, principal_id, claim_token, fence):
        """Terminalize a denied, uncharged provider claim without misreporting a paid failure."""
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                self._require_provider_principal(provider_id, principal_id)
                cur.execute("""SELECT 1 FROM external_reasoning_exchange_events
                    WHERE request_id=%s AND event_type='provider_attempt_started' LIMIT 1""",
                    (request_id,))
                attempt_started = cur.fetchone() is not None
                cur.execute("""SELECT 1 FROM grace_supervisory_authorization_events
                    WHERE request_id=%s AND event_type='luna_reserved' LIMIT 1""",
                    (request_id,))
                cost_reserved = cur.fetchone() is not None
                if (row["provider_id"] != provider_id or row["delivery_state"] != "awaiting_response"
                        or row["response_payload"] is not None or row["claim_owner"] != principal_id
                        or str(row["claim_token"]) != str(claim_token) or row["claim_fence"] != fence
                        or attempt_started or cost_reserved):
                    raise ExchangeConflict("provider admission denial is not safely terminal")
                cur.execute("""UPDATE external_reasoning_exchanges
                    SET delivery_state='failed',last_error_code='provider_attempt_admission_blocked',
                        claim_owner=NULL,claim_token=NULL,claim_lease_until=NULL,
                        updated_at=clock_timestamp() WHERE request_id=%s""", (row["request_id"],))
                row.update(delivery_state="failed", last_error_code="provider_attempt_admission_blocked")
                self._event(cur, row, "provider_attempt_admission_blocked",
                    "provider-attempt-admission-blocked", principal_id,
                    {"state": "failed", "error_code": "provider_attempt_admission_blocked",
                     "reason_code": "budget_or_repeat_blocked", "provider_id": provider_id,
                     "fence": fence, "charged": False})
        return True

    def has_terminal_review_for_objective(self, objective_id: str) -> bool:
        """Suppress repeated local inference after a bounded review chain is terminal."""
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            cur.execute("""SELECT EXISTS (
                SELECT 1 FROM external_reasoning_exchanges terminal
                WHERE terminal.objective_id=%s
                  AND terminal.request_payload ? 'review_subject'
                  AND terminal.delivery_state IN ('grace_consumed','expired','failed')
                  AND NOT EXISTS (SELECT 1 FROM external_reasoning_exchanges active
                    WHERE active.objective_id=terminal.objective_id
                      AND active.delivery_state IN
                        ('awaiting_delivery','awaiting_external_claim','awaiting_response','response_received')))
                AS has_terminal_review
                """, (objective_id,))
            return bool(cur.fetchone()["has_terminal_review"])

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

    @staticmethod
    def _require_steward_principal(principal_id):
        if (not isinstance(principal_id, str) or not principal_id.startswith("steward:")
                or len(principal_id) > 256):
            raise ExchangeUnauthorized("authenticated Steward principal required")

    def steward_eligible_requests(self, *, principal_id: str, limit=10) -> list[dict[str, Any]]:
        """List pending routed requests for the authenticated Comms5 Steward.

        This is a separate authorization path from provider OAuth. Provider routing
        is read from each durable row and cannot be selected by the caller.
        """
        self._require_steward_principal(principal_id)
        if type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError("eligible request limit must be between 1 and 10")
        now = _utc(self.clock())
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                cur.execute("""SELECT request_id FROM external_reasoning_exchanges
                    WHERE delivery_state NOT IN ('response_received','grace_consumed','expired','failed')
                      AND deadline_at<=%s ORDER BY deadline_at LIMIT 50 FOR UPDATE""", (now,))
                for expired in cur.fetchall():
                    row = self._lock(cur, expired["request_id"])
                    self._transition(cur, row, "expired", "request_expired", principal_id,
                                     "request_deadline_elapsed")
                cur.execute("""SELECT request_id,correlation_id,objective_id,conversation_id,
                    message_sequence,proposal_id,proposal_revision,request_schema,response_schema,
                    provider_id,classification,context_sha256,request_payload,requested_at,deadline_at,
                    delivery_state
                FROM external_reasoning_exchanges
                WHERE deadline_at>%s AND (
                    (delivery_state='awaiting_delivery' AND next_delivery_at<=%s
                     AND (delivery_lease_until IS NULL OR delivery_lease_until<=%s))
                    OR delivery_state IN ('awaiting_external_claim','awaiting_response'))
                ORDER BY requested_at,request_id LIMIT %s""",
                    (now, now, now, limit))
                return [dict(row) for row in cur.fetchall()]

    def steward_status(self, request_id: str, correlation_id: str, *,
                       principal_id: str) -> dict[str, Any]:
        """Return body-free exchange status to the authenticated Comms5 Steward."""
        self._require_steward_principal(principal_id)
        return self.status(request_id, correlation_id)

    def steward_claim(self, request_id: str, correlation_id: str, *,
                      principal_id: str, lease_seconds=120) -> ExchangeClaim | None:
        """Claim one exact routed request under the Steward audit identity."""
        self._require_steward_principal(principal_id)
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 300:
            raise ValueError("claim lease is out of range")
        now = _utc(self.clock())
        new_token = uuid4()
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                if self._expire_if_due(cur, row, now, principal_id):
                    return None
                if row["delivery_state"] in ("response_received", "grace_consumed"):
                    if row["claim_owner"] == principal_id:
                        return ExchangeClaim(str(row["request_id"]), str(row["correlation_id"]),
                            str(row["claim_token"]), row["claim_fence"], row["claim_lease_until"], True)
                    raise ExchangeConflict("request already has a terminal response")
                if row["delivery_state"] not in ("awaiting_external_claim", "awaiting_response"):
                    raise ExchangeConflict("request is not available for review claim")
                if row["claim_lease_until"] and row["claim_lease_until"] > now:
                    if row["claim_owner"] == principal_id:
                        return ExchangeClaim(str(row["request_id"]), str(row["correlation_id"]),
                            str(row["claim_token"]), row["claim_fence"], row["claim_lease_until"], True)
                    raise ExchangeConflict("another review claim is active")
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
                     "lease_until": lease_until.isoformat(), "review_authority": "steward"})
                return ExchangeClaim(str(row["request_id"]), str(row["correlation_id"]),
                    str(new_token), fence, lease_until)

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

    def claim_next_doorbell_request(self, provider_id: str, owner_id: str,
                                    lease_seconds: int) -> DoorbellDeliveryClaim | None:
        """Claim one due wake using existing exchange leases; return metadata only."""
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 120:
            raise ValueError("doorbell delivery lease is out of range")
        if not isinstance(owner_id, str) or not owner_id or len(owner_id) > 256:
            raise ValueError("doorbell delivery owner is invalid")
        provider = self.router.providers.get(provider_id)
        if provider is None or getattr(provider, "provider_id", None) != provider_id:
            raise ExchangeUnauthorized("provider_mismatch")
        now = _utc(self.clock())
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            cur.execute("""SELECT request_id::text AS request_id,
                    correlation_id::text AS correlation_id,deadline_at
                FROM external_reasoning_exchanges
                WHERE provider_id=%s AND delivery_state='awaiting_delivery'
                  AND deadline_at>%s AND next_delivery_at<=%s
                  AND (delivery_lease_until IS NULL OR delivery_lease_until<=%s)
                ORDER BY requested_at,request_id LIMIT 1""", (provider_id, now, now, now))
            candidate = cur.fetchone()
        if candidate is None:
            return None
        claim = self.begin_delivery(candidate["request_id"], provider_id,
                                    owner_id=owner_id, lease_seconds=lease_seconds)
        if claim is None:
            return None
        attempt_id = str(uuid5(NAMESPACE_URL,
            f"riverview-doorbell:{claim.request_id}:{claim.fence}"))
        return DoorbellDeliveryClaim(claim.request_id, claim.correlation_id,
            provider_id, attempt_id, claim.claim_token, claim.fence,
            claim.lease_until, candidate["deadline_at"])

    def record_doorbell_receipt(self, request_id: str, correlation_id: str,
            provider_id: str, owner_id: str, attempt_id: str, lease_token: str,
            fence: int, outcome: str, safe_error_code: str | None) -> str:
        """Atomically record a wake result and advance the same durable exchange."""
        if outcome not in {"submitted", "failed", "ambiguous"}:
            raise ValueError("doorbell outcome is invalid")
        if (outcome == "submitted") != (safe_error_code is None):
            raise ValueError("doorbell receipt error code does not match outcome")
        if safe_error_code is not None and not _DOORBELL_ERROR.fullmatch(safe_error_code):
            raise ValueError("doorbell diagnostic must be a recognized safe code")
        expected_attempt = str(uuid5(NAMESPACE_URL,
            f"riverview-doorbell:{request_id}:{fence}"))
        if (attempt_id != expected_attempt or type(fence) is not int or fence < 1
                or not isinstance(owner_id, str) or not owner_id or len(owner_id) > 256
                or not isinstance(lease_token, str) or not lease_token):
            raise ExchangeConflict("doorbell receipt identity is invalid")
        now = _utc(self.clock())
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self._set_path(cur)
                row = self._lock(cur, request_id, correlation_id)
                if row["provider_id"] != provider_id:
                    raise ExchangeUnauthorized("provider_mismatch")
                event_key = f"external-reasoning:{row['request_id']}:doorbell-receipt:{attempt_id}"
                cur.execute("""SELECT actor_id,payload FROM external_reasoning_exchange_events
                    WHERE idempotency_key=%s""", (event_key,))
                prior = cur.fetchone()
                if prior is not None:
                    payload = prior["payload"]
                    if (prior["actor_id"] != owner_id or payload.get("outcome") != outcome
                            or payload.get("safe_error_code") != safe_error_code
                            or payload.get("fence") != fence
                            or payload.get("lease_token_sha256") != hashlib.sha256(
                                lease_token.encode("utf-8")).hexdigest()):
                        raise ExchangeConflict("doorbell receipt conflicts with prior attempt")
                    return payload["state"]
                self._require_delivery_lease(row, provider_id, owner_id, lease_token, fence, now)
                if row["delivery_state"] != "awaiting_delivery":
                    raise ExchangeConflict("doorbell request is no longer awaiting delivery")
                if outcome == "submitted":
                    state = "awaiting_external_claim"
                    cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state=%s,
                        delivery_owner=NULL,delivery_token=NULL,delivery_lease_until=NULL,
                        updated_at=%s WHERE request_id=%s""", (state, now, row["request_id"]))
                else:
                    retryable = outcome == "failed" and safe_error_code in _DOORBELL_RETRYABLE
                    terminal = (not retryable or row["delivery_attempts"] >= _MAX_DELIVERY_ATTEMPTS
                                or row["deadline_at"] <= now)
                    state = "expired" if row["deadline_at"] <= now else (
                        "failed" if terminal else "awaiting_delivery")
                    delay = min(300, 2 ** min(row["delivery_attempts"], 8))
                    cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state=%s,
                        next_delivery_at=%s,delivery_owner=NULL,delivery_token=NULL,
                        delivery_lease_until=NULL,last_error_code=%s,updated_at=%s
                        WHERE request_id=%s""", (state, now + timedelta(seconds=delay),
                        safe_error_code.lower().replace("-", "_"), now, row["request_id"]))
                row.update(delivery_state=state)
                payload = {"state": state, "provider_id": provider_id,
                    "attempt_id": attempt_id, "fence": fence, "outcome": outcome,
                    "lease_token_sha256": hashlib.sha256(lease_token.encode("utf-8")).hexdigest(),
                    "safe_error_code": safe_error_code,
                    "retryable": outcome == "failed" and safe_error_code in _DOORBELL_RETRYABLE}
                self._event(cur, row, "doorbell_receipt", f"doorbell-receipt:{attempt_id}",
                            owner_id, payload)
                return state

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
                        idempotency_key: str, response: Mapping[str, Any],
                        review_subject_sha256: str | None = None,
                        provider_usage: Mapping[str, Any] | None = None) -> str:
        clean = self._validate_response(response, request_id, correlation_id, provider_id)
        self._require_provider_principal(provider_id, principal_id)
        return self._submit_response(request_id, correlation_id, provider_id=provider_id,
            principal_id=principal_id, reviewer_kind="provider", claim_token=claim_token,
            fence=fence, idempotency_key=idempotency_key, response=clean,
            review_subject_sha256=review_subject_sha256, provider_usage=provider_usage)

    def steward_submit_response(self, request_id: str, correlation_id: str, *,
                                principal_id: str, claim_token: str, fence: int,
                                idempotency_key: str, response: Mapping[str, Any],
                                review_subject_sha256: str | None = None) -> str:
        """Submit advice through Comms5 as an auditable Steward-originated review.

        The provider route is read from the durable exchange status and checked
        again against the immutable route on the locked exchange row. No provider
        principal is constructed or impersonated.
        """
        self._require_steward_principal(principal_id)
        if not isinstance(response, Mapping):
            raise ValueError("response does not match the versioned advisory schema")
        routed = self.status(request_id, correlation_id)
        provider_id = routed["provider_id"]
        if response.get("provider_id") != provider_id:
            raise ExchangeUnauthorized("provider_mismatch")
        clean = self._validate_response(response, request_id, correlation_id, provider_id)
        return self._submit_response(request_id, correlation_id, provider_id=provider_id,
            principal_id=principal_id, reviewer_kind="steward", claim_token=claim_token,
            fence=fence, idempotency_key=idempotency_key, response=clean,
            review_subject_sha256=review_subject_sha256)

    def _submit_response(self, request_id, correlation_id, *, provider_id, principal_id,
                         reviewer_kind, claim_token, fence, idempotency_key, response,
                         review_subject_sha256, provider_usage=None):
        if (not isinstance(idempotency_key, str)
                or not 1 <= len(idempotency_key) <= 240):
            raise ExchangeUnauthorized("response principal or idempotency key is invalid")
        if (type(fence) is not int or fence < 1 or not isinstance(claim_token, str)
                or not claim_token):
            raise ExchangeUnauthorized("active response claim and fencing token required")
        if review_subject_sha256 is not None and (
                not isinstance(review_subject_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", review_subject_sha256)):
            raise ExchangeUnauthorized("review subject digest is invalid")
        response_bytes = _json(response).encode("utf-8")
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
                request_payload = row.get("request_payload")
                subject = (request_payload.get("review_subject")
                    if isinstance(request_payload, Mapping) else None)
                expected_subject_digest = (subject.get("sha256")
                    if isinstance(subject, Mapping) else None)
                if expected_subject_digest is not None:
                    if (not isinstance(review_subject_sha256, str)
                            or review_subject_sha256 != expected_subject_digest):
                        if reviewer_kind == "steward":
                            raise ExchangeUnauthorized("review_subject_digest_mismatch")
                        raise ExchangeConflict("review_subject_digest_mismatch")
                elif review_subject_sha256 is not None:
                    if reviewer_kind == "steward":
                        raise ExchangeUnauthorized("review_subject_not_present")
                    raise ExchangeConflict("unexpected_review_subject_digest")
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
                    "provider_id": provider_id, "provider_model": response["provider_model"],
                    "response_id": response["response_id"], "received_at": now.isoformat(),
                    "claim_fence": fence}
                if reviewer_kind == "provider" and provider_usage is not None:
                    provenance["usage"] = dict(provider_usage)
                if reviewer_kind == "steward":
                    provenance.update({"reviewer_kind": "steward",
                        "reviewer_id": principal_id, "review_authority": "comms5_steward"})
                cur.execute("""UPDATE external_reasoning_exchanges SET delivery_state='response_received',
                    response_payload=%s::jsonb,response_sha256=%s,response_provenance=%s::jsonb,
                    response_idempotency_key=%s,response_received_at=%s,updated_at=%s WHERE request_id=%s""",
                    (_json(response), digest, _json(provenance), idempotency_key, now, now, row["request_id"]))
                row.update(delivery_state="response_received", response_sha256=digest,
                           response_payload=response, response_provenance=provenance)
                self._event(cur, row, "response_received", "response-received", principal_id,
                    {"state": row["delivery_state"], "response_sha256": digest,
                     "provider_id": provider_id, "provider_model": response["provider_model"],
                     **({"review_authority": "comms5_steward"}
                        if reviewer_kind == "steward" else {})})
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
                    subject = row["request_payload"].get("review_subject")
                    subject = validate_review_subject(subject) if subject is not None else None
                    return ExchangeConsumption(str(row["request_id"]), str(row["correlation_id"]),
                        row["consumption_key"], "", row["consumption_fence"],
                        row["consumed_at"], row["response_payload"], original, True, subject)
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
                subject = row["request_payload"].get("review_subject")
                subject = validate_review_subject(subject) if subject is not None else None
                return ExchangeConsumption(str(row["request_id"]), str(row["correlation_id"]),
                    consumption_key, str(token), fence, lease_until, response, original, active,
                    subject)

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
            result = {"request_id": str(row["request_id"]),
                "correlation_id": str(row["correlation_id"]),
                "objective_id": row["objective_id"], "delivery_state": row["delivery_state"],
                "diagnostic_state": self.STATES[row["delivery_state"]],
                "provider_id": row["provider_id"], "classification": row["classification"],
                "context_sha256": row["context_sha256"],
                "review_subject_sha256": ((row["request_payload"].get("review_subject") or {}).get("sha256")),
                "requested_at": row["requested_at"].isoformat(),
                "deadline_at": row["deadline_at"].isoformat(),
                "delivery_attempts": row["delivery_attempts"],
                "claim_attempts": row["claim_attempts"],
                "response_sha256": row["response_sha256"],
                "response_provenance": row["response_provenance"],
                "consumption_key": row["consumption_key"],
                "consumed_at": row["consumed_at"].isoformat() if row["consumed_at"] else None,
                "last_error_code": row["last_error_code"]}
            payload = row.get("request_payload")
            subject = payload.get("review_subject") if isinstance(payload, Mapping) else None
            if isinstance(subject, Mapping) and isinstance(subject.get("sha256"), str):
                result["review_subject_sha256"] = subject["sha256"]
            return result

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

    def review_successor(self, request_id: str, correlation_id: str):
        """Return an already-durable child exchange after parent crash recovery."""
        with self.ledger.db.cursor() as cur:
            self._set_path(cur)
            cur.execute("""SELECT request_id::text AS request_id,
                    correlation_id::text AS correlation_id,request_payload
                FROM external_reasoning_exchanges
                WHERE request_payload->'review_parent'->>'request_id'=%s
                  AND request_payload->'review_parent'->>'correlation_id'=%s
                ORDER BY requested_at,request_id LIMIT 1""",
                (str(request_id), str(correlation_id)))
            row = cur.fetchone()
        if row is None:
            return None
        subject = validate_review_subject(row["request_payload"].get("review_subject"))
        parent = row["request_payload"].get("review_parent") or {}
        return {"request_id": row["request_id"], "correlation_id": row["correlation_id"],
                "review_subject": subject, "response_sha256": parent.get("response_sha256")}

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
