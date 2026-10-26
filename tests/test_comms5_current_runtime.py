"""Focused tests for Comms5 operations on current Riverview services.

File Revision: 1.0.8
Component: COMMS5-CURRENT-RUNTIME-OPERATIONS-TESTS
History: New file; no predecessor existed.
Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Verify intent/authority projection and combined durable objective/proposal listing.
Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Verify resource status reflects current worker records without inventing policy.
Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Verify durable CME queue intent, exact grant, dependency readiness, and idempotent retries.
Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Update runtime catalog and verify new policy tool accounting.
Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Cover persisted policy projections and fixed operation dispatch without mutable MCP routing.
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Count the four bounded Steward exchange operations in live backend implementation status.
Changed: 2026-10-26 UTC | C2-COMMAND-GATEWAY-COMBINED | Account for preserved direct dispatch and fixed command gateway tools.
Changed: 2026-10-26 UTC | COMMS5-OPERATIONAL-COMMAND-EXECUTION | Count the two host-scoped command task tools in the implementation catalog.
"""

import unittest
from datetime import datetime, timezone
import json
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from riverview_core.comms5.server import Comms5Application
from riverview_core.resident_execution.comms5_operations import Comms5Operations
from riverview_core.resident_execution.proposals import ProposalConflict


class _Registry:
    def __init__(self):
        self.record = None
        self.created = None
        self.transitions = []

    def create_draft(self, content, **kwargs):
        self.created = (content, kwargs)
        proposal_id = "proposal:00000000-0000-4000-8000-000000000001"
        self.record = {"proposal": {"proposal_id": proposal_id,
                         "lifecycle_status": "DRAFT", "current_revision": 1},
                       "revision": {"revision": 1, "content_sha256": "a" * 64,
                                    **content},
                       "events": [], "reviews": [], "work_order_links": []}
        return self.record

    def get(self, proposal_id, revision=None):
        if not self.record or self.record["proposal"]["proposal_id"] != proposal_id:
            from riverview_core.resident_execution.proposals import ProposalNotFound
            raise ProposalNotFound("proposal not found")
        return self.record

    def transition(self, proposal_id, revision, new_status, **kwargs):
        self.transitions.append((proposal_id, revision, new_status, kwargs))
        self.record["proposal"]["lifecycle_status"] = new_status
        self.record["revision"]["lifecycle_status"] = new_status
        return self.record

    def _digest(self, content):
        return __import__("hashlib").sha256(json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()

    def revise(self, proposal_id, expected_revision, content, **kwargs):
        self.record["proposal"]["current_revision"] = expected_revision + 1
        self.record["revision"] = {"revision": expected_revision + 1,
            "content_sha256": self._digest(content), **content}
        self.record["proposal"]["content_sha256"] = self.record["revision"]["content_sha256"]
        self.record["proposal"]["lifecycle_status"] = "DRAFT"
        self.record["events"].append({"event_type": "proposal.revised",
            "idempotency_key": kwargs["idempotency_key"],
            "payload": {"content_sha256": self.record["revision"]["content_sha256"]}})
        self.revised_kwargs = kwargs
        return self.record


class _Lifecycle:
    def __init__(self):
        self.promotions = []
        self.decisions = []

    def decide(self, proposal_id, revision, **kwargs):
        self.decisions.append((proposal_id, revision, kwargs))
        return {"proposal": {"lifecycle_status": "APPROVED"}}

    def promote(self, proposal_id, revision, *, actor_id):
        self.promotions.append((proposal_id, revision, actor_id))
        return {"status": "GROUNDED", "objective_id": "objective:proposal:fixture:r1",
                "assignment_id": None, "work_order_dispatched": False,
                "execution_state": "awaiting_grace_planning", "reused": False}


class _QueueCursor:
    def __init__(self, db):
        self.db = db
        self.rowcount = 0
        self._one = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=()):
        if "FROM grace_objectives" in query:
            self._one = {"status": "PROPOSED", "scope_ref": "work-order:engineering"}
        elif "FROM grace_objective_steps" in query:
            self._one = {"status": "pending", "assignment_id": None}
        elif "FROM grace_objective_events" in query:
            self._one = next((event for event in self.db.events
                if event["idempotency_key"] == params[0]), None)
        elif "INSERT INTO grace_objective_events" in query:
            objective_id, event_type, idem, actor, payload = params
            if not any(event["idempotency_key"] == idem for event in self.db.events):
                self.db.events.append({"objective_id": objective_id,
                    "event_type": event_type, "idempotency_key": idem,
                    "actor_id": actor, "payload": json.loads(payload)})
                self.rowcount = 1
        else:
            raise AssertionError(f"unexpected SQL in queue test: {query}")

    def fetchone(self):
        return self._one


class _QueueDatabase:
    def __init__(self):
        self.events = []

    def cursor(self):
        return _QueueCursor(self)

    def transaction(self):
        from contextlib import nullcontext
        return nullcontext()


class _QueuePipeline:
    def __init__(self, *, grant_id="grant:engineering-submit"):
        self.db = _QueueDatabase()
        self.ledger = SimpleNamespace(db=self.db,
            _set_search_path=lambda cursor: None)
        self.authorizer = MagicMock()
        self.authorizer.require_principal.return_value = {"grant_id": grant_id}
        self.objective = {"status": "PROPOSED", "scope_ref": "work-order:engineering",
                          "revision": 3}
        self.dispatchable = {"step_id": "step:one"}

    def get_objective(self, _):
        return self.objective

    def dispatchable_step(self, _):
        return self.dispatchable

    def objective_events(self, objective_id):
        return [event for event in self.db.events if event["objective_id"] == objective_id]

    def _event(self, cursor, objective_id, event_type, idem, actor, payload):
        cursor.execute("INSERT INTO grace_objective_events", (
            objective_id, event_type, idem, actor, json.dumps(payload)))


class Comms5CurrentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.registry = _Registry()
        self.lifecycle = _Lifecycle()
        self.operations = Comms5Operations(self.registry, self.lifecycle)

    def seed(self):
        return {"seed_text": "A bounded idea for Riverview.", "idempotency_key": "seed-1",
                "client_id": "client", "client_type": "chat", "client_name": "ChatGPT",
                "authenticated_principal": "resident:attacker"}

    def test_experiment_grant_requires_one_explicit_attested_steward_action(self):
        tool = "comms5_authorize_grace_experiment"
        arguments = {"objective_id": "objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2",
            "objective_revision": 2, "explicit_steward_confirmation": True,
            "idempotency_key": "grace-autonomy-test-authorization"}
        operations = Comms5Operations(self.registry, self.lifecycle,
            objective_pipeline=SimpleNamespace(ledger=object()), authority_registry=object())
        with self.assertRaisesRegex(PermissionError, "explicit Steward confirmation"):
            operations.execute(tool, {**arguments, "explicit_steward_confirmation": False},
                principal_id="steward:camrui")
        with self.assertRaisesRegex(ValueError, "experiment_authorization_scope_invalid"):
            operations.execute(tool, arguments, principal_id="steward:spoofed")
        with self.assertRaisesRegex(ValueError, "experiment_authorization_fields_invalid"):
            operations.execute(tool, {**arguments, "authenticated_principal": "steward:camrui"},
                principal_id="steward:camrui")

    def test_experiment_amendment_is_exact_and_steward_gated(self):
        tool = "comms5_amend_grace_experiment"
        arguments = {
            "authorization_id": "a38cb2cc-cbd1-5867-ac44-b2721935f324",
            "objective_id": "objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2",
            "objective_revision": 2,
            "expected_max_luna_requests": 2,
            "new_max_luna_requests": 4,
            "expected_used_luna_requests": 2,
            "expected_used_recoveries": 4,
            "expected_cumulative_spend_usd": 0.04183460,
            "total_budget_usd": 5.0,
            "expires_at": "2026-10-25T09:11:16.041229-04:00",
            "explicit_steward_confirmation": True,
            "idempotency_key": "grace-autonomy-luna-r2-amend-20261024",
        }
        pipeline = SimpleNamespace(ledger=object())
        operations = Comms5Operations(self.registry, self.lifecycle,
            objective_pipeline=pipeline, authority_registry=object())
        with self.assertRaisesRegex(PermissionError, "authenticated Steward"):
            operations.execute(tool, arguments, principal_id="resident:grace")
        with self.assertRaisesRegex(PermissionError, "explicit Steward confirmation"):
            operations.execute(tool, {**arguments, "explicit_steward_confirmation": False},
                principal_id="steward:camrui")
        with self.assertRaisesRegex(ValueError, "experiment_amendment_fields_invalid"):
            operations.execute(tool, {**arguments, "unexpected": True},
                principal_id="steward:camrui")
        with patch("riverview_core.resident_execution.grace_experiment_authorization.GraceExperimentAuthorization.amend_luna_request_limit",
                   return_value={"status": "active"}) as amend:
            result = operations.execute(tool, arguments, principal_id="steward:camrui")
        self.assertEqual(result, {"status": "active"})
        self.assertEqual(amend.call_args.kwargs["actor_id"], "steward:camrui")
        self.assertEqual(amend.call_args.kwargs["revision"], 2)
        self.assertTrue(amend.call_args.kwargs["explicit_steward_confirmation"])

    def test_supervisory_authorization_operation_is_fixed_scope_and_steward_confirmed(self):
        operations = Comms5Operations(self.registry, self.lifecycle,
            objective_pipeline=SimpleNamespace(ledger=object()), authority_registry=object())
        args = {"total_budget_usd":5.0,"per_request_limit_usd":0.05,
            "explicit_steward_confirmation":True,
            "idempotency_key":"grace-supervision-contract-test"}
        with self.assertRaisesRegex(PermissionError,"explicit Steward confirmation"):
            operations.execute("comms5_authorize_grace_supervision",
                {**args,"explicit_steward_confirmation":False},principal_id="steward:camrui")
        with self.assertRaisesRegex(PermissionError,"authenticated Steward"):
            operations.execute("comms5_authorize_grace_supervision",args,principal_id="resident:grace")
        with self.assertRaisesRegex(ValueError,"grace_supervisory_authorization_scope_invalid"):
            operations.execute("comms5_authorize_grace_supervision",{**args,"total_budget_usd":5.01},
                principal_id="steward:camrui")

    def test_seed_is_persisted_as_unapproved_proposal_using_attested_identity(self):
        result = self.operations.execute("comms5_submit_steward_seed", self.seed(),
                                         principal_id="steward:camrui")
        content, kwargs = self.registry.created
        self.assertEqual(result["status"], "draft_saved")
        self.assertEqual(kwargs["created_by"], "steward:camrui")
        self.assertEqual(kwargs["origin_kind"], "steward_authored")
        self.assertEqual(kwargs["idempotency_key"], "seed-1")
        self.assertEqual(content["acceptance_criteria"], [])
        self.assertEqual(content["scope"], "Draft only; scope requires Grace and Steward review.")

    def test_specification_is_durable_but_formation_contract_is_not_execution(self):
        result = self.operations.execute("comms5_store_specification", {
            "content": "Build a test fixture", "summary": "A bounded test fixture",
            "idempotency_key": "spec-1", "client_id": "client", "client_type": "chat",
            "client_name": "ChatGPT", "authenticated_principal": "spoofed",
            "formation_contract": {"allowed_paths": ["src/**"]}},
            principal_id="steward:camrui")
        content, kwargs = self.registry.created
        self.assertEqual(result["status"], "specification_stored")
        self.assertEqual(kwargs["created_by"], "steward:camrui")
        self.assertEqual(content["acceptance_criteria"], [])
        self.assertIn("formation_contract", kwargs["provenance"])

    def test_cli_revision_uses_attested_steward_and_is_idempotent(self):
        proposal_id = "proposal:00000000-0000-4000-8000-000000000001"
        self.registry.record = {"proposal": {"proposal_id": proposal_id,
            "lifecycle_status": "DRAFT", "current_revision": 1},
            "revision": {"revision": 1, "content_sha256": "a" * 64},
            "events": [], "reviews": [], "work_order_links": []}
        content = {"title": "Updated", "summary": "Summary", "objective": "Objective",
            "scope": "Bounded", "proposed_approach": "Inspect", "constraints": [],
            "acceptance_criteria": ["One evidence check"], "tags": ["comms5"]}
        args = {"proposal_id": proposal_id, "expected_revision": 1, "content": content,
            "idempotency_key": "revise-1", "client_id": "codex-cli",
            "client_type": "cli", "client_name": "Codex CLI"}
        result = self.operations.execute("comms5_revise_specification", args,
                                         principal_id="steward:camrui")
        self.assertEqual(result["revision"], 2)
        self.assertEqual(result["content_sha256"], self.registry._digest(content))
        self.assertEqual(self.registry.revised_kwargs["actor_id"], "steward:camrui")
        self.assertEqual(self.registry.revised_kwargs["provenance"]["source"], "authenticated_comms5")
        replay = self.operations.execute("comms5_revise_specification", args,
                                         principal_id="steward:camrui")
        self.assertEqual(replay["status"], "revision_reused")
        self.assertEqual(self.registry.record["proposal"]["current_revision"], 2)

    def test_cli_prepare_presents_exact_revision_without_approving_or_promoting(self):
        proposal_id = "proposal:00000000-0000-4000-8000-000000000001"
        self.registry.record = {"proposal": {"proposal_id": proposal_id,
            "lifecycle_status": "DRAFT", "current_revision": 1},
            "revision": {"revision": 1, "content_sha256": "a" * 64},
            "events": [], "reviews": [], "work_order_links": []}
        result = self.operations.execute("comms5_prepare_proposal_for_decision", {
            "proposal_id": proposal_id, "expected_revision": 1,
            "expected_content_sha256": "a" * 64,
            "explicit_steward_confirmation": True, "idempotency_key": "prepare-1"},
            principal_id="steward:camrui")
        self.assertEqual(result["status"], "ready_for_steward_decision")
        self.assertFalse(result["approval_recorded"])
        self.assertEqual([transition[2] for transition in self.registry.transitions],
                         ["READY_FOR_REVIEW", "READY_FOR_STEWARD_DECISION"])
        self.assertEqual(self.lifecycle.decisions, [])
        self.assertEqual(self.lifecycle.promotions, [])

    def test_draft_cancellation_requires_explicit_confirmation(self):
        seed_result = self.operations.execute("comms5_submit_steward_seed", self.seed(),
                                              principal_id="steward:camrui")
        base = {"seed_id": seed_result["seed_id"], "reason": "Withdrawn",
                "idempotency_key": "cancel-1", "client_id": "c", "client_type": "chat",
                "client_name": "ChatGPT", "authenticated_principal": "spoofed"}
        with self.assertRaises(PermissionError):
            self.operations.execute("comms5_cancel_draft", base, principal_id="steward:camrui")
        base["explicit_steward_confirmation"] = True
        result = self.operations.execute("comms5_cancel_draft", base, principal_id="steward:camrui")
        self.assertEqual(result["status"], "draft_cancelled")
        self.assertEqual(self.registry.transitions[0][2], "ARCHIVED")

    def test_specification_rejects_unknown_formation_contract_fields(self):
        arguments = {"content": "Build a test fixture", "summary": "A bounded test fixture",
            "idempotency_key": "spec-2", "client_id": "client", "client_type": "chat",
            "client_name": "ChatGPT", "authenticated_principal": "spoofed",
            "formation_contract": {"allowed_paths": [], "privilege_escalation": True}}
        with self.assertRaisesRegex(ValueError, "formation_contract"):
            self.operations.execute("comms5_store_specification", arguments,
                                    principal_id="steward:camrui")
        self.assertIsNone(self.registry.created)

    def test_promotion_does_not_manufacture_proposal_approval(self):
        seed_result = self.operations.execute("comms5_submit_steward_seed", self.seed(),
                                              principal_id="steward:camrui")
        with self.assertRaises(ProposalConflict):
            self.operations.execute("comms5_confirm_and_promote_seed", {
                "seed_id": seed_result["seed_id"], "explicit_steward_confirmation": True},
                principal_id="steward:camrui")
        self.assertEqual(self.lifecycle.promotions, [])

    def test_explicit_comms5_confirmation_approves_exact_ready_revision_then_promotes(self):
        seed_result = self.operations.execute("comms5_submit_steward_seed", self.seed(),
                                              principal_id="steward:camrui")
        self.registry.record["proposal"]["lifecycle_status"] = "READY_FOR_STEWARD_DECISION"
        self.registry.record["revision"]["lifecycle_status"] = "READY_FOR_STEWARD_DECISION"
        result = self.operations.execute("comms5_confirm_and_promote_seed", {
            "seed_id": seed_result["seed_id"], "idempotency_key": "promote-1",
            "explicit_steward_confirmation": True}, principal_id="steward:camrui")
        self.assertEqual(result["status"], "GROUNDED")
        self.assertEqual(self.lifecycle.decisions[0][0], seed_result["proposal_id"])
        decision = self.lifecycle.decisions[0][2]
        self.assertEqual(decision["authority_reference"], "comms5-ingress:steward")
        self.assertEqual(decision["content_sha256"], "a" * 64)
        self.assertEqual(self.lifecycle.promotions, [(seed_result["proposal_id"], 1, "steward:camrui")])

    def test_approval_remains_recorded_when_exact_intake_grant_is_missing(self):
        seed_result = self.operations.execute("comms5_submit_steward_seed", self.seed(),
                                              principal_id="steward:camrui")
        self.registry.record["proposal"]["lifecycle_status"] = "READY_FOR_STEWARD_DECISION"
        self.registry.record["revision"]["lifecycle_status"] = "READY_FOR_STEWARD_DECISION"
        from riverview_core.resident_execution.pipeline import ObjectiveNotAuthorized
        self.lifecycle.promote = MagicMock(side_effect=ObjectiveNotAuthorized("no grant"))
        result = self.operations.execute("comms5_confirm_and_promote_seed", {
            "seed_id": seed_result["seed_id"], "idempotency_key": "promote-no-grant",
            "explicit_steward_confirmation": True}, principal_id="steward:camrui")
        self.assertEqual(result["status"], "approved_not_promoted")
        self.assertTrue(result["approval_recorded"])
        self.assertEqual(result["missing_prerequisite"], "objective.submit")

    def test_objective_status_returns_durable_lineage_without_objective_body(self):
        pipeline = MagicMock()
        now = datetime.now(timezone.utc)
        pipeline.get_objective.return_value = {"objective_id": "objective:test-1",
            "status": "WORK_ORDER_CREATED", "scope_ref": "work-order:engineering",
            "submitter_id": "steward:camrui", "revision": 4,
            "assignment_id": "assignment:test-1", "source_revision": "a" * 40,
            "source_sha256": "b" * 64, "created_at": now, "updated_at": now,
            "request": "private objective body", "acceptance_criteria": ["private criterion"],
            "evidence": {"status": "VERIFIED", "source_references": ["one", "two"],
                         "source_revision": "a" * 40, "source_sha256": "b" * 64,
                         "retrieval_complete": True}}
        pipeline.ledger.get.return_value = {"id": "assignment:test-1", "state": "running",
            "owner": "engineering", "workflow_id": "grace.objective-work-order.v1",
            "workflow_step": "step-1", "correlation_id": "objective:test-1"}
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.side_effect = [[{"step_id": "step-1", "step_order": 1,
            "depends_on": [], "status": "assigned", "assignment_id": "assignment:test-1",
            "dispatch_count": 1, "updated_at": now}], [{"assignment_id": "assignment:test-1",
            "worker_id": "codex", "lease_generation": 1, "capability": "engineering.codex-cli-artifact.v1",
            "effect_class": "retry_safe", "status": "succeeded", "attempt_id": "attempt-1",
            "started_at": now, "finished_at": now, "failure_class": None}]]
        cursor.fetchone.return_value = {"decision": "ACCEPTED", "verifier_revision": "v1",
                                        "created_at": now}
        pipeline.ledger.db.cursor.return_value = cursor
        pipeline.authorizer.require_principal.return_value = {"grant_id": "grant:objective-submit"}
        pipeline.objective_events.return_value = [{"event_type": "objective.received",
            "actor_id": "steward:camrui", "occurred_at": now, "payload": {"body": "secret"}}]
        self.operations.pipeline = pipeline
        result = self.operations.execute("comms5_objective_status",
            {"objective_id": "objective:test-1"}, principal_id="steward:camrui")
        serialized = str(result)
        self.assertEqual(result["objective"]["state"], "WORK_ORDER_CREATED")
        self.assertEqual(result["assignment"]["state"], "running")
        self.assertEqual(result["steps"][0]["assignment_id"], "assignment:test-1")
        self.assertEqual(result["verification"]["decision"], "ACCEPTED")
        self.assertEqual(result["execution_intents"][0]["worker_id"], "codex")
        self.assertEqual(result["submission_authority"]["grant_id"], "grant:objective-submit")
        self.assertNotIn("private objective body", serialized)
        self.assertNotIn("private criterion", serialized)
        self.assertNotIn("secret", serialized)

    def test_recent_submissions_combines_objectives_and_proposals_without_bodies(self):
        now = datetime.now(timezone.utc)
        pipeline = MagicMock()
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [{"record_id": "objective:test-1",
            "record_type": "objective", "lifecycle_status": "GROUNDED",
            "created_by": "steward:camrui", "created_at": now, "updated_at": now,
            "assignment_id": None}]
        pipeline.ledger.db.cursor.return_value = cursor
        self.operations.pipeline = pipeline
        self.registry.search = MagicMock(return_value={"items": [{
            "proposal_id": "proposal:test-1", "lifecycle_status": "DRAFT",
            "created_by": "steward:camrui", "updated_at": now.isoformat(),
            "current_revision": 1, "privacy_classification": "institutional",
            "objective": "private proposal body"}]})
        result = self.operations.execute("comms5_recent_steward_submissions", {},
                                         principal_id="steward:camrui")
        self.assertEqual({item["record_type"] for item in result["items"]},
                         {"objective", "proposal"})
        self.assertNotIn("private proposal body", str(result))

    def test_resource_policy_status_reports_real_workers_and_no_fabricated_policy(self):
        now = datetime.now(timezone.utc)
        pipeline = MagicMock()
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.side_effect = [[{"worker_id": "worker:codex-test",
            "capabilities": ["engineering.codex-cli-artifact.v1"],
            "scope_ref": "work-order:engineering", "active": True,
            "registered_at": now}], []]
        cursor.fetchone.return_value = None
        pipeline.ledger.db.cursor.return_value = cursor
        self.operations.pipeline = pipeline
        result = self.operations.execute("comms5_resource_policy_status", {},
                                         principal_id="steward:camrui")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["policy_state"], "not_configured")
        self.assertIsNone(result["policy"])
        self.assertTrue(result["policy_mutation_available"])
        self.assertEqual(result["registered_workers"][0]["worker_id"], "worker:codex-test")
        self.assertTrue(any("worker_registry" in call.args[0]
                            for call in cursor.execute.call_args_list))

    def test_form_and_queue_work_persists_idempotent_cme_request_under_exact_grant(self):
        pipeline = _QueuePipeline()
        self.operations.pipeline = pipeline
        arguments = {"objective_id": "objective:commissioning", "stage_id": "step:one",
            "authority_id": "grant:engineering-submit", "idempotency_key": "queue-1",
            "explicit_steward_confirmation": True, "client_id": "chatgpt",
            "client_type": "chat", "client_name": "ChatGPT",
            "correlation_id": "conversation:one"}
        result = self.operations.execute("comms5_form_and_queue_work", arguments,
                                         principal_id="steward:camrui")
        self.assertEqual(result["status"], "queued_for_cme")
        self.assertTrue(result["executed"])
        self.assertFalse(result["work_order_created"])
        self.assertFalse(result["dispatched"])
        self.assertEqual(len(pipeline.db.events), 1)
        event = pipeline.db.events[0]
        self.assertEqual(event["event_type"], "work_order.dispatch_requested")
        self.assertEqual(event["payload"]["stage_id"], "step:one")
        self.assertEqual(event["payload"]["correlation_id"], "conversation:one")
        self.assertEqual(event["payload"]["dispatch_authority"],
                         "existing_grace_execution_service_grant")
        self.assertEqual(pipeline.authorizer.require_principal.call_args.args[1:],
                         ("steward:camrui", "objective.submit", "work-order:engineering"))

        retry = self.operations.execute("comms5_form_and_queue_work", arguments,
                                        principal_id="steward:camrui")
        self.assertEqual(retry["status"], "already_queued_for_cme")
        self.assertEqual(len(pipeline.db.events), 1)

    def test_form_and_queue_work_rejects_mismatched_or_missing_authority(self):
        pipeline = _QueuePipeline(grant_id="grant:other")
        self.operations.pipeline = pipeline
        arguments = {"objective_id": "objective:commissioning", "stage_id": "step:one",
            "authority_id": "grant:engineering-submit", "idempotency_key": "queue-2",
            "explicit_steward_confirmation": True, "client_id": "chatgpt",
            "client_type": "chat", "client_name": "ChatGPT"}
        with self.assertRaisesRegex(PermissionError, "does not match"):
            self.operations.execute("comms5_form_and_queue_work", arguments,
                                    principal_id="steward:camrui")
        self.assertEqual(pipeline.db.events, [])

        pipeline.authorizer.require_principal.side_effect = type("GrantDenied", (Exception,), {})()
        with self.assertRaisesRegex(PermissionError, "not authorized"):
            self.operations.execute("comms5_form_and_queue_work", arguments,
                                    principal_id="steward:camrui")
        self.assertEqual(pipeline.db.events, [])

    def test_form_and_queue_work_rejects_non_ready_stage_without_event(self):
        pipeline = _QueuePipeline()
        pipeline.dispatchable = {"step_id": "step:other"}
        self.operations.pipeline = pipeline
        arguments = {"objective_id": "objective:commissioning", "stage_id": "step:one",
            "authority_id": "grant:engineering-submit", "idempotency_key": "queue-3",
            "explicit_steward_confirmation": True, "client_id": "chatgpt",
            "client_type": "chat", "client_name": "ChatGPT"}
        with self.assertRaisesRegex(ProposalConflict, "dependency-ready"):
            self.operations.execute("comms5_form_and_queue_work", arguments,
                                    principal_id="steward:camrui")
        self.assertEqual(pipeline.db.events, [])

    def test_form_and_queue_work_does_not_reuse_key_across_objectives(self):
        pipeline = _QueuePipeline()
        self.operations.pipeline = pipeline
        arguments = {"objective_id": "objective:commissioning", "stage_id": "step:one",
            "authority_id": "grant:engineering-submit", "idempotency_key": "queue-shared",
            "explicit_steward_confirmation": True, "client_id": "chatgpt",
            "client_type": "chat", "client_name": "ChatGPT"}
        first = self.operations.execute("comms5_form_and_queue_work", arguments,
                                       principal_id="steward:camrui")
        self.assertEqual(first["status"], "queued_for_cme")
        arguments["objective_id"] = "objective:different"
        with self.assertRaisesRegex(ProposalConflict, "bound to different"):
            self.operations.execute("comms5_form_and_queue_work", arguments,
                                    principal_id="steward:camrui")
        self.assertEqual(len(pipeline.db.events), 1)

    def test_mcp_uses_transport_attested_principal_not_argument_identity(self):
        class Backend:
            supported_tools = {"comms5_submit_steward_seed"}
            IMPLEMENTATION_STATUS = {"comms5_submit_steward_seed": "IMPLEMENTED"}
            def call_authenticated(inner, name, arguments, *, principal=None):
                return {"principal": principal, "argument_identity": arguments["authenticated_principal"]}

        application = Comms5Application("x" * 48, backend=Backend())
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "comms5_submit_steward_seed", "arguments": self.seed()}}
        response = application.handle(request, principal="steward")
        self.assertEqual(response["result"]["structuredContent"]["principal"], "steward")
        self.assertEqual(response["result"]["structuredContent"]["argument_identity"], "resident:attacker")

    def test_live_backend_status_counts_fully_implemented_operations(self):
        from riverview_core.comms5.dashboard_backend import DashboardReadBackend
        class Backend:
            supported_tools = DashboardReadBackend.supported_tools.fget(None)
            IMPLEMENTATION_STATUS = DashboardReadBackend.IMPLEMENTATION_STATUS
        application = Comms5Application("x" * 48, backend=Backend())
        status = {name: application.implementation_status(name)
                  for name in application.implemented_tools}
        self.assertEqual(sum(value == "IMPLEMENTED" for value in status.values()), 41)
        self.assertEqual(sum(value == "PARTIALLY_IMPLEMENTED" for value in status.values()), 0)
        self.assertEqual(41 - len(status), 0)

    def test_delegation_tools_route_to_authenticated_dashboard_operation(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from riverview_core.comms5.server import Comms5Application
        from riverview_core.comms5.dashboard_backend import DashboardReadBackend

        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "dashboard-token"
            credential.write_text("g" * 48)
            credential.chmod(0o600)
            backend = DashboardReadBackend(credential_file=credential)
            delegation_tools = {
                "comms5_request_delegation_grant",
                "comms5_get_delegation_grant_status",
                "comms5_revoke_delegation_grant",
                "comms5_request_delegation_grant_change",
            }
            self.assertTrue(delegation_tools <= backend.supported_tools)
            self.assertTrue(all(backend.IMPLEMENTATION_STATUS[name] == "IMPLEMENTED"
                                for name in delegation_tools))
            application = Comms5Application("x" * 48, backend=backend)
            arguments = {
                "principal_id": "steward:camrui",
                "action": "comms5.operations.non_destructive.v1",
                "scope_ref": "project:Riverview",
                "policy_ref": "policy:delegation.v1",
                "duration_spec": {"unit": "days", "value": 7},
                "request_ref": "seven-day unlimited grant test",
                "idempotency_key": "seven-day-unlimited-grant-test",
            }
            with patch.object(backend, "_post_operation", return_value={
                    "status": "pending", "request_id": "delegation-request:test"}) as post:
                result = application.handle({"jsonrpc": "2.0", "id": 1,
                    "method": "tools/call", "params": {
                        "name": "comms5_request_delegation_grant",
                        "arguments": arguments}}, principal="steward")
            post.assert_called_once_with("comms5_request_delegation_grant", arguments)
            self.assertEqual(result["result"]["structuredContent"]["status"], "pending")
            denied = application.handle({"jsonrpc": "2.0", "id": 2,
                "method": "tools/call", "params": {
                    "name": "comms5_request_delegation_grant",
                    "arguments": arguments}}, principal="provider")
            self.assertEqual(denied["result"]["structuredContent"]["status"],
                             "NOT_AUTHORIZED")

    def test_dashboard_internal_route_requires_service_token_and_comms5_attestation(self):
        from riverview_core.status_dashboard.server import _BoundedHTTPServer, make_handler
        registry = _Registry()
        server = _BoundedHTTPServer(("127.0.0.1", 0), make_handler(), token="d" * 48,
            projection=None, notification_service=None, objective_pipeline=None,
            conversation_service=None, account_auth_service=None, permission_store=None,
            static_dir="/nonexistent", proposal_registry=registry)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            arguments = self.seed()
            body = json.dumps({"tool": "comms5_submit_steward_seed", "arguments": arguments}).encode()
            url = f"http://127.0.0.1:{server.server_port}/api/v1/internal/comms5/operation"
            request = Request(url, data=body, headers={"Content-Type": "application/json"})
            with self.assertRaises(HTTPError) as denied:
                urlopen(request, timeout=2)
            self.assertEqual(denied.exception.code, 401)
            request = Request(url, data=body, headers={"Content-Type": "application/json",
                "Authorization": "Bearer " + "d" * 48})
            with self.assertRaises(HTTPError) as unattested:
                urlopen(request, timeout=2)
            self.assertEqual(unattested.exception.code, 403)
            self.assertIsNone(registry.created)
            request = Request(url, data=body, headers={"Content-Type": "application/json",
                "Authorization": "Bearer " + "d" * 48,
                "X-Riverview-Comms5": "1",
                "X-Riverview-Comms5-Principal": "steward"})
            with urlopen(request, timeout=2) as response:
                result = json.loads(response.read())
            self.assertEqual(result["status"], "draft_saved")
            self.assertEqual(registry.created[1]["created_by"], "steward:camrui")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_delegated_comms5_path_requires_canonical_authorization_before_operation(self):
        from riverview_core.status_dashboard.server import _BoundedHTTPServer, make_handler
        from riverview_core.institutional_authority.registry import AuthorityDenied
        registry = _Registry()
        class DelegationAuthority:
            def __init__(self): self.calls=[]; self.allowed=True
            def authorize_operation(self, *, principal_id, tool, operation_ref):
                self.calls.append((principal_id,tool,operation_ref))
                if not self.allowed:
                    raise AuthorityDenied("no active grant")
                return {"status":"authorized","principal_id":principal_id}
        authority=DelegationAuthority()
        server = _BoundedHTTPServer(("127.0.0.1", 0), make_handler(), token="d" * 48,
            projection=None, notification_service=None, objective_pipeline=None,
            conversation_service=None, account_auth_service=None, permission_store=None,
            static_dir="/nonexistent", proposal_registry=registry,
            delegation_grant_requests=authority)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            headers={"Content-Type":"application/json","Authorization":"Bearer " + "d"*48,
                "X-Riverview-Comms5":"1","X-Riverview-Comms5-Principal":"service:chatgpt"}
            auth_url=f"http://127.0.0.1:{server.server_port}/api/v1/internal/comms5/authorization"
            auth_body=json.dumps({"operation":"comms5_submit_steward_seed","operation_ref":"safe-readonly-test"}).encode()
            request=Request(auth_url,data=auth_body,headers=headers)
            with urlopen(request,timeout=2) as response:
                self.assertEqual(json.loads(response.read())["status"],"authorized")
            operation_url=f"http://127.0.0.1:{server.server_port}/api/v1/internal/comms5/operation"
            operation_body=json.dumps({"tool":"comms5_submit_steward_seed","arguments":self.seed()}).encode()
            request=Request(operation_url,data=operation_body,headers=headers)
            with urlopen(request,timeout=2) as response:
                self.assertEqual(json.loads(response.read())["status"],"draft_saved")
            self.assertEqual(registry.created[1]["created_by"],"service:chatgpt")
            created_before_denial=registry.created
            authority.allowed=False
            denied_body=json.dumps({"tool":"comms5_submit_steward_seed","arguments":self.seed()}).encode()
            request=Request(operation_url,data=denied_body,headers=headers)
            with self.assertRaises(HTTPError) as denied:
                urlopen(request,timeout=2)
            self.assertEqual(denied.exception.code,403)
            self.assertEqual(registry.created,created_before_denial)
            self.assertEqual(len(authority.calls),3)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_direct_codex_task_requires_delegation_and_stops_before_execution(self):
        from riverview_core.resident_execution.pipeline import ObjectiveStateError

        class IsolatedPipeline:
            authorizer = object()
            def __init__(self): self.record = None; self.submissions = []
            def get_objective(self, objective_id): return self.record
            def submit_objective(self, objective_id, request, criteria, *, scope_ref,
                                 principal, criteria_source):
                self.submissions.append((objective_id, principal.principal_id, scope_ref))
                self.record = {"submitter_id":principal.principal_id,"scope_ref":scope_ref,
                    "request":request,"acceptance_criteria":criteria,
                    "status":"WAITING_FOR_EVIDENCE","evidence":{"status":"unavailable"}}
            def ground_objective(self, objective_id): raise ObjectiveStateError()

        pipeline=IsolatedPipeline()
        operations=Comms5Operations(self.registry,self.lifecycle,objective_pipeline=pipeline)
        args={"task":"Prepare an isolated acceptance fixture.",
            "repository_reference":"repo://ppow1/Riverview-",
            "repository_revision":"a"*40,"authorized_paths":["tests/test_fixture.py"],
            "test_targets":["tests/test_fixture.py"],
            "acceptance_criteria":["No production records are changed."],
            "evidence_requirements":["Return the isolated fixture identifier."],
            "idempotency_key":"codex-isolated-acceptance-0001"}
        with self.assertRaises(PermissionError):
            operations.execute("comms5_submit_direct_engineering_task",args,
                principal_id="service:chatgpt")
        self.assertEqual(pipeline.submissions,[])
        result=operations.execute("comms5_submit_direct_engineering_task",args,
            principal_id="service:chatgpt",delegated_authorized=True)
        self.assertEqual(result["status"],"waiting_for_evidence")
        self.assertEqual(result["idempotent"],False)
        self.assertEqual(pipeline.submissions[0][1:],("service:chatgpt","work-order:engineering"))


if __name__ == "__main__":
    unittest.main()
