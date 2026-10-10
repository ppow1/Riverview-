# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_cme_monitor_service.py
# Component: CME
# Revision: 1.0.1
# Purpose: Verify installed monitor service isolation and protected credential startup
# Execution Model: Static systemd contract checks and mocked launcher boundary tests
# Observability: Sanitized setup errors; secret bytes never enter assertions or output
# Dependencies: Python 3.10+; Psycopg 3; unittest
# Authority: No service, credential, database, or privileged host changes
# Changed: 2026-10-10 UTC | RV-M2.4-002 | Assert machine-readable credential setup failure codes
# Contracts: docs/components/CME_MONITOR.md
# Tests: This file
# History: New file; Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Local contract tests for CME systemd deployment and credential validation."""

import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_cme_monitor


class CMEMonitorServiceContractTests(unittest.TestCase):
    def test_unit_is_separate_supervised_and_uses_private_systemd_credential(self):
        unit = (ROOT / "deploy/systemd/riverview-cme-monitor.service").read_text()
        for required in (
            "User=riverview", "Group=riverview", "RuntimeDirectory=riverview-cme-monitor",
            "RuntimeDirectoryMode=0700", "LoadCredential=pgpass:/etc/riverview/pgpass",
            "scripts/run_cme_monitor.py", "Restart=on-failure", "ProtectSystem=strict",
            "RIVERVIEW_CME_STALL_AFTER_SECONDS=300", "application_name=riverview-cme-monitor",
        ):
            self.assertIn(required, unit)
        self.assertNotIn("riverview-event-processor.service", unit)
        self.assertNotIn("riverview-status-dashboard.service", unit)

    def test_launcher_validates_exact_unit_and_copies_credential_for_service_uid(self):
        credential_dir = "/run/credentials/riverview-cme-monitor.service"
        with mock.patch.dict(os.environ, {
                "CREDENTIALS_DIRECTORY": credential_dir,
                "RIVERVIEW_DATABASE_DSN": "host=127.0.0.1 dbname=riverview user=riverview_core",
        }, clear=True):
            with mock.patch.object(run_cme_monitor, "systemd_credential_path") as validate:
                with mock.patch.object(run_cme_monitor, "copy_systemd_credential") as copy:
                    with mock.patch.object(run_cme_monitor.pwd, "getpwnam",
                                            return_value=SimpleNamespace(pw_uid=1234)):
                        with mock.patch.object(run_cme_monitor.os, "geteuid", return_value=1234):
                            run_cme_monitor.prepare_runtime_credential()
            source = Path(credential_dir) / "pgpass"
            validate.assert_called_once_with(source, service_unit="riverview-cme-monitor.service")
            copy.assert_called_once_with(source, run_cme_monitor.PASSFILE, 1234)
            self.assertEqual(os.environ["PGPASSFILE"], str(run_cme_monitor.PASSFILE))

    def test_launcher_rejects_ambient_overrides_password_dsn_and_root_identity(self):
        base = {"CREDENTIALS_DIRECTORY": "/run/credentials/riverview-cme-monitor.service",
                "RIVERVIEW_DATABASE_DSN": "host=127.0.0.1 dbname=riverview user=riverview_core"}
        with mock.patch.dict(os.environ, {**base, "PGPASSWORD": "never-reported"}, clear=True):
            with self.assertRaises(run_cme_monitor.BaselineError) as caught:
                run_cme_monitor.prepare_runtime_credential()
            self.assertEqual(caught.exception.code, "AMBIENT_DATABASE_OVERRIDE")
        with mock.patch.dict(os.environ, {**base, "RIVERVIEW_DATABASE_DSN":
                                         "host=127.0.0.1 dbname=riverview password=redacted"}, clear=True):
            with self.assertRaises(run_cme_monitor.BaselineError) as caught:
                run_cme_monitor.prepare_runtime_credential()
            self.assertEqual(caught.exception.code, "DSN_PASSWORD_FORBIDDEN")
        with mock.patch.dict(os.environ, base, clear=True):
            with mock.patch.object(run_cme_monitor, "systemd_credential_path"):
                with mock.patch.object(run_cme_monitor.pwd, "getpwnam",
                                        return_value=SimpleNamespace(pw_uid=0)):
                    with mock.patch.object(run_cme_monitor.os, "geteuid", return_value=0):
                        with self.assertRaises(run_cme_monitor.BaselineError) as caught:
                            run_cme_monitor.prepare_runtime_credential()
                        self.assertEqual(caught.exception.code, "IDENTITY_MISMATCH")


if __name__ == "__main__":
    unittest.main()
