# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/service.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.42
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
    PERSISTED_PROPOSAL_BLOCK_CODES = frozenset({"PROPOSAL_CRITERIA_BINDING_REJECTED"})

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
            if (type(candidate_revision) is int and
                    self._proposal_rejection_blocked(candidate_id, candidate_revision)):
                continue
            if self._reasoning_failure_count(candidate_id) >= self.MAX_REASONING_FAILURES:
                continue
            if (self.external_reasoning_exchange is not None and
                    (self.external_reasoning_exchange.has_active_for_objective(candidate_id) or
                     self.external_reasoning_exchange.has_terminal_review_for_objective(candidate_id))):
                continue
            candidate = row
            break
        if candidate is None:
            return False
        objective_id = candidate["objective_id"]
        self._current_objective_id = objective_id
        try:
            self._record_reasoning_attempt(objective_id)
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
                    return True
                proposal_persist_started = time.monotonic()
                try:
                    self.pipeline.record_proposal(
                        objective_id, result.proposal,
                        actor_id="office:" + self.resident_reasoner.office_id)
                except Exception as exc:
                    if self._reasoning_failure_detail_code(exc) == "PROPOSAL_CRITERIA_BINDING_REJECTED":
                        request = result.reasoning_request
                        assignment = getattr(request, "assignment", None)
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
                return True
            self._record_reasoning_failure(objective_id, result=result)
        except Exception as exc:
            detail_code = self._reasoning_failure_detail_code(exc)
            blocked_revision = (candidate_revision
                if detail_code in self.PERSISTED_PROPOSAL_BLOCK_CODES and
                type(candidate_revision) is int else None)
            failure_count = self._record_reasoning_failure(objective_id,
                failure_type=type(exc).__name__, detail_code=detail_code,
                blocked_revision=blocked_revision)
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
        if (type(exc).__name__ == "ObjectiveStateError" and
                str(exc) == "proposal omits one or more human acceptance criteria"):
            return "PROPOSAL_OMITS_ACCEPTANCE_CRITERIA"
        if (type(exc).__name__ == "ObjectiveStateError" and
                str(exc) == "proposal must bind every original criterion to an Engineering step or a supported lifecycle event"):
            return "PROPOSAL_CRITERIA_BINDING_REJECTED"
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

    def _runtime_revision(self):
        value = os.environ.get("RIVERVIEW_SOURCE_COMMIT", "")
        return value if re.fullmatch(r"[0-9a-f]{40}", value) else "unversioned"

    def _proposal_rejection_blocked(self, objective_id, objective_revision):
        """Suppress deterministic proposal rejection repeats for this objective revision."""
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT 1 FROM grace_objective_events
                WHERE objective_id=%s AND event_type='execution.reasoning_failed'
                  AND payload->>'status'='BLOCKED'
                  AND payload->>'objective_revision'=%s
                  AND payload->>'runtime_revision'=%s
                  AND payload->>'detail_code'=ANY(%s)
                ORDER BY sequence DESC LIMIT 1""",
                (objective_id, str(objective_revision), self._runtime_revision(),
                 list(self.PERSISTED_PROPOSAL_BLOCK_CODES)))
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

    def _record_reasoning_attempt(self, objective_id):
        request_id = str(uuid4())
        key = f"grace-reasoning-attempt:{objective_id}:{request_id}"
        with self.pipeline.ledger.db.transaction():
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'execution.reasoning_attempted',%s,
                        'service:grace-execution','{}'::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (objective_id, key))

    def _record_reasoning_failure(self, objective_id, *, result=None, failure_type=None,
                                  detail_code=None, blocked_revision=None):
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
                receipt = self.rejected_work_order_publisher(review_context)
                if (not isinstance(receipt, dict) or
                        receipt.get("status") not in {"published", "already_published"} or
                        receipt.get("verification_id") !=
                            context["completion"]["verification_id"]):
                    continue
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

    def request_external_reasoning(self, envelope, original_request, *, conversation_id,
            message_sequence, idempotency_key, deadline_at, classification="institutional",
            proposal_id=None, proposal_revision=None, source_references=(),
            review_subject=None, review_parent=None):
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
            review_subject=review_subject, review_parent=review_parent)

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
                    "direct_external_reasoning": direct_result}
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
