#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/migrate_institutional_authority.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Apply checksum-pinned authority migrations and reconcile release declarations
# Execution Model: Explicit DBA release command; never runs at application startup
# Observability: Applied migration versions and exit status
# Dependencies: PostgreSQL 16; psycopg 3; riverview_core.postgres_migrations
# Authority: Fixed database/schema and existing AuthorityRegistry migration runner
# Tests: tests/test_institutional_authority.py
# =============================================================================
"""Apply the release's authority migrations and capability declarations."""

from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
import sys

from riverview_core.postgres_migrations import apply_migrations


DSN = "dbname=riverview"
SCHEMA = "riverview_authority"


def main() -> int:
    if os.geteuid() != 0 and getpass.getuser() != "postgres":
        print("Run as the local PostgreSQL administrator.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    migrations = root / "src/riverview_core/institutional_authority/migrations"
    declarations = migrations.parent / "capability_declarations"
    if (not (migrations / "0015_deployed_capability_declarations.sql").is_file()
            or not declarations.is_dir()
            or declarations.is_symlink()
            or not any(path.suffix == ".json" and path.is_file() and not path.is_symlink()
                       for path in declarations.iterdir())):
        print(json.dumps({"status": "failed",
                          "error": "release_capability_declarations_missing"}),
              file=sys.stderr)
        return 2
    try:
        applied = apply_migrations(
            DSN, schema=SCHEMA, migrations_dir=migrations)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}),
              file=sys.stderr)
        return 1
    print(json.dumps({"status": "applied", "schema": SCHEMA,
                      "versions": applied,
                      "declarations_reconciled": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
