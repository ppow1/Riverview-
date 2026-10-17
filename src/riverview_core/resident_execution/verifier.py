# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/verifier.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Independently reopen and validate bounded Grace worker artifacts
# Execution Model: Read-only in-process verification separated from worker action
# Observability: Per-criterion decision and artifact/attempt evidence references
# Dependencies: worker-adapter VerificationResult contract; Python standard library
# Authority: Worker output is untrusted until independently reopened and accepted
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Add distinct artifact verifier implementation
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: tests/test_grace_execution.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Read-only artifact verification; does not share worker file-reading helpers."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

from ..worker_adapter.verifier import VerificationResult, VerificationStatus
from .worker import CAPABILITY, MAX_ARTIFACT_BYTES


class BoundedArtifactVerifier:
    """Verify assignment binding, content digest, work criteria, and provenance."""

    REVISION = "1.0.0"
    _NAME = re.compile(r"^grace-work-[0-9a-f]{64}\.json$")

    def __init__(self, artifact_root: str | Path):
        self.artifact_root = Path(artifact_root)

    def _read(self, name):
        path = self.artifact_root / name
        if path.parent != self.artifact_root or path.is_symlink():
            raise OSError("unsafe artifact reference")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or
                    not 0 < info.st_size <= MAX_ARTIFACT_BYTES):
                raise OSError("artifact metadata is unsafe")
            raw = os.read(fd, MAX_ARTIFACT_BYTES + 1)
            if len(raw) != info.st_size or len(raw) > MAX_ARTIFACT_BYTES:
                raise OSError("artifact size changed during read")
            return raw
        finally:
            os.close(fd)

    def verify(self, assignment, attempt, result):
        result = result if isinstance(result, dict) else {}
        criteria = {
            "attempt_succeeded": attempt.get("status") == "succeeded",
            "executor_capability_matches": attempt.get("capability") == CAPABILITY,
            "worker_report_succeeded": result.get("status") == "SUCCEEDED",
            "assignment_contract_matches": assignment.get("contract_ref") ==
                "repo://riverview/worker-adapter-contract.v1",
            "artifact_reference_is_safe": False,
            "artifact_digest_matches": False,
            "work_product_is_complete": False,
            "source_provenance_present": False,
        }
        evidence = (f"urn:rv:worker-attempt:{attempt.get('attempt_id', 'unknown')}",)
        name = result.get("artifact_name")
        try:
            root_stat = self.artifact_root.lstat()
            criteria["artifact_reference_is_safe"] = (
                stat.S_ISDIR(root_stat.st_mode) and not self.artifact_root.is_symlink() and
                root_stat.st_uid == os.geteuid() and stat.S_IMODE(root_stat.st_mode) == 0o700 and
                self.artifact_root.resolve() == self.artifact_root.absolute())
            if criteria["artifact_reference_is_safe"] and isinstance(name, str) and self._NAME.fullmatch(name):
                raw = self._read(name)
                criteria["artifact_digest_matches"] = (
                    hashlib.sha256(raw).hexdigest() == result.get("artifact_sha256") and
                    len(raw) == result.get("artifact_bytes"))
                if criteria["artifact_digest_matches"]:
                    artifact = json.loads(raw)
                    if not isinstance(artifact, dict):
                        raise ValueError("artifact root must be an object")
                    repository_reference = artifact.get("repository_reference")
                    criteria["work_product_is_complete"] = bool(
                        artifact.get("artifact_schema") == "rv.grace.work-product.v1" and
                        artifact.get("assignment_id") == assignment.get("id") and
                        artifact.get("objective_id") == assignment.get("objective_ref") and
                        artifact.get("task") and artifact.get("acceptance_criteria") and
                        artifact.get("allowed_operations") == ["write_bounded_json_artifact"] and
                        artifact.get("timeout_seconds") == 30 and
                        isinstance(repository_reference, str) and
                        repository_reference.startswith("repo://"))
                    criteria["source_provenance_present"] = bool(
                        re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",
                                     artifact.get("source_revision", "")) and
                        re.fullmatch(r"[0-9a-f]{64}", artifact.get("source_sha256", "")) and
                        artifact.get("source_references"))
                    evidence += (f"workspace://{name}",)
        except (OSError, ValueError, UnicodeDecodeError):
            pass
        accepted = all(criteria.values())
        return VerificationResult(
            VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria, evidence, self.REVISION,
            "bounded work product independently verified" if accepted else
            "bounded work product failed independent verification")
