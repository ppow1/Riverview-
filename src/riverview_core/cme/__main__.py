# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/cme/__main__.py
# Component: CME
# Revision: 1.0.0
# Purpose: Run the continuous PostgreSQL-backed CME monitor process
# Execution Model: Long-lived scheduled service with signal-driven shutdown
# Observability: Structured errors and persisted CME health/events
# Dependencies: Python 3.10+; Psycopg 3; explicit CME migration
# Authority: Reads assignment state; writes CME-owned records only
# Changed: 2026-10-10 UTC | RV-M2.4-001 | Add environment-configured service entrypoint
# Contracts: docs/components/CME_MONITOR.md
# Tests: tests/test_cme_monitor.py
# History: Git and revision/backup manifest
# =============================================================================
"""Environment-configured entrypoint for ``python -m riverview_core.cme``."""

import logging
import os
import signal
import threading

from .monitor import CMEPostgresMonitor


def main():
    dsn = os.environ.get("RIVERVIEW_DATABASE_DSN")
    stall_after = os.environ.get("RIVERVIEW_CME_STALL_AFTER_SECONDS")
    if not dsn or not stall_after:
        raise SystemExit("RIVERVIEW_DATABASE_DSN and RIVERVIEW_CME_STALL_AFTER_SECONDS are required")
    monitor = CMEPostgresMonitor(
        dsn,
        schema=os.environ.get("RIVERVIEW_CME_SCHEMA", "riverview_dev"),
        stall_after_seconds=float(stall_after),
        worker_freshness_seconds=float(
            os.environ.get("RIVERVIEW_CME_WORKER_FRESHNESS_SECONDS", "30")),
        poll_interval=float(os.environ.get("RIVERVIEW_CME_POLL_INTERVAL_SECONDS", "1")),
        max_backoff_seconds=float(
            os.environ.get("RIVERVIEW_CME_MAX_BACKOFF_SECONDS", "30")),
    )
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    logging.basicConfig(level=os.environ.get("RIVERVIEW_LOG_LEVEL", "INFO"))
    monitor.run_forever(stop)


if __name__ == "__main__":
    main()
