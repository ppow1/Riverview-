# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/runtime_baseline.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.2
# Purpose: Read-only M1.1 identity, credential and PostgreSQL commissioning probe
# Execution Model: Request-driven diagnostic; no institutional work loop
# Observability: rv.runtime-baseline.v1 JSON stdout; freshness expires after 60s
# Dependencies: Python 3.10+, Psycopg 3, Linux, PostgreSQL
# Authority: Read-only; never provisions, changes passwords or initializes tables
# Changed: 2026-10-10 UTC | RV-M1.1-009 | Validate systemd root-owned credential delivery separately
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py
# History: New file; no predecessor; Git
"""Validate commissioning without disclosing credential contents or DB errors."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys


class BaselineError(Exception):
    def __init__(self, code, step, detail=None):
        self.code, self.step, self.detail = code, step, detail


def private_path(path, uid, *, directory=False):
    """Reject symlinks, unsafe owners/modes and nonregular credential files."""
    try:
        info = path.lstat()
        kind_ok = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        step = "credential" if not directory else "storage"
        if path.resolve() != path.absolute():
            raise BaselineError("UNSAFE_PATH", step, "symlink_in_path")
        if not kind_ok:
            raise BaselineError("UNSAFE_PATH", step, "unexpected_file_type")
        if info.st_uid != uid:
            raise BaselineError("UNSAFE_PATH", step, "owner_uid_mismatch")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise BaselineError("UNSAFE_MODE", "credential" if not directory else "storage")
        if not directory and (info.st_size == 0 or not os.access(path, os.R_OK)):
            raise BaselineError("CREDENTIAL_UNREADABLE", "credential")
    except OSError:
        raise BaselineError("PATH_UNAVAILABLE", "credential" if not directory else "storage") from None


def systemd_credential_path(path):
    """Validate systemd's root-owned, read-only credential mount and its file.

    The credential is copied by PID 1 into /run/credentials/<unit>. That
    directory and file are intentionally root-owned; systemd grants the service
    read/traverse access. Runtime-owned state uses private_path() instead.
    """
    step = "credential"
    try:
        expected_dir = Path("/run/credentials/riverview-baseline.service")
        configured_dir = os.environ.get("CREDENTIALS_DIRECTORY")
        parent = path.parent
        if (configured_dir is None or Path(configured_dir) != expected_dir or
                parent != expected_dir or path.name != "pgpass"):
            raise BaselineError("UNSAFE_PATH", step, "unexpected_credential_location")
        if expected_dir.resolve() != expected_dir.absolute() or path.resolve() != path.absolute():
            raise BaselineError("UNSAFE_PATH", step, "symlink_in_path")
        directory_info = expected_dir.lstat()
        if not stat.S_ISDIR(directory_info.st_mode):
            raise BaselineError("UNSAFE_PATH", step, "unexpected_file_type")
        if directory_info.st_uid != 0:
            raise BaselineError("UNSAFE_PATH", step, "credential_directory_owner_mismatch")
        if stat.S_IMODE(directory_info.st_mode) != 0o550 or not os.access(expected_dir, os.X_OK, effective_ids=True):
            raise BaselineError("UNSAFE_MODE", step, "unsafe_credential_directory_mode")
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise BaselineError("UNSAFE_PATH", step, "unexpected_file_type")
        if info.st_uid != 0:
            raise BaselineError("UNSAFE_PATH", step, "credential_file_owner_mismatch")
        if stat.S_IMODE(info.st_mode) != 0o440 or info.st_size == 0:
            raise BaselineError("UNSAFE_MODE", step, "unsafe_credential_file_mode")
        if not os.access(path, os.R_OK, effective_ids=True):
            raise BaselineError("CREDENTIAL_UNREADABLE", step, "credential_not_readable")
    except OSError:
        raise BaselineError("PATH_UNAVAILABLE", step) from None


def check_database(connect, passfile):
    # Explicit endpoint and read-only options; no DSN or password in diagnostics.
    with connect(host="127.0.0.1", port=5432, dbname="riverview", user="riverview_core",
                 passfile=str(passfile), connect_timeout=5,
                 options="-c default_transaction_read_only=on") as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()[0] != "on":
                raise BaselineError("READ_ONLY_REQUIRED", "database")
            cur.execute("SELECT current_user, current_database(), inet_server_addr()::text")
            role, database, address = cur.fetchone()
            if (role, database, address) != ("riverview_core", "riverview", "127.0.0.1"):
                raise BaselineError("DATABASE_IDENTITY_MISMATCH", "database")
            cur.execute("SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
                        "FROM pg_roles WHERE rolname = current_user")
            privileges = cur.fetchone()
            if privileges is None or any(privileges):
                raise BaselineError("EXCESS_DATABASE_PRIVILEGE", "database")
            cur.execute("SELECT pg_get_userbyid(nspowner), "
                        "has_schema_privilege(current_user, oid, 'USAGE'), "
                        "has_schema_privilege(current_user, oid, 'CREATE') "
                        "FROM pg_namespace WHERE nspname = 'riverview_dev'")
            schema = cur.fetchone()
            if schema is None:
                raise BaselineError("SCHEMA_MISSING", "schema")
            if schema[1:] != (True, True):
                raise BaselineError("SCHEMA_AUTHORITY_MISMATCH", "schema")
            return {"schema_owner": schema[0]}


def probe(*, passfile, state_dir, account="riverview", connect=None):
    now = datetime.now(timezone.utc)
    result = dict(projection_version="rv.runtime-baseline.v1", component_id="RUNTIME-BASELINE",
                  component_version="1.0.0", workflow_id="runtime-baseline.v1", step_id="identity",
                  observed_at=now.isoformat(), expires_at=(now + timedelta(seconds=60)).isoformat(),
                  freshness="current", status="blocked", baseline_ready=False,
                  institutional_readiness="not_verified", heartbeat_at=None,
                  last_meaningful_progress_at=None, event_cursor=None,
                  database="riverview", schema="riverview_dev", database_role="riverview_core",
                  runtime_account=account, blocker_code=None, recovery_status="required",
                  diagnostic_ref="docs/components/RUNTIME_BASELINE_COOKBOOK.md",
                  responsible_office_id="office:operations", target_host=os.uname().nodename, source_commit=None,
                  path_failure_reason=None)
    commit_file = Path(__file__).resolve().parents[1] / "SOURCE_COMMIT"
    if commit_file.is_file():
        candidate = commit_file.read_text().strip()
        if re.fullmatch(r"[0-9a-f]{40}", candidate):
            result["source_commit"] = candidate
    try:
        try:
            identity = pwd.getpwnam(account)
        except KeyError:
            raise BaselineError("IDENTITY_MISSING", "identity") from None
        if identity.pw_uid == 0 or os.geteuid() != identity.pw_uid:
            raise BaselineError("IDENTITY_MISMATCH", "identity")
        if identity.pw_shell not in ("/usr/sbin/nologin", "/sbin/nologin", "/bin/false"):
            raise BaselineError("INTERACTIVE_SERVICE_ACCOUNT", "identity")
        result["step_id"] = "storage"
        private_path(state_dir, identity.pw_uid, directory=True)
        result["step_id"] = "credential"
        if passfile is None:
            raise BaselineError("CREDENTIAL_MISSING", "credential")
        systemd_credential_path(passfile)
        if any(os.environ.get(name) for name in ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
            raise BaselineError("AMBIENT_DATABASE_OVERRIDE", "credential")
        result["step_id"] = "database"
        if connect is None:
            try:
                import psycopg
            except ImportError:
                raise BaselineError("DEPENDENCY_MISSING", "database") from None
            connect = psycopg.connect
        result.update(check_database(connect, passfile))
        result.update(step_id="ready", status="baseline_ready", baseline_ready=True,
                      recovery_status="baseline_verified")
        return result, 0
    except BaselineError as exc:
        result.update(step_id=exc.step, blocker_code=exc.code)
        if exc.code == "UNSAFE_PATH":
            result["path_failure_reason"] = exc.detail
        return result, 2
    except Exception:
        # Driver errors can contain passwords/DSNs; expose only a stable code.
        result.update(status="unavailable", blocker_code="DATABASE_UNAVAILABLE")
        return result, 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passfile", type=Path)
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/riverview"))
    args = parser.parse_args()
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    passfile = args.passfile
    if passfile is None and credential_dir:
        passfile = Path(credential_dir) / "pgpass"
    report, code = probe(passfile=passfile, state_dir=args.state_dir)
    print(json.dumps(report, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
