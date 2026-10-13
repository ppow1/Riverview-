#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_account_auth_browser.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.1.2
# Purpose: Verify account enrollment UI, HTTPS cookies, cookie auth and denials in Firefox
# Execution Model: Isolated request-driven browser acceptance harness
# Observability: Secret-free JSON results; local fake transport and identities only
# Dependencies: Python 3.10+; Firefox; geckodriver; OpenSSL; dashboard package
# Authority: Temporary loopback listener and synthetic account state; no Camrui DB or services
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Report safe assertion details on browser check failure
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001-CSRF-PATH | Verify browser-visible CSRF token and successful logout
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Verify email ownership, pending hold, password setup and portal login
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT-BROWSER-RUNTIME-TRACE | Emit safe DOM state when email challenge UI fails to render
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT-BROWSER-URL-TRACE | Reload page to model email-link open in a fresh browser navigation
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: tests/test_account_auth.py; tests/test_account_auth_http.py
# History: Git and revision/backup manifest
# =============================================================================
"""Exercise the website account flow in Firefox against an isolated TLS mock."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request

from riverview_core.account_auth import AuthDenied, IssuedSession
from riverview_core.status_dashboard.server import DashboardHTTPServer


class _Projection:
    def status(self):
        return {"schema_version":"rv.dashboard.status.v1", "component_id":"STEWARD-DASHBOARD",
                "component_version":"test", "observed_at":"2026-10-12T00:00:00Z",
                "projection_status":"unavailable", "freshness":"unavailable",
                "source":{"kind":"postgresql","schema":"test"},
                "cme":{"status":"unavailable"}, "workers":{"status":"unknown"}}

    def assignments(self, **kwargs): return {"status":"available","items":[]}
    def events(self, **kwargs): return {"status":"available","items":[]}
    def workers(self, **kwargs): return {"status":"available","items":[]}
    def attention(self, **kwargs): return {"status":"available","items":[]}
    def snapshot(self): return {"schema_version":"rv.dashboard.snapshot.v1"}
    def assignment_detail(self, assignment_id): return None
    def objectives(self, **kwargs): return {"status":"not_initialized","items":[]}


class _AccountService:
    def __init__(self):
        self.session = None
        self.identity = {"account_id":"browser-test-account", "email":"viewer@example.org",
                         "roles":["viewer"]}

    def status(self):
        return {"component_id":"WEBSITE-ACCOUNT-AUTH","status":"degraded",
                "email_delivery":"configured_unverified","accounts":1,
                "pending_enrollments":0,"pending_email":0}

    def request_access(self, email, *, source_key):
        self.enrollment_email=email
        return {"status":"if_eligible_check_email","expires_in":900}

    def verify_enrollment(self, challenge_id, token):
        return {"status":"pending_steward_review"}

    def request_password_reset(self,email,*,source_key):
        return {"status":"if_eligible_check_email","expires_in":900}

    def set_password(self,challenge_id,token,password):
        self.password=password
        return {"status":"password_set"}

    def verify_steward_bootstrap(self, challenge_id, token, *, authority_principal_id):
        return {"status":"steward_account_created"}

    def authenticate_password(self,email,password,*,source_key):
        if email!="viewer@example.org" or password!=getattr(self,"password",None):
            raise AuthDenied()
        self.session = "S" * 43
        return IssuedSession("browser-test-account", "viewer@example.org", ("viewer",),
                             self.session, "C" * 43)

    def authenticate(self, token, *, csrf_token=None, state_changing=False):
        if token != self.session:
            return None
        if state_changing and csrf_token != "C" * 43:
            raise AuthDenied()
        return self.identity

    def require_role(self, identity, *roles):
        if not set(identity.get("roles", ())).intersection(roles):
            raise AuthDenied()
        return identity

    def logout(self, token):
        self.session = None
        return True


def main():
    with tempfile.TemporaryDirectory(prefix="rv-account-browser-") as temp_name:
        temp = Path(temp_name)
        token_file = temp / "dashboard-token"
        token_file.write_text("A" * 43, encoding="ascii")
        token_file.chmod(0o600)
        key, cert = temp / "key.pem", temp / "cert.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                        "-days", "1", "-keyout", str(key), "-out", str(cert),
                        "-subj", "/CN=127.0.0.1"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        server = None
        for port in range(8799, 8699, -1):
            try:
                account_service = _AccountService()
                server = DashboardHTTPServer("127.0.0.1", port, token_file, _Projection(),
                    Path(__file__).resolve().parents[1] / "src/riverview_core/status_dashboard/static",
                    account_auth_service=account_service)
                break
            except OSError:
                continue
        if server is None:
            raise RuntimeError("no loopback dashboard test port")
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert, key)
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"https://127.0.0.1:{server.server_port}"
        os.environ["RIVERVIEW_PUBLIC_ORIGINS"] = origin
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            driver_port = reservation.getsockname()[1]
        driver = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(driver_port)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        session_id = None

        def wd(method, path, payload=None):
            data = None if payload is None else json.dumps(payload).encode()
            request = urllib.request.Request(f"http://127.0.0.1:{driver_port}{path}", data=data,
                method=method, headers={"Content-Type":"application/json"} if data is not None else {})
            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    raw = response.read()
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as exc:
                raise RuntimeError(f"webdriver_http_{exc.code}") from None

        def js(script):
            return wd("POST", f"/session/{session_id}/execute/sync", {"script":script,"args":[]})["value"]

        def wait_for(script, timeout=15):
            until = time.monotonic() + timeout
            while time.monotonic() < until:
                value = js("return (" + script + ");")
                if value:
                    return value
                time.sleep(0.15)
            raise RuntimeError("browser_condition_timeout")

        try:
            for _ in range(100):
                try:
                    wd("GET", "/status")
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.1)
            caps = {"capabilities":{"alwaysMatch":{"browserName":"firefox",
                "acceptInsecureCerts":True,"moz:firefoxOptions":{"args":["-headless"]}}}}
            session_id = wd("POST", "/session", caps)["value"]["sessionId"]
            wd("POST", f"/session/{session_id}/url", {"url":origin + "/"})
            wait_for("!document.querySelector('#login').hidden")
            initial = js("return ({request:!!document.querySelector('#account-request-form'), login:!!document.querySelector('#account-login-form'), password:!!document.querySelector('#account-password'), recovery:!!document.querySelector('#login-form')})")
            js("document.querySelector('#request-email').value='new@example.org'; document.querySelector('#account-request-form').requestSubmit(); return true")
            wait_for("document.querySelector('#account-auth-message').textContent.includes('verify ownership')")
            wd("POST",f"/session/{session_id}/url",{"url":origin+"/?email-link=1#account-verify?purpose=enrollment&challenge_id="+"E"*24+"&token="+"T"*43})
            time.sleep(1)
            nav_state=js("return ({ready:document.readyState,challengeLength:document.querySelector('#challenge-id').value.length,purposeButtonHidden:document.querySelector('#verify-enrollment').hidden,formHidden:document.querySelector('#email-challenge-form').hidden,message:document.querySelector('#account-auth-message').textContent,appLoaded:[...document.scripts].some(s=>s.src.endsWith('/assets/app.js'))})")
            try:
                wait_for("!document.querySelector('#verify-enrollment').hidden")
            except RuntimeError:
                print(json.dumps({"browser_enrollment_link_state":nav_state},sort_keys=True),flush=True)
                try: print(json.dumps({"browser_console":wd("POST",f"/session/{session_id}/log",{"type":"browser"}).get("value",[])[:8]}),flush=True)
                except Exception: pass
                raise
            js("document.querySelector('#verify-enrollment').click(); return true")
            wait_for("document.querySelector('#account-auth-message').textContent.includes('Pending Steward Approval')")
            blocked=js("return document.querySelector('#workspace').hidden")
            wd("POST",f"/session/{session_id}/url",{"url":origin+"/?email-link=2#account-verify?purpose=password_setup&challenge_id="+"P"*24+"&token="+"U"*43})
            wait_for("!document.querySelector('#set-account-password').hidden")
            js("document.querySelector('#new-password').value='correct horse battery staple'; document.querySelector('#set-account-password').click(); return true")
            wait_for("document.querySelector('#account-auth-message').textContent.includes('Password set')")
            js("document.querySelector('#account-email').value='viewer@example.org'; document.querySelector('#account-password').value='correct horse battery staple'; document.querySelector('#account-login-form').requestSubmit(); return true")
            wait_for("!document.querySelector('#workspace').hidden")
            identity_visible = js("return document.querySelector('#account-label').textContent.includes('viewer@example.org')")
            wd("POST", f"/session/{session_id}/url", {"url":origin + "/api/v1/auth/session"})
            cookies = wd("GET", f"/session/{session_id}/cookie")["value"]
            cookie_props = {item["name"]:{"secure":item.get("secure"),"httpOnly":item.get("httpOnly"),
                            "sameSite":item.get("sameSite"),"path":item.get("path")} for item in cookies}
            wd("POST", f"/session/{session_id}/url", {"url":origin + "/"})
            probe = wd("POST", f"/session/{session_id}/execute/async", {"script":"fetch('/api/v1/notifications/00000000-0000-0000-0000-000000000000/acknowledge',{method:'POST'}).then(async r=>arguments[arguments.length-1]({status:r.status,body:await r.json()}))","args":[]})["value"]
            csrf_visible = js("return document.cookie.split(';').some(part=>part.trim().startsWith('rv_account_csrf='))")
            js("document.querySelector('#sign-out').click(); return true")
            wait_for("!document.querySelector('#login').hidden")
            report = {"browser":subprocess.check_output(["firefox","--version"],text=True).strip(),
                      "origin":"loopback HTTPS test only", "request_access_form":initial["request"],
                      "sign_in_form":initial["login"], "legacy_recovery_form":initial["recovery"],
                      "fake_enrollment_submit":"PASS", "cookie_session_sign_in":"PASS" if identity_visible else "FAIL",
                      "pending_approval_blocks_portal":"PASS" if blocked else "FAIL",
                      "password_setup_then_login":"PASS" if identity_visible else "FAIL",
                      "csrf_cookie_visible_to_dashboard":"PASS" if csrf_visible else "FAIL",
                      "csrf_protected_logout":"PASS" if js("return document.querySelector('#workspace').hidden") else "FAIL",
                      "cookies":cookie_props, "viewer_csrf_denial":probe}
            expected = {"rv_account_session":{"secure":True,"httpOnly":True,"sameSite":"Lax","path":"/api/v1"},
                        "rv_account_csrf":{"secure":True,"httpOnly":False,"sameSite":"Strict","path":"/"}}
            report["cookie_contract"] = "PASS" if cookie_props == expected else "FAIL"
            report["viewer_csrf_denial"] = "PASS" if probe and probe.get("status")==403 and probe.get("body",{}).get("error")=="csrf_or_session_check_failed" else "FAIL"
            print(json.dumps(report,sort_keys=True), flush=True)
            if report["cookie_session_sign_in"]!="PASS" or report["cookie_contract"]!="PASS" or report["viewer_csrf_denial"]!="PASS" or report["csrf_cookie_visible_to_dashboard"]!="PASS" or report["csrf_protected_logout"]!="PASS" or report["pending_approval_blocks_portal"]!="PASS" or report["password_setup_then_login"]!="PASS" or not initial["request"] or not initial["login"] or not initial["password"] or not initial["recovery"]:
                raise RuntimeError("account_browser_acceptance_failed")
        finally:
            if session_id:
                try: wd("DELETE", f"/session/{session_id}")
                except Exception: pass
            driver.terminate()
            try: driver.wait(timeout=5)
            except subprocess.TimeoutExpired:
                driver.kill(); driver.wait(timeout=5)
            server.shutdown(); server.server_close(); thread.join(timeout=3)


if __name__ == "__main__":
    main()
