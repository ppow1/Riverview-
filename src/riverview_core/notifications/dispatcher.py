# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/notifications/dispatcher.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.2
# Changed: 2026-10-24 UTC | RV-DELIVER-GRACE-BLOCKED-ESCALATION-20261024 | Project durable Grace blocked-objective events into the existing dashboard notification outbox.
# Purpose: Project durable CME attention into a replay-safe notification outbox
# Execution Model: Continuous scheduled reconciliation of PostgreSQL source rows
# Observability: Durable notification rows and dispatcher health; sanitized logs
# Dependencies: PostgreSQL 16; Psycopg 3; notification migration 0006
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

_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_SERVICE_ID = "notification.dispatcher.v1"
_EVENT_TYPES = ("assignment_stalled", "deadline_missed", "assignment_attention",
                "recovery_requested", "monitor_failed", "attention_resolved",
                "grace_objective_blocked")


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
                            "notifications_created": 0, "decision_requests_created": 0}
                cur.execute("""SELECT e.event_id,e.assignment_id,e.event_type,e.recorded_at,e.details,
                                      a.state AS assignment_state,a.version AS assignment_version
                               FROM cme_monitor_events e
                               LEFT JOIN assignments a ON a.id=e.assignment_id
                               WHERE e.event_type = ANY(%s)
                                 AND NOT EXISTS (SELECT 1 FROM attention_notifications n
                                                 WHERE n.source_event_id=e.event_id)
                                 AND (e.assignment_id IS NULL OR NOT EXISTS (
                                     SELECT 1 FROM events p WHERE p.assignment_id=e.assignment_id
                                       AND p.privacy_domain <> 'institution'))
                               ORDER BY e.recorded_at,e.event_id
                               LIMIT %s FOR UPDATE OF e SKIP LOCKED""",
                            (list(_EVENT_TYPES), self.batch_size))
                rows = cur.fetchall()
                created = 0
                requests = 0
                for row in rows:
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
                        if row["event_type"] == "grace_objective_blocked":
                            details = row["details"] or {}
                            objective_id = details.get("objective_id")
                            objective_revision = details.get("objective_revision")
                            if (isinstance(objective_id, str) and objective_id and
                                    type(objective_revision) is int and objective_revision > 0):
                                cur.execute("""INSERT INTO grace_recovery_decision_requests
                                    (source_event_id,notification_id,objective_id,objective_revision,
                                     recovery_action,attempt_limit,expires_at)
                                    VALUES (%s,%s,%s,%s,'retry_reasoning_once',1,
                                            clock_timestamp()+interval '24 hours')
                                    ON CONFLICT(source_event_id) DO NOTHING""",
                                    (row["event_id"], notice["notification_id"],
                                     objective_id, objective_revision))
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
