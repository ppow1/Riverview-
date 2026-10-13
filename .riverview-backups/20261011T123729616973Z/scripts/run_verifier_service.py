#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_verifier_service.py
# Component: WORKER-ADAPTER
# Revision: 1.0.1
# Purpose: Run a distinct authenticated verifier for durable worker results
# Execution Model: Persistent PostgreSQL polling with idempotent verification
# Observability: Decision, assignment and attempt IDs; no artifact body/token logs
# Dependencies: Psycopg; systemd credentials; independent verifier contract
# Authority: Exact worker.register and assignment.verify grants are mandatory
# Changed: 2026-10-11 UTC | RV-M3.3-WORKER-SERVICE | Initial verifier service runner
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Verify the persisted repository test-report file independently
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_service.py; tests/test_worker_adapter.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Independently verify deterministic worker artifacts under a distinct identity."""

import json
import logging
import os
import signal
import threading
import re

import psycopg

from riverview_core.worker_adapter import PostgresWorkerAdapter
from riverview_core.worker_adapter.service import (
    WorkerServiceConfigurationError, ensure_registered, load_runtime_config,
)
from riverview_core.worker_adapter.verifier import RepositoryContractTestVerifier

SERVICE_UNIT = "riverview-m33-verifier.service"
CAPABILITY = "assignment.verify.v1"


def next_candidate(adapter):
    with adapter.ledger.db.cursor() as cur:
        adapter.ledger._set_search_path(cur)
        cur.execute("""SELECT a.id AS assignment_id,wa.attempt_id
                       FROM assignments a JOIN worker_attempts wa
                         ON wa.assignment_id=a.id
                       JOIN worker_results wr USING(attempt_id)
                       WHERE a.state='awaiting_verification'
                         AND wa.status='succeeded'
                         AND wa.capability='engineering.repository-check.v1'
                       ORDER BY a.updated_at,wa.started_at,wa.attempt_id
                       LIMIT 1""")
        return cur.fetchone()


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    adapter = None
    try:
        dsn, schema, authority_schema, verifier_id, scope_ref, token = load_runtime_config(
            SERVICE_UNIT, "verifier-token")
        adapter = PostgresWorkerAdapter(dsn, schema=schema, authority_schema=authority_schema)
        ensure_registered(adapter, verifier_id, token, (CAPABILITY,), scope_ref)
        commit = os.environ.get("RIVERVIEW_KNOWLEDGE_COMMIT", "")
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise WorkerServiceConfigurationError("knowledge_pin_invalid")
        verifier = RepositoryContractTestVerifier(
            os.environ.get("RIVERVIEW_ARTIFACT_DIR",
                           "/var/lib/riverview-m33-worker/artifacts"), commit, root)
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        logging.info(json.dumps({"event": "verifier_service_started",
                                 "verifier_id": verifier_id, "capability": CAPABILITY,
                                 "schema": schema}, sort_keys=True))
        while not stop.is_set():
            try:
                candidate = next_candidate(adapter)
                if candidate is None:
                    stop.wait(float(os.environ.get("RIVERVIEW_VERIFIER_POLL_SECONDS", "1")))
                    continue
                decision = adapter.verify_attempt(
                    candidate["assignment_id"], candidate["attempt_id"], verifier_id,
                    token, verifier,
                    idempotency_key=f"service-verification:{candidate['attempt_id']}")
                logging.info(json.dumps({"event": "verification_recorded",
                                         "assignment_id": candidate["assignment_id"],
                                         "attempt_id": str(candidate["attempt_id"]),
                                         "decision": decision.status.value}, sort_keys=True))
            except psycopg.Error as exc:
                logging.warning(json.dumps({"event": "verifier_dependency_retry",
                                            "failure": "database_unavailable",
                                            "sqlstate": getattr(exc, "sqlstate", None)}, sort_keys=True))
                stop.wait(2.0)
            except Exception as exc:
                logging.error(json.dumps({"event": "verifier_cycle_failed",
                                          "failure_type": type(exc).__name__}, sort_keys=True))
                stop.wait(1.0)
        return 0
    except WorkerServiceConfigurationError as exc:
        logging.error(json.dumps({"event": "verifier_service_configuration_error",
                                  "failure_code": str(exc)}, sort_keys=True))
        return 2
    except Exception as exc:
        logging.error(json.dumps({"event": "verifier_service_start_failed",
                                  "failure_type": type(exc).__name__}, sort_keys=True))
        return 1
    finally:
        if adapter is not None:
            adapter.close()


if __name__ == "__main__":
    raise SystemExit(main())
