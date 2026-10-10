# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: interfaces/knowledge-provider-v1/__init__.py
# Component: KNOWLEDGE-PROVIDER-CONTRACT
# Revision: 1.0.0
# Purpose: Public exports for the frozen knowledge-provider v1 contract
# Execution Model: In-process interface package
# Observability: Parent contract result types
# Dependencies: contract.py
# Authority: No action authorization beyond VERIFIED contract status
# Changed: 2026-10-10 UTC | RV-KNOWLEDGE-IFACE-001 | Initial interface package
# Contracts: interfaces/knowledge-provider-v1/README.md
# Tests: interfaces/knowledge-provider-v1/test_contract.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
from .contract import KnowledgeProvider, KnowledgeResult, KnowledgeStatus, UnavailableKnowledgeProvider

__all__ = ["KnowledgeProvider", "KnowledgeResult", "KnowledgeStatus",
           "UnavailableKnowledgeProvider"]
