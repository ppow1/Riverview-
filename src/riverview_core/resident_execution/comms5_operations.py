# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/comms5_operations.py
# Component: COMMS5-CURRENT-RUNTIME-OPERATIONS
# Revision: 1.1.1
# Purpose: Share authenticated Comms5 proposal operations with Riverview callers
# Execution Model: Request-driven; durable state remains in existing proposal/objective stores
# Observability: Proposal registry events and linked objective lifecycle events
# Dependencies: ProposalRegistry; ProposalLifecycle; GraceExecutionPipeline
# Authority: Ingress-attested Steward identity; objective promotion still requires exact objective.submit
# Changed: 2026-10-17 UTC | RV-COMMS5-OPERATIONS-20261017 | Initial current-runtime bridge
# Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Add full bounded objective and combined Steward submission projections.
# Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Add an authenticated read projection for real worker capability inventory and explicitly unset policy state.
# Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Persist exact-grant-checked, idempotent Steward queue requests for CME without claiming assignment dispatch.
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Require fresh trusted repository grounding for stale-base rework and preserve dependency/completion semantics.
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Make repeated policy transitions auditable after intervening changes without losing retry safety.
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Route four advisory exchange tools through an explicit authenticated Steward bridge.
# Changed: 2026-10-26 UTC | COMMS5-OPERATIONAL-COMMAND-EXECUTION | Add exact-host-grant task submit/status without project-grant shell authorization.
# Contracts: docs/components/INSTITUTIONAL_PROPOSALS.md; Comms5 contract 5.0
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Shared current-runtime operation handlers; transport layers supply identity."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from ..institutional_authority.grants import InstitutionalPrincipal


_UNSET = object()
from ..comms5.delegation_policy import is_delegable_tool

HOST_SCOPED_COMMAND_TOOLS = frozenset({
    "comms5_command_submit", "comms5_command_status",
    "comms5_command_task_submit", "comms5_command_task_status",
})

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
        "comms5_revise_specification",
        "comms5_prepare_proposal_for_decision",
        "comms5_seed_status", "comms5_seed_lineage", "comms5_cancel_draft",
        "comms5_supersede_seed", "comms5_confirm_and_promote_seed",
        "comms5_resource_policy_status", "comms5_form_and_queue_work",
        "comms5_objective_status", "comms5_recent_steward_submissions",
        "comms5_revalidate_and_queue_work", "comms5_set_resource_policy",
        "comms5_set_resource_policy_lock",
        "comms5_authorize_grace_experiment",
        "comms5_amend_grace_experiment",
        "comms5_authorize_grace_supervision",
        "comms5_grace_supervision_status",
        "comms5_revoke_grace_supervision",
        "comms5_submit_direct_engineering_task",
        "comms5_request_delegation_grant", "comms5_get_delegation_grant_status",
        "comms5_revoke_delegation_grant", "comms5_request_delegation_grant_change",
        "comms5_command_submit", "comms5_command_status",
        "comms5_command_task_submit", "comms5_command_task_status",
        "reasoning_exchange_list_requests", "reasoning_exchange_claim_request",
        "reasoning_exchange_submit_response", "reasoning_exchange_status",
    })

    DELEGATION_OPERATION_IDS = {
        "comms5_request_delegation_grant": "comms5.delegation_grant.request",
        "comms5_get_delegation_grant_status": "comms5.delegation_grant.status.read",
        "comms5_revoke_delegation_grant": "comms5.delegation_grant.surrender",
        "comms5_request_delegation_grant_change": "comms5.delegation_grant.change.request",
    }

    def __init__(self, proposal_registry, proposal_lifecycle, objective_pipeline=None,
                 steward_review_bridge=None, authority_registry=None,
                 delegation_grant_requests=None):
        self.registry = proposal_registry
        self.lifecycle = proposal_lifecycle
        self.pipeline = objective_pipeline
        self.steward_review_bridge = steward_review_bridge
        self.authority_registry = authority_registry
        self.delegation_grant_requests = delegation_grant_requests

    def create_draft_record(self, content, *, actor_id, origin_kind,
                            source_references, provenance, idempotency_key,
                            delegated_authorized=False):
        """Single persistence path shared by Grace proposal drafting and Comms5."""
        actor = self._attested_grantee(actor_id) if delegated_authorized else self._actor(actor_id)
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
    def _attested_grantee(principal_id):
        if (not isinstance(principal_id, str) or len(principal_id) > 256 or
                not re.fullmatch(r"(?:steward|resident|human|service|worker):[A-Za-z0-9._:@-]{1,240}",
                                 principal_id)):
            raise PermissionError("authenticated grantee principal required")
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
    def _delegation_action(value):
        if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value)
                or "*" in value or value in {"authority.grant", "identity.manage", "office.manage"}):
            raise ValueError("delegated_action_must_be_exact_and_non_management")
        return value

    @staticmethod
    def _delegation_scope(value):
        if not isinstance(value, str) or not re.fullmatch(
                r"(?:project:[A-Za-z0-9._-]{1,128}|issue:[A-Za-z0-9._-]{1,128}/[A-Za-z0-9._-]{1,128}|host:[a-z][a-z0-9-]{1,62})", value):
            raise ValueError("delegation_scope_must_be_project_issue_or_registered_host")
        return value

    @staticmethod
    def _delegation_validity(arguments, *, allow_preserve=False):
        max_uses = (_UNSET if allow_preserve and "max_uses" not in arguments
                    else arguments.get("max_uses"))
        if (max_uses is not _UNSET and max_uses is not None and
                (type(max_uses) is not int or not 1 <= max_uses <= 1_000_000)):
            raise ValueError("delegation_max_uses_invalid")
        valid_until = (_UNSET if allow_preserve and "valid_until" not in arguments
                       else arguments.get("valid_until"))
        if valid_until is not None and valid_until is not _UNSET:
            if not isinstance(valid_until, str) or len(valid_until) > 64:
                raise ValueError("delegation_expiry_invalid")
            try:
                valid_until = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("delegation_expiry_invalid") from None
            if valid_until.tzinfo is None or valid_until <= datetime.now(timezone.utc):
                raise ValueError("delegation_expiry_must_be_future_and_timezone_aware")
        duration_spec = arguments.get("duration_spec")
        if duration_spec is not None:
            from ..institutional_authority.registry import normalize_grant_duration
            duration_spec = normalize_grant_duration(duration_spec)
            if valid_until is not None and valid_until is not _UNSET:
                raise ValueError("delegation_duration_and_absolute_expiry_are_mutually_exclusive")
        if (max_uses is None and valid_until is None and duration_spec is None
                and not allow_preserve):
            raise ValueError("delegation_grant_requires_use_limit_or_expiry")
        return max_uses, valid_until, duration_spec

    def _delegation_request_service(self):
        if self.delegation_grant_requests is None:
            raise RuntimeError("delegation_grant_request_service_unavailable")
        return self.delegation_grant_requests

    @staticmethod
    def _delegation_reason(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError("delegation_request_reference_invalid")
        return value.strip()

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

    def execute(self, tool, arguments, *, principal_id, delegated_authorized=False):
        if type(delegated_authorized) is not bool:
            raise ValueError("delegated_authorization_context_invalid")
        if delegated_authorized and not (is_delegable_tool(tool) or
                tool == "comms5_revoke_delegation_grant" or
                tool in HOST_SCOPED_COMMAND_TOOLS):
            raise PermissionError("Comms5 operation is excluded from delegated authority")
        actor = self._attested_grantee(principal_id) if delegated_authorized else self._actor(principal_id)
        if tool not in self.SUPPORTED:
            raise ValueError("operation_not_supported")
        if tool in HOST_SCOPED_COMMAND_TOOLS:
            if self.pipeline is None or self.authority_registry is None:
                raise RuntimeError("command_gateway_authority_unavailable")
            from ..comms5.command_gateway import WindowsCommandGateway
            gateway = WindowsCommandGateway.from_environment(
                authority_registry=self.authority_registry,
                authorizer=self.pipeline.authorizer,
                ledger_db=self.pipeline.ledger.db,
                command_grant_authority=self.delegation_grant_requests)
            if tool == "comms5_command_submit":
                return gateway.submit(actor, arguments)
            if tool == "comms5_command_status":
                return gateway.status(actor, arguments)
            if tool == "comms5_command_task_submit":
                return gateway.submit_task(actor, arguments)
            return gateway.task_status(actor, arguments)
        if tool == "comms5_authorize_grace_experiment":
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            if self.pipeline is None or self.authority_registry is None:
                raise RuntimeError("experiment_authorization_unavailable")
            if set(arguments) != {"objective_id", "objective_revision",
                                  "explicit_steward_confirmation", "idempotency_key"}:
                raise ValueError("experiment_authorization_fields_invalid")
            from .grace_experiment_authorization import GraceExperimentAuthorization
            return GraceExperimentAuthorization(self.pipeline, self.authority_registry).activate(
                actor_id=actor, objective_id=arguments["objective_id"],
                revision=arguments["objective_revision"],
                idempotency_key=self._idempotency(arguments["idempotency_key"]))
        if tool == "comms5_amend_grace_experiment":
            required = {"authorization_id", "objective_id", "objective_revision",
                "expected_max_luna_requests", "new_max_luna_requests",
                "expected_used_luna_requests", "expected_used_recoveries",
                "expected_cumulative_spend_usd", "total_budget_usd", "expires_at",
                "explicit_steward_confirmation", "idempotency_key"}
            if set(arguments) != required:
                raise ValueError("experiment_amendment_fields_invalid")
            if arguments["explicit_steward_confirmation"] is not True:
                raise PermissionError("explicit Steward confirmation is required")
            if self.pipeline is None or self.authority_registry is None:
                raise RuntimeError("experiment_authorization_unavailable")
            from .grace_experiment_authorization import GraceExperimentAuthorization
            values = {key: value for key, value in arguments.items()
                      if key not in {"idempotency_key", "explicit_steward_confirmation"}}
            values["revision"] = values.pop("objective_revision")
            return GraceExperimentAuthorization(self.pipeline, self.authority_registry).amend_luna_request_limit(
                actor_id=actor, explicit_steward_confirmation=True,
                idempotency_key=self._idempotency(arguments["idempotency_key"]), **values)
        if tool == "comms5_authorize_grace_supervision":
            required = {"total_budget_usd", "per_request_limit_usd",
                        "explicit_steward_confirmation", "idempotency_key"}
            if not required.issubset(arguments) or set(arguments) - required - {"expires_at"}:
                raise ValueError("grace_supervisory_authorization_fields_invalid")
            if arguments["explicit_steward_confirmation"] is not True:
                raise PermissionError("explicit Steward confirmation is required")
            if self.pipeline is None or self.authority_registry is None:
                raise RuntimeError("grace_supervisory_authorization_unavailable")
            from .grace_supervisory_authorization import GraceSupervisoryAuthorization
            return GraceSupervisoryAuthorization(self.pipeline, self.authority_registry).authorize(
                actor_id=actor, total_budget_usd=arguments["total_budget_usd"],
                per_request_limit_usd=arguments["per_request_limit_usd"],
                explicit_steward_confirmation=arguments["explicit_steward_confirmation"],
                idempotency_key=self._idempotency(arguments["idempotency_key"]),
                expires_at=arguments.get("expires_at"))
        if tool == "comms5_grace_supervision_status":
            if arguments:
                raise ValueError("grace_supervisory_status_arguments_invalid")
            if self.pipeline is None or self.authority_registry is None:
                raise RuntimeError("grace_supervisory_authorization_unavailable")
            from .grace_supervisory_authorization import GraceSupervisoryAuthorization
            return GraceSupervisoryAuthorization(self.pipeline, self.authority_registry).status()
        if tool == "comms5_revoke_grace_supervision":
            required = {"authorization_id", "explicit_steward_confirmation", "idempotency_key"}
            if set(arguments) != required:
                raise ValueError("grace_supervisory_revocation_fields_invalid")
            if self.pipeline is None or self.authority_registry is None:
                raise RuntimeError("grace_supervisory_authorization_unavailable")
            from .grace_supervisory_authorization import GraceSupervisoryAuthorization
            return GraceSupervisoryAuthorization(self.pipeline, self.authority_registry).revoke(
                actor_id=actor, authorization_id=arguments["authorization_id"],
                explicit_steward_confirmation=arguments["explicit_steward_confirmation"],
                idempotency_key=self._idempotency(arguments["idempotency_key"]))
        if tool == "comms5_request_delegation_grant":
            required = {"principal_id", "action", "scope_ref", "policy_ref", "request_ref", "idempotency_key"}
            optional = {"max_uses", "valid_until", "duration_spec"}
            if not required <= set(arguments) or set(arguments) - required - optional:
                raise ValueError("delegation_grant_request_fields_invalid")
            if (not isinstance(arguments["principal_id"], str) or
                    not 1 <= len(arguments["principal_id"]) <= 256 or
                    not isinstance(arguments["policy_ref"], str) or
                    not re.fullmatch(r"policy:[A-Za-z0-9._:-]{1,128}", arguments["policy_ref"])):
                raise ValueError("delegation_grant_request_identity_invalid")
            max_uses, valid_until, duration_spec = self._delegation_validity(arguments)
            return self._delegation_request_service().request_grant(
                requester_id=actor, principal_id=arguments["principal_id"],
                action=self._delegation_action(arguments["action"]),
                scope_ref=self._delegation_scope(arguments["scope_ref"]),
                policy_ref=arguments["policy_ref"], max_uses=max_uses,
                valid_until=valid_until, duration_spec=duration_spec,
                request_ref=self._delegation_reason(arguments["request_ref"]),
                idempotency_key=self._idempotency(arguments["idempotency_key"]))
        if tool == "comms5_get_delegation_grant_status":
            if set(arguments) not in ({"request_id"}, {"grant_id"}):
                raise ValueError("delegation_status_requires_one_exact_id")
            identifier_name = "request_id" if "request_id" in arguments else "grant_id"
            identifier = arguments[identifier_name]
            if not isinstance(identifier, str) or not 1 <= len(identifier) <= 128:
                raise ValueError("delegation_status_identity_invalid")
            return self._delegation_request_service().get_status(
                requester_id=actor, **{identifier_name: identifier})
        if tool == "comms5_revoke_delegation_grant":
            required = {"grant_id", "idempotency_key"}
            optional = {"reason_code"}
            if not required <= set(arguments) or set(arguments) - required - optional:
                raise ValueError("delegation_surrender_fields_invalid")
            grant_id = arguments["grant_id"]
            if not isinstance(grant_id, str) or not 1 <= len(grant_id) <= 128:
                raise ValueError("delegation_grant_identity_invalid")
            reason_code = arguments.get("reason_code", "grantee_surrendered")
            if not isinstance(reason_code, str) or not re.fullmatch(r"[a-z0-9_]{1,64}", reason_code):
                raise ValueError("delegation_surrender_reason_invalid")
            return self._delegation_request_service().surrender_grant(
                grantee_id=actor, grant_id=grant_id, reason_code=reason_code,
                idempotency_key=self._idempotency(arguments["idempotency_key"]))
        if tool == "comms5_request_delegation_grant_change":
            required = {"grant_id", "action", "scope_ref", "policy_ref", "request_ref", "idempotency_key"}
            optional = {"max_uses", "valid_until", "duration_spec", "change_kind"}
            if not required <= set(arguments) or set(arguments) - required - optional:
                raise ValueError("delegation_grant_change_fields_invalid")
            if (not isinstance(arguments["grant_id"], str) or
                    not 1 <= len(arguments["grant_id"]) <= 128 or
                    not isinstance(arguments["policy_ref"], str) or
                    not re.fullmatch(r"policy:[A-Za-z0-9._:-]{1,128}", arguments["policy_ref"])):
                raise ValueError("delegation_grant_change_identity_invalid")
            max_uses, valid_until, duration_spec = self._delegation_validity(
                arguments, allow_preserve=True)
            change = {}
            if max_uses is not _UNSET:
                change["max_uses"] = max_uses
            if valid_until is not _UNSET:
                change["valid_until"] = valid_until
            return self._delegation_request_service().request_change(
                requester_id=actor, grant_id=arguments["grant_id"],
                action=self._delegation_action(arguments["action"]),
                scope_ref=self._delegation_scope(arguments["scope_ref"]),
                policy_ref=arguments["policy_ref"], duration_spec=duration_spec,
                change_kind=arguments.get("change_kind"),
                request_ref=self._delegation_reason(arguments["request_ref"]),
                idempotency_key=self._idempotency(arguments["idempotency_key"]), **change)
        if tool.startswith("reasoning_exchange_"):
            if self.steward_review_bridge is None:
                raise RuntimeError("external_reasoning_exchange_unavailable")
            return self.steward_review_bridge.call_tool(actor, tool, arguments)
        if tool == "comms5_revise_specification":
            proposal_id = self._proposal_id(arguments.get("proposal_id"))
            expected_revision = arguments.get("expected_revision")
            if type(expected_revision) is not int or expected_revision < 1:
                raise ValueError("expected_revision_invalid")
            idem = self._idempotency(arguments.get("idempotency_key"))
            content = arguments.get("content")
            current = self.registry.get(proposal_id)
            if current["proposal"]["lifecycle_status"] != "DRAFT":
                raise ProposalConflict("only a draft proposal can be revised through Comms5")
            digest = self.registry._digest(content)
            event_key = "comms5-revision:" + hashlib.sha256(
                (actor + "\\0" + idem).encode("utf-8")).hexdigest()
            if current["proposal"]["current_revision"] != expected_revision:
                prior = next((event for event in reversed(current["events"])
                    if event.get("event_type") == "proposal.revised"
                    and event.get("idempotency_key") == event_key), None)
                if prior and prior.get("payload", {}).get("content_sha256") == digest:
                    return {**self._receipt(current), "status": "revision_reused",
                            "executed": True}
                raise ProposalConflict("proposal revision changed")
            record = self.registry.revise(proposal_id, expected_revision, content,
                actor_id=actor,
                provenance={"source": "authenticated_comms5", "contract": "riverview-comms-contract:5.0",
                    "client": self._provenance(arguments)["client"]},
                idempotency_key=event_key)
            return {**self._receipt(record), "status": "revised", "executed": True}

        if tool == "comms5_prepare_proposal_for_decision":
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            proposal_id = self._proposal_id(arguments.get("proposal_id"))
            revision = arguments.get("expected_revision")
            digest = arguments.get("expected_content_sha256")
            if (type(revision) is not int or revision < 1 or not isinstance(digest, str)
                    or not re.fullmatch(r"[a-f0-9]{64}", digest)):
                raise ValueError("proposal_revision_binding_invalid")
            idem = self._idempotency(arguments.get("idempotency_key"))
            record = self.registry.get(proposal_id, revision=revision)
            current = record["proposal"]
            content = record["revision"]
            if (current["current_revision"] != revision or
                    content["content_sha256"] != digest):
                raise ProposalConflict("proposal revision or digest changed")
            if current["lifecycle_status"] == "DRAFT":
                record = self.registry.transition(proposal_id, revision, "READY_FOR_REVIEW",
                    actor_id=actor, reason="Authenticated Comms5 Steward submitted exact revision for decision",
                    idempotency_key="comms5-ready-review:" + hashlib.sha256(
                        (actor + "\\0" + idem).encode()).hexdigest())
                current = record["proposal"]
            if current["lifecycle_status"] == "READY_FOR_REVIEW":
                record = self.registry.transition(proposal_id, revision, "READY_FOR_STEWARD_DECISION",
                    actor_id=actor, reason="Authenticated Comms5 Steward marked exact revision ready for Steward decision",
                    idempotency_key="comms5-ready-decision:" + hashlib.sha256(
                        (actor + "\\0" + idem).encode()).hexdigest())
            elif current["lifecycle_status"] != "READY_FOR_STEWARD_DECISION":
                raise ProposalConflict("proposal is not eligible for Steward decision")
            return {**self._receipt(record), "status": "ready_for_steward_decision",
                    "executed": True, "approval_recorded": False}
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
                provenance=provenance, idempotency_key=arguments["idempotency_key"],
                delegated_authorized=delegated_authorized)
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

        if tool == "comms5_submit_direct_engineering_task":
            required = {"task", "repository_reference", "repository_revision",
                "authorized_paths", "test_targets", "acceptance_criteria",
                "evidence_requirements", "idempotency_key"}
            if set(arguments) != required or self.pipeline is None:
                raise ValueError("direct_engineering_task_fields_invalid")
            task, repository, revision = (arguments["task"], arguments["repository_reference"],
                                          arguments["repository_revision"])
            paths, tests = arguments["authorized_paths"], arguments["test_targets"]
            criteria, evidence = arguments["acceptance_criteria"], arguments["evidence_requirements"]
            idem = self._idempotency(arguments["idempotency_key"])
            if (not isinstance(task, str) or not task.strip() or len(task.encode("utf-8")) > 4000
                    or not isinstance(repository, str) or not re.fullmatch(r"repo://[A-Za-z0-9._/-]{1,240}", repository)
                    or not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision)
                    or not isinstance(paths, list) or not 1 <= len(paths) <= 32
                    or any(not isinstance(path, str) or not re.fullmatch(r"(?:src|tests|docs)/[A-Za-z0-9._/-]{1,240}", path)
                           or ".." in path.split("/") or ".git" in path.split("/") for path in paths)
                    or len(set(paths)) != len(paths)
                    or not isinstance(tests, list) or not 1 <= len(tests) <= 32
                    or any(not isinstance(path, str) or not path.startswith("tests/") for path in tests)
                    or not set(tests) <= set(paths)
                    or not isinstance(criteria, list) or not 1 <= len(criteria) <= 20
                    or any(not isinstance(item, str) or not item.strip() or len(item) > 1000 for item in criteria)
                    or len(set(criteria)) != len(criteria)
                    or not isinstance(evidence, list) or not 1 <= len(evidence) <= 20
                    or any(not isinstance(item, str) or not item.strip() or len(item) > 1000 for item in evidence)):
                raise ValueError("direct_engineering_task_out_of_bounds")
            if self.pipeline.authorizer is None:
                raise RuntimeError("direct_engineering_authorizer_unavailable")
            from uuid import NAMESPACE_URL, uuid5
            objective_id = "objective:" + str(uuid5(NAMESPACE_URL,
                "riverview-comms5-direct-engineering:" + actor + ":" + idem))
            request = (task.strip() + "\nTarget repository: " + repository + " at " + revision
                + "\nAuthorized paths: " + ", ".join(paths) + "\nTest targets: " + ", ".join(tests)
                + "\nRequired evidence: " + "; ".join(item.strip() for item in evidence))
            existing = self.pipeline.get_objective(objective_id)
            created = existing is None
            if created:
                self.pipeline.submit_objective(objective_id, request, criteria,
                    scope_ref="work-order:engineering", principal=InstitutionalPrincipal(actor),
                    criteria_source="steward_supplied")
                existing = self.pipeline.get_objective(objective_id)
            elif (existing.get("submitter_id") != actor or existing.get("scope_ref") != "work-order:engineering"
                    or existing.get("request") != request or existing.get("acceptance_criteria") != criteria):
                raise ProposalConflict("direct-dispatch idempotency key is bound to different input")
            if existing.get("status") in {"RECEIVED", "WAITING_FOR_EVIDENCE"}:
                try:
                    existing = self.pipeline.ground_objective(objective_id)
                except Exception as exc:
                    from .pipeline import ObjectiveStateError
                    if not isinstance(exc, ObjectiveStateError):
                        raise
                    existing = self.pipeline.get_objective(objective_id)
                    if not existing or existing.get("status") != "WAITING_FOR_EVIDENCE":
                        raise
                    return {"status":"waiting_for_evidence", "executed":True,
                        "objective_id":objective_id,
                        "evidence_status":(existing.get("evidence") or {}).get("status"),
                        "idempotent":not created}
            if existing.get("status") == "GROUNDED":
                verified = existing.get("evidence") or {}
                if (verified.get("status") != "VERIFIED" or verified.get("retrieval_complete") is not True
                        or not verified.get("source_references")):
                    raise ProposalConflict("verified grounding evidence is incomplete")
                from ..resident_reasoning import PlanProposal, PlanStep
                proposal = PlanProposal(task.strip()[:4000], (PlanStep(
                    "direct-engineering", (task.strip() + "\nRequired evidence: " + "; ".join(evidence))[:4000],
                    tuple(criteria), execution_capability="engineering.codex-cli-source-change.v1",
                    authorized_paths=tuple(paths), test_targets=tuple(tests),
                    repository_reference=repository, repository_revision=revision),), 0)
                self.pipeline.record_proposal(objective_id, proposal, actor_id=actor)
                existing = self.pipeline.get_objective(objective_id)
            if existing.get("status") == "PROPOSED":
                event_key = "comms5-direct-dispatch:" + hashlib.sha256((actor + "\0" + idem).encode()).hexdigest()
                with self.pipeline.ledger.db.transaction():
                    with self.pipeline.ledger.db.cursor() as cur:
                        self.pipeline.ledger._set_search_path(cur)
                        self.pipeline._event(cur, objective_id, "comms5.direct_codex_dispatch_submitted",
                                             event_key, actor, {"repository_reference":repository,
                            "repository_revision":revision,"authorized_path_count":len(paths),
                            "test_target_count":len(tests),"evidence_requirement_count":len(evidence)})
                return {"status":"submitted", "executed":True,"objective_id":objective_id,
                        "work_order_status":"awaiting_existing_dispatcher","idempotent":not created}
            if existing.get("status") == "WORK_ORDER_CREATED":
                return {"status":"already_dispatched", "executed":True,"objective_id":objective_id,
                        "assignment_id":existing.get("assignment_id"),"idempotent":True}
            return {"status":"waiting_for_evidence", "executed":True,"objective_id":objective_id,
                    "evidence_status":(existing.get("evidence") or {}).get("status"),"idempotent":True}

        if tool == "comms5_form_and_queue_work":
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            if self.pipeline is None:
                raise RuntimeError("objective_pipeline_unavailable")
            objective_id = arguments.get("objective_id")
            stage_id = arguments.get("stage_id")
            authority_id = arguments.get("authority_id")
            if (not isinstance(objective_id, str) or
                    not objective_id.startswith("objective:") or len(objective_id) > 140 or
                    not isinstance(stage_id, str) or not stage_id or len(stage_id) > 80 or
                    not isinstance(authority_id, str) or not authority_id or len(authority_id) > 160):
                raise ValueError("work_order_scope_invalid")
            if arguments.get("protocol_version", "riverview-comms-contract:5.0") != \
                    "riverview-comms-contract:5.0":
                raise ValueError("protocol_version_invalid")
            correlation_id = arguments.get("correlation_id", "")
            if not isinstance(correlation_id, str) or len(correlation_id) > 160:
                raise ValueError("correlation_id_out_of_bounds")
            client = {}
            for key, maximum in (("client_id", 128), ("client_type", 64),
                                 ("client_name", 128), ("client_version", 64)):
                value = arguments.get(key, "")
                if not isinstance(value, str) or len(value) > maximum:
                    raise ValueError("client_provenance_out_of_bounds")
                if value:
                    client[key] = value
            classification = arguments.get("classification", "river")
            if not isinstance(classification, str) or len(classification) > 32:
                raise ValueError("classification_out_of_bounds")
            idem = self._idempotency(arguments.get("idempotency_key"))
            objective = self.pipeline.get_objective(objective_id)
            if objective is None:
                raise Comms5OperationNotFound("objective_not_found")
            if objective.get("status") not in {"PROPOSED", "WORK_ORDER_CREATED"}:
                raise ProposalConflict("objective is not in an executable proposal state")
            if objective.get("scope_ref") != "work-order:engineering":
                raise PermissionError("objective is outside the Engineering authority scope")
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""SELECT status,assignment_id FROM grace_objective_steps
                    WHERE objective_id=%s AND step_id=%s""", (objective_id, stage_id))
                stage = cur.fetchone()
            if stage is None:
                raise Comms5OperationNotFound("objective_stage_not_found")
            if stage["assignment_id"]:
                return {"status": "already_queued", "executed": True,
                    "objective_id": objective_id, "stage_id": stage_id,
                    "assignment_id": stage["assignment_id"], "dispatched": True}
            dispatchable = self.pipeline.dispatchable_step(objective_id)
            if not dispatchable or dispatchable["step_id"] != stage_id:
                raise ProposalConflict("the requested stage is not dependency-ready for CME dispatch")
            idem_key = "comms5-work-order-request:" + hashlib.sha256(
                (actor + "\0" + idem).encode("utf-8")).hexdigest()
            payload = {"stage_id": stage_id, "authority_id": authority_id,
                "proposal_revision": objective.get("revision"),
                "correlation_id": correlation_id or objective_id,
                "client": client, "classification": classification,
                "dispatch_authority": "existing_grace_execution_service_grant"}
            def prior_queue_request(cursor):
                cursor.execute("""SELECT objective_id,event_type,payload
                    FROM grace_objective_events WHERE idempotency_key=%s""", (idem_key,))
                return cursor.fetchone()

            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                existing = prior_queue_request(cur)
            if existing:
                if (existing["objective_id"] != objective_id or
                        existing["event_type"] != "work_order.dispatch_requested" or
                        existing["payload"] != payload):
                    raise ProposalConflict("idempotency key is already bound to different work-order input")
                return {"status": "already_queued_for_cme", "executed": True,
                    "objective_id": objective_id, "stage_id": stage_id,
                    "assignment_id": None, "dispatched": False,
                    "request_event_id": idem_key}
            with self.pipeline.ledger.db.transaction():
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""SELECT status,scope_ref FROM grace_objectives
                        WHERE objective_id=%s FOR UPDATE""", (objective_id,))
                    locked = cur.fetchone()
                    if (not locked or locked["status"] not in {"PROPOSED", "WORK_ORDER_CREATED"}
                            or locked["scope_ref"] != objective["scope_ref"]):
                        raise ProposalConflict("objective changed before CME work request")
                    try:
                        grant = self.pipeline.authorizer.require_principal(
                            cur, actor, "objective.submit", objective["scope_ref"])
                    except Exception as exc:
                        if type(exc).__name__ == "GrantDenied":
                            raise PermissionError("objective.submit is not authorized") from None
                        raise
                    if grant.get("grant_id") != authority_id:
                        raise PermissionError("the supplied Steward authority grant does not match this objective")
                    cur.execute("""SELECT status,assignment_id FROM grace_objective_steps
                        WHERE objective_id=%s AND step_id=%s FOR UPDATE""",
                        (objective_id, stage_id))
                    locked_stage = cur.fetchone()
                    if not locked_stage:
                        raise Comms5OperationNotFound("objective_stage_not_found")
                    if locked_stage["assignment_id"]:
                        return {"status": "already_queued", "executed": True,
                            "objective_id": objective_id, "stage_id": stage_id,
                            "assignment_id": locked_stage["assignment_id"], "dispatched": True}
                    prior = prior_queue_request(cur)
                    if prior:
                        if (prior["objective_id"] != objective_id or
                                prior["event_type"] != "work_order.dispatch_requested" or
                                prior["payload"] != payload):
                            raise ProposalConflict("idempotency key is already bound to different work-order input")
                        return {"status": "already_queued_for_cme", "executed": True,
                            "objective_id": objective_id, "stage_id": stage_id,
                            "assignment_id": None, "dispatched": False,
                            "request_event_id": idem_key}
                    self.pipeline._event(cur, objective_id, "work_order.dispatch_requested",
                        idem_key, actor, payload)
                    inserted = prior_queue_request(cur)
                    if (not inserted or inserted["objective_id"] != objective_id or
                            inserted["event_type"] != "work_order.dispatch_requested" or
                            inserted["payload"] != payload):
                        raise ProposalConflict("idempotency key was concurrently bound to different work-order input")
            return {"status": "queued_for_cme", "executed": True,
                "objective_id": objective_id, "stage_id": stage_id,
                "assignment_id": None, "work_order_created": False,
                "dispatched": False, "dispatch_state": "awaiting_grace_execution_service"}

        if tool == "comms5_revalidate_and_queue_work":
            if self.pipeline is None:
                raise RuntimeError("objective_pipeline_unavailable")
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            work_order_id = arguments.get("work_order_id")
            evidence = arguments.get("infrastructure_repair_evidence", [])
            if (not isinstance(work_order_id, str) or not work_order_id or len(work_order_id) > 160 or
                    not isinstance(evidence, list) or not 1 <= len(evidence) <= 20 or
                    any(not isinstance(item, str) or not item.strip() or len(item) > 512
                        for item in evidence)):
                raise ValueError("stale_base_revalidation_evidence_required")
            if arguments.get("protocol_version", "riverview-comms-contract:5.0") != \
                    "riverview-comms-contract:5.0":
                raise ValueError("protocol_version_invalid")
            if arguments.get("classification", "river") not in {
                    "river", "institutional", "confidential"}:
                raise ValueError("classification_invalid")
            idem = self._idempotency(arguments.get("idempotency_key"))
            # Reground against the same approved knowledge contract. Caller-supplied
            # evidence references are provenance only; they cannot assert a new base.
            assignment_projection = self.pipeline.ledger.get(work_order_id)
            if not assignment_projection:
                raise Comms5OperationNotFound("work_order_not_found")
            objective_id = assignment_projection.get("objective_ref")
            objective_projection = self.pipeline.get_objective(objective_id)
            if not objective_projection:
                raise Comms5OperationNotFound("work_order_objective_not_found")
            knowledge = getattr(self.pipeline, "knowledge", None)
            if knowledge is None:
                raise RuntimeError("verified_repository_knowledge_unavailable")
            grounding = knowledge.ground_assignment({
                "id": objective_id, "objective": objective_projection["request"],
                "acceptance_criteria": objective_projection["acceptance_criteria"],
                "contract_ref": getattr(self.pipeline, "CONTRACT_REF", "")})
            from ..worker_adapter.knowledge import KnowledgeStatus
            if (grounding.status is not KnowledgeStatus.VERIFIED or
                    grounding.retrieval_complete is not True or
                    not grounding.source_references or
                    not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",
                                     grounding.source_revision or "") or
                    not re.fullmatch(r"[0-9a-f]{64}", grounding.source_sha256 or "")):
                raise ProposalConflict("fresh repository base could not be verified")
            request_digest = hashlib.sha256(json.dumps({
                "work_order_id": work_order_id, "evidence": evidence,
                "correlation_id": arguments.get("correlation_id", ""),
                "classification": arguments.get("classification", "river")},
                ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            idem_key = "comms5-revalidate:" + hashlib.sha256(
                (actor + "\0" + idem).encode()).hexdigest()
            with self.pipeline.ledger.db.transaction():
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""SELECT objective_id,event_type,payload FROM grace_objective_events
                        WHERE idempotency_key=%s""", (idem_key,))
                    prior = cur.fetchone()
                    if prior:
                        if prior["event_type"] != "work_order.stale_base_revalidated" or \
                                prior["payload"].get("request_sha256") != request_digest:
                            raise ProposalConflict("idempotency key is already bound to different revalidation input")
                        return {"status": "already_queued_for_cme", "executed": True,
                            "objective_id": prior["objective_id"],
                            "successor_step_id": prior["payload"]["successor_step_id"],
                            "assignment_id": None, "dispatched": False,
                            "request_event_id": idem_key}
                    cur.execute("""SELECT a.id,a.objective_ref,a.authority_ref,a.correlation_id,
                            a.state,a.workflow_step,o.status AS objective_status,o.scope_ref,
                            o.proposal,o.revision,s.step_id,s.step_order,s.step_objective,
                            s.acceptance_criteria,s.depends_on,s.status AS step_status,
                            o.source_revision AS prior_source_revision,
                            i.failure_class,i.status AS intent_status,i.finished_at,
                            (SELECT count(*) FROM worker_results wr JOIN worker_attempts wa
                              USING(attempt_id) WHERE wa.assignment_id=a.id) AS result_count,
                            (SELECT count(*) FROM verification_records vr WHERE vr.assignment_id=a.id) AS verification_count
                        FROM assignments a
                        JOIN grace_objectives o ON o.objective_id=a.objective_ref
                        JOIN grace_objective_steps s ON s.objective_id=o.objective_id AND s.assignment_id=a.id
                        JOIN LATERAL (SELECT failure_class,status,finished_at FROM worker_execution_intents
                            WHERE assignment_id=a.id ORDER BY started_at DESC,intent_id DESC LIMIT 1) i ON true
                        WHERE a.id=%s FOR UPDATE OF a,o,s""", (work_order_id,))
                    failed = cur.fetchone()
                    if failed is None:
                        raise Comms5OperationNotFound("work_order_not_found")
                    if (failed["state"] != "blocked" or
                            failed["workflow_step"] != "WORKER_PRE_EXECUTION_FAILED" or
                            failed["intent_status"] != "failed" or
                            failed["failure_class"] not in {
                                "CodexActionFailure:repository_revision_mismatch",
                                "CodexActionFailure:stale_base"} or
                            failed["scope_ref"] != "work-order:engineering" or
                            failed["step_status"] not in {"failed", "blocked"} or
                            failed["result_count"] != 0 or failed["verification_count"] != 0):
                        raise ProposalConflict("work order lacks eligible durable stale-base failure evidence")
                    if grounding.source_revision == failed["prior_source_revision"]:
                        raise ProposalConflict("fresh repository base is unchanged from the stale pin")
                    if failed["objective_status"] not in {"WORK_ORDER_CREATED", "PROPOSED"}:
                        raise ProposalConflict("objective is not eligible for bounded revalidation")
                    try:
                        grant = self.pipeline.authorizer.require_principal(
                            cur, actor, "assignment.create", failed["scope_ref"])
                    except Exception as exc:
                        if type(exc).__name__ == "GrantDenied":
                            raise PermissionError("assignment.create is not authorized") from None
                        raise
                    policy = failed["proposal"]
                    if isinstance(policy, str):
                        policy = json.loads(policy)
                    steps = policy.get("steps", []) if isinstance(policy, dict) else []
                    original_step = next((item for item in steps
                        if isinstance(item, dict) and item.get("step_id") == failed["step_id"]), None)
                    if not original_step:
                        raise ProposalConflict("failed step is absent from immutable approved proposal scope")
                    cur.execute("""SELECT step_id,step_order,depends_on FROM grace_objective_steps
                        WHERE objective_id=%s ORDER BY step_order FOR UPDATE""",
                        (failed["objective_ref"],))
                    existing_steps = cur.fetchall()
                    if len(existing_steps) >= 20:
                        raise ProposalConflict("objective step limit prevents a safe successor")
                    successor = "revalidate:" + hashlib.sha256(
                        (work_order_id + "\0" + idem).encode()).hexdigest()[:32]
                    new_step = dict(original_step)
                    new_step["step_id"] = successor
                    new_step["depends_on"] = list(failed["depends_on"] or [])
                    new_order = max(int(row["step_order"]) for row in existing_steps) + 1
                    new_step["revalidates_step_id"] = failed["step_id"]
                    # Retarget direct successors to the verified rework step. Their
                    # criteria and scope remain unchanged; they cannot run until it verifies.
                    rewired = []
                    for current_step in existing_steps:
                        dependencies = list(current_step["depends_on"] or [])
                        if failed["step_id"] in dependencies:
                            updated_dependencies = [successor if item == failed["step_id"] else item
                                                   for item in dependencies]
                            cur.execute("""UPDATE grace_objective_steps SET depends_on=%s::jsonb,
                                updated_at=clock_timestamp() WHERE objective_id=%s AND step_id=%s""",
                                (json.dumps(updated_dependencies), failed["objective_ref"],
                                 current_step["step_id"]))
                            for plan_step in steps:
                                if isinstance(plan_step, dict) and plan_step.get("step_id") == current_step["step_id"]:
                                    plan_step["depends_on"] = updated_dependencies
                            rewired.append({"step_id": current_step["step_id"],
                                "depends_on": updated_dependencies})
                    details = {"source_work_order_id": work_order_id,
                        "source_step_id": failed["step_id"], "successor_step_id": successor,
                        "request_sha256": request_digest, "failure_class": failed["failure_class"],
                        "infrastructure_repair_evidence": evidence,
                        "authority_grant_id": grant["grant_id"],
                        "correlation_id": arguments.get("correlation_id") or failed["correlation_id"],
                        "classification": arguments.get("classification", "river"),
                        "scope_preserved": True, "verification_required": True,
                        "verified_base_revision": grounding.source_revision,
                        "verified_base_sha256": grounding.source_sha256,
                        "verified_base_references": list(grounding.source_references),
                        "rewired_successors": rewired}
                    policy["steps"].append(new_step)
                    refreshed_evidence = {"status": "VERIFIED", "retrieval_complete": True,
                        "source_references": list(grounding.source_references),
                        "source_revision": grounding.source_revision,
                        "source_sha256": grounding.source_sha256,
                        "value": grounding.value}
                    evidence_bytes = json.dumps(refreshed_evidence, ensure_ascii=False,
                        sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
                    if len(evidence_bytes) > getattr(self.pipeline, "MAX_EVIDENCE_BYTES", 32768):
                        raise ProposalConflict("verified repository evidence exceeds objective limit")
                    cur.execute("""UPDATE grace_objectives SET proposal=%s::jsonb,
                        evidence=%s::jsonb,source_revision=%s,source_sha256=%s,
                        revision=revision+1,updated_at=clock_timestamp() WHERE objective_id=%s""",
                        (json.dumps(policy, ensure_ascii=False, sort_keys=True),
                         json.dumps(refreshed_evidence, ensure_ascii=False, sort_keys=True),
                         grounding.source_revision, grounding.source_sha256,
                         failed["objective_ref"]))
                    cur.execute("""INSERT INTO grace_objective_steps
                        (objective_id,step_id,step_order,step_objective,acceptance_criteria,depends_on,status)
                        VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,'pending')""",
                        (failed["objective_ref"], successor, new_order,
                         failed["step_objective"], json.dumps(failed["acceptance_criteria"]),
                         json.dumps(list(failed["depends_on"] or []))))
                    self.pipeline._event(cur, failed["objective_ref"],
                        "work_order.continuation_proposed",
                        f"comms5-revalidate-continuation:{hashlib.sha256((work_order_id + chr(0) + idem).encode()).hexdigest()}",
                        actor, {"step_id": successor, "depends_on": new_step["depends_on"],
                            "source_work_order_id": work_order_id,
                            "authorization": "explicit_steward_revalidation",
                            "repository_revision": grounding.source_revision})
                    self.pipeline._event(cur, failed["objective_ref"],
                        "work_order.stale_base_revalidated", idem_key, actor, details)
            return {"status": "queued_for_cme", "executed": True,
                "objective_id": failed["objective_ref"], "source_work_order_id": work_order_id,
                "successor_step_id": successor, "assignment_id": None,
                "dispatched": False, "dispatch_state": "awaiting_grace_execution_service",
                "verification_required": True}

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

        if tool == "comms5_resource_policy_status":
            if self.pipeline is None:
                raise RuntimeError("resource_registry_unavailable")
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""SELECT worker_id,capabilities,scope_ref,active,registered_at
                    FROM worker_registry ORDER BY worker_id LIMIT 100""")
                rows = cur.fetchall()
                cur.execute("""SELECT policy_key,revision,mode,parameters,locked,changed_by,
                        authority_reference,rationale,last_selected_worker,updated_at
                    FROM resource_selection_policies WHERE policy_key='engineering'""")
                policy = cur.fetchone()
                events = []
                if policy:
                    cur.execute("""SELECT event_type,revision,actor_id,payload,occurred_at
                        FROM resource_selection_policy_events WHERE policy_key='engineering'
                        ORDER BY occurred_at DESC,event_id DESC LIMIT 20""")
                    events = cur.fetchall()
            return {"status": "available", "executed": True,
                "policy_state": "not_configured" if not policy else "configured",
                "policy": ({key: (policy[key].isoformat() if key == "updated_at" and
                    hasattr(policy[key], "isoformat") else policy[key])
                    for key in ("policy_key", "revision", "mode",
                    "parameters", "locked", "changed_by", "authority_reference",
                    "rationale", "last_selected_worker", "updated_at")} if policy else None),
                "policy_events": [{"event_type": row["event_type"],
                    "revision": row["revision"], "actor_id": row["actor_id"],
                    "payload": row["payload"], "occurred_at": row["occurred_at"].isoformat()}
                    for row in events],
                "selection_source": "durable_policy_and_registered_worker_capabilities",
                "registered_workers": [{
                    "worker_id": row["worker_id"],
                    "capabilities": row["capabilities"],
                    "scope_ref": row["scope_ref"],
                    "active": row["active"],
                    "registered_at": row["registered_at"].isoformat()
                        if hasattr(row["registered_at"], "isoformat") else row["registered_at"],
                } for row in rows],
                "policy_mutation_available": True}

        if tool == "comms5_set_resource_policy":
            if self.pipeline is None:
                raise RuntimeError("resource_registry_unavailable")
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            mode = arguments.get("mode")
            params = arguments.get("parameters")
            rationale = arguments.get("rationale", "")
            expected = arguments.get("expected_revision", -1)
            if not isinstance(mode, str) or mode not in {"automatic", "priority", "target", "balanced"}:
                raise ValueError("resource_policy_mode_unsupported")
            if (not isinstance(params, dict) or set(params) -
                    {"target_seat", "priority_order", "fallback", "consume_reset"} or
                    not isinstance(rationale, str) or len(rationale) > 1000 or
                    type(expected) is not int or expected < -1):
                raise ValueError("resource_policy_parameters_invalid")
            target = params.get("target_seat", "")
            order = params.get("priority_order", [])
            fallback = params.get("fallback", True)
            if (not isinstance(target, str) or len(target) > 160 or
                    not isinstance(order, list) or len(order) > 32 or
                    any(not isinstance(item, str) or not item or len(item) > 160 for item in order) or
                    len(order) != len(set(order)) or type(fallback) is not bool or
                    type(params.get("consume_reset", False)) is not bool or
                    params.get("consume_reset", False)):
                raise ValueError("resource_policy_parameters_invalid")
            if mode == "target" and not target:
                raise ValueError("resource_policy_target_required")
            if mode == "priority" and not order:
                raise ValueError("resource_policy_priority_order_required")
            params = {"target_seat": target, "priority_order": order,
                      "fallback": fallback, "consume_reset": False}
            with self.pipeline.ledger.db.transaction():
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""SELECT worker_id FROM worker_registry
                        WHERE scope_ref='work-order:engineering' ORDER BY worker_id""")
                    known_workers = {row["worker_id"] for row in cur.fetchall()}
                    named = set(order) | ({target} if target else set())
                    if not named <= known_workers:
                        raise ValueError("resource_policy_worker_not_registered_for_engineering")
                    cur.execute("""SELECT revision,mode,parameters,locked FROM
                        resource_selection_policies WHERE policy_key='engineering' FOR UPDATE""")
                    current = cur.fetchone()
                    if current and current["locked"]:
                        raise PermissionError("resource_policy_locked")
                    current_revision = current["revision"] if current else 0
                    document = {"mode": mode, "parameters": params, "rationale": rationale}
                    if (current and current["mode"] == mode and
                            current["parameters"] == params and
                            current["rationale"] == rationale and
                            current["changed_by"] == actor):
                        return {"status": "already_set", "executed": True,
                            "revision": current_revision, "policy": document}
                    if expected >= 0 and expected != current_revision:
                        raise ProposalConflict("resource_policy_revision_conflict")
                    idem = "comms5-resource-policy-set:" + hashlib.sha256(
                        (actor + "\0" + str(current_revision) + "\0" + json.dumps(document, sort_keys=True,
                            separators=(",", ":"))).encode()).hexdigest()
                    revision = current_revision + 1
                    cur.execute("""INSERT INTO resource_selection_policies
                        (policy_key,revision,mode,parameters,locked,changed_by,authority_reference,rationale,updated_at)
                        VALUES ('engineering',%s,%s,%s::jsonb,FALSE,%s,'authenticated-comms5-steward',%s,clock_timestamp())
                        ON CONFLICT(policy_key) DO UPDATE SET revision=EXCLUDED.revision,
                          mode=EXCLUDED.mode,parameters=EXCLUDED.parameters,changed_by=EXCLUDED.changed_by,
                          authority_reference=EXCLUDED.authority_reference,rationale=EXCLUDED.rationale,
                          updated_at=clock_timestamp()""",
                        (revision, mode, json.dumps(params, sort_keys=True), actor, rationale))
                    cur.execute("""INSERT INTO resource_selection_policy_events
                        (policy_key,revision,event_type,idempotency_key,actor_id,payload)
                        VALUES ('engineering',%s,'policy_set',%s,%s,%s::jsonb)""",
                        (revision, idem, actor, json.dumps(document, sort_keys=True)))
            return {"status": "policy_set", "executed": True, "revision": revision,
                    "locked": False, "policy": document}

        if tool == "comms5_set_resource_policy_lock":
            if self.pipeline is None:
                raise RuntimeError("resource_registry_unavailable")
            if arguments.get("explicit_steward_confirmation") is not True:
                raise PermissionError("explicit Steward confirmation is required")
            locked, rationale = arguments.get("locked"), arguments.get("rationale", "")
            if type(locked) is not bool or not isinstance(rationale, str) or len(rationale) > 1000:
                raise ValueError("resource_policy_lock_parameters_invalid")
            with self.pipeline.ledger.db.transaction():
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""SELECT revision,mode,parameters,locked FROM
                        resource_selection_policies WHERE policy_key='engineering' FOR UPDATE""")
                    current = cur.fetchone()
                    if current is None:
                        if not locked:
                            raise ProposalConflict("resource_policy_not_configured")
                        revision, mode, params, prior_lock = 1, "automatic", {}, False
                    else:
                        revision, mode, params, prior_lock = (current["revision"],
                            current["mode"], current["parameters"], current["locked"])
                    if prior_lock == locked:
                        return {"status": "already_locked" if locked else "already_unlocked",
                                "executed": True, "revision": revision, "locked": locked}
                    revision += 1
                    idem = "comms5-resource-policy-lock:" + hashlib.sha256(
                        (actor + "\0" + str(revision) + "\0" + str(locked) +
                         "\0" + rationale).encode()).hexdigest()
                    cur.execute("""INSERT INTO resource_selection_policies
                        (policy_key,revision,mode,parameters,locked,changed_by,authority_reference,rationale,updated_at)
                        VALUES ('engineering',%s,%s,%s::jsonb,%s,%s,'authenticated-comms5-steward',%s,clock_timestamp())
                        ON CONFLICT(policy_key) DO UPDATE SET revision=EXCLUDED.revision,
                          locked=EXCLUDED.locked,changed_by=EXCLUDED.changed_by,
                          authority_reference=EXCLUDED.authority_reference,rationale=EXCLUDED.rationale,
                          updated_at=clock_timestamp()""",
                        (revision, mode, json.dumps(params, sort_keys=True), locked, actor, rationale))
                    cur.execute("""INSERT INTO resource_selection_policy_events
                        (policy_key,revision,event_type,idempotency_key,actor_id,payload)
                        VALUES ('engineering',%s,%s,%s,%s,%s::jsonb) ON CONFLICT(idempotency_key) DO NOTHING""",
                        (revision, "policy_locked" if locked else "policy_unlocked", idem,
                         actor, json.dumps({"locked": locked, "rationale": rationale}, sort_keys=True)))
            return {"status": "locked" if locked else "unlocked", "executed": True,
                    "revision": revision, "locked": locked}

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
                provenance=provenance, idempotency_key=arguments["idempotency_key"],
                delegated_authorized=delegated_authorized)
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
