# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/assignment_scheduler/scheduler.py
# Component: ASSIGNMENT-SCHEDULER
# Revision: 1.0.0
# Purpose: Claim ready assignments fairly and fence stale lease holders
# Execution Model: PostgreSQL transactional request interface
# Observability: Durable lease generations and causally linked ledger events
# Dependencies: Python 3.10+; Psycopg 3; POSTGRES-LEDGER schema and lease migration
# Authority: Does not validate grants or independently verify worker results
# Changed: 2026-10-10 UTC | RV-M1.4-001 | Initial lease/fencing implementation
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

    def claim_next(self, worker_id, *, lease_seconds=30):
        """Claim the oldest unleased/expired ready assignment; return its fencing token."""
        self._validate_lease(worker_id, lease_seconds)
        db = self.ledger.db
        with db.transaction():
            with db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute(
                    """SELECT a.id,l.generation
                       FROM assignments AS a
                       LEFT JOIN assignment_leases AS l ON l.assignment_id=a.id
                       WHERE a.state='ready'
                         AND (l.assignment_id IS NULL OR l.expires_at<=clock_timestamp())
                       ORDER BY a.updated_at,a.id
                       FOR UPDATE OF a SKIP LOCKED LIMIT 1""")
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

    def heartbeat(self, assignment_id, worker_id, generation, *, lease_seconds=30):
        """Extend only a currently active exact worker/generation lease."""
        self._validate_lease(worker_id, lease_seconds)
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
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

    def start_assignment(self, assignment_id, worker_id, generation):
        """Atomically verify the active fencing token and transition ready to running."""
        db = self.ledger.db
        with db.transaction():
            with db.cursor() as cur:
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
                if "running" not in TRANSITIONS[assignment["state"]]:
                    raise SchedulerError("assignment is not eligible to start")
                step = f"worker:{worker_id}:execution"
                key = f"scheduler:start:{assignment_id}:{generation}"
                cur.execute("SELECT event_id FROM events WHERE idempotency_key=%s", (key,))
                if cur.fetchone():
                    raise SchedulerError("lease generation already started this assignment")
                cur.execute("SELECT event_id FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1",
                            (assignment_id,))
                cause = cur.fetchone()["event_id"]
                payload = {"from": assignment["state"], "to": "running", "step": step,
                           "actor_id": worker_id, "verified_claim": False,
                           "privacy_domain": "institution"}
                cur.execute("UPDATE assignments SET state='running',workflow_step=%s,updated_at=clock_timestamp(),version=version+1 WHERE id=%s",
                            (step, assignment_id))
                self.ledger._append_event(
                    cur, assignment_id=assignment_id, event_type="assignment.transitioned",
                    idempotency_key=key, actor_id=worker_id,
                    authority_ref=assignment["authority_ref"],
                    correlation_id=assignment["correlation_id"], causation_id=cause,
                    payload_schema="rv.assignment.transitioned.v1", payload=payload)
        return self.ledger.get(assignment_id)
