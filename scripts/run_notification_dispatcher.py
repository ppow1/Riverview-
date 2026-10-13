#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_notification_dispatcher.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.0
# Purpose: Launch the notification dispatcher with the exact protected PG credential
# Execution Model: Long-lived systemd-supervised service
# Observability: Sanitized startup/configuration errors and durable health rows
# Dependencies: Python 3.10+; Psycopg 3; runtime_baseline credential validator
# Authority: Validates and privately copies pgpass; never displays its contents
# Changed: 2026-10-11 UTC | RV-M3.2-001 | Add supervised dispatcher entry point
# Contracts: docs/components/NOTIFICATION_DELIVERY.md
# Tests: tests/test_notification_service.py
# History: New file; Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Validate systemd's exact credential and run the continuous dispatcher."""

import json
import logging
import os
from pathlib import Path
import pwd

import psycopg

from runtime_baseline import (BaselineError, copy_systemd_credential,
                              systemd_credential_path)

SERVICE_UNIT = "riverview-notification-dispatcher.service"
PASSFILE = Path("/run/riverview-notification-dispatcher/pgpass")


def prepare_runtime_credential():
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
        logging.error(json.dumps({"event": "notification_configuration_error",
                                  "failure_code": exc.code, "step": exc.step}))
        return 2
    except (OSError, KeyError):
        logging.error('{"event":"notification_configuration_error","failure_code":"CREDENTIAL_UNAVAILABLE"}')
        return 2
    from riverview_core.notifications.dispatcher import main as dispatcher_main
    try:
        dispatcher_main()
        return 0
    except (psycopg.Error, RuntimeError, ValueError) as exc:
        logging.error(json.dumps({"event": "notification_process_exit",
                                  "failure_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
