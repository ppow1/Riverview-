# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/cme/monitor.py
# Component: CME
# Revision: 1.0.0
# Purpose: Observe durable assignment progress, deadlines, workers, and CME health
# Execution Model: Continuous scheduled PostgreSQL polling with durable re-scan
# Observability: Read-only status snapshot and durable CME attention event ledger
# Dependencies: Python 3.10+; Psycopg 3; M1.2, M1.4, M2.1-M2.3 schema
# Authority: Observe work; write only CME monitor tables; never schedule or execute
# Changed: 2026-10-10 UTC | RV-M2.4-001 | Initial concurrent monitor implementation
# Contracts: docs/components/CME_MONITOR.md; docs/ROADMAP.md
# Tests: tests/test_cme_monitor.py
# History: Git and revision/backup manifest
# =============================================================================
"""A restart-safe observer for assignment progress and execution health.

The monitor scans every nonterminal assignment in one bounded read and writes
only CME-owned health and attention records. A durable event key deduplicates
repeated scans and process restarts. It requests recovery by recording an event;
it does not claim leases, change assignment state, or invoke execution adapters.
"""

import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

LOG = logging.getLogger("riverview.cme.monitor")
_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_ACTIVE = ("queued", "ready", "running", "awaiting_verification",
           "rework_required", "blocked", "awaiting_steward")
_TERMINAL = ("completed", "cancelled")


class CMEError(RuntimeError):
    """Monitor configuration or durable monitoring contract failed."""


class MonitorAlreadyRunning(CMEError):
    """The configured CME service identity is already active."""


class CMEPostgresMonitor:
    """Observe all eligible assignments without controlling worker execution."""

    SERVICE_ID = "cme.monitor.v1"
    COMPONENT_VERSION = "1.0.0"

    def __init__(self, dsn, *, schema="public", stall_after_seconds,
                 worker_freshness_seconds=30, poll_interval=1.0,
                 max_backoff_seconds=30.0, service_id=None):
        if not schema or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid PostgreSQL schema")
        if not isinstance(stall_after_seconds, (int, float)) or stall_after_seconds <= 0:
            raise ValueError("stall_after_seconds must be positive")
        if not isinstance(worker_freshness_seconds, (int, float)) or worker_freshness_seconds <= 0:
            raise ValueError("worker_freshness_seconds must be positive")
        if poll_interval <= 0 or max_backoff_seconds < poll_interval:
            raise ValueError("invalid polling or backoff bounds")
        self.dsn = dsn
        self.schema = schema
        self.stall_after_seconds = float(stall_after_seconds)
        self.worker_freshness_seconds = float(worker_freshness_seconds)
        self.poll_interval = float(poll_interval)
        self.max_backoff_seconds = float(max_backoff_seconds)
        self.service_id = service_id or self.SERVICE_ID
        self.instance_id = str(uuid4())

    def _connect(self):
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def _set_schema(self, cur):
        cur.execute("SELECT set_config('search_path', %s, false)", (self.schema,))

    def _append_event(self, cur, *, event_key, event_type, assignment_id=None,
                      attention_key=None, details=None):
        cur.execute("""INSERT INTO cme_monitor_events
            (event_key,service_id,assignment_id,event_type,attention_key,details)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb)
            ON CONFLICT (event_key) DO NOTHING RETURNING event_id""",
            (event_key, self.service_id, assignment_id, event_type, attention_key,
             json.dumps(details or {}, sort_keys=True)))
        return cur.fetchone() is not None

    def set_deadline(self, assignment_id, deadline_at):
        """Set or replace a deadline in CME-owned metadata without changing ledger state."""
        if deadline_at is None or deadline_at.tzinfo is None or deadline_at.utcoffset() is None:
            raise ValueError("deadline_at must be a timezone-aware datetime")
        with self._connect() as db, db.transaction(), db.cursor() as cur:
            self._set_schema(cur)
            cur.execute("SELECT 1 FROM assignments WHERE id=%s", (assignment_id,))
            if cur.fetchone() is None:
                raise CMEError("unknown assignment")
            cur.execute("""INSERT INTO cme_assignment_deadlines(assignment_id,deadline_at)
                VALUES (%s,%s) ON CONFLICT(assignment_id) DO UPDATE SET
                  deadline_at=EXCLUDED.deadline_at,updated_at=clock_timestamp()""",
                (assignment_id, deadline_at))

    @staticmethod
    def _ts(value):
        return value.isoformat() if value is not None else None

    def _scan(self):
        now = datetime.now(timezone.utc)
        with self._connect() as db, db.transaction(), db.cursor() as cur:
            self._set_schema(cur)
            cur.execute("""SELECT a.id,a.state,a.workflow_id,a.workflow_step,
                    a.updated_at,d.deadline_at,d.updated_at AS deadline_updated_at,
                    a.version,a.correlation_id,
                    p.seq AS progress_seq,p.recorded_at AS last_progress_at,
                    l.worker_id,l.generation,l.heartbeat_at,l.expires_at
                FROM assignments AS a
                LEFT JOIN LATERAL (
                    SELECT seq,recorded_at FROM events
                    WHERE assignment_id=a.id ORDER BY seq DESC LIMIT 1
                ) AS p ON TRUE
                LEFT JOIN cme_assignment_deadlines AS d ON d.assignment_id=a.id
                LEFT JOIN assignment_leases AS l ON l.assignment_id=a.id
                WHERE a.state = ANY(%s) ORDER BY a.updated_at,a.id""",
                (list(_ACTIVE),))
            assignments = cur.fetchall()
            observed = []
            active_attention_keys = set()
            stalled_count = overdue_count = recovery_count = 0
            for item in assignments:
                assignment_id = item["id"]
                state = item["state"]
                progress_at = item["last_progress_at"] or item["updated_at"]
                progress_age = max(0.0, (now - progress_at).total_seconds())
                deadline = item["deadline_at"]
                conditions = []
                if deadline is not None and deadline <= now:
                    key = (f"deadline:{assignment_id}:{deadline.isoformat()}:"
                           f"{item['deadline_updated_at'].isoformat()}")
                    conditions.append(("deadline_missed", key, {
                        "deadline_at": self._ts(deadline), "state": state,
                        "deadline_updated_at": self._ts(item["deadline_updated_at"]),
                        "assignment_version": item["version"],
                        "last_progress_at": self._ts(progress_at)}))
                    overdue_count += 1
                if (state in {"queued", "ready", "running", "awaiting_verification",
                              "rework_required"} and
                        progress_age >= self.stall_after_seconds):
                    key = f"stall:{assignment_id}:{item['progress_seq']}"
                    conditions.append(("assignment_stalled", key, {
                        "state": state, "workflow_id": item["workflow_id"],
                        "workflow_step": item["workflow_step"],
                        "progress_seq": item["progress_seq"],
                        "last_progress_at": self._ts(progress_at),
                        "progress_age_seconds": progress_age,
                        "stall_threshold_seconds": self.stall_after_seconds,
                        "worker_id": item["worker_id"],
                        "lease_generation": item["generation"],
                        "lease_expires_at": self._ts(item["expires_at"])}))
                    active_attention_keys.add(key)
                    stalled_count += 1
                    if item["expires_at"] is not None and item["expires_at"] <= now:
                        recovery_key = f"recovery:{assignment_id}:{item['generation']}"
                        conditions.append(("recovery_requested", recovery_key, {
                            "reason": "stalled_assignment_lease_expired",
                            "worker_id": item["worker_id"],
                            "lease_generation": item["generation"],
                            "lease_expires_at": self._ts(item["expires_at"])}))
                if state in {"blocked", "awaiting_steward"}:
                    key = f"state-attention:{assignment_id}:{state}:{item['progress_seq']}"
                    conditions.append(("assignment_attention", key, {
                        "state": state, "workflow_id": item["workflow_id"],
                        "workflow_step": item["workflow_step"],
                        "progress_seq": item["progress_seq"]}))
                    active_attention_keys.add(key)

                for event_type, key, details in conditions:
                    if event_type != "recovery_requested":
                        active_attention_keys.add(key)
                    inserted = self._append_event(
                        cur, event_key=key, event_type=event_type,
                        assignment_id=assignment_id,
                        attention_key=(key if event_type != "recovery_requested" else None),
                        details=details)
                    if event_type == "recovery_requested" and inserted:
                        recovery_count += 1
                observed.append({
                    "assignment_id": assignment_id,
                    "state": state,
                    "workflow_id": item["workflow_id"],
                    "workflow_step": item["workflow_step"],
                    "correlation_id": item["correlation_id"],
                    "last_progress_at": self._ts(progress_at),
                    "progress_age_seconds": progress_age,
                    "deadline_at": self._ts(deadline),
                    "deadline_missed": deadline is not None and deadline <= now,
                    "worker_id": item["worker_id"],
                    "worker_health": self._lease_health(item, now),
                })

            # Close only conditions that this complete scan can prove resolved.
            cur.execute("""SELECT event_id,assignment_id,attention_key,event_type,details
                FROM cme_monitor_events AS e
                WHERE e.event_type IN ('assignment_stalled','assignment_attention','deadline_missed')
                  AND NOT EXISTS (SELECT 1 FROM cme_monitor_events AS r
                    WHERE r.event_type='attention_resolved'
                      AND r.attention_key=e.attention_key)
                ORDER BY e.recorded_at,e.event_id""")
            for alert in cur.fetchall():
                if alert["attention_key"] in active_attention_keys:
                    continue
                assignment_id = alert["assignment_id"]
                cur.execute("""SELECT a.state,d.deadline_at,d.updated_at AS deadline_updated_at,
                    a.version
                    FROM assignments a LEFT JOIN cme_assignment_deadlines d
                    ON d.assignment_id=a.id WHERE a.id=%s""", (assignment_id,))
                current = cur.fetchone()
                if current is None:
                    continue
                details = alert["details"]
                resolved = current["state"] in _TERMINAL
                if alert["event_type"] == "assignment_stalled":
                    cur.execute("SELECT seq FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1",
                                (assignment_id,))
                    last = cur.fetchone()
                    resolved = (current["state"] not in {"queued", "ready", "running",
                                                          "awaiting_verification", "rework_required"} or
                                (last and str(last["seq"]) != str(details.get("progress_seq"))))
                elif alert["event_type"] == "assignment_attention":
                    resolved = current["state"] not in {"blocked", "awaiting_steward"}
                elif alert["event_type"] == "deadline_missed":
                    resolved = (current["state"] in _TERMINAL or
                                current["deadline_at"] is None or current["deadline_at"] > now or
                                self._ts(current["deadline_at"]) != details.get("deadline_at") or
                                self._ts(current["deadline_updated_at"]) !=
                                details.get("deadline_updated_at"))
                if resolved:
                    self._append_event(
                        cur,
                        event_key=f"resolved:{alert['attention_key']}:{current['version']}",
                        event_type="attention_resolved", assignment_id=assignment_id,
                        attention_key=alert["attention_key"],
                        details={"reason": "condition_no_longer_observed",
                                 "state": current["state"],
                                 "assignment_version": current["version"]})

            workers = self._worker_snapshot(cur, now)
            cur.execute("""INSERT INTO cme_monitor_health
                (service_id,instance_id,status,last_heartbeat_at,last_scan_at,
                 last_error,assignments_observed,workers_registered,workers_enabled)
                VALUES (%s,%s,'healthy',clock_timestamp(),clock_timestamp(),NULL,%s,%s,%s)
                ON CONFLICT(service_id) DO UPDATE SET
                  instance_id=EXCLUDED.instance_id,status='healthy',
                  last_heartbeat_at=EXCLUDED.last_heartbeat_at,
                  last_scan_at=EXCLUDED.last_scan_at,last_error=NULL,
                  assignments_observed=EXCLUDED.assignments_observed,
                  workers_registered=EXCLUDED.workers_registered,
                  workers_enabled=EXCLUDED.workers_enabled""",
                (self.service_id, self.instance_id, len(assignments),
                 len(workers), sum(1 for worker in workers if worker["enabled"])))
        return {"status": "healthy", "assignments_observed": len(assignments),
                "workers_registered": len(workers),
                "workers_enabled": sum(1 for worker in workers if worker["enabled"]),
                "workers": workers, "stalled": stalled_count,
                "overdue": overdue_count, "recovery_requests": recovery_count,
                "assignments": observed, "scanned_at": now.isoformat()}

    def _worker_snapshot(self, cur, now):
        cur.execute("""SELECT w.worker_id,w.active,l.heartbeat_at,l.expires_at
            FROM worker_registry AS w
            LEFT JOIN LATERAL (
              SELECT heartbeat_at,expires_at FROM assignment_leases
              WHERE worker_id=w.worker_id ORDER BY heartbeat_at DESC LIMIT 1
            ) AS l ON TRUE ORDER BY w.worker_id""")
        workers = []
        for worker in cur.fetchall():
            enabled = bool(worker["active"])
            if not enabled:
                health = "unavailable"
            elif worker["heartbeat_at"] is None:
                health = "unknown"
            else:
                age = (now - worker["heartbeat_at"]).total_seconds()
                health = ("stale" if age > self.worker_freshness_seconds or
                          worker["expires_at"] <= now else "healthy")
            workers.append({"worker_id": worker["worker_id"], "enabled": enabled,
                            "health": health,
                            "last_heartbeat_at": self._ts(worker["heartbeat_at"]),
                            "lease_expires_at": self._ts(worker["expires_at"])})
        return workers

    def _lease_health(self, item, now):
        if not item["worker_id"]:
            return "unknown"
        if item["heartbeat_at"] is None:
            return "unknown"
        heartbeat_age = (now - item["heartbeat_at"]).total_seconds()
        if (item["expires_at"] is not None and item["expires_at"] <= now or
                heartbeat_age > self.worker_freshness_seconds):
            return "stale"
        return "healthy"

    def scan_once(self):
        """Scan all current assignments and durably emit deduplicated attention."""
        return self._scan()

    def status(self, *, freshness_seconds=30):
        """Return a truthful service/worker status projection; DB failure is unavailable."""
        try:
            with self._connect() as db, db.cursor() as cur:
                self._set_schema(cur)
                cur.execute("SELECT * FROM cme_monitor_health WHERE service_id=%s",
                            (self.service_id,))
                health = cur.fetchone()
                if health is None:
                    return {"component_id": "CME", "version": self.COMPONENT_VERSION,
                            "status": "not_initialized", "service_id": self.service_id,
                            "last_heartbeat_at": None, "assignments_observed": 0,
                            "workers_registered": 0, "workers_enabled": 0,
                            "open_attention_count": 0, "workers": []}
                cur.execute("""SELECT count(*) AS count FROM cme_monitor_events e
                    WHERE e.event_type IN ('assignment_stalled','assignment_attention','deadline_missed')
                      AND NOT EXISTS (SELECT 1 FROM cme_monitor_events r
                        WHERE r.event_type='attention_resolved'
                          AND r.attention_key=e.attention_key)""")
                open_count = cur.fetchone()["count"]
                now = datetime.now(timezone.utc)
                age = max(0.0, (now - health["last_heartbeat_at"]).total_seconds())
                service_status = health["status"]
                if age > freshness_seconds:
                    service_status = "stale"
                elif health["last_error"]:
                    service_status = "degraded"
                return {"component_id": "CME", "version": self.COMPONENT_VERSION,
                        "status": service_status, "service_id": self.service_id,
                        "instance_id": str(health["instance_id"]),
                        "last_heartbeat_at": health["last_heartbeat_at"].isoformat(),
                        "heartbeat_age_seconds": age,
                        "last_scan_at": health["last_scan_at"].isoformat(),
                        "last_error": health["last_error"],
                        "assignments_observed": health["assignments_observed"],
                        "workers_registered": health["workers_registered"],
                        "workers_enabled": health["workers_enabled"],
                        "workers": self._worker_snapshot(cur, now),
                        "open_attention_count": open_count}
        except psycopg.Error:
            return {"component_id": "CME", "version": self.COMPONENT_VERSION,
                    "status": "unavailable", "service_id": self.service_id}

    def _record_failure(self, exc, backoff):
        error = type(exc).__name__
        LOG.error(json.dumps({"event": "cme_monitor_scan_failed",
                              "service_id": self.service_id,
                              "instance_id": self.instance_id,
                              "failure_type": error,
                              "backoff_seconds": backoff}, sort_keys=True))
        try:
            with self._connect() as db, db.transaction(), db.cursor() as cur:
                self._set_schema(cur)
                self._append_event(cur, event_key=f"monitor-failed:{self.instance_id}:{uuid4()}",
                                   event_type="monitor_failed",
                                   details={"failure_type": error,
                                            "backoff_seconds": backoff})
                cur.execute("""INSERT INTO cme_monitor_health
                    (service_id,instance_id,status,last_heartbeat_at,last_scan_at,last_error,
                     assignments_observed,workers_registered,workers_enabled)
                    VALUES (%s,%s,'degraded',clock_timestamp(),NULL,%s,0,0,0)
                    ON CONFLICT(service_id) DO UPDATE SET instance_id=EXCLUDED.instance_id,
                    status='degraded',last_heartbeat_at=EXCLUDED.last_heartbeat_at,
                    last_error=EXCLUDED.last_error""", (self.service_id,self.instance_id,error))
        except psycopg.Error:
            pass

    def run_forever(self, stop_event=None):
        """Run scans continuously; reacquire the database lock after restart/failure."""
        stop_event = stop_event or threading.Event()
        backoff = self.poll_interval
        lock_key = f"riverview-cme-monitor:{self.schema}:{self.service_id}"
        while not stop_event.is_set():
            try:
                with self._connect() as lock_db, lock_db.cursor() as lock_cur:
                    lock_cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s,0)) AS acquired",
                                     (lock_key,))
                    if not lock_cur.fetchone()["acquired"]:
                        raise MonitorAlreadyRunning("another CME monitor holds the service lease")
                    with lock_db.transaction(), lock_db.cursor() as cur:
                        self._set_schema(cur)
                        self._append_event(cur,
                            event_key=f"monitor-started:{self.instance_id}",
                            event_type="monitor_started",
                            details={"component_version": self.COMPONENT_VERSION})
                    while not stop_event.is_set():
                        try:
                            self.scan_once()
                            backoff = self.poll_interval
                            stop_event.wait(self.poll_interval)
                        except Exception as exc:
                            self._record_failure(exc, backoff)
                            stop_event.wait(backoff)
                            backoff = min(self.max_backoff_seconds, backoff * 2)
            except MonitorAlreadyRunning:
                raise
            except Exception as exc:
                self._record_failure(exc, backoff)
                stop_event.wait(backoff)
                backoff = min(self.max_backoff_seconds, backoff * 2)
