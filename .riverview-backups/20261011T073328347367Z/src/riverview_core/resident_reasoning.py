# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_reasoning.py
# Component: RESIDENT-REASONING
# Revision: 1.0.3
# Purpose: Regound institutional resident requests and route bounded plan proposals
# Execution Model: Request-driven in-process runtime with replaceable reasoning providers
# Observability: Office-scoped durable state stores grounding and provider outcomes
# Dependencies: Psycopg-backed AuthorityRegistry; knowledge-provider v1; standard library
# Authority: Reasoning proposes plans only; all actions require separate authority checks
# Changed: 2026-10-11 UTC | RV-M4.2-001 | Bound provider and knowledge calls; persist plan proposals and preserve explicit failover after timeout
# Changed: 2026-10-11 UTC | RV-M4.2-BOUND-REQUEST-BUDGET | Bound provider fanout, divide total requested tokens across explicit routes, and require acyclic step dependencies
# Changed: 2026-10-11 UTC | RV-M4.2-CONTEXT-REDACTION-BOUND | Reject credential-shaped context keys and oversized model inputs before provider invocation
# Contracts: docs/components/RESIDENT_REASONING.md
# Tests: tests/test_resident_reasoning.py
# History: .riverview-backups/manifest.jsonl
# =============================================================================
"""Resident regrounding and provider-neutral reasoning with fail-closed authority.

This module never executes a proposal. The active office binding selects the
primary provider; fallback routes are explicit configuration. Grounding and
regrounding must both be VERIFIED before a provider is called. Plan proposals
and sanitized outcomes are persisted in the authority registry's office state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
import threading
import time
from typing import Any, Mapping, Protocol
from uuid import uuid4

from .worker_adapter.knowledge import KnowledgeProvider, KnowledgeResult, KnowledgeStatus


class ReasoningStatus(str, Enum):
    PROPOSED = "PROPOSED"
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"
    STALE_CONTEXT = "STALE_CONTEXT"
    STATE_CONFLICT = "STATE_CONFLICT"
    INVALID_PROPOSAL = "INVALID_PROPOSAL"


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanProposal:
    summary: str
    steps: tuple[PlanStep, ...]
    tokens_used: int

    def __post_init__(self):
        if not isinstance(self.summary, str) or not self.summary.strip() or len(self.summary) > 4000:
            raise ValueError("proposal summary must contain 1..4000 characters")
        if not 1 <= len(self.steps) <= 20:
            raise ValueError("proposal must contain 1..20 steps")
        ids = [step.step_id for step in self.steps]
        if any(not isinstance(item, str) or not item or len(item) > 80 for item in ids):
            raise ValueError("proposal step IDs must be non-empty and bounded")
        if len(ids) != len(set(ids)):
            raise ValueError("proposal step IDs must be unique")
        prior = set()
        for step in self.steps:
            if (not step.objective or len(step.objective) > 2000
                    or not step.acceptance_criteria
                    or any(not criterion or len(criterion) > 1000
                           for criterion in step.acceptance_criteria)
                    or any(dep not in prior for dep in step.depends_on)):
                raise ValueError("proposal step has invalid objective, criteria, or dependency")
            prior.add(step.step_id)
        if type(self.tokens_used) is not int or self.tokens_used < 0:
            raise ValueError("tokens_used must be a non-negative integer")


@dataclass(frozen=True)
class ReasoningRequest:
    request_id: str
    office_id: str
    assignment_id: str
    assignment_revision: str
    binding_revision: int
    implementation_revision: str
    trigger: str
    token_budget: int
    assignment: Mapping[str, Any]
    verified_knowledge: tuple[Mapping[str, Any], ...]
    prior_plan: Mapping[str, Any] | None


class AssignmentContextReader(Protocol):
    def read(self, assignment_id: str) -> Mapping[str, Any]: ...


class ReasoningProvider(Protocol):
    provider_id: str

    def propose(self, request: ReasoningRequest) -> PlanProposal: ...


@dataclass(frozen=True)
class ReasoningResult:
    status: ReasoningStatus
    request_id: str
    detail_code: str
    provider_id: str | None = None
    state_revision: int | None = None
    proposal: PlanProposal | None = None


class _TimedCall:
    """Bounded daemon-thread call; timed-out provider work cannot hold the caller."""

    def __init__(self, slots: threading.BoundedSemaphore):
        self.slots = slots

    def run(self, fn, timeout):
        if not self.slots.acquire(timeout=timeout):
            return False, None
        done = threading.Event()
        box = []

        def invoke():
            try:
                box.append((True, fn()))
            except Exception:
                box.append((False, None))
            finally:
                self.slots.release()
                done.set()

        threading.Thread(target=invoke, name="resident-reasoner", daemon=True).start()
        if not done.wait(timeout):
            return False, None
        return box[0]


class ResidentReasoner:
    """Reground an assignment, request a durable plan proposal, never execute it."""

    STATE_KEY = "resident_reasoning_v1"
    MAX_STATE_BYTES = 64 * 1024
    MAX_CONTEXT_BYTES = 32 * 1024
    _SENSITIVE_KEY_PARTS = ("token", "credential", "password", "secret", "dsn", "api_key", "private_key")

    def __init__(self, *, registry, office_id: str, resident_credential: str,
                 assignments: AssignmentContextReader, knowledge: KnowledgeProvider,
                 providers: Mapping[str, ReasoningProvider],
                 fallback_routes: Mapping[str, tuple[str, ...]] | None = None,
                 timeout_seconds: float = 5.0):
        if not office_id or not resident_credential or timeout_seconds <= 0:
            raise ValueError("office, credential, and positive timeout are required")
        self.registry = registry
        self.office_id = office_id
        self._credential = resident_credential
        self.assignments = assignments
        self.knowledge = knowledge
        self.providers = dict(providers)
        self.fallback_routes = {key: tuple(value) for key, value in (fallback_routes or {}).items()}
        if (len(self.providers) > 8 or not 0 < timeout_seconds <= 30
                or any(not isinstance(key, str) or not key or len(route) > 2
                       or len(route) != len(set(route)) or key in route
                       for key, route in self.fallback_routes.items())):
            raise ValueError("provider count, timeout, or explicit fallback route exceeds its bound")
        self.timeout_seconds = timeout_seconds
        # Leave one bounded slot available for an explicit failover after a timeout.
        self._slots = _PROVIDER_SLOTS
        self._timed_call = _TimedCall(self._slots)

    @staticmethod
    def _knowledge_record(result: KnowledgeResult):
        return {"status": result.status.value,
                "source_references": list(result.source_references),
                "source_revision": result.source_revision,
                "source_sha256": result.source_sha256,
                "retrieval_complete": result.retrieval_complete}

    def _persist(self, snapshot, *, assignment_id, observation, proposal=None):
        state = dict(snapshot["state"])
        runtime = dict(state.get(self.STATE_KEY, {}))
        outcomes = list(runtime.get("outcomes", []))
        outcomes.append(observation)
        runtime["outcomes"] = outcomes[-32:]
        plans = dict(runtime.get("plans", {}))
        if proposal is not None:
            plans[assignment_id] = asdict(proposal)
        runtime["plans"] = plans
        state[self.STATE_KEY] = runtime
        if len(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()) > self.MAX_STATE_BYTES:
            return None
        try:
            return self.registry.set_office_state(
                self._credential, self.office_id, state,
                expected_revision=snapshot["state_revision"])
        except Exception:
            return None

    def _record(self, snapshot, assignment_id, request_id, status, trigger,
                grounding, regrounding, *, provider_id=None, code="", proposal=None):
        return self._persist(snapshot, assignment_id=assignment_id,
                             observation={"request_id": request_id,
                                          "assignment_id": assignment_id,
                                          "status": status.value,
                                          "detail_code": code,
                                          "trigger": trigger,
                                          "grounding": self._knowledge_record(grounding),
                                          "regrounding": self._knowledge_record(regrounding),
                                          "provider_id": provider_id},
                             proposal=proposal)

    def _call_knowledge(self, operation, *args):
        ok, result = self._timed_call.run(
            lambda: getattr(self.knowledge, operation)(*args), self.timeout_seconds)
        if not ok or not isinstance(result, KnowledgeResult):
            return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)
        return result

    @classmethod
    def _contains_secret_key(cls, value):
        if isinstance(value, Mapping):
            return any(any(part in str(key).lower() for part in cls._SENSITIVE_KEY_PARTS)
                       or cls._contains_secret_key(child) for key, child in value.items())
        if isinstance(value, (tuple, list)):
            return any(cls._contains_secret_key(child) for child in value)
        return False

    def propose(self, assignment_id: str, *, trigger: str, token_budget: int) -> ReasoningResult:
        request_id = str(uuid4())
        if (not assignment_id or not trigger or len(trigger) > 80
                or type(token_budget) is not int or not 1 <= token_budget <= 100_000):
            raise ValueError("assignment, bounded trigger, and token budget are required")
        snapshot = self.registry.office_snapshot(self.office_id)
        if not snapshot.get("occupant_id") or not snapshot.get("provider_ref"):
            empty = KnowledgeResult(KnowledgeStatus.UNVERIFIED)
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.WAITING_FOR_EVIDENCE, trigger, empty, empty,
                                    code="OFFICE_UNBOUND")
            return ReasoningResult(ReasoningStatus.WAITING_FOR_EVIDENCE, request_id,
                                  "OFFICE_UNBOUND", state_revision=revision)
        try:
            ok, raw_assignment = self._timed_call.run(
                lambda: self.assignments.read(assignment_id), self.timeout_seconds)
            if not ok or not isinstance(raw_assignment, Mapping):
                raise ValueError("assignment context is unavailable")
            assignment = dict(raw_assignment)
            if assignment.get("id") != assignment_id or not assignment.get("revision"):
                raise ValueError("assignment identity or revision is missing")
            if self._contains_secret_key(assignment):
                raise ValueError("assignment context contains a protected credential field")
            grounded = self._call_knowledge("ground_assignment", assignment)
            regrounded = self._call_knowledge("reground_assignment", assignment, trigger)
        except Exception:
            grounded = regrounded = KnowledgeResult(KnowledgeStatus.UNAVAILABLE)
            assignment = {"id": assignment_id, "revision": "unavailable"}
        if grounded.status is not KnowledgeStatus.VERIFIED or regrounded.status is not KnowledgeStatus.VERIFIED:
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.WAITING_FOR_EVIDENCE, trigger,
                                    grounded, regrounded, code="GROUNDING_NOT_VERIFIED")
            status = ReasoningStatus.WAITING_FOR_EVIDENCE if revision is not None else ReasoningStatus.STATE_CONFLICT
            return ReasoningResult(status, request_id, "GROUNDING_NOT_VERIFIED", state_revision=revision)
        try:
            serialized_context = json.dumps(
                [assignment, grounded.value, regrounded.value], ensure_ascii=False)
            if (len(serialized_context.encode("utf-8")) > self.MAX_CONTEXT_BYTES
                    or self._contains_secret_key([grounded.value, regrounded.value])):
                raise ValueError("verified context exceeds input boundary")
        except (TypeError, ValueError):
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.WAITING_FOR_EVIDENCE, trigger,
                                    grounded, regrounded, code="KNOWLEDGE_NOT_SERIALIZABLE")
            return ReasoningResult(ReasoningStatus.WAITING_FOR_EVIDENCE, request_id,
                                  "KNOWLEDGE_NOT_SERIALIZABLE", state_revision=revision)

        implementation_revision = snapshot.get("implementation_revision")
        provider_ref = snapshot.get("provider_ref")
        route = (provider_ref,) + self.fallback_routes.get(provider_ref, ())
        if any(not isinstance(provider_id, str) or provider_id not in self.providers
               for provider_id in route):
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.UNAVAILABLE, trigger, grounded, regrounded,
                                    code="PROVIDER_ROUTE_UNAVAILABLE")
            status = ReasoningStatus.UNAVAILABLE if revision is not None else ReasoningStatus.STATE_CONFLICT
            return ReasoningResult(status, request_id, "PROVIDER_ROUTE_UNAVAILABLE", state_revision=revision)

        prior_runtime = snapshot["state"].get(self.STATE_KEY, {})
        prior_plan = prior_runtime.get("plans", {}).get(assignment_id)
        per_attempt_budget = max(1, token_budget // len(route))
        request = ReasoningRequest(
            request_id=request_id, office_id=self.office_id, assignment_id=assignment_id,
            assignment_revision=str(assignment["revision"]),
            binding_revision=int(snapshot["binding_revision"]),
            implementation_revision=str(implementation_revision), trigger=trigger,
            token_budget=per_attempt_budget, assignment=assignment,
            verified_knowledge=(
                {"value": grounded.value, **self._knowledge_record(grounded)},
                {"value": regrounded.value, **self._knowledge_record(regrounded)}),
            prior_plan=prior_plan)

        for provider_id in route:
            provider = self.providers[provider_id]
            if getattr(provider, "provider_id", None) != provider_id:
                revision = self._record(snapshot, assignment_id, request_id,
                                        ReasoningStatus.UNAVAILABLE, trigger, grounded, regrounded,
                                        provider_id=provider_id, code="PROVIDER_ID_MISMATCH")
                status = ReasoningStatus.UNAVAILABLE if revision is not None else ReasoningStatus.STATE_CONFLICT
                return ReasoningResult(status, request_id, "PROVIDER_ID_MISMATCH",
                                      provider_id, revision)
            ok, result = self._timed_call.run(lambda: provider.propose(request), self.timeout_seconds)
            if not ok:
                # Only unavailable/timeout can use explicitly configured fallback.
                if provider_id == route[-1]:
                    revision = self._record(snapshot, assignment_id, request_id,
                                            ReasoningStatus.UNAVAILABLE, trigger, grounded, regrounded,
                                            provider_id=provider_id, code="PROVIDER_TIMEOUT_OR_FAILURE")
                    status = ReasoningStatus.UNAVAILABLE if revision is not None else ReasoningStatus.STATE_CONFLICT
                    return ReasoningResult(status, request_id, "PROVIDER_TIMEOUT_OR_FAILURE",
                                          provider_id, revision)
                continue
            if not isinstance(result, PlanProposal) or result.tokens_used > token_budget:
                revision = self._record(snapshot, assignment_id, request_id,
                                        ReasoningStatus.INVALID_PROPOSAL, trigger, grounded, regrounded,
                                        provider_id=provider_id, code="PROPOSAL_SCHEMA_OR_BUDGET")
                status = ReasoningStatus.INVALID_PROPOSAL if revision is not None else ReasoningStatus.STATE_CONFLICT
                return ReasoningResult(status, request_id, "PROPOSAL_SCHEMA_OR_BUDGET",
                                      provider_id, revision)
            latest = self.registry.office_snapshot(self.office_id)
            if (latest.get("binding_revision") != request.binding_revision
                    or latest.get("implementation_revision") != request.implementation_revision):
                revision = self._record(latest, assignment_id, request_id,
                                        ReasoningStatus.STALE_CONTEXT, trigger, grounded, regrounded,
                                        provider_id=provider_id, code="OFFICE_BINDING_CHANGED")
                return ReasoningResult(ReasoningStatus.STALE_CONTEXT, request_id,
                                      "OFFICE_BINDING_CHANGED", provider_id, revision)
            try:
                ok, current_assignment = self._timed_call.run(
                    lambda: self.assignments.read(assignment_id), self.timeout_seconds)
                if not ok:
                    current_assignment = None
            except Exception:
                current_assignment = None
            if not current_assignment or str(current_assignment.get("revision")) != request.assignment_revision:
                revision = self._record(latest, assignment_id, request_id,
                                        ReasoningStatus.STALE_CONTEXT, trigger, grounded, regrounded,
                                        provider_id=provider_id, code="ASSIGNMENT_CHANGED")
                return ReasoningResult(ReasoningStatus.STALE_CONTEXT, request_id,
                                      "ASSIGNMENT_CHANGED", provider_id, revision)
            revision = self._record(latest, assignment_id, request_id,
                                    ReasoningStatus.PROPOSED, trigger, grounded, regrounded,
                                    provider_id=provider_id, code="PROPOSAL_ONLY",
                                    proposal=result)
            if revision is None:
                return ReasoningResult(ReasoningStatus.STATE_CONFLICT, request_id,
                                      "DURABLE_STATE_WRITE_FAILED", provider_id)
            return ReasoningResult(ReasoningStatus.PROPOSED, request_id, "PROPOSAL_ONLY",
                                  provider_id, revision, result)
        return ReasoningResult(ReasoningStatus.UNAVAILABLE, request_id, "PROVIDER_UNAVAILABLE")


# Process-wide cap prevents resident replacement/request concurrency from creating
# an unbounded number of orphaned provider threads after timeouts.
_PROVIDER_SLOTS = threading.BoundedSemaphore(8)
