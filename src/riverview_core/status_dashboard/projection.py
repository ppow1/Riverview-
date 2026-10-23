# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/projection.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.18
# Changed: 2026-10-23 UTC | RV-ISSUE-253-V2-ENGINEERING-PROGRESS | Add owner-scoped cancellation reason/time to the objective progress projection.
# Changed: 2026-10-23 UTC | RV-GRACE-CANCELLED-PROGRESS-20261023 | Keep CANCELLED authoritative over historical failure and blocked activity.
# Changed: 2026-10-23 UTC | RV-WORKER-HEALTH-SNAPSHOT-20261023 | Require active engineering-scope registry and matching capability for live worker health.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Project accepted image downloads beside their assignment verification record.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Expose only independently accepted ComfyUI binary artifact metadata for authorized download.
# Changed: 2026-10-22 UTC | RV-W4-GRACE-ACTIONABLE-DIAGNOSTICS-20261022 | Project bounded sanitized grounding-failure history with owner-scoped objective progress.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-OPTIONAL-CRITERIA-20261021 | Expose the criteria source alongside effective objective criteria.
# Changed: 2026-10-20 UTC | RV-GRACE-ACCEPTED-STEP-REWORK-001 | Project durable rework escalation-pending events as actionable Steward holds.
# Changed: 2026-10-19 UTC | RV-C1-PR152-SCOPE-PROVENANCE-001 | Add principal-scoped, minimized Engineering progress projections
# Purpose: Project authoritative PostgreSQL/CME state into bounded safe views
# Execution Model: Request-driven read-only API dependency
# Observability: Versioned status, assignment, event, attention and snapshot JSON
# Dependencies: Python 3.10+; Psycopg 3; M1.2/M1.4/M2.1-M2.4 schema
# Authority: SELECT-only projection; never mutates CME or assignment state
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-ISOLATION | Include durable dispatch/verifier failure summaries
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Project persisted verified artifact path with objective result
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Project durable objective-linked Engineering progress and verifier/rework status to the authenticated conversation UI
# Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-ROLE-SEPARATION-001 | Distinguish Grace's substantive satisfied assessment awaiting structural verifier recheck
# Changed: 2026-10-13 UTC | RV-LEDGER-GRAPH-POSITION | Project only ledger-recorded graph and node identities
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_status_dashboard.py
# History: Git and revision/backup manifest
# =============================================================================
"""Bounded, privacy-filtered read models over the existing PostgreSQL ledger."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

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
                    last_error_type,cycles_completed,worker_capabilities FROM grace_execution_health
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
                        "worker_capabilities": grace["worker_capabilities"],
                        "source": "grace_execution_health"}
            if present["worker_registry"] and present["assignment_leases"]:
                if present["grace_execution_health"]:
                    cur.execute("""WITH worker_rows AS (
                                   SELECT w.worker_id, w.active, max(l.heartbeat_at) AS lease_heartbeat_at,
                                          extract(epoch FROM (clock_timestamp()-max(l.heartbeat_at))) AS lease_age,
                                          count(l.assignment_id) FILTER (WHERE l.expires_at > clock_timestamp()
                                            AND NOT EXISTS (SELECT 1 FROM events p
                                              WHERE p.assignment_id=l.assignment_id
                                                AND p.privacy_domain <> 'institution')) AS active_leases,
                                          gh.status AS runtime_status,
                                          extract(epoch FROM (clock_timestamp()-gh.last_heartbeat_at)) AS runtime_age,
                                          EXISTS (SELECT 1 FROM jsonb_array_elements(gh.worker_capabilities) cap
                                            WHERE cap->>'worker_id'=w.worker_id
                                              AND w.capabilities ? (cap->>'capability'))
                                            AND w.scope_ref='work-order:engineering' AS runtime_ready
                                   FROM worker_registry w LEFT JOIN assignment_leases l USING(worker_id)
                                   LEFT JOIN grace_execution_health gh ON gh.service_id='grace.execution.v1'
                                   GROUP BY w.worker_id,w.active,gh.status,gh.last_heartbeat_at,gh.worker_capabilities
                                 ), classified AS (
                                   SELECT *, CASE
                                     WHEN NOT active THEN 'inactive'
                                     WHEN runtime_ready AND runtime_age < 0 THEN 'unverified'
                                     WHEN runtime_ready AND runtime_age > %s THEN 'stale'
                                     WHEN runtime_ready AND runtime_status='healthy' THEN 'healthy'
                                     WHEN runtime_ready THEN 'degraded'
                                     WHEN lease_age IS NULL THEN 'unknown'
                                     WHEN lease_age < 0 THEN 'unverified'
                                     WHEN lease_age > %s THEN 'stale'
                                     ELSE 'healthy' END AS health
                                   FROM worker_rows
                                 )
                             SELECT count(*) FILTER (WHERE active) AS active_workers,
                                    count(*) FILTER (WHERE active AND health='healthy') AS healthy_workers,
                                    count(*) FILTER (WHERE active AND health='degraded') AS degraded_workers,
                                    count(*) FILTER (WHERE active AND health='stale') AS stale_workers,
                                    count(*) FILTER (WHERE active AND health='unknown') AS unknown_workers,
                                    count(*) FILTER (WHERE active AND health='unverified') AS unverified_workers,
                                    coalesce(sum(active_leases) FILTER (WHERE active),0) AS active_leases
                             FROM classified""", (self.heartbeat_stale_seconds,
                                                    self.heartbeat_stale_seconds))
                else:
                    cur.execute("""WITH worker_rows AS (
                                   SELECT w.worker_id, w.active, max(l.heartbeat_at) AS heartbeat_at,
                                          count(l.assignment_id) FILTER (WHERE l.expires_at > clock_timestamp()
                                            AND NOT EXISTS (SELECT 1 FROM events p
                                              WHERE p.assignment_id=l.assignment_id
                                                AND p.privacy_domain <> 'institution')) AS active_leases
                                   FROM worker_registry w LEFT JOIN assignment_leases l USING(worker_id)
                                   GROUP BY w.worker_id,w.active
                                 ), classified AS (
                                   SELECT *, CASE WHEN NOT active THEN 'inactive'
                                     WHEN heartbeat_at IS NULL THEN 'unknown'
                                     WHEN extract(epoch FROM (clock_timestamp()-heartbeat_at)) < 0 THEN 'unverified'
                                     WHEN extract(epoch FROM (clock_timestamp()-heartbeat_at)) > %s THEN 'stale'
                                     ELSE 'healthy' END AS health FROM worker_rows
                                 )
                             SELECT count(*) FILTER (WHERE active) AS active_workers,
                                    count(*) FILTER (WHERE active AND health='healthy') AS healthy_workers,
                                    0 AS degraded_workers,
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
                elif worker["degraded_workers"]:
                    worker_status = "degraded"
                elif worker["unknown_workers"]:
                    worker_status = "unknown"
                else:
                    worker_status = "healthy"
                result["workers"] = {
                    "status": worker_status, "active_workers": worker["active_workers"],
                    "healthy_workers": worker["healthy_workers"],
                    "degraded_workers": worker["degraded_workers"],
                    "stale_workers": worker["stale_workers"],
                    "unknown_workers": worker["unknown_workers"],
                    "unverified_workers": worker["unverified_workers"],
                    "active_leases": int(worker["active_leases"] or 0),
                    "source": "grace_execution_health_and_assignment_leases", "health_semantics":
                        "configured in-process capabilities use Grace runtime heartbeat; other workers use lease heartbeats",
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
                                a.process_graph_id,a.process_node_id,
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
                      "workflow_step": row["workflow_step"],
                      "process_graph_id": row["process_graph_id"],
                      "process_node_id": row["process_node_id"],
                      "updated_at": self._iso(row["updated_at"]),
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
                                a.process_graph_id,a.process_node_id,
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
                "workflow_step": assignment["workflow_step"],
                "process_graph_id": assignment["process_graph_id"],
                "process_node_id": assignment["process_node_id"],
                "updated_at": self._iso(assignment["updated_at"]),
                "version": assignment["version"], "correlation_id": assignment["correlation_id"]},
                "events": [{"event_id": str(row["event_id"]), "seq": row["seq"],
                            "event_type": row["event_type"], "recorded_at": self._iso(row["recorded_at"]),
                            "actor_id": row["actor_id"], "correlation_id": row["correlation_id"],
                            "causation_id": str(row["causation_id"]) if row["causation_id"] else None}
                           for row in events],
                "attempts": attempts, "verifications": verifications,
                "diagnostic_ref": "docs/components/STATUS_DASHBOARD_COOKBOOK.md"}
        detail = self._read(query)
        if (detail and re.fullmatch(r"[A-Za-z0-9:._-]{1,128}", assignment_id) and
                any(item.get("capability") == "engineering.comfyui-image.v1"
                          and item.get("status") == "succeeded"
                          for item in detail.get("attempts", []))):
            artifacts = []
            for index in range(1, 9):
                item = self.comfyui_artifact(assignment_id, index)
                if item is None:
                    break
                artifacts.append({"index": index, "name": item["name"],
                    "bytes": item["bytes"], "sha256": item["sha256"],
                    "download_url": f"/api/v1/assignments/{assignment_id}/artifacts/{index}"})
            detail["comfyui_artifacts"] = artifacts
        return detail

    def comfyui_artifact(self, assignment_id: str, index: int):
        """Return metadata only for one independently accepted ComfyUI output."""
        if (not isinstance(assignment_id, str) or len(assignment_id) > 256 or
                "\x00" in assignment_id or type(index) is not int or not 1 <= index <= 8):
            raise ValueError("invalid ComfyUI artifact reference")
        def query(cur):
            cur.execute("""SELECT a.state,wa.attempt_id,wr.result,wr.result_sha256,
                    (SELECT decision FROM verification_records vr WHERE vr.attempt_id=wa.attempt_id
                     ORDER BY vr.recorded_at DESC,vr.verification_id DESC LIMIT 1) AS decision
                FROM assignments a
                JOIN worker_attempts wa ON wa.assignment_id=a.id
                JOIN worker_results wr USING(attempt_id)
                WHERE a.id=%s AND wa.capability='engineering.comfyui-image.v1'
                  AND wa.status='succeeded'
                  AND NOT EXISTS (SELECT 1 FROM events p WHERE p.assignment_id=a.id
                                  AND p.privacy_domain <> 'institution')
                ORDER BY wa.started_at DESC,wa.attempt_id DESC LIMIT 1""", (assignment_id,))
            row = cur.fetchone()
            if row is None or row["decision"] != "ACCEPTED" or row["state"] != "completed":
                return None
            result = row["result"] if isinstance(row["result"], dict) else None
            if result is None:
                return None
            encoded = json.dumps(result, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False).encode("utf-8")
            if hashlib.sha256(encoded).hexdigest() != str(row["result_sha256"]).strip():
                return None
            records = result.get("artifacts")
            if not isinstance(records, list) or not 1 <= len(records) <= 8:
                return None
            total = 0
            valid_records = []
            assignment_key = hashlib.sha256(assignment_id.encode("utf-8")).hexdigest()
            for item_position, item in enumerate(records, 1):
                if not isinstance(item, dict):
                    return None
                name = item.get("name")
                if (not isinstance(name, str) or
                        re.fullmatch(rf"comfyui-output-{item_position}\.(?:png|jpg|webp)", name) is None):
                    return None
                expected_storage = assignment_key + "/" + hashlib.sha256(name.encode()).hexdigest()[:12]
                size = item.get("bytes")
                digest = item.get("sha256")
                media = item.get("media_type")
                if (item.get("storage_name") != expected_storage or type(size) is not int or
                        not 0 < size <= 16 * 1024 * 1024 or
                        not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or
                        media not in {"image/png", "image/jpeg", "image/webp"}):
                    return None
                total += size
                valid_records.append({"name": name, "storage_name": expected_storage,
                                      "bytes": size, "sha256": digest, "media_type": media})
            selected = next((item for pos, item in enumerate(valid_records, 1) if pos == index), None)
            if selected is None or total > 48 * 1024 * 1024:
                return None
            return {"status": "available", "assignment_id": assignment_id,
                    "attempt_id": str(row["attempt_id"]), "index": index,
                    "verification": "ACCEPTED", **selected}
        return self._read(query)

    def graph_execution_position(self, graph_id: str):
        """Return only a node identity recorded by the assignment event path."""
        if not isinstance(graph_id, str) or len(graph_id) > 200 or "\x00" in graph_id:
            raise ValueError("invalid process graph ID")
        def query(cur):
            cur.execute("""SELECT a.id,a.state,a.process_node_id,a.updated_at
                FROM assignments a WHERE a.process_graph_id=%s
                  AND a.process_node_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM events p WHERE p.assignment_id=a.id
                                  AND p.privacy_domain <> 'institution')
                ORDER BY a.updated_at DESC,a.id LIMIT 1""", (graph_id,))
            row = cur.fetchone()
            if row is None:
                return {"status": "unknown", "reason":
                    "No assignment has recorded a canonical node for this graph."}
            return {"status": "current", "assignment_id": row["id"],
                    "state": row["state"], "node_id": row["process_node_id"],
                    "recorded_at": self._iso(row["updated_at"]),
                    "reason": "Canonical node identity was persisted with the latest assignment transition."}
        return self._read(query)

    def workers(self, *, after: str | None = None, limit: int = 25):
        limit = self._page_limit(limit)
        if after is not None and (len(after) > 256 or "\x00" in after):
            raise ValueError("invalid worker cursor")
        def query(cur):
            rel = self._relations(cur, [f"{self.schema}.worker_registry",
                                        f"{self.schema}.assignment_leases",
                                        f"{self.schema}.events",
                                        f"{self.schema}.grace_execution_health"])
            required_relations = (f"{self.schema}.worker_registry",
                                  f"{self.schema}.assignment_leases",
                                  f"{self.schema}.events")
            if not all(rel[name] for name in required_relations):
                return {"status": "not_initialized", "items": [], "next_cursor": None,
                        "page_limit": limit}
            if rel[f"{self.schema}.grace_execution_health"]:
                cur.execute("""SELECT w.worker_id,w.active,w.capabilities,w.scope_ref,
                                max(l.heartbeat_at) AS lease_heartbeat_at,
                                extract(epoch FROM (clock_timestamp()-max(l.heartbeat_at))) AS lease_age,
                                count(l.assignment_id) FILTER (WHERE l.expires_at > clock_timestamp()
                                  AND NOT EXISTS (SELECT 1 FROM events p
                                    WHERE p.assignment_id=l.assignment_id
                                      AND p.privacy_domain <> 'institution')) AS active_leases,
                                gh.status AS runtime_status,gh.worker_capabilities,
                                gh.last_heartbeat_at AS runtime_heartbeat_at,
                                extract(epoch FROM (clock_timestamp()-gh.last_heartbeat_at)) AS runtime_age
                         FROM worker_registry w LEFT JOIN assignment_leases l USING(worker_id)
                         LEFT JOIN grace_execution_health gh ON gh.service_id='grace.execution.v1'
                         WHERE (%s::text IS NULL OR w.worker_id > %s)
                         GROUP BY w.worker_id,w.active,w.capabilities,w.scope_ref,gh.status,
                                  gh.worker_capabilities,gh.last_heartbeat_at
                         ORDER BY w.worker_id LIMIT %s""", (after, after, limit + 1))
            else:
                cur.execute("""SELECT w.worker_id,w.active,w.capabilities,w.scope_ref,
                                max(l.heartbeat_at) AS lease_heartbeat_at,
                                extract(epoch FROM (clock_timestamp()-max(l.heartbeat_at))) AS lease_age,
                                count(l.assignment_id) FILTER (WHERE l.expires_at > clock_timestamp()
                                  AND NOT EXISTS (SELECT 1 FROM events p
                                    WHERE p.assignment_id=l.assignment_id
                                      AND p.privacy_domain <> 'institution')) AS active_leases,
                                NULL::text AS runtime_status,NULL::jsonb AS worker_capabilities,
                                NULL::timestamptz AS runtime_heartbeat_at,NULL::numeric AS runtime_age
                         FROM worker_registry w LEFT JOIN assignment_leases l USING(worker_id)
                         WHERE (%s::text IS NULL OR w.worker_id > %s)
                         GROUP BY w.worker_id,w.active,w.capabilities,w.scope_ref
                         ORDER BY w.worker_id LIMIT %s""", (after, after, limit + 1))
            rows=cur.fetchall();more=len(rows)>limit;rows=rows[:limit];items=[]
            for row in rows:
                registered_capabilities = row["capabilities"] or []
                runtime_capabilities = [item for item in (row["worker_capabilities"] or [])
                    if isinstance(item, dict) and item.get("worker_id") == row["worker_id"] and
                    item.get("capability") in registered_capabilities and
                    row["scope_ref"] == "work-order:engineering"] if row["active"] else []
                runtime_age = (float(row["runtime_age"])
                               if row["runtime_age"] is not None else None)
                lease_age = float(row["lease_age"]) if row["lease_age"] is not None else None
                if not row["active"]:
                    health="inactive"
                elif runtime_capabilities and runtime_age is not None:
                    if runtime_age < 0: health="unverified"
                    elif runtime_age > self.heartbeat_stale_seconds: health="stale"
                    elif row["runtime_status"] == "healthy": health="healthy"
                    else: health="degraded"
                elif lease_age is None: health="unknown"
                elif lease_age < 0: health="unverified"
                elif lease_age > self.heartbeat_stale_seconds: health="stale"
                else: health="healthy"
                live_capabilities = sorted({item["capability"] for item in runtime_capabilities
                    if isinstance(item.get("capability"), str)})
                heartbeat_at = (row["runtime_heartbeat_at"] if runtime_capabilities
                                else row["lease_heartbeat_at"])
                items.append({"worker_id":row["worker_id"],"active":row["active"],
                    "status":health,"last_heartbeat_at":self._iso(heartbeat_at),
                    "heartbeat_age_seconds":round(runtime_age if runtime_capabilities else lease_age,3)
                        if (runtime_age if runtime_capabilities else lease_age) is not None else None,
                    "last_lease_heartbeat_at":self._iso(row["lease_heartbeat_at"]),
                    "active_leases":row["active_leases"],
                    "scope_ref":row["scope_ref"],
                    "registered_capabilities":registered_capabilities,
                    "live_registered_capabilities":live_capabilities,
                    "source":"grace_execution_health" if runtime_capabilities else "assignment_leases"})
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

    def objectives(self, *, limit: int = 25, objective_id: str | None = None,
                   conversation_id: str | None = None,
                   owner_principal_id: str | None = None,
                   progress_only: bool = False):
        """Read bounded objective and Engineering progress summaries.

        Conversation filtering uses only the durable objective.received origin;
        transcript bodies are neither selected nor returned.
        """
        limit = self._page_limit(limit)
        if (owner_principal_id is not None and
                (not isinstance(owner_principal_id, str) or not owner_principal_id.strip()
                 or len(owner_principal_id) > 256)):
            raise ValueError("owner_principal_id must be a bounded principal identifier")
        if type(progress_only) is not bool:
            raise ValueError("progress_only must be a boolean")
        if conversation_id is not None:
            try:
                conversation_id = str(UUID(conversation_id))
            except (ValueError, TypeError, AttributeError):
                raise ValueError("conversation_id must be a UUID") from None
        schema_version = ("rv.dashboard.objective_progress.v1" if progress_only
                          else "rv.dashboard.objectives.v1")
        def query(cur):
            present = self._relations(cur, [f"{self.schema}.grace_objectives"])
            if not next(iter(present.values())):
                return {"schema_version": schema_version,
                        "status": "not_initialized", "items": [], "limit": limit}
            cur.execute("""SELECT o.objective_id,o.request,o.scope_ref,o.submitter_id,
                    o.acceptance_criteria,o.status,o.assignment_id,o.source_revision,
                    o.source_sha256,o.revision,o.created_at,o.updated_at,
                    a.state AS assignment_state,wa.attempt_id,wr.result AS artifact,
                    wr.result_sha256,vr.decision AS verification_decision,
                    vr.verification_id,vr.verifier_revision,vr.summary AS verification_summary,
                    received.payload AS received_payload,
                    activity.event_type AS latest_event_type,activity.activity_at AS latest_event_at,
                    cancellation.event_type AS cancellation_event_type,
                    cancellation.occurred_at AS cancellation_at,
                    cancellation.actor_id AS cancellation_actor,
                    cancellation.payload AS cancellation_payload,
                    attempt_count.attempt_count,rejections.rejection_count,
                    rework.payload AS latest_rework,rework.occurred_at AS rework_at,
                    grounding.events AS grounding_diagnostics,
                    de.failure_count,
                    de.last_failure_at,ve.failure_count AS verification_failure_count,
                    ve.last_failure_at AS last_verification_failure_at
                FROM grace_objectives o
                LEFT JOIN assignments a ON a.id=o.assignment_id
                LEFT JOIN LATERAL (SELECT attempt_id FROM worker_attempts x
                    WHERE x.assignment_id=a.id ORDER BY x.started_at DESC LIMIT 1) wa ON true
                LEFT JOIN worker_results wr ON wr.attempt_id=wa.attempt_id
                LEFT JOIN LATERAL (SELECT verification_id,decision,verifier_revision
                        ,summary
                    FROM verification_records v WHERE v.assignment_id=a.id
                    ORDER BY v.recorded_at DESC,v.verification_id DESC LIMIT 1) vr ON true
                LEFT JOIN LATERAL (SELECT payload FROM grace_objective_events e
                    WHERE e.objective_id=o.objective_id AND e.event_type='objective.received'
                    ORDER BY e.sequence LIMIT 1) received ON true
                LEFT JOIN LATERAL (
                    SELECT event_type,activity_at FROM (
                        SELECT e.event_type,e.occurred_at AS activity_at
                        FROM grace_objective_events e WHERE e.objective_id=o.objective_id
                        UNION ALL
                        SELECT e.event_type,e.recorded_at AS activity_at FROM events e
                        WHERE e.assignment_id=a.id AND e.privacy_domain='institution'
                    ) activity_events ORDER BY activity_at DESC,event_type LIMIT 1
                ) activity ON true
                LEFT JOIN LATERAL (SELECT count(*)::bigint AS attempt_count
                    FROM worker_attempts x WHERE x.assignment_id=a.id) attempt_count ON true
                LEFT JOIN LATERAL (SELECT count(*)::bigint AS rejection_count
                    FROM verification_records x WHERE x.assignment_id=a.id AND x.decision='REJECTED') rejections ON true
                LEFT JOIN LATERAL (SELECT e.payload,e.occurred_at FROM grace_objective_events e
                    WHERE e.objective_id=o.objective_id
                      AND e.event_type IN ('engineering.rework_decided','engineering.rejection_reviewed','engineering.rework_escalation_pending')
                      AND e.payload->>'assignment_id'=a.id
                    ORDER BY e.sequence DESC LIMIT 1) rework ON true
                LEFT JOIN LATERAL (
                    SELECT coalesce(jsonb_agg(history.item ORDER BY history.sequence), '[]'::jsonb) AS events
                    FROM (
                        SELECT e.sequence, jsonb_build_object(
                            'event_id', e.event_id, 'occurred_at', e.occurred_at,
                            'diagnostic', e.payload->'grounding_diagnostic') AS item
                        FROM grace_objective_events e
                        WHERE e.objective_id=o.objective_id
                          AND e.payload ? 'grounding_diagnostic'
                        ORDER BY e.sequence DESC LIMIT 25
                    ) history
                ) grounding ON true
                LEFT JOIN LATERAL (SELECT e.event_type,e.occurred_at,e.actor_id,e.payload
                    FROM grace_objective_events e
                    WHERE e.objective_id=o.objective_id
                      AND e.event_type IN ('objective.cancelled','work_order.cancelled')
                    ORDER BY e.sequence DESC LIMIT 1) cancellation ON true
                LEFT JOIN LATERAL (SELECT count(*) AS failure_count,max(occurred_at) AS last_failure_at
                    FROM grace_objective_events e WHERE e.objective_id=o.objective_id
                      AND e.event_type='execution.dispatch_failed') de ON true
                LEFT JOIN LATERAL (SELECT count(*) AS failure_count,max(occurred_at) AS last_failure_at
                    FROM grace_objective_events e WHERE e.objective_id=o.objective_id
                      AND e.event_type='execution.verification_failed') ve ON true
                WHERE (%s::text IS NULL OR o.objective_id=%s)
                  AND (%s::uuid IS NULL OR received.payload #>> '{origin,conversation_id}'=%s)
                  AND (%s::text IS NULL OR o.submitter_id=%s)
                ORDER BY o.updated_at DESC,o.objective_id LIMIT %s""",
                (objective_id, objective_id, conversation_id, conversation_id,
                 owner_principal_id, owner_principal_id, limit))
            items=[]
            for row in cur.fetchall():
                artifact = row["artifact"] if isinstance(row["artifact"], dict) else None
                received_payload = row["received_payload"] if isinstance(row["received_payload"], dict) else {}
                origin = received_payload.get("origin") if isinstance(received_payload.get("origin"), dict) else {}
                rework = row["latest_rework"] if isinstance(row["latest_rework"], dict) else None
                verification_id = str(row["verification_id"]) if row["verification_id"] else None
                rework_is_current = bool(rework and rework.get("verification_id") == verification_id)
                action_needed = bool(rework_is_current and
                    rework.get("decision") in {"STEWARD_AUTHORIZATION_REQUIRED", "ESCALATION_PENDING"})
                assignment_state = row["assignment_state"]
                if row["status"] == "COMPLETED":
                    lifecycle_status, lifecycle_stage = "completed", "Objective completed"
                elif row["status"] == "CANCELLED":
                    lifecycle_status, lifecycle_stage = "cancelled", "Objective cancelled"
                elif action_needed:
                    lifecycle_status, lifecycle_stage = "blocked", (
                        "Rework escalation pending: Steward action required"
                        if rework.get("decision") == "ESCALATION_PENDING"
                        else "Steward action required")
                elif rework_is_current and rework.get("decision") == "OBJECTIVE_SATISFIED":
                    lifecycle_status, lifecycle_stage = "waiting", "Grace review complete; verifier recheck pending"
                elif assignment_state == "rework_required":
                    lifecycle_status, lifecycle_stage = "waiting", "Grace reviewing verifier rejection"
                elif assignment_state == "awaiting_verification":
                    lifecycle_status, lifecycle_stage = "waiting", "Independent verification"
                elif assignment_state == "blocked" or row["status"] == "FAILED":
                    lifecycle_status, lifecycle_stage = "blocked", "Blocked"
                elif assignment_state in {"queued", "ready", "running"}:
                    lifecycle_status, lifecycle_stage = "working", {
                        "queued": "Queued for Engineering",
                        "ready": "Ready for worker",
                        "running": "Engineering executing"}[assignment_state]
                elif row["status"] == "WAITING_FOR_EVIDENCE":
                    lifecycle_status, lifecycle_stage = "waiting", "Waiting for verified evidence"
                elif row["status"] in {"RECEIVED", "GROUNDED", "PROPOSED"}:
                    lifecycle_status, lifecycle_stage = "waiting", "Awaiting authorized work order"
                else:
                    lifecycle_status, lifecycle_stage = "waiting", str(row["status"])
                item = {"objective_id": row["objective_id"],
                    "request": str(row["request"])[:512], "scope_ref": row["scope_ref"],
                    "submitter_id": row["submitter_id"],
                    "acceptance_criteria": row["acceptance_criteria"],
                    "acceptance_criteria_source": received_payload.get(
                        "acceptance_criteria_source",
                        "steward_supplied" if row["acceptance_criteria"] else "legacy_unspecified"),
                    "status": row["status"], "assignment_id": row["assignment_id"],
                    "assignment_state": assignment_state,
                    "origin": ({"conversation_id": origin.get("conversation_id"),
                                "source_sequence": origin.get("source_sequence")}
                               if origin.get("conversation_id") and
                                  type(origin.get("source_sequence")) is int else None),
                    "lifecycle_status": lifecycle_status,
                    "lifecycle_stage": lifecycle_stage,
                    "latest_event": ({"event_type": row["latest_event_type"],
                                      "occurred_at": self._iso(row["latest_event_at"])}
                                     if row["latest_event_type"] else None),
                    "attempt_id": str(row["attempt_id"]) if row["attempt_id"] else None,
                    "artifact": ({"sha256": row["result_sha256"],
                                  "reference": artifact.get("artifact_name"),
                                  "path": artifact.get("artifact_path"),
                                  "status": artifact.get("status")}
                                 if artifact else None),
                    "verification": ({"decision": row["verification_decision"],
                                      "verification_id": verification_id,
                                      "verifier_revision": row["verifier_revision"],
                                      "summary": str(row["verification_summary"] or "")[:500]}
                                     if row["verification_decision"] else None),
                    "grounding_diagnostics": row["grounding_diagnostics"] or [],
                    "rework": {"rejected_results": int(row["rejection_count"] or 0),
                               "attempts": max(0, int(row["attempt_count"] or 0) - 1),
                               "decision": (rework.get("decision") if rework_is_current else None),
                               "rationale": (str(rework.get("rationale", ""))[:500]
                                             if rework_is_current else None),
                               "occurred_at": (self._iso(row["rework_at"])
                                               if rework_is_current else None)},
                    "steward_action_required": action_needed,
                    "dispatch_failures": int(row["failure_count"] or 0),
                    "last_dispatch_failure_at": self._iso(row["last_failure_at"]),
                    "verification_failures": int(row["verification_failure_count"] or 0),
                    "last_verification_failure_at": self._iso(row["last_verification_failure_at"]),
                    "source_revision": row["source_revision"],
                    "source_sha256": row["source_sha256"], "revision": row["revision"],
                    "created_at": self._iso(row["created_at"]),
                    "updated_at": self._iso(row["updated_at"])}
                cancellation_payload = (row["cancellation_payload"]
                    if isinstance(row["cancellation_payload"], dict) else {})
                item["cancellation"] = ({
                    "reason": str(cancellation_payload.get("reason", ""))[:500],
                    "cancelled_at": self._iso(row["cancellation_at"]),
                    "actor_id": str(row["cancellation_actor"] or "")[:256] or None,
                } if row["status"] == "CANCELLED" and row["cancellation_event_type"] else None)
                if progress_only:
                    item = {key: item[key] for key in (
                        "objective_id", "status", "assignment_id", "assignment_state",
                        "origin", "lifecycle_status", "lifecycle_stage", "latest_event",
                        "verification", "rework", "cancellation", "steward_action_required",
                        "grounding_diagnostics",
                        "dispatch_failures", "last_dispatch_failure_at",
                        "verification_failures", "last_verification_failure_at",
                        "created_at", "updated_at")}
                items.append(item)
            return {"schema_version": schema_version, "status": "available",
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
