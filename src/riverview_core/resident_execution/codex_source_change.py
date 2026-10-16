# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/codex_source_change.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.3
# Purpose: Execute explicitly scoped multi-file Engineering changes in a pinned disposable clone
# Execution Model: Leased worker action followed by independent patch and test verification
# Observability: Changed-file list, patch digest, base revision, test status and verifier evidence
# Dependencies: Codex CLI owner session; Git; bubblewrap; pytest-compatible configured runner
# Authority: Separate source-change capability; explicit exact file scope; never applies to production
# Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-001 | Initial bounded multi-file source change capability
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Chain independently verified predecessor patches for dependent work-order steps
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Recover and revalidate a durable patch after interruption before worker-result persistence
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Read patch artifacts with no-follow descriptor checks during independent verification
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: tests/test_codex_source_change.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Bounded Codex source-change execution and independent patch verification.

The adapter accepts only a durable assignment that names its immutable base,
authorized paths and fixed test targets. It returns a patch artifact; it never
applies that patch to the configured source checkout or a production release.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

from .codex_cli import CodexAdapterError, CodexCLIExecutionAdapter, _COMMIT

CAPABILITY = "engineering.codex-cli-source-change.v1"
CAPABILITY_REQUIREMENTS = {
    "capability": CAPABILITY,
    "dependencies": ("dedicated_codex_executable", "existing_chatgpt_owner_session",
                     "pinned_local_repository", "isolated_workspace", "artifact_filesystem",
                     "offline_bwrap_test_runner"),
    "authority_actions": ("worker.register", "assignment.execute", "assignment.verify"),
    "readiness": "startup_preflight_and_current_worker_heartbeat",
}
MAX_PATCH_BYTES = 2 * 1024 * 1024
_SAFE_PATH = re.compile(r"^(?:src|tests|docs)/[A-Za-z0-9._/-]{1,240}$")


def _paths(values, *, minimum=1, maximum=32):
    if (not isinstance(values, tuple) or not minimum <= len(values) <= maximum or
            any(not isinstance(path, str) or not _SAFE_PATH.fullmatch(path) or
                path.startswith("/") or ".." in Path(path).parts or
                ".git" in Path(path).parts for path in values) or
            len(set(values)) != len(values)):
        raise ValueError("source-change path scope is invalid")
    return values


@dataclass(frozen=True)
class CodexSourceChangeAssignment:
    assignment_id: str
    objective_id: str
    repository_reference: str
    repository_revision: str
    task_scope: str
    acceptance_criteria: tuple[str, ...]
    authorized_paths: tuple[str, ...]
    test_targets: tuple[str, ...]
    timeout_seconds: int = 300
    prior_patches: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if (not isinstance(self.assignment_id, str) or not self.assignment_id or
                not isinstance(self.objective_id, str) or not self.objective_id or
                not isinstance(self.repository_reference, str) or
                not self.repository_reference.startswith("repo://") or
                not isinstance(self.repository_revision, str) or
                not _COMMIT.fullmatch(self.repository_revision) or
                not isinstance(self.task_scope, str) or not self.task_scope.strip() or
                len(self.task_scope.encode()) > 4000 or
                not isinstance(self.acceptance_criteria, tuple) or
                not 1 <= len(self.acceptance_criteria) <= 20 or
                any(not isinstance(item, str) or not item.strip() or len(item) > 1000
                    for item in self.acceptance_criteria) or
                type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 300):
            raise ValueError("source-change assignment exceeds its bounded contract")
        _paths(self.authorized_paths)
        _paths(self.test_targets)
        if not set(self.test_targets) <= set(self.authorized_paths):
            raise ValueError("test targets must be included in the explicit authorized path scope")
        if (not isinstance(self.prior_patches, tuple) or len(self.prior_patches) > 1 or
                any(not isinstance(item, tuple) or len(item) != 2 or
                    not isinstance(item[0], str) or
                    not re.fullmatch(r"[0-9a-f]{64}", str(item[1]))
                    for item in self.prior_patches)):
            raise ValueError("source-change predecessor patch chain is invalid")


@dataclass(frozen=True)
class CodexSourceChangeResult:
    status: str
    capability: str
    assignment_id: str
    objective_id: str
    repository_revision: str
    changed_files: tuple[str, ...]
    patch_path: str | None
    patch_sha256: str | None
    patch_bytes: int | None
    test_status: str
    detail_code: str
    execution_started: bool


def _run_tests(repository: Path, targets: tuple[str, ...], timeout: int) -> bool:
    """Run only fixed pytest targets in an offline, read-only-root bwrap sandbox."""
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return False
    command = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
        "--unshare-net", "--bind", str(repository), str(repository), "--chdir",
        str(repository), sys.executable, "-m", "pytest", "-q", *targets]
    environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
                  "TMPDIR": "/tmp", "PYTHONPATH": str(repository / "src")}
    try:
        result = subprocess.run(command, cwd=repository, env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=timeout, check=False, close_fds=True)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class CodexSourceChangeAdapter:
    """Produce a scoped patch and run its requested tests in a disposable clone."""

    def __init__(self, *, base_adapter: CodexCLIExecutionAdapter,
                 repository_reference: str, authorized_paths: tuple[str, ...],
                 max_timeout_seconds: int = 300):
        if (not isinstance(base_adapter, CodexCLIExecutionAdapter) or
                not repository_reference.startswith("repo://") or
                type(max_timeout_seconds) is not int or not 1 <= max_timeout_seconds <= 300):
            raise ValueError("source-change adapter configuration is invalid")
        self.base = base_adapter
        self.repository_reference = repository_reference
        self.authorized_paths = _paths(authorized_paths, maximum=128)
        self.max_timeout_seconds = max_timeout_seconds

    def execute(self, assignment: CodexSourceChangeAssignment) -> CodexSourceChangeResult:
        if not isinstance(assignment, CodexSourceChangeAssignment):
            raise TypeError("a typed source-change assignment is required")
        if assignment.repository_reference != self.repository_reference:
            return self._result(assignment, "WAITING_FOR_RESOURCE", "repository_not_registered")
        if (not set(assignment.authorized_paths) <= set(self.authorized_paths) or
                assignment.timeout_seconds > self.max_timeout_seconds):
            return self._result(assignment, "BLOCKED", "source_scope_not_registered")
        try:
            binary, source = self.base._preflight()
            revision = self.base._git(["-C", str(source), "rev-parse", "--verify", "HEAD"],
                                      safe_repository=source)
            if revision != assignment.repository_revision:
                return self._result(assignment, "WAITING_FOR_EVIDENCE", "repository_revision_mismatch")
        except CodexAdapterError as exc:
            return self._result(assignment, "UNAVAILABLE", exc.code)
        key = hashlib.sha256(assignment.assignment_id.encode()).hexdigest()
        patch_path = self.base.artifact_root / f"codex-source-{key}.patch"
        if patch_path.exists() or patch_path.is_symlink():
            return self._recover_existing_patch(assignment, patch_path)
        started = False
        try:
            with tempfile.TemporaryDirectory(prefix=f"{key[:12]}-",
                    dir=self.base.workspace_root) as temporary:
                root = Path(temporary)
                repo = root / "repo"
                self.base._git(["clone", "--quiet", "--no-hardlinks", "--no-checkout",
                    "--", str(source), str(repo)], safe_repository=source)
                self.base._git(["-C", str(repo), "checkout", "--quiet", "--detach", revision])
                for prior_path, prior_sha256 in assignment.prior_patches:
                    prior_file = self._verified_prior_patch(prior_path, prior_sha256)
                    check_prior = subprocess.run(["/usr/bin/git", "-C", str(repo),
                        "apply", "--check", "--whitespace=error", str(prior_file)],
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=15, check=False, close_fds=True)
                    if check_prior.returncode:
                        return self._result(assignment, "WAITING_FOR_EVIDENCE",
                                            "predecessor_patch_not_applicable")
                    apply_prior = subprocess.run(["/usr/bin/git", "-C", str(repo),
                        "apply", "--whitespace=error", str(prior_file)],
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=15, check=False, close_fds=True)
                    if apply_prior.returncode or not set(
                            self.base._workspace_changed_paths(repo, revision)) <= set(
                                assignment.authorized_paths):
                        return self._result(assignment, "BLOCKED", "predecessor_scope_invalid")
                schema = root / "result.schema.json"
                schema.write_text(json.dumps({"type": "object", "properties": {
                    "status": {"const": "PATCH_PRODUCED"},
                    "summary": {"type": "string", "minLength": 1, "maxLength": 500}},
                    "required": ["status", "summary"], "additionalProperties": False}),
                    encoding="utf-8")
                result_file = root / "result.json"
                files = "\n".join("- " + item for item in assignment.authorized_paths)
                criteria = "\n".join("- " + item for item in assignment.acceptance_criteria)
                prompt = ("Make the requested source change only in the explicitly authorized files. "
                    "Do not access network services, secrets, credentials, or paths outside this repository. "
                    "Do not run arbitrary shell commands. Do not apply changes outside the listed scope. "
                    "After the edits, return the required structured result.\n\n"
                    f"Assignment: {assignment.assignment_id}\nTask:\n{assignment.task_scope}\n"
                    f"Acceptance criteria:\n{criteria}\nAuthorized files:\n{files}\n")
                env = {"PATH": "/usr/local/bin:/usr/bin:/bin",
                       "HOME": str(self.base.codex_home.parent if
                           (self.base.supervised_chatgpt_session or
                            self.base.persistent_chatgpt_owner_session) else self.base.codex_home),
                       "CODEX_HOME": str(self.base.codex_home), "TMPDIR": str(root)}
                argv = [str(binary), "exec", "--sandbox", "workspace-write", "--ephemeral",
                    "--ignore-user-config", "-c", 'approval_policy="never"', "-c",
                    "sandbox_workspace_write.network_access=false", "-C", str(repo),
                    "--output-schema", str(schema), "--output-last-message", str(result_file), "-"]
                process = subprocess.Popen(argv, cwd=repo, env=env, stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                    start_new_session=True)
                started = True
                try:
                    process.communicate(prompt.encode(), timeout=assignment.timeout_seconds)
                except subprocess.TimeoutExpired:
                    import signal
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                    return self._result(assignment, "UNAVAILABLE", "codex_timeout", started=started)
                if process.returncode:
                    return self._result(assignment, "UNAVAILABLE", "codex_process_failed", started=started)
                try:
                    parsed = json.loads(result_file.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    return self._result(assignment, "INVALID_RESULT", "codex_result_missing", started=started)
                if (not isinstance(parsed, dict) or set(parsed) != {"status", "summary"} or
                        parsed["status"] != "PATCH_PRODUCED" or not parsed["summary"].strip()):
                    return self._result(assignment, "INVALID_RESULT", "codex_result_invalid", started=started)
                changed = tuple(sorted(self.base._workspace_changed_paths(repo, revision)))
                if not changed or not set(changed) <= set(assignment.authorized_paths):
                    return self._result(assignment, "INVALID_RESULT", "workspace_change_set_invalid", started=started)
                for changed_path in changed:
                    candidate = repo / changed_path
                    metadata = candidate.lstat()
                    if not stat.S_ISREG(metadata.st_mode) or candidate.is_symlink():
                        return self._result(assignment, "INVALID_RESULT",
                            "workspace_change_metadata_invalid", started=started)
                # Stage only the allowlisted changed files in the disposable clone
                # to include both tracked edits and new files in the patch.
                self.base._git(["-C", str(repo), "add", "--", *changed])
                checked = subprocess.run(["/usr/bin/git", "-C", str(repo), "diff", "--cached",
                    "--check", revision, "--", *changed], stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                    check=False, close_fds=True)
                if checked.returncode:
                    return self._result(assignment, "INVALID_RESULT", "patch_integrity_check_failed", started=started)
                patch = subprocess.run(["/usr/bin/git", "-C", str(repo), "diff", "--cached",
                    "--binary", "--no-ext-diff", revision, "--", *changed],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    timeout=20, check=False, close_fds=True)
                if patch.returncode or not patch.stdout or len(patch.stdout) > MAX_PATCH_BYTES:
                    return self._result(assignment, "INVALID_RESULT", "patch_size_or_generation_invalid", started=started)
                if not _run_tests(repo, assignment.test_targets, assignment.timeout_seconds):
                    return self._result(assignment, "INVALID_RESULT", "requested_tests_failed", started=started)
                self.base._write_artifact(patch_path, patch.stdout)
                return CodexSourceChangeResult("PATCH_PRODUCED", CAPABILITY,
                    assignment.assignment_id, assignment.objective_id, revision, changed,
                    str(patch_path), hashlib.sha256(patch.stdout).hexdigest(), len(patch.stdout),
                    "passed", "independent_verification_required", started)
        except CodexAdapterError as exc:
            return self._result(assignment, "UNAVAILABLE", exc.code, started=started)
        except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
            return self._result(assignment, "UNAVAILABLE", "source_change_adapter_failed", started=started)

    @staticmethod
    def _result(assignment, status, code, *, started=False):
        return CodexSourceChangeResult(status, CAPABILITY, assignment.assignment_id,
            assignment.objective_id, assignment.repository_revision, (), None, None, None,
            "not_run", code, started)

    def _verified_prior_patch(self, path_value, expected_sha256):
        """Open an owner-only predecessor patch confined to the configured artifact root."""
        root = self.base.artifact_root.resolve(strict=True)
        path = Path(path_value)
        info = path.lstat()
        if (path.parent.resolve(strict=True) != root or path.is_symlink() or
                not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                stat.S_IMODE(info.st_mode) != 0o600 or not 0 < info.st_size <= MAX_PATCH_BYTES):
            raise CodexAdapterError("predecessor_patch_metadata_invalid")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            raw = os.read(fd, MAX_PATCH_BYTES + 1)
        finally:
            os.close(fd)
        if len(raw) != info.st_size or hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise CodexAdapterError("predecessor_patch_digest_mismatch")
        return path

    def _recover_existing_patch(self, assignment, patch_path):
        """Re-adopt an interrupted same-assignment patch only after fresh replay and tests."""
        try:
            root = self.base.artifact_root.resolve(strict=True)
            info = patch_path.lstat()
            if (patch_path.parent.resolve(strict=True) != root or patch_path.is_symlink() or
                    not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or
                    not 0 < info.st_size <= MAX_PATCH_BYTES):
                return self._result(assignment, "BLOCKED", "existing_patch_metadata_invalid")
            fd = os.open(patch_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                patch = os.read(fd, MAX_PATCH_BYTES + 1)
            finally:
                os.close(fd)
            if len(patch) != info.st_size:
                return self._result(assignment, "BLOCKED", "existing_patch_read_invalid")
            binary, source = self.base._preflight()
            del binary
            revision = self.base._git(["-C", str(source), "rev-parse", "--verify", "HEAD"],
                                      safe_repository=source)
            if revision != assignment.repository_revision:
                return self._result(assignment, "WAITING_FOR_EVIDENCE",
                                    "repository_revision_mismatch")
            with tempfile.TemporaryDirectory(prefix="recover-source-patch-",
                    dir=self.base.workspace_root) as temporary:
                root = Path(temporary)
                repo = root / "repo"
                self.base._git(["clone", "--quiet", "--no-hardlinks", "--no-checkout",
                    "--", str(source), str(repo)], safe_repository=source)
                self.base._git(["-C", str(repo), "checkout", "--quiet", "--detach", revision])
                patch_file = root / "existing.patch"
                patch_file.write_bytes(patch)
                check = subprocess.run(["/usr/bin/git", "-C", str(repo), "apply", "--check",
                    "--whitespace=error", str(patch_file)], stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                    check=False, close_fds=True)
                if check.returncode:
                    return self._result(assignment, "BLOCKED", "existing_patch_not_applicable")
                apply = subprocess.run(["/usr/bin/git", "-C", str(repo), "apply",
                    "--whitespace=error", str(patch_file)], stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                    check=False, close_fds=True)
                changed = tuple(sorted(self.base._workspace_changed_paths(repo, revision)))
                if (apply.returncode or not changed or
                        not set(changed) <= set(assignment.authorized_paths)):
                    return self._result(assignment, "BLOCKED", "existing_patch_scope_invalid")
                if not _run_tests(repo, assignment.test_targets, assignment.timeout_seconds):
                    return self._result(assignment, "BLOCKED", "existing_patch_tests_failed")
            return CodexSourceChangeResult("PATCH_PRODUCED", CAPABILITY,
                assignment.assignment_id, assignment.objective_id, revision, changed,
                str(patch_path), hashlib.sha256(patch).hexdigest(), len(patch),
                "passed", "recovered_existing_patch", False)
        except (OSError, ValueError, subprocess.SubprocessError, CodexAdapterError):
            return self._result(assignment, "BLOCKED", "existing_patch_recovery_failed")


class CodexSourceChangeVerifier:
    """Reapply a patch to a fresh pinned clone and independently rerun its tests."""

    def __init__(self, *, base_adapter: CodexCLIExecutionAdapter,
                 authorized_paths: tuple[str, ...], max_timeout_seconds: int = 300):
        self.base = base_adapter
        self.authorized_paths = _paths(authorized_paths, maximum=128)
        self.max_timeout_seconds = max_timeout_seconds

    def verify(self, assignment: CodexSourceChangeAssignment, result: CodexSourceChangeResult):
        if (not isinstance(assignment, CodexSourceChangeAssignment) or
                not isinstance(result, CodexSourceChangeResult) or
                result.status != "PATCH_PRODUCED" or result.capability != CAPABILITY or
                result.assignment_id != assignment.assignment_id or
                result.objective_id != assignment.objective_id or
                result.repository_revision != assignment.repository_revision or
                result.test_status != "passed" or
                not set(assignment.authorized_paths) <= set(self.authorized_paths) or
                not set(result.changed_files) <= set(assignment.authorized_paths) or
                not result.changed_files or assignment.timeout_seconds > self.max_timeout_seconds):
            return {"decision": "REJECTED", "reason": "source_change_contract_invalid",
                    "evidence": []}
        path = Path(result.patch_path or "")
        try:
            root = self.base.artifact_root.resolve(strict=True)
            info = path.lstat()
            if (path.parent.resolve(strict=True) != root or path.is_symlink() or
                    not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or not 0 < info.st_size <= MAX_PATCH_BYTES):
                raise ValueError
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                opened = os.fstat(fd)
                if (not stat.S_ISREG(opened.st_mode) or opened.st_uid != os.geteuid() or
                        stat.S_IMODE(opened.st_mode) != 0o600 or opened.st_size != info.st_size):
                    raise ValueError
                patch = os.read(fd, MAX_PATCH_BYTES + 1)
            finally:
                os.close(fd)
            if (len(patch) != result.patch_bytes or
                    hashlib.sha256(patch).hexdigest() != result.patch_sha256):
                raise ValueError
            _, source = self.base._preflight()
            with tempfile.TemporaryDirectory(prefix="rv-source-verify-",
                    dir=self.base.workspace_root) as temporary:
                repo = Path(temporary) / "repo"
                self.base._git(["clone", "--quiet", "--no-hardlinks", "--no-checkout",
                    "--", str(source), str(repo)], safe_repository=source)
                self.base._git(["-C", str(repo), "checkout", "--quiet", "--detach",
                    assignment.repository_revision])
                patch_file = Path(temporary) / "candidate.patch"
                patch_file.write_bytes(patch)
                check = subprocess.run(["/usr/bin/git", "-C", str(repo), "apply", "--check",
                    "--whitespace=error", str(patch_file)], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=15, check=False, close_fds=True)
                if check.returncode:
                    raise ValueError
                apply = subprocess.run(["/usr/bin/git", "-C", str(repo), "apply",
                    "--whitespace=error", str(patch_file)], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=15, check=False, close_fds=True)
                if apply.returncode:
                    raise ValueError
                changed = tuple(sorted(self.base._workspace_changed_paths(
                    repo, assignment.repository_revision)))
                if changed != tuple(sorted(result.changed_files)) or not set(changed) <= set(assignment.authorized_paths):
                    raise ValueError
                if not _run_tests(repo, assignment.test_targets, assignment.timeout_seconds):
                    return {"decision": "REJECTED", "reason": "independent_tests_failed",
                            "evidence": ["patch-sha256:" + result.patch_sha256]}
            return {"decision": "ACCEPTED", "reason": "scoped_patch_and_tests_verified",
                    "evidence": ["patch-sha256:" + result.patch_sha256,
                                 "base-revision:" + assignment.repository_revision,
                                 *["changed:" + item for item in result.changed_files],
                                 *["test:" + item for item in assignment.test_targets]]}
        except (OSError, ValueError, subprocess.SubprocessError, CodexAdapterError):
            return {"decision": "REJECTED", "reason": "patch_integrity_or_verification_failed",
                    "evidence": []}
