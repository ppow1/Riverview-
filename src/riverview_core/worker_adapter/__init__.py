# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/__init__.py
# Component: WORKER-ADAPTER
# Revision: 1.0.0
# Purpose: Isolated deterministic M2.1 worker interface
# Execution Model: Explicit request-driven PostgreSQL adapter
# Observability: Durable worker registry, attempt and result records
# Dependencies: Python 3.10+; Psycopg 3; M1.2 ledger schema
# Authority: Capability/scoped credential checks; no external worker execution
# Changed: 2026-10-10 UTC | RV-M2.1-001 | Initial package
# Contracts: docs/ROADMAP.md; docs/architecture/CORE_CONTRACT.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Capability-registered deterministic local worker adapter."""

from .adapter import (PostgresWorkerAdapter, WorkerAdapterError,
                      WorkerAuthorizationError, WorkerLeaseLost)

__all__ = ["PostgresWorkerAdapter", "WorkerAdapterError",
           "WorkerAuthorizationError", "WorkerLeaseLost"]
