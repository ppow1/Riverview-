# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/continuous.py
# Component: WORKER-ADAPTER
# Revision: 1.0.5
# Purpose: Execute isolated durable assignment cycles without global task coupling
# Execution Model: Repeatable poll cycle; durable claims and outcomes in PostgreSQL
# Observability: Assignment state, knowledge observations, attempts, and results
# Dependencies: Psycopg; M1.2 ledger; M1.4 scheduler; worker-adapter contract
# Authority: One assignment per cycle; no action without VERIFIED grounding/preflight
# Changed: 2026-10-10 UTC | RV-M2.3-001 | Persist effect class before invoking worker action
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Fail-closed worker cycles; assignment-local outcomes never halt later polls."""

import json
import logging
import threading
import time

from .adapter import PostgresWorkerAdapter, WorkerAdapterError
from .knowledge import KnowledgeResult, KnowledgeStatus, UnavailableKnowledgeProvider

LOG = logging.getLogger("riverview.continuous_worker")


class ContinuousWorker:
    """Poll one assignment at a time; callers may run independent workers concurrently."""

    ACTION = "deterministic.sha256.v1"

    def __init__(self, adapter: PostgresWorkerAdapter, worker_id: str,
                 credential: str, *, knowledge=None, lease_seconds=30,
                 action=None, action_effect_class=None, poll_interval=0.5,
                 knowledge_timeout_seconds=5.0):
        if poll_interval <= 0 or knowledge_timeout_seconds <= 0:
            raise ValueError("poll and knowledge timeout values must be positive")
        self.adapter = adapter
        self.worker_id = worker_id
        self.credential = credential
        self.knowledge = knowledge or UnavailableKnowledgeProvider()
        self.lease_seconds = lease_seconds
        self.action = action or self._default_action
        self.action_effect_class = (action_effect_class or
                                    ("retry_safe" if action is None else "external_uncertain"))
        if self.action_effect_class not in {"retry_safe", "external_uncertain"}:
            raise ValueError("action_effect_class must be retry_safe or external_uncertain")
        self.poll_interval = poll_interval
        self.knowledge_timeout_seconds = knowledge_timeout_seconds
        self._knowledge_slots = threading.BoundedSemaphore(4)

    @staticmethod
    def _default_action(assignment, grounded):
        value = grounded.value
        if not isinstance(value, str):
            value = assignment["objective_ref"]
        return value

    def _provider_call(self, operation, *args):
        """Bound wait time; late provider results are discarded and never authorize."""
        if not self._knowledge_slots.acquire(blocking=False):
            return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)
        result_box = []
        done = threading.Event()

        def invoke():
            try:
                result = getattr(self.knowledge, operation)(*args)
                result_box.append(result if isinstance(result, KnowledgeResult) else
                                  KnowledgeResult(KnowledgeStatus.UNVERIFIED))
            except Exception:
                result_box.append(KnowledgeResult(KnowledgeStatus.UNAVAILABLE))
            finally:
                self._knowledge_slots.release()
                done.set()

        threading.Thread(target=invoke, name=f"knowledge-{operation}", daemon=True).start()
        if not done.wait(self.knowledge_timeout_seconds):
            return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)
        return result_box[0]

    def _record(self, assignment, operation, result, *, action=None):
        return self.adapter.record_knowledge_observation(
            assignment["id"], self.worker_id, operation, result, action=action)

    def reground_assignment(self, assignment, trigger):
        """Refresh context after a caller-observed change, failure, restoration, or handoff."""
        result = self._provider_call("reground_assignment", assignment, trigger)
        self._record(assignment, "reground_assignment", result)
        return result

    def _wait_for_evidence(self, assignment, lease, operation, result, *, action=None):
        self._record(assignment, operation, result, action=action)
        self.adapter.scheduler.transition_with_lease(
            assignment["id"], "blocked", "WAITING_FOR_EVIDENCE",
            f"knowledge-wait:{assignment['id']}:{lease['generation']}:{operation}",
            self.worker_id, lease["generation"])
        return {"status": "WAITING_FOR_EVIDENCE", "assignment_id": assignment["id"],
                "operation": operation, "knowledge_status": result.status.value}

    def run_once(self):
        """Process at most one assignment; a blocked assignment cannot block a later cycle."""
        claim = self.adapter.claim_next(self.worker_id, self.credential,
                                        lease_seconds=self.lease_seconds)
        if claim is None:
            return {"status": "IDLE"}
        assignment, lease = claim["assignment"], claim["lease"]
        grounded = self._provider_call("ground_assignment", assignment)
        if grounded.status is not KnowledgeStatus.VERIFIED:
            return self._wait_for_evidence(assignment, lease, "ground_assignment", grounded)
        self._record(assignment, "ground_assignment", grounded)

        preflight = self._provider_call("preflight_action", assignment, self.ACTION)
        if preflight.status is not KnowledgeStatus.VERIFIED:
            return self._wait_for_evidence(assignment, lease, "preflight_action", preflight,
                                           action=self.ACTION)
        self._record(assignment, "preflight_action", preflight, action=self.ACTION)

        self.adapter.start_assignment(assignment["id"], self.worker_id,
                                      self.credential, lease["generation"])
        current_assignment = self.adapter.ledger.get(assignment["id"])
        trigger = "context_restored" if lease["generation"] > 1 else "before_action"
        if (current_assignment["version"] > assignment["version"] + 1):
            trigger = "assignment_changed"
        regrounded = self._provider_call("reground_assignment", current_assignment, trigger)
        self._record(current_assignment, "reground_assignment", regrounded, action=self.ACTION)
        if regrounded.status is not KnowledgeStatus.VERIFIED:
            self.adapter.scheduler.transition_with_lease(
                assignment["id"], "blocked", "WAITING_FOR_EVIDENCE",
                f"knowledge-wait:{assignment['id']}:{lease['generation']}:reground_assignment",
                self.worker_id, lease["generation"])
            return {"status": "WAITING_FOR_EVIDENCE", "assignment_id": assignment["id"],
                    "operation": "reground_assignment",
                    "knowledge_status": regrounded.status.value}

        intent_id = self.adapter.begin_execution_intent(
            assignment["id"], self.worker_id, self.credential, lease["generation"],
            f"continuous:{assignment['id']}:{lease['generation']}",
            effect_class=self.action_effect_class)
        try:
            data = self.action(assignment, regrounded)
            if not isinstance(data, str):
                raise WorkerAdapterError("worker action must return text for deterministic capability")
            outcome = self.adapter.execute_sha256(
                assignment["id"], self.worker_id, self.credential, lease["generation"],
                f"continuous:{assignment['id']}:{lease['generation']}", data,
                intent_id=intent_id)
            self.adapter.scheduler.transition_with_lease(
                assignment["id"], "awaiting_verification", "worker_result_recorded",
                f"continuous-result:{assignment['id']}:{lease['generation']}",
                self.worker_id, lease["generation"])
        except Exception as exc:
            # Assignment-local action failure is durable and does not escape the poll loop.
            intent_outcome = ("outcome_unknown" if
                              self.action_effect_class == "external_uncertain" else "failed")
            self.adapter.mark_execution_intent(intent_id, intent_outcome,
                                               failure_class=type(exc).__name__)
            failure = {"failure_type": type(exc).__name__}
            latest = self.adapter.ledger.get(assignment["id"])
            if latest:
                self.reground_assignment(latest, "action_failure")
            learned = self._provider_call("record_learning", assignment, failure)
            self._record(assignment, "record_learning", learned)
            current = self.adapter.ledger.get(assignment["id"])
            if current and current["state"] == "running":
                self.adapter.scheduler.transition_with_lease(
                    assignment["id"],
                    "awaiting_steward" if intent_outcome == "outcome_unknown" else "blocked",
                    "ACTION_OUTCOME_UNKNOWN" if intent_outcome == "outcome_unknown" else "worker_action_failed",
                    f"continuous-failure:{assignment['id']}:{lease['generation']}",
                    self.worker_id, lease["generation"])
            return {"status": "FAILED", "assignment_id": assignment["id"],
                    "failure_type": type(exc).__name__}

        learning = self._provider_call("record_learning", assignment,
                                       {"status": outcome["status"],
                                        "result_sha256": outcome["result_sha256"]})
        self._record(assignment, "record_learning", learning)
        return {"status": "AWAITING_VERIFICATION", "assignment_id": assignment["id"],
                "attempt_id": str(outcome["attempt_id"]),
                "result_sha256": outcome["result_sha256"]}

    def run_forever(self, *, shutdown_requested, sleep=time.sleep):
        """Poll continuously; shutdown is delegated to an explicit Steward control callback."""
        if not callable(shutdown_requested):
            raise TypeError("shutdown_requested must be an explicit Steward control callback")
        while not shutdown_requested():
            try:
                result = self.run_once()
            except Exception as exc:
                LOG.error(json.dumps({"event": "worker_cycle_failed",
                                      "worker_id": self.worker_id,
                                      "failure_type": type(exc).__name__}, sort_keys=True))
                sleep(self.poll_interval)
                continue
            if result["status"] == "IDLE":
                sleep(self.poll_interval)
