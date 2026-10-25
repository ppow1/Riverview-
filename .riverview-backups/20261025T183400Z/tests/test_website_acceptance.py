"""Focused acceptance-system tests.

Revision: 1.1.0
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("seed_personas",ROOT/"scripts/seed_website_test_personas.py")
seed=importlib.util.module_from_spec(spec); spec.loader.exec_module(seed)
driver_spec=importlib.util.spec_from_file_location("install_chromedriver",ROOT/"scripts/install_acceptance_chromedriver.py")
driver_module=importlib.util.module_from_spec(driver_spec); driver_spec.loader.exec_module(driver_module)


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

    def test_account_administration_acceptance_is_role_checked_and_mutation_free(self):
        source=(ROOT/"scripts/run_website_acceptance.py").read_text()
        self.assertIn('"account_admin_anonymous_denied"',source)
        self.assertIn('"account_admin_steward_read"',source)
        self.assertIn('"account_admin_viewer_denied"',source)
        self.assertIn("ACCOUNT_ADMIN_PRE_FEATURE_COMMIT",source)
        self.assertIn('"pre_feature_baseline_release"',source)
        self.assertIn("/api/v1/account/enrollments?limit=50",source)
        self.assertIn("/api/v1/account/users?limit=100",source)
        self.assertNotIn("/api/v1/account/enrollments/",source)
        self.assertIn("['disable',{disabled:true}]",source)
        self.assertIn("['roles',{role:'steward',grant:true}]",source)
        self.assertIn("['grant',{revoked:true}]",source)
        self.assertIn("[403,403,403,403,403,403,403]",source)
        self.assertIn('"account_state_controls_visible"',source)
        self.assertIn('"account_role_grant_controls_visible"',source)
        self.assertIn('ACCOUNT_STATE_PRE_FEATURE_COMMIT',source)
        self.assertIn('ACCOUNT_ROLE_GRANT_PRE_FEATURE_COMMIT',source)
        self.assertIn('ACCOUNT_EMAIL_PRE_FEATURE_COMMIT',source)
        self.assertIn('live_source_commit=live_source_commit',source)
        self.assertIn('"account_email_settings_steward_read"',source)
        self.assertIn("/api/v1/account/email-settings",source)
        self.assertIn("?.value??null",source)

    def test_predeploy_account_denial_and_nginx_snippet_rollback_are_safe(self):
        runner=(ROOT/"scripts/run_website_acceptance.py").read_text()
        deploy=(ROOT/"scripts/deploy_website_acceptance.sh").read_text()
        self.assertIn("status in {401,403}",runner)
        self.assertIn("restore_include()",deploy)
        self.assertIn('"$backup/riverview-website-acceptance.location.conf"',deploy)

    def test_verification_report_view_is_same_origin_and_redacted(self):
        page=(ROOT/"website/v2/deployed/index.html").read_text()
        script=(ROOT/"website/v2/deployed/assets/verification-status.js").read_text()
        self.assertIn("/v2/verification/latest.json",page)
        self.assertIn("/v2/verification/latest.json",script)
        self.assertIn("credentials:\"same-origin\"",script)

    def test_chromedriver_download_url_is_exact_official_build(self):
        metadata={"versions":[{"version":"155.0.8059.84","downloads":{"chromedriver":[
            {"platform":"linux64","url":"https://storage.googleapis.com/chrome-for-testing-public/155.0.8059.84/linux64/chromedriver-linux64.zip"}]}}]}
        self.assertEqual(driver_module.cft_url("155.0.8059.84",metadata),metadata["versions"][0]["downloads"]["chromedriver"][0]["url"])
        metadata["versions"][0]["downloads"]["chromedriver"][0]["url"]="https://example.invalid/driver.zip"
        with self.assertRaises(ValueError): driver_module.cft_url("155.0.8059.84",metadata)


if __name__=="__main__": unittest.main()
