# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/reconcile_grace_requirements_heading.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-RECONCILIATION | Initial fixed-scope root-local reconciliation command.
# Purpose: Apply the Steward-approved one-objective structural-heading correction
# Execution Model: Root-local single operation through the authorized Grace pipeline
# Observability: Emits only objective status, revision, actor, and audit timestamp
# Dependencies: Protected Steward credential; PostgreSQL; installed Grace release
# Authority: Fixed objective, fixed expected revision, exact-action grant, database CAS and trigger guard
# Contracts: GRACE_EXECUTION_PIPELINE.md; INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_grace_execution.py
# =============================================================================
"""Run the single Steward-approved audited acceptance-criteria reconciliation."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

from riverview_core.assignment_intake import AuthorizedAssignmentIntake
from riverview_core.institutional_authority.grants import ExactGrantAuthorizer
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.resident_execution.pipeline import GraceExecutionPipeline


OBJECTIVE_ID = "objective:grace-conversation:8416c5da-bde5-5294-9276-c0163418fae1"
STEWARD_TOKEN = Path("/etc/riverview/authority/steward.token")
PGPASS = Path("/etc/riverview/pgpass")
DSN = "host=127.0.0.1 port=5432 dbname=riverview user=riverview_core application_name=grace-criteria-reconciliation"
SCHEMA = "riverview_dev"
AUTHORITY_SCHEMA = "riverview_authority"
REASON = "Steward-approved removal of the misclassified structural heading Requirements:; substantive criteria, request, history, and verified evidence are preserved."


def _protected_token(path: Path) -> str:
    if path.is_symlink():
        raise RuntimeError("protected credential path is a symlink")
    info = path.stat(follow_symlinks=False)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
            stat.S_IMODE(info.st_mode) != 0o600 or not 32 <= info.st_size <= 512):
        raise RuntimeError("protected Steward credential metadata is invalid")
    return path.read_text(encoding="ascii").strip()


def main() -> int:
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        print('{"status":"BLOCKED","reason":"root_local_operation_required"}')
        return 2
    if PGPASS.is_symlink():
        print('{"status":"BLOCKED","reason":"pgpass_path_is_symlink"}')
        return 2
    pgpass_info = PGPASS.stat(follow_symlinks=False)
    if (not stat.S_ISREG(pgpass_info.st_mode) or pgpass_info.st_uid != 0 or
            stat.S_IMODE(pgpass_info.st_mode) != 0o600):
        print('{"status":"BLOCKED","reason":"pgpass_metadata_invalid"}')
        return 2
    os.environ["PGPASSFILE"] = str(PGPASS)
    token = _protected_token(STEWARD_TOKEN)
    ledger = PostgresLedger(DSN, schema=SCHEMA)
    try:
        authorizer = ExactGrantAuthorizer(AUTHORITY_SCHEMA)
        pipeline = GraceExecutionPipeline(
            ledger, authorizer, AuthorizedAssignmentIntake(ledger, authorizer), None)
        result = pipeline.reconcile_misclassified_requirements_heading(
            OBJECTIVE_ID, expected_revision=2, credential=token, reason=REASON)
        with ledger.db.cursor() as cur:
            ledger._set_search_path(cur)
            cur.execute("""SELECT event_id,actor_id,occurred_at,payload
                FROM grace_objective_events WHERE objective_id=%s
                  AND event_type='objective.criteria_reconciled'""", (OBJECTIVE_ID,))
            event = cur.fetchone()
        print(json.dumps({"status": result["status"], "revision": result["revision"],
            "actor": event["actor_id"], "event_id": str(event["event_id"]),
            "occurred_at": event["occurred_at"].isoformat(),
            "before_count": len(event["payload"]["before_criteria"]),
            "after_count": len(event["payload"]["after_criteria"])}, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "failure_type": type(exc).__name__}, sort_keys=True))
        return 1
    finally:
        ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
