#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_notification_delivery.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.0
# Purpose: Validate the systemd database credential and run the push delivery worker
# Execution Model: Long-lived systemd-supervised process with bounded reconciliation
# Observability: Sanitized journal, PostgreSQL queue and append-only delivery events
# Dependencies: Psycopg 3; runtime_baseline credential validation; notifications 0007
# Authority: Uses riverview_core only for notification-owned reads/writes
# Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial worker launcher
# Contracts: docs/components/NOTIFICATION_IPHONE_DELIVERY.md
# Tests: tests/test_notification_push.py
# History: Git + .riverview-backups/manifest.jsonl
# =============================================================================
"""Prepare the private libpq credential, then start the push delivery worker."""

import json
import logging
import os
import pwd
import signal
import threading
import time
from pathlib import Path

import psycopg

from runtime_baseline import BaselineError, copy_systemd_credential, systemd_credential_path

SERVICE_UNIT = "riverview-notification-delivery.service"
PASSFILE = Path("/run/riverview-notification-delivery/pgpass")


def prepare_runtime_credential():
    if any(os.environ.get(name) for name in ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
        raise BaselineError("AMBIENT_DATABASE_OVERRIDE", "credential")
    dsn = os.environ.get("RIVERVIEW_DATABASE_DSN", "")
    if not dsn or "password" in psycopg.conninfo.conninfo_to_dict(dsn):
        raise BaselineError("DATABASE_CONFIGURATION_INVALID", "database")
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
    logging.basicConfig(level=os.environ.get("RIVERVIEW_LOG_LEVEL", "INFO"))
    try:
        prepare_runtime_credential()
        from riverview_core.notifications.push import (
            NotificationDeliveryManager, PushConfig)
        config = PushConfig.load(os.environ["RIVERVIEW_NOTIFICATION_PUSH_CONFIG"])
        manager = NotificationDeliveryManager(
            os.environ["RIVERVIEW_DATABASE_DSN"], config,
            schema=os.environ.get("RIVERVIEW_NOTIFICATION_SCHEMA", "riverview_dev"))
    except (BaselineError, KeyError, OSError, ValueError) as exc:
        logging.error(json.dumps({"event": "notification_push_configuration_error",
                                  "failure_type": type(exc).__name__}))
        return 2
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    interval = max(5, min(300, int(os.environ.get("RIVERVIEW_NOTIFICATION_PUSH_POLL_SECONDS", "15"))))
    while not stop.is_set():
        try:
            logging.info(json.dumps({"event": "notification_push_cycle",
                                     **manager.run_once()}))
        except (psycopg.Error, RuntimeError, ValueError) as exc:
            logging.error(json.dumps({"event": "notification_push_cycle_failed",
                                      "failure_type": type(exc).__name__}))
            try:
                manager.record_health(status="degraded", error_code=type(exc).__name__[:80])
            except psycopg.Error:
                pass
        stop.wait(interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
