# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_engineering_artifact.py
# Component: WORKER-ADAPTER
# Revision: 1.0.0
# Purpose: Verify fixed test execution, bounded report artifacts, and independent file checks
# Execution Model: Local disposable package; no database, network, or systemd use
# Observability: Test count, actual output, persisted file hash, and verifier criteria
# Dependencies: Python standard library; repository engineering artifact action
# Authority: Creates data only under TemporaryDirectory
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Initial action and independent verification tests
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: This file
# History: New file; Git
# =============================================================================
"""Unit tests for the fixed, repository-pinned engineering artifact worker."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from riverview_core.worker_adapter.engineering_artifact import (
    OBJECTIVE_REF, RepositoryContractTestAction,
)
from riverview_core.worker_adapter.knowledge_provider_v1.contract import (
    KnowledgeResult, KnowledgeStatus,
)
from riverview_core.worker_adapter.verifier import (
    RepositoryContractTestVerifier, VerificationStatus,
)


class EngineeringArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.package = self.root / "package"
        tests = self.package / "tests"
        tests.mkdir(parents=True)
        self.commit = "a" * 40
        test_source = (
            "import unittest\n"
            "class RepositoryKnowledgeContractTests(unittest.TestCase):\n"
            "    def test_contract_version_is_stable(self): self.assertEqual('v1', 'v1')\n"
            "    def test_unknown_contract_is_not_authorized(self): self.assertNotEqual('NO_MATCH', 'VERIFIED')\n"
        ).encode()
        (tests / "test_repository_knowledge.py").write_bytes(test_source)
        (self.package / "src").mkdir()
        (self.package / "SOURCE_COMMIT").write_text(self.commit + "\n", encoding="ascii")
        checks = {
            "tests/test_repository_knowledge.py": hashlib.sha256(test_source).hexdigest(),
            "SOURCE_COMMIT": hashlib.sha256((self.commit + "\n").encode()).hexdigest(),
        }
        (self.package / "PACKAGE_SHA256SUMS").write_text(
            "".join(f"{digest}  {name}\n" for name, digest in checks.items()),
            encoding="ascii")
        for path in sorted(self.package.rglob("*"), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir(mode=0o700)
        self.assignment = {
            "id": "assignment:test-artifact",
            "contract_ref": "repo://riverview/worker-adapter-contract.v1",
            "objective_ref": OBJECTIVE_REF,
        }
        self.grounded = KnowledgeResult(
            KnowledgeStatus.VERIFIED, value={"contract_ref": self.assignment["contract_ref"]},
            source_references=("repo://src/riverview_core/worker_adapter/continuous.py",),
            source_revision=self.commit, source_sha256="b" * 64,
            retrieval_complete=True)

    def tearDown(self):
        # Make only this owned fixture writable for TemporaryDirectory cleanup.
        for path in self.package.rglob("*"):
            path.chmod(0o700 if path.is_dir() else 0o600)
        for path in sorted(self.package.rglob("*"), reverse=True):
            if path.is_dir():
                path.chmod(0o700)
        self.temp.cleanup()

    def test_action_runs_allowlisted_suite_and_verifier_reopens_real_file(self):
        action = RepositoryContractTestAction(self.package, self.artifacts, self.commit)
        result = action(self.assignment, self.grounded)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["test_count"], 2)
        report_path = self.artifacts / result["artifact_name"]
        self.assertEqual(report_path.stat().st_mode & 0o777, 0o600)
        report = json.loads(report_path.read_text())
        self.assertIn("Ran 2 tests", report["output"])
        attempt = {
            "attempt_id": "attempt:test-artifact", "assignment_id": self.assignment["id"],
            "status": "succeeded", "capability": "engineering.repository-check.v1",
            "result_sha256": hashlib.sha256(json.dumps(
                result, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                allow_nan=False).encode()).hexdigest(),
        }
        verifier = RepositoryContractTestVerifier(self.artifacts, self.commit, self.package)
        accepted = verifier.verify(self.assignment, attempt, result)
        self.assertIs(accepted.status, VerificationStatus.ACCEPTED)
        report_path.write_text("tampered")
        # Restore the protected artifact mode after deliberate tamper simulation.
        report_path.chmod(0o600)
        rejected = verifier.verify(self.assignment, attempt, result)
        self.assertIs(rejected.status, VerificationStatus.REJECTED)
        self.assertFalse(rejected.criteria["artifact_file_digest_valid"])

    def test_action_rejects_unverified_knowledge_and_unmanifested_source(self):
        action = RepositoryContractTestAction(self.package, self.artifacts, self.commit)
        missing = KnowledgeResult(KnowledgeStatus.UNAVAILABLE)
        with self.assertRaisesRegex(RuntimeError, "verified_assignment_contract_required"):
            action(self.assignment, missing)
        (self.package / "tests/test_repository_knowledge.py").chmod(0o644)
        (self.package / "tests/test_repository_knowledge.py").write_text("tampered\n")
        (self.package / "tests/test_repository_knowledge.py").chmod(0o444)
        with self.assertRaisesRegex(RuntimeError, "test_source_checksum_mismatch"):
            action(self.assignment, self.grounded)

    def test_repeat_after_prior_pass_reuses_artifact_instead_of_rewriting(self):
        action = RepositoryContractTestAction(self.package, self.artifacts, self.commit)
        first = action(self.assignment, self.grounded)
        before = (self.artifacts / first["artifact_name"]).read_bytes()
        second = action(self.assignment, self.grounded)
        self.assertEqual(first["artifact_sha256"], second["artifact_sha256"])
        self.assertEqual(before, (self.artifacts / second["artifact_name"]).read_bytes())


if __name__ == "__main__":
    unittest.main()
