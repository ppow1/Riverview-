#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_event_processor.py
# Component: EVENT-PROCESSOR
# Revision: 1.0.1
# Purpose: Start the continuous PostgreSQL assignment intake processor
# Execution Model: Event-driven supervised service
# Observability: Structured JSON stdout/stderr for systemd journal
# Dependencies: Python 3.10+; Psycopg 3; protected libpq passfile
# Authority: Accepts no password argument; DSN must not contain a password
# Changed: 2026-10-10 UTC | RV-M1.3-002 | Validate credential delivery and migration contract before processing
# Contracts: docs/development/M1.3-001_REVISION_RECORD.md
# Tests: tests/test_event_processor.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Run the continuously supervised PostgreSQL event processor."""

import logging
import os
from pathlib import Path
import pwd
import signal
import sys
import threading

import psycopg

from riverview_core.event_processor import PostgresEventProcessor
from runtime_baseline import (BaselineError, copy_systemd_credential,
                              systemd_credential_path)

SERVICE_UNIT = "riverview-event-processor.service"
PASSFILE = Path("/run/riverview-event-processor/pgpass")


def prepare_runtime_credential():
    """Copy PID 1's read-only credential into private libpq mode-0600 storage."""
    if any(os.environ.get(name) for name in
           ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
        raise BaselineError("AMBIENT_DATABASE_OVERRIDE", "credential")
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
    dsn = os.environ.get("RIVERVIEW_PG_DSN", "")
    schema = os.environ.get("RIVERVIEW_PG_SCHEMA", "riverview_dev")
    consumer_id = os.environ.get("RIVERVIEW_PROCESSOR_ID", "assignment-intake.v1")
    if not dsn:
        print('{"event":"configuration_error","reason":"RIVERVIEW_PG_DSN is required"}', file=sys.stderr)
        return 2
    if "password" in psycopg.conninfo.conninfo_to_dict(dsn):
        print('{"event":"configuration_error","reason":"DSN password is forbidden; configure PGPASSFILE"}', file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    processor = PostgresEventProcessor(dsn, schema=schema, consumer_id=consumer_id)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    try:
        try:
            prepare_runtime_credential()
        except BaselineError as exc:
            logging.error('{"event":"processor_configuration_error","failure_code":"%s"}', exc.code)
            return 2
        except (OSError, KeyError):
            logging.error('{"event":"processor_configuration_error","failure_code":"CREDENTIAL_UNAVAILABLE"}')
            return 1
        processor.run_forever(stop)
        return 0
    except (psycopg.Error, ValueError, RuntimeError) as exc:
        logging.error('{"event":"processor_exit","failure_type":"%s"}', type(exc).__name__)
        return 1
    finally:
        processor.close()


if __name__ == "__main__":
    raise SystemExit(main())
