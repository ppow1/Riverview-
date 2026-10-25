# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/db_boundary.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.22
# Changed: 2026-10-24 UTC | RV-GRACE-CAPABILITY-REGISTRY-SEARCHPATH-COMPAT-20261024 | Validate SECURITY DEFINER functions against their exact pinned search-path policy.
# Changed: 2026-10-24 UTC | RV-GRACE-CAPABILITY-REGISTRY-BOUNDARY-ALLOWLIST-20261024 | Preserve the existing narrowly granted Luna and autonomy authority functions during boundary preflight.
# Changed: 2026-10-24 UTC | RV-GRACE-CAPABILITY-REGISTRY-BRIDGE-20261024 | Include the narrow catalog and caller-grant projections in the runtime function allowlist.
# Purpose: Separate authority relation ownership from the shared runtime role
# Execution Model: Explicit PostgreSQL DBA operation; dry-run by default
# Observability: Redacted JSON preflight and applied-relation report
# Dependencies: Python 3.10+; Psycopg 3; PostgreSQL 16
# Authority: Exact authority relation allowlist; no rows, credentials or unrelated objects changed
# Changed: 2026-10-11 UTC | RV-M4.1-BOUNDARY-FORMAT-FIX | Escape PostgreSQL format tokens for Psycopg parameter parsing
# Changed: 2026-10-11 UTC | RV-M4.1-BOUNDARY-VERIFY | Use catalog OIDs and explicit role casts in post-apply privilege verification
# Changed: 2026-10-11 UTC | RV-M4.1-SCHEMA-OWNER-GATE | Reject runtime/manager schema ownership or membership that can bypass object ownership
# Changed: 2026-10-11 UTC | RV-M4.1-LEAST-PRIVILEGE | Use dedicated schema, scoped manager DML grants, and deny manager DDL/owner inheritance
# Changed: 2026-10-11 UTC | RV-M4.1-NOINHERIT-MANAGER | Require the manager LOGIN to inherit no PostgreSQL role memberships
# Changed: 2026-10-11 UTC | RV-M4.1-OWNER-SCHEMA-USAGE | Grant protected table owner schema USAGE so FK checks work without DDL access
# Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Manage the linked-principal exact-grant function under the same ACL boundary
# Changed: 2026-10-11 UTC | RV-M4.1-APPLY-REQUIRED-DRY-RUN | Detect incomplete schema/table ACLs during read-only preflight
# Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT | Expose only an owner-controlled exact-grant check to the runtime role
# Changed: 2026-10-11 UTC | RV-M4.1-RUNTIME-OFFICE-API | Expose only exact-grant office snapshot/CAS functions to the runtime role
# Changed: 2026-10-11 UTC | RV-M4.1-OFFICE-FUNCTION-DRIFT | Detect and repair office function ACL/security drift in preflight
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Allow only the restricted audited-upgrade decision function to runtime
# Changed: 2026-10-14 UTC | RV-RESIDENT-PERMISSIONS-001 | Extend protected ownership and function-only ACL to resident profiles
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_institutional_authority_boundary.py
# History: .riverview-backups/manifest.jsonl
# =============================================================================
"""Apply an explicit, additive PostgreSQL privilege boundary to M4.1 tables."""

from __future__ import annotations

import re

from psycopg import sql
from psycopg.rows import dict_row


AUTHORITY_TABLES = (
    "institutional_offices",
    "institutional_principals",
    "principal_credentials",
    "authority_grants",
    "resident_occupants",
    "resident_implementations",
    "office_bindings",
    "office_runtime_state",
    "institutional_authority_events",
    "capability_catalog", "resource_catalog", "capability_resources",
    "resident_permission_tiers", "resident_permission_profiles",
    "resident_permission_profile_drafts", "resident_permission_tier_rules",
    "resident_permission_rules",
    "resident_permission_events",
)
EVENT_TRIGGER_FUNCTION = "reject_institutional_authority_event_mutation"
PROFILE_EVENT_TRIGGER_FUNCTION = "reject_resident_permission_event_mutation"
APPEND_ONLY_TRIGGER_FUNCTIONS = (EVENT_TRIGGER_FUNCTION, PROFILE_EVENT_TRIGGER_FUNCTION)
AUTHORIZATION_FUNCTION = "authorize_exact_grant"
PRINCIPAL_AUTHORIZATION_FUNCTION = "authorize_exact_principal_grant"
PRINCIPAL_AUTHORIZATION_ARGUMENTS = "p_principal_id text, p_action text, p_scope_ref text"
RUNTIME_OFFICE_FUNCTIONS = {
    "read_authorized_office_state":
        "p_credential_sha256 bytea, p_office_id text",
    "write_authorized_office_state":
        "p_credential_sha256 bytea, p_office_id text, p_state jsonb, p_expected_revision bigint",
    "authorized_office_implementation_successor":
        "p_credential_sha256 bytea, p_office_id text, p_predecessor_id text, p_predecessor_revision text, p_successor_id text, p_successor_revision text, p_required_capability text",
}
RUNTIME_OFFICE_FUNCTION_SIGNATURES = {
    "read_authorized_office_state": "(bytea,text)",
    "write_authorized_office_state": "(bytea,text,jsonb,bigint)",
    "authorized_office_implementation_successor": "(bytea,text,text,text,text,text,text)",
}
RUNTIME_PERMISSION_FUNCTIONS = {
    "list_resident_permission_profiles": "p_actor text",
    "save_resident_permission_profile": "p_actor text, p_resident text, p_expected_revision bigint, p_profile jsonb",
    "approve_resident_permission_profile": "p_actor text, p_resident text, p_expected_revision bigint",
    "revoke_resident_permission_profile": "p_actor text, p_resident text, p_expected_revision bigint",
    "evaluate_resident_permission": "p_resident text, p_action text, p_resource text, p_access_level text, p_classification text, p_export boolean",
}
RUNTIME_PERMISSION_SIGNATURES = {
    "list_resident_permission_profiles": "(text)",
    "save_resident_permission_profile": "(text,text,bigint,jsonb)",
    "approve_resident_permission_profile": "(text,text,bigint)",
    "revoke_resident_permission_profile": "(text,text,bigint)",
    "evaluate_resident_permission": "(text,text,text,text,text,boolean)",
}
RUNTIME_PERMISSION_FUNCTIONS.update({
    "active_grace_luna_escalation_grant": "",
    "active_grace_autonomy_experiment_grant": "p_grant_id text, p_scope_ref text",
    "issue_grace_autonomy_experiment_grant": "p_actor_id text, p_grant_id text, p_scope_ref text, p_valid_until timestamp with time zone",
    "active_grace_supervisory_luna_grant": "p_grant_id text",
    "issue_grace_supervisory_luna_grant": "p_actor_id text, p_grant_id text, p_valid_until timestamp with time zone",
    "revoke_grace_supervisory_luna_grant": "p_actor_id text, p_grant_id text",
    "list_capability_registry": "",
    "list_capability_grants": "p_credential_sha256 bytea",
})
RUNTIME_PERMISSION_SEARCH_PATHS = {
    "active_grace_luna_escalation_grant": "search_path=pg_catalog, pg_temp",
    "active_grace_autonomy_experiment_grant": "search_path=pg_catalog, pg_temp",
    "issue_grace_autonomy_experiment_grant": "search_path=pg_catalog, pg_temp",
    "active_grace_supervisory_luna_grant": "search_path=pg_catalog, pg_temp",
    "issue_grace_supervisory_luna_grant": "search_path=pg_catalog, pg_temp",
    "revoke_grace_supervisory_luna_grant": "search_path=pg_catalog, pg_temp",
    "list_capability_registry": "search_path=pg_catalog, pg_temp",
    "list_capability_grants": "search_path=pg_catalog, pg_temp",
}
RUNTIME_PERMISSION_SIGNATURES.update({
    "active_grace_luna_escalation_grant": "()",
    "active_grace_autonomy_experiment_grant": "(text,text)",
    "issue_grace_autonomy_experiment_grant": "(text,text,text,timestamp with time zone)",
    "active_grace_supervisory_luna_grant": "(text)",
    "issue_grace_supervisory_luna_grant": "(text,text,timestamp with time zone)",
    "revoke_grace_supervisory_luna_grant": "(text,text)",
    "list_capability_registry": "()",
    "list_capability_grants": "(bytea)",
})
_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")


class BoundaryPreflightError(RuntimeError):
    """The exact selected target does not meet the safe ownership preflight."""


def _identifier(value, label):
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def provision_authority_boundary(connection, *, schema, runtime_role="riverview_core",
                                 manager_role="riverview_authority_manager",
                                 owner_role="riverview_authority_owner", apply=False):
    """Transfer only the versioned M4.1 relations to a NOLOGIN owner.

    The schema must not be owned by, or assumable by, the runtime or manager.
    A schema owner can drop objects despite not owning each relation. The
    schema owner therefore remains a distinct migration/DBA identity.

    ``manager_role`` must be separately provisioned as a non-superuser LOGIN
    with protected credential delivery. It receives only USAGE on the dedicated
    schema and SELECT/INSERT/UPDATE/DELETE on the nine allowlisted relations.
    The protected table owner also receives USAGE (never CREATE) on the schema,
    which PostgreSQL requires while enforcing foreign keys against its tables.
    It must not inherit the NOLOGIN table owner: owner membership would permit
    direct DDL and bypass append-only/registry controls. The ordinary runtime
    receives neither schema visibility nor table/function access. The selected
    schema may contain only these nine tables, the migration ledger, and the
    append-only trigger function.
    """
    schema = _identifier(schema, "schema")
    runtime_role = _identifier(runtime_role, "runtime role")
    manager_role = _identifier(manager_role, "authority manager role")
    owner_role = _identifier(owner_role, "authority owner role")
    if len({runtime_role, manager_role, owner_role}) != 3:
        raise ValueError("runtime, manager, and owner roles must be distinct")

    with connection.transaction():
        with connection.cursor(row_factory=dict_row) as cur:
            cur.execute("""SELECT current_user, r.rolsuper, r.rolcreaterole
                           FROM pg_roles r WHERE r.rolname=current_user""")
            administrator = cur.fetchone()
            if administrator is None or not administrator["rolsuper"]:
                raise BoundaryPreflightError("a PostgreSQL superuser connection is required")

            cur.execute("""SELECT pg_get_userbyid(n.nspowner) AS schema_owner
                           FROM pg_namespace n WHERE n.nspname=%s""", (schema,))
            schema_row = cur.fetchone()
            if schema_row is None:
                raise BoundaryPreflightError("selected schema does not exist")
            schema_owner = schema_row["schema_owner"]
            if schema_owner in {runtime_role, manager_role}:
                raise BoundaryPreflightError("runtime or manager must not own the selected schema")
            for candidate in (runtime_role, manager_role):
                cur.execute("SELECT pg_has_role(%s,%s,'MEMBER') AS member",
                            (candidate, schema_owner))
                if cur.fetchone()["member"]:
                    raise BoundaryPreflightError(
                        "runtime or manager can assume the selected schema owner role")

            cur.execute("""SELECT rolname,rolsuper,rolcreaterole,rolcreatedb,
                                  rolcanlogin,rolinherit,rolbypassrls
                           FROM pg_roles WHERE rolname=ANY(%s)""",
                        ([runtime_role, manager_role, owner_role],))
            roles = {row["rolname"]: row for row in cur.fetchall()}
            runtime = roles.get(runtime_role)
            manager = roles.get(manager_role)
            owner = roles.get(owner_role)
            if runtime is None:
                raise BoundaryPreflightError("runtime role does not exist")
            if (runtime["rolsuper"] or runtime["rolcreaterole"] or runtime["rolcreatedb"]
                    or runtime["rolbypassrls"]):
                raise BoundaryPreflightError("runtime role has a cluster-level privilege")
            if manager is None or not manager["rolcanlogin"]:
                raise BoundaryPreflightError("separately provisioned manager LOGIN role is required")
            if (manager["rolsuper"] or manager["rolcreaterole"] or manager["rolcreatedb"]
                    or manager["rolbypassrls"] or manager["rolinherit"]):
                raise BoundaryPreflightError("manager role must be a non-privileged NOINHERIT LOGIN")
            if owner is not None and (owner["rolcanlogin"] or owner["rolsuper"]
                                      or owner["rolcreaterole"] or owner["rolcreatedb"]
                                      or owner["rolbypassrls"]):
                raise BoundaryPreflightError("existing owner role is not a safe NOLOGIN role")
            if runtime_role == manager_role or runtime_role == owner_role or manager_role == owner_role:
                raise BoundaryPreflightError("role names must be distinct")

            if owner is not None:
                cur.execute("SELECT pg_has_role(%s,%s,'MEMBER') AS member",
                            (runtime_role, owner_role))
                if cur.fetchone()["member"]:
                    raise BoundaryPreflightError("runtime role already inherits or can assume the owner role")
            cur.execute("SELECT pg_has_role(%s,%s,'MEMBER') AS member",
                        (runtime_role, manager_role))
            if cur.fetchone()["member"]:
                raise BoundaryPreflightError("runtime role can assume the manager role")
            if owner is not None:
                cur.execute("SELECT pg_has_role(%s,%s,'MEMBER') AS member",
                            (manager_role, owner_role))
                if cur.fetchone()["member"]:
                    raise BoundaryPreflightError("manager role can assume the protected owner role")
            cur.execute("""SELECT parent.rolname FROM pg_auth_members m
                           JOIN pg_roles member ON member.oid=m.member
                           JOIN pg_roles parent ON parent.oid=m.roleid
                           WHERE member.rolname=%s""", (manager_role,))
            inherited_roles = sorted(row["rolname"] for row in cur.fetchall())
            if inherited_roles:
                raise BoundaryPreflightError("manager role has unapproved memberships")

            cur.execute("""SELECT c.relname, c.relkind FROM pg_class c
                           JOIN pg_namespace n ON n.oid=c.relnamespace
                           WHERE n.nspname=%s AND c.relkind IN ('r','p','v','m','S','f')""",
                        (schema,))
            allowed_objects = set(AUTHORITY_TABLES) | {"schema_migrations"}
            unexpected_objects = sorted(row["relname"] for row in cur.fetchall()
                                         if row["relname"] not in allowed_objects)
            if unexpected_objects:
                raise BoundaryPreflightError(
                    "selected schema contains non-authority objects: " + ",".join(unexpected_objects))
            cur.execute("""SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS arguments
                           FROM pg_proc p
                           JOIN pg_namespace n ON n.oid=p.pronamespace
                           WHERE n.nspname=%s AND NOT (p.proname=ANY(%s))""",
                        (schema, list(APPEND_ONLY_TRIGGER_FUNCTIONS)))
            function_rows = cur.fetchall()
            expected_auth_arguments = "p_credential_sha256 bytea, p_action text, p_scope_ref text"
            expected_functions = {
                (AUTHORIZATION_FUNCTION, expected_auth_arguments),
                (PRINCIPAL_AUTHORIZATION_FUNCTION, PRINCIPAL_AUTHORIZATION_ARGUMENTS),
                *RUNTIME_OFFICE_FUNCTIONS.items(),
                *RUNTIME_PERMISSION_FUNCTIONS.items(),
            }
            observed_functions = {(row["proname"], row["arguments"]) for row in function_rows}
            if observed_functions != expected_functions:
                unexpected_functions = sorted(name for name, _ in
                    observed_functions.symmetric_difference(expected_functions))
                raise BoundaryPreflightError(
                    "selected schema contains non-authority functions: " + ",".join(unexpected_functions))

            cur.execute("""SELECT tablename,tableowner FROM pg_tables
                           WHERE schemaname=%s AND tablename=ANY(%s)""",
                        (schema, list(AUTHORITY_TABLES)))
            tables = {row["tablename"]: row["tableowner"] for row in cur.fetchall()}
            missing = sorted(set(AUTHORITY_TABLES) - set(tables))
            if missing:
                raise BoundaryPreflightError("authority migration is incomplete: " + ",".join(missing))
            acceptable_owners = {runtime_role, owner_role, administrator["current_user"]}
            unexpected = sorted(name for name, table_owner in tables.items()
                                if table_owner not in acceptable_owners)
            if unexpected:
                raise BoundaryPreflightError("authority relation owner is outside the approved transition set")

            cur.execute("""SELECT p.proowner::regrole::text AS function_owner
                           FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                           WHERE n.nspname=%s AND p.proname=ANY(%s)
                             AND p.pronargs=0""",
                        (schema, list(APPEND_ONLY_TRIGGER_FUNCTIONS)))
            trigger_rows = cur.fetchall()
            if len(trigger_rows) != len(APPEND_ONLY_TRIGGER_FUNCTIONS):
                raise BoundaryPreflightError("append-only authority trigger function is missing")
            if any(row["function_owner"] not in acceptable_owners for row in trigger_rows):
                raise BoundaryPreflightError("authority trigger function owner is outside the approved transition set")

            cur.execute("""SELECT p.proowner::regrole::text AS function_owner,
                                  p.prosecdef AS security_definer,
                                  p.proconfig,
                                  has_function_privilege(%s::name,p.oid,'EXECUTE') AS runtime_execute,
                                  has_function_privilege(%s::name,p.oid,'EXECUTE') AS manager_execute
                           FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                           WHERE n.nspname=%s AND p.proname=%s AND p.pronargs=3
                             AND pg_get_function_identity_arguments(p.oid)=%s""",
                        (runtime_role, manager_role, schema, AUTHORIZATION_FUNCTION,
                         expected_auth_arguments))
            auth_functions = []
            for function_name, arguments in (
                    (AUTHORIZATION_FUNCTION, expected_auth_arguments),
                    (PRINCIPAL_AUTHORIZATION_FUNCTION, PRINCIPAL_AUTHORIZATION_ARGUMENTS)):
                cur.execute("""SELECT p.proowner::regrole::text AS function_owner,
                                      p.prosecdef AS security_definer,p.proconfig,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS runtime_execute,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS manager_execute
                               FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                               WHERE n.nspname=%s AND p.proname=%s
                                 AND pg_get_function_identity_arguments(p.oid)=%s""",
                            (runtime_role, manager_role, schema, function_name, arguments))
                function_row = cur.fetchone()
                if (function_row is None or not function_row["security_definer"]
                        or not function_row["proconfig"]
                        or "search_path=pg_catalog, pg_temp" not in function_row["proconfig"]
                        or function_row["function_owner"] not in acceptable_owners):
                    raise BoundaryPreflightError("exact-grant authorization function security configuration is unsafe")
                auth_functions.append(function_row)

            runtime_office_functions = []
            for function_name, arguments in RUNTIME_OFFICE_FUNCTIONS.items():
                cur.execute("""SELECT p.proowner::regrole::text AS function_owner,
                                      p.prosecdef AS security_definer,p.proconfig,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS runtime_execute,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS manager_execute
                               FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                               WHERE n.nspname=%s AND p.proname=%s
                                 AND pg_get_function_identity_arguments(p.oid)=%s""",
                            (runtime_role, manager_role, schema, function_name, arguments))
                function_row = cur.fetchone()
                if function_row is None or not function_row["security_definer"] or not function_row["proconfig"] \
                        or "search_path=pg_catalog, pg_temp" not in function_row["proconfig"] \
                        or function_row["function_owner"] not in acceptable_owners:
                    raise BoundaryPreflightError("resident office function security configuration is unsafe")
                runtime_office_functions.append(function_row)
            runtime_permission_functions = []
            for function_name, arguments in RUNTIME_PERMISSION_FUNCTIONS.items():
                cur.execute("""SELECT p.proowner::regrole::text AS function_owner,
                                      p.prosecdef AS security_definer,p.proconfig,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS runtime_execute,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS manager_execute
                               FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                               WHERE n.nspname=%s AND p.proname=%s
                                 AND pg_get_function_identity_arguments(p.oid)=%s""",
                            (runtime_role, manager_role, schema, function_name, arguments))
                function_row = cur.fetchone()
                expected_path = RUNTIME_PERMISSION_SEARCH_PATHS.get(
                    function_name, f"search_path={schema}, pg_catalog, pg_temp")
                if (function_row is None or not function_row["security_definer"]
                        or not function_row["proconfig"] or expected_path not in function_row["proconfig"]
                        or function_row["function_owner"] not in acceptable_owners):
                    raise BoundaryPreflightError("resident permission function security configuration is unsafe")
                runtime_permission_functions.append(function_row)

            cur.execute("""SELECT has_schema_privilege(%s::name,%s,'USAGE') AS runtime_usage,
                                  has_schema_privilege(%s::name,%s,'CREATE') AS runtime_create,
                                  has_schema_privilege(%s::name,%s,'USAGE') AS manager_usage,
                                  has_schema_privilege(%s::name,%s,'CREATE') AS manager_create,
                                  CASE WHEN to_regrole(%s) IS NULL THEN false
                                       ELSE has_schema_privilege(%s::name,%s,'USAGE') END AS owner_usage,
                                  CASE WHEN to_regrole(%s) IS NULL THEN false
                                       ELSE has_schema_privilege(%s::name,%s,'CREATE') END AS owner_create""",
                        (runtime_role, schema, runtime_role, schema,
                         manager_role, schema, manager_role, schema,
                         owner_role, owner_role, schema, owner_role, owner_role, schema))
            schema_access = cur.fetchone()
            cur.execute("""SELECT c.relname AS tablename,
                                  pg_get_userbyid(c.relowner) AS owner,
                                  has_table_privilege(%s::name,c.oid,'SELECT') AS runtime_select,
                                  has_table_privilege(%s::name,c.oid,'INSERT') AS runtime_insert,
                                  has_table_privilege(%s::name,c.oid,'UPDATE') AS runtime_update,
                                  has_table_privilege(%s::name,c.oid,'DELETE') AS runtime_delete,
                                  has_table_privilege(%s::name,c.oid,'SELECT') AS manager_select,
                                  has_table_privilege(%s::name,c.oid,'INSERT') AS manager_insert,
                                  has_table_privilege(%s::name,c.oid,'UPDATE') AS manager_update,
                                  has_table_privilege(%s::name,c.oid,'DELETE') AS manager_delete
                           FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                           WHERE n.nspname=%s AND c.relkind='r' AND c.relname=ANY(%s)""",
                        (runtime_role, runtime_role, runtime_role, runtime_role,
                         manager_role, manager_role, manager_role, manager_role,
                         schema, list(AUTHORITY_TABLES)))
            table_access = cur.fetchall()
            owner_dml = ("runtime_select", "runtime_insert", "runtime_update", "runtime_delete")
            manager_dml = ("manager_select", "manager_insert", "manager_update", "manager_delete")
            apply_required = (
                owner is None
                or len(table_access) != len(AUTHORITY_TABLES)
                or any(row["owner"] != owner_role for row in table_access)
                or any(row[name] for row in table_access for name in owner_dml)
                or any(not row[name] for row in table_access for name in manager_dml)
                or not schema_access["runtime_usage"] or schema_access["runtime_create"]
                or not schema_access["manager_usage"] or schema_access["manager_create"]
                or not schema_access["owner_usage"] or schema_access["owner_create"]
                or any(function["function_owner"] != owner_role
                       or not function["runtime_execute"] or function["manager_execute"]
                       for function in auth_functions)
                or any(function["function_owner"] != owner_role
                       or not function["security_definer"] or not function["proconfig"]
                       or "search_path=pg_catalog, pg_temp" not in function["proconfig"]
                       or not function["runtime_execute"] or function["manager_execute"]
                       for function in runtime_office_functions)
                or any(function["function_owner"] != owner_role
                       or not function["runtime_execute"] or function["manager_execute"]
                       for function in runtime_permission_functions)
            )

            if not apply:
                return {
                    "status": "PREFLIGHT_PASS",
                    "database_user": administrator["current_user"],
                    "schema": schema,
                    "runtime_role": runtime_role,
                    "manager_role": manager_role,
                    "owner_role": owner_role,
                    "authority_tables": sorted(tables),
                    "apply_required": apply_required,
                }

            if owner is None:
                cur.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS").format(
                    sql.Identifier(owner_role)))
            cur.execute(sql.SQL("REVOKE ALL ON SCHEMA {} FROM PUBLIC,{},{}").format(
                sql.Identifier(schema), sql.Identifier(runtime_role), sql.Identifier(owner_role)))
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(manager_role)))
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(owner_role)))
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(runtime_role)))
            for table_name in AUTHORITY_TABLES:
                cur.execute(sql.SQL("ALTER TABLE {}.{} OWNER TO {}").format(
                    sql.Identifier(schema), sql.Identifier(table_name), sql.Identifier(owner_role)))
                cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON TABLE {}.{} FROM PUBLIC,{}").format(
                    sql.Identifier(schema), sql.Identifier(table_name),
                    sql.SQL("{},{}").format(sql.Identifier(runtime_role), sql.Identifier(manager_role))))
                cur.execute(sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE {}.{} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(table_name), sql.Identifier(manager_role)))
            for trigger_function in APPEND_ONLY_TRIGGER_FUNCTIONS:
                cur.execute(sql.SQL("ALTER FUNCTION {}.{}() OWNER TO {}").format(
                    sql.Identifier(schema), sql.Identifier(trigger_function), sql.Identifier(owner_role)))
                cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON FUNCTION {}.{}() FROM PUBLIC,{},{}").format(
                    sql.Identifier(schema), sql.Identifier(trigger_function),
                    sql.Identifier(runtime_role), sql.Identifier(manager_role)))
            for function_name, signature in (
                    (AUTHORIZATION_FUNCTION, "(bytea,text,text)"),
                    (PRINCIPAL_AUTHORIZATION_FUNCTION, "(text,text,text)")):
                cur.execute(sql.SQL("ALTER FUNCTION {}.{}{} OWNER TO {}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(owner_role)))
                cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON FUNCTION {}.{}{} FROM PUBLIC,{},{}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(runtime_role), sql.Identifier(manager_role)))
                cur.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {}.{}{} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(runtime_role)))
            for function_name, signature in RUNTIME_OFFICE_FUNCTION_SIGNATURES.items():
                cur.execute(sql.SQL("ALTER FUNCTION {}.{}{} OWNER TO {}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(owner_role)))
                cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON FUNCTION {}.{}{} FROM PUBLIC,{},{}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(runtime_role), sql.Identifier(manager_role)))
                cur.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {}.{}{} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(runtime_role)))

            for function_name, signature in RUNTIME_PERMISSION_SIGNATURES.items():
                cur.execute(sql.SQL("ALTER FUNCTION {}.{}{} OWNER TO {}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(owner_role)))
                cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON FUNCTION {}.{}{} FROM PUBLIC,{},{}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(runtime_role), sql.Identifier(manager_role)))
                cur.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {}.{}{} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(function_name), sql.SQL(signature),
                    sql.Identifier(runtime_role)))

            cur.execute("""SELECT c.relname AS tablename,
                                  pg_get_userbyid(c.relowner) AS owner,
                                  has_table_privilege(%s::name,c.oid,'SELECT') AS runtime_select,
                                  has_table_privilege(%s::name,c.oid,'INSERT') AS runtime_insert,
                                  has_table_privilege(%s::name,c.oid,'UPDATE') AS runtime_update,
                                  has_table_privilege(%s::name,c.oid,'DELETE') AS runtime_delete,
                                  has_table_privilege(%s::name,c.oid,'SELECT') AS manager_select,
                                  has_table_privilege(%s::name,c.oid,'INSERT') AS manager_insert,
                                  has_table_privilege(%s::name,c.oid,'UPDATE') AS manager_update,
                                  has_table_privilege(%s::name,c.oid,'DELETE') AS manager_delete
                           FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                           WHERE n.nspname=%s AND c.relkind='r' AND c.relname=ANY(%s)""",
                        (runtime_role, runtime_role, runtime_role, runtime_role,
                         manager_role, manager_role, manager_role, manager_role,
                         schema, list(AUTHORITY_TABLES)))
            verification = cur.fetchall()
            cur.execute("""SELECT has_schema_privilege(%s::name,%s,'USAGE') AS runtime_usage,
                                  has_schema_privilege(%s::name,%s,'CREATE') AS runtime_create,
                                  has_schema_privilege(%s::name,%s,'USAGE') AS manager_usage,
                                  has_schema_privilege(%s::name,%s,'CREATE') AS manager_create,
                                  has_schema_privilege(%s::name,%s,'USAGE') AS owner_usage,
                                  has_schema_privilege(%s::name,%s,'CREATE') AS owner_create""",
                        (runtime_role, schema, runtime_role, schema,
                         manager_role, schema, manager_role, schema,
                         owner_role, schema, owner_role, schema))
            schema_access = cur.fetchone()
            auth_functions = []
            for function_name, arguments in (
                    (AUTHORIZATION_FUNCTION, "p_credential_sha256 bytea, p_action text, p_scope_ref text"),
                    (PRINCIPAL_AUTHORIZATION_FUNCTION, PRINCIPAL_AUTHORIZATION_ARGUMENTS)):
                cur.execute("""SELECT p.proowner::regrole::text AS function_owner,
                                      p.prosecdef AS security_definer,p.proconfig,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS runtime_execute,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS manager_execute
                               FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                               WHERE n.nspname=%s AND p.proname=%s
                                 AND pg_get_function_identity_arguments(p.oid)=%s""",
                            (runtime_role, manager_role, schema, function_name, arguments))
                function_row = cur.fetchone()
                if function_row is None:
                    raise BoundaryPreflightError("exact-grant authorization function post-apply verification failed")
                auth_functions.append(function_row)
            runtime_office_functions = []
            for function_name, arguments in RUNTIME_OFFICE_FUNCTIONS.items():
                cur.execute("""SELECT p.proowner::regrole::text AS function_owner,
                                      p.prosecdef AS security_definer,p.proconfig,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS runtime_execute,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS manager_execute
                               FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                               WHERE n.nspname=%s AND p.proname=%s
                                 AND pg_get_function_identity_arguments(p.oid)=%s""",
                            (runtime_role, manager_role, schema, function_name, arguments))
                function_row = cur.fetchone()
                if function_row is None:
                    raise BoundaryPreflightError("resident office function post-apply verification failed")
                runtime_office_functions.append(function_row)
            runtime_permission_functions = []
            for function_name, arguments in RUNTIME_PERMISSION_FUNCTIONS.items():
                cur.execute("""SELECT p.proowner::regrole::text AS function_owner,
                                      p.prosecdef AS security_definer,p.proconfig,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS runtime_execute,
                                      has_function_privilege(%s::name,p.oid,'EXECUTE') AS manager_execute
                               FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                               WHERE n.nspname=%s AND p.proname=%s
                                 AND pg_get_function_identity_arguments(p.oid)=%s""",
                            (runtime_role, manager_role, schema, function_name, arguments))
                function_row = cur.fetchone()
                if function_row is None:
                    raise BoundaryPreflightError("resident permission function post-apply verification failed")
                function_row["function_name"] = function_name
                runtime_permission_functions.append(function_row)
            if (len(verification) != len(AUTHORITY_TABLES)
                    or any(row["owner"] != owner_role for row in verification)
                    or any(row[name] for row in verification
                           for name in ("runtime_select", "runtime_insert", "runtime_update", "runtime_delete"))
                    or any(not row[name] for row in verification
                           for name in ("manager_select", "manager_insert", "manager_update", "manager_delete"))
                    or not schema_access["runtime_usage"] or schema_access["runtime_create"]
                    or not schema_access["manager_usage"] or schema_access["manager_create"]
                    or not schema_access["owner_usage"] or schema_access["owner_create"]
                    or any(function["function_owner"] != owner_role
                           or not function["security_definer"] or not function["proconfig"]
                           or "search_path=pg_catalog, pg_temp" not in function["proconfig"]
                           or not function["runtime_execute"] or function["manager_execute"]
                           for function in auth_functions)
                    or any(function["function_owner"] != owner_role
                           or not function["security_definer"] or not function["proconfig"]
                           or "search_path=pg_catalog, pg_temp" not in function["proconfig"]
                           or not function["runtime_execute"] or function["manager_execute"]
                           for function in runtime_office_functions)
                    or any(function["function_owner"] != owner_role
                           or not function["security_definer"] or not function["proconfig"]
                           or RUNTIME_PERMISSION_SEARCH_PATHS.get(
                               function["function_name"],
                               f"search_path={schema}, pg_catalog, pg_temp") not in function["proconfig"]
                           or not function["runtime_execute"] or function["manager_execute"]
                           for function in runtime_permission_functions)):
                raise BoundaryPreflightError("post-apply privilege verification failed; transaction rolled back")
            return {
                "status": "APPLIED",
                "schema": schema,
                "runtime_role": runtime_role,
                "manager_role": manager_role,
                "owner_role": owner_role,
                "authority_tables": sorted(tables),
                "runtime_schema_access": "USAGE and exact-grant office authorization/state functions only",
                "runtime_authority_table_access": "denied",
                "manager_dml": "allowlisted tables only",
                "manager_ddl_and_owner_inheritance": "denied",
            }
