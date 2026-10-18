# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_work_registry_startup.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Purpose: Verify Windows/Linux Codex wrapper semantics without starting Codex
# Execution Model: Mocked child process and temporary observational registry
# Authority: Tests do not start, stop, or alter any existing Codex session
# Tests: This file
# =============================================================================
"""Cross-interface startup contract tests without invoking Codex CLI."""
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from riverview_core.work_registry import WorkRegistry


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/start_riverview_codex.py"


class WorkRegistryStartupTests(unittest.TestCase):
    def test_existing_dispatcher_assignment_receipt_updates_registry(self):
        cli_path = ROOT / "scripts/register_work.py"
        spec = importlib.util.spec_from_file_location("work_registration_cli", cli_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            registry = WorkRegistry(path)
            registry.register_worker(worker_id="worker:dispatch", worker_type="engineering",
                hostname="build-host", os_name="Linux")
            registry.start_session("worker:dispatch", session_id="session:dispatch")
            registry.create_work_order(title="Dispatched item", work_order_id="work:dispatch",
                owner_label="Engineering worker", ownership_state="proposed", status="queued")
            with redirect_stdout(io.StringIO()):
                result = module.main(["--registry", str(path), "acknowledge-work-order",
                    "--work-order-id", "work:dispatch", "--worker-id", "worker:dispatch",
                    "--session-id", "session:dispatch"])
            self.assertEqual(result, 0)
            work = registry.snapshot()["work_orders"][0]
            self.assertEqual(work["ownership_state"], "acknowledged")
            self.assertEqual(work["session_id"], "session:dispatch")

    def test_explicit_assignment_startup_binds_work_and_preserves_opt_in_flags(self):
        spec = importlib.util.spec_from_file_location("registered_codex_startup", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            registry = WorkRegistry(path)
            registry.create_work_order(title="Initial proposed item", status="queued",
                work_order_id="work:issue120:test", owner_label="Windows W1",
                ownership_state="proposed")
            child = Mock()
            child.poll.return_value = 0
            child.returncode = 0
            argv = ["--registry", str(path), "--worker-id", "worker:test",
                "--session-id", "session:test", "--work-order-id", "work:issue120:test",
                "--model", "gpt-6-luna", "--reasoning-effort", "medium",
                "--full-permissions", "--", "--help"]
            with patch.object(module.subprocess, "Popen", return_value=child) as popen, \
                 patch.object(module, "_git_value", return_value=None), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(argv), 0)
            command = popen.call_args.args[0]
            self.assertIn("--model", command)
            self.assertIn("gpt-6-luna", command)
            self.assertIn('model_reasoning_effort="medium"', command)
            self.assertIn("--sandbox", command)
            self.assertIn("danger-full-access", command)
            self.assertIn("--ask-for-approval", command)
            self.assertIn("never", command)
            snapshot = registry.snapshot()
            self.assertEqual(snapshot["sessions"][0]["lifecycle"], "completed")
            self.assertEqual(snapshot["sessions"][0]["activity_state"], "unknown")
            self.assertEqual(snapshot["work_orders"][0]["ownership_state"], "acknowledged")
            self.assertEqual(snapshot["work_orders"][0]["status"], "unknown")

    def test_shell_and_powershell_interfaces_forward_existing_work_order_ids(self):
        shell = (ROOT / "scripts/start-riverview-codex-session.sh").read_text(encoding="utf-8")
        powershell = (ROOT / "scripts/Start-RiverviewCodexSession.ps1").read_text(encoding="utf-8")
        self.assertIn("RIVERVIEW_WORK_ORDER_ID", shell)
        self.assertIn("--work-order-id", shell)
        self.assertIn("$WorkOrderId", powershell)
        self.assertIn("--work-order-id", powershell)


if __name__ == "__main__":
    unittest.main()
