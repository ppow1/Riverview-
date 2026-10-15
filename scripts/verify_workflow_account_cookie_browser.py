# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_workflow_account_cookie_browser.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.0
# Purpose: Exercise canonical workflow loading with a browser-managed account cookie
# Execution Model: Isolated loopback fixture; starts and stops only its own HTTP and geckodriver processes
# Observability: Redacted JSON report and screenshot; synthetic account and workflow data only
# Dependencies: Python 3.10+, Firefox, geckodriver
# Authority: No production access; fixture login and graph reads only
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL025 | Add isolated account-cookie workflow browser regression
# Tests: scripts/verify_workflow_account_cookie_browser.py
# History: Git
"""Verify workflow index and detail requests use an account cookie in Firefox."""
import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_JS = ROOT / "src/riverview_core/status_dashboard/static/workflow.js"
APP_CSS = ROOT / "src/riverview_core/status_dashboard/static/app.css"
GRAPH_ID = "rv:test:account-cookie"
NODE_ID = f"{GRAPH_ID}:entry"
GRAPH = {
    "component_id": "TEST", "workflow_id": "account-cookie", "graph_revision": "1.0.0",
    "nodes": [{"id": NODE_ID, "type": "entry", "label": "Cookie-authenticated registry loaded",
               "node_revision": "1.0.0", "source_references": [],
               "documentation_references": [], "verification_evidence": []}],
    "edges": [], "execution_position": {"status": "unknown", "reason": "fixture"},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory for a redacted report and screenshot")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output_directory_must_not_exist")
    args.output.mkdir(parents=True, mode=0o700)
    os.chmod(args.output, 0o700)
    requests = []

    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *_):
            return

        def send_json(self, status, body, extra=()):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            for name, value in extra:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            authenticated = "rv_account_session=fixture-session" in self.headers.get("Cookie", "")
            requests.append({"path": self.path, "cookie_authenticated": authenticated,
                             "authorization_present": bool(self.headers.get("Authorization"))})
            if self.path == "/":
                body = b'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Workflow cookie fixture</title><link rel="stylesheet" href="/assets/app.css">
                <form id="login"><button id="sign-in" type="submit">Sign in fixture account</button></form>
                <button data-view="workflows">Workflows</button>
                <select id="graph-select" disabled></select><span id="graph-revision">Loading</span>
                <div id="graph-execution-position"></div><div id="graph-canvas"></div>
                <div id="graph-jumps"></div><aside id="graph-node-detail"></aside>
                <script>document.querySelector('#login').onsubmit=async e=>{e.preventDefault();
                const r=await fetch('/api/v1/auth/password',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({email:'fixture@example.invalid',password:'synthetic-only'})});
                if(r.ok)document.querySelector('#sign-in').textContent='Signed in';};</script>
                <script src="/assets/workflow.js" defer></script>'''
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif self.path == "/assets/workflow.js":
                body = WORKFLOW_JS.read_bytes(); self.send_response(200)
                self.send_header("Content-Type", "text/javascript")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif self.path == "/assets/app.css":
                body = APP_CSS.read_bytes(); self.send_response(200)
                self.send_header("Content-Type", "text/css")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif self.path == "/api/v1/graphs":
                if not authenticated:
                    return self.send_json(401, {"error": "authentication_required"})
                self.send_json(200, {"status": "available", "items": [{"graph_id": GRAPH_ID,
                    "component_id": "TEST", "workflow_id": "account-cookie"}]})
            elif self.path == "/api/v1/graphs/rv%3Atest%3Aaccount-cookie":
                if not authenticated:
                    return self.send_json(401, {"error": "authentication_required"})
                self.send_json(200, {"graph": GRAPH})
            else:
                self.send_json(404, {"error": "not_found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            if self.path != "/api/v1/auth/password":
                return self.send_json(404, {"error": "not_found"})
            requests.append({"path": self.path, "cookie_authenticated": False,
                             "authorization_present": bool(self.headers.get("Authorization"))})
            self.send_json(200, {"status": "authenticated"}, (
                ("Set-Cookie", "rv_account_session=fixture-session; Path=/; HttpOnly; SameSite=Strict"),
                ("Set-Cookie", "rv_account_csrf=fixture-csrf; Path=/; SameSite=Strict"),))

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0)); port = reservation.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), Fixture)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True); server_thread.start()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0)); driver_port = reservation.getsockname()[1]
    driver = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(driver_port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session_id = None

    def webdriver(method, path, payload=None):
        raw = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{driver_port}{path}", data=raw,
            method=method, headers={"Content-Type": "application/json"} if raw is not None else {})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"webdriver_http_{error.code}") from None

    def js(source, arguments=None):
        return webdriver("POST", f"/session/{session_id}/execute/sync",
                         {"script": source, "args": arguments or []})["value"]

    def wait_js(source, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = js("return (" + source + ");")
            if value:
                return value
            time.sleep(0.2)
        raise RuntimeError("browser_condition_timeout")

    try:
        for _ in range(100):
            if driver.poll() is not None:
                raise RuntimeError("geckodriver_stopped")
            try:
                webdriver("GET", "/status"); break
            except (OSError, urllib.error.URLError):
                time.sleep(0.2)
        else:
            raise RuntimeError("geckodriver_start_timeout")
        capabilities = {"capabilities": {"alwaysMatch": {
            "browserName": "firefox", "moz:firefoxOptions": {"args": ["-headless"]}}}}
        session_id = webdriver("POST", "/session", capabilities)["value"]["sessionId"]
        webdriver("POST", f"/session/{session_id}/window/rect",
                  {"x": 0, "y": 0, "width": 1280, "height": 850})
        webdriver("POST", f"/session/{session_id}/url", {"url": f"http://127.0.0.1:{port}/"})
        js("window.__rvBrowserErrors=[];addEventListener('error',e=>window.__rvBrowserErrors.push(String(e.message||'error')))")
        js("document.querySelector('#login').requestSubmit()")
        wait_js("document.cookie.includes('rv_account_csrf=fixture-csrf')")
        js("document.querySelector('[data-view=workflows]').click()")
        wait_js("document.querySelector('#graph-canvas svg') && document.querySelector('#graph-revision').textContent.includes('1 nodes')")
        js("document.querySelector('#graph-canvas .graph-node').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
        rendered = wait_js("document.querySelector('#graph-node-detail code')?.textContent")
        screenshot = base64.b64decode(webdriver("GET", f"/session/{session_id}/screenshot")["value"])
        errors = js("return window.__rvBrowserErrors")
        graph_requests = [item for item in requests if item["path"].startswith("/api/v1/graphs")]
        report = {"browser": subprocess.check_output(["firefox", "--version"], text=True).strip(),
                  "mode": "isolated_same_origin_account_cookie_fixture",
                  "registry_requests": graph_requests, "rendered_node_id": rendered,
                  "browser_errors": errors, "screenshot_bytes": len(screenshot)}
        report["failed_checks"] = []
        if len(graph_requests) != 2 or not all(item["cookie_authenticated"] for item in graph_requests):
            report["failed_checks"].append("account_cookie_registry_and_detail")
        if any(item["authorization_present"] for item in graph_requests):
            report["failed_checks"].append("unexpected_bearer_authorization")
        if rendered != NODE_ID:
            report["failed_checks"].append("workflow_node_not_rendered")
        if errors:
            report["failed_checks"].append("browser_errors")
        (args.output / "account-cookie-workflow.png").write_bytes(screenshot)
        (args.output / "browser-acceptance.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, sort_keys=True))
        if report["failed_checks"]:
            raise RuntimeError("workflow_account_cookie_browser_failed:" + ",".join(report["failed_checks"]))
    finally:
        if session_id:
            try: webdriver("DELETE", f"/session/{session_id}")
            except Exception: pass
        driver.terminate()
        try: driver.wait(timeout=5)
        except subprocess.TimeoutExpired: driver.kill(); driver.wait(timeout=5)
        server.shutdown(); server.server_close(); server_thread.join(timeout=2)


if __name__ == "__main__":
    main()
