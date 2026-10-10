# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/assignment_scheduler/scheduler.py
# Component: ASSIGNMENT-SCHEDULER
# Revision: 1.0.5
# Purpose: Claim ready assignments fairly and fence stale lease holders
# Execution Model: PostgreSQL transactional request interface
# Observability: Durable lease generations and causally linked ledger events
# Dependencies: Python 3.10+; Psycopg 3; POSTGRES-LEDGER schema and lease migration
# Authority: Does not validate grants or independently verify worker results
# Changed: 2026-10-10 UTC | RV-M2.1-001 | Add scope-filtered lease claim integration
# Contracts: docs/development/M1.4-001_REVISION_RECORD.md
# Tests: tests/test_assignment_scheduler.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Fair PostgreSQL assignment claims with monotonically fenced lease generations."""

from datetime import timedelta

from psycopg.rows import dict_row

from ..ledger import TRANSITIONS
from ..postgres_ledger import PostgresLedger


class SchedulerError(RuntimeError):
    """Scheduler operation failed its durable contract."""


class StaleLeaseError(SchedulerError):
    """Lease owner, generation, or expiry no longer authorizes this operation."""


class PostgresAssignmentScheduler:
    """Claim ready work in age order and reject stale worker generations.

    The caller must explicitly apply this component's migration before use.
    Claims do not execute work, validate authority grants, or assert verification.
    """

    def __init__(self, dsn, *, schema="public"):
        self.ledger = PostgresLedger(dsn, schema=schema)
        self.schema = schema

    def close(self):
        self.ledger.close()

    @staticmethod
    def _validate_lease(worker_id, lease_seconds):
        if not worker_id or not worker_id.strip():
            raise ValueError("worker_id is required")
        if not isinstance(lease_seconds, (int, float)) or lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")

    @staticmethod
    def _claim_candidate(cur, worker_id, lease_seconds, *, scope_ref=None):
        """Claim one eligible assignment in the caller's active transaction."""
        cur.execute(
            """SELECT a.id,l.generation
               FROM assignments AS a
               LEFT JOIN assignment_leases AS l ON l.assignment_id=a.id
               WHERE a.state='ready'
                 AND (l.assignment_id IS NULL OR l.expires_at<=clock_timestamp())
                 AND (%s::text IS NULL OR a.authority_ref=%s)
               ORDER BY a.updated_at,a.id
               FOR UPDATE OF a SKIP LOCKED LIMIT 1""",
            (scope_ref, scope_ref))
        assignment = cur.fetchone()
        if assignment is None:
            return None
        generation = (assignment["generation"] or 0) + 1
        cur.execute(
            """INSERT INTO assignment_leases
                   (assignment_id,worker_id,generation,acquired_at,heartbeat_at,expires_at)
               VALUES (%s,%s,%s,clock_timestamp(),clock_timestamp(),
                       clock_timestamp()+(%s * interval '1 second'))
               ON CONFLICT (assignment_id) DO UPDATE SET
                   worker_id=EXCLUDED.worker_id,
                   generation=EXCLUDED.generation,
                   acquired_at=EXCLUDED.acquired_at,
                   heartbeat_at=EXCLUDED.heartbeat_at,
                   expires_at=EXCLUDED.expires_at
               RETURNING assignment_id,worker_id,generation,acquired_at,heartbeat_at,expires_at""",
            (assignment["id"], worker_id, generation, lease_seconds))
        return cur.fetchone()

    def claim_next(self, worker_id, *, lease_seconds=30, scope_ref=None):
        """Claim oldest eligible ready work, optionally within an exact authority scope."""
        self._validate_lease(worker_id, lease_seconds)
        db = self.ledger.db
        with db.transaction():
            with db.cursor() as cur:
                self.ledger._set_search_path(cur)
                return self._claim_candidate(cur, worker_id, lease_seconds,
                                             scope_ref=scope_ref)

    def heartbeat(self, assignment_id, worker_id, generation, *, lease_seconds=30):
        """Extend only a currently active exact worker/generation lease.

        Lock the assignment first, matching claim/reclaim lock order, so a
        successful heartbeat cannot race with replacement by a newer generation.
        """
        self._validate_lease(worker_id, lease_seconds)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT id FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                if cur.fetchone() is None:
                    raise StaleLeaseError("assignment no longer exists")
                cur.execute(
                    """UPDATE assignment_leases
                       SET heartbeat_at=clock_timestamp(),
                           expires_at=clock_timestamp()+(%s * interval '1 second')
                       WHERE assignment_id=%s AND worker_id=%s AND generation=%s
                         AND expires_at>clock_timestamp()
                       RETURNING expires_at""",
                    (lease_seconds, assignment_id, worker_id, generation))
                row = cur.fetchone()
                if row is None:
                    raise StaleLeaseError("lease is absent, expired, or fenced by a newer generation")
                return row["expires_at"]

    def transition_with_lease(self, assignment_id, to_state, step, idempotency_key,
                              worker_id, generation, *, verified=False,
                              privacy_domain="institution"):
        """Apply any legal assignment transition only under the current lease token."""
        if not idempotency_key or not step or not worker_id:
            raise ValueError("idempotency key, step, and worker_id are required")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                assignment = cur.fetchone()
                if assignment is None:
                    raise SchedulerError("unknown assignment")
                cur.execute("SELECT worker_id,generation,expires_at FROM assignment_leases WHERE assignment_id=%s FOR UPDATE",
                            (assignment_id,))
                lease = cur.fetchone()
                cur.execute("SELECT clock_timestamp() AS now")
                now = cur.fetchone()["now"]
                if (lease is None or lease["worker_id"] != worker_id or
                        lease["generation"] != generation or lease["expires_at"] <= now):
                    raise StaleLeaseError("lease is absent, expired, or fenced by a newer generation")
                cur.execute("SELECT assignment_id,event_type,payload FROM events WHERE idempotency_key=%s",
                            (idempotency_key,))
                existing = cur.fetchone()
                if existing:
                    prior = existing["payload"]
                    if (existing["assignment_id"] != assignment_id or
                            existing["event_type"] != "assignment.transitioned" or
                            prior.get("to") != to_state or prior.get("step") != step or
                            prior.get("actor_id") != worker_id or
                            prior.get("verified_claim") is not bool(verified) or
                            prior.get("privacy_domain") != privacy_domain):
                        raise SchedulerError("idempotency key collision")
                    return self.ledger.get(assignment_id)
                payload = {"from": assignment["state"], "to": to_state, "step": step,
                           "actor_id": worker_id, "verified_claim": bool(verified),
                           "privacy_domain": privacy_domain}
                if to_state not in TRANSITIONS[assignment["state"]]:
                    raise SchedulerError(f"invalid transition: {assignment['state']} -> {to_state}")
                if to_state == "completed" and not verified:
                    raise SchedulerError("completion requires independently verified evidence")
                cur.execute("SELECT event_id FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1",
                            (assignment_id,))
                cause = cur.fetchone()["event_id"]
                cur.execute("UPDATE assignments SET state=%s,workflow_step=%s,updated_at=clock_timestamp(),version=version+1 WHERE id=%s",
                            (to_state, step, assignment_id))
                self.ledger._append_event(
                    cur, assignment_id=assignment_id, event_type="assignment.transitioned",
                    idempotency_key=idempotency_key, actor_id=worker_id,
                    authority_ref=assignment["authority_ref"],
                    correlation_id=assignment["correlation_id"], causation_id=cause,
                    payload_schema="rv.assignment.transitioned.v1", payload=payload,
                    privacy_domain=privacy_domain)
        return self.ledger.get(assignment_id)

    def start_assignment(self, assignment_id, worker_id, generation):
        """Start work with a current token, emitting one causal ledger event."""
        return self.transition_with_lease(
            assignment_id, "running", f"worker:{worker_id}:execution",
            f"scheduler:start:{assignment_id}:{generation}", worker_id, generation)
