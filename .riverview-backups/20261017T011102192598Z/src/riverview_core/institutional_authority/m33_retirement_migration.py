# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/m33_retirement_migration.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.2
# Purpose: Apply only the checksum-pinned M33 retirement event migration
# Execution Model: Explicit DBA operation under the local PostgreSQL administrator
# Observability: Redacted preflight/apply status; preserved rows and ACL snapshots
# Dependencies: PostgreSQL 16; Psycopg 3; authority migrations 0000-0009
# Authority: Fixed riverview_authority schema and migration 0009; no grants or registry writes
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Add fixed-scope guarded migration runner
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Allow only the single expected migration-ledger row count increase
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Keep CLI target fixed while supporting CI's disposable database identity
# Tests: tests/test_m33_retirement_migration.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Narrow checksum and prerequisite gate for authority migration 0009."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re

from psycopg import sql

MIGRATION_VERSION = "0009_worker_registration_retirement_event"
MIGRATION_FILE = MIGRATION_VERSION + ".sql"
EXPECTED_MIGRATION_SHA256 = (
    "0b5aa767a0209b22ec476721da02c47618443ee1b06e752aa1e416f6dbccaef6"
)
SCHEMA = "riverview_authority"
EXPECTED_VERSIONS = tuple(
    ["0000_authority_migration_ledger"] +
    [f"000{i}_{name}" for i, name in (
        (1, "institutional_authority"),
        (2, "exact_grant_authorization"),
        (3, "resident_office_state_api"),
        (4, "exact_principal_grant_authorization"),
        (5, "audited_model_rebinding"),
        (6, "authorized_implementation_successor"),
        (7, "audited_office_role_update"),
        (8, "resident_permission_profiles"),
    )]
)
BASE_EVENT_TYPES = frozenset({
    "steward_bootstrapped", "principal_created", "credential_issued",
    "credential_revoked", "authority_granted", "authority_revoked",
    "office_created", "occupant_created", "implementation_created",
    "office_binding_replaced", "office_state_updated",
    "office_model_implementation_changed", "office_role_updated",
})
RETIRED_EVENT_TYPES = BASE_EVENT_TYPES | {"worker_registration_retired"}
_EVENT_LITERAL = re.compile(r"'((?:[^']|'')*)'")
_MIGRATION_FILE_RE = re.compile(r"^(\d{4}_[a-z0-9_]+)\.sql$")


class RetirementMigrationError(RuntimeError):
    """A fixed migration prerequisite failed; the transaction made no change."""


def _migration_files(directory: Path) -> dict[str, Path]:
    try:
        entries = list(directory.iterdir())
    except OSError:
        raise RetirementMigrationError("migration_source_unavailable") from None
    found: dict[str, Path] = {}
    for path in entries:
        if path.is_symlink() or not path.is_file():
            raise RetirementMigrationError("migration_source_entry_invalid")
        match = _MIGRATION_FILE_RE.fullmatch(path.name)
        if not match or match.group(1) in found:
            raise RetirementMigrationError("migration_inventory_invalid")
        found[match.group(1)] = path
    expected = set(EXPECTED_VERSIONS) | {MIGRATION_VERSION}
    if set(found) != expected:
        raise RetirementMigrationError("unrelated_or_missing_migrations_present")
    return found


def _event_types(cur, schema: str) -> frozenset[str]:
    cur.execute(
        """SELECT pg_get_constraintdef(con.oid)
           FROM pg_catalog.pg_constraint con
           JOIN pg_catalog.pg_class rel ON rel.oid=con.conrelid
           JOIN pg_catalog.pg_namespace ns ON ns.oid=rel.relnamespace
           WHERE ns.nspname=%s AND rel.relname='institutional_authority_events'
             AND con.conname='institutional_authority_events_event_type_check'
             AND con.contype='c'""",
        (schema,),
    )
    rows = cur.fetchall()
    if len(rows) != 1:
        raise RetirementMigrationError("event_type_constraint_missing_or_ambiguous")
    definition = rows[0][0]
    return frozenset(value.replace("''", "'") for value in _EVENT_LITERAL.findall(definition))


def _schema_snapshot(cur, schema: str) -> tuple[tuple, tuple, tuple]:
    cur.execute(
        """SELECT nspowner,nspacl::text
           FROM pg_catalog.pg_namespace WHERE nspname=%s""",
        (schema,),
    )
    namespace = cur.fetchone()
    if namespace is None:
        raise RetirementMigrationError("authority_schema_missing")

    cur.execute(
        """SELECT relname,relkind,relowner,relacl::text
           FROM pg_catalog.pg_class c
           JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=%s AND c.relkind IN ('r','p','S','v','m','f')
           ORDER BY relname""",
        (schema,),
    )
    relations = tuple(tuple(row) for row in cur.fetchall())

    counts = []
    for name, kind, _owner, _acl in relations:
        if kind not in ("r", "p"):
            continue
        cur.execute(
            sql.SQL("SELECT count(*) FROM {}.{}").format(
                sql.Identifier(schema), sql.Identifier(name)
            )
        )
        counts.append((name, cur.fetchone()[0]))
    return tuple(namespace), relations, tuple(counts)


def _preflight(cur, directory: Path, schema: str = SCHEMA,
               expected_database: str = "riverview") -> tuple[Path, str, bool]:
    files = _migration_files(directory)
    migration_path = files[MIGRATION_VERSION]
    try:
        migration_bytes = migration_path.read_bytes()
    except OSError:
        raise RetirementMigrationError("migration_source_unavailable") from None
    migration_hash = hashlib.sha256(migration_bytes).hexdigest()
    if migration_hash != EXPECTED_MIGRATION_SHA256:
        raise RetirementMigrationError("migration_checksum_does_not_match_reviewed_source")

    cur.execute("SELECT current_database()")
    if cur.fetchone()[0] != expected_database:
        raise RetirementMigrationError("wrong_database")
    cur.execute("SELECT to_regnamespace(%s)", (schema,))
    if cur.fetchone()[0] is None:
        raise RetirementMigrationError("authority_schema_missing")
    cur.execute(
        sql.SQL("SELECT to_regclass({})").format(sql.Literal(schema + ".schema_migrations"))
    )
    if cur.fetchone()[0] is None:
        raise RetirementMigrationError("authority_migration_ledger_missing")
    cur.execute(
        sql.SQL("SELECT to_regclass({})").format(
            sql.Literal(schema + ".institutional_authority_events")
        )
    )
    if cur.fetchone()[0] is None:
        raise RetirementMigrationError("authority_event_table_missing")

    cur.execute("SELECT set_config('search_path',%s,true)", (schema,))
    cur.execute("SELECT version,checksum FROM schema_migrations ORDER BY version")
    ledger = dict(cur.fetchall())
    expected_prior = {}
    for version in EXPECTED_VERSIONS:
        expected_prior[version] = hashlib.sha256(files[version].read_bytes()).hexdigest()

    expected_unapplied = dict(expected_prior)
    expected_unapplied[MIGRATION_VERSION] = migration_hash
    expected_applied = dict(expected_unapplied)
    is_applied = MIGRATION_VERSION in ledger

    if is_applied:
        if ledger != expected_applied:
            raise RetirementMigrationError("authority_ledger_has_unexpected_state")
        if _event_types(cur, schema) != RETIRED_EVENT_TYPES:
            raise RetirementMigrationError("applied_migration_postcondition_mismatch")
    else:
        if ledger != expected_prior:
            raise RetirementMigrationError("prior_migrations_missing_or_unrelated_pending")
        if _event_types(cur, schema) != BASE_EVENT_TYPES:
            raise RetirementMigrationError("event_type_constraint_prerequisite_mismatch")
    return migration_path, migration_hash, is_applied


def apply_m33_retirement_migration(connection, migration_directory: Path,
                                   *, schema: str = SCHEMA,
                                   expected_database: str = "riverview") -> dict:
    """Atomically apply only 0009 after exact source, chain, and schema checks."""
    directory = Path(migration_directory)
    try:
        with connection.transaction():
            with connection.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                            ("riverview-migrations:" + schema,))
                migration_path, migration_hash, is_applied = _preflight(
                    cur, directory, schema, expected_database
                )
                if is_applied:
                    return {"status": "ALREADY_APPLIED", "version": MIGRATION_VERSION,
                            "checksum": migration_hash}

                before = _schema_snapshot(cur, schema)
                cur.execute(
                    "SELECT set_config('search_path',%s,true)", (schema,)
                )
                migration_sql = migration_path.read_text(encoding="utf-8")
                cur.execute(migration_sql, prepare=False)
                cur.execute(
                    "INSERT INTO schema_migrations(version,checksum) VALUES(%s,%s)",
                    (MIGRATION_VERSION, migration_hash),
                )
                if _event_types(cur, schema) != RETIRED_EVENT_TYPES:
                    raise RetirementMigrationError("event_type_constraint_postcondition_failed")
                after = _schema_snapshot(cur, schema)
                # The only expected authority row change is the checksum-ledger
                # record for this migration. The event constraint is DDL and
                # does not alter event data or ACLs.
                before_namespace, before_relations, before_counts = before
                after_namespace, after_relations, after_counts = after
                before_data = dict(before_counts)
                after_data = dict(after_counts)
                ledger = "schema_migrations"
                expected_after_data = dict(before_data)
                expected_after_data[ledger] = expected_after_data.get(ledger, 0) + 1
                if (before_namespace != after_namespace or
                        before_relations != after_relations or
                        after_data != expected_after_data):
                    raise RetirementMigrationError("authority_data_or_permissions_changed")
        return {"status": "APPLIED", "version": MIGRATION_VERSION,
                "checksum": EXPECTED_MIGRATION_SHA256,
                "authority_data_and_permissions": "PRESERVED"}
    except RetirementMigrationError:
        raise
    except Exception as exc:
        # Avoid returning a driver message that could include connection details.
        raise RetirementMigrationError(type(exc).__name__) from None


def check_m33_retirement_migration(connection, migration_directory: Path,
                                   *, schema: str = SCHEMA,
                                   expected_database: str = "riverview") -> dict:
    """Read-only prerequisite check; does not acquire a writer lock or apply DDL."""
    try:
        with connection.transaction():
            with connection.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                _path, checksum, is_applied = _preflight(
                    cur, Path(migration_directory), schema, expected_database
                )
        return {"status": "READY" if not is_applied else "ALREADY_APPLIED",
                "version": MIGRATION_VERSION, "checksum": checksum}
    except RetirementMigrationError:
        raise
    except Exception as exc:
        raise RetirementMigrationError(type(exc).__name__) from None
