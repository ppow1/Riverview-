# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_work_registry_monitor.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Purpose: Guard dynamic PowerShell control-board discovery and v4 compatibility
# Execution Model: Static contract checks and optional PowerShell parser validation
# Authority: The monitor is read-only and grants no capability or commissioning approval
# Tests: This file
# =============================================================================
"""Validate that the Windows board discovers registry rows without fixed slots."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MONITOR = ROOT / "scripts/Start-RiverviewControlBoard-Registry.ps1"


class WorkRegistryMonitorTests(unittest.TestCase):
    def test_monitor_enumerates_registry_and_keeps_legacy_fallback_separate(self):
        source = MONITOR.read_text(encoding="utf-8")
        self.assertIn("$snapshot.workers", source)
        self.assertIn("$snapshot.sessions", source)
        self.assertIn("$snapshot.work_orders", source)
        self.assertIn("legacy v4 source:", source)
        self.assertIn("PRODUCTION CAPABILITY / COMMISSIONING", source)
        self.assertIn("identity_state -eq 'unverified'", source)
        self.assertNotIn("@{ Id='W1'", source)
        self.assertNotIn("@{ Id='C1'", source)
        self.assertIn("$session.activity_state", source)
        self.assertIn("$current.status", source)

    @unittest.skipUnless(shutil.which("powershell") or shutil.which("pwsh"),
                         "PowerShell is not installed")
    def test_monitor_parses_on_available_powershell(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        command = ("$tokens=$null; $errors=$null; "
                   "[System.Management.Automation.Language.Parser]::ParseFile("
                   f"'{MONITOR.as_posix()}',[ref]$tokens,[ref]$errors) | Out-Null; "
                   "if ($errors.Count) { $errors | Out-String | Write-Error; exit 1 }")
        subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", command],
                       check=True, capture_output=True, text=True, timeout=20)

    @unittest.skipUnless(os.name == "nt" and (shutil.which("pwsh") or shutil.which("powershell")),
                         "Windows PowerShell runtime is required")
    def test_monitor_discovers_unbounded_registry_rows_and_unmatched_v4_json(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = root / "work-registry.json"
            legacy_dir = root / "control"
            legacy_dir.mkdir()
            session = {"session_id":"session:additional", "worker_id":"worker:additional",
                "identity_state":"unverified", "status":"unknown", "activity_state":"unknown",
                "current_work_order_id":"work:done", "last_heartbeat_at":None}
            order = {"work_order_id":"work:done", "session_id":"session:additional",
                "worker_id":"worker:additional", "title":"Completed fixture work",
                "status":"completed", "ownership_state":"assigned", "milestone":1,
                "milestones_total":1, "updated_at":"2026-10-18T02:00:00Z",
                "blocker":None, "pull_request":None,
                "evidence":["legacy v4 source: old.json"], "detail":"fixture"}
            registry.write_text(json.dumps({"schema_version":"rv.work-registry.v1",
                "workers":{"worker:additional":{"worker_id":"worker:additional",
                    "hostname":"fixture-host","status":"unknown"}},
                "sessions":{"session:additional":session},
                "work_orders":{"work:done":order}}), encoding="utf-8")
            (legacy_dir / "old.json").write_text(json.dumps({"task":"Synced old row",
                "status":"WAITING", "updated_at":"2026-10-18T01:00:00Z"}), encoding="utf-8")
            (legacy_dir / "new.json").write_text(json.dumps({"task":"Newer legacy source",
                "status":"WAITING", "updated_at":"2026-10-18T03:00:00Z"}), encoding="utf-8")
            result = subprocess.run([shell, "-NoProfile", "-File", str(MONITOR), "-Once",
                "-RegistryPath", str(registry), "-LegacyStatusDirectory", str(legacy_dir)],
                check=True, capture_output=True, text=True, timeout=20)
            self.assertIn("session:additional", result.stdout)
            self.assertIn("Completed fixture work", result.stdout)
            self.assertIn("completed", result.stdout)
            self.assertIn("Newer legacy source", result.stdout)
            self.assertNotIn("Synced old row", result.stdout)
            self.assertIn("UNVERIFIED", result.stdout)


if __name__ == "__main__":
    unittest.main()
