# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/projection.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.2
# Purpose: Project authoritative PostgreSQL/CME state into bounded safe views
# Execution Model: Request-driven read-only API dependency
# Observability: Versioned status, assignment, event, attention and snapshot JSON
# Dependencies: Python 3.10+; Psycopg 3; M1.2/M1.4/M2.1-M2.4 schema
# Authority: SELECT-only projection; never mutates CME or assignment state
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Add bounded objective/work-order projections
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_status_dashboard.py
# History: Git and revision/backup manifest
# =============================================================================
"""Bounded, privacy-filtered read models over the existing PostgreSQL ledger."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_SAFE_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")
_MAX_PAGE = 100
_MAX_SNAPSHOT_ASSIGNMENTS = 50
_MAX_SNAPSHOT_EVENTS = 25


class ProjectionUnavailable(RuntimeError):
    """The configured projection source could not be read."""


class DashboardProjection:
    """Perform isolated read-only, bounded queries on each API request."""

    COMPONENT_VERSION = "1.0.0"
    CME_SERVICE_ID = "cme.monitor.v1"

    def __init__(self, dsn: str, *, schema: str = "public", source_commit: str = "unknown",
                 deployment_id: str = "unconfigured", heartbeat_stale_seconds: int = 30,
                 connect_timeout: int = 2):
        if not isinstance(schema, str) or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid PostgreSQL schema")
        if not isinstance(heartbeat_stale_seconds, int) or heartbeat_stale_seconds < 1:
            raise ValueError("heartbeat_stale_seconds must be a positive integer")
        self.dsn = dsn
        self.schema = schema
        self.source_commit = source_commit if re.fullmatch(r"[0-9a-f]{40,64}", source_commit) else "unknown"
        self.deployment_id = deployment_id if _SAFE_CODE.fullmatch(deployment_id) else "unconfigured"
        self.heartbeat_stale_seconds = heartbeat_stale_seconds
        self.connect_timeout = connect_timeout

    def _read(self, operation):
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row,
                                 connect_timeout=self.connect_timeout) as db:
                with db.transaction(), db.cursor() as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SET LOCAL statement_timeout = '2000ms'")
                    cur.execute(sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(
                        sql.Identifier(self.schema)))
                    return operation(cur)
        except psycopg.Error as exc:
            raise ProjectionUnavailable(type(exc).__name__) from None

    @staticmethod
    def _iso(value):
        return value.isoformat() if isinstance(value, datetime) else None

    @staticmethod
    def _relations(cur, names):
        cur.execute("SELECT name, to_regclass(name) IS NOT NULL AS present "
                    "FROM unnest(%s::text[]) AS name", (list(names),))
        return {row["name"]: row["present"] for row in cur.fetchall()}

    def status(self) -> dict[str, Any]:
        def query(cur):
            cur.execute("SELECT current_database() AS database, clock_timestamp() AS observed_at")
            db = cur.fetchone()
            names = ("schema_migrations", "assignments", "events", "assignment_leases",
                     "worker_registry", "worker_attempts", "verification_records",
                     "cme_monitor_health", "cme_monitor_events", "grace_execution_health")
            rel = self._relations(cur, [f"{self.schema}.{name}" for name in names])
            present = {name: rel[f"{self.schema}.{name}"] for name in names}
            base_ready = present["assignments"] and present["events"] and present["schema_migrations"]
            result = {
                "schema_version": "rv.dashboard.status.v1",
                "component_id": "STEWARD-DASHBOARD",
                "component_version": self.COMPONENT_VERSION,
                "observed_at": self._iso(db["observed_at"]),
                "source": {"kind": "postgresql", "database": db["database"],
                           "schema": self.schema, "source_commit": self.source_commit,
                           "deployment_id": self.deployment_id},
                "projection_status": "healthy" if base_ready else "not_initialized",
                "freshness": "current" if base_ready else "unknown",
                "event_cursor": None,
                "assignment_counts": {},
                "assignments_total": 0,
                "cme": {"status": "not_initialized", "source": "cme_monitor_health"},
                "grace_execution": {"status": "not_initialized", "source": "grace_execution_health"},
                "workers": {"status": "not_initialized", "source": "assignment_leases"},
                "verification": {"status": "not_initialized" if not present["verification_records"] else "available"},
                "relations": {name: bool(value) for name, value in present.items()},
                "diagnostics": {
                    "component": "docs/components/STATUS_DASHBOARD_COOKBOOK.md",
                    "workflow": "rv:steward-dashboard:status:request",
                    "graph": "process_graphs/steward-dashboard/status.json",
                },
            }
            if not base_ready:
                return result
            cur.execute("SELECT version, applied_at FROM schema_migrations ORDER BY applied_at DESC, version DESC LIMIT 1")
            migration = cur.fetchone()
            result["source"]["latest_migration"] = migration["version"] if migration else None
            cur.execute("SELECT state, count(*) AS count FROM assignments a "
                        "WHERE NOT EXISTS (SELECT 1 FROM events p WHERE p.assignment_id=a.id "
                        "AND p.privacy_domain <> 'institution') GROUP BY state ORDER BY state")
            counts = cur.fetchall()
            result["assignment_counts"] = {row["state"]: row["count"] for row in counts}
            result["assignments_total"] = sum(row["count"] for row in counts)
            cur.execute("SELECT max(seq) AS cursor FROM events WHERE privacy_domain='institution'")
            result["event_cursor"] = cur.fetchone()["cursor"] or 0
            if present["cme_monitor_health"]:
                cur.execute("""SELECT status, instance_id, last_heartbeat_at, last_scan_at,
                                    last_error, assignments_observed, workers_registered,
                                    workers_enabled
                             FROM cme_monitor_health WHERE service_id=%s""",
                            (self.CME_SERVICE_ID,))
                health = cur.fetchone()
                if health:
                    cur.execute("SELECT extract(epoch FROM (clock_timestamp() - %s)) AS age",
                                (health["last_heartbeat_at"],))
                    age = float(cur.fetchone()["age"])
                    status = health["status"]
                    if age < 0:
                        status = "unverified"
                    elif status == "healthy" and age > self.heartbeat_stale_seconds:
                        status = "stale"
                    elif status == "healthy" and health["last_scan_at"] is None:
                        status = "degraded"
                    result["cme"] = {
                        "status": status, "service_id": self.CME_SERVICE_ID,
                        "instance_id": str(health["instance_id"]),
                        "last_heartbeat_at": self._iso(health["last_heartbeat_at"]),
                        "heartbeat_age_seconds": round(age, 3),
                        "last_scan_at": self._iso(health["last_scan_at"]),
                        "last_error_type": health["last_error"] if health["last_error"] and
                            _SAFE_CODE.fullmatch(str(health["last_error"])) else
                            ("recorded" if health["last_error"] else None),
                        "assignments_observed": health["assignments_observed"],
                        "workers_registered": health["workers_registered"],
                        "workers_enabled": health["workers_enabled"],
                        "source": "cme_monitor_health",
                    }
            if present["grace_execution_health"]:
                cur.execute("""SELECT instance_id,status,last_heartbeat_at,last_cycle_at,
                    last_error_type,cycles_completed FROM grace_execution_health
                    WHERE service_id='grace.execution.v1'""")
                grace = cur.fetchone()
                if grace:
                    cur.execute("SELECT extract(epoch FROM (clock_timestamp() - %s)) AS age",
                                (grace["last_heartbeat_at"],))
                    age = float(cur.fetchone()["age"])
                    grace_status = grace["status"]
                    if age < 0:
                        grace_status = "unverified"
                    elif grace_status == "healthy" and age > self.heartbeat_stale_seconds:
                        grace_status = "stale"
                    result["grace_execution"] = {
                        "status": grace_status, "service_id": "grace.execution.v1",
                        "instance_id": str(grace["instance_id"]),
                        "last_heartbeat_at": self._iso(grace["last_heartbeat_at"]),
                        "heartbeat_age_seconds": round(age, 3),
                        "last_cycle_at": self._iso(grace["last_cycle_at"]),
                        "last_error_type": grace["last_error_type"],
                        "cycles_completed": grace["cycles_completed"],
                        "source": "grace_execution_health"}
            if present["worker_registry"] and present["assignment_leases"]:
                cur.execute("""WITH worker_rows AS (
                               SELECT w.worker_id, w.active, max(l.heartbeat_at) AS heartbeat_at,
                                      count(l.assignment_id) FILTER (WHERE l.expires_at > clock_timestamp()
                                        AND NOT EXISTS (SELECT 1 FROM events p
                                          WHERE p.assignment_id=l.assignment_id
                                            AND p.privacy_domain <> 'institution')) AS active_leases
                               FROM worker_registry w LEFT JOIN assignment_leases l USING(worker_id)
                               GROUP BY w.worker_id, w.active
                             ), classified AS (
                               SELECT *, CASE
                                 WHEN NOT active THEN 'inactive'
                                 WHEN heartbeat_at IS NULL THEN 'unknown'
                                 WHEN extract(epoch FROM (clock_timestamp()-heartbeat_at)) < 0 THEN 'unverified'
                                 WHEN extract(epoch FROM (clock_timestamp()-heartbeat_at)) > %s THEN 'stale'
                                 ELSE 'healthy' END AS health
                               FROM worker_rows
                             )
                             SELECT count(*) FILTER (WHERE active) AS active_workers,
                                    count(*) FILTER (WHERE active AND health='healthy') AS healthy_workers,
                                    count(*) FILTER (WHERE active AND health='stale') AS stale_workers,
                                    count(*) FILTER (WHERE active AND health='unknown') AS unknown_workers,
                                    count(*) FILTER (WHERE active AND health='unverified') AS unverified_workers,
                                    coalesce(sum(active_leases) FILTER (WHERE active),0) AS active_leases
                             FROM classified""", (self.heartbeat_stale_seconds,))
                worker = cur.fetchone()
                if worker["active_workers"] == 0:
                    worker_status = "unknown"
                elif worker["unverified_workers"]:
                    worker_status = "unverified"
                elif worker["stale_workers"]:
                    worker_status = "stale"
                elif worker["unknown_workers"]:
                    worker_status = "unknown"
                else:
                    worker_status = "healthy"
                result["workers"] = {
                    "status": worker_status, "active_workers": worker["active_workers"],
                    "healthy_workers": worker["healthy_workers"],
                    "stale_workers": worker["stale_workers"],
                    "unknown_workers": worker["unknown_workers"],
                    "unverified_workers": worker["unverified_workers"],
                    "active_leases": int(worker["active_leases"] or 0),
                    "source": "assignment_leases", "health_semantics":
                        "per-worker latest lease heartbeat; no heartbeat is unknown, not healthy",
                }
            return result
        try:
            return self._read(query)
        except ProjectionUnavailable as exc:
            now = datetime.now(UTC).isoformat()
            return {
                "schema_version": "rv.dashboard.status.v1", "component_id": "STEWARD-DASHBOARD",
                "component_version": self.COMPONENT_VERSION, "observed_at": now,
                "source": {"kind": "postgresql", "schema": self.schema,
                           "source_commit": self.source_commit, "deployment_id": self.deployment_id},
                "projection_status": "unavailable", "freshness": "unavailable",
                "unavailable_reason": str(exc), "event_cursor": None, "assignment_counts": {},
                "assignments_total": 0, "cme": {"status": "unavailable"},
                "grace_execution": {"status": "unavailable"},
                "workers": {"status": "unavailable"}, "verification": {"status": "unavailable"},
                "diagnostics": {"component": "docs/components/STATUS_DASHBOARD_COOKBOOK.md"},
            }

    @staticmethod
    def _page_limit(value, default=25):
        try:
            return min(_MAX_PAGE, max(1, int(value)))
        except (TypeError, ValueError):
            return default

    def assignments(self, *, after: str | None = None, limit: int = 25):
        limit = self._page_limit(limit)
        if after is not None and (len(after) > 256 or "\x00" in after):
            raise ValueError("invalid assignment cursor")
        def query(cur):
            rel = self._relations(cur, [f"{self.schema}.assignments", f"{self.schema}.events"])
            if not all(rel.values()):
                return {"status": "not_initialized", "items": [], "next_cursor": None}
            cur.execute("""SELECT a.id, a.state, a.owner, a.workflow_id, a.workflow_step,
                                a.updated_at, a.version, a.correlation_id,
                                last.event_id AS last_event_id, last.seq AS last_event_seq,
                                last.event_type AS last_event_type, last.recorded_at AS last_progress_at
                         FROM assignments a
                         LEFT JOIN LATERAL (
                           SELECT event_id, seq, event_type, recorded_at FROM events
                           WHERE assignment_id=a.id AND privacy_domain='institution'
                           ORDER BY seq DESC LIMIT 1
                         ) last ON TRUE
                         WHERE (%s::text IS NULL OR a.id > %s)
                           AND NOT EXISTS (SELECT 1 FROM events p WHERE p.assignment_id=a.id
                                           AND p.privacy_domain <> 'institution')
                         ORDER BY a.id LIMIT %s""",
                        (after, after, limit + 1))
            rows = cur.fetchall()
            more = len(rows) > limit
            rows = rows[:limit]
            items = [{"assignment_id": row["id"], "state": row["state"],
                      "owner": row["owner"], "workflow_id": row["workflow_id"],
                      "workflow_step": row["workflow_step"], "updated_at": self._iso(row["updated_at"]),
                      "version": row["version"], "correlation_id": row["correlation_id"],
                      "last_meaningful_progress": {
                          "event_id": str(row["last_event_id"]) if row["last_event_id"] else None,
                          "event_seq": row["last_event_seq"], "event_type": row["last_event_type"],
                          "recorded_at": self._iso(row["last_progress_at"])},
                      "progress_measure": "last persisted event; no estimated percentage"}
                     for row in rows]
            return {"status": "available", "items": items,
                    "next_cursor": items[-1]["assignment_id"] if more and items else None,
                    "page_limit": limit, "truncated": more}
        return self._read(query)

    def events(self, *, after_seq: int | None = None, before_seq: int | None = None, limit: int = 25):
        limit = self._page_limit(limit)
        if after_seq is not None and before_seq is not None:
            raise ValueError("use either after_seq or before_seq")
        try:
            if after_seq is not None:
                after_seq = max(0, int(after_seq))
            if before_seq is not None:
                before_seq = max(0, int(before_seq))
        except (TypeError, ValueError):
            raise ValueError("invalid event cursor") from None
        def query(cur):
            rel = self._relations(cur, [f"{self.schema}.events"])
            if not next(iter(rel.values())):
                return {"status": "not_initialized", "items": [], "next_cursor": None}
            if before_seq is not None:
                cur.execute("""SELECT seq, event_id, event_type, occurred_at, recorded_at,
                                    assignment_id, actor_id, correlation_id, causation_id,
                                    payload_schema
                             FROM events WHERE seq < %s AND privacy_domain='institution'
                             ORDER BY seq DESC LIMIT %s""", (before_seq, limit + 1))
            elif after_seq is not None:
                cur.execute("""SELECT seq, event_id, event_type, occurred_at, recorded_at,
                                    assignment_id, actor_id, correlation_id, causation_id,
                                    payload_schema
                             FROM events WHERE seq > %s AND privacy_domain='institution'
                             ORDER BY seq LIMIT %s""", (after_seq, limit + 1))
            else:
                cur.execute("""SELECT seq, event_id, event_type, occurred_at, recorded_at,
                                    assignment_id, actor_id, correlation_id, causation_id,
                                    payload_schema
                             FROM events WHERE privacy_domain='institution'
                             ORDER BY seq DESC LIMIT %s""", (limit + 1,))
            rows = cur.fetchall()
            more = len(rows) > limit
            rows = rows[:limit]
            if after_seq is None:
                rows.reverse()
            items = [{"seq": row["seq"], "event_id": str(row["event_id"]),
                      "event_type": row["event_type"], "occurred_at": self._iso(row["occurred_at"]),
                      "recorded_at": self._iso(row["recorded_at"]),
                      "assignment_id": row["assignment_id"], "actor_id": row["actor_id"],
                      "correlation_id": row["correlation_id"],
                      "causation_id": str(row["causation_id"]) if row["causation_id"] else None,
                      "payload_schema": row["payload_schema"]} for row in rows]
            return {"status": "available", "items": items,
                    "next_cursor": items[-1]["seq"] if more and items else None,
                    "older_cursor": items[0]["seq"] if (before_seq is not None or after_seq is None)
                        and more and items else None,
                    "newer_cursor": items[-1]["seq"] if items else after_seq,
                    "page_limit": limit, "truncated": more}
        return self._read(query)

    def assignment_detail(self, assignment_id: str):
        if len(assignment_id) > 256 or "\x00" in assignment_id:
            raise ValueError("invalid assignment id")
        def query(cur):
            cur.execute("""SELECT a.id, a.state, a.owner, a.workflow_id, a.workflow_step,
                                a.updated_at, a.version, a.correlation_id
                         FROM assignments a WHERE a.id=%s AND NOT EXISTS (
                           SELECT 1 FROM events p WHERE p.assignment_id=a.id
                           AND p.privacy_domain <> 'institution')""", (assignment_id,))
            assignment = cur.fetchone()
            if assignment is None:
                return None
            cur.execute("""SELECT event_id, seq, event_type, recorded_at, actor_id,
                                correlation_id, causation_id FROM events
                         WHERE assignment_id=%s AND privacy_domain='institution'
                         ORDER BY seq DESC LIMIT 20""", (assignment_id,))
            events = cur.fetchall()
            tables = self._relations(cur, [f"{self.schema}.worker_attempts",
                                           f"{self.schema}.verification_records"])
            attempts = []
            verifications = []
            if tables[f"{self.schema}.worker_attempts"]:
                cur.execute("""SELECT attempt_id, worker_id, lease_generation, capability,
                                    status, started_at, finished_at, failure_class
                             FROM worker_attempts WHERE assignment_id=%s
                             ORDER BY started_at DESC, attempt_id DESC LIMIT 5""", (assignment_id,))
                attempts = [dict(row) for row in cur.fetchall()]
                for row in attempts:
                    row["attempt_id"] = str(row["attempt_id"])
                    row["started_at"] = self._iso(row["started_at"])
                    row["finished_at"] = self._iso(row["finished_at"])
                    if row["failure_class"] and not _SAFE_CODE.fullmatch(str(row["failure_class"])):
                        row["failure_class"] = "recorded"
            if tables[f"{self.schema}.verification_records"]:
                cur.execute("""SELECT verification_id, attempt_id, verifier_id,
                                    verifier_revision, decision, jsonb_array_length(evidence_references) AS evidence_count,
                                    recorded_at FROM verification_records WHERE assignment_id=%s
                             ORDER BY recorded_at DESC, verification_id DESC LIMIT 5""", (assignment_id,))
                verifications = [{"verification_id": str(row["verification_id"]),
                                  "attempt_id": str(row["attempt_id"]), "verifier_id": row["verifier_id"],
                                  "verifier_revision": row["verifier_revision"],
                                  "decision": row["decision"], "evidence_count": row["evidence_count"],
                                  "recorded_at": self._iso(row["recorded_at"])}
                                 for row in cur.fetchall()]
            return {"status": "available", "assignment": {
                "assignment_id": assignment["id"], "state": assignment["state"],
                "owner": assignment["owner"], "workflow_id": assignment["workflow_id"],
                "workflow_step": assignment["workflow_step"], "updated_at": self._iso(assignment["updated_at"]),
                "version": assignment["version"], "correlation_id": assignment["correlation_id"]},
                "events": [{"event_id": str(row["event_id"]), "seq": row["seq"],
                            "event_type": row["event_type"], "recorded_at": self._iso(row["recorded_at"]),
                            "actor_id": row["actor_id"], "correlation_id": row["correlation_id"],
                            "causation_id": str(row["causation_id"]) if row["causation_id"] else None}
                           for row in events],
                "attempts": attempts, "verifications": verifications,
                "diagnostic_ref": "docs/components/STATUS_DASHBOARD_COOKBOOK.md"}
        return self._read(query)

    def workers(self, *, after: str | None = None, limit: int = 25):
        limit = self._page_limit(limit)
        if after is not None and (len(after) > 256 or "\x00" in after):
            raise ValueError("invalid worker cursor")
        def query(cur):
            rel = self._relations(cur, [f"{self.schema}.worker_registry",
                                        f"{self.schema}.assignment_leases",
                                        f"{self.schema}.events"])
            if not all(rel.values()):
                return {"status": "not_initialized", "items": [], "next_cursor": None,
                        "page_limit": limit}
            cur.execute("""SELECT w.worker_id, w.active,
                                max(l.heartbeat_at) AS heartbeat_at,
                                extract(epoch FROM (clock_timestamp()-max(l.heartbeat_at))) AS heartbeat_age,
                                count(l.assignment_id) FILTER (WHERE l.expires_at > clock_timestamp()
                                  AND NOT EXISTS (SELECT 1 FROM events p
                                    WHERE p.assignment_id=l.assignment_id
                                      AND p.privacy_domain <> 'institution')) AS active_leases
                         FROM worker_registry w LEFT JOIN assignment_leases l USING(worker_id)
                         WHERE (%s::text IS NULL OR w.worker_id > %s)
                         GROUP BY w.worker_id,w.active ORDER BY w.worker_id LIMIT %s""",
                        (after, after, limit + 1))
            rows=cur.fetchall();more=len(rows)>limit;rows=rows[:limit];items=[]
            for row in rows:
                age=float(row["heartbeat_age"]) if row["heartbeat_age"] is not None else None
                if not row["active"]: health="inactive"
                elif age is None: health="unknown"
                elif age < 0: health="unverified"
                elif age > self.heartbeat_stale_seconds: health="stale"
                else: health="healthy"
                items.append({"worker_id":row["worker_id"],"active":row["active"],
                    "status":health,"last_heartbeat_at":self._iso(row["heartbeat_at"]),
                    "heartbeat_age_seconds":round(age,3) if age is not None else None,
                    "active_leases":row["active_leases"],"source":"assignment_leases"})
            return {"status":"available","items":items,
                    "next_cursor":items[-1]["worker_id"] if more and items else None,
                    "page_limit":limit,"truncated":more}
        return self._read(query)

    def attention(self, *, limit: int = 25):
        limit = self._page_limit(limit)
        def query(cur):
            rel = self._relations(cur, [f"{self.schema}.cme_monitor_events"])
            if not next(iter(rel.values())):
                return {"status": "not_initialized", "items": [], "limit": limit}
            cur.execute("""SELECT e.event_id, e.event_type, e.assignment_id, e.attention_key,
                                e.details, e.recorded_at FROM cme_monitor_events e
                         WHERE e.assignment_id IS NULL OR NOT EXISTS (
                           SELECT 1 FROM events p WHERE p.assignment_id=e.assignment_id
                           AND p.privacy_domain <> 'institution')
                         ORDER BY e.recorded_at DESC, e.event_id DESC LIMIT %s""", (limit,))
            items = []
            for row in cur.fetchall():
                details = row["details"] if isinstance(row["details"], dict) else {}
                failure_type = details.get("failure_type")
                items.append({"event_id": str(row["event_id"]), "event_type": row["event_type"],
                              "assignment_id": row["assignment_id"],
                              "attention_key": row["attention_key"],
                              "recorded_at": self._iso(row["recorded_at"]),
                              "failure_type": failure_type if isinstance(failure_type, str) and
                                  _SAFE_CODE.fullmatch(failure_type) else None})
            return {"status": "available", "items": items, "limit": limit}
        return self._read(query)

    def objectives(self, *, limit: int = 25, objective_id: str | None = None):
        """Read bounded objective, work-order, artifact and verification summaries."""
        limit = self._page_limit(limit)
        def query(cur):
            present = self._relations(cur, [f"{self.schema}.grace_objectives"])
            if not next(iter(present.values())):
                return {"schema_version": "rv.dashboard.objectives.v1",
                        "status": "not_initialized", "items": [], "limit": limit}
            cur.execute("""SELECT o.objective_id,o.request,o.scope_ref,o.submitter_id,
                    o.acceptance_criteria,o.status,o.assignment_id,o.source_revision,
                    o.source_sha256,o.revision,o.created_at,o.updated_at,
                    a.state AS assignment_state,wa.attempt_id,wr.result AS artifact,
                    wr.result_sha256,vr.decision AS verification_decision,
                    vr.verification_id,vr.verifier_revision,de.failure_count,
                    de.last_failure_at
                FROM grace_objectives o
                LEFT JOIN assignments a ON a.id=o.assignment_id
                LEFT JOIN LATERAL (SELECT attempt_id FROM worker_attempts x
                    WHERE x.assignment_id=a.id ORDER BY x.started_at DESC LIMIT 1) wa ON true
                LEFT JOIN worker_results wr ON wr.attempt_id=wa.attempt_id
                LEFT JOIN LATERAL (SELECT verification_id,decision,verifier_revision
                    FROM verification_records v WHERE v.assignment_id=a.id
                    ORDER BY v.verification_id DESC LIMIT 1) vr ON true
                LEFT JOIN LATERAL (SELECT count(*) AS failure_count,max(occurred_at) AS last_failure_at
                    FROM grace_objective_events e WHERE e.objective_id=o.objective_id
                      AND e.event_type='execution.dispatch_failed') de ON true
                WHERE (%s::text IS NULL OR o.objective_id=%s)
                ORDER BY o.updated_at DESC,o.objective_id LIMIT %s""",
                (objective_id, objective_id, limit))
            items=[]
            for row in cur.fetchall():
                artifact = row["artifact"] if isinstance(row["artifact"], dict) else None
                items.append({"objective_id": row["objective_id"],
                    "request": str(row["request"])[:512], "scope_ref": row["scope_ref"],
                    "submitter_id": row["submitter_id"],
                    "acceptance_criteria": row["acceptance_criteria"],
                    "status": row["status"], "assignment_id": row["assignment_id"],
                    "assignment_state": row["assignment_state"],
                    "attempt_id": str(row["attempt_id"]) if row["attempt_id"] else None,
                    "artifact": ({"sha256": row["result_sha256"],
                                  "reference": artifact.get("artifact_name"),
                                  "status": artifact.get("status")}
                                 if artifact else None),
                    "verification": ({"decision": row["verification_decision"],
                                      "verification_id": str(row["verification_id"]),
                                      "verifier_revision": row["verifier_revision"]}
                                     if row["verification_decision"] else None),
                    "dispatch_failures": int(row["failure_count"] or 0),
                    "last_dispatch_failure_at": self._iso(row["last_failure_at"]),
                    "source_revision": row["source_revision"],
                    "source_sha256": row["source_sha256"], "revision": row["revision"],
                    "created_at": self._iso(row["created_at"]),
                    "updated_at": self._iso(row["updated_at"])})
            return {"schema_version": "rv.dashboard.objectives.v1", "status": "available",
                    "observed_at": datetime.now(UTC).isoformat(), "items": items,
                    "limit": limit, "truncated": len(items) == limit}
        return self._read(query)

    def snapshot(self):
        status = self.status()
        if status["projection_status"] == "unavailable":
            assignments = {"status": "unavailable", "items": [], "truncated": False}
            event_page = {"status": "unavailable", "items": [], "truncated": False}
            attention = {"status": "unavailable", "items": []}
            workers = {"status": "unavailable", "items": [], "truncated": False}
        else:
            assignments = self.assignments(limit=_MAX_SNAPSHOT_ASSIGNMENTS)
            event_page = self.events(limit=_MAX_SNAPSHOT_EVENTS)
            attention = self.attention(limit=_MAX_SNAPSHOT_EVENTS)
            workers = self.workers(limit=_MAX_SNAPSHOT_EVENTS)
        return {"schema_version": "rv.dashboard.snapshot.v1", "captured_at": datetime.now(UTC).isoformat(),
                "observed_state": status["projection_status"] != "unavailable", "source": status["source"], "projection": status,
                "assignments": assignments, "events": event_page, "attention": attention, "workers": workers,
                "references": {"roadmap": "docs/ROADMAP.md",
                               "process_graph": "process_graphs/steward-dashboard/status.json",
                               "cookbook": "docs/components/STATUS_DASHBOARD_COOKBOOK.md"},
                "redaction": {"credentials": "excluded", "private_events": "excluded",
                              "payload_bodies": "excluded", "conversation_content": "not collected"},
                "client_state": {"ui_errors": "browser-local and not included by this API"}}
