# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/worker.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.4
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-002 | Generate bounded artifacts only from the persisted assignment contract
# Purpose: Provide a bounded local coding-worker artifact action and independent verifier
# Execution Model: Contract-bound private filesystem writes through ContinuousWorker
# Observability: Artifact set, digest, objective reference, and independent decision
# Dependencies: worker-adapter capability registry; Python standard library
# Authority: Persisted assignment contract only; no shell or caller-supplied path
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Initial bounded worker adapter
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Remove trailing whitespace from controlled file
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Bind the bounded worker artifact to the assigned proposal step
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-002 | Derive bounded artifact set identity and storage from the persisted contract
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
import tempfile
from dataclasses import dataclass
from time import monotonic

from ..resident_reasoning import ArtifactRequirement
from ..worker_adapter.knowledge import KnowledgeStatus


CAPABILITY = "engineering.bounded-artifact.v1"
MAX_ARTIFACT_BYTES = 8192
MAX_ARTIFACT_COUNT = 8


@dataclass(frozen=True)
class CodingWorkOrder:
    """Bounded worker request; no arbitrary command or filesystem destination."""

    assignment_id: str
    objective_id: str
    repository_reference: str
    repository_revision: str
    task_scope: str
    acceptance_criteria: tuple[str, ...]
    artifact_requirements: tuple[ArtifactRequirement, ...]
    source_sha256: str
    source_references: tuple[str, ...]
    allowed_operations: tuple[str, ...] = ("write_bounded_json_artifact",)
    timeout_seconds: int = 30

    def __post_init__(self):
        if (not isinstance(self.assignment_id, str) or not self.assignment_id or
                len(self.assignment_id) > 160 or
                not isinstance(self.objective_id, str) or not self.objective_id or
                len(self.objective_id) > 160 or
                not isinstance(self.repository_reference, str) or
                not self.repository_reference.startswith("repo://") or
                not isinstance(self.repository_revision, str) or
                not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.repository_revision) or
                not isinstance(self.task_scope, str) or not self.task_scope or len(self.task_scope) > 2000 or
                not isinstance(self.acceptance_criteria, tuple) or not self.acceptance_criteria or
                any(not isinstance(item, str) or not item or len(item) > 1000
                    for item in self.acceptance_criteria) or
                not isinstance(self.artifact_requirements, tuple) or
                not 1 <= len(self.artifact_requirements) <= MAX_ARTIFACT_COUNT or
                not isinstance(self.source_sha256, str) or
                not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256) or
                not isinstance(self.source_references, tuple) or not self.source_references or
                any(not isinstance(ref, str) or not ref.startswith("repo://") or
                    len(ref) > 512 for ref in self.source_references) or
                any(not isinstance(item, ArtifactRequirement) or
                    item.media_type != "application/json" for item in self.artifact_requirements) or
                len({item.name for item in self.artifact_requirements}) !=
                    len(self.artifact_requirements) or
                len({item.path for item in self.artifact_requirements}) !=
                    len(self.artifact_requirements) or
                self.allowed_operations != ("write_bounded_json_artifact",) or
                type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 90):
            raise ValueError("coding work order exceeds its bounded assignment contract")


class BoundedCodingWorkerError(RuntimeError):
    """The bounded worker could not safely execute or report its action."""


class BoundedLocalCodingWorker:
    """Write an assignment-defined JSON artifact set; never invokes a shell."""

    def __init__(self, objective_store, artifact_root: str | Path):
        self.objective_store = objective_store
        self.artifact_root = Path(artifact_root)

    @staticmethod
    def _storage_name(assignment_id, requirement):
        assignment_key = hashlib.sha256(assignment_id.encode("utf-8")).hexdigest()
        artifact_key = hashlib.sha256(requirement.name.encode("utf-8")).hexdigest()[:12]
        return f"{assignment_key}/{artifact_key}"

    @staticmethod
    def _read(root, storage_name):
        parts = storage_name.split("/") if isinstance(storage_name, str) else []
        if (len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]) or
                not re.fullmatch(r"[0-9a-f]{12}", parts[1])):
            raise BoundedCodingWorkerError("artifact storage identity is invalid")
        root_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                           getattr(os, "O_NOFOLLOW", 0))
        try:
            directory_fd = os.open(parts[0], os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                                   getattr(os, "O_NOFOLLOW", 0), dir_fd=root_fd)
        finally:
            os.close(root_fd)
        try:
            fd = os.open(parts[1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                         dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or
                    not 0 < info.st_size <= MAX_ARTIFACT_BYTES):
                raise BoundedCodingWorkerError("artifact metadata is unsafe")
            raw = os.read(fd, MAX_ARTIFACT_BYTES + 1)
            if len(raw) != info.st_size or len(raw) > MAX_ARTIFACT_BYTES:
                raise BoundedCodingWorkerError("artifact size changed during read")
            return raw
        finally:
            os.close(fd)

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
        raw_contract = step.get("artifact_requirements")
        if not isinstance(raw_contract, list) or not 1 <= len(raw_contract) <= MAX_ARTIFACT_COUNT:
            raise BoundedCodingWorkerError("persisted artifact contract is unavailable")
        try:
            requirements = tuple(ArtifactRequirement(
                item["name"], item["path"], item["media_type"],
                tuple(item["acceptance_criteria"]), item.get("max_bytes", 32768))
                for item in raw_contract)
        except (KeyError, TypeError, ValueError):
            raise BoundedCodingWorkerError("persisted artifact contract is invalid") from None
        canonical = []
        for item in requirements:
            canonical.append({"name": item.name, "path": item.path, "media_type": item.media_type,
                "acceptance_criteria": list(item.acceptance_criteria), "max_bytes": item.max_bytes})
        if canonical != raw_contract:
            raise BoundedCodingWorkerError("persisted artifact contract is not canonical")

        work_order = CodingWorkOrder(
            assignment_id=assignment["id"], objective_id=objective["objective_id"],
            repository_reference=objective["evidence"]["source_references"][0],
            repository_revision=objective["source_revision"], task_scope=step["objective"],
            acceptance_criteria=tuple(step["acceptance_criteria"]),
            artifact_requirements=requirements, source_sha256=objective["source_sha256"],
            source_references=tuple(objective["evidence"]["source_references"]))
        artifact_records = []
        total_bytes = 0
        for requirement in work_order.artifact_requirements:
            record = {
                "artifact_schema": "rv.grace.work-product.v2",
                "artifact_name": requirement.name,
                "artifact_path": requirement.path,
                "media_type": requirement.media_type,
                "objective_id": objective["objective_id"],
                "assignment_id": assignment["id"],
                "work_order_summary": objective["proposal"]["summary"],
                "task": work_order.task_scope,
                "acceptance_criteria": list(requirement.acceptance_criteria),
                "step_acceptance_criteria": list(work_order.acceptance_criteria),
                "repository_reference": work_order.repository_reference,
                "allowed_operations": list(work_order.allowed_operations),
                "timeout_seconds": work_order.timeout_seconds,
                "source_revision": work_order.repository_revision,
                "source_sha256": objective["source_sha256"],
                "source_references": objective["evidence"]["source_references"],
            }
            raw = json.dumps(record, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
            if len(raw) > min(requirement.max_bytes, MAX_ARTIFACT_BYTES):
                raise BoundedCodingWorkerError("artifact exceeds its assigned size limit")
            total_bytes += len(raw)
            if total_bytes > MAX_ARTIFACT_BYTES:
                raise BoundedCodingWorkerError("artifact set exceeds bounded size limit")
            artifact_records.append((requirement, self._storage_name(assignment["id"], requirement), raw))
        if monotonic() - started > work_order.timeout_seconds:
            raise BoundedCodingWorkerError("bounded worker execution timeout exceeded")

        root = self.artifact_root
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root_info = root.lstat()
        if (not stat.S_ISDIR(root_info.st_mode) or root.is_symlink() or
                root_info.st_uid != os.geteuid() or stat.S_IMODE(root_info.st_mode) != 0o700 or
                root.resolve() != root.absolute()):
            raise BoundedCodingWorkerError("artifact workspace is unsafe")
        assignment_key = hashlib.sha256(assignment["id"].encode("utf-8")).hexdigest()
        destination = root / assignment_key
        if destination.exists() or destination.is_symlink():
            try:
                info = destination.lstat()
                if (not stat.S_ISDIR(info.st_mode) or destination.is_symlink() or
                        info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700):
                    raise BoundedCodingWorkerError("existing assignment artifact set is unsafe")
                existing = {path.name for path in destination.iterdir()}
                expected_names = {storage.split("/", 1)[1] for _, storage, _ in artifact_records}
                if existing != expected_names:
                    raise BoundedCodingWorkerError("assignment artifact set is incomplete or expanded")
                for _, storage, raw in artifact_records:
                    if self._read(root, storage) != raw:
                        raise BoundedCodingWorkerError(
                            "assignment artifact already exists with different content")
            except OSError as exc:
                raise BoundedCodingWorkerError("existing assignment artifact set is unsafe") from exc
        else:
            staging = Path(tempfile.mkdtemp(prefix=".bounded-artifact-stage-", dir=root))
            staging.chmod(0o700)
            try:
                for _, storage, raw in artifact_records:
                    filename = storage.split("/", 1)[1]
                    path = staging / filename
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                 getattr(os, "O_NOFOLLOW", 0), 0o600)
                    try:
                        with os.fdopen(fd, "wb") as stream:
                            stream.write(raw)
                            stream.flush()
                            os.fsync(stream.fileno())
                    except BaseException:
                        path.unlink(missing_ok=True)
                        raise
                os.rename(staging, destination)
                root_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(root_fd)
                finally:
                    os.close(root_fd)
            except BaseException:
                if staging.exists():
                    import shutil
                    shutil.rmtree(staging, ignore_errors=True)
                raise
        return self._result(work_order, artifact_records)

    def _result(self, work_order, artifact_records):
        artifacts = tuple({"name": requirement.name, "path": requirement.path,
            "media_type": requirement.media_type, "storage_name": storage,
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "acceptance_criteria": list(requirement.acceptance_criteria)}
            for requirement, storage, raw in artifact_records)
        contract = [{"name": item.name, "path": item.path, "media_type": item.media_type,
            "acceptance_criteria": list(item.acceptance_criteria), "max_bytes": item.max_bytes}
            for item in work_order.artifact_requirements]
        first = artifacts[0]
        return {"status": "SUCCEEDED", "artifact_schema": "rv.grace.artifacts.v2",
            "capability": CAPABILITY, "assignment_id": work_order.assignment_id,
            "objective_id": work_order.objective_id, "artifact_contract": contract,
            "artifacts": list(artifacts), "artifact_name": first["storage_name"],
            "artifact_path": str(self.artifact_root / first["storage_name"]),
            "artifact_sha256": first["sha256"], "artifact_bytes": first["bytes"],
            "source_artifact_name": first["path"],
            "changed_files": sorted(item["path"] for item in contract),
            "source_revision": work_order.repository_revision,
            "source_sha256": work_order.source_sha256,
            "source_references": list(work_order.source_references)}
