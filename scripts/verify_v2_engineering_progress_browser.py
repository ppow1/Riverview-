#!/usr/bin/env python3
# Riverview~ Controlled Script
# File: scripts/verify_v2_engineering_progress_browser.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.1
# Changed: 2026-10-26 UTC | RV-ISSUE268-WEBSITE-ACCEPTANCE | Align the browser regression fixture with deployed resident navigation and summary APIs.
# Purpose: Verify Engineering Progress placement, sidebar transitions, and preserved chat state
# Execution Model: Isolated HTTPS fixture server and headless Firefox WebDriver
# Observability: Sanitized JSON result, screenshot evidence, and bounded API concurrency counts
# Dependencies: Python 3.10+, OpenSSL, Firefox, geckodriver
# Authority: Synthetic fixture only; no production endpoint, credential, or database access
# Tests: python3 scripts/verify_v2_engineering_progress_browser.py
# History: Git and .riverview-backups/manifest.jsonl
"""Browser acceptance for the V2 Engineering Progress responsive placement."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/evidence/issue253"
CONVERSATION = "conversation:fixture-253"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FixtureState:
    def __init__(self):
        self.lock = threading.Lock()
        self.objective_gets = 0
        self.objective_active = 0
        self.objective_max_active = 0
        self.cancel_posts = 0
        self.cancelled = {}
        self.last_reason = None
        self.last_objective_id = None
        self.last_unmatched_path = None
        self.settings = {"schema_version": "rv.notification_settings.v1", "status": "available",
            "level": "all", "quiet_hours": {"enabled": False, "start": "22:00", "end": "07:00", "timezone": "UTC"},
            "critical_policy": {"deliver_during_paused": True, "deliver_during_quiet_hours": True},
            "updated_at": "2026-10-24T00:00:00+00:00"}
        self.settings_gets = 0
        self.settings_puts = 0

    def snapshot(self):
        with self.lock:
            return {"objective_gets": self.objective_gets,
                    "objective_active": self.objective_active,
                    "objective_max_active": self.objective_max_active,
                    "cancel_posts": self.cancel_posts,
                    "cancelled": dict(self.cancelled),
                    "settings": dict(self.settings), "settings_gets": self.settings_gets,
                    "settings_puts": self.settings_puts,
                    "last_objective_id": self.last_objective_id,
                    "last_unmatched_path": self.last_unmatched_path}


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    state = FixtureState()
    objectives = [
        {"objective_id": "objective:fixture-grounded", "status": "GROUNDED",
         "lifecycle_status": "GROUNDED", "lifecycle_stage": "ready_for_work_order",
         "assignment_id": None, "assignment_state": None,
         "latest_event": {"event_type": "objective.grounded", "occurred_at": "2026-10-23T17:00:00Z"},
         "cancellation": None},
        {"objective_id": "objective:fixture-queued", "status": "WORK_ORDER_CREATED",
         "lifecycle_status": "WORK_ORDER_CREATED", "lifecycle_stage": "work_order_created",
         "assignment_id": "assignment:fixture-queued", "assignment_state": "ready",
         "latest_event": {"event_type": "assignment.queued", "occurred_at": "2026-10-23T17:01:00Z"},
         "cancellation": None},
        {"objective_id": "objective:fixture-command", "status": "WORK_ORDER_CREATED",
         "lifecycle_status": "WORK_ORDER_CREATED", "lifecycle_stage": "work_order_created",
         "assignment_id": "assignment:fixture-command", "assignment_state": "queued",
         "latest_event": {"event_type": "assignment.queued", "occurred_at": "2026-10-23T17:02:00Z"},
         "cancellation": None},
        {"objective_id": "objective:fixture-running", "status": "WORK_ORDER_CREATED",
         "lifecycle_status": "WORK_ORDER_CREATED", "lifecycle_stage": "engineering_executing",
         "assignment_id": "assignment:fixture-running", "assignment_state": "running",
         "latest_event": {"event_type": "assignment.started", "occurred_at": "2026-10-23T17:03:00Z"},
         "cancellation": None},
    ]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def send_json(self, code, payload):
            data = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path == "/__status":
                self.send_json(200, state.snapshot()); return
            if path == "/v2/" or path == "/v2/index.html":
                body = (ROOT / "website/v2/deployed/index.html").read_bytes()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
            if path.startswith("/v2/assets/"):
                relative = path.removeprefix("/v2/")
                asset = (ROOT / "website/v2/deployed" / relative).resolve()
                base = (ROOT / "website/v2/deployed").resolve()
                if base not in asset.parents or not asset.is_file():
                    self.send_error(404); return
                content_type = "text/javascript" if asset.suffix == ".js" else "text/css" if asset.suffix == ".css" else "image/svg+xml" if asset.suffix == ".svg" else "application/octet-stream"
                body = asset.read_bytes(); self.send_response(200); self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
            if path == "/api/v1/auth/session":
                self.send_json(200, {"identity": {"account_id": "fixture-steward", "roles": ["steward"]}}); return
            if path == "/api/v1/status":
                self.send_json(200, {"schema_version":"rv.dashboard.status.v1",
                    "projection_status":"unknown", "freshness":"unknown",
                    "observed_at":"2026-10-26T00:00:00Z",
                    "workers":{"status":"unknown","active_workers":None,
                        "healthy_workers":None,"stale_workers":None,"unknown_workers":None},
                    "grace_execution":{"status":"unknown"},"cme":{"status":"unknown"}}); return
            if path == "/api/v1/resources/telemetry":
                self.send_json(200, {"schema_version":"rv.dashboard.resource-telemetry.v1",
                    "status":"not_initialized", "observed_at":None, "hosts":[]}); return
            if path == "/api/v1/notification-settings":
                with state.lock:
                    state.settings_gets += 1
                    self.send_json(200, dict(state.settings))
                return
            if path == "/api/v1/resident/conversations":
                self.send_json(200, {"status": "available", "items": [{"conversation_id": CONVERSATION}]}); return
            if path == f"/api/v1/resident/conversations/{CONVERSATION}":
                self.send_json(200, {"conversation_id": CONVERSATION, "events": []}); return
            if path.startswith("/api/v1/objectives"):
                tracked_progress = "conversation_id" in parse_qs(urlsplit(self.path).query)
                if tracked_progress:
                    with state.lock:
                        state.objective_gets += 1
                        state.objective_active += 1
                        state.objective_max_active = max(state.objective_max_active, state.objective_active)
                try:
                    if tracked_progress: time.sleep(0.8)
                    items = [dict(item) for item in objectives]
                    for item in items:
                        if item["objective_id"] in state.cancelled:
                            item["status"] = item["lifecycle_status"] = "CANCELLED"
                            item["cancellation"] = {"reason": state.cancelled[item["objective_id"]],
                                "cancelled_at": "2026-10-23T17:02:00Z", "actor_id": "steward:fixture"}
                    self.send_json(200, {"schema_version": "rv.dashboard.objective_progress.v1",
                        "status": "available", "observed_at": "2026-10-23T17:02:01Z", "items": items})
                finally:
                    if tracked_progress:
                        with state.lock: state.objective_active -= 1
                return
            with state.lock: state.last_unmatched_path = path
            self.send_json(404, {"error": "fixture_not_found"})

        def do_POST(self):
            path = unquote(urlsplit(self.path).path)
            length = min(int(self.headers.get("Content-Length", "0")), 16384)
            body = self.rfile.read(length) if length else b"{}"
            if path == "/api/v1/resident/conversation-session":
                self.send_json(200, {"status": "available"}); return
            if path.startswith("/api/v1/objectives/") and path.endswith("/cancel"):
                try: payload = json.loads(body)
                except json.JSONDecodeError: payload = {}
                if not isinstance(payload.get("reason"), str) or not payload["reason"].strip():
                    self.send_json(400, {"error": "reason_required"}); return
                with state.lock:
                    state.cancel_posts += 1
                    state.last_reason = payload["reason"]
                    state.last_objective_id = path.split("/")[-2]
                    state.cancelled[state.last_objective_id] = payload["reason"]
                self.send_json(200, {"objective_id": path.split("/")[-2], "status": "CANCELLED"}); return
            with state.lock: state.last_unmatched_path = path
            self.send_json(404, {"error": "fixture_not_found"})

        def do_PUT(self):
            path = unquote(urlsplit(self.path).path)
            length = min(int(self.headers.get("Content-Length", "0")), 4096)
            try: payload = json.loads(self.rfile.read(length))
            except json.JSONDecodeError: payload = {}
            if path == "/api/v1/notification-settings":
                with state.lock:
                    state.settings_puts += 1
                    state.settings = {**state.settings, **payload,
                        "updated_at": "2026-10-24T00:01:00+00:00"}
                    result = dict(state.settings)
                self.send_json(200, result); return
            with state.lock: state.last_unmatched_path = path
            self.send_json(404, {"error": "fixture_not_found"})

    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    with tempfile.TemporaryDirectory(prefix="rv253-browser-") as tmp:
        key, cert = Path(tmp) / "key.pem", Path(tmp) / "cert.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(cert), "-days", "1", "-subj", "/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"], check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        driver_port = free_port()
        gecko = shutil.which("geckodriver") or ("/snap/bin/geckodriver" if Path("/snap/bin/geckodriver").exists() else None)
        if not gecko or not shutil.which("firefox"):
            raise RuntimeError("Firefox and geckodriver are required for browser acceptance")
        driver = subprocess.Popen([gecko, "--host", "127.0.0.1", "--port", str(driver_port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        session = None

        def wd(method, path, payload=None):
            data = json.dumps(payload).encode() if payload is not None else None
            req = Request(f"http://127.0.0.1:{driver_port}{path}", data=data, method=method,
                headers={"Content-Type": "application/json"} if data else {})
            try:
                with urlopen(req, timeout=30) as response: return json.loads(response.read())
            except HTTPError as exc: raise RuntimeError(f"webdriver_http_{exc.code}") from None

        def js(script, args=None):
            return wd("POST", f"/session/{session}/execute/sync", {"script": script, "args": args or []})["value"]

        def wait_for(expr, timeout=20):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                value = js("return (" + expr + ");")
                if value: return value
                time.sleep(0.1)
            detail = js("return {state:document.getElementById('engineering-progress-state')?.textContent,error:document.getElementById('grace-chat-error')?.textContent,root:document.getElementById('grace-chat-root')?.dataset.state,ids:[...document.querySelectorAll('#engineering-progress-list article')].map(x=>x.dataset.objectiveId)}")
            raise RuntimeError("browser_condition_timeout:" + json.dumps(
                {"browser": detail, "fixture": state.snapshot()}, sort_keys=True))

        try:
            for _ in range(100):
                if driver.poll() is not None: raise RuntimeError("geckodriver_stopped")
                try: wd("GET", "/status"); break
                except Exception: time.sleep(0.1)
            else: raise RuntimeError("geckodriver_start_timeout")
            caps = {"alwaysMatch": {"browserName": "firefox", "acceptInsecureCerts": True,
                "moz:firefoxOptions": {"args": ["-headless"]}}}
            session = wd("POST", "/session", {"capabilities": caps})["value"]["sessionId"]
            wd("POST", f"/session/{session}/window/rect", {"x": 0, "y": 0, "width": 1360, "height": 1000})
            wd("POST", f"/session/{session}/url", {"url": f"https://localhost:{port}/v2/"})
            js("window.__errors=[]; addEventListener('error',e=>window.__errors.push(String(e.message||'error'))); addEventListener('unhandledrejection',()=>window.__errors.push('unhandled_rejection'))")
            js("document.querySelector('[data-view=\"residents\"]').click(); document.querySelector('[data-resident-id=\"grace-preview\"]').click()")
            wait_for("document.getElementById('engineering-progress-panel').parentElement.id==='right-sidebar' && !document.getElementById('engineering-progress-panel').hidden")
            wait_for("document.querySelectorAll('#engineering-progress-list article').length===4")
            initial = js("return {parent:document.getElementById('engineering-progress-panel').parentElement.id, visible:!document.getElementById('engineering-progress-panel').hidden, fallbackHidden:document.getElementById('engineering-progress-fallback').hidden, cards:document.querySelectorAll('#engineering-progress-list article').length, composerBefore:document.getElementById('grace-message').value}")
            js("const box=document.getElementById('grace-message');box.value='draft stays through sidebar changes';box.focus();box.setSelectionRange(5,14);const log=document.getElementById('grace-chat-history');for(const [k,v] of Object.entries({height:'160px',maxHeight:'160px',minHeight:'160px',flex:'none',overflowY:'auto'}))log.style.setProperty(k.replace(/[A-Z]/g,m=>'-'+m.toLowerCase()),v,'important');const filler=document.createElement('div');filler.style.cssText='flex:0 0 1400px;height:1400px';filler.textContent='Synthetic scroll fixture';log.append(filler);log.scrollTop=17;window.__panel=document.getElementById('engineering-progress-panel');window.scrollTo(0,40)")
            # Expanded -> compact -> hidden -> restore; the same panel must move only to the fallback.
            states = []
            for _ in range(2):
                js("document.getElementById('right-state').click()")
                states.append(js("return document.querySelector('.app-shell').dataset.rightState"))
                wait_for("document.getElementById('engineering-progress-panel').parentElement.id==='engineering-progress-fallback'")
                js("requestAnimationFrame(()=>{})")
                preserved = js("const box=document.getElementById('grace-message'),log=document.getElementById('grace-chat-history');return {samePanel:window.__panel===document.getElementById('engineering-progress-panel'),draft:box.value,focused:document.activeElement===box,selection:[box.selectionStart,box.selectionEnd],chatScroll:log.scrollTop,chatScrollHeight:log.scrollHeight,chatClientHeight:log.clientHeight,windowScroll:window.scrollY,afterComposer:document.getElementById('engineering-progress-fallback').previousElementSibling.id}")
                if not preserved["samePanel"] or preserved["draft"] != "draft stays through sidebar changes" or not preserved["focused"] or preserved["selection"] != [5,14] or preserved["chatScroll"] != 17 or preserved["windowScroll"] != 40 or preserved["afterComposer"] != "grace-chat-root":
                    raise RuntimeError("sidebar_transition_did_not_preserve_chat_state:" + json.dumps(preserved, sort_keys=True))
            js("document.getElementById('right-restore').click()")
            wait_for("document.getElementById('engineering-progress-panel').parentElement.id==='right-sidebar'")
            restored_parent = js("return document.getElementById('engineering-progress-panel').parentElement.id")
            # Compact then resize to a phone viewport; the panel remains after the composer.
            js("document.getElementById('right-state').click()")
            wd("POST", f"/session/{session}/window/rect", {"x": 0, "y": 0, "width": 390, "height": 844})
            wait_for("innerWidth<=760 && document.getElementById('engineering-progress-panel').parentElement.id==='engineering-progress-fallback'")
            mobile = js("return {width:innerWidth,parent:document.getElementById('engineering-progress-panel').parentElement.id,afterComposer:document.getElementById('engineering-progress-fallback').previousElementSibling.id,chatComposerInside:document.getElementById('grace-chat-root').contains(document.getElementById('grace-message')),samePanel:window.__panel===document.getElementById('engineering-progress-panel')}")
            if mobile["afterComposer"] != "grace-chat-root" or not mobile["chatComposerInside"] or not mobile["samePanel"]:
                raise RuntimeError("mobile_progress_placement_invalid")
            js("document.getElementById('engineering-progress-panel').scrollIntoView({block:'start'})")
            time.sleep(0.4)
            mobile_png = base64.b64decode(wd("GET", f"/session/{session}/screenshot")["value"])
            (ARTIFACTS / "engineering-progress-mobile.png").write_bytes(mobile_png)
            # Wait for an actual five-second refresh and cause the layout move while the request is in flight.
            wd("POST", f"/session/{session}/window/rect", {"x": 0, "y": 0, "width": 1360, "height": 1000})
            js("document.getElementById('right-restore').click();window.scrollTo(0,0)")
            wait_for("innerWidth>760 && document.getElementById('engineering-progress-panel').parentElement.id==='right-sidebar'")
            desktop_png = base64.b64decode(wd("GET", f"/session/{session}/screenshot")["value"])
            (ARTIFACTS / "engineering-progress-desktop.png").write_bytes(desktop_png)
            before = state.snapshot()["objective_gets"]
            deadline = time.monotonic() + 12
            during_request_transition = False
            while time.monotonic() < deadline:
                snapshot = state.snapshot()
                if snapshot["objective_gets"] > before and snapshot["objective_active"] > 0:
                    js("document.getElementById('right-state').click()")
                    wait_for("document.getElementById('engineering-progress-panel').parentElement.id==='engineering-progress-fallback'")
                    during_request_transition = True
                    break
                time.sleep(0.05)
            if not during_request_transition:
                raise RuntimeError("five_second_progress_poll_not_observed")
            # Exercise eligible cancel UI against disposable fixture and verify refreshed authoritative result.
            js("document.getElementById('right-restore').click()")
            wait_for("document.getElementById('engineering-progress-panel').parentElement.id==='right-sidebar'")
            js("document.querySelector('[data-cancel-objective=\"objective:fixture-queued\"]').click()")
            js("document.getElementById('engineering-cancel-reason').value='fixture cancellation acceptance';document.getElementById('engineering-cancel-form').requestSubmit()")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if state.snapshot()["cancel_posts"] and js("return document.querySelector('#engineering-progress-list').textContent.includes('fixture cancellation acceptance')"):
                    break
                time.sleep(0.1)
            else: raise RuntimeError("fixture_cancel_refresh_not_observed")
            # The Objectives table shows the exact objective action only for eligible Steward records.
            js("document.querySelector('[data-view=\"work\"]').click()")
            wait_for("document.querySelector('#work-objectives-body [data-open-objective-cancellation=\"objective:fixture-grounded\"]')")
            if js("return Boolean(document.querySelector('#work-objectives-body [data-open-objective-cancellation=\"objective:fixture-running\"]'))"):
                raise RuntimeError("running_objective_exposed_cancel_action")
            js("document.querySelector('#work-objectives-body [data-open-objective-cancellation=\"objective:fixture-grounded\"]').click()")
            wait_for("document.getElementById('engineering-cancel-dialog').open && document.getElementById('engineering-cancel-target').textContent.includes('objective:fixture-grounded')")
            js("document.getElementById('engineering-cancel-reason').value='work table cancellation';document.getElementById('engineering-cancel-form').requestSubmit()")
            wait_for("document.querySelector('#work-objectives-body tr[data-objective-id=\"objective:fixture-grounded\"]')?.textContent.includes('CANCELLED') && !document.querySelector('#work-objectives-body [data-open-objective-cancellation=\"objective:fixture-grounded\"]')")
            if state.snapshot()["last_objective_id"] != "objective:fixture-grounded":
                raise RuntimeError("work_table_cancel_used_wrong_objective")
            # Conversational commands resolve exact assignment IDs, show confirmation, then use the same API.
            # Grace is selected from the deployed overview cards. The current
            # Residents page is a live authority directory and intentionally
            # does not render the old synthetic ``grace-preview`` fixture.
            js("document.querySelector('[data-view=\"overview\"]').click();document.querySelector('[data-resident-id=\"grace-preview\"]').click()")
            wait_for("document.getElementById('grace-chat-connected') && !document.getElementById('grace-chat-connected').hidden")
            js("const box=document.getElementById('grace-message');box.value='Grace, cancel work order assignment:fixture-command';document.getElementById('grace-chat-form').requestSubmit()")
            wait_for("document.getElementById('engineering-cancel-dialog').open && document.getElementById('engineering-cancel-target').textContent.includes('objective:fixture-command')")
            js("document.getElementById('engineering-cancel-reason').value='chat cancellation';document.getElementById('engineering-cancel-form').requestSubmit()")
            wait_for("document.querySelector('#engineering-progress-list').textContent.includes('chat cancellation')")
            if state.snapshot()["last_objective_id"] != "objective:fixture-command":
                raise RuntimeError("conversational_cancel_used_wrong_objective")
            cancel_count = state.snapshot()["cancel_posts"]
            js("const box=document.getElementById('grace-message');box.value='Grace, cancel the stalled engineering objective';document.getElementById('grace-chat-form').requestSubmit()")
            wait_for("document.getElementById('grace-chat-action-status').textContent.includes('no stalled flag')")
            if state.snapshot()["cancel_posts"] != cancel_count:
                raise RuntimeError("ambiguous_stalled_command_cancelled_without_clarification")
            # V2 settings page writes the persistent API contract; Grace chat uses that same API.
            js("document.querySelector('[data-view=\\\"notification-settings\\\"]').click()")
            wait_for("!document.getElementById('notification-settings-workspace').hidden && document.getElementById('notification-settings-status').textContent.includes('Saved on server')")
            js("document.getElementById('notification-settings-level').value='critical_only';document.getElementById('notification-quiet-enabled').checked=true;document.getElementById('notification-quiet-start').value='21:30';document.getElementById('notification-quiet-end').value='06:30';document.getElementById('notification-quiet-timezone').value='America/New_York';document.getElementById('notification-settings-form').requestSubmit()")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and state.snapshot()["settings_puts"] < 1: time.sleep(0.05)
            saved_settings = state.snapshot()["settings"]
            if saved_settings["level"] != "critical_only" or not saved_settings["quiet_hours"]["enabled"] or saved_settings["quiet_hours"]["timezone"] != "America/New_York":
                raise RuntimeError("v2_notification_settings_form_did_not_persist")
            js("document.querySelector('[data-view=\\\"overview\\\"]').click();document.querySelector('[data-resident-id=\\\"grace-preview\\\"]').click();const box=document.getElementById('grace-message');box.value='Grace, show notification settings';document.getElementById('grace-chat-form').requestSubmit()")
            wait_for("document.getElementById('grace-chat-action-status').textContent.includes('critical only')")
            js("window.confirm=()=>true;const box=document.getElementById('grace-message');box.value='Grace, set notification level to Important';document.getElementById('grace-chat-form').requestSubmit()")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and state.snapshot()["settings"]["level"] != "important": time.sleep(0.05)
            final_settings = state.snapshot()["settings"]
            if final_settings["level"] != "important" or state.snapshot()["settings_puts"] != 2:
                raise RuntimeError("grace_notification_settings_update_failed")
            final_state = state.snapshot()
            browser_errors = js("return window.__errors")
            report = {"result": "PASS", "browser": subprocess.check_output(["firefox", "--version"], text=True).strip(),
                "data_classification": "synthetic_browser_fixture_only", "initial_desktop": initial,
                "sidebar_states": states, "restored_parent": restored_parent, "mobile": mobile,
                "five_second_refresh": {"requests_observed": final_state["objective_gets"],
                    "max_concurrent_requests": final_state["objective_max_active"],
                    "transition_during_inflight_request": during_request_transition},
                "fixture_cancel": {"post_count": final_state["cancel_posts"],
                    "cancelled_objectives": sorted(final_state["cancelled"]),
                    "engineering_progress_work_order_cancelled": "objective:fixture-queued" in final_state["cancelled"],
                    "engineering_progress_refresh_reflected_reason": final_state["cancelled"].get("objective:fixture-queued") == "fixture cancellation acceptance",
                    "work_table_correct_objective": "objective:fixture-grounded" in final_state["cancelled"],
                    "grace_command_exact_work_order": "objective:fixture-command" in final_state["cancelled"],
                    "stalled_command_requested_clarification": True},
                "notification_settings": {"page_read": final_state["settings_gets"] >= 2,
                    "page_write": final_state["settings_puts"] >= 1,
                    "grace_read_and_write": final_state["settings_gets"] >= 3 and final_state["settings_puts"] == 2,
                    "final_level": final_state["settings"]["level"],
                    "quiet_hours_saved": final_state["settings"]["quiet_hours"]["enabled"]},
                "browser_errors": browser_errors,
                "screenshots": [str(ARTIFACTS / "engineering-progress-desktop.png"),
                    str(ARTIFACTS / "engineering-progress-mobile.png")]}
            print(json.dumps(report, sort_keys=True))
            if final_state["objective_max_active"] != 1 or browser_errors:
                raise RuntimeError("browser_acceptance_failed")
        finally:
            if session:
                try: wd("DELETE", f"/session/{session}")
                except Exception: pass
            driver.terminate()
            try: driver.wait(timeout=5)
            except subprocess.TimeoutExpired: driver.kill(); driver.wait(timeout=5)
        server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == "__main__":
    main()
