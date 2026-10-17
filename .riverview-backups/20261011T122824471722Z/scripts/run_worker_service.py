#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_worker_service.py
# Component: WORKER-ADAPTER
# Revision: 1.0.1
# Purpose: Run a fixed repository engineering test action as a supervised service
# Execution Model: Persistent scheduler polling with durable PostgreSQL attempts
# Observability: Structured status-only logs, lease and knowledge provenance
# Dependencies: Psycopg; systemd credentials; pinned repository package
# Authority: Exact worker.register and assignment.execute grants are mandatory
# Changed: 2026-10-11 UTC | RV-M3.3-WORKER-SERVICE | Initial executor service runner
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Execute the fixed repository regression task and persist its report artifact
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_service.py; tests/test_worker_adapter.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Start one exact-scope executor using a commit-pinned repository provider."""

import json
import logging
import os
import re
import signal
import threading

from riverview_core.worker_adapter import ContinuousWorker, PostgresWorkerAdapter
from riverview_core.worker_adapter.engineering_artifact import (
    CAPABILITY, RepositoryContractTestAction,
)
from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider
from riverview_core.worker_adapter.service import (
    WorkerServiceConfigurationError, ensure_registered, load_runtime_config,
)

SERVICE_UNIT = "riverview-m33-worker.service"
def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    adapter = None
    try:
        dsn, schema, authority_schema, worker_id, scope_ref, token = load_runtime_config(
            SERVICE_UNIT, "worker-token")
        commit = os.environ.get("RIVERVIEW_KNOWLEDGE_COMMIT", "")
        root = os.environ.get("RIVERVIEW_KNOWLEDGE_ROOT", "/opt/riverview-m33/current")
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise WorkerServiceConfigurationError("knowledge_pin_invalid")
        adapter = PostgresWorkerAdapter(dsn, schema=schema, authority_schema=authority_schema)
        ensure_registered(adapter, worker_id, token, (CAPABILITY,), scope_ref)
        provider = RepositoryKnowledgeProvider(root, commit)
        action = RepositoryContractTestAction(
            root, os.environ.get("RIVERVIEW_ARTIFACT_DIR",
                                 "/var/lib/riverview-m33-worker/artifacts"), commit)
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        engine = ContinuousWorker(adapter, worker_id, token, knowledge=provider,
                                  action=action, action_effect_class="retry_safe",
                                  action_capability=CAPABILITY)
        logging.info(json.dumps({"event": "worker_service_started",
                                 "worker_id": worker_id, "capability": CAPABILITY,
                                 "source_revision": commit, "schema": schema}, sort_keys=True))
        engine.run_forever(shutdown_requested=stop.is_set)
        return 0
    except WorkerServiceConfigurationError as exc:
        logging.error(json.dumps({"event": "worker_service_configuration_error",
                                  "failure_code": str(exc)}, sort_keys=True))
        return 2
    except Exception as exc:
        logging.error(json.dumps({"event": "worker_service_start_failed",
                                  "failure_type": type(exc).__name__}, sort_keys=True))
        return 1
    finally:
        if adapter is not None:
            adapter.close()


if __name__ == "__main__":
    raise SystemExit(main())
