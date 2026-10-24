"""Focused acceptance-system tests.

Revision: 1.0.0
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("seed_personas",ROOT/"scripts/seed_website_test_personas.py")
seed=importlib.util.module_from_spec(spec); spec.loader.exec_module(seed)


class WebsiteAcceptanceTests(unittest.TestCase):
    def test_seeded_password_hash_uses_account_auth_format(self):
        from riverview_core.account_auth import AccountAuthService
        secret="acceptance-secret-value-123456"
        self.assertTrue(AccountAuthService._password_matches(secret,seed.password_hash(secret)))

    def test_credential_file_persists_and_is_private(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"personas"/"credentials.json"
            first=seed.write_credentials(path)
            second=seed.write_credentials(path)
            self.assertEqual(first,second)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)

    def test_roles_are_existing_riverview_roles(self):
        self.assertEqual(set(seed.ROLES.values()),{"viewer","operator","steward"})
        self.assertEqual(seed.ROLES["engineering"],"operator")

    def test_grace_and_cancellation_are_explicitly_not_simulated(self):
        source=(ROOT/"scripts/run_website_acceptance.py").read_text()
        self.assertIn('"grace_natural_language_query","status":"SKIPPED"',source)
        self.assertIn('"production_cancellation_mutation","status":"SKIPPED"',source)
        self.assertNotIn("/api/v1/resident/conversations/stream",source)

    def test_verification_report_view_is_same_origin_and_redacted(self):
        page=(ROOT/"website/v2/deployed/index.html").read_text()
        script=(ROOT/"website/v2/deployed/assets/verification-status.js").read_text()
        self.assertIn("/v2/verification/latest.json",page)
        self.assertIn("/v2/verification/latest.json",script)
        self.assertIn("credentials:\"same-origin\"",script)


if __name__=="__main__": unittest.main()
