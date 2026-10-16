# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_codex_source_change.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.1
# Purpose: Verify explicit multi-file Codex source-change scope and independent patch checking
# Execution Model: Isolated temporary Git repository and synthetic CLI; no production services
# Observability: Assert patch digest, changed-file inventory, path rejection and verifier decision
# Dependencies: Python 3; Git; pytest
# Authority: Synthetic assignment only; does not grant execution or apply production patches
# Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-001 | Add bounded source-change adapter tests
# Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-001 | Exercise isolated offline tests and ensure source capability stays independently registered
# Contracts: src/riverview_core/resident_execution/codex_source_change.py
# Tests: This file
# History: Git
# =============================================================================
"""Tests for bounded Codex multi-file source changes and separate verification."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from riverview_core.resident_execution.codex_cli import CodexCLIExecutionAdapter
from riverview_core.resident_execution.codex_source_change import (
    CAPABILITY, CodexSourceChangeAdapter, CodexSourceChangeAssignment,
    CodexSourceChangeVerifier, _run_tests,
)


class CodexSourceChangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "README.md"], check=True)
        env = dict(os.environ, GIT_AUTHOR_NAME="Riverview Test",
                   GIT_AUTHOR_EMAIL="test@example.invalid",
                   GIT_COMMITTER_NAME="Riverview Test",
                   GIT_COMMITTER_EMAIL="test@example.invalid")
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "base"],
                       check=True, env=env)
        self.revision = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip()
        self.codex = self.root / "codex"
        self.codex.write_text("#!/usr/bin/env python3\n"
            "import json,pathlib,sys\n"
            "root=pathlib.Path.cwd()\n"
            "(root/'src/a.py').parent.mkdir(parents=True,exist_ok=True)\n"
            "(root/'src/a.py').write_text('A=1\\n')\n"
            "(root/'src/b.py').write_text('B=2\\n')\n"
            "(root/'tests/test_ab.py').parent.mkdir(parents=True,exist_ok=True)\n"
            "(root/'tests/test_ab.py').write_text('def test_ab():\\n assert True\\n')\n"
            "p=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1])\n"
            "p.write_text(json.dumps({'status':'PATCH_PRODUCED','summary':'Created scoped files'}))\n",
            encoding="utf-8")
        self.codex.chmod(0o700)
        self.codex_home = self.root / "home"
        self.workspace = self.root / "workspaces"
        self.artifacts = self.root / "artifacts"
        for path in (self.codex_home, self.workspace, self.artifacts):
            path.mkdir(mode=0o700)
        self.paths = ("src/a.py", "src/b.py", "tests/test_ab.py")
        self.base = CodexCLIExecutionAdapter(executable=str(self.codex),
            repository_path=self.repo, repository_reference="repo://test/repo",
            codex_home=self.codex_home, workspace_root=self.workspace,
            artifact_root=self.artifacts)
        self.assignment = CodexSourceChangeAssignment(
            assignment_id="assignment:test-source", objective_id="objective:test-source",
            repository_reference="repo://test/repo", repository_revision=self.revision,
            task_scope="Create two source files and one test file.",
            acceptance_criteria=("All three files exist in the change set.",),
            authorized_paths=self.paths, test_targets=("tests/test_ab.py",), timeout_seconds=10)

    def tearDown(self):
        self.temp.cleanup()

    def test_multiple_files_are_patched_tested_and_independently_verified(self):
        with patch.object(CodexCLIExecutionAdapter, "_verify_workspace_sandbox"), \
             patch("riverview_core.resident_execution.codex_source_change._run_tests",
                   return_value=True):
            adapter = CodexSourceChangeAdapter(base_adapter=self.base,
                repository_reference="repo://test/repo", authorized_paths=self.paths)
            result = adapter.execute(self.assignment)
            self.assertEqual(result.status, "PATCH_PRODUCED")
            self.assertEqual(result.capability, CAPABILITY)
            self.assertEqual(result.changed_files, self.paths)
            self.assertEqual(len(result.patch_sha256), 64)
            verifier = CodexSourceChangeVerifier(base_adapter=self.base,
                authorized_paths=self.paths)
            decision = verifier.verify(self.assignment, result)
        self.assertEqual(decision["decision"], "ACCEPTED")
        self.assertIn("base-revision:" + self.revision, decision["evidence"])
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_assignment_rejects_unauthorized_or_unsafe_paths(self):
        with self.assertRaises(ValueError):
            CodexSourceChangeAssignment(**{**self.assignment.__dict__,
                "authorized_paths": ("src/a.py", "src/../../outside", "tests/test_ab.py")})
        with self.assertRaises(ValueError):
            CodexSourceChangeAssignment(**{**self.assignment.__dict__,
                "test_targets": ("tests/test_ab.py", "tests/other.py")})
        adapter = CodexSourceChangeAdapter(base_adapter=self.base,
            repository_reference="repo://test/repo", authorized_paths=("src/a.py",))
        with patch.object(CodexCLIExecutionAdapter, "_verify_workspace_sandbox"):
            result = adapter.execute(self.assignment)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.detail_code, "source_scope_not_registered")

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap is not installed")
    def test_fixed_pytest_target_runs_in_offline_bubblewrap_sandbox(self):
        repo = self.root / "offline-tests"
        (repo / "tests").mkdir(parents=True)
        (repo / "tests/test_offline.py").write_text(
            "def test_offline():\n    assert 3 * 7 == 21\n", encoding="utf-8")
        self.assertTrue(_run_tests(repo, ("tests/test_offline.py",), 20))


if __name__ == "__main__":
    unittest.main()
