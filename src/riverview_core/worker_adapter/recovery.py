# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/recovery.py
# Component: WORKER-ADAPTER
# Revision: 1.0.1
# Purpose: Reconcile expired worker leases without losing or blindly repeating work
# Execution Model: Explicit PostgreSQL recovery pass at worker startup or polling
# Observability: Recovery records and causal assignment transition events
# Dependencies: Psycopg 3; PostgreSQL ledger, scheduler and worker migrations
# Authority: Recovery only; unknown external outcomes wait for Steward decision
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Enforce optional persistent retry ceilings
# Contracts: docs/ROADMAP.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Recover expired assignment work with conservative external-effect handling."""

from ..ledger import TRANSITIONS
from ..postgres_ledger import PostgresLedger


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

    def _transition_locked(self, cur, assignment, to_state, step, key):
        from_state = assignment["state"]
        if to_state not in TRANSITIONS[from_state]:
            raise RuntimeError(f"invalid recovery transition: {from_state} -> {to_state}")
        cur.execute("SELECT event_id FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1",
                    (assignment["id"],))
        cause = cur.fetchone()["event_id"]
        payload = {"from": from_state, "to": to_state, "step": step,
                   "actor_id": "cme:recovery", "verified_claim": False,
                   "privacy_domain": "institution"}
        cur.execute("""UPDATE assignments
            SET state=%s,workflow_step=%s,updated_at=clock_timestamp(),version=version+1
            WHERE id=%s""", (to_state, step, assignment["id"]))
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
