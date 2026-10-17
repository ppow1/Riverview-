# =============================================================================
# RIVERVIEW CONTROLLED TEST
# File: tests/test_comms5_steward_credential.py
# Component: COMMS5-OAUTH-IONOGE
# Revision: 1.0.1
# Purpose: Verify safe shared Comms5 credential validation, rotation and rollback
# Execution Model: Isolated unit test
# Observability: unittest assertions; test values are synthetic only
# Dependencies: Python standard library; scripts/rotate_comms5_steward_credential.py
# Authority: Temporary files only; never contacts services or production
# Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-ROTATION-HEALTH-REPAIR | Cover delayed readiness, deadline diagnostics and rollback
# Contracts: docs/components/COMMS5_OAUTH_TROUBLESHOOTING.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Isolated tests for Comms5 Steward credential provisioning and rollback."""

import hashlib
import importlib.util
import os
import re
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
            status = "401" if command[-1].endswith("/mcp") else "200"
            return CompletedProcess(command, 0, status, "")
        return CompletedProcess(command, 0, "", "")

    class FakeClock:
        def __init__(self):
            self.now = 0.0

        def monotonic(self):
            return self.now

        def sleep(self, seconds):
            self.now += seconds

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

    def test_delayed_readiness_retries_then_succeeds_with_exact_statuses(self):
        clock = self.FakeClock()
        attempts = {"oauth_health": 0}
        observed_statuses = []

        def delayed_run(command, timeout=20):
            if "curl" in command and "-w" in command:
                url = command[-1]
                expected = "401" if url.endswith("/mcp") else "200"
                if url.endswith("/healthz"):
                    attempts["oauth_health"] += 1
                    if attempts["oauth_health"] == 1:
                        observed_statuses.append((url, "503"))
                        return CompletedProcess(command, 0, "503", "")
                observed_statuses.append((url, expected))
                return CompletedProcess(command, 0, expected, "")
            return CompletedProcess(command, 0, "", "")

        self.assertTrue(
            MODULE._restart_and_health(
                delayed_run,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )
        )
        self.assertEqual(0.5, clock.now)
        self.assertEqual(["503", "200", "200", "401"], [status for _, status in observed_statuses])

    def test_operator_launcher_uses_checkout_scripts_parent_and_verified_target(self):
        launcher = (ROOT / "scripts" / "Invoke-RiverviewComms5StewardCredentialRotation.ps1").read_text(encoding="utf-8")
        self.assertIn("$RepoRoot = Split-Path -Parent $PSScriptRoot", launcher)
        self.assertIn("$SshTarget = 'root@64.227.21.54'", launcher)
        self.assertIn("StrictHostKeyChecking=yes", launcher)
        embedded_hash = re.search(r"\$ExpectedUtilitySha256 = '([0-9a-f]{64})'", launcher)
        actual_hash = hashlib.sha256((ROOT / "scripts" / "rotate_comms5_steward_credential.py").read_bytes()).hexdigest()
        self.assertIsNotNone(embedded_hash)
        self.assertEqual(actual_hash, embedded_hash.group(1))

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

    def test_persistent_readiness_failure_reports_check_and_successfully_rolls_back(self):
        clock = self.FakeClock()
        restart_cycles = 0

        def fail_new_revision_then_recover_predecessor(command, timeout=20):
            nonlocal restart_cycles
            if command[:2] == ["systemctl", "restart"] and command[2] == MODULE.SERVICES[0]:
                restart_cycles += 1
            if "curl" in command and "-w" in command:
                url = command[-1]
                if restart_cycles == 1 and url.endswith("/healthz"):
                    return CompletedProcess(command, 0, "503", "")
                status = "401" if url.endswith("/mcp") else "200"
                return CompletedProcess(command, 0, status, "")
            return CompletedProcess(command, 0, "", "")

        before = (self.caddy.read_bytes(), self.oauth.read_bytes())
        with self.assertRaisesRegex(
            MODULE.CredentialError,
            "readiness_deadline_exceeded:oauth_loopback_health_200; predecessor_restored",
        ):
            MODULE.install_from_stdin(
                caddy_env=self.caddy,
                oauth_env=self.oauth,
                backup_root=self.backups,
                secret_input=(self.new + "\n").encode(),
                run=fail_new_revision_then_recover_predecessor,
                require_root=False,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )
        self.assertEqual(before, (self.caddy.read_bytes(), self.oauth.read_bytes()))
        self.assertEqual(MODULE.READINESS_TIMEOUT_SECONDS, clock.now)
        self.assertEqual(2, restart_cycles)

    def test_rotation_succeeds_after_delayed_service_readiness(self):
        clock = self.FakeClock()
        first_probe = True

        def delayed_ready(command, timeout=20):
            nonlocal first_probe
            if "curl" in command and "-w" in command:
                url = command[-1]
                if url.endswith("/healthz") and first_probe:
                    first_probe = False
                    return CompletedProcess(command, 0, "503", "")
                status = "401" if url.endswith("/mcp") else "200"
                return CompletedProcess(command, 0, status, "")
            return CompletedProcess(command, 0, "", "")

        result = MODULE.install_from_stdin(
            caddy_env=self.caddy,
            oauth_env=self.oauth,
            backup_root=self.backups,
            secret_input=(self.new + "\n").encode(),
            run=delayed_ready,
            require_root=False,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )
        self.assertEqual("credential_installed", result["status"])
        self.assertEqual(0.5, clock.now)
        self.assertEqual(self.new, MODULE._value_from_line(MODULE._read_assignments(self.caddy)[1][0][1]))
        self.assertEqual(self.new, MODULE._value_from_line(MODULE._read_assignments(self.oauth)[1][0][1]))

    def test_restart_failure_restores_prior_files_with_sanitized_service_id(self):
        restart_attempts = 0

        def fail_first_restart(command, timeout=20):
            nonlocal restart_attempts
            if command[:2] == ["systemctl", "restart"]:
                restart_attempts += 1
                if restart_attempts == 1:
                    return CompletedProcess(command, 1, "", "service restart failed")
            return self._fake_run(command, timeout)

        before = (self.caddy.read_bytes(), self.oauth.read_bytes())
        with self.assertRaisesRegex(MODULE.CredentialError, "service_restart_failed:riverview-comms5-oauth; predecessor_restored"):
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
