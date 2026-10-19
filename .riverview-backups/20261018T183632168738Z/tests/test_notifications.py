# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_notifications.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.4
# Purpose: Verify notification API privacy, provider status projection, recovery, and receipt authority
# Execution Model: Isolated PostgreSQL integration tests against unique rvtest_* schemas
# Observability: CME source events, notification rows, receipt ledger, decision request status
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL 16 test database
# Authority: Creates and drops only unique rvtest_* schemas; no shared state
# Changed: 2026-10-18 UTC | RV-NOTIFICATION-STATUS-PROJECTION-20261018 | Test push status API contract and read-only PostgreSQL projection
# Contracts: docs/components/NOTIFICATION_DELIVERY.md
# Tests: This file
# History: New file; Git and revision/backup manifest
# =============================================================================
"""PostgreSQL integration tests for durable, non-authoritative notifications."""

import json
import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from riverview_core.cme import CMEPostgresMonitor
from riverview_core.notifications import (NotificationConflict, NotificationDispatcher,
                                          NotificationNotFound, NotificationService)
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.postgres_migrations import apply_migrations
from riverview_core.status_dashboard.server import DashboardHTTPServer

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


class _NoopProjection:
    pass


class _FakeNotificationService:
    def list_notifications(self, *, limit=25):
        return {"schema_version": "rv.notifications.v1", "status": "available",
                "observed_at": "2026-10-11T00:00:00+00:00", "dispatcher": {"status": "healthy"},
                "push_delivery": {"schema_version":"rv.notification_push_status.v2",
                    "component_id":"NOTIFICATION-DELIVERY","status":"not_initialized",
                    "observed_at":"2026-10-11T00:00:00+00:00",
                    "freshness":{"state":"unknown","heartbeat_age_seconds":None,"threshold_seconds":15},
                    "queue":{"state":"not_initialized","by_state":{"queued":0,"sending":0,"retry":0,
                        "accepted":0,"acknowledged":0,"expired":0,"failed":0},
                        "retry_due_count":0,"expired_lease_count":0},
                    "recovery":{"state":"unknown","retry_pending_count":0,"expired_lease_count":0},
                    "failure":{"state":"none","code":None},"last_cycle_at":None,"counters":None,
                    "read_only":True,"content_included":False},
                "items": [], "limit": limit}

    def confirm_delivery(self, notice):
        return {"schema_version": "rv.notification_receipt.v1", "status": "delivered",
                "notification_id": notice, "recorded_at": "2026-10-11T00:00:00+00:00",
                "already_recorded": False, "decision_request_status": None,
                "authority_effect": "none"}

    def acknowledge_receipt(self, notice):
        return {"schema_version": "rv.notification_receipt.v1", "status": "acknowledged",
                "notification_id": notice, "recorded_at": "2026-10-11T00:00:00+00:00",
                "already_recorded": False,
                "decision_request_status": "pending", "authority_effect": "none"}


class NotificationHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token_path = Path(self.temp.name) / "token"
        self.token = "T" * 43
        self.token_path.write_text(self.token)
        self.token_path.chmod(0o600)
        self.server = None
        for port in range(8799, 8699, -1):
            try:
                self.server = DashboardHTTPServer("127.0.0.1", port, self.token_path,
                    _NoopProjection(), ROOT / "src/riverview_core/status_dashboard/static",
                    notification_service=_FakeNotificationService())
                break
            except OSError:
                continue
        self.assertIsNotNone(self.server)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, *, token=None, body=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        headers = {"Authorization": "Bearer " + token} if token else {}
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        result = (response.status, json.loads(response.read()))
        conn.close()
        return result

    def test_notifications_are_authenticated_and_only_receipt_posts_are_allowed(self):
        notice = str(uuid4())
        self.assertEqual(self.request("GET", "/api/v1/notifications")[0], 401)
        status, body = self.request("GET", "/api/v1/notifications?limit=999", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(body["limit"], 50)
        self.assertEqual(body["push_delivery"]["status"], "not_initialized")
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / "docs/components/NOTIFICATION_DELIVERY_API.schema.json").read_text())
        Draft202012Validator(schema).validate(body)
        status_schema = schema["$defs"]["pushDelivery"]
        examples = json.loads((ROOT / "tests/fixtures/notification_delivery_status_examples.json").read_text())
        for example in examples["examples"]:
            Draft202012Validator(status_schema).validate(example)
        status, body = self.request("POST", f"/api/v1/notifications/{notice}/acknowledge", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(body["authority_effect"], "none")
        self.assertEqual(body["decision_request_status"], "pending")
        Draft202012Validator(schema).validate(body)
        self.assertEqual(self.request("POST", "/api/v1/status", token=self.token)[0], 405)
        status, body = self.request("POST", f"/api/v1/notifications/{notice}/delivered",
                                    token=self.token, body="x")
        self.assertEqual(status, 400)

    def test_dispatcher_unit_is_dedicated_credentialled_and_non_root(self):
        unit = (ROOT / "deploy/systemd/riverview-notification-dispatcher.service").read_text()
        self.assertIn("User=riverview", unit)
        self.assertIn("LoadCredential=pgpass:/etc/riverview/pgpass", unit)
        self.assertIn("NoNewPrivileges=yes", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("riverview-notification-dispatcher/current", unit)
        self.assertNotIn("sudo", unit.lower())


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class NotificationPostgresTests(unittest.TestCase):
    def setUp(self):
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        core = ROOT / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        for component in ("assignment_scheduler", "worker_adapter", "cme", "notifications"):
            apply_migrations(DSN, schema=self.schema,
                             migrations_dir=core / component / "migrations")
        self.admin.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.monitor = CMEPostgresMonitor(DSN, schema=self.schema, stall_after_seconds=0.01)
        self.dispatcher = NotificationDispatcher(DSN, schema=self.schema, poll_interval=0.05)
        self.service = NotificationService(DSN, schema=self.schema)

    def tearDown(self):
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def create_assignment(self, label, *, awaiting=False):
        assignment_id = f"notify-{label}-{uuid4().hex}"
        self.ledger.create(assignment_id, "engineering", f"create:{assignment_id}",
                           authority_ref="grant:test", objective_ref="objective:notification-test",
                           actor_id="resident:test")
        self.ledger.transition(assignment_id, "ready", "ready", f"ready:{assignment_id}",
                               actor_id="event-processor")
        if awaiting:
            self.ledger.transition(assignment_id, "running", "dispatch", f"run:{assignment_id}",
                                   actor_id="worker:test")
            self.ledger.transition(assignment_id, "awaiting_steward", "needs-review",
                                   f"review:{assignment_id}", actor_id="worker:test")
        return assignment_id

    def stale_event(self, assignment_id):
        with self.admin.cursor() as cur:
            cur.execute("UPDATE assignments SET updated_at=clock_timestamp()-interval '10 seconds' "
                        "WHERE id=%s", (assignment_id,))
            cur.execute("UPDATE events SET recorded_at=clock_timestamp()-interval '10 seconds' "
                        "WHERE assignment_id=%s", (assignment_id,))
        observed = self.monitor.scan_once()
        self.assertEqual(observed["status"], "healthy")
        self.assertGreaterEqual(observed["stalled"], 1)

    def rows(self, table):
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("SELECT * FROM {}.{} ORDER BY 1").format(
                sql.Identifier(self.schema), sql.Identifier(table)))
            return cur.fetchall()

    def test_real_stall_event_projects_once_across_dispatcher_restart(self):
        assignment = self.create_assignment("restart")
        self.stale_event(assignment)
        first = self.dispatcher.scan_once()
        self.assertEqual(first["notifications_created"], 1)
        self.assertEqual(self.dispatcher.scan_once()["notifications_created"], 0)
        # A new dispatcher instance has no in-memory cursor; durable uniqueness is the fence.
        restarted = NotificationDispatcher(DSN, schema=self.schema)
        self.assertEqual(restarted.scan_once()["notifications_created"], 0)
        notice = self.rows("attention_notifications")
        self.assertEqual(len(notice), 1)
        self.assertEqual(notice[0]["assignment_id"], assignment)
        self.assertEqual(len(self.rows("notification_events")), 1)

    def test_receipt_states_are_ordered_idempotent_and_never_resolve_request(self):
        assignment = self.create_assignment("awaiting", awaiting=True)
        self.monitor.scan_once()
        with self.admin.cursor() as cur:
            cur.execute("SELECT event_id FROM cme_monitor_events WHERE assignment_id=%s "
                        "AND event_type='assignment_attention'", (assignment,))
            self.assertIsNotNone(cur.fetchone())
        self.dispatcher.scan_once()
        notices = self.service.list_notifications(limit=10)["items"]
        self.assertEqual(len(notices), 1)
        notice = notices[0]
        self.assertEqual(notice["delivery_status"], "queued")
        self.assertEqual(notice["decision_status"], "pending")
        with self.assertRaises(NotificationConflict):
            self.service.acknowledge_receipt(notice["notification_id"])
        delivered = self.service.confirm_delivery(notice["notification_id"])
        self.assertEqual(delivered["authority_effect"], "none")
        self.assertEqual(delivered["decision_request_status"], "pending")
        self.assertTrue(self.service.confirm_delivery(notice["notification_id"])["already_recorded"])
        ack = self.service.acknowledge_receipt(notice["notification_id"])
        self.assertEqual(ack["decision_request_status"], "pending")
        self.assertEqual(ack["authority_effect"], "none")
        self.assertTrue(self.service.acknowledge_receipt(notice["notification_id"])["already_recorded"])
        self.assertEqual(self.rows("steward_decision_requests")[0]["status"], "pending")
        self.assertEqual(len(self.rows("notification_events")), 3)

    def test_private_assignment_never_becomes_an_external_notice(self):
        assignment = self.create_assignment("private")
        with self.admin.cursor() as cur:
            cur.execute("UPDATE events SET privacy_domain='undercurrent' WHERE assignment_id=%s",
                        (assignment,))
        self.stale_event(assignment)
        self.assertEqual(self.dispatcher.scan_once()["notifications_created"], 0)
        self.assertEqual(self.service.list_notifications()["items"], [])

    def test_unknown_and_unavailable_states_are_not_success(self):
        with self.assertRaises(NotificationNotFound):
            self.service.confirm_delivery(str(uuid4()))
        missing = NotificationService(DSN, schema="rvtest_absent_notifications")
        page = missing.list_notifications()
        self.assertEqual(page["status"], "not_initialized")
        self.assertEqual(page["push_delivery"]["status"], "not_initialized")

    def test_provider_status_projection_reports_fresh_queue_state_without_content(self):
        with self.admin.cursor() as cur:
            cur.execute("""INSERT INTO cme_monitor_events
                (event_key,service_id,assignment_id,event_type,details)
                VALUES (%s,'notification_status_fixture',NULL,'assignment_stalled','{}'::jsonb)
                RETURNING event_id""", ("status:" + uuid4().hex,))
            source_event = cur.fetchone()["event_id"]
            cur.execute("""INSERT INTO attention_notifications
                (source_event_id,event_type,summary_code,source_recorded_at)
                VALUES (%s,'assignment_stalled','assignment_stalled',clock_timestamp())
                RETURNING notification_id""", (source_event,))
            notice_id = cur.fetchone()["notification_id"]
            cur.execute("""INSERT INTO notification_delivery_queue
                (notification_id,provider,severity,title,message,idempotency_key,max_attempts,provider_receipt)
                VALUES (%s,'ntfy','warning','PRIVATE_TITLE_SENTINEL','PRIVATE_BODY_SENTINEL',%s,3,
                    'PRIVATE_RECEIPT_SENTINEL')""", (notice_id, str(notice_id) + ':ntfy'))
            cur.execute("""INSERT INTO notification_delivery_health
                (service_id,instance_id,status,last_heartbeat_at,last_cycle_at)
                VALUES ('notification.delivery.v1',%s,'healthy',clock_timestamp(),clock_timestamp())""",
                (uuid4(),))
        projection = self.service.list_notifications()["push_delivery"]
        self.assertEqual(projection["status"], "healthy")
        self.assertEqual(projection["freshness"]["state"], "fresh")
        self.assertEqual(projection["queue"]["by_state"]["queued"], 1)
        self.assertEqual(projection["recovery"]["state"], "idle")
        self.assertTrue(projection["read_only"])
        self.assertFalse(projection["content_included"])
        self.assertNotIn("last_heartbeat_at", projection)
        serialized = json.dumps(projection)
        for private in ("PRIVATE_TITLE_SENTINEL", "PRIVATE_BODY_SENTINEL",
                        "PRIVATE_RECEIPT_SENTINEL", str(notice_id)):
            self.assertNotIn(private, serialized)

        with self.admin.cursor() as cur:
            cur.execute("""UPDATE notification_delivery_queue SET state='retry',
                next_attempt_at=clock_timestamp()-interval '1 second' WHERE notification_id=%s""",
                (notice_id,))
            cur.execute("""UPDATE notification_delivery_health SET status='degraded',
                last_heartbeat_at=clock_timestamp(),last_error_code='provider_http_503'
                WHERE service_id='notification.delivery.v1'""")
        degraded = self.service.push_delivery_status()
        self.assertEqual(degraded["status"], "degraded")
        self.assertEqual(degraded["failure"], {"state":"recorded","code":"provider_http_503"})
        self.assertEqual(degraded["queue"]["retry_due_count"], 1)
        self.assertEqual(degraded["recovery"]["state"], "retry_pending")

        with self.admin.cursor() as cur:
            cur.execute("""UPDATE notification_delivery_health SET status='healthy',
                last_heartbeat_at=clock_timestamp()-interval '30 seconds',last_error_code=NULL
                WHERE service_id='notification.delivery.v1'""")
        stale = self.service.push_delivery_status()
        self.assertEqual(stale["status"], "stale")
        self.assertEqual(stale["freshness"]["state"], "stale")
        self.assertEqual(stale["recovery"]["state"], "retry_pending")

    def test_provider_status_reports_unavailable_without_leaking_database_errors(self):
        offline = NotificationService(
            "host=127.0.0.1 port=1 dbname=unavailable user=unavailable connect_timeout=1",
            schema=self.schema).push_delivery_status()
        self.assertEqual(offline["status"], "unavailable")
        self.assertEqual(offline["freshness"]["state"], "unavailable")
        self.assertEqual(offline["failure"], {"state":"unavailable","code":None})

    def test_receipt_history_is_append_only_and_stopped_dispatcher_becomes_stale(self):
        assignment = self.create_assignment("stale-health")
        self.stale_event(assignment)
        self.dispatcher.scan_once()
        notice = self.rows("attention_notifications")[0]
        with self.assertRaises(psycopg.errors.RaiseException):
            self.admin.execute("UPDATE notification_events SET event_type='delivery_confirmed'")
        with self.assertRaises(psycopg.errors.RaiseException):
            self.admin.execute("DELETE FROM notification_events")
        self.admin.execute("UPDATE notification_dispatcher_health SET last_heartbeat_at="
                           "clock_timestamp()-interval '30 seconds' "
                           "WHERE service_id='notification.dispatcher.v1'")
        page = self.service.list_notifications(limit=10)
        self.assertEqual(page["dispatcher"]["status"], "stale")
        self.assertGreater(page["dispatcher"]["heartbeat_age_seconds"], 15)
        self.assertEqual(page["items"][0]["notification_id"], str(notice["notification_id"]))
