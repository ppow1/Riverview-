# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/db_boundary.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Separate authority relation ownership from the shared runtime role
# Execution Model: Explicit PostgreSQL DBA operation; dry-run by default
# Observability: Redacted JSON preflight and applied-relation report
# Dependencies: Python 3.10+; Psycopg 3; PostgreSQL 16
# Authority: Exact authority relation allowlist; no rows, credentials or unrelated objects changed
# Changed: 2026-10-11 UTC | RV-M4.1-DB-BOUNDARY | Initial role-separated authority table ownership
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

    ``manager_role`` must be separately provisioned as a non-superuser LOGIN
    with protected credential delivery. It receives membership in ``owner_role``
    because the current registry implementation uses direct SQL. The ordinary
    runtime role receives no table or trigger-function access. This does not
    authorize assignments and does not remove a schema owner's CREATE/DROP
    ability; it specifically prevents direct access to these table objects.
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
                    or manager["rolbypassrls"] or not manager["rolinherit"]):
                raise BoundaryPreflightError("manager role must be a non-privileged, inheriting LOGIN")
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
            cur.execute(sql.SQL("GRANT USAGE,CREATE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(owner_role)))
            cur.execute(sql.SQL("GRANT {} TO {}").format(
                sql.Identifier(owner_role), sql.Identifier(manager_role)))
            for table_name in AUTHORITY_TABLES:
                cur.execute(sql.SQL("ALTER TABLE {}.{} OWNER TO {}").format(
                    sql.Identifier(schema), sql.Identifier(table_name), sql.Identifier(owner_role)))
                cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON TABLE {}.{} FROM PUBLIC,{}").format(
                    sql.Identifier(schema), sql.Identifier(table_name), sql.Identifier(runtime_role)))
            cur.execute(sql.SQL("ALTER FUNCTION {}.{}() OWNER TO {}").format(
                sql.Identifier(schema), sql.Identifier(EVENT_TRIGGER_FUNCTION), sql.Identifier(owner_role)))
            cur.execute(sql.SQL("REVOKE ALL PRIVILEGES ON FUNCTION {}.{}() FROM PUBLIC,{}").format(
                sql.Identifier(schema), sql.Identifier(EVENT_TRIGGER_FUNCTION), sql.Identifier(runtime_role)))
            cur.execute(sql.SQL("REVOKE CREATE ON SCHEMA {} FROM {}").format(
                sql.Identifier(schema), sql.Identifier(owner_role)))
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(manager_role)))

            cur.execute("""SELECT tablename,
                                  pg_get_userbyid((SELECT relowner FROM pg_class c
                                    JOIN pg_namespace n ON n.oid=c.relnamespace
                                   WHERE n.nspname=%s AND c.relname=p.tablename)) AS owner,
                                  has_table_privilege(%s,format('%I.%I',%s,tablename),'SELECT') AS runtime_select,
                                  has_table_privilege(%s,format('%I.%I',%s,tablename),'INSERT') AS runtime_insert,
                                  has_table_privilege(%s,format('%I.%I',%s,tablename),'UPDATE') AS runtime_update,
                                  has_table_privilege(%s,format('%I.%I',%s,tablename),'DELETE') AS runtime_delete,
                                  has_table_privilege(%s,format('%I.%I',%s,tablename),'SELECT') AS manager_select,
                                  has_table_privilege(%s,format('%I.%I',%s,tablename),'INSERT') AS manager_insert
                           FROM pg_tables p WHERE schemaname=%s AND tablename=ANY(%s)""",
                        (schema, runtime_role, schema, runtime_role, schema, runtime_role, schema,
                         runtime_role, schema, manager_role, schema, manager_role, schema,
                         schema, list(AUTHORITY_TABLES)))
            verification = cur.fetchall()
            if (len(verification) != len(AUTHORITY_TABLES)
                    or any(row["owner"] != owner_role for row in verification)
                    or any(row[name] for row in verification
                           for name in ("runtime_select", "runtime_insert", "runtime_update", "runtime_delete"))
                    or any(not row[name] for row in verification
                           for name in ("manager_select", "manager_insert"))):
                raise BoundaryPreflightError("post-apply privilege verification failed; transaction rolled back")
            return {
                "status": "APPLIED",
                "schema": schema,
                "runtime_role": runtime_role,
                "manager_role": manager_role,
                "owner_role": owner_role,
                "authority_tables": sorted(tables),
                "runtime_table_access": "denied",
                "manager_registry_access": "allowed",
            }
