# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/verifier.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.3
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Reject machine-readable negative outcomes and independently verify explicit artifact literals
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-002 | Independently verify the complete bounded artifact set against persisted assignment identity
# Purpose: Independently reopen and validate bounded Grace artifacts against persisted assignment contracts
# Execution Model: Read-only in-process verification separated from worker action
# Observability: Per-contract decision and artifact/attempt evidence references
# Dependencies: worker-adapter VerificationResult contract; Python standard library
# Authority: Worker output is untrusted until independently reopened and accepted
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Add distinct artifact verifier implementation
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-002 | Resolve artifact identity and verification from durable assignment step contract
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: tests/test_grace_execution.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Read-only assignment-contract artifact verification; never trusts worker paths."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

from ..resident_reasoning import ArtifactRequirement
from ..worker_adapter.verifier import VerificationResult, VerificationStatus
from .worker import CAPABILITY, MAX_ARTIFACT_BYTES, MAX_ARTIFACT_COUNT


_NEGATIVE_OUTCOME_KEYS = {
    "status", "decision", "outcome", "result", "verdict", "acceptance_status",
    "verification_status", "completion_status", "review_decision",
    "verification_decision", "acceptance_decision", "completion_decision",
    "task_status", "test_status", "error",
}
_POSITIVE_OUTCOME_KEYS = {"success", "succeeded", "accepted", "approved", "passed", "verified"}
_NEGATIVE_OUTCOMES = {
    "reject", "rejected", "fail", "failed", "failure", "blocked", "error", "denied",
    "not_accepted", "not_approved", "unsuccessful",
}


def json_has_authoritative_negative_outcome(value):
    """Recognize explicit negative decisions anywhere in a JSON result document."""
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in _NEGATIVE_OUTCOME_KEYS and isinstance(item, str):
                normalized = item.strip().lower().replace(" ", "_").replace("-", "_")
                negative_token = re.search(
                    r"(?:^|_)(?:reject(?:ed)?|fail(?:ed|ure)?|blocked|error|denied|"
                    r"not_accepted|not_approved|unsuccessful)(?:_|$)", normalized)
                if normalized in _NEGATIVE_OUTCOMES or negative_token:
                    return True
            if normalized_key in _POSITIVE_OUTCOME_KEYS and item is False:
                return True
            if json_has_authoritative_negative_outcome(item):
                return True
    elif isinstance(value, list):
        return any(json_has_authoritative_negative_outcome(item) for item in value)
    return False


def explicit_artifact_literals(criterion):
    """Extract only independently checkable literal clauses and quoted source paths."""
    if not isinstance(criterion, str):
        return ()
    cites_sources = bool(re.search(r"(?i)\b(cite|cites|citing|reference|references|list|name)\b",
                                   criterion))
    values = []
    for item in re.findall(r"`([^`\n]{1,512})`", criterion):
        item = item.strip()
        if not item:
            continue
        is_path = bool(re.fullmatch(r"(?:src|tests|docs)/[A-Za-z0-9._/-]+|[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,8}", item))
        if not is_path or cites_sources:
            values.append(item)
    if cites_sources:
        values.extend(path for path in re.findall(
            r"\b(?:src|tests|docs)/[A-Za-z0-9._/-]+", criterion) if path not in values)
    for match in re.finditer(r"(?i)(?:exact phrase|literal|contains exactly)\s*[:=]?\s*['\"“](.{1,512}?)['\"”]", criterion):
        value = match.group(1).strip()
        if value and value not in values:
            values.append(value)
    return tuple(values)


def artifact_literals_satisfied(raw, criteria):
    """Check quoted deliverable requirements without pretending to grade prose semantics."""
    try:
        text = raw.decode("utf-8")
    except (UnicodeError, AttributeError):
        return False
    expected = [literal for criterion in criteria for literal in explicit_artifact_literals(criterion)]
    return all(literal in text for literal in expected)


class BoundedArtifactVerifier:
    """Verify contract binding, content digest, work product, and provenance."""

    REVISION = "1.0.2"
    MAX_GRACE_REVIEW_BYTES = 12 * 1024

    def __init__(self, artifact_root: str | Path, pipeline):
        self.artifact_root = Path(artifact_root)
        self.pipeline = pipeline

    @staticmethod
    def _contract(step):
        raw = step.get("artifact_requirements") if isinstance(step, dict) else None
        if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_ARTIFACT_COUNT:
            return None
        try:
            items = tuple(ArtifactRequirement(item["name"], item["path"], item["media_type"],
                tuple(item["acceptance_criteria"]), item.get("max_bytes", 32768)) for item in raw)
        except (KeyError, TypeError, ValueError):
            return None
        normalized = [{"name": item.name, "path": item.path, "media_type": item.media_type,
            "acceptance_criteria": list(item.acceptance_criteria), "max_bytes": item.max_bytes}
            for item in items]
        return items if normalized == raw and all(item.media_type == "application/json"
            for item in items) else None

    @staticmethod
    def _storage_name(assignment_id, requirement):
        assignment_key = hashlib.sha256(assignment_id.encode("utf-8")).hexdigest()
        artifact_key = hashlib.sha256(requirement.name.encode("utf-8")).hexdigest()[:12]
        return f"{assignment_key}/{artifact_key}"

    def _read(self, name, expected, max_bytes):
        if not isinstance(name, str) or name != expected:
            raise ValueError("artifact storage identity is not assignment-contract-bound")
        parts = name.split("/")
        if (len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]) or
                not re.fullmatch(r"[0-9a-f]{12}", parts[1])):
            raise ValueError("artifact storage identity is invalid")
        root_fd = os.open(self.artifact_root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                          getattr(os, "O_NOFOLLOW", 0))
        try:
            directory_fd = os.open(parts[0], os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                                   getattr(os, "O_NOFOLLOW", 0), dir_fd=root_fd)
        finally:
            os.close(root_fd)
        try:
            directory_info = os.fstat(directory_fd)
            if (directory_info.st_uid != os.geteuid() or
                    stat.S_IMODE(directory_info.st_mode) != 0o700):
                raise ValueError("artifact directory protection metadata is invalid")
            fd = os.open(parts[1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                         dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or
                    type(max_bytes) is not int or
                    not 0 < info.st_size <= min(max_bytes, MAX_ARTIFACT_BYTES)):
                raise ValueError("artifact metadata is unsafe")
            raw = os.read(fd, min(max_bytes, MAX_ARTIFACT_BYTES) + 1)
            if len(raw) != info.st_size:
                raise ValueError("artifact size changed during read")
            return raw
        finally:
            os.close(fd)

    def _directory_matches_contract(self, assignment_id, contract):
        assignment_key = hashlib.sha256(assignment_id.encode("utf-8")).hexdigest()
        root_fd = os.open(self.artifact_root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                          getattr(os, "O_NOFOLLOW", 0))
        try:
            directory_fd = os.open(assignment_key, os.O_RDONLY |
                getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=root_fd)
        finally:
            os.close(root_fd)
        try:
            expected = {self._storage_name(assignment_id, item).split("/", 1)[1]
                        for item in contract}
            return set(os.listdir(directory_fd)) == expected
        finally:
            os.close(directory_fd)

    @staticmethod
    def _json_work_product(raw, entry, assignment, objective, step):
        try:
            artifact = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return False
        return bool(isinstance(artifact, dict) and
            not json_has_authoritative_negative_outcome(artifact) and
            artifact.get("artifact_schema") == "rv.grace.work-product.v2" and
            artifact.get("artifact_name") == entry.get("name") and
            artifact.get("artifact_path") == entry.get("path") and
            artifact.get("media_type") == entry.get("media_type") == "application/json" and
            artifact.get("objective_id") == assignment.get("objective_ref") == objective.get("objective_id") and
            artifact.get("assignment_id") == assignment.get("id") and
            artifact.get("task") == step.get("objective") and
            artifact.get("acceptance_criteria") == entry.get("acceptance_criteria") and
            artifact.get("step_acceptance_criteria") == step.get("acceptance_criteria") and
            artifact.get("repository_reference") and
            artifact.get("allowed_operations") == ["write_bounded_json_artifact"] and
            artifact.get("timeout_seconds") == 30 and
            artifact.get("source_revision") == objective.get("source_revision") and
            artifact.get("source_sha256") == objective.get("source_sha256") and
            artifact.get("source_references") == objective.get("evidence", {}).get("source_references"))

    def verify(self, assignment, attempt, result):
        result = result if isinstance(result, dict) else {}
        assignment_id = assignment.get("id")
        objective_id = assignment.get("objective_ref")
        has_persisted_resolver = (callable(getattr(self.pipeline, "proposal_step_for_assignment", None)) and
                                  callable(getattr(self.pipeline, "get_objective", None)))
        step = (self.pipeline.proposal_step_for_assignment(objective_id, assignment_id)
            if has_persisted_resolver and isinstance(assignment_id, str) and
               isinstance(objective_id, str) else None)
        objective = (self.pipeline.get_objective(objective_id)
            if has_persisted_resolver and isinstance(objective_id, str) else None)
        contract = self._contract(step)
        entries = result.get("artifacts")
        criteria = {
            "attempt_succeeded": attempt.get("status") == "succeeded",
            "executor_capability_matches": attempt.get("capability") == CAPABILITY,
            "worker_report_succeeded": result.get("status") == "SUCCEEDED",
            "result_schema_matches": result.get("artifact_schema") == "rv.grace.artifacts.v2",
            "assignment_and_objective_match": result.get("assignment_id") == assignment_id and
                result.get("objective_id") == objective_id,
            "persisted_assignment_contract_available": contract is not None,
            "artifact_set_matches_persisted_contract": False,
            "artifact_integrity_and_assignment_provenance_verified": False,
            "source_provenance_matches_persisted_objective": False,
            "artifact_projection_matches_contract": False,
            "artifact_semantic_outcome_not_negative": True,
            "explicit_artifact_acceptance_clauses_satisfied": True,
        }
        evidence = (f"urn:rv:worker-attempt:{attempt.get('attempt_id', 'unknown')}",)
        try:
            root_info = self.artifact_root.lstat()
            safe_root = (stat.S_ISDIR(root_info.st_mode) and not self.artifact_root.is_symlink() and
                root_info.st_uid == os.geteuid() and stat.S_IMODE(root_info.st_mode) == 0o700 and
                self.artifact_root.resolve() == self.artifact_root.absolute())
            if not safe_root or contract is None or not isinstance(entries, list):
                raise ValueError("persisted artifact contract unavailable")
            expected_contract = [{"name": item.name, "path": item.path,
                "media_type": item.media_type, "acceptance_criteria": list(item.acceptance_criteria),
                "max_bytes": item.max_bytes} for item in contract]
            criteria["artifact_set_matches_persisted_contract"] = (
                result.get("artifact_contract") == expected_contract and len(entries) == len(contract) and
                len({entry.get("name") for entry in entries if isinstance(entry, dict)}) == len(entries) and
                {entry.get("name") for entry in entries if isinstance(entry, dict)} ==
                    {item.name for item in contract})
            if not criteria["artifact_set_matches_persisted_contract"]:
                raise ValueError("result artifact set differs from persisted contract")
            if not self._directory_matches_contract(assignment_id, contract):
                criteria["artifact_set_matches_persisted_contract"] = False
                raise ValueError("stored artifact directory differs from persisted contract")
            verified = []
            for requirement in contract:
                entry = next(item for item in entries if item.get("name") == requirement.name)
                if (not isinstance(entry, dict) or set(entry) != {
                        "name", "path", "media_type", "storage_name", "sha256",
                        "bytes", "acceptance_criteria"} or
                        entry.get("path") != requirement.path or
                        entry.get("media_type") != requirement.media_type or
                        entry.get("acceptance_criteria") != list(requirement.acceptance_criteria)):
                    raise ValueError("artifact metadata differs from persisted contract")
                raw = self._read(entry.get("storage_name"),
                    self._storage_name(assignment_id, requirement), requirement.max_bytes)
                if requirement.media_type == "application/json":
                    try:
                        criteria["artifact_semantic_outcome_not_negative"] = (
                            criteria["artifact_semantic_outcome_not_negative"] and
                            not json_has_authoritative_negative_outcome(
                                json.loads(raw.decode("utf-8"))))
                    except (UnicodeError, json.JSONDecodeError):
                        criteria["artifact_semantic_outcome_not_negative"] = False
                criteria["explicit_artifact_acceptance_clauses_satisfied"] = (
                    criteria["explicit_artifact_acceptance_clauses_satisfied"] and
                    artifact_literals_satisfied(raw, requirement.acceptance_criteria))
                if (hashlib.sha256(raw).hexdigest() != entry.get("sha256") or
                        len(raw) != entry.get("bytes") or
                        not criteria["artifact_semantic_outcome_not_negative"] or
                        not criteria["explicit_artifact_acceptance_clauses_satisfied"] or
                        not self._json_work_product(raw, entry, assignment, objective or {}, step or {})):
                    raise ValueError("artifact integrity or work product validation failed")
                verified.append(entry)
                evidence += ("workspace://" + entry["storage_name"],
                             "sha256:" + entry["sha256"])
            criteria["artifact_integrity_and_assignment_provenance_verified"] = len(verified) == len(contract)
            evidence_record = (objective or {}).get("evidence", {})
            criteria["source_provenance_matches_persisted_objective"] = bool(
                result.get("source_revision") == (objective or {}).get("source_revision") and
                result.get("source_sha256") == (objective or {}).get("source_sha256") and
                result.get("source_references") == evidence_record.get("source_references") and
                evidence_record.get("status") == "VERIFIED" and
                evidence_record.get("retrieval_complete") is True)
            first = entries[0]
            criteria["artifact_projection_matches_contract"] = (
                result.get("artifact_name") == first.get("storage_name") and
                result.get("artifact_path") == str(self.artifact_root / first.get("storage_name", "")) and
                result.get("artifact_sha256") == first.get("sha256") and
                result.get("artifact_bytes") == first.get("bytes") and
                result.get("source_artifact_name") == first.get("path") and
                result.get("changed_files") == sorted(item.path for item in contract))
        except (OSError, ValueError, TypeError, StopIteration):
            pass
        accepted = all(criteria.values())
        return VerificationResult(
            VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria, evidence, self.REVISION,
            "Bounded artifact set independently verified against its persisted assignment contract"
            if accepted else
            "Bounded artifact set failed independent contract, integrity, or provenance verification")

    def read_artifact_for_grace_review(self, assignment_id, result):
        """Reopen all assignment-bound JSON artifacts after repeating integrity checks."""
        if (not isinstance(assignment_id, str) or not isinstance(result, dict) or
                result.get("status") != "SUCCEEDED" or
                result.get("artifact_schema") != "rv.grace.artifacts.v2" or
                result.get("capability") != CAPABILITY or
                result.get("assignment_id") != assignment_id or
                not isinstance(result.get("objective_id"), str) or
                not isinstance(result.get("artifacts"), list) or
                not 1 <= len(result["artifacts"]) <= MAX_ARTIFACT_COUNT):
            raise ValueError("verified assignment artifact set is required for Grace review")
        if (not callable(getattr(self.pipeline, "proposal_step_for_assignment", None)) or
                not callable(getattr(self.pipeline, "get_objective", None))):
            raise ValueError("persisted artifact contract is unavailable")
        step = self.pipeline.proposal_step_for_assignment(result["objective_id"], assignment_id)
        objective = self.pipeline.get_objective(result["objective_id"])
        contract = self._contract(step)
        if contract is None:
            raise ValueError("persisted artifact contract unavailable")
        expected_contract = [{"name": item.name, "path": item.path,
            "media_type": item.media_type, "acceptance_criteria": list(item.acceptance_criteria),
            "max_bytes": item.max_bytes} for item in contract]
        if result.get("artifact_contract") != expected_contract:
            raise ValueError("artifact contract changed before Grace review")
        if not self._directory_matches_contract(assignment_id, contract):
            raise ValueError("stored artifact directory differs from persisted contract")
        root_info = self.artifact_root.lstat()
        if (not stat.S_ISDIR(root_info.st_mode) or self.artifact_root.is_symlink() or
                root_info.st_uid != os.geteuid() or stat.S_IMODE(root_info.st_mode) != 0o700 or
                self.artifact_root.resolve() != self.artifact_root.absolute()):
            raise ValueError("artifact root is not protected for Grace review")
        outputs = []
        total = 0
        for requirement in contract:
            entry = next((item for item in result["artifacts"]
                if isinstance(item, dict) and item.get("name") == requirement.name), None)
            if entry is None:
                raise ValueError("artifact set is incomplete")
            raw = self._read(entry.get("storage_name"),
                self._storage_name(assignment_id, requirement), requirement.max_bytes)
            if (hashlib.sha256(raw).hexdigest() != entry.get("sha256") or
                    len(raw) != entry.get("bytes") or
                    not self._json_work_product(raw, entry,
                        {"id": assignment_id, "objective_ref": result["objective_id"]},
                        objective or {}, step or {})):
                raise ValueError("artifact integrity check failed before Grace review")
            total += len(raw)
            if total > self.MAX_GRACE_REVIEW_BYTES:
                raise ValueError("artifact set exceeds Grace review bounds")
            outputs.append({"name": entry["name"], "path": entry["path"],
                "media_type": entry["media_type"], "sha256": entry["sha256"],
                "body": raw.decode("utf-8")})
        return {"artifacts": outputs}
