# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/postgres_migrations.py
# Component: POSTGRES-LEDGER
# Revision: 1.0.0
# Purpose: Apply ordered, checksum-pinned PostgreSQL schema migrations
# Execution Model: Request-driven migration CLI/library
# Observability: Applied versions and checksums in schema_migrations
# Dependencies: Python 3.10+; Psycopg 3; PostgreSQL 16; SQL migration files
# Authority: Changes only the explicitly selected schema; never chooses a DSN
# Changed: 2026-10-10 UTC | RV-M1.2-001 | Initial versioned migration runner
# Contracts: docs/components/POSTGRES_LEDGER.md
# Tests: tests/test_postgres_ledger.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Checksum-verified runner for the PostgreSQL ledger's versioned SQL."""

import hashlib
import re
from pathlib import Path

import psycopg


MIGRATION_NAME = re.compile(r"^(\d{4}_[a-z0-9_]+)\.sql$")


class MigrationError(RuntimeError):
    """Raised when migration history is missing, inconsistent, or unsafe."""


def _files(directory):
    paths = []
    for path in Path(directory).iterdir():
        if path.is_symlink() or not path.is_file():
            raise MigrationError(f"migration directory contains a non-regular entry: {path.name}")
        match = MIGRATION_NAME.fullmatch(path.name)
        if not match:
            raise MigrationError(f"invalid migration filename: {path.name}")
        paths.append((match.group(1), path))
    paths.sort(key=lambda entry: entry[0])
    versions = [version for version, _ in paths]
    if len(versions) != len(set(versions)):
        raise MigrationError("duplicate migration version")
    return paths


def apply_migrations(dsn, *, schema="public", migrations_dir=None):
    """Apply each unseen migration atomically and reject applied-file drift."""
    if not schema or not schema[0].isalpha() or not schema.replace("_", "").isalnum():
        raise ValueError("invalid schema")
    directory = Path(migrations_dir) if migrations_dir else Path(__file__).with_name("migrations")
    migrations = _files(directory)
    applied = []
    with psycopg.connect(dsn, autocommit=True) as db:
        with db.cursor() as cur:
            cur.execute("SELECT set_config('search_path', %s, false)", (schema,))
        for version, path in migrations:
            sql = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with db.transaction():
                with db.cursor() as cur:
                    cur.execute("SELECT set_config('search_path', %s, false)", (schema,))
                    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                                (f"riverview-migrations:{schema}",))
                    cur.execute("SELECT to_regclass('schema_migrations') AS ledger")
                    if cur.fetchone()["ledger"] is not None:
                        cur.execute("SELECT checksum FROM schema_migrations WHERE version=%s",
                                    (version,))
                        existing = cur.fetchone()
                        if existing:
                            if existing["checksum"] != digest:
                                raise MigrationError(f"applied migration checksum mismatch: {version}")
                            continue
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations(version,checksum) VALUES(%s,%s)",
                        (version, digest))
                    applied.append(version)
    return applied
