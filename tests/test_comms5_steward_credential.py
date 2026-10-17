# =============================================================================
# RIVERVIEW CONTROLLED TEST
# File: tests/test_comms5_steward_credential.py
# Component: COMMS5-OAUTH-IONOGE
# Revision: 1.0.0
# Purpose: Verify safe shared Comms5 credential validation, rotation and rollback
# Execution Model: Isolated unit test
# Observability: unittest assertions; test values are synthetic only
# Dependencies: Python standard library; scripts/rotate_comms5_steward_credential.py
# Authority: Temporary files only; never contacts services or production
# Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-001 | Initial isolated coverage
# Contracts: docs/components/COMMS5_OAUTH_TROUBLESHOOTING.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Isolated tests for Comms5 Steward credential provisioning and rollback."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "comms5_credential", ROOT / "scripts" / "rotate_comms5_steward_credential.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class CredentialRotationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.caddy = self.root / "caddy.env"
        self.oauth = self.root / "oauth.env"
        self.backups = self.root / "backups"
        self.old = "A" * 64
        self.new = "B" * 64
        self._write(self.caddy, f"OTHER=value\n{MODULE.CLIENT_KEY}={self.old}\n")
        self._write(self.oauth, f"{MODULE.CLIENT_KEY}={self.old}\nOAUTH_PROXY=value\n")

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, path, text):
        path.write_text(text, encoding="utf-8")
        path.chmod(0o600)
        if os.geteuid() == 0:
            path.chown(0, 0)

    def _fake_run(self, command, timeout=20):
        if "curl" in command and "-w" in command:
            return CompletedProcess(command, 0, "401", "")
        return CompletedProcess(command, 0, "", "")

    def test_valid_configuration_reports_no_secret(self):
        result = MODULE.inspect_configuration(
            self.caddy, self.oauth, expected_uid=os.geteuid()
        )
        self.assertTrue(result["credential_shared_by_caddy_and_oauth"])
        self.assertNotIn(self.old, repr(result))

    def test_mismatched_values_fail_closed(self):
        self._write(self.oauth, f"{MODULE.CLIENT_KEY}={'C' * 64}\n")
        with self.assertRaisesRegex(MODULE.CredentialError, "do_not_match"):
            MODULE.inspect_configuration(self.caddy, self.oauth, expected_uid=os.geteuid())

    def test_duplicate_key_fails_closed(self):
        self._write(self.oauth, f"{MODULE.CLIENT_KEY}={self.old}\n{MODULE.CLIENT_KEY}={self.old}\n")
        with self.assertRaisesRegex(MODULE.CredentialError, "duplicated"):
            MODULE.inspect_configuration(self.caddy, self.oauth, expected_uid=os.geteuid())

    def test_rotation_updates_both_files_and_keeps_backup_private(self):
        result = MODULE.install_from_stdin(
            caddy_env=self.caddy,
            oauth_env=self.oauth,
            backup_root=self.backups,
            secret_input=(self.new + "\n").encode(),
            run=self._fake_run,
            require_root=False,
        )
        self.assertEqual(self.new, MODULE._value_from_line(MODULE._read_assignments(self.caddy)[1][0][1]))
        self.assertEqual(self.new, MODULE._value_from_line(MODULE._read_assignments(self.oauth)[1][0][1]))
        self.assertFalse(result["secret_value_emitted"])
        self.assertNotIn(self.new, repr(result))
        backup = Path(result["protected_predecessor"])
        self.assertEqual(0o700, backup.stat().st_mode & 0o777)
        self.assertEqual(0o600, (backup / "caddy.env").stat().st_mode & 0o777)
        self.assertIn(self.old, (backup / "caddy.env").read_text())

    def test_invalid_secret_does_not_change_files_or_create_backup(self):
        before = (self.caddy.read_bytes(), self.oauth.read_bytes())
        with self.assertRaisesRegex(MODULE.CredentialError, "format_invalid"):
            MODULE.install_from_stdin(
                caddy_env=self.caddy,
                oauth_env=self.oauth,
                backup_root=self.backups,
                secret_input=b"short-value\n",
                run=self._fake_run,
                require_root=False,
            )
        self.assertEqual(before, (self.caddy.read_bytes(), self.oauth.read_bytes()))
        self.assertFalse(self.backups.exists())

    def test_failed_health_restores_both_predecessors(self):
        calls = {"curl": 0, "restart": 0}

        def fail_first_health(command, timeout=20):
            if "curl" in command:
                calls["curl"] += 1
                if calls["curl"] == 1:
                    return CompletedProcess(command, 1, "", "unavailable")
                if "-w" in command:
                    return CompletedProcess(command, 0, "401", "")
            return CompletedProcess(command, 0, "", "")

        before = (self.caddy.read_bytes(), self.oauth.read_bytes())
        with self.assertRaisesRegex(MODULE.CredentialError, "predecessor_restored"):
            MODULE.install_from_stdin(
                caddy_env=self.caddy,
                oauth_env=self.oauth,
                backup_root=self.backups,
                secret_input=(self.new + "\n").encode(),
                run=fail_first_health,
                require_root=False,
            )
        self.assertEqual(before, (self.caddy.read_bytes(), self.oauth.read_bytes()))

    def test_restart_failure_restores_prior_files(self):
        calls = {"restart": 0}

        def fail_first_restart(command, timeout=20):
            if command[:2] == ["systemctl", "restart"]:
                calls["restart"] += 1
                if calls["restart"] == 1:
                    return CompletedProcess(command, 1, "", "service restart failed")
            if "curl" in command and "-w" in command:
                return CompletedProcess(command, 0, "401", "")
            return CompletedProcess(command, 0, "", "")

        before = (self.caddy.read_bytes(), self.oauth.read_bytes())
        with self.assertRaisesRegex(MODULE.CredentialError, "predecessor_restored"):
            MODULE.install_from_stdin(
                caddy_env=self.caddy,
                oauth_env=self.oauth,
                backup_root=self.backups,
                secret_input=(self.new + "\n").encode(),
                run=fail_first_restart,
                require_root=False,
            )
        self.assertEqual(before, (self.caddy.read_bytes(), self.oauth.read_bytes()))

    def test_systemd_environment_wiring_requires_exact_file(self):
        expected = CompletedProcess([], 0, f"{self.caddy} (ignore_errors=no)\n", "")
        self.assertTrue(MODULE._unit_reads_environment("caddy.service", self.caddy, lambda *a, **k: expected))
        other = CompletedProcess([], 0, "/etc/other.env (ignore_errors=no)\n", "")
        self.assertFalse(MODULE._unit_reads_environment("caddy.service", self.caddy, lambda *a, **k: other))


if __name__ == "__main__":
    unittest.main()
