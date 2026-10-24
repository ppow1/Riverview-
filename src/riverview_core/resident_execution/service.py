# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/service.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.44
# Changed: 2026-10-23 UTC | RV-GRACE-APPROVED-PROMOTION-LIFECYCLE-BINDING-20261023 | Bind the exact approved promotion criterion only to matching durable proposal and objective evidence.
# Changed: 2026-10-23 UTC | RV-GRACE-CRITERIA-BINDING-DIAGNOSTICS-20261023 | Record criterion-index mismatch diagnostics without retaining generated proposal text.
# Changed: 2026-10-23 UTC | RV-GRACE-CRITERIA-BINDING-RECOVERY-20261023 | Rebind only unchanged Steward criteria to one existing bounded step after the exact criteria-binding rejection.
# Changed: 2026-10-23 UTC | RV-GRACE-REASONING-FAILURE-FENCE-20261023 | Fence repeated objective reasoning failures by runtime revision and persist a safe blocked diagnostic.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Route only explicitly configured typed ComfyUI proposal steps to the existing capability worker.
# Changed: 2026-10-22 UTC | RV-GRACE-DURABLE-COMPLETION-001 | Reconcile the latest verified step first so terminal evidence uses the final completion cycle after restart.
# Changed: 2026-10-21 UTC | W4-GRACE-REASONING-DIAGNOSTICS-20261021 | Correlate objective proposal persistence outcomes with the resident request
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Service ready dispatch, execution, verification, completion and conversation publication before potentially slow model planning
# Changed: 2026-10-21 UTC | RV-GRACE-PROPOSAL-OUTPUT-BUDGET | Provide enough bounded completion tokens for full typed proposals with dynamic objective criteria
# Changed: 2026-10-20 UTC | RV-GRACE-GROUNDED-OBJECTIVE-FAIR-QUEUE-001 | Persist reasoning turns and skip externally blocked candidates without starving later grounded objectives.
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-002 | Route bounded and Codex artifacts through integrity-checked Grace review context
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Pass verifier-checked artifact sets to Grace review
# Changed: 2026-10-20 UTC | RV-GRACE-REASONING-PROPOSAL-RECOVERY-20261020 | Persist a safe detail code for rejected incomplete proposals
# Changed: 2026-10-20 UTC | RV-GRACE-ACCEPTED-STEP-REWORK-001 | Persist actionable rejection-review escalation when the provider is unavailable or bounded corrections are exhausted.
# Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Reconcile bounded review generations with active production behavior and exact-scope authorization.
# Changed: 2026-10-19 UTC | RV-C4-GRACE-RESULT-RETURN-DIAGNOSTICS | Record sanitized failing return stage and code location for bounded live remediation
# Changed: 2026-10-19 UTC | RV-C1-GRACE-RESULT-RECEIPT-001 | Derive publication acknowledgement cycle from the durable outbox and reject mismatched receipt cycles
# Changed: 2026-10-19 UTC | RV-C1-GRACE-REJECTION-ROLE-CLARIFICATION | Select the latest verifier record identity for exact Grace-review gating and same-attempt revalidation.
# Changed: 2026-10-19 UTC | RV-C1-GRACE-REJECTION-ROLE-CLARIFICATION | Preserve the durable verifier rejection for Grace even when unsafe artifact bytes cannot be reopened for substantive review.
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Poll optional injected ChatGPT wake worker in Grace owner cycle.
# Changed: 2026-10-17 UTC | RV-GRACE-PERSISTENT-AUTONOMY-001 | Persist and rate-limit failed resident proposals.
# Purpose: Reconcile durable Grace work orders through existing CME worker contracts
# Execution Model: Persistent scheduled poll over PostgreSQL objective state
# Observability: Objective events, worker attempts, verification records, dashboard projection
# Dependencies: GraceExecutionPipeline; ContinuousWorker; PostgresWorkerAdapter
# Authority: Exact assignment.create and assignment.verify grants; bounded capability only
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Initial persistent reconciler
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-ISOLATION | Persist verifier errors and avoid per-cycle candidate starvation
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-TEST-SEAM | Keep verifier replaceable behind existing result contract
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Bind optional resident reasoning to durable grounded objectives and office-scoped state
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-FAIR-CYCLE | Attempt at most one grounded objective before continuing CME work
# Changed: 2026-10-13 UTC | RV-SUPERVISED-CODEX-DISPATCH-001 | Add a targeted operator-supervised objective execution cycle
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Select registered execution capability for worker and verification queries
# Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Retry durable verified-result returns to the originating Grace conversation
# Changed: 2026-10-23 UTC | RV-WORKER-HEALTH-SNAPSHOT-20261023 | Publish configured worker capabilities with Grace heartbeat
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Dispatch only dependency-ready verified steps through existing worker leases
# Changed: 2026-10-16 UTC | RV-GRACE-STRUCTURED-REVIEW-001 | Persist cycle-specific result receipts and resume only idempotent same-objective continuations
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Re-evaluate preserved rejected results only when the verifier implementation revision changes
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Resume append-only verifier decisions after a correction, including interrupted completion transition
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-REASONING-BUDGET-001 | Raise bounded resident proposal default to fit typed dependency plans and source scopes
# Changed: 2026-10-18 UTC | RV-C3-EXACT-PROPOSAL-REVIEW-001 | Bind ChatGPT advisory to an exact proposal and support bounded Grace revision loop
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Reconcile existing assignments, execution state and verifier evidence to proposal revisions
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Consume correlated durable external advisory responses in Grace's persistent cycle
# Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Resolve current resident principal and admit typed model-selected advisory requests from grounded reasoning
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Resume durable verifier rejection review before another worker poll and acknowledge after source-chat persistence
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-FIX-001 | Verify only successful attempts without an existing verifier record so rework attempts receive independent review
# Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-ROLE-SEPARATION-001 | Give Grace digest-verified bounded Codex artifact text and verifier evidence for substantive review
# Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-ROLE-SEPARATION-001 | Require Grace's durable objective-satisfied assessment before rechecking an old Codex content rejection
# Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md
# Tests: tests/test_grace_execution.py; tests/test_resident_reasoning.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Persistent, idempotent orchestration over the existing assignment ledger."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5

from ..worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider
from .verifier import BoundedArtifactVerifier
from .worker import CAPABILITY, BoundedLocalCodingWorker

LOG = logging.getLogger("riverview.grace_execution")


class GraceExecutionService:
    """Dispatch authorized proposals, execute one leased action, verify and reconcile.

    Scheduler/event-processor state transitions remain owned by CME. Repeated calls
    are safe: objective state and the stable assignment idempotency key fence duplicate
    dispatch; worker leases and execution intents fence duplicate side effects.
    """

    MAX_REASONING_FAILURES = 3
    REASONING_FAILURE_WINDOW_SECONDS = 60
    # These are deterministic validator rejections for a fixed objective revision.
    # A retry cannot change the approved scope or artifact paths, and counting only
    # failures from the current immutable runtime would reopen the loop on deploy.
    PERSISTED_PROPOSAL_BLOCK_CODES = frozenset({
        "PROPOSAL_CRITERIA_BINDING_REJECTED",
        "PROPOSAL_ARTIFACT_PATH_UNAUTHORIZED",
    })

    def __init__(self, pipeline, adapter, worker, *, dispatch_credential,
                 authority_ref, verifier_id, verifier_credential, artifact_root,
                 max_dispatch_failures=3, verifier=None, resident_reasoner=None,
                 resident_token_budget=2048, execution_capability=CAPABILITY,
                 conversation_result_publisher=None, proposal_lifecycle=None,
                 external_reasoning_exchange=None, external_reasoning_authorize=None,
                 external_reasoning_principal=None, execution_workers=None, verifiers=None,
                 doorbell_worker=None, rejected_work_order_publisher=None,
                 direct_external_reasoning_provider=None):
        if not 1 <= max_dispatch_failures <= 10:
            raise ValueError("dispatch failure limit must be between 1 and 10")
        if type(resident_token_budget) is not int or not 1 <= resident_token_budget <= 4096:
            raise ValueError("resident reasoning token budget must be bounded")
        self.pipeline = pipeline
        self.adapter = adapter
        self.worker = worker
        self.dispatch_credential = dispatch_credential
        self.authority_ref = authority_ref
        self.verifier_id = verifier_id
        self.verifier_credential = verifier_credential
        self.verifier = verifier or BoundedArtifactVerifier(artifact_root, pipeline)
        self.max_dispatch_failures = max_dispatch_failures
        self.resident_reasoner = resident_reasoner
        self.resident_token_budget = resident_token_budget
        if not isinstance(execution_capability, str) or not execution_capability:
            raise ValueError("a registered execution capability is required")
        self.execution_capability = execution_capability
        if execution_workers is None:
            self.execution_workers = {execution_capability: worker}
        elif (not isinstance(execution_workers, Mapping) or not execution_workers or
              len(execution_workers) > 4 or any(not isinstance(key, str) or not key
                                                 for key in execution_workers)):
            raise ValueError("bounded execution workers keyed by capability are required")
        else:
            self.execution_workers = dict(execution_workers)
        if (execution_workers is not None and
                any(not callable(getattr(item, "run_once", None))
                    for item in self.execution_workers.values())):
            raise ValueError("each configured execution capability requires a worker loop")
        self.execution_capabilities = tuple(self.execution_workers)
        if verifiers is None:
            if len(self.execution_capabilities) != 1:
                raise ValueError("each enabled capability requires its independent verifier")
            self.verifiers = {execution_capability: self.verifier}
        else:
            self.verifiers = dict(verifiers)
            if (set(self.verifiers) != set(self.execution_capabilities) or
                    any(not callable(getattr(item, "verify", None))
                        for item in self.verifiers.values())):
                raise ValueError("each enabled capability requires its independent verifier")
        self.source_target_validators = {
            capability: getattr(getattr(item, "action", None), "validate_proposal_target", None)
            for capability, item in self.execution_workers.items()}
        if conversation_result_publisher is not None and not callable(conversation_result_publisher):
            raise ValueError("conversation result publisher must be callable")
        self.conversation_result_publisher = conversation_result_publisher
        if (rejected_work_order_publisher is not None and
                not callable(rejected_work_order_publisher)):
            raise ValueError("rejected work-order publisher must be callable")
        self.rejected_work_order_publisher = rejected_work_order_publisher
        if proposal_lifecycle is not None and not callable(
                getattr(proposal_lifecycle, "reconcile_links", None)):
            raise ValueError("proposal lifecycle reconciliation contract is invalid")
        self.proposal_lifecycle = proposal_lifecycle
        if (external_reasoning_exchange is None) != (external_reasoning_authorize is None):
            raise ValueError("external reasoning exchange and authorizer must be configured together")
        if external_reasoning_exchange is not None and not callable(external_reasoning_authorize):
            raise ValueError("external reasoning authorizer must be callable")
        self.external_reasoning_exchange = external_reasoning_exchange
        self.external_reasoning_authorize = external_reasoning_authorize
        self.external_reasoning_principal = external_reasoning_principal
        self.direct_external_reasoning_provider = direct_external_reasoning_provider
        if (direct_external_reasoning_provider is not None and
                (external_reasoning_exchange is None or
                 not callable(getattr(direct_external_reasoning_provider, "process_one", None)))):
            raise ValueError("direct external provider requires the existing durable exchange")
        if doorbell_worker is not None and not callable(getattr(doorbell_worker, "run_once", None)):
            raise ValueError("doorbell worker must provide a bounded run_once method")
        self.doorbell_worker = doorbell_worker
        if (external_reasoning_exchange is not None and
                (not isinstance(external_reasoning_principal, str) or
                 not external_reasoning_principal or
                 external_reasoning_principal == getattr(resident_reasoner, "office_id", None))):
            raise ValueError("external reasoning requires the principal from the active office binding")
        self.instance_id = uuid4()
        # Bind the retry-fence identity to the immutable code this process
        # loaded. Resolving the mutable `current` symlink per attempt can make
        # an old running process label its failures as a newly installed
        # release during an atomic switch.
        self._loaded_runtime_revision = self._read_runtime_revision()

    def _proposal_worker_capability(self, step):
        """Resolve legacy artifact plan labels to the sole configured artifact loop.

        Source-change plans always require an exact capability match. Older
        bounded artifact runtimes used a different registry label from the
        default Codex artifact label stored in typed plans.
        """
        if not isinstance(step, Mapping):
            requested = "engineering.codex-cli-artifact.v1"
        else:
            requested = step.get("execution_capability", "engineering.codex-cli-artifact.v1")
        source = "engineering.codex-cli-source-change.v1"
        if requested == source:
            return source if source in self.execution_workers else None
        comfyui = "engineering.comfyui-image.v1"
        if requested == comfyui:
            return comfyui if comfyui in self.execution_workers else None
        artifact_caps = {"engineering.codex-cli-artifact.v1",
                         "engineering.bounded-artifact.v1"}
        if requested not in artifact_caps:
            return None
        configured = [capability for capability in self.execution_capabilities
                      if capability in artifact_caps]
        if requested in configured:
            return requested
        return configured[0] if len(configured) == 1 else None

    def _with_grace_artifact_review(self, context):
        """Attach bounded reopened Codex artifact text, never a host path alone."""
        completion = context.get("completion") if isinstance(context, Mapping) else None
        artifact = completion.get("artifact") if isinstance(completion, Mapping) else None
        if not isinstance(artifact, Mapping):
            return context
        capability = artifact.get("capability")
        if capability not in {"engineering.codex-cli-artifact.v1",
                              "engineering.bounded-artifact.v1"}:
            return context
        verifier = self.verifiers.get(capability)
        reader = getattr(verifier, "read_artifact_for_grace_review", None)
        if not callable(reader):
            return {**context, "artifact_review": None,
                    "artifact_review_unavailable": "integrity_check_failed"}
        try:
            review_material = reader(context.get("assignment_id"), artifact)
        except (OSError, UnicodeError, ValueError):
            # Keep the immutable verifier failure visible to Grace even when the
            # artifact itself is unsafe to pass as trusted review text.
            return {**context, "artifact_review": None,
                    "artifact_review_unavailable": "integrity_check_failed"}
        return {**context, "artifact_review": review_material,
                "artifact_review_unavailable": None}

    def reason_one_grounded_objective(self, objective_id=None):
        """Propose for one verified objective; office authority never dispatches work."""
        if self.resident_reasoner is None or not self.resident_reasoner.providers:
            return False
        from ..resident_reasoning import ReasoningStatus
        rows = self.pipeline.grounded_objectives(scope_ref=self.authority_ref, limit=25,
                                                 objective_id=objective_id)
        candidate = None
        for row in rows:
            candidate_id = row["objective_id"]
            candidate_revision = row.get("revision")
            if (self.external_reasoning_exchange is not None and
                    (self.external_reasoning_exchange.has_active_for_objective(candidate_id) or
                     self.external_reasoning_exchange.has_terminal_review_for_objective(candidate_id))):
                continue
            recovery_request_id = None
            experiment_authorization = None
            if (type(candidate_revision) is int and
                    self._proposal_rejection_blocked(candidate_id, candidate_revision)):
                recovery_request_id = self._claim_approved_recovery(candidate_id,
                                                                    candidate_revision)
                if recovery_request_id is None:
                    experiment_authorization = self._claim_experiment_recovery(
                        candidate_id, candidate_revision)
                    if experiment_authorization is None:
                        continue
            if (recovery_request_id is None and
                    self._reasoning_failure_count(candidate_id) >= self.MAX_REASONING_FAILURES):
                continue
            candidate = {**row, "recovery_request_id": recovery_request_id,
                "experiment_authorization": experiment_authorization}
            break
        if candidate is None:
            return False
        objective_id = candidate["objective_id"]
        self._current_objective_id = objective_id
        try:
            self._record_reasoning_attempt(objective_id,
                recovery_request_id=candidate.get("recovery_request_id"),
                experiment_authorization=candidate.get("experiment_authorization"))
            result = self.resident_reasoner.propose(
                objective_id, trigger="persistent_resident_cycle",
                token_budget=self.resident_token_budget)
            if result.status is ReasoningStatus.PROPOSED and result.proposal is not None:
                if result.proposal.external_escalation is not None:
                    if result.reasoning_request is None:
                        raise RuntimeError("external_escalation_context_missing")
                    from ..reasoning_escalation import EscalationRequest
                    from .external_reasoning import build_review_subject
                    intent = result.proposal.external_escalation
                    subject_id = str(uuid5(NAMESPACE_URL,
                        "rv-grace-review-subject:" + result.reasoning_request.request_id + ":" +
                        intent.target_provider_id))
                    review_subject = build_review_subject(subject_id, 1, result.proposal)
                    escalation_id = str(uuid5(NAMESPACE_URL,
                        "rv-external-escalation:" + result.reasoning_request.request_id + ":" +
                        intent.target_provider_id + ":" + review_subject["sha256"]))
                    envelope = EscalationRequest.create(result.reasoning_request,
                        reason=intent.reason, target_provider_id=intent.target_provider_id,
                        max_tokens=min(512, self.resident_token_budget), timeout_seconds=30,
                        escalation_id=escalation_id)
                    received = next((event for event in
                        self.pipeline.objective_events(objective_id)
                        if event.get("event_type") == "objective.received"), None)
                    origin = (received or {}).get("payload", {}).get("origin")
                    if not isinstance(origin, dict):
                        raise RuntimeError("external_escalation_conversation_origin_missing")
                    proposal_ref = (received or {}).get("payload", {}).get("proposal_reference")
                    classification = "institutional"
                    proposal_id = proposal_revision = None
                    if isinstance(proposal_ref, dict):
                        classification = proposal_ref.get("privacy_classification", "institutional")
                        proposal_id = proposal_ref.get("proposal_id")
                        proposal_revision = proposal_ref.get("revision")
                    if classification not in {"institutional", "confidential"}:
                        raise RuntimeError("external_escalation_classification_not_permitted")
                    references = tuple(dict.fromkeys(
                        ref for item in result.reasoning_request.verified_knowledge
                        for ref in item.get("source_references", ())))[:32]
                    self.request_external_reasoning(envelope, result.reasoning_request,
                        conversation_id=origin["conversation_id"],
                        message_sequence=origin["source_sequence"],
                        idempotency_key=("grace-escalation:" +
                            result.reasoning_request.request_id + ":" +
                            intent.target_provider_id + ":" + review_subject["sha256"]),
                        deadline_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                        classification=classification, proposal_id=proposal_id,
                        proposal_revision=proposal_revision, source_references=references,
                        review_subject=review_subject)
                    self._record_experiment_outcome(candidate.get("experiment_authorization"),
                        outcome="escalation_queued", detail_code=None)
                    return True
                proposal_persist_started = time.monotonic()
                proposal_to_persist = result.proposal
                from ..resident_reasoning import lifecycle_evidence_event
                objective_snapshot = self.pipeline.get_objective(objective_id)
                omitted_verified = [criterion for criterion in
                    (objective_snapshot or {}).get("acceptance_criteria", ())
                    if lifecycle_evidence_event(criterion) == "proposal.approved_and_promoted"
                    and criterion not in {item for step in proposal_to_persist.steps
                                          for item in step.acceptance_criteria}
                    and criterion not in proposal_to_persist.system_owned_criteria]
                if omitted_verified:
                    with self.pipeline.ledger.db.cursor() as cur:
                        self.pipeline.ledger._set_search_path(cur)
                        bound = [criterion for criterion in omitted_verified
                            if self.pipeline.proposal_promotion_evidence(
                                cur, objective_id, criterion)]
                    if len(bound) == len(omitted_verified):
                        proposal_to_persist = replace(proposal_to_persist,
                            system_owned_criteria=tuple(
                                (*proposal_to_persist.system_owned_criteria, *bound)))
                try:
                    self.pipeline.record_proposal(
                        objective_id, proposal_to_persist,
                        actor_id="office:" + self.resident_reasoner.office_id)
                except Exception as exc:
                    if self._reasoning_failure_detail_code(exc) == "PROPOSAL_CRITERIA_BINDING_REJECTED":
                        request = result.reasoning_request
                        assignment = getattr(request, "assignment", None)
                        objective_snapshot = self.pipeline.get_objective(objective_id)
                        approved_criteria = (objective_snapshot or {}).get("acceptance_criteria", ())
                        if not approved_criteria and isinstance(assignment, Mapping):
                            approved_criteria = assignment.get("acceptance_criteria", ())
                        received = next((event for event in self.pipeline.objective_events(objective_id)
                            if event.get("event_type") == "objective.received"), None)
                        origin = (received or {}).get("payload", {}).get("origin")
                        has_conversation_origin = (isinstance(origin, Mapping) and
                            isinstance(origin.get("conversation_id"), str) and
                            bool(origin.get("conversation_id")))
                        criteria_diagnostic = self._criteria_binding_diagnostics(
                            result.proposal, approved_criteria, has_conversation_origin)
                        LOG.warning(json.dumps({
                            "event": "resident_proposal_criteria_binding_diagnostic",
                            "objective_id": objective_id,
                            "request_id": result.request_id,
                            "objective_revision": candidate_revision,
                            **criteria_diagnostic,
                        }, sort_keys=True))
                        repaired = self._restore_exact_single_step_criteria(
                            result.proposal, assignment)
                        if repaired is not None:
                            self.pipeline.record_proposal(objective_id, repaired,
                                actor_id="office:" + self.resident_reasoner.office_id)
                            LOG.info(json.dumps({
                                "event": "resident_proposal_criteria_reconciled",
                                "objective_id": objective_id,
                                "request_id": result.request_id,
                                "objective_revision": candidate_revision,
                                "step_count": 1,
                                "criteria_count": len(assignment["acceptance_criteria"]),
                                "criteria_source": "steward_supplied_exact",
                            }, sort_keys=True))
                            return True
                    LOG.warning(json.dumps({
                        "event": "resident_objective_proposal_persistence_failed",
                        "request_id": result.request_id,
                        "objective_id": objective_id,
                        "operation": "pipeline.record_proposal",
                        "failure_type": type(exc).__name__,
                        "detail_code": self._reasoning_failure_detail_code(exc),
                        "elapsed_ms": round((time.monotonic() - proposal_persist_started) * 1000),
                    }, sort_keys=True))
                    raise
                LOG.info(json.dumps({
                    "event": "resident_objective_proposal_persisted",
                    "request_id": result.request_id,
                    "objective_id": objective_id,
                    "operation": "pipeline.record_proposal",
                    "elapsed_ms": round((time.monotonic() - proposal_persist_started) * 1000),
                }, sort_keys=True))
                self._record_experiment_outcome(candidate.get("experiment_authorization"),
                    outcome="proposal_persisted", detail_code=None)
                return True
            self._record_reasoning_failure(objective_id, result=result,
                experiment_authorization=candidate.get("experiment_authorization"))
        except Exception as exc:
            detail_code = self._reasoning_failure_detail_code(exc)
            blocked_revision = (candidate_revision
                if detail_code in self.PERSISTED_PROPOSAL_BLOCK_CODES and
                type(candidate_revision) is int else None)
            failure_count = self._record_reasoning_failure(objective_id,
                failure_type=type(exc).__name__, detail_code=detail_code,
                blocked_revision=blocked_revision,
                experiment_authorization=candidate.get("experiment_authorization"))
            LOG.warning(json.dumps({"event": "resident_reasoning_cycle_failed",
                "objective_id": objective_id,
                "failure_type": type(exc).__name__,
                "detail_code": detail_code,
                "consecutive_failure_count": failure_count,
                "reasoning_status": "BLOCKED" if blocked_revision is not None else "RETRY_LIMITED",
                **({"objective_revision": blocked_revision}
                   if blocked_revision is not None else {})}, sort_keys=True))
        return False

    @staticmethod
    def _reasoning_failure_detail_code(exc):
        """Expose only a fixed diagnostic code; never log exception or prompt text."""
        if type(exc).__name__ == "ObjectiveStateError":
            # Keep validator evidence useful without persisting model output or
            # arbitrary exception text. These strings are internal fixed errors.
            return {
                "proposal omits one or more human acceptance criteria":
                    "PROPOSAL_OMITS_ACCEPTANCE_CRITERIA",
                "proposal must bind every original criterion to an Engineering step or a supported lifecycle event":
                    "PROPOSAL_CRITERIA_BINDING_REJECTED",
                "approved-promotion lifecycle evidence is not durably bound":
                    "PROPOSAL_LIFECYCLE_EVIDENCE_UNBOUND",
                "proposal cannot use missing or incomplete evidence":
                    "PROPOSAL_EVIDENCE_INCOMPLETE",
                "proposal acceptance-criteria source is invalid":
                    "PROPOSAL_CRITERIA_SOURCE_INVALID",
                "Grace-derived proposal criteria are empty, excessive, or duplicated":
                    "PROPOSAL_DERIVED_CRITERIA_INVALID",
                "source-change target identity and commit must be Steward-authorized":
                    "PROPOSAL_SOURCE_TARGET_UNAUTHORIZED",
                "source-change path is absent from the Steward-approved objective scope":
                    "PROPOSAL_SOURCE_PATH_UNAUTHORIZED",
                "artifact path is absent from the Steward-approved objective scope":
                    "PROPOSAL_ARTIFACT_PATH_UNAUTHORIZED",
                "external advisory provenance is invalid":
                    "PROPOSAL_EXTERNAL_ADVISORY_INVALID",
                "external advisory correlation is invalid":
                    "PROPOSAL_EXTERNAL_CORRELATION_INVALID",
                "exact proposal review evidence is invalid":
                    "PROPOSAL_REVIEW_EVIDENCE_INVALID",
                "final proposal does not match its exact review subject":
                    "PROPOSAL_REVIEW_BINDING_REJECTED",
                "objective changed during proposal":
                    "PROPOSAL_OBJECTIVE_STATE_CHANGED",
            }.get(str(exc), "REASONING_CYCLE_FAILED")
        return "REASONING_CYCLE_FAILED"

    @staticmethod
    def _restore_exact_single_step_criteria(proposal, assignment):
        """Rebind verbatim approved criteria to one existing step; never widen scope."""
        from ..resident_reasoning import PlanProposal, lifecycle_evidence_event
        if (not isinstance(proposal, PlanProposal) or len(proposal.steps) != 1 or
                not isinstance(assignment, Mapping) or
                assignment.get("acceptance_criteria_source") != "steward_supplied"):
            return None
        criteria = assignment.get("acceptance_criteria")
        if (not isinstance(criteria, (list, tuple)) or not 1 <= len(criteria) <= 20 or
                any(not isinstance(item, str) or not item.strip() for item in criteria) or
                len(criteria) != len(set(criteria))):
            return None
        accepted_lifecycle = tuple(item for item in proposal.system_owned_criteria
            if item in criteria and lifecycle_evidence_event(item) is not None)
        step_criteria = tuple(item for item in criteria if item not in accepted_lifecycle)
        step = replace(proposal.steps[0], acceptance_criteria=step_criteria)
        return replace(proposal, steps=(step,), system_owned_criteria=accepted_lifecycle)

    @staticmethod
    def _criteria_binding_diagnostics(proposal, requested_criteria, has_conversation_origin=False):
        """Report safe criterion alignment counts and indices, never generated text."""
        from ..resident_reasoning import PlanProposal, lifecycle_evidence_event
        requested = list(requested_criteria) if isinstance(requested_criteria, (list, tuple)) else []
        if not isinstance(proposal, PlanProposal) or any(not isinstance(c, str) for c in requested):
            return {"diagnostic_code": "UNAVAILABLE", "requested_count": len(requested)}
        step_criteria = [c for step in proposal.steps for c in step.acceptance_criteria]
        step_set = set(step_criteria)
        lifecycle = list(proposal.system_owned_criteria)
        lifecycle_set = set(lifecycle)
        artifact_criteria = {c for step in proposal.steps for requirement in step.artifact_requirements
                             for c in requirement.acceptance_criteria}
        requested_set = set(requested)
        missing = [i + 1 for i, criterion in enumerate(requested)
                   if criterion not in step_set and criterion not in lifecycle_set]
        supplemental = step_set - requested_set
        invalid_lifecycle = [i + 1 for i, criterion in enumerate(lifecycle)
                             if criterion not in requested_set or lifecycle_evidence_event(criterion) is None]
        reasons = []
        if len(step_criteria) != len(step_set):
            reasons.append("DUPLICATE_STEP_CRITERIA")
        if step_set & lifecycle_set:
            reasons.append("STEP_SYSTEM_OWNED_OVERLAP")
        if missing:
            reasons.append("UNBOUND_APPROVED_CRITERIA")
        if supplemental - artifact_criteria:
            reasons.append("UNAPPROVED_SUPPLEMENTAL_STEP_CRITERIA")
        if invalid_lifecycle:
            reasons.append("UNSUPPORTED_OR_UNAPPROVED_SYSTEM_OWNED_CRITERIA")
        if (any(lifecycle_evidence_event(c) == "work_order.exactly_one_dispatched" for c in lifecycle)
                and len(proposal.steps) != 1):
            reasons.append("DISPATCH_CRITERION_REQUIRES_SINGLE_STEP")
        if (not has_conversation_origin and any(
                lifecycle_evidence_event(c) == "conversation.result_published" for c in lifecycle)):
            reasons.append("CONVERSATION_CRITERION_WITHOUT_ORIGIN")
        if step_set | lifecycle_set != requested_set and "UNBOUND_APPROVED_CRITERIA" not in reasons:
            reasons.append("CRITERION_SET_MISMATCH")
        return {"diagnostic_code": "CRITERIA_BINDING_REJECTED",
                "requested_count": len(requested),
                "step_count": len(proposal.steps),
                "step_criterion_count": len(step_criteria),
                "unique_step_criterion_count": len(step_set),
                "system_owned_criterion_count": len(lifecycle),
                "missing_approved_criterion_indices": missing,
                "invalid_system_owned_criterion_indices": invalid_lifecycle,
                "supplemental_step_criterion_count": len(supplemental),
                "unapproved_supplemental_criterion_count": len(supplemental - artifact_criteria),
                "reason_codes": reasons}

    def _runtime_revision(self):
        return self._loaded_runtime_revision

    @staticmethod
    def _read_runtime_revision():
        # Immutable releases carry their own source marker. Prefer it over a
        # systemd drop-in that can outlive a release switch and mislabel events.
        try:
            from pathlib import Path
            marker = Path(__file__).resolve().parents[3] / "SOURCE_COMMIT"
            value = marker.read_text(encoding="ascii").strip()
            if re.fullmatch(r"[0-9a-f]{40}", value):
                return value
        except (OSError, UnicodeError):
            pass
        value = os.environ.get("RIVERVIEW_SOURCE_COMMIT", "")
        return value if re.fullmatch(r"[0-9a-f]{40}", value) else "unversioned"

    def _proposal_rejection_blocked(self, objective_id, objective_revision):
        """Suppress deterministic proposal rejection repeats for this objective revision."""
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT 1 FROM grace_objective_events
                WHERE objective_id=%s AND event_type='execution.reasoning_failed'
                  AND payload->>'detail_code'=ANY(%s)
                  AND ((payload->>'status'='BLOCKED'
                        AND payload->>'objective_revision'=%s)
                    OR (payload->>'detail_code'='PROPOSAL_ARTIFACT_PATH_UNAUTHORIZED'
                        AND payload->>'objective_revision' IS NULL
                        AND sequence > COALESCE((SELECT max(sequence)
                            FROM grace_objective_events
                            WHERE objective_id=%s AND event_type='objective.grounded'),0)))
                ORDER BY sequence DESC LIMIT 1""",
                (objective_id, list(self.PERSISTED_PROPOSAL_BLOCK_CODES),
                 str(objective_revision), objective_id))
            return cur.fetchone() is not None

    def _reasoning_failure_count(self, objective_id):
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT count(*) AS failures FROM grace_objective_events
                WHERE objective_id=%s AND event_type='execution.reasoning_failed'
                  AND payload->>'runtime_revision'=%s
                  AND sequence > COALESCE((SELECT max(sequence) FROM grace_objective_events
                      WHERE objective_id=%s AND event_type='work_order.proposed'),0)""",
                (objective_id, self._runtime_revision(), objective_id))
            return int(cur.fetchone()["failures"])

    def _record_reasoning_attempt(self, objective_id, *, recovery_request_id=None,
                                  experiment_authorization=None):
        request_id = str(uuid4())
        key = f"grace-reasoning-attempt:{objective_id}:{request_id}"
        payload = {}
        if recovery_request_id:
            payload.update({"authorized_recovery_request_id": recovery_request_id,
                            "recovery_attempt_limit": 1})
        if experiment_authorization:
            payload.update({"experiment_authorization_id": experiment_authorization["authorization_id"],
                "experiment_recovery_attempt": experiment_authorization["attempt_number"],
                "experiment_recovery_limit": 5})
        with self.pipeline.ledger.db.transaction():
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'execution.reasoning_attempted',%s,
                        'service:grace-execution',%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (objective_id, key, json.dumps(payload, sort_keys=True,
                        separators=(",", ":"))))

    def _claim_experiment_recovery(self, objective_id, objective_revision):
        """Atomically consume one exact, non-repeating use of the standing grant."""
        from .grace_experiment_authorization import GraceExperimentAuthorization
        scope_ref = GraceExperimentAuthorization.scope_ref(objective_id, objective_revision)
        try:
            with self.pipeline.ledger.db.transaction(), self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""SELECT * FROM grace_experiment_authorizations
                    WHERE objective_id=%s AND objective_revision=%s AND status='active'
                      AND activated_at<=clock_timestamp() AND expires_at>clock_timestamp()
                    ORDER BY activated_at DESC LIMIT 1 FOR UPDATE""",
                    (objective_id, objective_revision))
                auth = cur.fetchone()
                if auth is None:
                    return None
                grant = self.pipeline.authorizer.require_grace_experiment_grant(
                    cur, auth["authority_grant_id"], scope_ref)
                if grant["grant_id"] != auth["authority_grant_id"]:
                    return None
                cur.execute("""SELECT count(*) AS used FROM grace_experiment_authorization_events
                    WHERE authorization_id=%s AND event_type='recovery_claimed'""",
                    (auth["authorization_id"],))
                used = int(cur.fetchone()["used"])
                if used >= int(auth["max_recovery_attempts"]):
                    return None
                cur.execute("""SELECT payload FROM grace_experiment_authorization_events
                    WHERE authorization_id=%s AND event_type='reasoning_outcome'
                    ORDER BY occurred_at DESC,event_id DESC LIMIT 1""",
                    (auth["authorization_id"],))
                prior = cur.fetchone()
                if prior and prior["payload"].get("outcome") == "failed" and \
                        prior["payload"].get("runtime_revision") == self._runtime_revision():
                    LOG.info(json.dumps({"event":"grace_experiment_retry_suppressed",
                        "objective_id":objective_id,"authorization_id":str(auth["authorization_id"]),
                        "reason":"same_runtime_failure_has_no_new_diagnostic_information"},sort_keys=True))
                    return None
                attempt_number = used + 1
                auth_id = str(auth["authorization_id"])
                cur.execute("""INSERT INTO grace_experiment_authorization_events
                    (authorization_id,event_type,idempotency_key,objective_id,payload)
                    VALUES (%s,'recovery_claimed',%s,%s,%s::jsonb)""",
                    (auth["authorization_id"],
                     f"grace-experiment:{auth_id}:recovery:{attempt_number}",objective_id,
                     json.dumps({"attempt_number":attempt_number,
                         "attempt_limit":int(auth["max_recovery_attempts"]),
                         "objective_revision":objective_revision},sort_keys=True)))
                event_payload=json.dumps({"authorization_id":auth_id,
                    "authority_grant_id":auth["authority_grant_id"],
                    "attempt_number":attempt_number,"attempt_limit":5,
                    "objective_revision":objective_revision},sort_keys=True)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'execution.recovery_authorized',%s,
                        'service:grace-execution',%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (objective_id,f"grace-experiment-recovery:{auth_id}:{attempt_number}",
                     event_payload))
                return {"authorization_id":auth_id,"attempt_number":attempt_number}
        except Exception as exc:
            LOG.warning(json.dumps({"event":"grace_experiment_authorization_unavailable",
                "objective_id":objective_id,"failure_type":type(exc).__name__},sort_keys=True))
            return None

    def _record_experiment_outcome(self, experiment_authorization, *, outcome, detail_code,
                                   failure_type=None):
        if not experiment_authorization:
            return
        auth_id=experiment_authorization["authorization_id"]
        attempt_number=experiment_authorization["attempt_number"]
        payload={"outcome":outcome,"attempt_number":attempt_number,
            "runtime_revision":self._runtime_revision()}
        if detail_code:
            payload["detail_code"]=detail_code
        if failure_type and re.fullmatch(r"[A-Za-z0-9_]{1,80}",failure_type):
            payload["failure_type"]=failure_type
        try:
            with self.pipeline.ledger.db.transaction(), self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_experiment_authorization_events
                    (authorization_id,event_type,idempotency_key,objective_id,payload)
                    VALUES (%s,'reasoning_outcome',%s,%s,%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (auth_id,f"grace-experiment:{auth_id}:outcome:{attempt_number}",
                     self._current_objective_id,json.dumps(payload,sort_keys=True)))
        except Exception as exc:
            LOG.warning(json.dumps({"event":"grace_experiment_outcome_record_failed",
                "authorization_id":auth_id,"failure_type":type(exc).__name__},sort_keys=True))

    def _claim_approved_recovery(self, objective_id, objective_revision):
        """Consume one exact, unexpired Steward authorization; never lifts other fences."""
        try:
            with self.pipeline.ledger.db.transaction():
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""SELECT r.request_id,r.source_event_id
                        FROM grace_recovery_decision_requests r
                        JOIN cme_monitor_events e ON e.event_id=r.source_event_id
                        JOIN grace_recovery_decision_events d ON d.request_id=r.request_id
                          AND d.decision='approve'
                        WHERE r.objective_id=%s AND r.objective_revision=%s
                          AND r.recovery_action='retry_reasoning_once' AND r.attempt_limit=1
                          AND r.status='approved' AND r.expires_at>clock_timestamp()
                          AND e.event_type='grace_objective_blocked'
                          AND e.details->>'objective_id'=r.objective_id
                          AND (e.details->>'objective_revision')::integer=r.objective_revision
                          AND EXISTS (SELECT 1 FROM grace_objective_events b
                            WHERE b.objective_id=r.objective_id
                              AND b.event_type='execution.reasoning_failed'
                              AND b.payload->>'status'='BLOCKED'
                              AND b.payload->>'objective_revision'=r.objective_revision::text)
                        ORDER BY d.recorded_at DESC LIMIT 1 FOR UPDATE OF r SKIP LOCKED""",
                        (objective_id, objective_revision))
                    row = cur.fetchone()
                    if row is None:
                        return None
                    request_id = str(row["request_id"])
                    cur.execute("""UPDATE grace_recovery_decision_requests
                        SET status='dispatched' WHERE request_id=%s AND status='approved'
                        RETURNING request_id""", (row["request_id"],))
                    if cur.fetchone() is None:
                        return None
                    payload = json.dumps({"request_id": request_id,
                        "source_event_id": str(row["source_event_id"]),
                        "objective_id": objective_id,
                        "objective_revision": objective_revision,
                        "recovery_action": "retry_reasoning_once", "attempt_limit": 1},
                        sort_keys=True, separators=(",", ":"))
                    cur.execute("""INSERT INTO grace_objective_events
                        (objective_id,event_type,idempotency_key,actor_id,payload)
                        VALUES (%s,'execution.recovery_authorized',%s,
                          'service:grace-execution',%s::jsonb)
                        ON CONFLICT (idempotency_key) DO NOTHING""",
                        (objective_id, f"grace-recovery-dispatched:{request_id}", payload))
                    return request_id
        except Exception as exc:
            # Missing migration or unavailable authority ledger fails closed.
            LOG.warning(json.dumps({"event": "grace_recovery_authorization_unavailable",
                "objective_id": objective_id, "failure_type": type(exc).__name__},
                sort_keys=True))
            return None

    def _record_reasoning_failure(self, objective_id, *, result=None, failure_type=None,
                                  detail_code=None, blocked_revision=None,
                                  experiment_authorization=None):
        status = getattr(getattr(result, "status", None), "value", None)
        detail_code = detail_code or getattr(result, "detail_code", None)
        request_id = getattr(result, "request_id", None)
        if not isinstance(request_id, str) or not request_id:
            request_id = str(uuid4())
        if not isinstance(status, str) or not re.fullmatch(r"[A-Z_]{1,48}", status):
            status = "UNAVAILABLE"
        if not isinstance(detail_code, str) or not re.fullmatch(r"[A-Z0-9_]{1,80}", detail_code):
            detail_code = "REASONING_CYCLE_FAILED"
        if not isinstance(failure_type, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,80}", failure_type):
            failure_type = None
        key = f"grace-reasoning-failure:{objective_id}:{request_id}"
        payload = {"status": "BLOCKED" if type(blocked_revision) is int else status,
                   "detail_code": detail_code, "failure_type": failure_type,
                   "runtime_revision": self._runtime_revision()}
        if type(blocked_revision) is int:
            payload["objective_revision"] = blocked_revision
        with self.pipeline.ledger.db.transaction():
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'execution.reasoning_failed',%s,'service:grace-execution',%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (objective_id, key, json.dumps(payload, sort_keys=True,
                                                  separators=(",", ":"))))
        self._record_experiment_outcome(experiment_authorization,
            outcome="failed", detail_code=detail_code, failure_type=failure_type)
        return self._reasoning_failure_count(objective_id)

    def revalidate_rejected_one(self, assignment_id=None):
        """Append a new verifier decision after a verifier revision correction.

        The original rejection and result remain immutable. Only the same
        successful attempt may be reconsidered, and verify_attempt rechecks the
        current exact verifier grant plus the previous decision and revision.
        """
        available = {capability: verifier for capability, verifier in self.verifiers.items()
                     if isinstance(getattr(verifier, "REVISION", None), str) and
                     getattr(verifier, "REVISION", None)}
        if not available:
            return False
        with self.adapter.ledger.db.cursor() as cur:
            self.adapter.ledger._set_search_path(cur)
            cur.execute("""SELECT a.id AS assignment_id,a.objective_ref,wa.attempt_id,wa.capability,
                    latest.verification_id,latest.decision,latest.verifier_revision,
                    EXISTS (SELECT 1 FROM verification_records previous
                        WHERE previous.attempt_id=wa.attempt_id
                          AND previous.verifier_id=%s AND previous.decision='REJECTED'
                          AND previous.verifier_revision<>latest.verifier_revision) AS prior_rejection
                FROM assignments a
                JOIN worker_attempts wa ON wa.assignment_id=a.id
                JOIN LATERAL (
                    SELECT verification_id,decision,verifier_id,verifier_revision
                    FROM verification_records vr WHERE vr.attempt_id=wa.attempt_id
                    ORDER BY recorded_at DESC,verification_id DESC LIMIT 1
                ) latest ON true
                WHERE a.state='rework_required' AND wa.status='succeeded'
                  AND wa.capability=ANY(%s) AND latest.verifier_id=%s
                  AND latest.decision IN ('REJECTED','ACCEPTED')
                  AND NOT EXISTS (SELECT 1 FROM worker_attempts newer
                    WHERE newer.assignment_id=wa.assignment_id
                      AND (newer.started_at,newer.attempt_id)>(wa.started_at,wa.attempt_id))
                  AND (%s::text IS NULL OR a.id=%s)
                ORDER BY a.updated_at,wa.started_at,wa.attempt_id LIMIT 10""",
                (self.verifier_id, list(available), self.verifier_id,
                 assignment_id, assignment_id))
            candidates = cur.fetchall()
        for candidate in candidates:
            capability = candidate.get("capability")
            selected_verifier = available.get(capability)
            if selected_verifier is None:
                continue
            verifier_revision = selected_verifier.REVISION
            if capability == "engineering.codex-cli-artifact.v1":
                reviewed = any(event["event_type"] == "engineering.rejection_reviewed" and
                    (event.get("payload") or {}).get("decision") == "OBJECTIVE_SATISFIED" and
                    (event.get("payload") or {}).get("attempt_id") == str(candidate["attempt_id"]) and
                    (candidate["decision"] != "REJECTED" or
                     (event.get("payload") or {}).get("verification_id") ==
                        str(candidate["verification_id"]))
                    for event in self.pipeline.objective_events(candidate["objective_ref"]))
                if not reviewed:
                    continue
            if (candidate["decision"] == "REJECTED" and
                    candidate["verifier_revision"] == verifier_revision):
                continue
            if (candidate["decision"] == "ACCEPTED" and
                    (candidate["verifier_revision"] != verifier_revision or
                     not candidate["prior_rejection"])):
                continue
            key = (f"grace-verifier-revalidation:{candidate['attempt_id']}:{verifier_revision}")
            try:
                self.adapter.verify_attempt(candidate["assignment_id"], candidate["attempt_id"],
                    self.verifier_id, self.verifier_credential, selected_verifier,
                    idempotency_key=key)
                return True
            except Exception as exc:
                LOG.warning(json.dumps({"event": "grace_verifier_revalidation_failed",
                    "assignment_id": candidate["assignment_id"],
                    "failure_type": type(exc).__name__}, sort_keys=True))
        return False

    def _heartbeat(self, status, error_type=None):
        """Update the durable external health projection; never logs request content."""
        try:
            worker_capabilities = sorted(({
                "worker_id": worker.worker_id,
                "capability": capability,
            } for capability, worker in self.execution_workers.items()),
                key=lambda item: (item["worker_id"], item["capability"]))
            with self.pipeline.ledger.db.transaction():
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""INSERT INTO grace_execution_health
                        (service_id,instance_id,status,worker_capabilities,last_heartbeat_at,last_cycle_at,
                         last_error_type,cycles_completed)
                        VALUES ('grace.execution.v1',%s,%s,%s::jsonb,clock_timestamp(),clock_timestamp(),%s,
                          CASE WHEN %s IN ('healthy','degraded') THEN 1 ELSE 0 END)
                        ON CONFLICT (service_id) DO UPDATE SET instance_id=EXCLUDED.instance_id,
                          status=EXCLUDED.status,worker_capabilities=EXCLUDED.worker_capabilities,
                          last_heartbeat_at=clock_timestamp(),
                          last_cycle_at=clock_timestamp(),last_error_type=EXCLUDED.last_error_type,
                          cycles_completed=grace_execution_health.cycles_completed+
                            CASE WHEN EXCLUDED.status IN ('healthy','degraded') THEN 1 ELSE 0 END""",
                        (self.instance_id, status,
                         json.dumps(worker_capabilities, sort_keys=True, separators=(",", ":")),
                         error_type, status))
        except Exception as exc:
            LOG.warning(json.dumps({"event": "grace_heartbeat_write_failed",
                                    "failure_type": type(exc).__name__}, sort_keys=True))

    def _proposed(self, limit=25, objective_id=None):
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT objective_id,scope_ref FROM grace_objectives
                WHERE status IN ('PROPOSED','WORK_ORDER_CREATED') AND scope_ref=%s
                  AND (%s::text IS NULL OR objective_id=%s)
                ORDER BY created_at,objective_id LIMIT %s""",
                (self.authority_ref, objective_id, objective_id, limit))
            return cur.fetchall()

    def _dispatch_failure_count(self, objective_id):
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT count(*) AS failures FROM grace_objective_events
                WHERE objective_id=%s AND event_type='execution.dispatch_failed'""",
                (objective_id,))
            return int(cur.fetchone()["failures"])

    def _record_dispatch_failure(self, objective_id, error_type, ordinal):
        key = f"grace-dispatch-failure:{objective_id}:{ordinal}"
        with self.pipeline.ledger.db.transaction():
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'execution.dispatch_failed',%s,'service:grace-execution',%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (objective_id, key, json.dumps({"failure_type": error_type,
                     "retry": ordinal, "retry_limit": self.max_dispatch_failures},
                     sort_keys=True, separators=(",", ":"))))

    def dispatch_proposed(self, objective_id=None):
        dispatched = 0
        for row in self._proposed(limit=1 if objective_id else 25,
                                  objective_id=objective_id):
            objective_id = row["objective_id"]
            self._current_objective_id = objective_id
            step = self.pipeline.dispatchable_step(objective_id)
            if not step:
                continue
            objective = self.pipeline.get_objective(objective_id)
            proposal_steps = (objective.get("proposal", {}).get("steps", [])
                              if isinstance(objective, dict) else [])
            proposal_step = next((item for item in proposal_steps if isinstance(item, dict)
                                  and item.get("step_id") == step["step_id"]), None)
            selected_capability = self._proposal_worker_capability(proposal_step)
            if selected_capability is None:
                continue
            if (proposal_step and proposal_step.get("execution_capability") ==
                    "engineering.codex-cli-source-change.v1" and
                    (not callable(self.source_target_validators.get(
                         "engineering.codex-cli-source-change.v1")) or
                     not self.source_target_validators[
                         "engineering.codex-cli-source-change.v1"](proposal_step))):
                # No assignment is created until the configured source repository,
                # immutable commit, and path ceiling all match the Steward plan.
                continue
            failures = self._dispatch_failure_count(objective_id)
            if failures >= self.max_dispatch_failures:
                continue
            base = hashlib.sha256(objective_id.encode("utf-8")).hexdigest()[:40]
            assignment_id = "assignment:grace:" + base
            idempotency_key = f"grace-assignment:{objective_id}"
            if step["step_order"] > 1:
                suffix = hashlib.sha256(step["step_id"].encode("utf-8")).hexdigest()[:16]
                assignment_id += ":step:" + suffix
                idempotency_key += ":step:" + step["step_id"]
            try:
                self.pipeline.authorize_and_dispatch(
                    objective_id, assignment_id, credential=self.dispatch_credential,
                    authority_ref=self.authority_ref,
                    idempotency_key=idempotency_key, step_id=step["step_id"])
                dispatched += 1
            except Exception as exc:
                self._record_dispatch_failure(objective_id, type(exc).__name__, failures + 1)
                LOG.warning(json.dumps({"event": "grace_dispatch_failed",
                    "objective_id": objective_id, "failure_type": type(exc).__name__,
                    "retry": failures + 1}, sort_keys=True))
        return dispatched

    def verify_one(self, assignment_id=None):
        capabilities = list(self.execution_capabilities)
        with self.adapter.ledger.db.cursor() as cur:
            self.adapter.ledger._set_search_path(cur)
            cur.execute("""SELECT a.id AS assignment_id,wa.attempt_id,wa.capability
                ,a.objective_ref
                FROM assignments a JOIN worker_attempts wa ON wa.assignment_id=a.id
                JOIN worker_results wr USING(attempt_id)
                WHERE a.state='awaiting_verification' AND wa.status='succeeded'
                  AND wa.capability=ANY(%s)
                  AND NOT EXISTS (SELECT 1 FROM verification_records prior
                      WHERE prior.attempt_id=wa.attempt_id AND prior.verifier_id=%s)
                  AND (%s::text IS NULL OR a.id=%s)
                ORDER BY a.updated_at,wa.started_at,wa.attempt_id LIMIT 25""",
                (capabilities, self.verifier_id, assignment_id, assignment_id))
            candidates = cur.fetchall()
        for candidate in candidates:
            attempt_id = str(candidate["attempt_id"])
            verifier = self.verifiers.get(candidate["capability"])
            if verifier is None:
                continue
            failure_count = self._verification_failure_count(candidate["objective_ref"], attempt_id)
            if failure_count >= 3:
                continue
            try:
                self.adapter.verify_attempt(candidate["assignment_id"], candidate["attempt_id"],
                    self.verifier_id, self.verifier_credential, verifier,
                    idempotency_key=f"grace-verification:{attempt_id}")
                return True
            except Exception as exc:
                self._record_verification_failure(candidate["objective_ref"], attempt_id,
                                                  type(exc).__name__, failure_count + 1)
                LOG.warning(json.dumps({"event": "grace_verification_failed",
                    "assignment_id": candidate["assignment_id"], "attempt_id": attempt_id,
                    "failure_type": type(exc).__name__, "retry": failure_count + 1}, sort_keys=True))
        if self.revalidate_rejected_one(assignment_id=assignment_id):
            return True
        return False

    def _verification_failure_count(self, objective_id, attempt_id):
        if not objective_id:
            return 0
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT count(*) AS failures FROM grace_objective_events
                WHERE objective_id=%s AND event_type='execution.verification_failed'
                  AND payload->>'attempt_id'=%s""", (objective_id, attempt_id))
            return int(cur.fetchone()["failures"])

    def _record_verification_failure(self, objective_id, attempt_id, error_type, ordinal):
        if not objective_id:
            return
        key = f"grace-verification-failure:{attempt_id}:{ordinal}"
        with self.pipeline.ledger.db.transaction():
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'execution.verification_failed',%s,'service:grace-execution',%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (objective_id, key, json.dumps({"attempt_id": attempt_id,
                     "failure_type": error_type, "retry": ordinal, "retry_limit": 3},
                     sort_keys=True, separators=(",", ":"))))

    def reconcile_completions(self, limit=25, objective_id=None):
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT o.objective_id,s.assignment_id
                FROM grace_objectives o
                JOIN grace_objective_steps s USING (objective_id)
                JOIN assignments a ON a.id=s.assignment_id
                    AND a.objective_ref=o.objective_id
                WHERE o.status='WORK_ORDER_CREATED'
                  AND s.status IN ('assigned','verified')
                  AND a.state='completed'
                  AND EXISTS (SELECT 1 FROM verification_records vr
                      WHERE vr.assignment_id=a.id AND vr.decision='ACCEPTED')
                  AND (%s::text IS NULL OR o.objective_id=%s)
                ORDER BY o.updated_at,s.step_order DESC LIMIT %s""",
                (objective_id, objective_id, limit))
            rows = cur.fetchall()
        completed = 0
        for row in rows:
            try:
                self.pipeline.record_verified_completion(row["objective_id"],
                                                         row["assignment_id"])
                completed += 1
            except Exception as exc:
                LOG.warning(json.dumps({"event": "grace_completion_reconcile_failed",
                    "objective_id": row["objective_id"],
                    "assignment_id": row["assignment_id"],
                    "failure_type": type(exc).__name__}, sort_keys=True))
        return completed

    def publish_conversation_results(self, limit=10):
        """Retry post-verification chat delivery from a durable objective outbox."""
        if self.conversation_result_publisher is None:
            return 0
        published = 0
        for context in self.pipeline.pending_conversation_results(limit=limit):
            failure_stage = "outbox_validation"
            try:
                completion_cycle = context.get("completion_cycle")
                if type(completion_cycle) is not int or completion_cycle < 1:
                    raise ValueError("durable conversation result cycle is invalid")
                failure_stage = "artifact_review"
                review_context = self._with_grace_artifact_review(context)
                failure_stage = "resident_result_review"
                receipt = self.conversation_result_publisher(review_context)
                if (not isinstance(receipt, dict)
                        or receipt.get("status") not in {"published", "already_published"}):
                    continue
                failure_stage = "receipt_validation"
                receipt_cycle = receipt.get("completion_cycle")
                if receipt_cycle is not None and not (
                        (type(receipt_cycle) is int and receipt_cycle == completion_cycle)
                        or (isinstance(receipt_cycle, str)
                            and receipt_cycle == str(completion_cycle))):
                    raise ValueError("conversation result receipt cycle does not match outbox")
                durable_receipt = {key: receipt.get(key) for key in
                    ("request_id", "provider_id", "served_model", "implementation_id")}
                durable_receipt["completion_cycle"] = str(completion_cycle)
                failure_stage = "durable_acknowledgement"
                if receipt.get("review_generation") is not None:
                    durable_receipt.update({key: receipt.get(key) for key in
                        ("review_generation", "review_evidence_revision",
                         "review_evidence_sha256")})
                if receipt.get("review_decision") is not None:
                    durable_receipt["review_decision"] = receipt["review_decision"]
                self.pipeline.record_conversation_result_published(
                    context["objective_id"], durable_receipt)
                published += 1
            except Exception as exc:
                frame = exc.__traceback__
                location = None
                while frame is not None:
                    code = frame.tb_frame.f_code
                    location = f"{code.co_name}:{frame.tb_lineno}"
                    frame = frame.tb_next
                LOG.warning(json.dumps({"event": "grace_conversation_result_return_failed",
                    "objective_id": context.get("objective_id"),
                    "failure_type": type(exc).__name__, "failure_stage": failure_stage,
                    "failure_location": location}, sort_keys=True))
        return published

    def publish_rejected_work_order_reviews(self, limit=10):
        """Review rejected work within retry bounds or persist a Steward-action hold."""
        published = 0
        for context in self.pipeline.pending_rejected_work_order_reviews(limit=limit):
            attempts = context.get("rework_attempt_count", 0)
            if attempts >= self.pipeline.MAX_GOVERNED_REWORK_ATTEMPTS:
                self.pipeline.record_rework_escalation_pending(context, "retry_limit_exhausted")
                continue
            if self.rejected_work_order_publisher is None:
                self.pipeline.record_rework_escalation_pending(
                    context, "review_provider_uncommissioned")
                continue
            try:
                review_context = self._with_grace_artifact_review(context)
                if context.get("origin") is None:
                    review_context["current_authority_evidence"] = (
                        self.pipeline.rework_review_authority_evidence(
                            context, credential=self.dispatch_credential))
                receipt = self.rejected_work_order_publisher(review_context)
                if (not isinstance(receipt, dict) or
                        receipt.get("status") not in {"published", "already_published", "recorded"} or
                        receipt.get("verification_id") !=
                            context["completion"]["verification_id"]):
                    continue
                if context.get("origin") is None:
                    self.pipeline.record_rework_review_recorded(context, receipt["request_id"])
                else:
                    self.pipeline.record_rework_review_published(context["objective_id"],
                        context["completion"]["verification_id"], receipt["request_id"])
                published += 1
            except Exception as exc:
                self.pipeline.record_rework_escalation_pending(
                    context, "review_provider_unavailable")
                LOG.warning(json.dumps({"event": "grace_rejected_result_review_failed",
                    "objective_id": context.get("objective_id"),
                    "assignment_id": context.get("assignment_id"),
                    "verification_id": context.get("completion", {}).get("verification_id"),
                    "failure_type": type(exc).__name__}, sort_keys=True))
        return published

    def reconcile_proposal_lifecycle(self):
        """Recover proposal links and execution evidence through durable existing records."""
        if self.proposal_lifecycle is None:
            return 0
        try:
            return self.proposal_lifecycle.reconcile_links()
        except Exception as exc:
            LOG.warning(json.dumps({"event": "proposal_execution_reconciliation_failed",
                "failure_type": type(exc).__name__}, sort_keys=True))
            return 0

    def _evaluate_exact_external_review(self, consumed, request_id, correlation_id):
        """Finish, revise, or block one exact-subject review; never self-approve work."""
        from ..resident_reasoning import ReasoningStatus
        from .external_reasoning import (MAX_REVIEW_REVISIONS, build_review_subject,
            proposal_review_content)
        subject = consumed.review_subject
        if subject is None:
            raise ValueError("exact_review_subject_missing")
        parent = self.external_reasoning_exchange.review_successor(request_id, correlation_id)
        if parent is not None:
            child = parent["review_subject"]
            self.pipeline.record_external_review_decision(
                consumed.original_request.assignment_id, request_id=request_id,
                correlation_id=correlation_id,
                event_type="resident.reasoning.external_proposal_revised",
                actor_id="office:" + self.resident_reasoner.office_id,
                payload={"subject_id": child["subject_id"], "revision": child["revision"],
                    "subject_sha256": child["sha256"],
                    "response_sha256": parent["response_sha256"],
                    "proposal_sha256": hashlib.sha256(json.dumps(
                        child["proposal"], ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest(),
                    "decision": "revise", "successor_request_id": parent["request_id"],
                    "successor_correlation_id": parent["correlation_id"]})
            return

        if self._reasoning_failure_count(consumed.original_request.assignment_id) >= self.MAX_REASONING_FAILURES:
            return
        result = self.resident_reasoner.propose(
            consumed.original_request.assignment_id, trigger="external_proposal_review",
            token_budget=self.resident_token_budget, external_advisory=consumed.advisory,
            review_subject=subject)
        if result.status is not ReasoningStatus.PROPOSED or result.proposal is None:
            self._record_reasoning_failure(consumed.original_request.assignment_id, result=result)
            return
        response = consumed.advisory
        response_bytes = json.dumps(response, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")
        response_sha256 = hashlib.sha256(response_bytes).hexdigest()
        reviewed_content = subject["proposal"]
        proposed_content = proposal_review_content(result.proposal)
        proposal_sha256 = hashlib.sha256(json.dumps(
            proposed_content, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
        same = proposed_content == reviewed_content
        if same and result.proposal.external_escalation is None:
            provenance = {"request_id": request_id, "correlation_id": correlation_id,
                "response_id": response["response_id"], "response_sha256": response_sha256,
                "provider_id": response["provider_id"], "provider_model": response["provider_model"],
                "reasoning_request_id": result.request_id}
            evidence = {"subject_id": subject["subject_id"], "revision": subject["revision"],
                "subject_sha256": subject["sha256"], "response_sha256": response_sha256,
                "proposal_sha256": proposal_sha256, "decision": "finish"}
            self.pipeline.record_proposal(consumed.original_request.assignment_id,
                result.proposal, actor_id="office:" + self.resident_reasoner.office_id,
                external_exchange=provenance, review_evidence=evidence)
            return

        objective_id = consumed.original_request.assignment_id
        if subject["revision"] >= MAX_REVIEW_REVISIONS:
            self.pipeline.record_external_review_decision(objective_id,
                request_id=request_id, correlation_id=correlation_id,
                event_type="resident.reasoning.external_proposal_review_blocked",
                actor_id="office:" + self.resident_reasoner.office_id,
                payload={"subject_id": subject["subject_id"], "revision": subject["revision"],
                    "subject_sha256": subject["sha256"], "response_sha256": response_sha256,
                    "proposal_sha256": proposal_sha256, "decision": "blocked",
                    "reason_code": "review_revision_limit"})
            return

        intent = result.proposal.external_escalation
        target = intent.target_provider_id if intent is not None else response["provider_id"]
        reason = intent.reason if intent is not None else "low_confidence"
        if target not in self.resident_reasoner.external_reasoning_targets:
            self.pipeline.record_external_review_decision(objective_id,
                request_id=request_id, correlation_id=correlation_id,
                event_type="resident.reasoning.external_proposal_review_blocked",
                actor_id="office:" + self.resident_reasoner.office_id,
                payload={"subject_id": subject["subject_id"], "revision": subject["revision"],
                    "subject_sha256": subject["sha256"], "response_sha256": response_sha256,
                    "proposal_sha256": proposal_sha256, "decision": "blocked",
                    "reason_code": "review_target_not_configured"})
            return
        next_subject = build_review_subject(subject["subject_id"],
                                            subject["revision"] + 1, result.proposal)
        source_request = result.reasoning_request
        if source_request is None:
            raise ValueError("review_successor_context_missing")
        escalation_id = str(uuid5(NAMESPACE_URL,
            "rv-external-review:" + source_request.request_id + ":" + target + ":" +
            next_subject["sha256"]))
        from ..reasoning_escalation import EscalationRequest
        envelope = EscalationRequest.create(source_request, reason=reason,
            target_provider_id=target, max_tokens=min(512, self.resident_token_budget),
            timeout_seconds=30, escalation_id=escalation_id)
        received = next((event for event in self.pipeline.objective_events(objective_id)
            if event.get("event_type") == "objective.received"), None)
        origin = (received or {}).get("payload", {}).get("origin")
        if not isinstance(origin, dict):
            raise ValueError("external_review_conversation_origin_missing")
        references = tuple(dict.fromkeys(ref for item in source_request.verified_knowledge
            for ref in item.get("source_references", ())))[:32]
        receipt = self.request_external_reasoning(envelope, source_request,
            conversation_id=origin["conversation_id"], message_sequence=origin["source_sequence"],
            idempotency_key=("grace-review:" + request_id + ":" + correlation_id + ":" +
                response_sha256 + ":" + next_subject["sha256"]),
            deadline_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            source_references=references, review_subject=next_subject,
            review_parent={"request_id": request_id, "correlation_id": correlation_id,
                           "response_sha256": response_sha256})
        self.pipeline.record_external_review_decision(objective_id,
            request_id=request_id, correlation_id=correlation_id,
            event_type="resident.reasoning.external_proposal_revised",
            actor_id="office:" + self.resident_reasoner.office_id,
            payload={"subject_id": next_subject["subject_id"], "revision": next_subject["revision"],
                "subject_sha256": next_subject["sha256"], "response_sha256": response_sha256,
                "proposal_sha256": proposal_sha256, "decision": "revise",
                "successor_request_id": receipt.request_id,
                "successor_correlation_id": receipt.correlation_id})

    def consume_external_reasoning(self, *, limit=5):
        """Resume persisted advisory replies through Grace's existing reasoner.

        Proposal persistence and its correlated objective event are atomic; that
        event fences recovery after a crash before exchange acknowledgement.
        External advice remains an unapproved proposal and cannot dispatch work.
        """
        exchange = self.external_reasoning_exchange
        if exchange is None or self.resident_reasoner is None:
            return 0
        principal = self.external_reasoning_principal
        if not isinstance(principal, str) or not principal:
            return 0
        processed = 0
        for item in exchange.pending_responses(principal, limit=limit):
            request_id, correlation_id = item["request_id"], item["correlation_id"]
            try:
                consumed = exchange.consume(request_id, correlation_id,
                    principal_id=principal, authorize=self.external_reasoning_authorize)
                objective_id = consumed.original_request.assignment_id
                request_type = (consumed.original_request.trigger
                    if consumed.original_request.trigger in {
                        "cme_diagnostic_recovery", "performance_evaluation"} else None)
                if request_type in {"cme_diagnostic_recovery", "performance_evaluation"}:
                    try:
                        if request_type == "cme_diagnostic_recovery":
                            self._consume_cme_diagnostic_response(consumed, item)
                        else:
                            self._consume_performance_evaluation(consumed, item)
                    except Exception as supervisory_exc:
                        assignment_id = consumed.original_request.assignment.get("assignment_id")
                        if isinstance(assignment_id, str) and assignment_id:
                            self.pipeline.record_supervisory_event(objective_id, assignment_id,
                                event_type=("resident.reasoning.cme_recovery_blocked"
                                    if request_type == "cme_diagnostic_recovery" else
                                    "resident.performance.evaluation_blocked"),
                                request_id=request_id, correlation_id=correlation_id,
                                idempotency_key=f"supervisory-blocked:{request_id}",
                                payload={"reason_code": type(supervisory_exc).__name__})
                    exchange.acknowledge_consumed(request_id, correlation_id,
                        principal_id=principal, consumption_key=consumed.consumption_key,
                        consumption_token=consumed.consumption_token, fence=consumed.fence,
                        result_reference=f"objective:{objective_id}:external-reasoning:{request_id}",
                        authorize=self.external_reasoning_authorize)
                    processed += 1
                    continue
                durable_event = next((event for event in
                    self.pipeline.objective_events(objective_id)
                    if event.get("event_type") in {
                        "resident.reasoning.external_advisory_evaluated",
                        "resident.reasoning.external_proposal_reviewed",
                        "resident.reasoning.external_proposal_revised",
                        "resident.reasoning.external_proposal_review_blocked"} and
                        (event.get("payload") or {}).get("request_id") == request_id and
                        (event.get("payload") or {}).get("correlation_id") == correlation_id), None)
                if durable_event is None:
                    if consumed.review_subject is not None:
                        self._evaluate_exact_external_review(consumed, request_id, correlation_id)
                    else:
                        if self._reasoning_failure_count(objective_id) >= self.MAX_REASONING_FAILURES:
                            continue
                        from ..resident_reasoning import ReasoningStatus
                        result = self.resident_reasoner.propose(objective_id,
                            trigger="external_advisory_resume", token_budget=self.resident_token_budget,
                            external_advisory=consumed.advisory)
                        if result.status is not ReasoningStatus.PROPOSED or result.proposal is None:
                            self._record_reasoning_failure(objective_id, result=result)
                            continue
                        response = consumed.advisory
                        if not isinstance(response, dict):
                            raise ValueError("external advisory response is invalid")
                        provenance = {"request_id": request_id,
                            "correlation_id": correlation_id,
                            "response_id": response.get("response_id"),
                            "response_sha256": hashlib.sha256(json.dumps(
                                consumed.advisory, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest(),
                            "provider_id": response.get("provider_id"),
                            "provider_model": response.get("provider_model"),
                            "reasoning_request_id": result.request_id}
                        self.pipeline.record_proposal(objective_id, result.proposal,
                            actor_id="office:" + self.resident_reasoner.office_id,
                            external_exchange=provenance)
                exchange.acknowledge_consumed(request_id, correlation_id,
                    principal_id=principal, consumption_key=consumed.consumption_key,
                    consumption_token=consumed.consumption_token, fence=consumed.fence,
                    result_reference=f"objective:{objective_id}:external-reasoning:{request_id}",
                    authorize=self.external_reasoning_authorize)
                processed += 1
            except Exception as exc:
                LOG.warning(json.dumps({"event": "grace_external_reasoning_consume_failed",
                    "request_id": request_id, "correlation_id": correlation_id,
                    "failure_type": type(exc).__name__}, sort_keys=True))
        return processed

    def queue_cme_diagnostic_escalation(self):
        """Admit one idempotent Luna diagnostic request for a durable CME stall."""
        objective_id = "objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2"
        assignment_id = "assignment:grace:de19cd78b86f1889d32cdf02c6d3fe51d4658834:step:ad328846aa18b32a"
        exchange = self.external_reasoning_exchange
        reasoner = self.resident_reasoner
        if (exchange is None or reasoner is None or "gpt-6-luna" not in
                reasoner.external_reasoning_targets or exchange.has_active_for_objective(objective_id)):
            return None
        objective = self.pipeline.get_objective(objective_id)
        context = self.pipeline.supervisory_rejected_assignment_context(
            objective_id, assignment_id, "5e6e295b-d45a-46e3-a186-96d14877b33c")
        if (not objective or objective.get("status") != "WORK_ORDER_CREATED" or
                not context or context["step_id"] != "s2"):
            return None
        reference = self.pipeline.objective_proposal_reference(objective_id)
        if (not isinstance(reference, dict) or reference.get("revision") != 2 or
                not isinstance(reference.get("proposal_id"), str)):
            return None
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT event_id::text AS event_id,details FROM cme_monitor_events
                WHERE assignment_id=%s AND event_type='assignment_stalled'
                  AND details->>'state'='rework_required'
                ORDER BY recorded_at DESC,event_id DESC LIMIT 1""", (assignment_id,))
            stall = cur.fetchone()
            cur.execute("""SELECT auth.authorization_id,auth.status,auth.expires_at,
                    auth.max_recovery_attempts,auth.max_luna_requests,
                    (SELECT count(*) FROM grace_experiment_authorization_events e
                      WHERE e.authorization_id=auth.authorization_id
                        AND e.event_type='recovery_claimed') AS recoveries,
                    (SELECT count(*) FROM grace_experiment_authorization_events e
                      WHERE e.authorization_id=auth.authorization_id
                        AND e.event_type='luna_reserved') AS luna_requests
                FROM grace_experiment_authorizations auth
                WHERE auth.objective_id=%s AND auth.objective_revision=2
                  AND auth.status='active' AND auth.activated_at<=clock_timestamp()
                  AND auth.expires_at>clock_timestamp()
                ORDER BY auth.activated_at DESC LIMIT 1""", (objective_id,))
            grant = cur.fetchone()
        if (not stall or not grant or int(grant["recoveries"]) >= int(grant["max_recovery_attempts"])
                or int(grant["luna_requests"]) >= int(grant["max_luna_requests"])):
            return None
        details = stall["details"] if isinstance(stall["details"], dict) else {}
        if details.get("state") != "rework_required":
            return None
        event_id = stall["event_id"]
        if exchange.request_for_idempotency("cme-recovery:" + event_id):
            return None
        authority_evidence = self.pipeline.rework_review_authority_evidence(
            context, credential=self.dispatch_credential)
        objective_events = self.pipeline.objective_events(objective_id)
        recovery_history = [{"event_id": str(event["event_id"]),
            "event_type": event["event_type"],
            "decision": event["payload"].get("decision"),
            "reason_code": event["payload"].get("reason_code"),
            "review_generation": event["payload"].get("review_generation")}
            for event in objective_events if event["event_type"] in {
                "engineering.rework_decided", "engineering.rework_review_recorded",
                "engineering.rework_escalation_pending"}][-8:]
        office = reasoner.registry.authorize_office_state(reasoner._credential, reasoner.office_id)
        binding_revision = office.get("binding_revision")
        implementation_revision = office.get("implementation_revision")
        if (type(binding_revision) is not int or
                not isinstance(implementation_revision, str) or not implementation_revision):
            return None
        from ..resident_reasoning import ReasoningRequest
        from ..reasoning_escalation import EscalationRequest
        original_id = str(uuid5(NAMESPACE_URL, "rv-cme-recovery-original:" + event_id))
        source = {"objective_id": objective_id, "objective_revision": objective["revision"],
            "proposal_id": reference["proposal_id"], "proposal_revision": 2,
            "assignment_id": assignment_id, "step_id": context["step_id"],
            "verification_id": context["completion"]["verification_id"],
            "cme_event_id": event_id, "cme_state": details["state"],
            "cme_progress_seq": details.get("progress_seq"),
            "criteria": context["step_acceptance_criteria"],
            "verifier_decision": "REJECTED",
            "verifier_summary": str(context["completion"].get("summary", ""))[:600],
            "verifier_findings": context["completion"].get("criteria"),
            "verifier_id": context["completion"].get("verifier_id"),
            "verifier_revision": context["completion"].get("verifier_revision"),
            "verifier_evidence_references": context["completion"].get("evidence_references", [])[:8],
            "assignment_authority": authority_evidence,
            "recovery_history": recovery_history,
            "approved_scope_unchanged": True}
        request = ReasoningRequest(request_id=original_id, office_id=reasoner.office_id,
            assignment_id=objective_id, assignment_revision=str(objective["revision"]),
            binding_revision=binding_revision, implementation_revision=implementation_revision,
            trigger="cme_diagnostic_recovery", token_budget=192, assignment=source,
            verified_knowledge=(), prior_plan=None,
            external_reasoning_targets=reasoner.external_reasoning_targets,
            correlation_id=original_id)
        escalation_id = str(uuid5(NAMESPACE_URL, "rv-cme-recovery-escalation:" + event_id))
        envelope = EscalationRequest.create(request, reason="capability_gap",
            target_provider_id="gpt-6-luna", max_tokens=192, timeout_seconds=30,
            escalation_id=escalation_id)
        return self.request_external_reasoning(envelope, request,
            idempotency_key="cme-recovery:" + event_id,
            deadline_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            proposal_id=reference["proposal_id"], proposal_revision=2,
            source_references=(event_id, assignment_id, context["completion"]["verification_id"]),
            source_kind="cme_diagnostic_recovery", request_type="cme_diagnostic_recovery")

    def queue_performance_evaluation(self):
        """Request one evaluation only after durable execution or verification evidence."""
        objective_id = "objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2"
        exchange = self.external_reasoning_exchange
        reasoner = self.resident_reasoner
        if (exchange is None or reasoner is None or "gpt-6-luna" not in
                reasoner.external_reasoning_targets or exchange.has_active_for_objective(objective_id)):
            return None
        objective = self.pipeline.get_objective(objective_id)
        reference = self.pipeline.objective_proposal_reference(objective_id)
        if (not objective or objective.get("status") not in {"WORK_ORDER_CREATED", "COMPLETED"} or
                not isinstance(reference, dict) or reference.get("revision") != 2):
            return None
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT auth.max_luna_requests,
                    (SELECT count(*) FROM grace_experiment_authorization_events e
                      WHERE e.authorization_id=auth.authorization_id
                        AND e.event_type='luna_reserved') AS used
                FROM grace_experiment_authorizations auth
                WHERE auth.objective_id=%s AND auth.objective_revision=2
                  AND auth.status='active' AND auth.activated_at<=clock_timestamp()
                  AND auth.expires_at>clock_timestamp()
                ORDER BY auth.activated_at DESC LIMIT 1""", (objective_id,))
            budget_grant = cur.fetchone()
        if not budget_grant or int(budget_grant["used"]) >= int(budget_grant["max_luna_requests"]):
            return None
        events = self.pipeline.objective_events(objective_id)
        existing = any(event["event_type"] == "resident.performance.evaluation_recorded"
                       for event in events)
        evidence = [event for event in events if
            event["event_type"] == "objective.completed" or
            (event["event_type"] == "execution.step_verified" and
             (event["payload"] or {}).get("step_id") == "s2") or
            event["event_type"] == "resident.reasoning.cme_recovery_evaluated"]
        if existing or not evidence:
            return None
        latest = evidence[-1]
        evaluation_key = "performance-evaluation:" + str(latest["event_id"])
        if exchange.request_for_idempotency(evaluation_key):
            return None
        office = reasoner.registry.authorize_office_state(reasoner._credential, reasoner.office_id)
        from ..resident_reasoning import ReasoningRequest
        from ..reasoning_escalation import EscalationRequest
        assignment = {"objective_id": objective_id, "objective_revision": objective["revision"],
            "assignment_id": objective.get("assignment_id"),
            "proposal_id": reference["proposal_id"], "proposal_revision": 2,
            "proposal": {"summary": str((objective.get("proposal") or {}).get("summary", ""))[:800],
                "steps": [{key: step.get(key) for key in
                    ("step_id", "objective", "acceptance_criteria", "depends_on")
                    if key in step} for step in
                    (objective.get("proposal") or {}).get("steps", [])[:8]
                    if isinstance(step, dict)]},
            "evaluation_trigger_event_id": str(latest["event_id"]),
            "evidence": [{"event_id": str(event["event_id"]),
                "event_type": event["event_type"],
                "payload": {key: event["payload"].get(key) for key in
                    ("step_id", "decision", "verification_id", "assignment_id",
                     "recovery_action", "assessment", "rationale", "cme_event_id")
                    if key in event["payload"]}} for event in evidence[-8:]],
            "reasoning_history": [{"event_id": str(event["event_id"]),
                "event_type": event["event_type"],
                "failure_type": event["payload"].get("failure_type"),
                "detail_code": event["payload"].get("detail_code"),
                "runtime_revision": event["payload"].get("runtime_revision")}
                for event in events if event["event_type"] in {
                    "execution.reasoning_attempted", "execution.reasoning_failed"}][-8:],
            "reasoning_attempt_count": sum(event["event_type"] ==
                "execution.reasoning_attempted" for event in events),
            "reasoning_failure_count": sum(event["event_type"] ==
                "execution.reasoning_failed" for event in events),
            "exchange_history": [{"event_type": event["event_type"],
                "request_id": event["payload"].get("request_id"),
                "correlation_id": event["payload"].get("correlation_id")}
                for event in events
                if event["event_type"].startswith("external_reasoning.")][-8:]}
        request_id = str(uuid5(NAMESPACE_URL, "rv-performance-evaluation:" + str(latest["event_id"])))
        request = ReasoningRequest(request_id=request_id, office_id=reasoner.office_id,
            assignment_id=objective_id, assignment_revision=str(objective["revision"]),
            binding_revision=office["binding_revision"],
            implementation_revision=office["implementation_revision"],
            trigger="performance_evaluation", token_budget=384, assignment=assignment,
            verified_knowledge=(), prior_plan=None,
            external_reasoning_targets=reasoner.external_reasoning_targets,
            correlation_id=request_id)
        escalation = EscalationRequest.create(request, reason="low_confidence",
            target_provider_id="gpt-6-luna", max_tokens=384, timeout_seconds=30,
            escalation_id=request_id)
        return self.request_external_reasoning(escalation, request,
            idempotency_key=evaluation_key,
            deadline_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            proposal_id=reference["proposal_id"], proposal_revision=2,
            source_references=(str(latest["event_id"]),),
            source_kind="performance_evaluation", request_type="performance_evaluation")

    @staticmethod
    def _json_advisory(consumed, schema, allowed_fields):
        advisory = consumed.advisory.get("advisory") if isinstance(consumed.advisory, Mapping) else None
        if not isinstance(advisory, str) or len(advisory) > 8000:
            raise ValueError("supervisory_advisory_invalid")
        value = json.loads(advisory)
        if not isinstance(value, dict) or set(value) != allowed_fields or value.get("schema") != schema:
            raise ValueError("supervisory_advisory_schema_invalid")
        return value

    def _consume_cme_diagnostic_response(self, consumed, item):
        fields = {"schema", "assessment", "recovery_action", "rationale",
                  "correction_instruction", "criteria_to_address"}
        value = self._json_advisory(consumed, "rv.grace.cme-recovery-advice.v1", fields)
        objective_id = consumed.original_request.assignment_id
        original = consumed.original_request
        if (original.trigger != "cme_diagnostic_recovery" or
                value["recovery_action"] not in {"REWORK_PROPOSED", "STEWARD_AUTHORIZATION_REQUIRED"} or
                not isinstance(value["assessment"], str) or len(value["assessment"]) > 500 or
                not isinstance(value["rationale"], str) or len(value["rationale"]) > 1000 or
                (value["correction_instruction"] is not None and
                 (not isinstance(value["correction_instruction"], str) or
                  len(value["correction_instruction"]) > 512)) or
                not isinstance(value["criteria_to_address"], list)):
            raise ValueError("cme_advisory_fields_invalid")
        exchange_meta = self.pipeline.exchange_response_metadata(
            consumed.request_id, consumed.correlation_id)
        if (not exchange_meta or exchange_meta["delivery_state"] != "response_received" or
                exchange_meta["consumption_owner"] != "resident:grace" or
                exchange_meta["request_payload"].get("request_type") != "cme_diagnostic_recovery"):
            raise ValueError("cme_exchange_response_correlation_invalid")
        context = self.pipeline.supervisory_rejected_assignment_context(
            objective_id, original.assignment.get("assignment_id"),
            original.assignment.get("verification_id"))
        if not context:
            self.pipeline.record_supervisory_event(objective_id,
                original.assignment.get("assignment_id"),
                event_type="resident.reasoning.cme_recovery_blocked",
                request_id=consumed.request_id, correlation_id=consumed.correlation_id,
                idempotency_key=f"cme-recovery-blocked:{consumed.request_id}",
                payload={"reason_code": "authoritative_assignment_context_changed"})
            return
        criteria = context["step_acceptance_criteria"]
        criteria_to_address = value["criteria_to_address"]
        if (len(criteria_to_address) != len(set(criteria_to_address)) or
                any(item not in criteria for item in criteria_to_address)):
            raise ValueError("cme_advisory_criteria_out_of_scope")
        response_sha = exchange_meta["response_sha256"]
        cme_event_id = original.assignment.get("cme_event_id")
        if (not isinstance(cme_event_id, str) or
                not re.fullmatch(r"[0-9a-f-]{36}", cme_event_id) or
                not isinstance(response_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", response_sha)):
            raise ValueError("cme_advisory_lineage_invalid")
        metadata = {"request_id": consumed.request_id,
            "correlation_id": consumed.correlation_id,
            "response_sha256": response_sha, "cme_event_id": cme_event_id}
        if value["recovery_action"] == "REWORK_PROPOSED":
            decision = {"decision": "REWORK_PROPOSED", "rationale": value["rationale"],
                "correction_instruction": value["correction_instruction"],
                "criteria_to_address": criteria_to_address}
            if not criteria_to_address or not value["correction_instruction"]:
                raise ValueError("cme_advisory_rework_incomplete")
        else:
            decision = {"decision": "STEWARD_AUTHORIZATION_REQUIRED",
                "rationale": value["rationale"], "correction_instruction": None,
                "criteria_to_address": []}
        context["external_reasoning"] = metadata
        self.pipeline.record_rework_decision(context, decision,
            credential=self.dispatch_credential)
        self.pipeline.record_supervisory_event(objective_id, context["assignment_id"],
            event_type="resident.reasoning.cme_recovery_evaluated",
            request_id=consumed.request_id, correlation_id=consumed.correlation_id,
            idempotency_key=f"cme-recovery-evaluated:{consumed.request_id}",
            payload={"cme_event_id": cme_event_id,
                "recovery_action": decision["decision"],
                "assessment": value["assessment"],
                "response_sha256": response_sha})

    def _consume_performance_evaluation(self, consumed, item):
        fields = {"schema", "grade", "rubric", "what_went_well", "gaps",
                  "actionable_feedback", "authority_promotion_recommendation"}
        value = self._json_advisory(consumed, "rv.grace.performance-evaluation.v1", fields)
        rubric = value["rubric"]
        if (type(value["grade"]) is not int or not 1 <= value["grade"] <= 5 or
                not isinstance(rubric, dict) or set(rubric) !=
                    {"reasoning", "authorization", "execution", "verification"} or
                any(type(score) is not int or not 1 <= score <= 5 for score in rubric.values()) or
                value["authority_promotion_recommendation"] != "Steward_decision_required" or
                any(not isinstance(value[key], list) or len(value[key]) > 8 or
                    any(not isinstance(entry, str) or not entry or len(entry) > 400
                        for entry in value[key]) for key in
                    ("what_went_well", "gaps", "actionable_feedback"))):
            raise ValueError("performance_evaluation_fields_invalid")
        objective_id = consumed.original_request.assignment_id
        assignment_id = consumed.original_request.assignment.get("assignment_id")
        exchange_meta = self.pipeline.exchange_response_metadata(
            consumed.request_id, consumed.correlation_id)
        if (not exchange_meta or exchange_meta["delivery_state"] != "response_received" or
                exchange_meta["consumption_owner"] != "resident:grace" or
                exchange_meta["request_payload"].get("request_type") != "performance_evaluation"):
            raise ValueError("performance_exchange_response_correlation_invalid")
        payload = {"grade": value["grade"], "rubric": rubric,
            "what_went_well": value["what_went_well"], "gaps": value["gaps"],
            "actionable_feedback": value["actionable_feedback"],
            "authority_promotion_recommendation": "Steward_decision_required",
            "response_sha256": exchange_meta["response_sha256"]}
        self.pipeline.record_supervisory_event(objective_id, assignment_id,
            event_type="resident.performance.evaluation_recorded",
            request_id=consumed.request_id, correlation_id=consumed.correlation_id,
            idempotency_key=f"performance-evaluated:{consumed.request_id}", payload=payload)
        self.pipeline.record_supervisory_event(objective_id, assignment_id,
            event_type="resident.performance.feedback_consumed",
            request_id=consumed.request_id, correlation_id=consumed.correlation_id,
            idempotency_key=f"performance-feedback-consumed:{consumed.request_id}", payload=payload)

    def request_external_reasoning(self, envelope, original_request, *, conversation_id=None,
            message_sequence=None, idempotency_key, deadline_at, classification="institutional",
            proposal_id=None, proposal_revision=None, source_references=(),
            review_subject=None, review_parent=None, source_kind="conversation",
            request_type="objective_reasoning"):
        """Persist an authorized external advisory request without waiting for a provider."""
        if self.external_reasoning_exchange is None:
            raise RuntimeError("external_reasoning_exchange_unavailable")
        principal = self.external_reasoning_principal
        if (not isinstance(principal, str) or
                getattr(original_request, "office_id", None) !=
                getattr(self.resident_reasoner, "office_id", None)):
            raise PermissionError("Grace exchange principal does not match the original request")
        return self.external_reasoning_exchange.submit(envelope, original_request,
            principal_id=principal, authorize=self.external_reasoning_authorize,
            originating_resident_id=principal,
            objective_id=original_request.assignment_id,
            conversation_id=conversation_id, message_sequence=message_sequence,
            proposal_id=proposal_id, proposal_revision=proposal_revision,
            idempotency_key=idempotency_key, classification=classification,
            deadline_at=deadline_at, source_references=source_references,
            review_subject=review_subject, review_parent=review_parent,
            source_kind=source_kind, request_type=request_type)

    def run_once(self):
        """Advance ready durable work before a possibly slow reasoning request."""
        try:
            self._current_objective_id = None
            self._current_request_id = None
            self._current_stage = "proposal_dispatch"
            # Existing authorized work is latency-sensitive. A provider call can
            # take tens of seconds; do not put it ahead of work already admitted
            # under Steward scope or its verification/result-return path.
            dispatched = self.dispatch_proposed()
            self._current_stage = "worker_execution"
            worker_result = self._run_workers()
            self._current_stage = "independent_verification"
            verified = self.verify_one()
            self._current_stage = "completion_reconciliation"
            completed = self.reconcile_completions()
            self._current_stage = "conversation_receipt"
            returned = self.publish_conversation_results()
            self._current_stage = "proposal_lifecycle"
            proposal_updates = self.reconcile_proposal_lifecycle()
            self._current_stage = "rejected_work_order_review"
            rejected_reviewed = self.publish_rejected_work_order_reviews()
            self._current_stage = "external_reasoning"
            external_reasoned = self.consume_external_reasoning()
            self._current_stage = "cme_reasoning_admission"
            cme_request = self.queue_cme_diagnostic_escalation()
            if cme_request is None:
                self._current_stage = "performance_evaluation_admission"
                performance_request = self.queue_performance_evaluation()
            else:
                performance_request = None
            self._current_stage = "resident_reasoning"
            reasoned = self.reason_one_grounded_objective()
            direct_result = None
            if self.direct_external_reasoning_provider is not None:
                self._current_stage = "direct_external_reasoning"
                direct_result = self.direct_external_reasoning_provider.process_one(
                    self.external_reasoning_exchange)
                if isinstance(direct_result, Mapping) and direct_result.get("status") == "RESPONSE_SUBMITTED":
                    external_reasoned += self.consume_external_reasoning(limit=1)
            self._current_stage = "doorbell"
            doorbell = self._run_doorbell_worker()
            worker_failures = (worker_result.get("status") == "FAILED" or
                (isinstance(worker_result.get("capabilities"), dict) and any(
                    item.get("status") == "FAILED" for item in worker_result["capabilities"].values())))
            self._heartbeat("degraded" if worker_failures else "healthy",
                             "WorkerCycleFailure" if worker_failures else None)
            return {"external_reasoned": external_reasoned, "reasoned": reasoned,
                    "rejected_reviewed": rejected_reviewed,
                    "dispatched": dispatched, "worker": worker_result, "verified": verified,
                    "completed": completed, "returned": returned,
                    "proposal_updates": proposal_updates, "doorbell": doorbell,
                    "direct_external_reasoning": direct_result,
                    "cme_reasoning_request": getattr(cme_request, "request_id", None),
                    "performance_evaluation_request": getattr(performance_request, "request_id", None)}
        except Exception as exc:
            self._heartbeat("degraded", type(exc).__name__)
            raise

    def _run_doorbell_worker(self):
        """Poll the injected local wake adapter without coupling its failure to Grace."""
        if self.doorbell_worker is None:
            return {"status": "NOT_CONFIGURED"}
        try:
            result = self.doorbell_worker.run_once()
            status = getattr(result, "status", None)
            if status is None and isinstance(result, Mapping):
                status = result.get("status")
            return {"status": status if isinstance(status, str) else "POLL_COMPLETED"}
        except Exception as exc:
            LOG.warning(json.dumps({"event": "grace_doorbell_worker_failed",
                "failure_type": type(exc).__name__}, sort_keys=True))
            return {"status": "FAILED", "failure_type": type(exc).__name__}

    def _run_workers(self, assignment_id=None):
        """Poll each capability independently; a failed worker cannot starve its peer."""
        def poll(item):
            capability, worker = item
            try:
                return capability, worker.run_once(assignment_id=assignment_id)
            except Exception as exc:
                LOG.warning(json.dumps({"event": "grace_capability_worker_failed",
                    "capability": capability, "failure_type": type(exc).__name__},
                    sort_keys=True))
                return capability, {"status": "FAILED", "failure_type": type(exc).__name__}
        items = tuple(self.execution_workers.items())
        if len(items) == 1:
            return poll(items[0])[1]
        with ThreadPoolExecutor(max_workers=len(items),
                                thread_name_prefix="grace-capability") as pool:
            results = dict(pool.map(poll, items))
        failed = any(result.get("status") == "FAILED" for result in results.values())
        return {"status": "FAILED" if failed else "POLLED", "capabilities": results}

    def execute_supervised_objective(self, objective_id):
        """Execute only one already proposed objective from an operator TTY run."""
        if (not isinstance(objective_id, str) or not re.fullmatch(
                r"objective:[A-Za-z0-9._:-]{1,120}", objective_id)):
            raise ValueError("a bounded objective identity is required")
        try:
            objective = self.pipeline.get_objective(objective_id)
            if (objective is None or objective["scope_ref"] != self.authority_ref or
                    objective["status"] not in {"PROPOSED", "WORK_ORDER_CREATED"}):
                return {"status": "WAITING_FOR_PROPOSAL", "objective_id": objective_id}
            assignment_id = "assignment:grace:" + hashlib.sha256(
                objective_id.encode("utf-8")).hexdigest()[:40]
            if objective["status"] == "PROPOSED":
                self.dispatch_proposed(objective_id)
                objective = self.pipeline.get_objective(objective_id)
            if (objective is None or objective.get("assignment_id") != assignment_id):
                return {"status": "DISPATCH_NOT_AUTHORIZED", "objective_id": objective_id}
            assignment = self.pipeline.ledger.get(assignment_id)
            if not assignment:
                return {"status": "NOT_READY", "objective_id": objective_id,
                        "assignment_id": assignment_id}
            worker_capability = getattr(self, "execution_capability", CAPABILITY)
            objective_proposal = objective.get("proposal") or {}
            proposal_step = next((item for item in objective_proposal.get("steps", [])
                                  if item.get("step_id") == assignment.get("workflow_step")), None)
            if proposal_step:
                worker_capability = self._proposal_worker_capability(proposal_step)
            workers = getattr(self, "execution_workers", {worker_capability: self.worker})
            selected_worker = workers.get(worker_capability)
            if selected_worker is None:
                return {"status": "CAPABILITY_UNAVAILABLE", "objective_id": objective_id,
                        "assignment_id": assignment_id, "capability": worker_capability}
            worker_result = {"status": "ALREADY_COMPLETED" if assignment and
                             assignment["state"] == "completed" else "NOT_READY"}
            if assignment and assignment["state"] in {"ready", "queued"}:
                worker_result = selected_worker.run_once(assignment_id=assignment_id)
            verified = self.verify_one(assignment_id)
            completed = self.reconcile_completions(objective_id=objective_id)
            self._heartbeat("healthy")
            return {"status": "COMPLETED" if completed else worker_result.get("status", "PENDING"),
                    "objective_id": objective_id, "assignment_id": assignment_id,
                    "worker": worker_result, "verified": verified, "completed": completed}
        except Exception as exc:
            self._heartbeat("degraded", type(exc).__name__)
            raise

    def run_forever(self, *, shutdown_requested, poll_seconds=1.0, sleep=time.sleep):
        if not callable(shutdown_requested) or not 0.1 <= poll_seconds <= 30:
            raise ValueError("explicit shutdown callback and bounded poll interval required")
        self._heartbeat("starting")
        while not shutdown_requested():
            try:
                result = self.run_once()
                workers_idle = (result["worker"].get("status") == "IDLE" or
                    (result["worker"].get("status") == "POLLED" and
                     all(item.get("status") == "IDLE" for item in
                         result["worker"].get("capabilities", {}).values())))
                worker_failed = (result["worker"].get("status") == "FAILED" or
                    (isinstance(result["worker"].get("capabilities"), dict) and any(
                        item.get("status") == "FAILED" for item in
                        result["worker"]["capabilities"].values())))
                if (not result["reasoned"] and not result["dispatched"] and
                        (workers_idle or worker_failed)
                        and not result["verified"] and not result["completed"]
                        and not result["returned"]):
                    sleep(poll_seconds)
            except Exception as exc:
                LOG.error(json.dumps({"event": "grace_execution_cycle_failed",
                    "failure_type": type(exc).__name__,
                    "objective_id": getattr(self, "_current_objective_id", None),
                    "request_id": getattr(self, "_current_request_id", None),
                    "failure_stage": getattr(self, "_current_stage", "cycle")}, sort_keys=True))
                sleep(poll_seconds)
        self._heartbeat("stopping")


__all__ = ["GraceExecutionService", "TaskRelevantRepositoryKnowledgeProvider",
           "BoundedLocalCodingWorker"]
