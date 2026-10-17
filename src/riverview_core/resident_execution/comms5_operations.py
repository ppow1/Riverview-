# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/comms5_operations.py
# Component: COMMS5-CURRENT-RUNTIME-OPERATIONS
# Revision: 1.0.1
# Purpose: Share authenticated Comms5 proposal operations with Riverview callers
# Execution Model: Request-driven; durable state remains in existing proposal/objective stores
# Observability: Proposal registry events and linked objective lifecycle events
# Dependencies: ProposalRegistry; ProposalLifecycle; GraceExecutionPipeline
# Authority: Ingress-attested Steward identity; objective promotion still requires exact objective.submit
# Changed: 2026-10-17 UTC | RV-COMMS5-OPERATIONS-20261017 | Initial current-runtime bridge
# Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Add full bounded objective and combined Steward submission projections.
# Contracts: docs/components/INSTITUTIONAL_PROPOSALS.md; Comms5 contract 5.0
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Shared current-runtime operation handlers; transport layers supply identity."""

from __future__ import annotations

from .proposals import ProposalConflict


class Comms5OperationError(RuntimeError):
    """A bounded operation failed without claiming a state transition."""


class Comms5OperationNotFound(Comms5OperationError):
    """A requested durable record does not exist."""


class Comms5Operations:
    """Operations over Riverview's authoritative proposal and objective services.

    The caller must provide an identity derived from authenticated transport
    attestation. User arguments named ``authenticated_principal`` are never used.
    """

    SUPPORTED = frozenset({
        "comms5_submit_steward_seed", "comms5_store_specification",
        "comms5_seed_status", "comms5_seed_lineage", "comms5_cancel_draft",
        "comms5_supersede_seed", "comms5_confirm_and_promote_seed",
        "comms5_objective_status", "comms5_recent_steward_submissions",
    })

    def __init__(self, proposal_registry, proposal_lifecycle, objective_pipeline=None):
        self.registry = proposal_registry
        self.lifecycle = proposal_lifecycle
        self.pipeline = objective_pipeline

    def create_draft_record(self, content, *, actor_id, origin_kind,
                            source_references, provenance, idempotency_key):
        """Single persistence path shared by Grace proposal drafting and Comms5."""
        actor = self._actor(actor_id)
        return self.registry.create_draft(content, created_by=actor,
            origin_kind=origin_kind, source_references=source_references,
            provenance=provenance, idempotency_key=idempotency_key)

    @staticmethod
    def _actor(principal_id):
        if (not isinstance(principal_id, str) or not principal_id.startswith("steward:")
                or len(principal_id) > 256):
            raise PermissionError("authenticated Steward principal required")
        return principal_id

    @staticmethod
    def _proposal_id(value):
        if not isinstance(value, str) or not value.startswith("proposal:"):
            raise ValueError("seed_id must reference a current proposal ID")
        return value

    @staticmethod
    def _idempotency(value):
        if (not isinstance(value, str) or not 1 <= len(value) <= 200
                or any(ord(char) < 33 or ord(char) > 126 for char in value)):
            raise ValueError("idempotency_key_out_of_bounds")
        return value

    @staticmethod
    def _receipt(result):
        proposal = result["proposal"]
        revision = result["revision"]
        return {"status": "available", "executed": True,
                "seed_id": proposal["proposal_id"],
                "proposal_id": proposal["proposal_id"],
                "revision": revision["revision"],
                "lifecycle_status": proposal["lifecycle_status"],
                "content_sha256": revision["content_sha256"]}

    def execute(self, tool, arguments, *, principal_id):
        actor = self._actor(principal_id)
        if tool not in self.SUPPORTED:
            raise ValueError("operation_not_supported")
        if tool == "comms5_submit_steward_seed":
            text = arguments.get("seed_text")
            if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 4000:
                raise ValueError("seed_text_out_of_bounds")
            title = text.strip().splitlines()[0][:200].strip() or "Steward seed"
            refs = ([{"specification_id": arguments["specification_id"]}]
                    if arguments.get("specification_id") else [])
            provenance = self._provenance(arguments)
            record = self.create_draft_record({
                "title": title, "summary": text.strip()[:1000], "objective": text.strip(),
                "scope": "Draft only; scope requires Grace and Steward review.",
                "proposed_approach": "Await Grace proposal development; no execution is authorized.",
                "constraints": ["Submission does not approve or dispatch work."],
                "acceptance_criteria": [], "tags": ["comms5", "steward-seed"]},
                actor_id=actor, origin_kind="steward_authored", source_references=refs,
                provenance=provenance, idempotency_key=arguments["idempotency_key"])
            return {**self._receipt(record), "status": "draft_saved", "executed": True}

        if tool == "comms5_objective_status":
            if self.pipeline is None:
                raise RuntimeError("objective_pipeline_unavailable")
            objective_id = arguments.get("objective_id")
            if (not isinstance(objective_id, str) or not objective_id.startswith("objective:")
                    or len(objective_id) > 140):
                raise ValueError("invalid_objective_id")
            objective = self.pipeline.get_objective(objective_id)
            if objective is None:
                raise Comms5OperationNotFound("objective_not_found")
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""SELECT step_id,step_order,depends_on,status,assignment_id,
                        dispatch_count,updated_at FROM grace_objective_steps
                    WHERE objective_id=%s ORDER BY step_order""", (objective_id,))
                steps = cur.fetchall()
            events = self.pipeline.objective_events(objective_id)
            evidence = objective.get("evidence") if isinstance(objective.get("evidence"), dict) else {}
            assignment_id = objective.get("assignment_id")
            assignment = self.pipeline.ledger.get(assignment_id) if assignment_id else None
            verification = None
            if assignment_id:
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""SELECT decision,verifier_revision,recorded_at AS created_at
                        FROM verification_records WHERE assignment_id=%s
                        ORDER BY verification_id DESC LIMIT 1""", (assignment_id,))
                    verification = cur.fetchone()
            # Include bounded execution-intent evidence from the existing worker
            # ledger. Never return prompts, credential digests, or result bodies.
            assignment_ids = list(dict.fromkeys(
                [assignment_id] + [row["assignment_id"] for row in steps
                                   if row.get("assignment_id")]))
            intents = []
            if assignment_ids:
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""SELECT DISTINCT ON (assignment_id) assignment_id,
                            worker_id,lease_generation,capability,effect_class,status,
                            attempt_id,started_at,finished_at,failure_class
                        FROM worker_execution_intents WHERE assignment_id=ANY(%s)
                        ORDER BY assignment_id,started_at DESC,intent_id DESC""",
                        (assignment_ids,))
                    intents = cur.fetchall()
            authority = self._current_objective_authority(objective)
            return {"status": "available", "executed": True,
                "objective": {"objective_id": objective_id, "state": objective["status"],
                    "scope_ref": objective["scope_ref"], "submitter_id": objective["submitter_id"],
                    "revision": objective["revision"], "assignment_id": assignment_id,
                    "source_revision": objective.get("source_revision"),
                    "source_sha256": objective.get("source_sha256"),
                    "created_at": objective["created_at"].isoformat(),
                    "updated_at": objective["updated_at"].isoformat(),
                    "evidence": {"status": evidence.get("status"),
                        "source_reference_count": len(evidence.get("source_references", [])),
                        "source_revision": evidence.get("source_revision"),
                        "source_sha256": evidence.get("source_sha256"),
                        "retrieval_complete": evidence.get("retrieval_complete"),
                    "error_code": evidence.get("error_code")}},
                "submission_authority": authority,
                "assignment": ({key: assignment.get(key) for key in
                    ("id", "state", "owner", "workflow_id", "workflow_step", "correlation_id")}
                    if assignment else None),
                "steps": [{"step_id": row["step_id"], "order": row["step_order"],
                    "depends_on": row["depends_on"], "state": row["status"],
                    "assignment_id": row["assignment_id"], "dispatch_count": row["dispatch_count"],
                    "updated_at": row["updated_at"].isoformat()} for row in steps],
                "verification": ({key: verification[key].isoformat() if hasattr(verification[key], "isoformat")
                    else verification[key] for key in ("decision", "verifier_revision", "created_at")}
                    if verification else None),
                "execution_intents": [{key: (row[key].isoformat() if hasattr(row[key], "isoformat")
                    else str(row[key]) if key == "attempt_id" and row[key] is not None else row[key])
                    for key in ("assignment_id", "worker_id", "lease_generation", "capability",
                        "effect_class", "status", "attempt_id", "started_at", "finished_at",
                        "failure_class")} for row in intents],
                "event_lineage": [{"event_type": row["event_type"],
                    "actor_id": row["actor_id"], "occurred_at": row["occurred_at"].isoformat()}
                    for row in events]}

        if tool == "comms5_recent_steward_submissions":
            limit = arguments.get("limit", 20)
            if type(limit) is not int or not 1 <= limit <= 100:
                raise ValueError("invalid_limit")
            fetch_limit = min(100, limit + 1)
            items = []
            if self.pipeline is not None:
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""SELECT objective_id AS record_id,'objective' AS record_type,
                            status AS lifecycle_status,submitter_id AS created_by,
                            created_at,updated_at,assignment_id
                        FROM grace_objectives WHERE submitter_id LIKE %s
                        ORDER BY updated_at DESC,objective_id LIMIT %s""", ("steward:%", fetch_limit))
                    items.extend({**row, "record_id": row["record_id"],
                        "updated_at": row["updated_at"].isoformat(),
                        "created_at": row["created_at"].isoformat()} for row in cur.fetchall())
            proposal_page = self.registry.search("", created_by_prefix="steward:",
                limit=fetch_limit)
            items.extend({"record_id": row["proposal_id"], "record_type": "proposal",
                "lifecycle_status": row["lifecycle_status"], "created_by": row["created_by"],
                "updated_at": row["updated_at"], "current_revision": row["current_revision"],
                "privacy_classification": row["privacy_classification"]}
                for row in proposal_page["items"])
            items.sort(key=lambda item: item["updated_at"], reverse=True)
            truncated = len(items) > limit or (limit == 100 and len(items) == 100)
            return {"status": "available", "executed": True,
                "source": "authoritative_objective_and_proposal_registries",
                "items": items[:limit], "limit": limit,
                "truncated": truncated}

        if tool == "comms5_store_specification":
            content = arguments.get("content")
            summary = arguments.get("summary")
            if (not isinstance(content, str) or not content.strip() or len(content.encode("utf-8")) > 4000
                    or not isinstance(summary, str) or not summary.strip() or len(summary) > 1000):
                raise ValueError("specification_content_out_of_bounds")
            form = arguments.get("formation_contract") or {}
            allowed_form = {"repository_identity", "repository_root", "expected_base_sha",
                "bounded_instruction", "allowed_paths", "acceptance_criteria",
                "evidence_requirements", "capability_name", "action_type",
                "timeout_seconds", "write_policy"}
            if (not isinstance(form, dict) or set(form) - allowed_form
                    or len(str(form).encode("utf-8")) > 4096
                    or any(not isinstance(form.get(key, ""), str)
                           for key in ("repository_identity", "repository_root", "expected_base_sha",
                                       "bounded_instruction", "capability_name", "action_type", "write_policy"))
                    or any(not isinstance(form.get(key, []), list)
                           or any(not isinstance(item, str) for item in form.get(key, []))
                           for key in ("allowed_paths", "acceptance_criteria", "evidence_requirements"))
                    or type(form.get("timeout_seconds", 0)) is not int):
                raise ValueError("formation_contract_out_of_bounds")
            # A formation contract is retained as proposal provenance only. It is
            # never interpreted as permission or dispatched by this operation.
            provenance = self._provenance(arguments)
            provenance["formation_contract"] = form
            refs = []
            if arguments.get("correlation_id"):
                refs.append({"correlation_id": arguments["correlation_id"]})
            record = self.create_draft_record({
                "title": content.strip().splitlines()[0][:200] or "Steward specification",
                "summary": summary.strip(), "objective": content.strip(),
                "scope": "Draft specification; execution scope remains subject to review and approval.",
                "proposed_approach": "Grace review and formalization required before any execution.",
                "constraints": ["Stored formation fields are advisory and do not authorize execution."],
                "acceptance_criteria": list(form.get("acceptance_criteria", []))
                    if isinstance(form.get("acceptance_criteria", []), list) else [],
                "tags": ["comms5", "specification"]},
                actor_id=actor, origin_kind="steward_authored", source_references=refs,
                provenance=provenance, idempotency_key=arguments["idempotency_key"])
            return {**self._receipt(record), "status": "specification_stored", "executed": True}

        if tool in {"comms5_seed_status", "comms5_seed_lineage"}:
            proposal_id = self._proposal_id(arguments.get("seed_id"))
            record = self.registry.get(proposal_id)
            if tool == "comms5_seed_status":
                return {**self._receipt(record), "proposal": record["proposal"],
                        "revision_record": record["revision"],
                        "work_order_links": record["work_order_links"], "executed": True}
            return {"status": "available", "executed": True, "seed_id": proposal_id,
                    "proposal_id": proposal_id,
                    "events": [{"event_id": item["event_id"], "revision": item["revision"],
                        "event_type": item["event_type"], "actor_id": item["actor_id"],
                        "occurred_at": item["occurred_at"]} for item in record["events"]],
                    "reviews": record["reviews"], "work_order_links": record["work_order_links"]}

        if tool == "comms5_cancel_draft":
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            proposal_id = self._proposal_id(arguments.get("seed_id"))
            current = self.registry.get(proposal_id)
            record = self.registry.transition(proposal_id, current["revision"]["revision"],
                "ARCHIVED", actor_id=actor, reason=arguments["reason"],
                idempotency_key="comms5-cancel:" + self._idempotency(arguments["idempotency_key"]))
            return {**self._receipt(record), "status": "draft_cancelled", "executed": True}

        if tool == "comms5_supersede_seed":
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            proposal_id = self._proposal_id(arguments.get("seed_id"))
            replacement_id = self._proposal_id(arguments.get("replacement_seed_id"))
            replacement = self.registry.get(replacement_id)
            if replacement["proposal"]["lifecycle_status"] != "DRAFT":
                raise ProposalConflict("replacement must be an unreviewed draft")
            current = self.registry.get(proposal_id)
            record = self.registry.transition(proposal_id, current["revision"]["revision"],
                "SUPERSEDED", actor_id=actor, reason=arguments["reason"],
                idempotency_key="comms5-supersede:" + self._idempotency(arguments["idempotency_key"]),
                related_proposal_id=replacement_id)
            return {**self._receipt(record), "replacement_seed_id": replacement_id,
                    "status": "superseded", "executed": True}

        if tool == "comms5_confirm_and_promote_seed":
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            proposal_id = self._proposal_id(arguments.get("seed_id"))
            current = self.registry.get(proposal_id)
            revision = current["revision"]["revision"]
            if current["proposal"]["lifecycle_status"] == "READY_FOR_STEWARD_DECISION":
                if any(item["review_outcome"] != "NO_OBJECTION"
                       for item in current["reviews"]):
                    raise ProposalConflict("resolve review outcomes and conditions through the review workflow first")
                if len(current["revision"]["objective"]) > 963:
                    raise ProposalConflict("proposal objective exceeds approval-purpose limit")
                self.lifecycle.decide(proposal_id, revision, decision="APPROVE", actor_id=actor,
                    reason="Explicit authenticated Comms5 Steward confirmation",
                    idempotency_key="comms5-approval:" + self._idempotency(arguments["idempotency_key"]),
                    content_sha256=current["revision"]["content_sha256"],
                    approved_purpose=("Engineering work-order intake for: "
                        + current["revision"]["objective"]),
                    authority_reference="comms5-ingress:steward")
                current = self.registry.get(proposal_id, revision=revision)
            elif current["proposal"]["lifecycle_status"] != "APPROVED":
                raise ProposalConflict("proposal must be ready for Steward decision or already approved")
            # Intake rechecks the existing exact objective.submit grant. Approval
            # remains durable if intake is not authorized; no work is dispatched here.
            try:
                result = self.lifecycle.promote(proposal_id, revision, actor_id=actor)
            except Exception as exc:
                from .pipeline import ObjectiveNotAuthorized
                if isinstance(exc, ObjectiveNotAuthorized):
                    return {"status": "approved_not_promoted", "executed": True,
                        "proposal_id": proposal_id, "proposal_revision": revision,
                        "approval_recorded": True, "work_order_created": False,
                        "missing_prerequisite": "objective.submit"}
                raise
            return {"status": result["status"], "executed": True,
                    "proposal_id": proposal_id, "proposal_revision": current["revision"]["revision"],
                    **result}

        raise ValueError("operation_not_supported")

    @staticmethod
    def _provenance(arguments):
        keys = ("client_id", "client_type", "client_name", "client_version",
                "protocol_version", "correlation_id", "causation_id", "classification")
        return {"source": "authenticated_comms5", "contract": "riverview-comms-contract:5.0",
                "client": {key: arguments[key] for key in keys if arguments.get(key)}}

    def _current_objective_authority(self, objective):
        """Report present exact-grant readiness without inventing historical grants."""
        principal = objective.get("submitter_id")
        scope = objective.get("scope_ref")
        if not self.pipeline or not isinstance(principal, str) or not isinstance(scope, str):
            return {"status": "unavailable"}
        from ..institutional_authority import GrantCheckUnavailable, GrantDenied
        try:
            with self.pipeline.ledger.db.transaction():
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    grant = self.pipeline.authorizer.require_principal(
                        cur, principal, "objective.submit", scope)
        except GrantDenied:
            return {"status": "not_currently_authorized", "principal_id": principal,
                    "action": "objective.submit", "scope_ref": scope}
        except GrantCheckUnavailable:
            raise
        return {"status": "currently_authorized", "principal_id": principal,
                "action": "objective.submit", "scope_ref": scope,
                "grant_id": grant["grant_id"]}
