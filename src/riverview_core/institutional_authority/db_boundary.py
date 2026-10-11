# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/db_boundary.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.5
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
)
EVENT_TRIGGER_FUNCTION = "reject_institutional_authority_event_mutation"
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
            cur.execute("""SELECT p.proname FROM pg_proc p
                           JOIN pg_namespace n ON n.oid=p.pronamespace
                           WHERE n.nspname=%s AND p.proname<>%s""",
                        (schema, EVENT_TRIGGER_FUNCTION))
            unexpected_functions = sorted(row["proname"] for row in cur.fetchall())
            if unexpected_functions:
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
                           WHERE n.nspname=%s AND p.proname=%s
                             AND p.pronargs=0""",
                        (schema, EVENT_TRIGGER_FUNCTION))
            trigger_row = cur.fetchone()
            if trigger_row is None:
                raise BoundaryPreflightError("append-only authority trigger function is missing")
            if trigger_row["function_owner"] not in acceptable_owners:
                raise BoundaryPreflightError("authority trigger function owner is outside the approved transition set")

            if not apply:
                return {
                    "status": "PREFLIGHT_PASS",
                    "database_user": administrator["current_user"],
                    "schema": schema,
                    "runtime_role": runtime_role,
                    "manager_role": manager_role,
                    "owner_role": owner_role,
                    "authority_tables": sorted(tables),
                    "apply_required": owner is None or any(x != owner_role for x in tables.values()),
                }

            if owner is None:
                cur.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS").format(
                    sql.Identifier(owner_role)))
            cur.execute(sql.SQL("REVOKE ALL ON SCHEMA {} FROM PUBLIC,{},{}").format(
                sql.Identifier(schema), sql.Identifier(runtime_role), sql.Identifier(owner_role)))
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(manager_role)))
            for table_name in AUTHORITY_TABLES:
                cur.execute(sql.SQL("ALTER TABLE {}.{} OWNER TO {}").format(
                    sql.Identifier(schema), sql.Identifier(table_name), sql.Identifier(owner_role)))
                cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON TABLE {}.{} FROM PUBLIC,{}").format(
                    sql.Identifier(schema), sql.Identifier(table_name),
                    sql.SQL("{},{}").format(sql.Identifier(runtime_role), sql.Identifier(manager_role))))
                cur.execute(sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE {}.{} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(table_name), sql.Identifier(manager_role)))
            cur.execute(sql.SQL("ALTER FUNCTION {}.{}() OWNER TO {}").format(
                sql.Identifier(schema), sql.Identifier(EVENT_TRIGGER_FUNCTION), sql.Identifier(owner_role)))
            cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON FUNCTION {}.{}() FROM PUBLIC,{},{}").format(
                sql.Identifier(schema), sql.Identifier(EVENT_TRIGGER_FUNCTION),
                sql.Identifier(runtime_role), sql.Identifier(manager_role)))

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
                                  has_schema_privilege(%s::name,%s,'CREATE') AS manager_create""",
                        (runtime_role, schema, runtime_role, schema,
                         manager_role, schema, manager_role, schema))
            schema_access = cur.fetchone()
            if (len(verification) != len(AUTHORITY_TABLES)
                    or any(row["owner"] != owner_role for row in verification)
                    or any(row[name] for row in verification
                           for name in ("runtime_select", "runtime_insert", "runtime_update", "runtime_delete"))
                    or any(not row[name] for row in verification
                           for name in ("manager_select", "manager_insert", "manager_update", "manager_delete"))
                    or schema_access["runtime_usage"] or schema_access["runtime_create"]
                    or not schema_access["manager_usage"] or schema_access["manager_create"]):
                raise BoundaryPreflightError("post-apply privilege verification failed; transaction rolled back")
            return {
                "status": "APPLIED",
                "schema": schema,
                "runtime_role": runtime_role,
                "manager_role": manager_role,
                "owner_role": owner_role,
                "authority_tables": sorted(tables),
                "runtime_schema_and_table_access": "denied",
                "manager_dml": "allowlisted tables only",
                "manager_ddl_and_owner_inheritance": "denied",
            }
