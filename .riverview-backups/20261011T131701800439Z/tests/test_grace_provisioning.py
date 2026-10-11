# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_provisioning.py
# Component: GRACE-OPERATIONAL-INTEGRATION
# Revision: 1.0.0
# Purpose: Verify fail-closed and fixed-scope behavior of Grace identity bootstrap
# Execution Model: Standard-library unit tests with filesystem and database boundaries mocked
# Observability: Tests inspect safe failure codes, exact grant scope and secret-file metadata
# Dependencies: Python standard library
# Authority: Does not connect to Camrui PostgreSQL, create identities, or change services
# Changed: 2026-10-11 UTC | RV-M4.4-IDENTITY-BOOTSTRAP | Initial Grace provisioning safety tests
# Contracts: scripts/provision_grace_resident.py; docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: This file
# History: New file; Git
# =============================================================================
"""Safety tests for the fixed-scope Grace resident bootstrap."""

from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from scripts import provision_grace_resident as grace


class GraceProvisionerTests(unittest.TestCase):
    def test_non_root_fails_before_filesystem_or_registry_access(self):
        with mock.patch.object(grace.os, "geteuid", return_value=1000), \
             mock.patch.object(grace, "_ensure_directory",
                               side_effect=AssertionError("must not touch filesystem")):
            with self.assertRaisesRegex(grace.ProvisioningError, "root_local_operation_required"):
                grace.provision()

    def test_arbitrary_arguments_are_rejected_without_provisioning(self):
        output = mock.Mock()
        with mock.patch.object(grace.sys, "argv", ["provision_grace_resident.py", "--path"]), \
             mock.patch.object(grace, "provision",
                               side_effect=AssertionError("must not provision")), \
             mock.patch("builtins.print", output):
            self.assertEqual(grace.main(), 2)
        self.assertEqual(json.loads(output.call_args.args[0])["failure_code"],
                         "arguments_not_allowed")

    def test_secret_writer_accepts_only_fixed_path_and_exact_token_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            grace_dir = Path(directory)
            secret = grace_dir / "resident.credential"
            with mock.patch.object(grace, "GRACE_DIR", grace_dir), \
                 mock.patch.object(grace, "RESIDENT_TOKEN_FILE", secret), \
                 mock.patch.object(grace.os, "chown"):
                grace._write_secret(secret, "t" * 64)
                self.assertEqual(secret.read_bytes(), ("t" * 64 + "\n").encode())
                self.assertEqual(secret.stat().st_mode & 0o777, 0o600)
                grace._write_secret(secret, "t" * 64)
                with self.assertRaisesRegex(grace.ProvisioningError,
                                            "credential_file_conflict"):
                    grace._write_secret(secret, "x" * 64)
                with self.assertRaisesRegex(grace.ProvisioningError,
                                            "credential_destination_invalid"):
                    grace._write_secret(grace_dir / "other", "y" * 64)

    def test_grant_uses_only_exact_grace_office_scope_and_fixed_identity(self):
        registry = mock.Mock()
        registry.authorize.side_effect = grace.AuthorityDenied("missing")
        with mock.patch.object(grace, "_one", return_value=None):
            grace._ensure_state_grant(registry, "steward-secret", "resident-secret")
        registry.grant.assert_called_once_with(
            "steward-secret", "resident:grace", "office.state.write",
            "office:office:grace", grant_id="rv-grace:office-state-write:v1",
            policy_ref="rv.policy:grace-office-runtime-state.v1")

    def test_revoked_or_mismatched_fixed_grant_fails_closed(self):
        registry = mock.Mock()
        registry.authorize.side_effect = grace.AuthorityDenied("missing")
        with mock.patch.object(grace, "_one", return_value={
            "principal_id": "resident:other", "action": "office.state.write",
            "scope_ref": "office:office:grace", "revoked_at": None,
        }):
            with self.assertRaisesRegex(grace.ProvisioningError,
                                        "office_state_grant_conflict"):
                grace._ensure_state_grant(registry, "steward-secret", "resident-secret")
        registry.grant.assert_not_called()


if __name__ == "__main__":
    unittest.main()
