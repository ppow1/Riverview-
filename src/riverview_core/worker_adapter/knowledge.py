# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/knowledge.py
# Component: WORKER-ADAPTER
# Revision: 1.0.1
# Purpose: Re-export the versioned fail-closed knowledge-provider interface
# Execution Model: In-process interface invoked by durable worker cycles
# Observability: Machine-readable outcome status and source provenance
# Dependencies: Python 3.10+; standard library
# Authority: Knowledge may inform work; only VERIFIED outcomes authorize a cycle
# Changed: 2026-10-10 UTC | RV-M1.3-CONTINUOUS-KNOWLEDGE | Initial provider contract
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Runtime import location for the frozen knowledge-provider v1 contract."""

from .knowledge_provider_v1.contract import (
    KnowledgeProvider, KnowledgeResult, KnowledgeStatus, UnavailableKnowledgeProvider,
)

__all__ = ["KnowledgeProvider", "KnowledgeResult", "KnowledgeStatus",
           "UnavailableKnowledgeProvider"]
