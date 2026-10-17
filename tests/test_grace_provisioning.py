# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_provisioning.py
# Component: GRACE-OPERATIONAL-INTEGRATION
# Revision: 1.0.6
# Purpose: Verify fail-closed and fixed-scope behavior of Grace identity bootstrap
# Execution Model: Standard-library unit tests with filesystem and database boundaries mocked
# Observability: Tests inspect safe failure codes, exact grant scope and secret-file metadata
# Dependencies: Python standard library
# Authority: Does not connect to Camrui PostgreSQL, create identities, or change services
# Changed: 2026-10-11 UTC | RV-M4.4-IDENTITY-BOOTSTRAP | Initial Grace provisioning safety tests
# Changed: 2026-10-11 UTC | RV-M4.4-BOOTSTRAP-TEST-CORRECTION | Mock root-owned metadata validation for unprivileged test execution
# Changed: 2026-10-11 UTC | RV-M4.4-BOOTSTRAP-TEST-CORRECTION-2 | Apply metadata mock on existing-secret validation path
# Changed: 2026-10-11 UTC | RV-M4.1-BOOTSTRAP-ORPHAN-CREDENTIAL-RECOVERY | Verify interrupted token delivery revokes orphan before replacement
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Assert new Grace provisioning uses Director of Operations office title
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
    def test_grace_office_title_is_director_of_operations(self):
        self.assertEqual(grace.OFFICE_ROLE, "Director of Operations")

    def test_existing_office_role_is_corrected_through_authority_cas(self):
        registry = mock.Mock()
        with mock.patch.object(grace, "_one", return_value={
                "office_role": "AI director of engineering"}):
            grace._ensure_office(registry, "steward-token")
        registry.update_office_role.assert_called_once_with(
            "steward-token", grace.OFFICE_ID, "Director of Operations",
            expected_office_role="AI director of engineering")

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
                 mock.patch.object(grace.os, "chown"), \
                 mock.patch.object(grace, "_private_regular", side_effect=lambda path, **_: path.read_bytes()):
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
        persisted_path = None
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

    def test_interrupted_token_delivery_revokes_orphan_before_reissue(self):
        registry = mock.Mock()
        transaction_context = mock.MagicMock()
        cursor_context = mock.MagicMock()
        registry.db.transaction.return_value = transaction_context
        registry.db.cursor.return_value = cursor_context
        cursor = cursor_context.__enter__.return_value
        cursor.fetchall.return_value = [{"credential_id": "orphan-credential-id"}]
        with tempfile.TemporaryDirectory() as directory:
            secret_dir = Path(directory)
            secret_file = secret_dir / "resident.credential"
            with mock.patch.object(grace, "GRACE_DIR", secret_dir), \
                 mock.patch.object(grace, "RESIDENT_TOKEN_FILE", secret_file), \
                 mock.patch.object(grace, "_one", return_value={
                     "principal_kind": "resident", "office_id": "office:grace",
                     "status": "active",
                 }), \
                 mock.patch.object(grace, "_write_secret") as write_secret:
                persisted_path = secret_file
                registry.issue_credential.return_value = "replacement-token-value-123456789"
                token = grace._ensure_principal(registry, "steward-token")
        self.assertEqual(token, "replacement-token-value-123456789")
        registry.revoke_credential.assert_called_once_with(
            "steward-token", "orphan-credential-id",
            reason_code="bootstrap_delivery_recovery")
        registry.issue_credential.assert_called_once_with("steward-token", "resident:grace")
        write_secret.assert_called_once_with(persisted_path, token)


if __name__ == "__main__":
    unittest.main()

# Revision history
# - 1.0.0: Initial Grace provisioning safety tests.
# - 1.0.1: Mock root-owned file metadata check so the contract test runs safely in CI.
# - 1.0.2: Mock metadata readback for idempotent secret-file tests.
# - 1.0.3: Cover orphan bearer revocation after interrupted credential-file delivery.
# - 1.0.4: Correct context-manager fixture for repeated registry cursor use.
# - 1.0.5: Assert the injected temporary protected credential path.
