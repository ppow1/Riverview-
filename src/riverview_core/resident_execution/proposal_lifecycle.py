# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/proposal_lifecycle.py
# Component: INSTITUTIONAL-PROPOSALS
# Revision: 1.0.2
# Purpose: Bridge exact Steward proposal decisions to existing authorized objective intake
# Execution Model: Request-driven; recoverable through durable proposal and objective events
# Observability: Proposal events, objective events, assignment links, verification records
# Dependencies: ProposalRegistry; GraceExecutionPipeline; exact objective.submit grant
# Authority: Authenticated Steward account or Comms5 ingress for decision; pipeline exact grants for intake/dispatch
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Initial lifecycle bridge
# Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Permit current Comms5 Steward-authored provenance during approved proposal promotion.
# Contracts: docs/components/INSTITUTIONAL_PROPOSALS.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Proposal-to-existing-objective intake bridge; never dispatches workers itself."""

from __future__ import annotations

import hashlib
import json
import re
from uuid import NAMESPACE_URL, uuid5

from .pipeline import ObjectiveNotAuthorized, ObjectiveStateError
from ..institutional_authority.grants import InstitutionalPrincipal
from .proposals import ProposalConflict


_APPROVE_COMMAND = re.compile(
    r"(?i)grace,?\s+approve\s+proposal\s+(proposal:[0-9a-f-]{36})\s+revision\s+([1-9][0-9]{0,5})\s+for\s+(.+?)\.?$")
_PROMOTE_COMMAND = re.compile(
    r"(?i)grace,?\s+create\s+engineering\s+work\s+order\s+from\s+proposal\s+(proposal:[0-9a-f-]{36})\s+revision\s+([1-9][0-9]{0,5})\.?$")
_OTHER_DECISION_COMMAND = re.compile(
    r"(?i)grace,?\s+(request changes to|defer|reject)\s+proposal\s+(proposal:[0-9a-f-]{36})\s+revision\s+([1-9][0-9]{0,5})(?:\s+because\s+(.+))?\.?$")


def parse_steward_command(text):
    """Parse only explicit revision-bound commands; ordinary agreement is inert."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if match := _APPROVE_COMMAND.fullmatch(text):
        proposal_id, revision, purpose = match.groups()
        return {"action": "decision", "proposal_id": proposal_id,
            "revision": int(revision), "decision": "APPROVE",
            "approved_purpose": purpose.strip().rstrip("."),
            "reason": "Explicit authenticated conversational Steward decision"}
    if match := _PROMOTE_COMMAND.fullmatch(text):
        proposal_id, revision = match.groups()
        return {"action": "promote", "proposal_id": proposal_id,
            "revision": int(revision)}
    if match := _OTHER_DECISION_COMMAND.fullmatch(text):
        phrase, proposal_id, revision, reason = match.groups()
        decision = {"request changes to": "REQUEST_CHANGES", "defer": "DEFER",
                    "reject": "REJECT"}[phrase.casefold()]
        return {"action": "decision", "proposal_id": proposal_id,
            "revision": int(revision), "decision": decision,
            "reason": (reason or "Explicit authenticated conversational Steward decision").strip().rstrip(".")}
    return None


class ProposalLifecycle:
    """Coordinates proposal records with the established objective pipeline."""

    def __init__(self, registry, pipeline):
        if registry is None or pipeline is None:
            raise TypeError("proposal registry and objective pipeline are required")
        self.registry = registry
        self.pipeline = pipeline

    @staticmethod
    def objective_id(proposal_id, revision):
        stable = uuid5(NAMESPACE_URL, f"riverview:proposal-work-order:{proposal_id}:r{revision}")
        return f"objective:proposal:{stable}:r{revision}"

    def decide(self, proposal_id, revision, *, decision, actor_id, reason,
               idempotency_key, content_sha256, approved_purpose=None,
               accepted_conditions=(), authority_reference):
        """Record a decision only after the HTTP/account boundary authenticates Steward."""
        if not isinstance(actor_id, str) or not actor_id.startswith("steward:"):
            raise PermissionError("a Steward institutional principal is required")
        valid_account_session = (isinstance(authority_reference, str)
            and authority_reference.startswith("account-auth-session:"))
        valid_comms5_attestation = authority_reference == "comms5-ingress:steward"
        if not (valid_account_session or valid_comms5_attestation):
            raise PermissionError("authenticated Steward transport provenance is required")
        return self.registry.steward_decision(proposal_id, revision,
            decision=decision, actor_id=actor_id,
            authority_reference=authority_reference, reason=reason,
            idempotency_key=idempotency_key,
            expected_content_sha256=content_sha256,
            approved_purpose=approved_purpose,
            accepted_conditions=accepted_conditions)

    @staticmethod
    def _objective_request(revision, *, approved_purpose, privacy_classification,
                           retention_policy):
        return (f"{revision['title']}\n\n{revision['summary']}\n\n"
                f"Objective: {revision['objective']}\nScope: {revision['scope']}\n"
                f"Approach: {revision['proposed_approach']}\n"
                f"Approved purpose: {approved_purpose}\n"
                f"Privacy classification: {privacy_classification}\n"
                f"Retention policy: {retention_policy}\n"
                f"Constraints: {'; '.join(revision['constraints'])}")

    def promote(self, proposal_id, revision, *, actor_id):
        """Create/reuse an objective via existing objective.submit, never assignment creation."""
        if not isinstance(actor_id, str) or not actor_id.startswith("steward:"):
            raise PermissionError("a Steward institutional principal is required")
        record = self.registry.get(proposal_id, revision=revision)
        proposal = record["proposal"]
        rev = record["revision"]
        if (proposal["current_revision"] != revision or proposal["lifecycle_status"] != "APPROVED"
                or rev["lifecycle_status"] != "APPROVED"):
            raise ProposalConflict("only the current approved proposal revision can be promoted")
        decision = next((event for event in reversed(record["events"])
            if event["event_type"] == "proposal.steward_decision"
            and event["revision"] == revision and event["payload"].get("to") == "APPROVED"), None)
        if decision is None or decision["payload"].get("content_sha256") != rev["content_sha256"]:
            raise ProposalConflict("proposal revision has no matching Steward approval")
        if not decision["payload"].get("approved_purpose"):
            raise ProposalConflict("approved purpose is missing")
        criteria = list(rev["acceptance_criteria"])
        if not criteria:
            raise ProposalConflict("approved proposal has no acceptance criteria")
        objective_id = self.objective_id(proposal_id, revision)
        approved_purpose = decision["payload"]["approved_purpose"]
        request = self._objective_request(rev, approved_purpose=approved_purpose,
            privacy_classification=proposal["privacy_classification"],
            retention_policy=proposal["retention_policy"])
        # This exact grant authorizes intake only. Assignment dispatch remains a
        # separate capability check in Grace's existing persistent execution service.
        intake_authority = self.pipeline.authorize_objective_submission(
            actor_id, "work-order:engineering")
        reference = {"proposal_id": proposal_id, "revision": revision,
            "content_sha256": rev["content_sha256"],
            "approval_event_key": decision["idempotency_key"],
            "source_references": rev["source_references"],
            "privacy_classification": proposal["privacy_classification"],
            "retention_policy": proposal["retention_policy"],
            "approved_purpose": approved_purpose,
            "objective_submit_grant_id": intake_authority["grant_id"]}
        # Record the durable intake request only after exact objective.submit passes.
        reservation = self.registry.reserve_work_order_intake(proposal_id, revision,
            objective_id, actor_id=actor_id,
            authority_reference=f"objective.submit-grant:{intake_authority['grant_id']}")
        existing = self.pipeline.get_objective(objective_id)
        if existing is not None:
            persisted_ref = self.pipeline.objective_proposal_reference(objective_id)
            if (existing["submitter_id"] != actor_id or existing["scope_ref"] != "work-order:engineering"
                    or existing["request"] != request
                    or list(existing["acceptance_criteria"]) != criteria
                    or persisted_ref != reference):
                raise ProposalConflict("deterministic objective identity contains conflicting provenance")
            objective = existing
            reused = True
        else:
            try:
                objective = self.pipeline.submit_objective(objective_id, request, criteria,
                    principal=InstitutionalPrincipal(actor_id), scope_ref="work-order:engineering",
                    proposal_reference=reference)
                reused = False
            except ObjectiveStateError:
                # A same-request concurrent promotion may have committed; only reuse it after
                # validating every immutable field and the source proposal correlation.
                objective = self.pipeline.get_objective(objective_id)
                if objective is None:
                    raise
                persisted_ref = self.pipeline.objective_proposal_reference(objective_id)
                if (objective["submitter_id"] != actor_id or objective["scope_ref"] != "work-order:engineering"
                        or objective["request"] != request
                        or list(objective["acceptance_criteria"]) != criteria
                        or persisted_ref != reference):
                    raise ProposalConflict("concurrent objective intake has conflicting provenance") from None
                reused = True
        if objective["status"] in {"RECEIVED", "WAITING_FOR_EVIDENCE"}:
            try:
                objective = self.pipeline.ground_objective(objective_id)
            except ObjectiveStateError:
                # The existing pipeline records WAITING_FOR_EVIDENCE; approval and intake
                # remain durable and the existing service can retry grounding.
                objective = self.pipeline.get_objective(objective_id)
        return {"schema_version": "rv.proposal.work-order.v1",
            "status": objective["status"], "proposal_id": proposal_id,
            "proposal_revision": revision, "objective_id": objective_id,
            "assignment_id": objective.get("assignment_id"),
            "work_order_dispatched": bool(objective.get("assignment_id")),
            "execution_state": self._execution_state(objective),
            "missing_prerequisite": None,
            "reused": reused, "intake_request_created": reservation["created"],
            "source_sha256": objective.get("source_sha256")}

    def status(self, proposal_id, revision):
        record = self.registry.get(proposal_id, revision=revision)
        objective_ids = [event["payload"].get("objective_id") for event in record["events"]
            if event["event_type"] == "proposal.work_order_requested"
            and event["revision"] == revision]
        work_orders = []
        for objective_id in dict.fromkeys(objective_ids):
            objective = self.pipeline.get_objective(objective_id)
            if objective is None:
                work_orders.append({"objective_id": objective_id, "status": "intake_pending"})
                continue
            assignment = (self.pipeline.ledger.get(objective["assignment_id"])
                          if objective.get("assignment_id") else None)
            failure = self._latest_dispatch_failure(objective_id)
            work_orders.append({"objective_id": objective_id,
                "assignment_id": objective.get("assignment_id"),
                "objective_status": objective.get("status"),
                "assignment_status": assignment.get("state") if assignment else None,
                "execution_state": self._execution_state(objective),
                "missing_prerequisite": ("assignment.create" if failure == "ObjectiveNotAuthorized" else None),
                "last_dispatch_failure": failure,
                "assignment": assignment})
        return {"proposal": record, "work_orders": work_orders}

    def _latest_dispatch_failure(self, objective_id):
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT payload->>'failure_type' AS failure_type
                FROM grace_objective_events WHERE objective_id=%s
                  AND event_type='execution.dispatch_failed'
                ORDER BY sequence DESC LIMIT 1""", (objective_id,))
            row = cur.fetchone()
        return row["failure_type"] if row else None

    @staticmethod
    def _execution_state(objective):
        return {"RECEIVED": "grounding_pending", "WAITING_FOR_EVIDENCE": "waiting_for_evidence",
            "GROUNDED": "awaiting_grace_planning", "PROPOSED": "awaiting_authorized_dispatch",
            "WORK_ORDER_CREATED": "dispatched", "COMPLETED": "verified_complete",
            "FAILED": "failed", "CANCELLED": "cancelled"}.get(
                objective.get("status"), "unknown")

    def reconcile_links(self, limit=50):
        """Recover missing proposal/assignment links after restart from durable objective events."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("invalid reconciliation limit")
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT o.objective_id,o.submitter_id,o.status AS objective_status,
                    s.assignment_id FROM grace_objective_events e
                JOIN grace_objectives o ON o.objective_id=e.objective_id
                LEFT JOIN grace_objective_steps s ON s.objective_id=o.objective_id
                WHERE e.event_type='objective.received'
                  AND e.payload ? 'proposal_reference' AND s.assignment_id IS NOT NULL
                ORDER BY o.updated_at DESC,s.step_order LIMIT %s""", (limit,))
            rows = cur.fetchall()
        linked = 0
        for row in rows:
            reference = self.pipeline.objective_proposal_reference(row["objective_id"])
            if not reference:
                continue
            assignment = self.pipeline.ledger.get(row["assignment_id"])
            if assignment is None:
                continue
            record = self.registry.get(reference["proposal_id"], revision=reference["revision"])
            approval = next((event for event in reversed(record["events"])
                if event["event_type"] == "proposal.steward_decision"
                and event["revision"] == reference["revision"]
                and event["payload"].get("to") == "APPROVED"), None)
            if (approval is None or approval["payload"].get("content_sha256")
                    != reference["content_sha256"]):
                raise ProposalConflict("approved proposal provenance changed before execution reconciliation")
            approved_purpose = reference.get("approved_purpose")
            if not approved_purpose:
                record = self.registry.get(reference["proposal_id"], revision=reference["revision"])
                approved = next((event for event in reversed(record["events"])
                    if event["event_type"] == "proposal.steward_decision"
                    and event["revision"] == reference["revision"]
                    and event["payload"].get("to") == "APPROVED"), None)
                if not approved or approved["payload"].get("content_sha256") != reference["content_sha256"]:
                    raise ProposalConflict("approved proposal provenance changed before execution reconciliation")
                approved_purpose = approved["payload"].get("approved_purpose")
            self.registry.link_work_order(reference["proposal_id"], reference["revision"],
                objective_id=row["objective_id"], assignment_id=row["assignment_id"],
                approved_purpose=approved_purpose, actor_id=row["submitter_id"],
                authority_reference=(f"objective.submit-grant:{reference['objective_submit_grant_id']}"))
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""SELECT wr.result FROM worker_results wr
                    JOIN worker_attempts wa USING(attempt_id)
                    WHERE wa.assignment_id=%s AND wa.status='succeeded'
                    ORDER BY wa.started_at DESC LIMIT 1""", (row["assignment_id"],))
                result_row = cur.fetchone()
                cur.execute("""SELECT decision,verifier_id,verifier_revision,
                    evidence_references,recorded_at FROM verification_records
                    WHERE assignment_id=%s ORDER BY verification_id DESC LIMIT 1""",
                    (row["assignment_id"],))
                verification = cur.fetchone()
            worker_result = result_row["result"] if result_row else {}
            evidence = {"objective_status": row["objective_status"],
                "assignment_status": assignment.get("state")}
            if isinstance(worker_result, dict):
                if isinstance(worker_result.get("artifact_path"), str):
                    evidence["artifact_path"] = worker_result["artifact_path"][:1024]
                if isinstance(worker_result.get("artifact_sha256"), str):
                    evidence["artifact_sha256"] = worker_result["artifact_sha256"]
            if verification:
                evidence.update({"verification_decision": verification["decision"],
                    "verifier_id": verification["verifier_id"],
                    "verifier_revision": verification["verifier_revision"],
                    "verification_evidence_references": verification["evidence_references"],
                    "recorded_at": verification["recorded_at"].isoformat()})
            digest = hashlib.sha256(json.dumps(evidence, sort_keys=True,
                separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
            self.registry.record_execution_update(reference["proposal_id"], reference["revision"],
                objective_id=row["objective_id"], assignment_id=row["assignment_id"],
                status=str(assignment.get("state", "unknown")), evidence=evidence,
                idempotency_key=f"proposal-execution:{reference['proposal_id']}:{reference['revision']}:{digest}")
            linked += 1
        return linked
