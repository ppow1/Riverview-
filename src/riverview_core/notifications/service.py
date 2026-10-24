# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/notifications/service.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.3
# Changed: 2026-10-24 UTC | RV-DELIVER-GRACE-BLOCKED-ESCALATION-20261024 | Return allowlisted objective escalation details with correlated dashboard notifications.
# Purpose: Read notices and persist visual delivery/receipt transitions
# Execution Model: Request-driven bounded PostgreSQL transactions
# Observability: Notification rows and append-only delivery/acknowledgment events
# Dependencies: PostgreSQL 16; Psycopg 3; migration 0006
# Authority: Dashboard-client receipt only; cannot resolve a decision request
# Changed: 2026-10-11 UTC | RV-M3.2-001 | Derive stale dispatcher health and bound receipt lock waits
# Contracts: docs/components/NOTIFICATION_DELIVERY.md
# Tests: tests/test_notifications.py; tests/test_status_dashboard.py
# History: New file; Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Bounded visual notification projections and idempotent client receipts."""

from __future__ import annotations

import re
from datetime import time as datetime_time
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_HEALTH_STALE_SECONDS = 15.0
_SUMMARY = {
    "assignment_stalled": "Assignment has no recent durable progress.",
    "deadline_missed": "An active assignment passed its configured deadline.",
    "assignment_attention": "An assignment requires attention.",
    "recovery_requested": "An expired execution lease requires recovery reconciliation.",
    "monitor_failed": "The CME monitor recorded a scan failure.",
    "attention_resolved": "A previously recorded attention condition was resolved.",
    "grace_objective_blocked": "Grace is blocked on a grounded objective and needs Steward review.",
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

    def get_settings(self) -> dict:
        """Read the one persistent notification policy shared by V2 and Grace."""
        try:
            with self._connect() as db, db.cursor() as cur:
                cur.execute(sql.SQL("SELECT level,quiet_hours_enabled,quiet_start,quiet_end,quiet_timezone,updated_at "
                                    "FROM {}.notification_settings WHERE settings_id=1").format(
                                        sql.Identifier(self.schema)))
                row = cur.fetchone()
                if row is None:
                    raise NotificationUnavailable("settings_not_initialized")
                return {"schema_version": "rv.notification_settings.v1", "status": "available",
                        "level": row["level"], "quiet_hours": {
                            "enabled": row["quiet_hours_enabled"],
                            "start": row["quiet_start"].strftime("%H:%M"),
                            "end": row["quiet_end"].strftime("%H:%M"),
                            "timezone": row["quiet_timezone"]},
                        "critical_policy": {"deliver_during_paused": True,
                                            "deliver_during_quiet_hours": True},
                        "updated_at": row["updated_at"].isoformat()}
        except NotificationUnavailable:
            raise
        except psycopg.Error as exc:
            raise NotificationUnavailable(type(exc).__name__) from None

    def update_settings(self, value: dict) -> dict:
        """Validate and persist a full replacement of the shared settings row."""
        from .policy import validate_settings
        try:
            value = validate_settings(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(str(exc)) from None
        quiet = value["quiet_hours"]
        try:
            with self._connect() as db, db.cursor() as cur:
                cur.execute(sql.SQL("UPDATE {}.notification_settings SET level=%s,quiet_hours_enabled=%s,"
                                    "quiet_start=%s,quiet_end=%s,quiet_timezone=%s,updated_at=clock_timestamp() "
                                    "WHERE settings_id=1 RETURNING updated_at").format(
                                        sql.Identifier(self.schema)),
                            (value["level"], quiet["enabled"], datetime_time.fromisoformat(quiet["start"]),
                             datetime_time.fromisoformat(quiet["end"]), quiet["timezone"]))
                if cur.fetchone() is None:
                    raise NotificationUnavailable("settings_not_initialized")
            return self.get_settings()
        except NotificationUnavailable:
            raise
        except psycopg.Error as exc:
            raise NotificationUnavailable(type(exc).__name__) from None

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
                                "items": [], "limit": limit}
                    cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                        sql.Identifier(self.schema)))
                    cur.execute("""SELECT n.notification_id,n.source_event_id,n.assignment_id,
                                         n.event_type,n.channel,n.source_recorded_at,n.created_at,
                                         n.delivered_at,n.acknowledged_at,d.request_id,
                                         d.status AS decision_status,d.assignment_version,
                                         e.details AS source_details,
                                         r.request_id AS recovery_request_id,
                                         r.status AS recovery_status,
                                         r.objective_id AS recovery_objective_id,
                                         r.objective_revision AS recovery_objective_revision,
                                         r.recovery_action,r.attempt_limit,r.expires_at AS recovery_expires_at,
                                         CASE WHEN n.acknowledged_at IS NOT NULL THEN 'acknowledged'
                                              WHEN n.delivered_at IS NOT NULL THEN 'delivered'
                                              ELSE 'queued' END AS delivery_status
                                  FROM attention_notifications n
                                  JOIN cme_monitor_events e ON e.event_id=n.source_event_id
                                  LEFT JOIN steward_decision_requests d
                                    ON d.request_id=n.decision_request_id
                                  LEFT JOIN grace_recovery_decision_requests r
                                    ON r.notification_id=n.notification_id
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
                            "items": [{**row, "notification_id": str(row["notification_id"]),
                                       "source_event_id": str(row["source_event_id"]),
                                       "source_details": (self._blocked_objective_details(
                                           row["source_details"]) if row["event_type"] ==
                                           "grace_objective_blocked" else None),
                                       "decision_request_id": (str(row["request_id"])
                                           if row["request_id"] else None),
                                       "recovery_request_id": (str(row["recovery_request_id"])
                                           if row["recovery_request_id"] else None),
                                       "recovery_expires_at": (row["recovery_expires_at"].isoformat()
                                           if row["recovery_expires_at"] else None),
                                       "summary": _SUMMARY[row["event_type"]]}
                                      for row in rows]}
        except psycopg.Error as exc:
            raise NotificationUnavailable(type(exc).__name__) from None

    @staticmethod
    def _blocked_objective_details(value):
        """Project only the known safe CME fields for a Grace block escalation."""
        keys = ("objective_id", "objective_revision", "runtime_revision", "failure_count",
                "last_error_code", "blocked_at", "last_failure_at", "decision",
                "recommended_action", "automatic_recovery")
        return {key: value.get(key) for key in keys} if isinstance(value, dict) else {}

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

    def decide_grace_recovery(self, request_id: str, *, decision: str,
                              actor_principal_id: str, authority_reference: str,
                              reason: str, idempotency_key: str) -> dict:
        """Record an exact, one-attempt Steward decision without running Grace."""
        from uuid import UUID
        try:
            request_uuid = UUID(request_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("invalid recovery request") from exc
        if decision not in {"approve", "defer", "reject"}:
            raise ValueError("invalid recovery decision")
        if not all(isinstance(v, str) and v.strip() for v in
                   (actor_principal_id, authority_reference, reason, idempotency_key)):
            raise ValueError("invalid decision evidence")
        if len(reason) > 1000 or len(idempotency_key) > 200:
            raise ValueError("decision evidence exceeds bounds")
        status = {"approve": "approved", "defer": "deferred", "reject": "rejected"}[decision]
        try:
            with self._connect() as db, db.transaction(), db.cursor() as cur:
                cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                    sql.Identifier(self.schema)))
                cur.execute("""SELECT r.*,e.event_type,e.details,
                    (r.expires_at<=clock_timestamp()) AS is_expired
                    FROM grace_recovery_decision_requests r
                    JOIN cme_monitor_events e ON e.event_id=r.source_event_id
                    WHERE r.request_id=%s FOR UPDATE OF r""", (request_uuid,))
                row = cur.fetchone()
                if row is None:
                    raise NotificationNotFound("recovery decision request not found")
                # Recheck the authoritative objective and exact fence before any approval.
                cur.execute("""SELECT o.revision,o.status,
                    EXISTS(SELECT 1 FROM grace_objective_events b
                      WHERE b.objective_id=o.objective_id
                        AND b.event_type='execution.reasoning_failed'
                        AND b.payload->>'status'='BLOCKED'
                        AND b.payload->>'objective_revision'=o.revision::text) AS still_blocked
                    FROM grace_objectives o WHERE o.objective_id=%s""",
                    (row["objective_id"],))
                objective = cur.fetchone()
                if (row["event_type"] != "grace_objective_blocked" or
                        not isinstance(row["details"], dict) or
                        row["details"].get("objective_id") != row["objective_id"] or
                        row["details"].get("objective_revision") != row["objective_revision"]):
                    raise NotificationConflict("escalation binding is invalid")
                if (objective is None or
                        objective["revision"] != row["objective_revision"] or
                        objective["status"] != "GROUNDED" or not objective["still_blocked"]):
                    raise NotificationConflict("objective revision or blocked state is stale")
                cur.execute("""SELECT decision_id,decision,request_id,actor_principal_id,
                    reason,authority_reference FROM grace_recovery_decision_events
                    WHERE idempotency_key=%s""", (idempotency_key,))
                prior = cur.fetchone()
                if prior:
                    if (prior["request_id"] != request_uuid or prior["decision"] != decision or
                            prior["actor_principal_id"] != actor_principal_id or
                            prior["reason"] != reason or
                            prior["authority_reference"] != authority_reference):
                        raise NotificationConflict("idempotency key was used for another decision")
                    return {"status": "recorded", "decision_id": str(prior["decision_id"]),
                            "request_id": str(request_uuid), "decision": decision,
                            "idempotent_replay": True, "authority_effect": "decision_only"}
                if row["status"] != "pending":
                    raise NotificationConflict("recovery request is already decided")
                if row["is_expired"]:
                    cur.execute("UPDATE grace_recovery_decision_requests SET status='expired',decided_at=clock_timestamp() WHERE request_id=%s",
                                (request_uuid,))
                    return {"status": "expired", "request_id": str(request_uuid),
                            "authority_effect": "none", "retry_dispatched": False}
                cur.execute("""INSERT INTO grace_recovery_decision_events
                    (request_id,source_event_id,objective_id,objective_revision,recovery_action,
                     decision,actor_principal_id,authority_reference,reason,idempotency_key)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING decision_id""",
                    (request_uuid,row["source_event_id"],row["objective_id"],
                     row["objective_revision"],row["recovery_action"],decision,
                     actor_principal_id,authority_reference,reason,idempotency_key))
                decision_id = cur.fetchone()["decision_id"]
                cur.execute("UPDATE grace_recovery_decision_requests SET status=%s,decided_at=clock_timestamp() WHERE request_id=%s",
                            (status, request_uuid))
                return {"status": "recorded", "decision_id": str(decision_id),
                        "request_id": str(request_uuid), "decision": decision,
                        "objective_id": row["objective_id"],
                        "objective_revision": row["objective_revision"],
                        "source_event_id": str(row["source_event_id"]),
                        "recovery_action": row["recovery_action"], "attempt_limit": row["attempt_limit"],
                        "authority_effect": "decision_only", "retry_dispatched": False}
        except (NotificationNotFound, NotificationConflict, ValueError):
            raise
        except psycopg.Error as exc:
            raise NotificationUnavailable("recovery decision unavailable") from exc
