# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_worker_inventory_browser.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.13
# Purpose: Verify worker registration, heartbeat states and pagination in Firefox
# Execution Model: Isolated loopback fixture; owns only its HTTP and geckodriver processes
# Observability: Redacted JSON report and screenshot; synthetic account and assignment data
# Dependencies: Python 3.10+, Firefox, geckodriver
# Authority: No production access; authenticated fixture reads only
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL008 | Add isolated worker inventory browser verification
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL012 | Verify event provenance and diagnostic boundary rendering
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL016 | Verify documentation tab reuse and return to dashboard
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL010/015/020/023/024 | Verify readiness guidance, chat controls, menu states and milestone copy
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL019 | Verify long conversation and composer visibility at desktop and mobile sizes
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL036 | Verify accessible collapse/expand, persistent rail state, health and snapshot controls
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL003 | Verify assignment titles resolve only from exact canonical graph/node identity
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
           "recorded_at": f"2026-10-15T00:00:0{seq}Z", "assignment_id": "fixture-linked",
           "actor_id": "service:fixture.v1", "payload_schema": "rv.fixture_event.v1",
           "correlation_id": f"fixture-correlation-{seq}",
           "causation_id": "fixture-parent-event" if seq > 1 else None}
          for seq in range(1, 5)]
CHAT_EVENTS = []
for pair in range(1, 21):
    request_id = f"fixture-chat-request-{pair}"
    CHAT_EVENTS.extend([
        {"sequence": pair * 2 - 1, "request_id": request_id, "event_type": "user_message",
         "occurred_at": f"2026-10-15T00:{pair:02}:00Z", "body": (f"fixture prompt {pair} " + "long transcript text " * 18)},
        {"sequence": pair * 2, "request_id": request_id, "event_type": "assistant_message",
         "occurred_at": f"2026-10-15T00:{pair:02}:10Z", "body": (f"fixture response {pair} " + "long response text " * 18),
         "model_id": "fixture-model", "provider_ref": "fixture-provider"},
    ])


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
            if self.path.startswith("/docs/components/"):
                name = self.path.rsplit("/", 1)[-1]
                title = name.replace(".md", "")
                body = (f'<!doctype html><title>{title}</title><main><h1>{title}</h1>'
                        '<a id="doc-dashboard-link" href="/#activity" target="rv-dashboard-main">Riverview dashboard</a></main>')
                raw = body.encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
                return
            if not authenticated:
                return self.send_json(401, {"error": "authentication_required"})
            if self.path == "/api/v1/auth/session":
                return self.send_json(200, {"identity": {"email": "fixture@example.invalid", "roles": ["steward"]}})
            if self.path == "/api/v1/resident/conversations":
                return self.send_json(200, {"items": [{"conversation_id": "fixture-chat",
                    "created_at": "2026-10-15T00:00:00Z", "updated_at": "2026-10-15T00:20:10Z"}]})
            if self.path.startswith("/api/v1/resident/conversations/fixture-chat"):
                return self.send_json(200, {"conversation_id": "fixture-chat", "events": CHAT_EVENTS})
            if self.path == "/api/v1/status":
                return self.send_json(200, STATUS)
            if self.path.startswith("/api/v1/assignments?"):
                return self.send_json(200, {"status": "available", "items": ASSIGNMENTS, "next_cursor": None})
            if self.path.startswith("/api/v1/graphs/"):
                graph_id = unquote(self.path.rsplit("/", 1)[-1])
                if graph_id == "rv:test:assignment":
                    return self.send_json(200, {"graph": {"graph_id": graph_id, "nodes": [
                        {"id": "rv:test:assignment:inspect", "label": "Inspect delivery readiness"}]}})
                return self.send_json(404, {"error": "graph_not_found"})
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
                return self.send_json(200, {"status": "not_initialized", "items": []})
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

        def do_POST(self):
            authenticated = "rv_account_session=fixture-session" in self.headers.get("Cookie", "")
            requests.append({"path": self.path, "cookie_authenticated": authenticated,
                             "authorization_present": bool(self.headers.get("Authorization"))})
            if authenticated and self.path == "/api/v1/resident/conversation-session":
                return self.send_json(200, {"status": "connected"})
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
        wait_js("document.querySelector('#rail-health').textContent==='healthy'")
        rail_initial = js("return {collapsed:document.querySelector('.shell').classList.contains('rail-collapsed'),expanded:document.querySelector('#rail-toggle').getAttribute('aria-expanded'),names:[...document.querySelectorAll('.nav-item')].filter(button=>!button.hidden).every(button=>Boolean(button.getAttribute('aria-label')))}")
        js("document.querySelector('#rail-toggle').click()")
        wait_js("document.querySelector('.shell').classList.contains('rail-collapsed')")
        rail_compact = js("return {expanded:document.querySelector('#rail-toggle').getAttribute('aria-expanded'),label:document.querySelector('#rail-toggle').getAttribute('aria-label'),health:document.querySelector('#pulse-dot').getAttribute('aria-label'),healthVisible:document.querySelector('#pulse-dot').getClientRects().length>0,snapshotVisible:document.querySelector('#snapshot').getClientRects().length>0,snapshotLabel:document.querySelector('#snapshot').getAttribute('aria-label'),navLabelsHidden:[...document.querySelectorAll('.nav-item:not([hidden]) .nav-label')].every(label=>getComputedStyle(label).display==='none')}")
        js("document.querySelector('#rail-toggle').click()")
        wait_js("!document.querySelector('.shell').classList.contains('rail-collapsed')")
        rail_expanded = js("return {expanded:document.querySelector('#rail-toggle').getAttribute('aria-expanded'),label:document.querySelector('#rail-toggle').getAttribute('aria-label'),navLabelsVisible:[...document.querySelectorAll('.nav-item:not([hidden]) .nav-label')].every(label=>getComputedStyle(label).display!=='none')}")
        js("document.querySelector('[data-view=assignments]').click()")
        wait_js("document.querySelector('#assignment-list [data-assignment=fixture-linked]')")
        wait_js("document.querySelector('#assignment-list [data-assignment-title=fixture-linked]').textContent.includes('Inspect delivery readiness')")
        assignment_list_title = js("return {title:document.querySelector('#assignment-list [data-assignment-title=fixture-linked]').textContent,id:document.querySelector('#assignment-list [data-assignment=fixture-linked] .row-main').textContent}")
        js("document.querySelector('#assignment-list [data-assignment=fixture-linked]').click()")
        detail = wait_js("document.querySelector('#assignment-detail').textContent.includes('Inspect delivery readiness') && document.querySelector('#assignment-detail').textContent.includes('rv:test:assignment:inspect')")
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
        dashboard_handle = webdriver("GET", f"/session/{session_id}/window")["value"]
        js("document.querySelector('#event-list a').click()")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            handles = webdriver("GET", f"/session/{session_id}/window/handles")["value"]
            if len(handles) == 2: break
            time.sleep(0.2)
        docs_handle = next((handle for handle in handles if handle != dashboard_handle), None)
        webdriver("POST", f"/session/{session_id}/window", {"handle": docs_handle})
        first_docs_url = webdriver("GET", f"/session/{session_id}/url")["value"]
        js("document.querySelector('#doc-dashboard-link').click()")
        time.sleep(0.5)
        dashboard_url_after_return = None
        handles_after_return = webdriver("GET", f"/session/{session_id}/window/handles")["value"]
        webdriver("POST", f"/session/{session_id}/window", {"handle": dashboard_handle})
        dashboard_url_after_return = webdriver("GET", f"/session/{session_id}/url")["value"]
        js("document.querySelector('#view-activity .diagnostics a').click()")
        time.sleep(0.5)
        handles_after_second_doc = webdriver("GET", f"/session/{session_id}/window/handles")["value"]
        webdriver("POST", f"/session/{session_id}/window", {"handle": docs_handle})
        second_docs_url = webdriver("GET", f"/session/{session_id}/url")["value"]
        docs_navigation = {"dashboard_handle": dashboard_handle, "documentation_handle": docs_handle,
            "handles_after_first_doc": handles, "handles_after_dashboard_return": handles_after_return,
            "handles_after_second_doc": handles_after_second_doc, "first_docs_url": first_docs_url,
            "dashboard_url_after_return": dashboard_url_after_return, "second_docs_url": second_docs_url}
        webdriver("POST", f"/session/{session_id}/window", {"handle": dashboard_handle})
        js("document.querySelector('[data-view=objectives]').click()")
        wait_js("document.querySelector('#objective-state').textContent.includes('not initialized')")
        objective_guidance = js("return {status:document.querySelector('#objective-state').textContent,text:document.querySelector('#objective-readiness-guidance').textContent}")
        chat_guidance = js("return document.querySelector('#chat-controls-guidance').textContent")
        milestone_guidance = js("return document.querySelector('#overview-guidance').textContent")
        chat_actions = js("return [...document.querySelectorAll('.chat-more-menu button')].map(button=>({text:button.textContent,disabled:button.disabled}))")
        webdriver("POST", f"/session/{session_id}/window/rect", {"x": 0, "y": 0, "width": 390, "height": 844})
        if not js("return document.querySelector('.shell').classList.contains('rail-collapsed')"):
            js("document.querySelector('#rail-toggle').click()")
            wait_js("document.querySelector('.shell').classList.contains('rail-collapsed')")
        js("document.querySelector('[data-view=grace-chat]').click()")
        wait_js("document.querySelector('#chat-history').textContent.includes('fixture response 20')")
        js("document.querySelector('#chat-form').scrollIntoView({block:'end'})")
        chat_layout_mobile = js("const box=document.querySelector('#chat-history'),last=box.querySelector('.message-row:last-child'),composer=document.querySelector('#chat-form');const b=box.getBoundingClientRect(),l=last.getBoundingClientRect(),c=composer.getBoundingClientRect();return {messages:box.querySelectorAll('.message-row').length,scrollHeight:box.scrollHeight,clientHeight:box.clientHeight,scrollTop:box.scrollTop,lastMessage:last.innerText,boxBottom:b.bottom,lastBottom:l.bottom,composerTop:c.top,composerBottom:c.bottom,viewportHeight:innerHeight,documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,overflowing:[...document.querySelectorAll('body *')].map(e=>({tag:e.tagName,id:e.id,cls:String(e.className||''),right:Math.round(e.getBoundingClientRect().right),width:Math.round(e.getBoundingClientRect().width)})).filter(e=>e.right>innerWidth+1).slice(0,8)}")
        chat_screenshot = base64.b64decode(webdriver("GET", f"/session/{session_id}/screenshot")["value"])
        errors = js("return window.__rvBrowserErrors")
        protected_requests = [r for r in requests if r["path"].startswith("/api/v1/")]
        report = {"browser": subprocess.check_output(["firefox", "--version"], text=True).strip(),
                  "mode": "isolated_synthetic_account_cookie_fixture", "first_assignment": first,
                  "assignment_list_title": assignment_list_title,
                  "unlinked_assignment": second, "first_worker_page": first_page,
                  "worker_inventory": inventory, "mobile_worker_row": mobile,
                  "overview_guidance": guidance,
                  "initial_event_page": initial_event_page, "older_event_page": older_event_page,
                  "activity_paging": event_paging,
                  "documentation_navigation": docs_navigation,
                  "objective_readiness_guidance": objective_guidance,
                  "chat_control_guidance": chat_guidance,
                  "milestone_guidance": milestone_guidance,
                  "chat_menu_actions": chat_actions,
                  "chat_layout_mobile": chat_layout_mobile,
                  "rail_initial": rail_initial,
                  "rail_compact": rail_compact,
                  "rail_expanded": rail_expanded,
                  "api_requests": protected_requests, "browser_errors": errors,
                  "screenshot_bytes": len(screenshot), "checks": {}}
        report["checks"] = {
            "graph_and_node_ids_rendered": "rv:test:assignment:inspect" in first["text"],
            "safe_documentation_link": first["href"] == "/docs/components/STATUS_DASHBOARD_COOKBOOK.md",
            "missing_identity_is_explicit": "No process node ID recorded" in second["text"],
            "canonical_assignment_title_is_paired_with_stable_ids": "Inspect delivery readiness" in assignment_list_title["title"] and assignment_list_title["id"] == "fixture-linked" and "Inspect delivery readiness" in first["text"] and "rv:test:assignment:inspect" in first["text"],
            "unsafe_diagnostic_not_linked": second["unsafeLinks"] == 0,
            "inactive_registration_visible": "Registered · inactive" in inventory["rows"],
            "heartbeat_states_distinct": all(value in inventory["rows"].lower() for value in ["heartbeat healthy", "heartbeat stale", "heartbeat unknown"]),
            "loaded_inventory_counts_reconcile": "4 registered · 2 active · 1 inactive · 1 registration unknown" in inventory["summary"],
            "pagination_boundary_is_truthful": "more records available" in first_page["summary"] and inventory["pagerHidden"],
            "mobile_worker_row_fits": not mobile["overflow"],
            "overview_health_guidance_present": all(term in guidance for term in ["last observed institution event sequence", "separate heartbeat signals", "separate from chat availability", "browser cache bypass", "source observation time", "required ledger query succeeded", "current state could not be confirmed"]),
            "older_event_page_prepended": older_event_page == ["seq 1", "seq 2", "seq 3"],
            "newer_event_page_appended_without_duplicates": event_paging["sequences"] == ["seq 1", "seq 2", "seq 3", "seq 4"],
            "activity_page_controls_match_cursors": not initial_event_page["olderHidden"] and not initial_event_page["newerHidden"] and event_paging["olderHidden"] and not event_paging["newerHidden"],
            "event_cards_show_actor_schema_causation_and_assignment": all(term in js("return document.querySelector('#event-list').textContent") for term in ["Actor service:fixture.v1", "Payload schema rv.fixture_event.v1", "Caused by fixture-parent-event", "assignment fixture-linked"]),
            "event_cards_disclose_payload_and_diagnostic_boundary": "event-specific diagnostic reference are not included" in js("return document.querySelector('#event-list').textContent") and js("return [...document.querySelectorAll('#event-list a')].some(a => a.href.includes('STATUS_DASHBOARD_COOKBOOK.md'))"),
            "documentation_link_uses_reusable_named_tab": len(docs_navigation["handles_after_first_doc"]) == 2 and docs_navigation["first_docs_url"].endswith("STATUS_DASHBOARD_COOKBOOK.md"),
            "documentation_return_reuses_dashboard_window": len(docs_navigation["handles_after_dashboard_return"]) == 2 and docs_navigation["dashboard_url_after_return"].endswith("/#activity"),
            "second_document_reuses_documentation_tab": len(docs_navigation["handles_after_second_doc"]) == 2 and docs_navigation["second_docs_url"].endswith("RIVERVIEW_OPERATIONS_COOKBOOK.md"),
            "objective_not_initialized_guidance_names_safe_next_step": objective_guidance["status"].endswith("not initialized · 0 observed") and "does not apply migrations" in objective_guidance["text"] and "A responsive chat is separate" in objective_guidance["text"],
            "chat_controls_explain_session_history_and_newlines": all(term in chat_guidance for term in ["ends this browser's Grace session", "saved history remains", "reloads the current saved conversation", "Shift+Enter"]),
            "milestone_label_is_distinguished_from_release_acceptance": "DASHBOARD MILESTONE M3.1" in js("return document.querySelector('.topbar .eyebrow').textContent") and "roadmap progress, deployed release, and commissioning acceptance are tracked separately" in milestone_guidance,
            "chat_menu_marks_future_actions_unavailable": len(chat_actions) == 7 and all(item["disabled"] for item in chat_actions if any(term in item["text"] for term in ["future capability", "unavailable", "coming later"])),
            "chat_transcript_scrolls_and_last_message_is_visible": chat_layout_mobile["messages"] == 40 and chat_layout_mobile["scrollHeight"] > chat_layout_mobile["clientHeight"] and chat_layout_mobile["scrollTop"] >= chat_layout_mobile["scrollHeight"] - chat_layout_mobile["clientHeight"] - 2 and "fixture response 20" in chat_layout_mobile["lastMessage"] and chat_layout_mobile["lastBottom"] <= chat_layout_mobile["boxBottom"] + 1,
            "mobile_chat_composer_is_visible_without_horizontal_overflow": chat_layout_mobile["composerBottom"] <= chat_layout_mobile["viewportHeight"] + 1 and chat_layout_mobile["documentWidth"] <= chat_layout_mobile["viewportWidth"] and chat_layout_mobile["composerTop"] >= chat_layout_mobile["boxBottom"] - 1,
            "rail_collapses_with_explicit_accessible_state": rail_initial["expanded"] == "true" and rail_initial["names"] and rail_compact["expanded"] == "false" and rail_compact["label"] == "Expand navigation" and rail_compact["navLabelsHidden"],
            "compact_rail_retains_accessible_health_and_snapshot": rail_compact["health"] == "Source health: healthy" and rail_compact["healthVisible"] and rail_compact["snapshotVisible"] and rail_compact["snapshotLabel"] == "Download bounded diagnostic snapshot",
            "rail_expands_with_visible_labels": rail_expanded["expanded"] == "true" and rail_expanded["label"] == "Collapse navigation" and rail_expanded["navLabelsVisible"],
            "requests_use_account_cookie": bool(protected_requests) and all(r["cookie_authenticated"] for r in protected_requests),
            "no_bearer_authorization": all(not r["authorization_present"] for r in protected_requests),
            "no_browser_errors": not errors,
        }
        report["failed_checks"] = [name for name, passed in report["checks"].items() if not passed]
        (args.output / "worker-inventory.png").write_bytes(screenshot)
        (args.output / "activity-pagination.png").write_bytes(activity_screenshot)
        (args.output / "chat-layout-mobile.png").write_bytes(chat_screenshot)
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
