# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_worker_adapter.py
# Component: WORKER-ADAPTER
# Revision: 1.2.0
# Purpose: Verify scoped deterministic and structured worker artifacts
# Execution Model: PostgreSQL integration tests using isolated schemas
# Observability: Durable assignment, worker, attempt, result, and knowledge rows
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL test database
# Authority: Creates and drops only unique rvtest_* schemas
# Changed: 2026-10-10 UTC | RV-M2.4-001 | Verify knowledge timeout with synchronization instead of a brittle latency bound
# Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT-TEST-FIX | Give self-verification test its explicit verification grant
# Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT-REVOCATION | Deny registration without a grant and execution after revocation
# Changed: 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Verify structured artifact execution under its own exact capability grant
# Changed: 2026-10-11 UTC | RV-M3.3-REPOSITORY-KNOWLEDGE | Exercise pinned repository provider through worker and independent verifier
# Changed: 2026-10-11 UTC | RV-M3.3-WORKER-SERVICE | Verify service restart registration is exact and idempotent
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Exercise the repository test task, durable file artifact, and independent rerun in PostgreSQL
# Changed: 2026-10-11 UTC | RV-M33-ARTIFACT-FAILURE-DIAGNOSIS | Include safe action error code in isolated integration failure output
# Changed: 2026-10-11 UTC | RV-M33-ARTIFACT-FAILURE-DIAGNOSIS | Include durable failure class in isolated integration assertion
# Changed: 2026-10-11 UTC | RV-M33-ARTIFACT-VERIFICATION-DIAGNOSIS | Surface independent verifier criteria in the isolated regression
# Changed: 2026-10-11 UTC | RV-M33-ARTIFACT-VERIFICATION-DIAGNOSIS | Attach verifier criterion details to the repository artifact check
# Changed: 2026-10-11 UTC | RV-M33-ARTIFACT-VERIFICATION-DIAGNOSIS | Target repository-task verifier assertion for criteria output
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Verify audited recovery of a reproduced legacy pre-execution failure without mislabeling uncertain work
# Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Verify a later durable pre-launch failure requeues once within retry ceiling
# Contracts: docs/development/M2.3-001_REVISION_RECORD.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""M2.1 PostgreSQL integration tests; never target the shared app schema."""

import hashlib
import json
import os
import threading
import time
import unittest
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


def _crash_after_effect(dsn, schema, assignment_id, worker_id, credential, ready):
    """Commit one isolated test effect, signal the parent, and await SIGKILL."""
    import psycopg
    from psycopg import sql
    from riverview_core.worker_adapter import (ContinuousWorker, KnowledgeResult,
                                                KnowledgeStatus, PostgresWorkerAdapter)

    class Provider:
        @staticmethod
        def result():
            return KnowledgeResult(KnowledgeStatus.VERIFIED, value="verified input",
                source_references=("repo://test/recovery-contract",),
                source_revision="test-1", source_sha256="b" * 64,
                retrieval_complete=True)
        def ground_assignment(self, assignment): return self.result()
        def preflight_action(self, assignment, action): return self.result()
        def reground_assignment(self, assignment, trigger): return self.result()
        def record_learning(self, assignment, outcome): return self.result()

    adapter = PostgresWorkerAdapter(dsn, schema=schema)
    def effect(assignment, grounded):
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("INSERT INTO {} (assignment_id) VALUES (%s)")
                         .format(sql.Identifier(schema, "recovery_test_effects")),
                         (assignment_id,))
        ready.send("effect_committed")
        while True:
            time.sleep(1)
    try:
        ContinuousWorker(adapter, worker_id, credential, knowledge=Provider(),
                         lease_seconds=30, action=effect).run_once()
    finally:
        adapter.close()


def _crash_after_intent(dsn, schema, assignment_id, worker_id, credential,
                        generation, effect_class, ready):
    from riverview_core.worker_adapter import PostgresWorkerAdapter
    adapter = PostgresWorkerAdapter(dsn, schema=schema)
    try:
        intent_id = adapter.begin_execution_intent(
            assignment_id, worker_id, credential, generation,
            f"test-interrupted:{assignment_id}:{generation}", effect_class=effect_class)
        ready.send(str(intent_id))
        while True:
            time.sleep(1)
    finally:
        adapter.close()


def _crash_after_result(dsn, schema, assignment_id, worker_id, credential,
                        generation, ready):
    """Commit a PostgreSQL result, signal, then die before assignment transition."""
    from riverview_core.worker_adapter import PostgresWorkerAdapter
    adapter = PostgresWorkerAdapter(dsn, schema=schema)
    try:
        result = adapter.execute_sha256(
            assignment_id, worker_id, credential, generation,
            f"test-result-before-transition:{assignment_id}:{generation}",
            "durable result survives process death")
        ready.send(str(result["attempt_id"]))
        while True:
            time.sleep(1)
    finally:
        adapter.close()


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class WorkerAdapterTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.postgres_migrations import apply_migrations

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
        self.admin.execute(sql.SQL("CREATE TABLE {} (effect_id BIGSERIAL PRIMARY KEY, assignment_id TEXT NOT NULL)")
                           .format(sql.Identifier(self.schema, "recovery_test_effects")))
        root = Path(__file__).resolve().parents[1] / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=root / "assignment_scheduler/migrations")
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=root / "worker_adapter/migrations")
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=root / "institutional_authority/migrations")
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=root / "resident_execution/migrations")
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        from riverview_core.worker_adapter import PostgresWorkerAdapter
        self.worker = PostgresWorkerAdapter(DSN, schema=self.schema)
        self.admin.execute("INSERT INTO institutional_principals(principal_id,principal_kind) "
                           "VALUES ('steward:test','steward')")
        self.assignment = "worker-task-" + uuid4().hex
        self.worker_id = "worker-local-" + uuid4().hex
        self.scope = "grant:local-task"
        self.ledger.create(self.assignment, "engineering", f"create-{self.assignment}",
                           authority_ref=self.scope, objective_ref="objective:sha256",
                           actor_id="resident:test")
        self.ledger.transition(self.assignment, "ready", "intake", f"ready-{self.assignment}",
                               actor_id="event-processor")
        self.token = self.register()
        claim = self.worker.claim_next(self.worker_id, self.token, lease_seconds=60)
        self.assertEqual(claim["assignment"]["id"], self.assignment)
        self.lease = claim["lease"]
        self.worker.start_assignment(self.assignment, self.worker_id, self.token,
                                    self.lease["generation"])

    def tearDown(self):
        from psycopg import sql
        self.worker.close()
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def register(self, capabilities=None, scope=None):
        return self.register_as(self.worker_id,
                                capabilities or ["deterministic.sha256.v1"],
                                scope or self.scope)

    def register_as(self, worker_id, capabilities, scope):
        token = __import__("secrets").token_urlsafe(32)
        principal_id = "worker-principal:" + worker_id
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        self.admin.execute(
            "INSERT INTO institutional_principals(principal_id,principal_kind) VALUES (%s,'worker')",
            (principal_id,))
        self.admin.execute("""INSERT INTO principal_credentials
            (credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)""",
            (uuid4(), principal_id, digest))
        actions = ["worker.register"]
        if any(cap in capabilities for cap in
               ("deterministic.sha256.v1", "local.inference.v1",
                "engineering.repository-check.v1",
                "engineering.codex-cli-artifact.v1")):
            actions.append("assignment.execute")
        if "assignment.verify.v1" in capabilities:
            actions.append("assignment.verify")
        for action in actions:
            self.admin.execute("""INSERT INTO authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                VALUES (%s,%s,%s,%s,'steward:test','rv.policy:worker-fixture.v1')""",
                (f"test:{action}:{worker_id}", principal_id, action, scope))
        return self.worker.register_worker(worker_id, capabilities, scope,
                                           credential=token)

    def ready_assignment(self, *, scope=None, objective="objective:sha256"):
        assignment_id = "worker-cycle-" + uuid4().hex
        authority = scope or self.scope
        self.ledger.create(assignment_id, "engineering", f"create-{assignment_id}",
                           authority_ref=authority, objective_ref=objective,
                           actor_id="resident:test")
        self.ledger.transition(assignment_id, "ready", "intake", f"ready-{assignment_id}",
                               actor_id="event-processor")
        return assignment_id

    class VerifiedProvider:
        def __init__(self, value="objective:sha256"):
            self.value = value

        def _verified(self):
            from riverview_core.worker_adapter import KnowledgeResult, KnowledgeStatus
            return KnowledgeResult(KnowledgeStatus.VERIFIED, value=self.value,
                                   source_references=("repo://docs/architecture/CORE_CONTRACT.md",),
                                   source_revision="1.0.0", source_sha256="a" * 64,
                                   retrieval_complete=True)

        def ground_assignment(self, assignment):
            return self._verified()

        def preflight_action(self, assignment, action):
            return self._verified()

        def reground_assignment(self, assignment, trigger):
            return self._verified()

        def record_learning(self, assignment, outcome):
            from riverview_core.worker_adapter import KnowledgeResult, KnowledgeStatus
            return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)

    def test_scoped_authenticated_execution_persists_attributed_idempotent_result(self):
        token = self.token
        payload = "deterministic local task"
        first = self.worker.execute_sha256(
            self.assignment, self.worker_id, token, self.lease["generation"],
            "attempt:one", payload)
        self.assertEqual(first["status"], "succeeded")
        self.assertEqual(first["result"]["sha256"], hashlib.sha256(payload.encode()).hexdigest())
        replay = self.worker.execute_sha256(
            self.assignment, self.worker_id, token, self.lease["generation"],
            "attempt:one", payload)
        self.assertEqual(replay["attempt_id"], first["attempt_id"])
        self.assertEqual(replay["result"], first["result"])
        from riverview_core.worker_adapter import WorkerAdapterError
        with self.assertRaisesRegex(WorkerAdapterError, "idempotency key collision"):
            self.worker.execute_sha256(self.assignment, self.worker_id, token,
                                       self.lease["generation"], "attempt:one", "different input")
        with self.worker.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT credential_sha256 FROM worker_registry WHERE worker_id=%s",
                        (self.worker_id,))
            saved_credential = bytes(cur.fetchone()["credential_sha256"])
            self.assertNotEqual(saved_credential, token.encode())
            cur.execute("SELECT worker_id,lease_generation,status FROM worker_attempts WHERE attempt_id=%s",
                        (first["attempt_id"],))
            attempt = cur.fetchone()
            self.assertEqual((attempt["worker_id"], attempt["lease_generation"], attempt["status"]),
                             (self.worker_id, self.lease["generation"], "succeeded"))
            cur.execute("SELECT result,result_sha256 FROM worker_results WHERE attempt_id=%s",
                        (first["attempt_id"],))
            result = cur.fetchone()
            self.assertEqual(result["result"], first["result"])
            self.assertEqual(result["result_sha256"], first["result_sha256"])

    def test_continuous_worker_persists_structured_artifact_and_independent_verification(self):
        from riverview_core.worker_adapter import (
            ContinuousWorker, VerificationResult, VerificationStatus)

        assignment_id = self.ready_assignment(objective="objective:local:label-auth-message")
        inference_worker_id = "worker-inference-" + uuid4().hex
        inference_token = self.register_as(
            inference_worker_id, [self.worker.LOCAL_INFERENCE_CAPABILITY], self.scope)
        prompt = ("Classify the diagnostic text. Return exactly one lowercase label: "
                  "auth or resource. Text: credential expired during authentication.")

        class GroundedProvider(WorkerAdapterTests.VerifiedProvider):
            pass

        engine = ContinuousWorker(
            self.worker, inference_worker_id, inference_token,
            knowledge=GroundedProvider(prompt),
            action=lambda assignment, grounded: {
                "provider": "test-local-model", "model": "fixture-model-v1",
                "output": "auth", "finish_reason": "stop"},
            action_capability=self.worker.LOCAL_INFERENCE_CAPABILITY,
            action_effect_class="retry_safe", lease_seconds=60)
        outcome = engine.run_once()
        self.assertEqual(outcome["status"], "AWAITING_VERIFICATION")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "awaiting_verification")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT capability,input_sha256,status FROM worker_attempts WHERE attempt_id=%s",
                        (outcome["attempt_id"],))
            attempt = cur.fetchone()
            cur.execute("SELECT result,result_sha256 FROM worker_results WHERE attempt_id=%s",
                        (outcome["attempt_id"],))
            artifact = cur.fetchone()
        self.assertEqual(attempt["capability"], self.worker.LOCAL_INFERENCE_CAPABILITY)
        self.assertEqual(attempt["status"], "succeeded")
        self.assertEqual(artifact["result"]["output"], "auth")
        canonical = json.dumps(artifact["result"], sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), artifact["result_sha256"].strip())

        verifier_id = "worker-inference-verifier-" + uuid4().hex
        verifier_token = self.register_as(verifier_id, ["assignment.verify.v1"], self.scope)

        class IndependentVerifier:
            REVISION = "local-inference-test-verifier-1"
            def verify(self, assignment, attempt_row, result):
                accepted = (result.get("provider") == "test-local-model"
                            and result.get("model") == "fixture-model-v1"
                            and result.get("output") == "auth"
                            and result.get("finish_reason") == "stop"
                            and attempt_row.get("status") == "succeeded")
                criteria = {"distinct_executor_result": accepted,
                            "expected_classification": result.get("output") == "auth"}
                return VerificationResult(
                    VerificationStatus.ACCEPTED if all(criteria.values()) else
                    VerificationStatus.REJECTED, criteria,
                    (f"urn:rv:attempt:{attempt_row['attempt_id']}",), self.REVISION,
                    "fixture artifact independently matches expected classification")

        verified = self.worker.verify_attempt(
            assignment_id, outcome["attempt_id"], verifier_id, verifier_token,
            IndependentVerifier(), idempotency_key="verify-local-inference-" + assignment_id)
        self.assertEqual(verified.status, VerificationStatus.ACCEPTED)
        self.assertEqual(self.ledger.get(assignment_id)["state"], "completed")
        self.assertEqual(self.worker.incomplete_attempts(), [])

    def test_wrong_credential_capability_and_scope_are_rejected(self):
        from riverview_core.worker_adapter import WorkerAuthorizationError
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.claim_next(self.worker_id, self.token, capability="unsupported.v1")
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.claim_next(self.worker_id, "wrong-token")
        other_id = "worker-other-" + uuid4().hex
        other_token = self.register_as(
            other_id, ["deterministic.sha256.v1"], "grant:other")
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.execute_sha256(self.assignment, other_id, other_token,
                                       self.lease["generation"], "bad-scope", "x")
        other_assignment = "worker-task-other-" + uuid4().hex
        self.ledger.create(other_assignment, "engineering", f"create-{other_assignment}",
                           authority_ref="grant:other", objective_ref="objective:other",
                           actor_id="resident:test")
        self.ledger.transition(other_assignment, "ready", "intake", f"ready-{other_assignment}",
                               actor_id="event-processor")
        scoped_claim = self.worker.claim_next(other_id, other_token, lease_seconds=30)
        self.assertEqual(scoped_claim["assignment"]["id"], other_assignment)

    def test_missing_registration_grant_and_revoked_execution_grant_fail_closed(self):
        import secrets
        from riverview_core.worker_adapter import WorkerAuthorizationError

        with self.assertRaises(WorkerAuthorizationError):
            self.worker.register_worker(
                "worker-ungranted-" + uuid4().hex,
                ["deterministic.sha256.v1"], self.scope,
                credential=secrets.token_urlsafe(32))
        digest = hashlib.sha256(self.token.encode("utf-8")).digest()
        self.admin.execute("UPDATE principal_credentials SET revoked_at=clock_timestamp() "
                           "WHERE credential_sha256=%s", (digest,))
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.execute_sha256(
                self.assignment, self.worker_id, self.token,
                self.lease["generation"], "revoked-action:" + uuid4().hex, "must not run")
        with self.worker.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT count(*) AS attempts FROM worker_attempts WHERE assignment_id=%s",
                        (self.assignment,))
            self.assertEqual(cur.fetchone()["attempts"], 0)

    def test_interrupted_attempt_is_durably_visible_for_worker_loss_detection(self):
        token = self.token
        with self.worker.ledger.db.transaction():
            with self.worker.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO worker_attempts
                    (attempt_id,assignment_id,worker_id,lease_generation,capability,
                     idempotency_key,input_sha256,status)
                    VALUES (%s,%s,%s,%s,'deterministic.sha256.v1','attempt:interrupted',%s,'running')""",
                    (uuid4(), self.assignment, self.worker_id, self.lease["generation"],
                     hashlib.sha256(b"interrupted").hexdigest()))
        incomplete = self.worker.incomplete_attempts()
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0]["worker_id"], self.worker_id)
        self.assertEqual(incomplete[0]["assignment_id"], self.assignment)
        self.assertEqual(len(token), 43)

    def _interrupt_child_after_intent(self, *, effect_class):
        import multiprocessing
        import os
        import signal
        from riverview_core.worker_adapter import PostgresRecoveryCoordinator

        ctx = multiprocessing.get_context("fork")
        parent, child = ctx.Pipe(duplex=False)
        process = ctx.Process(target=_crash_after_intent,
            args=(DSN, self.schema, self.assignment, self.worker_id, self.token,
                  self.lease["generation"], effect_class, child))
        process.start()
        child.close()
        try:
            self.assertTrue(parent.poll(10), "subprocess did not persist its execution intent")
            self.assertTrue(parent.recv())
        finally:
            os.kill(process.pid, signal.SIGKILL)
            process.join(10)
            parent.close()
        self.assertEqual(process.exitcode, -signal.SIGKILL)
        self.admin.execute("UPDATE assignment_leases SET expires_at=acquired_at+interval '1 microsecond' WHERE assignment_id=%s",
                           (self.assignment,))
        recovery = PostgresRecoveryCoordinator(DSN, schema=self.schema)
        try:
            return recovery.reconcile_expired()
        finally:
            recovery.close()

    def test_forced_worker_termination_requeues_only_durable_retry_safe_intent(self):
        result = self._interrupt_child_after_intent(effect_class="retry_safe")
        self.assertEqual(result, [{"assignment_id": self.assignment,
                                   "lease_generation": self.lease["generation"],
                                   "decision": "retry_safe", "resulting_state": "ready"}])
        self.assertEqual(self.ledger.get(self.assignment)["state"], "ready")
        claimed = self.worker.claim_next(self.worker_id, self.token, lease_seconds=30)
        self.assertEqual(claimed["assignment"]["id"], self.assignment)
        self.assertGreater(claimed["lease"]["generation"], self.lease["generation"])
        with self.worker.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT decision FROM worker_recovery_records WHERE assignment_id=%s",
                        (self.assignment,))
            self.assertEqual(cur.fetchone()["decision"], "retry_safe")

    def test_confirmed_legacy_codex_preexecution_failure_requeues_once(self):
        import tempfile
        from riverview_core.worker_adapter import PostgresRecoveryCoordinator

        objective_id = "objective:legacy-codex:" + uuid4().hex
        assignment_id = self.ready_assignment(objective=objective_id)
        self.admin.execute("""INSERT INTO grace_objectives
            (objective_id,request,scope_ref,submitter_id,acceptance_criteria,status,
             evidence,assignment_id,source_revision,source_sha256)
            VALUES (%s,'synthetic bounded fixture',%s,'steward:test','[]'::jsonb,
                    'WORK_ORDER_CREATED','{"status":"VERIFIED"}'::jsonb,%s,%s,%s)""",
            (objective_id, self.scope, assignment_id, "a" * 40, "b" * 64))
        worker_id = "worker-codex-recovery-" + uuid4().hex
        credential = self.register_as(
            worker_id, ["engineering.codex-cli-artifact.v1"], self.scope)
        claim = self.worker.claim_next(worker_id, credential, assignment_id=assignment_id,
            lease_seconds=60, capability="engineering.codex-cli-artifact.v1")
        generation = claim["lease"]["generation"]
        self.worker.start_assignment(assignment_id, worker_id, credential, generation,
            capability="engineering.codex-cli-artifact.v1")
        intent_id = self.worker.begin_execution_intent(
            assignment_id, worker_id, credential, generation,
            f"continuous:{assignment_id}:{generation}", effect_class="external_uncertain",
            capability="engineering.codex-cli-artifact.v1")
        self.worker.mark_execution_intent(intent_id, "outcome_unknown",
                                          failure_class="CodexActionFailure")
        self.worker.scheduler.transition_with_lease(assignment_id, "awaiting_steward",
            "ACTION_OUTCOME_UNKNOWN", f"fixture-unknown:{assignment_id}:{generation}",
            worker_id, generation)
        self.admin.execute("""UPDATE assignment_leases
            SET acquired_at=clock_timestamp()-interval '2 seconds',
                expires_at=clock_timestamp()-interval '1 second'
            WHERE assignment_id=%s""",
                           (assignment_id,))
        with tempfile.TemporaryDirectory(prefix="rv-codex-recovery-") as directory:
            artifact_root = Path(directory) / "artifacts"
            artifact_root.mkdir(mode=0o700)
            recovery = PostgresRecoveryCoordinator(DSN, schema=self.schema, max_retries=3)
            try:
                result = recovery.reconcile_confirmed_codex_preexecution_failures(
                    repository_revision="c" * 40, artifact_root=artifact_root,
                    legacy_git_refusal_verified=True)
                self.assertEqual(result, [{"assignment_id": assignment_id,
                    "intent_id": str(intent_id), "lease_generation": generation,
                    "decision": "retry_safe", "resulting_state": "ready"}])
                self.assertEqual(recovery.reconcile_confirmed_codex_preexecution_failures(
                    repository_revision="c" * 40, artifact_root=artifact_root,
                    legacy_git_refusal_verified=True), [])
                resumed = self.worker.claim_next(worker_id, credential,
                    assignment_id=assignment_id, lease_seconds=30,
                    capability="engineering.codex-cli-artifact.v1")
                self.assertEqual(resumed["assignment"]["id"], assignment_id)
                second_generation = resumed["lease"]["generation"]
                self.worker.start_assignment(assignment_id, worker_id, credential,
                    second_generation, capability="engineering.codex-cli-artifact.v1")
                second_intent = self.worker.begin_execution_intent(
                    assignment_id, worker_id, credential, second_generation,
                    f"continuous:{assignment_id}:{second_generation}",
                    effect_class="external_uncertain",
                    capability="engineering.codex-cli-artifact.v1")
                self.worker.mark_execution_intent(second_intent, "failed",
                                                  failure_class="CodexActionFailure")
                self.worker.scheduler.transition_with_lease(assignment_id, "blocked",
                    "WORKER_PRE_EXECUTION_FAILED",
                    f"fixture-preexecution:{assignment_id}:{second_generation}",
                    worker_id, second_generation)
                self.admin.execute("""UPDATE assignment_leases
                    SET acquired_at=clock_timestamp()-interval '2 seconds',
                        expires_at=clock_timestamp()-interval '1 second'
                    WHERE assignment_id=%s""", (assignment_id,))
                recovered_preexecution = recovery.reconcile_confirmed_codex_preexecution_failures(
                    repository_revision="c" * 40, artifact_root=artifact_root,
                    legacy_git_refusal_verified=True)
                self.assertEqual(recovered_preexecution, [{
                    "assignment_id": assignment_id, "intent_id": str(second_intent),
                    "lease_generation": second_generation,
                    "decision": "retry_safe", "resulting_state": "ready"}])
                self.assertEqual(recovery.reconcile_confirmed_codex_preexecution_failures(
                    repository_revision="c" * 40, artifact_root=artifact_root,
                    legacy_git_refusal_verified=True), [])
                last_evidence = self.admin.execute("""SELECT payload->'recovery_evidence'
                    FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1""",
                    (assignment_id,)).fetchone()[0]
                self.assertEqual(last_evidence["proof"],
                    "durable_worker_preexecution_failure_before_cli_launch")
                self.assertEqual(last_evidence["execution_process_started"], False)
            finally:
                recovery.close()
        ready = self.ledger.get(assignment_id)
        self.assertEqual(ready["state"], "ready")
        self.assertEqual(ready["process_graph_id"],
                         "rv:postgres-ledger:assignment-lifecycle")
        self.assertEqual(ready["process_node_id"],
                         "rv:postgres-ledger:assignment-lifecycle:ready")
        intent = self.admin.execute("SELECT status FROM worker_execution_intents WHERE intent_id=%s",
                                    (intent_id,)).fetchone()
        self.assertEqual(intent[0], "retry_scheduled")
        recorded = self.admin.execute("SELECT count(*) FROM worker_recovery_records WHERE assignment_id=%s",
                                      (assignment_id,)).fetchone()[0]
        self.assertEqual(recorded, 2)
        event = self.admin.execute("""SELECT payload->'recovery_evidence'
            FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1""",
            (assignment_id,)).fetchone()[0]
        self.assertEqual(event["execution_process_started"], False)
        self.assertEqual(event["assignment_attempt_absent"], True)
        self.assertEqual(event["assignment_artifact_absent"], True)
        transition = self.admin.execute("""SELECT payload->>'process_node_id'
            FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1""",
            (assignment_id,)).fetchone()[0]
        self.assertEqual(transition, "rv:postgres-ledger:assignment-lifecycle:ready")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "ready")

    def test_preexecution_codex_failure_is_not_misreported_as_unknown(self):
        from riverview_core.worker_adapter import ContinuousWorker
        assignment_id = self.ready_assignment(objective="objective:known-preexecution")
        class KnownPreExecutionFailure(RuntimeError):
            execution_started = False
        def fail_before_process(_assignment, _grounded):
            raise KnownPreExecutionFailure("repository_preflight_failed")
        engine = ContinuousWorker(self.worker, self.worker_id, self.token,
            knowledge=self.VerifiedProvider(), action=fail_before_process,
            action_effect_class="external_uncertain",
            action_capability="deterministic.sha256.v1")
        result = engine.run_once(assignment_id=assignment_id)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "blocked")
        intent = self.admin.execute("SELECT status FROM worker_execution_intents WHERE assignment_id=%s",
                                    (assignment_id,)).fetchone()
        self.assertEqual(intent[0], "failed")

    def test_killed_external_action_is_not_replayed_and_unrelated_work_continues(self):
        import multiprocessing
        import os
        import signal
        from riverview_core.worker_adapter import ContinuousWorker

        assignment_id = self.ready_assignment(objective="objective:external-effect")
        worker_id = "worker-crash-" + uuid4().hex
        credential = self.register_as(
            worker_id, ["deterministic.sha256.v1"], self.scope)
        ctx = multiprocessing.get_context("fork")
        parent, child = ctx.Pipe(duplex=False)
        process = ctx.Process(target=_crash_after_effect,
            args=(DSN, self.schema, assignment_id, worker_id, credential, child))
        process.start()
        child.close()
        try:
            self.assertTrue(parent.poll(10), "external test action did not commit before interruption")
            self.assertEqual(parent.recv(), "effect_committed")
        finally:
            os.kill(process.pid, signal.SIGKILL)
            process.join(10)
            parent.close()
        self.assertEqual(process.exitcode, -signal.SIGKILL)
        self.admin.execute("UPDATE assignment_leases SET expires_at=acquired_at+interval '1 microsecond' WHERE assignment_id=%s",
                           (assignment_id,))
        unrelated = self.ready_assignment(objective="objective:unrelated-after-recovery")
        worker = ContinuousWorker(self.worker, worker_id, credential,
                                  knowledge=self.VerifiedProvider())
        resumed = worker.run_once()  # Restart boundary: recovery runs before the claim.
        self.assertEqual(resumed["assignment_id"], unrelated)
        self.assertEqual(resumed["status"], "AWAITING_VERIFICATION")
        self.assertEqual(self.ledger.get(assignment_id)["state"], "awaiting_steward")
        records = self.admin.execute("SELECT decision FROM worker_recovery_records WHERE assignment_id=%s",
                                     (assignment_id,)).fetchone()[0]
        self.assertEqual(records, "outcome_unknown")
        count = self.admin.execute("SELECT count(*) FROM recovery_test_effects WHERE assignment_id=%s",
                                   (assignment_id,)).fetchone()[0]
        self.assertEqual(count, 1)
        count = self.admin.execute("SELECT count(*) FROM recovery_test_effects WHERE assignment_id=%s",
                                   (assignment_id,)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_durable_result_is_preserved_for_verification_after_restart(self):
        import multiprocessing
        import os
        import signal
        from riverview_core.worker_adapter import PostgresRecoveryCoordinator
        ctx = multiprocessing.get_context("fork")
        parent, child = ctx.Pipe(duplex=False)
        process = ctx.Process(target=_crash_after_result,
            args=(DSN, self.schema, self.assignment, self.worker_id, self.token,
                  self.lease["generation"], child))
        process.start()
        child.close()
        try:
            self.assertTrue(parent.poll(10), "worker did not commit result before interruption")
            attempt_id = parent.recv()
        finally:
            os.kill(process.pid, signal.SIGKILL)
            process.join(10)
            parent.close()
        self.assertEqual(process.exitcode, -signal.SIGKILL)
        self.admin.execute("UPDATE assignment_leases SET expires_at=acquired_at+interval '1 microsecond' WHERE assignment_id=%s",
                           (self.assignment,))
        recovery = PostgresRecoveryCoordinator(DSN, schema=self.schema)
        try:
            outcomes = recovery.reconcile_expired()
        finally:
            recovery.close()
        self.assertEqual(outcomes[0]["decision"], "result_preserved")
        self.assertEqual(self.ledger.get(self.assignment)["state"], "awaiting_verification")
        saved = self.admin.execute("SELECT result_sha256 FROM worker_results WHERE attempt_id=%s",
                                   (attempt_id,)).fetchone()[0]
        self.assertEqual(len(saved.strip()), 64)
        verifier_id = "verifier-recovery-" + uuid4().hex
        verifier_token = self.register_as(
            verifier_id, ["assignment.verify.v1"], self.scope)
        from riverview_core.worker_adapter import DeterministicSha256Verifier
        decision = self.worker.verify_attempt(
            self.assignment, attempt_id, verifier_id, verifier_token,
            DeterministicSha256Verifier(),
            idempotency_key="verify-after-recovery:" + uuid4().hex)
        self.assertEqual(decision.status.value, "ACCEPTED", dict(decision.criteria))
        self.assertEqual(self.ledger.get(self.assignment)["state"], "completed")
        recovery = PostgresRecoveryCoordinator(DSN, schema=self.schema)
        try:
            self.assertEqual(recovery.reconcile_expired(), [])
        finally:
            recovery.close()
        self.assertEqual(self.ledger.get(self.assignment)["state"], "completed")

    def test_unavailable_grounding_waits_without_blocking_later_verified_assignment(self):
        from riverview_core.worker_adapter import ContinuousWorker

        waiting_id = self.ready_assignment(objective="objective:needs-evidence")
        successful_id = self.ready_assignment(objective="objective:verified")
        waiting_engine = ContinuousWorker(self.worker, self.worker_id, self.token)
        waiting = waiting_engine.run_once()
        self.assertEqual(waiting["assignment_id"], waiting_id)
        self.assertEqual(waiting["status"], "WAITING_FOR_EVIDENCE")
        self.assertEqual(waiting["knowledge_status"], "UNAVAILABLE")
        self.assertEqual(self.ledger.get(waiting_id)["state"], "blocked")
        self.assertEqual(self.ledger.get(waiting_id)["workflow_step"], "WAITING_FOR_EVIDENCE")

        waiting_engine.knowledge = self.VerifiedProvider("knowledge-directed action")
        successful = waiting_engine.run_once()
        self.assertEqual(successful["assignment_id"], successful_id)
        self.assertEqual(successful["status"], "AWAITING_VERIFICATION")
        self.assertEqual(self.ledger.get(successful_id)["state"], "awaiting_verification")
        payload = "knowledge-directed action"
        expected = hashlib.sha256(payload.encode()).hexdigest()
        result = {"sha256": expected, "utf8_bytes": len(payload.encode())}
        encoded_result = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(successful["result_sha256"],
                         hashlib.sha256(encoded_result).hexdigest())

        with self.worker.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT operation,status,source_references,source_revision,
                                  source_sha256,retrieval_complete
                           FROM knowledge_observations WHERE assignment_id=%s
                           ORDER BY recorded_at,observation_id""", (waiting_id,))
            waiting_rows = cur.fetchall()
            self.assertEqual([(r["operation"], r["status"]) for r in waiting_rows],
                             [("ground_assignment", "UNAVAILABLE")])
            cur.execute("""SELECT operation,status,source_references,source_revision,
                                  source_sha256,retrieval_complete
                           FROM knowledge_observations WHERE assignment_id=%s""", (successful_id,))
            successful_rows = cur.fetchall()
            self.assertEqual({r["operation"] for r in successful_rows},
                             {"ground_assignment", "preflight_action",
                              "reground_assignment", "record_learning"})
            self.assertTrue(all(r["status"] in {"VERIFIED", "UNAVAILABLE"}
                                for r in successful_rows))
            verified = next(r for r in successful_rows
                            if r["operation"] == "preflight_action")
            self.assertEqual(verified["source_references"],
                             ["repo://docs/architecture/CORE_CONTRACT.md"])
            self.assertEqual(verified["source_revision"], "1.0.0")
            self.assertEqual(verified["source_sha256"].strip(), "a" * 64)
            self.assertIs(verified["retrieval_complete"], True)

    def test_concurrent_scoped_worker_cycles_progress_independently(self):
        from concurrent.futures import ThreadPoolExecutor
        from riverview_core.worker_adapter import ContinuousWorker, PostgresWorkerAdapter

        assignments = []
        workers = []
        for index in range(2):
            scope = f"grant:parallel:{index}"
            assignment_id = self.ready_assignment(scope=scope)
            worker_id = f"worker-parallel-{uuid4().hex}"
            credential = self.register_as(worker_id,
                          ["deterministic.sha256.v1"], scope)
            adapter = PostgresWorkerAdapter(DSN, schema=self.schema)
            workers.append((adapter, ContinuousWorker(
                adapter, worker_id, credential, knowledge=self.VerifiedProvider(f"action-{index}"))))
            assignments.append(assignment_id)

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(engine.run_once) for _, engine in workers]
                outcomes = [future.result(timeout=10) for future in futures]
            self.assertEqual({outcome["assignment_id"] for outcome in outcomes}, set(assignments))
            self.assertTrue(all(outcome["status"] == "AWAITING_VERIFICATION"
                                for outcome in outcomes))
            self.assertTrue(all(self.ledger.get(assignment)["state"] == "awaiting_verification"
                                for assignment in assignments))
        finally:
            for adapter, _ in workers:
                adapter.close()

    def test_provider_timeout_is_unavailable_and_does_not_hold_assignment_loop(self):
        from riverview_core.worker_adapter import ContinuousWorker

        class SlowProvider(self.VerifiedProvider):
            def __init__(self):
                self.started = threading.Event()
                self.release = threading.Event()
                self.finished = threading.Event()

            def ground_assignment(self, assignment):
                self.started.set()
                self.release.wait(timeout=5)
                self.finished.set()
                return self._verified()

        waiting_id = self.ready_assignment(objective="objective:slow-provider")
        provider = SlowProvider()
        engine = ContinuousWorker(self.worker, self.worker_id, self.token,
                                  knowledge=provider, knowledge_timeout_seconds=0.01)
        result_box = []
        errors = []

        def run():
            try:
                result_box.append(engine.run_once())
            except Exception as exc:
                errors.append(exc)

        execution = threading.Thread(target=run)
        execution.start()
        self.assertTrue(provider.started.wait(timeout=3), "provider call did not start")
        execution.join(timeout=3)
        provider_finished_before_release = provider.finished.is_set()
        provider.release.set()
        execution.join(timeout=3)
        self.assertFalse(execution.is_alive(), "worker remained blocked on provider")
        self.assertEqual(errors, [])
        self.assertFalse(provider_finished_before_release,
                         "worker waited for the provider's delayed response")
        provider.finished.wait(timeout=1)
        self.assertEqual(len(result_box), 1)
        result = result_box[0]
        self.assertEqual(result["status"], "WAITING_FOR_EVIDENCE")
        self.assertEqual(result["knowledge_status"], "UNAVAILABLE")
        self.assertEqual(self.ledger.get(waiting_id)["workflow_step"], "WAITING_FOR_EVIDENCE")

    def _execute_to_verification(self, payload="independent verification target"):
        outcome = self.worker.execute_sha256(
            self.assignment, self.worker_id, self.token, self.lease["generation"],
            "verify:" + uuid4().hex, payload)
        self.ledger.transition(self.assignment, "awaiting_verification", "worker_result",
                               "await-verification:" + uuid4().hex,
                               actor_id=f"worker:{self.worker_id}")
        verifier_id = "verifier-" + uuid4().hex
        credential = self.register_as(
            verifier_id, ["assignment.verify.v1"], self.scope)
        from riverview_core.worker_adapter.verifier import DeterministicSha256Verifier
        return outcome, verifier_id, credential, DeterministicSha256Verifier()

    def test_independent_verifier_accepts_valid_result_and_gates_completion(self):
        import psycopg
        from riverview_core.ledger import TransitionError
        outcome, verifier_id, credential, verifier = self._execute_to_verification()
        with self.assertRaises(psycopg.Error):
            with self.worker.ledger.db.transaction():
                with self.worker.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    cur.execute("UPDATE assignments SET state='completed' WHERE id=%s",
                                (self.assignment,))
        with self.assertRaisesRegex(TransitionError, "persisted independent verification"):
            self.ledger.transition(self.assignment, "completed", "claimed-success",
                                   "complete-without-evidence", actor_id="caller", verified=True)
        verification_key = "verify-valid:" + uuid4().hex
        result = self.worker.verify_attempt(
            self.assignment, outcome["attempt_id"], verifier_id, credential, verifier,
            idempotency_key=verification_key)
        self.assertEqual(result.status.value, "ACCEPTED")
        self.assertEqual(self.ledger.get(self.assignment)["state"], "completed")
        replay = self.worker.verify_attempt(
            self.assignment, outcome["attempt_id"], verifier_id, credential, verifier,
            idempotency_key=verification_key)
        self.assertEqual(replay.status.value, "ACCEPTED")
        with self.worker.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT decision,executor_id,verifier_id,criteria,evidence_references
                           FROM verification_records WHERE attempt_id=%s""",
                        (outcome["attempt_id"],))
            row = cur.fetchone()
        self.assertEqual(row["decision"], "ACCEPTED")
        self.assertEqual(row["executor_id"], self.worker_id)
        self.assertEqual(row["verifier_id"], verifier_id)
        self.assertTrue(all(row["criteria"].values()))
        self.assertGreaterEqual(len(row["evidence_references"]), 1)

    def test_tampered_result_is_rejected_and_routed_to_rework(self):
        outcome, verifier_id, credential, verifier = self._execute_to_verification()
        with self.worker.ledger.db.transaction():
            with self.worker.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("UPDATE worker_results SET result=jsonb_set(result,'{sha256}',to_jsonb(%s::text)) WHERE attempt_id=%s",
                            ("0" * 64, outcome["attempt_id"]))
        decision = self.worker.verify_attempt(
            self.assignment, outcome["attempt_id"], verifier_id, credential, verifier,
            idempotency_key="verify-tampered:" + uuid4().hex)
        self.assertEqual(decision.status.value, "REJECTED")
        self.assertEqual(self.ledger.get(self.assignment)["state"], "rework_required")

    def test_pinned_repository_provider_drives_worker_artifact_and_independent_verification(self):
        import shutil
        import subprocess
        import tempfile
        from riverview_core.worker_adapter import ContinuousWorker
        from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider
        from riverview_core.worker_adapter.verifier import DeterministicSha256Verifier

        source_root = Path(__file__).resolve().parents[1]
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repository = Path(temporary.name) / "pinned-source"
        repository.mkdir()
        source_paths = RepositoryKnowledgeProvider.CONTRACTS[
            RepositoryKnowledgeProvider.WORKER_CONTRACT]
        for relative in source_paths:
            destination = repository / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, destination)
        subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.name", "Riverview test"], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repository), "commit", "-qm", "pinned worker contract"], check=True)
        commit = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"],
                                check=True, capture_output=True, text=True).stdout.strip()
        provider = RepositoryKnowledgeProvider(repository, commit)
        contract_ref = RepositoryKnowledgeProvider.WORKER_CONTRACT
        assignment_id = "repository-knowledge-" + uuid4().hex
        self.ledger.create(assignment_id, "engineering", f"create-{assignment_id}",
                           authority_ref=self.scope, objective_ref="objective:verify-worker-contract",
                           actor_id="resident:test", contract_ref=contract_ref)
        self.ledger.transition(assignment_id, "ready", "intake", f"ready-{assignment_id}",
                               actor_id="event-processor")
        executor_id = "worker-repository-" + uuid4().hex
        executor_credential = self.register_as(
            executor_id, ["deterministic.sha256.v1"], self.scope)

        def create_artifact(assignment, grounding):
            self.assertEqual(assignment["contract_ref"], contract_ref)
            self.assertEqual(grounding.status.value, "VERIFIED")
            self.assertTrue(grounding.retrieval_complete)
            return grounding.value["documents"][0]["content"]

        execution = ContinuousWorker(
            self.worker, executor_id, executor_credential, knowledge=provider,
            action=create_artifact, action_effect_class="retry_safe").run_once()
        self.assertEqual(execution["status"], "AWAITING_VERIFICATION")
        verifier_id = "verifier-repository-" + uuid4().hex
        verifier_credential = self.register_as(
            verifier_id, ["assignment.verify.v1"], self.scope)
        decision = self.worker.verify_attempt(
            assignment_id, execution["attempt_id"], verifier_id, verifier_credential,
            DeterministicSha256Verifier(),
            idempotency_key=f"repository-verification:{execution['attempt_id']}")
        self.assertEqual(decision.status.value, "ACCEPTED", dict(decision.criteria))
        self.assertEqual(self.ledger.get(assignment_id)["state"], "completed")
        self.assertNotEqual(executor_id, verifier_id)
        with self.worker.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT operation,status,source_revision,retrieval_complete
                           FROM knowledge_observations WHERE assignment_id=%s
                           ORDER BY recorded_at,observation_id""", (assignment_id,))
            observations = cur.fetchall()
            cur.execute("SELECT result FROM worker_results WHERE attempt_id=%s",
                        (execution["attempt_id"],))
            artifact = cur.fetchone()["result"]
        grounded = [row for row in observations
                    if row["operation"] in {"ground_assignment", "preflight_action",
                                             "reground_assignment"}]
        self.assertEqual({row["operation"] for row in grounded},
                         {"ground_assignment", "preflight_action", "reground_assignment"})
        self.assertTrue(all(row["status"] == "VERIFIED" and
                            row["source_revision"] == commit and
                            row["retrieval_complete"] is True for row in grounded))
        self.assertEqual(set(artifact), {"sha256", "utf8_bytes"})
        self.assertEqual(len(artifact["sha256"]), 64)
        self.assertGreater(artifact["utf8_bytes"], 0)

    def test_worker_service_registration_is_idempotent_and_exact(self):
        from riverview_core.worker_adapter.service import (
            WorkerServiceConfigurationError, ensure_registered,
        )

        ensure_registered(self.worker, self.worker_id, self.token,
                          ("deterministic.sha256.v1",), self.scope)
        with self.assertRaises(WorkerServiceConfigurationError):
            ensure_registered(self.worker, self.worker_id, self.token,
                              ("assignment.verify.v1",), self.scope)
        with self.assertRaises(WorkerServiceConfigurationError):
            ensure_registered(self.worker, self.worker_id, self.token,
                              ("deterministic.sha256.v1",), "work-order:other")
        with self.worker.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT count(*) AS n FROM worker_registry WHERE worker_id=%s",
                        (self.worker_id,))
            self.assertEqual(cur.fetchone()["n"], 1)

    def test_repository_test_assignment_persists_real_file_and_independent_reverification(self):
        import hashlib
        import json
        import shutil
        import subprocess
        import tempfile
        from riverview_core.worker_adapter import ContinuousWorker
        from riverview_core.worker_adapter.engineering_artifact import (
            CAPABILITY, OBJECTIVE_REF, RepositoryContractTestAction,
        )
        from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider
        from riverview_core.worker_adapter.verifier import RepositoryContractTestVerifier

        source_root = Path(__file__).resolve().parents[1]
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        source_repo, package = base / "source-repo", base / "immutable-release"
        source_repo.mkdir()
        source_paths = RepositoryKnowledgeProvider.CONTRACTS[
            RepositoryKnowledgeProvider.WORKER_CONTRACT]
        test_path = "tests/test_repository_knowledge.py"
        for relative in [*source_paths, test_path]:
            destination = source_repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, destination)
        subprocess.run(["git", "-C", str(source_repo), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(source_repo), "config", "user.name", "Riverview test"], check=True)
        subprocess.run(["git", "-C", str(source_repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(source_repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(source_repo), "commit", "-qm", "pinned engineering test package"], check=True)
        commit = subprocess.run(["git", "-C", str(source_repo), "rev-parse", "HEAD"],
                                check=True, capture_output=True, text=True).stdout.strip()
        package.mkdir()
        for relative in [*source_paths, test_path]:
            destination = package / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_repo / relative, destination)
        (package / "SOURCE_COMMIT").write_text(commit + "\n", encoding="ascii")
        manifest_paths = [*source_paths, test_path, "SOURCE_COMMIT"]
        rows = []
        for relative in manifest_paths:
            raw = (package / relative).read_bytes()
            rows.append(f"{hashlib.sha256(raw).hexdigest()}  {relative}")
        (package / "PACKAGE_SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="ascii")
        for path in sorted(package.rglob("*"), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        package.chmod(0o555)
        def restore_fixture_permissions():
            for item in package.rglob("*"):
                item.chmod(0o755 if item.is_dir() else 0o644)
            package.chmod(0o755)
        self.addCleanup(restore_fixture_permissions)
        artifacts = base / "artifacts"
        artifacts.mkdir(mode=0o700)

        provider = RepositoryKnowledgeProvider(package, commit)
        assignment_id = "engineering-test-" + uuid4().hex
        contract_ref = RepositoryKnowledgeProvider.WORKER_CONTRACT
        self.ledger.create(assignment_id, "engineering", f"create-{assignment_id}",
                           authority_ref=self.scope, objective_ref=OBJECTIVE_REF,
                           actor_id="steward:test", contract_ref=contract_ref)
        self.ledger.transition(assignment_id, "ready", "intake", f"ready-{assignment_id}",
                               actor_id="event-processor")
        executor_id = "worker-engineering-test-" + uuid4().hex
        executor_credential = self.register_as(executor_id, [CAPABILITY], self.scope)
        action_impl = RepositoryContractTestAction(package, artifacts, commit)
        action_failures = []
        def action(assignment, grounding):
            try:
                return action_impl(assignment, grounding)
            except Exception as exc:
                action_failures.append(type(exc).__name__ + ":" + str(exc))
                raise
        execution = ContinuousWorker(
            self.worker, executor_id, executor_credential, knowledge=provider,
            action=action, action_effect_class="retry_safe",
            action_capability=CAPABILITY).run_once()
        self.assertEqual(execution["status"], "AWAITING_VERIFICATION",
                         {"action_failures": action_failures,
                          "worker_failure_type": execution.get("failure_type"),
                          "execution": execution})

        result_row = self.admin.execute(
            "SELECT result,result_sha256 FROM worker_results WHERE attempt_id=%s",
            (execution["attempt_id"],)).fetchone()
        artifact = result_row[0]
        artifact_path = artifacts / artifact["artifact_name"]
        self.assertTrue(artifact_path.is_file())
        self.assertEqual(hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                         artifact["artifact_sha256"])
        report = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")
        self.assertGreater(report["test_count"], 0)
        self.assertIn("Ran ", report["output"])

        verifier_id = "verifier-engineering-test-" + uuid4().hex
        verifier_credential = self.register_as(
            verifier_id, ["assignment.verify.v1"], self.scope)
        verifier = RepositoryContractTestVerifier(artifacts, commit, package)
        decision = self.worker.verify_attempt(
            assignment_id, execution["attempt_id"], verifier_id, verifier_credential,
            verifier, idempotency_key=f"engineering-test-verification:{execution['attempt_id']}")
        self.assertEqual(decision.status.value, "ACCEPTED", dict(decision.criteria))
        self.assertTrue(all(decision.criteria.values()))
        self.assertNotEqual(executor_id, verifier_id)
        self.assertEqual(self.ledger.get(assignment_id)["state"], "completed")
        self.assertTrue(decision.criteria["independent_test_rerun_matches_report"])
        observations = self.admin.execute(
            "SELECT operation,status,source_revision,retrieval_complete FROM knowledge_observations "
            "WHERE assignment_id=%s ORDER BY recorded_at,observation_id", (assignment_id,)).fetchall()
        self.assertEqual({row[0] for row in observations},
                         {"ground_assignment", "preflight_action", "reground_assignment", "record_learning"})
        self.assertTrue(all(row[1] == "VERIFIED" and row[2] == commit
                            and row[3] is True for row in observations[:3]))

    def test_executor_identity_cannot_verify_its_own_attempt(self):
        from riverview_core.worker_adapter import WorkerAuthorizationError
        outcome = self.worker.execute_sha256(
            self.assignment, self.worker_id, self.token, self.lease["generation"],
            "verify-self:" + uuid4().hex, "self verification")
        self.ledger.transition(self.assignment, "awaiting_verification", "worker_result",
                               "await-self:" + uuid4().hex,
                               actor_id=f"worker:{self.worker_id}")
        with self.worker.ledger.db.transaction():
            with self.worker.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("UPDATE worker_registry SET capabilities=capabilities || '[\"assignment.verify.v1\"]'::jsonb WHERE worker_id=%s",
                            (self.worker_id,))
        self.admin.execute("""INSERT INTO authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES (%s,%s,'assignment.verify',%s,'steward:test','rv.policy:self-verification-test.v1')""",
            ("test:self-verify:" + self.worker_id,
             "worker-principal:" + self.worker_id, self.scope))
        from riverview_core.worker_adapter.verifier import DeterministicSha256Verifier
        with self.assertRaisesRegex(WorkerAuthorizationError, "cannot verify its own"):
            self.worker.verify_attempt(
                self.assignment, outcome["attempt_id"], self.worker_id, self.token,
                DeterministicSha256Verifier(), idempotency_key="verify-self-result")
