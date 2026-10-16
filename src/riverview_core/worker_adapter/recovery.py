# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/recovery.py
# Component: WORKER-ADAPTER
# Revision: 1.2.0
# Purpose: Reconcile expired worker leases without losing or blindly repeating work
# Execution Model: Explicit PostgreSQL recovery pass at worker startup or polling
# Observability: Recovery records and causal assignment transition events
# Dependencies: Psycopg 3; PostgreSQL ledger, scheduler and worker migrations
# Authority: Recovery only; unknown external outcomes wait for Steward decision
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Enforce optional persistent retry ceilings
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Reconcile only legacy Git ownership failures proven to precede Codex launch and all durable effects
# Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Resume bounded, durable no-launch failures after correcting provenance validation
# Contracts: docs/ROADMAP.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Recover expired or specifically proven no-effect assignment failures."""

import hashlib
import os
from pathlib import Path
import re

from ..ledger import TRANSITIONS
from ..postgres_ledger import PostgresLedger, assignment_process_position


class PostgresRecoveryCoordinator:
    """Atomically reconcile expired leases and persist each recovery decision."""

    def __init__(self, dsn, *, schema="public", max_retries=None):
        if max_retries is not None and (type(max_retries) is not int or not 0 <= max_retries <= 100):
            raise ValueError("max_retries must be None or an integer from 0 to 100")
        self.ledger = PostgresLedger(dsn, schema=schema)
        self.schema = schema
        self.max_retries = max_retries

    def close(self):
        self.ledger.close()

    def _transition_locked(self, cur, assignment, to_state, step, key, *, evidence=None):
        from_state = assignment["state"]
        if to_state not in TRANSITIONS[from_state]:
            raise RuntimeError(f"invalid recovery transition: {from_state} -> {to_state}")
        cur.execute("SELECT event_id FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1",
                    (assignment["id"],))
        cause = cur.fetchone()["event_id"]
        payload = {"from": from_state, "to": to_state, "step": step,
                   "actor_id": "cme:recovery", "verified_claim": False,
                   "privacy_domain": "institution"}
        graph_id, node_id = assignment_process_position(to_state)
        payload.update({"process_graph_id": graph_id, "process_node_id": node_id})
        if evidence:
            payload["recovery_evidence"] = evidence
        cur.execute("""UPDATE assignments
            SET state=%s,workflow_step=%s,process_graph_id=%s,process_node_id=%s,
                updated_at=clock_timestamp(),version=version+1 WHERE id=%s""",
            (to_state, step, graph_id, node_id, assignment["id"]))
        self.ledger._append_event(
            cur, assignment_id=assignment["id"], event_type="assignment.transitioned",
            idempotency_key=key, actor_id="cme:recovery",
            authority_ref=assignment["authority_ref"],
            correlation_id=assignment["correlation_id"], causation_id=cause,
            payload_schema="rv.assignment.transitioned.v1", payload=payload)
        assignment["state"] = to_state

    def reconcile_expired(self, *, limit=100):
        """Reconcile expired running leases in isolated, idempotent transactions.

        A durable result is retained for independent verification. An intent
        classified retry-safe is requeued with the old generation fenced. Every
        other incomplete or legacy action goes to ``awaiting_steward`` because
        its external outcome cannot be proven absent.
        """
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        recovered = []
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT a.*,l.generation,l.expires_at,l.worker_id AS lease_worker
                    FROM assignments a JOIN assignment_leases l ON l.assignment_id=a.id
                    WHERE a.state='running' AND l.expires_at<=clock_timestamp()
                    ORDER BY l.expires_at,a.id FOR UPDATE OF a,l SKIP LOCKED LIMIT %s""",
                    (limit,))
                assignments = cur.fetchall()
                for assignment in assignments:
                    generation = assignment["generation"]
                    cur.execute("""SELECT * FROM worker_execution_intents
                        WHERE assignment_id=%s AND lease_generation=%s FOR UPDATE""",
                        (assignment["id"], generation))
                    intent = cur.fetchone()
                    cur.execute("""SELECT a.attempt_id,a.status,r.result_sha256
                        FROM worker_attempts a LEFT JOIN worker_results r USING(attempt_id)
                        WHERE a.assignment_id=%s AND a.lease_generation=%s
                        ORDER BY a.started_at DESC,a.attempt_id DESC
                        LIMIT 1 FOR UPDATE OF a""", (assignment["id"], generation))
                    attempt = cur.fetchone()
                    has_result = bool(attempt and attempt["result_sha256"] is not None)
                    if has_result:
                        decision, target, step = "result_preserved", "awaiting_verification", "RECOVERY_RESULT_PRESERVED"
                    elif intent and intent["effect_class"] == "retry_safe":
                        cur.execute("SELECT count(*) AS retries FROM worker_recovery_records "
                                    "WHERE assignment_id=%s AND decision='retry_safe'",
                                    (assignment["id"],))
                        retries = int(cur.fetchone()["retries"])
                        if self.max_retries is not None and retries >= self.max_retries:
                            decision, target, step = "retry_exhausted", "blocked", "RECOVERY_RETRY_LIMIT"
                        else:
                            decision, target, step = "retry_safe", "ready", "RECOVERY_REQUEUED"
                    else:
                        decision, target, step = "outcome_unknown", "awaiting_steward", "RECOVERY_OUTCOME_UNKNOWN"

                    cur.execute("""INSERT INTO worker_recovery_records
                        (assignment_id,lease_generation,intent_id,attempt_id,decision,
                         previous_state,resulting_state,observed_expiry)
                        VALUES (%s,%s,%s,%s,%s,'running',%s,%s)""",
                        (assignment["id"], generation,
                         intent["intent_id"] if intent else None,
                         attempt["attempt_id"] if attempt else None, decision,
                         target, assignment["expires_at"]))

                    if attempt and not has_result and attempt["status"] == "running":
                        cur.execute("""UPDATE worker_attempts
                            SET status='lease_lost',finished_at=clock_timestamp(),
                                failure_class='ProcessInterrupted'
                            WHERE attempt_id=%s AND status='running'""",
                            (attempt["attempt_id"],))
                    if intent and intent["status"] == "running":
                        new_status = {"retry_safe": "retry_scheduled",
                                      "retry_exhausted": "failed",
                                      "outcome_unknown": "outcome_unknown",
                                      "result_preserved": "succeeded"}[decision]
                        cur.execute("""UPDATE worker_execution_intents
                            SET status=%s,finished_at=clock_timestamp(),
                                failure_class=%s WHERE intent_id=%s""",
                            (new_status, None if has_result else "ProcessInterrupted",
                             intent["intent_id"]))

                    prefix = f"recovery:{assignment['id']}:{generation}"
                    if decision == "retry_safe":
                        self._transition_locked(cur, assignment, "blocked",
                                                "RECOVERY_RETRY_SCHEDULED", prefix + ":blocked")
                        self._transition_locked(cur, assignment, "ready", step, prefix + ":ready")
                    else:
                        self._transition_locked(cur, assignment, target, step,
                                                prefix + ":" + target)
                    recovered.append({"assignment_id": assignment["id"],
                                      "lease_generation": generation,
                                      "decision": decision, "resulting_state": target})
        return recovered

    def reconcile_confirmed_codex_preexecution_failures(
            self, *, repository_revision, artifact_root, legacy_git_refusal_verified,
            limit=10):
        """Requeue only Codex failures proven to precede all durable effects.

        The caller must have reproduced Git's protected-configuration ownership
        refusal for the configured root-owned repository. Within one transaction
        this method requires either the predecessor outcome-unknown record or a
        worker-recorded failure before process launch, a mismatched immutable
        objective/repository provenance pair, a very short execution-intent
        duration, an expired lease, verified objective provenance, no attempts or
        verification, and no assignment-bound artifact. Recovery is bounded by
        the configured retry ceiling. Normal claim-time exact grants remain
        mandatory before any resumed action can execute.
        """
        if (legacy_git_refusal_verified is not True or
                not isinstance(repository_revision, str) or
                not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", repository_revision) or
                not isinstance(limit, int) or not 1 <= limit <= 100):
            raise ValueError("confirmed Codex recovery evidence is invalid")
        root = Path(artifact_root)
        try:
            info = root.lstat()
            safe_root = (root.is_absolute() and root.is_dir() and not root.is_symlink() and
                         info.st_uid == os.geteuid() and
                         (info.st_mode & 0o777) == 0o700 and root.resolve() == root.absolute())
        except OSError:
            safe_root = False
        if not safe_root:
            raise ValueError("Codex artifact root is not a private owned directory")

        recovered = []
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT a.id,a.state,a.workflow_step,a.authority_ref,
                        a.correlation_id,a.objective_ref,l.generation,l.expires_at,
                        i.intent_id,i.worker_id,i.capability,i.effect_class,i.status AS intent_status,
                        i.failure_class,i.started_at,i.finished_at,o.source_revision
                    FROM assignments a
                    JOIN assignment_leases l ON l.assignment_id=a.id
                    JOIN worker_execution_intents i ON i.assignment_id=a.id
                        AND i.lease_generation=l.generation
                    JOIN grace_objectives o ON o.assignment_id=a.id
                        AND o.objective_id=a.objective_ref
                    WHERE ((a.state='awaiting_steward'
                            AND a.workflow_step='ACTION_OUTCOME_UNKNOWN'
                            AND i.status='outcome_unknown')
                        OR (a.state='blocked'
                            AND a.workflow_step='WORKER_PRE_EXECUTION_FAILED'
                            AND i.status='failed'))
                      AND l.expires_at<=clock_timestamp()
                      AND i.capability='engineering.codex-cli-artifact.v1'
                      AND i.effect_class='external_uncertain'
                      AND i.failure_class='CodexActionFailure'
                      AND i.finished_at-i.started_at<=interval '2 seconds'
                      AND o.status='WORK_ORDER_CREATED'
                      AND o.assignment_id=a.id
                      AND o.evidence->>'status'='VERIFIED'
                      AND o.source_revision IS NOT NULL
                      AND o.source_revision<>%s
                    ORDER BY i.started_at,a.id
                    FOR UPDATE OF a,l,i SKIP LOCKED LIMIT %s""",
                    (repository_revision, limit))
                candidates = cur.fetchall()
                for candidate in candidates:
                    assignment_id = candidate["id"]
                    generation = candidate["generation"]
                    if self.max_retries is not None:
                        cur.execute("SELECT count(*) AS n FROM worker_recovery_records "
                                    "WHERE assignment_id=%s AND decision='retry_safe'",
                                    (assignment_id,))
                        if int(cur.fetchone()["n"]) >= self.max_retries:
                            continue
                    artifact_name = "codex-" + hashlib.sha256(
                        assignment_id.encode("utf-8")).hexdigest() + ".md"
                    artifact = root / artifact_name
                    if artifact.exists() or artifact.is_symlink():
                        continue
                    cur.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s",
                                (assignment_id,))
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    cur.execute("SELECT count(*) AS n FROM verification_records WHERE assignment_id=%s",
                                (assignment_id,))
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    cur.execute("SELECT 1 FROM worker_recovery_records "
                                "WHERE assignment_id=%s AND lease_generation=%s",
                                (assignment_id, generation))
                    if cur.fetchone() is not None:
                        continue
                    cur.execute("""INSERT INTO worker_recovery_records
                        (assignment_id,lease_generation,intent_id,attempt_id,decision,
                         previous_state,resulting_state,observed_expiry)
                        VALUES (%s,%s,%s,NULL,'retry_safe',%s,'ready',%s)""",
                        (assignment_id, generation, candidate["intent_id"],
                         candidate["state"], candidate["expires_at"]))
                    cur.execute("""UPDATE worker_execution_intents
                        SET status='retry_scheduled',finished_at=clock_timestamp()
                        WHERE intent_id=%s AND assignment_id=%s
                          AND lease_generation=%s AND status=%s""",
                        (candidate["intent_id"], assignment_id, generation,
                         candidate["intent_status"]))
                    if cur.rowcount != 1:
                        raise RuntimeError("Codex recovery intent changed during reconciliation")
                    evidence = {
                        "proof": ("legacy_git_safe_directory_refusal_before_cli_launch"
                                  if candidate["intent_status"] == "outcome_unknown" else
                                  "durable_worker_preexecution_failure_before_cli_launch"),
                        "legacy_failure_class": candidate["failure_class"],
                        "execution_process_started": False,
                        "assignment_attempt_absent": True,
                        "verification_absent": True,
                        "assignment_artifact_absent": True,
                        "knowledge_source_revision": candidate["source_revision"],
                        "execution_repository_revision": repository_revision,
                        "intent_id": str(candidate["intent_id"]),
                    }
                    key = f"codex-preexecution-recovery:{assignment_id}:{generation}:ready"
                    self._transition_locked(cur, candidate, "ready",
                        "RECOVERY_CONFIRMED_PREEXECUTION_NO_EFFECT", key,
                        evidence=evidence)
                    recovered.append({"assignment_id": assignment_id,
                        "intent_id": str(candidate["intent_id"]),
                        "lease_generation": generation, "decision": "retry_safe",
                        "resulting_state": "ready"})
        return recovered
