# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/verifier.py
# Component: OUTCOME-VERIFIER
# Revision: 1.0.2
# Purpose: Independently evaluate the deterministic M2.1 artifact contract
# Execution Model: Pure in-process verifier; persistence is owned by adapter
# Observability: Typed decision, criteria, evidence references, verifier revision
# Dependencies: Python 3.10+; standard library
# Authority: Executor output is untrusted until verified independently
# Changed: 2026-10-10 UTC | RV-M2.2-001 | Initial result verifier contract
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Independently verify pinned repository test report files
# Changed: 2026-10-11 UTC | RV-M33-ARTIFACT-EVIDENCE-REF | Point verification evidence to the actual artifact path
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Independent result-verification contract and deterministic first verifier."""

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
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


class RepositoryContractTestVerifier:
    """Reopen the test-report artifact and independently check its evidence."""

    REVISION = "1.0.1"
    CAPABILITY = "engineering.repository-check.v1"
    OBJECTIVE_REF = "objective:verify-repository-knowledge-provider"
    SUITE = "tests.test_repository_knowledge"
    COUNT = re.compile(r"Ran ([1-9][0-9]*) tests?\b")
    MAX_ARTIFACT_BYTES = 24 * 1024

    def __init__(self, artifact_root: str | Path, source_commit: str,
                 package_root: str | Path | None = None):
        self.artifact_root = Path(artifact_root)
        self.source_commit = source_commit
        self.package_root = (Path(package_root) if package_root is not None else
                             Path(__file__).resolve().parents[3])

    def verify(self, assignment, attempt, result):
        """Accept only a pinned report file with recomputed database/file digests."""
        criteria = {
            "assignment_objective_matches": assignment.get("objective_ref") == self.OBJECTIVE_REF,
            "attempt_succeeded": attempt.get("status") == "succeeded",
            "executor_capability_matches": attempt.get("capability") == self.CAPABILITY,
            "ledger_result_digest_valid": False,
            "artifact_path_is_assignment_bound": False,
            "artifact_owner_and_mode_valid": False,
            "artifact_file_digest_valid": False,
            "report_is_complete_and_passing": False,
            "source_package_revision_matches": False,
            "independent_test_rerun_matches_report": False,
        }
        evidence = (f"urn:rv:worker-attempt:{attempt.get('attempt_id', 'unknown')}",)
        try:
            result_bytes = json.dumps(dict(result), sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False, allow_nan=False).encode("utf-8")
            criteria["ledger_result_digest_valid"] = (
                hashlib.sha256(result_bytes).hexdigest() == attempt.get("result_sha256"))
            expected_name = "repository-check-" + hashlib.sha256(
                assignment["id"].encode("utf-8")).hexdigest() + ".json"
            name = result.get("artifact_name")
            criteria["artifact_path_is_assignment_bound"] = (
                isinstance(name, str) and name == expected_name and
                Path(name).name == name and not Path(name).is_symlink())
            if criteria["artifact_path_is_assignment_bound"]:
                root_info = self.artifact_root.lstat()
                if (stat.S_ISDIR(root_info.st_mode) and root_info.st_uid == os.geteuid() and
                        stat.S_IMODE(root_info.st_mode) == 0o700 and
                        self.artifact_root.resolve() == self.artifact_root.absolute()):
                    artifact_path = self.artifact_root / name
                    fd = os.open(artifact_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                    try:
                        info = os.fstat(fd)
                        criteria["artifact_owner_and_mode_valid"] = (
                            stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and
                            stat.S_IMODE(info.st_mode) == 0o600 and
                            0 < info.st_size <= self.MAX_ARTIFACT_BYTES)
                        raw = os.read(fd, self.MAX_ARTIFACT_BYTES + 1)
                    finally:
                        os.close(fd)
                    criteria["artifact_file_digest_valid"] = (
                        len(raw) <= self.MAX_ARTIFACT_BYTES and
                        hashlib.sha256(raw).hexdigest() == result.get("artifact_sha256"))
                    if criteria["artifact_file_digest_valid"]:
                        report = json.loads(raw)
                        match = self.COUNT.search(report.get("output", ""))
                        criteria["report_is_complete_and_passing"] = bool(
                            report.get("artifact_schema") == "rv.engineering-test-report.v1" and
                            report.get("assignment_id") == assignment.get("id") and
                            report.get("status") == "PASS" and
                            report.get("test_suite") == self.SUITE and
                            isinstance(report.get("command"), list) and
                            report.get("command", [None])[1:] == ["-m", "unittest", self.SUITE, "-v"] and
                            type(report.get("test_count")) is int and report["test_count"] > 0 and
                            match and int(match.group(1)) == report["test_count"] and
                            report.get("exit_code") == 0 and
                            report.get("output", "").rstrip().endswith("OK"))
                        criteria["source_package_revision_matches"] = (
                            report.get("source_commit") == self.source_commit and
                            result.get("source_commit") == self.source_commit and
                            report.get("test_source_sha256") == result.get("test_source_sha256") and
                            self._test_source_matches_package(result.get("test_source_sha256")))
                        if (criteria["report_is_complete_and_passing"] and
                                criteria["source_package_revision_matches"]):
                            rerun = subprocess.run(
                                [sys.executable, "-m", "unittest",
                                 "tests.test_repository_knowledge", "-v"],
                                cwd=self.package_root, env={
                                    "PATH": "/usr/bin:/bin", "PYTHONPATH": "src",
                                    "PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C.UTF-8",
                                }, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=90, check=False)
                            rerun_output = rerun.stdout.decode("utf-8", errors="replace")
                            rerun_count = self.COUNT.search(rerun_output)
                            criteria["independent_test_rerun_matches_report"] = bool(
                                rerun.returncode == 0 and rerun_count and
                                int(rerun_count.group(1)) == report.get("test_count") and
                                rerun_output.rstrip().endswith("OK"))
                    evidence += (artifact_path.resolve().as_uri(),)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError,
                subprocess.SubprocessError):
            pass
        accepted = all(criteria.values())
        return VerificationResult(
            VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria, evidence, self.REVISION,
            "repository contract test report independently verified" if accepted else
            "repository contract test report failed independent verification",
        )

    def _test_source_matches_package(self, claimed_digest):
        try:
            root = self.package_root.resolve(strict=True)
            info = root.lstat()
            if (not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o022 or
                    (root / "SOURCE_COMMIT").read_text(encoding="ascii").strip() != self.source_commit):
                return False
            values = {}
            for row in (root / "PACKAGE_SHA256SUMS").read_text(encoding="ascii").splitlines():
                match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._/-]+)", row)
                if not match or match.group(2) in values:
                    return False
                values[match.group(2)] = match.group(1)
            source = root / "tests/test_repository_knowledge.py"
            raw = source.read_bytes()
            return (not source.is_symlink() and
                    source.resolve().is_relative_to(root) and
                    not os.access(source, os.W_OK, effective_ids=True) and
                    values.get("tests/test_repository_knowledge.py") == claimed_digest ==
                    hashlib.sha256(raw).hexdigest())
        except (OSError, ValueError, UnicodeError):
            return False
