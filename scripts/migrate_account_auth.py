#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/migrate_account_auth.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.0.0
# Purpose: Apply checksum-pinned account migrations to the dedicated account schema
# Execution Model: Explicit DBA commissioning CLI; never runs at application startup
# Observability: Applied migration version list and exit code
# Dependencies: PostgreSQL 16; psycopg 3; riverview_core.postgres_migrations
# Authority: Fixed database/schema target; additive migration files only
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Initial explicit account migration command
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: tests/test_account_auth.py
# History: Git and revision/backup manifest
# =============================================================================
"""Apply only account-auth migrations to riverview.riverview_accounts."""

from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
import sys

from riverview_core.postgres_migrations import apply_migrations

DSN = "dbname=riverview"
SCHEMA = "riverview_accounts"


def main():
    if os.geteuid() != 0 and getpass.getuser() != "postgres":
        print("Run as the local PostgreSQL administrator.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    try:
        applied = apply_migrations(
            DSN, schema=SCHEMA,
            migrations_dir=root / "src/riverview_core/account_auth/migrations")
    except Exception as exc:
        print(json.dumps({"status":"failed", "error_type":type(exc).__name__}), file=sys.stderr)
        return 1
    print(json.dumps({"status":"applied", "schema":SCHEMA, "versions":applied}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
