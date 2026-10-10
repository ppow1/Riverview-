# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/postgres_ledger.py
# Component: POSTGRES-LEDGER
# Revision: 1.1.3
# Purpose: Persist contract-aligned assignments and causally linked events
# Execution Model: Request-driven library
# Observability: PostgreSQL assignment/event queries and schema version
# Dependencies: Python 3.10+; Psycopg 3; PostgreSQL 16; versioned migrations
# Authority: Persistence only; authority references are recorded, not validated
# Changed: 2026-10-10 UTC | RV-M2.2-001 | Preserve verified acceptance provenance in event
# Contracts: docs/components/POSTGRES_LEDGER.md; docs/architecture/EVENT_AND_ASSIGNMENT_CONTRACT_v0.1.md
# Tests: tests/test_postgres_ledger.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""PostgreSQL persistence adapter for durable assignments and events."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from .ledger import TRANSITIONS, TransitionError
from .postgres_migrations import MigrationError, apply_migrations


class PostgresLedger:
    """Request-driven ledger; schema changes are explicit migrations."""

    def __init__(self, dsn, *, schema="public"):
        if not schema or not schema[0].isalpha() or not schema.replace("_", "").isalnum():
            raise ValueError("invalid schema")
        self.schema = schema
        self.db = psycopg.connect(dsn, row_factory=dict_row, autocommit=True)
        try:
            with self.db.cursor() as cur:
                cur.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s) AS present",
                            (schema,))
                if not cur.fetchone()["present"]:
                    raise MigrationError(f"target schema does not exist: {schema}")
                cur.execute("SELECT set_config('search_path', %s, false)", (schema,))
                cur.execute("SELECT to_regclass('schema_migrations') AS ledger")
                if cur.fetchone()["ledger"] is None:
                    raise MigrationError("schema is not migrated; call apply_migrations first")
                cur.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
                if cur.fetchone() is None:
                    raise MigrationError("schema has no applied ledger migration")
        except BaseException:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    @staticmethod
    def _timestamp():
        return datetime.now(timezone.utc)

    def _set_search_path(self, cur):
        cur.execute("SELECT set_config('search_path', %s, false)", (self.schema,))

    def _append_event(self, cur, *, assignment_id, event_type, idempotency_key,
                      actor_id, authority_ref, correlation_id, causation_id,
                      payload_schema, payload, privacy_domain="institution"):
        # Identity sequence values are allocated before transaction commit. Serialize
        # event inserts through commit so a cursor consumer cannot observe a higher
        # sequence while a lower sequence remains uncommitted and later skip it.
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    ("riverview:ledger:event-sequence",))
        event_id = uuid4()
        cur.execute(
            """INSERT INTO events
               (event_id, schema, event_type, occurred_at, recorded_at,
                assignment_id, actor_id, correlation_id, causation_id,
                idempotency_key, authority_ref, privacy_domain, payload_schema, payload)
               VALUES (%s, 'rv.event.v1', %s, %s, %s, %s, %s, %s, %s,
                       %s, %s, %s, %s, %s)""",
            (event_id, event_type, self._timestamp(), self._timestamp(),
             assignment_id, actor_id, correlation_id, causation_id,
             idempotency_key, authority_ref, privacy_domain, payload_schema,
             json.dumps(payload, sort_keys=True)))
        return event_id

    def _replay(self, cur, key, assignment_id, event_type, expected, *, actor_id,
                authority_ref, correlation_id, payload_schema):
        cur.execute(
            """SELECT assignment_id,event_type,payload,actor_id,authority_ref,
                      correlation_id,payload_schema FROM events WHERE idempotency_key=%s""",
            (key,))
        existing = cur.fetchone()
        if not existing:
            return None
        if (existing["assignment_id"] != assignment_id or
                existing["event_type"] != event_type or
                existing["payload"] != expected or existing["actor_id"] != actor_id or
                existing["authority_ref"] != authority_ref or
                existing["correlation_id"] != correlation_id or
                existing["payload_schema"] != payload_schema):
            raise TransitionError("idempotency key collision")
        return self.get(assignment_id)

    def create(self, assignment_id, owner, idempotency_key, *, authority_ref,
               objective_ref, actor_id, contract_ref=None, workflow_id="assignment.v1",
               workflow_step="intake", occupant_id=None, correlation_id=None):
        required = (assignment_id, owner, idempotency_key, authority_ref,
                    objective_ref, actor_id, workflow_id, workflow_step)
        if any(not value for value in required):
            raise ValueError("assignment, owner, authority, objective, actor, and workflow metadata are required")
        correlation_id = correlation_id or assignment_id
        payload = {
            "owner": owner, "occupant_id": occupant_id,
            "authority_ref": authority_ref, "objective_ref": objective_ref,
            "contract_ref": contract_ref, "workflow_id": workflow_id,
            "workflow_step": workflow_step, "state": "queued",
        }
        with self.db.transaction():
            with self.db.cursor() as cur:
                self._set_search_path(cur)
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                            (idempotency_key,))
                replay = self._replay(cur, idempotency_key, assignment_id,
                                      "assignment.created", payload, actor_id=actor_id,
                                      authority_ref=authority_ref,
                                      correlation_id=correlation_id,
                                      payload_schema="rv.assignment.created.v1")
                if replay is not None:
                    return replay
                cur.execute("SELECT 1 FROM assignments WHERE id=%s", (assignment_id,))
                if cur.fetchone():
                    raise TransitionError("assignment already exists")
                now = self._timestamp()
                cur.execute(
                    """INSERT INTO assignments
                       (id,state,owner,occupant_id,authority_ref,objective_ref,contract_ref,
                        workflow_id,workflow_step,correlation_id,updated_at)
                       VALUES (%s,'queued',%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (assignment_id, owner, occupant_id, authority_ref, objective_ref,
                     contract_ref, workflow_id, workflow_step, correlation_id, now))
                self._append_event(
                    cur, assignment_id=assignment_id, event_type="assignment.created",
                    idempotency_key=idempotency_key, actor_id=actor_id,
                    authority_ref=authority_ref, correlation_id=correlation_id,
                    causation_id=None, payload_schema="rv.assignment.created.v1",
                    payload=payload)
        return self.get(assignment_id)

    def transition(self, assignment_id, to_state, step, idempotency_key, *, actor_id,
                   verified=False, privacy_domain="institution"):
        if not idempotency_key or not step or not actor_id:
            raise ValueError("idempotency key, actor, and workflow step are required")
        with self.db.transaction():
            with self.db.cursor() as cur:
                self._set_search_path(cur)
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                            (idempotency_key,))
                cur.execute(
                    "SELECT assignment_id,event_type,payload FROM events WHERE idempotency_key=%s",
                    (idempotency_key,))
                existing = cur.fetchone()
                if existing:
                    payload = existing["payload"]
                    if (existing["assignment_id"] != assignment_id or
                            existing["event_type"] != "assignment.transitioned" or
                            payload.get("to") != to_state or payload.get("step") != step or
                            payload.get("actor_id") != actor_id or
                            payload.get("verified_claim") is not verified or
                            payload.get("privacy_domain") != privacy_domain):
                        raise TransitionError("idempotency key collision")
                    return self.get(assignment_id)
                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE",
                            (assignment_id,))
                row = cur.fetchone()
                if row is None:
                    raise TransitionError("unknown assignment")
                if to_state not in TRANSITIONS[row["state"]]:
                    raise TransitionError(f"invalid transition: {row['state']} -> {to_state}")
                if to_state == "completed" and not verified:
                    raise TransitionError("completion requires independently verified evidence")
                cur.execute(
                    "SELECT event_id FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1",
                    (assignment_id,))
                previous_event_id = cur.fetchone()["event_id"]
                payload = {"from": row["state"], "to": to_state, "step": step,
                           "actor_id": actor_id, "verified_claim": bool(verified),
                           "privacy_domain": privacy_domain}
                if to_state == "completed":
                    cur.execute("SELECT to_regclass('verification_records') AS present")
                    if cur.fetchone()["present"] is not None:
                        cur.execute("""SELECT 1 FROM verification_records
                                       WHERE assignment_id=%s AND decision='ACCEPTED'
                                       LIMIT 1""", (assignment_id,))
                        if cur.fetchone() is None:
                            raise TransitionError("completion requires persisted independent verification")
                now = self._timestamp()
                cur.execute(
                    "UPDATE assignments SET state=%s,workflow_step=%s,updated_at=%s,version=version+1 WHERE id=%s",
                    (to_state, step, now, assignment_id))
                self._append_event(
                    cur, assignment_id=assignment_id, event_type="assignment.transitioned",
                    idempotency_key=idempotency_key, actor_id=actor_id,
                    authority_ref=row["authority_ref"],
                    correlation_id=row["correlation_id"],
                    causation_id=previous_event_id,
                    payload_schema="rv.assignment.transitioned.v1", payload=payload,
                    privacy_domain=privacy_domain)
        return self.get(assignment_id)

    def get(self, assignment_id):
        with self.db.cursor() as cur:
            self._set_search_path(cur)
            cur.execute("SELECT * FROM assignments WHERE id=%s", (assignment_id,))
            return cur.fetchone()

    def list_assignments(self):
        with self.db.cursor() as cur:
            self._set_search_path(cur)
            cur.execute("SELECT * FROM assignments ORDER BY id")
            return cur.fetchall()

    def events(self, after_seq=0):
        with self.db.cursor() as cur:
            self._set_search_path(cur)
            cur.execute("SELECT * FROM events WHERE seq>%s ORDER BY seq", (after_seq,))
            return cur.fetchall()
