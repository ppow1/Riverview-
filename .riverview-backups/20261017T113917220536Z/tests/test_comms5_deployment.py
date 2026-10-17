"""Comms5 deployment-unit safety regression tests.

File Revision: 1.0.2
Component: COMMS5-CAMRUI-DEPLOYMENT-TESTS
History: New file; no predecessor existed.
"""

import unittest
from pathlib import Path


class Comms5DeploymentTests(unittest.TestCase):
    def test_oauth_principal_is_copied_from_successful_forward_auth(self):
        fragment = (Path(__file__).parents[1] / "deploy/comms5/caddy-comms5-oauth-block.caddy").read_text()
        oauth_path = fragment.split("\n\thandle {\n\t\tforward_auth", 1)[1]
        self.assertIn("copy_headers X-Riverview-Comms5-Principal", oauth_path)
        self.assertIn("header_up -X-Riverview-Comms5", oauth_path)
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
