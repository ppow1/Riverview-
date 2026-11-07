# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_proposal_work_order_lifecycle.py
# Component: INSTITUTIONAL-PROPOSALS
# Revision: 1.1.7
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-CLASSIFICATION-20261021 | Name approved artifact destinations in proposal promotion fixtures
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-002 | Include required artifact contracts in bounded proposal lifecycle fixtures
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Cover dynamic assignment artifacts, multi-file persistence, and independent contract verification
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Use a task-scoped path in typed formation contract fixture
# Purpose: Verify revision approval and promotion into the existing objective pipeline
# Execution Model: Pure command parser tests and disposable PostgreSQL integration
# Observability: Proposal/objective events and correlation IDs are asserted
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL 16; Psycopg 3
# Authority: Unique disposable schema only; no production grants or records
# Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Exercise current-runtime Comms5 objective and proposal projections against a disposable PostgreSQL schema.
# Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Exercise the append-only supersede transition for a confirmed replacement draft.
# Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Exercise idempotent Comms5 CME queue-intent persistence against isolated PostgreSQL and exact Steward grants.
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Initial lifecycle bridge coverage
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Compose authenticated API approval/intake with real disposable worker execution, independent verification, and proposal result linkage
# =============================================================================
"""Proposal approval and work-order bridge tests; PostgreSQL is disposable."""

import hashlib
from http.client import HTTPConnection
import json
import os
import socket
from pathlib import Path
import tempfile
import threading
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1]


def _can_bind(probe, port):
    try:
        probe.bind(("127.0.0.1", port))
        probe.close()
        return True
    except OSError:
        return False


class ProposalCommandTests(unittest.TestCase):
    def test_only_explicit_revision_bound_commands_are_actions(self):
        from riverview_core.resident_execution.proposal_lifecycle import parse_steward_command
        proposal = "proposal:12345678-1234-4234-8234-123456789abc"
        self.assertIsNone(parse_steward_command("Yes, that looks good."))
        self.assertIsNone(parse_steward_command("Please proceed."))
        self.assertEqual(parse_steward_command(
            f"Grace, approve proposal {proposal} revision 2 for internal prototype"), {
                "action": "decision", "proposal_id": proposal, "revision": 2,
                "decision": "APPROVE", "approved_purpose": "internal prototype",
                "reason": "Explicit authenticated conversational Steward decision"})
        self.assertEqual(parse_steward_command(
            f"Grace, create Engineering work order from proposal {proposal} revision 2."), {
                "action": "promote", "proposal_id": proposal, "revision": 2})


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class ProposalPromotionPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.assignment_intake import AuthorizedAssignmentIntake
        from riverview_core.institutional_authority import ExactGrantAuthorizer
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.postgres_migrations import apply_migrations
        from riverview_core.resident_execution.pipeline import GraceExecutionPipeline
        from riverview_core.resident_execution.proposals import ProposalRegistry
        from riverview_core.worker_adapter.knowledge_provider_v1.contract import KnowledgeResult, KnowledgeStatus

        class VerifiedKnowledge:
            @staticmethod
            def result():
                return KnowledgeResult(KnowledgeStatus.VERIFIED, value={"grounded": True},
                    source_references=("repo://docs/verified-source.md",),
                    source_revision="a" * 40, source_sha256="b" * 64,
                    retrieval_complete=True)
            def ground_assignment(self, assignment): return self.result()
            def preflight_action(self, assignment, action): return self.result()
            def reground_assignment(self, assignment, trigger): return self.result()
            def record_learning(self, assignment, outcome): return self.result()

        self.psycopg = psycopg
        self.sql = sql
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {} ").format(sql.Identifier(self.schema)))
        apply_migrations(DSN, schema=self.schema)
        core = ROOT / "src/riverview_core"
        for component in ("assignment_scheduler", "worker_adapter", "institutional_authority",
                          "resident_execution"):
            apply_migrations(DSN, schema=self.schema, migrations_dir=core / component / "migrations")
        self.scope = "work-order:engineering"
        self.tokens = {}
        for principal, actions in {
                "steward:authorized": ("objective.submit", "assignment.create"),
                "worker:lifecycle-test": ("worker.register", "assignment.execute"),
                "verifier:lifecycle-test": ("worker.register", "assignment.verify")}.items():
            token = "test-" + uuid4().hex + uuid4().hex
            self.tokens[principal] = token
            self.admin.execute(sql.SQL("""INSERT INTO {}.institutional_principals
                (principal_id,principal_kind) VALUES (%s,%s)""").format(sql.Identifier(self.schema)),
                (principal, "steward" if principal.startswith("steward:") else "resident"))
            self.admin.execute(sql.SQL("""INSERT INTO {}.principal_credentials
                (credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)""").format(
                    sql.Identifier(self.schema)), (uuid4(), principal,
                    hashlib.sha256(token.encode()).digest()))
            for action in actions:
                self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
                    (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                    VALUES (%s,%s,%s,%s,%s,'rv.policy:proposal-lifecycle-test.v1')""").format(
                        sql.Identifier(self.schema)),
                    (f"{principal}-{action}", principal, action, self.scope, principal))
        resident = "resident:grace"
        self.tokens[resident] = "test-" + uuid4().hex + uuid4().hex
        self.admin.execute(sql.SQL("""INSERT INTO {}.institutional_principals
            (principal_id,principal_kind) VALUES (%s,'resident')""").format(sql.Identifier(self.schema)),
            (resident,))
        self.admin.execute(sql.SQL("""INSERT INTO {}.principal_credentials
            (credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)""").format(
                sql.Identifier(self.schema)), (uuid4(), resident,
                hashlib.sha256(self.tokens[resident].encode()).digest()))
        for action in ("proposal.draft.submit", "proposal.status.read"):
            self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                VALUES (%s,%s,%s,'institution:proposal-drafts','steward:authorized',
                    'rv.policy:proposal-lifecycle-test.v1')""").format(sql.Identifier(self.schema)),
                (f"{resident}-{action}", resident, action))
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.authorizer = ExactGrantAuthorizer(self.schema)
        self.knowledge = VerifiedKnowledge()
        self.pipeline = GraceExecutionPipeline(self.ledger, self.authorizer,
            AuthorizedAssignmentIntake(self.ledger, self.authorizer), self.knowledge)
        self.registry = ProposalRegistry(DSN, schema=self.schema)
        from riverview_core.resident_execution.proposal_lifecycle import ProposalLifecycle
        self.lifecycle = ProposalLifecycle(self.registry, self.pipeline)
        from riverview_core.worker_adapter import PostgresWorkerAdapter
        self.adapter = PostgresWorkerAdapter(DSN, schema=self.schema)
        self.worker_id = "worker:" + uuid4().hex
        self.verifier_id = "verifier:" + uuid4().hex
        self.adapter.register_worker(self.worker_id, ["engineering.bounded-artifact.v1"],
            self.scope, credential=self.tokens["worker:lifecycle-test"])
        self.adapter.register_worker(self.verifier_id, ["assignment.verify.v1"],
            self.scope, credential=self.tokens["verifier:lifecycle-test"])
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.artifact_root = Path(self.temp.name) / "artifacts"

    def tearDown(self):
        self.adapter.close()
        self.registry.close()
        self.ledger.close()
        self.admin.execute(self.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
            self.sql.Identifier(self.schema)))
        self.admin.close()
        self.temp.cleanup()

    @property
    def content(self):
        return {"title": "Bounded test proposal", "summary": "A scoped report task.",
            "objective": "Prepare a source-grounded report at reports/lifecycle.json or reports/http-result.json.",
            "scope": "Create and independently verify one bounded Engineering artifact at an explicitly named path.",
            "proposed_approach": "Ground the objective, then use the existing Engineering pipeline.",
            "constraints": ["No production changes."],
            "acceptance_criteria": ["The existing objective pipeline receives this approved revision."],
            "tags": ["engineering"]}

    def test_resident_draft_capability_persists_idempotently_with_exact_grants(self):
        from riverview_core.resident_execution.proposals import ResidentProposalDraftService
        from riverview_core.resident_execution.capability_registry import GraceCapabilityRegistry
        service = ResidentProposalDraftService(self.registry, self.authorizer,
            lambda: self.psycopg.connect(DSN))
        receipt = service.create(self.content, credential=self.tokens["resident:grace"],
            expected_principal="resident:grace", correlation_id="clock-acceptance-1",
            idempotency_key="clock-acceptance-draft-1")
        retry = service.create(self.content, credential=self.tokens["resident:grace"],
            expected_principal="resident:grace", correlation_id="clock-acceptance-1",
            idempotency_key="clock-acceptance-draft-1")
        self.assertEqual(receipt["proposal_id"], retry["proposal_id"])
        self.assertEqual(receipt["content_sha256"], retry["content_sha256"])
        self.assertEqual(receipt["author_principal_id"], "resident:grace")
        self.assertTrue(receipt["readback_verified"])
        self.assertEqual(receipt["lifecycle_status"], "DRAFT")
        self.assertEqual(service.read(receipt["proposal_id"],
            credential=self.tokens["resident:grace"])["proposal"]["created_by"], "resident:grace")
        with self.assertRaises(PermissionError):
            service.create(self.content, credential=self.tokens["resident:grace"],
                expected_principal="resident:other", correlation_id="clock-acceptance-1",
                idempotency_key="clock-acceptance-draft-1")
        class Authority:
            @staticmethod
            def set_office_state(*_args, **_kwargs):
                raise AssertionError("proposal operation must not change office authority")
        tools = GraceCapabilityRegistry(dsn=DSN,
            resident_credential=self.tokens["resident:grace"], authorizer=self.authorizer,
            authority_registry=Authority(), proposal_registry=self.registry,
            authority_schema=self.schema, runtime_schema=self.schema,
            connect=lambda: self.psycopg.connect(DSN))
        specs = tools.tool_specs()
        spec = next(item for item in specs if item["name"] == "proposal.draft.submit")
        self.assertEqual(spec["inputSchema"]["properties"]["scope_ref"]["enum"],
            ["institution:proposal-drafts"])
        with self.psycopg.connect(DSN) as debug_connection, debug_connection.cursor() as debug_cursor:
            write_grant = self.authorizer.require(debug_cursor, self.tokens["resident:grace"],
                "proposal.draft.submit", "institution:proposal-drafts")
            read_grant = self.authorizer.require(debug_cursor, self.tokens["resident:grace"],
                "proposal.status.read", "institution:proposal-drafts")
        self.assertEqual(write_grant["principal_id"], read_grant["principal_id"])
        tool_result = tools.invoke("proposal.draft.submit", {"scope_ref": "institution:proposal-drafts",
            "input": {"content": self.content, "correlation_id": "capability-path-e2e",
                "idempotency_key": "capability-path-idempotency"}})
        self.assertEqual(tool_result["status"], "ok", {"tool": tool_result,
            "snapshot": tools.snapshot(capability_id="proposal.draft.submit",
                scope_ref="institution:proposal-drafts")})
        self.assertEqual(tool_result["result"]["author_principal_id"], "resident:grace")
        self.assertTrue(tool_result["result"]["readback_verified"])
        status_spec = next(item for item in specs if item["name"] == "proposal.status.read")
        self.assertEqual(status_spec["inputSchema"]["properties"]["scope_ref"]["enum"],
            ["institution:proposal-drafts"])
        status_result = tools.invoke("proposal.status.read", {
            "scope_ref": "institution:proposal-drafts",
            "input": {"proposal_id": tool_result["result"]["proposal_id"]}})
        self.assertEqual(status_result["status"], "ok", status_result)
        self.assertEqual(status_result["result"]["lifecycle_status"], "DRAFT")
        self.assertEqual(status_result["result"]["content_sha256"],
                         tool_result["result"]["content_sha256"])
        self.assertEqual(status_result["result"]["author_principal_id"], "resident:grace")

        # Exercise the same catalog -> model-router directive -> native capability
        # executor path used by Grace, with a controlled model response and the real
        # exact-grant authority and proposal PostgreSQL registries above.
        from riverview_core.local_reasoning_provider import ChatCompletion, ProviderReadiness
        from riverview_core.resident_execution.internal_tools import GraceInternalTools
        from riverview_core.resident_execution.model_router import GraceModelRouter

        class Model:
            model = "controlled-proposal-model"
            model_sha256 = "b" * 64
            provider_id = "test.controlled-proposal-model"
            def __init__(self, responses): self.responses, self.calls = list(responses), []
            def readiness(self): return ProviderReadiness("READY", self.model, "ready")
            def complete_chat(self, messages, *, max_tokens, expected_revision,
                              timeout_seconds=120):
                self.calls.append(messages)
                return ChatCompletion(self.responses.pop(0), self.model, 10, 8, "stop",
                    provider_id=self.provider_id)

        content = {**self.content, "title": "Model-routed clock proposal"}
        directive = {"name": "proposal.draft.submit", "arguments": {
            "scope_ref": "institution:proposal-drafts", "input": {
                "content": content, "correlation_id": "model-router-clock-e2e",
                "idempotency_key": "model-router-clock-e2e-v1"}}}
        model = Model(["<rv-tool-call>" + json.dumps(directive, separators=(",", ":")) +
                       "</rv-tool-call>",
                       "The proposal draft was persisted and awaits Steward review."])
        class EmptyBackend:
            supported_tools = frozenset()
            def call(self, *_args, **_kwargs): raise AssertionError("no Comms5 tool call expected")
        internal_tools = GraceInternalTools(backend=EmptyBackend(), capability_registry=tools)
        router = GraceModelRouter(autonomic=model, vision=model, reasoning=model,
                                  internal_tools=internal_tools)
        completion = router.complete_chat([{"role": "user", "content":
            "Prepare and submit a date/time clock proposal for Steward approval."}],
            max_tokens=128, expected_revision=router.model_sha256,
            required_capability="grace.reasoning.80b")
        self.assertEqual(len(completion.internal_tool_results), 1)
        model_receipt = completion.internal_tool_results[0]["result"]
        persisted_model_proposal = self.registry.get(model_receipt["proposal_id"])
        self.assertEqual(model_receipt["lifecycle_status"], "DRAFT")
        self.assertTrue(model_receipt["readback_verified"])
        self.assertEqual(persisted_model_proposal["proposal"]["created_by"], "resident:grace")
        self.assertEqual(persisted_model_proposal["revision"]["content_sha256"],
                         model_receipt["content_sha256"])

    def test_authenticated_resident_http_proposal_api_uses_the_internal_registry(self):
        from riverview_core.resident_execution.proposals import ResidentProposalDraftService
        from riverview_core.status_dashboard.server import DashboardHTTPServer
        class Projection:
            pass
        service = ResidentProposalDraftService(self.registry, self.authorizer,
            lambda: self.psycopg.connect(DSN))
        token_path = Path(self.temp.name) / "dashboard-token"
        token_path.write_text("D" * 43, encoding="ascii")
        token_path.chmod(0o600)
        with socket.socket() as probe:
            for port in range(8799, 8699, -1):
                try:
                    probe.bind(("127.0.0.1", port))
                    break
                except OSError:
                    continue
            else:
                self.fail("no loopback dashboard test port available")
        server = DashboardHTTPServer("127.0.0.1", port, token_path, Projection(),
            ROOT / "src/riverview_core/status_dashboard/static", proposal_registry=self.registry,
            resident_proposal_service=service)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = json.dumps({"content": self.content,
                "correlation_id": "native-clock-http-e2e",
                "expected_principal": "resident:grace",
                "idempotency_key": "native-clock-http-e2e"})
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            connection.request("POST", "/api/v1/internal/resident-proposals", body,
                headers={"Authorization": "Bearer " + self.tokens["resident:grace"],
                         "Content-Type": "application/json"})
            created = connection.getresponse()
            receipt = json.loads(created.read())
            self.assertEqual(created.status, 201)
            connection.close()
            self.assertTrue(receipt["readback_verified"])
            self.assertEqual(receipt["lifecycle_status"], "DRAFT")
            self.assertEqual(receipt["author_principal_id"], "resident:grace")
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            connection.request("GET", "/api/v1/internal/resident-proposals/" + receipt["proposal_id"],
                headers={"Authorization": "Bearer " + self.tokens["resident:grace"]})
            response = connection.getresponse()
            record = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(record["revision"]["content_sha256"], receipt["content_sha256"])
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def ready_proposal(self, *, actor="steward:authorized", key="proposal:test"):
        record = self.registry.create_draft(self.content, created_by=actor,
            origin_kind="steward_authored", source_references=[{"kind": "test", "id": key}],
            provenance={"test": True}, idempotency_key=key)
        proposal_id = record["proposal"]["proposal_id"]
        self.registry.transition(proposal_id, 1, "READY_FOR_REVIEW", actor_id=actor,
            reason="Formal proposal ready for review")
        self.registry.transition(proposal_id, 1, "READY_FOR_STEWARD_DECISION", actor_id=actor,
            reason="Review disposition recorded")
        return self.registry.get(proposal_id)

    def approve(self, record, *, actor="steward:authorized", key="decision:test"):
        from riverview_core.resident_execution.proposal_lifecycle import ProposalLifecycle
        return self.lifecycle.decide(record["proposal"]["proposal_id"], 1,
            decision="APPROVE", actor_id=actor, reason="Bounded internal test approval",
            idempotency_key=key,
            content_sha256=record["revision"]["content_sha256"],
            approved_purpose="disposable Engineering acceptance",
            authority_reference="account-auth-session:test-account:steward")

    def test_unapproved_cannot_promote_and_missing_submit_grant_preserves_approval(self):
        from riverview_core.resident_execution.proposals import ProposalConflict
        record = self.ready_proposal()
        with self.assertRaises(ProposalConflict):
            self.lifecycle.promote(record["proposal"]["proposal_id"], 1, actor_id="steward:authorized")
        approved = self.approve(record)
        self.assertEqual(approved["proposal"]["lifecycle_status"], "APPROVED")
        self.admin.execute(self.sql.SQL("DELETE FROM {}.authority_grants WHERE grant_id=%s").format(
            self.sql.Identifier(self.schema)), ("steward:authorized-objective.submit",))
        from riverview_core.resident_execution.pipeline import ObjectiveNotAuthorized
        with self.assertRaises(ObjectiveNotAuthorized):
            self.lifecycle.promote(record["proposal"]["proposal_id"], 1, actor_id="steward:authorized")
        self.assertEqual(self.registry.get(record["proposal"]["proposal_id"])["proposal"]["lifecycle_status"], "APPROVED")

    def test_approved_proposal_without_assignment_grant_stays_approved_and_grounded(self):
        record = self.ready_proposal()
        self.approve(record)
        self.admin.execute(self.sql.SQL("DELETE FROM {}.authority_grants WHERE grant_id=%s").format(
            self.sql.Identifier(self.schema)), ("steward:authorized-assignment.create",))
        promoted = self.lifecycle.promote(record["proposal"]["proposal_id"], 1,
            actor_id="steward:authorized")
        self.assertEqual(promoted["status"], "GROUNDED")
        self.assertIsNone(promoted["assignment_id"])
        self.assertEqual(self.registry.get(record["proposal"]["proposal_id"])["proposal"]["lifecycle_status"], "APPROVED")

    def test_exact_approval_is_idempotent_and_promotes_into_existing_pipeline(self):
        from riverview_core.resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep
        from riverview_core.resident_execution.worker import BoundedLocalCodingWorker
        from riverview_core.resident_execution.verifier import BoundedArtifactVerifier
        from riverview_core.worker_adapter import ContinuousWorker
        from riverview_core.resident_execution.proposals import ResidentProposalDraftService
        drafts = ResidentProposalDraftService(self.registry, self.authorizer,
            lambda: self.psycopg.connect(DSN))
        receipt = drafts.create(self.content, credential=self.tokens["resident:grace"],
            expected_principal="resident:grace", correlation_id="clock-e2e-correlation",
            idempotency_key="clock-e2e-proposal-draft")
        proposal_id = receipt["proposal_id"]
        self.registry.transition(proposal_id, 1, "READY_FOR_REVIEW", actor_id="service:review-queue",
            reason="Formal proposal entered independent review")
        self.registry.transition(proposal_id, 1, "READY_FOR_STEWARD_DECISION",
            actor_id="service:review-queue", reason="Independent review disposition recorded")
        record = self.registry.get(proposal_id)
        self.assertEqual(record["proposal"]["created_by"], "resident:grace")
        self.assertEqual(record["revision"]["source_references"], [
            {"kind": "resident_correlation", "id": "clock-e2e-correlation"}])
        approved = self.approve(record)
        retried = self.approve(record)
        self.assertEqual(approved["proposal"]["lifecycle_status"], "APPROVED")
        self.assertEqual(retried["proposal"]["lifecycle_status"], "APPROVED")
        promoted = self.lifecycle.promote(proposal_id, 1, actor_id="steward:authorized")
        repeated = self.lifecycle.promote(proposal_id, 1, actor_id="steward:authorized")
        self.assertEqual(promoted["objective_id"], repeated["objective_id"])
        self.assertTrue(repeated["reused"])
        objective = self.pipeline.get_objective(promoted["objective_id"])
        self.assertEqual(objective["status"], "GROUNDED")
        self.assertEqual(self.pipeline.objective_proposal_reference(promoted["objective_id"]), {
            "proposal_id": proposal_id, "revision": 1,
            "content_sha256": record["revision"]["content_sha256"],
            "approval_event_key": "decision:test",
            "source_references": record["revision"]["source_references"],
            "privacy_classification": "institutional", "retention_policy": "standard",
            "approved_purpose": "disposable Engineering acceptance",
            "objective_submit_grant_id": "steward:authorized-objective.submit"})
        plan = PlanProposal("Bounded Engineering work", (PlanStep("report",
            "Write the assignment-bound artifact",
            tuple(objective["acceptance_criteria"]), artifact_requirements=(
                ArtifactRequirement("lifecycle-report", "reports/lifecycle.json", "application/json",
                    tuple(objective["acceptance_criteria"])),)),), 0)
        self.pipeline.record_proposal(promoted["objective_id"], plan)
        assignment_id = "assignment:" + uuid4().hex
        self.pipeline.authorize_and_dispatch(promoted["objective_id"], assignment_id,
            credential=self.tokens["steward:authorized"], authority_ref=self.scope,
            idempotency_key="proposal-lifecycle-dispatch:" + assignment_id, step_id="report")
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
            "proposal-lifecycle-ready:" + assignment_id, actor_id="event-processor")
        worker = ContinuousWorker(self.adapter, self.worker_id,
            self.tokens["worker:lifecycle-test"], knowledge=self.knowledge,
            action=BoundedLocalCodingWorker(self.pipeline, self.artifact_root),
            action_effect_class="retry_safe", action_capability="engineering.bounded-artifact.v1")
        outcome = worker.run_once(assignment_id=assignment_id)
        self.assertEqual(outcome["status"], "AWAITING_VERIFICATION")
        decision = self.adapter.verify_attempt(assignment_id, outcome["attempt_id"],
            self.verifier_id, self.tokens["verifier:lifecycle-test"],
            BoundedArtifactVerifier(self.artifact_root, self.pipeline),
            idempotency_key="proposal-lifecycle-verify:" + assignment_id)
        self.assertEqual(decision.status.value, "ACCEPTED")
        self.pipeline.record_verified_completion(promoted["objective_id"], assignment_id)
        self.assertEqual(self.lifecycle.reconcile_links(), 1)
        final = self.registry.get(proposal_id)
        self.assertEqual(len(final["work_order_links"]), 1)
        execution = [event for event in final["events"]
            if event["event_type"] == "proposal.execution_updated"]
        self.assertEqual(len(execution), 1)
        self.assertEqual(execution[0]["payload"]["status"], "completed")
        self.assertEqual(execution[0]["payload"]["evidence"]["verification_decision"], "ACCEPTED")
        with self.registry.db.cursor() as cur:
            self.registry._path(cur)
            cur.execute("""SELECT count(*) AS count FROM institutional_proposal_events
                WHERE proposal_id=%s AND revision=1 AND event_type='proposal.work_order_requested'""",
                (proposal_id,))
            self.assertEqual(cur.fetchone()["count"], 1)

    @unittest.skipUnless(os.environ.get("R3_SOURCE_ROOT") and
                         os.environ.get("R3_HR_SOURCE_ROOT"),
        "R3_SOURCE_ROOT and R3_HR_SOURCE_ROOT are required for the cross-repository native-tool acceptance test")
    def test_r3_native_tool_internal_registry_to_verified_engineering_completion(self):
        import importlib
        import sqlite3
        import sys
        import time
        from http.server import ThreadingHTTPServer
        r3_root = Path(os.environ["R3_SOURCE_ROOT"]).resolve()
        hr_root = Path(os.environ["R3_HR_SOURCE_ROOT"]).resolve()
        sys.path.insert(0, str(r3_root))
        self.addCleanup(lambda: sys.path.remove(str(r3_root)) if str(r3_root) in sys.path else None)
        import runtime
        runtime.__path__ = list(runtime.__path__)
        hr_runtime_path = str(hr_root / "runtime")
        if not (Path(hr_runtime_path) / "hr_store.py").is_file():
            self.fail("R3_HR_SOURCE_ROOT must contain the authoritative HRStore implementation")
        runtime.__path__.append(hr_runtime_path)
        self.addCleanup(lambda: runtime.__path__.remove(hr_runtime_path)
            if hr_runtime_path in runtime.__path__ else None)
        authority_module = importlib.import_module("runtime.capability_authority")
        identity_module = importlib.import_module("runtime.resident_identity")
        native_module = importlib.import_module("runtime.native_tools")
        tool_server_module = importlib.import_module("runtime.tool_server")
        hr_store_module = importlib.import_module("runtime.hr_store")
        hr_records_module = importlib.import_module("runtime.hr_records")

        from riverview_core.resident_execution.proposals import ResidentProposalDraftService
        from riverview_core.status_dashboard.server import DashboardHTTPServer
        resident_service = ResidentProposalDraftService(self.registry, self.authorizer,
            lambda: self.psycopg.connect(DSN))
        token_path = Path(self.temp.name) / "dashboard-token"
        token_path.write_text("D" * 43, encoding="ascii")
        token_path.chmod(0o600)
        with socket.socket() as probe:
            dashboard_port = next((port for port in range(8799, 8699, -1)
                if _can_bind(probe, port)), None)
        self.assertIsNotNone(dashboard_port)
        class Projection:
            pass
        dashboard = DashboardHTTPServer("127.0.0.1", dashboard_port, token_path,
            Projection(), ROOT / "src/riverview_core/status_dashboard/static",
            proposal_registry=self.registry, resident_proposal_service=resident_service)
        dashboard_thread = threading.Thread(target=dashboard.serve_forever, daemon=True)
        dashboard_thread.start()
        self.addCleanup(dashboard.server_close)
        self.addCleanup(dashboard_thread.join, 3)
        self.addCleanup(dashboard.shutdown)

        r3_db = Path(self.temp.name) / "r3-authority.db"
        tool_db = Path(self.temp.name) / "r3-tool-audit.db"
        hr_db = Path(self.temp.name) / "r3-hr.db"
        resident_principal = "resident:fixture-" + uuid4().hex
        r3_principal = "resident:r3-fixture-" + uuid4().hex
        hr_resident_id = "r3:fixture-" + uuid4().hex
        resident_credential = "test-" + uuid4().hex + uuid4().hex
        institutional_write_grant_id = "grant:rv-proposal-write-" + uuid4().hex
        institutional_read_grant_id = "grant:rv-proposal-read-" + uuid4().hex
        r3_write_grant_id = "grant:r3-proposal-write-" + uuid4().hex
        r3_read_grant_id = "grant:r3-proposal-read-" + uuid4().hex
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.institutional_principals
            (principal_id,principal_kind) VALUES (%s,'resident')""").format(
                self.sql.Identifier(self.schema)), (resident_principal,))
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.principal_credentials
            (credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)""").format(
                self.sql.Identifier(self.schema)), (uuid4(), resident_principal,
                hashlib.sha256(resident_credential.encode()).digest()))
        for action, grant_id in (("proposal.draft.submit", institutional_write_grant_id),
                                 ("proposal.status.read", institutional_read_grant_id)):
            self.admin.execute(self.sql.SQL("""INSERT INTO {}.authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                VALUES (%s,%s,%s,'institution:proposal-drafts','steward:authorized',
                    'rv.policy:proposal-lifecycle-test.v1')""").format(
                        self.sql.Identifier(self.schema)),
                (grant_id, resident_principal, action))
        hr_store = hr_store_module.HRStore(hr_db)
        hr_record = hr_records_module.ResidentHRRecord(
            resident_id=hr_resident_id, display_name="Test Resident", office="office:grace",
            status="active", extensions={
                "r3_principal": hr_records_module.HRField(
                    r3_principal, "confidential"),
                "authority_principal": hr_records_module.HRField(
                    resident_principal, "confidential"),
            })
        hr_store.put(hr_record)
        hr_store.close()
        authority_module.initialize_empty_schema(r3_db)
        resident_id = uuid4().hex
        r3_credential = identity_module.PREFIX + "." + resident_id + "." + "A" * 43
        now = time.time()
        with sqlite3.connect(r3_db) as db:
            db.execute("""INSERT INTO resident_credentials
                (credential_id,principal,secret_hash,created_at,expires_at,revoked_at,
                 issued_by,idempotency_key) VALUES (?,?,?,?,?,?,?,?)""",
                (resident_id, r3_principal,
                 identity_module.digest_secret(resident_id, r3_credential), now,
                 now + 3600, None, "human:steward:test", "cross-system-clock-test"))
            db.executemany("""INSERT INTO capability_grants
                (grant_id,principal,resource_ref,action,operation,scope_ref,active,approved_by)
                VALUES (?,?,?,?,?,?,1,?)""", [
                (r3_write_grant_id, r3_principal,
                 "riverview:institutional-proposals", "proposal.draft.submit", "write",
                 "institution:proposal-drafts", "human:steward:test"),
                (r3_read_grant_id, r3_principal,
                 "riverview:institutional-proposals", "proposal.status.read", "read",
                 "institution:proposal-drafts", "human:steward:test")])
        institutional_credential = Path(self.temp.name) / "resident-credential"
        institutional_credential.write_text(resident_credential, encoding="ascii")
        institutional_credential.chmod(0o600)
        router = tool_server_module.build_router(audit_db=tool_db, authority_db=r3_db,
            institutional_proposal_url=(f"http://127.0.0.1:{dashboard.server_port}"
                "/api/v1/internal/resident-proposals"),
            institutional_proposal_credential_file=institutional_credential,
            hr_database=hr_db)
        native_server = ThreadingHTTPServer(("127.0.0.1", 0),
            tool_server_module.handler_for(router))
        native_thread = threading.Thread(target=native_server.serve_forever, daemon=True)
        native_thread.start()
        self.addCleanup(native_server.server_close)
        self.addCleanup(native_thread.join, 3)
        self.addCleanup(native_server.shutdown)
        native = native_module.NativeTools(f"http://127.0.0.1:{native_server.server_port}",
            timeout=5, allowed_tools=("r3.proposal.submit", "r3.proposal.status"),
            credential=r3_credential)
        submit_tool = next(item for item in native.discover()
            if item["tool"] == "r3.proposal.submit")
        submitted = json.loads(native.invoke(submit_tool, {"content": self.content},
            correlation_id="website-clock-cross-repository-e2e"))["result"]
        proposal_id = submitted["proposal_id"]
        retried = json.loads(native.invoke(submit_tool, {"content": self.content},
            correlation_id="website-clock-cross-repository-e2e"))["result"]
        self.assertEqual(retried["proposal_id"], proposal_id)
        status_tool = next(item for item in native.discover()
            if item["tool"] == "r3.proposal.status")
        status = json.loads(native.invoke(status_tool, {"proposal_id": proposal_id},
            correlation_id="website-clock-cross-repository-status"))["result"]
        self.assertEqual(status["lifecycle_status"], "DRAFT")
        self.assertEqual(status["content_sha256"], submitted["content_sha256"])
        persisted = self.registry.get(proposal_id)
        self.assertEqual(persisted["proposal"]["created_by"], resident_principal)
        self.assertEqual(persisted["revision"]["content_sha256"], submitted["content_sha256"])
        self.registry.transition(proposal_id, 1, "READY_FOR_REVIEW",
            actor_id="service:review-queue", reason="Independent review queued")
        self.registry.transition(proposal_id, 1, "READY_FOR_STEWARD_DECISION",
            actor_id="service:review-queue", reason="Review disposition recorded")
        approved = self.approve(persisted, key="website-clock-cross-repo-approval")
        self.assertEqual(approved["proposal"]["lifecycle_status"], "APPROVED")
        promoted = self.lifecycle.promote(proposal_id, 1, actor_id="steward:authorized")
        objective = self.pipeline.get_objective(promoted["objective_id"])
        from riverview_core.resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep
        from riverview_core.resident_execution.worker import BoundedLocalCodingWorker
        from riverview_core.resident_execution.verifier import BoundedArtifactVerifier
        from riverview_core.worker_adapter import ContinuousWorker
        plan = PlanProposal("Website clock proposal delivery", (PlanStep("clock-proposal",
            "Create a disposable acceptance artifact representing the approved clock proposal",
            tuple(objective["acceptance_criteria"]), artifact_requirements=(
                ArtifactRequirement("clock-acceptance", "reports/http-result.json",
                    "application/json", tuple(objective["acceptance_criteria"])),)),), 0)
        self.pipeline.record_proposal(promoted["objective_id"], plan)
        assignment_id = "assignment:" + uuid4().hex
        self.pipeline.authorize_and_dispatch(promoted["objective_id"], assignment_id,
            credential=self.tokens["steward:authorized"], authority_ref=self.scope,
            idempotency_key="website-clock-cross-repo-dispatch", step_id="clock-proposal")
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
            "website-clock-cross-repo-ready", actor_id="event-processor")
        worker = ContinuousWorker(self.adapter, self.worker_id,
            self.tokens["worker:lifecycle-test"], knowledge=self.knowledge,
            action=BoundedLocalCodingWorker(self.pipeline, self.artifact_root),
            action_effect_class="retry_safe", action_capability="engineering.bounded-artifact.v1")
        execution = worker.run_once(assignment_id=assignment_id)
        self.assertEqual(execution["status"], "AWAITING_VERIFICATION")
        decision = self.adapter.verify_attempt(assignment_id, execution["attempt_id"],
            self.verifier_id, self.tokens["verifier:lifecycle-test"],
            BoundedArtifactVerifier(self.artifact_root, self.pipeline),
            idempotency_key="website-clock-cross-repo-review")
        self.assertEqual(decision.status.value, "ACCEPTED")
        self.pipeline.record_verified_completion(promoted["objective_id"], assignment_id)
        self.lifecycle.reconcile_links()
        final = self.registry.get(proposal_id)
        self.assertEqual(self.pipeline.get_objective(promoted["objective_id"])["status"], "COMPLETED")
        self.assertEqual(final["work_order_links"][0]["assignment_id"], assignment_id)
        self.assertEqual(final["events"][-1]["payload"]["status"], "completed")
        evidence = {"schema_version": "riverview.grace.internal-autonomy-e2e.v1",
            "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "r3_principal": r3_principal,
            "hr_resident_id": hr_resident_id,
            "r3_write_grant_id": r3_write_grant_id,
            "r3_read_grant_id": r3_read_grant_id,
            "institutional_write_grant_id": institutional_write_grant_id,
            "institutional_read_grant_id": institutional_read_grant_id,
            "proposal_id": proposal_id, "proposal_revision": 1,
            "proposal_sha256": submitted["content_sha256"],
            "proposal_author": resident_principal, "proposal_state": "APPROVED",
            "steward_decision_event_key": "website-clock-cross-repo-approval",
            "objective_id": promoted["objective_id"], "assignment_id": assignment_id,
            "execution_attempt_id": execution["attempt_id"],
            "worker_id": self.worker_id, "verifier_id": self.verifier_id,
            "review_decision": decision.status.value,
            "objective_state": "COMPLETED", "proposal_execution_state": "completed",
            "dispatch_count": 1, "internal_api": "/api/v1/internal/resident-proposals",
            "comms5_used": False, "website_changed": False,
            "transition_evidence": [
                {"transition": "proposal.draft.persisted", "proposal_id": proposal_id,
                 "revision": 1, "content_sha256": submitted["content_sha256"],
                 "status": "DRAFT", "readback_verified": True},
                {"transition": "proposal.steward_approved", "proposal_id": proposal_id,
                 "event_key": "website-clock-cross-repo-approval", "status": "APPROVED"},
                {"transition": "objective.promoted", "objective_id": promoted["objective_id"],
                 "status": objective["status"]},
                {"transition": "assignment.dispatched", "assignment_id": assignment_id,
                 "dispatch_count": 1},
                {"transition": "engineering.executed", "assignment_id": assignment_id,
                 "attempt_id": execution["attempt_id"], "status": execution["status"]},
                {"transition": "independent_review.recorded", "assignment_id": assignment_id,
                 "attempt_id": execution["attempt_id"], "decision": decision.status.value},
                {"transition": "objective.accepted_completion", "objective_id": promoted["objective_id"],
                 "assignment_id": assignment_id, "status": "COMPLETED"}]}
        evidence_path = os.environ.get("RIVERVIEW_E2E_EVIDENCE_FILE")
        if evidence_path:
            Path(evidence_path).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print("INTERNAL_AUTONOMY_E2E=" + json.dumps(evidence, sort_keys=True))

    def test_authenticated_http_decision_and_promotion_use_the_same_lifecycle(self):
        from riverview_core.status_dashboard.server import DashboardHTTPServer

        record = self.ready_proposal(key="proposal:http-lifecycle")
        proposal_id = record["proposal"]["proposal_id"]

        class Projection:
            pass

        class AccountSessions:
            def authenticate(_self, verifier, *, csrf_token=None, state_changing=False):
                from riverview_core.account_auth import AuthDenied
                if state_changing and csrf_token != "C" * 43:
                    raise AuthDenied()
                if verifier == "S" * 43:
                    return {"account_id": "account-steward", "roles": ("steward",),
                        "authority_principal_id": "steward:authorized"}
                if verifier == "V" * 43:
                    return {"account_id": "account-viewer", "roles": ("viewer",),
                        "authority_principal_id": "resident:viewer"}
                raise AuthDenied()

            def require_role(_self, identity, *roles):
                from riverview_core.account_auth import AuthDenied
                if not set(identity.get("roles", ())) & set(roles):
                    raise AuthDenied()

        class ConversationStore:
            db = self.ledger.db
            def _path(_self, cur):
                self.ledger._set_search_path(cur)

        class ConversationService:
            store = ConversationStore()
            def history(_self, authority, conversation_id):
                if authority.principal_id != "steward:authorized":
                    raise PermissionError("Steward conversation access required")
                return {"conversation_id": conversation_id}

        with tempfile.TemporaryDirectory() as temp:
            token_path = Path(temp) / "dashboard-token"
            token_path.write_text("T" * 43, encoding="ascii")
            token_path.chmod(0o600)
            port = None
            for candidate in range(8799, 8699, -1):
                probe = socket.socket()
                try:
                    probe.bind(("127.0.0.1", candidate))
                    port = candidate
                    break
                except OSError:
                    pass
                finally:
                    probe.close()
            if port is None:
                self.fail("no free dashboard test port in the reserved range")
            server = DashboardHTTPServer("127.0.0.1", port, token_path, Projection(),
                ROOT / "src/riverview_core/status_dashboard/static",
                objective_pipeline=self.pipeline, conversation_service=ConversationService(),
                account_auth_service=AccountSessions(), proposal_registry=self.registry)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def request(method, path, body=None, *, verifier="S", csrf=None):
                headers = {"Cookie": "rv_account_session=" + verifier * 43}
                if csrf:
                    headers["X-Riverview-CSRF"] = csrf
                if body is not None:
                    headers["Content-Type"] = "application/json"
                connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                connection.request(method, path,
                    body=json.dumps(body) if body is not None else None, headers=headers)
                response = connection.getresponse()
                result = response.status, response.read()
                connection.close()
                return result

            path = f"/api/v1/institutional-proposals/{proposal_id}/decision"
            decision = {"revision": 1, "decision": "APPROVE", "reason": "bounded test",
                "idempotency_key": "decision:http-test", "content_sha256": record["revision"]["content_sha256"],
                "approved_purpose": "disposable lifecycle test"}
            try:
                self.assertEqual(request("POST", path, decision, verifier="V", csrf="C" * 43)[0], 403)
                self.assertNotEqual(request("POST", path, decision)[0], 200)
                approved_status, approved = request("POST", path, decision, csrf="C" * 43)
                self.assertEqual(approved_status, 200, approved.decode())
                self.assertEqual(json.loads(approved)["proposal"]["lifecycle_status"], "APPROVED")

                intake_path = f"/api/v1/institutional-proposals/{proposal_id}/work-orders"
                first_status, first = request("POST", intake_path, {"revision": 1}, csrf="C" * 43)
                second_status, second = request("POST", intake_path, {"revision": 1}, csrf="C" * 43)
                self.assertEqual(first_status, 202, first.decode())
                self.assertEqual(second_status, 202, second.decode())
                first_result, second_result = json.loads(first), json.loads(second)
                self.assertEqual(first_result["objective_id"], second_result["objective_id"])
                self.assertTrue(second_result["reused"])
                conversation_id = uuid4()
                self.admin.execute(self.sql.SQL("""INSERT INTO {}.resident_conversations
                    (conversation_id,office_id,owner_principal_id) VALUES (%s,'office:grace',%s)""").format(
                        self.sql.Identifier(self.schema)), (conversation_id, "steward:authorized"))
                command = (f"Grace, create Engineering work order from proposal {proposal_id} revision 1.")
                self.admin.execute(self.sql.SQL("""INSERT INTO {}.resident_conversation_events
                    (conversation_id,sequence,request_id,client_message_id,event_type,actor_kind,actor_id,body)
                    VALUES (%s,1,%s,%s,'user_message','principal',%s,%s)""").format(
                        self.sql.Identifier(self.schema)), (conversation_id, uuid4(), uuid4(),
                            "steward:authorized", command))
                command_status, command_body = request("POST",
                    "/api/v1/institutional-proposals/conversational-command",
                    {"conversation_id": str(conversation_id), "source_sequence": 1}, csrf="C" * 43)
                self.assertEqual(command_status, 202, command_body.decode())
                command_result = json.loads(command_body)["result"]
                self.assertEqual(command_result["objective_id"], first_result["objective_id"])
                self.assertTrue(command_result["reused"])
                from riverview_core.resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep
                from riverview_core.resident_execution.worker import BoundedLocalCodingWorker
                from riverview_core.resident_execution.verifier import BoundedArtifactVerifier
                from riverview_core.worker_adapter import ContinuousWorker
                objective = self.pipeline.get_objective(first_result["objective_id"])
                plan = PlanProposal("Authenticated proposal execution", (PlanStep(
                    "report", "Write and verify the approved bounded artifact",
                    tuple(objective["acceptance_criteria"]), artifact_requirements=(
                        ArtifactRequirement("http-report", "reports/http-result.json", "application/json",
                            tuple(objective["acceptance_criteria"])),)),), 0)
                self.pipeline.record_proposal(first_result["objective_id"], plan)
                assignment_id = "assignment:" + uuid4().hex
                self.pipeline.authorize_and_dispatch(first_result["objective_id"], assignment_id,
                    credential=self.tokens["steward:authorized"], authority_ref=self.scope,
                    idempotency_key="proposal-http-dispatch:" + assignment_id, step_id="report")
                self.ledger.transition(assignment_id, "ready", "event_processor_ready",
                    "proposal-http-ready:" + assignment_id, actor_id="event-processor")
                worker = ContinuousWorker(self.adapter, self.worker_id,
                    self.tokens["worker:lifecycle-test"], knowledge=self.knowledge,
                    action=BoundedLocalCodingWorker(self.pipeline, self.artifact_root),
                    action_effect_class="retry_safe", action_capability="engineering.bounded-artifact.v1")
                outcome = worker.run_once(assignment_id=assignment_id)
                self.assertEqual(outcome["status"], "AWAITING_VERIFICATION")
                decision = self.adapter.verify_attempt(assignment_id, outcome["attempt_id"],
                    self.verifier_id, self.tokens["verifier:lifecycle-test"],
                    BoundedArtifactVerifier(self.artifact_root, self.pipeline),
                    idempotency_key="proposal-http-verify:" + assignment_id)
                self.assertEqual(decision.status.value, "ACCEPTED")
                self.pipeline.record_verified_completion(first_result["objective_id"], assignment_id)
                self.assertEqual(self.lifecycle.reconcile_links(), 1)
                self.assertEqual(self.lifecycle.reconcile_links(), 1)
                detail_status, detail = request("GET",
                    f"/api/v1/institutional-proposals/{proposal_id}?revision=1")
                self.assertEqual(detail_status, 200)
                detail_result = json.loads(detail)
                self.assertEqual(detail_result["proposal"]["revision"]["revision"], 1)
                self.assertEqual(detail_result["work_orders"][0]["objective_id"], first_result["objective_id"])
                self.assertEqual(detail_result["work_orders"][0]["objective_status"], "COMPLETED")
                linked = detail_result["proposal"]["work_order_links"][0]
                self.assertEqual(linked["assignment_id"], assignment_id)
                execution_events = [event for event in detail_result["proposal"]["events"]
                    if event["event_type"] == "proposal.execution_updated"]
                self.assertEqual(execution_events[-1]["payload"]["status"], "completed")
                self.assertEqual(execution_events[-1]["payload"]["evidence"]["verification_decision"], "ACCEPTED")
                self.assertEqual(request("GET",
                    f"/api/v1/institutional-proposals/{proposal_id}?revision=0")[0], 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_stale_revision_and_unauthenticated_principal_are_rejected(self):
        from riverview_core.resident_execution.proposals import ProposalConflict
        record = self.ready_proposal()
        self.approve(record)
        revised = dict(self.content, title="Replacement revision")
        self.registry.revise(record["proposal"]["proposal_id"], 1, revised,
            actor_id="steward:authorized")
        with self.assertRaises(ProposalConflict):
            self.lifecycle.promote(record["proposal"]["proposal_id"], 1,
                actor_id="steward:authorized")
        with self.assertRaises(PermissionError):
            self.lifecycle.decide(record["proposal"]["proposal_id"], 2,
                decision="APPROVE", actor_id="resident:untrusted", reason="x",
                idempotency_key="bad", content_sha256="0" * 64,
                approved_purpose="test",
                authority_reference="account-auth-session:untrusted:steward")

    def test_comms5_recent_and_objective_status_use_current_durable_registries(self):
        from riverview_core.resident_execution.comms5_operations import Comms5Operations
        saved = self.registry.create_draft(self.content, created_by="steward:authorized",
            origin_kind="steward_authored", source_references=[],
            provenance={"source": "isolated-test"}, idempotency_key="comms5:recent:1")
        objective_id = "objective:" + uuid4().hex
        self.pipeline.submit_objective(objective_id, "Private bounded test request",
            ["Private acceptance criterion"], credential=self.tokens["steward:authorized"],
            scope_ref=self.scope)
        operations = Comms5Operations(self.registry, self.lifecycle, self.pipeline)
        recent = operations.execute("comms5_recent_steward_submissions", {},
            principal_id="steward:authorized")
        self.assertEqual({item["record_type"] for item in recent["items"]},
                         {"objective", "proposal"})
        self.assertIn(saved["proposal"]["proposal_id"],
                      {item["record_id"] for item in recent["items"]})
        detail = operations.execute("comms5_objective_status",
            {"objective_id": objective_id}, principal_id="steward:authorized")
        self.assertEqual(detail["objective"]["state"], "RECEIVED")
        self.assertEqual(detail["submission_authority"]["grant_id"],
                         "steward:authorized-objective.submit")
        self.assertEqual(detail["execution_intents"], [])
        serialized = json.dumps(detail)
        self.assertNotIn("Private bounded test request", serialized)
        self.assertNotIn("Private acceptance criterion", serialized)

    def test_comms5_queue_request_is_durable_idempotent_and_does_not_claim_dispatch(self):
        from riverview_core.resident_reasoning import PlanProposal, PlanStep
        from riverview_core.resident_execution.comms5_operations import Comms5Operations

        record = self.ready_proposal()
        proposal_id = record["proposal"]["proposal_id"]
        self.approve(record)
        promoted = self.lifecycle.promote(proposal_id, 1, actor_id="steward:authorized")
        objective = promoted["objective_id"]
        grounded = self.pipeline.get_objective(objective)
        plan = PlanProposal("One bounded Engineering step", (PlanStep(
            "report", "Write the approved bounded artifact",
            tuple(grounded["acceptance_criteria"])),), 0)
        self.pipeline.record_proposal(objective, plan)

        operations = Comms5Operations(self.registry, self.lifecycle, self.pipeline)
        args = {"objective_id": objective, "stage_id": "report",
            "authority_id": "steward:authorized-objective.submit",
            "idempotency_key": "comms5:queue:" + uuid4().hex,
            "explicit_steward_confirmation": True, "client_id": "isolated-test",
            "client_type": "test", "client_name": "Comms5 integration"}
        first = operations.execute("comms5_form_and_queue_work", args,
            principal_id="steward:authorized")
        second = operations.execute("comms5_form_and_queue_work", args,
            principal_id="steward:authorized")
        self.assertEqual(first["status"], "queued_for_cme")
        self.assertFalse(first["work_order_created"])
        self.assertFalse(first["dispatched"])
        self.assertEqual(second["status"], "already_queued_for_cme")
        events = [item for item in self.pipeline.objective_events(objective)
            if item["event_type"] == "work_order.dispatch_requested"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["stage_id"], "report")
        self.assertEqual(events[0]["payload"]["authority_id"],
                         "steward:authorized-objective.submit")
        self.assertIsNone(self.pipeline.get_objective(objective)["assignment_id"])

    def test_comms5_proposal_operations_use_durable_lifecycle_and_existing_objective_intake(self):
        from riverview_core.resident_execution.comms5_operations import Comms5Operations
        operations = Comms5Operations(self.registry, self.lifecycle, self.pipeline)
        base = {"client_id": "isolated", "client_type": "test", "client_name": "Comms5 fixture"}

        seed = operations.execute("comms5_submit_steward_seed", {
            **base, "seed_text": "A bounded proposal seed.", "idempotency_key": "comms5:seed:1"},
            principal_id="steward:authorized")
        self.assertEqual(seed["status"], "draft_saved")
        seed_status = operations.execute("comms5_seed_status", {"seed_id": seed["seed_id"]},
            principal_id="steward:authorized")
        self.assertEqual(seed_status["proposal"]["lifecycle_status"], "DRAFT")
        lineage = operations.execute("comms5_seed_lineage", {"seed_id": seed["seed_id"]},
            principal_id="steward:authorized")
        self.assertIn("proposal.created", {item["event_type"] for item in lineage["events"]})

        spec = operations.execute("comms5_store_specification", {
            **base, "content": "A bounded specification.", "summary": "Fixture",
            "idempotency_key": "comms5:spec:1",
            "formation_contract": {"allowed_paths": ["reports/summary.txt"]}},
            principal_id="steward:authorized")
        cancelled = operations.execute("comms5_cancel_draft", {
            **base, "seed_id": spec["seed_id"], "reason": "Fixture cancellation",
            "idempotency_key": "comms5:cancel:1", "explicit_steward_confirmation": True},
            principal_id="steward:authorized")
        self.assertEqual(cancelled["status"], "draft_cancelled")
        self.assertEqual(self.registry.get(spec["seed_id"])["proposal"]["lifecycle_status"], "ARCHIVED")

        replaced = operations.execute("comms5_submit_steward_seed", {
            **base, "seed_text": "An older bounded draft.", "idempotency_key": "comms5:old:1"},
            principal_id="steward:authorized")
        replacement = operations.execute("comms5_submit_steward_seed", {
            **base, "seed_text": "Its replacement draft.", "idempotency_key": "comms5:new:1"},
            principal_id="steward:authorized")
        superseded = operations.execute("comms5_supersede_seed", {
            **base, "seed_id": replaced["seed_id"], "replacement_seed_id": replacement["seed_id"],
            "reason": "Revision replaced", "idempotency_key": "comms5:supersede:1",
            "explicit_steward_confirmation": True}, principal_id="steward:authorized")
        self.assertEqual(superseded["status"], "superseded")
        self.assertEqual(self.registry.get(replaced["seed_id"])["proposal"]["lifecycle_status"], "SUPERSEDED")

        ready = self.ready_proposal(key="comms5:ready:1")
        promoted = operations.execute("comms5_confirm_and_promote_seed", {
            **base, "seed_id": ready["proposal"]["proposal_id"],
            "idempotency_key": "comms5:promote:1", "explicit_steward_confirmation": True},
            principal_id="steward:authorized")
        self.assertEqual(promoted["status"], "GROUNDED")
        self.assertTrue(promoted["executed"])
        objective = self.pipeline.get_objective(promoted["objective_id"])
        self.assertEqual(objective["status"], "GROUNDED")
        self.assertIsNone(objective["assignment_id"])
