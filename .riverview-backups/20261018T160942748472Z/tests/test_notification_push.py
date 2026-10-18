# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_notification_push.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.1
# Purpose: Verify provider routing, durable outbox recovery, retries, and ack semantics
# Execution Model: Unit tests plus disposable PostgreSQL integration tests
# Observability: Queue state, provider call evidence, append-only event ledger
# Dependencies: Python 3.10+; Psycopg 3; optional disposable PostgreSQL 16
# Authority: Test-only schema; no production credential or provider call
# Changed: 2026-10-18 UTC | RV-NOTIFICATION-QUEUE-RETRY-ACCEPTANCE-20261018 | Add disposable retry/restart acceptance coverage
# Contracts: docs/components/NOTIFICATION_IPHONE_DELIVERY.md
# Tests: pytest tests/test_notification_push.py
# History: Git + .riverview-backups/manifest.jsonl
# =============================================================================
"""Provider and PostgreSQL tests for durable iPhone notification delivery."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qs

import psycopg
from psycopg import sql

from riverview_core.notifications.push import (
    HttpPushTransport, NotificationDeliveryManager, PushConfig,
    PushConfigurationError, PushProviderError,
)
from riverview_core.postgres_migrations import apply_migrations

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


class FakeTransport:
    def __init__(self, outcomes=None, receipts=None):
        self.outcomes = list(outcomes or [{"accepted": True}])
        self.receipts = dict(receipts or {})
        self.calls = []

    def send(self, provider, severity, title, message, idempotency_key):
        self.calls.append((provider, severity, idempotency_key))
        result = self.outcomes.pop(0) if self.outcomes else {"accepted": True}
        if isinstance(result, Exception):
            raise result
        return result

    def receipt(self, receipt_id):
        return self.receipts.get(receipt_id, {"acknowledged": False, "expired": False})


def config(*, routes=None, retry_limit=3):
    return PushConfig(
        routes=routes or {"info": ("ntfy",), "warning": ("ntfy", "pushover"),
                          "critical": ("pushover",)},
        event_severity={"attention_resolved": "info", "assignment_stalled": "warning",
                        "deadline_missed": "critical", "assignment_attention": "warning",
                        "recovery_requested": "critical", "monitor_failed": "critical"},
        ntfy_base_url="https://ntfy.example.test", ntfy_topic="riverview_test",
        retry_limit=retry_limit, retry_base_seconds=1, retry_max_seconds=5,
        emergency_retry_seconds=30, emergency_expire_seconds=300)


class PushConfigTests(unittest.TestCase):
    def test_config_rejects_public_ntfy_service(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"routes": {"info": ["ntfy"]},
                "ntfy": {"base_url": "https://ntfy.sh", "topic": "secret"}}))
            with self.assertRaisesRegex(PushConfigurationError, "public_ntfy_service_not_allowed"):
                PushConfig.load(path)

    def test_config_rejects_unbounded_retries_and_invalid_emergency_window(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"retry_limit": 100}))
            with self.assertRaisesRegex(PushConfigurationError, "retry_limit_out_of_range"):
                PushConfig.load(path)
            path.write_text(json.dumps({"emergency_retry_seconds": 5}))
            with self.assertRaisesRegex(PushConfigurationError, "invalid_emergency_retry_window"):
                PushConfig.load(path)

    def test_provider_requests_keep_credentials_out_of_urls_and_support_emergency_receipts(self):
        class Response:
            status = 200
            def __init__(self, body): self.body = body
            def read(self, _limit): return self.body
            def __enter__(self): return self
            def __exit__(self, *_args): return False

        with tempfile.TemporaryDirectory() as directory:
            credentials = Path(directory)
            for name, value in (("ntfy_token", "ntfy-secret"),
                                ("pushover_app_token", "app-secret"),
                                ("pushover_user_key", "user-secret")):
                path = credentials / name
                path.write_text(value)
                path.chmod(0o400)
            requests = []
            # JSON body fixture follows the real API receipt shape.
            def opener(request, timeout):
                requests.append((request, timeout))
                if request.full_url.endswith("messages.json"):
                    return Response(json.dumps({"status": 1, "receipt": "R" * 30}).encode())
                if "/receipts/" in request.full_url:
                    return Response(b'{"status":1,"acknowledged":1,"expired":0}')
                return Response(b"ok")
            transport = HttpPushTransport(config(), credentials_dir=directory, opener=opener)
            accepted = transport.send("pushover", "critical", "title", "body", "stable-key")
            self.assertEqual(accepted["receipt_id"], "R" * 30)
            payload = parse_qs(requests[0][0].data.decode())
            self.assertEqual(payload["priority"], ["2"])
            self.assertEqual(payload["retry"], ["30"])
            self.assertEqual(payload["expire"], ["300"])
            self.assertNotIn("app-secret", requests[0][0].full_url)
            self.assertTrue(transport.receipt("R" * 30)["acknowledged"])
            transport.send("ntfy", "warning", "title", "body", "stable-key")
            self.assertEqual(requests[2][0].get_header("Authorization"), "Bearer ntfy-secret")
            self.assertEqual(requests[2][0].full_url, "https://ntfy.example.test/riverview_test")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class PushDeliveryPostgresTests(unittest.TestCase):
    def setUp(self):
        self.schema = "rvtest_push_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        if not self.admin.execute("SELECT 1 FROM pg_roles WHERE rolname='riverview_core'").fetchone():
            self.admin.execute("CREATE ROLE riverview_core NOLOGIN")
        core = ROOT / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        for component in ("assignment_scheduler", "worker_adapter", "cme", "notifications"):
            apply_migrations(DSN, schema=self.schema,
                             migrations_dir=core / component / "migrations")
        self.manager_transport = FakeTransport()
        self.manager = NotificationDeliveryManager(DSN, config(), schema=self.schema,
                                                   transport=self.manager_transport)
        with self.admin.cursor() as cursor:
            cursor.execute("SET search_path TO " + self.schema)
            cursor.execute("""INSERT INTO cme_monitor_events
                (event_key,service_id,assignment_id,event_type,details)
                VALUES (%s,'test.notification',NULL,'assignment_stalled','{}'::jsonb)
                RETURNING event_id""", ("event:" + uuid4().hex,))
            source_event = cursor.fetchone()[0]
            cursor.execute("""INSERT INTO attention_notifications
                (source_event_id,event_type,summary_code,source_recorded_at)
                VALUES (%s,'assignment_stalled','assignment_stalled',clock_timestamp())
                RETURNING notification_id""", (source_event,))
            self.notification_id = cursor.fetchone()[0]

    def tearDown(self):
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def rows(self, query, params=()):
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
            cursor.execute(query, params)
            return cursor.fetchall()

    def test_reconcile_deduplicates_and_http_acceptance_is_not_phone_delivery(self):
        self.assertEqual(self.manager.reconcile(), {"notices_scanned": 1, "deliveries_queued": 2})
        self.assertEqual(self.manager.reconcile(), {"notices_scanned": 0, "deliveries_queued": 0})
        results = [self.manager.deliver_one(), self.manager.deliver_one()]
        self.assertEqual([item["status"] for item in results],
                         ["provider_accepted", "provider_accepted"])
        self.assertTrue(all(item["handset_delivery"] == "unverified" for item in results))
        self.assertEqual(len(self.rows("SELECT * FROM notification_delivery_queue")), 2)
        self.assertEqual(len(self.rows("SELECT * FROM notification_delivery_events WHERE event_type='delivery_queued'")), 2)

    def test_bounded_retry_then_success_and_terminal_failure(self):
        self.manager.config = config(routes={"warning": ("ntfy",)}, retry_limit=3)
        self.manager.reconcile()
        self.manager.transport = FakeTransport([
            PushProviderError("network unavailable"), {"accepted": True}])
        self.assertEqual(self.manager.deliver_one()["status"], "retry_or_failed")
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL("UPDATE {}.notification_delivery_queue SET next_attempt_at=clock_timestamp() WHERE provider='ntfy'").format(sql.Identifier(self.schema)))
        self.assertEqual(self.manager.deliver_one()["status"], "provider_accepted")
        state = self.rows("SELECT state,attempt_count,max_attempts FROM notification_delivery_queue")[0]
        self.assertEqual(state[0], "accepted")
        self.assertEqual((state[1], state[2]), (2, 3))

    def test_disposable_queue_retry_survives_worker_restart_without_duplicate_delivery(self):
        """Exercise durable notice-to-provider acceptance across a worker restart."""
        self.manager.config = config(routes={"warning": ("ntfy",)}, retry_limit=3)
        self.assertEqual(self.manager.reconcile(),
                         {"notices_scanned": 1, "deliveries_queued": 1})
        self.assertEqual(self.manager.reconcile(),
                         {"notices_scanned": 0, "deliveries_queued": 0})

        first_transport = FakeTransport([PushProviderError("temporary network failure")])
        self.manager.transport = first_transport
        failed_attempt = self.manager.deliver_one()
        self.assertEqual(failed_attempt["status"], "retry_or_failed")
        delivery_id = failed_attempt["delivery_id"]
        first_key = first_transport.calls[0][2]
        first_state = self.rows("""SELECT state,attempt_count,max_attempts,
                idempotency_key,last_error_code FROM notification_delivery_queue""")[0]
        self.assertEqual(first_state,
                         ("retry", 1, 3, first_key, "provider_error"))

        # Model a process restart: all retry intent and identity must come from PostgreSQL.
        restarted_transport = FakeTransport([{"accepted": True}])
        restarted = NotificationDeliveryManager(
            DSN, config(routes={"warning": ("ntfy",)}, retry_limit=3),
            schema=self.schema, transport=restarted_transport)
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL("UPDATE {}.notification_delivery_queue "
                "SET next_attempt_at=clock_timestamp() WHERE delivery_id=%s")
                .format(sql.Identifier(self.schema)), (delivery_id,))
        accepted = restarted.deliver_one()
        self.assertEqual(accepted["status"], "provider_accepted")
        self.assertEqual(accepted["delivery_id"], delivery_id)
        self.assertEqual(accepted["handset_delivery"], "unverified")
        self.assertEqual(restarted_transport.calls[0][2], first_key)

        final_state = self.rows("""SELECT state,attempt_count,max_attempts,
                idempotency_key,provider_accepted_at FROM notification_delivery_queue""")[0]
        self.assertEqual(final_state[:4], ("accepted", 2, 3, first_key))
        self.assertIsNotNone(final_state[4])
        self.assertEqual(len(self.rows("SELECT delivery_id FROM notification_delivery_queue")), 1)
        self.assertEqual(len(self.rows("""SELECT event_id FROM notification_delivery_events
                WHERE event_type='delivery_queued'""")), 1)
        self.assertEqual(len(self.rows("""SELECT event_id FROM notification_delivery_events
                WHERE event_type='retry_scheduled'""")), 1)
        self.assertEqual(len(self.rows("""SELECT event_id FROM notification_delivery_events
                WHERE event_type='provider_accepted'""")), 1)

    def test_retry_limit_moves_delivery_to_terminal_failed(self):
        self.manager.config = config(routes={"warning": ("ntfy",)}, retry_limit=1)
        self.manager.reconcile()
        self.manager.transport = FakeTransport([PushProviderError("provider unavailable")])
        self.assertEqual(self.manager.deliver_one()["status"], "retry_or_failed")
        state = self.rows("SELECT state,attempt_count,max_attempts,last_error_code FROM notification_delivery_queue")[0]
        self.assertEqual(state[0:3], ("failed", 1, 1))
        self.assertEqual(state[3], "provider_error")

    def test_expired_worker_lease_is_recovered_without_duplicate_row(self):
        self.manager.reconcile()
        first = self.manager._claim()
        self.assertIsNotNone(first)
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL("UPDATE {}.notification_delivery_queue SET lease_until=clock_timestamp()-interval '1 second' WHERE delivery_id=%s").format(sql.Identifier(self.schema)), (first["delivery_id"],))
        self.manager = NotificationDeliveryManager(DSN, config(), schema=self.schema,
                                                   transport=FakeTransport())
        recovered = self.manager._claim()
        self.assertEqual(recovered["delivery_id"], first["delivery_id"])
        self.assertNotEqual(recovered["lease_id"], first["lease_id"])
        self.assertEqual(recovered["attempt_count"], first["attempt_count"] + 1)
        self.assertEqual(len(self.rows("SELECT * FROM notification_delivery_queue")), 2)

    def test_pushover_emergency_acknowledgment_is_persisted(self):
        self.manager_transport = FakeTransport([{"accepted": True, "receipt_id": "A" * 30}],
                                               {"A" * 30: {"acknowledged": True, "expired": False}})
        self.manager.transport = self.manager_transport
        # Reconcile has both providers; select critical event through an isolated row.
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL("UPDATE {}.attention_notifications SET event_type='recovery_requested',summary_code='recovery_requested' WHERE notification_id=%s").format(sql.Identifier(self.schema)), (self.notification_id,))
        self.manager.reconcile()
        # Critical routes only to Pushover.
        self.assertEqual(self.manager.deliver_one()["provider"], "pushover")
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL("UPDATE {}.notification_delivery_queue SET next_receipt_check_at=clock_timestamp()-interval '1 second'").format(sql.Identifier(self.schema)))
        result = self.manager.poll_emergency_acknowledgments()
        self.assertEqual(result["acknowledged"], 1)
        state = self.rows("SELECT state,acknowledged_at FROM notification_delivery_queue")[0]
        self.assertEqual(state[0], "acknowledged")
        self.assertIsNotNone(state[1])
        self.assertEqual(len(self.rows("SELECT * FROM notification_delivery_events WHERE event_type='emergency_acknowledged'")), 1)

    def test_runtime_role_gets_only_required_source_and_queue_columns(self):
        self.manager.reconcile()
        limited = psycopg.connect(DSN, autocommit=True)
        try:
            limited.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO riverview_core").format(
                sql.Identifier(self.schema)))
            limited.execute("SET ROLE riverview_core")
            limited.execute(sql.SQL("SET search_path TO {},pg_catalog").format(
                sql.Identifier(self.schema)))
            self.assertEqual(len(limited.execute(
                "SELECT notification_id FROM attention_notifications").fetchall()), 1)
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                limited.execute("SELECT payload FROM events")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                limited.execute("UPDATE notification_delivery_queue SET title='forbidden'")
        finally:
            limited.close()
