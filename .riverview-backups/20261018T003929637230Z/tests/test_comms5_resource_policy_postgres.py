"""Isolated PostgreSQL acceptance of durable Comms5 worker policy enforcement."""
import hashlib
import os
import unittest
from uuid import uuid4

from riverview_core.postgres_migrations import apply_migrations
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.assignment_scheduler import PostgresAssignmentScheduler
from riverview_core.resident_execution.comms5_operations import Comms5Operations

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class Comms5ResourcePolicyPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        self.psycopg, self.sql = psycopg, sql
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        if not self.admin.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='riverview_core')").fetchone()[0]:
            self.admin.execute("CREATE ROLE riverview_core NOLOGIN")
            self.created_role = True
        else:
            self.created_role = False
        core = ROOT / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        for component in ("assignment_scheduler", "worker_adapter", "cme",
                          "institutional_authority", "resident_execution"):
            apply_migrations(DSN, schema=self.schema,
                migrations_dir=core / component / "migrations")
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.scheduler = PostgresAssignmentScheduler(DSN, schema=self.schema)
        class Authorizer:
            @staticmethod
            def require_principal(_cur, principal, action, scope):
                if principal != "steward:test" or action != "assignment.create" or scope != "work-order:engineering":
                    raise PermissionError("grant denied")
                return {"grant_id": "grant:assignment-create-test"}
        from riverview_core.resident_execution.pipeline import GraceExecutionPipeline
        self.pipeline = object.__new__(GraceExecutionPipeline)
        self.pipeline.ledger = self.ledger
        self.pipeline.authorizer = Authorizer()
        self.operations = Comms5Operations(object(), object(), self.pipeline)
        self.worker_ids = ("worker:engineering-a", "worker:engineering-b")
        for worker in self.worker_ids:
            self.admin.execute(self.sql.SQL("""INSERT INTO {}.worker_registry
                (worker_id,credential_sha256,capabilities,scope_ref,active)
                VALUES (%s,%s,%s::jsonb,'work-order:engineering',TRUE)""").format(
                    self.sql.Identifier(self.schema)), (worker, hashlib.sha256(worker.encode()).digest(),
                    '["engineering.codex-cli-artifact.v1"]'))

    def tearDown(self):
        from psycopg import sql
        self.scheduler.close()
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
            sql.Identifier(self.schema)))
        if self.created_role:
            self.admin.execute("DROP ROLE IF EXISTS riverview_core")
        self.admin.close()

    def test_policy_persists_audit_lock_and_selects_only_target_worker(self):
        result = self.operations.execute("comms5_set_resource_policy", {
            "mode": "target", "parameters": {"target_seat": self.worker_ids[0],
                "fallback": False}, "explicit_steward_confirmation": True,
            "rationale": "Bounded policy integration test", "expected_revision": 0},
            principal_id="steward:test")
        self.assertEqual(result["status"], "policy_set")
        self.assertEqual(result["revision"], 1)
        locked = self.operations.execute("comms5_set_resource_policy_lock", {
            "locked": True, "explicit_steward_confirmation": True,
            "rationale": "Test lock"}, principal_id="steward:test")
        self.assertTrue(locked["locked"])
        with self.assertRaises(PermissionError):
            self.operations.execute("comms5_set_resource_policy", {
                "mode": "automatic", "parameters": {},
                "explicit_steward_confirmation": True}, principal_id="steward:test")
        with self.assertRaises(PermissionError):
            self.operations.execute("comms5_set_resource_policy_lock", {
                "locked": False, "explicit_steward_confirmation": True},
                principal_id="resident:unauthorized")

        assignment = "assignment:resource-policy-test"
        self.ledger.create(assignment, self.worker_ids[0], "create-policy-test",
            authority_ref="work-order:engineering", objective_ref="objective:policy-test",
            actor_id="steward:test")
        self.ledger.transition(assignment, "ready", "intake", "ready-policy-test",
            actor_id="event-processor")
        self.assertIsNone(self.scheduler.claim_next(self.worker_ids[1], scope_ref="work-order:engineering",
            required_capability="engineering.codex-cli-artifact.v1"))
        claim = self.scheduler.claim_next(self.worker_ids[0], scope_ref="work-order:engineering",
            required_capability="engineering.codex-cli-artifact.v1")
        self.assertEqual(claim["assignment_id"], assignment)
        status = self.operations.execute("comms5_resource_policy_status", {},
            principal_id="steward:test")
        self.assertEqual(status["policy_state"], "configured")
        self.assertTrue(status["policy"]["locked"])
        self.assertIn("worker_selected", [event["event_type"] for event in status["policy_events"]])

    def test_stale_base_revalidation_queues_scoped_successor_without_accepting_failure(self):
        objective_id = "objective:stale-base-test"
        assignment_id = "assignment:stale-base-test"
        proposal = {"summary": "bounded source update", "steps": [{
            "step_id": "step:source", "objective": "Update bounded source",
            "acceptance_criteria": ["preserve scope"], "depends_on": [],
            "execution_capability": "engineering.codex-cli-artifact.v1",
            "authorized_paths": [], "test_targets": []}]}
        evidence = {"status": "VERIFIED", "retrieval_complete": True,
            "source_references": ["repo://fixture"], "source_sha256": "a" * 64}
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.grace_objectives
            (objective_id,request,scope_ref,submitter_id,acceptance_criteria,status,evidence,
             proposal,assignment_id,source_revision,source_sha256)
            VALUES (%s,'bounded stale base objective','work-order:engineering','steward:test',
             '[\"preserve scope\"]'::jsonb,'WORK_ORDER_CREATED',%s::jsonb,%s::jsonb,%s,%s,%s)""").format(
                self.sql.Identifier(self.schema)), (objective_id, __import__("json").dumps(evidence),
                __import__("json").dumps(proposal), assignment_id, "a" * 40, "a" * 64))
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.grace_objective_steps
            (objective_id,step_id,step_order,step_objective,acceptance_criteria,depends_on,status,assignment_id)
            VALUES (%s,'step:source',1,'Update bounded source','[\"preserve scope\"]'::jsonb,'[]'::jsonb,'blocked',%s)""").format(
                self.sql.Identifier(self.schema)), (objective_id, assignment_id))
        self.ledger.create(assignment_id, self.worker_ids[0], "create-stale-base-test",
            authority_ref="work-order:engineering", objective_ref=objective_id,
            actor_id="steward:test", workflow_id="grace.objective-work-order.v1")
        self.ledger.transition(assignment_id, "ready", "dispatch", "ready-stale-base-test",
            actor_id="event-processor")
        self.ledger.transition(assignment_id, "running", "execute", "running-stale-base-test",
            actor_id=self.worker_ids[0])
        self.ledger.transition(assignment_id, "blocked", "WORKER_PRE_EXECUTION_FAILED",
            "blocked-stale-base-test", actor_id=self.worker_ids[0])
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.worker_execution_intents
            (assignment_id,worker_id,lease_generation,capability,effect_class,idempotency_key,
             status,started_at,finished_at,failure_class)
            VALUES (%s,%s,1,'engineering.codex-cli-artifact.v1','external_uncertain',
             'stale-base-intent-test','failed',clock_timestamp()-interval '1 second',
             clock_timestamp(),'CodexActionFailure:repository_revision_mismatch')""").format(
                self.sql.Identifier(self.schema)), (assignment_id, self.worker_ids[0]))
        args = {"work_order_id": assignment_id, "idempotency_key": "retry-stale-base-1",
            "explicit_steward_confirmation": True,
            "infrastructure_repair_evidence": ["repo://verified-base/" + "b" * 40],
            "client_id": "test", "client_type": "chat", "client_name": "test"}
        result = self.operations.execute("comms5_revalidate_and_queue_work", args,
            principal_id="steward:test")
        self.assertEqual(result["status"], "queued_for_cme")
        self.assertFalse(result["dispatched"])
        self.assertTrue(result["verification_required"])
        repeated = self.operations.execute("comms5_revalidate_and_queue_work", args,
            principal_id="steward:test")
        self.assertEqual(repeated["status"], "already_queued_for_cme")
        self.assertEqual(repeated["successor_step_id"], result["successor_step_id"])
        self.assertEqual(self.ledger.get(assignment_id)["state"], "blocked")
        self.assertIsNotNone(self.pipeline.dispatchable_step(objective_id))


if __name__ == "__main__":
    unittest.main()
