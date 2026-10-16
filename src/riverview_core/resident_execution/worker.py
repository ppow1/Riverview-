# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/worker.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.2
# Purpose: Provide a bounded local coding-worker artifact action and independent verifier
# Execution Model: Fixed local filesystem write through the existing ContinuousWorker
# Observability: Artifact name, digest, objective reference, and independent decision
# Dependencies: worker-adapter capability registry; Python standard library
# Authority: One assignment-bound JSON artifact only; no shell or caller-supplied path
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Initial bounded worker adapter
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Remove trailing whitespace from controlled file
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Bind the bounded worker artifact to the assigned proposal step
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: tests/test_grace_execution.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Bounded artifact worker action; execution is still fenced by CME leases."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from dataclasses import dataclass
from time import monotonic

from ..worker_adapter.knowledge import KnowledgeStatus


CAPABILITY = "engineering.bounded-artifact.v1"
MAX_ARTIFACT_BYTES = 8192


@dataclass(frozen=True)
class CodingWorkOrder:
    """Bounded worker request; no arbitrary command or filesystem destination."""

    assignment_id: str
    objective_id: str
    repository_reference: str
    repository_revision: str
    task_scope: str
    acceptance_criteria: tuple[str, ...]
    allowed_operations: tuple[str, ...] = ("write_bounded_json_artifact",)
    timeout_seconds: int = 30

    def __post_init__(self):
        if (not self.assignment_id or not self.objective_id or
                not self.repository_reference.startswith("repo://") or
                not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.repository_revision) or
                not self.task_scope or len(self.task_scope) > 2000 or
                not self.acceptance_criteria or
                any(not item or len(item) > 1000 for item in self.acceptance_criteria) or
                self.allowed_operations != ("write_bounded_json_artifact",) or
                type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 90):
            raise ValueError("coding work order exceeds the fixed artifact-worker contract")


class BoundedCodingWorkerError(RuntimeError):
    """The bounded worker could not safely execute or report its fixed action."""


class BoundedLocalCodingWorker:
    """Write one assignment-bound JSON work product; never invokes a shell.

    This is a deterministic local test/initial adapter, not an LLM coding worker.
    Later executors can implement the same action boundary while the scheduler,
    assignment lease, authority, and verifier contracts remain unchanged.
    """

    def __init__(self, objective_store, artifact_root: str | Path):
        self.objective_store = objective_store
        self.artifact_root = Path(artifact_root)

    def __call__(self, assignment, grounded):
        started = monotonic()
        if (grounded.status is not KnowledgeStatus.VERIFIED or
                grounded.retrieval_complete is not True or
                grounded.source_revision is None or not grounded.source_references):
            raise BoundedCodingWorkerError("verified repository grounding required")
        objective = self.objective_store.get_objective(assignment.get("objective_ref"))
        if (not objective or objective["status"] != "WORK_ORDER_CREATED" or
                objective["assignment_id"] != assignment.get("id") or
                objective["evidence"]["status"] != KnowledgeStatus.VERIFIED.value):
            raise BoundedCodingWorkerError("persisted authorized work order required")
        if objective["evidence"]["source_revision"] != grounded.source_revision:
            raise BoundedCodingWorkerError("worker evidence revision mismatch")
        step = self.objective_store.proposal_step_for_assignment(
            objective["objective_id"], assignment.get("id"))
        if step is None and len(objective["proposal"]["steps"]) == 1:
            step = objective["proposal"]["steps"][0]
        if step is None:
            raise BoundedCodingWorkerError("persisted assignment step is unavailable")
        work_order = CodingWorkOrder(
            assignment_id=assignment["id"], objective_id=objective["objective_id"],
            repository_reference=objective["evidence"]["source_references"][0],
            repository_revision=objective["source_revision"],
            task_scope=step["objective"],
            acceptance_criteria=tuple(step["acceptance_criteria"]))

        root = self.artifact_root
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root_info = root.lstat()
        if (not stat.S_ISDIR(root_info.st_mode) or root.is_symlink() or
                root_info.st_uid != os.geteuid() or stat.S_IMODE(root_info.st_mode) != 0o700 or
                root.resolve() != root.absolute()):
            raise BoundedCodingWorkerError("artifact workspace is unsafe")
        artifact = {
            "artifact_schema": "rv.grace.work-product.v1",
            "objective_id": objective["objective_id"],
            "assignment_id": assignment["id"],
            "work_order_summary": objective["proposal"]["summary"],
            "task": work_order.task_scope,
            "acceptance_criteria": list(work_order.acceptance_criteria),
            "repository_reference": work_order.repository_reference,
            "allowed_operations": list(work_order.allowed_operations),
            "timeout_seconds": work_order.timeout_seconds,
            "source_revision": work_order.repository_revision,
            "source_sha256": objective["source_sha256"],
            "source_references": objective["evidence"]["source_references"],
        }
        raw = json.dumps(artifact, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise BoundedCodingWorkerError("artifact exceeds fixed size limit")
        if monotonic() - started > work_order.timeout_seconds:
            raise BoundedCodingWorkerError("bounded worker execution timeout exceeded")
        filename = "grace-work-" + hashlib.sha256(assignment["id"].encode()).hexdigest() + ".json"
        destination = root / filename
        try:
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            prior = self._read(destination)
            if prior == raw:
                return self._result(filename, raw, artifact)
            raise BoundedCodingWorkerError("assignment artifact already exists with different content")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return self._result(filename, raw, artifact)

    @staticmethod
    def _result(filename, raw, artifact):
        report = {"status": "SUCCEEDED",
                "artifact_schema": artifact["artifact_schema"],
                "artifact_name": filename,
                "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                "artifact_bytes": len(raw),
                "objective_id": artifact["objective_id"],
                "source_revision": artifact["source_revision"],
                "source_sha256": artifact["source_sha256"],
                "allowed_operations": artifact["allowed_operations"],
                "timeout_seconds": artifact["timeout_seconds"]}
        return report

    @staticmethod
    def _read(path):
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or
                info.st_size <= 0 or info.st_size > MAX_ARTIFACT_BYTES):
            raise BoundedCodingWorkerError("existing artifact path or size is invalid")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            raw = os.read(fd, MAX_ARTIFACT_BYTES + 1)
        finally:
            os.close(fd)
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise BoundedCodingWorkerError("existing artifact exceeds fixed size limit")
        return raw
