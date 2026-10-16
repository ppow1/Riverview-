# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/codex_workflow.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.2.0
# Purpose: Adapt bounded Codex production and independent Markdown verification to CME
# Execution Model: Existing leased worker action and independent verifier contract
# Observability: Persisted artifact location, digest, criteria and verifier evidence
# Dependencies: Codex CLI adapter; PostgreSQL objective/attempt/verification records
# Authority: Requires registered engineering.codex-cli-artifact.v1 worker and assignment.execute
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Initial persistent worker/verifier adapters
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Separate evidence provenance from the Codex repository pin and retain process-start status
# Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Validate objective evidence against its immutable provenance, independently of current grounding revision
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_codex_workflow.py
# History: Git
# =============================================================================
"""Narrow Codex action and independent verifier for the existing CME path."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
from collections.abc import Mapping

from ..worker_adapter.knowledge import KnowledgeStatus
from ..worker_adapter.verifier import VerificationResult, VerificationStatus
from .codex_cli import CAPABILITY, CodexAssignment, CodexCLIExecutionAdapter

CAPABILITY_REQUIREMENTS = {
    "capability": CAPABILITY,
    "dependencies": ("dedicated_codex_executable", "dedicated_codex_home",
                     "pinned_local_repository", "isolated_workspace", "artifact_filesystem"),
    "authority_actions": ("worker.register", "assignment.execute", "assignment.verify"),
    "readiness": "startup_preflight_and_current_worker_heartbeat",
}


class CodexActionFailure(RuntimeError):
    """Sanitized action failure with an explicit external-effect boundary."""

    def __init__(self, code, *, execution_started=False):
        self.execution_started = bool(execution_started)
        super().__init__(code)


class CodexWorkAction:
    """Build a fixed adapter request from a persisted, authorized objective."""

    def __init__(self, pipeline, adapter: CodexCLIExecutionAdapter,
                 repository_reference: str, timeout_seconds: int = 180):
        if (not isinstance(adapter, CodexCLIExecutionAdapter) or
                not isinstance(repository_reference, str) or
                not repository_reference.startswith("repo://") or
                type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300):
            raise ValueError("Codex work action configuration is invalid")
        self.pipeline = pipeline
        self.adapter = adapter
        self.repository_reference = repository_reference
        self.timeout_seconds = timeout_seconds

    def __call__(self, assignment, grounded):
        if (grounded.status is not KnowledgeStatus.VERIFIED or
                grounded.retrieval_complete is not True or
                not grounded.source_revision or not grounded.source_sha256):
            raise CodexActionFailure("verified_regrounding_required")
        objective_id = assignment.get("objective_ref")
        objective = self.pipeline.get_objective(objective_id)
        evidence = objective.get("evidence") if isinstance(objective, Mapping) else None
        if (not objective or objective["status"] != "WORK_ORDER_CREATED" or
                objective["assignment_id"] != assignment.get("id") or
                not isinstance(evidence, Mapping) or
                evidence.get("status") != KnowledgeStatus.VERIFIED.value or
                objective.get("source_revision") != evidence.get("source_revision") or
                objective.get("source_sha256") != evidence.get("source_sha256") or
                not objective.get("proposal")):
            raise CodexActionFailure("persisted_work_order_provenance_required")
        step = objective["proposal"]["steps"][0]
        try:
            repository_revision = self.adapter.repository_revision()
        except Exception as exc:
            code = getattr(exc, "code", "repository_preflight_failed")
            raise CodexActionFailure(code) from None
        request = CodexAssignment(
            assignment_id=assignment["id"], objective_id=objective_id,
            repository_reference=self.repository_reference,
            # Knowledge-source provenance and the code revision used to execute
            # the assignment are separate immutable facts.
            repository_revision=repository_revision,
            task_scope=step["objective"],
            acceptance_criteria=tuple(step["acceptance_criteria"]),
            timeout_seconds=self.timeout_seconds)
        result = self.adapter.execute(request)
        if result.status != "DELIVERABLE_PRODUCED" or not result.artifact_name:
            raise CodexActionFailure(result.detail_code,
                                     execution_started=result.execution_started)
        artifact_path = self.adapter.artifact_root / result.artifact_name
        return {
            "status": "SUCCEEDED", "artifact_schema": "rv.codex-cli.deliverable.v2",
            "capability": CAPABILITY, "assignment_id": assignment["id"],
            "objective_id": objective_id, "artifact_name": result.artifact_name,
            "artifact_path": str(artifact_path),
            "artifact_sha256": result.artifact_sha256,
            "artifact_bytes": result.artifact_bytes,
            "source_revision": grounded.source_revision,
            "source_sha256": grounded.source_sha256,
            "repository_revision": result.repository_revision,
            "acceptance_criteria": list(request.acceptance_criteria),
            "detail_code": result.detail_code,
        }

    def reconcile_legacy_preexecution_failures(self, recovery):
        """Use existing CME recovery only when the predecessor Git refusal is reproduced."""
        if not self.adapter.legacy_git_ownership_refused():
            return []
        try:
            repository_revision = self.adapter.repository_revision()
        except Exception:
            return []
        return recovery.reconcile_confirmed_codex_preexecution_failures(
            repository_revision=repository_revision,
            artifact_root=self.adapter.artifact_root,
            legacy_git_refusal_verified=True)


class CodexMarkdownVerifier:
    """Independently reopen artifact and verify assignment binding, digest and contract."""

    REVISION = "1.0.0"
    MAX_BYTES = 32 * 1024
    _NAME = re.compile(r"^codex-[0-9a-f]{64}\.md$")

    def __init__(self, artifact_root: str | Path):
        self.artifact_root = Path(artifact_root)

    def verify(self, assignment, attempt, result):
        name = result.get("artifact_name") if isinstance(result, dict) else None
        attempt_id = attempt.get("attempt_id", "unknown")
        evidence = (f"urn:rv:worker-attempt:{attempt_id}",)
        criteria = {
            "attempt_succeeded": attempt.get("status") == "succeeded",
            "executor_capability_matches": attempt.get("capability") == CAPABILITY,
            "result_is_codex_deliverable": isinstance(result, dict) and
                result.get("status") == "SUCCEEDED" and
                result.get("artifact_schema") == "rv.codex-cli.deliverable.v2",
            "artifact_path_is_assignment_bound": False,
            "artifact_owner_mode_and_size_valid": False,
            "artifact_digest_matches": False,
            "markdown_deliverable_matches_objective": False,
            "acceptance_criteria_are_present": False,
            "source_provenance_is_pinned": False,
            "repository_provenance_is_pinned": False,
        }
        raw = None
        expected_name = "codex-" + hashlib.sha256(
            assignment["id"].encode("utf-8")).hexdigest() + ".md"
        path = self.artifact_root / expected_name
        criteria["artifact_path_is_assignment_bound"] = bool(
            name == expected_name and self._NAME.fullmatch(str(name)) and
            result.get("artifact_path") == str(path))
        try:
            root_info = self.artifact_root.lstat()
            safe_root = (stat.S_ISDIR(root_info.st_mode) and
                not self.artifact_root.is_symlink() and
                root_info.st_uid == os.geteuid() and
                stat.S_IMODE(root_info.st_mode) == 0o700 and
                self.artifact_root.resolve() == self.artifact_root.absolute())
            if safe_root and criteria["artifact_path_is_assignment_bound"]:
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                try:
                    info = os.fstat(fd)
                    criteria["artifact_owner_mode_and_size_valid"] = (
                        stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and
                        stat.S_IMODE(info.st_mode) == 0o600 and
                        0 < info.st_size <= self.MAX_BYTES)
                    raw = os.read(fd, self.MAX_BYTES + 1)
                finally:
                    os.close(fd)
                criteria["artifact_digest_matches"] = bool(
                    raw is not None and len(raw) <= self.MAX_BYTES and
                    len(raw) == result.get("artifact_bytes") and
                    hashlib.sha256(raw).hexdigest() == result.get("artifact_sha256"))
                if criteria["artifact_digest_matches"]:
                    body = raw.decode("utf-8")
                    criteria["markdown_deliverable_matches_objective"] = bool(
                        body.startswith("# ") and assignment.get("objective_ref") ==
                        result.get("objective_id") and body.strip())
                    criteria["acceptance_criteria_are_present"] = bool(
                        result.get("acceptance_criteria") and all(
                            isinstance(item, str) and item in body
                            for item in result["acceptance_criteria"]))
                    evidence += ("workspace://" + name,
                                 "sha256:" + result["artifact_sha256"])
            criteria["source_provenance_is_pinned"] = bool(
                re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",
                             str(result.get("source_revision", ""))) and
                re.fullmatch(r"[0-9a-f]{64}",
                             str(result.get("source_sha256", ""))))
        except (OSError, UnicodeError, ValueError):
            pass
        criteria["repository_provenance_is_pinned"] = bool(
            isinstance(result, dict) and
            re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",
                         str(result.get("repository_revision", ""))))
        accepted = all(criteria.values())
        return VerificationResult(
            VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria, evidence if raw is not None else evidence[:1], self.REVISION,
            "Codex Markdown artifact independently verified" if accepted else
            "Codex Markdown artifact failed independent verification")
