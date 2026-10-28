"""Exercise release activation/rollback in an isolated fixture, with fake services.

Controlled test revision: 1.0.0 (2026-10-28).
The script copy points only into TemporaryDirectory; no real service is called.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/grace_current_controls_20261028.sh"
COMM_ID = "b6b5ce715508590cc8e56051c00bf7ed17fdbf79"
DASH_ID = "8325d3ffe8e53f3deaab4c9e14e471467454a08b"
FILES = {
    "COMM_SERVER_BASE": ("comms5", "riverview_core/comms5/server.py"),
    "COMM_BACKEND_BASE": ("comms5", "riverview_core/comms5/dashboard_backend.py"),
    "COMM_CATALOG_BASE": ("comms5", "riverview_core/comms5/tool_catalog.json"),
    "DASH_SERVER_BASE": ("dashboard", "riverview_core/status_dashboard/server.py"),
    "OPS_BASE": ("dashboard", "riverview_core/resident_execution/comms5_operations.py"),
    "PIPE_BASE": ("dashboard", "riverview_core/resident_execution/pipeline.py"),
}
NEXT = {
    "COMM_BACKEND_NEXT": "riverview_core/comms5/dashboard_backend.py",
    "COMM_HASH_NEXT": "riverview_core/comms5/tool_catalog.json",
    "OPS_NEXT": "riverview_core/resident_execution/comms5_operations.py",
    "PIPE_NEXT": "riverview_core/resident_execution/pipeline.py",
}


@unittest.skipUnless(hasattr(os, "geteuid") and os.geteuid() == 0, "fixture activation requires root; never uses /opt")
class InstallerLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grace-controls-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / "candidate/src"
        script = SCRIPT.read_text()
        self.bases = {}
        hashes = {}
        for component, revision in (("comms5", COMM_ID), ("dashboard", DASH_ID)):
            base = self.root / component / "releases" / revision
            base.mkdir(parents=True)
            self.bases[component] = base
            (self.root / component / "current").symlink_to(base)
        for constant, (component, relative) in FILES.items():
            path = self.bases[component] / "src" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            data = b'{}\n' if relative.endswith(".json") else b'pass\n'
            path.write_bytes(data)
            hashes[constant] = hashlib.sha256(data).hexdigest()
        for constant, relative in NEXT.items():
            path = self.stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            data = b'{"candidate":true}\n' if relative.endswith(".json") else b'pass # candidate\n'
            path.write_bytes(data)
            hashes[constant] = hashlib.sha256(data).hexdigest()
        for constant, digest in hashes.items():
            script = re.sub(r"(?m)^readonly " + constant + r"=.*$", "readonly " + constant + "=" + digest, script)
        script = re.sub(r"(?m)^COMM_ROOT=.*$", "COMM_ROOT=" + str(self.root / "comms5"), script)
        script = re.sub(r"(?m)^DASH_ROOT=.*$", "DASH_ROOT=" + str(self.root / "dashboard"), script)
        script = re.sub(r"(?m)^readonly STAGE=.*$", "readonly STAGE=" + str(self.stage), script)
        self.script = self.root / "entry.sh"
        self.script.write_text(script)
        commands = self.root / "bin"
        commands.mkdir()
        systemctl = commands / "systemctl"
        systemctl.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$FIXTURE_LOG"\n'
            'if [ "$1" = restart ] && [ "$2" = riverview-status-dashboard.service ] '
            '&& [ "${FAIL_DASH_ONCE:-0}" = 1 ] && [ ! -e "$FIXTURE_FAILED" ]; then\n'
            'touch "$FIXTURE_FAILED"\nexit 1\nfi\nexit 0\n')
        curl = commands / "curl"
        curl.write_text('#!/bin/sh\ncase "$*" in *api/v1/status*) printf 401;; esac\nexit 0\n')
        systemctl.chmod(0o755)
        curl.chmod(0o755)
        self.env = dict(os.environ, PATH=str(commands) + ":" + os.environ["PATH"],
            FIXTURE_LOG=str(self.root / "calls.log"), FIXTURE_FAILED=str(self.root / "failed"))
        self.env.pop("RIVERVIEW_CONTROLS_TEST_ROOT", None)

    def run_mode(self, mode, **extra):
        return subprocess.run(["bash", str(self.script), mode], env=dict(self.env, **extra),
            text=True, capture_output=True, timeout=20)

    def assert_base_pointers(self):
        for component, base in self.bases.items():
            self.assertEqual((self.root / component / "current").resolve(), base)

    def test_apply_then_explicit_rollback_preserves_predecessors(self):
        applied = self.run_mode("--apply")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        for component, base in self.bases.items():
            current = (self.root / component / "current").resolve()
            self.assertNotEqual(current, base)
            self.assertTrue(current.name.endswith("-grace-controls-20261028-r1"))
        self.assertEqual((self.bases["comms5"] / "src/riverview_core/comms5/dashboard_backend.py").read_bytes(), b"pass\n")
        rolled_back = self.run_mode("--rollback")
        self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
        self.assert_base_pointers()

    def test_restart_failure_restores_both_pointers(self):
        result = self.run_mode("--apply", FAIL_DASH_ONCE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assert_base_pointers()
        calls = (self.root / "calls.log").read_text()
        self.assertGreaterEqual(calls.count("restart riverview-comms5-camrui.service"), 2)
        self.assertGreaterEqual(calls.count("restart riverview-status-dashboard.service"), 2)

    def test_candidate_drift_stops_before_release_creation(self):
        (self.stage / "riverview_core/comms5/dashboard_backend.py").write_text("changed\n")
        result = self.run_mode("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assert_base_pointers()
        self.assertFalse((self.root / "calls.log").exists())
        self.assertEqual(len(list((self.root / "comms5/releases").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
