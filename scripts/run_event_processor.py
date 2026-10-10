#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_event_processor.py
# Component: EVENT-PROCESSOR
# Revision: 1.0.0
# Purpose: Start the continuous PostgreSQL assignment intake processor
# Execution Model: Event-driven supervised service
# Observability: Structured JSON stdout/stderr for systemd journal
# Dependencies: Python 3.10+; Psycopg 3; protected libpq passfile
# Authority: Accepts no password argument; DSN must not contain a password
# Changed: 2026-10-10 UTC | RV-M1.3-001 | Initial supervised processor entry point
# Contracts: docs/development/M1.3-001_REVISION_RECORD.md
# Tests: tests/test_event_processor.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Run the continuously supervised PostgreSQL event processor."""

import logging
import os
import signal
import sys
import threading

import psycopg

from riverview_core.event_processor import PostgresEventProcessor


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
        processor.run_forever(stop)
        return 0
    except (psycopg.Error, ValueError, RuntimeError) as exc:
        logging.error('{"event":"processor_exit","failure_type":"%s"}', type(exc).__name__)
        return 1
    finally:
        processor.close()


if __name__ == "__main__":
    raise SystemExit(main())
