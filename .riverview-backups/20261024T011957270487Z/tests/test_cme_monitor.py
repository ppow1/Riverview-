# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_cme_monitor.py
# Component: CME
# Revision: 1.0.4
# Purpose: Verify concurrent monitoring, durable alerts, health and process restart
# Execution Model: Isolated PostgreSQL integration tests and real monitor subprocesses
# Observability: CME health rows, append-only alerts and independent status projection
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL 16 test database
# Authority: Creates and drops only unique rvtest_* schemas
# Changed: 2026-10-10 UTC | RV-M2.4-001 | Verify stale/unavailable CME health and unknown worker state
# Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT | Exercise registry-backed worker grant checks
# Contracts: docs/components/CME_MONITOR.md; docs/ROADMAP.md
# Tests: This file
# History: Git and revision/backup manifest
# =============================================================================
"""PostgreSQL-backed tests for CME monitoring; never target shared app data."""

import os
import signal
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class CMEMonitorTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.postgres_migrations import apply_migrations

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
        self.root = Path(__file__).resolve().parents[1] / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=self.root / "assignment_scheduler/migrations")
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=self.root / "worker_adapter/migrations")
        self.assertEqual(apply_migrations(
            DSN, schema=self.schema, migrations_dir=self.root / "cme/migrations"),
            ["0005_cme_monitoring"])
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=self.root / "institutional_authority/migrations")
        self.admin.execute("INSERT INTO institutional_principals(principal_id,principal_kind) "
                           "VALUES ('steward:test','steward')")
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        from riverview_core.cme import CMEPostgresMonitor
        self.monitor = CMEPostgresMonitor(DSN, schema=self.schema,
                                          stall_after_seconds=5,
                                          worker_freshness_seconds=0.05,
                                          poll_interval=0.05,
                                          max_backoff_seconds=0.2)

    def register_worker(self, worker, worker_id, capabilities, scope):
        import hashlib
        import secrets
        from uuid import uuid4

        token = secrets.token_urlsafe(32)
        principal_id = "worker-principal:" + worker_id
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        self.admin.execute(
            "INSERT INTO institutional_principals(principal_id,principal_kind) VALUES (%s,'worker')",
            (principal_id,))
        self.admin.execute("""INSERT INTO principal_credentials
            (credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)""",
            (uuid4(), principal_id, digest))
        actions = ["worker.register"]
        if worker.SHA256_CAPABILITY in capabilities:
            actions.append("assignment.execute")
        for action in actions:
            self.admin.execute("""INSERT INTO authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                VALUES (%s,%s,%s,%s,'steward:test','rv.policy:cme-fixture.v1')""",
                (f"test:{action}:{worker_id}", principal_id, action, scope))
        return worker.register_worker(worker_id, capabilities, scope,
                                      credential=token)

    def tearDown(self):
        from psycopg import sql
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def create_assignment(self, name, *, state="queued"):
        assignment_id = f"monitor-{name}-{uuid4().hex}"
        self.ledger.create(assignment_id, "engineering", f"create:{assignment_id}",
                           authority_ref="grant:test", objective_ref=f"objective:{name}",
                           actor_id="resident:test")
        if state in {"ready", "running"}:
            self.ledger.transition(assignment_id, "ready", "intake", f"ready:{assignment_id}",
                                   actor_id="event-processor")
        if state == "running":
            from riverview_core.worker_adapter import PostgresWorkerAdapter
            worker = PostgresWorkerAdapter(DSN, schema=self.schema)
            worker_id = f"worker:{assignment_id}"
            try:
                token = self.register_worker(worker, worker_id,
                    [worker.SHA256_CAPABILITY], "grant:test")
                lease = worker.claim_next(worker_id, token, lease_seconds=30)
                self.assertEqual(lease["assignment"]["id"], assignment_id)
                worker.start_assignment(assignment_id, worker_id, token,
                                        lease["lease"]["generation"])
            finally:
                worker.close()
        return assignment_id

    def make_stale(self, assignment_id, *, expired_lease=False):
        with self.admin.cursor() as cur:
            cur.execute("UPDATE events SET recorded_at=clock_timestamp()-interval '10 seconds' "
                        "WHERE assignment_id=%s", (assignment_id,))
            cur.execute("UPDATE assignments SET updated_at=clock_timestamp()-interval '10 seconds' "
                        "WHERE id=%s", (assignment_id,))
            if expired_lease:
                cur.execute("UPDATE assignment_leases SET acquired_at=clock_timestamp()-interval '11 seconds', "
                            "heartbeat_at=clock_timestamp()-interval '10 seconds', "
                            "expires_at=clock_timestamp()-interval '1 second' WHERE assignment_id=%s",
                            (assignment_id,))

    def event_rows(self, assignment_id):
        with self.admin.cursor() as cur:
            cur.execute("SELECT event_type,event_key,attention_key,details FROM cme_monitor_events "
                        "WHERE assignment_id=%s ORDER BY recorded_at,event_id", (assignment_id,))
            return cur.fetchall()

    def test_stall_deadline_and_expired_lease_do_not_block_unrelated_assignment(self):
        from riverview_core.assignment_scheduler import PostgresAssignmentScheduler

        stalled = self.create_assignment("stalled", state="running")
        self.make_stale(stalled, expired_lease=True)
        overdue = self.create_assignment("overdue")
        self.monitor.set_deadline(overdue, datetime.now(timezone.utc) - timedelta(seconds=2))
        unrelated = self.create_assignment("unrelated", state="ready")

        result = self.monitor.scan_once()
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["stalled"], 1)
        self.assertEqual(result["overdue"], 1)
        self.assertEqual(result["recovery_requests"], 1)
        observed = {row["assignment_id"]: row for row in result["assignments"]}
        self.assertIn(stalled, observed)
        self.assertIn(overdue, observed)
        self.assertIn(unrelated, observed)
        self.assertEqual(observed[stalled]["worker_health"], "stale")
        self.assertIn("stale", {worker["health"] for worker in result["workers"]})
        self.assertEqual(self.ledger.get(stalled)["state"], "running")

        # The monitor is observational: a separate scheduler can still claim other work.
        scheduler = PostgresAssignmentScheduler(DSN, schema=self.schema)
        try:
            claim = scheduler.claim_next("worker:independent", lease_seconds=30)
        finally:
            scheduler.close()
        self.assertEqual(claim["assignment_id"], unrelated)
        types = [row["event_type"] for row in self.event_rows(stalled)]
        self.assertIn("assignment_stalled", types)
        self.assertIn("recovery_requested", types)
        deadline_types = [row["event_type"] for row in self.event_rows(overdue)]
        self.assertIn("deadline_missed", deadline_types)

        # Repeated scans use stable condition/event keys and emit no duplicates.
        first_counts = {key: len(self.event_rows(key)) for key in (stalled, overdue)}
        self.monitor.scan_once()
        self.assertEqual({key: len(self.event_rows(key)) for key in (stalled, overdue)},
                         first_counts)

    def test_progress_resolves_stall_and_cme_health_is_machine_readable(self):
        stalled = self.create_assignment("cleared", state="running")
        self.make_stale(stalled)
        self.monitor.scan_once()
        first = self.event_rows(stalled)
        self.assertEqual([row["event_type"] for row in first].count("assignment_stalled"), 1)
        self.ledger.transition(stalled, "awaiting_verification", "result-recorded",
                               f"progress:{stalled}", actor_id="worker:test")
        self.monitor.scan_once()
        event_types = [row["event_type"] for row in self.event_rows(stalled)]
        self.assertIn("attention_resolved", event_types)
        status = self.monitor.status()
        self.assertEqual(status["component_id"], "CME")
        self.assertEqual(status["status"], "healthy")
        self.assertGreaterEqual(status["open_attention_count"], 0)
        with self.admin.cursor() as cur:
            cur.execute("UPDATE cme_monitor_health SET last_heartbeat_at="
                        "clock_timestamp()-interval '2 minutes'")
        self.assertEqual(self.monitor.status(freshness_seconds=1)["status"], "stale")

    def test_registered_worker_without_lease_is_unknown_not_healthy(self):
        from riverview_core.worker_adapter import PostgresWorkerAdapter
        worker = PostgresWorkerAdapter(DSN, schema=self.schema)
        try:
            self.register_worker(worker, "worker:no-lease",
                                 [worker.SHA256_CAPABILITY], "grant:test")
        finally:
            worker.close()
        result = self.monitor.scan_once()
        observed = next(worker for worker in result["workers"]
                        if worker["worker_id"] == "worker:no-lease")
        self.assertEqual(observed["health"], "unknown")
        self.admin.execute("UPDATE worker_registry SET active=FALSE WHERE worker_id='worker:no-lease'")
        result = self.monitor.scan_once()
        observed = next(worker for worker in result["workers"]
                        if worker["worker_id"] == "worker:no-lease")
        self.assertEqual(observed["health"], "unavailable")

    def test_deadline_requires_timezone_aware_datetime(self):
        assignment_id = self.create_assignment("invalid-deadline")
        with self.assertRaisesRegex(ValueError, "timezone-aware datetime"):
            self.monitor.set_deadline(assignment_id, datetime.now())
        with self.assertRaisesRegex(ValueError, "timezone-aware datetime"):
            self.monitor.set_deadline(assignment_id, "2026-10-10T00:00:00Z")

    def test_real_monitor_process_restart_reuses_durable_alert_and_refreshes_health(self):
        stalled = self.create_assignment("restart", state="running")
        self.make_stale(stalled, expired_lease=True)
        env = dict(os.environ)
        env.update({
            "PYTHONPATH": str(self.root.parent),
            "RIVERVIEW_DATABASE_DSN": DSN,
            "RIVERVIEW_CME_SCHEMA": self.schema,
            "RIVERVIEW_CME_STALL_AFTER_SECONDS": "0.05",
            "RIVERVIEW_CME_WORKER_FRESHNESS_SECONDS": "0.05",
            "RIVERVIEW_CME_POLL_INTERVAL_SECONDS": "0.05",
            "RIVERVIEW_CME_MAX_BACKOFF_SECONDS": "0.2",
        })

        def start():
            return subprocess.Popen([sys.executable, "-m", "riverview_core.cme"],
                                    env=env, cwd=self.root.parents[1],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        first = start()
        try:
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if any(row["event_type"] == "assignment_stalled"
                       for row in self.event_rows(stalled)):
                    break
                if first.poll() is not None:
                    self.fail(f"CME process exited early with {first.returncode}")
                time.sleep(0.05)
            self.assertTrue(any(row["event_type"] == "assignment_stalled"
                                for row in self.event_rows(stalled)))
            first_instance = self.monitor.status()["instance_id"]
            before = len(self.event_rows(stalled))
            first.send_signal(signal.SIGKILL)
            first.wait(timeout=5)
        finally:
            if first.poll() is None:
                first.kill()
                first.wait(timeout=5)

        second = start()
        try:
            deadline = time.monotonic() + 8
            previous_instance = None
            while time.monotonic() < deadline:
                status = self.monitor.status()
                if (status.get("status") == "healthy" and status.get("instance_id") and
                        status.get("instance_id") != first_instance):
                    previous_instance = status["instance_id"]
                    break
                if second.poll() is not None:
                    self.fail(f"restarted CME process exited early with {second.returncode}")
                time.sleep(0.05)
            self.assertIsNotNone(previous_instance)
            self.assertEqual(len(self.event_rows(stalled)), before)
            with self.admin.cursor() as cur:
                cur.execute("SELECT count(*) AS count FROM cme_monitor_events WHERE event_type='monitor_started'")
                self.assertEqual(cur.fetchone()["count"], 2)
        finally:
            second.send_signal(signal.SIGTERM)
            second.wait(timeout=5)

    def test_database_unavailable_is_not_reported_healthy(self):
        from riverview_core.cme import CMEPostgresMonitor
        offline = CMEPostgresMonitor("host=/definitely-missing port=1 dbname=none user=none",
                                     schema="public", stall_after_seconds=1)
        self.assertEqual(offline.status()["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
