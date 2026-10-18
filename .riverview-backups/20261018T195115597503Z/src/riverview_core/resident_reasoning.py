# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_reasoning.py
# Component: RESIDENT-REASONING
# Revision: 1.0.18
# Purpose: Regound institutional resident requests and route bounded plan proposals
# Execution Model: Request-driven in-process runtime with replaceable reasoning providers
# Observability: Office-scoped durable state stores grounding and provider outcomes
# Dependencies: Psycopg-backed AuthorityRegistry; knowledge-provider v1; standard library
# Authority: Reasoning proposes plans only; all actions require separate authority checks
# Changed: 2026-10-11 UTC | RV-M4.2-001 | Bound provider and knowledge calls; persist plan proposals and preserve explicit failover after timeout
# Changed: 2026-10-11 UTC | RV-M4.2-BOUND-REQUEST-BUDGET | Bound provider fanout, divide total requested tokens across explicit routes, and require acyclic step dependencies
# Changed: 2026-10-11 UTC | RV-M4.2-CONTEXT-REDACTION-BOUND | Reject credential-shaped context keys and oversized model inputs before provider invocation
# Changed: 2026-10-11 UTC | RV-M4.2-EXACT-STATE-AUTHORITY | Require the exact active office-state grant before context access and report durable-write failures precisely
# Changed: 2026-10-11 UTC | RV-M4.2-AUTHORITY-DENIAL-STATUS | Expose a typed authority-denied result when the resident office-state grant is absent or revoked
# Changed: 2026-10-11 UTC | RV-M4.2-ENFORCE-PER-ROUTE-TOKEN-BUDGET | Reject provider output that exceeds its allocated attempt budget
# Changed: 2026-10-11 UTC | RV-M4.2-ROUTE-MINIMUM-BUDGET | Reject a configured route whose provider count cannot fit the requested total token budget
# Changed: 2026-10-11 UTC | RV-M4.4-CONTEXT-FAILURE-CLASS | Distinguish oversize grounded input from JSON serialization failure
# Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Persist actual served-model provenance with typed resident proposals
# Changed: 2026-10-15 UTC | RV-GRACE-PROPOSAL-TIMEOUT-001 | Permit bounded 60-second 80B proposal inference
# Previous Revision: 1.0.13
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Carry exact authorized execution capability and source-change scope in durable plan steps
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reject empty or malformed source-change scopes instead of truthy generator results
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Restrict source-change test targets to tests paths
# Changed: 2026-10-15 UTC | RV-GRACE-AUTHORIZED-SNAPSHOT-001 | Revalidate office through the restricted runtime function after inference
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Accept bounded advisory input separately from verified knowledge
# Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Add typed model-selected external advisory intent at the existing reasoning boundary
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
import hashlib
import json
import re
import threading
import time
from typing import Any, Mapping, Protocol
from uuid import NAMESPACE_URL, uuid4, uuid5

from .worker_adapter.knowledge import KnowledgeProvider, KnowledgeResult, KnowledgeStatus
from .institutional_authority import AuthorityDenied, IdentityConflict, RegistryUnavailable


class ReasoningStatus(str, Enum):
    PROPOSED = "PROPOSED"
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    AUTHORITY_DENIED = "AUTHORITY_DENIED"
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
    execution_capability: str = "engineering.codex-cli-artifact.v1"
    authorized_paths: tuple[str, ...] = ()
    test_targets: tuple[str, ...] = ()
    repository_reference: str | None = None
    repository_revision: str | None = None

    def __post_init__(self):
        if self.execution_capability not in {
                "engineering.codex-cli-artifact.v1",
                "engineering.codex-cli-source-change.v1"}:
            raise ValueError("plan step execution capability is not registered")
        if self.execution_capability == "engineering.codex-cli-source-change.v1":
            def safe(values):
                return (isinstance(values, tuple) and 1 <= len(values) <= 32 and
                    len(values) == len(set(values)) and all(
                        isinstance(path, str) and re.fullmatch(
                            r"(?:src|tests|docs)/[A-Za-z0-9._/-]{1,240}", path) and
                        ".." not in path.split("/") and ".git" not in path.split("/")
                        for path in values))
            if (not isinstance(self.repository_reference, str) or
                    not re.fullmatch(r"repo://[A-Za-z0-9._/-]{1,240}", self.repository_reference) or
                    not isinstance(self.repository_revision, str) or
                    not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", self.repository_revision) or
                    not safe(self.authorized_paths) or not safe(self.test_targets) or
                    any(not path.startswith("tests/") for path in self.test_targets) or
                    not set(self.test_targets) <= set(self.authorized_paths)):
                raise ValueError("source-change plan step requires a pinned repository and bounded paths and test targets")
        elif self.authorized_paths or self.test_targets or self.repository_reference is not None or self.repository_revision is not None:
            raise ValueError("bounded artifact steps cannot carry source-change target scope")

@dataclass(frozen=True)
class ExternalEscalationIntent:
    """Explicit model decision to request bounded, advisory external reasoning."""

    reason: str
    target_provider_id: str

    def __post_init__(self):
        if (self.reason not in {"task_complexity", "capability_gap", "low_confidence"}
                or not isinstance(self.target_provider_id, str)
                or not self.target_provider_id or len(self.target_provider_id) > 160):
            raise ValueError("external escalation intent is invalid")


@dataclass(frozen=True)
class PlanProposal:
    summary: str
    steps: tuple[PlanStep, ...]
    tokens_used: int
    provider_id: str | None = None
    served_model: str | None = None
    model_revision: str | None = None
    reasoning_stage: str | None = None
    external_escalation: ExternalEscalationIntent | None = None

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
        provenance = (self.provider_id, self.served_model, self.model_revision,
                      self.reasoning_stage)
        if any(value is not None for value in provenance):
            if (not all(isinstance(value, str) and value for value in provenance)
                    or len(self.model_revision) != 64
                    or any(char not in "0123456789abcdef" for char in self.model_revision)
                    or self.reasoning_stage != "reasoning"):
                raise ValueError("proposal provider provenance is incomplete or invalid")


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
    external_advisory: Mapping[str, Any] | None = None
    external_reasoning_targets: tuple[str, ...] = ()


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
    reasoning_request: ReasoningRequest | None = None


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
                 external_reasoning_targets: tuple[str, ...] = (),
                 timeout_seconds: float = 5.0):
        if not office_id or not resident_credential or timeout_seconds <= 0:
            raise ValueError("office, credential, and positive timeout are required")
        self.registry = registry
        self.office_id = office_id
        self._credential = resident_credential
        self.assignments = assignments
        self.knowledge = knowledge
        self.providers = dict(providers)
        if (not isinstance(external_reasoning_targets, tuple)
                or len(external_reasoning_targets) > 8
                or len(set(external_reasoning_targets)) != len(external_reasoning_targets)
                or any(not isinstance(item, str) or not item or len(item) > 160
                       for item in external_reasoning_targets)):
            raise ValueError("external reasoning target registry is invalid")
        self.external_reasoning_targets = external_reasoning_targets
        self.fallback_routes = {key: tuple(value) for key, value in (fallback_routes or {}).items()}
        if (len(self.providers) > 8 or not 0 < timeout_seconds <= 60
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
        except AuthorityDenied:
            return "AUTHORITY_DENIED"
        except IdentityConflict:
            return "STATE_CONFLICT"
        except RegistryUnavailable:
            return "AUTHORITY_UNAVAILABLE"
        except Exception:
            return "AUTHORITY_UNAVAILABLE"

    @staticmethod
    def _result_after_record(revision, desired, request_id, code, provider_id=None):
        if type(revision) is int:
            return ReasoningResult(desired, request_id, code, provider_id, revision)
        if revision == "AUTHORITY_DENIED":
            return ReasoningResult(ReasoningStatus.AUTHORITY_DENIED, request_id,
                                  "OFFICE_STATE_GRANT_REVOKED", provider_id)
        if revision == "AUTHORITY_UNAVAILABLE":
            return ReasoningResult(ReasoningStatus.UNAVAILABLE, request_id,
                                  "OFFICE_STATE_STORE_UNAVAILABLE", provider_id)
        return ReasoningResult(ReasoningStatus.STATE_CONFLICT, request_id,
                              str(revision or "DURABLE_STATE_WRITE_FAILED"), provider_id)

    def _record(self, snapshot, assignment_id, request_id, status, trigger,
                grounding, regrounding, *, provider_id=None, code="", proposal=None,
                external_advisory=None):
        advisory_provenance = None
        if external_advisory is not None:
            advisory_provenance = {
                "request_id": external_advisory["request_id"],
                "correlation_id": external_advisory["correlation_id"],
                "response_id": external_advisory["response_id"],
                "provider_id": external_advisory["provider_id"],
                "provider_model": external_advisory["provider_model"],
                "response_sha256": hashlib.sha256(json.dumps(
                    external_advisory, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False).encode("utf-8")).hexdigest(),
            }
        return self._persist(snapshot, assignment_id=assignment_id,
                             observation={"request_id": request_id,
                                          "assignment_id": assignment_id,
                                          "status": status.value,
                                          "detail_code": code,
                                          "trigger": trigger,
                                          "grounding": self._knowledge_record(grounding),
                                          "regrounding": self._knowledge_record(regrounding),
                                          "provider_id": provider_id,
                                          "external_advisory": advisory_provenance},
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

    @staticmethod
    def _validate_external_advisory(value):
        if value is None:
            return None
        required = {"schema_version", "request_id", "correlation_id", "response_id",
                    "advisory", "evidence_references", "provider_id", "provider_model"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise ValueError("external advisory does not match its typed response contract")
        try:
            from uuid import UUID
            UUID(str(value["request_id"]))
            UUID(str(value["correlation_id"]))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("external advisory correlation is invalid") from None
        refs = value["evidence_references"]
        if (value["schema_version"] != "rv.external-reasoning.response.v1"
                or not isinstance(value["response_id"], str) or not value["response_id"]
                or len(value["response_id"]) > 160
                or not isinstance(value["advisory"], str) or not value["advisory"].strip()
                or len(value["advisory"]) > 8000
                or not isinstance(refs, list) or len(refs) > 32
                or any(not isinstance(item, str) or not item or len(item) > 512 for item in refs)
                or any(not isinstance(value[key], str) or not value[key] or len(value[key]) > 160
                       for key in ("provider_id", "provider_model"))):
            raise ValueError("external advisory fields exceed the bounded response contract")
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(encoded) > 16 * 1024:
            raise ValueError("external advisory exceeds the response size limit")
        return dict(value)

    def propose(self, assignment_id: str, *, trigger: str, token_budget: int,
                external_advisory: Mapping[str, Any] | None = None) -> ReasoningResult:
        request_id = str(uuid4())
        if (not assignment_id or not trigger or len(trigger) > 80
                or type(token_budget) is not int or not 1 <= token_budget <= 100_000):
            raise ValueError("assignment, bounded trigger, and token budget are required")
        external_advisory = self._validate_external_advisory(external_advisory)
        try:
            snapshot = self.registry.authorize_office_state(
                self._credential, self.office_id)
        except AuthorityDenied:
            return ReasoningResult(ReasoningStatus.AUTHORITY_DENIED, request_id,
                                  "OFFICE_STATE_GRANT_REQUIRED")
        except Exception:
            return ReasoningResult(ReasoningStatus.UNAVAILABLE, request_id,
                                  "OFFICE_STATE_STORE_UNAVAILABLE")
        if not snapshot.get("occupant_id") or not snapshot.get("provider_ref"):
            empty = KnowledgeResult(KnowledgeStatus.UNVERIFIED)
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.WAITING_FOR_EVIDENCE, trigger, empty, empty,
                                    code="OFFICE_UNBOUND")
            return self._result_after_record(revision, ReasoningStatus.WAITING_FOR_EVIDENCE,
                                             request_id, "OFFICE_UNBOUND")
        context_failure_code = "ASSIGNMENT_CONTEXT_UNAVAILABLE"
        try:
            ok, raw_assignment = self._timed_call.run(
                lambda: self.assignments.read(assignment_id), self.timeout_seconds)
            if not ok or not isinstance(raw_assignment, Mapping):
                raise ValueError("assignment context is unavailable")
            assignment = dict(raw_assignment)
            if assignment.get("id") != assignment_id or not assignment.get("revision"):
                raise ValueError("assignment identity or revision is missing")
            if self._contains_secret_key(assignment):
                context_failure_code = "ASSIGNMENT_CONTEXT_REDACTION_REJECTED"
                raise ValueError("assignment context contains a protected credential field")
            context_failure_code = None
            grounded = self._call_knowledge("ground_assignment", assignment)
            regrounded = self._call_knowledge("reground_assignment", assignment, trigger)
        except Exception:
            grounded = regrounded = KnowledgeResult(KnowledgeStatus.UNAVAILABLE)
            assignment = {"id": assignment_id, "revision": "unavailable"}
        if grounded.status is not KnowledgeStatus.VERIFIED or regrounded.status is not KnowledgeStatus.VERIFIED:
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.WAITING_FOR_EVIDENCE, trigger,
                                    grounded, regrounded,
                                    code=context_failure_code or "GROUNDING_NOT_VERIFIED")
            return self._result_after_record(revision, ReasoningStatus.WAITING_FOR_EVIDENCE,
                                             request_id, context_failure_code or "GROUNDING_NOT_VERIFIED")
        try:
            serialized_context = json.dumps(
                [assignment, grounded.value, regrounded.value], ensure_ascii=False)
        except (TypeError, ValueError):
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.WAITING_FOR_EVIDENCE, trigger,
                                    grounded, regrounded, code="KNOWLEDGE_NOT_SERIALIZABLE")
            return self._result_after_record(revision, ReasoningStatus.WAITING_FOR_EVIDENCE,
                                             request_id, "KNOWLEDGE_NOT_SERIALIZABLE")
        if len(serialized_context.encode("utf-8")) > self.MAX_CONTEXT_BYTES:
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.WAITING_FOR_EVIDENCE, trigger,
                                    grounded, regrounded, code="CONTEXT_TOO_LARGE")
            return self._result_after_record(revision, ReasoningStatus.WAITING_FOR_EVIDENCE,
                                             request_id, "CONTEXT_TOO_LARGE")
        if self._contains_secret_key([grounded.value, regrounded.value]):
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.WAITING_FOR_EVIDENCE, trigger,
                                    grounded, regrounded, code="KNOWLEDGE_REDACTION_REJECTED")
            return self._result_after_record(revision, ReasoningStatus.WAITING_FOR_EVIDENCE,
                                             request_id, "KNOWLEDGE_REDACTION_REJECTED")

        implementation_revision = snapshot.get("implementation_revision")
        provider_ref = snapshot.get("provider_ref")
        route = (provider_ref,) + self.fallback_routes.get(provider_ref, ())
        if any(not isinstance(provider_id, str) or provider_id not in self.providers
               for provider_id in route):
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.UNAVAILABLE, trigger, grounded, regrounded,
                                    code="PROVIDER_ROUTE_UNAVAILABLE")
            return self._result_after_record(revision, ReasoningStatus.UNAVAILABLE,
                                             request_id, "PROVIDER_ROUTE_UNAVAILABLE")

        if token_budget < len(route):
            revision = self._record(snapshot, assignment_id, request_id,
                                    ReasoningStatus.INVALID_PROPOSAL, trigger, grounded, regrounded,
                                    code="BUDGET_TOO_SMALL_FOR_ROUTE")
            return self._result_after_record(revision, ReasoningStatus.INVALID_PROPOSAL,
                                             request_id, "BUDGET_TOO_SMALL_FOR_ROUTE")

        # Stable for the same office binding and assignment revision. A restart or
        # duplicate CME cycle therefore reuses the same external-exchange key.
        request_id = str(uuid5(NAMESPACE_URL, "rv-resident-reasoning:" + ":".join((
            self.office_id, assignment_id, str(assignment["revision"]),
            str(snapshot["binding_revision"]), str(implementation_revision), trigger))))
        prior_runtime = snapshot["state"].get(self.STATE_KEY, {})
        prior_plan = prior_runtime.get("plans", {}).get(assignment_id)
        per_attempt_budget = token_budget // len(route)
        request = ReasoningRequest(
            request_id=request_id, office_id=self.office_id, assignment_id=assignment_id,
            assignment_revision=str(assignment["revision"]),
            binding_revision=int(snapshot["binding_revision"]),
            implementation_revision=str(implementation_revision), trigger=trigger,
            token_budget=per_attempt_budget, assignment=assignment,
            verified_knowledge=(
                {"value": grounded.value, **self._knowledge_record(grounded)},
                {"value": regrounded.value, **self._knowledge_record(regrounded)}),
            prior_plan=prior_plan, external_advisory=external_advisory,
            external_reasoning_targets=self.external_reasoning_targets)

        for provider_id in route:
            provider = self.providers[provider_id]
            if getattr(provider, "provider_id", None) != provider_id:
                revision = self._record(snapshot, assignment_id, request_id,
                                        ReasoningStatus.UNAVAILABLE, trigger, grounded, regrounded,
                                        provider_id=provider_id, code="PROVIDER_ID_MISMATCH")
                return self._result_after_record(revision, ReasoningStatus.UNAVAILABLE,
                                                 request_id, "PROVIDER_ID_MISMATCH", provider_id)
            ok, result = self._timed_call.run(lambda: provider.propose(request), self.timeout_seconds)
            if not ok:
                # Only unavailable/timeout can use explicitly configured fallback.
                if provider_id == route[-1]:
                    revision = self._record(snapshot, assignment_id, request_id,
                                            ReasoningStatus.UNAVAILABLE, trigger, grounded, regrounded,
                                            provider_id=provider_id, code="PROVIDER_TIMEOUT_OR_FAILURE")
                    return self._result_after_record(revision, ReasoningStatus.UNAVAILABLE,
                                                     request_id, "PROVIDER_TIMEOUT_OR_FAILURE", provider_id)
                continue
            if not isinstance(result, PlanProposal) or result.tokens_used > request.token_budget:
                revision = self._record(snapshot, assignment_id, request_id,
                                        ReasoningStatus.INVALID_PROPOSAL, trigger, grounded, regrounded,
                                        provider_id=provider_id, code="PROPOSAL_SCHEMA_OR_BUDGET")
                return self._result_after_record(revision, ReasoningStatus.INVALID_PROPOSAL,
                                                 request_id, "PROPOSAL_SCHEMA_OR_BUDGET", provider_id)
            # The persistent runtime role is intentionally denied direct reads of
            # AuthorityRegistry tables. Revalidate authorization and binding via
            # the narrowly granted runtime-safe function.
            latest = self.registry.authorize_office_state(self._credential, self.office_id)
            if (latest.get("binding_revision") != request.binding_revision
                    or latest.get("implementation_revision") != request.implementation_revision):
                revision = self._record(latest, assignment_id, request_id,
                                        ReasoningStatus.STALE_CONTEXT, trigger, grounded, regrounded,
                                        provider_id=provider_id, code="OFFICE_BINDING_CHANGED")
                return self._result_after_record(revision, ReasoningStatus.STALE_CONTEXT,
                                                 request_id, "OFFICE_BINDING_CHANGED", provider_id)
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
                return self._result_after_record(revision, ReasoningStatus.STALE_CONTEXT,
                                                 request_id, "ASSIGNMENT_CHANGED", provider_id)
            revision = self._record(latest, assignment_id, request_id,
                                    ReasoningStatus.PROPOSED, trigger, grounded, regrounded,
                                    provider_id=provider_id, code="PROPOSAL_ONLY",
                                    proposal=result, external_advisory=external_advisory)
            final = self._result_after_record(revision, ReasoningStatus.PROPOSED,
                                              request_id, "PROPOSAL_ONLY", provider_id)
            if final.status is not ReasoningStatus.PROPOSED:
                return final
            if (result.external_escalation is not None and
                    result.external_escalation.target_provider_id not in self.external_reasoning_targets):
                return ReasoningResult(ReasoningStatus.INVALID_PROPOSAL, request_id,
                    "EXTERNAL_PROVIDER_NOT_CONFIGURED", provider_id, final.state_revision)
            return ReasoningResult(final.status, final.request_id, final.detail_code,
                                  final.provider_id, final.state_revision, result, request)
        return ReasoningResult(ReasoningStatus.UNAVAILABLE, request_id, "PROVIDER_UNAVAILABLE")


# Process-wide cap prevents resident replacement/request concurrency from creating
# an unbounded number of orphaned provider threads after timeouts.
_PROVIDER_SLOTS = threading.BoundedSemaphore(8)
