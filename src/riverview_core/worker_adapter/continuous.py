# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/continuous.py
# Component: WORKER-ADAPTER
# Revision: 1.1.5
# Purpose: Execute bounded capability work with pinned source-digest provenance
# Execution Model: Repeatable poll cycle; durable claims and outcomes in PostgreSQL
# Observability: Assignment state, knowledge observations, attempts, and results
# Dependencies: Psycopg; M1.2 ledger; M1.4 scheduler; worker-adapter contract
# Authority: One assignment per cycle; no action without VERIFIED grounding/preflight
# Changed: 2026-10-10 UTC | RV-M2.3-001 | Persist effect class before invoking worker action
# Changed: 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Route registered action capability and persist structured artifacts
# Changed: 2026-10-11 UTC | RV-M33-GROUNDED-PROVENANCE-BOUND | Persist source digest and references instead of duplicating full grounded documents in the attempt input
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Support configured bounded lease-recovery retry limit
# Changed: 2026-10-13 UTC | RV-SUPERVISED-CODEX-DISPATCH-001 | Add a single-assignment claim without reconciling unrelated leases
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Keep proven pre-execution failures out of the unknown external-effect state
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-BOUNDED-RETRY-001 | Persist sanitized retryable Codex failures as blocked no-artifact outcomes
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001 | Reground and safely requeue the same Codex assignment after a recoverable evidence wait
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001-GUARD-REVIEW | Revalidate both evidence and action preflight before same-assignment recovery
# Changed: 2026-10-16 UTC | RV-GRACE-SCOPE-LEASE-RECONCILE-001 | Authenticate recovery scope and heartbeat leases throughout bounded actions
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Permit bounded source-change retries only through the verified deterministic patch artifact boundary
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Fail-closed worker cycles; assignment-local outcomes never halt later polls."""

import json
import logging
import threading
import time
from contextlib import contextmanager
from collections.abc import Mapping

from .adapter import PostgresWorkerAdapter, WorkerAdapterError
from .knowledge import KnowledgeResult, KnowledgeStatus, UnavailableKnowledgeProvider
from .recovery import PostgresRecoveryCoordinator

LOG = logging.getLogger("riverview.continuous_worker")


class ContinuousWorker:
    """Poll one assignment at a time; callers may run independent workers concurrently."""

    ACTION = "deterministic.sha256.v1"

    def __init__(self, adapter: PostgresWorkerAdapter, worker_id: str,
                 credential: str, *, knowledge=None, lease_seconds=30,
                 action=None, action_effect_class=None, poll_interval=0.5,
                 knowledge_timeout_seconds=5.0, action_capability=None,
                 recovery_max_retries=None):
        if poll_interval <= 0 or knowledge_timeout_seconds <= 0:
            raise ValueError("poll and knowledge timeout values must be positive")
        self.adapter = adapter
        self.worker_id = worker_id
        self.credential = credential
        self.knowledge = knowledge or UnavailableKnowledgeProvider()
        self.lease_seconds = lease_seconds
        self.action = action or self._default_action
        self.action_capability = action_capability or self.ACTION
        if not isinstance(self.action_capability, str) or not self.action_capability:
            raise ValueError("action_capability must be a non-empty string")
        self.action_effect_class = (action_effect_class or
                                    ("retry_safe" if action is None else "external_uncertain"))
        if self.action_effect_class not in {"retry_safe", "external_uncertain"}:
            raise ValueError("action_effect_class must be retry_safe or external_uncertain")
        self.poll_interval = poll_interval
        self.knowledge_timeout_seconds = knowledge_timeout_seconds
        if recovery_max_retries is not None and (
                type(recovery_max_retries) is not int or not 0 <= recovery_max_retries <= 100):
            raise ValueError("recovery_max_retries must be None or an integer from 0 to 100")
        self.recovery_max_retries = recovery_max_retries
        self._knowledge_slots = threading.BoundedSemaphore(4)
        action_timeout = getattr(action, "timeout_seconds", 0)
        self.action_lease_seconds = max(
            lease_seconds,
            int(action_timeout) + 30 if isinstance(action_timeout, (int, float)) else lease_seconds)

    @contextmanager
    def _lease_heartbeat(self, assignment_id, generation):
        """Keep a long bounded action leased while another worker polls recovery."""
        stopped = threading.Event()
        failures = []
        interval = max(0.25, min(5.0, self.action_lease_seconds / 3))

        def maintain():
            while not stopped.wait(interval):
                try:
                    self.adapter.scheduler.heartbeat(
                        assignment_id, self.worker_id, generation,
                        lease_seconds=self.action_lease_seconds)
                except Exception as exc:
                    failures.append(type(exc).__name__)
                    stopped.set()

        thread = threading.Thread(target=maintain, name="assignment-lease-heartbeat",
                                  daemon=True)
        thread.start()
        try:
            yield failures
        finally:
            stopped.set()
            thread.join(timeout=2)

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

    def _resume_verified_waiting_assignment(self, recovery):
        """Requeue at most one same-scope Codex assignment after current evidence verifies."""
        if (self.action_capability != PostgresWorkerAdapter.CODEX_CLI_CAPABILITY or
                not callable(getattr(self.knowledge, "ground_assignment", None))):
            return False
        artifact_root = getattr(getattr(self.action, "adapter", None), "artifact_root", None)
        if artifact_root is None:
            return False
        candidates = self.adapter.waiting_for_evidence(
            self.worker_id, self.credential,
            capability=self.action_capability, limit=1)
        if not candidates:
            return False
        assignment = candidates[0]
        grounded = self._provider_call("ground_assignment", assignment)
        if (grounded.status is not KnowledgeStatus.VERIFIED or
                grounded.retrieval_complete is not True):
            return False
        preflight = self._provider_call("preflight_action", assignment,
                                        self.action_capability)
        if (preflight.status is not KnowledgeStatus.VERIFIED or
                preflight.retrieval_complete is not True):
            return False
        return recovery.resume_verified_waiting_for_evidence(
            assignment["id"], grounded, preflight, worker_id=self.worker_id,
            worker_scope=assignment["authority_ref"], artifact_root=artifact_root)

    def run_once(self, *, assignment_id=None):
        """Recover normally, or claim one explicitly selected assignment only."""
        if assignment_id is None:
            scope_ref = self.adapter.authenticated_scope(
                self.worker_id, self.credential, self.action_capability)
            recovery = PostgresRecoveryCoordinator(self.adapter.dsn, schema=self.adapter.schema,
                                                   max_retries=self.recovery_max_retries)
            try:
                recovery.reconcile_expired(scope_ref=scope_ref, worker_id=self.worker_id)
                late_artifact_reconcile = getattr(
                    self.action, "reconcile_late_artifacts", None)
                if callable(late_artifact_reconcile):
                    late_artifact_reconcile(
                        recovery, worker_adapter=self.adapter, worker_id=self.worker_id,
                        credential=self.credential, capability=self.action_capability,
                        scope_ref=scope_ref)
                reconcile_action = getattr(self.action, "reconcile_retryable_no_artifact_failures", None)
                if callable(reconcile_action):
                    reconcile_action(recovery, scope_ref=scope_ref,
                                     worker_id=self.worker_id)
                self._resume_verified_waiting_assignment(recovery)
            finally:
                recovery.close()
        claim = self.adapter.claim_next(self.worker_id, self.credential,
                                        capability=self.action_capability,
                                        lease_seconds=self.action_lease_seconds,
                                        assignment_id=assignment_id)
        if claim is None:
            return {"status": "IDLE"}
        assignment, lease = claim["assignment"], claim["lease"]
        grounded = self._provider_call("ground_assignment", assignment)
        if grounded.status is not KnowledgeStatus.VERIFIED:
            return self._wait_for_evidence(assignment, lease, "ground_assignment", grounded)
        self._record(assignment, "ground_assignment", grounded)

        preflight = self._provider_call("preflight_action", assignment,
                                        self.action_capability)
        if preflight.status is not KnowledgeStatus.VERIFIED:
            return self._wait_for_evidence(assignment, lease, "preflight_action", preflight,
                                           action=self.action_capability)
        self._record(assignment, "preflight_action", preflight,
                     action=self.action_capability)

        self.adapter.start_assignment(assignment["id"], self.worker_id,
                                      self.credential, lease["generation"],
                                      capability=self.action_capability)
        current_assignment = self.adapter.ledger.get(assignment["id"])
        trigger = "context_restored" if lease["generation"] > 1 else "before_action"
        if (current_assignment["version"] > assignment["version"] + 1):
            trigger = "assignment_changed"
        regrounded = self._provider_call("reground_assignment", current_assignment, trigger)
        self._record(current_assignment, "reground_assignment", regrounded,
                     action=self.action_capability)
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
            effect_class=self.action_effect_class,
            capability=self.action_capability)
        try:
            with self._lease_heartbeat(assignment["id"], lease["generation"]) as heartbeat_failures:
                data = self.action(assignment, regrounded)
                if heartbeat_failures:
                    raise WorkerAdapterError("assignment lease heartbeat was lost during action")
            attempt_key = f"continuous:{assignment['id']}:{lease['generation']}"
            if isinstance(data, str) and self.action_capability == self.ACTION:
                outcome = self.adapter.execute_sha256(
                    assignment["id"], self.worker_id, self.credential, lease["generation"],
                    attempt_key, data, intent_id=intent_id)
            else:
                if isinstance(data, str):
                    data = {"output": data}
                if not isinstance(data, Mapping):
                    raise WorkerAdapterError("artifact worker action must return a JSON object")
                input_data = json.dumps({
                    "assignment_id": assignment["id"],
                    "objective_ref": assignment.get("objective_ref"),
                    "contract_ref": assignment.get("contract_ref"),
                    "knowledge_status": regrounded.status.value,
                    "source_references": list(regrounded.source_references),
                    "source_revision": regrounded.source_revision,
                    "source_sha256": regrounded.source_sha256,
                    "retrieval_complete": regrounded.retrieval_complete,
                }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                outcome = self.adapter.execute_artifact(
                    assignment["id"], self.worker_id, self.credential, lease["generation"],
                    attempt_key, input_data, dict(data),
                    capability=self.action_capability, intent_id=intent_id)
            self.adapter.scheduler.transition_with_lease(
                assignment["id"], "awaiting_verification", "worker_result_recorded",
                f"continuous-result:{assignment['id']}:{lease['generation']}",
                self.worker_id, lease["generation"])
        except Exception as exc:
            # Assignment-local action failure is durable and does not escape the poll loop.
            # A Codex adapter failure explicitly marked before process launch has
            # no external effect. Keep it blocked and diagnosable rather than
            # misreporting an unknown outcome that requires Steward adjudication.
            pre_execution_failure = (
                self.action_effect_class == "external_uncertain" and
                getattr(exc, "execution_started", None) is False)
            retryable_without_artifact = (
                self.action_effect_class in {"external_uncertain", "retry_safe"} and
                self.action_capability in {"engineering.codex-cli-artifact.v1",
                                           "engineering.codex-cli-source-change.v1"} and
                type(exc).__name__ == "CodexActionFailure" and
                getattr(exc, "retryable_without_durable_artifact", None) is True)
            intent_outcome = ("failed" if (pre_execution_failure or retryable_without_artifact) else
                              "outcome_unknown" if
                              self.action_effect_class == "external_uncertain" else "failed")
            safe_code = getattr(exc, "code", None)
            failure_marker = type(exc).__name__
            if (retryable_without_artifact and isinstance(safe_code, str) and
                    len(safe_code) <= 64 and safe_code.isascii() and
                    all(char.islower() or char.isdigit() or char == "_" for char in safe_code)):
                failure_marker += ":" + safe_code
            self.adapter.mark_execution_intent(intent_id, intent_outcome,
                                               failure_class=failure_marker)
            failure = {"failure_type": type(exc).__name__}
            if isinstance(safe_code, str) and len(safe_code) <= 64 and safe_code.isascii():
                failure["failure_code"] = safe_code
            if retryable_without_artifact:
                failure["durable_artifact_created"] = False
            LOG.warning(json.dumps({"event": "worker_action_failed",
                "assignment_id": assignment["id"], "failure_type": type(exc).__name__,
                "failure_code": safe_code if isinstance(safe_code, str) and
                    len(safe_code) <= 64 and safe_code.isascii() else None,
                "execution_started": getattr(exc, "execution_started", None),
                "durable_artifact_created": False if retryable_without_artifact else None},
                sort_keys=True))
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
                    "ACTION_OUTCOME_UNKNOWN" if intent_outcome == "outcome_unknown" else
                    "WORKER_RETRYABLE_NO_ARTIFACT" if retryable_without_artifact else
                    "WORKER_PRE_EXECUTION_FAILED" if pre_execution_failure else "worker_action_failed",
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
