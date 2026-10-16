# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_execution.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.16
# Purpose: Exercise objective-to-authorized-worker-to-independent-verification pipeline
# Execution Model: Isolated PostgreSQL schema, committed repository fixture, deterministic proposal
# Observability: Durable objective/assignment events, worker attempt, artifact, verifier decision
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL; Git; Psycopg 3
# Authority: Random isolated test schema and temporary directories only
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Initial end-to-end tests
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Add constrained worker-contract negative tests and optional sanitized evidence export
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Exercise dashboard intake and restart-resumed service completion
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-RETRY-TEST-FIX | Expire fixture lease without violating acquired/expiry invariant
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-VERIFIER-ISOLATION | Prove one failed verifier does not starve another objective
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-LOOP-TEST | Exercise repeated objectives through the continuous service loop
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-LOOP-TEST-FIX | Match scheduler schema and validated service polling bounds
# Changed: 2026-10-11 UTC | RV-M4.4-PROCESS-RESTART-EVIDENCE | Exercise separate execution processes across queued-work recovery
# Changed: 2026-10-11 UTC | RV-M4.4-SPAWNED-RESTART-TEST-FIX | Avoid sharing inherited libpq sockets across worker process restart
# Changed: 2026-10-11 UTC | RV-M4.4-SPAWN-CONTEXT-RESTART-FIX | Launch fresh importable service target with spawn context
# Changed: 2026-10-11 UTC | RV-M4.1-PERSISTENT-RUNTIME-INTEGRATION | Verify only complete grounded objectives enter resident context
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-FAIR-CYCLE | Prove waiting reasoning does not delay existing worker execution
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-FAIR-FIX | Advance queued work through the event processor before fairness assertion
# Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-REGROUND-001 | Verify successful evidence retry advances a waiting objective exactly once
# Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-CONTEXT-001 | Verify grounded objective context resolves resident knowledge contract
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Verify dependent step assignments wait for independent predecessor verification
# Changed: 2026-10-16 UTC | RV-GRACE-STRUCTURED-REVIEW-001 | Verify same-objective continuation is durable, scoped, and dispatched through CME
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Model-independent integration test of Grace objective execution."""

import hashlib
import json
import multiprocessing
import os
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from riverview_core.assignment_intake import AuthorizedAssignmentIntake
from riverview_core.institutional_authority import ExactGrantAuthorizer
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.postgres_migrations import apply_migrations
from riverview_core.resident_execution import (
    GraceExecutionPipeline, ObjectiveNotAuthorized, ObjectiveStateError,
)
from riverview_core.resident_reasoning import (
    PlanProposal, PlanStep, ReasoningResult, ReasoningStatus,
)
from riverview_core.worker_adapter import ContinuousWorker, PostgresWorkerAdapter
from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider
from riverview_core.worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider
from riverview_core.resident_execution.worker import BoundedLocalCodingWorker, CodingWorkOrder
from riverview_core.resident_execution.verifier import BoundedArtifactVerifier

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
CORE = Path(__file__).resolve().parents[1] / "src/riverview_core"
RESIDENT_FILES = (
    "docs/components/RESIDENT_REASONING.md",
    "docs/components/GRACE_OPERATIONAL_INTEGRATION_FLOW.md",
    "docs/components/INSTITUTIONAL_AUTHORITY.md",
    "src/riverview_core/resident_reasoning.py",
    "src/riverview_core/local_reasoning_provider.py",
    "src/riverview_core/worker_adapter/repository_knowledge.py",
    "docs/ROADMAP.md",
)
WORKER_FILES = (
    "docs/components/WORKER_ADAPTER.md",
    "src/riverview_core/worker_adapter/adapter.py",
    "src/riverview_core/worker_adapter/continuous.py",
    "src/riverview_core/worker_adapter/knowledge_provider_v1/contract.py",
    "src/riverview_core/worker_adapter/repository_knowledge.py",
)


def fixture_repository(root):
    for path in set(RESIDENT_FILES + WORKER_FILES):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(
            "# Verified fixture contract\n\n"
            "A bounded work order records its repository provenance, task criteria, "
            "assignment identity, and independent verification.\n\n"
            "Unrelated dashboard navigation and browser rendering notes.\n",
            encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "verified fixture"], check=True)
    return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


def persistent_service_process(stop_event, dsn, schema, authority_schema, scope,
                               repository, commit, artifact_root, worker_id,
                               worker_token, dispatch_token, verifier_id, verifier_token):
    """Construct a fresh process-local runtime using only durable DB state."""
    from riverview_core.assignment_intake import AuthorizedAssignmentIntake
    from riverview_core.institutional_authority import ExactGrantAuthorizer
    from riverview_core.postgres_ledger import PostgresLedger
    from riverview_core.resident_execution import GraceExecutionPipeline
    from riverview_core.resident_execution.service import GraceExecutionService
    from riverview_core.resident_execution.worker import BoundedLocalCodingWorker
    from riverview_core.worker_adapter import ContinuousWorker, PostgresWorkerAdapter
    from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider
    from riverview_core.worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider

    ledger = PostgresLedger(dsn, schema=schema)
    adapter = PostgresWorkerAdapter(dsn, schema=schema, authority_schema=authority_schema)
    authorizer = ExactGrantAuthorizer(authority_schema)
    knowledge = TaskRelevantRepositoryKnowledgeProvider(repository, commit)
    pipeline = GraceExecutionPipeline(ledger, authorizer,
        AuthorizedAssignmentIntake(ledger, authorizer), knowledge)
    worker = ContinuousWorker(adapter, worker_id, worker_token,
        knowledge=RepositoryKnowledgeProvider(repository, commit),
        action=BoundedLocalCodingWorker(pipeline, artifact_root),
        action_effect_class="retry_safe",
        action_capability="engineering.bounded-artifact.v1")
    service = GraceExecutionService(pipeline, adapter, worker,
        dispatch_credential=dispatch_token, authority_ref=scope,
        verifier_id=verifier_id, verifier_credential=verifier_token,
        artifact_root=artifact_root)
    try:
        service.run_forever(shutdown_requested=stop_event.is_set, poll_seconds=0.1)
    finally:
        adapter.close()
        ledger.close()


class CodingWorkOrderContractTests(unittest.TestCase):
    def test_worker_contract_rejects_unbounded_operations_and_timeout(self):
        common = dict(assignment_id="assignment:1", objective_id="objective:1",
                      repository_reference="repo://docs/contract.md",
                      repository_revision="a" * 40, task_scope="write a bounded artifact",
                      acceptance_criteria=("artifact exists",))
        self.assertEqual(CodingWorkOrder(**common).allowed_operations,
                         ("write_bounded_json_artifact",))
        with self.assertRaises(ValueError):
            CodingWorkOrder(**common, allowed_operations=("shell",))
        with self.assertRaises(ValueError):
            CodingWorkOrder(**common, timeout_seconds=91)
        with self.assertRaises(ValueError):
            CodingWorkOrder(**{**common, "repository_revision": "not-a-commit"})


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class GraceExecutionTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        apply_migrations(DSN, schema=self.schema)
        root = Path(__file__).resolve().parents[1] / "src/riverview_core"
        for component in ("assignment_scheduler", "worker_adapter",
                          "institutional_authority", "resident_execution"):
            apply_migrations(DSN, schema=self.schema,
                             migrations_dir=root / component / "migrations")
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.adapter = PostgresWorkerAdapter(DSN, schema=self.schema)
        self.authorizer = ExactGrantAuthorizer(self.schema)
        self.intake = AuthorizedAssignmentIntake(self.ledger, self.authorizer)
        self.scope = "work-order:grace-test"
        self.credentials = {}
        self.principals = {
            "steward": ("steward:test", secrets.token_urlsafe(36),
                        ("objective.submit", "assignment.create", "assignment.cancel")),
            "worker": ("worker:test", secrets.token_urlsafe(36),
                       ("worker.register", "assignment.execute")),
            "verifier": ("verifier:test", secrets.token_urlsafe(36),
                         ("worker.register", "assignment.verify")),
        }
        for key, (principal, credential, actions) in self.principals.items():
            self.credentials[key] = credential
            self.admin.execute(sql.SQL(
                "INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,%s)")
                .format(sql.Identifier(self.schema)),
                (principal, "steward" if key == "steward" else "resident"))
            self.admin.execute(sql.SQL("""INSERT INTO {}.principal_credentials
                (credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)""")
                .format(sql.Identifier(self.schema)),
                (uuid4(), principal, hashlib.sha256(credential.encode()).digest()))
            for action in actions:
                self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
                    (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                    VALUES (%s,%s,%s,%s,%s,'rv.policy:grace-execution-test.v1')""")
                    .format(sql.Identifier(self.schema)),
                    (f"{key}-{action}", principal, action, self.scope, principal))
        self.worker_id = "worker:" + uuid4().hex
        self.verifier_id = "verifier:" + uuid4().hex
        self.adapter.register_worker(self.worker_id, ["engineering.bounded-artifact.v1"],
                                     self.scope, credential=self.credentials["worker"])
        self.adapter.register_worker(self.verifier_id, ["assignment.verify.v1"],
                                     self.scope, credential=self.credentials["verifier"])
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.commit = fixture_repository(self.repo)
        self.knowledge = TaskRelevantRepositoryKnowledgeProvider(self.repo, self.commit)
        self.pipeline = GraceExecutionPipeline(self.ledger, self.authorizer,
                                                self.intake, self.knowledge)

    def tearDown(self):
        self.adapter.close()
        self.ledger.close()
        self.admin.execute("DROP SCHEMA IF EXISTS " + self.schema + " CASCADE")
        self.admin.close()
        self.temp.cleanup()

    def test_authorized_objective_executes_and_is_independently_verified(self):
        with self.assertRaises(ObjectiveNotAuthorized):
            self.pipeline.submit_objective(
                "objective:denied", "document retry contract", ["record source"],
                credential=secrets.token_urlsafe(36), scope_ref=self.scope)
        row = self.pipeline.submit_objective(
            "objective:grace-e2e", "document worker retry contract",
            ["artifact contains the task and verified repository provenance"],
            credential=self.credentials["steward"], scope_ref=self.scope)
        self.assertEqual(row["status"], "RECEIVED")
        with self.assertRaises(ObjectiveStateError):
            self.pipeline.record_proposal(
                row["objective_id"],
                PlanProposal("premature", (PlanStep("step", "write artifact", ("contains evidence",)),), 0))
        row = self.pipeline.ground_objective(row["objective_id"])
        self.assertEqual(row["status"], "GROUNDED")
        self.assertEqual(row["source_revision"], self.commit)
        self.assertTrue(row["evidence"]["source_references"])
        self.assertEqual(self.pipeline.grounded_objectives(scope_ref=self.scope),
                         [{"objective_id": row["objective_id"], "revision": row["revision"]}])
        context = self.pipeline.read_reasoning_context(row["objective_id"])
        self.assertEqual(context["id"], row["objective_id"])
        self.assertEqual(context["revision"], str(row["revision"]))
        self.assertEqual(context["contract_ref"], self.pipeline.CONTRACT_REF)
        self.assertEqual(context["verified_evidence"]["status"], "VERIFIED")
        resident_grounding = self.knowledge.ground_assignment(context)
        resident_regrounding = self.knowledge.reground_assignment(
            context, "persistent_resident_cycle")
        self.assertEqual(resident_grounding.status.value, "VERIFIED")
        self.assertTrue(resident_grounding.retrieval_complete)
        self.assertEqual(resident_regrounding.status.value, "VERIFIED")
        self.assertTrue(resident_regrounding.retrieval_complete)
        proposal = PlanProposal("Document worker retry contract", (
            PlanStep("document", "Create a bounded retry-contract work product",
                     ("artifact contains the task and verified repository provenance",)),), 0)
        self.pipeline.record_proposal(row["objective_id"], proposal)
        with self.assertRaises(ObjectiveNotAuthorized):
            self.pipeline.authorize_and_dispatch(
                row["objective_id"], "assignment:denied", credential=secrets.token_urlsafe(36),
                authority_ref=self.scope, idempotency_key="grace-denied-assignment")
        assignment_id = "assignment:" + uuid4().hex
        assignment = self.pipeline.authorize_and_dispatch(
            row["objective_id"], assignment_id, credential=self.credentials["steward"],
            authority_ref=self.scope, idempotency_key="grace-create-" + assignment_id)
        self.assertEqual(assignment["state"], "queued")
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
                               "grace-ready-" + assignment_id, actor_id="event-processor")
        worker_knowledge = RepositoryKnowledgeProvider(self.repo, self.commit)
        action = BoundedLocalCodingWorker(self.pipeline, self.root / "artifacts")
        worker = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
                                  knowledge=worker_knowledge, action=action,
                                  action_effect_class="retry_safe",
                                  action_capability="engineering.bounded-artifact.v1")
        outcome = worker.run_once()
        self.assertEqual(outcome["status"], "AWAITING_VERIFICATION")
        attempt_id = outcome["attempt_id"]
        with self.adapter.ledger.db.cursor() as cur:
            self.adapter.ledger._set_search_path(cur)
            cur.execute("SELECT status FROM worker_attempts WHERE attempt_id=%s", (attempt_id,))
            self.assertEqual(cur.fetchone()["status"], "succeeded")
        with self.assertRaises(ObjectiveStateError):
            self.pipeline.record_verified_completion(row["objective_id"], assignment_id)
        decision = self.adapter.verify_attempt(
            assignment_id, attempt_id, self.verifier_id, self.credentials["verifier"],
            BoundedArtifactVerifier(self.root / "artifacts"),
            idempotency_key="grace-verify-" + assignment_id)
        self.assertEqual(decision.status.value, "ACCEPTED", dict(decision.criteria))
        result = self.pipeline.record_verified_completion(row["objective_id"], assignment_id)
        self.assertEqual(result["status"], "COMPLETED")
        product = next((self.root / "artifacts").glob("grace-work-*.json"))
        self.assertTrue(product.is_file())
        self.assertGreater(product.stat().st_size, 0)
        evidence_dir = os.environ.get("RIVERVIEW_TEST_EVIDENCE_DIR")
        if evidence_dir:
            evidence_root = Path(evidence_dir)
            artifact_dir = evidence_root / "artifacts"
            artifact_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            preserved = artifact_dir / "bounded-work-product.json"
            shutil.copyfile(product, preserved)
            os.chmod(preserved, 0o600)
            report = {
                "evidence_schema": "rv.grace.execution-checkout.v1",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "component_id": "RESIDENT-ORCHESTRATION",
                "source_commit": subprocess.run(
                    ["git", "rev-parse", "HEAD"], check=True,
                    capture_output=True, text=True).stdout.strip(),
                "test_schema": self.schema,
                "postgresql_version": self.admin.execute("SELECT version()").fetchone()[0].split(",")[0],
                "objective_id": row["objective_id"],
                "objective_status": result["status"],
                "assignment_id": assignment_id,
                "assignment_status": self.ledger.get(assignment_id)["state"],
                "attempt_id": attempt_id,
                "verifier_status": decision.status.value,
                "verifier_revision": decision.verifier_revision,
                "verifier_criteria": dict(decision.criteria),
                "objective_event_types": [event["event_type"] for event in
                                          self.pipeline.objective_events(row["objective_id"])],
                "artifact_path": "artifacts/bounded-work-product.json",
                "artifact_sha256": hashlib.sha256(preserved.read_bytes()).hexdigest(),
                "artifact_size_bytes": preserved.stat().st_size,
                "repository_revision": result["source_revision"],
                "repository_sha256": result["source_sha256"],
                "mode": "isolated model-independent deterministic integration test",
                "shared_services_modified": False,
            }
            (evidence_root / "integration-result.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual([event["event_type"] for event in
                          self.pipeline.objective_events(row["objective_id"])],
                         ["objective.received", "objective.grounded",
                          "work_order.proposed", "work_order.dispatched",
                          "objective.completed"])

    def test_multistep_dispatch_waits_for_prior_step_verification(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id = "objective:dependent-steps"
        self.pipeline.submit_objective(objective_id, "create two verified work products",
            ["first step artifact is accepted", "second step artifact is accepted"],
            credential=self.credentials["steward"], scope_ref=self.scope,
            origin={"conversation_id": str(uuid4()), "source_sequence": 1})
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal(
            "Create dependent work products", (
                PlanStep("prepare", "Prepare the first bounded work product",
                         ("first step artifact is accepted",)),
                PlanStep("followup", "Prepare the dependent bounded work product",
                         ("second step artifact is accepted",), depends_on=("prepare",))), 0))
        worker = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=BoundedLocalCodingWorker(self.pipeline, self.root / "step-artifacts"),
            action_effect_class="retry_safe", action_capability="engineering.bounded-artifact.v1")
        service = GraceExecutionService(self.pipeline, self.adapter, worker,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=self.root / "step-artifacts")

        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        first = self.pipeline.get_objective(objective_id)["assignment_id"]
        self.assertIsNone(self.pipeline.dispatchable_step(objective_id))
        self.ledger.transition(first, "ready", "event_processor_ready", "ready:" + first,
                               actor_id="event-processor")
        result = worker.run_once(assignment_id=first)
        self.assertEqual(result["status"], "AWAITING_VERIFICATION")
        verification = service.verify_one(first)
        self.assertTrue(verification)
        self.assertEqual(self.pipeline.record_verified_completion(objective_id, first)["status"],
                         "WORK_ORDER_CREATED")

        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        second = self.pipeline.get_objective(objective_id)["assignment_id"]
        self.assertNotEqual(first, second)
        assignment = self.ledger.get(second)
        self.assertEqual(assignment["workflow_step"], "followup")
        self.ledger.transition(second, "ready", "event_processor_ready", "ready:" + second,
                               actor_id="event-processor")
        result = worker.run_once(assignment_id=second)
        self.assertEqual(result["status"], "AWAITING_VERIFICATION")
        self.assertTrue(service.verify_one(second))
        self.assertEqual(self.pipeline.record_verified_completion(objective_id, second)["status"],
                         "COMPLETED")
        pending = self.pipeline.pending_conversation_results()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["completion_cycle"], 2)
        self.pipeline.record_conversation_result_published(objective_id, {
            "request_id": str(uuid4()), "provider_id": "provider:test",
            "served_model": "model:test", "implementation_id": "implementation:test",
            "completion_cycle": "2"})
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT step_id,status,assignment_id FROM grace_objective_steps
                WHERE objective_id=%s ORDER BY step_order""", (objective_id,))
            rows = cur.fetchall()
        self.assertEqual([row["step_id"] for row in rows], ["prepare", "followup"])
        self.assertEqual([row["status"] for row in rows], ["verified", "verified"])
        self.assertNotEqual(rows[0]["assignment_id"], rows[1]["assignment_id"])

        continued = self.pipeline.propose_continuation(objective_id, second,
            PlanStep("supplemental", "Supplement the accepted evidence",
                     ("first step artifact is accepted",), depends_on=("followup",)))
        self.assertEqual(continued["objective_id"], objective_id)
        self.assertEqual(continued["status"], "WORK_ORDER_CREATED")
        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        third = self.pipeline.get_objective(objective_id)["assignment_id"]
        self.assertNotEqual(third, second)
        self.assertEqual(self.ledger.get(third)["objective_ref"], objective_id)
        self.ledger.transition(third, "ready", "event_processor_ready", "ready:" + third,
                               actor_id="event-processor")
        result = worker.run_once(assignment_id=third)
        self.assertEqual(result["status"], "AWAITING_VERIFICATION")
        self.assertTrue(service.verify_one(third))
        self.assertEqual(self.pipeline.record_verified_completion(objective_id, third)["status"],
                         "COMPLETED")
        pending = self.pipeline.pending_conversation_results()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["completion_cycle"], 3)
        completions = [event for event in self.pipeline.objective_events(objective_id)
                       if event["event_type"] == "objective.completed"]
        self.assertEqual([event["payload"]["completion_cycle"] for event in completions], [2, 3])

    def test_missing_or_oversized_evidence_fails_closed(self):
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        class FixedKnowledge:
            def __init__(self, result):
                self.result = result
            def ground_assignment(self, assignment):
                return self.result

        no_evidence = GraceExecutionPipeline(
            self.ledger, self.authorizer, self.intake,
            FixedKnowledge(KnowledgeResult(KnowledgeStatus.NO_MATCH, retrieval_complete=True)))
        no_evidence.submit_objective("objective:no-evidence", "write a document",
                                     ["include evidence"], credential=self.credentials["steward"],
                                     scope_ref=self.scope)
        with self.assertRaises(ObjectiveStateError):
            no_evidence.ground_objective("objective:no-evidence")
        self.assertEqual(no_evidence.get_objective("objective:no-evidence")["status"],
                         "WAITING_FOR_EVIDENCE")

        oversized = GraceExecutionPipeline(
            self.ledger, self.authorizer, self.intake,
            FixedKnowledge(KnowledgeResult(
                KnowledgeStatus.VERIFIED, value={"content": "x" * 9000},
                source_references=("repo://docs/example.md",), source_revision=self.commit,
                source_sha256="a" * 64, retrieval_complete=True)))
        oversized.submit_objective("objective:oversized", "write a document",
                                   ["include evidence"], credential=self.credentials["steward"],
                                   scope_ref=self.scope)
        with self.assertRaisesRegex(ObjectiveStateError, "exceeds context"):
            oversized.ground_objective("objective:oversized")
        oversized_record = oversized.get_objective("objective:oversized")
        self.assertEqual(oversized_record["status"], "WAITING_FOR_EVIDENCE")
        self.assertEqual(oversized_record["evidence"]["error_code"], "EVIDENCE_TOO_LARGE")

    def test_verified_grounding_retry_advances_waiting_objective_once(self):
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        class MutableKnowledge:
            def __init__(inner_self):
                inner_self.result = KnowledgeResult(
                    KnowledgeStatus.INCOMPLETE,
                    source_references=("repo://docs/verified.md",),
                    source_revision=self.commit,
                    source_sha256="a" * 64,
                    retrieval_complete=False)

            def ground_assignment(inner_self, _assignment):
                return inner_self.result

        knowledge = MutableKnowledge()
        self.pipeline.knowledge = knowledge
        criteria = ["preserve the original acceptance criteria"]
        self.pipeline.submit_objective(
            "objective:retry-grounding", "document the verified retry behavior", criteria,
            credential=self.credentials["steward"], scope_ref=self.scope)

        with self.assertRaises(ObjectiveStateError):
            self.pipeline.ground_objective("objective:retry-grounding")
        waiting = self.pipeline.get_objective("objective:retry-grounding")
        self.assertEqual(waiting["status"], "WAITING_FOR_EVIDENCE")
        self.assertEqual(waiting["revision"], 2)

        knowledge.result = KnowledgeResult(
            KnowledgeStatus.VERIFIED,
            value={"verified_fact": "complete bounded evidence"},
            source_references=("repo://docs/verified.md",),
            source_revision=self.commit,
            source_sha256="b" * 64,
            retrieval_complete=True)
        grounded = self.pipeline.ground_objective("objective:retry-grounding")

        self.assertEqual(grounded["status"], "GROUNDED")
        self.assertEqual(grounded["revision"], 3)
        self.assertEqual(grounded["acceptance_criteria"], criteria)
        self.assertEqual(grounded["source_revision"], self.commit)
        self.assertEqual(grounded["evidence"]["status"], "VERIFIED")
        self.assertEqual([event["event_type"] for event in
                          self.pipeline.objective_events("objective:retry-grounding")],
                         ["objective.received", "objective.waiting_for_evidence",
                          "objective.grounded"])
        self.assertEqual(self.pipeline.grounded_objectives(scope_ref=self.scope),
                         [{"objective_id": "objective:retry-grounding", "revision": 3}])

    def test_worker_failure_and_incomplete_verification_do_not_complete_objective(self):
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        # Intake, grounding, proposal, and authorization use the same production path.
        objective_id = "objective:worker-failure"
        self.pipeline.submit_objective(objective_id, "document worker provenance verification",
                                       ["record verified repository provenance"],
                                       credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal("Record provenance", (
            PlanStep("provenance", "Write bounded work evidence",
                     ("record verified repository provenance",)),), 0))
        assignment_id = "assignment:" + uuid4().hex
        self.pipeline.authorize_and_dispatch(
            objective_id, assignment_id, credential=self.credentials["steward"],
            authority_ref=self.scope, idempotency_key="grace-create-" + assignment_id)
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
                               "grace-ready-" + assignment_id, actor_id="event-processor")
        class FailingAction:
            def __call__(self, assignment, grounded):
                raise OSError("fixture worker failure")
        worker = ContinuousWorker(
            self.adapter, self.worker_id, self.credentials["worker"],
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=FailingAction(), action_effect_class="retry_safe",
            action_capability="engineering.bounded-artifact.v1")
        outcome = worker.run_once()
        self.assertEqual(outcome["status"], "FAILED")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "blocked")
        with self.assertRaises(ObjectiveStateError):
            self.pipeline.record_verified_completion(objective_id, assignment_id)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "WORK_ORDER_CREATED")

    def test_exactly_authorized_pre_execution_cancellation_is_durable(self):
        objective_id = "objective:cancel"
        self.pipeline.submit_objective(objective_id, "document worker provenance verification",
                                       ["record verified repository provenance"],
                                       credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal("Cancel test", (
            PlanStep("cancel", "Write bounded work evidence",
                     ("record verified repository provenance",)),), 0))
        assignment_id = "assignment:" + uuid4().hex
        self.pipeline.authorize_and_dispatch(
            objective_id, assignment_id, credential=self.credentials["steward"],
            authority_ref=self.scope, idempotency_key="grace-create-" + assignment_id)
        with self.assertRaises(ObjectiveNotAuthorized):
            self.pipeline.cancel_work_order(
                objective_id, credential=secrets.token_urlsafe(36), authority_ref=self.scope)
        cancelled = self.pipeline.cancel_work_order(
            objective_id, credential=self.credentials["steward"], authority_ref=self.scope)
        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "cancelled")

    def test_dashboard_submission_persistent_restart_worker_verification_and_projection(self):
        import psycopg
        from http.client import HTTPConnection
        from psycopg import sql
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.status_dashboard.projection import DashboardProjection
        from riverview_core.status_dashboard.server import DashboardHTTPServer

        # Give the execution resident its own narrow assignment.create credential.
        principal, dispatch_credential = "resident:grace-dispatch-test", secrets.token_urlsafe(36)
        self.admin.execute(sql.SQL(
            "INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,'resident')")
            .format(sql.Identifier(self.schema)), (principal,))
        self.admin.execute(sql.SQL("""INSERT INTO {}.principal_credentials
            (credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)""")
            .format(sql.Identifier(self.schema)),
            (uuid4(), principal, hashlib.sha256(dispatch_credential.encode()).digest()))
        self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES ('grace-dispatch-test',%s,'assignment.create',%s,%s,
                    'rv.policy:grace-execution-test.v1')""")
            .format(sql.Identifier(self.schema)), (principal, self.scope, "steward:test"))

        dashboard_token = "D" * 43
        token_path = self.root / "dashboard-token"
        token_path.write_text(dashboard_token, encoding="ascii")
        token_path.chmod(0o600)
        projection = DashboardProjection(DSN, schema=self.schema, source_commit=self.commit,
                                         deployment_id="isolated-test")
        server = None
        thread = None
        for port in range(8799, 8699, -1):
            try:
                server = DashboardHTTPServer("127.0.0.1", port, token_path, projection,
                    Path(__file__).resolve().parents[1] / "src/riverview_core/status_dashboard/static",
                    objective_pipeline=self.pipeline)
                break
            except OSError:
                continue
        self.assertIsNotNone(server)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def request(method, path, payload=None, *, authority=None):
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            headers = {"Authorization": "Bearer " + dashboard_token}
            if payload is not None:
                headers["Content-Type"] = "application/json"
                headers["Content-Length"] = str(len(payload))
            if authority:
                headers["X-Riverview-Authority"] = authority
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            result = (response.status, json.loads(response.read() or b"{}"))
            conn.close()
            return result

        objective_id = "objective:persistent-service"
        body = json.dumps({"objective_id": objective_id,
            "request": "Record verified repository provenance in the bounded work product",
            "acceptance_criteria": ["artifact records verified repository provenance"],
            "scope_ref": self.scope}, separators=(",", ":")).encode()
        try:
            denied_status, _ = request("POST", "/api/v1/objectives", body,
                                       authority=secrets.token_urlsafe(36))
            self.assertEqual(denied_status, 403)
            self.assertIsNone(self.pipeline.get_objective(objective_id))
            submit_status, submitted = request("POST", "/api/v1/objectives", body,
                                               authority=self.credentials["steward"])
            self.assertEqual(submit_status, 202)
            self.assertEqual(submitted["status"], "GROUNDED")
            proposal = {"summary": "Record verified repository provenance",
                "steps": [{"step_id": "record", "objective": "Write one bounded work product",
                    "acceptance_criteria": ["artifact records verified repository provenance"],
                    "depends_on": []}], "tokens_used": 0}
            proposal_payload = json.dumps(proposal, separators=(",", ":")).encode()
            denied_proposal, _ = request("POST", f"/api/v1/objectives/{objective_id}/proposal",
                                         proposal_payload, authority=secrets.token_urlsafe(36))
            self.assertEqual(denied_proposal, 403)
            status, proposed = request("POST", f"/api/v1/objectives/{objective_id}/proposal",
                                       proposal_payload,
                                       authority=self.credentials["steward"])
            self.assertEqual(status, 202)
            self.assertEqual(proposed["status"], "PROPOSED")

            artifact_root = self.root / "service-artifacts"
            def new_runtime():
                engine = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
                    knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
                    action=BoundedLocalCodingWorker(self.pipeline, artifact_root),
                    action_effect_class="retry_safe",
                    action_capability="engineering.bounded-artifact.v1")
                return GraceExecutionService(self.pipeline, self.adapter, engine,
                    dispatch_credential=dispatch_credential, authority_ref=self.scope,
                    verifier_id=self.verifier_id,
                    verifier_credential=self.credentials["verifier"],
                    artifact_root=artifact_root)

            first_process = new_runtime()
            self.assertEqual(first_process.dispatch_proposed(), 1)
            assignment_id = self.pipeline.get_objective(objective_id)["assignment_id"]
            self.assertIsNotNone(assignment_id)
            # Existing event processor owns queued -> ready. This call models its
            # durable PostgreSQL event transition; Grace never mutates scheduler state.
            self.ledger.transition(assignment_id, "ready", "event_processor_ready",
                "grace-persistent-ready:" + assignment_id, actor_id="event-processor")

            # Discard runtime objects and reconstruct from PostgreSQL, simulating restart.
            resumed = new_runtime()
            result = resumed.run_once()
            self.assertEqual(result["worker"]["status"], "AWAITING_VERIFICATION")
            self.assertTrue(result["verified"])
            self.assertEqual(result["completed"], 1)
            self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "COMPLETED")
            self.assertEqual(resumed.dispatch_proposed(), 0)
            with self.adapter.ledger.db.cursor() as cur:
                self.adapter.ledger._set_search_path(cur)
                cur.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s",
                            (assignment_id,))
                self.assertEqual(cur.fetchone()["n"], 1)
                cur.execute("SELECT count(*) AS n FROM verification_records WHERE assignment_id=%s",
                            (assignment_id,))
                self.assertEqual(cur.fetchone()["n"], 1)
            projected_status, projected = request("GET", f"/api/v1/objectives/{objective_id}")
            self.assertEqual(projected_status, 200)
            self.assertEqual(projected["status"], "COMPLETED")
            self.assertEqual(projected["assignment_state"], "completed")
            self.assertEqual(projected["verification"]["decision"], "ACCEPTED")
            self.assertTrue(projected["artifact"]["sha256"])
            status_projection, details = request("GET", "/api/v1/status")
            self.assertEqual(status_projection, 200)
            self.assertEqual(details["grace_execution"]["status"], "healthy")
        finally:
            if server:
                server.shutdown()
                server.server_close()
            if thread:
                thread.join(timeout=2)

    def test_persistent_service_worker_recovery_retry_ceiling_is_durable(self):
        from riverview_core.worker_adapter.recovery import PostgresRecoveryCoordinator
        assignment_id = "assignment:grace-retry-limit"
        self.ledger.create(assignment_id, "engineering", "grace-retry-limit-create",
            authority_ref=self.scope, objective_ref="objective:retry-limit",
            contract_ref="repo://riverview/worker-adapter-contract.v1",
            workflow_id="grace.objective-work-order.v1", workflow_step="test",
            actor_id="steward:test", correlation_id="objective:retry-limit")
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
            "grace-retry-limit-ready", actor_id="event-processor")
        claim = self.adapter.claim_next(self.worker_id, self.credentials["worker"],
            capability="engineering.bounded-artifact.v1")
        self.assertIsNotNone(claim)
        generation = claim["lease"]["generation"]
        self.adapter.start_assignment(assignment_id, self.worker_id,
            self.credentials["worker"], generation,
            capability="engineering.bounded-artifact.v1")
        self.adapter.begin_execution_intent(assignment_id, self.worker_id,
            self.credentials["worker"], generation, "grace-retry-limit-intent",
            effect_class="retry_safe", capability="engineering.bounded-artifact.v1")
        with self.adapter.ledger.db.transaction(), self.adapter.ledger.db.cursor() as cur:
            self.adapter.ledger._set_search_path(cur)
            cur.execute("UPDATE assignment_leases SET acquired_at=clock_timestamp()-interval '2 minutes', "
                        "expires_at=clock_timestamp()-interval '1 minute' "
                        "WHERE assignment_id=%s", (assignment_id,))
        recovery = PostgresRecoveryCoordinator(DSN, schema=self.schema, max_retries=0)
        try:
            outcomes = recovery.reconcile_expired()
        finally:
            recovery.close()
        self.assertEqual(outcomes[0]["decision"], "retry_exhausted")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "blocked")
        with self.adapter.ledger.db.cursor() as cur:
            self.adapter.ledger._set_search_path(cur)
            cur.execute("SELECT decision,resulting_state FROM worker_recovery_records "
                        "WHERE assignment_id=%s", (assignment_id,))
            record = cur.fetchone()
        self.assertEqual(record, {"decision": "retry_exhausted", "resulting_state": "blocked"})

    def test_failed_verification_attempt_does_not_block_next_candidate(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objectives = []
        for suffix in ("verify-isolation-a", "verify-isolation-b"):
            objective_id = "objective:" + suffix
            self.pipeline.submit_objective(objective_id,
                "record independently checked repository provenance",
                ["artifact includes the requested work and provenance"],
                credential=self.credentials["steward"], scope_ref=self.scope)
            self.pipeline.ground_objective(objective_id)
            self.pipeline.record_proposal(objective_id, PlanProposal("Verify bounded artifact", (
                PlanStep("artifact", "Create a bounded work product",
                         ("artifact includes the requested work and provenance",)),), 0))
            objectives.append(objective_id)

        failing_id = {"value": None}
        delegate = BoundedArtifactVerifier(self.root / "isolation-artifacts")
        class IsolatedVerifier:
            def verify(self, assignment, attempt, result):
                if failing_id["value"] is None:
                    failing_id["value"] = assignment["id"]
                    raise RuntimeError("isolated verifier fixture failure")
                if assignment["id"] == failing_id["value"]:
                    raise RuntimeError("isolated verifier fixture failure")
                return delegate.verify(assignment, attempt, result)

        artifact_root = self.root / "isolation-artifacts"
        def new_service():
            engine = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
                knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
                action=BoundedLocalCodingWorker(self.pipeline, artifact_root),
                action_effect_class="retry_safe",
                action_capability="engineering.bounded-artifact.v1")
            return GraceExecutionService(self.pipeline, self.adapter, engine,
                dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
                verifier_id=self.verifier_id,
                verifier_credential=self.credentials["verifier"],
                artifact_root=artifact_root, verifier=IsolatedVerifier())

        service = new_service()
        self.assertEqual(service.dispatch_proposed(), 2)
        assignments = [self.pipeline.get_objective(objective_id)["assignment_id"]
                       for objective_id in objectives]
        for assignment_id in assignments:
            self.ledger.transition(assignment_id, "ready", "event_processor_ready",
                "verify-isolation-ready:" + assignment_id, actor_id="event-processor")
        first = service.run_once()
        self.assertEqual(first["worker"]["status"], "AWAITING_VERIFICATION")
        self.assertFalse(first["verified"])
        second = service.run_once()
        self.assertEqual(second["worker"]["status"], "AWAITING_VERIFICATION")
        self.assertTrue(second["verified"])
        self.assertNotEqual(failing_id["value"], None)
        states = {assignment_id: self.ledger.get(assignment_id)["state"]
                  for assignment_id in assignments}
        self.assertEqual(states[failing_id["value"]], "awaiting_verification")
        completed = [assignment_id for assignment_id,state in states.items()
                     if state == "completed"]
        self.assertEqual(len(completed), 1)
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT attempt_id FROM worker_attempts WHERE assignment_id=%s",
                        (failing_id["value"],))
            failed_attempt = str(cur.fetchone()["attempt_id"])
            cur.execute("SELECT count(*) AS n FROM grace_objective_events "
                "WHERE event_type='execution.verification_failed' AND payload->>'attempt_id'=%s",
                (failed_attempt,))
            self.assertEqual(cur.fetchone()["n"], 2)

    def test_continuous_service_processes_repeated_objectives_without_run_once_calls(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_ids = ("objective:continuous-a", "objective:continuous-b")
        for objective_id in objective_ids:
            self.pipeline.submit_objective(objective_id,
                "record a repeatable verified repository work product",
                ["artifact records the requested task and source provenance"],
                credential=self.credentials["steward"], scope_ref=self.scope)
            self.pipeline.ground_objective(objective_id)
            self.pipeline.record_proposal(objective_id, PlanProposal("Create work product", (
                PlanStep("artifact", "Write the bounded engineering work product",
                    ("artifact records the requested task and source provenance",)),), 0))
        artifact_root = self.root / "continuous-artifacts"
        engine = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=BoundedLocalCodingWorker(self.pipeline, artifact_root),
            action_effect_class="retry_safe",
            action_capability="engineering.bounded-artifact.v1")
        service = GraceExecutionService(self.pipeline, self.adapter, engine,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=artifact_root)
        scheduler_ledger = PostgresLedger(DSN, schema=self.schema)
        stop = threading.Event()

        def scheduler_loop():
            while not stop.is_set():
                with scheduler_ledger.db.cursor() as cur:
                    scheduler_ledger._set_search_path(cur)
                    cur.execute("SELECT id FROM assignments WHERE state='queued' "
                        "AND objective_ref = ANY(%s) ORDER BY updated_at,id LIMIT 10",
                        (list(objective_ids),))
                    queued = [row["id"] for row in cur.fetchall()]
                for assignment_id in queued:
                    try:
                        scheduler_ledger.transition(assignment_id, "ready", "event_processor_ready",
                            "continuous-test-ready:" + assignment_id, actor_id="event-processor")
                    except Exception:
                        continue
                stop.wait(0.02)

        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        service_thread = threading.Thread(target=service.run_forever,
            kwargs={"shutdown_requested": stop.is_set, "poll_seconds": 0.1}, daemon=True)
        scheduler_thread.start()
        service_thread.start()
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                statuses = [self.pipeline.get_objective(item)["status"] for item in objective_ids]
                if statuses == ["COMPLETED", "COMPLETED"]:
                    break
                time.sleep(0.05)
            self.assertEqual([self.pipeline.get_objective(item)["status"] for item in objective_ids],
                             ["COMPLETED", "COMPLETED"])
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT count(*) AS n FROM worker_attempts wa JOIN assignments a "
                    "ON a.id=wa.assignment_id WHERE a.objective_ref = ANY(%s)", (list(objective_ids),))
                self.assertEqual(cur.fetchone()["n"], 2)
                cur.execute("SELECT count(*) AS n FROM verification_records vr JOIN assignments a "
                    "ON a.id=vr.assignment_id WHERE a.objective_ref = ANY(%s) AND vr.decision='ACCEPTED'",
                    (list(objective_ids),))
                self.assertEqual(cur.fetchone()["n"], 2)
        finally:
            stop.set()
            scheduler_thread.join(timeout=2)
            service_thread.join(timeout=2)
            scheduler_ledger.close()

    def test_waiting_resident_reasoning_does_not_block_existing_cme_work(self):
        from riverview_core.resident_execution.service import GraceExecutionService

        for objective_id in ("objective:reasoning-wait-a", "objective:reasoning-wait-b"):
            self.pipeline.submit_objective(
                objective_id, "document verified worker provenance",
                ["retain source provenance"], credential=self.credentials["steward"],
                scope_ref=self.scope)
            self.pipeline.ground_objective(objective_id)

        execution_id = "objective:fair-cycle-execution"
        criteria = ["artifact contains the requested task and verified repository provenance"]
        self.pipeline.submit_objective(
            execution_id, "record a bounded engineering result", criteria,
            credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(execution_id)
        self.pipeline.record_proposal(execution_id, PlanProposal(
            "Create bounded engineering result", (PlanStep(
                "artifact", "Write the bounded engineering work product", tuple(criteria)),), 0))

        artifact_root = self.root / "fair-cycle-artifacts"
        engine = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=BoundedLocalCodingWorker(self.pipeline, artifact_root),
            action_effect_class="retry_safe",
            action_capability="engineering.bounded-artifact.v1")

        class WaitingResident:
            office_id = "office:grace-test"
            providers = {"provider.test": object()}

            def __init__(self):
                self.calls = []

            def propose(self, objective_id, **_kwargs):
                self.calls.append(objective_id)
                return ReasoningResult(ReasoningStatus.WAITING_FOR_EVIDENCE,
                                       "request:test", "GROUNDING_UNAVAILABLE")

        resident = WaitingResident()
        service = GraceExecutionService(self.pipeline, self.adapter, engine,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=artifact_root, resident_reasoner=resident)
        self.assertEqual(service.dispatch_proposed(), 1)
        assignment_id = self.pipeline.get_objective(execution_id)["assignment_id"]
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
            "fair-cycle-ready:" + assignment_id, actor_id="event-processor")
        result = service.run_once()

        self.assertEqual(resident.calls, ["objective:reasoning-wait-a"])
        self.assertEqual(result["worker"]["status"], "AWAITING_VERIFICATION")
        self.assertTrue(result["verified"])
        self.assertEqual(self.pipeline.get_objective(execution_id)["status"], "COMPLETED")
        self.assertEqual(self.pipeline.get_objective("objective:reasoning-wait-b")["status"], "GROUNDED")

    def test_separate_service_process_restarts_and_resumes_durable_queued_work(self):
        import psycopg
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id = "objective:process-restart-resume"
        self.pipeline.submit_objective(objective_id,
            "create a provenance-bound bounded work product",
            ["artifact includes its source revision and request"],
            credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal("Create work product", (
            PlanStep("artifact", "Write the bounded work product",
                ("artifact includes its source revision and request",)),), 0))
        artifact_root = self.root / "process-restart-artifacts"
        context = multiprocessing.get_context("spawn")
        process_args = (
            DSN, self.schema, self.schema, self.scope, str(self.repo), self.commit,
            str(artifact_root), self.worker_id, self.credentials["worker"],
            self.credentials["steward"], self.verifier_id, self.credentials["verifier"],
        )

        first_stop = context.Event()
        first_process = context.Process(target=persistent_service_process,
                                        args=(first_stop, *process_args))
        first_process.start()
        try:
            deadline = time.monotonic() + 8
            objective = None
            while time.monotonic() < deadline:
                objective = self.pipeline.get_objective(objective_id)
                if objective["status"] == "WORK_ORDER_CREATED":
                    break
                time.sleep(0.05)
            self.assertEqual(objective["status"], "WORK_ORDER_CREATED")
            assignment_id = objective["assignment_id"]
            self.assertEqual(self.ledger.get(assignment_id)["state"], "queued")
        finally:
            first_stop.set()
            first_process.join(timeout=5)
            if first_process.is_alive():
                first_process.terminate()
                first_process.join(timeout=2)
        self.assertEqual(first_process.exitcode, 0)

        scheduler_ledger = PostgresLedger(DSN, schema=self.schema)
        scheduler_stop = threading.Event()
        def promote_queue():
            while not scheduler_stop.is_set():
                queued = [row["id"] for row in scheduler_ledger.db.execute(
                    "SELECT id FROM assignments WHERE state='queued' AND id=%s",
                    (assignment_id,)).fetchall()]
                for pending in queued:
                    try:
                        scheduler_ledger.transition(pending, "ready", "event_processor_ready",
                            "process-restart-ready:" + pending, actor_id="event-processor")
                    except Exception:
                        continue
                scheduler_stop.wait(0.02)

        scheduler_thread = threading.Thread(target=promote_queue, daemon=True)
        second_stop = context.Event()
        second_process = context.Process(target=persistent_service_process,
                                         args=(second_stop, *process_args))
        scheduler_thread.start()
        second_process.start()
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if self.pipeline.get_objective(objective_id)["status"] == "COMPLETED":
                    break
                time.sleep(0.05)
            self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "COMPLETED")
        finally:
            second_stop.set()
            scheduler_stop.set()
            second_process.join(timeout=5)
            scheduler_thread.join(timeout=2)
            scheduler_ledger.close()
            if second_process.is_alive():
                second_process.terminate()
                second_process.join(timeout=2)
        self.assertEqual(second_process.exitcode, 0)
        with psycopg.connect(DSN, row_factory=psycopg.rows.dict_row) as db:
            db.execute(f'SET search_path TO "{self.schema}"')
            attempts = db.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s",
                                  (assignment_id,)).fetchone()["n"]
            verifications = db.execute("SELECT count(*) AS n FROM verification_records "
                "WHERE assignment_id=%s AND decision='ACCEPTED'", (assignment_id,)).fetchone()["n"]
        self.assertEqual(attempts, 1)
        self.assertEqual(verifications, 1)


if __name__ == "__main__":
    unittest.main()
