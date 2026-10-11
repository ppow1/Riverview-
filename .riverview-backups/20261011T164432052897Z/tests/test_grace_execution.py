# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_execution.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Exercise objective-to-authorized-worker-to-independent-verification pipeline
# Execution Model: Isolated PostgreSQL schema, committed repository fixture, deterministic proposal
# Observability: Durable objective/assignment events, worker attempt, artifact, verifier decision
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL; Git; Psycopg 3
# Authority: Random isolated test schema and temporary directories only
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Initial end-to-end tests
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Model-independent integration test of Grace objective execution."""

import hashlib
import os
import secrets
import subprocess
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from riverview_core.assignment_intake import AuthorizedAssignmentIntake
from riverview_core.institutional_authority import ExactGrantAuthorizer
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.postgres_migrations import apply_migrations
from riverview_core.resident_execution import (
    GraceExecutionPipeline, ObjectiveNotAuthorized, ObjectiveStateError,
)
from riverview_core.resident_reasoning import PlanProposal, PlanStep
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
        self.assertEqual([event["event_type"] for event in
                          self.pipeline.objective_events(row["objective_id"])],
                         ["objective.received", "objective.grounded",
                          "work_order.proposed", "work_order.dispatched",
                          "objective.completed"])

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


if __name__ == "__main__":
    unittest.main()
