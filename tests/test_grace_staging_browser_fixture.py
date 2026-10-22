# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_grace_staging_browser_fixture.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Run the authenticated Grace staging browser suite against a disposable loopback fixture
# Execution Model: Isolated nested Chromium acceptance runner with synthetic cookie authorization
# Observability: Assert successful UI boundary check, guardrail report, and redacted private evidence
# Dependencies: .venv Playwright/Chromium and pytest; no external service or production credential
# Authority: Test-only cookie, loopback-only fixture, no objective creation or work-order submission
# Changed: 2026-10-18 UTC | RV-C2-DOD-REMEDIATION-001 | Advance revision prospectively; retain local staging guard proof
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: tests/test_grace_staging_browser_fixture.py
# History: Git
# =============================================================================
"""Prove cookie loading, Grace boundary inspection, network fencing, and redacted evidence locally."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PAGE = ROOT / "browser-tests/fixtures/grace-staging.html"
TEST_COOKIE = "synthetic-c2-cookie-never-a-credential"
CONVERSATION_ID = "00000000-0000-4000-8000-000000000001"
ACCOUNT_LABEL = "C2 Synthetic Steward (fixture only)"
SEED_TEXT = "Harmless local staging acceptance request."


class GraceFixtureHandler(BaseHTTPRequestHandler):
    server_version = "RiverviewDisposableGraceFixture/1.0"
    protocol_version = "HTTP/1.1"
    requests_seen: list[tuple[str, str, bool]] = []

    def log_message(self, format, *args):
        # Never echo Cookie headers, request bodies, or fixture conversation text.
        return

    def _authorized(self) -> bool:
        return f"rv_test_session={TEST_COOKIE}" in self.headers.get("Cookie", "")

    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        authorized = self._authorized()
        self.requests_seen.append(("GET", self.path, authorized))
        if not authorized:
            self._send(401, b"fixture authentication required", "text/plain")
            return
        if self.path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        elif self.path == "/":
            self._send(200, FIXTURE_PAGE.read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        # The staging bridge's one permitted write is an empty-body session initialization.
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        authorized = self._authorized()
        self.requests_seen.append(("POST", self.path, authorized))
        if (not authorized or self.path != "/api/v1/resident/conversation-session"
                or body):
            self._send(403, b"fixture request rejected", "text/plain")
            return
        self._send(200, b"{}", "application/json")


class GraceStagingBrowserFixtureTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / ".venv/bin/python").is_file(),
                         "requires the optional local Playwright .venv; run the documented focused command")
    def test_authenticated_staging_bridge_is_scoped_read_only_and_redacted(self):
        GraceFixtureHandler.requests_seen.clear()
        server = ThreadingHTTPServer(("127.0.0.1", 0), GraceFixtureHandler)
        server.daemon_threads = True
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            origin = f"http://{host}:{port}"
            with tempfile.TemporaryDirectory(prefix="rv-c2-staging-") as temp:
                temp_path = Path(temp)
                state_path = temp_path / "storage-state.json"
                state_path.write_text(json.dumps({
                    "cookies": [{"name": "rv_test_session", "value": TEST_COOKIE,
                                 "domain": host, "path": "/", "expires": -1,
                                 "httpOnly": True, "secure": False, "sameSite": "Lax"}],
                    "origins": [],
                }), encoding="utf-8")
                state_path.chmod(0o600)
                output = temp_path / "evidence"
                env = os.environ.copy()
                env.update({
                    "RIVERVIEW_GRACE_STAGING_MODE": "",
                    "RIVERVIEW_GRACE_STAGING_FIXTURE": "1",
                    "RIVERVIEW_GRACE_STAGING_ORIGIN": origin,
                    "RIVERVIEW_GRACE_STAGING_STORAGE_STATE": str(state_path),
                    "RIVERVIEW_GRACE_STAGING_TEST_ACCOUNT_LABEL": ACCOUNT_LABEL,
                    "RIVERVIEW_GRACE_STAGING_CONVERSATION_ID": CONVERSATION_ID,
                    "RIVERVIEW_GRACE_STAGING_SEED_MESSAGE_TEXT": SEED_TEXT,
                    "RIVERVIEW_GRACE_STAGING_CONFIRMATION": "I_CONFIRM_DISPOSABLE_GRACE_STAGING",
                    "RIVERVIEW_BROWSER_BASE_URL": origin,
                })
                runner = ROOT / "scripts/run_linux_browser_acceptance.py"
                result = subprocess.run(
                    [sys.executable, str(runner), "--grace-staging-readonly",
                     "--base-url", origin, "--smoke-path", "/", "--output", str(output)],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=90, check=False,
                )
                self.assertEqual(result.returncode, 0, msg=f"fixture browser run failed: {result.stdout}\n{result.stderr}")

                report = json.loads((output / "browser-errors.json").read_text())
                run = json.loads((output / "runner-result.json").read_text())
                self.assertEqual(report["failed"], 0)
                self.assertEqual(report["passed"], 3)
                self.assertEqual(report["skipped"], 1)
                self.assertTrue(any(name.endswith("grace-staging-redacted.png")
                                    for name in report["screenshots"]))
                self.assertEqual(report["traces"], [])
                self.assertEqual(run["status"], "PASS")
                self.assertEqual(run["http_methods_allowed"],
                                 ["GET", "HEAD", "POST /api/v1/resident/conversation-session (empty body)"])
                self.assertTrue(GraceFixtureHandler.requests_seen)
                self.assertTrue(all(authorized for _, _, authorized in GraceFixtureHandler.requests_seen),
                                "browser did not apply the scoped cookie to the exact fixture host")
                self.assertTrue(all(method == "GET" and path in {"/", "/favicon.ico"}
                                    or method == "POST" and path == "/api/v1/resident/conversation-session"
                                    for method, path, _ in GraceFixtureHandler.requests_seen),
                                "a denied mutation or cross-origin request reached the fixture server")
                for artifact in output.rglob("*"):
                    if not artifact.is_file() or artifact == state_path:
                        continue
                    self.assertFalse(artifact.stat().st_mode & 0o077, f"evidence mode too broad: {artifact.name}")
                    if artifact.suffix in {".json", ".txt"}:
                        content = artifact.read_text(encoding="utf-8", errors="replace")
                        for sensitive in (TEST_COOKIE, ACCOUNT_LABEL, CONVERSATION_ID, SEED_TEXT,
                                          "Private fixture input", "Synthetic fixture objective details",
                                          "269535bd", "private-cookie", "private-token",
                                          "private-conversation-id", "private-query-token",
                                          "cross-origin-private-id", "private-cross-origin-token",
                                          "Private failure conversation"):
                            self.assertNotIn(sensitive, content, f"private fixture content leaked in {artifact.name}")
                screenshot = next(output.rglob("grace-staging-redacted.png"))
                self.assertEqual(screenshot.stat().st_mode & 0o777, 0o600)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
