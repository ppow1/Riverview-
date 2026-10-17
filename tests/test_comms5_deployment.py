"""Comms5 deployment-unit safety regression tests.

File Revision: 1.0.4
Component: COMMS5-CAMRUI-DEPLOYMENT-TESTS
History: New file; no predecessor existed.
Changed: 2026-10-17 UTC | RV-COMMS5-OAUTH-FORWARD-HEADERS-001 | Reject header deletion that strips the trusted Comms5 marker.
"""

import unittest
from pathlib import Path


class Comms5DeploymentTests(unittest.TestCase):
    def test_service_uses_systemd_dashboard_credential_and_loopback_projection(self):
        unit = (Path(__file__).parents[1] / "deploy/systemd/riverview-comms5-camrui.service").read_text()
        self.assertIn("LoadCredential=dashboard-token:/home/admin1/.config/riverview/status-dashboard.token", unit)
        self.assertIn("Environment=RIVERVIEW_COMMS5_DASHBOARD_URL=http://127.0.0.1:8767", unit)
        self.assertIn("Environment=RIVERVIEW_COMMS5_HOST=127.0.0.1", unit)
        self.assertIn("DynamicUser=yes", unit)

    def test_oauth_principal_is_copied_from_successful_forward_auth(self):
        fragment = (Path(__file__).parents[1] / "deploy/comms5/caddy-comms5-oauth-block.caddy").read_text()
        oauth_path = fragment.split("\n\thandle {\n\t\tforward_auth", 1)[1]
        self.assertIn("copy_headers X-Riverview-Comms5-Principal", oauth_path)
        self.assertIn("header_up X-Riverview-Comms5 1", oauth_path)
        self.assertNotIn("header_up -X-Riverview-Comms5\n", oauth_path)
        self.assertNotIn("header_up -X-Riverview-Comms5-Principal", oauth_path)
        self.assertNotIn("header_up X-Riverview-Comms5-Principal steward", oauth_path)
        # The legacy compatibility route remains explicitly bound to the Steward identity.
        self.assertEqual(fragment.count("header_up X-Riverview-Comms5-Principal steward"), 1)

    def test_reverse_tunnel_credential_is_passed_by_systemd(self):
        unit = (Path(__file__).parents[1] / "deploy/systemd/riverview-comms5-tunnel.service").read_text()
        self.assertIn("User=admin1", unit)
        self.assertIn("LoadCredential=ionoge-tunnel:/etc/riverview/comms5/ionoge-tunnel", unit)
        self.assertIn("LoadCredential=known-hosts:/etc/riverview/comms5/known_hosts", unit)
        self.assertIn("-i %d/ionoge-tunnel", unit)
        self.assertIn("StrictHostKeyChecking=yes", unit)
        self.assertIn("UserKnownHostsFile=%d/known-hosts", unit)
        self.assertNotIn("UserKnownHostsFile=/etc/riverview/", unit)
        self.assertIn("-R 127.0.0.1:11826:127.0.0.1:11826", unit)
        self.assertNotIn("-i /etc/riverview/comms5/ionoge-tunnel", unit)


if __name__ == "__main__":
    unittest.main()
