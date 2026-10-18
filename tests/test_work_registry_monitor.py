# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_work_registry_monitor.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.1
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-STATUS-ACCURACY-001 | Cover terminal/latest results separately from current assignment, heartbeat, and activity.
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
        self.assertIn("$latestResult.status", source)
        self.assertIn("latest_result=", source)
        self.assertIn("@('completed','failed','cancelled')", source)

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
                "hostname":"fixture-host", "os":"Windows", "repository":None, "branch":None,
                "pull_request":None, "model_identity":None, "endpoint_ref":None,
                "lifecycle":"running", "identity_state":"unverified", "activity_state":"idle",
                "current_work_order_id":"work:done", "started_at":None,
                "last_heartbeat_at":None, "last_activity_at":None, "ended_at":None}
            blocked_session = {"session_id":"session:blocked", "worker_id":"worker:additional",
                "hostname":"fixture-host", "os":"Windows", "repository":None, "branch":None,
                "pull_request":None, "model_identity":None, "endpoint_ref":None,
                "identity_state":"unverified", "activity_state":"idle", "lifecycle":"running",
                "current_work_order_id":"work:blocked", "started_at":None,
                "last_heartbeat_at":"2020-01-01T00:00:00Z", "last_activity_at":None, "ended_at":None}
            order = {"work_order_id":"work:done", "session_id":"session:additional",
                "worker_id":"worker:additional", "title":"Completed fixture work",
                "status":"completed", "ownership_state":"assigned", "milestone":1,
                "milestones_total":1, "updated_at":"2026-10-18T02:00:00Z",
                "blocker":None, "pull_request":None,
                "evidence":["legacy v4 source: old.json"], "detail":"fixture"}
            blocked_order = {"work_order_id":"work:blocked", "session_id":"session:blocked",
                "worker_id":"worker:additional", "title":"Blocked fixture work",
                "status":"blocked", "ownership_state":"assigned", "milestone":1,
                "milestones_total":2, "updated_at":"2026-10-18T04:00:00Z",
                "blocker":"Fixture dependency", "pull_request":None,
                "evidence":[], "detail":"fixture"}
            registry.write_text(json.dumps({"schema_version":"rv.work-registry.v1",
                "workers":{"worker:additional":{"worker_id":"worker:additional",
                    "worker_type":"codex", "hostname":"fixture-host", "os":"Windows",
                    "capabilities":[], "model_identity":None, "endpoint_ref":None,
                    "registered_at":"2026-10-18T00:00:00Z"}},
                "sessions":{"session:additional":session,"session:blocked":blocked_session},
                "work_orders":{"work:done":order,"work:blocked":blocked_order}}), encoding="utf-8")
            (legacy_dir / "old.json").write_text(json.dumps({"task":"Synced old row",
                "status":"WAITING", "updated_at":"2026-10-18T01:00:00Z"}), encoding="utf-8")
            (legacy_dir / "new.json").write_text(json.dumps({"task":"Newer legacy source",
                "status":"WAITING", "updated_at":"2026-10-18T03:00:00Z"}), encoding="utf-8")
            result = subprocess.run([shell, "-NoProfile", "-File", str(MONITOR), "-Once",
                "-RegistryPath", str(registry), "-LegacyStatusDirectory", str(legacy_dir),
                "-CamruiMonitorTarget", ""],
                check=True, capture_output=True, text=True, timeout=20)
            self.assertIn("session:additional", result.stdout)
            self.assertIn("assignment=unassigned", result.stdout)
            self.assertIn("latest_result=completed: Completed fixture", result.stdout)
            self.assertIn("assignment=Blocked fixture work", result.stdout)
            self.assertIn("latest_result=blocked: Blocked fixture work", result.stdout)
            self.assertIn("availability=unknown", result.stdout)
            self.assertIn("availability=stale", result.stdout)
            self.assertIn("activity=idle", result.stdout)
            self.assertIn("Newer legacy source", result.stdout)
            self.assertNotIn("Synced old row", result.stdout)
            self.assertIn("UNVERIFIED", result.stdout)


if __name__ == "__main__":
    unittest.main()
