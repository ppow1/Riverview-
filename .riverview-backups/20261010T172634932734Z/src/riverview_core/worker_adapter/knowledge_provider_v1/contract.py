# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/knowledge_provider_v1/contract.py
# Component: KNOWLEDGE-PROVIDER-CONTRACT
# Revision: 1.0.1
# Purpose: Frozen in-process assignment knowledge-provider contract v1
# Execution Model: Synchronous provider calls at worker execution boundary
# Observability: Typed result statuses and source references
# Dependencies: Python 3.10+; standard library
# Authority: VERIFIED is required to authorize an action; absence is fail-closed
# Changed: 2026-10-10 UTC | RV-KNOWLEDGE-IFACE-001 | Freeze retrieval completeness and provenance validation
# Contracts: interfaces/knowledge-provider-v1/README.md
# Tests: interfaces/knowledge-provider-v1/test_contract.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Version 1 provider protocol shared by Camrui workers and OctoMiner 2."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol


class KnowledgeStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NO_MATCH = "NO_MATCH"
    UNAVAILABLE = "UNAVAILABLE"
    INCOMPLETE = "INCOMPLETE"
    CONTRADICTORY = "CONTRADICTORY"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class KnowledgeResult:
    status: KnowledgeStatus
    value: Any = None
    source_references: tuple[str, ...] = field(default_factory=tuple)
    source_revision: str | None = None
    source_sha256: str | None = None
    retrieval_complete: bool | None = None

    def __post_init__(self):
        if not isinstance(self.status, KnowledgeStatus):
            raise TypeError("status must be a KnowledgeStatus")
        if any(not isinstance(ref, str) or not ref or ".." in ref.split("/")
               for ref in self.source_references):
            raise ValueError("source references must be safe non-empty URIs or repository paths")
        if self.status is KnowledgeStatus.VERIFIED:
            if not self.source_references:
                raise ValueError("VERIFIED requires at least one source reference")
            if self.retrieval_complete is not True:
                raise ValueError("VERIFIED requires retrieval_complete=True")
        if self.status is KnowledgeStatus.INCOMPLETE and self.retrieval_complete is True:
            raise ValueError("INCOMPLETE cannot claim complete retrieval")
        if self.source_sha256 is not None:
            import re
            if not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256):
                raise ValueError("source_sha256 must be 64 lowercase hexadecimal characters")


class KnowledgeProvider(Protocol):
    """Implement all four calls; assignments are read-only mappings from the ledger."""

    def ground_assignment(self, assignment: Mapping[str, Any]) -> KnowledgeResult: ...
    def preflight_action(self, assignment: Mapping[str, Any], action: str) -> KnowledgeResult: ...
    def reground_assignment(self, assignment: Mapping[str, Any], trigger: str) -> KnowledgeResult: ...
    def record_learning(self, assignment: Mapping[str, Any], outcome: Mapping[str, Any]) -> KnowledgeResult: ...


class UnavailableKnowledgeProvider:
    """Default behavior when no provider is configured: every operation is unavailable."""

    @staticmethod
    def _unavailable():
        return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)

    def ground_assignment(self, assignment):
        return self._unavailable()

    def preflight_action(self, assignment, action):
        return self._unavailable()

    def reground_assignment(self, assignment, trigger):
        return self._unavailable()

    def record_learning(self, assignment, outcome):
        return self._unavailable()
