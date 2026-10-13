#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_grace_execution_service.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.1
# Purpose: Run persistent Grace dispatch, bounded worker, and independent verification cycles
# Execution Model: systemd-supervised repeated PostgreSQL polling
# Observability: Structured sanitized lifecycle logs and existing dashboard/PostgreSQL projections
# Dependencies: PostgreSQL; protected systemd credentials; pinned Riverview release
# Authority: Exact grants for Grace dispatch, executor registration/execution, and verification
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Add supervised runtime entry point
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Bind runtime to current Grace office grant and persisted office state
# Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md
# Tests: tests/test_grace_execution.py; tests/test_resident_reasoning.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Systemd entry point for the persistent model-independent Grace runtime."""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import threading
from pathlib import Path

from riverview_core.assignment_intake import AuthorizedAssignmentIntake
from riverview_core.institutional_authority import AuthorityRegistry, ExactGrantAuthorizer
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.resident_execution import GraceExecutionPipeline
from riverview_core.resident_execution.pipeline import ObjectiveContextReader
from riverview_core.resident_execution.service import GraceExecutionService
from riverview_core.resident_execution.worker import BoundedLocalCodingWorker
from riverview_core.worker_adapter import ContinuousWorker, PostgresWorkerAdapter
from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider
from riverview_core.worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider
from riverview_core.worker_adapter.service import (WorkerServiceConfigurationError,
    ensure_registered, load_runtime_config, read_worker_credential)
from riverview_core.resident_reasoning import ResidentReasoner
from riverview_core.local_reasoning_provider import LocalReasoningProvider

SERVICE_UNIT = "riverview-grace-execution.service"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ledger = adapter = authority_registry = None
    try:
        dsn, schema, authority_schema, worker_id, scope_ref, worker_token = load_runtime_config(
            SERVICE_UNIT, "worker-token")
        dispatch_token = read_worker_credential(SERVICE_UNIT, "dispatch-token")
        verifier_token = read_worker_credential(SERVICE_UNIT, "verifier-token")
        resident_token = read_worker_credential(SERVICE_UNIT, "resident-token")
        office_id = os.environ.get("RIVERVIEW_RESIDENT_OFFICE_ID", "")
        verifier_id = os.environ.get("RIVERVIEW_VERIFIER_ID", "")
        commit = os.environ.get("RIVERVIEW_KNOWLEDGE_COMMIT", "")
        repo_root = Path(os.environ.get("RIVERVIEW_KNOWLEDGE_ROOT", "/opt/riverview-core"))
        artifact_root = Path(os.environ.get("RIVERVIEW_ARTIFACT_DIR", "/var/lib/riverview-grace/artifacts"))
        if (not verifier_id or not office_id.startswith("office:")
                or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit)
                or not scope_ref.startswith("work-order:")):
            raise WorkerServiceConfigurationError("grace_runtime_configuration_invalid")
        ledger = PostgresLedger(dsn, schema=schema)
        adapter = PostgresWorkerAdapter(dsn, schema=schema, authority_schema=authority_schema)
        authorizer = ExactGrantAuthorizer(authority_schema)
        authority_registry = AuthorityRegistry(dsn, schema=authority_schema, runtime_safe=True)
        # Fail startup closed when the configured resident is not the currently bound,
        # explicitly authorized occupant. A service restart reloads the current credential.
        office = authority_registry.authorize_office_state(resident_token, office_id)
        if not office.get("provider_ref"):
            raise WorkerServiceConfigurationError("resident_office_unbound")
        intake = AuthorizedAssignmentIntake(ledger, authorizer)
        resident_knowledge = TaskRelevantRepositoryKnowledgeProvider(repo_root, commit)
        pipeline = GraceExecutionPipeline(ledger, authorizer, intake, resident_knowledge)
        providers = {}
        reasoning_endpoint = os.environ.get("RIVERVIEW_REASONING_ENDPOINT")
        reasoning_model = os.environ.get("RIVERVIEW_REASONING_MODEL")
        reasoning_sha = os.environ.get("RIVERVIEW_REASONING_MODEL_SHA256")
        configured_reasoning = (reasoning_endpoint, reasoning_model, reasoning_sha)
        if any(configured_reasoning) and not all(configured_reasoning):
            raise WorkerServiceConfigurationError("resident_reasoning_provider_incomplete")
        if all(configured_reasoning):
            provider = LocalReasoningProvider(reasoning_endpoint, reasoning_model, reasoning_sha)
            providers[provider.provider_id] = provider
        resident_reasoner = ResidentReasoner(
            registry=authority_registry, office_id=office_id,
            resident_credential=resident_token, assignments=ObjectiveContextReader(pipeline),
            knowledge=resident_knowledge, providers=providers,
            timeout_seconds=float(os.environ.get("RIVERVIEW_RESIDENT_REASONING_TIMEOUT", "5")))
        ensure_registered(adapter, worker_id, worker_token,
            ("engineering.bounded-artifact.v1",), scope_ref)
        ensure_registered(adapter, verifier_id, verifier_token,
            ("assignment.verify.v1",), scope_ref)
        engine = ContinuousWorker(adapter, worker_id, worker_token,
            knowledge=RepositoryKnowledgeProvider(repo_root, commit),
            action=BoundedLocalCodingWorker(pipeline, artifact_root),
            action_effect_class="retry_safe",
            action_capability="engineering.bounded-artifact.v1",
            recovery_max_retries=int(os.environ.get("RIVERVIEW_GRACE_MAX_WORKER_RECOVERIES", "3")))
        service = GraceExecutionService(pipeline, adapter, engine,
            dispatch_credential=dispatch_token, authority_ref=scope_ref,
            verifier_id=verifier_id, verifier_credential=verifier_token,
            artifact_root=artifact_root,
            max_dispatch_failures=int(os.environ.get("RIVERVIEW_GRACE_MAX_DISPATCH_FAILURES", "3")),
            resident_reasoner=resident_reasoner,
            resident_token_budget=int(os.environ.get("RIVERVIEW_RESIDENT_REASONING_TOKENS", "256")))
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        logging.info(json.dumps({"event": "grace_execution_service_started",
            "component_id": "RESIDENT-ORCHESTRATION", "worker_id": worker_id,
            "verifier_id": verifier_id, "resident_office_id": office_id,
            "resident_occupant_id": office["occupant_id"],
            "resident_binding_revision": office["binding_revision"],
            "resident_provider_ref": office["provider_ref"],
            "reasoning_provider_configured": bool(providers),
            "source_revision": commit, "scope_ref": scope_ref},
            sort_keys=True))
        service.run_forever(shutdown_requested=stop.is_set,
            poll_seconds=float(os.environ.get("RIVERVIEW_GRACE_POLL_SECONDS", "1")))
        return 0
    except WorkerServiceConfigurationError as exc:
        logging.error(json.dumps({"event": "grace_service_configuration_error",
                                  "failure_code": str(exc)}, sort_keys=True))
        return 2
    except Exception as exc:
        logging.error(json.dumps({"event": "grace_service_start_failed",
                                  "failure_type": type(exc).__name__}, sort_keys=True))
        return 1
    finally:
        if adapter is not None:
            adapter.close()
        if authority_registry is not None:
            authority_registry.close()
        if ledger is not None:
            ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
