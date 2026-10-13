#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/provision_account_auth_schema.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.1.0
# Purpose: Provision the dedicated NOLOGIN account schema owner and runtime privileges
# Execution Model: Explicit DBA commissioning CLI; never runs during dashboard startup
# Observability: Secret-free JSON plan/result and exit code
# Dependencies: PostgreSQL 16; psycopg 3; local postgres peer connection
# Authority: Only creates an additive schema/role; refuses existing owner mismatch
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Initial least-privilege account schema provisioner
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Permit isolated-DSN verification without changing production targeting
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Grant least-privilege access to email provider configuration
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: Disposable PostgreSQL migration integration tests
# History: Git and revision/backup manifest
# =============================================================================
"""Provision only the dedicated Riverview account schema and runtime grants."""

from __future__ import annotations

import argparse
import json
import re
import sys

import psycopg

DATABASE_DSN = "dbname=riverview"
SCHEMA = "riverview_accounts"
OWNER = "riverview_accounts_owner"
RUNTIME = "riverview_core"
TABLES = (
    "schema_migrations", "enrollments", "accounts", "account_roles",
    "challenges", "sessions", "rate_limits", "account_audit",
    "email_provider_config",
)


def _ident(value):
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", value):
        raise ValueError("invalid SQL identifier")
    return '"' + value + '"'


def provision(*, apply=False, dsn=DATABASE_DSN):
    schema = _ident(SCHEMA)
    owner = _ident(OWNER)
    runtime = _ident(RUNTIME)
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=%s",
                    (RUNTIME,))
        runtime_role = cur.fetchone()
        if not runtime_role or any(runtime_role):
            raise RuntimeError("runtime role is missing or overprivileged")
        cur.execute("SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls "
                    "FROM pg_roles WHERE rolname=%s", (OWNER,))
        owner_role = cur.fetchone()
        if owner_role and any(owner_role):
            raise RuntimeError("account schema owner role is not a safe NOLOGIN role")
        cur.execute("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=%s",
                    (SCHEMA,))
        schema_row = cur.fetchone()
        if schema_row and schema_row[0] != OWNER:
            raise RuntimeError("existing account schema has an unexpected owner")
        cur.execute("SELECT member.rolname FROM pg_auth_members m "
                    "JOIN pg_roles role ON role.oid=m.roleid "
                    "JOIN pg_roles member ON member.oid=m.member "
                    "WHERE role.rolname=%s AND member.rolname=%s", (OWNER, RUNTIME))
        if cur.fetchone():
            raise RuntimeError("runtime role must not inherit account schema owner")
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", (f"{SCHEMA}.accounts",))
        tables_exist = bool(cur.fetchone()[0])
        plan = {
            "schema": SCHEMA,
            "owner_role": OWNER,
            "runtime_role": RUNTIME,
            "schema_exists": bool(schema_row),
            "migration_tables_exist": tables_exist,
            "action": "preflight_only" if not apply else "provision_additive_schema_and_grants",
        }
        if not apply:
            return plan
        with conn.transaction():
            with conn.cursor() as cur:
                if not owner_role:
                    cur.execute(f"CREATE ROLE {owner} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
                if not schema_row:
                    cur.execute(f"CREATE SCHEMA {schema} AUTHORIZATION {owner}")
                cur.execute(f"REVOKE CREATE ON SCHEMA {schema} FROM PUBLIC")
                cur.execute(f"REVOKE CREATE ON SCHEMA {schema} FROM {runtime}")
                cur.execute(f"GRANT USAGE ON SCHEMA {schema} TO {runtime}")
                if tables_exist:
                    for table in TABLES:
                        cur.execute(f"ALTER TABLE {schema}.{_ident(table)} OWNER TO {owner}")
                    cur.execute(f"ALTER FUNCTION {schema}.reject_account_audit_mutation() OWNER TO {owner}")
                    cur.execute(f"GRANT SELECT ON {schema}.schema_migrations TO {runtime}")
                    cur.execute(f"GRANT SELECT, INSERT, UPDATE ON {schema}.enrollments TO {runtime}")
                    cur.execute(f"GRANT SELECT, INSERT, UPDATE ON {schema}.accounts TO {runtime}")
                    cur.execute(f"GRANT SELECT, INSERT, DELETE ON {schema}.account_roles TO {runtime}")
                    cur.execute(f"GRANT SELECT, INSERT, UPDATE ON {schema}.challenges TO {runtime}")
                    cur.execute(f"GRANT SELECT, INSERT, UPDATE ON {schema}.sessions TO {runtime}")
                    cur.execute(f"GRANT SELECT, INSERT, UPDATE ON {schema}.rate_limits TO {runtime}")
                    cur.execute(f"GRANT SELECT, INSERT ON {schema}.account_audit TO {runtime}")
                    cur.execute(f"GRANT SELECT, INSERT, UPDATE ON {schema}.email_provider_config TO {runtime}")
                    cur.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {runtime}")
                    cur.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM PUBLIC")
                    cur.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {schema} FROM PUBLIC")
        plan["action"] = "provisioned" if tables_exist else "schema_created_apply_migration_then_rerun_for_grants"
        return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply the displayed additive role/schema/grants plan")
    args = parser.parse_args()
    if args.apply and __import__("os").geteuid() != 0 and __import__("getpass").getuser() != "postgres":
        print("Run as the local PostgreSQL administrator.", file=sys.stderr)
        return 2
    try:
        result = provision(apply=args.apply)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"failed", "error_type":type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
