# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/engineering_artifact.py
# Component: WORKER-ADAPTER
# Revision: 1.0.1
# Purpose: Run one allowlisted repository contract suite and preserve its real report
# Execution Model: Bounded subprocess in an immutable release; atomic artifact creation
# Observability: Suite identity, package pin, test count, exit status, and file digest
# Dependencies: Python 3.10+; standard library
# Authority: Fixed test command only; no user command, path, environment, or shell execution
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Initial bounded engineering task adapter
# Contracts: docs/components/WORKER_ADAPTER.md; repository-knowledge contract
# Tests: tests/test_engineering_artifact.py; tests/test_worker_adapter.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Execute a single pinned repository regression suite and save its report."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone

from .knowledge import KnowledgeStatus


CAPABILITY = "engineering.repository-check.v1"
CONTRACT_REF = "repo://riverview/worker-adapter-contract.v1"
OBJECTIVE_REF = "objective:verify-repository-knowledge-provider"
SUITE_ID = "tests.test_repository_knowledge"
TEST_PATH = "tests/test_repository_knowledge.py"
MAX_ARTIFACT_BYTES = 24 * 1024
MAX_OUTPUT_BYTES = 12 * 1024
TEST_COUNT = re.compile(r"Ran ([1-9][0-9]*) tests?\b")


class EngineeringArtifactError(RuntimeError):
    """A fixed test action could not safely produce an artifact."""


def _package_test(root: Path, expected_commit: str) -> Path:
    """Require the exact immutable package and manifested test source."""
    try:
        resolved = root.resolve(strict=True)
        info = resolved.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o022:
            raise EngineeringArtifactError("package_path_not_immutable")
        commit = (resolved / "SOURCE_COMMIT").read_text(encoding="ascii").strip()
        if commit != expected_commit:
            raise EngineeringArtifactError("package_commit_mismatch")
        sums = (resolved / "PACKAGE_SHA256SUMS").read_text(encoding="ascii").splitlines()
        manifest = {}
        for row in sums:
            match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._/-]+)", row)
            if not match or match.group(2) in manifest:
                raise EngineeringArtifactError("package_manifest_invalid")
            manifest[match.group(2)] = match.group(1)
        candidate = resolved / TEST_PATH
        if candidate.is_symlink() or not candidate.is_file() or not candidate.resolve().is_relative_to(resolved):
            raise EngineeringArtifactError("test_source_path_invalid")
        if os.access(candidate, os.W_OK, effective_ids=True):
            raise EngineeringArtifactError("test_source_writable_by_worker")
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if manifest.get(TEST_PATH) != digest:
            raise EngineeringArtifactError("test_source_checksum_mismatch")
        return candidate
    except EngineeringArtifactError:
        raise
    except (OSError, UnicodeError, ValueError):
        raise EngineeringArtifactError("package_provenance_unavailable") from None


class RepositoryContractTestAction:
    """Run only the packaged repository knowledge contract test module.

    The action has no shell, caller-supplied command, test selector, output path,
    provider URL, or extra environment. It writes one bounded JSON report under
    the systemd StateDirectory. A completed report is reused on safe recovery.
    """

    def __init__(self, package_root: str | Path, artifact_root: str | Path,
                 approved_commit: str, *, timeout_seconds: float = 90.0):
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", approved_commit or ""):
            raise ValueError("approved_commit must be a full commit hash")
        if not 1 <= timeout_seconds <= 90:
            raise ValueError("timeout_seconds is outside the fixed action limit")
        self.package_root = Path(package_root)
        self.artifact_root = Path(artifact_root)
        self.approved_commit = approved_commit
        self.timeout_seconds = timeout_seconds

    def __call__(self, assignment, grounded):
        if (assignment.get("contract_ref") != CONTRACT_REF or
                assignment.get("objective_ref") != OBJECTIVE_REF or
                grounded.status is not KnowledgeStatus.VERIFIED or
                grounded.retrieval_complete is not True or
                grounded.source_revision != self.approved_commit or
                not grounded.source_references):
            raise EngineeringArtifactError("verified_assignment_contract_required")
        package_test = _package_test(self.package_root, self.approved_commit)
        root = package_test.parents[1]
        artifact_root = self.artifact_root
        artifact_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = artifact_root.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
                stat.S_IMODE(info.st_mode) != 0o700 or
                artifact_root.resolve() != artifact_root.absolute()):
            raise EngineeringArtifactError("artifact_directory_unsafe")
        name = "repository-check-" + hashlib.sha256(
            assignment["id"].encode("utf-8")).hexdigest() + ".json"
        destination = artifact_root / name
        if destination.exists() or destination.is_symlink():
            prior = self._read_existing(destination, assignment["id"])
            if prior.get("status") == "PASS" and prior.get("source_commit") == self.approved_commit:
                return self._result(prior, name, destination)
            raise EngineeringArtifactError("prior_artifact_exists_without_verified_pass")

        started = datetime.now(timezone.utc)
        env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": "src",
               "PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C.UTF-8"}
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", SUITE_ID, "-v"],
                cwd=root, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=self.timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired:
            raise EngineeringArtifactError("approved_test_suite_timeout") from None
        output = completed.stdout
        if len(output) > MAX_OUTPUT_BYTES:
            raise EngineeringArtifactError("approved_test_suite_output_exceeded_limit")
        decoded = output.decode("utf-8", errors="replace")
        count_match = TEST_COUNT.search(decoded)
        tests_run = int(count_match.group(1)) if count_match else 0
        passed = completed.returncode == 0 and tests_run > 0 and decoded.rstrip().endswith("OK")
        finished = datetime.now(timezone.utc)
        report = {
            "artifact_schema": "rv.engineering-test-report.v1",
            "assignment_id": assignment["id"],
            "status": "PASS" if passed else "FAIL",
            "test_suite": SUITE_ID,
            "command": [Path(sys.executable).name, "-m", "unittest", SUITE_ID, "-v"],
            "source_commit": self.approved_commit,
            "test_source_sha256": hashlib.sha256(package_test.read_bytes()).hexdigest(),
            "test_count": tests_run,
            "exit_code": completed.returncode,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "duration_ms": max(0, int((finished-started).total_seconds()*1000)),
            "output": decoded,
        }
        raw = json.dumps(report, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise EngineeringArtifactError("engineering_artifact_exceeded_limit")
        try:
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            prior = self._read_existing(destination, assignment["id"])
            if prior.get("status") == "PASS" and prior.get("source_commit") == self.approved_commit:
                return self._result(prior, name, destination)
            raise EngineeringArtifactError("artifact_creation_collision") from None
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return self._result(report, name, destination)

    @staticmethod
    def _read_existing(path, assignment_id):
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                raise EngineeringArtifactError("existing_artifact_path_invalid")
            raw = path.read_bytes()
            if len(raw) > MAX_ARTIFACT_BYTES:
                raise EngineeringArtifactError("existing_artifact_size_invalid")
            report = json.loads(raw)
            if report.get("assignment_id") != assignment_id:
                raise EngineeringArtifactError("existing_artifact_assignment_mismatch")
            return report
        except EngineeringArtifactError:
            raise
        except (OSError, ValueError, UnicodeDecodeError):
            raise EngineeringArtifactError("existing_artifact_unavailable") from None

    @staticmethod
    def _result(report, name, path):
        raw = path.read_bytes()
        return {"artifact_schema": report["artifact_schema"],
                "artifact_name": name,
                "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                "test_suite": report["test_suite"],
                "source_commit": report["source_commit"],
                "test_source_sha256": report["test_source_sha256"],
                "test_count": report["test_count"],
                "exit_code": report["exit_code"],
                "status": report["status"]}

