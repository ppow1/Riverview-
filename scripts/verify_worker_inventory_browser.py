# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_worker_inventory_browser.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.6
# Purpose: Verify worker registration, heartbeat states and pagination in Firefox
# Execution Model: Isolated loopback fixture; owns only its HTTP and geckodriver processes
# Observability: Redacted JSON report and screenshot; synthetic account and assignment data
# Dependencies: Python 3.10+, Firefox, geckodriver
# Authority: No production access; authenticated fixture reads only
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL008 | Add isolated worker inventory browser verification
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: scripts/verify_worker_inventory_browser.py
# History: Git
"""Verify worker registration and heartbeat distinctions in Firefox."""
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
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/riverview_core/status_dashboard/static"
ASSIGNMENTS = [{"assignment_id": "fixture-linked", "state": "active", "owner": "fixture",
                "workflow_id": "rv:test:assignment", "workflow_step": "inspect",
                "process_graph_id": "rv:test:assignment", "process_node_id": "rv:test:assignment:inspect",
                "version": 3, "correlation_id": "fixture-correlation", "updated_at": "2026-10-15T00:00:00Z",
                "last_meaningful_progress": {"event_seq": 7, "recorded_at": "2026-10-15T00:00:00Z"}},
               {"assignment_id": "fixture-unlinked", "state": "blocked", "owner": "fixture",
                "workflow_id": "rv:test:assignment", "workflow_step": "unknown",
                "process_graph_id": None, "process_node_id": None, "version": 1,
                "correlation_id": "fixture-correlation-2", "updated_at": None,
                "last_meaningful_progress": {}}]
STATUS = {"projection_status": "healthy", "freshness": "fresh", "observed_at": "2026-10-15T00:00:00Z",
          "source": {"database": "fixture", "schema": "fixture", "source_commit": "fixture", "deployment_id": "fixture"},
          "assignment_counts": {"active": 1, "blocked": 1}, "assignments_total": 2, "event_cursor": 3,
          "cme": {"status": "unknown"}, "workers": {"status": "available"},
          "grace_execution": {"status": "not_initialized"}, "relations": {"cme_monitor_events": False}}
WORKERS = [
    {"worker_id": "worker-active", "active": True, "status": "healthy", "active_leases": 1,
     "last_heartbeat_at": "2026-10-15T00:00:00Z"},
    {"worker_id": "worker-inactive", "active": False, "status": "inactive", "active_leases": 0,
     "last_heartbeat_at": None},
    {"worker_id": "worker-stale", "active": True, "status": "stale", "active_leases": 0,
     "last_heartbeat_at": "2026-10-14T00:00:00Z"},
    {"worker_id": "worker-unknown", "active": None, "status": "unknown", "active_leases": 0,
     "last_heartbeat_at": None},
]
EVENTS = [{"seq": seq, "event_id": f"fixture-event-{seq}", "event_type": f"fixture_event_{seq}",
           "recorded_at": f"2026-10-15T00:00:0{seq}Z", "assignment_id": None,
           "correlation_id": f"fixture-correlation-{seq}", "causation_id": None}
          for seq in range(1, 5)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory for report and screenshot")
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

        def send_file(self, path, content_type, extra=()):
            raw = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
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
                return self.send_file(STATIC / "index.html", "text/html; charset=utf-8",
                    (("Set-Cookie", "rv_account_session=fixture-session; Path=/; HttpOnly; SameSite=Strict"),))
            if self.path.startswith("/assets/"):
                name = self.path.removeprefix("/assets/")
                allowed = {"app.js": "text/javascript", "workflow.js": "text/javascript",
                           "resident-permissions.js": "text/javascript", "app.css": "text/css"}
                if name in allowed:
                    return self.send_file(STATIC / name, allowed[name])
            if not authenticated:
                return self.send_json(401, {"error": "authentication_required"})
            if self.path == "/api/v1/auth/session":
                return self.send_json(200, {"identity": {"email": "fixture@example.invalid", "roles": ["steward"]}})
            if self.path == "/api/v1/status":
                return self.send_json(200, STATUS)
            if self.path.startswith("/api/v1/assignments?"):
                return self.send_json(200, {"status": "available", "items": ASSIGNMENTS, "next_cursor": None})
            if self.path.startswith("/api/v1/events?"):
                query = parse_qs(urlsplit(self.path).query)
                if "before_seq" in query:
                    items = EVENTS[:int(query["before_seq"][0]) - 1]
                    return self.send_json(200, {"status": "available", "items": items,
                        "next_cursor": None, "older_cursor": None})
                if "after_seq" in query:
                    items = EVENTS[int(query["after_seq"][0]):]
                    return self.send_json(200, {"status": "available", "items": items,
                        "next_cursor": None, "older_cursor": None})
                return self.send_json(200, {"status": "available", "items": EVENTS[1:3],
                    "next_cursor": None, "older_cursor": 2})
            if self.path.startswith("/api/v1/objectives?"):
                return self.send_json(200, {"status": "available", "items": []})
            if self.path.startswith("/api/v1/workers?"):
                after = "after=worker-cursor" in self.path
                return self.send_json(200, {"status": "available", "items": WORKERS[3:] if after else WORKERS[:3],
                    "next_cursor": None if after else "worker-cursor", "page_limit": 25})
            if self.path.startswith("/api/v1/assignments/"):
                assignment_id = unquote(self.path.rsplit("/", 1)[-1])
                assignment = next((entry for entry in ASSIGNMENTS if entry["assignment_id"] == assignment_id), None)
                if not assignment:
                    return self.send_json(404, {"error": "assignment_not_found"})
                return self.send_json(200, {"assignment": assignment, "events": [], "attempts": [],
                    "verifications": [], "diagnostic_ref": ("docs/components/STATUS_DASHBOARD_COOKBOOK.md"
                    if assignment_id == "fixture-linked" else "javascript:alert(1)")})
            return self.send_json(404, {"error": "not_found"})

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0)); port = reservation.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0)); driver_port = reservation.getsockname()[1]
    driver = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(driver_port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session_id = None

    def webdriver(method, path, payload=None):
        raw = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{driver_port}{path}", data=raw, method=method,
                                         headers={"Content-Type": "application/json"} if raw is not None else {})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"webdriver_http_{error.code}") from None

    def js(source):
        return webdriver("POST", f"/session/{session_id}/execute/sync", {"script": source, "args": []})["value"]

    def wait_js(source):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            value = js("return (" + source + ");")
            if value:
                return value
            time.sleep(0.2)
        raise RuntimeError("browser_condition_timeout:" + json.dumps({"condition": source,
            "summary": js("return document.querySelector('#worker-inventory-summary')?.textContent"),
            "worker_requests": [entry for entry in requests if "/api/v1/workers" in entry["path"]]}))

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
        session_id = webdriver("POST", "/session", {"capabilities": {"alwaysMatch": {
            "browserName": "firefox", "moz:firefoxOptions": {"args": ["-headless"]}}}})["value"]["sessionId"]
        webdriver("POST", f"/session/{session_id}/window/rect", {"x": 0, "y": 0, "width": 1280, "height": 850})
        webdriver("POST", f"/session/{session_id}/url", {"url": f"http://127.0.0.1:{port}/"})
        js("window.__rvBrowserErrors=[];addEventListener('error',e=>window.__rvBrowserErrors.push(String(e.message||'error'))) ")
        wait_js("document.querySelector('#workspace') && !document.querySelector('#workspace').hidden")
        js("document.querySelector('[data-view=assignments]').click()")
        wait_js("document.querySelector('#assignment-list [data-assignment=fixture-linked]')")
        js("document.querySelector('#assignment-list [data-assignment=fixture-linked]').click()")
        detail = wait_js("document.querySelector('#assignment-detail').textContent.includes('rv:test:assignment:inspect')")
        first = js("return {text:document.querySelector('#assignment-detail').innerText,href:document.querySelector('#assignment-detail a')?.getAttribute('href')}")
        screenshot = base64.b64decode(webdriver("GET", f"/session/{session_id}/screenshot")["value"])
        js("document.querySelector('#assignment-list [data-assignment=fixture-unlinked]').click()")
        wait_js("document.querySelector('#assignment-detail').textContent.includes('No graph ID recorded')")
        second = js("return {text:document.querySelector('#assignment-detail').innerText,unsafeLinks:[...document.querySelectorAll('#assignment-detail a')].filter(a=>a.protocol==='javascript:').length}")
        js("document.querySelector('[data-view=overview]').click()")
        wait_js("document.querySelector('#worker-inventory-summary').textContent.includes('registered')")
        guidance = js("return document.querySelector('#overview-guidance').textContent")
        first_page = js("return {summary:document.querySelector('#worker-inventory-summary').textContent,rows:document.querySelector('#worker-list').innerText,pagerHidden:document.querySelector('#more-workers').hidden}")
        js("document.querySelector('#more-workers').click()")
        wait_js("document.querySelector('#worker-inventory-summary').textContent.includes('all records observed')")
        inventory = js("return {summary:document.querySelector('#worker-inventory-summary').textContent,rows:document.querySelector('#worker-list').innerText,pageNote:document.querySelector('#worker-page-note').textContent,pagerHidden:document.querySelector('#more-workers').hidden}")
        webdriver("POST", f"/session/{session_id}/window/rect", {"x": 0, "y": 0, "width": 390, "height": 844})
        mobile = js("return {grid:getComputedStyle(document.querySelector('.worker-row')).gridTemplateColumns,overflow:document.querySelector('.worker-row').scrollWidth>document.querySelector('.worker-row').clientWidth}")
        screenshot = base64.b64decode(webdriver("GET", f"/session/{session_id}/screenshot")["value"])
        webdriver("POST", f"/session/{session_id}/window/rect", {"x": 0, "y": 0, "width": 1280, "height": 850})
        js("document.querySelector('[data-view=activity]').click()")
        wait_js("document.querySelector('#event-list').textContent.includes('seq 3')")
        initial_event_page = js("return {rows:[...document.querySelectorAll('#event-list .event-ids span:first-child')].map(node=>node.textContent),olderHidden:document.querySelector('#more-events').hidden,newerHidden:document.querySelector('#newer-events').hidden}")
        js("document.querySelector('#more-events').click()")
        wait_js("document.querySelector('#event-list').textContent.includes('seq 1')")
        older_event_page = js("return [...document.querySelectorAll('#event-list .event-ids span:first-child')].map(node=>node.textContent)")
        js("document.querySelector('#newer-events').click()")
        wait_js("document.querySelector('#event-list').textContent.includes('seq 4')")
        activity_screenshot = base64.b64decode(webdriver("GET", f"/session/{session_id}/screenshot")["value"])
        event_paging = js("return {sequences:[...document.querySelectorAll('#event-list .event-ids span:first-child')].map(node=>node.textContent),olderHidden:document.querySelector('#more-events').hidden,newerHidden:document.querySelector('#newer-events').hidden}")
        errors = js("return window.__rvBrowserErrors")
        protected_requests = [r for r in requests if r["path"].startswith("/api/v1/")]
        report = {"browser": subprocess.check_output(["firefox", "--version"], text=True).strip(),
                  "mode": "isolated_synthetic_account_cookie_fixture", "first_assignment": first,
                  "unlinked_assignment": second, "first_worker_page": first_page,
                  "worker_inventory": inventory, "mobile_worker_row": mobile,
                  "overview_guidance": guidance,
                  "initial_event_page": initial_event_page, "older_event_page": older_event_page,
                  "activity_paging": event_paging,
                  "api_requests": protected_requests, "browser_errors": errors,
                  "screenshot_bytes": len(screenshot), "checks": {}}
        report["checks"] = {
            "graph_and_node_ids_rendered": "rv:test:assignment:inspect" in first["text"],
            "safe_documentation_link": first["href"] == "/docs/components/STATUS_DASHBOARD_COOKBOOK.md",
            "missing_identity_is_explicit": "No process node ID recorded" in second["text"],
            "unsafe_diagnostic_not_linked": second["unsafeLinks"] == 0,
            "inactive_registration_visible": "Registered · inactive" in inventory["rows"],
            "heartbeat_states_distinct": all(value in inventory["rows"].lower() for value in ["heartbeat healthy", "heartbeat stale", "heartbeat unknown"]),
            "loaded_inventory_counts_reconcile": "4 registered · 2 active · 1 inactive · 1 registration unknown" in inventory["summary"],
            "pagination_boundary_is_truthful": "more records available" in first_page["summary"] and inventory["pagerHidden"],
            "mobile_worker_row_fits": not mobile["overflow"],
            "overview_health_guidance_present": all(term in guidance for term in ["last observed institution event sequence", "separate heartbeat signals", "separate from chat availability"]),
            "older_event_page_prepended": older_event_page == ["seq 1", "seq 2", "seq 3"],
            "newer_event_page_appended_without_duplicates": event_paging["sequences"] == ["seq 1", "seq 2", "seq 3", "seq 4"],
            "activity_page_controls_match_cursors": not initial_event_page["olderHidden"] and not initial_event_page["newerHidden"] and event_paging["olderHidden"] and not event_paging["newerHidden"],
            "requests_use_account_cookie": bool(protected_requests) and all(r["cookie_authenticated"] for r in protected_requests),
            "no_bearer_authorization": all(not r["authorization_present"] for r in protected_requests),
            "no_browser_errors": not errors,
        }
        report["failed_checks"] = [name for name, passed in report["checks"].items() if not passed]
        (args.output / "worker-inventory.png").write_bytes(screenshot)
        (args.output / "activity-pagination.png").write_bytes(activity_screenshot)
        (args.output / "browser-acceptance.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, sort_keys=True))
        if report["failed_checks"]:
            raise RuntimeError("dashboard_browser_failed:" + ",".join(report["failed_checks"]))
    finally:
        if session_id:
            try: webdriver("DELETE", f"/session/{session_id}")
            except Exception: pass
        driver.terminate()
        try: driver.wait(timeout=5)
        except subprocess.TimeoutExpired: driver.kill(); driver.wait(timeout=5)
        server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == "__main__":
    main()
