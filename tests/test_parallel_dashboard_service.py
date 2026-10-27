# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_parallel_dashboard_service.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.1
# Purpose: Verify isolated Dashboard unit credentials, runtime passfile, and loopback endpoint settings
# Execution Model: Fast unit tests; no services or production credentials
# Dependencies: Python 3.10+
# Authority: Temporary files and mocks only
# Changed: 2026-10-27 UTC | RV-ISSUE-359-PARALLEL-DASHBOARD | Cover unit-specific systemd credential validation, distinct runtime paths, and Comms5 loopback routing.
# Contracts: docs/operations/ISSUE_359_PARALLEL_DASHBOARD_RUNBOOK.md
# =============================================================================
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import os
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_status_dashboard_parallel as parallel
import run_status_dashboard


class ParallelDashboardServiceTests(unittest.TestCase):
    def test_parallel_launcher_validates_its_own_credential_mount_and_passfile(self):
        credential_dir = "/run/credentials/riverview-status-dashboard-parallel.service"
        source = Path(credential_dir) / "pgpass"
        env = {"CREDENTIALS_DIRECTORY": credential_dir}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(run_status_dashboard, "systemd_credential_path") as validate, \
             mock.patch.object(run_status_dashboard, "copy_systemd_credential") as copy, \
             mock.patch.object(run_status_dashboard.pwd, "getpwnam",
                               return_value=SimpleNamespace(pw_uid=1410)), \
             mock.patch.object(run_status_dashboard.os, "geteuid", return_value=1410):
            parallel.prepare_runtime_credential(
                service_unit=parallel.SERVICE_UNIT, passfile=Path(parallel.PASSFILE))
            self.assertEqual(os.environ["PGPASSFILE"], parallel.PASSFILE)

        validate.assert_called_once_with(source, service_unit=parallel.SERVICE_UNIT)
        copy.assert_called_once_with(source, Path(parallel.PASSFILE), 1410)
        self.assertNotEqual(parallel.PASSFILE, str(run_status_dashboard.PASSFILE))

    def test_parallel_unit_isolated_from_active_dashboard_configuration(self):
        unit = (ROOT / "deploy/riverview-status-dashboard-parallel.service").read_text()
        self.assertIn("RuntimeDirectory=riverview-status-dashboard-parallel", unit)
        self.assertIn("RIVERVIEW_DASHBOARD_HOST=127.0.0.1", unit)
        self.assertIn("RIVERVIEW_DASHBOARD_PORT=8770", unit)
        self.assertIn("application_name=riverview-status-dashboard-parallel", unit)
        self.assertIn("run_status_dashboard_parallel.py", unit)
        self.assertIn("LoadCredential=authority-manager-pgpass:", unit)
        self.assertIn("LoadCredential=authority-steward-token:", unit)
        self.assertIn("LoadCredential=command-agent-token:", unit)
        self.assertIn("LoadCredential=command-agent-ca.pem:", unit)
        self.assertNotIn("RIVERVIEW_GRACE_ENABLE_MODEL_ROUTER", unit)
        self.assertNotIn("WorkingDirectory=/opt/riverview-status-dashboard/current", unit)

    def test_parallel_comms5_backend_accepts_candidate_loopback_url(self):
        from riverview_core.comms5.dashboard_backend import DashboardReadBackend
        with TemporaryDirectory(prefix="rv-parallel-dashboard-token-") as temp:
            token = Path(temp) / "dashboard-token"
            token.write_text("p" * 48, encoding="ascii")
            token.chmod(0o600)
            backend = DashboardReadBackend(base_url="http://127.0.0.1:8770",
                                           credential_file=token)
        self.assertIsNotNone(backend)

    def test_parallel_launcher_rejects_shared_dashboard_passfile(self):
        credential_dir = "/run/credentials/riverview-status-dashboard-parallel.service"
        with mock.patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": credential_dir}, clear=True), \
             mock.patch.object(run_status_dashboard, "systemd_credential_path") as validate, \
             mock.patch.object(run_status_dashboard, "copy_systemd_credential") as copy, \
             mock.patch.object(run_status_dashboard.pwd, "getpwnam",
                               return_value=SimpleNamespace(pw_uid=1410)), \
             mock.patch.object(run_status_dashboard.os, "geteuid", return_value=1410):
            with self.assertRaisesRegex(run_status_dashboard.BaselineError,
                                        "unexpected_runtime_credential_location"):
                parallel.prepare_runtime_credential(
                    service_unit=parallel.SERVICE_UNIT,
                    passfile=run_status_dashboard.PASSFILE)
        validate.assert_not_called()
        copy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
