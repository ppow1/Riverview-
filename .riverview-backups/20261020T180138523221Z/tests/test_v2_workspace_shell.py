# Riverview~ Controlled Source
# File: tests/test_v2_workspace_shell.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.0
# Purpose: Verify preview server boundary and shell contract
# Authority: Local fixture preview only
# Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Initial offline preview tests
"""Offline tests for the fixture-only V2 preview."""
import http.client
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkspacePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/serve_v2_workspace_preview.py"), "--port", "0"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        line = cls.proc.stdout.readline().strip()
        if "http://127.0.0.1:" not in line:
            raise RuntimeError(f"preview did not start: {line}")
        cls.port = int(line.rsplit(":", 1)[1].split("/", 1)[0])
        for _ in range(50):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=1)
                conn.request("GET", "/")
                response = conn.getresponse()
                response.read()
                conn.close()
                if response.status == 200:
                    return
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("preview_server_not_ready")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
            cls.proc.wait(timeout=3)

    def request(self, method, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        conn.request(method, path)
        response = conn.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        conn.close()
        return response.status, headers, body

    def test_serves_shell_and_assets_with_no_network_policy(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Fixture data", body)
        self.assertIn("connect-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        for asset in ("fixtures.js", "workspace.js", "workspace.css"):
            self.assertEqual(self.request("GET", f"/assets/{asset}")[0], 200)

    def test_rejects_mutations_and_traversal(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            self.assertEqual(self.request(method, "/")[0], 405)
        self.assertIn(self.request("GET", "/%2e%2e/scripts/serve_v2_workspace_preview.py")[0], (403, 404))

    def test_shell_has_fixture_only_resident_and_no_production_api(self):
        html = (ROOT / "website/v2/index.html").read_text()
        js = (ROOT / "website/v2/assets/workspace.js").read_text()
        fixtures = (ROOT / "website/v2/assets/fixtures.js").read_text()
        self.assertIn("Persistent context", html)
        self.assertIn("ChatGPT", html)
        self.assertIn("Comms5", html)
        self.assertIn("fixtures[view]", js)
        self.assertIn("fixture-resident-02", fixtures)
        self.assertNotIn("/api/v1/", html + js + fixtures)
        self.assertNotIn("fetch(", js)
        self.assertNotIn("localStorage", js)
        self.assertNotIn("sessionStorage", js)


if __name__ == "__main__":
    unittest.main()
