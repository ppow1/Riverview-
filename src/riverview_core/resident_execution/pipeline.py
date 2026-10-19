# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/pipeline.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.1.14
# Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Reconcile bounded review generations with active production behavior and exact-scope authorization.
# Purpose: Persist objectives, require verified grounding, and hand proposals to CME intake
# Execution Model: Request-driven orchestration over existing PostgreSQL authority and ledger
# Observability: Append-only objective events linked to assignment and evidence provenance
# Dependencies: Psycopg 3; AuthorizedAssignmentIntake; knowledge-provider v1
# Authority: objective.submit and assignment.create exact grants; no proposal self-authorization
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Initial durable execution bridge
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Expose bounded grounded objective context to ResidentReasoner
# Changed: 2026-10-13 UTC | RV-GRACE-CONVERSATION-WORKORDER | Accept authenticated principals and retain conversation origin
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Carry independently verified artifact location into Grace completion event
# Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Add durable retryable outbox for verified conversation-origin work results
# Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RETRY-003 | Revalidate exact submission grant before retrying existing objectives
# Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-REGROUND-001 | Commit verified grounding when resuming a durable WAITING_FOR_EVIDENCE objective
# Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-CONTEXT-001 | Include resident contract reference in durable reasoning context
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Persist dependency-ordered step execution and verified continuation in existing objective ledger
# Changed: 2026-10-16 UTC | RV-GRACE-STRUCTURED-REVIEW-001 | Store safe same-objective continuation proposals and cycle-specific result receipts
# Previous Revision: 1.1.1
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Persist per-step execution capability and file scope in proposal provenance; resolve verified predecessor patches
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reject model-proposed source paths unless every path is explicitly named in the original Steward request or accepted criteria
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Require Grace 80B review of each verified predecessor before dispatching dependent work
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Expose each verified objective step to the existing Grace result-review outbox
# Changed: 2026-10-16 UTC | RV-GRACE-REVIEW-OBJECTIVE-PROGRESS | Include authoritative objective and step state in Grace's verified-result review context
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Persist Grace's bounded same-assignment rework decision and recovery receipt against the original verifier rejection
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-FIX-001 | Resolve rejected steps from objective links, fence completed leases, and resume only the current rejection decision
# Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-ROLE-SEPARATION-001 | Persist verifier identity/criteria/evidence for Grace review and gate Codex rechecks on a durable objective-satisfied decision
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Persist immutable proposal revision, approval, source and exact-grant correlation on objective intake
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Persist Grace's external-advisory evaluation atomically with the resulting proposal
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Resolve failed steps only after their linked revalidation successor is independently verified
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Share the verified rework completion predicate with objective reconciliation.
# Changed: 2026-10-18 UTC | RV-C3-EXACT-PROPOSAL-REVIEW-001 | Persist exact-subject review, revision and blocked decisions
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: tests/test_grace_execution.py; tests/test_resident_reasoning.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Durable, fail-closed objective intake and work-order handoff.

Reasoning is replaceable: callers provide a typed PlanProposal produced by
ResidentReasoner (tests use deterministic fixtures). This component persists the
proposal but never approves its own authority. Assignment creation still passes
through AuthorizedAssignmentIntake and the existing CME ledger.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re

from ..assignment_intake import AuthorizedAssignmentIntake, AssignmentIntakeDenied
from ..resident_reasoning import PlanProposal
from ..worker_adapter.knowledge import KnowledgeStatus


class ObjectiveError(RuntimeError):
    """Objective persistence or evidence operation failed safely."""


class ObjectiveNotAuthorized(ObjectiveError):
    """No exact active grant authorizes the requested objective operation."""


class ObjectiveStateError(ObjectiveError):
    """The requested lifecycle transition is invalid or its evidence incomplete."""


class ObjectiveContextReader:
    """ResidentReasoner adapter over verified, office-scoped objective records."""

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def read(self, assignment_id):
        return self.pipeline.read_reasoning_context(assignment_id)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


class GraceExecutionPipeline:
    """Persist an objective, evidence, proposal, assignment link, and completion."""

    MAX_OBJECTIVE_BYTES = 4096
    MAX_EVIDENCE_BYTES = 8 * 1024
    WORKFLOW_ID = "grace.objective-work-order.v1"
    CONTRACT_REF = "repo://riverview/resident-engineering.v1"

    def __init__(self, ledger, authorizer, assignment_intake, knowledge):
        if (not isinstance(assignment_intake, AuthorizedAssignmentIntake) or
                assignment_intake.ledger is not ledger):
            raise TypeError("AuthorizedAssignmentIntake is required")
        self.ledger = ledger
        self.authorizer = authorizer
        self.assignment_intake = assignment_intake
        self.knowledge = knowledge

    def _event(self, cur, objective_id, event_type, idem, actor_id, payload):
        cur.execute("""INSERT INTO grace_objective_events
            (objective_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT (idempotency_key) DO NOTHING""",
            (objective_id, event_type, idem, actor_id, _json(payload)))

    def authorize_objective_submission(self, principal_id, scope_ref):
        """Recheck the existing exact objective.submit grant for an idempotent retry."""
        db = self.ledger.db
        try:
            with db.transaction():
                with db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    return self.authorizer.require_principal(
                        cur, principal_id, "objective.submit", scope_ref)
        except Exception as exc:
            if type(exc).__name__ == "GrantDenied":
                raise ObjectiveNotAuthorized("objective.submit is not authorized") from None
            raise

    def submit_objective(self, objective_id, request, acceptance_criteria, *,
                         scope_ref, credential=None, principal=None, origin=None,
                         proposal_reference=None):
        if (not isinstance(objective_id, str) or not re.fullmatch(r"objective:[A-Za-z0-9._:-]{1,120}", objective_id)
                or not isinstance(request, str) or not request.strip()
                or len(request.encode("utf-8")) > self.MAX_OBJECTIVE_BYTES
                or not isinstance(acceptance_criteria, (list, tuple))
                or not acceptance_criteria or len(acceptance_criteria) > 20
                or any(not isinstance(item, str) or not item.strip() or len(item) > 1000
                       for item in acceptance_criteria)):
            raise ValueError("objective identity, bounded request, and acceptance criteria are required")
        if (credential is None) == (principal is None):
            raise ValueError("exactly one authenticated credential or principal is required")
        if origin is not None:
            if (not isinstance(origin, dict) or set(origin) != {"conversation_id", "source_sequence"}
                    or not isinstance(origin["conversation_id"], str)
                    or len(origin["conversation_id"]) != 36
                    or type(origin["source_sequence"]) is not int
                    or origin["source_sequence"] < 1):
                raise ValueError("conversation origin is invalid")
        if proposal_reference is not None:
            if (not isinstance(proposal_reference, dict) or set(proposal_reference) != {
                    "proposal_id", "revision", "content_sha256", "approval_event_key",
                    "source_references", "privacy_classification", "retention_policy",
                    "approved_purpose", "objective_submit_grant_id"}
                    or not isinstance(proposal_reference["proposal_id"], str)
                    or type(proposal_reference["revision"]) is not int
                    or not re.fullmatch(r"[0-9a-f]{64}", proposal_reference["content_sha256"])
                    or not isinstance(proposal_reference["approval_event_key"], str)
                    or not isinstance(proposal_reference["source_references"], list)
                    or proposal_reference["privacy_classification"] not in {
                        "institutional", "confidential", "restricted", "local_only"}
                    or proposal_reference["retention_policy"] not in {
                        "standard", "minimum_required", "ephemeral"}
                    or not isinstance(proposal_reference["approved_purpose"], str)
                    or not proposal_reference["approved_purpose"].strip()
                    or not isinstance(proposal_reference["objective_submit_grant_id"], str)
                    or not proposal_reference["objective_submit_grant_id"]
                    or len(_json(proposal_reference).encode("utf-8")) > 8192):
                raise ValueError("proposal correlation is invalid")
        db = self.ledger.db
        try:
            with db.transaction():
                with db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    if principal is not None:
                        actor = self.authorizer.require_principal(
                            cur, getattr(principal, "principal_id", None),
                            "objective.submit", scope_ref)
                    else:
                        actor = self.authorizer.require(
                            cur, credential, "objective.submit", scope_ref)
                    cur.execute("""INSERT INTO grace_objectives
                        (objective_id,request,scope_ref,submitter_id,acceptance_criteria,status)
                        VALUES (%s,%s,%s,%s,%s::jsonb,'RECEIVED')""",
                        (objective_id, request.strip(), scope_ref, actor["principal_id"],
                         _json(list(acceptance_criteria))))
                    self._event(cur, objective_id, "objective.received",
                                f"grace-objective-received:{objective_id}", actor["principal_id"],
                                {"acceptance_criteria": list(acceptance_criteria),
                                 **({"proposal_reference": proposal_reference}
                                    if proposal_reference is not None else {}),
                                 **({"origin": origin} if origin is not None else {})})
        except Exception as exc:
            if type(exc).__name__ in {"GrantDenied", "GrantCheckUnavailable"}:
                raise ObjectiveNotAuthorized("objective.submit is not authorized") from None
            if "UniqueViolation" in type(exc).__name__:
                raise ObjectiveStateError("objective identity already exists") from None
            raise
        return self.get_objective(objective_id)

    def ground_objective(self, objective_id):
        objective = self.get_objective(objective_id)
        if objective is None or objective["status"] not in {"RECEIVED", "WAITING_FOR_EVIDENCE"}:
            raise ObjectiveStateError("objective is not awaiting grounding")
        evidence_input = {"id": objective_id, "objective": objective["request"],
                          "acceptance_criteria": objective["acceptance_criteria"],
                          "contract_ref": self.CONTRACT_REF}
        result = self.knowledge.ground_assignment(evidence_input)
        evidence = {"status": result.status.value,
                    "source_references": list(result.source_references),
                    "source_revision": result.source_revision,
                    "source_sha256": result.source_sha256,
                    "retrieval_complete": result.retrieval_complete,
                    "value": result.value}
        try:
            raw_evidence = _json(evidence).encode("utf-8")
        except (TypeError, ValueError):
            evidence = {"status": KnowledgeStatus.UNVERIFIED.value,
                        "source_references": list(result.source_references),
                        "source_revision": result.source_revision,
                        "source_sha256": result.source_sha256,
                        "retrieval_complete": False,
                        "error_code": "EVIDENCE_SERIALIZATION_FAILED", "value": None}
            self._set_waiting(objective_id, evidence, "knowledge-provider")
            raise ObjectiveStateError("grounded evidence serialization failed") from None
        if len(raw_evidence) > self.MAX_EVIDENCE_BYTES:
            evidence = {"status": KnowledgeStatus.INCOMPLETE.value,
                        "source_references": list(result.source_references),
                        "source_revision": result.source_revision,
                        "source_sha256": result.source_sha256,
                        "retrieval_complete": False,
                        "error_code": "EVIDENCE_TOO_LARGE", "value": None}
            self._set_waiting(objective_id, evidence, "knowledge-provider")
            raise ObjectiveStateError("grounded evidence exceeds context boundary")
        if (result.status is not KnowledgeStatus.VERIFIED or
                result.retrieval_complete is not True or not result.source_references or
                not result.source_revision or not result.source_sha256):
            self._set_waiting(objective_id, evidence, "knowledge-provider")
            raise ObjectiveStateError("repository evidence is not complete and verified")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE grace_objectives SET status='GROUNDED',evidence=%s::jsonb,
                    source_revision=%s,source_sha256=%s,revision=revision+1,updated_at=clock_timestamp()
                    WHERE objective_id=%s AND status IN ('RECEIVED','WAITING_FOR_EVIDENCE')""",
                    (_json(evidence), result.source_revision, result.source_sha256, objective_id))
                if cur.rowcount != 1:
                    raise ObjectiveStateError("objective changed during grounding")
                self._event(cur, objective_id, "objective.grounded",
                            f"grace-objective-grounded:{objective_id}", "grace:knowledge-provider",
                            {key: evidence[key] for key in ("status", "source_references",
                                "source_revision", "source_sha256", "retrieval_complete")})
        return self.get_objective(objective_id)

    def _set_waiting(self, objective_id, evidence, actor):
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE grace_objectives SET status='WAITING_FOR_EVIDENCE',
                    evidence=%s::jsonb,revision=revision+1,updated_at=clock_timestamp()
                    WHERE objective_id=%s AND status IN ('RECEIVED','WAITING_FOR_EVIDENCE')
                    RETURNING revision""",
                    (_json(evidence), objective_id))
                row = cur.fetchone()
                if not row:
                    raise ObjectiveStateError("objective changed while recording missing evidence")
                self._event(cur, objective_id, "objective.waiting_for_evidence",
                            f"grace-objective-waiting:{objective_id}:{row['revision']}", actor,
                            {"status": evidence["status"],
                             "retrieval_complete": evidence["retrieval_complete"]})

    def record_proposal(self, objective_id, proposal: PlanProposal, *, actor_id="resident:grace",
                        external_exchange=None, review_evidence=None):
        if not isinstance(proposal, PlanProposal):
            raise TypeError("proposal must satisfy the existing PlanProposal contract")
        objective = self.get_objective(objective_id)
        if objective is None or objective["status"] != "GROUNDED":
            raise ObjectiveStateError("verified objective evidence is required before proposal")
        evidence = objective["evidence"]
        if (evidence.get("status") != KnowledgeStatus.VERIFIED.value or
                evidence.get("retrieval_complete") is not True or
                not evidence.get("source_references") or not evidence.get("source_sha256")):
            raise ObjectiveStateError("proposal cannot use missing or incomplete evidence")
        requested = set(objective["acceptance_criteria"])
        proposed = {criterion for step in proposal.steps
                    for criterion in step.acceptance_criteria}
        if not requested.issubset(proposed):
            raise ObjectiveStateError("proposal omits one or more human acceptance criteria")
        # A model cannot turn a general objective into filesystem authority.
        # Every source path must have been explicitly named in the Steward's
        # original request or accepted criteria; the adapter allowlist is only
        # a second, operator-configured ceiling.
        approved_source_scope = [objective["request"], *objective["acceptance_criteria"]]
        for step in proposal.steps:
            if step.execution_capability == "engineering.codex-cli-source-change.v1":
                target_values = (step.repository_reference, step.repository_revision)
                if any(not any(value in text for text in approved_source_scope)
                       for value in target_values):
                    raise ObjectiveStateError(
                        "source-change target identity and commit must be Steward-authorized")
                if any(not any(re.search(r"(?<![A-Za-z0-9._/-])" + re.escape(path) +
                                         r"(?![A-Za-z0-9_/-]|\.(?=[A-Za-z0-9._/-]))", text)
                               for text in approved_source_scope)
                       for path in step.authorized_paths):
                    raise ObjectiveStateError(
                        "source-change path is absent from the Steward-approved objective scope")
        if external_exchange is not None:
            required = {"request_id", "correlation_id", "response_id", "response_sha256", "provider_id",
                        "provider_model", "reasoning_request_id"}
            if (not isinstance(external_exchange, dict) or set(external_exchange) != required
                    or not all(isinstance(external_exchange[key], str) and external_exchange[key]
                               and len(external_exchange[key]) <= 160 for key in required)
                    or not re.fullmatch(r"[0-9a-f]{64}", external_exchange["response_sha256"])):
                raise ObjectiveStateError("external advisory provenance is invalid")
            from uuid import UUID
            try:
                UUID(external_exchange["request_id"])
                UUID(external_exchange["correlation_id"])
            except (ValueError, TypeError, AttributeError):
                raise ObjectiveStateError("external advisory correlation is invalid") from None
        if review_evidence is not None:
            required_review = {"subject_id", "revision", "subject_sha256", "response_sha256",
                               "proposal_sha256", "decision"}
            if (not isinstance(review_evidence, dict) or set(review_evidence) != required_review
                    or not isinstance(review_evidence["subject_id"], str)
                    or type(review_evidence["revision"]) is not int
                    or not 1 <= review_evidence["revision"] <= 3
                    or any(not isinstance(review_evidence[k], str) or not re.fullmatch(
                        r"[0-9a-f]{64}", review_evidence[k]) for k in
                        ("subject_sha256", "response_sha256", "proposal_sha256"))
                    or review_evidence["decision"] != "finish"):
                raise ObjectiveStateError("exact proposal review evidence is invalid")
            from .external_reasoning import proposal_review_content
            review_content = proposal_review_content(proposal)
            review_content_sha = hashlib.sha256(_json(review_content).encode("utf-8")).hexdigest()
            subject_sha = hashlib.sha256(_json({
                "subject_id": review_evidence["subject_id"],
                "revision": review_evidence["revision"],
                "proposal": review_content}).encode("utf-8")).hexdigest()
            if (review_content_sha != review_evidence["proposal_sha256"] or
                    subject_sha != review_evidence["subject_sha256"]):
                raise ObjectiveStateError("final proposal does not match its exact review subject")
        document = asdict(proposal)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE grace_objectives SET status='PROPOSED',proposal=%s::jsonb,
                    revision=revision+1,updated_at=clock_timestamp()
                    WHERE objective_id=%s AND status='GROUNDED'""",
                    (_json(document), objective_id))
                if cur.rowcount != 1:
                    raise ObjectiveStateError("objective changed during proposal")
                for ordinal, step in enumerate(proposal.steps, start=1):
                    cur.execute("""INSERT INTO grace_objective_steps
                        (objective_id,step_id,step_order,step_objective,acceptance_criteria,
                         depends_on,status)
                        VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,'pending')""",
                        (objective_id, step.step_id, ordinal, step.objective,
                         _json(list(step.acceptance_criteria)), _json(list(step.depends_on))))
                self._event(cur, objective_id, "work_order.proposed",
                            f"grace-work-order-proposed:{objective_id}", actor_id,
                            {"proposal_sha256": hashlib.sha256(_json(document).encode()).hexdigest(),
                             "step_ids": [step.step_id for step in proposal.steps],
                             "approved": False})
                if external_exchange is not None:
                    self._event(cur, objective_id,
                        "resident.reasoning.external_advisory_evaluated",
                        f"external-reasoning:{external_exchange['request_id']}:reasoned",
                        actor_id, {**external_exchange,
                            "decision": "advisory_evaluated_as_unapproved_proposal",
                            "proposal_sha256": hashlib.sha256(
                                _json(document).encode("utf-8")).hexdigest()})
                if review_evidence is not None:
                    self._event(cur, objective_id,
                        "resident.reasoning.external_proposal_reviewed",
                        f"external-proposal-reviewed:{external_exchange['request_id']}",
                        actor_id, {**external_exchange, **review_evidence})
        return self.get_objective(objective_id)

    def record_external_review_decision(self, objective_id, *, request_id,
            correlation_id, event_type, payload, actor_id="office:grace"):
        """Durably record a non-final review decision without proposing or authorizing work."""
        allowed = {"resident.reasoning.external_proposal_revised",
                   "resident.reasoning.external_proposal_review_blocked"}
        if (event_type not in allowed or not isinstance(payload, dict)
                or not isinstance(request_id, str) or not isinstance(correlation_id, str)):
            raise ObjectiveStateError("external review decision is invalid")
        objective = self.get_objective(objective_id)
        if objective is None or objective["status"] != "GROUNDED":
            raise ObjectiveStateError("review revision requires a grounded objective")
        safe = {key: value for key, value in payload.items() if key in {
            "subject_id", "revision", "subject_sha256", "response_sha256",
            "proposal_sha256", "decision", "successor_request_id", "successor_correlation_id",
            "reason_code"}}
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                suffix = ("revised" if event_type ==
                    "resident.reasoning.external_proposal_revised" else "blocked")
                self._event(cur, objective_id, event_type,
                    f"external-proposal-review:{request_id}:{suffix}",
                    actor_id, {"request_id": request_id, "correlation_id": correlation_id, **safe})

    def dispatchable_step(self, objective_id):
        """Return the next pending step after verified dependencies and Grace review."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT step_id,step_order,step_objective,acceptance_criteria,
                    depends_on,status,assignment_id FROM grace_objective_steps
                WHERE objective_id=%s ORDER BY step_order""", (objective_id,))
            rows = cur.fetchall()
            cur.execute("""SELECT payload->>'step_id' AS step_id
                FROM grace_objective_events WHERE objective_id=%s
                  AND event_type='work_order.continuation_proposed'""", (objective_id,))
            reviewed = {row["step_id"] for row in cur.fetchall()}
        verified = {row["step_id"] for row in rows if row["status"] == "verified"}
        for row in rows:
            if (row["status"] == "pending" and set(row["depends_on"]) <= verified and
                    (row["step_order"] == 1 or row["step_id"] in reviewed)):
                return row
        return None

    def objective_steps_complete(self, cur, objective_id):
        """Treat a blocked step as resolved only through its verified rework successor."""
        cur.execute("""SELECT bool_and(s.status='verified' OR (
                s.status='blocked' AND EXISTS (
                    SELECT 1 FROM grace_objective_events re
                    JOIN grace_objective_steps successor
                      ON successor.objective_id=re.objective_id
                     AND successor.step_id=re.payload->>'successor_step_id'
                    WHERE re.objective_id=s.objective_id
                      AND re.event_type='work_order.stale_base_revalidated'
                      AND re.payload->>'source_step_id'=s.step_id
                      AND successor.status='verified')))
            AS complete FROM grace_objective_steps s WHERE s.objective_id=%s""",
            (objective_id,))
        row = cur.fetchone()
        return bool(row and row["complete"])

    def proposal_step_for_assignment(self, objective_id, assignment_id):
        """Resolve proposal content through the durable objective-step assignment link."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT s.step_id,s.step_objective,s.acceptance_criteria,s.depends_on,
                    o.proposal,d.payload AS dispatch_payload
                FROM grace_objective_steps s JOIN grace_objectives o USING(objective_id)
                LEFT JOIN LATERAL (
                    SELECT payload FROM grace_objective_events e
                    WHERE e.objective_id=s.objective_id
                      AND e.event_type='work_order.dispatched'
                      AND e.payload->>'assignment_id'=s.assignment_id
                      AND e.payload->>'workflow_step'=s.step_id
                    ORDER BY e.sequence DESC LIMIT 1
                ) d ON true
                WHERE s.objective_id=%s AND s.assignment_id=%s""",
                (objective_id, assignment_id))
            row = cur.fetchone()
        if row is None:
            return None
        proposal = row["proposal"] if isinstance(row["proposal"], dict) else {}
        raw_step = next((item for item in proposal.get("steps", [])
                         if isinstance(item, dict) and item.get("step_id") == row["step_id"]), {})
        return {"step_id": row["step_id"], "objective": row["step_objective"],
                "acceptance_criteria": row["acceptance_criteria"],
                "depends_on": row["depends_on"],
                "execution_capability": raw_step.get(
                    "execution_capability", "engineering.codex-cli-artifact.v1"),
                "authorized_paths": raw_step.get("authorized_paths", []),
                "test_targets": raw_step.get("test_targets", []),
                "repository_reference": raw_step.get("repository_reference"),
                "repository_revision": raw_step.get("repository_revision"),
                "source_target_binding": (row["dispatch_payload"].get("source_target_binding")
                    if isinstance(row["dispatch_payload"], dict) else None)}

    @staticmethod
    def _source_target_binding(objective, step, assignment_id):
        """Snapshot a typed source target into the append-only dispatch event."""
        proposal = objective.get("proposal") if isinstance(objective, dict) else None
        raw_steps = proposal.get("steps", []) if isinstance(proposal, dict) else []
        raw_step = next((item for item in raw_steps if isinstance(item, dict) and
                         item.get("step_id") == step["step_id"]), None)
        if not isinstance(raw_step, dict):
            raise ObjectiveStateError("persisted proposal step is unavailable at dispatch")
        if raw_step.get("execution_capability") != "engineering.codex-cli-source-change.v1":
            return {}
        if (raw_step.get("step_id") != step["step_id"] or
                raw_step.get("objective") != step.get("step_objective") or
                tuple(raw_step.get("acceptance_criteria", ())) != tuple(
                    step.get("acceptance_criteria", ()))):
            raise ObjectiveStateError("source proposal changed before assignment dispatch")
        repository_reference = raw_step.get("repository_reference")
        repository_revision = raw_step.get("repository_revision")
        if (not isinstance(repository_reference, str) or
                not re.fullmatch(r"repo://[A-Za-z0-9._/-]{1,240}", repository_reference) or
                not isinstance(repository_revision, str) or
                not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", repository_revision)):
            raise ObjectiveStateError("source target binding is incomplete")
        return {"source_target_binding": {
            "version": "grace.source-target-binding.v1",
            "objective_id": objective["objective_id"],
            "assignment_id": assignment_id,
            "step_id": step["step_id"],
            "capability": raw_step["execution_capability"],
            "repository_reference": repository_reference,
            "repository_revision": repository_revision,
            "authorized_paths": raw_step.get("authorized_paths"),
            "test_targets": raw_step.get("test_targets"),
            "proposal_step_sha256": hashlib.sha256(
                _json(raw_step).encode("utf-8")).hexdigest(),
        }}

    def verified_source_change_predecessor(self, objective_id, step):
        """Return the latest independently verified patch and scope for a linear dependent step."""
        from ..resident_reasoning import PlanStep
        if not isinstance(step, PlanStep) or step.execution_capability != \
                "engineering.codex-cli-source-change.v1":
            raise ObjectiveStateError("source-change step is required")
        if not step.depends_on:
            return {"prior_patches": (), "authorized_paths": (), "test_targets": ()}
        if len(step.depends_on) != 1:
            raise ObjectiveStateError("source-change patch chains require one verified predecessor")
        predecessor_id = step.depends_on[0]
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT s.status,s.assignment_id,o.proposal,wr.result
                FROM grace_objective_steps s JOIN grace_objectives o USING(objective_id)
                JOIN assignments a ON a.id=s.assignment_id
                JOIN worker_attempts wa ON wa.assignment_id=a.id AND wa.status='succeeded'
                JOIN worker_results wr USING(attempt_id)
                WHERE s.objective_id=%s AND s.step_id=%s
                ORDER BY wa.started_at DESC LIMIT 1""", (objective_id, predecessor_id))
            row = cur.fetchone()
        if not row or row["status"] != "verified" or not row["assignment_id"]:
            raise ObjectiveStateError("dependent source change requires verified predecessor")
        result = row["result"]
        if (not isinstance(result, dict) or result.get("capability") !=
                "engineering.codex-cli-source-change.v1" or
                result.get("status") != "SUCCEEDED" or
                not isinstance(result.get("patch_path"), str) or
                not re.fullmatch(r"[0-9a-f]{64}", str(result.get("patch_sha256", "")))):
            raise ObjectiveStateError("verified predecessor patch provenance is incomplete")
        proposal = row["proposal"] if isinstance(row["proposal"], dict) else {}
        raw_step = next((item for item in proposal.get("steps", [])
                         if isinstance(item, dict) and item.get("step_id") == predecessor_id), {})
        return {"prior_patches": ((result["patch_path"], result["patch_sha256"]),),
                "authorized_paths": tuple(raw_step.get("authorized_paths", ())),
                "test_targets": tuple(raw_step.get("test_targets", ())),
                "repository_reference": result.get("repository_reference"),
                "repository_revision": result.get("repository_revision")}

    def authorize_and_dispatch(self, objective_id, assignment_id, *, credential,
                               authority_ref, idempotency_key, step_id=None):
        objective = self.get_objective(objective_id)
        if (objective is None or objective["status"] not in {"PROPOSED", "WORK_ORDER_CREATED"}
                or objective["scope_ref"] != authority_ref or not objective["proposal"]):
            raise ObjectiveStateError("grounded proposal and matching exact authority scope are required")
        step = self.dispatchable_step(objective_id)
        if step is None or (step_id is not None and step["step_id"] != step_id):
            raise ObjectiveStateError("no dependency-ready step is available for dispatch")
        if not objective["evidence"] or objective["evidence"]["status"] != "VERIFIED":
            raise ObjectiveStateError("verified evidence is required for dispatch")
        try:
            # Both adapters share this ledger connection. The nested intake
            # transaction is a savepoint, so assignment + event and objective
            # linkage commit or roll back as one unit.
            with self.ledger.db.transaction():
                with self.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    cur.execute("""SELECT status,proposal FROM grace_objectives
                        WHERE objective_id=%s FOR UPDATE""", (objective_id,))
                    locked_objective = cur.fetchone()
                    if not locked_objective or locked_objective["status"] not in {
                            "PROPOSED", "WORK_ORDER_CREATED"}:
                        raise ObjectiveStateError("objective changed before step dispatch")
                    if _json(locked_objective["proposal"]) != _json(objective["proposal"]):
                        raise ObjectiveStateError("proposal changed before assignment dispatch")
                    assignment = self.assignment_intake.create(
                        assignment_id, "engineering", idempotency_key,
                        credential=credential, authority_ref=authority_ref,
                        objective_ref=objective_id,
                        contract_ref="repo://riverview/worker-adapter-contract.v1",
                        workflow_id=self.WORKFLOW_ID,
                        workflow_step=step["step_id"], correlation_id=objective_id)
                    cur.execute("""UPDATE grace_objective_steps SET status='assigned',
                        assignment_id=%s,dispatch_count=dispatch_count+1,
                        updated_at=clock_timestamp() WHERE objective_id=%s AND step_id=%s
                        AND status='pending' AND assignment_id IS NULL""",
                        (assignment_id, objective_id, step["step_id"]))
                    if cur.rowcount != 1:
                        raise ObjectiveStateError("step dispatch raced with another worker")
                    cur.execute("""SELECT actor_id FROM events WHERE assignment_id=%s
                        AND event_type='assignment.created' ORDER BY seq LIMIT 1""",
                        (assignment_id,))
                    created_event = cur.fetchone()
                    if not created_event:
                        raise ObjectiveStateError("assignment creation event is missing")
                    cur.execute("""UPDATE grace_objectives SET status='WORK_ORDER_CREATED',
                        assignment_id=%s,revision=revision+1,updated_at=clock_timestamp()
                        WHERE objective_id=%s AND status IN ('PROPOSED','WORK_ORDER_CREATED')""",
                        (assignment_id, objective_id))
                    if cur.rowcount != 1:
                        raise ObjectiveStateError("objective assignment link conflicts with existing state")
                    binding_objective = dict(objective)
                    binding_objective["proposal"] = locked_objective["proposal"]
                    self._event(cur, objective_id, "work_order.dispatched",
                                f"grace-work-order-dispatched:{objective_id}:{step['step_id']}",
                                created_event["actor_id"],
                        {"assignment_id": assignment_id,
                         "workflow_step": step["step_id"],
                         **self._source_target_binding(binding_objective, step, assignment_id)})
        except AssignmentIntakeDenied:
            raise ObjectiveNotAuthorized("assignment.create is not authorized") from None
        return assignment

    def record_verified_completion(self, objective_id, assignment_id):
        objective = self.get_objective(objective_id)
        assignment = self.ledger.get(assignment_id)
        if (objective is None or objective["status"] != "WORK_ORDER_CREATED" or
                objective["assignment_id"] != assignment_id or not assignment or
                assignment["state"] != "completed"):
            raise ObjectiveStateError("completed assignment is not independently verified")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT verification_id,decision,verifier_id,criteria,
                    verifier_revision,evidence_references,summary
                FROM verification_records WHERE assignment_id=%s AND decision='ACCEPTED'
                ORDER BY recorded_at DESC,verification_id DESC LIMIT 1""", (assignment_id,))
            verification = cur.fetchone()
        if not verification:
            raise ObjectiveStateError("persisted independent verification is required")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT step_id,step_order FROM grace_objective_steps
                    WHERE objective_id=%s AND assignment_id=%s FOR UPDATE""",
                    (objective_id, assignment_id))
                step_row = cur.fetchone()
                if not step_row:
                    raise ObjectiveStateError("verified assignment is not linked to an objective step")
                cur.execute("""UPDATE grace_objective_steps SET status='verified',
                    verified_at=clock_timestamp(),updated_at=clock_timestamp()
                    WHERE objective_id=%s AND step_id=%s AND status='assigned'
                    AND assignment_id=%s""", (objective_id, step_row["step_id"], assignment_id))
                if cur.rowcount not in (0, 1):
                    raise ObjectiveStateError("step verification state is inconsistent")
                all_steps = self.objective_steps_complete(cur, objective_id)
        completion_cycle = step_row["step_order"]
        payload = {"assignment_id": assignment_id, "step_id": step_row["step_id"],
                   "completion_cycle": completion_cycle,
                   "verification_id": str(verification["verification_id"]),
                   "decision": verification["decision"],
                   "verifier_id": verification["verifier_id"],
                   "verifier_revision": verification["verifier_revision"],
                   "verification_criteria": verification["criteria"],
                   "verification_summary": verification["summary"],
                   "evidence_references": list(verification["evidence_references"])}
        if all_steps:
            payload["proposal"] = objective.get("proposal")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT wr.result FROM worker_attempts wa
                JOIN worker_results wr USING(attempt_id)
                WHERE wa.assignment_id=%s AND wa.status='succeeded'
                ORDER BY wa.started_at DESC LIMIT 1""", (assignment_id,))
            artifact_row = cur.fetchone()
        artifact = artifact_row["result"] if artifact_row else None
        if isinstance(artifact, dict):
            allowed_evidence = ("artifact_name", "artifact_path", "artifact_sha256",
                "artifact_bytes", "capability", "changed_files", "patch_sha256",
                "patch_bytes", "test_status", "repository_reference", "repository_revision",
                "assignment_id", "objective_id", "artifact_schema", "source_artifact_name",
                "source_revision", "source_sha256", "rework_verification_id", "status")
            payload["artifact"] = {key: artifact[key] for key in allowed_evidence
                                    if key in artifact}
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE grace_objectives SET status=%s,revision=revision+1,
                    updated_at=clock_timestamp() WHERE objective_id=%s
                    AND status='WORK_ORDER_CREATED' AND assignment_id=%s""",
                    ("COMPLETED" if all_steps else "WORK_ORDER_CREATED",
                     objective_id, assignment_id))
                if cur.rowcount != 1:
                    raise ObjectiveStateError("objective completion raced with another update")
                if all_steps:
                    self._event(cur, objective_id, "objective.completed",
                                f"grace-objective-completed:{objective_id}:{completion_cycle}", "verifier:independent",
                                payload)
                else:
                    self._event(cur, objective_id, "execution.step_verified",
                                f"grace-step-verified:{objective_id}:{step_row['step_id']}",
                                "verifier:independent", payload)
        return self.get_objective(objective_id)

    def cancel_work_order(self, objective_id, *, credential, authority_ref):
        """Cancel only work that has not started, using an exact assignment.cancel grant."""
        objective = self.get_objective(objective_id)
        if (objective is None or objective["status"] != "WORK_ORDER_CREATED" or
                objective["scope_ref"] != authority_ref or not objective["assignment_id"]):
            raise ObjectiveStateError("a dispatched objective in the exact scope is required")
        try:
            with self.ledger.db.transaction():
                with self.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    actor = self.authorizer.require(
                        cur, credential, "assignment.cancel", authority_ref)
                    assignment = self.ledger.get(objective["assignment_id"])
                    if not assignment or assignment["state"] not in {"queued", "ready"}:
                        raise ObjectiveStateError("only queued or ready work can be cancelled safely")
                    self.ledger.transition(
                        assignment["id"], "cancelled", "authorized_work_order_cancellation",
                        f"grace-work-order-cancel:{objective_id}", actor_id=actor["principal_id"])
                    cur.execute("""UPDATE grace_objectives SET status='CANCELLED',
                        revision=revision+1,updated_at=clock_timestamp()
                        WHERE objective_id=%s AND status='WORK_ORDER_CREATED'""",
                        (objective_id,))
                    if cur.rowcount != 1:
                        raise ObjectiveStateError("objective cancellation raced with another update")
                    self._event(cur, objective_id, "work_order.cancelled",
                                f"grace-work-order-cancelled:{objective_id}",
                                actor["principal_id"],
                                {"assignment_id": assignment["id"]})
        except AssignmentIntakeDenied:
            raise ObjectiveNotAuthorized("assignment.cancel is not authorized") from None
        except Exception as exc:
            if type(exc).__name__ == "GrantDenied":
                raise ObjectiveNotAuthorized("assignment.cancel is not authorized") from None
            raise
        return self.get_objective(objective_id)

    def get_objective(self, objective_id):
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT * FROM grace_objectives WHERE objective_id=%s", (objective_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def objective_proposal_reference(self, objective_id):
        """Read proposal provenance from the immutable objective.received event."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT payload->'proposal_reference' AS proposal_reference
                FROM grace_objective_events WHERE objective_id=%s
                  AND event_type='objective.received'""", (objective_id,))
            row = cur.fetchone()
        return row["proposal_reference"] if row else None

    def grounded_objectives(self, *, scope_ref, limit=25, objective_id=None):
        """Return a bounded, stable queue of objectives ready for resident reasoning."""
        if not isinstance(scope_ref, str) or not scope_ref or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("exact scope and bounded objective limit are required")
        if objective_id is not None and (not isinstance(objective_id, str) or
                not re.fullmatch(r"objective:[A-Za-z0-9._:-]{1,120}", objective_id)):
            raise ValueError("objective identity is invalid")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT objective_id,revision FROM grace_objectives
                WHERE status='GROUNDED' AND scope_ref=%s
                  AND (%s::text IS NULL OR objective_id=%s)
                ORDER BY created_at,objective_id LIMIT %s""",
                (scope_ref, objective_id, objective_id, limit))
            return cur.fetchall()

    def read_reasoning_context(self, objective_id):
        """Adapt a durable GROUNDED objective to ResidentReasoner's assignment contract."""
        objective = self.get_objective(objective_id)
        if (objective is None or objective["status"] != "GROUNDED"
                or objective["evidence"].get("status") != KnowledgeStatus.VERIFIED.value
                or objective["evidence"].get("retrieval_complete") is not True):
            raise ObjectiveStateError("verified grounded objective context is required")
        return {
            "id": objective["objective_id"],
            "revision": str(objective["revision"]),
            "state": objective["status"],
            "contract_ref": self.CONTRACT_REF,
            "objective": objective["request"],
            "acceptance_criteria": list(objective["acceptance_criteria"]),
            "verified_evidence": objective["evidence"],
        }

    def objective_events(self, objective_id):
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT event_type,idempotency_key,actor_id,payload,occurred_at
                FROM grace_objective_events WHERE objective_id=%s ORDER BY sequence""",
                (objective_id,))
            return cur.fetchall()

    def pending_conversation_results(self, *, limit=10):
        """Return verified results with an initial review or requested review generation due."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("conversation result limit must be between 1 and 100")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT o.objective_id,c.payload->>'completion_cycle' AS completion_cycle,
                    c.payload,c.event_type
                FROM grace_objectives o
                JOIN LATERAL (SELECT e.payload,e.event_type,e.sequence
                    FROM grace_objective_events e
                    WHERE e.objective_id=o.objective_id
                      AND e.event_type IN ('execution.step_verified','objective.completed')
                      AND EXISTS (SELECT 1 FROM grace_objective_events r
                        WHERE r.objective_id=o.objective_id AND r.event_type='objective.received'
                          AND r.payload ? 'origin')
                    ORDER BY e.sequence DESC LIMIT 1) c ON true
                WHERE o.status IN ('COMPLETED','WORK_ORDER_CREATED')
                ORDER BY o.updated_at,o.objective_id LIMIT %s""", (limit,))
            objective_rows = cur.fetchall()
        results = []
        for objective_row in objective_rows:
            objective_id = objective_row["objective_id"]
            objective = self.get_objective(objective_id)
            events = self.objective_events(objective_id)
            received = next((event for event in events
                if event["event_type"] == "objective.received"), None)
            origin = ((received or {}).get("payload") or {}).get("origin")
            completion = objective_row["payload"]
            if (not objective or not isinstance(origin, dict)
                    or not isinstance(completion, dict)
                    or not completion.get("assignment_id")):
                continue
            cycle = int(objective_row["completion_cycle"] or 1)
            same_cycle = [event for event in events
                if (event.get("payload") or {}).get("completion_cycle") == cycle]
            published_generations = set()
            requested_generations = {}
            for event in same_cycle:
                payload = event.get("payload") or {}
                if event["event_type"] == "conversation.result_published":
                    published_generations.add(int(payload.get("review_generation") or 1))
                elif event["event_type"] == "conversation.result_review_published":
                    published_generations.add(int(payload.get("review_generation") or 0))
                elif event["event_type"] == "conversation.result_review_requested":
                    generation = int(payload.get("review_generation") or 0)
                    if generation > 1:
                        requested_generations[generation] = payload
            pending_reviews = sorted(g for g in requested_generations
                                     if g not in published_generations)
            if pending_reviews:
                review_generation = pending_reviews[0]
                review_request = requested_generations[review_generation]
                # Do not let a later re-review skip an earlier outstanding generation.
                if len(pending_reviews) != 1:
                    continue
            elif 1 not in published_generations:
                review_generation = 1
                review_request = None
            else:
                continue
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT step_id,status FROM grace_objective_steps
                    WHERE objective_id=%s ORDER BY step_order""", (objective_id,))
                step_progress = [{"step_id": row["step_id"], "status": row["status"]}
                                 for row in cur.fetchall()]
            result = {"objective_id": objective_id,
                "assignment_id": completion["assignment_id"],
                "request": objective["request"],
                "acceptance_criteria": list(objective["acceptance_criteria"]),
                "proposal": completion.get("proposal", objective.get("proposal")),
                "objective_status": objective["status"],
                "step_progress": step_progress,
                "submitter_id": received.get("actor_id"),
                "origin": origin,
                "completion_cycle": cycle,
                "completion": completion,
                "review_generation": review_generation}
            if review_request is not None:
                result.update({"review_evidence_revision": review_request["evidence_revision"],
                    "review_evidence": list(review_request["evidence"]),
                    "review_evidence_sha256": review_request["evidence_sha256"]})
            results.append(result)
        return results

    MAX_RESULT_REVIEW_GENERATIONS = 4
    MAX_REVIEW_EVIDENCE_BYTES = 4096

    def request_conversation_result_rereview(self, objective_id, completion_cycle, *,
            evidence_revision, evidence, credential, idempotency_key):
        """Append a Steward-authorized, bounded new review generation for verified evidence.

        objective.submit authorizes this evidence revision only. Assignment creation
        remains independently gated by the persistent dispatcher's assignment.create check.
        """
        if (type(completion_cycle) is not int or completion_cycle < 1
                or not isinstance(evidence_revision, str)
                or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", evidence_revision)
                or not isinstance(evidence, (list, tuple)) or not 1 <= len(evidence) <= 6
                or any(not isinstance(item, str) or not item.strip() or len(item) > 1000
                       for item in evidence)
                or len(_json(list(evidence)).encode("utf-8")) > self.MAX_REVIEW_EVIDENCE_BYTES
                or not isinstance(idempotency_key, str) or not idempotency_key.strip()
                or len(idempotency_key) > 200):
            raise ValueError("verified-result review revision is invalid")
        evidence = list(evidence)
        evidence_sha256 = hashlib.sha256(_json({
            "evidence_revision": evidence_revision, "evidence": evidence
        }).encode("utf-8")).hexdigest()
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT status,scope_ref FROM grace_objectives "
                    "WHERE objective_id=%s FOR UPDATE", (objective_id,))
                objective = cur.fetchone()
                if not objective or objective["status"] not in {"WORK_ORDER_CREATED", "COMPLETED"}:
                    raise ObjectiveStateError("a verified conversation objective is required")
                try:
                    actor = self.authorizer.require(cur, credential, "objective.submit",
                                                    objective["scope_ref"])
                except Exception as exc:
                    if type(exc).__name__ == "GrantDenied":
                        raise ObjectiveNotAuthorized("objective.submit is not authorized for evidence revision") from None
                    raise
                cur.execute("""SELECT 1 FROM grace_objective_events
                    WHERE objective_id=%s
                      AND event_type IN ('execution.step_verified','objective.completed')
                      AND payload->>'completion_cycle'=%s
                      AND payload->>'decision'='ACCEPTED' LIMIT 1""",
                    (objective_id, str(completion_cycle)))
                if not cur.fetchone():
                    raise ObjectiveStateError("matching accepted verified result is required")
                cur.execute("""SELECT event_type,payload FROM grace_objective_events
                    WHERE objective_id=%s AND idempotency_key=%s""",
                    (objective_id, idempotency_key))
                prior = cur.fetchone()
                if prior:
                    payload = prior["payload"] or {}
                    if (prior["event_type"] != "conversation.result_review_requested"
                            or payload.get("completion_cycle") != completion_cycle
                            or payload.get("evidence_revision") != evidence_revision
                            or payload.get("evidence_sha256") != evidence_sha256):
                        raise ObjectiveStateError("review revision idempotency key conflicts")
                    return {"review_generation": payload["review_generation"],
                            "evidence_revision": evidence_revision,
                            "evidence_sha256": evidence_sha256, "reused": True}
                cur.execute("""SELECT event_type,payload FROM grace_objective_events
                    WHERE objective_id=%s AND payload->>'completion_cycle'=%s
                      AND event_type IN ('conversation.result_published',
                         'conversation.result_review_published',
                         'conversation.result_review_requested')
                    ORDER BY sequence""", (objective_id, str(completion_cycle)))
                review_events = cur.fetchall()
                published = {int((row["payload"] or {}).get("review_generation") or 1)
                    for row in review_events if row["event_type"] in {
                        "conversation.result_published", "conversation.result_review_published"}}
                requested = {int((row["payload"] or {}).get("review_generation") or 0)
                    for row in review_events if row["event_type"] == "conversation.result_review_requested"}
                if 1 not in published:
                    raise ObjectiveStateError("the initial verified-result review must publish first")
                pending = requested - published
                if pending:
                    raise ObjectiveStateError("a review generation is already pending")
                generation = max({1, *published, *requested}) + 1
                if generation > self.MAX_RESULT_REVIEW_GENERATIONS:
                    raise ObjectiveStateError("verified-result review generation limit reached")
                payload = {"completion_cycle": completion_cycle,
                    "review_generation": generation, "evidence_revision": evidence_revision,
                    "evidence": evidence, "evidence_sha256": evidence_sha256,
                    "authorization": "objective.submit evidence revision",
                    "actor_principal_id": actor["principal_id"]}
                self._event(cur, objective_id, "conversation.result_review_requested",
                    idempotency_key, actor["principal_id"], payload)
        return {"review_generation": generation, "evidence_revision": evidence_revision,
                "evidence_sha256": evidence_sha256, "reused": False}

    def record_conversation_result_published(self, objective_id, receipt):
        """Acknowledge a durable chat reply after the conversation insert succeeds."""
        base_fields = {
                "request_id", "provider_id", "served_model", "implementation_id",
                "completion_cycle"}
        optional_fields = {"review_generation", "review_evidence_revision",
                           "review_evidence_sha256", "review_decision"}
        if (not isinstance(receipt, dict) or not base_fields <= set(receipt)
                or set(receipt) - base_fields - optional_fields
                or any(not isinstance(value, str) for value in receipt.values())
                or any(not receipt[key] for key in base_fields)
                or not receipt["completion_cycle"].isdigit()):
            raise ValueError("conversation result receipt is invalid")
        generation = int(receipt.get("review_generation", "1"))
        if (receipt.get("review_decision") is not None and receipt["review_decision"] not in {
                "OBJECTIVE_COMPLETE", "ADDITIONAL_EVIDENCE_REQUIRED",
                "ENGINEERING_STEP_PROPOSED", "STEWARD_AUTHORIZATION_REQUIRED"}):
            raise ValueError("conversation result review decision is invalid")
        if (not 1 <= generation <= self.MAX_RESULT_REVIEW_GENERATIONS
                or (generation > 1 and (not receipt.get("review_evidence_revision")
                    or not re.fullmatch(r"[0-9a-f]{64}",
                        receipt.get("review_evidence_sha256", ""))))):
            raise ValueError("conversation result review receipt is invalid")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT status FROM grace_objectives
                    WHERE objective_id=%s FOR UPDATE""", (objective_id,))
                row = cur.fetchone()
                if not row:
                    raise ObjectiveStateError("objective is missing before chat return")
                cur.execute("""SELECT 1 FROM grace_objective_events
                    WHERE objective_id=%s
                      AND event_type IN ('execution.step_verified','objective.completed')
                      AND payload->>'completion_cycle'=%s""",
                    (objective_id, receipt["completion_cycle"]))
                if not cur.fetchone():
                    raise ObjectiveStateError("matching verified completion cycle is required before chat return")
                if generation > 1:
                    cur.execute("""SELECT payload FROM grace_objective_events
                        WHERE objective_id=%s AND payload->>'completion_cycle'=%s
                          AND event_type IN ('conversation.result_review_requested',
                                             'conversation.result_review_published')
                          AND (payload->>'review_generation')::integer=%s
                        ORDER BY sequence DESC LIMIT 1""",
                        (objective_id, receipt["completion_cycle"], generation))
                    review_request = cur.fetchone()
                    request_payload = (review_request or {}).get("payload") or {}
                    if (request_payload.get("evidence_revision") !=
                            receipt.get("review_evidence_revision") or
                            request_payload.get("evidence_sha256") !=
                            receipt.get("review_evidence_sha256")):
                        raise ObjectiveStateError("matching durable re-review request is required")
                elif "review_generation" in receipt and generation != 1:
                    raise ValueError("initial review receipt generation is invalid")
                event_type = ("conversation.result_published" if generation == 1
                              else "conversation.result_review_published")
                event_key = (f"grace-conversation-result-published:{objective_id}:"
                    f"{receipt['completion_cycle']}" if generation == 1 else
                    f"grace-conversation-result-review-published:{objective_id}:"
                    f"{receipt['completion_cycle']}:{generation}")
                self._event(cur, objective_id, event_type, event_key, "office:grace", receipt)
        return True

    def pending_rejected_work_order_reviews(self, *, limit=10):
        """Return durable conversation-origin verifier rejections for Grace review.

        A saved Grace decision is returned without another model call until its
        source-conversation receipt is acknowledged. Otherwise only the current
        latest rejected attempt is eligible. Earlier verification records remain
        append-only and are never rewritten.
        """
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("rejected work-order review limit must be between 1 and 100")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT o.objective_id,o.assignment_id,o.request,
                    o.acceptance_criteria,o.proposal,o.status,
                    received.payload AS received_payload,received.actor_id AS submitter_id
                FROM grace_objectives o
                JOIN LATERAL (SELECT payload,actor_id FROM grace_objective_events e
                    WHERE e.objective_id=o.objective_id AND e.event_type='objective.received'
                      AND e.payload ? 'origin' ORDER BY e.sequence LIMIT 1) received ON true
                WHERE o.status='WORK_ORDER_CREATED' AND o.assignment_id IS NOT NULL
                ORDER BY o.updated_at,o.objective_id LIMIT %s""", (limit,))
            objectives = cur.fetchall()
        pending = []
        for row in objectives:
            origin_payload = row["received_payload"] or {}
            origin = origin_payload.get("origin") if isinstance(origin_payload, dict) else None
            if (not isinstance(origin, dict) or set(origin) != {"conversation_id", "source_sequence"}
                    or type(origin.get("source_sequence")) is not int):
                continue
            objective_id, assignment_id = row["objective_id"], row["assignment_id"]
            events = self.objective_events(objective_id)
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT vr.verification_id,vr.attempt_id,vr.decision,
                        vr.criteria,vr.evidence_references,vr.verifier_id,
                        vr.verifier_revision,vr.summary,wa.status AS attempt_status,
                        wr.result,wr.result_sha256,a.workflow_step,a.authority_ref
                    FROM verification_records vr
                    JOIN assignments a ON a.id=vr.assignment_id
                    JOIN worker_attempts wa ON wa.attempt_id=vr.attempt_id
                    LEFT JOIN worker_results wr ON wr.attempt_id=vr.attempt_id
                    WHERE vr.assignment_id=%s
                    ORDER BY vr.recorded_at DESC,vr.verification_id DESC LIMIT 1""",
                    (assignment_id,))
                verification = cur.fetchone()
            if (not verification or verification["decision"] != "REJECTED" or
                    verification["attempt_status"] != "succeeded" or
                    verification["result"] is None):
                continue
            verification_id = str(verification["verification_id"])
            if any(event["event_type"] == "conversation.rework_review_published" and
                    event["payload"].get("verification_id") == verification_id for event in events):
                continue
            matching_decisions = [event for event in events if event["event_type"] in {
                "engineering.rework_decided", "engineering.rejection_reviewed"} and
                event["payload"].get("assignment_id") == assignment_id and
                event["payload"].get("verification_id") == verification_id]
            decision_event = matching_decisions[-1] if matching_decisions else None
            if (not verification or verification["decision"] != "REJECTED" or
                    verification["attempt_status"] != "succeeded" or
                    verification["result"] is None):
                continue
            step = self.proposal_step_for_assignment(objective_id, assignment_id)
            # The assignment scheduler writes transition names (for example
            # ``verification_rejected``) into assignments.workflow_step. The
            # durable objective-step/assignment link is the authoritative plan
            # step after execution transitions, so do not compare against that
            # overloaded field here.
            if not step:
                continue
            result = verification["result"]
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (ValueError, TypeError):
                    result = None
            completion = {"decision": "REJECTED", "assignment_id": assignment_id,
                "verification_id": str(verification["verification_id"]),
                "attempt_id": str(verification["attempt_id"]),
                "verifier_id": verification["verifier_id"],
                "verifier_revision": verification["verifier_revision"],
                "criteria": verification["criteria"],
                "evidence_references": list(verification["evidence_references"] or []),
                "summary": verification["summary"],
                "artifact": result if isinstance(result, dict) else {},
                "artifact_sha256": verification["result_sha256"]}
            item = {"objective_id": objective_id, "assignment_id": assignment_id,
                "request": row["request"], "acceptance_criteria": list(row["acceptance_criteria"]),
                "proposal": row["proposal"], "objective_status": row["status"],
                "step_id": step["step_id"], "step_objective": step["objective"],
                "step_acceptance_criteria": list(step["acceptance_criteria"]),
                "submitter_id": row["submitter_id"], "origin": origin,
                "completion": completion}
            if decision_event:
                item["persisted_decision"] = decision_event["payload"]
            pending.append(item)
            if len(pending) >= limit:
                break
        return pending

    def record_rework_decision(self, context, decision, *, credential):
        """Persist Grace's bounded reject/stop decision and governed same-assignment requeue."""
        if (not isinstance(context, dict) or not isinstance(decision, dict) or
                set(decision) != {"decision", "rationale", "correction_instruction",
                                  "criteria_to_address"}):
            raise ObjectiveStateError("rework decision contract is invalid")
        verification_id = context.get("completion", {}).get("verification_id")
        objective_id, assignment_id = context.get("objective_id"), context.get("assignment_id")
        criteria = context.get("step_acceptance_criteria")
        if (not isinstance(verification_id, str) or not isinstance(objective_id, str) or
                not isinstance(assignment_id, str) or not isinstance(criteria, list) or
                not criteria or decision["decision"] not in {
                    "OBJECTIVE_SATISFIED", "REWORK_PROPOSED",
                    "STEWARD_AUTHORIZATION_REQUIRED"} or
                not isinstance(decision["rationale"], str) or
                not decision["rationale"].strip() or len(decision["rationale"]) > 1000 or
                not isinstance(decision["criteria_to_address"], list) or
                len(decision["criteria_to_address"]) > len(criteria) or
                any(not isinstance(item, str) or not item for item in decision["criteria_to_address"]) or
                any(item not in criteria for item in decision["criteria_to_address"]) or
                len(set(decision["criteria_to_address"])) != len(decision["criteria_to_address"])):
            raise ObjectiveStateError("rework decision exceeds the persisted assignment scope")
        instruction = decision["correction_instruction"]
        if decision["decision"] == "REWORK_PROPOSED":
            if (not isinstance(instruction, str) or not instruction.strip() or
                    len(instruction) > 512 or not decision["criteria_to_address"]):
                raise ObjectiveStateError("bounded corrective instructions are required")
        elif instruction is not None or decision["criteria_to_address"]:
            raise ObjectiveStateError("a non-rework decision cannot carry executable instructions")
        payload = {"verification_id": verification_id, "assignment_id": assignment_id,
            "attempt_id": str(context.get("completion", {}).get("attempt_id", "")),
            "decision": decision["decision"], "rationale": decision["rationale"].strip(),
            "correction_instruction": instruction.strip() if isinstance(instruction, str) else None,
            "criteria_to_address": list(decision["criteria_to_address"]),
            "acceptance_criteria_sha256": hashlib.sha256(
                _json(criteria).encode("utf-8")).hexdigest()}
        satisfied = decision["decision"] == "OBJECTIVE_SATISFIED"
        idem = (f"grace-rejection-review:{verification_id}" if satisfied else
                f"grace-rework-decision:{verification_id}")
        event_type = "engineering.rejection_reviewed" if satisfied else "engineering.rework_decided"
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT status,assignment_id FROM grace_objectives "
                    "WHERE objective_id=%s FOR UPDATE", (objective_id,))
                objective = cur.fetchone()
                cur.execute("SELECT state,authority_ref,workflow_step,objective_ref "
                    "FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                assignment = cur.fetchone()
                if (not objective or objective["assignment_id"] != assignment_id or not assignment or
                        assignment["objective_ref"] != objective_id):
                    raise ObjectiveStateError("same objective assignment is not eligible for rework")
                cur.execute("SELECT payload FROM grace_objective_events WHERE objective_id=%s "
                    "AND idempotency_key=%s", (objective_id, idem))
                existing = cur.fetchone()
                if existing:
                    existing_payload = dict(existing["payload"])
                    comparable_existing = {key: value for key, value in existing_payload.items()
                                           if key != "authorization_principal_id"}
                    if comparable_existing != payload:
                        raise ObjectiveStateError("rework decision idempotency conflict")
                    return existing_payload
                if (objective["status"] != "WORK_ORDER_CREATED" or
                        assignment["state"] not in {"rework_required", "ready"}):
                    raise ObjectiveStateError("same objective assignment is not eligible for rework")
                cur.execute("""SELECT vr.decision,vr.attempt_id,wa.status
                    FROM verification_records vr JOIN worker_attempts wa
                      ON wa.attempt_id=vr.attempt_id
                    WHERE vr.verification_id=%s AND vr.assignment_id=%s
                    ORDER BY vr.recorded_at DESC LIMIT 1""", (verification_id, assignment_id))
                verification = cur.fetchone()
                cur.execute("""SELECT verification_id FROM verification_records
                    WHERE assignment_id=%s ORDER BY recorded_at DESC,verification_id DESC LIMIT 1""",
                    (assignment_id,))
                latest = cur.fetchone()
                if (not verification or verification["decision"] != "REJECTED" or
                        verification["status"] != "succeeded" or not latest or
                        str(latest["verification_id"]) != verification_id):
                    raise ObjectiveStateError("current independent rejection is required")
                cur.execute("SELECT step_id,step_objective,acceptance_criteria,status,assignment_id "
                    "FROM grace_objective_steps WHERE objective_id=%s AND assignment_id=%s FOR UPDATE",
                    (objective_id, assignment_id))
                step = cur.fetchone()
                if (not step or step["step_id"] != context.get("step_id") or
                        list(step["acceptance_criteria"]) != criteria or step["status"] != "assigned"):
                    raise ObjectiveStateError("persisted assignment criteria changed")
                principal = self.assignment_intake.authorizer.require(
                    cur, credential, self.assignment_intake.ACTION, assignment["authority_ref"])
                payload["authorization_principal_id"] = principal["principal_id"]
                if decision["decision"] == "REWORK_PROPOSED":
                    # Verification only runs after the worker action has
                    # completed, but the scheduler retains its lease until
                    # expiry. Fence that completed generation now so the
                    # approved rework can be claimed immediately as the next
                    # generation instead of sitting ready behind its own lease.
                    cur.execute("UPDATE assignment_leases SET expires_at=clock_timestamp() "
                        "WHERE assignment_id=%s AND expires_at>clock_timestamp()",
                        (assignment_id,))
                    self.ledger.transition(assignment_id, "ready", context["step_id"],
                        f"grace-rework-ready:{verification_id}", actor_id="office:grace")
                self._event(cur, objective_id, event_type, idem,
                    "office:grace", payload)
                cur.execute("SELECT payload FROM grace_objective_events WHERE objective_id=%s "
                    "AND idempotency_key=%s", (objective_id, idem))
                recorded = cur.fetchone()
                if not recorded or recorded["payload"] != payload:
                    raise ObjectiveStateError("rework decision event could not be confirmed")
        return payload

    def latest_rework_instruction(self, assignment_id):
        """Return the latest persisted bounded rework instruction for this assignment."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT e.payload FROM grace_objective_events e
                WHERE e.event_type='engineering.rework_decided'
                  AND e.payload->>'assignment_id'=%s
                  AND e.payload->>'decision'='REWORK_PROPOSED'
                ORDER BY e.sequence DESC LIMIT 1""", (assignment_id,))
            row = cur.fetchone()
        return row["payload"] if row else None

    def record_rework_review_published(self, objective_id, verification_id, request_id):
        """Acknowledge the idempotent Grace response only after source-chat persistence."""
        if not all(isinstance(value, str) and value for value in
                   (objective_id, verification_id, request_id)):
            raise ValueError("rework response receipt is invalid")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT payload FROM grace_objective_events WHERE objective_id=%s "
                    "AND idempotency_key=ANY(%s)", (objective_id,
                    [f"grace-rework-decision:{verification_id}",
                     f"grace-rejection-review:{verification_id}"]))
                row = cur.fetchone()
                if not row or row["payload"].get("verification_id") != verification_id:
                    raise ObjectiveStateError("durable Grace rejection decision is required before response receipt")
                self._event(cur, objective_id, "conversation.rework_review_published",
                    f"grace-rework-review-published:{verification_id}", "office:grace",
                    {"verification_id": verification_id, "request_id": request_id})
        return True

    def propose_continuation(self, objective_id, parent_assignment_id, step, *, actor_id="office:grace"):
        """Persist a model-proposed step only inside the accepted objective's exact scope."""
        from ..resident_reasoning import PlanProposal, PlanStep
        objective = self.get_objective(objective_id)
        # An initial multi-step proposal is still gated one verified result at a
        # time. Grace's authenticated 80B review must explicitly confirm the
        # already scoped dependent step before CME may dispatch it.
        if (isinstance(step, PlanStep) and objective is not None and
                objective["status"] == "WORK_ORDER_CREATED" and
                objective.get("assignment_id") == parent_assignment_id):
            proposal = objective.get("proposal") if isinstance(objective.get("proposal"), dict) else {}
            raw = next((item for item in proposal.get("steps", [])
                        if isinstance(item, dict) and item.get("step_id") == step.step_id), None)
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT parent.step_id AS parent_step,parent.status AS parent_status,
                        target.step_order,target.status AS target_status,target.step_objective,
                        target.acceptance_criteria,target.depends_on
                    FROM grace_objective_steps parent
                    JOIN grace_objective_steps target ON target.objective_id=parent.objective_id
                    WHERE parent.objective_id=%s AND parent.assignment_id=%s
                      AND target.step_id=%s""", (objective_id, parent_assignment_id, step.step_id))
                link = cur.fetchone()
            exact = (raw is not None and raw.get("objective") == step.objective and
                tuple(raw.get("acceptance_criteria", ())) == tuple(step.acceptance_criteria) and
                tuple(raw.get("depends_on", ())) == tuple(step.depends_on) and
                raw.get("execution_capability", "engineering.codex-cli-artifact.v1") == step.execution_capability and
                tuple(raw.get("authorized_paths", ())) == tuple(step.authorized_paths) and
                tuple(raw.get("test_targets", ())) == tuple(step.test_targets) and
                raw.get("repository_reference") == step.repository_reference and
                raw.get("repository_revision") == step.repository_revision)
            if (link and exact and link["parent_status"] == "verified" and
                    link["target_status"] == "pending" and
                    link["parent_step"] in tuple(link["depends_on"]) and
                    step.step_id in {row.get("step_id") for row in proposal.get("steps", [])
                                     if isinstance(row, dict)}):
                idem = f"grace-step-continuation-review:{objective_id}:{parent_assignment_id}:{step.step_id}"
                existing = any(event["event_type"] == "work_order.continuation_proposed" and
                    event["idempotency_key"] == idem for event in self.objective_events(objective_id))
                if existing:
                    return objective
                with self.ledger.db.transaction():
                    with self.ledger.db.cursor() as cur:
                        self.ledger._set_search_path(cur)
                        cur.execute("SELECT status,assignment_id FROM grace_objectives WHERE objective_id=%s FOR UPDATE",
                                    (objective_id,))
                        locked = cur.fetchone()
                        if (not locked or locked["status"] != "WORK_ORDER_CREATED" or
                                locked["assignment_id"] != parent_assignment_id):
                            raise ObjectiveStateError("objective changed before reviewed continuation")
                        self._event(cur, objective_id, "work_order.continuation_proposed", idem,
                            actor_id, {"parent_assignment_id": parent_assignment_id,
                                "step_id": step.step_id,"step_order": link["step_order"],
                                "acceptance_criteria": list(step.acceptance_criteria),
                                "repository_reference": step.repository_reference,
                                "repository_revision": step.repository_revision,
                                "authorization": "original_scope_exact_grant_rechecked_at_dispatch",
                                "review_type": "verified_predecessor_result"})
                return self.get_objective(objective_id)
        objective = self.get_objective(objective_id)
        if (isinstance(step, PlanStep) and objective is not None and
                objective["status"] == "WORK_ORDER_CREATED"):
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT step_objective,acceptance_criteria,depends_on
                    FROM grace_objective_steps WHERE objective_id=%s AND step_id=%s""",
                    (objective_id, step.step_id))
                prior = cur.fetchone()
            if (prior and prior["step_objective"] == step.objective and
                    tuple(prior["acceptance_criteria"]) == tuple(step.acceptance_criteria) and
                    tuple(prior["depends_on"]) == tuple(step.depends_on) and
                    any(event["event_type"] == "work_order.continuation_proposed" and
                        event["payload"].get("parent_assignment_id") == parent_assignment_id and
                        event["payload"].get("step_id") == step.step_id and
                        event["payload"].get("repository_reference") == step.repository_reference and
                        event["payload"].get("repository_revision") == step.repository_revision
                        for event in self.objective_events(objective_id))):
                return objective
        if (not isinstance(step, PlanStep) or objective is None or
                objective["status"] != "COMPLETED" or
                objective.get("assignment_id") != parent_assignment_id or
                not objective.get("proposal") or not objective.get("acceptance_criteria")):
            raise ObjectiveStateError("a completed objective and its latest verified assignment are required")
        prior_steps = objective["proposal"].get("steps", [])
        prior_ids = {item.get("step_id") for item in prior_steps if isinstance(item, dict)}
        accepted = set(objective["acceptance_criteria"])
        if (len(prior_steps) >= 20 or step.step_id in prior_ids or
                not set(step.depends_on) <= prior_ids or
                not set(step.acceptance_criteria) <= accepted):
            raise ObjectiveStateError("continuation exceeds the original accepted scope")
        authorized_paths = {path for item in prior_steps if isinstance(item, dict)
                            for path in item.get("authorized_paths", ())}
        if step.execution_capability == "engineering.codex-cli-source-change.v1" and (
                not set(step.authorized_paths) <= authorized_paths or
                not set(step.test_targets) <= set(step.authorized_paths) or
                not any(item.get("execution_capability") ==
                        "engineering.codex-cli-source-change.v1" and
                        item.get("repository_reference") == step.repository_reference and
                        item.get("repository_revision") == step.repository_revision
                        for item in prior_steps if isinstance(item, dict))):
            raise ObjectiveStateError("continuation exceeds the originally approved file scope")
        continuation = PlanStep(step.step_id, step.objective, tuple(step.acceptance_criteria),
                                tuple(step.depends_on), step.execution_capability,
                                tuple(step.authorized_paths), tuple(step.test_targets),
                                step.repository_reference, step.repository_revision)
        merged = dict(objective["proposal"])
        merged["steps"] = [*prior_steps, asdict(continuation)]
        # Reuse the public typed contract to validate unique IDs and acyclic
        # earlier-step dependencies before durable state is changed.
        PlanProposal(merged["summary"], tuple(
            PlanStep(item["step_id"], item["objective"],
                     tuple(item["acceptance_criteria"]), tuple(item.get("depends_on", ())),
                     item.get("execution_capability", "engineering.codex-cli-artifact.v1"),
                     tuple(item.get("authorized_paths", ())),
                     tuple(item.get("test_targets", ())),
                     item.get("repository_reference"), item.get("repository_revision"))
            for item in merged["steps"]), 0)
        step_order = len(prior_steps) + 1
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT status,assignment_id,proposal FROM grace_objectives
                    WHERE objective_id=%s FOR UPDATE""", (objective_id,))
                locked = cur.fetchone()
                if (not locked or locked["status"] != "COMPLETED" or
                        locked["assignment_id"] != parent_assignment_id):
                    raise ObjectiveStateError("objective changed before continuation proposal")
                cur.execute("""INSERT INTO grace_objective_steps
                    (objective_id,step_id,step_order,step_objective,acceptance_criteria,
                     depends_on,status)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,'pending')""",
                    (objective_id, continuation.step_id, step_order, continuation.objective,
                     _json(list(continuation.acceptance_criteria)),
                     _json(list(continuation.depends_on))))
                cur.execute("""UPDATE grace_objectives SET status='WORK_ORDER_CREATED',
                    proposal=%s::jsonb,revision=revision+1,updated_at=clock_timestamp()
                    WHERE objective_id=%s AND status='COMPLETED'""",
                    (_json(merged), objective_id))
                if cur.rowcount != 1:
                    raise ObjectiveStateError("objective continuation raced with another update")
                self._event(cur, objective_id, "work_order.continuation_proposed",
                    f"grace-work-order-continuation:{objective_id}:{continuation.step_id}",
                    actor_id, {"parent_assignment_id": parent_assignment_id,
                        "step_id": continuation.step_id,"step_order": step_order,
                        "acceptance_criteria": list(continuation.acceptance_criteria),
                        "authorization": "original_scope_exact_grant_rechecked_at_dispatch"})
        return self.get_objective(objective_id)
