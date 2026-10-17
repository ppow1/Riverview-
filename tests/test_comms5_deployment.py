"""Comms5 deployment-unit safety regression tests.

File Revision: 1.0.0
Component: COMMS5-CAMRUI-DEPLOYMENT-TESTS
History: New file; no predecessor existed.
"""

import unittest
from pathlib import Path


class Comms5DeploymentTests(unittest.TestCase):
    def test_reverse_tunnel_credential_is_passed_by_systemd(self):
        unit = (Path(__file__).parents[1] / "deploy/systemd/riverview-comms5-tunnel.service").read_text()
        self.assertIn("User=admin1", unit)
        self.assertIn("LoadCredential=ionoge-tunnel:/etc/riverview/comms5/ionoge-tunnel", unit)
        self.assertIn("-i %d/ionoge-tunnel", unit)
        self.assertIn("StrictHostKeyChecking=yes", unit)
        self.assertIn("UserKnownHostsFile=/etc/riverview/comms5/known_hosts", unit)
        self.assertIn("-R 127.0.0.1:11826:127.0.0.1:11826", unit)
        self.assertNotIn("-i /etc/riverview/comms5/ionoge-tunnel", unit)


if __name__ == "__main__":
    unittest.main()
