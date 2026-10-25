# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_execution.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.88
# Changed: 2026-10-25 UTC | RV-AGREED-AUTONOMY-POLICY-20261025 | Assert interrupted one-shot recovery is terminalized and never replayed.
# Changed: 2026-10-25 UTC | RV-AGREED-AUTONOMY-POLICY-20261025 | Prove local recovery cannot spend externally and interrupted one-shot reasoning is never replayed.
# Changed: 2026-10-25 UTC | RV-AGREED-AUTONOMY-POLICY-20261025 | Verify one exact local criteria-binding recovery supersedes, but preserves, the pending Steward request.
# Changed: 2026-10-25 UTC | RV-ISSUE310-VERIFIER-PUBLICATION-20261025 | Use a supported exact-literal criterion in late-artifact verifier recovery and record verifier 1.0.5.
# Changed: 2026-10-25 UTC | RV-GRACE-S5-EVIDENCE-RETRY-20261025 | Cover a legitimately consumed S5 CME-recovery evaluation as runtime evidence for same-assignment rework.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-EVAL-TRIGGER-20261025 | Exercise S4 rejection-trigger evaluation provenance and remove the historical S3 request pin from the one-use exception path.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-REPLAY-CORRELATION-20261025 | Verify historical S3 event persistence after pointer advancement and reject cross-objective assignment references.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-EVIDENCE-RECOVERY-20261025 | Exercise exact consumed Luna exchange provenance and evaluation lifecycle evidence through PostgreSQL.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-REWORK-EXCEPTION-20261025 | Fix the integration fixture's explicit service import for concurrent admission coverage.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-REWORK-EXCEPTION-20261025 | Exercise exact S4 single-use exception issuance and concurrent atomic consumption without resetting prior rework attempts.
# Changed: 2026-10-25 UTC | RV-GRACE-REWORK-CONTROLLER-AUTHORITY-20261024 | Prove persisted authorization stops are checked against the active exact grant without another re-review.
# Changed: 2026-10-24 UTC | RV-GRACE-REWORK-AUTHORITY-EVIDENCE-20261024 | Verify re-review evidence carries exact active Luna grant scope and bounded prior request attempt facts.
# Changed: 2026-10-23 UTC | RV-GRACE-APPROVED-PROMOTION-LIFECYCLE-BINDING-20261023 | Bind the exact approved promotion criterion only to matching durable proposal and objective evidence.
# Changed: 2026-10-23 UTC | RV-GRACE-CRITERIA-BINDING-DIAGNOSTICS-20261023 | Verify safe per-index mismatch diagnostics exclude proposal text.
# Changed: 2026-10-23 UTC | RV-GRACE-CRITERIA-BINDING-RECOVERY-20261023 | Verify single-step recovery preserves every exact Steward acceptance criterion and rejects ambiguous scopes.
# Changed: 2026-10-23 UTC | RV-WORKER-HEALTH-SNAPSHOT-20261023 | Verify Grace persists the exact configured worker capability set.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Verify Grace selects ComfyUI only when the explicitly keyed worker exists.
# Changed: 2026-10-23 UTC | RV-DASHBOARD-GROUNDED-OBJECTIVE-CANCEL-20261023 | Preserve cancellation authorization, audit, idempotency, queue exclusion, and active-work protection tests.
# Changed: 2026-10-22 UTC | RV-GRACE-DURABLE-COMPLETION-001 | Prove four-step verified completion recovers after restart and ignores conversational review disagreement.
# Changed: 2026-10-22 UTC | RV-W4-PR216-REVIEW-FOLLOWUP | Verify concurrent grounding failures serialize into distinct durable attempts and duplicate attempt replay is a no-op.
# Changed: 2026-10-22 UTC | RV-W4-GRACE-ACTIONABLE-DIAGNOSTICS-20261022 | Cover durable sanitized grounding failure codes, persistence, exception redaction, and retry history.
# Changed: 2026-10-22 UTC | RV-W4-GRACE-ARTIFACT-STEP-CRITERIA-20261022-R1 | Align the database regression fixture with available repository grounding terms.
# Changed: 2026-10-22 UTC | RV-W4-GRACE-ARTIFACT-STEP-CRITERIA-20261022 | Verify artifact checks remain separate from exact formal-criteria coverage.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-TRIGGER-PRIVILEGE-FIX | Verify the audited criteria guard reads only fields granted to the runtime role and takes no forbidden row lock.
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
# ======================================================================"""Model-independent integration test of Grace objective execution."""

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
from unittest.mock import patch

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

    def test_comfyui_proposal_requires_an_explicitly_configured_capability_worker(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        class Worker:
            def run_once(self, **_kwargs): return {"status": "IDLE"}
        class Verifier:
            REVISION = "fixture-v1"
            def verify(self, *_args): return None
        comfy = "engineering.comfyui-image.v1"
        artifact = "engineering.codex-cli-artifact.v1"
        workers = {artifact: Worker(), comfy: Worker()}
        service = GraceExecutionService(None, None, workers[artifact],
            dispatch_credential="dispatch", authority_ref="work-order:test",
            verifier_id="verifier", verifier_credential="verify", artifact_root="/tmp/unused",
            execution_capability=artifact, execution_workers=workers,
            verifiers={artifact: Verifier(), comfy: Verifier()})
        self.assertEqual(service._proposal_worker_capability({"execution_capability": comfy}), comfy)
        service_without_comfy = GraceExecutionService(None, None, workers[artifact],
            dispatch_credential="dispatch", authority_ref="work-order:test",
            verifier_id="verifier", verifier_credential="verify", artifact_root="/tmp/unused")
        self.assertIsNone(service_without_comfy._proposal_worker_capability(
            {"execution_capability": comfy}))

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
    def test_artifact_path_fence_suppresses_again_after_service_reconstruction(self):
        from types import SimpleNamespace
        from riverview_core.resident_execution.service import GraceExecutionService

        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, query, params):
                self.query, self.params = query, params
            def fetchone(self): return {"blocked": True}

        class DB:
            def __init__(self): self.value = Cursor()
            def cursor(self): return self.value

        class Reasoner:
            providers = {"provider.test": object()}
            office_id = "office:test"
            calls = 0
            def propose(self, *_args, **_kwargs):
                self.calls += 1
                raise AssertionError("durably fenced objective must not be reasoned again")

        pipeline = SimpleNamespace(
            ledger=SimpleNamespace(db=DB(), _set_search_path=lambda _cur: None),
            grounded_objectives=lambda **_kwargs: [{
                "objective_id": "objective:artifact-path-fence:r2", "revision": 2}],
        )

        def restarted_service():
            service = object.__new__(GraceExecutionService)
            service.pipeline = pipeline
            service.resident_reasoner = Reasoner()
            service.authority_ref = "work-order:test"
            service.external_reasoning_exchange = None
            service._claim_approved_recovery = lambda *_args: None
            service._claim_experiment_recovery = lambda *_args: None
            service._reasoning_failure_count = lambda *_args: self.fail(
                "terminal revision fence should be checked before retry counters")
            return service

        first = restarted_service()
        self.assertFalse(first.reason_one_grounded_objective())
        second = restarted_service()
        self.assertFalse(second.reason_one_grounded_objective())
        self.assertEqual(first.resident_reasoner.calls, 0)
        self.assertEqual(second.resident_reasoner.calls, 0)
        query = pipeline.ledger.db.value.query
        self.assertIn("payload->>'objective_revision' IS NULL", query)
        self.assertIn("event_type='objective.grounded'", query)
        self.assertEqual(set(pipeline.ledger.db.value.params[1]), {
            "PROPOSAL_CRITERIA_BINDING_REJECTED",
            "PROPOSAL_ARTIFACT_PATH_UNAUTHORIZED",
        })
        self.assertEqual(pipeline.ledger.db.value.params[2:], ("2", "objective:artifact-path-fence:r2"))

    def test_revision_failure_fence_survives_immutable_release_change(self):
        from types import SimpleNamespace
        from riverview_core.resident_execution.service import GraceExecutionService

        class Cursor:
            row = {"blocked": True}
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, query, params):
                self.query, self.params = query, params
            def fetchone(self): return self.row

        class DB:
            def __init__(self): self.cursor_value = Cursor()
            def cursor(self): return self.cursor_value

        class Ledger:
            def __init__(self): self.db = DB()
            def _set_search_path(self, _cursor): pass

        service = object.__new__(GraceExecutionService)
        service.pipeline = SimpleNamespace(ledger=Ledger())
        self.assertTrue(service._proposal_rejection_blocked("objective:test:r2", 2))
        query = service.pipeline.ledger.db.cursor_value.query
        self.assertNotIn("runtime_revision", query)
        self.assertEqual(service.pipeline.ledger.db.cursor_value.params[0],
                         "objective:test:r2")
        self.assertIn("PROPOSAL_ARTIFACT_PATH_UNAUTHORIZED",
                      service.pipeline.ledger.db.cursor_value.params[1])

    def test_recorded_objective_criteria_have_one_lifecycle_binding_in_offline_fixture(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.resident_reasoning import PlanProposal, PlanStep, lifecycle_evidence_event

        criteria = (
            "An eligible disposable diagnostic objective is promoted only following explicit Steward approval of the exact proposal revision and digest.",
            "Exactly one bounded diagnostic work order is formed and queued under the existing assignment.create and execution authorization checks.",
            "Grace processes the approved objective using its configured local reasoning model and records reasoning state transitions.",
            "Exactly one authorized GPT-6 Luna advisory escalation is issued through the durable external reasoning exchange, with no uncontrolled retries.",
            "The Luna request and response are durably correlated to the objective, with actual token usage and cost recorded.",
            "Grace durably consumes the Luna advisory response without treating it as approval or execution authority.",
            "The objective shows an observable post-consumption state transition or a precise durable failure reason.",
            "CLI-accessible diagnostic evidence identifies objective, authorization, reasoning, exchange, consumption, and outcome without disclosing protected credentials.",
        )
        self.assertEqual(lifecycle_evidence_event(criteria[0]), "proposal.approved_and_promoted")
        self.assertTrue(all(lifecycle_evidence_event(item) is None for item in criteria[1:]))
        plan = PlanProposal("Bounded diagnostic plan", (
            PlanStep("form", "Form bounded diagnostic work", (criteria[1],)),
            PlanStep("process", "Process the objective", (criteria[2],)),
            PlanStep("escalate", "Request bounded Luna advice", (criteria[3], criteria[4])),
            PlanStep("consume", "Consume and inspect the advisory", (criteria[5], criteria[6], criteria[7])),
        ), 128)
        diagnostic = GraceExecutionService._criteria_binding_diagnostics(plan, criteria)
        self.assertEqual(diagnostic["missing_approved_criterion_indices"], [1])
        corrected = PlanProposal(plan.summary, plan.steps, plan.tokens_used,
            system_owned_criteria=(criteria[0],))
        corrected_diagnostic = GraceExecutionService._criteria_binding_diagnostics(
            corrected, criteria)
        self.assertEqual(corrected_diagnostic["missing_approved_criterion_indices"], [])
        self.assertEqual(corrected_diagnostic["invalid_system_owned_criterion_indices"], [])

    def test_incomplete_acceptance_proposal_has_safe_detail_code(self):
        from riverview_core.resident_execution.service import GraceExecutionService

        error = ObjectiveStateError("proposal omits one or more human acceptance criteria")
        self.assertEqual(GraceExecutionService._reasoning_failure_detail_code(error),
                         "PROPOSAL_OMITS_ACCEPTANCE_CRITERIA")
        self.assertEqual(GraceExecutionService._reasoning_failure_detail_code(
            ObjectiveStateError(
                "proposal must bind every original criterion to an Engineering step or a supported lifecycle event")),
            "PROPOSAL_CRITERIA_BINDING_REJECTED")
        self.assertEqual(GraceExecutionService._reasoning_failure_detail_code(
            ObjectiveStateError("approved-promotion lifecycle evidence is not durably bound")),
            "PROPOSAL_LIFECYCLE_EVIDENCE_UNBOUND")
        self.assertEqual(GraceExecutionService._reasoning_failure_detail_code(
            RuntimeError("untrusted provider message")), "REASONING_CYCLE_FAILED")
        self.assertEqual(GraceExecutionService._reasoning_failure_detail_code(
            ObjectiveStateError("untrusted provider message")), "REASONING_CYCLE_FAILED")

    def test_single_step_recovery_binds_exact_steward_criteria_without_widening_scope(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.resident_reasoning import PlanProposal, PlanStep
        criteria = ["Verify one bounded Luna request.",
                    "Confirm Grace consumes the correlated response."]
        original = PlanProposal("Run bounded diagnostics", (
            PlanStep("diagnostic", "Verify one bounded diagnostic", (criteria[0],)),), 12)
        repaired = GraceExecutionService._restore_exact_single_step_criteria(original, {
            "acceptance_criteria_source": "steward_supplied",
            "acceptance_criteria": criteria,
        })
        self.assertEqual(repaired.summary, original.summary)
        self.assertEqual(len(repaired.steps), 1)
        self.assertEqual(repaired.steps[0].objective, original.steps[0].objective)
        self.assertEqual(repaired.steps[0].execution_capability,
                         original.steps[0].execution_capability)
        self.assertEqual(repaired.steps[0].acceptance_criteria, tuple(criteria))
        self.assertEqual(GraceExecutionService._restore_exact_single_step_criteria(
            original, {"acceptance_criteria_source": "grace_derived",
                      "acceptance_criteria": criteria}), None)
        multiple = PlanProposal("Two steps", (original.steps[0],
            PlanStep("diagnostic-2", "Check diagnostics", (criteria[1],))), 12)
        self.assertIsNone(GraceExecutionService._restore_exact_single_step_criteria(
            multiple, {"acceptance_criteria_source": "steward_supplied",
                      "acceptance_criteria": criteria}))

    def test_criteria_binding_diagnostic_identifies_missing_approved_indices_only(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.resident_reasoning import PlanProposal, PlanStep
        criteria = ["First approved check.", "Second approved check.",
                    "Third approved check."]
        plan = PlanProposal("Check two items", (PlanStep("check", "Check approved items",
            (criteria[0], "Invented extra requirement")),), 8)
        diagnostic = GraceExecutionService._criteria_binding_diagnostics(plan, criteria)
        self.assertEqual(diagnostic["missing_approved_criterion_indices"], [2, 3])
        self.assertEqual(diagnostic["supplemental_step_criterion_count"], 1)
        self.assertEqual(diagnostic["unapproved_supplemental_criterion_count"], 1)
        self.assertIn("UNBOUND_APPROVED_CRITERIA", diagnostic["reason_codes"])
        self.assertNotIn("First approved check.", str(diagnostic))
        self.assertNotIn("Invented extra requirement", str(diagnostic))

class ProposalPromotionEvidenceBindingTests(unittest.TestCase):
    def test_promotion_binding_requires_exact_approved_revision_and_objective_link(self):
        import hashlib
        from uuid import NAMESPACE_URL, uuid5
        from riverview_core.resident_execution.pipeline import GraceExecutionPipeline, _json

        proposal_id, revision = "proposal:18ec0798-a441-494d-b45e-68cf99e72cd2", 2
        objective_id = ("objective:proposal:" + str(uuid5(NAMESPACE_URL,
            f"riverview:proposal-work-order:{proposal_id}:r{revision}")) + f":r{revision}")
        content = {"title": "t", "summary": "s", "objective": "o", "scope": "s",
                   "proposed_approach": "a", "constraints": [],
                   "acceptance_criteria": ["criterion"], "tags": []}
        digest = hashlib.sha256(_json(content).encode()).hexdigest()
        grant_id, approval_key = "grant:test", "approval:test"
        reference = {"proposal_id": proposal_id, "revision": revision,
            "content_sha256": digest, "approval_event_key": approval_key,
            "objective_submit_grant_id": grant_id}

        class Cursor:
            def __init__(self, rows): self.rows, self.index = rows, 0
            def execute(self, *_args): pass
            def fetchone(self):
                row = self.rows[self.index]
                self.index += 1
                return row

        def make_rows(approval_digest=digest, promoted_objective=objective_id):
            return [dict(current_revision=revision, proposal_status="APPROVED",
                         revision_status="APPROVED", **content),
                {"actor_id": "steward:confirmed",
                 "payload": {"to": "APPROVED", "content_sha256": approval_digest,
                             "authority_reference": "comms5-ingress:steward"}},
                {"actor_id": "steward:confirmed", "payload": {
                    "objective_id": promoted_objective, "content_sha256": digest,
                    "approval_event_key": approval_key,
                    "authority_reference": f"objective.submit-grant:{grant_id}"}}]

        pipeline = object.__new__(GraceExecutionPipeline)
        pipeline.objective_proposal_reference = lambda _objective_id: reference
        criterion = ("An eligible disposable diagnostic objective is promoted only following "
                     "explicit Steward approval of the exact proposal revision and digest.")
        self.assertTrue(pipeline.proposal_promotion_evidence(
            Cursor(make_rows()), objective_id, criterion))
        self.assertFalse(pipeline.proposal_promotion_evidence(
            Cursor(make_rows(approval_digest="0" * 64)), objective_id, criterion))
        self.assertFalse(pipeline.proposal_promotion_evidence(
            Cursor(make_rows(promoted_objective="objective:wrong")), objective_id, criterion))


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
        for component in ("assignment_scheduler", "worker_adapter", "cme",
                          "notifications", "institutional_authority", "resident_execution"):
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

    def test_grace_health_heartbeat_persists_live_worker_capabilities(self):
        from types import SimpleNamespace
        from riverview_core.resident_execution.service import GraceExecutionService

        class Verifier:
            def verify(self, *_args, **_kwargs):
                return None

        repository_worker = SimpleNamespace(worker_id=self.worker_id, run_once=lambda **_kwargs: {})
        comfy_worker = SimpleNamespace(worker_id=self.worker_id, run_once=lambda **_kwargs: {})
        verifier = Verifier()
        capabilities = {
            "engineering.codex-cli-artifact.v1": repository_worker,
            "engineering.comfyui-image.v1": comfy_worker,
        }
        service = GraceExecutionService(self.pipeline, self.adapter, repository_worker,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=self.root / "health-artifacts", execution_workers=capabilities,
            verifiers={key: verifier for key in capabilities})
        service._heartbeat("healthy")

        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT worker_capabilities FROM grace_execution_health "
                        "WHERE service_id='grace.execution.v1'")
            observed = cur.fetchone()["worker_capabilities"]
        self.assertEqual(observed, [
            {"worker_id": self.worker_id, "capability": "engineering.codex-cli-artifact.v1"},
            {"worker_id": self.worker_id, "capability": "engineering.comfyui-image.v1"},
        ])

    def _create_grounded_reasoning_objective(self, objective_id):
        row = self.pipeline.submit_objective(
            objective_id, "Document worker retry contract",
            ["artifact contains the task and verified repository provenance"],
            credential=self.credentials["steward"], scope_ref=self.scope)
        return self.pipeline.ground_objective(row["objective_id"])

    def test_criteria_binding_failure_gets_one_local_recovery_and_supersedes_pending_request(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id = "objective:auto-local-recovery:" + uuid4().hex
        grounded = self._create_grounded_reasoning_objective(objective_id)
        service = GraceExecutionService(self.pipeline,self.adapter,object(),
            dispatch_credential=self.credentials["steward"],authority_ref=self.scope,
            verifier_id=self.verifier_id,verifier_credential=self.credentials["verifier"],
            artifact_root=self.root/"auto-recovery",resident_reasoner=object())
        service._record_reasoning_failure(objective_id,failure_type="ObjectiveStateError",
            detail_code="PROPOSAL_CRITERIA_BINDING_REJECTED",
            blocked_revision=grounded["revision"],diagnostic_context={
                "missing_approved_criterion_indices":[1],"reason_codes":["criterion_unbound"]})

        source_event, notification_id = uuid4(), uuid4()
        self.admin.execute(f'''INSERT INTO "{self.schema}".cme_monitor_events
            (event_id,event_key,service_id,event_type,details)
            VALUES (%s,%s,'cme.monitor.v1','grace_objective_blocked',
             %s::jsonb)''',(source_event,"cme:"+str(source_event),json.dumps({
                "objective_id":objective_id,"objective_revision":grounded["revision"]})))
        self.admin.execute(f'''INSERT INTO "{self.schema}".attention_notifications
            (notification_id,source_event_id,event_type,summary_code,source_recorded_at)
            VALUES (%s,%s,'grace_objective_blocked','grace_objective_blocked',clock_timestamp())''',
            (notification_id,source_event))
        request_id=uuid4()
        self.admin.execute(f'''INSERT INTO "{self.schema}".grace_recovery_decision_requests
            (request_id,source_event_id,notification_id,objective_id,objective_revision,
             recovery_action,attempt_limit,expires_at)
            VALUES (%s,%s,%s,%s,%s,'retry_reasoning_once',1,clock_timestamp()+interval '1 hour')''',
            (request_id,source_event,notification_id,objective_id,grounded["revision"]))

        claim=service._claim_autonomous_local_recovery(objective_id,grounded["revision"])
        self.assertIsNotNone(claim)
        self.assertEqual(claim["missing_criterion_indices"],[1])
        resumed=service._claim_autonomous_local_recovery(objective_id,grounded["revision"])
        self.assertIsNone(resumed)
        attempt_events=[event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"]=="execution.reasoning_attempted"]
        self.assertEqual(len(attempt_events),1)
        interrupted=[event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"]=="execution.reasoning_failed" and
            event["payload"].get("detail_code")=="AUTONOMOUS_RECOVERY_INTERRUPTED"]
        self.assertEqual(len(interrupted),1)
        self.assertEqual(interrupted[0]["payload"]["recovery_event_id"],claim["event_id"])
        self.assertEqual(interrupted[0]["payload"]["action"],
                         "request_steward_review_without_replaying_reasoning")
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"],"GROUNDED")
        self.assertEqual(self.pipeline.get_objective(objective_id)["acceptance_criteria"],
                         grounded["acceptance_criteria"])
        request=self.admin.execute(f'''SELECT status FROM "{self.schema}".grace_recovery_decision_requests
            WHERE request_id=%s''',(request_id,)).fetchone()
        self.assertEqual(request[0],"superseded")
        decision=self.admin.execute(f'''SELECT decision,actor_principal_id,reason
            FROM "{self.schema}".grace_recovery_decision_events WHERE request_id=%s''',
            (request_id,)).fetchone()
        self.assertEqual(decision[0],"supersede")
        self.assertEqual(decision[1],"service:grace-execution")
        self.assertIn("one exact-scope local",decision[2])
        recovery=[event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"]=="execution.autonomous_recovery_authorized"]
        self.assertEqual(len(recovery),1)
        self.assertFalse(recovery[0]["payload"]["acceptance_criteria_changed"])
        self.assertFalse(recovery[0]["payload"]["external_provider_authorized"])

    def test_autonomous_local_recovery_rejects_other_failure_codes(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id="objective:auto-local-recovery-denied:"+uuid4().hex
        grounded=self._create_grounded_reasoning_objective(objective_id)
        service=GraceExecutionService(self.pipeline,self.adapter,object(),
            dispatch_credential=self.credentials["steward"],authority_ref=self.scope,
            verifier_id=self.verifier_id,verifier_credential=self.credentials["verifier"],
            artifact_root=self.root/"auto-recovery-denied",resident_reasoner=object())
        service._record_reasoning_failure(objective_id,failure_type="ProviderError",
            detail_code="PROVIDER_UNAVAILABLE",blocked_revision=grounded["revision"])
        self.assertIsNone(service._claim_autonomous_local_recovery(objective_id,grounded["revision"]))
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"],"GROUNDED")

    def test_owner_session_automatically_recovers_criteria_binding_failure_once(self):
        from types import SimpleNamespace
        from riverview_core.resident_reasoning import (ExternalEscalationIntent,
            PlanProposal, PlanStep, ReasoningResult, ReasoningStatus)
        objective_id="objective:auto-local-recovery-cycle:"+uuid4().hex
        grounded=self._create_grounded_reasoning_objective(objective_id)
        criterion=grounded["acceptance_criteria"][0]
        corrected=PlanProposal("Bind the approved criterion exactly",(
            PlanStep("document","Produce a bounded engineering record",(criterion,)),),0,
            external_escalation=ExternalEscalationIntent("task_complexity","provider.test"))

        class SequenceReasoner:
            office_id="office:grace-test"
            providers={"provider.test":object()}
            def __init__(inner_self):
                inner_self.requests=[]
            def propose(inner_self, requested_objective, **kwargs):
                self.assertEqual(requested_objective,objective_id)
                trigger=kwargs["trigger"]
                inner_self.requests.append(trigger)
                proposal=(PlanProposal("Omit the required criterion",(
                    PlanStep("document","Produce a bounded engineering record",
                        ("unsupported extra criterion",)),),0)
                    if len(inner_self.requests)==1 else corrected)
                return ReasoningResult(status=ReasoningStatus.PROPOSED,
                    request_id="criteria-request-"+str(len(inner_self.requests)),
                    detail_code="PROPOSAL_READY",provider_id="provider.test",
                    proposal=proposal,reasoning_request=SimpleNamespace(
                        request_id="criteria-request-"+str(len(inner_self.requests)),
                        assignment={"acceptance_criteria":grounded["acceptance_criteria"]}))

        reasoner=SequenceReasoner()
        service=self._reasoning_service(reasoner)
        service.request_external_reasoning=lambda *_args,**_kwargs: self.fail(
            "one-shot local recovery must not queue a paid provider request")
        self.assertFalse(service.reason_one_grounded_objective())
        failures=[event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"]=="execution.reasoning_failed"]
        self.assertEqual(len(failures),1)
        self.assertEqual(failures[0]["payload"]["detail_code"],
                         "PROPOSAL_CRITERIA_BINDING_REJECTED")
        self.assertTrue(service.reason_one_grounded_objective())
        self.assertEqual(reasoner.requests,["persistent_resident_cycle",
            "criteria_binding_recovery:1"])
        current=self.pipeline.get_objective(objective_id)
        self.assertEqual(current["status"],"PROPOSED")
        self.assertEqual(current["proposal"]["steps"][0]["acceptance_criteria"],[criterion])
        events=self.pipeline.objective_events(objective_id)
        self.assertEqual(sum(event["event_type"]=="execution.autonomous_recovery_authorized"
                             for event in events),1)
        self.assertEqual(sum(event["event_type"]=="execution.reasoning_attempted"
                             for event in events),2)
        self.assertEqual(sum(event["event_type"]=="work_order.proposed"
                             for event in events),1)
        suppressed=[event for event in events
            if event["event_type"]=="execution.external_escalation_suppressed"]
        self.assertEqual(len(suppressed),1)
        self.assertEqual(suppressed[0]["payload"]["reason_code"],
            "LOCAL_RECOVERY_HAS_NO_EXTERNAL_PROVIDER_AUTHORITY")

    def test_interrupted_one_shot_recovery_is_not_replayed_after_restart(self):
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id="objective:auto-local-recovery-interrupted:"+uuid4().hex
        grounded=self._create_grounded_reasoning_objective(objective_id)
        first=self._reasoning_service(object())
        first._record_reasoning_failure(objective_id,failure_type="ObjectiveStateError",
            detail_code="PROPOSAL_CRITERIA_BINDING_REJECTED",
            blocked_revision=grounded["revision"],diagnostic_context={
                "missing_approved_criterion_indices":[1],"reason_codes":["criterion_unbound"]})
        admitted=first._claim_autonomous_local_recovery(objective_id,grounded["revision"])
        self.assertIsNotNone(admitted)

        class MustNotRun:
            office_id="office:grace-test"
            providers={"provider.test":object()}
            calls=0
            def propose(inner_self,*_args,**_kwargs):
                inner_self.calls+=1
                raise AssertionError("persisted one-shot attempt must not be replayed")

        reasoner=MustNotRun()
        restarted=self._reasoning_service(reasoner)
        restarted._claim_approved_recovery=lambda *_args: None
        restarted._claim_experiment_recovery=lambda *_args: None
        self.assertFalse(restarted.reason_one_grounded_objective())
        self.assertEqual(reasoner.calls,0)
        events=self.pipeline.objective_events(objective_id)
        attempts=[event for event in events if event["event_type"]=="execution.reasoning_attempted"]
        holds=[event for event in events if event["event_type"]=="execution.reasoning_failed"
            and event["payload"].get("detail_code")=="AUTONOMOUS_RECOVERY_INTERRUPTED"]
        self.assertEqual(len(attempts),1)
        self.assertEqual(len(holds),1)

    def test_luna_acceptance_fixture_reproduces_and_repairs_only_index_one(self):
        from riverview_core.resident_reasoning import PlanProposal, PlanStep

        criteria = (
            "An eligible disposable diagnostic objective is promoted only following explicit Steward approval of the exact proposal revision and digest.",
            "Exactly one bounded diagnostic work order is formed and queued under the existing assignment.create and execution authorization checks.",
            "Grace processes the approved objective using its configured local reasoning model and records reasoning state transitions.",
            "Exactly one authorized GPT-6 Luna advisory escalation is issued through the durable external reasoning exchange, with no uncontrolled retries.",
            "The Luna request and response are durably correlated to the objective, with actual token usage and cost recorded.",
            "Grace durably consumes the Luna advisory response without treating it as approval or execution authority.",
            "The objective shows an observable post-consumption state transition or a precise durable failure reason.",
            "CLI-accessible diagnostic evidence identifies objective, authorization, reasoning, exchange, consumption, and outcome without disclosing protected credentials.",
        )
        objective_id = "objective:offline-luna-validator:" + uuid4().hex
        submitted = self.pipeline.submit_objective(objective_id,
            "Exercise the approved Grace/Luna diagnostic acceptance plan.", list(criteria),
            credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(submitted["objective_id"])
        proposal = PlanProposal("Bounded Luna acceptance work", (
            PlanStep("work-order", "Queue the authorized diagnostic work", (criteria[1],)),
            PlanStep("grace", "Process the existing objective locally", (criteria[2],)),
            PlanStep("exchange", "Issue and correlate one bounded Luna advisory",
                     (criteria[3], criteria[4])),
            PlanStep("consume", "Consume advice and record observable outcome",
                     (criteria[5], criteria[6], criteria[7])),
        ), 64)
        with self.assertRaisesRegex(ObjectiveStateError,
                "bind every original criterion to an Engineering step"):
            self.pipeline.record_proposal(submitted["objective_id"], proposal)

        corrected = PlanProposal(proposal.summary, proposal.steps, proposal.tokens_used,
            system_owned_criteria=(criteria[0],))
        with self.assertRaisesRegex(ObjectiveStateError,
                "approved-promotion lifecycle evidence is not durably bound"):
            self.pipeline.record_proposal(submitted["objective_id"], corrected)

        original_evidence_check = self.pipeline.proposal_promotion_evidence
        self.pipeline.proposal_promotion_evidence = lambda _cur, _objective, criterion: criterion == criteria[0]
        try:
            stored = self.pipeline.record_proposal(submitted["objective_id"], corrected)
        finally:
            self.pipeline.proposal_promotion_evidence = original_evidence_check
        self.assertEqual(stored["proposal"]["system_owned_criteria"], [criteria[0]])
        self.assertEqual(stored["acceptance_criteria"], list(criteria))

    def test_single_work_order_lifecycle_criterion_requires_one_step_and_one_dispatch(self):
        from riverview_core.resident_reasoning import ArtifactRequirement

        objective_id = "objective:single-work-order-contract"
        lifecycle = "- Create exactly one Engineering assignment for the report."
        deliverables = ["The first report is produced.", "The second report is produced."]
        self.pipeline.submit_objective(objective_id,
            "Create reports/first.txt and reports/second.txt.",
            [*deliverables, lifecycle], credential=self.credentials["steward"],
            scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        multiple_steps = PlanProposal("Produce both requested reports", (
            PlanStep("first", "Create the first report", (deliverables[0],),
                artifact_requirements=(ArtifactRequirement(
                    "first", "reports/first.txt", "text/plain", (deliverables[0],)),)),
            PlanStep("second", "Create the second report", (deliverables[1],),
                depends_on=("first",), artifact_requirements=(ArtifactRequirement(
                    "second", "reports/second.txt", "text/plain", (deliverables[1],)),)),
        ), 0, system_owned_criteria=(lifecycle,))
        with self.assertRaisesRegex(ObjectiveStateError, "bind every original criterion"):
            self.pipeline.record_proposal(objective_id, multiple_steps)

        single_objective_id = "objective:single-work-order-contract-valid"
        file_criterion = "reports/result.txt contains the requested text."
        self.pipeline.submit_objective(single_objective_id,
            "Create reports/result.txt with the requested text.",
            [file_criterion, lifecycle], credential=self.credentials["steward"],
            scope_ref=self.scope)
        self.pipeline.ground_objective(single_objective_id)
        single_step = PlanStep("report", "Create reports/result.txt", (file_criterion,),
            artifact_requirements=(ArtifactRequirement(
                "result", "reports/result.txt", "text/plain", (file_criterion,)),))
        single_proposal = PlanProposal("Produce the requested report", (single_step,), 0,
            system_owned_criteria=(lifecycle,))
        self.pipeline.record_proposal(single_objective_id, single_proposal)
        self.pipeline.authorize_and_dispatch(single_objective_id,
            "assignment:single-work-order-contract", credential=self.credentials["steward"],
            authority_ref=self.scope, idempotency_key="single-work-order-dispatch")
        with self.ledger.db.cursor() as cursor:
            self.ledger._set_search_path(cursor)
            evidence = self.pipeline._system_criterion_evidence(cursor,
                single_objective_id,
                {"system_owned_criteria": [lifecycle]}, "cycle-1")
        self.assertEqual(evidence[0]["event_keys"], [
            f"grace-work-order-dispatched:{single_objective_id}:report"])

        class Cursor:
            def __init__(self, rows):
                self.rows = rows

            def execute(self, query, params):
                self.query = query
                self.params = params

            def fetchall(self):
                return self.rows

        self.assertEqual(evidence[0]["evidence_event_type"],
                         "work_order.exactly_one_dispatched")
        with self.assertRaisesRegex(ObjectiveStateError, "exactly one dispatched"):
            self.pipeline._system_criterion_evidence(Cursor([
                {"idempotency_key": "dispatch:one", "assignment_id": "assignment:one"},
                {"idempotency_key": "dispatch:two", "assignment_id": "assignment:two"},
            ]), objective_id, {"system_owned_criteria": [lifecycle]}, "cycle-1")

    def _reasoning_service(self, reasoner):
        from riverview_core.resident_execution.service import GraceExecutionService

        return GraceExecutionService(
            self.pipeline, None, None, dispatch_credential="dispatch",
            authority_ref=self.scope, verifier_id=self.verifier_id,
            verifier_credential=self.credentials["verifier"],
            artifact_root=str(self.root), resident_reasoner=reasoner)

    def test_retry_fence_runtime_revision_is_pinned_at_service_construction(self):
        from riverview_core.resident_execution.service import GraceExecutionService

        first = "a" * 40
        with patch.object(GraceExecutionService, "_read_runtime_revision",
                          return_value=first) as read_revision:
            service = self._reasoning_service(None)
            self.assertEqual(service._runtime_revision(), first)
            read_revision.return_value = "b" * 40
            self.assertEqual(service._runtime_revision(), first)
            self.assertEqual(read_revision.call_count, 1)

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

    def test_artifact_path_terminal_failure_stays_fenced_after_service_restart(self):
        from types import SimpleNamespace

        objective_id = "objective:artifact-path-fence:" + uuid4().hex
        objective = self._create_grounded_reasoning_objective(objective_id)

        class CountingReasoner:
            office_id = "office:grace-test"
            providers = {"provider.test": object()}
            calls = []
            def propose(self, *_args, **_kwargs):
                self.calls.append(True)
                raise AssertionError("persisted terminal fence must suppress reasoning")

        first_service = self._reasoning_service(CountingReasoner())
        first_service._record_reasoning_failure(objective_id,
            failure_type="ObjectiveStateError",
            detail_code="PROPOSAL_ARTIFACT_PATH_UNAUTHORIZED")
        before = [event for event in self.pipeline.objective_events(objective_id)
                  if event["event_type"] == "execution.reasoning_attempted"]

        # Reconstruct the service over the same durable ledger, as after a process
        # restart or immutable release switch. No in-memory retry counter is shared.
        restarted = self._reasoning_service(CountingReasoner())
        # Keep this regression focused on the persisted failure fence, independent
        # of optional recovery tables absent from the base test migration set.
        restarted._claim_approved_recovery = lambda *_args: None
        restarted._claim_experiment_recovery = lambda *_args: None
        self.assertFalse(restarted.reason_one_grounded_objective())
        after = [event for event in self.pipeline.objective_events(objective_id)
                 if event["event_type"] == "execution.reasoning_attempted"]
        self.assertEqual(after, before)
        failures = [event for event in self.pipeline.objective_events(objective_id)
                    if event["event_type"] == "execution.reasoning_failed"]
        self.assertEqual(len(failures), 1)
        # Match the legacy production event: no BLOCKED marker or revision field.
        self.assertEqual(failures[0]["payload"]["status"], "UNAVAILABLE")
        self.assertNotIn("objective_revision", failures[0]["payload"])
        self.assertEqual(failures[0]["payload"]["detail_code"],
                         "PROPOSAL_ARTIFACT_PATH_UNAUTHORIZED")

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

    def test_reconciliation_guard_reads_only_runtime_selectable_audit_fields(self):
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT pg_get_functiondef(to_regprocedure(%s)) AS definition",
                (f"{self.schema}.guard_grace_derived_objective_criteria()",))
            definition = cur.fetchone()["definition"]
        self.assertIn("SELECT actor_id,payload FROM %I.grace_objective_events", definition)
        self.assertNotIn("FOR SHARE", definition)

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

    def test_cli_diagnostic_artifact_paths_are_objective_and_revision_bound(self):
        from riverview_core.resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep

        def objective_id():
            return f"objective:proposal:{uuid4()}:r2"

        criterion = (
            "CLI-accessible diagnostic evidence identifies objective, reasoning, and outcome.")
        valid_id = objective_id()
        valid_uuid = valid_id.split(":")[-2]
        valid = self.pipeline.submit_objective(valid_id,
            "Create one bounded diagnostic evidence artifact using the approved artifact workflow.",
            [criterion], credential=self.credentials["steward"], scope_ref=self.scope)
        grounded = self.pipeline.ground_objective(valid_id)
        self.assertEqual(grounded["revision"], 2)

        def proposal(requirements):
            return PlanProposal("Record bounded diagnostic evidence", (
                PlanStep("evidence", "Record the approved diagnostic evidence", (criterion,),
                    artifact_requirements=tuple(ArtifactRequirement(name, path,
                        "application/json", (criterion,)) for name, path in requirements)),), 0)

        invalid_id = objective_id()
        self.pipeline.submit_objective(invalid_id,
            "Create one bounded diagnostic evidence artifact using the approved artifact workflow.",
            [criterion], credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(invalid_id)
        with self.assertRaisesRegex(ObjectiveStateError, "artifact path is absent"):
            self.pipeline.record_proposal(invalid_id, proposal((
                ("evidence_log", f"diagnostics/evidence_{valid_uuid}_r2.json"),)))

        outputs = (("work_order_record", "work_order"),
                   ("reasoning_state_log", "reasoning_state"),
                   ("luna_request_record", "luna_request"),
                   ("luna_response_record", "luna_response"),
                   ("final_outcome_log", "final_outcome"))
        requirements = tuple((name,
            f"diagnostics/{stem}_{valid_uuid}_r2.json") for name, stem in outputs)
        stored = self.pipeline.record_proposal(valid_id, proposal(requirements))
        self.assertEqual(stored["status"], "PROPOSED")
        actual_paths = [item["path"] for item in
            stored["proposal"]["steps"][0]["artifact_requirements"]]
        self.assertEqual(actual_paths, [path for _, path in requirements])

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

    def test_artifact_specific_step_checks_do_not_expand_formal_criteria(self):
        from riverview_core.resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep

        objective_id = "objective:artifact-step-checks:" + uuid4().hex
        formal = "The report documents the worker retry contract."
        artifact_check = "The report includes the stated acceptance phrase."
        self.pipeline.submit_objective(objective_id,
            "Document the worker retry contract at reports/acceptance.txt and include the stated acceptance phrase.",
            [formal], credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        proposal = PlanProposal("Create the requested report", (
            PlanStep("report", "Create reports/acceptance.txt",
                (formal, artifact_check), artifact_requirements=(ArtifactRequirement(
                    "report", "reports/acceptance.txt", "text/plain",
                    (artifact_check,)),)),), 0)
        stored = self.pipeline.record_proposal(objective_id, proposal)
        self.assertEqual(stored["acceptance_criteria"], [formal])
        self.assertEqual(stored["proposal"]["steps"][0]["acceptance_criteria"],
                         [formal, artifact_check])
        self.assertEqual(stored["proposal"]["steps"][0]["artifact_requirements"][0][
            "acceptance_criteria"], [artifact_check])

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
                          "execution.step_verified",
                          "objective.completed"])

    def test_late_codex_artifact_is_preserved_for_independent_verification(self):
        from unittest.mock import patch
        from riverview_core.resident_execution.codex_cli import CAPABILITY
        from riverview_core.resident_execution.codex_workflow import CodexArtifactVerifier
        from riverview_core.worker_adapter import PostgresRecoveryCoordinator
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        objective_id = "objective:late-codex:" + uuid4().hex
        criterion = 'The report contains exact phrase "late output from worker".'
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
            self.assertEqual(rows, [ ("1.0.0", "REJECTED"), ("1.0.5", "ACCEPTED")])
            self.assertEqual(self.admin.execute(f'SELECT count(*) FROM "{self.schema}".worker_attempts '
                "WHERE assignment_id=%s", (assignment_id,)).fetchone()[0], 1)
        finally:
            recovery.close()

    def test_four_verified_steps_complete_once_after_restart_before_reconciliation(self):
        from riverview_core.resident_execution.service import GraceExecutionService

        objective_id = "objective:completion-restart:" + uuid4().hex
        criteria = tuple(f"Step {index} report records its verified repository provenance."
                         for index in range(1, 5))
        self.pipeline.submit_objective(objective_id,
            "Create four sequential reports at reports/completion-1.json, "
            "reports/completion-2.json, reports/completion-3.json, and "
            "reports/completion-4.json; each records its verified repository provenance.",
            list(criteria), credential=self.credentials["steward"], scope_ref=self.scope,
            origin={"conversation_id": str(uuid4()), "source_sequence": 4})
        self.pipeline.ground_objective(objective_id)
        steps = tuple(PlanStep(f"s{index}", f"Create report {index}", (criterion,),
            artifact_requirements=(ArtifactRequirement(f"report-{index}",
                f"reports/completion-{index}.json", "application/json", (criterion,)),))
            for index, criterion in enumerate(criteria, 1))
        self.pipeline.record_proposal(objective_id,
            PlanProposal("Create four independently verified reports", steps, 0))

        artifact_root = self.root / "completion-restart-artifacts"
        class ResultPublisher:
            def __call__(self, context):
                return {"status": "published", "request_id": "restart-review:" +
                    str(context["completion_cycle"]), "provider_id": "provider:test",
                    "served_model": "model:test", "implementation_id": "implementation:test",
                    "review_decision": "ADDITIONAL_EVIDENCE_REQUIRED"}

        def make_service(pipeline=None, adapter=None):
            pipeline = pipeline or self.pipeline
            adapter = adapter or self.adapter
            engine = ContinuousWorker(adapter, self.worker_id, self.credentials["worker"],
                knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
                action=BoundedLocalCodingWorker(pipeline, artifact_root),
                action_effect_class="retry_safe",
                action_capability="engineering.bounded-artifact.v1")
            return GraceExecutionService(pipeline, adapter, engine,
                dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
                verifier_id=self.verifier_id,
                verifier_credential=self.credentials["verifier"], artifact_root=artifact_root,
                conversation_result_publisher=ResultPublisher())

        service = make_service()
        assignments = []
        for index in range(1, 5):
            self.assertEqual(service.dispatch_proposed(objective_id), 1)
            assignment_id = self.pipeline.get_objective(objective_id)["assignment_id"]
            assignments.append(assignment_id)
            self.ledger.transition(assignment_id, "ready", "event_processor_ready",
                f"completion-restart-ready:{index}:{assignment_id}", actor_id="event-processor")
            outcome = service.worker.run_once(assignment_id=assignment_id)
            self.assertEqual(outcome["status"], "AWAITING_VERIFICATION")
            self.assertTrue(service.verify_one(assignment_id))
            if index < 4:
                self.assertEqual(service.reconcile_completions(objective_id=objective_id), index)
                self.assertEqual(self.pipeline.get_objective(objective_id)["status"],
                                 "WORK_ORDER_CREATED")

        # Simulate process loss after PostgreSQL accepted the final verification,
        # before the objective-step/completion reconciliation runs.
        self.assertFalse(any(event["event_type"] == "objective.completed"
                             for event in self.pipeline.objective_events(objective_id)))
        restarted_ledger = PostgresLedger(DSN, schema=self.schema)
        restarted_adapter = PostgresWorkerAdapter(DSN, schema=self.schema)
        self.addCleanup(restarted_ledger.close)
        self.addCleanup(restarted_adapter.close)
        restarted_pipeline = GraceExecutionPipeline(restarted_ledger, self.authorizer,
            AuthorizedAssignmentIntake(restarted_ledger, self.authorizer), self.knowledge)
        service = make_service(restarted_pipeline, restarted_adapter)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 4)
        completed = restarted_pipeline.get_objective(objective_id)
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(restarted_pipeline.get_objective(objective_id)["status"], "COMPLETED",
                         "a conflicting conversational review cannot veto persisted completion")
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 0)
        self.assertEqual(restarted_pipeline.record_verified_completion(
            objective_id, assignments[-1])["status"], "COMPLETED")
        events = restarted_pipeline.objective_events(objective_id)
        self.assertEqual(sum(event["event_type"] == "objective.completed" for event in events), 1)
        self.assertEqual(sum(event["event_type"] == "work_order.dispatched" for event in events), 4)
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT step_id,status,dispatch_count FROM grace_objective_steps
                WHERE objective_id=%s ORDER BY step_order""", (objective_id,))
            steps_after = cur.fetchall()
        self.assertEqual([row["status"] for row in steps_after], ["verified"] * 4)
        self.assertEqual([row["dispatch_count"] for row in steps_after], [1] * 4)
        self.assertEqual(len(set(assignments)), 4)

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
                         "COMPLETED")
        self.assertEqual(service.publish_conversation_results(), 1,
                         "the final result is delivered after durable completion")
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 0)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "COMPLETED",
                         "a later conversational review cannot reverse accepted persisted state")
        self.assertEqual(self.pipeline.pending_conversation_results(), [])
        revision = self.pipeline.request_conversation_result_rereview(objective_id, 2,
            evidence_revision="final-review-evidence-v1",
            evidence=["The final verified artifact satisfies the objective's substantive criteria."],
            credential=self.credentials["steward"],
            idempotency_key="final-review:" + objective_id)
        self.assertEqual(revision["review_generation"], 2)
        publisher.decisions[2] = "OBJECTIVE_COMPLETE"
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 0)
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

    def _create_rework_fixture(self, suffix, *, conversation_id=None,
                               proposal_reference=None, step_id="s1"):
        if proposal_reference is None:
            objective_id = "objective:governed-rework:" + suffix
        else:
            from uuid import NAMESPACE_URL, uuid5
            proposal_id, revision = (proposal_reference["proposal_id"],
                                     proposal_reference["revision"])
            objective_id = ("objective:proposal:" + str(uuid5(NAMESPACE_URL,
                f"riverview:proposal-work-order:{proposal_id}:r{revision}")) +
                f":r{revision}")
        assignment_id = "assignment:grace:governed-rework:" + suffix
        criteria = ["criterion " + str(index) + " must be preserved exactly"
                    for index in range(1, 5)]
        origin = (None if proposal_reference is not None else
            {"conversation_id": conversation_id or str(uuid4()), "source_sequence": 6})
        self.pipeline.submit_objective(objective_id,
            "Create a bounded acceptance artifact at reports/acceptance.txt", criteria,
            credential=self.credentials["steward"], scope_ref=self.scope, origin=origin,
            proposal_reference=proposal_reference)
        self.pipeline.ground_objective(objective_id)
        self.pipeline.record_proposal(objective_id,
            PlanProposal("Create acceptance artifact", (PlanStep(step_id,
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

    def test_proposal_origin_rework_requires_promotion_evidence_and_records_once(self):
        proposal_reference = {"proposal_id":"proposal:18ec0798-a441-494d-b45e-68cf99e72cd2",
            "revision":2, "content_sha256":"a" * 64,
            "approval_event_key":"proposal-approved:test", "source_references":[],
            "privacy_classification":"institutional", "retention_policy":"minimum_required",
            "approved_purpose":"Bounded proposal-origin rework regression test",
            "objective_submit_grant_id":"grant:test"}
        objective_id, assignment_id, _criteria, _action, worker, verifier = \
            self._create_rework_fixture("proposal-origin", proposal_reference=proposal_reference)
        with self.admin.cursor() as cur:
            cur.execute("UPDATE " + self.schema + ".grace_objectives "
                "SET proposal=jsonb_set(proposal,'{system_owned_criteria}',%s::jsonb) "
                "WHERE objective_id=%s", (json.dumps(["Approved proposal promotion" ]), objective_id))
        self.pipeline.proposal_promotion_evidence = lambda _cur, _objective, _criterion: False
        first = worker.run_once(assignment_id=assignment_id)
        self.adapter.verify_attempt(assignment_id, first["attempt_id"], self.verifier_id,
            self.credentials["verifier"], verifier,
            idempotency_key="proposal-origin-reject:" + assignment_id)
        self.assertEqual(self.pipeline.pending_rejected_work_order_reviews(), [])

        self.pipeline.proposal_promotion_evidence = lambda _cur, _objective, _criterion: True
        context = self.pipeline.pending_rejected_work_order_reviews()[0]
        self.assertIsNone(context["origin"])
        self.assertEqual(context["proposal_reference"], proposal_reference)
        self.pipeline.record_rework_escalation_pending(context, "review_provider_unavailable")
        self.assertEqual(self.pipeline.pending_rejected_work_order_reviews(), [],
            "a reviewer failure must not loop again within the same immutable release")
        self.pipeline.runtime_release_id = lambda: "f" * 40
        context = self.pipeline.pending_rejected_work_order_reviews()[0]
        decision = {"decision":"REWORK_PROPOSED",
            "rationale":"Add the missing exact criteria to the same assigned artifact.",
            "correction_instruction":"Include all four exact criteria in the assigned artifact.",
            "criteria_to_address":context["step_acceptance_criteria"]}
        persisted = self.pipeline.record_rework_decision(context, decision,
            credential=self.credentials["steward"])
        from uuid import NAMESPACE_URL, uuid5
        request_id = str(uuid5(NAMESPACE_URL,
            "riverview:grace-rework-review:" + objective_id + ":" + assignment_id + ":" +
            context["completion"]["verification_id"]))
        self.assertTrue(self.pipeline.record_rework_review_recorded(context, request_id))
        self.assertTrue(self.pipeline.record_rework_review_recorded(context, request_id))
        with self.assertRaisesRegex(ValueError, "correlation is invalid"):
            self.pipeline.record_rework_review_recorded(context, "wrong-request")
        self.assertEqual(self.pipeline.pending_rejected_work_order_reviews(), [])
        events = [event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"] == "engineering.rework_review_recorded"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["verification_id"], persisted["verification_id"])
        self.assertEqual(events[0]["payload"]["request_id"], request_id)

    def test_steward_authorization_stop_is_resolved_by_controller_without_re_review(self):
        proposal_reference = {"proposal_id":"proposal:18ec0798-a441-494d-b45e-68cf99e72cd2",
            "revision":2, "content_sha256":"a" * 64,
            "approval_event_key":"proposal-approved:test", "source_references":[],
            "privacy_classification":"institutional", "retention_policy":"minimum_required",
            "approved_purpose":"Bounded proposal-origin re-review regression test",
            "objective_submit_grant_id":"grant:test"}
        objective_id, assignment_id, criteria, _action, worker, verifier = \
            self._create_rework_fixture("proposal-rereview", proposal_reference=proposal_reference)
        with self.admin.cursor() as cur:
            cur.execute("UPDATE " + self.schema + ".grace_objectives "
                "SET proposal=jsonb_set(proposal,'{system_owned_criteria}',%s::jsonb) "
                "WHERE objective_id=%s", (json.dumps(["Approved proposal promotion"]), objective_id))
        self.pipeline.proposal_promotion_evidence = lambda _cur, _objective, _criterion: True
        first = worker.run_once(assignment_id=assignment_id)
        self.adapter.verify_attempt(assignment_id, first["attempt_id"], self.verifier_id,
            self.credentials["verifier"], verifier,
            idempotency_key="proposal-origin-stop:" + assignment_id)
        context = self.pipeline.pending_rejected_work_order_reviews()[0]
        self.assertEqual(context["review_generation"], 1)
        stop = {"decision":"STEWARD_AUTHORIZATION_REQUIRED",
            "rationale":"The previous review lacked current authoritative grant facts.",
            "correction_instruction":None, "criteria_to_address":[]}
        self.pipeline.record_rework_decision(context, stop,
            credential=self.credentials["steward"])
        from uuid import NAMESPACE_URL, uuid5
        first_request = str(uuid5(NAMESPACE_URL,
            "riverview:grace-rework-review:" + objective_id + ":" + assignment_id + ":" +
            context["completion"]["verification_id"]))
        self.pipeline.record_rework_review_recorded(context, first_request)
        second_context = self.pipeline.pending_rejected_work_order_reviews()[0]
        self.assertEqual(second_context["review_generation"], 1)
        self.assertEqual(second_context["prior_review_decision"]["decision"],
            "STEWARD_AUTHORIZATION_REQUIRED")
        self.admin.execute("INSERT INTO " + self.schema +
            ".authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) "
            "VALUES ('steward-authority-grant','steward:test','authority.grant','institution',"
            "'steward:test','rv.policy:grace-execution-test.v1')")
        self.admin.execute("INSERT INTO " + self.schema +
            ".institutional_principals(principal_id,principal_kind) "
            "VALUES ('resident:grace','resident')")
        from riverview_core.institutional_authority.registry import AuthorityRegistry
        from riverview_core.resident_execution.grace_supervisory_authorization import \
            GraceSupervisoryAuthorization
        authority_registry = AuthorityRegistry(DSN, schema=self.schema)
        supervisory = GraceSupervisoryAuthorization(self.pipeline, authority_registry)
        grant = supervisory.authorize(actor_id="steward:test", total_budget_usd="5.00",
            per_request_limit_usd="0.05", explicit_steward_confirmation=True,
            idempotency_key="test-supervisory-evidence-" + uuid4().hex)
        before = self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".grace_objective_events WHERE objective_id=%s", (objective_id,)).fetchone()[0]
        authority = self.pipeline.rework_review_authority_evidence(
            second_context, credential=self.credentials["steward"])
        after = self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".grace_objective_events WHERE objective_id=%s", (objective_id,)).fetchone()[0]
        self.assertEqual(before, after)
        self.assertTrue(authority["read_only"])
        self.assertTrue(authority["assignment_create_grant"]["active"])
        self.assertTrue(authority["same_assignment_rework"]["available"])
        self.assertEqual(authority["same_assignment_rework"]["maximum_rework_attempts"],
            self.pipeline.MAX_GOVERNED_REWORK_ATTEMPTS)
        self.assertTrue(authority["same_assignment_rework"]["independent_verification_required"])
        self.assertEqual(authority["assignment_id"], assignment_id)
        self.assertEqual(authority["objective_runtime_evidence"]["objective"]["objective_id"],
            objective_id)
        self.assertTrue(authority["objective_runtime_evidence"]["read_only"])
        self.assertIn("supervisory_luna_authorization", authority)
        self.assertIn("prior_provider_requests", authority)
        self.assertTrue(authority["supervisory_luna_authorization"]["active"])
        self.assertEqual(authority["supervisory_luna_authorization"]["authorization_id"],
            grant["authorization_id"])
        self.assertEqual(authority["supervisory_luna_authorization"]["scope"]["functions"],
            ["cme_diagnostic_recovery", "performance_evaluation"])
        self.assertEqual(authority["prior_provider_requests"], [])
        validation = self.pipeline.record_rework_controller_validation(
            second_context, second_context["prior_review_decision"])
        self.assertEqual(validation["validation_outcome"],
            "reviewer_authorization_stop_rejected_active_exact_grant")
        self.assertTrue(validation["authorization_lookup"]["active"])
        self.assertEqual(validation["objective_id"], objective_id)
        self.assertEqual(validation["assignment_id"], assignment_id)
        self.assertEqual(self.ledger.get(assignment_id)["state"], "rework_required")
        decisions = [event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"] == "engineering.rework_decided"]
        receipts = [event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"] == "engineering.rework_review_recorded"]
        controller_events = [event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"] == "engineering.rework_controller_validation"]
        self.assertEqual([event["payload"]["decision"] for event in decisions],
            ["STEWARD_AUTHORIZATION_REQUIRED"])
        self.assertEqual(len(receipts), 1)
        self.assertEqual(len(controller_events), 2)
        self.assertEqual(controller_events[-1]["payload"]["authorization_lookup"]["grant_id"],
            grant["authority_grant_id"])
        self.assertEqual(self.pipeline.pending_rejected_work_order_reviews(), [])

        active_objective, active_assignment, _, _action, active_worker, active_verifier = \
            self._create_rework_fixture("active-reviewer-stop")
        active_attempt = active_worker.run_once(assignment_id=active_assignment)
        self.adapter.verify_attempt(active_assignment, active_attempt["attempt_id"],
            self.verifier_id, self.credentials["verifier"], active_verifier,
            idempotency_key="active-reviewer-stop:" + active_assignment)
        active_context = next(item for item in
            self.pipeline.pending_rejected_work_order_reviews()
            if item["objective_id"] == active_objective)
        blocked = self.pipeline.record_rework_decision(active_context, stop,
            credential=self.credentials["steward"])
        self.assertTrue(blocked["controller_hold"])
        self.assertEqual(blocked["decision"], "CONTROLLER_HOLD")
        self.assertTrue(blocked["controller_validation"]["event_id"])
        active_events = self.pipeline.objective_events(active_objective)
        self.assertFalse(any(event["event_type"] == "engineering.rework_decided"
            for event in active_events))
        self.assertTrue(any(event["event_type"] == "engineering.rework_controller_validation"
            for event in active_events))
        self.assertEqual(self.ledger.get(active_assignment)["state"], "rework_required")
        self.assertEqual(self.pipeline.pending_rejected_work_order_reviews(), [])

    def test_diagnostic_runtime_evidence_is_read_only_and_limited_to_exact_references(self):
        historical_id = "objective:grace-conversation:74b28df1-ea8e-5944-8bde-0ff56b117794"
        self.pipeline.submit_objective(historical_id, "Historical cancelled objective",
            ["Preserve history"], credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.submit_objective("objective:diagnostic-evidence:test",
            "Inspect " + historical_id + " using read-only authoritative history",
            ["Report exact runtime evidence"], credential=self.credentials["steward"],
            scope_ref=self.scope)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                for index in range(599):
                    self.pipeline._event(cur, historical_id,
                        "execution.reasoning_attempted", f"test-attempt-{index}",
                        "office:grace", {})
                    self.pipeline._event(cur, historical_id,
                        "execution.reasoning_failed", f"test-failed-{index}",
                        "office:grace", {"reason_code":"fixture_failure"})
                cur.execute("UPDATE grace_objectives SET status='CANCELLED' WHERE objective_id=%s",
                            (historical_id,))
                self.pipeline._event(cur, historical_id, "objective.cancelled",
                    "test-cancelled", "steward:test", {"reason":"fixture"})
        before = self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".grace_objective_events WHERE objective_id=%s", (historical_id,)).fetchone()[0]

        evidence = self.pipeline.diagnostic_runtime_evidence("objective:diagnostic-evidence:test")

        after = self.admin.execute("SELECT count(*) FROM " + self.schema +
            ".grace_objective_events WHERE objective_id=%s", (historical_id,)).fetchone()[0]
        self.assertTrue(evidence["read_only"])
        self.assertEqual(evidence["referenced_historical_objectives"][0]["objective_id"],
                         historical_id)
        counts = evidence["referenced_historical_objectives"][0]["event_counts"]
        self.assertEqual(counts["execution.reasoning_attempted"], 599)
        self.assertEqual(counts["execution.reasoning_failed"], 599)
        self.assertEqual(before, after)

        self.pipeline.submit_objective("objective:diagnostic-evidence:unreferenced",
            "No historic objective is cited", ["No disclosure"],
            credential=self.credentials["steward"], scope_ref=self.scope)
        unreferenced = self.pipeline.diagnostic_runtime_evidence(
            "objective:diagnostic-evidence:unreferenced")
        self.assertEqual(unreferenced["referenced_historical_objectives"], [])

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
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"],
                         "WORK_ORDER_CREATED",
                         "a rejected step cannot complete before corrected accepted verification")
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
        self.assertEqual(completion["status"], "COMPLETED")
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 0)
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

    def test_exact_s4_rework_exception_is_consumed_once_under_concurrent_admission(self):
        from concurrent.futures import ThreadPoolExecutor
        from contextlib import ExitStack
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.resident_execution.grace_supervisory_authorization import (
            GraceSupervisoryAuthorization)
        from riverview_core.resident_execution import GraceExecutionPipeline

        objective_id, assignment_id, criteria, _action, worker, verifier = \
            self._create_rework_fixture("s4-one-use", step_id="s4")
        service = GraceExecutionService(self.pipeline, self.adapter, worker,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=self.root / "s4-rework-artifacts", verifier=verifier,
            rejected_work_order_publisher=None)
        for index in range(self.pipeline.MAX_GOVERNED_REWORK_ATTEMPTS):
            self.assertEqual(worker.run_once(assignment_id=assignment_id)["status"],
                "AWAITING_VERIFICATION")
            self.assertTrue(service.verify_one(assignment_id))
            context = self.pipeline.pending_rejected_work_order_reviews()[0]
            decision = {"decision":"REWORK_PROPOSED",
                "rationale":"The exact S4 rejection requires one correction.",
                "correction_instruction":"Use a deliberately incomplete correction.",
                "criteria_to_address":[criteria[index % len(criteria)]]}
            self.pipeline.record_rework_decision(context, decision,
                credential=self.credentials["steward"])
        self.assertEqual(worker.run_once(assignment_id=assignment_id)["status"],
            "AWAITING_VERIFICATION")
        self.assertTrue(service.verify_one(assignment_id))
        context = self.pipeline.pending_rejected_work_order_reviews()[0]
        self.assertEqual(context["rework_attempt_count"], 3)
        self.admin.execute("UPDATE " + self.schema +
            ".grace_objectives SET revision=10 WHERE objective_id=%s", (objective_id,))
        context = self.pipeline.pending_rejected_work_order_reviews()[0]
        self.assertEqual(context["objective_revision"], 10)
        self.assertEqual(service.publish_rejected_work_order_reviews(), 0)
        verification_id=context["completion"]["verification_id"]
        objective_revision=self.pipeline.get_objective(objective_id)["revision"]

        auth_module=__import__(
            "riverview_core.resident_execution.grace_supervisory_authorization",
            fromlist=["S4_REWORK_OBJECTIVE_ID"])
        with ExitStack() as stack:
            for name,value in (("S4_REWORK_OBJECTIVE_ID",objective_id),
                ("S4_REWORK_ASSIGNMENT_ID",assignment_id),
                ("S4_REWORK_VERIFICATION_ID",verification_id),
                ("S4_REWORK_EXCEPTION_IDEMPOTENCY_KEY",
                    "grace-s4-rework-authorized:" + verification_id)):
                stack.enter_context(patch.object(auth_module,name,value))
            authorization=GraceSupervisoryAuthorization(self.pipeline,self.authorizer)
            evaluation_request_id=str(uuid4())
            evaluation_trigger_event_id=str(uuid4())
            evaluation_response_sha256="d"*64
            with patch.object(self.pipeline,
                    "performance_evaluation_runtime_evidence_for_assignment",
                    return_value={"schema":
                        "rv.grace.performance-evaluation-runtime-evidence.v1",
                        "objective_id":objective_id,"assignment_id":assignment_id,
                        "exchange":{"request_id":evaluation_request_id,
                            "response_sha256":evaluation_response_sha256,
                            "evaluation_trigger_event_id":evaluation_trigger_event_id,
                            "delivery_state":"grace_consumed"},
                        "evaluation":{"trigger_event_id":evaluation_trigger_event_id,
                            "feedback_consumed":True,
                            "authority_granted":False}}):
                grant=authorization.authorize_one_s4_rework_attempt(
                    actor_id="steward:camrui",objective_id=objective_id,
                    objective_revision=objective_revision,
                    objective_assignment_id=assignment_id,assignment_id=assignment_id,
                    verification_id=verification_id,
                    assignment_credential=self.credentials["steward"],
                    explicit_steward_confirmation=True)
            self.assertEqual(grant["status"],"authorized")
            events = self.pipeline.objective_events(objective_id)
            candidate = self.pipeline._available_s4_rework_exception(
                events, objective_id, assignment_id, verification_id,
                objective_revision=10, objective_assignment_id=assignment_id)
            self.assertIsNotNone(candidate, repr([(event["event_type"],
                event.get("idempotency_key"), event.get("actor_id"), event.get("payload")) for event in events
                if event["event_type"] == "engineering.rework_retry_authorized"]))
            eligible=self.pipeline.pending_rejected_work_order_reviews()[0]
            self.assertEqual(eligible["s4_retry_exception"]["event_id"],grant["event_id"])

            def consume_once():
                import psycopg
                ledger=PostgresLedger(DSN,schema=self.schema)
                intake=AuthorizedAssignmentIntake(ledger,self.authorizer)
                pipeline=GraceExecutionPipeline(ledger,self.authorizer,intake,self.knowledge)
                try:
                    return pipeline.consume_s4_rework_exception(
                        eligible,credential=self.credentials["steward"])
                except Exception as exc:
                    return exc
                finally:
                    ledger.close()

            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes=list(executor.map(lambda _i:consume_once(),range(2)))
            successes=[value for value in outcomes if isinstance(value,dict) and
                value.get("status")=="authorized_rework_queued"]
            self.assertEqual(len(successes),1,repr(outcomes))
            self.assertEqual(self.ledger.get(assignment_id)["state"],"ready")
            events=self.pipeline.objective_events(objective_id)
            consumed=[event for event in events if event["event_type"]==
                "engineering.rework_retry_consumed"]
            decisions=[event for event in events if event["event_type"]==
                "engineering.rework_decided" and
                event["payload"].get("decision")=="REWORK_PROPOSED"]
            self.assertEqual(len(consumed),1)
            self.assertEqual(len(decisions),4)

    def test_s3_evaluation_replay_uses_original_assignment_after_objective_advances_to_s4(self):
        objective_id, s3_assignment, _criteria, _action, _worker, _verifier = \
            self._create_rework_fixture("s3-evaluation-after-s4", step_id="s3")
        s4_assignment = s3_assignment + ":step:s4"
        self.intake.create(s4_assignment, "worker:test", "advance-to-s4:" + objective_id,
            credential=self.credentials["steward"], authority_ref=self.scope,
            objective_ref=objective_id, workflow_id=self.pipeline.WORKFLOW_ID,
            workflow_step="s4", correlation_id=objective_id)
        self.admin.execute("""INSERT INTO """ + self.schema + """.grace_objective_steps
            (objective_id,step_id,step_order,step_objective,acceptance_criteria,
             depends_on,status,assignment_id,dispatch_count)
            VALUES (%s,'s4',2,'Complete S4 after S3',%s::jsonb,'["s3"]'::jsonb,
                'assigned',%s,1)""", (objective_id, json.dumps(["S4 acceptance"]), s4_assignment))
        self.admin.execute("UPDATE " + self.schema +
            ".grace_objectives SET assignment_id=%s,revision=10 WHERE objective_id=%s",
            (s4_assignment, objective_id))

        request_id, correlation_id = str(uuid4()), str(uuid4())
        response_sha256 = "d" * 64
        from dataclasses import asdict
        from riverview_core.resident_reasoning import ReasoningRequest
        from riverview_core.resident_execution.external_reasoning import (
            DurableExternalReasoningExchange)
        from riverview_core.reasoning_escalation import (
            EscalationRequest, ReasoningEscalationRouter)
        original_request = ReasoningRequest(request_id=str(uuid4()),
            office_id="office:grace", assignment_id=objective_id,
            assignment_revision="9", binding_revision=1,
            implementation_revision="a"*64, trigger="performance_evaluation",
            token_budget=512, assignment={"assignment_id":s3_assignment,
                "evaluation_trigger_event_id":"event:s3-evaluation-trigger"},
            verified_knowledge=(), prior_plan=None,
            external_reasoning_targets=("gpt-6-luna",), correlation_id=request_id)
        envelope = EscalationRequest.create(original_request, reason="low_confidence",
            target_provider_id="gpt-6-luna", max_tokens=512, timeout_seconds=45,
            escalation_id=request_id)
        request_payload = {"request_type":"performance_evaluation", "max_tokens":512,
            "timeout_seconds":45, "original_request":asdict(original_request)}
        response_payload = {"advisory":json.dumps({
            "schema_version":"rv.grace.performance-evaluation.v1", "grade":2,
            "grade_explanation":"Persisted S3 evidence was evaluated.",
            "rubric_scores":{"reasoning":2,"authorization":3,
                "execution":2,"verification":2},
            "what_went_well":[],"gaps":[],"actionable_feedback":[],
            "authority_promotion_recommendation":"Steward_decision_required"})}
        self.admin.execute("""INSERT INTO """ + self.schema + """.external_reasoning_exchanges
            (request_id,correlation_id,original_request_id,originating_resident_id,
             objective_id,conversation_id,message_sequence,request_schema,response_schema,
             reason,context_sha256,classification,provider_id,idempotency_key,
             request_sha256,request_payload,delivery_state,deadline_at,response_payload,
             response_sha256,response_provenance,response_idempotency_key,response_received_at,
             consumption_key,consumed_at,consumption_result)
            VALUES (%s,%s,%s,'resident:grace',%s,%s,1,'rv.external-reasoning.request.v1',
             'rv.external-reasoning.response.v1','task_complexity',%s,'institutional',
             'gpt-6-luna',%s,%s,%s::jsonb,'grace_consumed',clock_timestamp()+interval '1 hour',
             %s::jsonb,%s,%s::jsonb,%s,clock_timestamp(),%s,clock_timestamp(),%s::jsonb)""",
            (request_id,correlation_id,original_request.request_id,objective_id,
             str(uuid4()),envelope.context_sha256,"s3-replay:"+request_id,"f"*64,
             json.dumps(request_payload),json.dumps(response_payload),response_sha256,
             json.dumps({"response_id":"resp_s3_replay_fixture","usage":{
                 "input_tokens":100,"output_tokens":50,"cost_usd":"0.0001"}}),
             "response:s3-replay:"+request_id,
             f"external-reasoning-consumed:{request_id}",
             json.dumps({"advisory_sha256":response_sha256})))
        self.admin.execute("""INSERT INTO """ + self.schema + """.grace_objective_events
            (objective_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,'resident.performance.evaluation_blocked',%s,'office:grace',%s::jsonb)""",
            (objective_id,"s3-stale-evaluation-block:"+request_id,json.dumps({
                "assignment_id":s4_assignment,"request_id":request_id,
                "correlation_id":correlation_id,"reason_code":"supervisory_consumer_failed"})))

        replay = self.pipeline.pending_consumed_performance_evaluation_replays()
        selected = next(item for item in replay if item["request_id"] == request_id)
        self.assertEqual(selected["assignment_id"], s3_assignment)

        from types import SimpleNamespace
        from riverview_core.resident_execution.service import GraceExecutionService
        class Provider:
            provider_id = "gpt-6-luna"
            def propose(self, _request):
                raise AssertionError("persisted replay must not call the provider")
        exchange = DurableExternalReasoningExchange(self.ledger,
            ReasoningEscalationRouter({"gpt-6-luna":Provider()}), actor_id="resident:grace")
        service=object.__new__(GraceExecutionService)
        service.pipeline=self.pipeline
        service.external_reasoning_exchange=exchange
        service.resident_reasoner=object()
        service.external_reasoning_principal="resident:grace"
        service.external_reasoning_authorize=lambda *_args, **_kwargs: True
        self.assertEqual(service.consume_external_reasoning(),1)
        events=self.pipeline.objective_events(objective_id)
        recorded=next(event for event in events if event["event_type"] ==
            "resident.performance.evaluation_recorded" and
            event["payload"].get("request_id") == request_id)
        self.assertEqual(recorded["payload"]["assignment_id"],s3_assignment)
        self.assertEqual(recorded["payload"]["grade"],2)
        feedback=next(event for event in events if event["event_type"] ==
            "resident.performance.feedback_consumed" and
            event["payload"].get("request_id") == request_id)
        self.assertEqual(feedback["payload"]["assignment_id"],s3_assignment)
        for key, forged in (("assignment_id", "assignment:foreign"),
                ("request_id", str(uuid4())), ("correlation_id", str(uuid4()))):
            with self.assertRaisesRegex(ObjectiveStateError,
                    "supervisory event identity override rejected"):
                self.pipeline.record_supervisory_event(objective_id, s3_assignment,
                    event_type="resident.performance.feedback_consumed", request_id=request_id,
                    correlation_id=correlation_id,
                    idempotency_key="spoofed-"+key+":"+request_id,
                    payload={key:forged, "grade":2})
        _foreign_objective, foreign_assignment, *_ = self._create_rework_fixture(
            "foreign-supervisory-assignment")
        with self.assertRaisesRegex(ObjectiveStateError,
                "supervisory event correlation changed"):
            self.pipeline.record_supervisory_event(objective_id, foreign_assignment,
                event_type="resident.performance.feedback_consumed", request_id=request_id,
                correlation_id=correlation_id, idempotency_key="foreign-feedback:"+request_id,
                payload={"grade":2,"response_sha256":response_sha256})
        self.assertEqual(self.pipeline.get_objective(objective_id)["assignment_id"], s4_assignment)

    def test_s4_performance_evidence_reader_validates_durable_exchange_and_grade(self):
        objective_id, assignment_id, _criteria, _action, _worker, _verifier = \
            self._create_rework_fixture("s4-evaluation-evidence", step_id="s4")
        request_id, correlation_id = str(uuid4()), str(uuid4())
        trigger_event_id = str(uuid4())
        verification_id = "54d1fb2f-411e-4771-a137-785d2b620de7"
        response_sha256 = "a" * 64
        usage = {"input_tokens":2572,"output_tokens":280,
            "reasoning_tokens":130,"cached_input_tokens":0,"cost_usd":"0.00039720"}
        original = {"trigger":"performance_evaluation","assignment_id":objective_id,
            "assignment":{"assignment_id":assignment_id,
                "evaluation_trigger_event_id":trigger_event_id}}
        request = {"request_type":"performance_evaluation","original_request":original}
        response = {"advisory":json.dumps({"schema":"rv.grace.performance-evaluation.v1",
            "grade":2})}
        provenance = {"response_id":"resp_s4_fixture","provider_model":"gpt-6-luna",
            "usage":usage}
        self.admin.execute("""INSERT INTO """ + self.schema + """.external_reasoning_exchanges
            (request_id,correlation_id,original_request_id,originating_resident_id,
             objective_id,conversation_id,message_sequence,request_schema,response_schema,
             reason,context_sha256,classification,provider_id,idempotency_key,
             request_sha256,request_payload,delivery_state,deadline_at,response_payload,
             response_sha256,response_provenance,response_idempotency_key,response_received_at,
             consumption_key,consumed_at,consumption_result)
            VALUES (%s,%s,%s,%s,%s,%s,1,'rv.external-reasoning.request.v1',
             'rv.external-reasoning.response.v1','task_complexity',%s,'institutional',
             'gpt-6-luna',%s,%s,%s::jsonb,'grace_consumed',clock_timestamp()+interval '1 hour',
             %s::jsonb,%s,%s::jsonb,%s,clock_timestamp(),%s,clock_timestamp(),%s::jsonb)""",
            (request_id,correlation_id,"request:s4-fixture","resident:grace",objective_id,
             str(uuid4()),"b"*64,"exchange:s4-fixture", "c"*64,
             json.dumps(request),json.dumps(response),response_sha256,json.dumps(provenance),
             "response:s4-fixture",f"external-reasoning-consumed:{request_id}",
             json.dumps({"advisory_sha256":response_sha256})))
        for seq,(event_type,payload) in enumerate((
                ("provider_attempt_started",{"provider_id":"gpt-6-luna",
                    "provider_model":"gpt-6-luna","attempt":1}),
                ("provider_attempt_settled",{"status":"settled","usage":usage}),
                ("response_received",{"response_sha256":response_sha256}),
                ("grace_consumed",{"state":"grace_consumed"})),1):
            self.admin.execute("""INSERT INTO """ + self.schema +
                """.external_reasoning_exchange_events
                (request_id,correlation_id,event_type,idempotency_key,actor_id,payload)
                VALUES (%s,%s,%s,%s,'service:test',%s::jsonb)""",
                (request_id,correlation_id,event_type,f"event:s4-fixture:{seq}",
                 json.dumps(payload)))
        self.admin.execute("""INSERT INTO """ + self.schema + """.grace_objective_events
            (event_id,objective_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,%s,'engineering.rework_escalation_pending',%s,'office:grace',%s::jsonb)""",
            (trigger_event_id,objective_id,"s4-trigger:"+trigger_event_id,
             json.dumps({"assignment_id":assignment_id,"step_id":"s4",
                 "decision":"ESCALATION_PENDING","reason_code":"retry_limit_exhausted",
                 "verification_id":verification_id})))
        evaluation = {"grade":2,"rubric":{"reasoning":1,"authorization":3,
            "execution":2,"verification":2},"response_sha256":response_sha256,
            "evaluation_trigger_event_id":trigger_event_id}
        for event_type,suffix in (("resident.performance.evaluation_recorded","grade"),
                ("resident.performance.feedback_consumed","feedback")):
            self.pipeline.record_supervisory_event(objective_id,assignment_id,
                event_type=event_type,request_id=request_id,correlation_id=correlation_id,
                idempotency_key=f"s4-eval:{suffix}:{request_id}",payload=evaluation)

        evidence=self.pipeline.performance_evaluation_runtime_evidence_for_assignment(
            objective_id,assignment_id)
        self.assertEqual(evidence["exchange"]["request_id"],request_id)
        self.assertEqual(evidence["exchange"]["usage"],usage)
        self.assertEqual(evidence["evaluation"]["grade"],2)
        self.assertEqual(evidence["evaluation"]["trigger_event_id"],trigger_event_id)
        self.assertTrue(evidence["evaluation"]["feedback_consumed"])
        self.assertFalse(evidence["evaluation"]["authority_granted"])
        self.assertNotIn("advisory",json.dumps(evidence))

        # S5 evaluations are triggered by the durable CME recovery review, not
        # the S4 retry-limit escalation event above.
        request_id, correlation_id = str(uuid4()), str(uuid4())
        trigger_event_id = str(uuid4())
        cme_event_id = str(uuid4())
        trigger_payload = {"request_id":str(uuid4()),
            "correlation_id":str(uuid4()),"cme_event_id":cme_event_id,
            "assignment_id":assignment_id,"recovery_action":"REWORK_PROPOSED",
            "response_sha256":"f"*64}
        original["assignment"]["evaluation_trigger_event_id"] = trigger_event_id
        request = {"request_type":"performance_evaluation","original_request":original}
        response_sha256 = "e"*64
        provenance = {"response_id":"resp_s5_fixture","provider_model":"gpt-6-luna",
            "usage":usage}
        self.admin.execute("""INSERT INTO """ + self.schema + """.external_reasoning_exchanges
            (request_id,correlation_id,original_request_id,originating_resident_id,
             objective_id,conversation_id,message_sequence,request_schema,response_schema,
             reason,context_sha256,classification,provider_id,idempotency_key,
             request_sha256,request_payload,delivery_state,deadline_at,response_payload,
             response_sha256,response_provenance,response_idempotency_key,response_received_at,
             consumption_key,consumed_at,consumption_result)
            VALUES (%s,%s,%s,%s,%s,%s,1,'rv.external-reasoning.request.v1',
             'rv.external-reasoning.response.v1','task_complexity',%s,'institutional',
             'gpt-6-luna',%s,%s,%s::jsonb,'grace_consumed',clock_timestamp()+interval '1 hour',
             %s::jsonb,%s,%s::jsonb,%s,clock_timestamp(),%s,clock_timestamp(),%s::jsonb)""",
            (request_id,correlation_id,"request:s5-fixture","resident:grace",objective_id,
             str(uuid4()),"b"*64,"exchange:s5-fixture", "c"*64,
             json.dumps(request),json.dumps(response),response_sha256,json.dumps(provenance),
             "response:s5-fixture",f"external-reasoning-consumed:{request_id}",
             json.dumps({"advisory_sha256":response_sha256})))
        for seq,(event_type,payload) in enumerate((
                ("provider_attempt_started",{"provider_id":"gpt-6-luna",
                    "provider_model":"gpt-6-luna","attempt":1}),
                ("provider_attempt_settled",{"status":"settled","usage":usage}),
                ("response_received",{"response_sha256":response_sha256}),
                ("grace_consumed",{"state":"grace_consumed"})),1):
            self.admin.execute("""INSERT INTO """ + self.schema + """.external_reasoning_exchange_events
                (request_id,correlation_id,event_type,idempotency_key,actor_id,payload)
                VALUES (%s,%s,%s,%s,'service:test',%s::jsonb)""",
                (request_id,correlation_id,event_type,f"event:s5-fixture:{seq}",
                 json.dumps(payload)))
        self.admin.execute("""INSERT INTO """ + self.schema + """.grace_objective_events
            (event_id,objective_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,%s,'resident.reasoning.cme_recovery_evaluated',%s,'office:grace',%s::jsonb)""",
            (trigger_event_id,objective_id,"s5-trigger:"+trigger_event_id,
             json.dumps(trigger_payload)))
        evaluation["response_sha256"] = response_sha256
        evaluation["evaluation_trigger_event_id"] = trigger_event_id
        for event_type,suffix in (("resident.performance.evaluation_recorded","grade"),
                ("resident.performance.feedback_consumed","feedback")):
            self.pipeline.record_supervisory_event(objective_id,assignment_id,
                event_type=event_type,request_id=request_id,correlation_id=correlation_id,
                idempotency_key=f"s5-eval:{suffix}:{request_id}",payload=evaluation)
        evidence=self.pipeline.performance_evaluation_runtime_evidence_for_assignment(
            objective_id,assignment_id)
        self.assertEqual(evidence["exchange"]["request_id"],request_id)
        self.assertEqual(evidence["evaluation"]["trigger_event_id"],trigger_event_id)

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
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 2)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "COMPLETED")

        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 0)
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

    def test_reconciliation_verifies_earlier_step_after_objective_pointer_advances(self):
        """A later dispatch must not hide an earlier completed step from reconciliation."""
        from riverview_core.resident_execution.service import GraceExecutionService

        objective_id = "objective:step-reconcile-pointer:" + uuid4().hex
        criteria = ("Step one artifact records the baseline.",
                    "Step two artifact records the analysis.",
                    "Step three artifact records the risks.")
        self.pipeline.submit_objective(objective_id,
            "Create baseline, analysis, and risks artifacts at s1.json, s2.json, and s3.json for this execution test.",
            criteria, credential=self.credentials["steward"], scope_ref=self.scope,
            origin={"conversation_id": str(uuid4()), "source_sequence": 1})
        self.pipeline.ground_objective(objective_id)
        steps = tuple(PlanStep(step_id, task, (criterion,),
            artifact_requirements=(ArtifactRequirement(name, path, "application/json",
                (criterion,)),)) for step_id, task, criterion, name, path in (
                    ("s1", "Create the baseline artifact", criteria[0], "baseline", "s1.json"),
                    ("s2", "Create the analysis artifact", criteria[1], "analysis", "s2.json"),
                    ("s3", "Create the risks artifact", criteria[2], "risks", "s3.json")))
        self.pipeline.record_proposal(objective_id,
            PlanProposal("Create three verified artifacts", steps, 0))

        class ResultPublisher:
            def __call__(self, context):
                cycle = context["completion_cycle"]
                return {"status": "published", "request_id": f"step-reconcile:{cycle}",
                    "provider_id": "provider:test", "served_model": "model:test",
                    "implementation_id": "implementation:test",
                    "review_decision": ("OBJECTIVE_COMPLETE" if cycle == 3 else
                                        "ENGINEERING_STEP_PROPOSED")}

        artifact_root = self.root / "step-reconcile-artifacts"
        worker = ContinuousWorker(self.adapter, self.worker_id, self.credentials["worker"],
            knowledge=RepositoryKnowledgeProvider(self.repo, self.commit),
            action=BoundedLocalCodingWorker(self.pipeline, artifact_root),
            action_effect_class="retry_safe", action_capability="engineering.bounded-artifact.v1")
        service = GraceExecutionService(self.pipeline, self.adapter, worker,
            dispatch_credential=self.credentials["steward"], authority_ref=self.scope,
            verifier_id=self.verifier_id, verifier_credential=self.credentials["verifier"],
            artifact_root=artifact_root, conversation_result_publisher=ResultPublisher())

        def execute_and_verify(assignment_id):
            self.ledger.transition(assignment_id, "ready", "event_processor_ready",
                "step-reconcile-ready:" + assignment_id, actor_id="event-processor")
            outcome = worker.run_once(assignment_id=assignment_id)
            self.assertEqual(outcome["status"], "AWAITING_VERIFICATION")
            self.assertTrue(service.verify_one(assignment_id))
            self.assertEqual(self.ledger.get(assignment_id)["state"], "completed")

        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        s1 = self.pipeline.get_objective(objective_id)["assignment_id"]
        execute_and_verify(s1)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 1)
        self.assertEqual(service.publish_conversation_results(), 1)

        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        s2 = self.pipeline.get_objective(objective_id)["assignment_id"]
        execute_and_verify(s2)
        # Dispatching a later eligible step advances the objective's single
        # assignment pointer before S2's accepted verification is reconciled.
        self.assertEqual(service.dispatch_proposed(objective_id), 1)
        s3 = self.pipeline.get_objective(objective_id)["assignment_id"]
        self.assertNotEqual(s2, s3)
        execute_and_verify(s3)
        self.assertEqual(self.pipeline.get_objective(objective_id)["assignment_id"], s3)
        self.assertEqual(self.admin.execute(f'SELECT count(*) FROM "{self.schema}".verification_records '
            "WHERE assignment_id=ANY(%s) AND decision='ACCEPTED'", ([s2, s3],)).fetchone()[0], 2)

        service.reconcile_completions(objective_id=objective_id)
        steps_after_reconcile = self.admin.execute(f'SELECT step_id,status FROM "{self.schema}".grace_objective_steps '
            "WHERE objective_id=%s ORDER BY step_order", (objective_id,)).fetchall()
        self.assertEqual(steps_after_reconcile, [("s1", "verified"),
            ("s2", "verified"), ("s3", "verified")])
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "COMPLETED")
        self.assertEqual(service.publish_conversation_results(), 1)
        self.assertEqual(service.reconcile_completions(objective_id=objective_id), 0)

        completed = self.pipeline.get_objective(objective_id)
        self.assertEqual(completed["status"], "COMPLETED")
        events = self.pipeline.objective_events(objective_id)
        step_events = [event for event in events if event["event_type"] == "execution.step_verified"]
        self.assertEqual({event["payload"]["step_id"] for event in step_events}, {"s1", "s2", "s3"})
        completion = next(event for event in events if event["event_type"] == "objective.completed")
        self.assertEqual(completion["payload"]["decision"], "ACCEPTED")
        self.assertEqual(completion["payload"]["assignment_id"], s3)
        self.assertTrue(completion["payload"]["artifact"]["artifact_sha256"])


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

    def test_grounding_failure_diagnostics_are_durable_sanitized_and_retryable(self):
        from types import SimpleNamespace
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        cases = [
            ("no-match", KnowledgeResult(KnowledgeStatus.NO_MATCH), "GROUNDING_NO_MATCH"),
            ("unavailable", KnowledgeResult(KnowledgeStatus.UNAVAILABLE),
             "KNOWLEDGE_PROVIDER_UNAVAILABLE"),
            ("incomplete", KnowledgeResult(KnowledgeStatus.INCOMPLETE),
             "GROUNDING_RETRIEVAL_INCOMPLETE"),
            ("contradictory", KnowledgeResult(KnowledgeStatus.CONTRADICTORY),
             "GROUNDING_EVIDENCE_CONTRADICTORY"),
            ("unverified", KnowledgeResult(KnowledgeStatus.UNVERIFIED),
             "GROUNDING_EVIDENCE_UNVERIFIED"),
            ("missing-reference", SimpleNamespace(status=KnowledgeStatus.VERIFIED,
                source_references=(), source_revision=self.commit, source_sha256="a" * 64,
                retrieval_complete=True, value=None), "GROUNDING_SOURCE_REFERENCES_MISSING"),
            ("missing-revision", KnowledgeResult(KnowledgeStatus.VERIFIED,
                source_references=("repo://docs/evidence.md",), source_sha256="a" * 64,
                retrieval_complete=True), "GROUNDING_SOURCE_REVISION_MISSING"),
            ("missing-hash", KnowledgeResult(KnowledgeStatus.VERIFIED,
                source_references=("repo://docs/evidence.md",), source_revision=self.commit,
                retrieval_complete=True), "GROUNDING_SOURCE_HASH_MISSING"),
            ("incomplete-flag", SimpleNamespace(status=KnowledgeStatus.VERIFIED,
                source_references=("repo://docs/evidence.md",), source_revision=self.commit,
                source_sha256="a" * 64, retrieval_complete=False, value=None),
             "GROUNDING_RETRIEVAL_INCOMPLETE"),
            ("invalid-status", SimpleNamespace(status="unexpected", source_references=(),
                source_revision=None, source_sha256=None, retrieval_complete=False, value=None),
             "KNOWLEDGE_RESULT_INVALID"),
            ("serialization", KnowledgeResult(KnowledgeStatus.VERIFIED,
                value={"private": {"must-not-appear"}},
                source_references=("repo://docs/evidence.md",), source_revision=self.commit,
                source_sha256="a" * 64, retrieval_complete=True),
             "EVIDENCE_SERIALIZATION_FAILED"),
            ("oversized", KnowledgeResult(KnowledgeStatus.VERIFIED,
                value={"private": "sensitive-value-" * 1000},
                source_references=("repo://docs/evidence.md",), source_revision=self.commit,
                source_sha256="a" * 64, retrieval_complete=True), "EVIDENCE_TOO_LARGE"),
        ]

        for label, result, expected_code in cases:
            objective_id = "objective:grounding-diagnostic:" + label
            class FixedKnowledge:
                def ground_assignment(self, _assignment):
                    return result
            pipeline = GraceExecutionPipeline(self.ledger, self.authorizer, self.intake,
                                              FixedKnowledge())
            pipeline.submit_objective(objective_id, "Ground bounded evidence",
                ["preserve objective evidence"], credential=self.credentials["steward"],
                scope_ref=self.scope, origin={"conversation_id": str(uuid4()),
                                              "source_sequence": 1})
            with self.assertRaises(ObjectiveStateError):
                pipeline.ground_objective(objective_id)
            events = pipeline.objective_events(objective_id)
            waiting = events[-1]
            diagnostic = waiting["payload"]["grounding_diagnostic"]
            self.assertEqual(diagnostic["reason_code"], expected_code, label)
            self.assertEqual(diagnostic["new_state"], "WAITING_FOR_EVIDENCE")
            self.assertEqual(diagnostic["previous_state"], "RECEIVED")
            expected_component = ("KNOWLEDGE-PROVIDER" if expected_code in {
                "KNOWLEDGE_PROVIDER_UNAVAILABLE", "GROUNDING_NO_MATCH",
                "GROUNDING_RETRIEVAL_INCOMPLETE", "GROUNDING_EVIDENCE_CONTRADICTORY",
                "GROUNDING_EVIDENCE_UNVERIFIED"} and label != "incomplete-flag"
                else "RESIDENT-ORCHESTRATION")
            self.assertEqual(diagnostic["responsible_component"], expected_component, label)
            self.assertEqual(diagnostic["objective_revision"], 2)
            self.assertEqual(diagnostic["retry"]["retryable"], True)
            self.assertFalse(diagnostic["retry"]["automatic"])
            self.assertIn("same conversation work-order action",
                          diagnostic["retry"]["next_permitted_action"])
            self.assertEqual(diagnostic["event_id"], str(waiting["event_id"]))
            self.assertIsNotNone(waiting["occurred_at"])
            self.assertRegex(diagnostic["evidence"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(diagnostic["attempt_id"],
                             r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
            self.assertNotIn("must-not-appear", json.dumps(waiting["payload"]))
            self.assertNotIn("sensitive-value", json.dumps(waiting["payload"]))
            self.assertEqual(pipeline.get_objective(objective_id)["status"],
                             "WAITING_FOR_EVIDENCE")

        objective_id = "objective:grounding-diagnostic:provider-error"
        class FailingKnowledge:
            def ground_assignment(self, _assignment):
                raise RuntimeError("secret provider detail must not persist")
        pipeline = GraceExecutionPipeline(self.ledger, self.authorizer, self.intake,
                                          FailingKnowledge())
        pipeline.submit_objective(objective_id, "Ground bounded evidence",
            ["preserve objective evidence"], credential=self.credentials["steward"],
            scope_ref=self.scope)
        with self.assertRaises(ObjectiveStateError):
            pipeline.ground_objective(objective_id)
        waiting = pipeline.objective_events(objective_id)[-1]
        diagnostic = waiting["payload"]["grounding_diagnostic"]
        self.assertEqual(diagnostic["reason_code"], "KNOWLEDGE_PROVIDER_ERROR")
        self.assertEqual(diagnostic["failure_type"], "RuntimeError")
        self.assertNotIn("secret provider detail", json.dumps(waiting["payload"]))

        objective_id = "objective:grounding-diagnostic:provider-timeout"
        class TimeoutKnowledge:
            def ground_assignment(self, _assignment):
                raise TimeoutError("timeout detail must not persist")
        pipeline = GraceExecutionPipeline(self.ledger, self.authorizer, self.intake,
                                          TimeoutKnowledge())
        pipeline.submit_objective(objective_id, "Ground bounded evidence",
            ["preserve objective evidence"], credential=self.credentials["steward"],
            scope_ref=self.scope)
        with self.assertRaises(ObjectiveStateError):
            pipeline.ground_objective(objective_id)
        self.assertEqual(pipeline.objective_events(objective_id)[-1]["payload"]
                         ["grounding_diagnostic"]["reason_code"], "KNOWLEDGE_PROVIDER_TIMEOUT")

    def test_grounding_failure_attempt_history_survives_successful_retry(self):
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        class MutableKnowledge:
            def __init__(self):
                self.result = KnowledgeResult(KnowledgeStatus.NO_MATCH)
            def ground_assignment(self, _assignment):
                return self.result

        knowledge = MutableKnowledge()
        pipeline = GraceExecutionPipeline(self.ledger, self.authorizer, self.intake, knowledge)
        objective_id = "objective:grounding-diagnostic:retry-history"
        pipeline.submit_objective(objective_id, "Ground then retry",
            ["preserve objective evidence"], credential=self.credentials["steward"],
            scope_ref=self.scope)
        with self.assertRaises(ObjectiveStateError):
            pipeline.ground_objective(objective_id)
        with self.assertRaises(ObjectiveStateError):
            pipeline.ground_objective(objective_id)
        knowledge.result = KnowledgeResult(KnowledgeStatus.VERIFIED,
            value={"evidence": "verified"}, source_references=("repo://docs/evidence.md",),
            source_revision=self.commit, source_sha256="b" * 64, retrieval_complete=True)
        self.assertEqual(pipeline.ground_objective(objective_id)["status"], "GROUNDED")
        events = pipeline.objective_events(objective_id)
        diagnostics = [event for event in events if event["event_type"] ==
                       "objective.waiting_for_evidence"]
        self.assertEqual(len(diagnostics), 2)
        self.assertNotEqual(diagnostics[0]["payload"]["grounding_diagnostic"]["attempt_id"],
                            diagnostics[1]["payload"]["grounding_diagnostic"]["attempt_id"])
        self.assertEqual(diagnostics[0]["payload"]["grounding_diagnostic"]["reason_code"],
                         "GROUNDING_NO_MATCH")
        self.assertEqual(diagnostics[1]["payload"]["grounding_diagnostic"]["objective_revision"], 3)
        self.assertEqual([event["event_type"] for event in events][-1], "objective.grounded")

    def test_concurrent_grounding_failures_keep_attempt_history_and_idempotent_replay(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        barrier = Barrier(2)

        class ConcurrentKnowledge:
            def ground_assignment(self, _assignment):
                barrier.wait(timeout=10)
                return KnowledgeResult(KnowledgeStatus.NO_MATCH)

        pipeline = GraceExecutionPipeline(self.ledger, self.authorizer, self.intake,
                                          ConcurrentKnowledge())
        objective_id = "objective:grounding-diagnostic:concurrent-failures"
        pipeline.submit_objective(objective_id, "Ground then retry concurrently",
            ["preserve objective evidence"], credential=self.credentials["steward"],
            scope_ref=self.scope)

        def attempt_grounding():
            from riverview_core.assignment_intake import AuthorizedAssignmentIntake
            from riverview_core.postgres_ledger import PostgresLedger

            ledger = PostgresLedger(DSN, schema=self.schema)
            attempt_pipeline = GraceExecutionPipeline(ledger, self.authorizer,
                AuthorizedAssignmentIntake(ledger, self.authorizer), ConcurrentKnowledge())
            try:
                attempt_pipeline.ground_objective(objective_id)
            except Exception as exc:
                return exc
            finally:
                ledger.close()
            return None

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: attempt_grounding(), range(2)))

        self.assertTrue(all(isinstance(result, ObjectiveStateError) and
                            str(result) == "repository evidence is not complete and verified"
                            for result in results), repr(results))
        objective = pipeline.get_objective(objective_id)
        self.assertEqual(objective["status"], "WAITING_FOR_EVIDENCE")
        self.assertEqual(objective["revision"], 3)
        self.assertEqual(objective["evidence"]["error_code"], "GROUNDING_NO_MATCH")
        events = [event for event in pipeline.objective_events(objective_id)
                  if event["event_type"] == "objective.waiting_for_evidence"]
        self.assertEqual(len(events), 2)
        diagnostics = [event["payload"]["grounding_diagnostic"] for event in events]
        self.assertEqual([diagnostic["objective_revision"] for diagnostic in diagnostics], [2, 3])
        self.assertEqual([diagnostic["previous_state"] for diagnostic in diagnostics],
                         ["RECEIVED", "WAITING_FOR_EVIDENCE"])
        self.assertEqual(len({diagnostic["attempt_id"] for diagnostic in diagnostics}), 2)

        latest = diagnostics[-1]
        duplicate_result = pipeline._set_waiting(objective, objective["evidence"],
            latest["attempt_id"], latest["attempt_started_at"],
            error_code="GROUNDING_NO_MATCH",
            explanation="The knowledge provider returned no matching evidence.",
            stage="provider_result", responsible_component="KNOWLEDGE-PROVIDER",
            evidence_bytes=None)
        self.assertFalse(duplicate_result)
        after_replay = pipeline.get_objective(objective_id)
        self.assertEqual(after_replay["revision"], objective["revision"])
        self.assertEqual(after_replay["evidence"], objective["evidence"])
        self.assertEqual(len([event for event in pipeline.objective_events(objective_id)
                              if event["event_type"] == "objective.waiting_for_evidence"]), 2)

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

    def test_authorized_grounded_objective_cancellation_is_audited_and_leaves_queue(self):
        objective_id = "objective:grounded-cancel"
        grounded = self._create_grounded_reasoning_objective(objective_id)
        initial_revision = grounded["revision"]
        self.assertEqual([row["objective_id"] for row in
            self.pipeline.grounded_objectives(scope_ref=self.scope)], [objective_id])

        with self.assertRaises(ObjectiveNotAuthorized):
            self.pipeline.cancel_work_order(objective_id,
                credential=secrets.token_urlsafe(36), authority_ref=self.scope,
                reason="Obsolete test objective")
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "GROUNDED")

        cancelled = self.pipeline.cancel_work_order(objective_id,
            credential=self.credentials["steward"], authority_ref=self.scope,
            reason="Obsolete test objective")
        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertEqual(cancelled["revision"], initial_revision + 1)
        self.assertEqual(self.pipeline.grounded_objectives(scope_ref=self.scope), [])
        events = [event for event in self.pipeline.objective_events(objective_id)
                  if event["event_type"] == "objective.cancelled"]
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["actor_id"], "steward:test")
        self.assertIsNotNone(event["occurred_at"])
        self.assertEqual(event["payload"]["reason"], "Obsolete test objective")
        self.assertEqual(event["payload"]["authorized_principal"], "steward:test")
        self.assertEqual(event["payload"]["objective_revision"], initial_revision + 1)
        self.assertTrue(event["payload"]["cancelled_at"])

    def test_grounded_objective_cancellation_requires_reason_and_is_idempotent(self):
        objective_id = "objective:grounded-cancel-idempotent"
        grounded = self._create_grounded_reasoning_objective(objective_id)
        with self.assertRaises(ValueError):
            self.pipeline.cancel_work_order(objective_id,
                credential=self.credentials["steward"], authority_ref=self.scope)
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "GROUNDED")

        reason = "Duplicate proposal is obsolete"
        first = self.pipeline.cancel_work_order(objective_id,
            credential=self.credentials["steward"], authority_ref=self.scope, reason=reason)
        repeated = self.pipeline.cancel_work_order(objective_id,
            credential=self.credentials["steward"], authority_ref=self.scope, reason=reason)
        self.assertEqual(first["revision"], grounded["revision"] + 1)
        self.assertEqual(repeated["revision"], first["revision"])
        self.assertEqual(len([event for event in self.pipeline.objective_events(objective_id)
            if event["event_type"] == "objective.cancelled"]), 1)
        with self.assertRaises(ObjectiveStateError):
            self.pipeline.cancel_work_order(objective_id,
                credential=self.credentials["steward"], authority_ref=self.scope,
                reason="Different cancellation reason")

    def test_grounded_cancellation_rejects_any_existing_engineering_assignment(self):
        from psycopg import sql

        objective_id = "objective:grounded-cancel-assignment-exists"
        self._create_grounded_reasoning_objective(objective_id)
        assignment_id = "assignment:" + uuid4().hex
        self.admin.execute(sql.SQL("""INSERT INTO {}.assignments
            (id,state,owner,authority_ref,objective_ref,workflow_id,workflow_step,
             correlation_id,updated_at)
            VALUES (%s,'queued','engineering',%s,%s,'grace.objective-work-order.v1',
                    'test-step',%s,clock_timestamp())""").format(sql.Identifier(self.schema)),
            (assignment_id, self.scope, objective_id, objective_id))

        with self.assertRaisesRegex(ObjectiveStateError, "assignment or dispatch history"):
            self.pipeline.cancel_work_order(objective_id,
                credential=self.credentials["steward"], authority_ref=self.scope,
                reason="Obsolete")
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"], "GROUNDED")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "queued")

    def test_running_engineering_work_remains_uncancellable(self):
        from riverview_core.resident_reasoning import ArtifactRequirement

        objective_id = "objective:cancel-running"
        criterion = "reports/cancel.json contains the task and verified repository provenance"
        self.pipeline.submit_objective(objective_id,
            "Create reports/cancel.json with the task and verified repository provenance.",
            [criterion], credential=self.credentials["steward"], scope_ref=self.scope)
        self.pipeline.ground_objective(objective_id)
        proposal = PlanProposal("Create the requested cancellation test artifact", (
            PlanStep("create-report", "Create reports/cancel.json", (criterion,),
                artifact_requirements=(ArtifactRequirement(
                    "cancel-report", "reports/cancel.json", "application/json",
                    (criterion,)),)),), 0)
        self.pipeline.record_proposal(objective_id, proposal)
        assignment_id = "assignment:" + uuid4().hex
        self.pipeline.authorize_and_dispatch(objective_id, assignment_id,
            credential=self.credentials["steward"], authority_ref=self.scope,
            idempotency_key="grounded-cancel-running-" + assignment_id)
        self.ledger.transition(assignment_id, "ready", "event_processor_ready",
            "cancel-running-ready-" + assignment_id, actor_id="event-processor:test")
        self.ledger.transition(assignment_id, "running", "worker_started",
            "cancel-running-started-" + assignment_id, actor_id="worker:test")

        with self.assertRaisesRegex(ObjectiveStateError, "queued or ready"):
            self.pipeline.cancel_work_order(objective_id,
                credential=self.credentials["steward"], authority_ref=self.scope,
                reason="Must not interrupt running work")
        self.assertEqual(self.pipeline.get_objective(objective_id)["status"],
                         "WORK_ORDER_CREATED")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "running")

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
