# Revision: 1.0.2 | 2026-10-28
# Changed: Use a dedicated synthetic fixture so tests are independent of deployment-template revision.
"""Offline guards and rollback tests for the approved source-worker updater."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from update_grace_source_worker_20261028 import (  # noqa: E402
    APPROVED_PATHS,
    RELEASE_MANIFEST_PATHS,
    GuardFailure,
    atomic_replace,
    create_backup,
    parse_loaded_environment,
    parse_dropin_environment,
    render_dropin,
    stage_exact_checkout,
    transition_with_rollback,
)
import update_grace_source_worker_20261028 as updater  # noqa: E402


class GraceSourceWorkerUpdateTests(unittest.TestCase):
    def test_idle_cgroup_check_succeeds_without_tty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            group = root / "system.slice" / updater.UNIT
            group.mkdir(parents=True)
            (group / "cgroup.procs").write_text("123\n", encoding="ascii")
            values = {
                "ActiveState": "active", "MainPID": "123",
                "ControlGroup": f"/system.slice/{updater.UNIT}",
            }
            with patch.object(updater, "systemd_property", side_effect=values.__getitem__):
                updater._check_idle_cgroup("123", root)

    def test_idle_cgroup_check_rejects_additional_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            group = root / "system.slice" / updater.UNIT
            group.mkdir(parents=True)
            (group / "cgroup.procs").write_text("123\n456\n", encoding="ascii")
            values = {
                "ActiveState": "active", "MainPID": "123",
                "ControlGroup": f"/system.slice/{updater.UNIT}",
            }
            with patch.object(updater, "systemd_property", side_effect=values.__getitem__):
                with self.assertRaisesRegex(GuardFailure, "owner_session_cgroup_busy"):
                    updater._check_idle_cgroup("123", root)

    def test_idle_cgroup_check_fails_closed_when_process_state_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "system.slice" / updater.UNIT).mkdir(parents=True)
            values = {
                "ActiveState": "active", "MainPID": "123",
                "ControlGroup": f"/system.slice/{updater.UNIT}",
            }
            with patch.object(updater, "systemd_property", side_effect=values.__getitem__):
                with self.assertRaisesRegex(GuardFailure, "unit_cgroup_state_unavailable"):
                    updater._check_idle_cgroup("123", root)

    def test_apply_rechecks_idle_after_staging_before_any_protected_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old_release = root / "old"
            old_release.mkdir()
            target_release = root / "target"
            def preflight():
                updater._check_idle_cgroup("123")
                return b"original", b"candidate", None, {}, "123"

            with (
                patch.object(updater, "_preflight", side_effect=preflight),
                patch.object(updater, "TARGET_RELEASE", target_release),
                patch.object(updater, "OLD_RELEASE", old_release),
                patch.object(updater, "stage_exact_checkout", return_value=True) as stage,
                patch.object(updater, "_check_idle_cgroup",
                             side_effect=[None, GuardFailure("owner_session_cgroup_busy")]),
                patch.object(updater, "create_backup") as backup,
                patch.object(updater, "_atomic_receipt") as receipt,
            ):
                with self.assertRaisesRegex(GuardFailure, "owner_session_cgroup_busy"):
                    updater.apply_update()
                stage.assert_called_once()
                backup.assert_not_called()
                receipt.assert_not_called()

    def test_health_waits_for_startup_event_and_stable_loaded_pid(self):
        clock = {"now": 0.0}

        def monotonic():
            return clock["now"]

        def sleep(seconds):
            clock["now"] += seconds

        with (
            patch.object(updater, "STARTUP_TIMEOUT_SECONDS", 12),
            patch.object(updater, "STARTUP_STABLE_SECONDS", 3),
            patch.object(updater, "STARTUP_POLL_SECONDS", 1),
            patch.object(updater, "_unit_active", return_value=True),
            patch.object(updater, "systemd_property", side_effect=lambda key: {
                "MainPID": "321", "ExecMainStartTimestamp": "startup",
            }[key]),
            patch.object(updater, "verify_loaded") as loaded,
            patch.object(updater, "_journal_startup_state", return_value=(True, False)),
            patch.object(updater.time, "monotonic", side_effect=monotonic),
            patch.object(updater.time, "sleep", side_effect=sleep),
        ):
            updater.verify_service_health({}, previous_pid="123")
        self.assertGreaterEqual(clock["now"], 3)
        self.assertGreaterEqual(loaded.call_count, 4)

    def test_health_fails_closed_on_pid_change_or_missing_startup_event(self):
        pids = iter(("321", "322"))

        def properties(key):
            return next(pids) if key == "MainPID" else "startup"

        with patch.object(updater, "STARTUP_STABLE_SECONDS", 99), \
                patch.object(updater, "_unit_active", return_value=True), \
                patch.object(updater, "systemd_property", side_effect=properties), \
                patch.object(updater, "verify_loaded") as loaded, \
                patch.object(updater, "_journal_startup_state", return_value=(True, False)):
            with self.assertRaisesRegex(GuardFailure, "owner_session_pid_unstable"):
                updater.verify_service_health({}, previous_pid="123")
            loaded.assert_called_once_with({})

        clock = {"now": 0.0}

        def monotonic():
            return clock["now"]

        def sleep(seconds):
            clock["now"] += seconds

        with (
            patch.object(updater, "STARTUP_TIMEOUT_SECONDS", 3),
            patch.object(updater, "STARTUP_POLL_SECONDS", 1),
            patch.object(updater, "_unit_active", return_value=True),
            patch.object(updater, "systemd_property", side_effect=lambda key: {
                "MainPID": "321", "ExecMainStartTimestamp": "startup",
            }[key]),
            patch.object(updater, "verify_loaded"),
            patch.object(updater, "_journal_startup_state", return_value=(False, False)),
            patch.object(updater.time, "monotonic", side_effect=monotonic),
            patch.object(updater.time, "sleep", side_effect=sleep),
        ):
            with self.assertRaisesRegex(GuardFailure, "owner_session_startup_signal_missing"):
                updater.verify_service_health({})

    def test_renderer_changes_only_approved_source_mapping(self):
        source = (ROOT / "tests/fixtures/grace_source_worker_predecessor.conf").read_bytes()
        source += (
            b"Environment=RIVERVIEW_CODEX_REPOSITORY_PATH=/opt/artifact/current\n"
            b"Environment=RIVERVIEW_CODEX_REPOSITORY_REF=repo://artifact/repo\n"
            b"Environment=RIVERVIEW_ENGINEERING_ADAPTER=codex-cli\n"
            b"LoadCredential=worker-token:/etc/riverview/worker/grace-executor.credential\n")
        candidate = render_dropin(source)
        before = parse_dropin_environment(source)
        after = parse_dropin_environment(candidate)
        self.assertEqual(after["RIVERVIEW_SOURCE_CODEX_REPOSITORY_REF"],
                         before["RIVERVIEW_SOURCE_CODEX_REPOSITORY_REF"])
        self.assertEqual(after["RIVERVIEW_SOURCE_WORKER_ID"], before["RIVERVIEW_SOURCE_WORKER_ID"])
        self.assertEqual(after["RIVERVIEW_SOURCE_WORKER_PRINCIPAL"], before["RIVERVIEW_SOURCE_WORKER_PRINCIPAL"])
        self.assertEqual(after["RIVERVIEW_SOURCE_CODEX_WORKSPACE_DIR"],
                         before["RIVERVIEW_SOURCE_CODEX_WORKSPACE_DIR"])
        self.assertEqual(after["RIVERVIEW_SOURCE_CODEX_ARTIFACT_DIR"],
                         before["RIVERVIEW_SOURCE_CODEX_ARTIFACT_DIR"])
        self.assertEqual(after["RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS"],
                         __import__("json").dumps(list(APPROVED_PATHS), separators=(",", ":")))
        old_lines = source.decode().splitlines()
        new_lines = candidate.decode().splitlines()
        changed_old = [line for line in old_lines if line not in new_lines]
        changed_new = [line for line in new_lines if line not in old_lines]
        self.assertEqual(len(changed_old), 3)
        self.assertEqual(len(changed_new), 3)
        self.assertTrue(all(any(key in line for key in (
            "RIVERVIEW_SOURCE_CODEX_REPOSITORY_PATH",
            "RIVERVIEW_SOURCE_CODEX_REPOSITORY_REVISION",
            "RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS")) for line in changed_old + changed_new))
        for protected in (
            "Environment=RIVERVIEW_CODEX_REPOSITORY_PATH=/opt/artifact/current",
            "Environment=RIVERVIEW_CODEX_REPOSITORY_REF=repo://artifact/repo",
            "Environment=RIVERVIEW_ENGINEERING_ADAPTER=codex-cli",
            "LoadCredential=worker-token:/etc/riverview/worker/grace-executor.credential",
            "LoadCredential=source-worker-token:/etc/riverview/worker/grace-engineering-source-change.credential",
        ):
            self.assertIn(protected, candidate.decode())

    def test_renderer_fails_closed_on_source_config_drift_or_duplicate(self):
        baseline = (ROOT / "tests/fixtures/grace_source_worker_predecessor.conf").read_bytes()
        with self.assertRaisesRegex(GuardFailure, "dropin_source_baseline_mismatch"):
            render_dropin(baseline.replace(b"RIVERVIEW_SOURCE_WORKER_ENABLED=1",
                                           b"RIVERVIEW_SOURCE_WORKER_ENABLED=0"))
        duplicated = baseline + b"Environment=RIVERVIEW_SOURCE_WORKER_ID=unexpected\n"
        with self.assertRaisesRegex(GuardFailure, "dropin_source_key_duplicate"):
            render_dropin(duplicated)

    def test_loaded_environment_parser_returns_only_requested_safe_keys(self):
        selected = parse_loaded_environment(
            'RIVERVIEW_SOURCE_WORKER_ID=worker:grace-engineering-source-change '
            'RIVERVIEW_SOURCE_CODEX_REPOSITORY_PATH=/opt/source/release '
            'PRIVATE_TOKEN=synthetic-secret',
            ("RIVERVIEW_SOURCE_WORKER_ID", "RIVERVIEW_SOURCE_CODEX_REPOSITORY_PATH"))
        self.assertEqual(set(selected), {
            "RIVERVIEW_SOURCE_WORKER_ID", "RIVERVIEW_SOURCE_CODEX_REPOSITORY_PATH"})
        self.assertNotIn("PRIVATE_TOKEN", selected)
        last_value = parse_loaded_environment(
            "RIVERVIEW_SOURCE_WORKER_ENABLED=0 RIVERVIEW_SOURCE_WORKER_ENABLED=1",
            ("RIVERVIEW_SOURCE_WORKER_ENABLED",))
        self.assertEqual(last_value["RIVERVIEW_SOURCE_WORKER_ENABLED"], "1")

    def test_atomic_override_backup_and_rollback_preserve_exact_bytes_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "source-worker.conf"
            backup = Path(directory) / "source-worker.conf.backup"
            original = b"[Service]\nEnvironment=RIVERVIEW_SOURCE_WORKER_ENABLED=1\n"
            candidate = original + b"# candidate\n"
            config.write_bytes(original)
            config.chmod(0o640)
            info = config.stat()
            create_backup(config, backup, original, info)
            atomic_replace(config, candidate, mode=0o640, uid=info.st_uid, gid=info.st_gid)
            self.assertEqual(config.read_bytes(), candidate)
            self.assertEqual((config.stat().st_mode & 0o777, config.stat().st_uid, config.stat().st_gid),
                             (0o640, info.st_uid, info.st_gid))
            atomic_replace(config, backup.read_bytes(), mode=0o640, uid=info.st_uid, gid=info.st_gid)
            self.assertEqual(config.read_bytes(), original)
            self.assertEqual(backup.read_bytes(), original)

    def test_failed_activation_restores_exact_predecessor(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "source-worker.conf"
            original, candidate = b"old config\n", b"new config\n"
            config.write_bytes(original)
            info = config.stat()
            restored = []

            def activate():
                self.assertEqual(config.read_bytes(), candidate)
                raise RuntimeError("synthetic postcheck failure")

            def restore_activation():
                self.assertEqual(config.read_bytes(), original)
                restored.append(True)

            with self.assertRaisesRegex(GuardFailure, "apply_postcheck_failed_rolled_back"):
                transition_with_rollback(config, original, candidate, info,
                                         activate, restore_activation)
            self.assertEqual(config.read_bytes(), original)
            self.assertEqual(restored, [True])

    def test_clean_release_clone_uses_exact_commit_not_dirty_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.email", "test@invalid"], check=True)
            for relative in dict.fromkeys((*APPROVED_PATHS, *RELEASE_MANIFEST_PATHS)):
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("committed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
            subprocess.run(["git", "-C", str(source), "commit", "-qm", "immutable base"], check=True)
            revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
            (source / APPROVED_PATHS[1]).write_text("uncommitted workspace edit\n", encoding="utf-8")
            (source / "untracked-private-note.txt").write_text("excluded\n", encoding="utf-8")
            destination = root / "releases" / revision
            destination.parent.mkdir()
            self.assertTrue(stage_exact_checkout(source, destination, revision))
            self.assertEqual(subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip(), revision)
            self.assertEqual(subprocess.check_output(["git", "-C", str(destination), "status",
                "--porcelain", "--untracked-files=no"], text=True), "")
            self.assertEqual((destination / APPROVED_PATHS[1]).read_text(encoding="utf-8"), "committed\n")
            self.assertFalse((destination / "untracked-private-note.txt").exists())
            self.assertEqual((destination / "SOURCE_COMMIT").read_text(encoding="ascii"), revision + "\n")
            self.assertTrue((destination / "PACKAGE_SHA256SUMS").is_file())


if __name__ == "__main__":
    unittest.main()
