# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_codex_cli_adapter.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Verify bounded Codex CLI adapter contracts without invoking a real account
# Execution Model: Isolated temporary Git repository and synthetic executable
# Observability: Assertions inspect sanitized adapter status and artifact metadata
# Dependencies: Python 3; Git
# Authority: No live model, service, or account credential is used
# Changed: 2026-10-13 UTC | RV-CODEX-CLI-ADAPTER-001 | Add isolated adapter contract tests
# Contracts: src/riverview_core/resident_execution/codex_cli.py
# Tests: python3 -m unittest tests.test_codex_cli_adapter -v
# History: Git
# =============================================================================
"""Synthetic tests for the Codex CLI boundary; never invokes the real CLI."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from riverview_core.resident_execution.codex_cli import (
    CAPABILITY, CodexAssignment, CodexCLIExecutionAdapter,
)


class CodexCLIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "source"
        self.repo.mkdir(mode=0o700)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "README.md").write_text("Pinned test source.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "README.md"], check=True)
        test_env = dict(os.environ, GIT_AUTHOR_NAME="Riverview Test",
                        GIT_AUTHOR_EMAIL="riverview-test@example.invalid",
                        GIT_COMMITTER_NAME="Riverview Test",
                        GIT_COMMITTER_EMAIL="riverview-test@example.invalid")
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "fixture"],
                       check=True, env=test_env)
        self.revision = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip()
        self.codex = self.root / "fake-codex"
        self.codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            "args=sys.argv[1:]\n"
            "required=['--sandbox','workspace-write','--ephemeral','--ignore-user-config']\n"
            "required += ['approval_policy=\"never\"','sandbox_workspace_write.network_access=false']\n"
            "if any(value not in args for value in required): raise SystemExit(8)\n"
            "if '--fail' in args: raise SystemExit(4)\n"
            "path=pathlib.Path.cwd()/'deliverable.md'\n"
            "path.write_text('# Verified fixture\\n\\nTest artifact.\\n')\n"
            "out=pathlib.Path(args[args.index('--output-last-message')+1])\n"
            "out.write_text(json.dumps({'status':'DELIVERABLE_PRODUCED',"
            "'artifact_name':'deliverable.md','summary':'Created fixture'}))\n",
            encoding="utf-8")
        self.codex.chmod(0o700)
        self.codex_home = self.root / "service-codex-home"
        self.workspace = self.root / "workspaces"
        self.artifacts = self.root / "artifacts"
        for path in (self.codex_home, self.workspace, self.artifacts):
            path.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def adapter(self):
        return CodexCLIExecutionAdapter(executable=str(self.codex),
            repository_path=self.repo, repository_reference="repo://example/test",
            codex_home=self.codex_home, workspace_root=self.workspace,
            artifact_root=self.artifacts)

    def assignment(self, **changes):
        values = dict(assignment_id="assignment:test-1", objective_id="objective:test-1",
            repository_reference="repo://example/test", repository_revision=self.revision,
            task_scope="Create a short test deliverable.",
            acceptance_criteria=("The deliverable exists.",), timeout_seconds=5)
        values.update(changes)
        return CodexAssignment(**values)

    def test_fixed_pinned_workspace_produces_assignment_bound_artifact(self):
        result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "DELIVERABLE_PRODUCED")
        self.assertEqual(result.capability, CAPABILITY)
        self.assertTrue(result.verification_required)
        path = self.artifacts / result.artifact_name
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.read_text(encoding="utf-8"), "# Verified fixture\n\nTest artifact.\n")
        self.assertEqual(result.artifact_bytes, path.stat().st_size)
        self.assertEqual(len(result.artifact_sha256), 64)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_wrong_repository_and_revision_fail_before_codex(self):
        wrong_repo = self.adapter().execute(self.assignment(repository_reference="repo://other"))
        self.assertEqual(wrong_repo.detail_code, "repository_not_registered")
        wrong_revision = "0" * 40
        stale = self.adapter().execute(self.assignment(repository_revision=wrong_revision))
        self.assertEqual(stale.status, "WAITING_FOR_EVIDENCE")
        self.assertEqual(stale.detail_code, "repository_revision_mismatch")

    def test_cli_failure_is_sanitized_and_creates_no_artifact(self):
        self.codex.write_text(self.codex.read_text().replace("args=sys.argv[1:]", "args=sys.argv[1:] + ['--fail']"),
                              encoding="utf-8")
        result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_process_failed")
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_timeout_kills_the_codex_process_and_returns_no_artifact(self):
        self.codex.write_text(
            "#!/usr/bin/env python3\nimport time\ntime.sleep(10)\n", encoding="utf-8")
        self.codex.chmod(0o700)
        result = self.adapter().execute(self.assignment(timeout_seconds=1))
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_timeout")
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_personal_codex_home_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "dedicated service CODEX_HOME"):
            CodexCLIExecutionAdapter(executable=str(self.codex), repository_path=self.repo,
                repository_reference="repo://example/test", codex_home=Path.home() / ".codex",
                workspace_root=self.workspace, artifact_root=self.artifacts)


if __name__ == "__main__":
    unittest.main()
