# Riverview~ Controlled Source
# File: tests/test_v2_workspace_shell.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.2
# Purpose: Verify fixture preview, authentication, LAN restrictions, rate limiting, and recovery boundaries
# Execution Model: Request-driven local unittest fixtures
# Observability: unittest case names, counts, and exit status
# Dependencies: Python 3.10+ standard library; local V2 preview source
# Inputs/Outputs: Starts/stops isolated loopback test servers and temporary hash files
# Authority: Local fixture preview only; no production data or credentials
# Changed: 2026-10-20 UTC | RV-WEB-V2-LAN-PREVIEW-001 | Test protected LAN preview access
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: tests/test_v2_workspace_shell.py
# History: Git and revision/backup manifest
"""Offline tests for the fixture-only V2 preview."""
import http.client
import ipaddress
import json
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode

from scripts.serve_v2_workspace_preview import (
    LOGIN_MAX_FAILURES,
    LOGIN_WINDOW_SECONDS,
    PreviewHandler,
    PreviewServer,
    SESSION_SECONDS,
    create_password_record,
    load_password_record,
    trusted_client,
    verify_password,
)
from scripts.setup_v2_workspace_preview_auth import write_password_file

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

    def request(self, method, path, *, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return result

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


class AuthenticatedPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory(prefix="rv-v2-auth-test-")
        cls.auth_path = Path(cls.tempdir.name) / "auth.json"
        cls.password = secrets.token_urlsafe(18)
        write_password_file(cls.auth_path, cls.password)
        cls.record = load_password_record(cls.auth_path)
        cls.server = PreviewServer(("127.0.0.1", 0), PreviewHandler, auth_record=cls.record)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.tempdir.cleanup()

    def setUp(self):
        with self.server.login_attempts_lock:
            self.server.login_attempts.clear()

    def request(self, method, path, *, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return result

    def login(self, password):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://127.0.0.1:{self.port}",
        }
        return self.request("POST", "/login", headers=headers, body=urlencode({"password": password}))

    def test_auth_blocks_assets_until_password_and_issues_session_cookie(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"LAN-only preview over HTTP", body)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.request("GET", "/assets/workspace.js")[0], 401)
        status, _headers, body = self.login("incorrect human password")
        self.assertEqual(status, 200)
        self.assertIn(b"Password was not accepted", body)
        status, headers, _body = self.login(self.password)
        self.assertEqual(status, 303)
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn(f"Max-Age={SESSION_SECONDS}", cookie)
        self.assertNotIn("Secure", cookie)
        status, _headers, body = self.request("GET", "/assets/workspace.js", headers={"Cookie": cookie.split(";", 1)[0]})
        self.assertEqual(status, 200)
        self.assertIn(b"workspace", body)

    def test_session_signature_and_expiry(self):
        token = self.server.make_session_cookie(now=1000)
        self.assertTrue(self.server.valid_session_cookie(token, now=1001))
        self.assertFalse(self.server.valid_session_cookie(token, now=1000 + SESSION_SECONDS))
        self.assertFalse(self.server.valid_session_cookie(token + "x", now=1001))
        restarted = PreviewServer(("127.0.0.1", 0), PreviewHandler, auth_record=self.record)
        try:
            self.assertFalse(restarted.valid_session_cookie(token, now=1001))
        finally:
            restarted.server_close()

    def test_non_lan_client_is_rejected_before_login(self):
        network = ipaddress.ip_network("192.168.1.0/24")
        server = PreviewServer(("127.0.0.1", 0), PreviewHandler,
                               auth_record=self.record, trusted_network=network)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            conn.request("GET", "/", headers={"Host": f"127.0.0.1:{server.server_port}"})
            response = conn.getresponse()
            response.read()
            conn.close()
            self.assertEqual(response.status, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_origin_and_host_restrictions(self):
        status, _headers, _body = self.request("GET", "/", headers={"Host": "untrusted.example"})
        self.assertEqual(status, 400)
        status, _headers, _body = self.request("POST", "/login", headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "http://untrusted.example",
        }, body=urlencode({"password": self.password}))
        self.assertEqual(status, 403)
        status, _headers, _body = self.request("POST", "/login", headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "http://127.0.0.1:1",
        }, body=urlencode({"password": self.password}))
        self.assertEqual(status, 403)

    def test_rate_limit_after_five_failures(self):
        for _ in range(LOGIN_MAX_FAILURES - 1):
            status, _headers, _body = self.login("incorrect human password")
            self.assertEqual(status, 200)
        status, headers, _body = self.login("incorrect human password")
        self.assertEqual(status, 429)
        self.assertGreaterEqual(int(headers["Retry-After"]), LOGIN_WINDOW_SECONDS - 1)
        self.assertEqual(self.login(self.password)[0], 429)

    def test_lan_bind_requires_auth_and_narrow_network(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/serve_v2_workspace_preview.py"),
             "--host", "192.168.1.155", "--trusted-network", "192.168.1.0/24", "--port", "0"],
            cwd=ROOT, capture_output=True, text=True, timeout=5,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires an owner-only --auth-file", result.stderr)
        self.assertTrue(trusted_client("192.168.1.88", ipaddress.ip_network("192.168.1.0/24")))
        self.assertFalse(trusted_client("203.0.113.9", ipaddress.ip_network("192.168.1.0/24")))
        self.assertTrue(trusted_client("203.0.113.9", None))


class PasswordSetupTests(unittest.TestCase):
    def test_setup_persists_only_salted_hash_with_private_permissions(self):
        with tempfile.TemporaryDirectory(prefix="rv-v2-password-test-") as directory:
            path = Path(directory) / "auth.json"
            password = secrets.token_urlsafe(18)
            write_password_file(path, password)
            record = json.loads(path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(password, path.read_text())
            self.assertEqual(set(record), {"format", "algorithm", "iterations", "salt", "password_hash"})
            self.assertTrue(verify_password(password, record))
            self.assertFalse(verify_password("incorrect human password", record))
            with self.assertRaises(FileExistsError):
                write_password_file(path, password)


if __name__ == "__main__":
    unittest.main()
