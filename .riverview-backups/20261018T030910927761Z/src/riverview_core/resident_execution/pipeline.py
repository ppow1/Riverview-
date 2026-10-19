# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/pipeline.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.1.6
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Persist immutable source-target binding with each authorized dispatch and preserve target identity across dependent steps.
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
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Persist immutable proposal revision, approval, source and exact-grant correlation on objective intake
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

    def record_proposal(self, objective_id, proposal: PlanProposal, *, actor_id="resident:grace"):
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
                if (any(not any(re.search(r"(?<![A-Za-z0-9._/-])" + re.escape(path) +
                                          r"(?![A-Za-z0-9_/-]|\.(?=[A-Za-z0-9._/-]))", text)
                                    for text in approved_source_scope)
                        for path in step.authorized_paths)):
                    raise ObjectiveStateError(
                        "source-change path is absent from the Steward-approved objective scope")
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
        return self.get_objective(objective_id)

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
            cur.execute("""SELECT decision,verifier_revision,evidence_references
                FROM verification_records WHERE assignment_id=%s AND decision='ACCEPTED'
                ORDER BY verification_id DESC LIMIT 1""", (assignment_id,))
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
                cur.execute("""SELECT bool_and(status='verified') AS complete
                    FROM grace_objective_steps WHERE objective_id=%s""", (objective_id,))
                all_steps = bool(cur.fetchone()["complete"])
        completion_cycle = step_row["step_order"]
        payload = {"assignment_id": assignment_id, "step_id": step_row["step_id"],
                   "completion_cycle": completion_cycle,
                   "decision": verification["decision"],
                   "verifier_revision": verification["verifier_revision"],
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
                "patch_bytes", "test_status", "repository_reference",
                "repository_revision")
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
        """Return verified conversation-origin steps not yet reviewed by Grace."""
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
                      AND NOT EXISTS (SELECT 1 FROM grace_objective_events p
                        WHERE p.objective_id=o.objective_id
                          AND p.event_type='conversation.result_published'
                          AND p.payload->>'completion_cycle'=e.payload->>'completion_cycle')
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
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT step_id,status FROM grace_objective_steps
                    WHERE objective_id=%s ORDER BY step_order""", (objective_id,))
                step_progress = [{"step_id": row["step_id"], "status": row["status"]}
                                 for row in cur.fetchall()]
            results.append({"objective_id": objective_id,
                "assignment_id": completion["assignment_id"],
                "request": objective["request"],
                "acceptance_criteria": list(objective["acceptance_criteria"]),
                "proposal": completion.get("proposal", objective.get("proposal")),
                "objective_status": objective["status"],
                "step_progress": step_progress,
                "submitter_id": received.get("actor_id"),
                "origin": origin,
                "completion_cycle": int(objective_row["completion_cycle"] or 1),
                "completion": completion})
        return results

    def record_conversation_result_published(self, objective_id, receipt):
        """Acknowledge a durable chat reply after the conversation insert succeeds."""
        if (not isinstance(receipt, dict) or set(receipt) != {
                "request_id", "provider_id", "served_model", "implementation_id",
                "completion_cycle"}
                or any(not isinstance(value, str) or not value for value in receipt.values())
                or not receipt["completion_cycle"].isdigit()):
            raise ValueError("conversation result receipt is invalid")
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
                self._event(cur, objective_id, "conversation.result_published",
                    f"grace-conversation-result-published:{objective_id}:{receipt['completion_cycle']}",
                    "office:grace", receipt)
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
