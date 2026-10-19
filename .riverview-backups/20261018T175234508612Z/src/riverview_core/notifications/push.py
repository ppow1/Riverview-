# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/notifications/push.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.0
# Purpose: Route durable institutional notices through ntfy and Pushover
# Execution Model: Request-driven enqueue/reconcile and bounded delivery worker
# Observability: PostgreSQL delivery queue, append-only events, worker result projection
# Dependencies: PostgreSQL notification migrations 0006/0007; Python urllib
# Authority: Sends fixed-summary attention notices only; never changes work or decisions
# Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial Camrui push adapter
# Contracts: docs/components/NOTIFICATION_IPHONE_DELIVERY.md
# Tests: tests/test_notification_push.py
# History: Git + .riverview-backups/manifest.jsonl
# =============================================================================
"""Durable ntfy/Pushover delivery layered on Riverview's notification ledger.

Provider HTTP acceptance is recorded as ``accepted``. It is not evidence that
an iPhone displayed the notice. Only Pushover emergency receipts can provide
the provider's explicit user-acknowledgment state.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_PROVIDERS = {"ntfy", "pushover"}
_SEVERITIES = {"info", "warning", "critical"}
_EVENT_SEVERITY = {
    "attention_resolved": "info",
    "assignment_stalled": "warning",
    "deadline_missed": "critical",
    "assignment_attention": "warning",
    "recovery_requested": "critical",
    "monitor_failed": "critical",
}
_EVENT_SUMMARY = {
    "assignment_stalled": "Assignment has no recent durable progress.",
    "deadline_missed": "An active assignment passed its configured deadline.",
    "assignment_attention": "An assignment requires attention.",
    "recovery_requested": "An expired execution lease requires recovery reconciliation.",
    "monitor_failed": "The CME monitor recorded a scan failure.",
    "attention_resolved": "A previously recorded attention condition was resolved.",
}


class PushConfigurationError(ValueError):
    """Provider routing or protected credential configuration is invalid."""


class PushProviderError(RuntimeError):
    """A provider rejected or could not accept a notification."""


class PushTransport(Protocol):
    def send(self, provider: str, severity: str, title: str, message: str,
             idempotency_key: str) -> dict[str, Any]: ...
    def receipt(self, receipt_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class PushConfig:
    routes: dict[str, tuple[str, ...]]
    event_severity: dict[str, str]
    ntfy_base_url: str | None = None
    ntfy_topic: str | None = None
    ntfy_credential: str = "ntfy_token"
    pushover_app_credential: str = "pushover_app_token"
    pushover_user_credential: str = "pushover_user_key"
    retry_limit: int = 5
    lease_seconds: int = 60
    retry_base_seconds: int = 5
    retry_max_seconds: int = 300
    emergency_retry_seconds: int = 60
    emergency_expire_seconds: int = 1800

    @classmethod
    def load(cls, path: str | Path) -> "PushConfig":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PushConfigurationError(f"config_unavailable:{type(exc).__name__}") from None
        if not isinstance(raw, dict):
            raise PushConfigurationError("config_must_be_object")
        routes_raw = raw.get("routes", {})
        if not isinstance(routes_raw, dict):
            raise PushConfigurationError("routes_must_be_object")
        routes: dict[str, tuple[str, ...]] = {}
        for severity, providers in routes_raw.items():
            if severity not in _SEVERITIES or not isinstance(providers, list):
                raise PushConfigurationError("invalid_severity_route")
            if any(provider not in _PROVIDERS for provider in providers):
                raise PushConfigurationError("unsupported_provider")
            routes[severity] = tuple(dict.fromkeys(providers))
        severity_raw = raw.get("event_severity", _EVENT_SEVERITY)
        if not isinstance(severity_raw, dict) or any(
                event not in _EVENT_SEVERITY or severity not in _SEVERITIES
                for event, severity in severity_raw.items()):
            raise PushConfigurationError("invalid_event_severity")
        ntfy_raw = raw.get("ntfy", {})
        pushover_raw = raw.get("pushover", {})
        if not isinstance(ntfy_raw, dict) or not isinstance(pushover_raw, dict):
            raise PushConfigurationError("provider_config_must_be_object")
        config = cls(
            routes=routes,
            event_severity={**_EVENT_SEVERITY, **severity_raw},
            ntfy_base_url=ntfy_raw.get("base_url"),
            ntfy_topic=ntfy_raw.get("topic"),
            ntfy_credential=ntfy_raw.get("credential", "ntfy_token"),
            pushover_app_credential=pushover_raw.get("app_credential", "pushover_app_token"),
            pushover_user_credential=pushover_raw.get("user_credential", "pushover_user_key"),
            retry_limit=int(raw.get("retry_limit", 5)),
            lease_seconds=int(raw.get("lease_seconds", 60)),
            retry_base_seconds=int(raw.get("retry_base_seconds", 5)),
            retry_max_seconds=int(raw.get("retry_max_seconds", 300)),
            emergency_retry_seconds=int(raw.get("emergency_retry_seconds", 60)),
            emergency_expire_seconds=int(raw.get("emergency_expire_seconds", 1800)),
        )
        if not 1 <= config.retry_limit <= 10:
            raise PushConfigurationError("retry_limit_out_of_range")
        if not 5 <= config.lease_seconds <= 600:
            raise PushConfigurationError("lease_seconds_out_of_range")
        if not 1 <= config.retry_base_seconds <= config.retry_max_seconds <= 3600:
            raise PushConfigurationError("invalid_retry_bounds")
        if config.emergency_retry_seconds < 30 or not (
                config.emergency_retry_seconds <= config.emergency_expire_seconds <= 10800):
            raise PushConfigurationError("invalid_emergency_retry_window")
        if any("ntfy" in providers for providers in routes.values()):
            if not config.ntfy_base_url or not config.ntfy_topic:
                raise PushConfigurationError("ntfy_route_missing_endpoint_or_topic")
            parsed_url = urlsplit(config.ntfy_base_url)
            if not parsed_url.hostname or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment:
                raise PushConfigurationError("invalid_ntfy_base_url")
            hostname = parsed_url.hostname.lower().rstrip(".")
            local_http = parsed_url.scheme == "http" and hostname == "127.0.0.1"
            if parsed_url.scheme != "https" and not local_http:
                raise PushConfigurationError("ntfy_must_use_https_or_loopback")
            if hostname == "ntfy.sh" or hostname.endswith(".ntfy.sh"):
                raise PushConfigurationError("public_ntfy_service_not_allowed")
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", config.ntfy_topic):
                raise PushConfigurationError("invalid_ntfy_topic")
        return config


def _credential(name: str, *, credentials_dir: str | None = None) -> str:
    """Read one systemd LoadCredential value without logging its contents."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name):
        raise PushConfigurationError("invalid_credential_name")
    root_value = credentials_dir or os.environ.get("CREDENTIALS_DIRECTORY")
    if not root_value:
        raise PushConfigurationError("credentials_directory_missing")
    root = Path(root_value)
    path = root / name
    try:
        if path.is_symlink() or not path.is_file():
            raise PushConfigurationError("credential_missing")
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise PushConfigurationError(f"credential_unavailable:{type(exc).__name__}") from None
    if not value:
        raise PushConfigurationError("credential_empty")
    return value


class HttpPushTransport:
    """Minimal HTTPS clients for self-hosted ntfy and Pushover."""

    def __init__(self, config: PushConfig, *, credentials_dir: str | None = None,
                 timeout_seconds: float = 8.0, opener=urlopen):
        self.config = config
        self.credentials_dir = credentials_dir
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def _request(self, request: Request) -> tuple[int, bytes]:
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                return response.status, response.read(65536)
        except HTTPError as exc:
            return exc.code, exc.read(65536)
        except (URLError, TimeoutError, OSError) as exc:
            raise PushProviderError(f"transport_{type(exc).__name__}") from None

    def send(self, provider: str, severity: str, title: str, message: str,
             idempotency_key: str) -> dict[str, Any]:
        if provider == "ntfy":
            base = self.config.ntfy_base_url.rstrip("/")
            url = f"{base}/{self.config.ntfy_topic}"
            headers = {
                "Content-Type": "text/plain; charset=utf-8",
                "Title": title,
                "Priority": {"info": "3", "warning": "4", "critical": "5"}[severity],
                "Tags": f"riverview,{severity}",
            }
            token = _credential(self.config.ntfy_credential, credentials_dir=self.credentials_dir)
            headers["Authorization"] = f"Bearer {token}"
            request = Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
        elif provider == "pushover":
            app_token = _credential(self.config.pushover_app_credential,
                                    credentials_dir=self.credentials_dir)
            user_key = _credential(self.config.pushover_user_credential,
                                   credentials_dir=self.credentials_dir)
            priority = {"info": 0, "warning": 1, "critical": 2}[severity]
            fields: dict[str, str | int] = {
                "token": app_token, "user": user_key, "title": title, "message": message,
                "priority": priority,
            }
            if priority == 2:
                fields["retry"] = self.config.emergency_retry_seconds
                fields["expire"] = self.config.emergency_expire_seconds
            request = Request("https://api.pushover.net/1/messages.json",
                              data=urlencode(fields).encode("ascii"),
                              headers={"Content-Type": "application/x-www-form-urlencoded"},
                              method="POST")
        else:
            raise PushProviderError("unsupported_provider")
        status, body = self._request(request)
        if not 200 <= status < 300:
            raise PushProviderError(f"provider_http_{status}")
        if provider == "pushover":
            try:
                payload = json.loads(body or b"{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise PushProviderError("provider_invalid_response") from None
            if payload.get("status") != 1:
                raise PushProviderError("provider_rejected")
            return {"accepted": True, "receipt_id": payload.get("receipt")}
        return {"accepted": True, "receipt_id": None}

    def receipt(self, receipt_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9]{30}", receipt_id):
            raise PushProviderError("invalid_receipt")
        token = _credential(self.config.pushover_app_credential,
                            credentials_dir=self.credentials_dir)
        url = f"https://api.pushover.net/1/receipts/{receipt_id}.json?{urlencode({'token': token})}"
        status, body = self._request(Request(url, method="GET"))
        if not 200 <= status < 300:
            raise PushProviderError(f"provider_http_{status}")
        try:
            payload = json.loads(body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise PushProviderError("provider_invalid_receipt_response") from None
        if payload.get("status") != 1:
            raise PushProviderError("provider_receipt_rejected")
        return {"acknowledged": payload.get("acknowledged") == 1,
                "expired": payload.get("expired") == 1}


class NotificationDeliveryManager:
    """CME notice outbox with deduplication, bounded retry, leases and audit events."""

    def __init__(self, dsn: str, config: PushConfig, *, schema: str = "public",
                 transport: PushTransport | None = None, credentials_dir: str | None = None,
                 clock=None):
        if not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid PostgreSQL schema")
        self.dsn, self.schema, self.config = dsn, schema, config
        self.transport = transport or HttpPushTransport(config, credentials_dir=credentials_dir)
        self.instance_id = uuid4()

    def _connect(self):
        return psycopg.connect(self.dsn, connect_timeout=3, row_factory=dict_row,
                               application_name="riverview-notification-delivery")

    def reconcile(self) -> dict[str, int]:
        """Queue configured providers for eligible, privacy-filtered CME notices."""
        if not any(self.config.routes.values()):
            return {"notices_scanned": 0, "deliveries_queued": 0}
        created = 0
        observed = 0
        with self._connect() as db:
            with db.transaction(), db.cursor() as cur:
                cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                    sql.Identifier(self.schema)))
                cur.execute("""SELECT n.notification_id,n.event_type
                    FROM attention_notifications n
                    CROSS JOIN notification_delivery_settings s
                    WHERE (n.assignment_id IS NULL OR NOT EXISTS (
                        SELECT 1 FROM events p WHERE p.assignment_id=n.assignment_id
                          AND p.privacy_domain <> 'institution'))
                      AND n.created_at>=s.enabled_since
                      AND NOT EXISTS (SELECT 1 FROM notification_delivery_queue q
                                      WHERE q.notification_id=n.notification_id)
                    ORDER BY n.created_at,n.notification_id
                    LIMIT 500""")
                rows = cur.fetchall()
                observed = len(rows)
                for row in rows:
                    severity = self.config.event_severity[row["event_type"]]
                    for provider in self.config.routes.get(severity, ()):
                        cur.execute("""INSERT INTO notification_delivery_queue
                            (notification_id,provider,severity,title,message,idempotency_key,max_attempts)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT(notification_id,provider) DO NOTHING
                            RETURNING delivery_id""",
                            (row["notification_id"], provider, severity,
                             "Riverview attention", _EVENT_SUMMARY[row["event_type"]],
                             f"{row['notification_id']}:{provider}", self.config.retry_limit))
                        inserted = cur.fetchone()
                        if inserted:
                            created += 1
                            self._event(cur, inserted["delivery_id"], "delivery_queued",
                                        f"queued:{row['notification_id']}:{provider}")
        return {"notices_scanned": observed, "deliveries_queued": created}

    @staticmethod
    def _event(cur, delivery_id: UUID, event_type: str, key: str, details: dict | None = None):
        cur.execute("""INSERT INTO notification_delivery_events
            (delivery_id,event_type,actor_type,idempotency_key,details)
            VALUES (%s,%s,'notification_delivery_worker',%s,%s::jsonb)
            ON CONFLICT(idempotency_key) DO NOTHING""",
            (delivery_id, event_type, key, json.dumps(details or {}, sort_keys=True)))

    def _claim(self) -> dict[str, Any] | None:
        lease_id = uuid4()
        with self._connect() as db:
            with db.transaction(), db.cursor() as cur:
                cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                    sql.Identifier(self.schema)))
                cur.execute("""WITH exhausted AS (
                    UPDATE notification_delivery_queue SET state='failed',lease_id=NULL,
                      lease_until=NULL,last_error_code='lease_expired_at_retry_limit',
                      updated_at=clock_timestamp()
                    WHERE state='sending' AND lease_until<clock_timestamp()
                      AND attempt_count>=max_attempts
                    RETURNING delivery_id,attempt_count
                ) SELECT delivery_id,attempt_count FROM exhausted""")
                for expired in cur.fetchall():
                    self._event(cur, expired["delivery_id"], "delivery_failed",
                                f"lease-exhausted:{expired['delivery_id']}:{expired['attempt_count']}",
                                {"error_code": "lease_expired_at_retry_limit"})
                cur.execute("""WITH candidate AS (
                    SELECT delivery_id FROM notification_delivery_queue
                    WHERE (state IN ('queued','retry') AND next_attempt_at<=clock_timestamp())
                       OR (state='sending' AND lease_until<clock_timestamp()
                           AND attempt_count<max_attempts)
                    ORDER BY next_attempt_at,created_at,delivery_id
                    FOR UPDATE SKIP LOCKED LIMIT 1
                ) UPDATE notification_delivery_queue q SET state='sending',
                    attempt_count=q.attempt_count+1,lease_id=%s,
                    lease_until=clock_timestamp()+(%s * interval '1 second'),updated_at=clock_timestamp()
                    FROM candidate c WHERE q.delivery_id=c.delivery_id
                    RETURNING q.*""", (lease_id, self.config.lease_seconds))
                row = cur.fetchone()
                if row:
                    self._event(cur, row["delivery_id"], "delivery_claimed",
                                f"claimed:{row['delivery_id']}:{row['attempt_count']}:{lease_id}",
                                {"attempt": row["attempt_count"]})
                return row

    def _finish(self, row: dict[str, Any], *, accepted: dict[str, Any] | None = None,
                error_code: str | None = None) -> None:
        delivery_id, lease_id = row["delivery_id"], row["lease_id"]
        with self._connect() as db:
            with db.transaction(), db.cursor() as cur:
                cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                    sql.Identifier(self.schema)))
                if accepted is not None:
                    receipt = accepted.get("receipt_id")
                    cur.execute("""UPDATE notification_delivery_queue SET state='accepted',
                        provider_accepted_at=clock_timestamp(),provider_receipt=%s,
                        next_receipt_check_at=CASE WHEN %s THEN clock_timestamp()+interval '15 seconds' END,
                        lease_id=NULL,lease_until=NULL,last_error_code=NULL,updated_at=clock_timestamp()
                        WHERE delivery_id=%s AND state='sending' AND lease_id=%s""",
                        (receipt, bool(receipt), delivery_id, lease_id))
                    if cur.rowcount != 1:
                        return
                    self._event(cur, delivery_id, "provider_accepted",
                                f"accepted:{delivery_id}:{row['attempt_count']}",
                                {"provider": row["provider"], "receipt_present": bool(receipt)})
                elif row["attempt_count"] >= row["max_attempts"]:
                    cur.execute("""UPDATE notification_delivery_queue SET state='failed',
                        lease_id=NULL,lease_until=NULL,last_error_code=%s,updated_at=clock_timestamp()
                        WHERE delivery_id=%s AND state='sending' AND lease_id=%s""",
                        (error_code or "provider_failure", delivery_id, lease_id))
                    if cur.rowcount != 1:
                        return
                    self._event(cur, delivery_id, "delivery_failed",
                                f"failed:{delivery_id}:{row['attempt_count']}",
                                {"error_code": error_code or "provider_failure"})
                else:
                    delay = min(self.config.retry_max_seconds,
                                self.config.retry_base_seconds * (2 ** (row["attempt_count"] - 1)))
                    cur.execute("""UPDATE notification_delivery_queue SET state='retry',
                        next_attempt_at=clock_timestamp()+(%s * interval '1 second'),
                        lease_id=NULL,lease_until=NULL,last_error_code=%s,updated_at=clock_timestamp()
                        WHERE delivery_id=%s AND state='sending' AND lease_id=%s""",
                        (delay, error_code or "provider_failure", delivery_id, lease_id))
                    if cur.rowcount != 1:
                        return
                    self._event(cur, delivery_id, "retry_scheduled",
                                f"retry:{delivery_id}:{row['attempt_count']}",
                                {"error_code": error_code or "provider_failure", "delay_seconds": delay})

    def deliver_one(self) -> dict[str, Any]:
        row = self._claim()
        if not row:
            return {"status": "idle"}
        try:
            result = self.transport.send(row["provider"], row["severity"], row["title"],
                                         row["message"], row["idempotency_key"])
            if not result.get("accepted"):
                raise PushProviderError("provider_rejected")
            receipt = result.get("receipt_id")
            if row["provider"] == "pushover" and row["severity"] == "critical":
                if not isinstance(receipt, str) or not re.fullmatch(r"[A-Za-z0-9]{30}", receipt):
                    raise PushProviderError("emergency_receipt_missing_or_invalid")
            elif receipt is not None and (not isinstance(receipt, str) or len(receipt) > 128):
                raise PushProviderError("provider_reference_invalid")
            self._finish(row, accepted=result)
            return {"status": "provider_accepted", "delivery_id": str(row["delivery_id"]),
                    "provider": row["provider"], "handset_delivery": "unverified"}
        except (PushProviderError, PushConfigurationError) as exc:
            code = "configuration_error" if isinstance(exc, PushConfigurationError) else "provider_error"
            self._finish(row, error_code=code)
            return {"status": "retry_or_failed", "delivery_id": str(row["delivery_id"]),
                    "provider": row["provider"], "error_code": code}

    def poll_emergency_acknowledgments(self, *, batch_size: int = 20) -> dict[str, int]:
        """Poll Pushover receipts conservatively; ntfy has no server-side ack contract."""
        claimed: list[dict[str, Any]] = []
        with self._connect() as db:
            with db.transaction(), db.cursor() as cur:
                cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                    sql.Identifier(self.schema)))
                cur.execute("""SELECT delivery_id,provider_receipt FROM notification_delivery_queue
                    WHERE provider='pushover' AND severity='critical' AND state='accepted'
                      AND provider_receipt IS NOT NULL AND acknowledged_at IS NULL
                      AND (next_receipt_check_at IS NULL OR next_receipt_check_at<=clock_timestamp())
                    ORDER BY next_receipt_check_at NULLS FIRST FOR UPDATE SKIP LOCKED LIMIT %s""",
                    (max(1, min(50, batch_size)),))
                claimed = cur.fetchall()
                for row in claimed:
                    cur.execute("UPDATE notification_delivery_queue SET next_receipt_check_at=clock_timestamp()+interval '15 seconds' WHERE delivery_id=%s",
                                (row["delivery_id"],))
        acknowledged = 0
        failed = 0
        for row in claimed:
            try:
                result = self.transport.receipt(row["provider_receipt"])
            except (PushProviderError, PushConfigurationError):
                failed += 1
                continue
            if result.get("acknowledged"):
                with self._connect() as db:
                    with db.transaction(), db.cursor() as cur:
                        cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                            sql.Identifier(self.schema)))
                        cur.execute("""UPDATE notification_delivery_queue SET state='acknowledged',
                            acknowledged_at=clock_timestamp(),
                            next_receipt_check_at=NULL,updated_at=clock_timestamp()
                            WHERE delivery_id=%s AND acknowledged_at IS NULL""", (row["delivery_id"],))
                        self._event(cur, row["delivery_id"], "emergency_acknowledged",
                                    f"acknowledged:{row['delivery_id']}")
                        acknowledged += 1
            elif result.get("expired"):
                with self._connect() as db:
                    with db.transaction(), db.cursor() as cur:
                        cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                            sql.Identifier(self.schema)))
                        cur.execute("UPDATE notification_delivery_queue SET state='expired',next_receipt_check_at=NULL,updated_at=clock_timestamp() WHERE delivery_id=%s AND acknowledged_at IS NULL",
                                    (row["delivery_id"],))
                        self._event(cur, row["delivery_id"], "emergency_expired",
                                    f"expired:{row['delivery_id']}")
        return {"polled": len(claimed), "acknowledged": acknowledged, "poll_failures": failed}

    def run_once(self) -> dict[str, Any]:
        queued = self.reconcile()
        delivered = 0
        for _ in range(100):
            result = self.deliver_one()
            if result["status"] == "idle":
                break
            delivered += int(result["status"] == "provider_accepted")
        receipts = self.poll_emergency_acknowledgments()
        result = {**queued, "provider_accepted": delivered, "receipt_poll": receipts}
        self.record_health(status="healthy", result=result)
        return result

    def record_health(self, *, status: str, error_code: str | None = None,
                      result: dict[str, Any] | None = None) -> None:
        """Persist a sanitized heartbeat and counters for the operational projection."""
        if status not in {"healthy", "degraded"}:
            raise ValueError("invalid health status")
        result = result or {}
        with self._connect() as db:
            with db.transaction(), db.cursor() as cur:
                cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                    sql.Identifier(self.schema)))
                cur.execute("""INSERT INTO notification_delivery_health
                    (service_id,instance_id,status,last_heartbeat_at,last_cycle_at,last_error_code,
                     notices_scanned,deliveries_queued,provider_accepted,emergency_acknowledged)
                    VALUES ('notification.delivery.v1',%s,%s,clock_timestamp(),
                      CASE WHEN %s THEN clock_timestamp() END,%s,%s,%s,%s,%s)
                    ON CONFLICT(service_id) DO UPDATE SET instance_id=excluded.instance_id,
                      status=excluded.status,last_heartbeat_at=excluded.last_heartbeat_at,
                      last_cycle_at=COALESCE(excluded.last_cycle_at,notification_delivery_health.last_cycle_at),
                      last_error_code=excluded.last_error_code,
                      notices_scanned=notification_delivery_health.notices_scanned+excluded.notices_scanned,
                      deliveries_queued=notification_delivery_health.deliveries_queued+excluded.deliveries_queued,
                      provider_accepted=notification_delivery_health.provider_accepted+excluded.provider_accepted,
                      emergency_acknowledged=notification_delivery_health.emergency_acknowledged+excluded.emergency_acknowledged""",
                    (self.instance_id, status, status == "healthy", error_code,
                     int(result.get("notices_scanned", 0)), int(result.get("deliveries_queued", 0)),
                     int(result.get("provider_accepted", 0)),
                     int(result.get("receipt_poll", {}).get("acknowledged", 0))))

    def status(self) -> dict[str, Any]:
        """Read a bounded health/count projection; no notice content is returned."""
        with self._connect() as db:
            with db.transaction(), db.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute(sql.SQL("SET LOCAL search_path TO {},pg_catalog").format(
                    sql.Identifier(self.schema)))
                cur.execute("""SELECT state,count(*)::int AS count FROM notification_delivery_queue
                    GROUP BY state ORDER BY state""")
                states = {row["state"]: row["count"] for row in cur.fetchall()}
                cur.execute("""SELECT status,last_heartbeat_at,last_cycle_at,last_error_code,
                    notices_scanned,deliveries_queued,provider_accepted,emergency_acknowledged
                    FROM notification_delivery_health WHERE service_id='notification.delivery.v1'""")
                health = cur.fetchone()
                if health:
                    health = dict(health)
                    for key in ("last_heartbeat_at", "last_cycle_at"):
                        if health.get(key):
                            health[key] = health[key].isoformat()
                return {"schema_version": "rv.notification_push_status.v1",
                        "status": "not_initialized" if health is None else health["status"],
                        "health": health, "queue": states}
