# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/provision_authority_boundary.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.1
# Purpose: Preflight/apply exact authority table ownership separation
# Execution Model: Explicit local operator command; read-only by default
# Observability: Redacted JSON report and process exit status
# Dependencies: Python 3.10+; Psycopg 3; riverview_core
# Authority: Only allowlisted M4.1 relations; requires PostgreSQL superuser for apply
# Changed: 2026-10-11 UTC | RV-M4.1-DB-BOUNDARY | Add dry-run-first authority owner provisioner
# Changed: 2026-10-11 UTC | RV-M4.1-PREFLIGHT-DIAGNOSTIC | Return safe static boundary failure details to operators
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# Tests: tests/test_institutional_authority_boundary.py
# History: .riverview-backups/manifest.jsonl
# =============================================================================
"""Dry-run-first provisioner for the M4.1 authority relation ownership boundary.

The database DSN is read only from RIVERVIEW_AUTHORITY_DBA_DSN and is never
printed. Shared schemas are not touched unless an operator explicitly selects
one and supplies --apply after the protected backup/restore preflight.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import psycopg

from riverview_core.institutional_authority.db_boundary import (
    BoundaryPreflightError,
    provision_authority_boundary,
)


def _safe_error_detail(exc):
    """Expose only reviewed static boundary messages or PostgreSQL SQLSTATEs."""
    if isinstance(exc, BoundaryPreflightError):
        return str(exc)
    if isinstance(exc, psycopg.Error) and exc.sqlstate:
        return "sqlstate=" + exc.sqlstate
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--runtime-role", default="riverview_core")
    parser.add_argument("--manager-role", default="riverview_authority_manager")
    parser.add_argument("--owner-role", default="riverview_authority_owner")
    parser.add_argument("--apply", action="store_true",
                        help="apply DDL; default performs read-only preflight")
    args = parser.parse_args(argv)
    dsn = os.environ.get("RIVERVIEW_AUTHORITY_DBA_DSN")
    if not dsn:
        print(json.dumps({"status": "ERROR", "error": "RIVERVIEW_AUTHORITY_DBA_DSN is required"}))
        return 2
    try:
        with psycopg.connect(dsn, autocommit=True) as connection:
            report = provision_authority_boundary(
                connection, schema=args.schema, runtime_role=args.runtime_role,
                manager_role=args.manager_role, owner_role=args.owner_role,
                apply=args.apply,
            )
        print(json.dumps(report, sort_keys=True))
        return 0
    except (BoundaryPreflightError, ValueError, psycopg.Error) as exc:
        # Exception strings may contain SQL details; report only the type/code.
        detail = _safe_error_detail(exc)
        print(json.dumps({"status": "ERROR", "failure_type": type(exc).__name__,
                          "detail": detail}, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
