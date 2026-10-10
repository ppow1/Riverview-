# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/knowledge.py
# Component: WORKER-ADAPTER
# Revision: 1.0.0
# Purpose: Define a replaceable, fail-closed in-process assignment knowledge boundary
# Execution Model: In-process interface invoked by durable worker cycles
# Observability: Machine-readable outcome status and source provenance
# Dependencies: Python 3.10+; standard library
# Authority: Knowledge may inform work; only VERIFIED outcomes authorize a cycle
# Changed: 2026-10-10 UTC | RV-M1.3-CONTINUOUS-KNOWLEDGE | Initial provider contract
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Small replaceable knowledge-provider contract; the default provider fails closed."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class KnowledgeStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NO_MATCH = "NO_MATCH"
    UNAVAILABLE = "UNAVAILABLE"
    INCOMPLETE = "INCOMPLETE"
    CONTRADICTORY = "CONTRADICTORY"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class KnowledgeResult:
    """Provider response with optional actionable value and verifiable provenance."""

    status: KnowledgeStatus
    value: Any = None
    source_references: tuple[str, ...] = field(default_factory=tuple)
    source_revision: str | None = None
    source_sha256: str | None = None

    def __post_init__(self):
        if not isinstance(self.status, KnowledgeStatus):
            raise TypeError("status must be a KnowledgeStatus")
        if any(not isinstance(ref, str) or not ref for ref in self.source_references):
            raise ValueError("source references must be non-empty strings")


class KnowledgeProvider(Protocol):
    """Replaceable local boundary; no repository or network implementation is implied."""

    def ground_assignment(self, assignment: dict) -> KnowledgeResult: ...
    def preflight_action(self, assignment: dict, action: str) -> KnowledgeResult: ...
    def reground_assignment(self, assignment: dict, trigger: str) -> KnowledgeResult: ...
    def record_learning(self, assignment: dict, outcome: dict) -> KnowledgeResult: ...


class UnavailableKnowledgeProvider:
    """Explicitly report that no knowledge source is configured."""

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
