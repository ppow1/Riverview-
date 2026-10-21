# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_execution.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.53
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-RECONCILIATION | Cover exact-scope audited heading removal, authorization, and revision conflicts.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-OPTIONAL-CRITERIA-20261021 | Run derived-criteria persistence under the exact authorized Engineering intake scope.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-OPTIONAL-CRITERIA-20261021 | Verify empty intake derives and atomically persists one proposal-bound criteria list.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-CLASSIFICATION-20261021 | Reject artifact paths not named in the authorized request and reject invented formal criteria
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Reject narrative lifecycle false positives, missing publication origin, and duplicated criterion ownership
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Verify ready lifecycle work runs before slow proposal reasoning and persist lifecycle criteria separately from one deliverable step
# Changed: 2026-10-21 UTC | RV-GRACE-PROPOSAL-OUTPUT-BUDGET | Require a 2048-token default proposal completion budget
# Changed: 2026-10-20 UTC | RV-GRACE-GROUNDED-OBJECTIVE-FAIR-QUEUE-001 | Prove never-attempted and least-recently-attempted grounded objectives take fair reasoning turns, including repeated failures.
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-002 | Cover arbitrary multi-artifact bounded contracts and repair PostgreSQL proposal fixtures
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Cover dynamic assignment artifacts, multi-file persistence, and independent contract verification
# Changed: 2026-10-20 UTC | RV-GRACE-REASONING-PROPOSAL-RECOVERY-20261020 | Assert incomplete-proposal exceptions map to a fixed safe diagnostic code
# Changed: 2026-10-20 UTC | RV-GRACE-ACCEPTED-STEP-REWORK-001 | Cover verifier-accepted dependent dispatch without second-model gating and bounded durable rejection escalation.
# Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Preserve production behavior while integrating the authenticated bounded re-review caller.
# Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Verify generation-two evidence preserves the active digest-checked artifact-review contract.
# Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Cover global review-key collision, bounded due-review selection and persisted rework receipt recovery.
# Changed: 2026-10-19 UTC | RV-C1-GRACE-RESULT-RECEIPT-001 | Exercise PostgreSQL outbox acknowledgement when publisher omits completion_cycle
# Changed: 2026-10-19 UTC | RV-C1-PR152-SCOPE-PROVENANCE-001 | Authenticate objective detail integration read with a Steward account session
# Changed: 2026-10-19 UTC | RV-GRACE-REREVIEW-OPERATOR-CALLER-001 | Verify authenticated HTTP rereview persistence, scope denial, idempotency, and no dispatch side effect.
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Cover mixed-capability claims, verification routing, and isolated worker failure behavior.
# Changed: 2026-10-17 UTC | RV-GRACE-PERSISTENT-AUTONOMY-001 | Cover persistent proposal failure recording and retry limits.
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
# Changed: 2026-10-19 UTC | RV-GRACE-REREVIEW-PG-QUALIFICATION | Cover authorization, evidence idempotency, crash recovery, and rejected continuation in PostgreSQL
# Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-GENERATIONS-001 | Cover authorized durable review revision request and bounded receipt
# Changed: 2026-10-16 UTC | RV-GRACE-STRUCTURED-REVIEW-001 | Verify same-objective continuation is durable, scoped, and dispatched through CME
# Changed: 2026-10-16 UTC | RV-GRACE-SCOPE-LEASE-RECONCILE-001 | Scope expired recovery and verify a late Codex artifact proceeds through independent verification
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Exercise same-objective rejection/rework/acceptance and repeated-rejection stop with real PostgreSQL authority and ledger
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-FIX-001 | Cover rework after assignment workflow_step has been replaced by the verifier transition label
# Changed: 2026-10-19 UTC | RV-C1-GRACE-REJECTION-ROLE-CLARIFICATION | Require Grace's durable substantive-satisfaction decision before same-attempt Codex verifier revalidation; preserve legacy rejection.
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Verify late artifact recovery, preserved rejection, and restart-safe accepted revalidation
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reject source-change proposals whose exact paths were not included in the Steward's request or accepted criteria
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-REASONING-BUDGET-001 | Guard the default completion budget needed for typed multi-step plans
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Use a verified test-only repository observation while testing explicit path authorization
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Prove a persisted source-change work order cannot be claimed by the artifact worker after mutable ledger transitions
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Keep generic retry recovery fixture outside Grace proposal scope fencing
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reject model source-change proposals with empty, malformed, or unbounded file scope
# Changed: 2026-10-16 UTC | RV-GRACE-REVIEW-OBJECTIVE-PROGRESS | Include durable objective and step status in verified-result review records
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reject source-change execution tests outside tests/ paths
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Gate dependent-step dispatch on durable result review and continuation decision
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
    ArtifactRequirement, PlanProposal, PlanStep, ReasoningResult, ReasoningStatus,
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
    def test_persistent_reasoning_failures_are_recorded_and_rate_limited(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.resident_reasoning import ReasoningStatus

        class Cursor:
            def __init__(self, db):
                self.db = db
                self.row = None
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, query, params):
                if query.lstrip().startswith("SELECT count(*)"):
                    self.row = {"failures": len(self.db.failures)}
                elif "execution.reasoning_failed" in query:
                    self.db.failures.append(params[1])
            def fetchone(self): return self.row

        class DB:
            def __init__(self): self.failures = []
            def cursor(self): return Cursor(self)
            def transaction(self): return nullcontext()

        class Ledger:
            def __init__(self): self.db = DB()
            def _set_search_path(self, _cursor): pass

        class Pipeline:
            def __init__(self): self.ledger = Ledger()
            def grounded_objectives(self, **_kwargs):
                return [{"objective_id": "objective:bounded-test"}]

        class Reasoner:
            office_id = "office:grace"
            providers = {"80B": object()}
            calls = 0
            def propose(self, *_args, **_kwargs):
                self.calls += 1
                return SimpleNamespace(status=ReasoningStatus.INVALID_PROPOSAL,
                    detail_code="PROPOSAL_SCHEMA_OR_BUDGET",
                    request_id=f"request-{self.calls}", proposal=None)

        pipeline, reasoner = Pipeline(), Reasoner()
        class Worker:
            def run_once(self, **_kwargs): return {"status": "IDLE"}
        service = GraceExecutionService(pipeline, None, Worker(),
            dispatch_credential="dispatch", authority_ref="work-order:engineering",
            verifier_id="verifier", verifier_credential="verify", artifact_root="/tmp/unused",
            resident_reasoner=reasoner)
        self.assertFalse(service.reason_one_grounded_objective())
        self.assertFalse(service.reason_one_grounded_objective())
        self.assertFalse(service.reason_one_grounded_objective())
        self.assertFalse(service.reason_one_grounded_objective())
        self.assertEqual(reasoner.calls, 3)
        self.assertEqual(len(pipeline.ledger.db.failures), 3)

    def test_grace_proposal_budget_supports_bounded_multistep_plans(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        class Worker:
            def run_once(self, **_kwargs): return {"status": "IDLE"}
        service = GraceExecutionService(None, None, Worker(), dispatch_credential="dispatch",
            authority_ref="work-order:test", verifier_id="verifier",
            verifier_credential="verify", artifact_root="/tmp/unused")
        self.assertEqual(service.resident_token_budget, 2048)

    def test_run_once_advances_ready_work_before_slow_grounded_reasoning(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        import threading

        entered_reasoning = threading.Event()
        release_reasoning = threading.Event()
        order = []
        class Worker:
            def run_once(self, **_kwargs):
                order.append("worker")
                return {"status": "IDLE"}

        service = GraceExecutionService(None, None, Worker(), dispatch_credential="dispatch",
            authority_ref="work-order:test", verifier_id="verifier",
            verifier_credential="verify", artifact_root="/tmp/unused")
        def record(name, result=0):
            def run(*_args, **_kwargs):
                order.append(name)
                return result
            return run
        service.dispatch_proposed = record("dispatch")
        service.verify_one = record("verify")
        service.reconcile_completions = record("completion")
        service.publish_conversation_results = record("publish")
        service.reconcile_proposal_lifecycle = record("proposal_lifecycle")
        service.publish_rejected_work_order_reviews = record("rejected_review")
        service.consume_external_reasoning = record("external_reasoning")
        def slow_reasoning():
            order.append("proposal_reasoning")
            entered_reasoning.set()
            self.assertTrue(release_reasoning.wait(2))
            return True
        service.reason_one_grounded_objective = slow_reasoning
        service._run_doorbell_worker = record("doorbell", {"status": "NOT_CONFIGURED"})
        service._heartbeat = record("heartbeat")

        thread = threading.Thread(target=service.run_once)
        thread.start()
        self.assertTrue(entered_reasoning.wait(2))
        self.assertEqual(order[:5], ["dispatch", "worker", "verify", "completion", "publish"])
        release_reasoning.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())


    def test_dual_capability_worker_failure_isolated_from_peer(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        calls = []
        class Worker:
            def __init__(self, name, fail=False): self.name, self.fail = name, fail
            def run_once(self, **_kwargs):
                calls.append(self.name)
                if self.fail: raise RuntimeError("fixture")
                return {"status": "IDLE"}
        class Verifier:
            REVISION = "test-v1"
            def verify(self, *_args): return None
        artifact = "engineering.codex-cli-artifact.v1"
        source = "engineering.codex-cli-source-change.v1"
        workers = {artifact: Worker("artifact", fail=True), source: Worker("source")}
        service = GraceExecutionService(None, None, workers[artifact],
            dispatch_credential="dispatch", authority_ref="work-order:test",
            verifier_id="verifier", verifier_credential="verify", artifact_root="/tmp/unused",
            execution_capability=artifact, execution_workers=workers,
            verifiers={artifact: Verifier(), source: Verifier()})
        result = service._run_workers()
        self.assertEqual(set(calls), {"artifact", "source"})
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["capabilities"][artifact]["status"], "FAILED")
        self.assertEqual(result["capabilities"][source]["status"], "IDLE")

    def test_artifact_only_worker_configuration_remains_supported(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        class Worker:
            def run_once(self, **_kwargs): return {"status": "IDLE"}
        service = GraceExecutionService(None, None, Worker(), dispatch_credential="dispatch",
            authority_ref="work-order:test", verifier_id="verifier",
            verifier_credential="verify", artifact_root="/tmp/unused")
        self.assertEqual(service.execution_capabilities, ("engineering.bounded-artifact.v1",))
        self.assertEqual(service._run_workers(), {"status": "IDLE"})

    def test_source_change_plan_requires_nonempty_bounded_authorized_paths(self):
        from riverview_core.resident_reasoning import PlanStep
        capability = "engineering.codex-cli-source-change.v1"
        with self.assertRaises(ValueError):
            PlanStep("step", "edit", ("verify",), execution_capability=capability)
        with self.assertRaises(ValueError):
            PlanStep("step", "edit", ("verify",), execution_capability=capability,
                     authorized_paths=("src/app.py",), test_targets=())
        with self.assertRaises(ValueError):
            PlanStep("step", "edit", ("verify",), execution_capability=capability,
                     authorized_paths=("src/../private.py",), test_targets=("tests/test_app.py",))
        with self.assertRaises(ValueError):
            PlanStep("step", "edit", ("verify",), execution_capability=capability,
                     authorized_paths=("src/app.py",), test_targets=("src/app.py",))
        valid = PlanStep("step", "edit", ("verify",), execution_capability=capability,
                         authorized_paths=("src/app.py", "tests/test_app.py"),
                         test_targets=("tests/test_app.py",),
                         repository_reference="repo://test/repo",
                         repository_revision="a" * 40)
        self.assertEqual(valid.authorized_paths, ("src/app.py", "tests/test_app.py"))

    def test_worker_contract_rejects_unbounded_operations_and_timeout(self):
        common = dict(assignment_id="assignment:1", objective_id="objective:1",
                      repository_reference="repo://docs/contract.md",
                      repository_revision="a" * 40, task_scope="write a bounded artifact",
                      acceptance_criteria=("artifact exists",),
                      artifact_requirements=(ArtifactRequirement("proof", "results/proof.json",
                          "application/json", ("artifact exists",)),),
                      source_sha256="b" * 64, source_references=("repo://docs/contract.md",))
        self.assertEqual(CodingWorkOrder(**common).allowed_operations,
                         ("write_bounded_json_artifact",))
        with self.assertRaises(ValueError):
            CodingWorkOrder(**common, allowed_operations=("shell",))
        with self.assertRaises(ValueError):
            CodingWorkOrder(**common, timeout_seconds=91)
        with self.assertRaises(ValueError):
            CodingWorkOrder(**{**common, "repository_revision": "not-a-commit"})


class GraceReasoningFailureDiagnosticTests(unittest.TestCase):
    def test_incomplete_acceptance_proposal_has_safe_detail_code(self):
        from riverview_core.resident_execution.service import GraceExecutionService

        error = ObjectiveStateError("proposal omits one or more human acceptance criteria")
        self.assertEqual(GraceExecutionService._reasoning_failure_detail_code(error),
                         "PROPOSAL_OMITS_ACCEPTANCE_CRITERIA")
        self.assertEqual(GraceExecutionService._reasoning_failure_detail_code(
            RuntimeError("untrusted provider message")), "REASONING_CYCLE_FAILED")

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

    def _create_grounded_reasoning_objective(self, objective_id):
        row = self.pipeline.submit_objective(
            objective_id, "Document worker retry contract",
            ["artifact contains the task and verified repository provenance"],
            credential=self.credentials["steward"], scope_ref=self.scope)
        return self.pipeline.ground_objective(row["objective_id"])

    def _reasoning_service(self, reasoner):
        from riverview_core.resident_execution.service import GraceExecutionService

        return GraceExecutionService(
            self.pipeline, None, None, dispatch_credential="dispatch",
            authority_ref=self.scope, verifier_id=self.verifier_id,
            verifier_credential=self.credentials["verifier"],
            artifact_root=str(self.root), resident_reasoner=reasoner)

    def test_grounded_reasoning_schedules_never_attempted_then_least_recently_attempted(self):
        from types import SimpleNamespace

        older_id = "objective:queue-fairness-older"
        newer_id = "objective:queue-fairness-newer"
        self._create_grounded_reasoning_objective(older_id)
        self._create_grounded_reasoning_objective(newer_id)

        class FailingReasoner:
            office_id = "office:grace-test"
            providers = {"provider.test": object()}

            def __init__(self):
                self.calls = []

            def propose(inner_self, objective_id, **_kwargs):
                inner_self.calls.append(objective_id)
                return SimpleNamespace(status=ReasoningStatus.INVALID_PROPOSAL,
                    detail_code="PROPOSAL_SCHEMA_OR_BUDGET",
                    request_id=f"failed-{len(inner_self.calls)}", proposal=None)

        reasoner = FailingReasoner()
        service = self._reasoning_service(reasoner)
        for _ in range(4):
            self.assertFalse(service.reason_one_grounded_objective())

        self.assertEqual(reasoner.calls, [older_id, newer_id, older_id, newer_id])
        for objective_id in (older_id, newer_id):
            event_types = [event["event_type"] for event in
                           self.pipeline.objective_events(objective_id)]
            self.assertEqual(event_types.count("execution.reasoning_attempted"), 2)
            self.assertEqual(event_types.count("execution.reasoning_failed"), 2)

    def test_single_grounded_objective_can_still_persist_its_typed_proposal(self):
        from types import SimpleNamespace

        from riverview_core.resident_reasoning import PlanProposal, PlanStep

        objective_id = "objective:queue-fairness-single"
        objective = self._create_grounded_reasoning_objective(objective_id)
        criterion = objective["acceptance_criteria"][0]
        proposal = PlanProposal("Document the retry contract", (
            PlanStep("document", "Create a bounded retry-contract work product",
                     (criterion,)),), 0)

        class ProposingReasoner:
            office_id = "office:grace-test"
            providers = {"provider.test": object()}

            def __init__(inner_self):
                inner_self.calls = []

            def propose(inner_self, objective_id, **_kwargs):
                inner_self.calls.append(objective_id)
                return SimpleNamespace(status=ReasoningStatus.PROPOSED,
                    request_id="proposal-request", proposal=proposal)

        reasoner = ProposingReasoner()
        service = self._reasoning_service(reasoner)

        self.assertTrue(service.reason_one_grounded_objective())
        self.assertEqual(reasoner.calls, [objective_id])
        persisted = self.pipeline.get_objective(objective_id)
        self.assertEqual(persisted["status"], "PROPOSED")
        self.assertEqual(persisted["proposal"]["summary"], proposal.summary)
        event_types = [event["event_type"] for event in
                       self.pipeline.objective_events(objective_id)]
        self.assertIn("execution.reasoning_attempted", event_types)

    def test_grace_derived_criteria_become_the_single_effective_objective_list(self):
        from psycopg import sql
        from riverview_core.resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep

        objective_id = "objective:derived-criteria:" + uuid4().hex
        principal = self.principals["steward"][0]
        self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES (%s,%s,'objective.submit','work-order:engineering',%s,
                    'rv.policy:grace-execution-test.v1')""").format(sql.Identifier(self.schema)),
            ("steward-derived-objective-submit", principal, principal))
        criterion = "The report contains the exact requested verification statement."
        request = "Create a report at reports/derived.txt containing the exact requested verification statement."
        row = self.pipeline.submit_objective(objective_id, request, [],
            credential=self.credentials["steward"], scope_ref="work-order:engineering",
            origin={"conversation_id": str(uuid4()), "source_sequence": 1},
            criteria_source="grace_derived")
        self.assertEqual(row["acceptance_criteria"], [])
        self.assertEqual(row["acceptance_criteria_source"], "grace_derived")
        self.pipeline.ground_objective(objective_id)
        proposal = PlanProposal("Create the requested report", (
            PlanStep("report", "Create the bounded report", (criterion,),
                artifact_requirements=(ArtifactRequirement("report", "reports/derived.txt",
                    "text/plain", (criterion,)),)),), 0)
        stored = self.pipeline.record_proposal(objective_id, proposal)
        self.assertEqual(stored["acceptance_criteria"], [criterion])
        self.assertEqual(stored["acceptance_criteria_source"], "grace_derived")
        event = next(item for item in self.pipeline.objective_events(objective_id)
                     if item["event_type"] == "work_order.proposed")
        self.assertEqual(event["payload"]["acceptance_criteria_source"], "grace_derived")

    def test_authorized_criteria_reconciliation_is_exact_atomic_and_audited(self):
        from psycopg import sql
        from riverview_core.resident_execution import ObjectiveNotAuthorized, ObjectiveStateError

        objective_id = "objective:grace-conversation:8416c5da-bde5-5294-9276-c0163418fae1"
        principal = self.principals["steward"][0]
        before = [
            "Requirements:",
            "- Create exactly one Engineering assignment for the file.",
            "- Use the authorized artifact destination recorded in the work order.",
            "- Independently verify the actual file contents.",
            "- Close the objective only after successful verification.",
        ]
        original_request = "Original complete request remains preserved."
        self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES (%s,%s,'objective.submit','work-order:engineering',%s,
                    'rv.policy:grace-execution-test.v1')""").format(sql.Identifier(self.schema)),
            ("criteria-reconcile-submit-test", principal, principal))
        self.pipeline.submit_objective(objective_id, original_request, before,
            credential=self.credentials["steward"], scope_ref="work-order:engineering")
        grounded = self.pipeline.ground_objective(objective_id)
        self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES (%s,%s,'objective.criteria.reconcile',%s,%s,
                    'rv.policy:grace-execution-test.v1')""").format(sql.Identifier(self.schema)),
            ("criteria-reconcile-test", principal, objective_id, principal))

        with self.assertRaises(ObjectiveStateError):
            self.pipeline.reconcile_misclassified_requirements_heading(objective_id,
                expected_revision=grounded["revision"] + 1,
                credential=self.credentials["steward"], reason="test")
        self.assertEqual(self.pipeline.get_objective(objective_id)["revision"], 2)
        with self.assertRaises(ObjectiveNotAuthorized):
            self.pipeline.reconcile_misclassified_requirements_heading(objective_id,
                expected_revision=2, credential=secrets.token_urlsafe(36), reason="test")
        reconciled = self.pipeline.reconcile_misclassified_requirements_heading(objective_id,
            expected_revision=2, credential=self.credentials["steward"],
            reason="Steward-approved removal of the misclassified structural heading.")
        self.assertEqual(reconciled["status"], "GROUNDED")
        self.assertEqual(reconciled["revision"], 3)
        self.assertEqual(reconciled["request"], original_request)
        self.assertEqual(reconciled["acceptance_criteria"], before[1:])
        self.assertEqual(reconciled["evidence"], grounded["evidence"])
        self.assertIsNone(reconciled["proposal"])
        self.assertIsNone(reconciled["assignment_id"])
        events = [event for event in self.pipeline.objective_events(objective_id)
                  if event["event_type"] == "objective.criteria_reconciled"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["actor_id"], principal)
        self.assertEqual(events[0]["payload"]["before_criteria"], before)
        self.assertEqual(events[0]["payload"]["after_criteria"], before[1:])
        self.assertEqual(events[0]["payload"]["expected_revision"], 2)
        self.assertEqual(events[0]["payload"]["new_revision"], 3)
        self.assertEqual(events[0]["payload"]["authorization_grant_id"],
                         "criteria-reconcile-test")
        from psycopg.errors import RaiseException
        with self.assertRaises(RaiseException):
            with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE grace_objective_events SET payload='{}'::jsonb
                    WHERE objective_id=%s AND event_type='objective.criteria_reconciled'""",
                    (objective_id,))
        with self.assertRaises(ObjectiveStateError):
            self.pipeline.reconcile_misclassified_requirements_heading(objective_id,
                expected_revision=2, credential=self.credentials["steward"], reason="replay")

    def test_criteria_guard_rejects_unapproved_direct_mutation(self):
        from psycopg.errors import RaiseException

        objective_id = "objective:criteria-guard:" + uuid4().hex
        objective = self._create_grounded_reasoning_objective(objective_id)
        with self.assertRaises(RaiseException):
            with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE grace_objectives SET acceptance_criteria='[\"invented\"]'::jsonb
                    WHERE objective_id=%s""", (objective_id,))
        self.assertEqual(self.pipeline.get_objective(objective_id)["acceptance_criteria"],
                         objective["acceptance_criteria"])

    def test_lifecycle_criteria_remain_durable_without_receipt_work_steps(self):
        from riverview_core.resident_reasoning import lifecycle_evidence_event

        self.assertIsNone(lifecycle_evidence_event(
            "The report contains a section describing the proposal being saved."))
        objective_id = "objective:lifecycle-criteria:" + uuid4().hex
        deliverable = "The report contains exact phrase `verified delivery`."
        lifecycle = (
            "The objective is grounded before execution.",
            "The approved work order is dispatched.",
            "Independent verification is accepted.",
            "Grace returns the result to the Steward conversation.",
            "The objective is completed.",
        )
        self.pipeline.submit_objective(objective_id,
            "Create one bounded report at reports/report.md and complete the existing institutional workflow.",
            [deliverable, *lifecycle], credential=self.credentials["steward"],
            scope_ref=self.scope, origin={"conversation_id": str(uuid4()), "source_sequence": 1})
        self.pipeline.ground_objective(objective_id)
        proposal = PlanProposal("Create and verify one report", (
            PlanStep("report", "Create the bounded report", (deliverable,),
                artifact_requirements=(ArtifactRequirement("report", "reports/report.md",
                    "text/markdown", (deliverable,)),)),), 0,
            system_owned_criteria=lifecycle)
        with self.assertRaisesRegex(ObjectiveStateError, "every original criterion"):
            self.pipeline.record_proposal(objective_id, PlanProposal(
                "Omit the lifecycle requirements", (PlanStep("wrong", "Create report",
                    (deliverable,)),), 0))
        with self.assertRaisesRegex(ObjectiveStateError, "every original criterion"):
            self.pipeline.record_proposal(objective_id, PlanProposal(
                "Duplicate the deliverable", (
                    PlanStep("first", "Create report", (deliverable,)),
                    PlanStep("second", "Repeat report", (deliverable,))), 0,
                system_owned_criteria=lifecycle))
        with self.assertRaisesRegex(ObjectiveStateError, "every original criterion"):
            self.pipeline.record_proposal(objective_id, PlanProposal(
                "Promote request instructions to criteria", (
                    PlanStep("report", "Create report", (deliverable,
                        "Do not create a replacement objective."), artifact_requirements=(
                            ArtifactRequirement("report", "reports/report.md", "text/markdown",
                                                (deliverable,)),)),), 0,
                system_owned_criteria=lifecycle))
        with self.assertRaisesRegex(ObjectiveStateError, "artifact path is absent"):
            self.pipeline.record_proposal(objective_id, PlanProposal(
                "Use an unauthorized artifact path", (
                    PlanStep("report", "Create report", (deliverable,), artifact_requirements=(
                        ArtifactRequirement("report", "private/report.md", "text/markdown",
                                            (deliverable,)),)),), 0,
                system_owned_criteria=lifecycle))
        stored = self.pipeline.record_proposal(objective_id, proposal)
        self.assertEqual(len(stored["proposal"]["steps"]), 1)
        self.assertEqual(stored["proposal"]["system_owned_criteria"], list(lifecycle))
        self.assertEqual(stored["acceptance_criteria"], [deliverable, *lifecycle])
        proposed_event = next(event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"] == "work_order.proposed")
        self.assertEqual([item["criterion"] for item in
            proposed_event["payload"]["system_owned_criteria"]], list(lifecycle))
        self.assertEqual({item["evidence_event_type"] for item in
            proposed_event["payload"]["system_owned_criteria"]}, {
                "objective.grounded", "work_order.dispatched", "execution.step_verified",
                "conversation.result_published", "objective.completed"})
        assignment_id = "assignment:lifecycle-criteria:" + uuid4().hex
        assignment = self.pipeline.authorize_and_dispatch(objective_id, assignment_id,
            credential=self.credentials["steward"], authority_ref=self.scope,
            idempotency_key="lifecycle-criteria:" + objective_id, step_id="report")
        self.assertEqual(assignment["workflow_step"], "report")
        self.assertEqual(self.admin.execute(f'SELECT count(*) FROM "{self.schema}".assignments '
            "WHERE objective_ref=%s", (objective_id,)).fetchone()[0], 1)

        no_origin_id = "objective:lifecycle-no-origin:" + uuid4().hex
        no_origin = self.pipeline.submit_objective(no_origin_id,
            "Create a bounded report and return the result to the Steward conversation.",
            ["The bounded report exists.",
             "Grace returns the result to the Steward conversation."],
            credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(no_origin["objective_id"])
        with self.assertRaisesRegex(ObjectiveStateError, "every original criterion"):
            self.pipeline.record_proposal(no_origin["objective_id"], PlanProposal(
                "Return the result", (PlanStep("report", "Create the report",
                    ("The bounded report exists.",)),), 0,
                system_owned_criteria=("Grace returns the result to the Steward conversation.",)))

    def test_authorized_objective_executes_and_is_independently_verified(self):
        with self.assertRaises(ObjectiveNotAuthorized):
            self.pipeline.submit_objective(
                "objective:denied", "document retry contract", ["record source"],
                credential=secrets.token_urlsafe(36), scope_ref=self.scope)
        row = self.pipeline.submit_objective(
            "objective:grace-e2e", "document worker retry contract at results/retry.json and evidence/summary.data",
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
                     ("artifact contains the task and verified repository provenance",),
                     artifact_requirements=(ArtifactRequirement("retry-proof", "results/retry.json",
                         "application/json", ("artifact contains the task and verified repository provenance",)),
                         ArtifactRequirement("audit-summary", "evidence/summary.data",
                         "application/json", ("artifact contains the task and verified repository provenance",)))),), 0)
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
        verifier = BoundedArtifactVerifier(self.root / "artifacts", self.pipeline)
        with self.adapter.ledger.db.cursor() as cur:
            self.adapter.ledger._set_search_path(cur)
            cur.execute("SELECT result FROM worker_results WHERE attempt_id=%s", (attempt_id,))
            worker_result = cur.fetchone()["result"]
        rejected_contract = json.loads(json.dumps(worker_result))
        rejected_contract["artifact_contract"][0]["name"] = "unauthorized-name"
        rejected = verifier.verify({"id": assignment_id, "objective_ref": row["objective_id"]},
            {"status": "succeeded", "capability": "engineering.bounded-artifact.v1",
             "attempt_id": attempt_id}, rejected_contract)
        self.assertEqual(rejected.status.value, "REJECTED")
        from unittest.mock import patch
        resolved_step = self.pipeline.proposal_step_for_assignment(row["objective_id"], assignment_id)
        changed_step = json.loads(json.dumps(resolved_step))
        changed_step["artifact_requirements"][0]["path"] = "unauthorized/changed.json"
        with patch.object(self.pipeline, "proposal_step_for_assignment", return_value=changed_step):
            rejected_changed_contract = verifier.verify(
                {"id": assignment_id, "objective_ref": row["objective_id"]},
                {"status": "succeeded", "capability": "engineering.bounded-artifact.v1",
                 "attempt_id": attempt_id}, worker_result)
        self.assertEqual(rejected_changed_contract.status.value, "REJECTED")
        artifact_dir = (self.root / "artifacts" / worker_result["artifacts"][0]["storage_name"]).parent
        extra_file = artifact_dir / "unauthorized-extra-object"
        extra_file.write_text("{}", encoding="utf-8")
        extra_file.chmod(0o600)
        rejected_extra = verifier.verify({"id": assignment_id, "objective_ref": row["objective_id"]},
            {"status": "succeeded", "capability": "engineering.bounded-artifact.v1",
             "attempt_id": attempt_id}, worker_result)
        self.assertEqual(rejected_extra.status.value, "REJECTED")
        extra_file.unlink()
        decision = self.adapter.verify_attempt(
            assignment_id, attempt_id, self.verifier_id, self.credentials["verifier"],
            verifier,
            idempotency_key="grace-verify-" + assignment_id)
        self.assertEqual(decision.status.value, "ACCEPTED", dict(decision.criteria))
        result = self.pipeline.record_verified_completion(row["objective_id"], assignment_id)
        self.assertEqual(result["status"], "COMPLETED")
        products = [path for path in (self.root / "artifacts").rglob("*") if path.is_file()]
        self.assertEqual(len(products), 2)
        self.assertTrue(all(path.stat().st_size > 0 for path in products))
        evidence_dir = os.environ.get("RIVERVIEW_TEST_EVIDENCE_DIR")
        if evidence_dir:
            evidence_root = Path(evidence_dir)
            artifact_dir = evidence_root / "artifacts"
            artifact_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            preserved = artifact_dir / "bounded-work-product.json"
            shutil.copyfile(products[0], preserved)
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

    def test_late_codex_artifact_is_preserved_for_independent_verification(self):
        from unittest.mock import patch
        from riverview_core.resident_execution.codex_cli import CAPABILITY
        from riverview_core.resident_execution.codex_workflow import CodexArtifactVerifier
        from riverview_core.worker_adapter import PostgresRecoveryCoordinator
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        objective_id = "objective:late-codex:" + uuid4().hex
        criterion = "artifact contains the exact late output"
        self.pipeline.submit_objective(objective_id,
            "produce one bounded report at reports/late-report.md", [criterion],
            credential=self.credentials["steward"], scope_ref=self.scope,
            origin={"conversation_id": str(uuid4()), "source_sequence": 6})
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal("Produce a bounded report", (
            PlanStep("report", "Create a Markdown report", (criterion,), artifact_requirements=(
                ArtifactRequirement("late-report", "reports/late-report.md", "text/markdown",
                                    (criterion,)),), execution_capability=CAPABILITY),), 0))
        assignment_id = "assignment:late-codex:" + uuid4().hex
        self.pipeline.authorize_and_dispatch(objective_id, assignment_id,
            credential=self.credentials["steward"], authority_ref=self.scope,
            idempotency_key="late-codex-dispatch:" + assignment_id)
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
            "late-codex-ready:" + assignment_id, actor_id="event-processor")
        executor_id = "worker:late-codex:" + uuid4().hex
        self.adapter.register_worker(executor_id, [CAPABILITY], self.scope,
                                     credential=self.credentials["worker"])
        claim = self.adapter.claim_next(executor_id, self.credentials["worker"],
            capability=CAPABILITY, assignment_id=assignment_id, lease_seconds=30)
        generation = claim["lease"]["generation"]
        self.adapter.start_assignment(assignment_id, executor_id, self.credentials["worker"],
                                      generation, capability=CAPABILITY)
        intent_id = self.adapter.begin_execution_intent(assignment_id, executor_id,
            self.credentials["worker"], generation, "late-codex-intent:" + assignment_id,
            effect_class="external_uncertain", capability=CAPABILITY)
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/components/WORKER_ADAPTER.md",),
            source_revision=self.commit, source_sha256="a" * 64,
            retrieval_complete=True)
        self.adapter.record_knowledge_observation(assignment_id, executor_id,
            "reground_assignment", grounded, action=CAPABILITY)
        self.admin.execute(f'UPDATE "{self.schema}".assignment_leases SET '
            "acquired_at=clock_timestamp()-interval '2 minutes', "
            "heartbeat_at=clock_timestamp()-interval '2 minutes', "
            "expires_at=clock_timestamp()-interval '1 minute' WHERE assignment_id=%s",
            (assignment_id,))
        recovery = PostgresRecoveryCoordinator(DSN, schema=self.schema)
        try:
            expired = recovery.reconcile_expired(scope_ref=self.scope, worker_id=executor_id)
            self.assertEqual(expired[0]["decision"], "outcome_unknown")
            artifact_root = self.root / "late-artifacts"
            artifact_root.mkdir(mode=0o700)
            name = "codex-" + hashlib.sha256(assignment_id.encode()).hexdigest()
            artifact_dir = artifact_root / name
            artifact_dir.mkdir(mode=0o700)
            artifact = artifact_dir / hashlib.sha256(b"late-report").hexdigest()[:12]
            artifact.write_text("# Completed bounded report\n\n" + criterion + "\n",
                                encoding="utf-8")
            artifact.chmod(0o600)
            recovered = recovery.reconcile_late_codex_artifacts(
                worker_adapter=self.adapter, worker_id=executor_id,
                credential=self.credentials["worker"], capability=CAPABILITY,
                scope_ref=self.scope, artifact_root=artifact_root,
                repository_revision=self.commit)
            self.assertEqual(len(recovered), 1)
            self.assertEqual(recovered[0]["assignment_id"], assignment_id)
            self.assertEqual(self.ledger.get(assignment_id)["state"], "awaiting_verification")
            self.assertEqual(self.admin.execute(f'SELECT decision FROM "{self.schema}".worker_recovery_records '
                "WHERE assignment_id=%s", (assignment_id,)).fetchone()[0], "outcome_unknown")
            intent = self.admin.execute(f'SELECT status,failure_class FROM "{self.schema}".worker_execution_intents '
                "WHERE intent_id=%s", (intent_id,)).fetchone()
            self.assertEqual(intent, ("succeeded", "ProcessInterrupted"))
            from riverview_core.worker_adapter.verifier import VerificationResult, VerificationStatus

            class PriorVerifier:
                REVISION = "1.0.0"
                def verify(self, assignment, attempt, result):
                    return VerificationResult(VerificationStatus.REJECTED,
                        {"legacy_exact_criteria_parser": False},
                        (f"urn:rv:worker-attempt:{attempt['attempt_id']}",),
                        self.REVISION, "preserved predecessor verifier decision")

            prior = self.adapter.verify_attempt(assignment_id, recovered[0]["attempt_id"],
                self.verifier_id, self.credentials["verifier"], PriorVerifier(),
                idempotency_key="late-codex-verification:" + assignment_id)
            self.assertEqual(prior.status, VerificationStatus.REJECTED)
            self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
            from riverview_core.resident_execution.service import GraceExecutionService
            service = GraceExecutionService(self.pipeline, self.adapter,
                ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"]),
                dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
                verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
                artifact_root=artifact_root, verifier=CodexArtifactVerifier(artifact_root, self.pipeline),
                execution_capability=CAPABILITY)
            self.assertFalse(service.revalidate_rejected_one(assignment_id))
            rejected_context = self.pipeline.pending_rejected_work_order_reviews()[0]
            satisfied = {"decision": "OBJECTIVE_SATISFIED",
                "rationale": "Grace assessed the actual bounded report as substantively satisfying the assigned requirement.",
                "correction_instruction": None, "criteria_to_address": []}
            self.pipeline.record_rework_decision(rejected_context, satisfied,
                credential=self.credentials["steward"])
            self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
            corrected_key = (f"grace-verifier-revalidation:{recovered[0]['attempt_id']}:{CodexArtifactVerifier.REVISION}")
            with patch.object(self.adapter.ledger, "transition",
                              side_effect=RuntimeError("simulated transition interruption")):
                with self.assertRaisesRegex(RuntimeError, "transition interruption"):
                    self.adapter.verify_attempt(assignment_id, recovered[0]["attempt_id"],
                        self.verifier_id, self.credentials["verifier"],
                        CodexArtifactVerifier(artifact_root, self.pipeline), idempotency_key=corrected_key)
            self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
            self.assertEqual(self.admin.execute(f'SELECT count(*) FROM "{self.schema}".verification_records '
                "WHERE attempt_id=%s AND decision='ACCEPTED'", (recovered[0]["attempt_id"],)).fetchone()[0], 1)
            self.assertTrue(service.verify_one(assignment_id))
            self.assertEqual(self.ledger.get(assignment_id)["state"], "completed")
            rows = self.admin.execute(f'SELECT verifier_revision,decision FROM "{self.schema}".verification_records '
                "WHERE attempt_id=%s ORDER BY verifier_revision", (recovered[0]["attempt_id"],)).fetchall()
            self.assertEqual(rows, [ ("1.0.0", "REJECTED"), ("1.0.4", "ACCEPTED")])
            self.assertEqual(self.admin.execute(f'SELECT count(*) FROM "{self.schema}".worker_attempts '
                "WHERE assignment_id=%s", (assignment_id,)).fetchone()[0], 1)
        finally:
            recovery.close()

    def test_multistep_dispatch_follows_independent_acceptance_without_second_model_gate(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id = "objective:project-status-report"
        self.pipeline.submit_objective(objective_id,
            "Assess whether a simple project-status report should be standard for new Riverview Engineering assignments; identify useful fields, stalled-work value, and risks. Produce reports/project-status.json and reports/assignment-analysis.json.",
            ["The assigned report answers the assessment using only the original request and verified records",
             "The report discloses when historical assignment analysis was not performed"],
            credential=self.credentials["steward"], scope_ref=self.scope,
            origin={"conversation_id": str(uuid4()), "source_sequence": 1})
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal(
            "Draft a project-status report and map its fields", (
                PlanStep("prepare", "Create the requested project-status assessment",
                         ("The assigned report answers the assessment using only the original request and verified records",),
                         artifact_requirements=(ArtifactRequirement("status-report", "reports/project-status.json",
                             "application/json", ("The assigned report answers the assessment using only the original request and verified records",)),)),
                PlanStep("followup", "Map report fields from verified assignment records and disclose when historical assignment analysis was not performed",
                         ("The report discloses when historical assignment analysis was not performed",),
                         depends_on=("prepare",), artifact_requirements=(ArtifactRequirement(
                             "analysis-data", "reports/assignment-analysis.json", "application/json",
                             ("The report discloses when historical assignment analysis was not performed",)),))), 0))
        class ResultPublisher:
            def __init__(self):
                self.cycles = []
            def __call__(self, context):
                self.cycles.append(context["completion_cycle"])
                return {"status": "published", "request_id": f"result:{context['completion_cycle']}",
                    "provider_id": "provider:test", "served_model": "model:test",
                    "implementation_id": "implementation:test",
                    "review_decision": "OBJECTIVE_COMPLETE"}
        publisher = ResultPublisher()
        worker = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=BoundedLocalCodingWorker(self.pipeline, self.root / "step-artifacts"),
            action_effect_class="retry_safe", action_capability="engineering.bounded-artifact.v1")
        service = GraceExecutionService(self.pipeline, self.adapter, worker,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=self.root / "step-artifacts",
            conversation_result_publisher=publisher)

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
        pending_step_review = self.pipeline.pending_conversation_results()
        self.assertEqual(len(pending_step_review), 1)
        self.assertEqual(pending_step_review[0]["completion_cycle"], 1)
        self.assertEqual(pending_step_review[0]["completion"]["assignment_id"], first)
        self.assertEqual(pending_step_review[0]["completion"]["decision"], "ACCEPTED")
        self.assertEqual(pending_step_review[0]["objective_status"], "WORK_ORDER_CREATED")
        self.assertEqual([step["status"] for step in pending_step_review[0]["step_progress"]],
                         ["verified", "pending"])
        self.assertEqual(self.pipeline.dispatchable_step(objective_id)["step_id"], "followup",
                         "independent ACCEPTED s1 advances through the persisted dependency graph")
        assignments_before = self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".assignments WHERE objective_ref=%s", (objective_id,)).fetchone()[0]
        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        second = self.pipeline.get_objective(objective_id)["assignment_id"]
        self.assertEqual(self.ledger.get(second)["workflow_step"], "followup")
        self.assertEqual(service.dispatch_proposed(objective_id), 0)
        self.assertEqual(self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".assignments WHERE objective_ref=%s", (objective_id,)).fetchone()[0], assignments_before + 1)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "WORK_ORDER_CREATED",
                         "one accepted step must not complete the multi-step objective")
        class DurableReviewPublisher:
            def __init__(self):
                self.receipts = {}
                self.calls = {}
                self.cycles = []
                self.decisions = {1: "ADDITIONAL_EVIDENCE_REQUIRED",
                                  2: "ADDITIONAL_EVIDENCE_REQUIRED"}
            def __call__(self, context):
                cycle = context["completion_cycle"]
                generation = context["review_generation"]
                self.cycles.append(cycle)
                key = (cycle, generation)
                self.calls[key] = self.calls.get(key, 0) + 1
                if key not in self.receipts:
                    self.receipts[key] = {"request_id":f"test-result:cycle:{cycle}:generation:{generation}",
                        "provider_id":"provider:test", "served_model":"model:test",
                        "implementation_id":"implementation:test",
                        "review_decision":self.decisions[cycle]}
                    if generation > 1:
                        self.receipts[key].update({"review_generation":str(generation),
                            "review_evidence_revision":context["review_evidence_revision"],
                            "review_evidence_sha256":context["review_evidence_sha256"]})
                return {"status":"published" if self.calls[key] == 1 else "already_published",
                        **self.receipts[key]}
        publisher = DurableReviewPublisher()
        service.conversation_result_publisher = publisher
        record_receipt = self.pipeline.record_conversation_result_published
        crash_once = {"pending":True}
        def fail_before_ack(obj_id, receipt):
            if obj_id == objective_id and crash_once["pending"]:
                crash_once["pending"] = False
                raise RuntimeError("simulated crash after conversation persistence")
            return record_receipt(obj_id, receipt)
        self.pipeline.record_conversation_result_published = fail_before_ack
        self.assertEqual(service.publish_conversation_results(), 0)
        self.assertEqual(publisher.calls[(1, 1)], 1)
        self.assertFalse(any(event["event_type"] == "conversation.result_published"
                             for event in self.pipeline.objective_events(objective_id)))
        self.pipeline.record_conversation_result_published = record_receipt
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(publisher.calls[(1, 1)], 2)
        self.assertEqual(service.publish_conversation_results(), 0)
        self.assertEqual(publisher.calls[(1, 1)], 2)
        wrong_scope_credential = secrets.token_urlsafe(36)
        wrong_scope_principal = "steward:wrong-scope:" + uuid4().hex
        self.admin.execute(f'INSERT INTO "{self.schema}".institutional_principals '
            "(principal_id,principal_kind) VALUES (%s,'resident')", (wrong_scope_principal,))
        self.admin.execute(f'INSERT INTO "{self.schema}".principal_credentials '
            "(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)",
            (uuid4(), wrong_scope_principal,
             hashlib.sha256(wrong_scope_credential.encode()).digest()))
        self.admin.execute(f'INSERT INTO "{self.schema}".authority_grants '
            "(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) "
            "VALUES (%s,%s,'objective.submit',%s,%s,'rv.policy:grace-execution-test.v1')",
            (wrong_scope_principal + ":submit", wrong_scope_principal,
             self.scope + ":different-objective", wrong_scope_principal))
        with self.assertRaises(ObjectiveNotAuthorized):
            self.pipeline.request_conversation_result_rereview(objective_id, 1,
                evidence_revision="wrong-scope-rev",
                evidence=["Evidence from a wrong-scope principal."],
                credential=wrong_scope_credential,
                idempotency_key="wrong-scope:" + objective_id)
        revision = self.pipeline.request_conversation_result_rereview(objective_id, 1,
            evidence_revision="steward-evidence-rev-1",
            evidence=["Read-only historical assignment aggregates were shared with Grace."],
            credential=self.credentials["steward"],
            idempotency_key="review-evidence-revision:" + objective_id + ":1")
        self.assertEqual(revision["review_generation"], 2)
        self.assertFalse(revision["reused"])
        retried_revision = self.pipeline.request_conversation_result_rereview(objective_id, 1,
            evidence_revision="steward-evidence-rev-1",
            evidence=["Read-only historical assignment aggregates were shared with Grace."],
            credential=self.credentials["steward"],
            idempotency_key="review-evidence-revision:" + objective_id + ":1")
        self.assertTrue(retried_revision["reused"])
        with self.assertRaisesRegex(ObjectiveStateError, "idempotency key conflicts"):
            self.pipeline.request_conversation_result_rereview(objective_id, 1,
                evidence_revision="steward-evidence-rev-CHANGED",
                evidence=["Changed evidence must not reuse the existing generation key."],
                credential=self.credentials["steward"],
                idempotency_key="review-evidence-revision:" + objective_id + ":1")
        review_context = self.pipeline.pending_conversation_results()
        self.assertEqual(review_context[0]["review_generation"], 2)
        self.assertEqual(review_context[0]["review_evidence_revision"],
                         "steward-evidence-rev-1")
        self.assertEqual(review_context[0]["review_evidence_sha256"],
                         revision["evidence_sha256"])
        self.assertIsNone(self.pipeline.dispatchable_step(objective_id),
                          "the only dependent step is already durably assigned")
        self.pipeline.record_conversation_result_published(objective_id, {
            "request_id": str(uuid4()), "provider_id": "provider:test",
            "served_model": "model:test", "implementation_id": "implementation:test",
            "completion_cycle": "1", "review_generation": "2",
            "review_evidence_revision": "steward-evidence-rev-1",
            "review_evidence_sha256": revision["evidence_sha256"]})
        self.assertEqual(self.pipeline.pending_conversation_results(), [])
        expanded_step = PlanStep("followup", "Expand beyond the accepted objective",
            ("Create an unrelated application",), depends_on=("prepare",))
        with self.assertRaises(ObjectiveStateError):
            self.pipeline.propose_continuation(objective_id, first, expanded_step)
        self.assertFalse(any(event["event_type"] == "work_order.continuation_proposed"
                             for event in self.pipeline.objective_events(objective_id)))
        self.assertFalse(any(event["event_type"] == "work_order.continuation_proposed"
                             and event["payload"].get("step_id") == "supplemental"
                             for event in self.pipeline.objective_events(objective_id)))
        assignment = self.ledger.get(second)
        self.assertEqual(assignment["workflow_step"], "followup")
        self.ledger.transition(second, "ready", "event_processor_ready", "ready:" + second,
                               actor_id="event-processor")
        result = worker.run_once(assignment_id=second)
        self.assertEqual(result["status"], "AWAITING_VERIFICATION")
        self.assertTrue(service.verify_one(second))
        self.assertEqual(self.pipeline.record_verified_completion(objective_id, second)["status"],
                         "WORK_ORDER_CREATED")
        self.assertEqual(service.publish_conversation_results(), 1,
                         "the final output is delivered for Grace's substantive review")
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 1)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "WORK_ORDER_CREATED",
                         "additional evidence is not accepted as objective completion")
        self.assertEqual(self.pipeline.pending_conversation_results(), [])
        revision = self.pipeline.request_conversation_result_rereview(objective_id, 2,
            evidence_revision="final-review-evidence-v1",
            evidence=["The final verified artifact satisfies the objective's substantive criteria."],
            credential=self.credentials["steward"],
            idempotency_key="final-review:" + objective_id)
        self.assertEqual(revision["review_generation"], 2)
        publisher.decisions[2] = "OBJECTIVE_COMPLETE"
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 1)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "COMPLETED")
        pending = self.pipeline.pending_conversation_results()
        self.assertEqual(pending, [])
        self.assertEqual(service.publish_conversation_results(), 0)
        self.assertIn(2, publisher.cycles)
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT step_id,status,assignment_id FROM grace_objective_steps
                WHERE objective_id=%s ORDER BY step_order""", (objective_id,))
            rows = cur.fetchall()
        self.assertEqual([row["step_id"] for row in rows], ["prepare", "followup"])
        self.assertEqual([row["status"] for row in rows], ["verified", "verified"])
        self.assertNotEqual(rows[0]["assignment_id"], rows[1]["assignment_id"])

    def _create_rework_fixture(self, suffix, *, conversation_id=None):
        objective_id = "objective:governed-rework:" + suffix
        assignment_id = "assignment:grace:governed-rework:" + suffix
        criteria = ["criterion " + str(index) + " must be preserved exactly"
                    for index in range(1, 5)]
        origin = {"conversation_id": conversation_id or str(uuid4()), "source_sequence": 6}
        self.pipeline.submit_objective(objective_id,
            "Create a bounded acceptance artifact at reports/acceptance.txt", criteria,
            credential=self.credentials["steward"], scope_ref=self.scope, origin=origin)
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id,
            PlanProposal("Create acceptance artifact", (PlanStep("s1",
                "Create an acceptance artifact", tuple(criteria), artifact_requirements=(
                    ArtifactRequirement("acceptance", "reports/acceptance.txt", "text/plain",
                        tuple(criteria)),)),), 0))
        self.pipeline.authorize_and_dispatch(objective_id, assignment_id,
            credential=self.credentials["steward"], authority_ref=self.scope,
            idempotency_key="rework-dispatch:" + suffix)
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
            "rework-ready:" + suffix, actor_id="event-processor")

        class ReworkAction:
            def __init__(_self, pipeline):
                _self.pipeline = pipeline
                _self.calls = []
            def __call__(_self, assignment, _grounded):
                instruction = _self.pipeline.latest_rework_instruction(assignment["id"])
                _self.calls.append(instruction)
                return {"status": "SUCCEEDED", "artifact_schema": "rv.test.rework.v1",
                    "artifact_name": "attempt-" + str(len(_self.calls)) + ".json",
                    "acceptance_criteria": list(criteria),
                    "correction_instruction": (instruction or {}).get("correction_instruction"),
                    "criteria_to_address": (instruction or {}).get("criteria_to_address", [])}

        class RejectUntilCorrectedVerifier:
            REVISION = "test-governed-rework-1"
            def verify(_self, _assignment, attempt, result):
                from riverview_core.worker_adapter.verifier import VerificationResult, VerificationStatus
                fixed = result.get("correction_instruction") == \
                    "Include all four exact criteria in the assigned artifact."
                accepted = fixed
                flags = {"acceptance_criteria_are_present": bool(accepted),
                    "result_is_bound_to_assignment": result.get("acceptance_criteria") == criteria}
                return VerificationResult(VerificationStatus.ACCEPTED if accepted else
                    VerificationStatus.REJECTED, flags,
                    ("urn:rv:worker-attempt:" + str(attempt["attempt_id"]),),
                    _self.REVISION, "accepted" if accepted else "required exact criteria are absent")

        action = ReworkAction(self.pipeline)
        worker = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
            knowledge=self.knowledge, action=action, action_effect_class="retry_safe",
            action_capability="engineering.bounded-artifact.v1")
        return objective_id, assignment_id, criteria, action, worker, RejectUntilCorrectedVerifier()

    def test_rejected_assignment_rework_preserves_rejection_and_reaches_independent_acceptance(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id, assignment_id, criteria, action, worker, verifier = self._create_rework_fixture("accept")
        class GraceAcceptancePublisher:
            def __call__(_self, context):
                return {"status": "published", "request_id": "test-grace-accepted:" +
                    str(context["completion_cycle"]), "provider_id": "provider:test",
                    "served_model": "model:test", "implementation_id": "implementation:test",
                    "review_decision": "OBJECTIVE_COMPLETE"}
        service = GraceExecutionService(self.pipeline, self.adapter, worker,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=self.root / "rework-artifacts", verifier=verifier,
            execution_capability="engineering.bounded-artifact.v1",
            conversation_result_publisher=GraceAcceptancePublisher())
        first = worker.run_once(assignment_id=assignment_id)
        self.assertEqual(first["status"], "AWAITING_VERIFICATION")
        first_generation = self.admin.execute("SELECT generation FROM " + self.schema +
            ".assignment_leases WHERE assignment_id=%s", (assignment_id,)).fetchone()[0]
        self.assertTrue(service.verify_one(assignment_id))
        self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
        context = self.pipeline.pending_rejected_work_order_reviews()[0]
        self.assertEqual(context["objective_id"], objective_id)
        self.assertEqual(context["assignment_id"], assignment_id)
        # The assignment transition records "verification_rejected" in the
        # legacy workflow_step field; the objective-step link remains canonical.
        self.assertEqual(self.ledger.get(assignment_id)["workflow_step"],
                         "verification_rejected")
        self.assertEqual(context["step_id"], "s1")
        self.assertEqual(context["step_acceptance_criteria"], criteria)
        decision = {"decision": "REWORK_PROPOSED", "rationale": "The artifact omitted the exact criteria.",
            "correction_instruction": "Include all four exact criteria in the assigned artifact.",
            "criteria_to_address": criteria}
        persisted = self.pipeline.record_rework_decision(context, decision,
            credential=self.credentials["steward"])
        self.assertEqual(persisted["verification_id"], context["completion"]["verification_id"])
        self.assertEqual(self.ledger.get(assignment_id)["state"], "ready")
        self.assertEqual(self.ledger.get(assignment_id)["workflow_step"], "s1")
        self.assertEqual(self.pipeline.get_objective(objective_id)["assignment_id"], assignment_id)
        retried = worker.run_once(assignment_id=assignment_id)
        self.assertEqual(retried["status"], "AWAITING_VERIFICATION")
        retry_generation = self.admin.execute("SELECT generation FROM " + self.schema +
            ".assignment_leases WHERE assignment_id=%s", (assignment_id,)).fetchone()[0]
        self.assertEqual(retry_generation, first_generation + 1)
        self.assertEqual(action.calls[-1]["verification_id"], context["completion"]["verification_id"])
        self.assertTrue(service.verify_one(assignment_id))
        self.assertEqual(self.ledger.get(assignment_id)["state"], "completed")
        completion = self.pipeline.record_verified_completion(objective_id, assignment_id)
        self.assertEqual(completion["status"], "WORK_ORDER_CREATED")
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 1)
        completion = self.pipeline.get_objective(objective_id)
        self.assertEqual(completion["status"], "COMPLETED")
        table = self.schema + ".verification_records"
        rows = self.admin.execute("SELECT decision FROM " + table +
            " WHERE assignment_id=%s ORDER BY recorded_at,verification_id", (assignment_id,)).fetchall()
        self.assertEqual(rows, [("REJECTED",), ("ACCEPTED",)])
        self.assertEqual(self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".assignments WHERE objective_ref=%s", (objective_id,)).fetchone()[0], 1)
        self.assertEqual(self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".worker_attempts WHERE assignment_id=%s", (assignment_id,)).fetchone()[0], 2)
        self.assertEqual(self.pipeline.get_objective(objective_id)["acceptance_criteria"], criteria)
        events = self.pipeline.objective_events(objective_id)
        rework_events = [event for event in events if event["event_type"] == "engineering.rework_decided"]
        self.assertEqual(len(rework_events), 1)
        repeated = self.pipeline.record_rework_decision(context, decision,
            credential=self.credentials["steward"])
        self.assertEqual(repeated, rework_events[0]["payload"])

    def test_repeated_rejection_can_stop_within_bounded_retry_limit(self):
        objective_id, assignment_id, criteria, _action, worker, verifier = self._create_rework_fixture("stop")
        first = worker.run_once(assignment_id=assignment_id)
        self.adapter.verify_attempt(assignment_id, first["attempt_id"], self.verifier_id,
            self.credentials["verifier"], verifier,
            idempotency_key="governed-rework-first:" + assignment_id)
        first_context = self.pipeline.pending_rejected_work_order_reviews()[0]
        rework = {"decision": "REWORK_PROPOSED", "rationale": "Attempt the bounded correction.",
            "correction_instruction": "Use the exact accepted criteria, but this fixture still omits them.",
            "criteria_to_address": criteria}
        self.pipeline.record_rework_decision(first_context, rework,
            credential=self.credentials["steward"])
        second = worker.run_once(assignment_id=assignment_id)
        self.adapter.verify_attempt(assignment_id, second["attempt_id"], self.verifier_id,
            self.credentials["verifier"], verifier,
            idempotency_key="governed-rework-second:" + assignment_id)
        self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
        second_context = self.pipeline.pending_rejected_work_order_reviews()[0]
        self.assertNotEqual(first_context["completion"]["verification_id"],
                            second_context["completion"]["verification_id"])
        stop = {"decision": "STEWARD_AUTHORIZATION_REQUIRED",
            "rationale": "The second independently rejected result needs Steward direction.",
            "correction_instruction": None, "criteria_to_address": []}
        self.pipeline.record_rework_decision(second_context, stop,
            credential=self.credentials["steward"])
        repeated = self.pipeline.record_rework_decision(second_context, stop,
            credential=self.credentials["steward"])
        self.assertEqual(repeated["decision"], "STEWARD_AUTHORIZATION_REQUIRED")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
        self.assertEqual(len([event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"] == "engineering.rework_decided"]), 2)
        self.assertEqual(self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".verification_records WHERE assignment_id=%s AND decision='REJECTED'",
            (assignment_id,)).fetchone()[0], 2)
        self.assertEqual(self.pipeline.get_objective(objective_id)["assignment_id"], assignment_id)

    def test_rework_retry_exhaustion_persists_actionable_pending_without_dispatch(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id, assignment_id, criteria, _action, worker, _verifier = \
            self._create_rework_fixture("retry-exhaustion")

        class AlwaysReject:
            REVISION = "test-project-status-report-rejection-1"
            def verify(_self, _assignment, _attempt, _result):
                from riverview_core.worker_adapter.verifier import VerificationResult, VerificationStatus
                return VerificationResult(VerificationStatus.REJECTED,
                    {"criterion_missing": True}, ("urn:rv:worker-attempt:rejected",),
                    _self.REVISION, "The assigned artifact omitted a scoped acceptance criterion")

        service = GraceExecutionService(self.pipeline, self.adapter, worker,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=self.root / "rework-artifacts", verifier=AlwaysReject())
        for index in range(self.pipeline.MAX_GOVERNED_REWORK_ATTEMPTS):
            outcome = worker.run_once(assignment_id=assignment_id)
            self.assertEqual(outcome["status"], "AWAITING_VERIFICATION")
            self.assertTrue(service.verify_one(assignment_id))
            context = self.pipeline.pending_rejected_work_order_reviews()[0]
            self.assertEqual(context["step_acceptance_criteria"], criteria)
            decision = {"decision": "REWORK_PROPOSED",
                "rationale": "Correct only the listed project-status acceptance criterion.",
                "correction_instruction": "Update the assigned artifact for the exact rejected criterion.",
                "criteria_to_address": [criteria[index % len(criteria)]]}
            saved = self.pipeline.record_rework_decision(context, decision,
                credential=self.credentials["steward"])
            self.assertEqual(saved["decision"], "REWORK_PROPOSED")

        final_outcome = worker.run_once(assignment_id=assignment_id)
        self.assertEqual(final_outcome["status"], "AWAITING_VERIFICATION")
        self.assertTrue(service.verify_one(assignment_id))
        exhausted = self.pipeline.pending_rejected_work_order_reviews()[0]
        self.assertEqual(exhausted["rework_attempt_count"],
                         self.pipeline.MAX_GOVERNED_REWORK_ATTEMPTS)
        self.assertEqual(service.publish_rejected_work_order_reviews(), 0)
        events = self.pipeline.objective_events(objective_id)
        pending = [event for event in events
            if event["event_type"] == "engineering.rework_escalation_pending"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["payload"]["decision"], "ESCALATION_PENDING")
        self.assertEqual(pending[0]["payload"]["reason_code"], "retry_limit_exhausted")
        self.assertEqual(pending[0]["payload"]["step_id"], "s1")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
        self.assertEqual(self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".assignments WHERE objective_ref=%s", (objective_id,)).fetchone()[0], 1)
        forbidden = {"decision": "REWORK_PROPOSED",
            "rationale": "Attempt beyond bound.",
            "correction_instruction": "Repeat the same scoped correction.",
            "criteria_to_address": [criteria[0]]}
        with self.assertRaisesRegex(ObjectiveStateError, "retry limit is exhausted"):
            self.pipeline.record_rework_decision(exhausted, forbidden,
                credential=self.credentials["steward"])

        from riverview_core.status_dashboard.projection import DashboardProjection
        projection = DashboardProjection(DSN, schema=self.schema,
            source_commit=self.commit, deployment_id="test-rework-escalation")
        item = projection.objectives(objective_id=objective_id)["items"][0]
        self.assertEqual(item["lifecycle_status"], "blocked")
        self.assertTrue(item["steward_action_required"])

    def test_uncommissioned_rejection_review_provider_records_pending_without_requeue(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id, assignment_id, _criteria, _action, worker, verifier = \
            self._create_rework_fixture("provider-uncommissioned")
        service = GraceExecutionService(self.pipeline, self.adapter, worker,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=self.root / "rework-artifacts", verifier=verifier,
            rejected_work_order_publisher=None)
        attempt = worker.run_once(assignment_id=assignment_id)
        self.assertEqual(attempt["status"], "AWAITING_VERIFICATION")
        self.assertTrue(service.verify_one(assignment_id))
        self.assertEqual(service.publish_rejected_work_order_reviews(), 0)
        pending = [event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"] == "engineering.rework_escalation_pending"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["payload"]["reason_code"], "review_provider_uncommissioned")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
        self.assertEqual(self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".assignments WHERE objective_ref=%s", (objective_id,)).fetchone()[0], 1)

    def test_dashboard_projects_current_rejection_and_steward_rework_decision_by_conversation(self):
        from riverview_core.status_dashboard.projection import DashboardProjection
        conversation_id = str(uuid4())
        objective_id, assignment_id, criteria, _action, worker, verifier = \
            self._create_rework_fixture("projection-rejected", conversation_id=conversation_id)
        result = worker.run_once(assignment_id=assignment_id)
        self.adapter.verify_attempt(assignment_id, result["attempt_id"], self.verifier_id,
            self.credentials["verifier"], verifier,
            idempotency_key="progress-projection-verify:" + assignment_id)
        projection = DashboardProjection(DSN, schema=self.schema,
            source_commit=self.commit, deployment_id="test-governed-rework")
        initial = projection.objectives(conversation_id=conversation_id)["items"]
        self.assertEqual(len(initial), 1)
        item = initial[0]
        self.assertEqual(item["objective_id"], objective_id)
        self.assertEqual(item["assignment_id"], assignment_id)
        self.assertEqual(item["origin"]["source_sequence"], 6)
        self.assertEqual(item["lifecycle_status"], "waiting")
        self.assertEqual(item["lifecycle_stage"], "Grace reviewing verifier rejection")
        self.assertEqual(item["verification"]["decision"], "REJECTED")
        self.assertIn("required exact criteria are absent", item["verification"]["summary"])
        self.assertEqual(item["rework"]["rejected_results"], 1)
        self.assertFalse(item["steward_action_required"])
        self.assertEqual(projection.objectives(conversation_id=str(uuid4()))["items"], [])
        context = self.pipeline.pending_rejected_work_order_reviews()[0]
        stop = {"decision": "STEWARD_AUTHORIZATION_REQUIRED",
            "rationale": "The rejection requires Steward direction.",
            "correction_instruction": None, "criteria_to_address": []}
        self.pipeline.record_rework_decision(context, stop,
            credential=self.credentials["steward"])
        blocked = projection.objectives(conversation_id=conversation_id)["items"][0]
        self.assertEqual(blocked["lifecycle_status"], "blocked")
        self.assertTrue(blocked["steward_action_required"])

    def test_source_change_paths_must_be_explicit_in_steward_scope(self):
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        class FixedVerifiedKnowledge:
            def ground_assignment(_self, _assignment):
                return KnowledgeResult(KnowledgeStatus.VERIFIED,
                    {"evidence": "bounded source repository"},
                    ("repo://src/a.py", "repo://src/b.py", "repo://tests/test_ab.py"),
                    self.commit, "c" * 64, True)

        self.pipeline.knowledge = FixedVerifiedKnowledge()
        target_root = self.root / "independent-target-repository"
        target_root.mkdir()
        subprocess.run(["git", "init", "-q", str(target_root)], check=True)
        (target_root / "src").mkdir()
        (target_root / "src/a.py").write_text("VALUE = 1\n", encoding="utf-8")
        (target_root / "tests").mkdir()
        (target_root / "tests/test_ab.py").write_text("def test_value(): assert True\n",
                                                        encoding="utf-8")
        subprocess.run(["git", "-C", str(target_root), "config", "user.email", "test@invalid"], check=True)
        subprocess.run(["git", "-C", str(target_root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(target_root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(target_root), "commit", "-qm", "pinned target"], check=True)
        target_revision = subprocess.check_output(
            ["git", "-C", str(target_root), "rev-parse", "HEAD"], text=True).strip()
        self.assertNotEqual(target_revision, self.commit)
        objective_id = "objective:source-change-human-scope"
        self.pipeline.submit_objective(objective_id,
            f"Improve the test fixture in repo://test/repo at {target_revision}.",
            ["The test remains passing."], credential=self.credentials["steward"],
            scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        paths = ("src/a.py", "src/b.py", "tests/test_ab.py")
        source_step = PlanStep("source", "Modify bounded files",
            ("The test remains passing.",), execution_capability=
            "engineering.codex-cli-source-change.v1", authorized_paths=paths,
            test_targets=("tests/test_ab.py",), repository_reference="repo://test/repo",
            repository_revision=target_revision)
        with self.assertRaisesRegex(ObjectiveStateError, "Steward-approved objective scope"):
            self.pipeline.record_proposal(objective_id,
                PlanProposal("Scoped source change", (source_step,), 0))
        approved_id = "objective:source-change-explicit-scope"
        self.pipeline.submit_objective(approved_id,
            f"Update repo://test/repo at {target_revision}; files: src/a.py, src/b.py, and tests/test_ab.py.",
            ["Only those three files change and the focused test passes."],
            credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(approved_id)
        approved_step = PlanStep("source", "Modify bounded files",
            ("Only those three files change and the focused test passes.",),
            execution_capability="engineering.codex-cli-source-change.v1",
            authorized_paths=paths, test_targets=("tests/test_ab.py",),
            repository_reference="repo://test/repo", repository_revision=target_revision)
        persisted = self.pipeline.record_proposal(approved_id,
            PlanProposal("Scoped source change", (approved_step,), 0))
        self.assertEqual(persisted["status"], "PROPOSED")
        self.assertEqual(persisted["proposal"]["steps"][0]["authorized_paths"], list(paths))
        assignment_id = "assignment:source-capability:" + uuid4().hex
        self.pipeline.authorize_and_dispatch(approved_id, assignment_id,
            credential=self.credentials["steward"], authority_ref=self.scope,
            idempotency_key="dispatch:" + assignment_id)
        assignment_step = self.pipeline.proposal_step_for_assignment(approved_id, assignment_id)
        binding = assignment_step["source_target_binding"]
        self.assertEqual(binding["version"], "grace.source-target-binding.v1")
        self.assertEqual(binding["repository_reference"], "repo://test/repo")
        self.assertEqual(binding["repository_revision"], target_revision)
        objective_record = self.pipeline.get_objective(approved_id)
        self.assertEqual(objective_record["source_revision"], self.commit)
        self.assertNotEqual(objective_record["source_revision"], binding["repository_revision"])
        self.assertEqual(binding["assignment_id"], assignment_id)
        self.assertEqual(binding["step_id"], "source")
        self.assertEqual(binding["authorized_paths"], list(paths))
        self.assertEqual(binding["test_targets"], ["tests/test_ab.py"])
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
            "ready:" + assignment_id, actor_id="event-processor")
        artifact_worker = "worker:artifact-only:" + uuid4().hex
        source_worker = "worker:source-change:" + uuid4().hex
        self.adapter.register_worker(artifact_worker,
            ["engineering.codex-cli-artifact.v1"], self.scope,
            credential=self.credentials["worker"])
        self.adapter.register_worker(source_worker,
            ["engineering.codex-cli-source-change.v1"], self.scope,
            credential=self.credentials["worker"])
        self.assertIsNone(self.adapter.claim_next(artifact_worker,
            self.credentials["worker"], capability="engineering.codex-cli-artifact.v1",
            assignment_id=assignment_id))
        source_claim = self.adapter.claim_next(source_worker, self.credentials["worker"],
            capability="engineering.codex-cli-source-change.v1",
            assignment_id=assignment_id)
        self.assertIsNotNone(source_claim)

    def test_dual_capability_claims_and_verification_route_by_persisted_attempt_capability(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.worker_adapter.verifier import VerificationResult, VerificationStatus
        artifact_cap = "engineering.bounded-artifact.v1"
        source_cap = "engineering.codex-cli-source-change.v1"
        source_id, source_token = "worker:source-test:" + uuid4().hex, secrets.token_urlsafe(36)
        source_principal = "principal:" + source_id
        self.admin.execute(f'INSERT INTO "{self.schema}".institutional_principals '
            "(principal_id,principal_kind) VALUES (%s,'resident')", (source_principal,))
        self.admin.execute(f'INSERT INTO "{self.schema}".principal_credentials '
            "(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)",
            (uuid4(), source_principal, hashlib.sha256(source_token.encode()).digest()))
        for action in ("worker.register", "assignment.execute"):
            self.admin.execute(f'INSERT INTO "{self.schema}".authority_grants '
                "(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) "
                "VALUES (%s,%s,%s,%s,%s,'rv.policy:grace-execution-test.v1')",
                (source_id + ":" + action, source_principal, action, self.scope, source_principal))
        source_adapter = PostgresWorkerAdapter(DSN, schema=self.schema)
        self.addCleanup(source_adapter.close)
        source_adapter.register_worker(source_id, [source_cap], self.scope,
                                       credential=source_token)

        class Action:
            def __init__(self, capability): self.capability = capability
            def __call__(self, assignment, _grounded):
                return {"status": "SUCCEEDED", "capability": self.capability,
                        "assignment_id": assignment["id"]}
            def validate_proposal_target(self, _step): return True
        class RecordingVerifier:
            def __init__(self, capability): self.capability, self.calls = capability, []
            REVISION = "dual-test-v1"
            def verify(self, assignment, attempt, _result):
                self.calls.append((assignment["id"], attempt["capability"]))
                return VerificationResult(VerificationStatus.ACCEPTED,
                    {"selected_capability_matches": attempt["capability"] == self.capability},
                    ("test://capability-verification",), self.REVISION,
                    "capability-specific test verifier")
        class WrapWorker:
            def __init__(self, worker, action): self.worker, self.action = worker, action
            def run_once(self, **kwargs): return self.worker.run_once(**kwargs)

        artifact_action, source_action = Action(artifact_cap), Action(source_cap)
        artifact_loop = ContinuousWorker(self.adapter, self.worker_id,
            self.credentials["worker"], knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=artifact_action, action_effect_class="retry_safe", action_capability=artifact_cap)
        source_loop = ContinuousWorker(source_adapter, source_id, source_token,
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit), action=source_action,
            action_effect_class="retry_safe", action_capability=source_cap)
        artifact_verifier, source_verifier = RecordingVerifier(artifact_cap), RecordingVerifier(source_cap)
        workers = {artifact_cap: WrapWorker(artifact_loop, artifact_action),
                   source_cap: WrapWorker(source_loop, source_action)}
        service = GraceExecutionService(self.pipeline, self.adapter, workers[artifact_cap],
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=self.root / "dual-artifacts", execution_capability=artifact_cap,
            execution_workers=workers, verifiers={artifact_cap: artifact_verifier,
                                                   source_cap: source_verifier})

        artifact_objective = "objective:dual-artifact:" + uuid4().hex
        criterion = "The bounded result is accepted."
        self.pipeline.submit_objective(artifact_objective,
            "Create a bounded artifact result at results/dual-proof.json.",
            [criterion], credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(artifact_objective)
        self.pipeline.record_proposal(artifact_objective, PlanProposal("Artifact test", (
            PlanStep("artifact", "Create a bounded result", (criterion,), artifact_requirements=(
                ArtifactRequirement("dual-proof", "results/dual-proof.json", "application/json",
                                    (criterion,)),)),), 0))
        self.pipeline.authorize_and_dispatch(artifact_objective, "assignment:dual:artifact:" + uuid4().hex,
            credential=self.credentials["steward"], authority_ref=self.scope,
            idempotency_key="dual-artifact:" + uuid4().hex)

        source_objective = "objective:dual-source:" + uuid4().hex
        target_ref = "repo://test/dual-source"
        paths = ("src/a.py", "tests/test_a.py")
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
        self.pipeline.knowledge = type("FixedVerifiedKnowledge", (), {
            "ground_assignment": lambda _self, _assignment: KnowledgeResult(
                KnowledgeStatus.VERIFIED, {"evidence": "bounded source repository"},
                ("repo://docs/verified.md",), self.commit, "c" * 64, True),
            "reground_assignment": lambda _self, _assignment, _trigger: KnowledgeResult(
                KnowledgeStatus.VERIFIED, {"evidence": "bounded source repository"},
                ("repo://docs/verified.md",), self.commit, "c" * 64, True)})()
        self.pipeline.submit_objective(source_objective,
            f"Edit src/a.py and tests/test_a.py in {target_ref} at {self.commit}.",
            ["The scoped source test passes."], credential=self.credentials["steward"],
            scope_ref=self.scope)
        self.pipeline.ground_objective(source_objective)
        source_plan = PlanStep("source", "Make the bounded source change",
            ("The scoped source test passes.",), execution_capability=source_cap,
            authorized_paths=paths, test_targets=("tests/test_a.py",),
            repository_reference=target_ref, repository_revision=self.commit)
        self.pipeline.record_proposal(source_objective,
            PlanProposal("Source test", (source_plan,), 0))
        self.pipeline.authorize_and_dispatch(source_objective, "assignment:dual:source:" + uuid4().hex,
            credential=self.credentials["steward"], authority_ref=self.scope,
            idempotency_key="dual-source:" + uuid4().hex)

        assignments = [self.pipeline.get_objective(artifact_objective)["assignment_id"],
                       self.pipeline.get_objective(source_objective)["assignment_id"]]
        for assignment_id in assignments:
            self.ledger.transition(assignment_id, "ready", "event_processor_ready",
                "dual-ready:" + assignment_id, actor_id="event-processor")
        outcomes = [artifact_loop.run_once(assignment_id=assignments[0]),
                    source_loop.run_once(assignment_id=assignments[1])]
        self.assertEqual([item["status"] for item in outcomes],
                         ["AWAITING_VERIFICATION", "AWAITING_VERIFICATION"])
        self.assertTrue(service.verify_one())
        self.assertTrue(service.verify_one())
        self.assertEqual(artifact_verifier.calls, [(assignments[0], artifact_cap)])
        self.assertEqual(source_verifier.calls, [(assignments[1], source_cap)])
        self.assertEqual(self.pipeline.record_verified_completion(artifact_objective,
            assignments[0])["status"], "COMPLETED")
        self.assertEqual(self.pipeline.record_verified_completion(source_objective,
            assignments[1])["status"], "COMPLETED")

    def test_pr62_source_change_cycle_persists_two_verified_dependent_steps(self):
        import shutil
        from riverview_core.resident_execution.codex_cli import CodexCLIExecutionAdapter
        from riverview_core.resident_execution.codex_source_change import (
            CAPABILITY as SOURCE_CAPABILITY, CodexSourceChangeAdapter,
            CodexSourceChangeVerifier)
        from riverview_core.resident_execution.codex_workflow import (
            CodexSourceChangeResultVerifier, CodexSourceChangeWorkAction)
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
        pinned = "5885c8d9395dde43898f7a47a37a15cfc849299a"
        fixture = Path("/opt/riverview-pr62-disposable-acceptance")
        if not fixture.is_dir():
            self.skipTest("pinned PR62 fixture is not installed")
        target = self.root / "pr62-two-step-target"
        shutil.copytree(fixture, target)
        target_revision = subprocess.check_output(["/usr/bin/git", "-C", str(target),
            "rev-parse", "HEAD"], text=True).strip()
        if target_revision != pinned:
            self.skipTest("isolated PR62 target does not match the approved test commit")
        self.assertNotEqual(target_revision, self.commit)
        codex_exec = self.root / "pr62-codex"
        codex_exec.write_text("#!/usr/bin/env python3\n"
            "import json,pathlib,sys\n"
            "prompt=sys.stdin.read()\n"
            "root=pathlib.Path.cwd()\n"
            "if 'Step 1:' in prompt:\n"
            " (root/'src/status.py').write_text('def normalize_status(value):\\n    return str(value).strip().upper()\\n')\n"
            "else:\n"
            " (root/'src/report.py').write_text('from status import normalize_status\\n\\ndef readiness_report(value):\\n    return f\\\"Readiness: {normalize_status(value)}\\\"\\n')\n"
            "p=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1])\n"
            "p.write_text(json.dumps({'status':'PATCH_PRODUCED','summary':'bounded PR62 change'}))\n",
            encoding="utf-8")
        codex_exec.chmod(0o700)
        repo_ref = "repo://riverview/pr62-disposable-acceptance"
        codex_home = self.root / "pr62-codex-home"
        workspace = self.root / "pr62-workspaces"
        codex_artifacts = self.root / "pr62-patch-artifacts"
        for directory in (codex_home, workspace, codex_artifacts):
            directory.mkdir(mode=0o700)
        base = CodexCLIExecutionAdapter(executable=str(codex_exec), repository_path=target,
            repository_reference=repo_ref, codex_home=codex_home,
            workspace_root=workspace, artifact_root=codex_artifacts)
        source_adapter = CodexSourceChangeAdapter(base_adapter=base,
            repository_reference=repo_ref,
            authorized_paths=("src/status.py", "tests/test_status.py", "src/report.py",
                              "tests/test_report.py"), max_timeout_seconds=30)
        source_verifier = CodexSourceChangeVerifier(base_adapter=base,
            authorized_paths=source_adapter.authorized_paths, max_timeout_seconds=30)
        action = CodexSourceChangeWorkAction(self.pipeline, source_adapter, repo_ref,
                                             timeout_seconds=30)
        source_result_verifier = CodexSourceChangeResultVerifier(
            self.pipeline, source_verifier, action)

        source_id = "worker:source-test:" + uuid4().hex
        source_token = secrets.token_urlsafe(36)
        principal = "principal:" + source_id
        self.admin.execute(f'INSERT INTO "{self.schema}".institutional_principals '
            "(principal_id,principal_kind) VALUES (%s,'resident')", (principal,))
        self.admin.execute(f'INSERT INTO "{self.schema}".principal_credentials '
            "(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)",
            (uuid4(), principal, hashlib.sha256(source_token.encode()).digest()))
        for verb in ("worker.register", "assignment.execute"):
            self.admin.execute(f'INSERT INTO "{self.schema}".authority_grants '
                "(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) "
                "VALUES (%s,%s,%s,%s,%s,'rv.policy:grace-execution-test.v1')",
                (source_id + ":" + verb, principal, verb, self.scope, principal))
        source_db = PostgresWorkerAdapter(DSN, schema=self.schema)
        self.addCleanup(source_db.close)
        source_db.register_worker(source_id, [SOURCE_CAPABILITY], self.scope,
                                  credential=source_token)

        class VerifiedKnowledge:
            def ground_assignment(_self, _assignment):
                return KnowledgeResult(KnowledgeStatus.VERIFIED,
                    {"evidence": "separate resident knowledge fixture"},
                    ("repo://docs/verified.md",), self.commit, "c" * 64, True)
            reground_assignment = ground_assignment

        source_loop = ContinuousWorker(source_db, source_id, source_token,
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=action, action_effect_class="retry_safe",
            action_capability=SOURCE_CAPABILITY)
        artifact_root = self.root / "pr62-artifacts"
        artifact_loop = ContinuousWorker(self.adapter, self.worker_id,
            self.credentials["worker"], knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=BoundedLocalCodingWorker(self.pipeline, artifact_root),
            action_effect_class="retry_safe", action_capability="engineering.bounded-artifact.v1")

        class ResultPublisher:
            def __init__(self): self.cycles = []
            def __call__(self, context):
                cycle = context["completion_cycle"]
                self.cycles.append(cycle)
                return {"status":"published", "request_id":f"test-result:{cycle}",
                    "provider_id":"provider:test", "served_model":"model:test",
                    "implementation_id":"implementation:test",
                    "review_decision":("OBJECTIVE_COMPLETE" if cycle == 2 else
                                        "ENGINEERING_STEP_PROPOSED"),
                    "completion_cycle":str(cycle)}
        publisher = ResultPublisher()
        service = GraceExecutionService(self.pipeline, self.adapter, artifact_loop,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=artifact_root,
            execution_capability="engineering.bounded-artifact.v1",
            execution_workers={"engineering.bounded-artifact.v1":artifact_loop,
                               SOURCE_CAPABILITY:source_loop},
            verifiers={"engineering.bounded-artifact.v1":BoundedArtifactVerifier(artifact_root, self.pipeline),
                       SOURCE_CAPABILITY:source_result_verifier},
            conversation_result_publisher=publisher)

        objective_id = "objective:pr62-source-cycle:" + uuid4().hex
        criteria = ('normalize_status(" ready ") == "READY"',
                    'readiness_report(" ready ") == "Readiness: READY"')
        scope_text = (f"In {repo_ref} at commit {pinned}, change only src/status.py, "
            "tests/test_status.py, src/report.py, and tests/test_report.py. "
            "normalize_status(\" ready \") must equal \"READY\" and "
            "readiness_report(\" ready \") must equal \"Readiness: READY\".")
        self.pipeline.knowledge = VerifiedKnowledge()
        self.pipeline.submit_objective(objective_id, scope_text, criteria,
            credential=self.credentials["steward"], scope_ref=self.scope,
            origin={"conversation_id":str(uuid4()), "source_sequence":1})
        self.pipeline.ground_objective(objective_id)
        first = PlanStep("step1", "Step 1: normalize_status trims and uppercases input.",
            (criteria[0],), execution_capability=SOURCE_CAPABILITY,
            authorized_paths=("src/status.py", "tests/test_status.py"),
            test_targets=("tests/test_status.py",), repository_reference=repo_ref,
            repository_revision=pinned)
        second = PlanStep("step2", "Step 2: readiness_report returns the normalized report.",
            (criteria[1],), depends_on=("step1",), execution_capability=SOURCE_CAPABILITY,
            authorized_paths=("src/report.py", "tests/test_report.py"),
            test_targets=("tests/test_report.py",), repository_reference=repo_ref,
            repository_revision=pinned)
        self.pipeline.record_proposal(objective_id, PlanProposal("Normalize status and report",
            (first, second), 0))
        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        first_assignment = self.pipeline.get_objective(objective_id)["assignment_id"]
        with self.assertRaises(ObjectiveStateError):
            self.pipeline.authorize_and_dispatch(objective_id,
                "assignment:pr62:premature:" + uuid4().hex,
                credential=self.credentials["steward"], authority_ref=self.scope,
                idempotency_key="pr62-premature:" + uuid4().hex, step_id="step2")
        self.assertIsNone(self.pipeline.dispatchable_step(objective_id))
        self.ledger.transition(first_assignment, "ready", "event_processor_ready",
            "pr62-ready:" + first_assignment, actor_id="event-processor")
        first_outcome = source_loop.run_once(assignment_id=first_assignment)
        self.assertEqual(first_outcome["status"], "AWAITING_VERIFICATION", first_outcome)
        first_result = self.admin.execute(f'SELECT result FROM "{self.schema}".worker_results '
            "WHERE attempt_id=%s", (first_outcome["attempt_id"],)).fetchone()[0]
        self.assertEqual(first_result["repository_reference"], repo_ref)
        self.assertEqual(first_result["repository_revision"], pinned)
        self.assertTrue(service.verify_one(first_assignment))
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 1)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "WORK_ORDER_CREATED")
        first_decision = self.admin.execute(f'SELECT decision FROM "{self.schema}".verification_records '
            "WHERE assignment_id=%s", (first_assignment,)).fetchone()[0]
        self.assertEqual(first_decision, "ACCEPTED")
        self.assertEqual(self.pipeline.dispatchable_step(objective_id)["step_id"], "step2")
        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        second_assignment = self.pipeline.get_objective(objective_id)["assignment_id"]
        self.assertNotEqual(second_assignment, first_assignment)
        self.assertEqual(service.dispatch_proposed(objective_id), 0)
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(publisher.cycles, [1])
        self.ledger.transition(second_assignment, "ready", "event_processor_ready",
            "pr62-ready:" + second_assignment, actor_id="event-processor")
        # Reconstruct the source worker and Grace service after the assignment is
        # durable and ready, as systemd would after an owner-session restart.
        restarted_source_db = PostgresWorkerAdapter(DSN, schema=self.schema)
        self.addCleanup(restarted_source_db.close)
        restarted_source_loop = ContinuousWorker(restarted_source_db, source_id, source_token,
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit), action=action,
            action_effect_class="retry_safe", action_capability=SOURCE_CAPABILITY)
        service = GraceExecutionService(self.pipeline, self.adapter, artifact_loop,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=artifact_root,
            execution_capability="engineering.bounded-artifact.v1",
            execution_workers={"engineering.bounded-artifact.v1":artifact_loop,
                               SOURCE_CAPABILITY:restarted_source_loop},
            verifiers={"engineering.bounded-artifact.v1":BoundedArtifactVerifier(artifact_root, self.pipeline),
                       SOURCE_CAPABILITY:source_result_verifier},
            conversation_result_publisher=publisher)
        self.assertEqual(service.dispatch_proposed(objective_id), 0,
                         "restart must not create a duplicate assignment")
        self.assertEqual(service.publish_conversation_results(), 0,
                         "restart must not republish the acknowledged first-step result")
        self.assertEqual(publisher.cycles, [1])
        second_outcome = restarted_source_loop.run_once(assignment_id=second_assignment)
        self.assertEqual(second_outcome["status"], "AWAITING_VERIFICATION")
        second_result = self.admin.execute(f'SELECT result FROM "{self.schema}".worker_results '
            "WHERE attempt_id=%s", (second_outcome["attempt_id"],)).fetchone()[0]
        self.assertEqual(second_result["repository_reference"], repo_ref)
        self.assertEqual(second_result["repository_revision"], pinned)
        self.assertTrue(service.verify_one(second_assignment))
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 1)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "WORK_ORDER_CREATED")

        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 1)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "COMPLETED")
        self.assertEqual(service.publish_conversation_results(), 0)
        self.assertEqual(publisher.cycles, [1, 2])
        self.assertEqual(restarted_source_loop.run_once(assignment_id=second_assignment)["status"],
                         "IDLE")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=ANY(%s)",
                        ([first_assignment, second_assignment],))
            self.assertEqual(cur.fetchone()["n"], 2)
            cur.execute("SELECT count(*) AS n FROM verification_records WHERE assignment_id=ANY(%s) "
                        "AND decision='ACCEPTED'", ([first_assignment, second_assignment],))
            self.assertEqual(cur.fetchone()["n"], 2)
        events = self.pipeline.objective_events(objective_id)
        self.assertEqual(sum(event["event_type"] == "work_order.dispatched" for event in events), 2)
        self.assertEqual(sum(event["event_type"] == "conversation.result_published" for event in events), 2)
        self.assertEqual(sum(event["event_type"] == "objective.completed" for event in events), 1)
        final_event = next(event for event in events if event["event_type"] == "objective.completed")
        self.assertEqual(final_event["payload"]["artifact"]["repository_reference"], repo_ref)
        self.assertEqual(final_event["payload"]["artifact"]["repository_revision"], pinned)


    def test_rereview_key_collision_across_objectives_fails_closed(self):
        from riverview_core.resident_execution import ObjectiveStateError

        objective_id = "objective:rereview-key-owner"
        other_id = "objective:rereview-key-other"
        origin = {"conversation_id": str(uuid4()), "source_sequence": 1}
        for candidate in (objective_id, other_id):
            self.pipeline.submit_objective(candidate, "Review accepted evidence",
                ["the accepted result remains within scope"], credential=self.credentials["steward"],
                scope_ref=self.scope, origin=origin)
        self.admin.execute(f'UPDATE "{self.schema}".grace_objectives '
            "SET status='WORK_ORDER_CREATED',assignment_id=%s WHERE objective_id=%s",
            ("assignment:" + objective_id, objective_id))
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                self.pipeline._event(cur, objective_id, "execution.step_verified",
                    "verified:" + objective_id, "verifier:test", {
                        "assignment_id":"assignment:" + objective_id,
                        "completion_cycle":1, "decision":"ACCEPTED"})
                self.pipeline._event(cur, objective_id, "conversation.result_published",
                    "published:" + objective_id, "office:grace", {
                        "completion_cycle":1, "review_generation":1})
                foreign_key = "global-rereview-key:" + uuid4().hex
                self.pipeline._event(cur, other_id, "objective.test_key_reserved",
                    foreign_key, "steward:test", {"owner":other_id})
        with self.assertRaisesRegex(ObjectiveStateError, "another objective"):
            self.pipeline.request_conversation_result_rereview(objective_id, 1,
                evidence_revision="new-evidence-revision", evidence=["bounded new evidence"],
                credential=self.credentials["steward"], idempotency_key=foreign_key)

    def test_pending_rereview_is_not_starved_by_older_published_objectives(self):
        old_ids = ["objective:reviewed-prefix:" + str(index) for index in range(2)]
        pending_id = "objective:review-pending-after-prefix"
        origin = {"conversation_id": str(uuid4()), "source_sequence": 1}
        for objective_id in old_ids + [pending_id]:
            self.pipeline.submit_objective(objective_id, "Review accepted evidence",
                ["the accepted result remains within scope"], credential=self.credentials["steward"],
                scope_ref=self.scope, origin=origin)
            assignment_id = "assignment:" + objective_id
            self.admin.execute(f'UPDATE "{self.schema}".grace_objectives '
                "SET status='WORK_ORDER_CREATED',assignment_id=%s WHERE objective_id=%s",
                (assignment_id, objective_id))
            with self.ledger.db.transaction():
                with self.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    self.pipeline._event(cur, objective_id, "execution.step_verified",
                        "verified:" + objective_id, "verifier:test", {
                            "assignment_id":assignment_id, "completion_cycle":1,
                            "decision":"ACCEPTED"})
                    self.pipeline._event(cur, objective_id, "conversation.result_published",
                        "published:" + objective_id, "office:grace", {
                            "completion_cycle":1, "review_generation":1})
                    if objective_id == pending_id:
                        evidence = ["new durable evidence"]
                        revision = "batch-review-revision"
                        digest = hashlib.sha256(json.dumps({"evidence_revision":revision,
                            "evidence":evidence}, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")).encode()).hexdigest()
                        self.pipeline._event(cur, objective_id,
                            "conversation.result_review_requested", "request:" + objective_id,
                            "steward:test", {"completion_cycle":1,"review_generation":2,
                                "evidence_revision":revision,"evidence":evidence,
                                "evidence_sha256":digest})
        due = self.pipeline.pending_conversation_results(limit=1)
        self.assertEqual([row["objective_id"] for row in due], [pending_id])
        self.assertEqual(due[0]["review_generation"], 2)
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
        self.pipeline.submit_objective(objective_id,
            "document worker provenance verification at evidence/provenance.json",
                                       ["record verified repository provenance"],
                                       credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal("Record provenance", (
            PlanStep("provenance", "Write bounded work evidence",
                     ("record verified repository provenance",), artifact_requirements=(
                ArtifactRequirement("provenance", "evidence/provenance.json", "application/json",
                    ("record verified repository provenance",)),)),), 0))
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
        self.pipeline.submit_objective(objective_id,
            "document worker provenance verification at evidence/cancel.json",
                                       ["record verified repository provenance"],
                                       credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal("Cancel test", (
            PlanStep("cancel", "Write bounded work evidence",
                     ("record verified repository provenance",), artifact_requirements=(
                ArtifactRequirement("cancellation-proof", "evidence/cancel.json", "application/json",
                    ("record verified repository provenance",)),)),), 0))
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
        class StewardAccountAuth:
            def authenticate(self, credential, *, csrf_token, state_changing):
                if credential != "test-account-session":
                    from riverview_core.account_auth import AuthDenied
                    raise AuthDenied("session denied")
                return {"roles": ["steward"], "authority_principal_id": "steward:camrui"}
            def status(self):
                return {"status": "available"}

        server._account_auth_service = StewardAccountAuth()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def request(method, path, payload=None, *, authority=None, account_session=False):
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            headers = {"Authorization": "Bearer " + dashboard_token}
            if payload is not None:
                headers["Content-Type"] = "application/json"
                headers["Content-Length"] = str(len(payload))
            if authority:
                headers["X-Riverview-Authority"] = authority
            if account_session:
                headers["Cookie"] = "rv_account_session=test-account-session"
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            result = (response.status, json.loads(response.read() or b"{}"))
            conn.close()
            return result

        objective_id = "objective:persistent-service"
        body = json.dumps({"objective_id": objective_id,
            "request": "Record verified repository provenance in the bounded work product at reports/proof.json",
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
                    "artifact_requirements": [{"name": "proof", "path": "reports/proof.json",
                        "media_type": "application/json", "acceptance_criteria": [
                            "artifact records verified repository provenance"], "max_bytes": 32768}],
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
            projected_status, projected = request("GET", f"/api/v1/objectives/{objective_id}",
                                                  account_session=True)
            self.assertEqual(projected_status, 200)
            self.assertEqual(projected["status"], "COMPLETED")
            self.assertEqual(projected["assignment_state"], "completed")
            self.assertEqual(projected["verification"]["decision"], "ACCEPTED")
            self.assertTrue(projected["artifact"]["sha256"])

            # The operator-facing route must use the exact objective.submit
            # bearer and only append a bounded rereview request. It never dispatches.
            self.pipeline.record_conversation_result_published(objective_id, {
                "request_id": str(uuid4()), "provider_id": "provider:test",
                "served_model": "model:test", "implementation_id": "implementation:test",
                "completion_cycle": "1", "review_decision": "ADDITIONAL_EVIDENCE_REQUIRED"})
            rereview_path = f"/api/v1/objectives/{objective_id}/result-rereview"
            rereview_data = {"completion_cycle": 1, "evidence_revision": "steward-evidence-rev-1",
                "evidence": ["Steward supplied one new, bounded evidence item."],
                "idempotency_key": "grace-rereview:" + objective_id + ":cycle-1:revision-1"}
            rereview_body = json.dumps(rereview_data, separators=(",", ":")).encode()
            denied_rereview, _ = request("POST", rereview_path, rereview_body,
                authority=secrets.token_urlsafe(36))
            self.assertEqual(denied_rereview, 403)
            authorized_rereview, rereview_receipt = request("POST", rereview_path,
                rereview_body, authority=self.credentials["steward"])
            self.assertEqual(authorized_rereview, 202)
            self.assertEqual(rereview_receipt["schema_version"], "rv.grace.result-review-request.v1")
            self.assertEqual(rereview_receipt["review_generation"], 2)
            self.assertFalse(rereview_receipt["reused"])
            replay_status, replay_receipt = request("POST", rereview_path,
                rereview_body, authority=self.credentials["steward"])
            self.assertEqual(replay_status, 202)
            self.assertTrue(replay_receipt["reused"])
            changed_data = {**rereview_data,
                "evidence": ["Changed content cannot reuse the same idempotency key."]}
            changed_status, _ = request("POST", rereview_path,
                json.dumps(changed_data, separators=(",", ":")).encode(),
                authority=self.credentials["steward"])
            self.assertEqual(changed_status, 409)
            self.assertIsNone(self.pipeline.dispatchable_step(objective_id))
            self.assertEqual(self.pipeline.get_objective(objective_id)["assignment_id"], assignment_id)
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
            workflow_id="engineering.retry-limit-test.v1", workflow_step="test",
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
            outcomes = recovery.reconcile_expired(scope_ref=self.scope, worker_id=self.worker_id)
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
                "record independently checked repository provenance at reports/work-proof.json",
                ["artifact includes the requested work and provenance"],
                credential=self.credentials["steward"], scope_ref=self.scope)
            self.pipeline.ground_objective(objective_id)
            self.pipeline.record_proposal(objective_id, PlanProposal("Verify bounded artifact", (
                PlanStep("artifact", "Create a bounded work product",
                         ("artifact includes the requested work and provenance",), artifact_requirements=(
                             ArtifactRequirement("work-proof", "reports/work-proof.json", "application/json",
                                 ("artifact includes the requested work and provenance",)),)),), 0))
            objectives.append(objective_id)

        failing_id = {"value": None}
        delegate = BoundedArtifactVerifier(self.root / "isolation-artifacts", self.pipeline)
        class IsolatedVerifier:
            REVISION = "isolated-test-verifier-1"
            def verify(self, assignment, attempt, result):
                if failing_id["value"] is None:
                    failing_id["value"] = assignment["id"]
                    raise RuntimeError("isolated verifier fixture failure")
                if assignment["id"] == failing_id["value"]:
                    raise RuntimeError("isolated verifier fixture failure")
                decision = delegate.verify(assignment, attempt, result)
                return type(decision)(decision.status, decision.criteria,
                    decision.evidence_references, self.REVISION, decision.summary)

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
            "record a repeatable verified repository work product at results/continuous.json",
                ["artifact records the requested task and source provenance"],
                credential=self.credentials["steward"], scope_ref=self.scope)
            self.pipeline.ground_objective(objective_id)
            self.pipeline.record_proposal(objective_id, PlanProposal("Create work product", (
                PlanStep("artifact", "Write the bounded engineering work product",
                    ("artifact records the requested task and source provenance",), artifact_requirements=(
                        ArtifactRequirement("continuous-proof", "results/continuous.json", "application/json",
                            ("artifact records the requested task and source provenance",)),)),), 0))
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
            execution_id, "record a bounded engineering result at results/fair-cycle.json", criteria,
            credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(execution_id)
        self.pipeline.record_proposal(execution_id, PlanProposal(
            "Create bounded engineering result", (PlanStep(
                "artifact", "Write the bounded engineering work product", tuple(criteria),
                artifact_requirements=(ArtifactRequirement("fair-cycle-result", "results/fair-cycle.json",
                    "application/json", tuple(criteria)),)),), 0))

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
            "create a provenance-bound bounded work product at evidence/restart.json",
            ["artifact includes its source revision and request"],
            credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id, PlanProposal("Create work product", (
            PlanStep("artifact", "Write the bounded work product",
                ("artifact includes its source revision and request",), artifact_requirements=(
                    ArtifactRequirement("restart-proof", "evidence/restart.json", "application/json",
                        ("artifact includes its source revision and request",)),)),), 0))
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
