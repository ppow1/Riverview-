# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/postgres_ledger.py
# Component: POSTGRES-LEDGER
# Revision: 1.0.0
# Purpose: PostgreSQL development assignment and event ledger
# Execution Model: Request-driven library
# Observability: PostgreSQL events and state projection
# Dependencies: Python 3; psycopg 3; PostgreSQL
# Authority: Development backend; caller authorization external
# Changed: 2026-10-09 UTC | ENG-REV-004 | Initial controlled header migration
# Contracts: docs/components/POSTGRES_LEDGER.md
# Tests: tests/test_postgres_ledger.py
# History: Git commit 6810e00374f50a81820be5f4e7714b329965ea66 and staged predecessor manifest
# =============================================================================

"""PostgreSQL development backend for the Riverview assignment ledger.

Requires psycopg 3. Schema isolation is selected with a connection option
(search_path), not interpolated SQL. This is not a production authority service.
"""
import json
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from .ledger import TRANSITIONS, TransitionError


class PostgresLedger:
    def __init__(self, dsn, *, schema="public"):
        if not schema.replace("_", "").isalnum() or not schema[0].isalpha():
            raise ValueError("invalid schema")
        self.db = psycopg.connect(dsn, row_factory=dict_row, autocommit=True)
        with self.db.transaction():
            with self.db.cursor() as cur:
                cur.execute("SELECT set_config('search_path', %s, false)", (schema,))
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS assignments (
                        id TEXT PRIMARY KEY, state TEXT NOT NULL, owner TEXT NOT NULL,
                        workflow_step TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL,
                        version INTEGER NOT NULL DEFAULT 1
                    )""")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        seq BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        event_id UUID NOT NULL UNIQUE,
                        idempotency_key TEXT NOT NULL UNIQUE,
                        assignment_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        occurred_at TIMESTAMPTZ NOT NULL,
                        payload JSONB NOT NULL
                    )""")

    def close(self):
        self.db.close()

    def _event(self, cur, assignment_id, event_type, key, payload):
        cur.execute(
            "INSERT INTO events(event_id,idempotency_key,assignment_id,event_type,occurred_at,payload) VALUES(%s,%s,%s,%s,%s,%s)",
            (uuid4(), key, assignment_id, event_type, datetime.now(timezone.utc), json.dumps(payload)))

    def create(self, assignment_id, owner, idempotency_key):
        if not assignment_id or not owner or not idempotency_key:
            raise ValueError("assignment_id, owner, and idempotency_key are required")
        with self.db.transaction():
            with self.db.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (idempotency_key,))
                cur.execute("SELECT assignment_id,event_type FROM events WHERE idempotency_key=%s", (idempotency_key,))
                existing = cur.fetchone()
                if existing:
                    if existing["assignment_id"] != assignment_id or existing["event_type"] != "assignment.created":
                        raise TransitionError("idempotency key collision")
                    return self.get(assignment_id)
                cur.execute("SELECT 1 FROM assignments WHERE id=%s", (assignment_id,))
                if cur.fetchone():
                    raise TransitionError("assignment already exists")
                cur.execute(
                    "INSERT INTO assignments(id,state,owner,workflow_step,updated_at) VALUES(%s,'queued',%s,'intake',%s)",
                    (assignment_id, owner, datetime.now(timezone.utc)))
                self._event(cur, assignment_id, "assignment.created", idempotency_key,
                            {"owner": owner, "state": "queued"})
        return self.get(assignment_id)

    def transition(self, assignment_id, to_state, step, idempotency_key, *, verified=False):
        if not idempotency_key or not step:
            raise ValueError("idempotency_key and workflow step required")
        with self.db.transaction():
            with self.db.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (idempotency_key,))
                cur.execute("SELECT assignment_id,event_type,payload FROM events WHERE idempotency_key=%s", (idempotency_key,))
                existing = cur.fetchone()
                if existing:
                    payload = existing["payload"]
                    if (existing["assignment_id"] != assignment_id or
                        existing["event_type"] != "assignment.transitioned" or
                        payload.get("to") != to_state or payload.get("step") != step):
                        raise TransitionError("idempotency key collision")
                    return self.get(assignment_id)
                cur.execute("SELECT state FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                row = cur.fetchone()
                if row is None:
                    raise TransitionError("unknown assignment")
                if to_state not in TRANSITIONS[row["state"]]:
                    raise TransitionError(f"invalid transition: {row['state']} -> {to_state}")
                if to_state == "completed" and not verified:
                    raise TransitionError("completion requires independently verified evidence")
                cur.execute(
                    "UPDATE assignments SET state=%s,workflow_step=%s,updated_at=%s,version=version+1 WHERE id=%s",
                    (to_state, step, datetime.now(timezone.utc), assignment_id))
                self._event(cur, assignment_id, "assignment.transitioned", idempotency_key,
                            {"from": row["state"], "to": to_state, "step": step, "verified_claim": verified})
        return self.get(assignment_id)

    def get(self, assignment_id):
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM assignments WHERE id=%s", (assignment_id,))
            return cur.fetchone()

    def list_assignments(self):
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM assignments ORDER BY id")
            return cur.fetchall()

    def events(self, after_seq=0):
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM events WHERE seq>%s ORDER BY seq", (after_seq,))
            return cur.fetchall()
