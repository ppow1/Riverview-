# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/ledger.py
# Component: CORE-LEDGER
# Revision: 1.0.3
# Purpose: SQLite development assignment and event ledger
# Execution Model: Request-driven library
# Observability: SQLite records and event queries
# Dependencies: Python 3; sqlite3
# Authority: Development prototype; not production authority
# Changed: 2026-10-09 UTC | ENG-REV-004 | Initial controlled header migration
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Allow the verifier-corrected verified path to complete the development ledger
# Contracts: docs/architecture/EVENT_AND_ASSIGNMENT_CONTRACT_v0.1.md
# Tests: tests/test_ledger.py
# History: Git commit 6810e00374f50a81820be5f4e7714b329965ea66 and staged predecessor manifest
# =============================================================================

"""Small executable contract prototype: durable assignments, events, status projection.

SQLite is an isolated developer backend; PostgreSQL is required for the intended
multi-host deployment. No workers, auth service, or notification transport yet.
"""
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

TRANSITIONS = {
    "queued": {"ready", "cancelled", "blocked"},
    "ready": {"running", "blocked", "cancelled"},
    "running": {"awaiting_verification", "blocked", "awaiting_steward"},
    "awaiting_verification": {"completed", "rework_required", "blocked"},
    "rework_required": {"ready", "blocked", "cancelled", "completed"},
    "blocked": {"ready", "cancelled", "awaiting_steward"},
    "awaiting_steward": {"ready", "cancelled", "awaiting_verification"},
    "completed": set(),
    "cancelled": set(),
}

class TransitionError(ValueError):
    pass

class Ledger:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS assignments (
            id TEXT PRIMARY KEY, state TEXT NOT NULL, owner TEXT NOT NULL,
            workflow_step TEXT NOT NULL, updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE, idempotency_key TEXT NOT NULL UNIQUE,
            assignment_id TEXT NOT NULL, event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL, payload TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    def _timestamp(self):
        return datetime.now(timezone.utc).isoformat()

    def _event(self, assignment_id, event_type, key, payload):
        self.db.execute(
            "INSERT INTO events(event_id,idempotency_key,assignment_id,event_type,occurred_at,payload) VALUES(?,?,?,?,?,?)",
            (str(uuid4()), key, assignment_id, event_type, self._timestamp(), json.dumps(payload, sort_keys=True)))

    def create(self, assignment_id, owner, idempotency_key):
        if not assignment_id or not owner or not idempotency_key:
            raise ValueError("assignment_id, owner, and idempotency_key are required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT assignment_id,event_type FROM events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                if existing["assignment_id"] != assignment_id or existing["event_type"] != "assignment.created":
                    raise TransitionError("idempotency key collision")
                self.db.execute("COMMIT")
                return self.get(assignment_id)
            if self.db.execute("SELECT 1 FROM assignments WHERE id=?", (assignment_id,)).fetchone():
                raise TransitionError("assignment already exists")
            self.db.execute("INSERT INTO assignments(id,state,owner,workflow_step,updated_at) VALUES(?,?,?,?,?)",
                            (assignment_id, "queued", owner, "intake", self._timestamp()))
            self._event(assignment_id, "assignment.created", idempotency_key, {"owner": owner, "state": "queued"})
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return self.get(assignment_id)

    def transition(self, assignment_id, to_state, step, idempotency_key, *, verified=False):
        if not idempotency_key or not step:
            raise ValueError("idempotency_key and workflow step required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT assignment_id,event_type,payload FROM events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                payload = json.loads(existing["payload"])
                if existing["assignment_id"] != assignment_id or existing["event_type"] != "assignment.transitioned" or payload.get("to") != to_state or payload.get("step") != step:
                    raise TransitionError("idempotency key collision")
                self.db.execute("COMMIT")
                return self.get(assignment_id)
            row = self.db.execute("SELECT state FROM assignments WHERE id=?", (assignment_id,)).fetchone()
            if row is None:
                raise TransitionError("unknown assignment")
            if to_state not in TRANSITIONS[row["state"]]:
                raise TransitionError(f"invalid transition: {row['state']} -> {to_state}")
            if to_state == "completed" and not verified:
                raise TransitionError("completion requires independently verified evidence")
            self.db.execute("UPDATE assignments SET state=?,workflow_step=?,updated_at=?,version=version+1 WHERE id=?",
                            (to_state, step, self._timestamp(), assignment_id))
            self._event(assignment_id, "assignment.transitioned", idempotency_key,
                        {"from": row["state"], "to": to_state, "step": step, "verified_claim": verified})
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return self.get(assignment_id)

    def get(self, assignment_id):
        row = self.db.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        return dict(row) if row else None

    def list_assignments(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM assignments ORDER BY id")]

    def events(self, after_seq=0):
        return [dict(r) for r in self.db.execute("SELECT * FROM events WHERE seq>? ORDER BY seq", (after_seq,))]
