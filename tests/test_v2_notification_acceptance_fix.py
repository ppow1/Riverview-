"""Focused regression checks for live V2 notification settings acceptance."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class V2NotificationAcceptanceFixTests(unittest.TestCase):
    def test_grace_routes_natural_current_setting_question_to_shared_api(self):
        source = (ROOT / "website/v2/deployed/assets/grace-chat.js").read_text()
        self.assertIn("what(?:'s|\\s+(?:is|are))", source)
        self.assertIn("notification\\s+(?:setting|settings|level|preferences|configuration)", source)
        self.assertIn('apiWithTransientRetry("/api/v1/notification-settings")', source)
        self.assertIn("time zone: ${settings.quiet_hours.timezone}", source)
        self.assertIn("Notification settings request failed", source)

    def test_notification_api_retries_only_transient_gateway_failures(self):
        source = (ROOT / "website/v2/deployed/assets/notification-settings.js").read_text()
        self.assertIn("const delays = [0, 300, 800, 1500]", source)
        self.assertIn("[502, 503, 504].includes(response.status)", source)
        self.assertIn("credentials: \"same-origin\"", source)
        self.assertIn('fetch("/api/v1/notification-settings"', source)

    def test_live_workspace_copy_does_not_claim_sample_records_are_live(self):
        html = (ROOT / "website/v2/deployed/index.html").read_text()
        self.assertIn("<title>Riverview V2 Workspace</title>", html)
        self.assertIn('id="v2-current-date"', html)
        self.assertIn("overview cards contain sample records", html)
        self.assertNotIn("TUESDAY, OCTOBER 20", html)


if __name__ == "__main__":
    unittest.main()
