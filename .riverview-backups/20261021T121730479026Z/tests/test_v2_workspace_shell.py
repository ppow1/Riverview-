# Riverview~ Controlled Source
# File: tests/test_v2_workspace_shell.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.16
# Purpose: Verify V2 preview, authenticated Grace integration, and truthful resource/communications monitor state
# Execution Model: Request-driven local unittest fixtures
# Observability: unittest case names, counts, and exit status
# Dependencies: Python 3.10+ standard library; local V2 preview source
# Inputs/Outputs: Starts/stops isolated loopback test servers and temporary hash files
# Authority: Local fixture preview only; no production data or credentials
# Changed: 2026-10-21 UTC | RV-WEB-V2-HW-AI-RESOURCE-001 | Verify resource monitor provenance, unavailable metrics, and authorization behavior
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: tests/test_v2_workspace_shell.py
# History: Git and revision/backup manifest
"""Offline tests for the fixture workspace and authenticated Grace API client."""
import http.client
import ipaddress
import json
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import unittest
from pathlib import Path
from urllib.parse import urlencode

from scripts.serve_v2_workspace_preview import (
    CSRF_TOKEN_SECONDS,
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
        self.assertIn(b"Fixture workspace", body)
        self.assertIn("connect-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        for asset in ("fixtures.js", "workspace.js", "workspace.css", "communications.js", "communications.css", "resource-monitor.js", "resource-monitor.css", "grace-chat.js"):
            self.assertEqual(self.request("GET", f"/assets/{asset}")[0], 200)

    def test_grace_conversation_is_mounted_in_center_workspace(self):
        html = (ROOT / "website/v2/index.html").read_text(encoding="utf-8")
        workspace = html.index('id="workspace-main"')
        chat = html.index('id="grace-chat-root"')
        context = html.index('id="right-sidebar"')
        self.assertLess(workspace, chat)
        self.assertLess(chat, context)
        self.assertIn('id="grace-workspace"', html)
        self.assertIn('id="overview-content"', html)
        self.assertIn('id="grace-chat-history"', html)
        self.assertIn('id="grace-chat-form"', html)
        self.assertIn('Persisted messages with Grace', html)
        self.assertNotIn('id="conversation-toggle"', html)
        self.assertNotIn('id="grace-chat-root"', html[context:])

    def test_workspace_navigation_uses_authenticated_grace_and_keeps_fixtures_separate(self):
        source = (ROOT / "website/v2/assets/workspace.js").read_text(encoding="utf-8")
        fixtures = (ROOT / "website/v2/assets/fixtures.js").read_text(encoding="utf-8")
        snapshot = (ROOT / "website/v2/assets/snapshot.js").read_text(encoding="utf-8")
        self.assertIn('render(resident.realIdentity ? "grace" : "residents")', source)
        self.assertIn('status: "Authenticated chat · sign-in required"', fixtures)
        self.assertIn('status === "connected"', snapshot)
        self.assertIn('grace-conversation', snapshot)
        self.assertNotIn("conversation-toggle", source)

    def test_communications_activity_is_explicitly_unverified_without_authorized_feed(self):
        html = (ROOT / "website/v2/index.html").read_text(encoding="utf-8")
        monitor = (ROOT / "website/v2/assets/communications.js").read_text(encoding="utf-8")
        snapshot = (ROOT / "website/v2/assets/snapshot.js").read_text(encoding="utf-8")
        self.assertIn('data-view="communications"', html)
        self.assertIn('id="communications-workspace"', html)
        self.assertIn('data-state="unverified">UNVERIFIED', html)
        self.assertIn('data-count="outbound">Unavailable', html)
        self.assertIn('data-count="inbound">Unavailable', html)
        self.assertIn("This is not evidence of zero traffic", html + monitor)
        self.assertIn('id="communications-search"', html)
        self.assertIn('id="communications-window"', html)
        self.assertIn('id="communications-status"', html)
        self.assertIn('id="communications-direction"', html)
        self.assertIn('id="communications-ledger-body"', html)
        self.assertIn('id="communications-detail"', html)
        self.assertIn("sourceConfigured: false", monitor)
        self.assertIn("outbound: null, inbound: null", monitor)
        self.assertIn("No network request was sent", monitor)
        self.assertNotIn("fetch(", monitor)
        self.assertNotIn("innerHTML", monitor)
        self.assertIn("RiverviewV2Communications?.snapshotDiagnostics()", snapshot)
        self.assertIn("pending_count: null", snapshot)
        self.assertIn("failed_count: null", snapshot)
        self.assertIn("completed_count: null", snapshot)

    def test_hardware_ai_monitor_distinguishes_dashboard_status_from_unavailable_gpu_metrics(self):
        html = (ROOT / "website/v2/index.html").read_text(encoding="utf-8")
        monitor = (ROOT / "website/v2/assets/resource-monitor.js").read_text(encoding="utf-8")
        snapshot = (ROOT / "website/v2/assets/snapshot.js").read_text(encoding="utf-8")
        self.assertIn('data-view="resources"', html)
        self.assertIn("Hardware &amp; AI Resource Monitor", html)
        self.assertIn("GPU devices", html)
        self.assertIn("Utilization, memory &amp; thermals", html)
        self.assertIn("Loaded models &amp; server readiness", html)
        self.assertIn("Active jobs &amp; queues", html)
        self.assertIn("Unavailable", html)
        self.assertIn('"/api/v1/auth/session"', monitor)
        self.assertIn('"/api/v1/status"', monitor)
        self.assertIn('credentials: "same-origin"', monitor)
        self.assertIn('schema_version !== "rv.dashboard.status.v1"', monitor)
        self.assertNotIn("/api/v1/", html)
        self.assertNotRegex(monitor, r"192\.168\.1\.(160|162)|:8080|:18080")
        self.assertNotIn("innerHTML", monitor)
        self.assertNotIn("setInterval(", monitor)
        self.assertIn("hardware_ai_resource_monitor", snapshot)
        self.assertIn("worker counts, assignment states, hardware values, model identities and request details are excluded", snapshot)

    def test_resource_monitor_runtime_auth_provenance_and_failure_cases(self):
        result = subprocess.run(
            ["node", str(ROOT / "scripts/verify_v2_resource_monitor.cjs")],
            cwd=ROOT, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_rejects_mutations_and_traversal(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            self.assertEqual(self.request(method, "/")[0], 405)
        self.assertIn(self.request("GET", "/%2e%2e/scripts/serve_v2_workspace_preview.py")[0], (403, 404))

    def test_shell_has_fixture_only_resident_and_no_production_api(self):
        html = (ROOT / "website/v2/index.html").read_text()
        js = (ROOT / "website/v2/assets/workspace.js").read_text()
        fixtures = (ROOT / "website/v2/assets/fixtures.js").read_text()
        self.assertIn("PERSISTENT CONTEXT", html)
        self.assertIn("ChatGPT", html)
        self.assertIn("Comms5", html)
        self.assertIn('id="grace-chat-root"', html)
        self.assertIn('id="grace-login-form"', html)
        self.assertIn('id="grace-chat-history"', html)
        self.assertIn('id="grace-chat-form"', html)
        self.assertIn('src="assets/grace-chat.js"', html)
        self.assertIn("secure Dashboard authentication", html)
        self.assertIn('id="comms5-status" data-state="unverified"', html)
        self.assertIn("Traffic counts: UNVERIFIED", html)
        self.assertIn("not reported as zero", html)
        self.assertIn("fixtures[view]", js)
        self.assertIn("fixture-resident-02", fixtures)
        self.assertNotIn("/api/v1/", html + js + fixtures)
        self.assertNotIn("fetch(", js)
        self.assertIn('localStorage.getItem("rv.v2.theme")', js)
        self.assertIn('localStorage.setItem("rv.v2.theme", choice)', js)
        self.assertNotIn("sessionStorage", js)
        self.assertIn('id="theme-select"', html)
        self.assertIn('id="left-state"', html)
        self.assertIn('id="right-state"', html)
        self.assertIn('data-view="overview" aria-label="Overview"', html)
        self.assertIn('data-tooltip=', html)
        self.assertIn('id="snapshot-action"', html)
        self.assertNotIn('id="snapshot-action" class="snapshot-action" type="button" disabled', html)
        self.assertIn('localStorage.setItem("rv.v2.theme", choice)', js)
        self.assertNotIn("sessionStorage", js)
        self.assertIn('id="theme-select"', html)
        self.assertIn('id="left-state"', html)
        self.assertIn('id="right-state"', html)
        self.assertIn('data-view="overview" aria-label="Overview"', html)
        self.assertIn('data-tooltip=', html)
        self.assertIn('id="snapshot-action"', html)
        self.assertNotIn('id="snapshot-action" class="snapshot-action" type="button" disabled', html)
        self.assertIn("LIMIT_BYTES = 2 * 1024 * 1024", (ROOT / "website/v2/assets/snapshot.js").read_text())

    def test_grace_client_uses_existing_same_origin_session_csrf_and_grants(self):
        client = (ROOT / "website/v2/assets/grace-chat.js").read_text()
        self.assertIn('"/api/v1/auth/session"', client)
        self.assertIn('"/api/v1/resident/conversation-session"', client)
        self.assertIn('"/api/v1/resident/conversations/stream"', client)
        self.assertIn("rv_account_csrf=", client)
        self.assertIn('"X-Riverview-CSRF"', client)
        self.assertIn('credentials: "same-origin"', client)
        self.assertIn("resident_conversation_not_authorized", client)
        self.assertIn('localStorage.setItem(HISTORY_KEY, state.conversationId)', client)
        self.assertNotIn("Authorization", client)
        self.assertNotIn("sessionStorage.setItem", client)
        self.assertNotIn("innerHTML", client)
        self.assertNotIn("assistant_message", client.split('async function api', 1)[1].split('function setStatus', 1)[0])
        self.assertIn('location.pathname.startsWith("/v2/")', client)

    def test_v2_nginx_mount_is_same_origin_static_and_csp_restricted(self):
        route = (ROOT / "deploy/nginx/riverview-v2.location.conf").read_text()
        self.assertIn("location = /v2", route)
        self.assertIn("location ^~ /v2/", route)
        self.assertIn("alias /var/www/riverview-v2-preview/releases/RV-WEB-V2-COMMS-ACTIVITY-001/", route)
        self.assertIn("autoindex off", route)
        self.assertIn("connect-src 'self'", route)
        self.assertIn("frame-ancestors 'none'", route)
        self.assertIn("Cache-Control", route)
        self.assertNotIn("proxy_pass", route)

    def test_snapshot_uses_chat_status_without_capturing_conversation(self):
        snapshot = (ROOT / "website/v2/assets/snapshot.js").read_text()
        self.assertIn("RiverviewGraceChat?.snapshotDiagnostics()", snapshot)
        self.assertIn("messages_captured: false", (ROOT / "website/v2/assets/grace-chat.js").read_text())
        self.assertIn("No conversation or message contents or IDs", snapshot)
        self.assertNotIn("state.history", snapshot)
        self.assertIn("LIMIT_BYTES = 2 * 1024 * 1024", snapshot)
        self.assertIn('name: "workspace-state.json"', snapshot)
        self.assertIn('name: "rendered-view.txt"', snapshot)
        self.assertIn("safe history count", snapshot)
        self.assertIn("excludes conversation contents", snapshot)
        self.assertNotIn("does not contain live or server data", snapshot)
        self.assertIn('name: "manifest.json"', snapshot)
        self.assertIn('view === "grace" ? chat.status === "connected"', snapshot)
        self.assertIn('view === "resources" ? resourceMonitor.dashboard_projection === "healthy"', snapshot)
        self.assertIn('view === "grace" ? "grace-conversation" : view', snapshot)
        self.assertIn('schema: "riverview-v2-browser-snapshot/2"', snapshot)
        self.assertIn('outbound_count: null, inbound_count: null', snapshot)
        self.assertIn('inspectable_messages: false', snapshot)
        self.assertNotIn("fetch(", snapshot)
        self.assertIn("credentials: \"excluded\"", snapshot)

    def test_real_chrome_verifier_checks_actual_reply_and_reload_without_saving_text(self):
        verifier = (ROOT / "scripts/verify_v2_grace_chat_chrome.py").read_text()
        self.assertIn("Target.createTarget", verifier)
        self.assertIn("/api/v1/resident/conversations/stream", verifier)
        self.assertIn("reload_history_not_identical", verifier)
        self.assertIn("response_text_captured:false", verifier)
        self.assertIn("conversation text omitted from evidence", verifier)
        self.assertNotIn("--password", verifier)


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
        status, _headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        match = re.search(rb'name="csrf_token" value="([A-Za-z0-9_-]+)"', body)
        self.assertIsNotNone(match)
        return self.submit_login(password, match.group(1).decode("ascii"))

    def submit_login(self, password, csrf_token, *, origin="same"):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if origin == "same":
            headers["Origin"] = f"http://127.0.0.1:{self.port}"
        elif origin is not None:
            headers["Origin"] = origin
        fields = {"password": password}
        if csrf_token is not None:
            fields["csrf_token"] = csrf_token
        return self.request("POST", "/login", headers=headers, body=urlencode(fields))

    def csrf_token(self):
        status, _headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        match = re.search(rb'name="csrf_token" value="([A-Za-z0-9_-]+)"', body)
        self.assertIsNotNone(match)
        return match.group(1).decode("ascii")

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
        status, _headers, _body = self.submit_login(self.password, self.csrf_token(), origin="http://untrusted.example")
        self.assertEqual(status, 403)
        status, _headers, _body = self.submit_login(self.password, self.csrf_token(), origin="http://127.0.0.1:1")
        self.assertEqual(status, 403)

    def test_null_origin_with_valid_one_time_token_passes_origin_gate(self):
        status, _headers, body = self.submit_login("incorrect human password", self.csrf_token(), origin="null")
        self.assertEqual(status, 200)
        self.assertIn(b"Password was not accepted", body)

    def test_absent_origin_requires_and_accepts_valid_token(self):
        status, _headers, body = self.submit_login("incorrect human password", self.csrf_token(), origin=None)
        self.assertEqual(status, 200)
        self.assertIn(b"Password was not accepted", body)

    def test_csrf_token_is_required_one_time_ip_bound_and_short_lived(self):
        status, _headers, _body = self.submit_login(self.password, None)
        self.assertEqual(status, 403)
        token = self.csrf_token()
        status, _headers, _body = self.submit_login(self.password, token)
        self.assertEqual(status, 303)
        self.assertEqual(self.submit_login(self.password, token)[0], 403)
        token = self.server.issue_csrf_token("192.0.2.1", now=100.0)
        self.assertFalse(self.server.consume_csrf_token(token, "127.0.0.1", now=101.0))
        token = self.server.issue_csrf_token("127.0.0.1", now=100.0)
        self.assertFalse(self.server.consume_csrf_token(token, "127.0.0.1", now=100.0 + CSRF_TOKEN_SECONDS))

    def test_csrf_token_can_only_be_consumed_once_under_concurrency(self):
        token = self.server.issue_csrf_token("127.0.0.1")
        start = threading.Barrier(8)
        def consume():
            start.wait(timeout=2)
            return self.server.consume_csrf_token(token, "127.0.0.1")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _index: consume(), range(8)))
        self.assertEqual(sum(results), 1)

    def test_foreign_origin_is_rejected_even_with_valid_token(self):
        status, _headers, _body = self.submit_login(self.password, self.csrf_token(), origin="https://127.0.0.1")
        self.assertEqual(status, 403)

    def test_origin_authority_and_port_must_match_exactly(self):
        status, _headers, body = self.submit_login("incorrect human password", self.csrf_token(),
                                                   origin=f"http://127.0.0.1:{self.port}")
        self.assertEqual(status, 200)
        self.assertIn(b"Password was not accepted", body)
        status, _headers, _body = self.submit_login(self.password, self.csrf_token(),
                                                    origin=f"http://127.0.0.1:{self.port + 1}")
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
