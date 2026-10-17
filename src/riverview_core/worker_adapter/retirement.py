# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/retirement.py
# Component: WORKER-ADAPTER / INSTITUTIONAL-AUTHORITY
# Revision: 1.0.1
# Purpose: Retire only revoked, stopped M33 worker registrations with no executable work
# Execution Model: Explicit root-local operator action using one PostgreSQL transaction
# Observability: Append-only institutional authority event and resulting active registration count
# Dependencies: PostgreSQL schemas riverview_dev/riverview_authority; systemd; AuthorityRegistry
# Authority: Exact M33 IDs, active Steward identity.manage grant, revoked worker authority, stopped units, no runnable work
# Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Initial guarded retirement operation
# Changed: 2026-10-17 UTC | M33-0009-SYSTEMD-PARSER-FIX | Parse named systemd properties without relying on output order
# Contracts: docs/components/WORKER_ADAPTER_COOKBOOK.md; docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# Tests: tests/test_worker_registration_retirement.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Narrow, auditable retirement for the single revoked M33 commissioning run."""

from __future__ import annotations

import subprocess
from uuid import uuid4

from psycopg import sql

from ..institutional_authority import AuthorityDenied, IdentityConflict

RUN_ID = "e92ec51590b34cd3b04d05c000f3eab4"
SCOPE = "work-order:m33-live-e92ec51590b34cd3"
WORKER_IDS = (
    "worker:m33:executor:e92ec51590b34cd3",
    "worker:m33:verifier:e92ec51590b34cd3",
)
GRACE_IDS = (
    "worker:grace-engineering",
    "worker:grace-engineering-source-change",
    "verifier:grace-engineering",
)
EXPECTED_ACTIVE = frozenset((*WORKER_IDS, *GRACE_IDS))
RUN_GRANTS = {
    "rv-m33:e92ec51590b34cd3:assignment-create": ("steward:camrui", "assignment.create"),
    "rv-m33:e92ec51590b34cd3:assignment-execute": (WORKER_IDS[0], "assignment.execute"),
    "rv-m33:e92ec51590b34cd3:assignment-verify": (WORKER_IDS[1], "assignment.verify"),
    "rv-m33:e92ec51590b34cd3:executor-register": (WORKER_IDS[0], "worker.register"),
    "rv-m33:e92ec51590b34cd3:verifier-register": (WORKER_IDS[1], "worker.register"),
}
SERVICE_UNITS = (
    "riverview-assignment-intake.service",
    "riverview-m33-worker.service",
    "riverview-m33-verifier.service",
)
EXECUTABLE_STATES = ("queued", "ready", "running", "awaiting_verification",
                     "rework_required")


class WorkerRetirementError(RuntimeError):
    """A retirement precondition failed; the transaction made no change."""


def _verify_stopped_services() -> dict[str, dict[str, str]]:
    result = {}
    for unit in SERVICE_UNITS:
        completed = subprocess.run(
            ["systemctl", "show", "--property=ActiveState", "--property=SubState",
             "--property=MainPID", unit],
            capture_output=True, text=True, check=False, timeout=5)
        properties = {}
        for line in completed.stdout.splitlines():
            key, separator, value = line.partition("=")
            if not separator or key in properties:
                raise WorkerRetirementError("m33_service_not_stopped")
            properties[key] = value
        if (completed.returncode != 0 or
                properties != {"MainPID": "0", "ActiveState": "inactive", "SubState": "dead"}):
            raise WorkerRetirementError("m33_service_not_stopped")
        result[unit] = {"active_state": properties["ActiveState"],
                        "sub_state": properties["SubState"],
                        "main_pid": properties["MainPID"]}
    return result


def retire_revoked_m33_registrations(registry, steward_token: str, *,
                                     worker_schema: str = "riverview_dev") -> dict:
    """Atomically retire the two fixed M33 registrations after all live preflights."""
    service_states = _verify_stopped_services()
    authority_schema = registry.schema
    if not worker_schema.replace("_", "").isalnum():
        raise WorkerRetirementError("worker_schema_invalid")
    if not authority_schema.replace("_", "").isalnum():
        raise WorkerRetirementError("authority_schema_invalid")

    try:
        with registry.db.transaction():
            with registry.db.cursor() as cur:
                registry._path(cur)
                actor = registry._require(
                    cur, steward_token,
                    "identity.manage", "institution")
                if actor.get("principal_kind") != "steward":
                    raise AuthorityDenied("worker retirement requires an active Steward")

                worker_table = sql.SQL("{}.worker_registry").format(sql.Identifier(worker_schema))
                assignment_table = sql.SQL("{}.assignments").format(sql.Identifier(worker_schema))
                lease_table = sql.SQL("{}.assignment_leases").format(sql.Identifier(worker_schema))
                cur.execute("SELECT has_table_privilege(current_user,%s,'UPDATE') AS allowed",
                            (f"{worker_schema}.worker_registry",))
                if not cur.fetchone()["allowed"]:
                    raise WorkerRetirementError("database_role_cannot_retire_registration")
                cur.execute(sql.SQL("SELECT worker_id,active,scope_ref FROM {} WHERE worker_id=ANY(%s) ORDER BY worker_id FOR UPDATE").format(worker_table), (list(WORKER_IDS),))
                workers = cur.fetchall()
                if (len(workers) != 2 or {row["worker_id"] for row in workers} != set(WORKER_IDS) or
                        any(not row["active"] or row["scope_ref"] != SCOPE for row in workers)):
                    raise WorkerRetirementError("exact_active_m33_registrations_not_found")

                cur.execute(sql.SQL("SELECT worker_id FROM {} WHERE active ORDER BY worker_id").format(worker_table))
                active_ids = frozenset(row["worker_id"] for row in cur.fetchall())
                cur.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(worker_table))
                total_rows = cur.fetchone()["n"]
                if active_ids != EXPECTED_ACTIVE or total_rows != 7:
                    raise WorkerRetirementError("registry_inventory_changed")

                cur.execute("""SELECT grant_id,principal_id,action,scope_ref,revoked_at
                               FROM authority_grants WHERE grant_id=ANY(%s) ORDER BY grant_id""",
                            (list(RUN_GRANTS),))
                grants = cur.fetchall()
                if (len(grants) != len(RUN_GRANTS) or any(
                        RUN_GRANTS.get(row["grant_id"]) != (row["principal_id"], row["action"])
                        or row["scope_ref"] != SCOPE or row["revoked_at"] is None
                        for row in grants)):
                    raise WorkerRetirementError("commissioning_grants_not_exactly_revoked")
                cur.execute("SELECT count(*) AS n FROM authority_grants WHERE scope_ref=%s AND revoked_at IS NULL",
                            (SCOPE,))
                if cur.fetchone()["n"]:
                    raise WorkerRetirementError("worker_authority_not_fully_revoked")
                cur.execute("""SELECT principal_id,count(*) AS total,
                                      count(*) FILTER (WHERE revoked_at IS NULL) AS not_revoked
                               FROM principal_credentials WHERE principal_id=ANY(%s)
                               GROUP BY principal_id ORDER BY principal_id""",
                            (list(WORKER_IDS),))
                credentials = cur.fetchall()
                if (len(credentials) != len(WORKER_IDS) or any(
                        row["total"] < 1 or row["not_revoked"] for row in credentials)):
                    raise WorkerRetirementError("worker_credentials_not_revoked")

                cur.execute(sql.SQL("SELECT count(*) AS n FROM {} WHERE worker_id=ANY(%s) AND expires_at>clock_timestamp()").format(lease_table), (list(WORKER_IDS),))
                if cur.fetchone()["n"]:
                    raise WorkerRetirementError("active_worker_lease_exists")
                cur.execute(sql.SQL("SELECT count(*) AS n FROM {} WHERE authority_ref=%s AND state=ANY(%s)").format(assignment_table), (SCOPE, list(EXECUTABLE_STATES)))
                executable_count = cur.fetchone()["n"]
                if executable_count:
                    raise WorkerRetirementError("executable_m33_assignment_exists")

                cur.execute(sql.SQL("UPDATE {} SET active=false WHERE worker_id=ANY(%s) AND active RETURNING worker_id").format(worker_table), (list(WORKER_IDS),))
                retired = sorted(row["worker_id"] for row in cur.fetchall())
                if retired != sorted(WORKER_IDS):
                    raise WorkerRetirementError("registration_update_incomplete")

                for worker_id in retired:
                    registry._event(cur, event_type="worker_registration_retired",
                                    actor_id=actor["principal_id"], subject_id=worker_id,
                                    payload={"worker_id": worker_id, "scope_ref": SCOPE,
                                             "commissioning_run_id": RUN_ID,
                                             "reason_code": "revoked_commissioning_run",
                                             "verified_stopped_services": list(SERVICE_UNITS),
                                             "executable_assignments": executable_count,
                                             "active_leases": 0})

                cur.execute(sql.SQL("SELECT count(*) AS n FROM {} WHERE active").format(worker_table))
                active_after = cur.fetchone()["n"]
                cur.execute(sql.SQL("SELECT worker_id FROM {} WHERE active ORDER BY worker_id").format(worker_table))
                active_after_ids = sorted(row["worker_id"] for row in cur.fetchall())
                if active_after != 3 or active_after_ids != sorted(GRACE_IDS):
                    raise WorkerRetirementError("active_registry_postcondition_failed")
        return {"status": "RETIRED", "run_id": RUN_ID, "retired_worker_ids": sorted(WORKER_IDS),
                "active_workers": 3, "remaining_active_worker_ids": sorted(GRACE_IDS),
                "verified_services": service_states}
    except (AuthorityDenied, IdentityConflict, WorkerRetirementError):
        raise
    except Exception as exc:
        raise WorkerRetirementError(type(exc).__name__) from None
