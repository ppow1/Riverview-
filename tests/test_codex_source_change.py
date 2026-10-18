# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_codex_source_change.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.5
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Cover source target provenance and the pinned PR62 two-step patch/verifier sequence.
# Purpose: Verify explicit multi-file Codex source-change scope and independent patch checking
# Execution Model: Isolated temporary Git repository and synthetic CLI; no production services
# Observability: Assert patch digest, changed-file inventory, path rejection and verifier decision
# Dependencies: Python 3; Git; pytest
# Authority: Synthetic assignment only; does not grant execution or apply production patches
# Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-001 | Add bounded source-change adapter tests
# Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-001 | Exercise isolated offline tests and ensure source capability stays independently registered
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reuse an owner-only patch safely when worker-result persistence is interrupted
# Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-OBJECTIVE-CONTEXT | Ensure source-change Codex receives the original task while scope remains step-specific
# Contracts: src/riverview_core/resident_execution/codex_source_change.py
# Tests: This file
# History: Git
# =============================================================================
"""Tests for bounded Codex multi-file source changes and separate verification."""

import os
import hashlib
import json
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
            f"marker=pathlib.Path({str(self.root / 'codex-calls')!r})\n"
            "marker.write_text(str(int(marker.read_text())+1) if marker.exists() else '1')\n"
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
            calls_before_recovery = (self.root / "codex-calls").read_text()
            recovered = adapter.execute(self.assignment)
        self.assertEqual(decision["decision"], "ACCEPTED")
        self.assertEqual(recovered.status, "PATCH_PRODUCED")
        self.assertEqual(recovered.detail_code, "recovered_existing_patch")
        self.assertEqual((self.root / "codex-calls").read_text(), calls_before_recovery)
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

    def test_source_action_carries_original_objective_into_bounded_step(self):
        from riverview_core.resident_execution.codex_workflow import CodexSourceChangeWorkAction
        source_scope = ("src/a.py", "tests/test_ab.py")
        step = {"step_id": "step-1", "objective": "Implement the addition function",
            "acceptance_criteria": ("Test zero and signed values",), "depends_on": (),
            "execution_capability": CAPABILITY, "authorized_paths": list(source_scope),
            "test_targets": ["tests/test_ab.py"], "repository_reference": "repo://test/repo",
            "repository_revision": self.revision}
        binding = {"version": "grace.source-target-binding.v1",
            "objective_id": "objective:scope-context", "assignment_id": "assignment:scope-context",
            "step_id": "step-1", "capability": CAPABILITY,
            "repository_reference": "repo://test/repo", "repository_revision": self.revision,
            "authorized_paths": list(source_scope), "test_targets": ["tests/test_ab.py"],
            "proposal_step_sha256": hashlib.sha256(json.dumps(step, sort_keys=True,
                separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()}
        objective = {"status": "WORK_ORDER_CREATED", "assignment_id": "assignment:scope-context",
            "request": "Implement exact addition and test positive, negative, and zero values.",
            "source_revision": "b" * 40, "source_sha256": "c" * 64,
            "evidence": {"status": "VERIFIED", "retrieval_complete": True,
                "source_revision": "b" * 40, "source_sha256": "c" * 64},
            "proposal": {"steps": [step]}}

        class Pipeline:
            def get_objective(self, _objective_id): return objective
            def proposal_step_for_assignment(self, _objective_id, _assignment_id):
                return {**step, "source_target_binding": binding}

        action = CodexSourceChangeWorkAction(Pipeline(),
            CodexSourceChangeAdapter(base_adapter=self.base,
                repository_reference="repo://test/repo", authorized_paths=source_scope),
            "repo://test/repo")
        _objective, _step, request = action._assignment({
            "id": "assignment:scope-context", "objective_ref": "objective:scope-context"})
        self.assertIn(objective["request"], request.task_scope)
        self.assertIn(step["objective"], request.task_scope)
        self.assertEqual(request.authorized_paths, source_scope)
        self.assertEqual(request.test_targets, ("tests/test_ab.py",))
        self.assertEqual(request.repository_reference, "repo://test/repo")
        self.assertEqual(request.repository_revision, self.revision)
        self.assertEqual(objective["source_revision"], "b" * 40)

    def test_source_action_rejects_unbound_historical_proposal(self):
        from riverview_core.resident_execution.codex_workflow import (
            CodexActionFailure, CodexSourceChangeWorkAction)
        step = {"step_id": "step-1", "objective": "edit", "acceptance_criteria": ("done",),
            "depends_on": (), "execution_capability": CAPABILITY,
            "authorized_paths": ("src/a.py", "tests/test_ab.py"),
            "test_targets": ("tests/test_ab.py",), "repository_reference": "repo://test/repo",
            "repository_revision": self.revision}
        objective = {"status": "WORK_ORDER_CREATED", "assignment_id": "assignment:old",
            "request": "edit", "source_revision": "b" * 40,
            "source_sha256": "c" * 64, "evidence": {"status": "VERIFIED",
                "retrieval_complete": True, "source_revision": "b" * 40,
                "source_sha256": "c" * 64}, "proposal": {"steps": [step]}}
        class Pipeline:
            def get_objective(self, _objective_id): return objective
            def proposal_step_for_assignment(self, _objective_id, _assignment_id):
                return {**step, "source_target_binding": None}
        action = CodexSourceChangeWorkAction(Pipeline(), CodexSourceChangeAdapter(
            base_adapter=self.base, repository_reference="repo://test/repo",
            authorized_paths=self.paths), "repo://test/repo")
        with self.assertRaisesRegex(CodexActionFailure, "persisted_source_target_binding_invalid"):
            action._assignment({"id": "assignment:old", "objective_ref": "objective:old"})

    def test_source_action_rejects_mutated_proposal_and_wrong_target_configuration(self):
        from riverview_core.resident_execution.codex_workflow import (
            CodexActionFailure, CodexSourceChangeWorkAction)
        step = {"step_id": "step-1", "objective": "edit", "acceptance_criteria": ("done",),
            "depends_on": (), "execution_capability": CAPABILITY,
            "authorized_paths": ["src/a.py", "tests/test_ab.py"],
            "test_targets": ["tests/test_ab.py"], "repository_reference": "repo://test/repo",
            "repository_revision": self.revision}
        binding = {"version": "grace.source-target-binding.v1",
            "objective_id": "objective:mutation", "assignment_id": "assignment:mutation",
            "step_id": "step-1", "capability": CAPABILITY,
            "repository_reference": "repo://test/repo", "repository_revision": self.revision,
            "authorized_paths": step["authorized_paths"], "test_targets": step["test_targets"],
            "proposal_step_sha256": hashlib.sha256(json.dumps(step, sort_keys=True,
                separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()}
        objective = {"status": "WORK_ORDER_CREATED", "assignment_id": "assignment:mutation",
            "request": "edit", "source_revision": "b" * 40, "source_sha256": "c" * 64,
            "evidence": {"status": "VERIFIED", "retrieval_complete": True,
                "source_revision": "b" * 40, "source_sha256": "c" * 64},
            "proposal": {"steps": [step]}}
        class Pipeline:
            def get_objective(self, _objective_id): return objective
            def proposal_step_for_assignment(self, _objective_id, _assignment_id):
                return {**step, "source_target_binding": binding}
        action = CodexSourceChangeWorkAction(Pipeline(), CodexSourceChangeAdapter(
            base_adapter=self.base, repository_reference="repo://test/repo",
            authorized_paths=self.paths), "repo://test/repo")
        step["objective"] = "mutated after dispatch"
        with self.assertRaisesRegex(CodexActionFailure, "persisted_source_target_binding_invalid"):
            action._assignment({"id": "assignment:mutation", "objective_ref": "objective:mutation"})
        self.assertFalse(action.validate_proposal_target({**step,
            "repository_reference": "repo://another/repository"}))
        self.assertFalse(action.validate_proposal_target({**step,
            "repository_revision": "d" * 40}))
        self.assertFalse(action.validate_proposal_target({**step,
            "authorized_paths": ["src/a.py", "tests/test_ab.py", "src/outside.py"]}))

    @unittest.skipUnless(Path("/opt/riverview-pr62-disposable-acceptance/.git").exists(),
                         "pinned PR62 disposable fixture is not installed")
    def test_pinned_pr62_two_step_patch_chain_is_independently_replayed(self):
        fixture = Path("/opt/riverview-pr62-disposable-acceptance")
        pinned = "5885c8d9395dde43898f7a47a37a15cfc849299a"
        target = self.root / "pr62-target"
        import shutil as shutil_module
        shutil_module.copytree(fixture, target)
        observed = subprocess.check_output(["/usr/bin/git", "-C", str(target),
            "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        if observed != pinned:
            self.skipTest("isolated PR62 copy is not at the reviewed immutable commit")
        self.codex.write_text("#!/usr/bin/env python3\n"
            "import json,pathlib,sys\n"
            "prompt=sys.stdin.read()\n"
            "root=pathlib.Path.cwd()\n"
            "if 'readiness_report' not in prompt:\n"
            " (root/'src/status.py').write_text('def normalize_status(value):\\n    return str(value).strip().upper()\\n')\n"
            "else:\n"
            " (root/'src/report.py').write_text('from status import normalize_status\\n\\ndef readiness_report(value):\\n    return f\\\"Readiness: {normalize_status(value)}\\\"\\n')\n"
            "p=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1])\n"
            "p.write_text(json.dumps({'status':'PATCH_PRODUCED','summary':'bounded PR62 change'}))\n",
            encoding="utf-8")
        self.codex.chmod(0o700)
        base = CodexCLIExecutionAdapter(executable=str(self.codex), repository_path=target,
            repository_reference="repo://riverview/pr62-disposable-acceptance",
            codex_home=self.codex_home, workspace_root=self.workspace,
            artifact_root=self.artifacts)
        all_paths = ("src/status.py", "tests/test_status.py", "src/report.py",
                     "tests/test_report.py")
        adapter = CodexSourceChangeAdapter(base_adapter=base,
            repository_reference="repo://riverview/pr62-disposable-acceptance",
            authorized_paths=all_paths)
        verifier = CodexSourceChangeVerifier(base_adapter=base, authorized_paths=all_paths)
        first = CodexSourceChangeAssignment("assignment:pr62:step1", "objective:pr62:test",
            "repo://riverview/pr62-disposable-acceptance", pinned,
            "Implement normalize_status to trim whitespace and uppercase status.",
            ('normalize_status(" ready ") == "READY"',),
            ("src/status.py", "tests/test_status.py"), ("tests/test_status.py",),
            timeout_seconds=30)
        first_result = adapter.execute(first)
        first_decision = verifier.verify(first, first_result)
        self.assertEqual(first_result.status, "PATCH_PRODUCED")
        self.assertEqual(first_decision["decision"], "ACCEPTED")
        self.assertIn("base-revision:" + pinned, first_decision["evidence"])
        second = CodexSourceChangeAssignment("assignment:pr62:step2", "objective:pr62:test",
            "repo://riverview/pr62-disposable-acceptance", pinned,
            "Implement readiness_report as Readiness: READY using normalize_status.",
            ('readiness_report(" ready ") == "Readiness: READY"',), all_paths,
            ("tests/test_status.py", "tests/test_report.py"), timeout_seconds=30,
            prior_patches=((first_result.patch_path, first_result.patch_sha256),))
        second_result = adapter.execute(second)
        second_decision = verifier.verify(second, second_result)
        self.assertEqual(second_result.status, "PATCH_PRODUCED", second_result.detail_code)
        self.assertEqual(second_result.repository_reference,
                         "repo://riverview/pr62-disposable-acceptance")
        self.assertEqual(second_result.repository_revision, pinned)
        self.assertEqual(second_decision["decision"], "ACCEPTED")
        self.assertIn("changed:src/status.py", second_decision["evidence"])
        self.assertIn("changed:src/report.py", second_decision["evidence"])
        self.assertIn("test:tests/test_status.py", second_decision["evidence"])
        self.assertIn("test:tests/test_report.py", second_decision["evidence"])
        self.assertEqual(subprocess.check_output(["/usr/bin/git", "-C", str(target),
            "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip(), pinned)

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap is not installed")
    def test_fixed_pytest_target_runs_in_offline_bubblewrap_sandbox(self):
        repo = self.root / "offline-tests"
        (repo / "tests").mkdir(parents=True)
        (repo / "tests/test_offline.py").write_text(
            "def test_offline():\n    assert 3 * 7 == 21\n", encoding="utf-8")
        self.assertTrue(_run_tests(repo, ("tests/test_offline.py",), 20))


if __name__ == "__main__":
    unittest.main()
