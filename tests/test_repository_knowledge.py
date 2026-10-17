# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_repository_knowledge.py
# Component: REPOSITORY-KNOWLEDGE-PROVIDER
# Revision: 1.0.1
# Purpose: Verify pinned source retrieval and fail-closed provider outcomes
# Execution Model: Standard-library unit tests with disposable local Git repos
# Observability: Typed KnowledgeResult status, references, commit and content hash
# Dependencies: Python 3.10+; Git; repository knowledge-provider module
# Authority: Uses only temporary test repositories; no network or database access
# Changed: 2026-10-11 UTC | RV-M3.3-REPOSITORY-KNOWLEDGE | Initial tests
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Verify repository regression action is grounded by the real provider contract
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: This file
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Contract tests for the read-only, pinned repository knowledge provider."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider
from riverview_core.worker_adapter.knowledge_provider_v1.contract import KnowledgeStatus


SOURCES = {
    "docs/components/WORKER_ADAPTER.md": "# Worker contract\n deterministic.sha256.v1\n",
    "src/riverview_core/worker_adapter/adapter.py": "CAPABILITY = 'deterministic.sha256.v1'\n",
    "src/riverview_core/worker_adapter/continuous.py": "ACTION = 'deterministic.sha256.v1'\n",
    "src/riverview_core/worker_adapter/knowledge_provider_v1/contract.py": "class KnowledgeProvider: pass\n",
    "src/riverview_core/worker_adapter/repository_knowledge.py": "class RepositoryKnowledgeProvider: pass\n",
}


class RepositoryKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Riverview test")
        self.git("config", "user.email", "test@example.invalid")
        for relative, content in SOURCES.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.provider = RepositoryKnowledgeProvider(self.root, self.commit)
        self.assignment = {
            "id": "assignment:test", "authority_ref": "grant:test",
            "objective_ref": "objective:test",
            "contract_ref": RepositoryKnowledgeProvider.WORKER_CONTRACT,
        }

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout

    def test_grounding_returns_complete_commit_pinned_sources_and_hash(self):
        result = self.provider.ground_assignment(self.assignment)
        self.assertIs(result.status, KnowledgeStatus.VERIFIED)
        self.assertTrue(result.retrieval_complete)
        self.assertEqual(result.source_revision, self.commit)
        self.assertEqual(len(result.source_sha256), 64)
        self.assertEqual(len(result.source_references), len(SOURCES))
        self.assertIn("deterministic.sha256.v1",
                      result.value["documents"][0]["content"])

    def test_action_preflight_is_bound_to_assignment_contract(self):
        result = self.provider.preflight_action(self.assignment,
                                                "deterministic.sha256.v1")
        self.assertIs(result.status, KnowledgeStatus.VERIFIED)
        self.assertIs(self.provider.preflight_action(
            self.assignment, "engineering.repository-check.v1").status,
            KnowledgeStatus.VERIFIED)
        mismatch = dict(self.assignment, contract_ref="repo://unrelated")
        self.assertIs(self.provider.preflight_action(
            mismatch, "deterministic.sha256.v1").status,
            KnowledgeStatus.CONTRADICTORY)
        self.assertIs(self.provider.preflight_action(
            self.assignment, "arbitrary.command").status, KnowledgeStatus.NO_MATCH)

    def test_regrounding_requires_a_trigger_and_reloads_pinned_sources(self):
        result = self.provider.reground_assignment(self.assignment, "context_restored")
        self.assertIs(result.status, KnowledgeStatus.VERIFIED)
        self.assertEqual(result.value["trigger"], "context_restored")
        self.assertIs(self.provider.reground_assignment(
            self.assignment, "").status, KnowledgeStatus.UNVERIFIED)

    def test_uncommitted_contract_changes_cannot_be_reported_verified(self):
        path = self.root / "src/riverview_core/worker_adapter/adapter.py"
        path.write_text("changed action implementation\n", encoding="utf-8")
        result = self.provider.preflight_action(self.assignment,
                                                "deterministic.sha256.v1")
        self.assertIs(result.status, KnowledgeStatus.UNVERIFIED)
        self.assertFalse(result.retrieval_complete)
        self.assertIsNone(result.value)

    def test_wrong_approved_commit_and_missing_contract_do_not_verify(self):
        other = "0" * 40 if self.commit != "0" * 40 else "1" * 40
        stale = RepositoryKnowledgeProvider(self.root, other)
        self.assertIs(stale.ground_assignment(self.assignment).status,
                      KnowledgeStatus.UNVERIFIED)
        no_contract = dict(self.assignment, contract_ref="repo://missing")
        self.assertIs(self.provider.ground_assignment(no_contract).status,
                      KnowledgeStatus.NO_MATCH)
        self.assertIs(self.provider.ground_assignment(
            {"id": "assignment:missing"}).status, KnowledgeStatus.NO_MATCH)

    def test_learning_is_explicitly_unavailable_for_read_only_provider(self):
        result = self.provider.record_learning(self.assignment, {"result": "unused"})
        self.assertIs(result.status, KnowledgeStatus.UNAVAILABLE)
        self.assertIsNone(result.retrieval_complete)

    def test_source_size_limit_returns_incomplete(self):
        self.provider.MAX_SOURCE_BYTES = 8
        result = self.provider.ground_assignment(self.assignment)
        self.assertIs(result.status, KnowledgeStatus.INCOMPLETE)
        self.assertFalse(result.retrieval_complete)

    def test_verified_package_checksums_support_gitless_deployment(self):
        import hashlib

        package = Path(self.temp.name) / "package"
        package.mkdir()
        checksums = []
        for relative, content in SOURCES.items():
            path = package / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode("utf-8")
            path.write_bytes(data)
            checksums.append(f"{hashlib.sha256(data).hexdigest()}  {relative}")
        package.joinpath("SOURCE_COMMIT").write_text(self.commit + "\n", encoding="ascii")
        commit_data = (self.commit + "\n").encode("ascii")
        checksums.append(f"{hashlib.sha256(commit_data).hexdigest()}  SOURCE_COMMIT")
        package.joinpath("PACKAGE_SHA256SUMS").write_text(
            "\n".join(checksums) + "\n", encoding="ascii")
        result = RepositoryKnowledgeProvider(package, self.commit).ground_assignment(self.assignment)
        self.assertIs(result.status, KnowledgeStatus.VERIFIED)
        self.assertEqual(result.source_revision, self.commit)
        path = package / "src/riverview_core/worker_adapter/adapter.py"
        path.write_text("tampered\n", encoding="utf-8")
        tampered = RepositoryKnowledgeProvider(package, self.commit).ground_assignment(self.assignment)
        self.assertIs(tampered.status, KnowledgeStatus.UNVERIFIED)


if __name__ == "__main__":
    unittest.main()
