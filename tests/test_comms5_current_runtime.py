"""Focused tests for Comms5 operations on current Riverview services.

File Revision: 1.0.1
Component: COMMS5-CURRENT-RUNTIME-OPERATIONS-TESTS
History: New file; no predecessor existed.
Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Verify intent/authority projection and combined durable objective/proposal listing.
"""

import unittest
from datetime import datetime, timezone
import json
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock
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


class Comms5CurrentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.registry = _Registry()
        self.lifecycle = _Lifecycle()
        self.operations = Comms5Operations(self.registry, self.lifecycle)

    def seed(self):
        return {"seed_text": "A bounded idea for Riverview.", "idempotency_key": "seed-1",
                "client_id": "client", "client_type": "chat", "client_name": "ChatGPT",
                "authenticated_principal": "resident:attacker"}

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

    def test_live_backend_status_counts_new_operations_without_marking_partial_complete(self):
        from riverview_core.comms5.dashboard_backend import DashboardReadBackend
        class Backend:
            supported_tools = DashboardReadBackend.supported_tools.fget(None)
            IMPLEMENTATION_STATUS = DashboardReadBackend.IMPLEMENTATION_STATUS
        application = Comms5Application("x" * 48, backend=Backend())
        status = {name: application.implementation_status(name)
                  for name in application.implemented_tools}
        self.assertEqual(sum(value == "IMPLEMENTED" for value in status.values()), 15)
        self.assertEqual(sum(value == "PARTIALLY_IMPLEMENTED" for value in status.values()), 1)
        self.assertEqual(21 - len(status), 5)

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


if __name__ == "__main__":
    unittest.main()
