#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_assignment_intake.py
# Component: ASSIGNMENT-INTAKE
# Revision: 1.0.0
# Purpose: Start the loopback exact-grant assignment request service
# Execution Model: systemd-supervised bounded HTTP process
# Observability: Safe JSON diagnostics; no request body or bearer logging
# Dependencies: Python 3.10+; Psycopg 3; systemd credential delivery
# Authority: Creates assignments only through AuthorizedAssignmentIntake
# Changed: 2026-10-11 UTC | RV-M3.3-GOVERNED-INTAKE-ROUTE | Initial service runner
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_assignment_intake_http.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Start the grant-gated assignment intake API under its systemd unit."""

import ipaddress
import json
import logging
import os
from pathlib import Path
import signal
import threading

import psycopg

from riverview_core.assignment_intake_http import (
    AssignmentIntakeHandler, AssignmentIntakeHTTPServer,
)
from riverview_core.postgres_ledger import PostgresLedger
from runtime_baseline import (BaselineError, copy_systemd_credential,
                              systemd_credential_path)

SERVICE_UNIT = "riverview-assignment-intake.service"
PASSFILE = Path("/run/riverview-assignment-intake/pgpass")


def prepare_runtime_credential():
    if any(os.environ.get(name) for name in
           ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
        raise BaselineError("AMBIENT_DATABASE_OVERRIDE", "credential")
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if not credential_dir:
        raise BaselineError("CREDENTIAL_MISSING", "credential")
    source = Path(credential_dir) / "pgpass"
    systemd_credential_path(source, service_unit=SERVICE_UNIT)
    identity = __import__("pwd").getpwnam("riverview")
    if identity.pw_uid == 0 or os.geteuid() != identity.pw_uid:
        raise BaselineError("IDENTITY_MISMATCH", "credential")
    copy_systemd_credential(source, PASSFILE, identity.pw_uid)
    os.environ["PGPASSFILE"] = str(PASSFILE)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    dsn = os.environ.get("RIVERVIEW_PG_DSN", "")
    schema = os.environ.get("RIVERVIEW_PG_SCHEMA", "riverview_dev")
    authority_schema = os.environ.get("RIVERVIEW_AUTHORITY_SCHEMA", "riverview_authority")
    host = os.environ.get("RIVERVIEW_INTAKE_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("RIVERVIEW_INTAKE_PORT", "8710"))
        if not dsn or "password" in psycopg.conninfo.conninfo_to_dict(dsn):
            raise ValueError("database DSN invalid")
        if not ipaddress.ip_address(host).is_loopback or not 1 <= port <= 65535:
            raise ValueError("listener configuration invalid")
        for item in (schema, authority_schema):
            if not item or not item[0].isalpha() or not item.replace("_", "").isalnum():
                raise ValueError("schema configuration invalid")
        prepare_runtime_credential()
        probe = PostgresLedger(dsn, schema=schema)
        try:
            with probe.db.cursor() as cur:
                cur.execute("SELECT to_regprocedure(%s) IS NOT NULL AS available",
                            (f"{authority_schema}.authorize_exact_grant(bytea,text,text)",))
                if not cur.fetchone()["available"]:
                    raise RuntimeError("exact grant function unavailable")
        finally:
            probe.close()
        server = AssignmentIntakeHTTPServer(
            (host, port), AssignmentIntakeHandler, dsn=dsn, schema=schema,
            authority_schema=authority_schema)
        stop = lambda *_: threading.Thread(target=server.shutdown, daemon=True).start()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        logging.info(json.dumps({"event": "assignment_intake_started",
                                 "host": host, "port": port,
                                 "schema": schema,
                                 "authority_schema": authority_schema}, sort_keys=True))
        try:
            server.serve_forever(poll_interval=0.25)
        finally:
            server.server_close()
        return 0
    except BaselineError as exc:
        logging.error(json.dumps({"event": "assignment_intake_configuration_error",
                                  "failure_code": exc.code}, sort_keys=True))
        return 2
    except (ValueError, psycopg.Error, OSError, RuntimeError):
        logging.error(json.dumps({"event": "assignment_intake_startup_failed",
                                  "failure_code": "preflight_failed"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
