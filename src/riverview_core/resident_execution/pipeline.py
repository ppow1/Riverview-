# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/pipeline.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.8
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
                         scope_ref, credential=None, principal=None, origin=None):
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
        if len(proposal.steps) != 1:
            raise ObjectiveStateError(
                "this execution adapter accepts exactly one proposal step; multi-step fanout is not yet implemented")
        requested = set(objective["acceptance_criteria"])
        proposed = {criterion for step in proposal.steps
                    for criterion in step.acceptance_criteria}
        if not requested.issubset(proposed):
            raise ObjectiveStateError("proposal omits one or more human acceptance criteria")
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
                self._event(cur, objective_id, "work_order.proposed",
                            f"grace-work-order-proposed:{objective_id}", actor_id,
                            {"proposal_sha256": hashlib.sha256(_json(document).encode()).hexdigest(),
                             "step_ids": [step.step_id for step in proposal.steps],
                             "approved": False})
        return self.get_objective(objective_id)

    def authorize_and_dispatch(self, objective_id, assignment_id, *, credential,
                               authority_ref, idempotency_key):
        objective = self.get_objective(objective_id)
        if (objective is None or objective["status"] not in {"PROPOSED", "WORK_ORDER_CREATED"}
                or objective["scope_ref"] != authority_ref or not objective["proposal"]):
            raise ObjectiveStateError("grounded proposal and matching exact authority scope are required")
        step = objective["proposal"]["steps"][0]
        if not objective["evidence"] or objective["evidence"]["status"] != "VERIFIED":
            raise ObjectiveStateError("verified evidence is required for dispatch")
        try:
            # Both adapters share this ledger connection. The nested intake
            # transaction is a savepoint, so assignment + event and objective
            # linkage commit or roll back as one unit.
            with self.ledger.db.transaction():
                with self.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    assignment = self.assignment_intake.create(
                        assignment_id, "engineering", idempotency_key,
                        credential=credential, authority_ref=authority_ref,
                        objective_ref=objective_id,
                        contract_ref="repo://riverview/worker-adapter-contract.v1",
                        workflow_id=self.WORKFLOW_ID,
                        workflow_step=step["step_id"], correlation_id=objective_id)
                    cur.execute("""SELECT actor_id FROM events WHERE assignment_id=%s
                        AND event_type='assignment.created' ORDER BY seq LIMIT 1""",
                        (assignment_id,))
                    created_event = cur.fetchone()
                    if not created_event:
                        raise ObjectiveStateError("assignment creation event is missing")
                    cur.execute("""UPDATE grace_objectives SET status='WORK_ORDER_CREATED',
                        assignment_id=%s,revision=revision+1,updated_at=clock_timestamp()
                        WHERE objective_id=%s AND status IN ('PROPOSED','WORK_ORDER_CREATED')
                          AND (assignment_id IS NULL OR assignment_id=%s)""",
                        (assignment_id, objective_id, assignment_id))
                    if cur.rowcount != 1:
                        raise ObjectiveStateError("objective assignment link conflicts with existing state")
                    self._event(cur, objective_id, "work_order.dispatched",
                                f"grace-work-order-dispatched:{objective_id}",
                                created_event["actor_id"],
                                {"assignment_id": assignment_id,
                                 "workflow_step": step["step_id"]})
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
        payload = {"assignment_id": assignment_id, "decision": verification["decision"],
                   "verifier_revision": verification["verifier_revision"],
                   "evidence_references": list(verification["evidence_references"])}
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT wr.result FROM worker_attempts wa
                JOIN worker_results wr USING(attempt_id)
                WHERE wa.assignment_id=%s AND wa.status='succeeded'
                ORDER BY wa.started_at DESC LIMIT 1""", (assignment_id,))
            artifact_row = cur.fetchone()
        artifact = artifact_row["result"] if artifact_row else None
        if isinstance(artifact, dict):
            payload["artifact"] = {key: artifact[key] for key in
                ("artifact_name", "artifact_path", "artifact_sha256", "artifact_bytes")
                if key in artifact}
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE grace_objectives SET status='COMPLETED',revision=revision+1,
                    updated_at=clock_timestamp() WHERE objective_id=%s
                    AND status='WORK_ORDER_CREATED' AND assignment_id=%s""",
                    (objective_id, assignment_id))
                if cur.rowcount != 1:
                    raise ObjectiveStateError("objective completion raced with another update")
                self._event(cur, objective_id, "objective.completed",
                            f"grace-objective-completed:{objective_id}", "verifier:independent",
                            payload)
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
        """Return completed conversation-origin objectives not yet returned to chat."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("conversation result limit must be between 1 and 100")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT o.objective_id FROM grace_objectives o
                WHERE o.status='COMPLETED'
                  AND EXISTS (SELECT 1 FROM grace_objective_events r
                    WHERE r.objective_id=o.objective_id AND r.event_type='objective.received'
                      AND r.payload ? 'origin')
                  AND EXISTS (SELECT 1 FROM grace_objective_events c
                    WHERE c.objective_id=o.objective_id AND c.event_type='objective.completed')
                  AND NOT EXISTS (SELECT 1 FROM grace_objective_events p
                    WHERE p.objective_id=o.objective_id
                      AND p.event_type='conversation.result_published')
                ORDER BY o.updated_at,o.objective_id LIMIT %s""", (limit,))
            objective_ids = [row["objective_id"] for row in cur.fetchall()]
        results = []
        for objective_id in objective_ids:
            objective = self.get_objective(objective_id)
            events = self.objective_events(objective_id)
            received = next((event for event in events
                if event["event_type"] == "objective.received"), None)
            completed = next((event for event in reversed(events)
                if event["event_type"] == "objective.completed"), None)
            origin = ((received or {}).get("payload") or {}).get("origin")
            completion = (completed or {}).get("payload")
            if (not objective or not isinstance(origin, dict)
                    or not isinstance(completion, dict)
                    or not objective.get("assignment_id")):
                continue
            results.append({"objective_id": objective_id,
                "assignment_id": objective["assignment_id"],
                "request": objective["request"],
                "acceptance_criteria": list(objective["acceptance_criteria"]),
                "proposal": objective.get("proposal"),
                "submitter_id": received.get("actor_id"),
                "origin": origin,
                "completion": completion})
        return results

    def record_conversation_result_published(self, objective_id, receipt):
        """Acknowledge a durable chat reply after the conversation insert succeeds."""
        if (not isinstance(receipt, dict) or set(receipt) != {
                "request_id", "provider_id", "served_model", "implementation_id"}
                or any(not isinstance(value, str) or not value for value in receipt.values())):
            raise ValueError("conversation result receipt is invalid")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT status FROM grace_objectives
                    WHERE objective_id=%s FOR UPDATE""", (objective_id,))
                row = cur.fetchone()
                if not row or row["status"] != "COMPLETED":
                    raise ObjectiveStateError("verified completion is required before chat return")
                self._event(cur, objective_id, "conversation.result_published",
                    f"grace-conversation-result-published:{objective_id}",
                    "office:grace", receipt)
        return True
