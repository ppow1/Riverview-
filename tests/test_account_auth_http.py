# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_account_auth_http.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.1.1
# Purpose: Verify account cookie, CSRF, role and enrollment HTTP boundaries
# Execution Model: Loopback HTTP component test with an in-memory service double
# Observability: unittest HTTP status and response assertions
# Dependencies: Python 3.10+; Riverview dashboard server
# Authority: Binds a temporary loopback port and uses synthetic test identities only
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Initial account HTTP security tests
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Supply bounded account health projection in server tests
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001-CSRF-PATH | Assert dashboard-readable CSRF cookie scope
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Exercise password sign-in and server-side grant checks
# Changed: 2026-10-25 UTC | RV-WEB-V2-GRACE-RECOVERY-SESSION-CAPABILITY | Verify recovery UI hint requires a linked Steward without exposing its principal ID
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: This file
# History: Git and revision/backup manifest
# =============================================================================
"""HTTP-level checks for account authentication and role enforcement."""

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from riverview_core.account_auth import AuthDenied, IssuedSession
from riverview_core.status_dashboard.server import DashboardHTTPServer
from tests.test_status_dashboard import _FakeProjection, ROOT


class _AccountService:
    def __init__(self):
        self.identity = {"account_id":"account-1", "email":"viewer@example.org", "roles":["viewer"]}

    def status(self):
        return {"component_id":"WEBSITE-ACCOUNT-AUTH", "status":"degraded",
                "email_delivery":"disabled", "accounts":0, "pending_enrollments":0,
                "pending_email":0}

    def request_access(self, email, *, source_key):
        return {"status":"if_eligible_check_email", "expires_in":900}

    def verify_enrollment(self, challenge_id, token):
        return {"status":"pending_steward_review"}

    def request_login(self, email, *, source_key):
        return {"status":"if_eligible_check_email", "expires_in":900}

    def authenticate_password(self,email,password,*,source_key):
        if email!="viewer@example.org" or password!="correct horse battery staple":
            raise AuthDenied()
        return IssuedSession("account-1",email,("viewer",),"S"*43,"C"*43)

    def request_password_reset(self,email,*,source_key):
        return {"status":"if_eligible_check_email","expires_in":900}

    def set_password(self,challenge_id,token,password):
        return {"status":"password_set"}

    def consume_login(self, challenge_id, token):
        return IssuedSession("account-1", "viewer@example.org", ("viewer",), "S" * 43, "C" * 43)

    def authenticate(self, token, *, csrf_token=None, state_changing=False):
        if token != "S" * 43:
            return None
        if state_changing and csrf_token != "C" * 43:
            raise AuthDenied()
        return self.identity

    def require_role(self, identity, *roles):
        if not set(identity["roles"]).intersection(roles):
            raise AuthDenied()
        return identity

    def logout(self, token):
        return True

    def review_enrollments(self, actor, *, limit=50):
        self.require_role(actor, "steward")
        return []

    def list_accounts(self, actor, *, limit=50):
        self.require_role(actor, "steward")
        return []

    def decide_enrollment(self, actor, enrollment_id, decision, *, role="viewer",grant_type=None):
        self.require_role(actor, "steward")
        return {"status":decision}

    def set_account_state(self, actor, account_id, *, disabled):
        self.require_role(actor, "steward")
        return {"status":"updated"}

    def change_role(self, actor, account_id, role, *, grant):
        self.require_role(actor, "steward")
        return {"status":"updated"}

    def revoke_sessions(self, actor, account_id):
        self.require_role(actor, "steward")
        return {"status":"revoked", "sessions_revoked":1}


class AccountAuthHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token_path = Path(self.temp.name) / "dashboard-token"
        self.token = "A" * 43
        self.token_path.write_text(self.token)
        self.token_path.chmod(0o600)
        self.accounts = _AccountService()
        self.server = None
        for port in range(8799, 8699, -1):
            try:
                self.server = DashboardHTTPServer(
                    "127.0.0.1", port, self.token_path, _FakeProjection(),
                    ROOT / "src/riverview_core/status_dashboard/static",
                    account_auth_service=self.accounts)
                break
            except OSError:
                continue
        if self.server is None:
            self.fail("no free dashboard test port")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, *, cookie=None, csrf=None, body=None, origin=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        if csrf:
            headers["X-Riverview-CSRF"] = csrf
        if body is not None:
            headers["Content-Type"] = "application/json"
        if origin:
            headers["Origin"] = origin
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
        connection.request(method, path, body=None if body is None else json.dumps(body), headers=headers)
        response = connection.getresponse()
        result = response.status, response.getheaders(), response.read()
        connection.close()
        return result

    def test_public_enrollment_and_login_responses_are_generic(self):
        status, _, body = self.request("POST", "/api/v1/auth/enrollment",
                                       body={"email":"new@example.org"},
                                       origin="https://192.168.1.155")
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body)["status"], "if_eligible_check_email")
        status, _, body = self.request("POST", "/api/v1/auth/login",
            body={"email":"unknown@example.org","password":"not-the-password"})
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "not_authorized")
        status, _, body = self.request("POST", "/api/v1/auth/enrollment",
                                       body={"email":"new@example.org"},
                                       origin="https://attacker.invalid")
        self.assertEqual(status, 403)

    def test_login_issues_secure_http_only_session_and_csrf_cookie(self):
        status, headers, body = self.request("POST", "/api/v1/auth/session",
            body={"email":"viewer@example.org","password":"correct horse battery staple"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["identity"]["roles"], ["viewer"])
        cookies = [value for key, value in headers if key.lower() == "set-cookie"]
        self.assertEqual(len(cookies), 2)
        self.assertIn("Secure; HttpOnly; SameSite=Lax", cookies[0])
        self.assertIn("Secure; SameSite=Strict", cookies[1])
        self.assertNotIn("HttpOnly", cookies[1])
        self.assertIn("Path=/;", cookies[1])

    def test_session_reads_and_mutations_require_csrf_and_operator_role(self):
        cookie = "rv_account_session=" + "S"*43
        status, _, body = self.request("GET", "/api/v1/auth/session", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["identity"]["account_id"], "account-1")
        self.assertFalse(json.loads(body)["identity"]["can_decide_grace_recovery"])
        status, _, body = self.request("POST", "/api/v1/notifications/00000000-0000-0000-0000-000000000000/acknowledge",
                                       cookie=cookie, body={})
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "csrf_or_session_check_failed")
        status, _, body = self.request("POST", "/api/v1/notifications/00000000-0000-0000-0000-000000000000/acknowledge",
                                       cookie=cookie, csrf="C"*43, body={})
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "not_authorized")

    def test_recovery_decision_capability_hint_requires_linked_steward(self):
        cookie = "rv_account_session=" + "S"*43
        self.accounts.identity = {"account_id":"account-2", "email":"steward@example.org",
                                  "roles":["steward"]}
        status, _, body = self.request("GET", "/api/v1/auth/session", cookie=cookie)
        self.assertEqual(status, 200)
        identity = json.loads(body)["identity"]
        self.assertFalse(identity["can_decide_grace_recovery"])
        self.assertNotIn("authority_principal_id", identity)

        self.accounts.identity["authority_principal_id"] = "steward:fixture"
        status, _, body = self.request("GET", "/api/v1/auth/session", cookie=cookie)
        self.assertEqual(status, 200)
        identity = json.loads(body)["identity"]
        self.assertTrue(identity["can_decide_grace_recovery"])
        self.assertNotIn("authority_principal_id", identity)

    def test_steward_routes_deny_viewer_sessions(self):
        cookie = "rv_account_session=" + "S"*43
        status, _, body = self.request("GET", "/api/v1/account/enrollments", cookie=cookie)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "not_authorized")


if __name__ == "__main__":
    unittest.main()
