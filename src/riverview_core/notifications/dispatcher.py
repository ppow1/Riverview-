# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/notifications/dispatcher.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.2
# Purpose: Project durable CME attention into a replay-safe notification outbox
# Execution Model: Continuous scheduled reconciliation of PostgreSQL source rows
# Observability: Durable notification rows and dispatcher health; sanitized logs
# Dependencies: PostgreSQL 16; Psycopg 3; notification migrations 0006 and 0007
# Authority: Reads CME/assignment state; writes notification-owned tables only
# Changed: 2026-10-11 UTC | RV-M3.2-001 | Keep failed scans from advancing the last-successful-scan timestamp
# Contracts: docs/components/NOTIFICATION_DELIVERY.md
# Tests: tests/test_notifications.py
# History: New file; Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Continuously and idempotently project CME attention into visual notices."""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import threading
import time
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .policy import allowed

_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_SERVICE_ID = "notification.dispatcher.v1"
_EVENT_TYPES = ("assignment_stalled", "deadline_missed", "assignment_attention",
                "recovery_requested", "monitor_failed", "attention_resolved")


class NotificationDispatcher:
    """Re-scan unprojected source rows; unique event identity is the replay fence."""

    def __init__(self, dsn: str, *, schema: str = "public", poll_interval: float = 2.0,
                 max_backoff_seconds: float = 30.0, batch_size: int = 100,
                 service_id: str = _SERVICE_ID):
        if not isinstance(schema, str) or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid PostgreSQL schema")
        if not 0.05 <= poll_interval <= 3600 or not poll_interval <= max_backoff_seconds <= 3600:
            raise ValueError("invalid dispatcher retry bounds")
        if not 1 <= batch_size <= 500:
            raise ValueError("batch_size must be between 1 and 500")
        self.dsn = dsn
        self.schema = schema
        self.poll_interval = poll_interval
        self.max_backoff_seconds = max_backoff_seconds
        self.batch_size = batch_size
        self.service_id = service_id
        self.instance_id = uuid4()

    def _connection(self):
        return psycopg.connect(self.dsn, connect_timeout=3, row_factory=dict_row,
                               application_name="riverview-notification-dispatcher")

    def _health(self, cur, *, status, error_type=None, scanned=0, created=0, requests=0,
                successful_scan=True):
        cur.execute(sql.SQL("""INSERT INTO {}.notification_dispatcher_health
            (service_id,instance_id,status,last_heartbeat_at,last_scan_at,last_error_type,
             source_events_scanned,notifications_created,decision_requests_created)
            VALUES (%s,%s,%s,clock_timestamp(),CASE WHEN %s THEN clock_timestamp() END,%s,%s,%s,%s)
            ON CONFLICT(service_id) DO UPDATE SET instance_id=excluded.instance_id,
              status=excluded.status,last_heartbeat_at=excluded.last_heartbeat_at,
              last_scan_at=COALESCE(excluded.last_scan_at,notification_dispatcher_health.last_scan_at),
              last_error_type=excluded.last_error_type,
              source_events_scanned=notification_dispatcher_health.source_events_scanned+excluded.source_events_scanned,
              notifications_created=notification_dispatcher_health.notifications_created+excluded.notifications_created,
              decision_requests_created=notification_dispatcher_health.decision_requests_created+excluded.decision_requests_created""").format(
                  sql.Identifier(self.schema)),
                  (self.service_id, self.instance_id, status, successful_scan, error_type,
                   scanned, created, requests))

    def scan_once(self) -> dict:
        """Reconcile a bounded batch. No assignment rows are changed."""
        with self._connection() as db:
            with db.transaction(), db.cursor() as cur:
                cur.execute(sql.SQL("SELECT set_config('search_path', %s, true)").format(),
                            (self.schema,))
                cur.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) AS locked",
                            (f"riverview-notification-dispatcher:{self.schema}",))
                if not cur.fetchone()["locked"]:
                    return {"status": "another_instance_active", "scanned": 0,
                            "notifications_created": 0, "notifications_suppressed": 0,
                            "decision_requests_created": 0}
                cur.execute("""SELECT level,quiet_hours_enabled,quiet_start,quiet_end,quiet_timezone
                               FROM notification_settings WHERE settings_id=1""")
                preferences = cur.fetchone()
                if preferences is None:
                    raise RuntimeError("notification_settings_not_initialized")
                settings = {"level": preferences["level"], "quiet_hours": {
                    "enabled": preferences["quiet_hours_enabled"],
                    "start": preferences["quiet_start"].strftime("%H:%M"),
                    "end": preferences["quiet_end"].strftime("%H:%M"),
                    "timezone": preferences["quiet_timezone"]}}
                cur.execute("""SELECT e.event_id,e.assignment_id,e.event_type,e.recorded_at,
                                      a.state AS assignment_state,a.version AS assignment_version
                               FROM cme_monitor_events e
                               LEFT JOIN assignments a ON a.id=e.assignment_id
                               WHERE e.event_type = ANY(%s)
                                 AND NOT EXISTS (SELECT 1 FROM attention_notifications n
                                                 WHERE n.source_event_id=e.event_id)
                                 AND NOT EXISTS (SELECT 1 FROM notification_suppressions s
                                                 WHERE s.source_event_id=e.event_id)
                                 AND (e.assignment_id IS NULL OR NOT EXISTS (
                                     SELECT 1 FROM events p WHERE p.assignment_id=e.assignment_id
                                       AND p.privacy_domain <> 'institution'))
                               ORDER BY e.recorded_at,e.event_id
                               LIMIT %s FOR UPDATE OF e SKIP LOCKED""",
                            (list(_EVENT_TYPES), self.batch_size))
                rows = cur.fetchall()
                created = 0
                suppressed = 0
                requests = 0
                for row in rows:
                    permitted, suppression_reason = allowed(row["event_type"], settings)
                    if not permitted:
                        cur.execute("""INSERT INTO notification_suppressions
                            (source_event_id,event_type,reason) VALUES (%s,%s,%s)
                            ON CONFLICT(source_event_id) DO NOTHING""",
                                    (row["event_id"], row["event_type"], suppression_reason))
                        suppressed += 1
                        continue
                    request_id = None
                    if (row["event_type"] == "assignment_attention" and
                            row["assignment_state"] == "awaiting_steward" and
                            row["assignment_id"]):
                        cur.execute("""INSERT INTO steward_decision_requests
                            (source_event_id,assignment_id,assignment_version,request_type)
                            VALUES (%s,%s,%s,'assignment_review') ON CONFLICT DO NOTHING
                            RETURNING request_id""",
                            (row["event_id"], row["assignment_id"], row["assignment_version"]))
                        result = cur.fetchone()
                        if result:
                            request_id = result["request_id"]
                            requests += 1
                        else:
                            cur.execute("""SELECT request_id FROM steward_decision_requests
                                           WHERE assignment_id=%s AND status='pending'
                                           ORDER BY created_at,request_id LIMIT 1""",
                                        (row["assignment_id"],))
                            request = cur.fetchone()
                            request_id = request["request_id"] if request else None
                    cur.execute("""INSERT INTO attention_notifications
                        (source_event_id,decision_request_id,assignment_id,event_type,summary_code,
                         source_recorded_at)
                        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(source_event_id) DO NOTHING
                        RETURNING notification_id""",
                        (row["event_id"], request_id, row["assignment_id"], row["event_type"],
                         row["event_type"], row["recorded_at"]))
                    notice = cur.fetchone()
                    if notice:
                        created += 1
                        cur.execute("""INSERT INTO notification_events
                            (notification_id,event_type,actor_type,idempotency_key)
                            VALUES (%s,'notification_queued','notification_dispatcher',%s)
                            ON CONFLICT(idempotency_key) DO NOTHING""",
                            (notice["notification_id"],
                             f"queued:{row['event_id']}"))
                self._health(cur, status="healthy", scanned=len(rows), created=created,
                             requests=requests)
                return {"status": "healthy", "scanned": len(rows),
                        "notifications_created": created,
                        "notifications_suppressed": suppressed,
                        "decision_requests_created": requests}

    def _record_failure(self, error_type: str) -> None:
        try:
            with self._connection() as db:
                with db.transaction(), db.cursor() as cur:
                    cur.execute(sql.SQL("SELECT set_config('search_path', %s, true)"),
                                (self.schema,))
                    self._health(cur, status="degraded", error_type=error_type,
                                 successful_scan=False)
        except psycopg.Error:
            return

    def run_forever(self, stop_event: threading.Event | None = None) -> None:
        """Keep reconciling with bounded backoff; only an explicit signal stops the loop."""
        stop_event = stop_event or threading.Event()
        delay = self.poll_interval
        logging.info(json.dumps({"event": "notification_dispatcher_started",
                                 "service_id": self.service_id,
                                 "instance_id": str(self.instance_id)}))
        while not stop_event.is_set():
            try:
                self.scan_once()
                delay = self.poll_interval
            except (psycopg.Error, RuntimeError, ValueError) as exc:
                error_type = type(exc).__name__
                logging.error(json.dumps({"event": "notification_dispatcher_retry",
                                          "failure_type": error_type,
                                          "retry_seconds": delay}))
                self._record_failure(error_type)
                delay = min(self.max_backoff_seconds, max(self.poll_interval, delay * 2))
            stop_event.wait(delay)
        logging.info(json.dumps({"event": "notification_dispatcher_stopped",
                                 "instance_id": str(self.instance_id)}))


def main():
    dsn = os.environ.get("RIVERVIEW_DATABASE_DSN", "")
    if not dsn:
        raise SystemExit("RIVERVIEW_DATABASE_DSN is required")
    dispatcher = NotificationDispatcher(
        dsn, schema=os.environ.get("RIVERVIEW_NOTIFICATION_SCHEMA", "riverview_dev"),
        poll_interval=float(os.environ.get("RIVERVIEW_NOTIFICATION_POLL_SECONDS", "2")),
        max_backoff_seconds=float(os.environ.get("RIVERVIEW_NOTIFICATION_MAX_BACKOFF_SECONDS", "30")))
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    logging.basicConfig(level=os.environ.get("RIVERVIEW_LOG_LEVEL", "INFO"))
    dispatcher.run_forever(stop)


if __name__ == "__main__":
    main()
