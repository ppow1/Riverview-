# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/reasoning_escalation.py
# Component: RESIDENT-REASONING
# Revision: 1.0.2
# Purpose: Define bounded, authority-checked task escalation without execution authority
# Execution Model: One provider call over an immutable, correlated ReasoningRequest
# Observability: Typed decision, provider, budget, timeout and context fingerprint
# Dependencies: Existing ResidentReasoner provider contract; standard library
# Authority: Exact resident.reasoning.escalate grant; proposal only, never dispatch
# Changed: 2026-10-13 UTC | RV-REASONING-ESCALATION-CONTRACT | Add additive escalation request/result contract
# Changed: 2026-10-13 UTC | RV-REASONING-ESCALATION-CONTEXT-SNAPSHOT | Recheck correlation and deep-copy provider context before invocation
# Changed: 2026-10-13 UTC | RV-REASONING-ESCALATION-AUTHORITY-STATUS | Distinguish denied grants from unavailable authority checks
# Contracts: docs/components/RESIDENT_REASONING.md
# Tests: tests/test_reasoning_escalation.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""A bounded task-escalation contract, deliberately separate from failure fallback.

This module does not select a higher-capability provider automatically and does
not create assignments. A caller must provide an explicit reason, exact target,
and existing-authority decision before the provider is invoked.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
import copy
import hashlib
import json
import queue
import threading
from uuid import uuid4

from .resident_reasoning import PlanProposal, ReasoningRequest
from .institutional_authority import GrantCheckUnavailable, GrantDenied


class EscalationStatus(str, Enum):
    PROPOSED = "PROPOSED"
    DENIED = "DENIED"
    AUTHORITY_UNAVAILABLE = "AUTHORITY_UNAVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    TIMED_OUT = "TIMED_OUT"
    INVALID_RESULT = "INVALID_RESULT"
    STALE_CONTEXT = "STALE_CONTEXT"


def context_fingerprint(request: ReasoningRequest) -> str:
    """Hash the full objective, revision, verified facts and prior plan."""
    try:
        document = asdict(request)
        payload = json.dumps(document, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        raise ValueError("reasoning context is not serializable") from None
    if len(payload) > 32 * 1024:
        raise ValueError("reasoning context exceeds escalation bound")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class EscalationRequest:
    schema_version: str
    escalation_id: str
    original_request_id: str
    office_id: str
    assignment_id: str
    assignment_revision: str
    binding_revision: int
    implementation_revision: str
    context_sha256: str
    reason: str
    target_provider_id: str
    max_tokens: int
    timeout_seconds: int

    @classmethod
    def create(cls, original: ReasoningRequest, *, reason: str,
               target_provider_id: str, max_tokens: int = 512,
               timeout_seconds: int = 30):
        if (not isinstance(original, ReasoningRequest) or
                reason not in {"task_complexity", "capability_gap", "low_confidence"} or
                not isinstance(target_provider_id, str) or not target_provider_id or
                len(target_provider_id) > 160 or type(max_tokens) is not int or
                not 1 <= max_tokens <= 512 or type(timeout_seconds) is not int or
                not 1 <= timeout_seconds <= 60):
            raise ValueError("escalation request exceeds its bounded contract")
        return cls("rv.resident.escalation-request.v1", str(uuid4()),
                   original.request_id, original.office_id, original.assignment_id,
                   original.assignment_revision, original.binding_revision,
                   original.implementation_revision, context_fingerprint(original),
                   reason, target_provider_id, max_tokens, timeout_seconds)


@dataclass(frozen=True)
class EscalationResult:
    schema_version: str
    escalation_id: str
    original_request_id: str
    status: EscalationStatus
    provider_id: str
    context_sha256: str
    detail_code: str
    proposal: PlanProposal | None = None


class ReasoningEscalationRouter:
    """Invoke one explicitly selected provider after the exact grant check."""

    ACTION = "resident.reasoning.escalate"

    def __init__(self, providers, *, max_concurrency=2):
        if not isinstance(providers, dict) or len(providers) > 8:
            raise ValueError("escalation provider registry is invalid")
        if type(max_concurrency) is not int or not 1 <= max_concurrency <= 4:
            raise ValueError("escalation concurrency is outside its bound")
        self.providers = dict(providers)
        self._slots = threading.BoundedSemaphore(max_concurrency)

    def execute(self, envelope: EscalationRequest, original: ReasoningRequest, *,
                principal_id: str, authorize):
        if (not isinstance(envelope, EscalationRequest) or
                not isinstance(original, ReasoningRequest) or
                not callable(authorize) or not principal_id or
                envelope.original_request_id != original.request_id or
                envelope.office_id != original.office_id or
                envelope.assignment_id != original.assignment_id or
                envelope.assignment_revision != original.assignment_revision or
                envelope.binding_revision != original.binding_revision or
                envelope.implementation_revision != original.implementation_revision or
                envelope.schema_version != "rv.resident.escalation-request.v1"):
            raise ValueError("escalation correlation does not match the original request")
        try:
            if context_fingerprint(original) != envelope.context_sha256:
                return self._result(envelope, EscalationStatus.STALE_CONTEXT,
                                    "original_context_changed")
        except ValueError:
            return self._result(envelope, EscalationStatus.STALE_CONTEXT,
                                "original_context_unavailable")
        provider = self.providers.get(envelope.target_provider_id)
        if provider is None or getattr(provider, "provider_id", None) != envelope.target_provider_id:
            return self._result(envelope, EscalationStatus.UNAVAILABLE, "provider_not_registered")
        try:
            if authorize(principal_id, self.ACTION,
                         "provider:" + envelope.target_provider_id) is not True:
                return self._result(envelope, EscalationStatus.DENIED, "exact_grant_required")
        except GrantDenied:
            return self._result(envelope, EscalationStatus.DENIED, "exact_grant_required")
        except GrantCheckUnavailable:
            return self._result(envelope, EscalationStatus.AUTHORITY_UNAVAILABLE,
                                "authority_check_unavailable")
        except Exception:
            return self._result(envelope, EscalationStatus.AUTHORITY_UNAVAILABLE,
                                "authority_check_failed")
        if not self._slots.acquire(blocking=False):
            return self._result(envelope, EscalationStatus.UNAVAILABLE, "capacity_unavailable")
        done = threading.Event()
        box = []
        bounded_request = replace(original,
            assignment=copy.deepcopy(dict(original.assignment)),
            verified_knowledge=copy.deepcopy(tuple(original.verified_knowledge)),
            prior_plan=copy.deepcopy(original.prior_plan),
            token_budget=envelope.max_tokens)

        def invoke():
            try:
                box.append((True, provider.propose(bounded_request)))
            except Exception:
                box.append((False, None))
            finally:
                self._slots.release()
                done.set()

        threading.Thread(target=invoke, name="resident-escalation", daemon=True).start()
        if not done.wait(envelope.timeout_seconds):
            return self._result(envelope, EscalationStatus.TIMED_OUT, "provider_timeout")
        if not box or not box[0][0]:
            return self._result(envelope, EscalationStatus.UNAVAILABLE, "provider_failed")
        proposal = box[0][1]
        if (not isinstance(proposal, PlanProposal) or
                proposal.tokens_used > envelope.max_tokens):
            return self._result(envelope, EscalationStatus.INVALID_RESULT,
                                "proposal_contract_or_budget_invalid")
        try:
            unchanged = context_fingerprint(original) == envelope.context_sha256
        except ValueError:
            unchanged = False
        if not unchanged:
            return self._result(envelope, EscalationStatus.STALE_CONTEXT,
                                "original_context_changed")
        return self._result(envelope, EscalationStatus.PROPOSED,
                            "structured_proposal_returned", proposal)

    @staticmethod
    def _result(envelope, status, detail, proposal=None):
        return EscalationResult("rv.resident.escalation-result.v1",
            envelope.escalation_id, envelope.original_request_id, status,
            envelope.target_provider_id, envelope.context_sha256, detail, proposal)
