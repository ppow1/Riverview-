# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_worker_adapter.py
# Component: WORKER-ADAPTER
# Revision: 1.0.7
# Purpose: Verify scoped dispatch, fail-closed knowledge, independent outcomes, and recovery
# Execution Model: PostgreSQL integration tests using isolated schemas
# Observability: Durable assignment, worker, attempt, result, and knowledge rows
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL test database
# Authority: Creates and drops only unique rvtest_* schemas
# Changed: 2026-10-10 UTC | RV-M2.2-001 | Add independent outcome verification coverage
# Contracts: docs/development/M2.1-001_REVISION_RECORD.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""M2.1 PostgreSQL integration tests; never target the shared app schema."""

import hashlib
import json
import os
import time
import unittest
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


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
        root = Path(__file__).resolve().parents[1] / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=root / "assignment_scheduler/migrations")
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=root / "worker_adapter/migrations")
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        from riverview_core.worker_adapter import PostgresWorkerAdapter
        self.worker = PostgresWorkerAdapter(DSN, schema=self.schema)
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
        return self.worker.register_worker(
            self.worker_id,
            capabilities or ["deterministic.sha256.v1"],
            scope or self.scope)

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
        self.assertEqual(self.worker.incomplete_attempts(), [])

    def test_wrong_credential_capability_and_scope_are_rejected(self):
        from riverview_core.worker_adapter import WorkerAuthorizationError
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.claim_next(self.worker_id, self.token, capability="unsupported.v1")
        with self.assertRaises(WorkerAuthorizationError):
            self.worker.claim_next(self.worker_id, "wrong-token")
        other_id = "worker-other-" + uuid4().hex
        other_token = self.worker.register_worker(
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
            credential = self.worker.register_worker(worker_id,
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
            def ground_assignment(self, assignment):
                time.sleep(0.15)
                return self._verified()

        waiting_id = self.ready_assignment(objective="objective:slow-provider")
        engine = ContinuousWorker(self.worker, self.worker_id, self.token,
                                  knowledge=SlowProvider(), knowledge_timeout_seconds=0.01)
        started = time.monotonic()
        result = engine.run_once()
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.10)
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
        credential = self.worker.register_worker(
            verifier_id, ["assignment.verify.v1"], self.scope)
        from riverview_core.worker_adapter.verifier import DeterministicSha256Verifier
        return outcome, verifier_id, credential, DeterministicSha256Verifier()

    def test_independent_verifier_accepts_valid_result_and_gates_completion(self):
        import psycopg
        outcome, verifier_id, credential, verifier = self._execute_to_verification()
        with self.assertRaises(psycopg.Error):
            self.ledger.transition(self.assignment, "completed", "claimed-success",
                                   "complete-without-evidence", actor_id="caller", verified=True)
        result = self.worker.verify_attempt(
            self.assignment, outcome["attempt_id"], verifier_id, credential, verifier,
            idempotency_key="verify-valid:" + uuid4().hex)
        self.assertEqual(result.status.value, "ACCEPTED")
        self.assertEqual(self.ledger.get(self.assignment)["state"], "completed")
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
        from riverview_core.worker_adapter.verifier import DeterministicSha256Verifier
        with self.assertRaisesRegex(WorkerAuthorizationError, "cannot verify its own"):
            self.worker.verify_attempt(
                self.assignment, outcome["attempt_id"], self.worker_id, self.token,
                DeterministicSha256Verifier(), idempotency_key="verify-self-result")
