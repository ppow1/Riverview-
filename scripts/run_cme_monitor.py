#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_cme_monitor.py
# Component: CME
# Revision: 1.0.0
# Purpose: Launch the CME monitor with systemd-delivered PostgreSQL credentials
# Execution Model: Long-lived supervised monitor service
# Observability: Sanitized structured configuration failures; CME health in PostgreSQL
# Dependencies: Python 3.10+; Psycopg 3; scripts/runtime_baseline.py
# Authority: Validates protected passfile delivery; never reads or logs its contents
# Changed: 2026-10-10 UTC | RV-M2.4-002 | Add protected installed monitor launcher
# Contracts: docs/components/CME_MONITOR.md
# Tests: tests/test_cme_monitor_service.py
# History: New file; Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Start CME after validating systemd credential and runtime account boundaries."""

import json
import logging
import os
from pathlib import Path
import pwd
import sys

import psycopg

from runtime_baseline import (BaselineError, copy_systemd_credential,
                              systemd_credential_path)

SERVICE_UNIT = "riverview-cme-monitor.service"
PASSFILE = Path("/run/riverview-cme-monitor/pgpass")


def prepare_runtime_credential():
    """Copy PID 1's protected credential to the service's private runtime dir."""
    if any(os.environ.get(name) for name in
           ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
        raise BaselineError("AMBIENT_DATABASE_OVERRIDE", "credential")
    dsn = os.environ.get("RIVERVIEW_DATABASE_DSN", "")
    if not dsn:
        raise BaselineError("DATABASE_CONFIGURATION_MISSING", "database")
    if "password" in psycopg.conninfo.conninfo_to_dict(dsn):
        raise BaselineError("DSN_PASSWORD_FORBIDDEN", "database")
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if not credential_dir:
        raise BaselineError("CREDENTIAL_MISSING", "credential")
    source = Path(credential_dir) / "pgpass"
    systemd_credential_path(source, service_unit=SERVICE_UNIT)
    identity = pwd.getpwnam("riverview")
    if identity.pw_uid == 0 or os.geteuid() != identity.pw_uid:
        raise BaselineError("IDENTITY_MISMATCH", "credential")
    copy_systemd_credential(source, PASSFILE, identity.pw_uid)
    os.environ["PGPASSFILE"] = str(PASSFILE)


def main():
    try:
        prepare_runtime_credential()
    except BaselineError as exc:
        logging.error(json.dumps({"event": "cme_configuration_error",
                                  "failure_code": exc.code, "step": exc.step}))
        return 2
    except (OSError, KeyError):
        logging.error('{"event":"cme_configuration_error","failure_code":"CREDENTIAL_UNAVAILABLE"}')
        return 2
    from riverview_core.cme.__main__ import main as monitor_main
    try:
        monitor_main()
        return 0
    except (psycopg.Error, RuntimeError, ValueError) as exc:
        logging.error(json.dumps({"event": "cme_process_exit",
                                  "failure_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
