# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/verifier.py
# Component: OUTCOME-VERIFIER
# Revision: 1.0.0
# Purpose: Independently evaluate the deterministic M2.1 artifact contract
# Execution Model: Pure in-process verifier; persistence is owned by adapter
# Observability: Typed decision, criteria, evidence references, verifier revision
# Dependencies: Python 3.10+; standard library
# Authority: Executor output is untrusted until verified independently
# Changed: 2026-10-10 UTC | RV-M2.2-001 | Initial result verifier contract
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Independent result-verification contract and deterministic first verifier."""

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Protocol


class VerificationStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    criteria: Mapping[str, bool]
    evidence_references: tuple[str, ...]
    verifier_revision: str
    summary: str

    def __post_init__(self):
        if not isinstance(self.status, VerificationStatus):
            raise TypeError("status must be a VerificationStatus")
        if not self.verifier_revision or not self.summary:
            raise ValueError("verifier revision and summary are required")
        if not self.criteria or any(type(value) is not bool for value in self.criteria.values()):
            raise ValueError("criteria must contain boolean results")
        if self.status is VerificationStatus.ACCEPTED:
            if not all(self.criteria.values()) or not self.evidence_references:
                raise ValueError("ACCEPTED requires all criteria and evidence references")
        if any(not isinstance(ref, str) or not ref or " " in ref
               for ref in self.evidence_references):
            raise ValueError("evidence references must be non-empty and contain no spaces")


class OutcomeVerifier(Protocol):
    """Implement independently of the execution code and worker identity."""

    def verify(self, assignment: Mapping[str, Any], attempt: Mapping[str, Any],
               result: Mapping[str, Any]) -> VerificationResult: ...


class DeterministicSha256Verifier:
    """Check the documented SHA-256 artifact without trusting its claimed digest."""

    REVISION = "1.0.0"

    def verify(self, assignment, attempt, result):
        shape = (isinstance(result, Mapping) and
                 isinstance(result.get("sha256"), str) and
                 type(result.get("utf8_bytes")) is int and
                 result.get("utf8_bytes", -1) >= 0)
        input_match = bool(shape and result["sha256"] == attempt["input_sha256"])
        canonical_digest = None
        if shape:
            canonical = json.dumps(dict(result), sort_keys=True,
                                   separators=(",", ":")).encode("utf-8")
            canonical_digest = hashlib.sha256(canonical).hexdigest()
        stored_digest_match = bool(canonical_digest and
                                   canonical_digest == attempt["result_sha256"])
        criteria = {
            "attempt_succeeded": attempt.get("status") == "succeeded",
            "result_shape_valid": shape,
            "output_matches_input_digest": input_match,
            "stored_result_digest_valid": stored_digest_match,
        }
        accepted = all(criteria.values())
        return VerificationResult(
            VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria,
            (f"urn:rv:worker-attempt:{attempt['attempt_id']}",
             "repo://src/riverview_core/worker_adapter/adapter.py"),
            self.REVISION,
            "all deterministic artifact checks passed" if accepted else
            "one or more deterministic artifact checks failed",
        )
