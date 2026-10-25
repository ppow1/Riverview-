# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/postgres_migrations.py
# Component: POSTGRES-LEDGER
# Revision: 1.0.3
# Changed: 2026-10-25 UTC | C3-AUTOMATIC-CAPABILITY-REGISTRATION | Reconcile bounded release declarations after authority migration runs, including no-op runs
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
import json
import re
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


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
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as db:
        with db.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s) AS present",
                        (schema,))
            if not cur.fetchone()["present"]:
                raise MigrationError(f"target schema does not exist: {schema}")
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
    # The institutional capability declaration files are part of the same
    # immutable release as their executors. Reconcile them after schema
    # migrations on every authority deployment, even when the migration ledger
    # is already current, so newly shipped declarations do not require a
    # separate Steward/C3 follow-up.
    declarations_dir = directory.parent / "capability_declarations"
    declaration_paths = []
    if declarations_dir.is_symlink():
        raise MigrationError("capability declaration path is not a regular directory")
    if declarations_dir.exists():
        if not declarations_dir.is_dir():
            raise MigrationError("capability declaration path is not a regular directory")
        entries = sorted(declarations_dir.iterdir())
        if any(path.suffix != ".json" or path.is_symlink() or not path.is_file()
               for path in entries):
            raise MigrationError("capability declaration directory contains an unsupported entry")
        declaration_paths = entries
    if declaration_paths:
        if len(declaration_paths) > 512:
            raise MigrationError("too many capability declaration files")
        declarations = []
        total_bytes = 0
        for path in declaration_paths:
            size = path.stat(follow_symlinks=False).st_size
            total_bytes += size
            if size > 65536 or total_bytes > 8 * 1024 * 1024:
                raise MigrationError("capability declaration batch exceeds size limits")
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise MigrationError(f"invalid capability declaration: {path.name}") from exc
            if not isinstance(item, dict):
                raise MigrationError(f"invalid capability declaration: {path.name}")
            item["declaration_source"] = path.name
            declarations.append(item)
        source_commit = _source_commit(directory)
        with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as db:
            with db.transaction():
                with db.cursor() as cur:
                    cur.execute("SELECT set_config('search_path', %s, false)", (schema,))
                    cur.execute(
                        "SELECT reconcile_capability_declarations(%s::jsonb,%s)",
                        (json.dumps(declarations, sort_keys=True), source_commit))
    return applied


def _source_commit(migrations_dir):
    """Return package/source identity without making it an authorization input."""
    root = Path(migrations_dir).resolve().parents[3]
    packaged = root / "SOURCE_COMMIT"
    if packaged.is_file() and not packaged.is_symlink():
        value = packaged.read_text(encoding="ascii").strip()
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
            return value
    return "unpackaged"
