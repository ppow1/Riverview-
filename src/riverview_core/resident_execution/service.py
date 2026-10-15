# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/service.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.7
# Purpose: Reconcile durable Grace work orders through existing CME worker contracts
# Execution Model: Persistent scheduled poll over PostgreSQL objective state
# Observability: Objective events, worker attempts, verification records, dashboard projection
# Dependencies: GraceExecutionPipeline; ContinuousWorker; PostgresWorkerAdapter
# Authority: Exact assignment.create and assignment.verify grants; bounded capability only
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Initial persistent reconciler
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-ISOLATION | Persist verifier errors and avoid per-cycle candidate starvation
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-TEST-SEAM | Keep verifier replaceable behind existing result contract
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Bind optional resident reasoning to durable grounded objectives and office-scoped state
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-FAIR-CYCLE | Attempt at most one grounded objective before continuing CME work
# Changed: 2026-10-13 UTC | RV-SUPERVISED-CODEX-DISPATCH-001 | Add a targeted operator-supervised objective execution cycle
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Select registered execution capability for worker and verification queries
# Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Retry durable verified-result returns to the originating Grace conversation
# Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md
# Tests: tests/test_grace_execution.py; tests/test_resident_reasoning.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Persistent, idempotent orchestration over the existing assignment ledger."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from uuid import uuid4

from ..worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider
from .verifier import BoundedArtifactVerifier
from .worker import CAPABILITY, BoundedLocalCodingWorker

LOG = logging.getLogger("riverview.grace_execution")


class GraceExecutionService:
    """Dispatch authorized proposals, execute one leased action, verify and reconcile.

    Scheduler/event-processor state transitions remain owned by CME. Repeated calls
    are safe: objective state and the stable assignment idempotency key fence duplicate
    dispatch; worker leases and execution intents fence duplicate side effects.
    """

    def __init__(self, pipeline, adapter, worker, *, dispatch_credential,
                 authority_ref, verifier_id, verifier_credential, artifact_root,
                 max_dispatch_failures=3, verifier=None, resident_reasoner=None,
                 resident_token_budget=256, execution_capability=CAPABILITY,
                 conversation_result_publisher=None):
        if not 1 <= max_dispatch_failures <= 10:
            raise ValueError("dispatch failure limit must be between 1 and 10")
        if type(resident_token_budget) is not int or not 1 <= resident_token_budget <= 4096:
            raise ValueError("resident reasoning token budget must be bounded")
        self.pipeline = pipeline
        self.adapter = adapter
        self.worker = worker
        self.dispatch_credential = dispatch_credential
        self.authority_ref = authority_ref
        self.verifier_id = verifier_id
        self.verifier_credential = verifier_credential
        self.verifier = verifier or BoundedArtifactVerifier(artifact_root)
        self.max_dispatch_failures = max_dispatch_failures
        self.resident_reasoner = resident_reasoner
        self.resident_token_budget = resident_token_budget
        if not isinstance(execution_capability, str) or not execution_capability:
            raise ValueError("a registered execution capability is required")
        self.execution_capability = execution_capability
        if conversation_result_publisher is not None and not callable(conversation_result_publisher):
            raise ValueError("conversation result publisher must be callable")
        self.conversation_result_publisher = conversation_result_publisher
        self.instance_id = uuid4()

    def reason_one_grounded_objective(self, objective_id=None):
        """Propose for one verified objective; office authority never dispatches work."""
        if self.resident_reasoner is None or not self.resident_reasoner.providers:
            return False
        from ..resident_reasoning import ReasoningStatus
        rows = self.pipeline.grounded_objectives(scope_ref=self.authority_ref, limit=1,
                                                 objective_id=objective_id)
        if not rows:
            return False
        objective_id = rows[0]["objective_id"]
        try:
            result = self.resident_reasoner.propose(
                objective_id, trigger="persistent_resident_cycle",
                token_budget=self.resident_token_budget)
            if result.status is ReasoningStatus.PROPOSED and result.proposal is not None:
                self.pipeline.record_proposal(
                    objective_id, result.proposal,
                    actor_id="office:" + self.resident_reasoner.office_id)
                return True
        except Exception as exc:
            LOG.warning(json.dumps({"event": "resident_reasoning_cycle_failed",
                "objective_id": objective_id,
                "failure_type": type(exc).__name__}, sort_keys=True))
        return False

    def _heartbeat(self, status, error_type=None):
        """Update the durable external health projection; never logs request content."""
        try:
            with self.pipeline.ledger.db.transaction():
                with self.pipeline.ledger.db.cursor() as cur:
                    self.pipeline.ledger._set_search_path(cur)
                    cur.execute("""INSERT INTO grace_execution_health
                        (service_id,instance_id,status,last_heartbeat_at,last_cycle_at,
                         last_error_type,cycles_completed)
                        VALUES ('grace.execution.v1',%s,%s,clock_timestamp(),clock_timestamp(),%s,
                          CASE WHEN %s IN ('healthy','degraded') THEN 1 ELSE 0 END)
                        ON CONFLICT (service_id) DO UPDATE SET instance_id=EXCLUDED.instance_id,
                          status=EXCLUDED.status,last_heartbeat_at=clock_timestamp(),
                          last_cycle_at=clock_timestamp(),last_error_type=EXCLUDED.last_error_type,
                          cycles_completed=grace_execution_health.cycles_completed+
                            CASE WHEN EXCLUDED.status IN ('healthy','degraded') THEN 1 ELSE 0 END""",
                        (self.instance_id, status, error_type, status))
        except Exception as exc:
            LOG.warning(json.dumps({"event": "grace_heartbeat_write_failed",
                                    "failure_type": type(exc).__name__}, sort_keys=True))

    def _proposed(self, limit=25, objective_id=None):
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT objective_id,scope_ref FROM grace_objectives
                WHERE status='PROPOSED' AND scope_ref=%s
                  AND (%s::text IS NULL OR objective_id=%s)
                ORDER BY created_at,objective_id LIMIT %s""",
                (self.authority_ref, objective_id, objective_id, limit))
            return cur.fetchall()

    def _dispatch_failure_count(self, objective_id):
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT count(*) AS failures FROM grace_objective_events
                WHERE objective_id=%s AND event_type='execution.dispatch_failed'""",
                (objective_id,))
            return int(cur.fetchone()["failures"])

    def _record_dispatch_failure(self, objective_id, error_type, ordinal):
        key = f"grace-dispatch-failure:{objective_id}:{ordinal}"
        with self.pipeline.ledger.db.transaction():
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'execution.dispatch_failed',%s,'service:grace-execution',%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (objective_id, key, json.dumps({"failure_type": error_type,
                     "retry": ordinal, "retry_limit": self.max_dispatch_failures},
                     sort_keys=True, separators=(",", ":"))))

    def dispatch_proposed(self, objective_id=None):
        dispatched = 0
        for row in self._proposed(limit=1 if objective_id else 25,
                                  objective_id=objective_id):
            objective_id = row["objective_id"]
            failures = self._dispatch_failure_count(objective_id)
            if failures >= self.max_dispatch_failures:
                continue
            assignment_id = "assignment:grace:" + hashlib.sha256(
                objective_id.encode("utf-8")).hexdigest()[:40]
            try:
                self.pipeline.authorize_and_dispatch(
                    objective_id, assignment_id, credential=self.dispatch_credential,
                    authority_ref=self.authority_ref,
                    idempotency_key=f"grace-assignment:{objective_id}")
                dispatched += 1
            except Exception as exc:
                self._record_dispatch_failure(objective_id, type(exc).__name__, failures + 1)
                LOG.warning(json.dumps({"event": "grace_dispatch_failed",
                    "objective_id": objective_id, "failure_type": type(exc).__name__,
                    "retry": failures + 1}, sort_keys=True))
        return dispatched

    def verify_one(self, assignment_id=None):
        with self.adapter.ledger.db.cursor() as cur:
            self.adapter.ledger._set_search_path(cur)
            cur.execute("""SELECT a.id AS assignment_id,wa.attempt_id
                ,a.objective_ref
                FROM assignments a JOIN worker_attempts wa ON wa.assignment_id=a.id
                JOIN worker_results wr USING(attempt_id)
                WHERE a.state='awaiting_verification' AND wa.status='succeeded'
                  AND wa.capability=%s
                  AND (%s::text IS NULL OR a.id=%s)
                ORDER BY a.updated_at,wa.started_at,wa.attempt_id LIMIT 25""",
                (self.execution_capability, assignment_id, assignment_id))
            candidates = cur.fetchall()
        for candidate in candidates:
            attempt_id = str(candidate["attempt_id"])
            failure_count = self._verification_failure_count(candidate["objective_ref"], attempt_id)
            if failure_count >= 3:
                continue
            try:
                self.adapter.verify_attempt(candidate["assignment_id"], candidate["attempt_id"],
                    self.verifier_id, self.verifier_credential, self.verifier,
                    idempotency_key=f"grace-verification:{attempt_id}")
                return True
            except Exception as exc:
                self._record_verification_failure(candidate["objective_ref"], attempt_id,
                                                  type(exc).__name__, failure_count + 1)
                LOG.warning(json.dumps({"event": "grace_verification_failed",
                    "assignment_id": candidate["assignment_id"], "attempt_id": attempt_id,
                    "failure_type": type(exc).__name__, "retry": failure_count + 1}, sort_keys=True))
        return False

    def _verification_failure_count(self, objective_id, attempt_id):
        if not objective_id:
            return 0
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT count(*) AS failures FROM grace_objective_events
                WHERE objective_id=%s AND event_type='execution.verification_failed'
                  AND payload->>'attempt_id'=%s""", (objective_id, attempt_id))
            return int(cur.fetchone()["failures"])

    def _record_verification_failure(self, objective_id, attempt_id, error_type, ordinal):
        if not objective_id:
            return
        key = f"grace-verification-failure:{attempt_id}:{ordinal}"
        with self.pipeline.ledger.db.transaction():
            with self.pipeline.ledger.db.cursor() as cur:
                self.pipeline.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'execution.verification_failed',%s,'service:grace-execution',%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (objective_id, key, json.dumps({"attempt_id": attempt_id,
                     "failure_type": error_type, "retry": ordinal, "retry_limit": 3},
                     sort_keys=True, separators=(",", ":"))))

    def reconcile_completions(self, limit=25, objective_id=None):
        with self.pipeline.ledger.db.cursor() as cur:
            self.pipeline.ledger._set_search_path(cur)
            cur.execute("""SELECT objective_id,assignment_id FROM grace_objectives
                WHERE status='WORK_ORDER_CREATED' AND assignment_id IS NOT NULL
                  AND (%s::text IS NULL OR objective_id=%s)
                ORDER BY updated_at LIMIT %s""", (objective_id, objective_id, limit))
            rows = cur.fetchall()
        completed = 0
        for row in rows:
            assignment = self.pipeline.ledger.get(row["assignment_id"])
            if assignment and assignment["state"] == "completed":
                try:
                    self.pipeline.record_verified_completion(row["objective_id"],
                                                             row["assignment_id"])
                    completed += 1
                except Exception as exc:
                    LOG.warning(json.dumps({"event": "grace_completion_reconcile_failed",
                        "objective_id": row["objective_id"],
                        "failure_type": type(exc).__name__}, sort_keys=True))
        return completed

    def publish_conversation_results(self, limit=10):
        """Retry post-verification chat delivery from a durable objective outbox."""
        if self.conversation_result_publisher is None:
            return 0
        published = 0
        for context in self.pipeline.pending_conversation_results(limit=limit):
            try:
                receipt = self.conversation_result_publisher(context)
                if (not isinstance(receipt, dict)
                        or receipt.get("status") not in {"published", "already_published"}):
                    continue
                durable_receipt = {key: receipt.get(key) for key in
                    ("request_id", "provider_id", "served_model", "implementation_id")}
                self.pipeline.record_conversation_result_published(
                    context["objective_id"], durable_receipt)
                published += 1
            except Exception as exc:
                LOG.warning(json.dumps({"event": "grace_conversation_result_return_failed",
                    "objective_id": context.get("objective_id"),
                    "failure_type": type(exc).__name__}, sort_keys=True))
        return published

    def run_once(self):
        """Run bounded dispatch, one existing leased worker poll and verification."""
        try:
            reasoned = self.reason_one_grounded_objective()
            dispatched = self.dispatch_proposed()
            worker_result = self.worker.run_once()
            verified = self.verify_one()
            completed = self.reconcile_completions()
            returned = self.publish_conversation_results()
            self._heartbeat("healthy")
            return {"reasoned": reasoned, "dispatched": dispatched, "worker": worker_result,
                    "verified": verified, "completed": completed, "returned": returned}
        except Exception as exc:
            self._heartbeat("degraded", type(exc).__name__)
            raise

    def execute_supervised_objective(self, objective_id):
        """Execute only one already proposed objective from an operator TTY run."""
        if (not isinstance(objective_id, str) or not re.fullmatch(
                r"objective:[A-Za-z0-9._:-]{1,120}", objective_id)):
            raise ValueError("a bounded objective identity is required")
        try:
            objective = self.pipeline.get_objective(objective_id)
            if (objective is None or objective["scope_ref"] != self.authority_ref or
                    objective["status"] not in {"PROPOSED", "WORK_ORDER_CREATED"}):
                return {"status": "WAITING_FOR_PROPOSAL", "objective_id": objective_id}
            assignment_id = "assignment:grace:" + hashlib.sha256(
                objective_id.encode("utf-8")).hexdigest()[:40]
            if objective["status"] == "PROPOSED":
                self.dispatch_proposed(objective_id)
                objective = self.pipeline.get_objective(objective_id)
            if (objective is None or objective.get("assignment_id") != assignment_id):
                return {"status": "DISPATCH_NOT_AUTHORIZED", "objective_id": objective_id}
            assignment = self.pipeline.ledger.get(assignment_id)
            worker_result = {"status": "ALREADY_COMPLETED" if assignment and
                             assignment["state"] == "completed" else "NOT_READY"}
            if assignment and assignment["state"] in {"ready", "queued"}:
                worker_result = self.worker.run_once(assignment_id=assignment_id)
            verified = self.verify_one(assignment_id)
            completed = self.reconcile_completions(objective_id=objective_id)
            self._heartbeat("healthy")
            return {"status": "COMPLETED" if completed else worker_result.get("status", "PENDING"),
                    "objective_id": objective_id, "assignment_id": assignment_id,
                    "worker": worker_result, "verified": verified, "completed": completed}
        except Exception as exc:
            self._heartbeat("degraded", type(exc).__name__)
            raise

    def run_forever(self, *, shutdown_requested, poll_seconds=1.0, sleep=time.sleep):
        if not callable(shutdown_requested) or not 0.1 <= poll_seconds <= 30:
            raise ValueError("explicit shutdown callback and bounded poll interval required")
        self._heartbeat("starting")
        while not shutdown_requested():
            try:
                result = self.run_once()
                if (not result["reasoned"] and not result["dispatched"] and result["worker"].get("status") == "IDLE"
                        and not result["verified"] and not result["completed"]
                        and not result["returned"]):
                    sleep(poll_seconds)
            except Exception as exc:
                LOG.error(json.dumps({"event": "grace_execution_cycle_failed",
                    "failure_type": type(exc).__name__}, sort_keys=True))
                sleep(poll_seconds)
        self._heartbeat("stopping")


__all__ = ["GraceExecutionService", "TaskRelevantRepositoryKnowledgeProvider",
           "BoundedLocalCodingWorker"]
