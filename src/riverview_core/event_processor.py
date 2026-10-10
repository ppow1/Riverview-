# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/event_processor.py
# Component: EVENT-PROCESSOR
# Revision: 1.0.2
# Purpose: Replay durable assignment events and checkpoint resumable progression
# Execution Model: Event-driven continuous service with repeatable polling
# Observability: Structured lifecycle logs, event cursor, failures and retry state
# Dependencies: Python 3.10+; Psycopg 3; PostgreSQL 16; POSTGRES-LEDGER
# Authority: Advances queued assignments to ready; performs no external effects
# Changed: 2026-10-10 UTC | RV-M1.3-002 | Verify deployed migration contract before event consumption
# Contracts: docs/development/M1.3-001_REVISION_RECORD.md; docs/components/POSTGRES_LEDGER.md
# Tests: tests/test_event_processor.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""A durable, at-least-once PostgreSQL event consumer for assignment intake."""

import json
import hashlib
import logging
import re
import threading
import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from .ledger import TransitionError
from .postgres_ledger import PostgresLedger

LOG = logging.getLogger("riverview.event_processor")
_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class ProcessorError(RuntimeError):
    """Processor startup or durable-state contract failure."""


class ProcessorLeaseError(ProcessorError):
    """Another process already owns this consumer identity."""


class PostgresEventProcessor:
    """Consume committed events and checkpoint only after idempotent handling."""

    def __init__(self, dsn, *, schema="public", consumer_id="assignment-intake.v1",
                 batch_size=32, poll_interval=0.5, max_backoff=30.0):
        if not schema or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid schema")
        if not consumer_id or not consumer_id.strip():
            raise ValueError("consumer_id is required")
        if batch_size < 1 or poll_interval <= 0 or max_backoff < poll_interval:
            raise ValueError("invalid polling or retry bounds")
        self.dsn = dsn
        self.schema = schema
        self.consumer_id = consumer_id
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.max_backoff = max_backoff
        self._closed = False

    def _connection(self):
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def verify_schema(self):
        """Fail closed unless the deployed base and cursor migrations match source."""
        repo = Path(__file__).resolve().parent
        expected = {
            "0001_assignment_event_ledger": repo / "migrations/0001_assignment_event_ledger.sql",
            "0002_event_processor_cursor": repo / "event_processor/migrations/0002_event_processor_cursor.sql",
        }
        checksums = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                     for name, path in expected.items()}
        with self._connection() as db, db.cursor() as cur:
            cur.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
            cur.execute("SELECT version, checksum FROM schema_migrations WHERE version = ANY(%s)",
                        (list(checksums),))
            found = {row["version"]: row["checksum"] for row in cur.fetchall()}
            if found != checksums:
                raise ProcessorError("required migration history is missing or differs from source")
            cur.execute("SELECT to_regclass('event_processor_cursors') AS cursor_table")
            if cur.fetchone()["cursor_table"] is None:
                raise ProcessorError("event processor cursor table is missing")
        return checksums

    def cursor_position(self):
        with self._connection() as db, db.cursor() as cur:
            cur.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
            cur.execute("SELECT last_seq FROM event_processor_cursors WHERE consumer_id=%s",
                        (self.consumer_id,))
            row = cur.fetchone()
            return int(row["last_seq"]) if row else 0

    def _handle(self, event):
        """Apply the event idempotently; this method is also a crash-window seam."""
        if event["event_type"] != "assignment.created":
            return "ignored"
        ledger = PostgresLedger(self.dsn, schema=self.schema)
        try:
            assignment = ledger.get(event["assignment_id"])
            if assignment is None:
                raise ProcessorError("created event references a missing assignment")
            if assignment["state"] != "queued":
                return "already_advanced"
            ledger.transition(
                event["assignment_id"], "ready", "event_processor:intake",
                f"event-processor:{self.consumer_id}:{event['event_id']}",
                actor_id=f"service:{self.consumer_id}")
            return "advanced"
        finally:
            ledger.close()

    def run_once(self):
        """Process one ordered batch and return its count; safe to call repeatedly."""
        if self._closed:
            raise ProcessorError("processor is closed")
        processed = 0
        with self._connection() as db:
            with db.transaction():
                with db.cursor() as cur:
                    cur.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
                    cur.execute("INSERT INTO event_processor_cursors(consumer_id,last_seq) VALUES(%s,0) ON CONFLICT(consumer_id) DO NOTHING",
                                (self.consumer_id,))
                    cur.execute("SELECT last_seq FROM event_processor_cursors WHERE consumer_id=%s FOR UPDATE",
                                (self.consumer_id,))
                    last_seq = int(cur.fetchone()["last_seq"])
                    cur.execute("SELECT seq,event_id::text AS event_id,assignment_id,event_type,payload FROM events WHERE seq>%s ORDER BY seq LIMIT %s",
                                (last_seq, self.batch_size))
                    events = cur.fetchall()
                    for event in events:
                        outcome = self._handle(event)
                        cur.execute("UPDATE event_processor_cursors SET last_seq=%s,updated_at=clock_timestamp() WHERE consumer_id=%s",
                                    (event["seq"], self.consumer_id))
                        LOG.info(json.dumps({"event":"event_processed","consumer_id":self.consumer_id,
                                             "event_id":event["event_id"],"seq":event["seq"],
                                             "event_type":event["event_type"],"outcome":outcome},
                                            sort_keys=True))
                        processed += 1
        return processed

    def run_forever(self, stop_event=None):
        """Poll until stopped; reconnect and reacquire leadership after DB recovery."""
        stop_event = stop_event or threading.Event()
        backoff = self.poll_interval
        while not stop_event.is_set():
            try:
                self.verify_schema()
                self._run_as_leader(stop_event)
                return
            except ProcessorLeaseError:
                raise
            except psycopg.Error as exc:
                LOG.error(json.dumps({"event":"processor_dependency_retry",
                                      "consumer_id":self.consumer_id,
                                      "failure_type":type(exc).__name__,
                                      "backoff_seconds":backoff}, sort_keys=True))
                stop_event.wait(backoff)
                backoff = min(self.max_backoff, backoff * 2)

    def _run_as_leader(self, stop_event):
        lock_key = f"riverview-event-processor:{self.schema}:{self.consumer_id}"
        with self._connection() as lock_db, lock_db.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s,0)) AS acquired",
                        (lock_key,))
            if not cur.fetchone()["acquired"]:
                raise ProcessorLeaseError("another processor holds this consumer lease")
            LOG.info(json.dumps({"event":"processor_started","consumer_id":self.consumer_id,
                                 "schema":self.schema,"cursor":self.cursor_position()}, sort_keys=True))
            backoff = self.poll_interval
            try:
                while not stop_event.is_set():
                    try:
                        processed = self.run_once()
                        # The held session owns the advisory lock. A lightweight
                        # ping makes an administrator or PostgreSQL restart visible
                        # before another instance could process under a lost lease.
                        cur.execute("SELECT 1")
                        backoff = self.poll_interval
                        delay = 0 if processed else self.poll_interval
                    except (ProcessorError, TransitionError) as exc:
                        LOG.error(json.dumps({"event":"processor_retry",
                                              "consumer_id":self.consumer_id,
                                              "failure_type":type(exc).__name__,
                                              "backoff_seconds":backoff}, sort_keys=True))
                        delay = backoff
                        backoff = min(self.max_backoff, backoff * 2)
                    stop_event.wait(delay)
            finally:
                try:
                    cur.execute("SELECT pg_advisory_unlock(hashtextextended(%s,0))", (lock_key,))
                    cursor = self.cursor_position()
                except psycopg.Error:
                    cursor = None
                LOG.info(json.dumps({"event":"processor_stopped","consumer_id":self.consumer_id,
                                     "cursor":cursor}, sort_keys=True))

    def close(self):
        self._closed = True

