# Riverview~ controlled test
# File: tests/test_grace_owner_release_update.py
# Revision: 1.0.1 | 2026-10-28
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

STAGE = Path(__file__).resolve().parents[1]
HELPER = STAGE / "owner-release-update.sh"
GUARD_PATH = STAGE / "owner_release_guard.py"
spec = importlib.util.spec_from_file_location("owner_release_guard", GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(guard)


class GraceOwnerReleaseUpdateTests(unittest.TestCase):
    def fake_cgroup(self, root: Path, parent: str, child: str = "") -> Path:
        group = root / "system.slice/riverview-grace-execution-owner-session.service"
        nested = group / "worker"
        nested.mkdir(parents=True)
        (group / "cgroup.procs").write_text(parent)
        (nested / "cgroup.procs").write_text(child)
        return group

    def test_busy_recursive_group_rejected_without_release_staging(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_cgroup(root / "cgroup", "410\n", "411\n")
            candidate = root / "candidate-release"
            before = set(root.iterdir())
            values = iter(("active", "410", "/system.slice/riverview-grace-execution-owner-session.service"))
            def get_property(_name):
                return next(values)
            with self.assertRaisesRegex(guard.GuardFailure, "owner_session_cgroup_busy"):
                guard.check_owner_idle(get_property=get_property, cgroup_root=root / "cgroup")
            self.assertFalse(candidate.exists())
            self.assertEqual(before, set(root.iterdir()))

    def test_stopped_rollback_allowed_only_for_empty_recursive_group(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "cgroup"
            self.fake_cgroup(root, "", "")
            values = iter(("failed", "0", "/system.slice/riverview-grace-execution-owner-session.service",
                           "failed", "0", "/system.slice/riverview-grace-execution-owner-session.service"))
            self.assertEqual("stopped", guard.check_owner_idle(
                allow_stopped=True, get_property=lambda _name: next(values), cgroup_root=root))

    def test_stopped_unit_without_cgroup_can_roll_back(self):
        values = {"ActiveState": "inactive", "MainPID": "0", "ControlGroup": ""}
        self.assertEqual("stopped", guard.check_owner_idle(
            allow_stopped=True, get_property=values.__getitem__))

    def test_rollback_does_not_require_candidate_health(self):
        script = HELPER.read_text()
        rollback = script.split("  --rollback)\n", 1)[1].split("\nesac", 1)[0]
        self.assertIn('rollback_state="$(idle_state allow-stopped)"', rollback)
        self.assertNotIn("unit_ready", rollback.split("atomic_pointer \"$BASE\"", 1)[0])
        self.assertIn('if [[ "$rollback_state" == STOPPED ]]', rollback)

    def test_predecessor_hash_mismatch_remains_fail_closed(self):
        script = HELPER.read_text()
        actual = "3a31111efe3bea0910be6571cef97076dc1a9562fbc57cdff526ca2507394c2d"
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "helper.sh"
            copy.write_text(script.replace(actual, "0" * 64, 1))
            copy.chmod(0o700)
            result = subprocess.run([str(copy), "--dry-run"], capture_output=True, text=True, timeout=15)
            self.assertEqual(2, result.returncode)
            self.assertIn("predecessor_hash_mismatch", result.stdout)

    def test_wrong_pointer_rollback_guard_remains_fail_closed(self):
        script = HELPER.read_text()
        script = script.replace(
            'root_required() { [[ "$EUID" -eq 0 ]] || blocked root_required; }',
            'root_required() { :; }', 1)
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "helper.sh"
            copy.write_text(script)
            copy.chmod(0o700)
            result = subprocess.run([str(copy), "--rollback"], capture_output=True, text=True, timeout=15)
            self.assertEqual(2, result.returncode)
            self.assertIn("current_pointer_mismatch", result.stdout)


if __name__ == "__main__":
    unittest.main()
