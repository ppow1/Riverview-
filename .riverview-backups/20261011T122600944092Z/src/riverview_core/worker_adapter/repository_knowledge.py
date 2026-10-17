# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/repository_knowledge.py
# Component: REPOSITORY-KNOWLEDGE-PROVIDER
# Revision: 1.0.0
# Purpose: Provide bounded, commit-pinned retrieval of approved worker contracts
# Execution Model: Synchronous in-process read-only provider
# Observability: KnowledgeResult status, source refs, pinned commit and SHA-256
# Dependencies: Python 3.10+; Git; knowledge-provider v1 contract
# Authority: Read-only knowledge; never grants identity or assignment authority
# Changed: 2026-10-11 UTC | RV-M3.3-REPOSITORY-KNOWLEDGE | Initial bounded provider
# Contracts: docs/components/WORKER_ADAPTER.md; knowledge-provider v1 contract
# Tests: tests/test_repository_knowledge.py; tests/test_worker_adapter.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Read approved repository contract material pinned to one clean Git commit.

This provider is deliberately narrow. It can supply the worker's exact
deterministic adapter contract, but it is not a general search engine, policy
engine, or learning store. Its VERIFIED result proves retrieval of the
configured sources at the configured commit; it does not prove the action is
authorized or that its output is acceptable.
"""

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .knowledge_provider_v1.contract import KnowledgeResult, KnowledgeStatus


class RepositoryKnowledgeProvider:
    """Retrieve the pinned worker contract from a clean local Git checkout."""

    WORKER_CONTRACT = "repo://riverview/worker-adapter-contract.v1"
    CONTRACTS = {
        WORKER_CONTRACT: (
            "docs/components/WORKER_ADAPTER.md",
            "src/riverview_core/worker_adapter/adapter.py",
            "src/riverview_core/worker_adapter/continuous.py",
            "src/riverview_core/worker_adapter/knowledge_provider_v1/contract.py",
            "src/riverview_core/worker_adapter/repository_knowledge.py",
        )
    }
    ACTIONS = {"deterministic.sha256.v1": WORKER_CONTRACT}
    MAX_SOURCE_BYTES = 256 * 1024
    MAX_TOTAL_BYTES = 768 * 1024

    def __init__(self, repository: str | Path, approved_commit: str):
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", approved_commit or ""):
            raise ValueError("approved_commit must be a full lowercase Git commit ID")
        root = Path(repository).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("repository must be a directory")
        self.root = root
        self.approved_commit = approved_commit

    def _git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3,
        ).stdout

    def _package_sources(self, paths):
        manifest_path = self.root / "PACKAGE_SHA256SUMS"
        source_path = self.root / "SOURCE_COMMIT"
        if not (manifest_path.is_file() and source_path.is_file()):
            return None
        source_revision = source_path.read_text(encoding="ascii").strip()
        if source_revision != self.approved_commit:
            return (KnowledgeStatus.UNVERIFIED, source_revision, None)
        checksums = {}
        for line in manifest_path.read_text(encoding="ascii").splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._/-]+)", line)
            if not match or match.group(2) in checksums:
                return (KnowledgeStatus.UNVERIFIED, source_revision, None)
            checksums[match.group(2)] = match.group(1)
        documents, total = [], 0
        digest = hashlib.sha256()
        for relative in paths:
            candidate = self.root / relative
            try:
                resolved = candidate.resolve(strict=True)
                if not resolved.is_relative_to(self.root) or candidate.is_symlink() or not candidate.is_file():
                    return (KnowledgeStatus.UNAVAILABLE, source_revision, None)
                raw = candidate.read_bytes()
                expected = checksums.get(relative)
                if expected is None or hashlib.sha256(raw).hexdigest() != expected:
                    return (KnowledgeStatus.UNVERIFIED, source_revision, None)
                total += len(raw)
                if len(raw) > self.MAX_SOURCE_BYTES or total > self.MAX_TOTAL_BYTES:
                    return (KnowledgeStatus.INCOMPLETE, source_revision, None)
                content = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                return (KnowledgeStatus.UNAVAILABLE, source_revision, None)
            reference = f"repo://{relative}"
            digest.update(relative.encode("utf-8") + b"\0" + raw + b"\0")
            documents.append({"reference": reference, "content": content})
        return (KnowledgeStatus.VERIFIED, source_revision,
                (documents, digest.hexdigest()))

    @staticmethod
    def _result(status, *, refs=(), revision=None, digest=None, complete=None, value=None):
        return KnowledgeResult(status, value=value, source_references=tuple(refs),
                               source_revision=revision, source_sha256=digest,
                               retrieval_complete=complete)

    def _retrieve(self, contract_ref: str) -> KnowledgeResult:
        paths = self.CONTRACTS.get(contract_ref)
        if paths is None:
            return self._result(KnowledgeStatus.NO_MATCH, complete=True)
        try:
            package_result = self._package_sources(paths)
            if package_result is not None:
                status, source_revision, payload = package_result
                if status is not KnowledgeStatus.VERIFIED:
                    return self._result(status, revision=source_revision,
                                        complete=False if status is not KnowledgeStatus.UNAVAILABLE else None)
                documents, source_digest = payload
                return self._result(
                    KnowledgeStatus.VERIFIED,
                    refs=(item["reference"] for item in documents), revision=source_revision,
                    digest=source_digest, complete=True,
                    value={"contract_ref": contract_ref, "documents": documents},
                )
            head = self._git("rev-parse", "--verify", "HEAD^{commit}").decode().strip()
            if head != self.approved_commit:
                return self._result(KnowledgeStatus.UNVERIFIED, revision=head, complete=False)
            dirty = self._git("status", "--porcelain", "--untracked-files=no", "--", *paths)
            if dirty:
                return self._result(KnowledgeStatus.UNVERIFIED, revision=head, complete=False)
            documents = []
            total = 0
            digest = hashlib.sha256()
            for relative in paths:
                raw = self._git("show", f"{head}:{relative}")
                if len(raw) > self.MAX_SOURCE_BYTES or total + len(raw) > self.MAX_TOTAL_BYTES:
                    return self._result(KnowledgeStatus.INCOMPLETE,
                                        revision=head, complete=False)
                total += len(raw)
                content = raw.decode("utf-8")
                ref = f"repo://{relative}"
                digest.update(relative.encode("utf-8") + b"\0" + raw + b"\0")
                documents.append({"reference": ref, "content": content})
            return self._result(
                KnowledgeStatus.VERIFIED,
                refs=(item["reference"] for item in documents), revision=head,
                digest=digest.hexdigest(), complete=True,
                value={"contract_ref": contract_ref, "documents": documents},
            )
        except (OSError, subprocess.SubprocessError, UnicodeDecodeError, ValueError):
            return self._result(KnowledgeStatus.UNAVAILABLE, complete=None)

    def ground_assignment(self, assignment: Mapping[str, Any]) -> KnowledgeResult:
        if not isinstance(assignment, Mapping):
            return self._result(KnowledgeStatus.UNVERIFIED, complete=False)
        contract_ref = assignment.get("contract_ref")
        if not isinstance(contract_ref, str) or not contract_ref:
            return self._result(KnowledgeStatus.NO_MATCH, complete=True)
        return self._retrieve(contract_ref)

    def preflight_action(self, assignment: Mapping[str, Any], action: str) -> KnowledgeResult:
        if not isinstance(assignment, Mapping) or not isinstance(action, str) or not action:
            return self._result(KnowledgeStatus.UNVERIFIED, complete=False)
        expected = self.ACTIONS.get(action)
        if expected is None:
            return self._result(KnowledgeStatus.NO_MATCH, complete=True)
        if assignment.get("contract_ref") != expected:
            return self._result(KnowledgeStatus.CONTRADICTORY, complete=True)
        return self._retrieve(expected)

    def reground_assignment(self, assignment: Mapping[str, Any], trigger: str) -> KnowledgeResult:
        if not isinstance(trigger, str) or not trigger or len(trigger) > 64:
            return self._result(KnowledgeStatus.UNVERIFIED, complete=False)
        result = self.ground_assignment(assignment)
        if result.status is not KnowledgeStatus.VERIFIED:
            return result
        value = dict(result.value)
        value["trigger"] = trigger
        return self._result(result.status, refs=result.source_references,
                            revision=result.source_revision, digest=result.source_sha256,
                            complete=result.retrieval_complete, value=value)

    def record_learning(self, assignment: Mapping[str, Any], outcome: Mapping[str, Any]) -> KnowledgeResult:
        """This immutable source provider has no learning-write capability."""
        return self._result(KnowledgeStatus.UNAVAILABLE, complete=None)
