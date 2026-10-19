# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/notifications/service.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.3
# Purpose: Project safe notification and provider-delivery status; persist visual receipts
# Execution Model: Request-driven bounded PostgreSQL transactions
# Observability: Notification rows and append-only delivery/acknowledgment events
# Dependencies: PostgreSQL 16; Psycopg 3; migration 0006
# Authority: Dashboard-client receipt only; cannot resolve a decision request
# Changed: 2026-10-18 UTC | RV-NOTIFICATION-STATUS-PROJECTION-20261018 | Add read-only provider queue/freshness projection
# Contracts: docs/components/NOTIFICATION_DELIVERY.md
# Tests: tests/test_notifications.py; tests/test_status_dashboard.py
# History: New file; Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Bounded visual notification projections and idempotent client receipts."""

from __future__ import annotations

import re
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_HEALTH_STALE_SECONDS = 15.0
_PUSH_HEALTH_STALE_SECONDS = 15.0
_PUSH_STATES = ("queued", "sending", "retry", "accepted", "acknowledged", "expired", "failed")
_SAFE_ERROR_CODE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_SUMMARY = {
    "assignment_stalled": "Assignment has no recent durable progress.",
    "deadline_missed": "An active assignment passed its configured deadline.",
    "assignment_attention": "An assignment requires attention.",
    "recovery_requested": "An expired execution lease requires recovery reconciliation.",
    "monitor_failed": "The CME monitor recorded a scan failure.",
    "attention_resolved": "A previously recorded attention condition was resolved.",
}


class NotificationUnavailable(RuntimeError):
    pass


class NotificationNotFound(RuntimeError):
    pass


class NotificationConflict(RuntimeError):
    pass


class NotificationService:
    """Only the visual notification ledger is writable through this API."""

    def __init__(self, dsn: str, *, schema: str = "public", connect_timeout: int = 2):
        if not isinstance(schema, str) or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid PostgreSQL schema")
        self.dsn = dsn
        self.schema = schema
        self.connect_timeout = connect_timeout

    def _connect(self):
        return psycopg.connect(self.dsn, connect_timeout=self.connect_timeout,
                               row_factory=dict_row, application_name="riverview-dashboard-notifications")

    def list_notifications(self, *, limit: int = 25) -> dict:
        limit = min(50, max(1, int(limit)))
        try:
            with self._connect() as db:
                with db.transaction(), db.cursor() as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SET LOCAL statement_timeout='2000ms'")
                    cur.execute("SELECT to_regclass(%s) AS notification_table",
                                (f"{self.schema}.attention_notifications",))
                    if not cur.fetchone()["notification_table"]:
                        return {"schema_version": "rv.notifications.v1", "status": "not_initialized",
                                "observed_at": None, "dispatcher": {"status": "not_initialized"},
                                "items": [], "limit": limit,
                                "push_delivery": self.push_delivery_status()}
                    cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                        sql.Identifier(self.schema)))
                    cur.execute("""SELECT n.notification_id,n.source_event_id,n.assignment_id,
                                         n.event_type,n.channel,n.source_recorded_at,n.created_at,
                                         n.delivered_at,n.acknowledged_at,d.request_id,
                                         d.status AS decision_status,d.assignment_version,
                                         CASE WHEN n.acknowledged_at IS NOT NULL THEN 'acknowledged'
                                              WHEN n.delivered_at IS NOT NULL THEN 'delivered'
                                              ELSE 'queued' END AS delivery_status
                                  FROM attention_notifications n
                                  LEFT JOIN steward_decision_requests d
                                    ON d.request_id=n.decision_request_id
                                  WHERE n.assignment_id IS NULL OR NOT EXISTS (
                                      SELECT 1 FROM events p WHERE p.assignment_id=n.assignment_id
                                        AND p.privacy_domain <> 'institution')
                                  ORDER BY n.created_at DESC,n.notification_id DESC LIMIT %s""",
                                (limit,))
                    rows = cur.fetchall()
                    cur.execute("""SELECT status,last_heartbeat_at,last_scan_at,last_error_type,
                                         notifications_created,decision_requests_created
                                  FROM notification_dispatcher_health
                                  WHERE service_id='notification.dispatcher.v1'""")
                    health = cur.fetchone()
                    cur.execute("SELECT clock_timestamp() AS observed_at")
                    observed_at = cur.fetchone()["observed_at"]
                    if health:
                        health = dict(health)
                        heartbeat = health.get("last_heartbeat_at")
                        age = ((observed_at - heartbeat).total_seconds() if heartbeat else None)
                        health["heartbeat_age_seconds"] = age
                        if health["status"] != "degraded":
                            health["status"] = ("unknown" if age is None else
                                                "unverified" if age < 0 else
                                                "stale" if age > _HEALTH_STALE_SECONDS else "healthy")
                    return {"schema_version": "rv.notifications.v1", "status": "available",
                            "observed_at": observed_at.isoformat(), "limit": limit,
                            "dispatcher": health or {"status": "not_initialized"},
                            "push_delivery": self.push_delivery_status(),
                            "items": [{**row, "notification_id": str(row["notification_id"]),
                                       "source_event_id": str(row["source_event_id"]),
                                       "decision_request_id": (str(row["request_id"])
                                           if row["request_id"] else None),
                                       "summary": _SUMMARY[row["event_type"]]}
                                      for row in rows]}
        except psycopg.Error as exc:
            raise NotificationUnavailable(type(exc).__name__) from None

    def push_delivery_status(self) -> dict:
        """Return a read-only, redacted provider-queue health projection.

        This is metadata for the authenticated notification API. It intentionally
        excludes delivery IDs, provider receipts, notice titles/messages, source
        event details, URLs, and credentials. A missing additive push migration
        does not make the underlying visual notification list unavailable.
        """
        base = {
            "schema_version": "rv.notification_push_status.v2",
            "component_id": "NOTIFICATION-DELIVERY",
            "status": "unavailable",
            "observed_at": None,
            "freshness": {"state": "unavailable", "heartbeat_age_seconds": None,
                          "threshold_seconds": _PUSH_HEALTH_STALE_SECONDS},
            "queue": {"state": "unavailable", "by_state": {}, "retry_due_count": None,
                      "expired_lease_count": None},
            "recovery": {"state": "unavailable", "retry_pending_count": None,
                         "expired_lease_count": None},
            "failure": {"state": "unavailable", "code": None},
            "last_cycle_at": None,
            "counters": None,
            "read_only": True,
            "content_included": False,
        }
        try:
            with self._connect() as db:
                with db.transaction(), db.cursor() as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SET LOCAL statement_timeout='2000ms'")
                    cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                        sql.Identifier(self.schema)))
                    cur.execute("""SELECT clock_timestamp() AS observed_at,
                        to_regclass(%s) AS queue_table,
                        to_regclass(%s) AS health_table""",
                        (f'"{self.schema}".notification_delivery_queue',
                         f'"{self.schema}".notification_delivery_health'))
                    relations = cur.fetchone()
                    observed = relations["observed_at"]
                    base["observed_at"] = observed.isoformat()
                    has_queue = relations["queue_table"] is not None
                    has_health = relations["health_table"] is not None
                    if not has_queue and not has_health:
                        base.update(status="not_initialized")
                        base["freshness"].update(state="unknown")
                        base["queue"].update(state="not_initialized", by_state={state: 0 for state in _PUSH_STATES},
                                              retry_due_count=0, expired_lease_count=0)
                        base["recovery"].update(state="unknown", retry_pending_count=0,
                                                expired_lease_count=0)
                        base["failure"].update(state="none")
                        return base
                    if not has_queue or not has_health:
                        base["status"] = "unavailable"
                        base["failure"] = {"state": "recorded",
                                            "code": "notification_push_schema_incomplete"}
                        return base

                    cur.execute("""SELECT state,count(*)::int AS count,
                        count(*) FILTER (WHERE state='retry' AND next_attempt_at<=%s)::int AS retry_due,
                        count(*) FILTER (WHERE state='sending' AND lease_until<=%s)::int AS expired_lease
                        FROM notification_delivery_queue GROUP BY state""", (observed, observed))
                    rows = cur.fetchall()
                    by_state = {state: 0 for state in _PUSH_STATES}
                    retry_due = expired_leases = retry_pending = 0
                    for row in rows:
                        state = row["state"]
                        if state not in by_state:
                            base["status"] = "unavailable"
                            base["failure"] = {"state": "recorded",
                                                "code": "notification_push_state_invalid"}
                            return base
                        by_state[state] = row["count"]
                        retry_pending += row["count"] if state == "retry" else 0
                        retry_due += row["retry_due"]
                        expired_leases += row["expired_lease"]

                    cur.execute("""SELECT status,last_heartbeat_at,last_cycle_at,last_error_code,
                        notices_scanned,deliveries_queued,provider_accepted,emergency_acknowledged
                        FROM notification_delivery_health WHERE service_id='notification.delivery.v1'""")
                    health = cur.fetchone()
                    base["queue"] = {"state": "available", "by_state": by_state,
                                      "retry_due_count": retry_due,
                                      "expired_lease_count": expired_leases}
                    base["recovery"].update(retry_pending_count=retry_pending,
                                            expired_lease_count=expired_leases)
                    if health is None:
                        base.update(status="not_initialized")
                        base["freshness"].update(state="unknown")
                        base["recovery"]["state"] = ("retry_pending" if retry_pending else
                                                        "lease_recovery_pending" if expired_leases else "unknown")
                        base["failure"].update(state="none")
                        return base

                    age = ((observed - health["last_heartbeat_at"]).total_seconds()
                           if health["last_heartbeat_at"] else None)
                    if age is None or age < 0:
                        status, freshness = "unknown", "unknown"
                    elif health["status"] == "degraded":
                        status, freshness = "degraded", "fresh"
                    elif age > _PUSH_HEALTH_STALE_SECONDS:
                        status, freshness = "stale", "stale"
                    else:
                        status, freshness = "healthy", "fresh"
                    base.update(status=status,
                                last_cycle_at=(health["last_cycle_at"].isoformat()
                                               if health["last_cycle_at"] else None),
                                counters={key: int(health[key]) for key in (
                                    "notices_scanned", "deliveries_queued", "provider_accepted",
                                    "emergency_acknowledged")})
                    base["freshness"].update(state=freshness, heartbeat_age_seconds=age)
                    error_code = health["last_error_code"]
                    safe_code = (error_code if isinstance(error_code, str)
                                 and _SAFE_ERROR_CODE.fullmatch(error_code) else
                                 "notification_error_code_redacted" if error_code else None)
                    base["failure"] = {"state": "recorded" if error_code else "none",
                                        "code": safe_code}
                    if expired_leases:
                        recovery = "lease_recovery_pending"
                    elif retry_pending:
                        recovery = "retry_pending"
                    elif status in {"stale", "degraded"}:
                        recovery = "worker_recovery_required"
                    elif status == "healthy":
                        recovery = "idle"
                    else:
                        recovery = "unknown"
                    base["recovery"]["state"] = recovery
                    return base
        except psycopg.Error:
            return base

    def _transition(self, notification_id: str, *, transition: str) -> dict:
        try:
            notification_uuid = UUID(notification_id)
        except (ValueError, TypeError, AttributeError):
            raise NotificationNotFound("notification_not_found") from None
        target_column = "delivered_at" if transition == "delivered" else "acknowledged_at"
        event_type = "delivery_confirmed" if transition == "delivered" else "receipt_acknowledged"
        actor_type = "authenticated_dashboard_client"
        key = f"{transition}:{notification_uuid}"
        try:
            with self._connect() as db:
                with db.transaction(), db.cursor() as cur:
                    cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                        sql.Identifier(self.schema)))
                    cur.execute("SET LOCAL statement_timeout='2000ms'")
                    cur.execute("SET LOCAL lock_timeout='1000ms'")
                    cur.execute("SELECT notification_id,delivered_at,acknowledged_at "
                                "FROM attention_notifications WHERE notification_id=%s FOR UPDATE",
                                (notification_uuid,))
                    row = cur.fetchone()
                    if not row:
                        raise NotificationNotFound("notification_not_found")
                    if transition == "acknowledged" and row["delivered_at"] is None:
                        raise NotificationConflict("delivery_receipt_required")
                    if row[target_column] is None:
                        cur.execute(sql.SQL("UPDATE attention_notifications SET {}=clock_timestamp() "
                                            "WHERE notification_id=%s RETURNING {} AS changed_at").format(
                            sql.Identifier(target_column), sql.Identifier(target_column)),
                                    (notification_uuid,))
                        changed = cur.fetchone()
                        cur.execute("""INSERT INTO notification_events
                            (notification_id,event_type,actor_type,idempotency_key)
                            VALUES (%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING""",
                                    (notification_uuid, event_type, actor_type, key))
                        timestamp = changed["changed_at"]
                        already = False
                    else:
                        timestamp = row[target_column]
                        already = True
                    cur.execute("SELECT status FROM steward_decision_requests "
                                "WHERE request_id=(SELECT decision_request_id FROM attention_notifications "
                                "WHERE notification_id=%s)", (notification_uuid,))
                    decision = cur.fetchone()
                    return {"schema_version": "rv.notification_receipt.v1",
                            "status": "acknowledged" if transition == "acknowledged" else "delivered",
                            "notification_id": str(notification_uuid),
                            "recorded_at": timestamp.isoformat() if timestamp else None,
                            "already_recorded": already,
                            "decision_request_status": decision["status"] if decision else None,
                            "authority_effect": "none"}
        except (NotificationNotFound, NotificationConflict):
            raise
        except psycopg.Error as exc:
            raise NotificationUnavailable(type(exc).__name__) from None

    def confirm_delivery(self, notification_id: str) -> dict:
        """Record that an authenticated browser successfully rendered a notice."""
        return self._transition(notification_id, transition="delivered")

    def acknowledge_receipt(self, notification_id: str) -> dict:
        """Record a client's receipt acknowledgment; this is not decision authority."""
        return self._transition(notification_id, transition="acknowledged")
