# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/__init__.py
# Component: WORKER-ADAPTER
# Revision: 1.0.3
# Purpose: Export execution, knowledge, and independent verification contracts
# Execution Model: In-process package boundary over durable PostgreSQL adapters
# Observability: Durable worker, attempt, result, verification, and knowledge records
# Dependencies: Python 3.10+; Psycopg 3; PostgreSQL ledger/scheduler
# Authority: Scoped credentials; no action without verified knowledge preflight
# Changed: 2026-10-10 UTC | RV-M2.3-001 | Export PostgreSQL recovery coordinator
# Contracts: docs/ROADMAP.md; docs/architecture/CORE_CONTRACT.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Capability-registered deterministic local worker adapter."""

from .adapter import (PostgresWorkerAdapter, WorkerAdapterError,
                      WorkerAuthorizationError, WorkerLeaseLost)
from .continuous import ContinuousWorker
from .recovery import PostgresRecoveryCoordinator
from .knowledge import KnowledgeResult, KnowledgeStatus, UnavailableKnowledgeProvider
from .verifier import (DeterministicSha256Verifier, OutcomeVerifier,
                       VerificationResult, VerificationStatus)

__all__ = ["PostgresWorkerAdapter", "WorkerAdapterError",
           "WorkerAuthorizationError", "WorkerLeaseLost", "ContinuousWorker",
           "PostgresRecoveryCoordinator",
           "KnowledgeResult", "KnowledgeStatus", "UnavailableKnowledgeProvider",
           "DeterministicSha256Verifier", "OutcomeVerifier", "VerificationResult",
           "VerificationStatus"]
