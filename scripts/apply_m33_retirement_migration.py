#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/apply_m33_retirement_migration.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.1.0
# Purpose: Check or apply only the checksum-pinned M33 retirement migrations 0008 and 0009
# Execution Model: Explicit local PostgreSQL-administrator action; no startup side effects
# Observability: Redacted JSON status and exit code
# Dependencies: PostgreSQL 16; Psycopg 3; migrations 0000-0009
# Authority: Fixed database/schema/migration; no grants or worker-registry changes
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Add exact migration preflight/apply command
# Changed: 2026-10-17 UTC | RV-M33-MIGRATION-CHAIN-0008-0009 | Add guarded one-migration prerequisite mode
# Tests: tests/test_m33_retirement_migration.py
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Apply only the reviewed M33 worker-registration-retirement event migration."""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path
import sys

import psycopg

from riverview_core.institutional_authority.m33_retirement_migration import (
    RetirementMigrationError,
    apply_m33_retirement_migration,
    check_m33_retirement_migration,
    apply_m33_retirement_prerequisite,
    check_m33_retirement_prerequisite,
)

DSN = "dbname=riverview"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply-0008", action="store_true",
                       help="apply only migration 0008 after exact predecessor checks")
    modes.add_argument("--check-0008", action="store_true",
                       help="run a read-only preflight for migration 0008")
    modes.add_argument("--apply", action="store_true",
                       help="apply only migration 0009 after all fixed checks pass")
    modes.add_argument("--check", action="store_true",
                       help="run a read-only prerequisite check for migration 0009 (default)")
    args = parser.parse_args(argv)
    if getpass.getuser() != "postgres":
        print(json.dumps({"status": "ERROR", "failure_code": "local_postgres_operator_required"}))
        return 2

    root = Path(__file__).resolve().parents[1]
    migration_directory = root / "src/riverview_core/institutional_authority/migrations"
    try:
        with psycopg.connect(DSN, autocommit=True) as connection:
            if args.apply_0008:
                result = apply_m33_retirement_prerequisite(connection, migration_directory)
            elif args.check_0008:
                result = check_m33_retirement_prerequisite(connection, migration_directory)
            elif args.apply:
                result = apply_m33_retirement_migration(connection, migration_directory)
            else:
                result = check_m33_retirement_migration(connection, migration_directory)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (RetirementMigrationError, psycopg.Error, OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "failure_code": type(exc).__name__},
                         sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
