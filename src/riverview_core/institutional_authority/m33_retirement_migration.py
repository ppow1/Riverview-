# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/m33_retirement_migration.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.2.0
# Purpose: Apply M33 migrations with an atomic resident-profile runtime boundary
# Execution Model: Explicit DBA transaction including migration and ACL postconditions
# Observability: Redacted preflight/apply status; preserved rows and ACL snapshots
# Dependencies: PostgreSQL 16; Psycopg 3; authority migrations 0000-0009
# Authority: Fixed riverview_authority schema and migrations 0008/0009; no grants or registry writes
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Add fixed-scope guarded migration runner
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Allow only the single expected migration-ledger row count increase
# Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Keep CLI target fixed while supporting CI's disposable database identity
# Changed: 2026-10-17 UTC | RV-M33-MIGRATION-CHAIN-0008-0009 | Add fail-closed single-migration 0008 prerequisite mode
# Changed: 2026-10-17 UTC | M33-0008-ATOMIC-RUNTIME-ACL | Provision and verify the approved profile function boundary in the 0008 transaction
# Tests: tests/test_m33_retirement_migration.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Narrow checksum and prerequisite gates for authority migrations 0008-0009."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re

from psycopg import sql
from .db_boundary import BoundaryPreflightError, provision_authority_boundary

MIGRATION_VERSION = "0009_worker_registration_retirement_event"
MIGRATION_FILE = MIGRATION_VERSION + ".sql"
PREREQUISITE_VERSION = "0008_resident_permission_profiles"
PREREQUISITE_FILE = PREREQUISITE_VERSION + ".sql"
EXPECTED_PREREQUISITE_SHA256 = (
    "570c7aeb16fca04c64c4e010f1534d0efebe92628ddacd8f05f6eb1eda12d339"
)
EXPECTED_MIGRATION_SHA256 = (
    "0b5aa767a0209b22ec476721da02c47618443ee1b06e752aa1e416f6dbccaef6"
)
SCHEMA = "riverview_authority"
RUNTIME_ROLE = "riverview_core"
MANAGER_ROLE = "riverview_authority_manager"
OWNER_ROLE = "riverview_authority_owner"
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
PROFILE_TABLE_COUNTS = {
    "capability_catalog": 18,
    "resource_catalog": 11,
    "capability_resources": 26,
    "resident_permission_tiers": 4,
    "resident_permission_profiles": 0,
    "resident_permission_profile_drafts": 0,
    "resident_permission_tier_rules": 50,
    "resident_permission_rules": 0,
    "resident_permission_events": 0,
}
PROFILE_FUNCTION_SIGNATURES = {
    "list_resident_permission_profiles": "p_actor text",
    "save_resident_permission_profile": "p_actor text, p_resident text, p_expected_revision bigint, p_profile jsonb",
    "approve_resident_permission_profile": "p_actor text, p_resident text, p_expected_revision bigint",
    "revoke_resident_permission_profile": "p_actor text, p_resident text, p_expected_revision bigint",
    "evaluate_resident_permission": "p_resident text, p_action text, p_resource text, p_access_level text, p_classification text, p_export boolean",
}


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


def _verify_0008_postcondition(cur, schema: str, runtime_role: str = RUNTIME_ROLE,
                              manager_role: str = MANAGER_ROLE,
                              owner_role: str = OWNER_ROLE) -> None:
    """Reject partial or altered profile migration state without returning row data."""
    tables = set(PROFILE_TABLE_COUNTS) | {"schema_migrations"}
    cur.execute(
        """SELECT c.relname,c.relkind,pg_get_userbyid(c.relowner)
           FROM pg_catalog.pg_class c
           JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=%s AND c.relkind IN ('r','p','S','v','m','f')""",
        (schema,),
    )
    observed_relations = {row[0] for row in cur.fetchall()}
    if not tables.issubset(observed_relations):
        raise RetirementMigrationError("resident_permission_objects_missing")

    for table, expected_count in PROFILE_TABLE_COUNTS.items():
        cur.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(
            sql.Identifier(schema), sql.Identifier(table)))
        if cur.fetchone()[0] != expected_count:
            raise RetirementMigrationError("resident_permission_seed_state_mismatch")

    cur.execute("SELECT rolname,oid FROM pg_catalog.pg_roles WHERE rolname=ANY(%s)",
                ([runtime_role, manager_role, owner_role],))
    role_oids = {name: oid for name, oid in cur.fetchall()}
    if set(role_oids) != {runtime_role, manager_role, owner_role}:
        raise RetirementMigrationError("profile_boundary_roles_missing")

    cur.execute(
        """SELECT has_schema_privilege(%s::name,n.oid,'USAGE'),
                  has_schema_privilege(%s::name,n.oid,'CREATE'),
                  has_schema_privilege(%s::name,n.oid,'USAGE'),
                  has_schema_privilege(%s::name,n.oid,'CREATE'),
                  has_schema_privilege(%s::name,n.oid,'USAGE'),
                  has_schema_privilege(%s::name,n.oid,'CREATE'),
                  count(*) FILTER (WHERE a.grantee=0 OR
                    a.grantee NOT IN (%s,%s,%s,n.nspowner) OR
                    (a.grantee<>n.nspowner AND a.privilege_type<>'USAGE'))
           FROM pg_catalog.pg_namespace n
           LEFT JOIN LATERAL aclexplode(COALESCE(n.nspacl,acldefault('n',n.nspowner))) a ON true
           WHERE n.nspname=%s
           GROUP BY n.nspowner,n.oid""",
        (runtime_role, runtime_role, manager_role, manager_role,
         owner_role, owner_role, role_oids[runtime_role],
         role_oids[manager_role], role_oids[owner_role], schema),
    )
    schema_boundary = cur.fetchone()
    if (schema_boundary is None or not schema_boundary[0] or schema_boundary[1]
            or not schema_boundary[2] or schema_boundary[3]
            or not schema_boundary[4] or schema_boundary[5]
            or schema_boundary[6]):
        raise RetirementMigrationError("profile_schema_boundary_mismatch")

    cur.execute(
        """SELECT count(*) FROM pg_catalog.pg_class c
           JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
           CROSS JOIN LATERAL aclexplode(
             COALESCE(c.relacl,acldefault('r',c.relowner))) a
           WHERE n.nspname=%s AND c.relname=ANY(%s) AND
             (a.grantee=0 OR a.grantee NOT IN (%s,%s,c.relowner) OR
              (a.grantee=%s AND a.privilege_type NOT IN ('SELECT','INSERT','UPDATE','DELETE')))
        """,
        (schema, list(PROFILE_TABLE_COUNTS), role_oids[manager_role],
         role_oids[owner_role], role_oids[manager_role]),
    )
    if cur.fetchone()[0] != 0:
        raise RetirementMigrationError("resident_permission_table_acl_unexpected")
    cur.execute(
        """SELECT count(*) FROM pg_catalog.pg_class c
           JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=%s AND c.relname=ANY(%s) AND
             (has_table_privilege(%s::name,c.oid,'SELECT') OR
              has_table_privilege(%s::name,c.oid,'INSERT') OR
              has_table_privilege(%s::name,c.oid,'UPDATE') OR
              has_table_privilege(%s::name,c.oid,'DELETE') OR
              NOT has_table_privilege(%s::name,c.oid,'SELECT') OR
              NOT has_table_privilege(%s::name,c.oid,'INSERT') OR
              NOT has_table_privilege(%s::name,c.oid,'UPDATE') OR
              NOT has_table_privilege(%s::name,c.oid,'DELETE'))""",
        (schema, list(PROFILE_TABLE_COUNTS), runtime_role, runtime_role,
         runtime_role, runtime_role, manager_role, manager_role,
         manager_role, manager_role),
    )
    if cur.fetchone()[0] != 0:
        raise RetirementMigrationError("resident_permission_table_privilege_mismatch")

    cur.execute(
        """SELECT p.proname,pg_get_function_identity_arguments(p.oid),
                  pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,
                  EXISTS(SELECT 1 FROM aclexplode(
                      COALESCE(p.proacl,acldefault('f',p.proowner))) a
                         WHERE a.grantee=0 AND a.privilege_type='EXECUTE')
           FROM pg_catalog.pg_proc p
           JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
           WHERE n.nspname=%s""",
        (schema,),
    )
    functions = cur.fetchall()
    observed = {(row[0], row[1]) for row in functions}
    expected = set(PROFILE_FUNCTION_SIGNATURES.items()) | {
        ("reject_resident_permission_event_mutation", "")
    }
    if not expected.issubset(observed):
        raise RetirementMigrationError("resident_permission_functions_missing")
    for name, signature in PROFILE_FUNCTION_SIGNATURES.items():
        rows = [row for row in functions if (row[0], row[1]) == (name, signature)]
        if len(rows) != 1:
            raise RetirementMigrationError("resident_permission_function_ambiguous")
        _name, _arguments, function_owner, security_definer, config, public_execute = rows[0]
        expected_path = f"search_path={schema}, pg_catalog, pg_temp"
        if (function_owner != owner_role or not security_definer or not config
                or expected_path not in config or public_execute):
            raise RetirementMigrationError("resident_permission_function_boundary_mismatch")
        cur.execute(
            """SELECT has_function_privilege(%s::name,p.oid,'EXECUTE'),
                      has_function_privilege(%s::name,p.oid,'EXECUTE'),
                      count(*) FILTER (WHERE a.grantee=0 OR
                        a.grantee NOT IN (%s,%s,p.proowner) OR
                        (a.grantee=%s AND a.privilege_type<>'EXECUTE'))
               FROM pg_catalog.pg_proc p
               JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
               LEFT JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a ON true
               WHERE n.nspname=%s AND p.proname=%s
                 AND pg_get_function_identity_arguments(p.oid)=%s
               GROUP BY p.oid""",
            (runtime_role, manager_role, role_oids[runtime_role],
             role_oids[owner_role], role_oids[runtime_role], schema, name, signature),
        )
        function_acl = cur.fetchone()
        if (function_acl is None or not function_acl[0] or function_acl[1]
                or function_acl[2]):
            raise RetirementMigrationError("resident_permission_function_acl_unexpected")
    cur.execute(
        """SELECT count(*) FROM pg_catalog.pg_trigger t
           JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid
           JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=%s AND c.relname='resident_permission_events'
             AND t.tgname='resident_permission_events_append_only' AND NOT t.tgisinternal""",
        (schema,),
    )
    if cur.fetchone()[0] != 1:
        raise RetirementMigrationError("resident_permission_append_only_trigger_missing")

    cur.execute(
        """SELECT indexname FROM pg_catalog.pg_indexes
           WHERE schemaname=%s AND indexname IN
             ('resident_permission_rule_lookup_idx','resident_permission_events_subject_idx')""",
        (schema,),
    )
    if {row[0] for row in cur.fetchall()} != {
        "resident_permission_rule_lookup_idx",
        "resident_permission_events_subject_idx",
    }:
        raise RetirementMigrationError("resident_permission_indexes_missing")


def _preflight_0008(cur, directory: Path, schema: str,
                    expected_database: str, runtime_role: str = RUNTIME_ROLE,
                    manager_role: str = MANAGER_ROLE,
                    owner_role: str = OWNER_ROLE) -> tuple[Path, str, bool]:
    files = _migration_files(directory)
    migration_path = files[PREREQUISITE_VERSION]
    try:
        digest = hashlib.sha256(migration_path.read_bytes()).hexdigest()
    except OSError:
        raise RetirementMigrationError("migration_source_unavailable") from None
    if digest != EXPECTED_PREREQUISITE_SHA256:
        raise RetirementMigrationError("prerequisite_checksum_does_not_match_reviewed_source")
    later_digest = hashlib.sha256(files[MIGRATION_VERSION].read_bytes()).hexdigest()
    if later_digest != EXPECTED_MIGRATION_SHA256:
        raise RetirementMigrationError("dependent_migration_checksum_does_not_match_reviewed_source")
    cur.execute("SELECT current_database()")
    if cur.fetchone()[0] != expected_database:
        raise RetirementMigrationError("wrong_database")
    cur.execute("SELECT to_regnamespace(%s)", (schema,))
    if cur.fetchone()[0] is None:
        raise RetirementMigrationError("authority_schema_missing")
    cur.execute(sql.SQL("SELECT to_regclass({})").format(
        sql.Literal(schema + ".schema_migrations")))
    if cur.fetchone()[0] is None:
        raise RetirementMigrationError("authority_migration_ledger_missing")
    cur.execute(sql.SQL("SELECT to_regclass({})").format(
        sql.Literal(schema + ".institutional_authority_events")))
    if cur.fetchone()[0] is None:
        raise RetirementMigrationError("authority_event_table_missing")
    cur.execute("SELECT set_config('search_path',%s,true)", (schema,))
    cur.execute("SELECT version,checksum FROM schema_migrations ORDER BY version")
    ledger = dict(cur.fetchall())
    prior_versions = EXPECTED_VERSIONS[:-1]
    expected_prior = {
        version: hashlib.sha256(files[version].read_bytes()).hexdigest()
        for version in prior_versions
    }
    expected_after_0008 = dict(expected_prior)
    expected_after_0008[PREREQUISITE_VERSION] = digest
    expected_after_0009 = dict(expected_after_0008)
    expected_after_0009[MIGRATION_VERSION] = EXPECTED_MIGRATION_SHA256

    if ledger == expected_prior:
        if _event_types(cur, schema) != BASE_EVENT_TYPES:
            raise RetirementMigrationError("event_type_constraint_prerequisite_mismatch")
        cur.execute(
            """SELECT count(*) FROM pg_catalog.pg_class c
               JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname=%s AND c.relname=ANY(%s)""",
            (schema, list(PROFILE_TABLE_COUNTS)),
        )
        if cur.fetchone()[0] != 0:
            raise RetirementMigrationError("resident_permission_objects_exist_without_ledger")
        cur.execute(
            """SELECT count(*) FROM pg_catalog.pg_proc p
               JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
               WHERE n.nspname=%s AND p.proname=ANY(%s)""",
            (schema, list(PROFILE_FUNCTION_SIGNATURES) +
             ["reject_resident_permission_event_mutation"]),
        )
        if cur.fetchone()[0] != 0:
            raise RetirementMigrationError("resident_permission_functions_exist_without_ledger")
        return migration_path, digest, False
    if ledger == expected_after_0008:
        if _event_types(cur, schema) != BASE_EVENT_TYPES:
            raise RetirementMigrationError("prerequisite_event_constraint_mismatch")
        _verify_0008_postcondition(cur, schema, runtime_role, manager_role, owner_role)
        return migration_path, digest, True
    if ledger == expected_after_0009:
        if _event_types(cur, schema) != RETIRED_EVENT_TYPES:
            raise RetirementMigrationError("applied_migration_postcondition_mismatch")
        _verify_0008_postcondition(cur, schema, runtime_role, manager_role, owner_role)
        return migration_path, digest, True
    raise RetirementMigrationError("prior_migrations_missing_or_unrelated_pending")


def _schema_snapshot(cur, schema: str) -> tuple[tuple, tuple, tuple]:
    cur.execute(
        """SELECT nspowner,
                  (SELECT string_agg(a.grantee::text||':'||a.privilege_type||':'||
                                     a.is_grantable::text||':'||a.grantor::text,','
                                     ORDER BY a.grantee,a.privilege_type,a.is_grantable,a.grantor)
                   FROM aclexplode(COALESCE(n.nspacl,acldefault('n',n.nspowner))) a)
           FROM pg_catalog.pg_namespace n WHERE n.nspname=%s""",
        (schema,),
    )
    namespace = cur.fetchone()
    if namespace is None:
        raise RetirementMigrationError("authority_schema_missing")

    cur.execute(
        """SELECT c.relname,c.relkind,pg_get_userbyid(c.relowner),
                  (SELECT string_agg(a.grantee::text||':'||a.privilege_type||':'||
                                     a.is_grantable::text||':'||a.grantor::text,','
                                     ORDER BY a.grantee,a.privilege_type,a.is_grantable,a.grantor)
                   FROM aclexplode(COALESCE(c.relacl,acldefault(
                     CASE WHEN c.relkind='S' THEN 's'::"char" ELSE 'r'::"char" END,
                     c.relowner))) a)
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


def _function_snapshot(cur, schema: str) -> tuple[tuple, ...]:
    cur.execute(
        """SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.proowner,
                  (SELECT string_agg(a.grantee::text||':'||a.privilege_type||':'||
                                     a.is_grantable::text||':'||a.grantor::text,','
                                     ORDER BY a.grantee,a.privilege_type,a.is_grantable,a.grantor)
                   FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a),
                  p.proconfig,p.prosecdef,p.prorettype
           FROM pg_catalog.pg_proc p
           JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
           WHERE n.nspname=%s ORDER BY p.proname,2""",
        (schema,),
    )
    return tuple(tuple(row) for row in cur.fetchall())


def _validate_0008_changes(before, after, before_functions, after_functions,
                           schema: str, expected_owner: str,
                           expected_owner_oid: int) -> None:
    before_namespace, before_relations, before_counts = before
    after_namespace, after_relations, after_counts = after
    profile_tables = set(PROFILE_TABLE_COUNTS)
    old_relations = {row[0]: row for row in before_relations}
    new_relations = {row[0]: row for row in after_relations}
    if before_namespace[0] != after_namespace[0]:
        raise RetirementMigrationError("authority_schema_owner_changed")
    if any(new_relations.get(name) != row for name, row in old_relations.items()):
        raise RetirementMigrationError("preexisting_relation_owner_or_acl_changed")
    added_relations = set(new_relations) - set(old_relations)
    if added_relations != profile_tables:
        raise RetirementMigrationError("unexpected_resident_permission_relations")
    if any(new_relations[name][2] != expected_owner for name in profile_tables):
        raise RetirementMigrationError("resident_permission_owner_mismatch")

    before_counts_map, after_counts_map = dict(before_counts), dict(after_counts)
    expected_counts = dict(before_counts_map)
    expected_counts["schema_migrations"] += 1
    expected_counts.update(PROFILE_TABLE_COUNTS)
    if after_counts_map != expected_counts:
        raise RetirementMigrationError("authority_data_or_seed_counts_changed")

    old_functions = {row[:2]: row for row in before_functions}
    new_functions = {row[:2]: row for row in after_functions}
    if any(new_functions.get(key) != row for key, row in old_functions.items()):
        raise RetirementMigrationError("preexisting_authority_function_changed")
    added_functions = set(new_functions) - set(old_functions)
    expected_functions = set(PROFILE_FUNCTION_SIGNATURES.items()) | {
        ("reject_resident_permission_event_mutation", "")
    }
    if added_functions != expected_functions:
        raise RetirementMigrationError("unexpected_resident_permission_functions")
    if any(new_functions[key][2] != expected_owner_oid for key in added_functions):
        raise RetirementMigrationError("resident_permission_function_owner_mismatch")


def _profile_boundary(connection, *, schema: str, apply: bool,
                      runtime_role: str = RUNTIME_ROLE,
                      manager_role: str = MANAGER_ROLE,
                      owner_role: str = OWNER_ROLE) -> dict:
    """Apply or verify the established least-privilege boundary for 0008 objects."""
    try:
        report = provision_authority_boundary(
            connection, schema=schema, runtime_role=runtime_role,
            manager_role=manager_role, owner_role=owner_role, apply=apply,
        )
    except BoundaryPreflightError:
        raise RetirementMigrationError("profile_runtime_boundary_prerequisite_failed") from None
    if apply:
        if report.get("status") != "APPLIED":
            raise RetirementMigrationError("profile_runtime_boundary_apply_failed")
    elif report.get("apply_required") is not False:
        raise RetirementMigrationError("profile_runtime_boundary_not_ready")
    return report


def apply_m33_retirement_prerequisite(connection, migration_directory: Path,
                                      *, schema: str = SCHEMA,
                                      expected_database: str = "riverview",
                                      runtime_role: str = RUNTIME_ROLE,
                                      manager_role: str = MANAGER_ROLE,
                                      owner_role: str = OWNER_ROLE) -> dict:
    """Apply only 0008 after exact predecessor, source, and effect checks."""
    directory = Path(migration_directory)
    try:
        with connection.transaction():
            with connection.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                            ("riverview-migrations:" + schema,))
                migration_path, digest, is_applied = _preflight_0008(
                    cur, directory, schema, expected_database,
                    runtime_role, manager_role, owner_role
                )
                if is_applied:
                    _profile_boundary(connection, schema=schema, apply=False,
                                      runtime_role=runtime_role, manager_role=manager_role,
                                      owner_role=owner_role)
                    return {"status": "ALREADY_APPLIED",
                            "version": PREREQUISITE_VERSION, "checksum": digest}

                before = _schema_snapshot(cur, schema)
                before_functions = _function_snapshot(cur, schema)
                cur.execute("SELECT set_config('search_path',%s,true)", (schema,))
                cur.execute(migration_path.read_text(encoding="utf-8"), prepare=False)
                cur.execute(
                    "INSERT INTO schema_migrations(version,checksum) VALUES(%s,%s)",
                    (PREREQUISITE_VERSION, digest),
                )
                # Migration DDL, ledger insertion, ownership transfer and the
                # exact runtime ACL become visible together at the outer commit.
                _profile_boundary(connection, schema=schema, apply=True,
                                  runtime_role=runtime_role, manager_role=manager_role,
                                  owner_role=owner_role)
                _profile_boundary(connection, schema=schema, apply=False,
                                  runtime_role=runtime_role, manager_role=manager_role,
                                  owner_role=owner_role)
                cur.execute("SELECT oid FROM pg_catalog.pg_roles WHERE rolname=%s",
                            (owner_role,))
                owner_oid = cur.fetchone()
                if owner_oid is None:
                    raise RetirementMigrationError("authority_owner_role_missing")
                owner_oid = owner_oid[0]
                owner = owner_role
                _verify_0008_postcondition(cur, schema, runtime_role, manager_role, owner_role)
                if _event_types(cur, schema) != BASE_EVENT_TYPES:
                    raise RetirementMigrationError("prerequisite_event_constraint_changed")
                after = _schema_snapshot(cur, schema)
                after_functions = _function_snapshot(cur, schema)
                _validate_0008_changes(
                    before, after, before_functions, after_functions,
                    schema, owner, owner_oid,
                )
        return {"status": "APPLIED", "version": PREREQUISITE_VERSION,
                "checksum": EXPECTED_PREREQUISITE_SHA256,
                "preexisting_authority_data_and_permissions": "PRESERVED",
                "profile_records_created": 0,
                "runtime_function_acl": "five profile functions only; PUBLIC denied"}
    except RetirementMigrationError:
        raise
    except Exception as exc:
        raise RetirementMigrationError(type(exc).__name__) from None


def check_m33_retirement_prerequisite(connection, migration_directory: Path,
                                      *, schema: str = SCHEMA,
                                      expected_database: str = "riverview",
                                      runtime_role: str = RUNTIME_ROLE,
                                      manager_role: str = MANAGER_ROLE,
                                      owner_role: str = OWNER_ROLE) -> dict:
    """Read-only preflight for 0008; no DDL, grants, or data writes."""
    try:
        with connection.transaction():
            with connection.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                _path, digest, is_applied = _preflight_0008(
                    cur, Path(migration_directory), schema, expected_database,
                    runtime_role, manager_role, owner_role
                )
                if is_applied:
                    _profile_boundary(connection, schema=schema, apply=False,
                                      runtime_role=runtime_role, manager_role=manager_role,
                                      owner_role=owner_role)
        return {"status": "ALREADY_APPLIED" if is_applied else "READY",
                "version": PREREQUISITE_VERSION, "checksum": digest}
    except RetirementMigrationError:
        raise
    except Exception as exc:
        raise RetirementMigrationError(type(exc).__name__) from None


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
                                   expected_database: str = "riverview",
                                   runtime_role: str = RUNTIME_ROLE,
                                   manager_role: str = MANAGER_ROLE,
                                   owner_role: str = OWNER_ROLE) -> dict:
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
                _profile_boundary(connection, schema=schema, apply=False,
                                  runtime_role=runtime_role, manager_role=manager_role,
                                  owner_role=owner_role)
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
                                   expected_database: str = "riverview",
                                   runtime_role: str = RUNTIME_ROLE,
                                   manager_role: str = MANAGER_ROLE,
                                   owner_role: str = OWNER_ROLE) -> dict:
    """Read-only prerequisite check; does not acquire a writer lock or apply DDL."""
    try:
        with connection.transaction():
            with connection.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                _path, checksum, is_applied = _preflight(
                    cur, Path(migration_directory), schema, expected_database
                )
                _profile_boundary(connection, schema=schema, apply=False,
                                  runtime_role=runtime_role, manager_role=manager_role,
                                  owner_role=owner_role)
        return {"status": "READY" if not is_applied else "ALREADY_APPLIED",
                "version": MIGRATION_VERSION, "checksum": checksum}
    except RetirementMigrationError:
        raise
    except Exception as exc:
        raise RetirementMigrationError(type(exc).__name__) from None
