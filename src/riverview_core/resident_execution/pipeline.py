# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/pipeline.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.1.37
# Changed: 2026-10-25 UTC | RV-GRACE-REWORK-CONTROLLER-AUTH-UUID-20261025 | Serialize the registered authorization UUID as text in append-only controller evidence.
# Changed: 2026-10-24 UTC | RV-GRACE-PIN-RUNTIME-RELEASE-ID-20261024 | Pin retry-hold release identity at pipeline construction so an old process cannot adopt a newly switched symlink.
# Changed: 2026-10-23 UTC | RV-GRACE-APPROVED-PROMOTION-LIFECYCLE-BINDING-20261023 | Bind the exact approved promotion criterion only to matching durable proposal and objective evidence.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Persist and revalidate typed ComfyUI requests through durable assignment dispatch.
# Changed: 2026-10-23 UTC | RV-DASHBOARD-GROUNDED-OBJECTIVE-CANCEL-20261023 | Preserve deployed exact-grant grounded objective cancellation and durable audit evidence.
# Changed: 2026-10-22 UTC | RV-GRACE-DURABLE-COMPLETION-001 | Complete from durable accepted step state and make duplicate completion calls idempotent; conversation reviews are post-completion delivery only.
# Changed: 2026-10-22 UTC | RV-W4-PR216-REVIEW-FOLLOWUP | Serialize grounding failure event persistence and make attempt replay idempotent.
# Changed: 2026-10-22 UTC | RV-W4-GRACE-ACTIONABLE-DIAGNOSTICS-20261022 | Persist sanitized, correlated grounding failure details in durable objective events.
# Changed: 2026-10-22 UTC | RV-W4-GRACE-ARTIFACT-STEP-CRITERIA-20261022 | Permit artifact-specific step checks only when retained in the same artifact contract.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-RECONCILIATION | Add exact-objective audited removal of one misclassified structural heading.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-OPTIONAL-CRITERIA-20261021 | Persist Grace-derived criteria as the objective's validated effective list.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-CLASSIFICATION-20261021 | Require artifact destinations to be named in the authorized objective scope
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Require unique criterion ownership and conversation origin for publication lifecycle evidence
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Persist lifecycle criteria separately from Engineering steps and bind them to durable workflow evidence
# Changed: 2026-10-20 UTC | RV-GRACE-GROUNDED-OBJECTIVE-FAIR-QUEUE-001 | Order grounded reasoning candidates by their most recent persisted attempt, with never-attempted objectives first.
# Changed: 2026-10-20 UTC | RV-GRACE-ACCEPTED-STEP-REWORK-001 | Advance independently accepted steps through persisted dependencies and bound rejected-step retries with durable escalation pending.
# Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Integrate PostgreSQL qualification and active production regression coverage.
# Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Fail closed on globally reused event keys and select due review generations before applying the batch limit.
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
# Changed: 2026-10-19 UTC | RV-GRACE-REREVIEW-PG-QUALIFICATION | Normalize integer and string completion-cycle receipt values
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Bind exact per-step artifact contracts into durable dispatch events
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
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import NAMESPACE_URL, uuid4, uuid5

from ..assignment_intake import AuthorizedAssignmentIntake, AssignmentIntakeDenied
from ..resident_reasoning import PlanProposal, lifecycle_evidence_event
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
    MAX_GOVERNED_REWORK_ATTEMPTS = 3

    def __init__(self, ledger, authorizer, assignment_intake, knowledge):
        if (not isinstance(assignment_intake, AuthorizedAssignmentIntake) or
                assignment_intake.ledger is not ledger):
            raise TypeError("AuthorizedAssignmentIntake is required")
        self.ledger = ledger
        self.authorizer = authorizer
        self.assignment_intake = assignment_intake
        self.knowledge = knowledge
        self._runtime_release_id = self._discover_runtime_release_id()

    def _event(self, cur, objective_id, event_type, idem, actor_id, payload):
        cur.execute("""INSERT INTO grace_objective_events
            (objective_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT (idempotency_key) DO NOTHING""",
            (objective_id, event_type, idem, actor_id, _json(payload)))

    @staticmethod
    def _discover_runtime_release_id():
        """Read the immutable release identity once when the pipeline is constructed."""
        try:
            commit = (Path(__file__).resolve().parents[3] / "SOURCE_COMMIT").read_text(
                encoding="ascii").strip()
        except (OSError, UnicodeError):
            return "development"
        return commit if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit) else "unpackaged"

    def runtime_release_id(self):
        """Return the startup-pinned release so runtime pointer changes cannot affect this process."""
        return self._runtime_release_id

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

    def reconcile_misclassified_requirements_heading(
            self, objective_id, *, expected_revision, credential, reason):
        """Remove only the previously approved structural heading from one objective."""
        target_id = "objective:grace-conversation:8416c5da-bde5-5294-9276-c0163418fae1"
        if (objective_id != target_id or expected_revision != 2 or
                not isinstance(credential, str) or len(credential) < 32 or
                not isinstance(reason, str) or
                not reason.strip() or len(reason.strip()) > 500):
            raise ObjectiveStateError("criteria reconciliation request is outside its approved scope")
        db = self.ledger.db
        try:
            with db.transaction():
                with db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    try:
                        grant = self.authorizer.require(
                            cur, credential, "objective.criteria.reconcile", objective_id)
                    except Exception as exc:
                        if type(exc).__name__ in {"GrantDenied", "GrantCheckUnavailable"}:
                            raise ObjectiveNotAuthorized(
                                "objective.criteria.reconcile is not authorized") from None
                        raise
                    actor_id = grant["principal_id"]
                    cur.execute("""SELECT objective_id,request,scope_ref,submitter_id,
                        acceptance_criteria,status,evidence,proposal,assignment_id,revision
                        FROM grace_objectives WHERE objective_id=%s FOR UPDATE""",
                        (objective_id,))
                    row = cur.fetchone()
                    expected_before = [
                        "Requirements:",
                        "- Create exactly one Engineering assignment for the file.",
                        "- Use the authorized artifact destination recorded in the work order.",
                        "- Independently verify the actual file contents.",
                        "- Close the objective only after successful verification.",
                    ]
                    if (row is None or row["revision"] != expected_revision or
                            row["status"] != "GROUNDED" or row["proposal"] is not None or
                            row["assignment_id"] is not None or
                            row["scope_ref"] != "work-order:engineering" or
                            row["submitter_id"] != actor_id or
                            row["acceptance_criteria"] != expected_before or
                            not isinstance(row["evidence"], dict) or
                            row["evidence"].get("status") != "VERIFIED"):
                        raise ObjectiveStateError(
                            "objective no longer satisfies the authorized reconciliation preconditions")
                    after = expected_before[1:]
                    grant_id = grant["grant_id"]
                    payload = {
                        "before_criteria": expected_before,
                        "after_criteria": after,
                        "reason": reason.strip(),
                        "authorized_actor": actor_id,
                        "authorization_action": "objective.criteria.reconcile",
                        "authorization_scope": objective_id,
                        "authorization_grant_id": grant_id,
                        "expected_revision": expected_revision,
                        "new_revision": expected_revision + 1,
                    }
                    self._event(cur, objective_id, "objective.criteria_reconciled",
                        f"grace-criteria-reconciled:{objective_id}:r{expected_revision}",
                        actor_id, payload)
                    cur.execute("""UPDATE grace_objectives SET acceptance_criteria=%s::jsonb,
                        revision=revision+1,updated_at=clock_timestamp()
                        WHERE objective_id=%s AND revision=%s AND status='GROUNDED'
                          AND proposal IS NULL AND assignment_id IS NULL
                          AND acceptance_criteria=%s::jsonb
                        RETURNING revision""",
                        (_json(after), objective_id, expected_revision,
                         _json(expected_before)))
                    updated = cur.fetchone()
                    if updated is None:
                        raise ObjectiveStateError("objective revision changed during reconciliation")
        except (ObjectiveNotAuthorized, ObjectiveStateError):
            raise
        return self.get_objective(objective_id)

    def submit_objective(self, objective_id, request, acceptance_criteria, *,
                         scope_ref, credential=None, principal=None, origin=None,
                         proposal_reference=None, criteria_source="steward_supplied"):
        if (not isinstance(objective_id, str) or not re.fullmatch(r"objective:[A-Za-z0-9._:-]{1,120}", objective_id)
                or not isinstance(request, str) or not request.strip()
                or len(request.encode("utf-8")) > self.MAX_OBJECTIVE_BYTES
                or not isinstance(acceptance_criteria, (list, tuple))
                or len(acceptance_criteria) > 20
                or any(not isinstance(item, str) or not item.strip() or len(item) > 1000
                       for item in acceptance_criteria)
                or criteria_source not in {"steward_supplied", "grace_derived"}
                or (criteria_source == "steward_supplied" and not acceptance_criteria)
                or (criteria_source == "grace_derived" and acceptance_criteria)):
            raise ValueError("objective identity, bounded request, and criteria source are required")
        if (credential is None) == (principal is None):
            raise ValueError("exactly one authenticated credential or principal is required")
        if origin is not None:
            if (not isinstance(origin, dict) or set(origin) != {"conversation_id", "source_sequence"}
                    or not isinstance(origin["conversation_id"], str)
                    or len(origin["conversation_id"]) != 36
                    or type(origin["source_sequence"]) is not int
                    or origin["source_sequence"] < 1):
                raise ValueError("conversation origin is invalid")
        if criteria_source == "grace_derived" and (
                scope_ref != "work-order:engineering" or origin is None):
            raise ValueError("Grace-derived criteria require the authorized conversation intake")
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
                                 "acceptance_criteria_source": criteria_source,
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
        attempt_id = str(uuid4())
        attempt_started_at = datetime.now(timezone.utc).isoformat()
        evidence_input = {"id": objective_id, "objective": objective["request"],
                          "acceptance_criteria": objective["acceptance_criteria"],
                          "contract_ref": self.CONTRACT_REF}
        try:
            result = self.knowledge.ground_assignment(evidence_input)
        except Exception as exc:
            failure_type = self._safe_failure_type(exc)
            error_code = ("KNOWLEDGE_PROVIDER_TIMEOUT" if isinstance(exc, TimeoutError)
                          else "KNOWLEDGE_PROVIDER_ERROR")
            evidence = {"status": KnowledgeStatus.UNAVAILABLE.value,
                        "source_references": [], "source_revision": None,
                        "source_sha256": None, "retrieval_complete": False,
                        "error_code": error_code, "value": None}
            self._set_waiting(objective, evidence, attempt_id, attempt_started_at,
                error_code=error_code,
                explanation=("The knowledge provider call timed out." if isinstance(exc, TimeoutError)
                             else "The knowledge provider call failed before returning evidence."),
                stage="provider_call", responsible_component="KNOWLEDGE-PROVIDER",
                failure_type=failure_type, evidence_bytes=None)
            raise ObjectiveStateError("knowledge provider did not return grounding evidence") from None

        status_value = getattr(getattr(result, "status", None), "value", None)
        source_references = getattr(result, "source_references", ())
        if not isinstance(source_references, (tuple, list)) or any(
                not isinstance(reference, str) for reference in source_references):
            source_references = ()
        source_revision = getattr(result, "source_revision", None)
        if not isinstance(source_revision, str) or not source_revision:
            source_revision = None
        source_sha256 = getattr(result, "source_sha256", None)
        if not isinstance(source_sha256, str) or not source_sha256:
            source_sha256 = None
        retrieval_complete = getattr(result, "retrieval_complete", None)
        evidence = {"status": status_value if isinstance(status_value, str)
                    else KnowledgeStatus.UNVERIFIED.value,
                    "source_references": list(source_references),
                    "source_revision": source_revision,
                    "source_sha256": source_sha256,
                    "retrieval_complete": retrieval_complete,
                    "value": getattr(result, "value", None)}
        try:
            raw_evidence = _json(evidence).encode("utf-8")
        except (TypeError, ValueError):
            evidence = {"status": KnowledgeStatus.UNVERIFIED.value,
                        "source_references": list(source_references),
                        "source_revision": source_revision,
                        "source_sha256": source_sha256,
                        "retrieval_complete": False,
                        "error_code": "EVIDENCE_SERIALIZATION_FAILED", "value": None}
            self._set_waiting(objective, evidence, attempt_id, attempt_started_at,
                error_code="EVIDENCE_SERIALIZATION_FAILED",
                explanation="Grounding evidence could not be serialized for durable storage.",
                stage="evidence_serialization", responsible_component="RESIDENT-ORCHESTRATION",
                evidence_bytes=None)
            raise ObjectiveStateError("grounded evidence serialization failed") from None
        if len(raw_evidence) > self.MAX_EVIDENCE_BYTES:
            evidence = {"status": KnowledgeStatus.INCOMPLETE.value,
                        "source_references": list(source_references),
                        "source_revision": source_revision,
                        "source_sha256": source_sha256,
                        "retrieval_complete": False,
                        "error_code": "EVIDENCE_TOO_LARGE", "value": None}
            self._set_waiting(objective, evidence, attempt_id, attempt_started_at,
                error_code="EVIDENCE_TOO_LARGE",
                explanation="The returned grounding evidence exceeded the configured storage boundary.",
                stage="evidence_size_validation", responsible_component="RESIDENT-ORCHESTRATION",
                evidence_bytes=raw_evidence)
            raise ObjectiveStateError("grounded evidence exceeds context boundary")
        failure = self._grounding_failure(status_value, retrieval_complete,
                                          source_references, source_revision, source_sha256)
        if failure:
            error_code, explanation, stage, responsible_component = failure
            evidence["error_code"] = error_code
            self._set_waiting(objective, evidence, attempt_id, attempt_started_at,
                error_code=error_code, explanation=explanation, stage=stage,
                responsible_component=responsible_component, evidence_bytes=raw_evidence)
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

    @staticmethod
    def _safe_failure_type(exc):
        name = type(exc).__name__
        return name[:80] if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", name) else "ProviderException"

    @staticmethod
    def _grounding_failure(status_value, retrieval_complete,
                           source_references, source_revision, source_sha256):
        if not isinstance(status_value, str) or status_value not in {
                status.value for status in KnowledgeStatus}:
            return ("KNOWLEDGE_RESULT_INVALID", "The provider returned a result with an unrecognized status.",
                    "provider_result_validation", "RESIDENT-ORCHESTRATION")
        status_failures = {
            KnowledgeStatus.UNAVAILABLE.value: ("KNOWLEDGE_PROVIDER_UNAVAILABLE",
                "The knowledge provider reported that it is unavailable.", "provider_result",
                "KNOWLEDGE-PROVIDER"),
            KnowledgeStatus.NO_MATCH.value: ("GROUNDING_NO_MATCH",
                "The knowledge provider returned no matching evidence.", "provider_result",
                "KNOWLEDGE-PROVIDER"),
            KnowledgeStatus.INCOMPLETE.value: ("GROUNDING_RETRIEVAL_INCOMPLETE",
                "The knowledge provider reported incomplete retrieval.", "provider_result",
                "KNOWLEDGE-PROVIDER"),
            KnowledgeStatus.CONTRADICTORY.value: ("GROUNDING_EVIDENCE_CONTRADICTORY",
                "The knowledge provider reported contradictory evidence.", "provider_result",
                "KNOWLEDGE-PROVIDER"),
            KnowledgeStatus.UNVERIFIED.value: ("GROUNDING_EVIDENCE_UNVERIFIED",
                "The knowledge provider did not verify the returned evidence.", "provider_result",
                "KNOWLEDGE-PROVIDER"),
        }
        if status_value in status_failures:
            return status_failures[status_value]
        if retrieval_complete is not True:
            return ("GROUNDING_RETRIEVAL_INCOMPLETE",
                    "The evidence did not confirm complete retrieval.", "grounding_validation",
                    "RESIDENT-ORCHESTRATION")
        if not source_references:
            return ("GROUNDING_SOURCE_REFERENCES_MISSING",
                    "Verified evidence did not include a source reference.", "grounding_validation",
                    "RESIDENT-ORCHESTRATION")
        if not source_revision:
            return ("GROUNDING_SOURCE_REVISION_MISSING",
                    "Verified evidence did not include its source revision.", "grounding_validation",
                    "RESIDENT-ORCHESTRATION")
        if not source_sha256:
            return ("GROUNDING_SOURCE_HASH_MISSING",
                    "Verified evidence did not include its source SHA-256.", "grounding_validation",
                    "RESIDENT-ORCHESTRATION")
        return None

    def _set_waiting(self, objective, evidence, attempt_id, attempt_started_at, *,
                     error_code, explanation, stage, responsible_component,
                     evidence_bytes, failure_type=None):
        objective_id = objective["objective_id"]
        if evidence_bytes is None:
            evidence_bytes = _json({key: evidence.get(key) for key in
                ("status", "source_references", "source_revision", "source_sha256",
                 "retrieval_complete", "error_code")}).encode("utf-8")
        received = next((event for event in self.objective_events(objective_id)
                         if event["event_type"] == "objective.received"), None)
        received_payload = (received or {}).get("payload") or {}
        origin = received_payload.get("origin") if isinstance(received_payload, dict) else None
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT revision,status FROM grace_objectives
                    WHERE objective_id=%s AND status IN ('RECEIVED','WAITING_FOR_EVIDENCE')
                    FOR UPDATE""", (objective_id,))
                row = cur.fetchone()
                if not row:
                    raise ObjectiveStateError("objective changed while recording missing evidence")
                next_revision = row["revision"] + 1
                event_id = str(uuid4())
                source_revision = evidence.get("source_revision")
                if (not isinstance(source_revision, str) or len(source_revision) > 128 or
                        not re.fullmatch(r"[A-Za-z0-9._:-]+", source_revision)):
                    source_revision = None
                diagnostic = {
                    "event_id": event_id, "attempt_id": attempt_id,
                    "objective_id": objective_id, "objective_revision": next_revision,
                    "source": ({"conversation_id": origin.get("conversation_id"),
                                "source_sequence": origin.get("source_sequence")}
                               if isinstance(origin, dict) else None),
                    "previous_state": row["status"],
                    "new_state": "WAITING_FOR_EVIDENCE", "stage": stage,
                    "attempted_operation": "knowledge_provider.ground_assignment",
                    "outcome": "blocked", "reason_code": error_code,
                    "explanation": explanation,
                    "evidence": {"status": evidence.get("status"),
                        "source_revision": source_revision,
                        "source_sha256_present": bool(evidence.get("source_sha256")),
                        "retrieval_complete": evidence.get("retrieval_complete") is True,
                        "reference_count": len(evidence.get("source_references", ())),
                        "sha256": hashlib.sha256(evidence_bytes).hexdigest()},
                    "responsible_component": responsible_component,
                    "retry": {"status": "authorized_same_objective_retry_available",
                        "retryable": True, "automatic": False, "next_retry_at": None,
                        "required_actor": "steward",
                        "next_permitted_action":
                            "Retry grounding through the same conversation work-order action; objective.submit is rechecked."},
                    "attempt_started_at": attempt_started_at,
                }
                if failure_type:
                    diagnostic["failure_type"] = failure_type
                payload = {"status": evidence["status"],
                           "retrieval_complete": evidence.get("retrieval_complete") is True,
                           "grounding_diagnostic": diagnostic}
                cur.execute("""INSERT INTO grace_objective_events
                    (event_id,objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,%s,'objective.waiting_for_evidence',%s,'knowledge-provider',%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING event_id""",
                    (event_id, objective_id,
                     f"grace-grounding-failure:{objective_id}:{attempt_id}", _json(payload)))
                if cur.fetchone() is None:
                    return False
                cur.execute("""UPDATE grace_objectives SET status='WAITING_FOR_EVIDENCE',
                    evidence=%s::jsonb,revision=%s,updated_at=clock_timestamp()
                    WHERE objective_id=%s AND revision=%s
                      AND status IN ('RECEIVED','WAITING_FOR_EVIDENCE')""",
                    (_json(evidence), next_revision, objective_id, row["revision"]))
                if cur.rowcount != 1:
                    raise ObjectiveStateError("objective changed while recording missing evidence")
        return True

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
        requested_list = list(objective["acceptance_criteria"])
        step_criteria = [criterion for step in proposal.steps
                         for criterion in step.acceptance_criteria]
        proposed = set(step_criteria)
        lifecycle = set(proposal.system_owned_criteria)
        received = next((event for event in self.objective_events(objective_id)
                         if event["event_type"] == "objective.received"), None)
        received_payload = (received or {}).get("payload") or {}
        criteria_source = received_payload.get("acceptance_criteria_source", "steward_supplied")
        origin = received_payload.get("origin")
        has_conversation_origin = (isinstance(origin, dict) and
                                   isinstance(origin.get("conversation_id"), str) and
                                   bool(origin["conversation_id"]))
        if criteria_source == "grace_derived" and not requested_list:
            requested_list = [*step_criteria, *proposal.system_owned_criteria]
            if (not requested_list or len(requested_list) > 20 or
                    len(set(requested_list)) != len(requested_list)):
                raise ObjectiveStateError("Grace-derived proposal criteria are empty, excessive, or duplicated")
        elif criteria_source != "steward_supplied" or not requested_list:
            raise ObjectiveStateError("objective acceptance-criteria source is invalid")
        requested = set(requested_list)
        for criterion in lifecycle:
            if lifecycle_evidence_event(criterion) == "proposal.approved_and_promoted":
                with self.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    if not self.proposal_promotion_evidence(cur, objective_id, criterion):
                        raise ObjectiveStateError(
                            "approved-promotion lifecycle evidence is not durably bound")
        artifact_criteria = {criterion for step in proposal.steps
            for requirement in step.artifact_requirements
            for criterion in requirement.acceptance_criteria}
        supplemental_step_criteria = proposed - requested
        formal_step_criteria = proposed & requested
        requires_one_dispatch = any(
            lifecycle_evidence_event(criterion) == "work_order.exactly_one_dispatched"
            for criterion in proposal.system_owned_criteria)
        if (proposed & lifecycle or
                len(step_criteria) != len(proposed) or
                not supplemental_step_criteria <= artifact_criteria or
                any(lifecycle_evidence_event(criterion) is not None
                    for criterion in supplemental_step_criteria) or
                (requires_one_dispatch and len(proposal.steps) != 1) or
                any(criterion not in requested or lifecycle_evidence_event(criterion) is None
                    for criterion in lifecycle) or
                (not has_conversation_origin and any(
                    lifecycle_evidence_event(criterion) == "conversation.result_published"
                    for criterion in lifecycle)) or
                formal_step_criteria | lifecycle != requested):
            raise ObjectiveStateError(
                "proposal must bind every original criterion to an Engineering step or a supported lifecycle event")
        # A model cannot turn a general objective into filesystem authority.
        # Every source path must have been explicitly named in the Steward's
        # original request or accepted criteria; the adapter allowlist is only
        # a second, operator-configured ceiling.
        approved_source_scope = [objective["request"], *objective["acceptance_criteria"]]
        # A Steward may approve CLI-accessible diagnostic evidence without
        # naming every deterministic output filename. Permit only the
        # objective/revision-bound JSON path under diagnostics/; the artifact
        # worker separately pins the repository, checks the exact persisted
        # contract, rejects symlinks/traversal, and stores output in its private
        # artifact root. This does not authorize source changes or other paths.
        diagnostic_evidence_approved = any(
            isinstance(criterion, str) and
            "cli-accessible diagnostic evidence" in criterion.casefold()
            for criterion in objective["acceptance_criteria"])
        objective_match = re.fullmatch(
            r"objective:proposal:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}):r([1-9][0-9]*)",
            objective_id)
        diagnostic_artifact_suffix = (
            f"_{objective_match.group(1)}_r{objective_match.group(2)}.json"
            if objective_match and int(objective_match.group(2)) == objective["revision"]
            else None)
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
            elif step.execution_capability == "engineering.codex-cli-artifact.v1":
                def artifact_path_is_named(item):
                    return any(re.search(r"(?<![A-Za-z0-9._/-])" + re.escape(item.path) +
                                         r"(?![A-Za-z0-9_/-]|\.(?=[A-Za-z0-9._/-]))", text)
                               for text in approved_source_scope)

                def artifact_path_is_diagnostic_scoped(item):
                    if (not diagnostic_evidence_approved or
                            diagnostic_artifact_suffix is None):
                        return False
                    # The typed artifact name carries the output role; the
                    # filename uses its concise stem (for example
                    # work_order_record -> work_order).
                    stem = re.sub(r"_(?:record|log)$", "", item.name)
                    return item.path == f"diagnostics/{stem}{diagnostic_artifact_suffix}"

                if any(not artifact_path_is_named(item) and
                       not artifact_path_is_diagnostic_scoped(item)
                       for item in step.artifact_requirements):
                    raise ObjectiveStateError(
                        "artifact path is absent from the Steward-approved objective scope")
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
                if criteria_source == "grace_derived":
                    cur.execute("""UPDATE grace_objectives SET status='PROPOSED',proposal=%s::jsonb,
                        acceptance_criteria=%s::jsonb,revision=revision+1,
                        updated_at=clock_timestamp()
                        WHERE objective_id=%s AND status='GROUNDED' AND acceptance_criteria='[]'::jsonb""",
                        (_json(document), _json(requested_list), objective_id))
                else:
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
                             "system_owned_criteria": [
                                 {"criterion": criterion,
                                  "evidence_event_type": lifecycle_evidence_event(criterion)}
                                 for criterion in proposal.system_owned_criteria],
                             "acceptance_criteria_source": criteria_source,
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

    def record_supervisory_event(self, objective_id, assignment_id, *, event_type,
            request_id, correlation_id, idempotency_key, payload):
        """Append bounded CME/Luna or performance feedback evidence to the objective ledger."""
        allowed = {"resident.reasoning.cme_recovery_evaluated",
                   "resident.reasoning.cme_recovery_blocked",
                   "resident.performance.evaluation_recorded",
                   "resident.performance.feedback_consumed",
                   "resident.performance.evaluation_blocked"}
        if (event_type not in allowed or not all(isinstance(value, str) and value
                for value in (objective_id, assignment_id, request_id, correlation_id,
                              idempotency_key)) or not isinstance(payload, dict) or
                len(_json(payload).encode("utf-8")) > 8192):
            raise ObjectiveStateError("supervisory event exceeds its bounded contract")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT status,assignment_id FROM grace_objectives "
                    "WHERE objective_id=%s FOR UPDATE", (objective_id,))
                objective = cur.fetchone()
                cur.execute("SELECT objective_ref FROM assignments WHERE id=%s", (assignment_id,))
                assignment = cur.fetchone()
                if (not objective or objective["assignment_id"] != assignment_id or
                        not assignment or assignment["objective_ref"] != objective_id):
                    raise ObjectiveStateError("supervisory event correlation changed")
                self._event(cur, objective_id, event_type, idempotency_key,
                    "office:grace", {"assignment_id": assignment_id,
                        "request_id": request_id, "correlation_id": correlation_id,
                        **payload})
        return True

    def supervisory_rejected_assignment_context(self, objective_id, assignment_id,
                                                verification_id):
        """Re-read one exact rejected assignment for the CME advisory consumer."""
        if not all(isinstance(value, str) and value for value in
                   (objective_id, assignment_id, verification_id)):
            return None
        step = self.proposal_step_for_assignment(objective_id, assignment_id)
        if not step:
            return None
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT o.status,o.assignment_id,a.state,a.objective_ref,
                    vr.attempt_id,vr.decision,wa.status AS attempt_status,
                    vr.criteria,vr.summary,vr.evidence_references,
                    vr.verifier_id,vr.verifier_revision
                FROM grace_objectives o JOIN assignments a ON a.id=o.assignment_id
                JOIN verification_records vr ON vr.assignment_id=a.id
                JOIN worker_attempts wa ON wa.attempt_id=vr.attempt_id
                WHERE o.objective_id=%s AND a.id=%s AND vr.verification_id=%s
                  AND vr.verification_id=(SELECT latest.verification_id
                    FROM verification_records latest WHERE latest.assignment_id=a.id
                    ORDER BY latest.recorded_at DESC,latest.verification_id DESC LIMIT 1)
                ORDER BY vr.recorded_at DESC LIMIT 1""",
                (objective_id, assignment_id, verification_id))
            row = cur.fetchone()
        if (not row or row["status"] != "WORK_ORDER_CREATED" or
                row["assignment_id"] != assignment_id or row["objective_ref"] != objective_id or
                row["state"] != "rework_required" or row["decision"] != "REJECTED" or
                row["attempt_status"] != "succeeded"):
            return None
        return {"objective_id": objective_id, "assignment_id": assignment_id,
            "step_id": step["step_id"],
            "step_acceptance_criteria": list(step["acceptance_criteria"]),
            "review_generation": 6,
            "completion": {"verification_id": verification_id,
                "attempt_id": str(row["attempt_id"]), "decision": "REJECTED",
                "summary": row["summary"], "criteria": row["criteria"],
                "evidence_references": list(row["evidence_references"] or []),
                "verifier_id": row["verifier_id"],
                "verifier_revision": row["verifier_revision"]}}

    def latest_performance_feedback(self, objective_id):
        """Return only the latest durable bounded grade/feedback for this objective."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT payload FROM grace_objective_events
                WHERE objective_id=%s AND event_type='resident.performance.feedback_consumed'
                ORDER BY sequence DESC LIMIT 1""", (objective_id,))
            row = cur.fetchone()
        return dict(row["payload"]) if row else None

    def exchange_response_metadata(self, request_id, correlation_id):
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT response_sha256,request_payload,delivery_state,
                    consumption_owner FROM external_reasoning_exchanges
                WHERE request_id=%s AND correlation_id=%s""", (request_id, correlation_id))
            row = cur.fetchone()
        return dict(row) if row else None

    def dispatchable_step(self, objective_id):
        """Return the first pending step whose persisted dependencies are verified."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT step_id,step_order,step_objective,acceptance_criteria,
                    depends_on,status,assignment_id FROM grace_objective_steps
                WHERE objective_id=%s ORDER BY step_order""", (objective_id,))
            rows = cur.fetchall()
        verified = {row["step_id"] for row in rows if row["status"] == "verified"}
        for row in rows:
            if row["status"] == "pending" and set(row["depends_on"]) <= verified:
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

    def _system_criterion_evidence(self, cur, objective_id, proposal, completion_cycle):
        """Resolve every lifecycle-only criterion to actual or deterministic future event evidence."""
        evidence = []
        for criterion in proposal.get("system_owned_criteria", []):
            event_type = lifecycle_evidence_event(criterion)
            if event_type is None:
                raise ObjectiveStateError("system-owned criterion has no lifecycle evidence contract")
            if event_type == "proposal.approved_and_promoted":
                if not self.proposal_promotion_evidence(cur, objective_id, criterion):
                    raise ObjectiveStateError("approved-promotion lifecycle evidence is not durable")
                reference = self.objective_proposal_reference(objective_id)
                keys = [reference["approval_event_key"],
                    f"proposal-work-order-request:{reference['proposal_id']}:{reference['revision']}"]
            elif event_type == "objective.completed":
                keys = [f"grace-objective-completed:{objective_id}:{completion_cycle}"]
            elif event_type == "conversation.result_published":
                keys = [f"grace-conversation-result-published:{objective_id}:{completion_cycle}"]
            elif event_type == "work_order.exactly_one_dispatched":
                cur.execute("""SELECT e.idempotency_key,e.payload->>'assignment_id' AS assignment_id
                    FROM grace_objective_events e JOIN assignments a
                      ON a.id=e.payload->>'assignment_id'
                    WHERE e.objective_id=%s AND e.event_type='work_order.dispatched'
                      AND a.objective_ref=%s ORDER BY e.sequence""",
                    (objective_id, objective_id))
                rows = cur.fetchall()
                assignment_ids = {row["assignment_id"] for row in rows}
                if len(rows) != 1 or len(assignment_ids) != 1:
                    raise ObjectiveStateError("exactly one dispatched Engineering assignment is required")
                keys = [rows[0]["idempotency_key"]]
            else:
                acceptable_types = (("execution.step_verified", "objective.completed")
                    if event_type == "execution.step_verified" else (event_type,))
                cur.execute("""SELECT idempotency_key FROM grace_objective_events
                    WHERE objective_id=%s AND event_type=ANY(%s)
                    ORDER BY sequence""", (objective_id, list(acceptable_types)))
                keys = [row["idempotency_key"] for row in cur.fetchall()]
                if event_type == "execution.step_verified" and not keys:
                    keys = [f"grace-objective-completed:{objective_id}:{completion_cycle}"]
                if not keys:
                    raise ObjectiveStateError("required lifecycle evidence is not durable")
            evidence.append({"criterion": criterion, "evidence_event_type": event_type,
                             "event_keys": keys})
        return evidence

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
        dispatch_payload = row["dispatch_payload"] if isinstance(row["dispatch_payload"], dict) else {}
        artifact_contract = dispatch_payload.get("artifact_contract")
        declared_contract = raw_step.get("artifact_requirements", [])
        if (not isinstance(artifact_contract, list) or artifact_contract != declared_contract):
            return None
        capability = raw_step.get("execution_capability", "engineering.codex-cli-artifact.v1")
        comfyui_binding = dispatch_payload.get("comfyui_request_binding")
        if capability == "engineering.comfyui-image.v1":
            expected = {"version": "grace.comfyui-request-binding.v1",
                "objective_id": objective_id, "assignment_id": assignment_id,
                "step_id": row["step_id"], "capability": capability,
                "workflow_id": raw_step.get("comfyui_workflow_id"),
                "parameters": raw_step.get("comfyui_parameters"),
                "proposal_step_sha256": hashlib.sha256(_json(raw_step).encode("utf-8")).hexdigest()}
            if not isinstance(comfyui_binding, dict) or comfyui_binding != expected:
                return None
        elif comfyui_binding is not None:
            return None
        return {"step_id": row["step_id"], "objective": row["step_objective"],
                "acceptance_criteria": row["acceptance_criteria"],
                "depends_on": row["depends_on"],
                "artifact_requirements": artifact_contract,
                "execution_capability": capability,
                "authorized_paths": raw_step.get("authorized_paths", []),
                "test_targets": raw_step.get("test_targets", []),
                "repository_reference": raw_step.get("repository_reference"),
                "repository_revision": raw_step.get("repository_revision"),
                "comfyui_request_binding": comfyui_binding,
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

    @staticmethod
    def _comfyui_request_binding(objective, step, assignment_id):
        """Snapshot a typed registered-workflow request in the durable dispatch event."""
        proposal = objective.get("proposal") if isinstance(objective, dict) else None
        raw_steps = proposal.get("steps", []) if isinstance(proposal, dict) else []
        raw_step = next((item for item in raw_steps if isinstance(item, dict) and
                         item.get("step_id") == step["step_id"]), None)
        if not isinstance(raw_step, dict):
            raise ObjectiveStateError("persisted proposal step is unavailable at dispatch")
        if raw_step.get("execution_capability") != "engineering.comfyui-image.v1":
            return {}
        if (raw_step.get("step_id") != step["step_id"] or
                raw_step.get("objective") != step.get("step_objective") or
                tuple(raw_step.get("acceptance_criteria", ())) != tuple(
                    step.get("acceptance_criteria", ())) or
                not isinstance(raw_step.get("comfyui_workflow_id"), str) or
                not isinstance(raw_step.get("comfyui_parameters"), dict)):
            raise ObjectiveStateError("ComfyUI request changed or is incomplete before dispatch")
        return {"comfyui_request_binding": {
            "version": "grace.comfyui-request-binding.v1",
            "objective_id": objective["objective_id"],
            "assignment_id": assignment_id,
            "step_id": step["step_id"],
            "capability": raw_step["execution_capability"],
            "workflow_id": raw_step["comfyui_workflow_id"],
            "parameters": raw_step["comfyui_parameters"],
            "proposal_step_sha256": hashlib.sha256(
                _json(raw_step).encode("utf-8")).hexdigest()}}

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
                    raw_step = next((item for item in locked_objective["proposal"].get("steps", [])
                        if isinstance(item, dict) and item.get("step_id") == step["step_id"]), None)
                    if not isinstance(raw_step, dict):
                        raise ObjectiveStateError("persisted proposal step is unavailable at dispatch")
                    artifact_contract = raw_step.get("artifact_requirements", [])
                    from ..resident_reasoning import ArtifactRequirement
                    if (raw_step.get("execution_capability", "engineering.codex-cli-artifact.v1") ==
                            "engineering.codex-cli-artifact.v1"):
                        if not isinstance(artifact_contract, list) or not 1 <= len(artifact_contract) <= 8:
                            raise ObjectiveStateError("assignment artifact contract is required before dispatch")
                        try:
                            requirements = [ArtifactRequirement(
                                item["name"], item["path"], item["media_type"],
                                tuple(item["acceptance_criteria"]), item.get("max_bytes", 32768))
                                for item in artifact_contract]
                            normalized_contract = []
                            for requirement in requirements:
                                item = asdict(requirement)
                                item["acceptance_criteria"] = list(requirement.acceptance_criteria)
                                normalized_contract.append(item)
                        except (KeyError, TypeError, ValueError):
                            raise ObjectiveStateError("assignment artifact contract is invalid") from None
                        if normalized_contract != artifact_contract:
                            raise ObjectiveStateError("assignment artifact contract is not canonical")
                        artifact_contract = normalized_contract
                    else:
                        artifact_contract = []
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
                         "artifact_contract": artifact_contract,
                         **self._source_target_binding(binding_objective, step, assignment_id),
                         **self._comfyui_request_binding(binding_objective, step, assignment_id)})
        except AssignmentIntakeDenied:
            raise ObjectiveNotAuthorized("assignment.create is not authorized") from None
        return assignment

    def record_verified_completion(self, objective_id, assignment_id):
        objective = self.get_objective(objective_id)
        assignment = self.ledger.get(assignment_id)
        if objective and objective["status"] == "COMPLETED":
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT
                    EXISTS (SELECT 1 FROM verification_records
                        WHERE assignment_id=%s AND decision='ACCEPTED') AS accepted,
                    EXISTS (SELECT 1 FROM grace_objective_steps
                        WHERE objective_id=%s AND assignment_id=%s AND status='verified')
                        AS verified_step,
                    EXISTS (SELECT 1 FROM grace_objective_events
                        WHERE objective_id=%s AND event_type='objective.completed')
                        AS terminal_event""",
                    (assignment_id, objective_id, assignment_id, objective_id))
                durable = cur.fetchone()
            if (assignment and assignment.get("objective_ref") == objective_id and
                    assignment["state"] == "completed" and durable["accepted"] and
                    durable["verified_step"] and durable["terminal_event"]):
                return objective
            raise ObjectiveStateError("completed objective does not match verified assignment")
        if (objective is None or objective["status"] != "WORK_ORDER_CREATED" or
                not assignment or assignment.get("objective_ref") != objective_id or
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
                cur.execute("SELECT status FROM grace_objectives WHERE objective_id=%s FOR UPDATE",
                            (objective_id,))
                locked_objective = cur.fetchone()
                if not locked_objective or locked_objective["status"] != "WORK_ORDER_CREATED":
                    raise ObjectiveStateError("objective changed before step verification")
                cur.execute("""SELECT step_id,step_order,status FROM grace_objective_steps
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
                completion_step = None
                if all_steps:
                    cur.execute("""SELECT step_id,step_order,assignment_id
                        FROM grace_objective_steps WHERE objective_id=%s
                        ORDER BY step_order DESC LIMIT 1""", (objective_id,))
                    completion_step = cur.fetchone()
        if step_row["status"] == "verified" and not all_steps:
            # A duplicate completion notification for an already verified
            # intermediate step is a no-op. Once every step is verified, the
            # same persisted row can still drive crash recovery below.
            return objective
        completion_assignment_id = (completion_step["assignment_id"] if all_steps
                                    else assignment_id)
        completion_verification = verification
        if all_steps and completion_assignment_id != assignment_id:
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT verification_id,decision,verifier_id,criteria,
                        verifier_revision,evidence_references,summary
                    FROM verification_records WHERE assignment_id=%s AND decision='ACCEPTED'
                    ORDER BY recorded_at DESC,verification_id DESC LIMIT 1""",
                    (completion_assignment_id,))
                completion_verification = cur.fetchone()
            if not completion_verification:
                raise ObjectiveStateError("final step has no persisted independent acceptance")
        completion_cycle = (completion_step["step_order"] if all_steps
                            else step_row["step_order"])
        payload = {"assignment_id": completion_assignment_id,
                   "step_id": (completion_step["step_id"] if all_steps else step_row["step_id"]),
                   "completion_cycle": completion_cycle,
                   "verification_id": str(completion_verification["verification_id"]),
                   "decision": completion_verification["decision"],
                   "verifier_id": completion_verification["verifier_id"],
                   "verifier_revision": completion_verification["verifier_revision"],
                   "verification_criteria": completion_verification["criteria"],
                   "verification_summary": completion_verification["summary"],
                   "evidence_references": list(completion_verification["evidence_references"])}
        step_payload = {"assignment_id": assignment_id, "step_id": step_row["step_id"],
                        "completion_cycle": step_row["step_order"],
                        "verification_id": str(verification["verification_id"]),
                        "decision": verification["decision"],
                        "verifier_id": verification["verifier_id"],
                        "verifier_revision": verification["verifier_revision"],
                        "verification_criteria": verification["criteria"],
                        "verification_summary": verification["summary"],
                        "evidence_references": list(verification["evidence_references"])}
        if all_steps:
            payload["proposal"] = objective.get("proposal")
            payload["objective_acceptance_criteria"] = list(objective.get(
                "acceptance_criteria", ()))
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                payload["system_owned_criteria_evidence"] = self._system_criterion_evidence(
                    cur, objective_id, objective.get("proposal") or {}, completion_cycle)
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT wr.result FROM worker_attempts wa
                JOIN worker_results wr USING(attempt_id)
                WHERE wa.assignment_id=%s AND wa.status='succeeded'
                ORDER BY wa.started_at DESC LIMIT 1""", (completion_assignment_id,))
            completion_artifact_row = cur.fetchone()
            if completion_assignment_id != assignment_id:
                cur.execute("""SELECT wr.result FROM worker_attempts wa
                    JOIN worker_results wr USING(attempt_id)
                    WHERE wa.assignment_id=%s AND wa.status='succeeded'
                    ORDER BY wa.started_at DESC LIMIT 1""", (assignment_id,))
                step_artifact_row = cur.fetchone()
            else:
                step_artifact_row = completion_artifact_row
        allowed_evidence = ("artifact_name", "artifact_path", "artifact_sha256",
            "artifact_bytes", "capability", "changed_files", "patch_sha256",
            "patch_bytes", "test_status", "repository_reference", "repository_revision",
            "assignment_id", "objective_id", "artifact_schema", "source_artifact_name",
            "artifacts", "artifact_contract", "source_revision", "source_sha256",
            "rework_verification_id", "status")
        completion_artifact = (completion_artifact_row or {}).get("result")
        if isinstance(completion_artifact, dict):
            payload["artifact"] = {key: completion_artifact[key] for key in allowed_evidence
                                    if key in completion_artifact}
        step_artifact = (step_artifact_row or {}).get("result")
        if isinstance(step_artifact, dict):
            step_payload["artifact"] = {key: step_artifact[key] for key in allowed_evidence
                                         if key in step_artifact}
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE grace_objectives SET status=%s,revision=revision+1,
                    updated_at=clock_timestamp() WHERE objective_id=%s
                    AND status='WORK_ORDER_CREATED'""",
                    ("COMPLETED" if all_steps else "WORK_ORDER_CREATED", objective_id))
                if cur.rowcount != 1:
                    raise ObjectiveStateError("objective completion raced with another update")
                self._event(cur, objective_id, "execution.step_verified",
                            f"grace-step-verified:{objective_id}:{step_row['step_id']}",
                            "verifier:independent", step_payload)
                if all_steps:
                    self._event(cur, objective_id, "objective.completed",
                                f"grace-objective-completed:{objective_id}:{completion_cycle}", "verifier:independent",
                                payload)
        return self.get_objective(objective_id)

    def cancel_work_order(self, objective_id, *, credential, authority_ref, reason=None):
        """Cancel grounded or not-yet-started work under the exact assignment.cancel grant."""
        if reason is not None and (not isinstance(reason, str) or
                                   not reason.strip() or len(reason.strip()) > 1000):
            raise ValueError("a bounded cancellation reason is required")
        supplied_reason = reason is not None
        reason = reason.strip() if supplied_reason else "Authorized work-order cancellation"
        objective = self.get_objective(objective_id)
        if (objective is None or objective["scope_ref"] != authority_ref or
                objective["status"] not in {"GROUNDED", "WORK_ORDER_CREATED", "CANCELLED"}):
            raise ObjectiveStateError("a cancellable objective in the exact scope is required")
        if objective["status"] == "GROUNDED" and not supplied_reason:
            raise ValueError("grounded objective cancellation requires an explicit reason")

        try:
            with self.ledger.db.transaction():
                with self.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    cur.execute("""SELECT status,scope_ref,assignment_id,revision
                        FROM grace_objectives WHERE objective_id=%s FOR UPDATE""",
                        (objective_id,))
                    locked = cur.fetchone()
                    if (locked is None or locked["scope_ref"] != authority_ref or
                            locked["status"] not in {
                                "GROUNDED", "WORK_ORDER_CREATED", "CANCELLED"}):
                        raise ObjectiveStateError("objective changed before cancellation")
                    actor = self.authorizer.require(
                        cur, credential, "assignment.cancel", authority_ref)
                    if locked["status"] == "CANCELLED":
                        cur.execute("""SELECT event_type,payload FROM grace_objective_events
                            WHERE objective_id=%s AND idempotency_key IN (%s,%s)
                            ORDER BY sequence DESC LIMIT 1""",
                            (objective_id,
                             f"grace-objective-cancelled:{objective_id}",
                             f"grace-work-order-cancelled:{objective_id}"))
                        prior = cur.fetchone()
                        if (prior is None or
                                prior["payload"].get("reason", reason) != reason):
                            raise ObjectiveStateError(
                                "objective was already cancelled for a different reason")
                    elif locked["status"] == "GROUNDED":
                        if locked["assignment_id"] is not None:
                            raise ObjectiveStateError(
                                "grounded objective already has an Engineering assignment")
                        cur.execute("""SELECT
                            EXISTS (SELECT 1 FROM assignments WHERE objective_ref=%s) AS has_assignment,
                            EXISTS (SELECT 1 FROM grace_objective_events
                                WHERE objective_id=%s AND event_type='work_order.dispatched') AS has_dispatch,
                            EXISTS (SELECT 1 FROM grace_objective_steps
                                WHERE objective_id=%s AND
                                  (assignment_id IS NOT NULL OR status<>'pending' OR dispatch_count>0))
                                AS has_step_activity""",
                            (objective_id, objective_id, objective_id))
                        activity = cur.fetchone()
                        if any(activity.values()):
                            raise ObjectiveStateError(
                                "grounded objective has Engineering assignment or dispatch history")
                        cur.execute("""UPDATE grace_objectives SET status='CANCELLED',
                            revision=revision+1,updated_at=clock_timestamp()
                            WHERE objective_id=%s AND status='GROUNDED'
                              AND assignment_id IS NULL AND revision=%s
                            RETURNING revision,updated_at""",
                            (objective_id, locked["revision"]))
                        cancelled = cur.fetchone()
                        if cancelled is None:
                            raise ObjectiveStateError(
                                "objective cancellation raced with another update")
                        self._event(cur, objective_id, "objective.cancelled",
                            f"grace-objective-cancelled:{objective_id}",
                            actor["principal_id"], {
                                "reason": reason,
                                "authorized_principal": actor["principal_id"],
                                "objective_revision": cancelled["revision"],
                                "cancelled_at": cancelled["updated_at"].isoformat(),
                            })
                    else:
                        assignment = self.ledger.get(locked["assignment_id"])
                        if not assignment or assignment["state"] not in {"queued", "ready"}:
                            raise ObjectiveStateError(
                                "only queued or ready work can be cancelled safely")
                        self.ledger.transition(
                            assignment["id"], "cancelled", "authorized_work_order_cancellation",
                            f"grace-work-order-cancel:{objective_id}",
                            actor_id=actor["principal_id"])
                        cur.execute("""UPDATE grace_objectives SET status='CANCELLED',
                            revision=revision+1,updated_at=clock_timestamp()
                            WHERE objective_id=%s AND status='WORK_ORDER_CREATED'
                              AND revision=%s RETURNING revision,updated_at""",
                            (objective_id, locked["revision"]))
                        cancelled = cur.fetchone()
                        if cancelled is None:
                            raise ObjectiveStateError(
                                "objective cancellation raced with another update")
                        self._event(cur, objective_id, "work_order.cancelled",
                            f"grace-work-order-cancelled:{objective_id}",
                            actor["principal_id"], {
                                "assignment_id": assignment["id"],
                                "reason": reason,
                                "authorized_principal": actor["principal_id"],
                                "objective_revision": cancelled["revision"],
                                "cancelled_at": cancelled["updated_at"].isoformat(),
                            })
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
        if not row:
            return None
        objective = dict(row)
        received = next((event for event in self.objective_events(objective_id)
                         if event["event_type"] == "objective.received"), None)
        payload = (received or {}).get("payload") or {}
        objective["acceptance_criteria_source"] = payload.get(
            "acceptance_criteria_source",
            "steward_supplied" if objective["acceptance_criteria"] else "legacy_unspecified")
        return objective

    def objective_proposal_reference(self, objective_id):
        """Read proposal provenance from the immutable objective.received event."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT payload->'proposal_reference' AS proposal_reference
                FROM grace_objective_events WHERE objective_id=%s
                  AND event_type='objective.received'""", (objective_id,))
            row = cur.fetchone()
        return row["proposal_reference"] if row else None

    def proposal_promotion_evidence(self, cur, objective_id, criterion):
        """Verify one approved-promotion lifecycle criterion against immutable records."""
        from ..resident_reasoning import lifecycle_evidence_event
        if lifecycle_evidence_event(criterion) != "proposal.approved_and_promoted":
            return False
        reference = self.objective_proposal_reference(objective_id)
        required = {"proposal_id", "revision", "content_sha256", "approval_event_key",
                    "objective_submit_grant_id"}
        if not isinstance(reference, dict) or not required <= set(reference):
            return False
        proposal_id, revision = reference["proposal_id"], reference["revision"]
        digest, approval_key = reference["content_sha256"], reference["approval_event_key"]
        if (not isinstance(proposal_id, str) or type(revision) is not int or revision < 1 or
                not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or
                not isinstance(approval_key, str) or not reference["objective_submit_grant_id"]):
            return False
        expected_objective_id = ("objective:proposal:" + str(uuid5(
            NAMESPACE_URL, f"riverview:proposal-work-order:{proposal_id}:r{revision}")) +
            f":r{revision}")
        if expected_objective_id != objective_id:
            return False
        cur.execute("""SELECT p.current_revision,p.lifecycle_status AS proposal_status,
                r.lifecycle_status AS revision_status,r.title,r.summary,r.objective,r.scope,
                r.proposed_approach,r.constraints,r.acceptance_criteria,r.tags
            FROM institutional_proposals p JOIN institutional_proposal_revisions r
              ON r.proposal_id=p.proposal_id AND r.revision=%s
            WHERE p.proposal_id=%s""", (revision, proposal_id))
        proposal = cur.fetchone()
        if not proposal or proposal["current_revision"] != revision or \
                proposal["proposal_status"] != "APPROVED" or \
                proposal["revision_status"] != "APPROVED":
            return False
        content = {key: proposal[key] for key in (
            "title", "summary", "objective", "scope", "proposed_approach",
            "constraints", "acceptance_criteria", "tags")}
        if hashlib.sha256(_json(content).encode("utf-8")).hexdigest() != digest:
            return False
        cur.execute("""SELECT actor_id,payload FROM institutional_proposal_events
            WHERE proposal_id=%s AND revision=%s AND event_type='proposal.steward_decision'
              AND idempotency_key=%s""", (proposal_id, revision, approval_key))
        approval = cur.fetchone()
        if (not approval or not str(approval["actor_id"]).startswith("steward:") or
                approval["payload"].get("to") != "APPROVED" or
                approval["payload"].get("content_sha256") != digest or
                not (approval["payload"].get("authority_reference") == "comms5-ingress:steward" or
                     str(approval["payload"].get("authority_reference", "")).startswith(
                         "account-auth-session:"))):
            return False
        cur.execute("""SELECT actor_id,payload FROM institutional_proposal_events
            WHERE proposal_id=%s AND revision=%s AND event_type='proposal.work_order_requested'
              AND idempotency_key=%s""", (
            proposal_id, revision, f"proposal-work-order-request:{proposal_id}:{revision}"))
        promotion = cur.fetchone()
        return bool(promotion and str(promotion["actor_id"]).startswith("steward:") and
            promotion["payload"].get("objective_id") == objective_id and
            promotion["payload"].get("content_sha256") == digest and
            promotion["payload"].get("approval_event_key") == approval_key and
            promotion["payload"].get("authority_reference") ==
                f"objective.submit-grant:{reference['objective_submit_grant_id']}")

    def grounded_objectives(self, *, scope_ref, limit=25, objective_id=None):
        """Return a bounded, stable queue of objectives ready for resident reasoning."""
        if not isinstance(scope_ref, str) or not scope_ref or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("exact scope and bounded objective limit are required")
        if objective_id is not None and (not isinstance(objective_id, str) or
                not re.fullmatch(r"objective:[A-Za-z0-9._:-]{1,120}", objective_id)):
            raise ValueError("objective identity is invalid")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT objective.objective_id,objective.revision
                FROM grace_objectives AS objective
                LEFT JOIN LATERAL (
                    SELECT max(event.occurred_at) AS last_attempt_at
                    FROM grace_objective_events AS event
                    WHERE event.objective_id=objective.objective_id
                      AND event.event_type IN
                          ('execution.reasoning_attempted','execution.reasoning_failed')
                ) AS reasoning_attempt ON TRUE
                WHERE objective.status='GROUNDED' AND objective.scope_ref=%s
                  AND (%s::text IS NULL OR objective.objective_id=%s)
                ORDER BY reasoning_attempt.last_attempt_at NULLS FIRST,
                    objective.created_at,objective.objective_id LIMIT %s""",
                (scope_ref, objective_id, objective_id, limit))
            return cur.fetchall()

    def read_reasoning_context(self, objective_id):
        """Adapt a durable GROUNDED objective to ResidentReasoner's assignment contract."""
        objective = self.get_objective(objective_id)
        if (objective is None or objective["status"] != "GROUNDED"
                or objective["evidence"].get("status") != KnowledgeStatus.VERIFIED.value
                or objective["evidence"].get("retrieval_complete") is not True):
            raise ObjectiveStateError("verified grounded objective context is required")
        received = next((event for event in self.objective_events(objective_id)
                         if event["event_type"] == "objective.received"), None)
        received_payload = (received or {}).get("payload") or {}
        return {
            "id": objective["objective_id"],
            "revision": str(objective["revision"]),
            "state": objective["status"],
            "contract_ref": self.CONTRACT_REF,
            "objective": objective["request"],
            "acceptance_criteria": list(objective["acceptance_criteria"]),
            "acceptance_criteria_source": received_payload.get(
                "acceptance_criteria_source", "steward_supplied"),
            "verified_evidence": objective["evidence"],
        }

    def objective_events(self, objective_id):
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT event_id,event_type,idempotency_key,actor_id,payload,occurred_at
                FROM grace_objective_events WHERE objective_id=%s ORDER BY sequence""",
                (objective_id,))
            return cur.fetchall()

    def diagnostic_runtime_evidence(self, objective_id):
        """Return bounded read-only lifecycle facts for an assigned diagnostic artifact."""
        if not isinstance(objective_id, str) or not re.fullmatch(
                r"objective:[A-Za-z0-9._:-]{1,150}", objective_id):
            raise ValueError("diagnostic objective identity is invalid")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT request,status,revision FROM grace_objectives WHERE objective_id=%s",
                        (objective_id,))
            current = cur.fetchone()
            if not current:
                raise ObjectiveStateError("diagnostic objective is unavailable")
            cur.execute("""SELECT event_type,count(*) AS count
                FROM grace_objective_events WHERE objective_id=%s
                GROUP BY event_type ORDER BY event_type""", (objective_id,))
            counts = {row["event_type"]: int(row["count"]) for row in cur.fetchall()}
            cur.execute("""SELECT event_id,event_type,occurred_at FROM grace_objective_events
                WHERE objective_id=%s AND event_type=ANY(%s)
                ORDER BY sequence DESC LIMIT 16""", (objective_id, [
                    "execution.reasoning_attempted", "execution.reasoning_failed",
                    "work_order.proposed", "work_order.dispatched",
                    "execution.step_verified", "objective.completed", "objective.cancelled"]))
            recent = [{"event_id": str(row["event_id"]), "event_type": row["event_type"],
                "occurred_at": row["occurred_at"].isoformat()} for row in cur.fetchall()]
            cur.execute("SELECT count(*) AS count FROM external_reasoning_exchanges WHERE objective_id=%s",
                        (objective_id,))
            exchange_count = int(cur.fetchone()["count"])
            history_ids = list(dict.fromkeys(re.findall(
                r"objective:grace-conversation:[0-9a-f-]{36}", current["request"] or "")))
            if len(history_ids) > 2:
                raise ObjectiveStateError("diagnostic history reference limit exceeded")
            history = []
            for history_id in history_ids:
                cur.execute("SELECT status,revision FROM grace_objectives WHERE objective_id=%s",
                            (history_id,))
                historical = cur.fetchone()
                if not historical:
                    continue
                cur.execute("""SELECT event_type,count(*) AS count FROM grace_objective_events
                    WHERE objective_id=%s GROUP BY event_type ORDER BY event_type""",
                    (history_id,))
                history_counts = {row["event_type"]: int(row["count"])
                                  for row in cur.fetchall()}
                cur.execute("""SELECT event_id,occurred_at FROM grace_objective_events
                    WHERE objective_id=%s AND event_type='objective.cancelled'
                    ORDER BY sequence DESC LIMIT 1""", (history_id,))
                cancelled = cur.fetchone()
                cur.execute("SELECT count(*) AS count FROM external_reasoning_exchanges WHERE objective_id=%s",
                            (history_id,))
                history.append({"objective_id": history_id,
                    "status": historical["status"], "revision": int(historical["revision"]),
                    "event_counts": history_counts,
                    "external_exchange_count": int(cur.fetchone()["count"]),
                    "cancellation_event": ({"event_id": str(cancelled["event_id"]),
                        "occurred_at": cancelled["occurred_at"].isoformat()}
                        if cancelled else None)})
        result = {"schema": "rv.grace-diagnostic-runtime-evidence.v1",
            "read_only": True,
            "objective": {"objective_id": objective_id, "status": current["status"],
                "revision": int(current["revision"]), "event_counts": counts,
                "external_exchange_count": exchange_count, "recent_events": recent},
            "referenced_historical_objectives": history}
        if len(_json(result).encode("utf-8")) > 8192:
            raise ObjectiveStateError("diagnostic runtime evidence exceeds its bound")
        return result

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
                  AND (
                    NOT EXISTS (SELECT 1 FROM grace_objective_events initial_publication
                        WHERE initial_publication.objective_id=o.objective_id
                          AND initial_publication.event_type='conversation.result_published'
                          AND initial_publication.payload->>'completion_cycle'=c.payload->>'completion_cycle'
                          AND COALESCE(initial_publication.payload->>'review_generation','1')='1')
                    OR EXISTS (SELECT 1 FROM grace_objective_events review_request
                        WHERE review_request.objective_id=o.objective_id
                          AND review_request.event_type='conversation.result_review_requested'
                          AND review_request.payload->>'completion_cycle'=c.payload->>'completion_cycle'
                          AND NOT EXISTS (SELECT 1 FROM grace_objective_events review_publication
                            WHERE review_publication.objective_id=o.objective_id
                              AND review_publication.event_type='conversation.result_review_published'
                              AND review_publication.payload->>'completion_cycle'=c.payload->>'completion_cycle'
                              AND review_publication.payload->>'review_generation'=
                                  review_request.payload->>'review_generation'))
                  )
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
                if str((event.get("payload") or {}).get("completion_cycle")) == str(cycle)]
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
                cur.execute("""SELECT objective_id,event_type,payload FROM grace_objective_events
                    WHERE idempotency_key=%s""", (idempotency_key,))
                prior = cur.fetchone()
                if prior:
                    if prior["objective_id"] != objective_id:
                        raise ObjectiveStateError(
                            "review revision idempotency key belongs to another objective")
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
                cur.execute("""SELECT objective_id,event_type,payload FROM grace_objective_events
                    WHERE idempotency_key=%s""", (idempotency_key,))
                stored = cur.fetchone()
                if (not stored or stored["objective_id"] != objective_id
                        or stored["event_type"] != "conversation.result_review_requested"
                        or stored["payload"] != payload):
                    raise ObjectiveStateError("review revision idempotency key conflicts")
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
                cur.execute("""SELECT status,proposal FROM grace_objectives
                    WHERE objective_id=%s FOR UPDATE""", (objective_id,))
                row = cur.fetchone()
                if not row:
                    raise ObjectiveStateError("objective is missing before chat return")
                lifecycle_evidence = []
                proposal = row.get("proposal") if isinstance(row.get("proposal"), dict) else {}
                for criterion in proposal.get("system_owned_criteria", []):
                    if lifecycle_evidence_event(criterion) == "conversation.result_published":
                        lifecycle_evidence.append({"criterion": criterion,
                            "evidence_event_type": "conversation.result_published",
                            "event_keys": [f"grace-conversation-result-published:{objective_id}:"
                                f"{receipt['completion_cycle']}"]})
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
                event_payload = dict(receipt)
                if lifecycle_evidence:
                    event_payload["system_owned_criteria_evidence"] = lifecycle_evidence
                self._event(cur, objective_id, event_type, event_key, "office:grace", event_payload)
        return True

    def pending_rejected_work_order_reviews(self, *, limit=10):
        """Return durable conversation- or approved-proposal-origin rejections for Grace review.

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
                    ORDER BY e.sequence LIMIT 1) received ON true
                WHERE o.status='WORK_ORDER_CREATED' AND o.assignment_id IS NOT NULL
                ORDER BY o.updated_at,o.objective_id LIMIT %s""", (limit,))
            objectives = cur.fetchall()
        pending = []
        for row in objectives:
            origin_payload = row["received_payload"] or {}
            origin = origin_payload.get("origin") if isinstance(origin_payload, dict) else None
            objective_id, assignment_id = row["objective_id"], row["assignment_id"]
            conversation_origin = (isinstance(origin, dict) and
                set(origin) == {"conversation_id", "source_sequence"} and
                type(origin.get("source_sequence")) is int and
                isinstance(origin.get("conversation_id"), str))
            proposal_reference = (origin_payload.get("proposal_reference")
                if isinstance(origin_payload, dict) else None)
            if not conversation_origin:
                lifecycle = ((row["proposal"] or {}).get("system_owned_criteria", [])
                    if isinstance(row["proposal"], dict) else [])
                with self.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    promoted = any(self.proposal_promotion_evidence(cur, objective_id, criterion)
                                   for criterion in lifecycle if isinstance(criterion, str))
                if not promoted or not isinstance(proposal_reference, dict):
                    continue
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
            if any(event["event_type"] == "engineering.rework_controller_validation" and
                    event["payload"].get("verification_id") == verification_id and
                    event["payload"].get("schema") == "rv.grace.rework-controller-validation.v2" and
                    event["payload"].get("authorization_lookup", {}).get("active") is True
                    for event in events):
                continue
            receipt_types = {"conversation.rework_review_published",
                             "engineering.rework_review_recorded"}
            review_receipts = [event for event in events if
                event["event_type"] in receipt_types and
                event["payload"].get("verification_id") == verification_id]
            review_generation = 1
            reopened_after_release_change = False
            prior_authorization_stop = False
            if review_receipts:
                last_receipt = review_receipts[-1]
                if conversation_origin:
                    continue
                if (last_receipt["event_type"] == "engineering.rework_review_recorded" and
                        last_receipt["payload"].get("decision") ==
                            "STEWARD_AUTHORIZATION_REQUIRED"):
                    # This is a controller preflight, never another model-review
                    # opportunity. Validate the exact authority and request ledger
                    # once, regardless of release churn.
                    prior_authorization_stop = True
                    prior_generation = last_receipt["payload"].get("review_generation", 1)
                    if type(prior_generation) is not int or prior_generation not in {1, 2, 3, 4, 5, 6}:
                        continue
                    review_generation = prior_generation
                else:
                    continue
            same_release_hold = any(event["event_type"] ==
                "engineering.rework_escalation_pending" and
                event["payload"].get("verification_id") == verification_id and
                event["payload"].get("runtime_release_id") == self.runtime_release_id()
                for event in events)
            if same_release_hold:
                continue
            matching_decisions = [event for event in events if event["event_type"] in {
                "engineering.rework_decided", "engineering.rejection_reviewed"} and
                event["payload"].get("assignment_id") == assignment_id and
                event["payload"].get("verification_id") == verification_id and
                event.get("idempotency_key") == (f"grace-rework-decision:{verification_id}" if
                    review_generation == 1 else
                    f"grace-rework-decision:{verification_id}:review:{review_generation}")]
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
                "completion": completion, "review_generation": review_generation}
            if prior_authorization_stop:
                prior_generation = last_receipt["payload"].get("review_generation", 1)
                prior_key = (f"grace-rework-decision:{verification_id}" if prior_generation == 1 else
                    f"grace-rework-decision:{verification_id}:review:{prior_generation}")
                prior_decision_event = next((event for event in reversed(events)
                    if event.get("idempotency_key") == prior_key and
                    event["event_type"] == "engineering.rework_decided" and
                    event["payload"].get("assignment_id") == assignment_id and
                    event["payload"].get("verification_id") == verification_id), None)
                if prior_decision_event:
                    item["prior_review_decision"] = {
                        "event_id": str(prior_decision_event["event_id"]),
                        "decision": prior_decision_event["payload"].get("decision"),
                        "rationale": prior_decision_event["payload"].get("rationale"),
                        "review_generation": prior_generation,
                        "request_id": last_receipt["payload"].get("request_id")}
                else:
                    item["prior_review_decision"] = {
                        "decision": "STEWARD_AUTHORIZATION_REQUIRED",
                        "rationale": "Persisted reviewer stop; controller authorization preflight required.",
                        "review_generation": prior_generation,
                        "request_id": last_receipt["payload"].get("request_id")}
            if not conversation_origin:
                item["proposal_reference"] = proposal_reference
            if decision_event and not reopened_after_release_change:
                item["persisted_decision"] = decision_event["payload"]
            item["rework_attempt_count"] = sum(1 for event in events
                if event["event_type"] == "engineering.rework_decided" and
                event["payload"].get("assignment_id") == assignment_id and
                event["payload"].get("decision") == "REWORK_PROPOSED")
            pending.append(item)
            if len(pending) >= limit:
                break
        return pending

    def rework_review_authority_evidence(self, context, *, credential):
        """Return read-only current work-order, assignment, and supervisory grant facts."""
        from psycopg import sql
        if (not isinstance(context, dict) or
                not all(isinstance(context.get(key), str) and context[key]
                    for key in ("objective_id", "assignment_id"))):
            raise ValueError("rework review authority subject is invalid")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT o.objective_id,o.status AS objective_status,o.revision,
                        o.assignment_id AS objective_assignment_id,
                        a.state AS assignment_state,a.objective_ref,
                        a.authority_ref,a.id AS assignment_id
                    FROM grace_objectives o JOIN assignments a
                      ON a.id=o.assignment_id
                    WHERE o.objective_id=%s AND a.id=%s""",
                    (context["objective_id"], context["assignment_id"]))
                row = cur.fetchone()
                if (not row or row["objective_id"] != context["objective_id"] or
                        row["objective_status"] != "WORK_ORDER_CREATED" or
                        row["objective_assignment_id"] != context["assignment_id"] or
                        row["assignment_id"] != context["assignment_id"]):
                    raise ObjectiveStateError("same active work-order assignment is required")
                if row["objective_ref"] != context["objective_id"]:
                    raise ObjectiveStateError("assignment objective correlation changed")
                try:
                    grant = self.assignment_intake.authorizer.require(
                        cur, credential, self.assignment_intake.ACTION, row["authority_ref"])
                except Exception as exc:
                    if type(exc).__name__ == "GrantDenied":
                        grant = None
                    else:
                        raise ObjectiveStateError("assignment authority evidence is unavailable") from None
                cur.execute("""SELECT EXISTS (SELECT 1 FROM grace_objective_events
                    WHERE objective_id=%s AND event_type='work_order.dispatched'
                      AND payload->>'assignment_id'=%s) AS dispatched""",
                    (context["objective_id"], context["assignment_id"]))
                dispatched = bool(cur.fetchone()["dispatched"])
                controller_facts = self._rework_controller_facts(cur,
                    context["objective_id"], context["assignment_id"])
                cur.execute(sql.SQL("""SELECT a.authorization_id,a.authority_grant_id,
                        a.authorized_by,a.scope,a.status,
                        {}.active_grace_supervisory_luna_grant(a.authority_grant_id) AS active_grant
                    FROM grace_supervisory_authorizations a
                    WHERE a.status='active' AND a.activated_at<=clock_timestamp()
                      AND (a.valid_until IS NULL OR a.valid_until>clock_timestamp())
                      AND a.scope->>'provider_id'='gpt-6-luna'
                      AND a.scope->'functions' ? 'performance_evaluation'
                    ORDER BY a.activated_at DESC LIMIT 1""").format(
                        sql.Identifier(self.authorizer.schema)))
                authorization = cur.fetchone()
        diagnostic_evidence = self.diagnostic_runtime_evidence(context["objective_id"])
        return {"schema": "rv.grace-rework-authority-evidence.v1", "read_only": True,
            "objective_id": context["objective_id"],
            "objective_status": row["objective_status"],
            "objective_revision": int(row["revision"]),
            "assignment_id": row["assignment_id"],
            "assignment_state": row["assignment_state"],
            "assignment_scope": row["authority_ref"],
            "work_order_dispatched": dispatched,
            "proposal_reference": context.get("proposal_reference"),
            "objective_runtime_evidence": diagnostic_evidence,
            "assignment_create_grant": {"active": grant is not None,
                "action": self.assignment_intake.ACTION,
                "scope_ref": row["authority_ref"],
                "principal_id": grant["principal_id"] if grant else None,
                "grant_id": grant["grant_id"] if grant else None},
            "supervisory_luna_authorization": ({
                "authorization_id": str(authorization["authorization_id"]),
                "authority_grant_id": authorization["authority_grant_id"],
                "authorized_by": authorization["authorized_by"],
                "scope": authorization["scope"],
                "active": (authorization["status"] == "active" and
                    authorization["active_grant"] == authorization["authority_grant_id"])}
                if authorization else None),
            "luna_escalation_authorization": {
                "source": f"{self.authorizer.schema}.active_grace_luna_escalation_grant",
                "action": "resident.reasoning.escalate",
                "scope_ref": "provider:gpt-6-luna",
                "grant_id": controller_facts["luna_escalation_authorization"]["grant_id"],
                "authorization_id": controller_facts["luna_escalation_authorization"]["authorization_id"],
                "active": controller_facts["luna_escalation_authorization"]["active"]},
            "prior_provider_requests": controller_facts["request_history"],
            "performance_evaluation_events": controller_facts["performance_evaluation_events"],
            "same_assignment_rework": {"available": bool(grant is not None and dispatched and
                    row["assignment_state"] == "rework_required"),
                "assignment_id": row["assignment_id"],
                "prior_rework_attempts": context.get("rework_attempt_count", 0),
                "maximum_rework_attempts": self.MAX_GOVERNED_REWORK_ATTEMPTS,
                "scope_changes": False,
                "independent_verification_required": True}}

    def _rework_controller_facts(self, cur, objective_id, assignment_id):
        """Read exact Luna authorization and objective-scoped request/evaluation facts."""
        from psycopg import sql
        cur.execute("""SELECT o.status AS objective_status,o.revision,
                o.assignment_id,a.state AS assignment_state
            FROM grace_objectives o JOIN assignments a ON a.id=o.assignment_id
            WHERE o.objective_id=%s AND a.id=%s AND a.objective_ref=o.objective_id""",
            (objective_id, assignment_id))
        lifecycle = cur.fetchone()
        if not lifecycle:
            raise ObjectiveStateError("controller facts require the current objective assignment")
        cur.execute(sql.SQL("SELECT {}.active_grace_luna_escalation_grant() AS grant_id")
            .format(sql.Identifier(self.authorizer.schema)))
        grant_id = cur.fetchone()["grant_id"]
        cur.execute(sql.SQL("""SELECT a.authorization_id,a.authority_grant_id,
                a.authorized_by,a.scope,a.status,
                {}.active_grace_supervisory_luna_grant(a.authority_grant_id) AS active_grant
            FROM grace_supervisory_authorizations a
            WHERE a.status='active' AND a.activated_at<=clock_timestamp()
              AND (a.valid_until IS NULL OR a.valid_until>clock_timestamp())
              AND a.scope->>'provider_id'='gpt-6-luna'
              AND a.scope->'functions' ? 'performance_evaluation'
            ORDER BY a.activated_at DESC LIMIT 1""").format(
                sql.Identifier(self.authorizer.schema)))
        supervisory = cur.fetchone()
        cur.execute("""SELECT min(occurred_at) AS dispatched_at FROM grace_objective_events
            WHERE objective_id=%s AND event_type='work_order.dispatched'
              AND payload->>'assignment_id'=%s""", (objective_id, assignment_id))
        dispatched_at = cur.fetchone()["dispatched_at"]
        cur.execute("""SELECT x.request_id,x.request_payload->>'request_type' AS request_type,
                x.provider_id,x.classification,x.delivery_state,x.requested_at,
                count(e.event_id) FILTER (WHERE e.event_type='provider_attempt_started') AS attempt_count,
                max(e.payload->>'authorization_id') FILTER (
                    WHERE e.event_type='provider_attempt_started') AS attempt_authorization_id,
                max(e.payload->'usage'->>'http_status') FILTER (
                    WHERE e.event_type='provider_attempt_settled') AS http_status,
                max(e.payload->'usage'->>'provider_error_type') FILTER (
                    WHERE e.event_type='provider_attempt_settled') AS provider_error_type,
                max(e.payload->'usage'->>'provider_error_param') FILTER (
                    WHERE e.event_type='provider_attempt_settled') AS provider_error_param,
                max(e.payload->'usage'->>'provider_request_id') FILTER (
                    WHERE e.event_type='provider_attempt_settled') AS provider_request_id
            FROM external_reasoning_exchanges x
            LEFT JOIN external_reasoning_exchange_events e ON e.request_id=x.request_id
            WHERE x.objective_id=%s AND x.requested_at >= %s
              AND x.request_payload->>'request_type' IN
                  ('performance_evaluation','cme_diagnostic_recovery')
            GROUP BY x.request_id,x.request_payload,x.provider_id,x.classification,
                x.delivery_state,x.requested_at
            ORDER BY x.requested_at,x.request_id LIMIT 32""",
            (objective_id, dispatched_at or datetime.min.replace(tzinfo=timezone.utc)))
        requests = [{"request_id": str(item["request_id"]),
            "request_type": item["request_type"], "provider_id": item["provider_id"],
            "classification": item["classification"],
            "requested_at": item["requested_at"].isoformat(),
            "delivery_state": item["delivery_state"],
            "provider_attempt_count": int(item["attempt_count"] or 0),
            "attempt_authorization_id": item["attempt_authorization_id"],
            "http_status": item["http_status"],
            "provider_error_type": item["provider_error_type"],
            "provider_error_param": item["provider_error_param"],
            "provider_request_id": item["provider_request_id"]}
            for item in cur.fetchall()]
        cur.execute("""SELECT count(*) FILTER (WHERE event_type=
                    'resident.performance.evaluation_recorded') AS evaluations,
                count(*) FILTER (WHERE event_type=
                    'resident.performance.feedback_consumed') AS feedback_consumed,
                count(*) FILTER (WHERE event_type=
                    'resident.performance.evaluation_blocked') AS evaluations_blocked
            FROM grace_objective_events WHERE objective_id=%s""", (objective_id,))
        evaluation_events = cur.fetchone()
        return {"objective_status": lifecycle["objective_status"],
            "objective_revision": int(lifecycle["revision"]),
            "assignment_state": lifecycle["assignment_state"],
            "luna_escalation_authorization": {
                "source": f"{self.authorizer.schema}.active_grace_luna_escalation_grant",
                "action": "resident.reasoning.escalate", "scope_ref": "provider:gpt-6-luna",
                "grant_id": grant_id,
                "authorization_id": (str(supervisory["authorization_id"])
                    if supervisory else None),
                "active": bool(grant_id)},
            "supervisory_luna_authorization": ({
                "authorization_id": str(supervisory["authorization_id"]),
                "authority_grant_id": supervisory["authority_grant_id"],
                "authorized_by": supervisory["authorized_by"],
                "scope": supervisory["scope"],
                "active": (supervisory["status"] == "active" and
                    supervisory["active_grant"] == supervisory["authority_grant_id"])}
                if supervisory else None),
            "request_history": requests,
            "performance_evaluation_events": {
                "evaluation_recorded": int(evaluation_events["evaluations"]),
                "feedback_consumed": int(evaluation_events["feedback_consumed"]),
                "evaluation_blocked": int(evaluation_events["evaluations_blocked"])}}

    def record_rework_controller_validation(self, context, reviewer_decision):
        """Persist controller-verified disposition of a reviewer authorization stop."""
        if (not isinstance(context, dict) or not isinstance(reviewer_decision, dict) or
                reviewer_decision.get("decision") != "STEWARD_AUTHORIZATION_REQUIRED" or
                not all(isinstance(context.get(key), str) and context[key]
                    for key in ("objective_id", "assignment_id")) or
                not isinstance(context.get("completion"), dict) or
                not isinstance(context["completion"].get("verification_id"), str)):
            raise ObjectiveStateError("controller authorization validation context is invalid")
        objective_id, assignment_id = context["objective_id"], context["assignment_id"]
        verification_id = context["completion"]["verification_id"]
        review_generation = context.get("review_generation", 1)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT status,revision,assignment_id FROM grace_objectives "
                    "WHERE objective_id=%s FOR UPDATE", (objective_id,))
                objective = cur.fetchone()
                cur.execute("SELECT state,objective_ref FROM assignments WHERE id=%s FOR UPDATE",
                    (assignment_id,))
                assignment = cur.fetchone()
                cur.execute("SELECT verification_id,decision,criteria,summary FROM verification_records "
                    "WHERE assignment_id=%s ORDER BY recorded_at DESC,verification_id DESC LIMIT 1",
                    (assignment_id,))
                verification = cur.fetchone()
                if (not objective or objective["status"] != "WORK_ORDER_CREATED" or
                        objective["assignment_id"] != assignment_id or not assignment or
                        assignment["objective_ref"] != objective_id or
                        assignment["state"] != "rework_required" or not verification or
                        str(verification["verification_id"]) != verification_id or
                        verification["decision"] != "REJECTED"):
                    raise ObjectiveStateError("controller validation requires the current rejected assignment")
                facts = self._rework_controller_facts(cur, objective_id, assignment_id)
                auth_state = facts["luna_escalation_authorization"]
                idem_suffix = auth_state["grant_id"] or "missing"
                idem = f"grace-rework-controller-validation-v2:{verification_id}:{idem_suffix}"
                request_history = facts["request_history"]
                advisory_requests = [item for item in request_history
                    if item["request_type"] == "cme_diagnostic_recovery"]
                evaluation_requests = [item for item in request_history
                    if item["request_type"] == "performance_evaluation"]
                auth = auth_state
                evaluation_events = facts["performance_evaluation_events"]
                authorized_advisory_requests = [item for item in advisory_requests
                    if auth["active"] and facts["supervisory_luna_authorization"] and
                    facts["supervisory_luna_authorization"]["active"] and
                    facts["supervisory_luna_authorization"]["authority_grant_id"] == auth["grant_id"] and
                    item["attempt_authorization_id"] ==
                        facts["supervisory_luna_authorization"]["authorization_id"] and
                    item["provider_attempt_count"] > 0]
                successful_advisory_count = sum(item["delivery_state"] in
                    {"response_received", "grace_consumed"}
                    for item in authorized_advisory_requests)
                acceptance_assessment = {
                    "criterion": "Exactly one authorized GPT-6 Luna advisory escalation is issued through the durable external reasoning exchange, with no uncontrolled retries.",
                    "authorized_advisory_exchange_count": len(authorized_advisory_requests),
                    "authorized_advisory_provider_attempt_count": sum(
                        item["provider_attempt_count"] for item in authorized_advisory_requests),
                    "failed_authorized_advisory_exchange_count": sum(
                        item["delivery_state"] == "failed"
                        for item in authorized_advisory_requests),
                    "successful_authorized_advisory_exchange_count": successful_advisory_count,
                    "performance_evaluation_request_count": len(evaluation_requests),
                    "evaluation_recorded_count": evaluation_events["evaluation_recorded"],
                    "feedback_consumed_count": evaluation_events["feedback_consumed"],
                    "passed": (len(authorized_advisory_requests) == 1 and
                        sum(item["provider_attempt_count"] for item in authorized_advisory_requests) == 1 and
                        successful_advisory_count == 1)}
                if auth["active"]:
                    outcome = "reviewer_authorization_stop_rejected_active_exact_grant"
                    reason = ("The exact Luna escalation grant is active, so the reviewer's missing-"
                        "authorization claim is not supported. The authoritative request ledger shows "
                        f"{len(authorized_advisory_requests)} authorized advisory exchange(s), "
                        f"{sum(item['provider_attempt_count'] for item in authorized_advisory_requests)} "
                        f"provider attempt(s), and {successful_advisory_count} successful advisory "
                        f"response(s). The independent verifier still records {verification['decision']} "
                        "for this assignment, so s3 cannot advance; failed provider attempts are not a "
                        "successful evaluation or verifier acceptance.")
                    next_action = "retain_rework_required_without_80b_or_luna_retry"
                else:
                    outcome = "reviewer_authorization_stop_confirmed_exact_grant_missing"
                    reason = ("The existing authority registry returned no active "
                        "resident.reasoning.escalate grant for provider:gpt-6-luna.")
                    next_action = "retain_rework_required_pending_exact_authorization"
                reviewer = {key: reviewer_decision.get(key) for key in
                    ("event_id", "decision", "rationale", "request_id", "review_generation")}
                payload = {"schema": "rv.grace.rework-controller-validation.v2",
                    "objective_id": objective_id, "assignment_id": assignment_id,
                    "objective_status": objective["status"],
                    "objective_revision": int(objective["revision"]),
                    "assignment_state": assignment["state"],
                    "verification_id": verification_id,
                    "reviewer_decision": reviewer,
                    "authorization_lookup": auth,
                    "supervisory_authorization": facts["supervisory_luna_authorization"],
                    "request_history": request_history,
                    "acceptance_assessment": acceptance_assessment,
                    "performance_evaluation_events": evaluation_events,
                    "verification": {"decision": verification["decision"],
                        "criteria": verification["criteria"],
                        "summary": verification["summary"]},
                    "acceptance_criteria": list(context.get("step_acceptance_criteria", [])),
                    "validation_outcome": outcome, "next_action": next_action,
                    "reason": reason, "classification": "institutional",
                    "source_references": ([f"verification:{verification_id}"] +
                        ([f"authority-grant:{auth['grant_id']}"] if auth["grant_id"] else []) +
                        [f"external-reasoning-request:{item['request_id']}"
                         for item in request_history])}
                if len(_json(payload).encode("utf-8")) > 24576:
                    raise ObjectiveStateError("controller validation evidence exceeds its bound")
                cur.execute("SELECT event_id,payload FROM grace_objective_events WHERE objective_id=%s "
                    "AND idempotency_key=%s", (objective_id, idem))
                existing = cur.fetchone()
                if existing:
                    if dict(existing["payload"]) != payload:
                        raise ObjectiveStateError("controller validation idempotency conflict")
                    return {**payload, "event_id": str(existing["event_id"])}
                self._event(cur, objective_id, "engineering.rework_controller_validation",
                    idem, "office:grace-controller", payload)
                cur.execute("SELECT event_id FROM grace_objective_events WHERE objective_id=%s "
                    "AND idempotency_key=%s", (objective_id, idem))
                recorded = cur.fetchone()
                if not recorded:
                    raise ObjectiveStateError("controller validation event could not be confirmed")
        return {**payload, "event_id": str(recorded["event_id"])}

    def record_rework_decision(self, context, decision, *, credential):
        """Persist Grace's bounded reject/stop decision and governed same-assignment requeue."""
        if (not isinstance(context, dict) or not isinstance(decision, dict) or
                set(decision) != {"decision", "rationale", "correction_instruction",
                                  "criteria_to_address"}):
            raise ObjectiveStateError("rework decision contract is invalid")
        verification_id = context.get("completion", {}).get("verification_id")
        objective_id, assignment_id = context.get("objective_id"), context.get("assignment_id")
        criteria = context.get("step_acceptance_criteria")
        review_generation = context.get("review_generation", 1)
        external_reasoning = context.get("external_reasoning")
        if (not isinstance(verification_id, str) or not isinstance(objective_id, str) or
                not isinstance(assignment_id, str) or not isinstance(criteria, list) or
                not criteria or type(review_generation) is not int or
                not 1 <= review_generation <= 6 or decision["decision"] not in {
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
        controller_validation = None
        if decision["decision"] == "STEWARD_AUTHORIZATION_REQUIRED":
            controller_validation = self.record_rework_controller_validation(context, decision)
            if controller_validation["authorization_lookup"]["active"]:
                return {"verification_id": verification_id,
                    "decision": "CONTROLLER_HOLD", "controller_hold": True,
                    "controller_validation": controller_validation}
        payload = {"verification_id": verification_id, "assignment_id": assignment_id,
            "attempt_id": str(context.get("completion", {}).get("attempt_id", "")),
            "decision": decision["decision"], "rationale": decision["rationale"].strip(),
            "correction_instruction": instruction.strip() if isinstance(instruction, str) else None,
            "criteria_to_address": list(decision["criteria_to_address"]),
            "acceptance_criteria_sha256": hashlib.sha256(
                _json(criteria).encode("utf-8")).hexdigest()}
        if controller_validation is not None:
            payload["controller_validation_outcome"] = controller_validation["validation_outcome"]
        if external_reasoning is not None:
            if (not isinstance(external_reasoning, dict) or
                    set(external_reasoning) != {"request_id", "correlation_id", "response_sha256",
                        "cme_event_id"} or
                    any(not isinstance(external_reasoning.get(key), str) or not external_reasoning[key]
                        for key in external_reasoning) or
                    not re.fullmatch(r"[0-9a-f]{64}", external_reasoning["response_sha256"])):
                raise ObjectiveStateError("CME advisory correlation is invalid")
            payload["external_reasoning"] = dict(external_reasoning)
        satisfied = decision["decision"] == "OBJECTIVE_SATISFIED"
        base_idem = (f"grace-rejection-review:{verification_id}" if satisfied else
                     f"grace-rework-decision:{verification_id}")
        idem = base_idem if review_generation == 1 else (
            f"grace-rework-decision:{verification_id}:review:{review_generation}")
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
                if external_reasoning is not None:
                    cur.execute("""SELECT delivery_state,consumption_owner,provider_id,
                            request_payload,response_sha256 FROM external_reasoning_exchanges
                        WHERE request_id=%s AND correlation_id=%s AND objective_id=%s FOR UPDATE""",
                        (external_reasoning["request_id"], external_reasoning["correlation_id"],
                         objective_id))
                    exchange = cur.fetchone()
                    original = ((exchange["request_payload"] or {}).get("original_request", {})
                        if exchange else {})
                    if (not exchange or exchange["delivery_state"] != "response_received" or
                            exchange["provider_id"] != "gpt-6-luna" or
                            exchange["consumption_owner"] != "resident:grace" or
                            exchange["request_payload"].get("request_type") !=
                                "cme_diagnostic_recovery" or
                            original.get("assignment_id") != objective_id or
                            exchange["response_sha256"] != external_reasoning["response_sha256"]):
                        raise ObjectiveStateError("correlated CME Luna advisory must be under Grace consumption")
                if decision["decision"] == "REWORK_PROPOSED":
                    cur.execute("""SELECT count(*) AS attempt_count FROM grace_objective_events
                        WHERE objective_id=%s AND event_type='engineering.rework_decided'
                          AND payload->>'assignment_id'=%s AND payload->>'decision'='REWORK_PROPOSED'""",
                        (objective_id, assignment_id))
                    attempt_count = cur.fetchone()["attempt_count"]
                    retry_limit = (1 if external_reasoning is not None else
                        self.MAX_GOVERNED_REWORK_ATTEMPTS)
                    if attempt_count >= retry_limit:
                        raise ObjectiveStateError("governed rework retry limit is exhausted")
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

    def record_rework_escalation_pending(self, context, reason_code):
        """Persist an actionable escalation hold without dispatching or inventing a provider."""
        allowed = {"review_provider_uncommissioned", "review_provider_unavailable",
                   "retry_limit_exhausted"}
        if (not isinstance(context, dict) or reason_code not in allowed or
                not isinstance(context.get("objective_id"), str) or
                not isinstance(context.get("assignment_id"), str) or
                not isinstance(context.get("completion"), dict) or
                not isinstance(context["completion"].get("verification_id"), str)):
            raise ObjectiveStateError("rework escalation context is invalid")
        objective_id = context["objective_id"]
        assignment_id = context["assignment_id"]
        verification_id = context["completion"]["verification_id"]
        runtime_release_id = self.runtime_release_id()
        payload = {"decision": "ESCALATION_PENDING", "reason_code": reason_code,
            "assignment_id": assignment_id, "verification_id": verification_id,
            "step_id": context.get("step_id"),
            "rework_attempt_count": context.get("rework_attempt_count", 0),
            "retry_limit": self.MAX_GOVERNED_REWORK_ATTEMPTS,
            "runtime_release_id": runtime_release_id,
            "required_action": "Steward to commission or restore the authorized rejection-review provider, or direct the next scoped correction."}
        idem = f"grace-rework-escalation-pending:{verification_id}:{reason_code}:{runtime_release_id}"
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT status,assignment_id FROM grace_objectives WHERE objective_id=%s FOR UPDATE",
                            (objective_id,))
                objective = cur.fetchone()
                cur.execute("SELECT state,objective_ref FROM assignments WHERE id=%s FOR UPDATE",
                            (assignment_id,))
                assignment = cur.fetchone()
                cur.execute("""SELECT vr.verification_id,vr.decision
                    FROM verification_records vr WHERE vr.assignment_id=%s
                    ORDER BY vr.recorded_at DESC,vr.verification_id DESC LIMIT 1""", (assignment_id,))
                latest = cur.fetchone()
                if (not objective or objective["status"] != "WORK_ORDER_CREATED" or
                        objective["assignment_id"] != assignment_id or not assignment or
                        assignment["objective_ref"] != objective_id or
                        assignment["state"] != "rework_required" or not latest or
                        latest["decision"] != "REJECTED" or
                        str(latest["verification_id"]) != verification_id):
                    raise ObjectiveStateError("current independently rejected assignment is required")
                cur.execute("SELECT payload FROM grace_objective_events WHERE objective_id=%s AND idempotency_key=%s",
                            (objective_id, idem))
                existing = cur.fetchone()
                if existing and dict(existing["payload"]) != payload:
                    raise ObjectiveStateError("rework escalation idempotency conflict")
                self._event(cur, objective_id, "engineering.rework_escalation_pending", idem,
                            "office:grace", payload)
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

    def record_rework_review_recorded(self, context, request_id):
        """Acknowledge a proposal-origin review without inventing a conversation receipt."""
        if (not isinstance(context, dict) or context.get("origin") is not None or
                not all(isinstance(context.get(key), str) and context[key]
                    for key in ("objective_id", "assignment_id")) or
                not isinstance(request_id, str) or not request_id or
                not isinstance(context.get("completion"), dict)):
            raise ValueError("proposal-origin review receipt is invalid")
        objective_id, assignment_id = context["objective_id"], context["assignment_id"]
        verification_id = context["completion"].get("verification_id")
        review_generation = context.get("review_generation", 1)
        if (not isinstance(verification_id, str) or not verification_id or
                type(review_generation) is not int or not 1 <= review_generation <= 6):
            raise ValueError("proposal-origin verifier identity is required")
        request_subject = ("riverview:grace-rework-review:" + objective_id + ":" +
            assignment_id + ":" + verification_id)
        if review_generation > 1:
            request_subject += f":review:{review_generation}"
        expected_request_id = str(uuid5(NAMESPACE_URL, request_subject))
        if request_id != expected_request_id:
            raise ValueError("proposal-origin rework request correlation is invalid")
        key = (f"grace-rework-review-recorded:{verification_id}" if review_generation == 1 else
               f"grace-rework-review-recorded:{verification_id}:review:{review_generation}")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT status,assignment_id FROM grace_objectives
                    WHERE objective_id=%s FOR UPDATE""", (objective_id,))
                objective = cur.fetchone()
                cur.execute("""SELECT state,objective_ref FROM assignments
                    WHERE id=%s FOR UPDATE""", (assignment_id,))
                assignment = cur.fetchone()
                cur.execute("""SELECT verification_id,decision FROM verification_records
                    WHERE assignment_id=%s ORDER BY recorded_at DESC,verification_id DESC LIMIT 1""",
                    (assignment_id,))
                latest = cur.fetchone()
                decision_key = (f"grace-rework-decision:{verification_id}" if review_generation == 1 else
                    f"grace-rework-decision:{verification_id}:review:{review_generation}")
                cur.execute("""SELECT payload FROM grace_objective_events
                    WHERE objective_id=%s AND idempotency_key=ANY(%s)""", (objective_id,
                    [decision_key] if review_generation > 1 else
                    [decision_key, f"grace-rejection-review:{verification_id}"]))
                decision = cur.fetchone()
                if (not objective or objective["status"] != "WORK_ORDER_CREATED" or
                        objective["assignment_id"] != assignment_id or not assignment or
                        assignment["objective_ref"] != objective_id or
                        assignment["state"] not in {"rework_required", "ready"} or
                        not latest or latest["decision"] != "REJECTED" or
                        str(latest["verification_id"]) != verification_id or not decision or
                        decision["payload"].get("verification_id") != verification_id):
                    raise ObjectiveStateError("current proposal-origin rejection decision is required")
                payload = {"assignment_id": assignment_id,
                    "verification_id": verification_id,
                    "request_id": request_id,
                    "decision": decision["payload"].get("decision"),
                    "review_generation": review_generation,
                    "runtime_release_id": self.runtime_release_id()}
                self._event(cur, objective_id, "engineering.rework_review_recorded", key,
                    "office:grace", payload)
                cur.execute("SELECT event_type,payload FROM grace_objective_events "
                    "WHERE objective_id=%s AND idempotency_key=%s", (objective_id, key))
                recorded = cur.fetchone()
                if (not recorded or recorded["event_type"] != "engineering.rework_review_recorded" or
                        recorded["payload"] != payload):
                    raise ObjectiveStateError("proposal-origin rework receipt idempotency conflict")
        return True

    def propose_continuation(self, objective_id, parent_assignment_id, step, *, actor_id="office:grace"):
        """Persist a model-proposed step only inside the accepted objective's exact scope."""
        from ..resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep
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
                raw.get("repository_revision") == step.repository_revision and
                raw.get("comfyui_workflow_id") == step.comfyui_workflow_id and
                raw.get("comfyui_parameters") == step.comfyui_parameters and
                raw.get("artifact_requirements", []) == [
                    {"name": item.name, "path": item.path, "media_type": item.media_type,
                     "acceptance_criteria": list(item.acceptance_criteria),
                     "max_bytes": item.max_bytes} for item in step.artifact_requirements])
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
                step.repository_reference, step.repository_revision,
                tuple(step.artifact_requirements), step.comfyui_workflow_id,
                step.comfyui_parameters)
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
                     item.get("repository_reference"), item.get("repository_revision"),
                     tuple(ArtifactRequirement(requirement["name"], requirement["path"],
                         requirement["media_type"], tuple(requirement["acceptance_criteria"]),
                         requirement.get("max_bytes", 32768))
                         for requirement in item.get("artifact_requirements", [])),
                     item.get("comfyui_workflow_id"), item.get("comfyui_parameters"))
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
