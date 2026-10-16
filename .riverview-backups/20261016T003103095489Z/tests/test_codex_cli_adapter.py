# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_codex_cli_adapter.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.2.0
# Purpose: Verify bounded subscription-authenticated Codex adapter contracts
# Execution Model: Isolated temporary Git repository and synthetic executable
# Observability: Assertions inspect sanitized adapter status and artifact metadata
# Dependencies: Python 3; Git
# Authority: No live model, service, or account credential is used
# Changed: 2026-10-13 UTC | RV-CODEX-CLI-ADAPTER-001 | Add isolated adapter contract tests
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Test leased worker action and independent Markdown verification contracts
# Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Verify API-key-free child environment and interactive session gate
# Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Verify persistent owner-session mode without TTY or credential copy
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-SANDBOX-READINESS-001 | Verify workspace sandbox failure blocks before dispatch
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Verify scoped Git trust, separate source/repository pins, and explicit process-start provenance
# Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Verify older objective evidence remains valid under current grounding provenance
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
from types import SimpleNamespace
from unittest.mock import patch

from riverview_core.resident_execution.codex_cli import (
    CAPABILITY, CodexAdapterError, CodexAssignment, CodexCLIExecutionAdapter,
)
from riverview_core.resident_execution.codex_workflow import (
    CodexMarkdownVerifier, CodexWorkAction,
)
from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus


class CodexCLIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.sandbox_patch = patch.object(CodexCLIExecutionAdapter,
            "_verify_workspace_sandbox", return_value=None)
        self.sandbox_patch.start()
        self.addCleanup(self.sandbox_patch.stop)
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
            "path.write_text('# Verified fixture\\n\\nThe deliverable exists.\\n')\n"
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
        self.assertTrue(result.execution_started)
        self.assertEqual(result.capability, CAPABILITY)
        self.assertTrue(result.verification_required)
        path = self.artifacts / result.artifact_name
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.read_text(encoding="utf-8"),
                         "# Verified fixture\n\nThe deliverable exists.\n")
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
        self.assertFalse(stale.execution_started)

    def test_git_trust_is_scoped_to_one_private_command_configuration(self):
        original_run = subprocess.run
        observed = []

        def capture(command, **kwargs):
            config = kwargs.get("env", {}).get("GIT_CONFIG_GLOBAL")
            if config:
                path = Path(config)
                observed.append((path.read_text(encoding="utf-8"),
                                 path.stat().st_mode & 0o777))
            return original_run(command, **kwargs)

        with patch("riverview_core.resident_execution.codex_cli.subprocess.run",
                   side_effect=capture):
            self.assertEqual(self.adapter().repository_revision(), self.revision)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][1], 0o600)
        self.assertIn(str(self.repo.resolve()), observed[0][0])
        self.assertNotIn("directory = *", observed[0][0])
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_legacy_git_ownership_refusal_is_detected_without_logging_git_output(self):
        adapter = self.adapter()
        completed = subprocess.CompletedProcess(
            ["git"], 128, stdout=b"", stderr=b"fatal: detected dubious ownership in repository")
        with patch.object(adapter, "_preflight", return_value=(self.codex, self.repo)), \
             patch("riverview_core.resident_execution.codex_cli.subprocess.run",
                   return_value=completed):
            self.assertTrue(adapter.legacy_git_ownership_refused())

    def test_unavailable_workspace_sandbox_fails_closed_before_codex(self):
        with patch.object(CodexCLIExecutionAdapter, "_verify_workspace_sandbox",
                          side_effect=CodexAdapterError("codex_sandbox_unavailable")):
            result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_sandbox_unavailable")
        self.assertFalse(result.execution_started)
        self.assertFalse(list(self.artifacts.iterdir()))
        self.assertFalse(list(self.workspace.iterdir()))

    def test_cli_failure_is_sanitized_and_creates_no_artifact(self):
        self.codex.write_text(self.codex.read_text().replace("args=sys.argv[1:]", "args=sys.argv[1:] + ['--fail']"),
                              encoding="utf-8")
        result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_process_failed")
        self.assertTrue(result.execution_started)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_timeout_kills_the_codex_process_and_returns_no_artifact(self):
        self.codex.write_text(
            "#!/usr/bin/env python3\nimport time\ntime.sleep(10)\n", encoding="utf-8")
        self.codex.chmod(0o700)
        result = self.adapter().execute(self.assignment(timeout_seconds=1))
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_timeout")
        self.assertTrue(result.execution_started)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_personal_codex_home_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "dedicated service CODEX_HOME"):
            CodexCLIExecutionAdapter(executable=str(self.codex), repository_path=self.repo,
                repository_reference="repo://example/test", codex_home=Path.home() / ".codex",
                workspace_root=self.workspace, artifact_root=self.artifacts)

    def test_persistent_action_and_separate_verifier_accept_real_file_contract(self):
        knowledge_revision = "a" * 40
        objective_revision = "c" * 40
        objective_digest = "d" * 64
        class Pipeline:
            def get_objective(self, _objective_id):
                return {"objective_id": "objective:test-1", "status": "WORK_ORDER_CREATED",
                    "assignment_id": "assignment:test-1", "source_revision": objective_revision,
                    "source_sha256": objective_digest,
                    "evidence": {"status": "VERIFIED", "source_revision": objective_revision,
                                 "source_sha256": objective_digest},
                    "proposal": {"steps": [{"objective": "Create bounded Markdown.",
                        "acceptance_criteria": ["The deliverable exists."]}]}}
        adapter = self.adapter()
        action = CodexWorkAction(Pipeline(), adapter, "repo://example/test", 5)
        assignment = {"id": "assignment:test-1", "objective_ref": "objective:test-1"}
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=knowledge_revision,
            source_sha256="b" * 64, retrieval_complete=True)
        result = action(assignment, grounded)
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["source_revision"], knowledge_revision)
        self.assertEqual(result["source_sha256"], "b" * 64)
        self.assertEqual(result["repository_revision"], self.revision)
        self.assertTrue(Path(result["artifact_path"]).is_file())
        verification = CodexMarkdownVerifier(self.artifacts).verify(
            assignment, {"status": "succeeded", "capability": CAPABILITY,
                       "attempt_id": "attempt:fixture"}, result)
        self.assertEqual(verification.status.value, "ACCEPTED")
        self.assertTrue(all(verification.criteria.values()))

    def test_independent_verifier_rejects_changed_artifact(self):
        class Pipeline:
            def get_objective(self, _objective_id):
                return {"objective_id": "objective:test-1", "status": "WORK_ORDER_CREATED",
                    "assignment_id": "assignment:test-1", "source_revision": revision,
                    "source_sha256": "a" * 64, "evidence": {"status": "VERIFIED",
                        "source_revision": revision, "source_sha256": "a" * 64},
                    "proposal": {"steps": [{"objective": "Create bounded Markdown.",
                        "acceptance_criteria": ["The deliverable exists."]}]}}
        revision = self.revision
        adapter = self.adapter()
        action = CodexWorkAction(Pipeline(), adapter, "repo://example/test", 5)
        assignment = {"id": "assignment:test-1", "objective_ref": "objective:test-1"}
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=revision,
            source_sha256="b" * 64, retrieval_complete=True)
        result = action(assignment, grounded)
        self.assertEqual(result["repository_revision"], revision)
        Path(result["artifact_path"]).write_text("# altered\n", encoding="utf-8")
        verification = CodexMarkdownVerifier(self.artifacts).verify(
            assignment, {"status": "succeeded", "capability": CAPABILITY,
                       "attempt_id": "attempt:fixture"}, result)
        self.assertEqual(verification.status.value, "REJECTED")

    def test_codex_child_does_not_receive_an_api_key(self):
        script = self.codex.read_text(encoding="utf-8")
        self.codex.write_text(script.replace(
            "args=sys.argv[1:]",
            "import os\nif 'OPENAI_API_KEY' in os.environ: raise SystemExit(9)\nargs=sys.argv[1:]"),
            encoding="utf-8")
        result = CodexCLIExecutionAdapter(executable=str(self.codex),
            repository_path=self.repo, repository_reference="repo://example/test",
            codex_home=self.codex_home, workspace_root=self.workspace,
            artifact_root=self.artifacts).execute(self.assignment())
        self.assertEqual(result.status, "DELIVERABLE_PRODUCED")

    def test_subscription_session_requires_interactive_owner_terminal(self):
        with self.assertRaisesRegex(ValueError, "supervised ChatGPT authentication"):
            CodexCLIExecutionAdapter(executable=str(self.codex), repository_path=self.repo,
                repository_reference="repo://example/test", codex_home=Path.home() / ".codex",
                workspace_root=self.workspace, artifact_root=self.artifacts,
                supervised_chatgpt_session=True)

    def test_persistent_owner_session_uses_existing_protected_login_without_tty(self):
        owner_home = self.root / "admin1"
        codex_home = owner_home / ".codex"
        codex_home.mkdir(parents=True, mode=0o700)
        auth = codex_home / "auth.json"
        auth.write_text("synthetic credential marker", encoding="utf-8")
        auth.chmod(0o600)
        with patch("riverview_core.resident_execution.codex_cli.Path.home",
                   return_value=owner_home), \
             patch("riverview_core.resident_execution.codex_cli.pwd.getpwnam",
                   return_value=SimpleNamespace(pw_uid=os.geteuid())):
            adapter = CodexCLIExecutionAdapter(executable=str(self.codex),
                repository_path=self.repo, repository_reference="repo://example/test",
                codex_home=codex_home, workspace_root=self.workspace,
                artifact_root=self.artifacts, persistent_chatgpt_owner_session=True)
        self.assertTrue(adapter.persistent_chatgpt_owner_session)
        self.assertFalse(adapter.supervised_chatgpt_session)
        self.assertEqual(adapter._preflight()[1], self.repo.resolve())
        self.assertEqual(auth.read_text(encoding="utf-8"), "synthetic credential marker")

    def test_persistent_owner_session_rejects_copy_or_weak_auth_file(self):
        owner_home = self.root / "admin1"
        codex_home = owner_home / ".codex"
        codex_home.mkdir(parents=True, mode=0o700)
        auth = codex_home / "auth.json"
        auth.write_text("synthetic credential marker", encoding="utf-8")
        auth.chmod(0o644)
        with patch("riverview_core.resident_execution.codex_cli.Path.home",
                   return_value=owner_home), \
             patch("riverview_core.resident_execution.codex_cli.pwd.getpwnam",
                   return_value=SimpleNamespace(pw_uid=os.geteuid())):
            with self.assertRaisesRegex(ValueError, "protected local login"):
                CodexCLIExecutionAdapter(executable=str(self.codex),
                    repository_path=self.repo, repository_reference="repo://example/test",
                    codex_home=codex_home, workspace_root=self.workspace,
                    artifact_root=self.artifacts, persistent_chatgpt_owner_session=True)


if __name__ == "__main__":
    unittest.main()
