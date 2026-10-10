# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_event_processor.py
# Component: EVENT-PROCESSOR
# Revision: 1.0.0
# Purpose: Verify durable cursor, no-turn progression, restart and replay idempotency
# Execution Model: Request-driven PostgreSQL tests using isolated schemas
# Observability: unittest outcomes; durable assignment/event/cursor assertions
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL test database
# Authority: Creates and drops only unique rvtest_* schemas
# Changed: 2026-10-10 UTC | RV-M1.3-001 | Initial event processor acceptance tests
# Contracts: docs/development/M1.3-001_REVISION_RECORD.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""PostgreSQL integration tests for the M1.3 persistent event consumer."""

import os
import threading
import time
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import psycopg
from psycopg import sql

from riverview_core.event_processor import PostgresEventProcessor, ProcessorError
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.postgres_migrations import apply_migrations

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
PROCESSOR_MIGRATIONS = (Path(__file__).resolve().parents[1]
                        / "src/riverview_core/event_processor/migrations")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class EventProcessorTests(unittest.TestCase):
    def setUp(self):
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        apply_migrations(DSN, schema=self.schema)
        self.cursor_migration = apply_migrations(
            DSN, schema=self.schema, migrations_dir=PROCESSOR_MIGRATIONS)
        self.assertEqual(self.cursor_migration, ["0002_event_processor_cursor"])
        self.ledger = PostgresLedger(DSN, schema=self.schema)

    def tearDown(self):
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def create(self, assignment_id):
        return self.ledger.create(
            assignment_id, "engineering", f"create-{assignment_id}",
            authority_ref="grant:test", objective_ref=f"objective:{assignment_id}",
            actor_id="resident:test", workflow_id="workflow:test", workflow_step="intake")

    def processor(self, **kwargs):
        return PostgresEventProcessor(DSN, schema=self.schema,
                                     poll_interval=0.01, max_backoff=0.1, **kwargs)

    def test_assignment_advances_without_turn_and_cursor_survives_processor_restart(self):
        processor = self.processor(consumer_id="continuous-test")
        stopping = threading.Event()
        thread = threading.Thread(target=processor.run_forever, args=(stopping,), daemon=True)
        thread.start()
        try:
            self.create("auto-one")
            deadline = time.monotonic() + 3
            while self.ledger.get("auto-one")["state"] != "ready" and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(self.ledger.get("auto-one")["state"], "ready")
            self.assertGreater(processor.cursor_position(), 0)
        finally:
            stopping.set()
            thread.join(timeout=3)
            processor.close()
        self.assertFalse(thread.is_alive())

        self.create("auto-two")
        resumed = self.processor(consumer_id="continuous-test")
        stop_again = threading.Event()
        resumed_thread = threading.Thread(target=resumed.run_forever, args=(stop_again,), daemon=True)
        resumed_thread.start()
        try:
            deadline = time.monotonic() + 3
            while self.ledger.get("auto-two")["state"] != "ready" and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(self.ledger.get("auto-two")["state"], "ready")
        finally:
            stop_again.set()
            resumed_thread.join(timeout=3)
            resumed.close()
        self.assertFalse(resumed_thread.is_alive())

    def test_crash_after_transition_replays_without_duplicate_event(self):
        self.create("crash-window")
        source_event = self.ledger.events()[0]
        processor = self.processor(consumer_id="crash-window-test")
        event = {"event_id": str(source_event["event_id"]), "seq": source_event["seq"],
                 "assignment_id": source_event["assignment_id"],
                 "event_type": source_event["event_type"], "payload": source_event["payload"]}
        self.assertEqual(processor._handle(event), "advanced")
        self.assertEqual(self.ledger.get("crash-window")["state"], "ready")
        self.assertEqual(processor.cursor_position(), 0)
        processor.close()

        resumed = self.processor(consumer_id="crash-window-test")
        try:
            self.assertEqual(resumed.run_once(), 2)  # replay source, then checkpoint its transition event
            self.assertEqual(resumed.cursor_position(), max(event["seq"] for event in self.ledger.events()))
            self.assertEqual(resumed.run_once(), 0)
            events = self.ledger.events()
            self.assertEqual([event["event_type"] for event in events],
                             ["assignment.created", "assignment.transitioned"])
            self.assertEqual(self.ledger.get("crash-window")["state"], "ready")
        finally:
            resumed.close()

    def test_repeated_same_consumer_does_not_duplicate_progress(self):
        self.create("repeat-event")
        processor = self.processor(consumer_id="repeat-test")
        try:
            self.assertEqual(processor.run_once(), 1)
            self.assertEqual(processor.run_once(), 1)
            self.assertEqual(processor.run_once(), 0)
            self.assertEqual(processor.run_once(), 0)
            self.assertEqual(self.ledger.get("repeat-event")["state"], "ready")
            self.assertEqual(len(self.ledger.events()), 2)
        finally:
            processor.close()

    def test_handler_failure_preserves_cursor_for_retry(self):
        self.create("failed-handler")
        processor = self.processor(consumer_id="failure-test")
        try:
            with patch.object(processor, "_handle", side_effect=ProcessorError("injected transient failure")):
                with self.assertRaises(ProcessorError):
                    processor.run_once()
            self.assertEqual(processor.cursor_position(), 0)
            self.assertEqual(processor.run_once(), 1)
            self.assertEqual(self.ledger.get("failed-handler")["state"], "ready")
        finally:
            processor.close()


if __name__ == "__main__":
    unittest.main()
