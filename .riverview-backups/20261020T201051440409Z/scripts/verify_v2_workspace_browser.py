#!/usr/bin/env python3
# Riverview~ Controlled Source
# File: scripts/verify_v2_workspace_browser.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.1
# Purpose: Exercise local V2 preview and measure navigation and responsive layout
# Execution Model: Request-driven acceptance utility; starts/stops only its own geckodriver
# Observability: Sanitized JSON stdout; no credentials or write operations
# Dependencies: Python 3.10+, Firefox, geckodriver, local V2 preview
# Inputs/Outputs: Loopback preview URL; navigation timings and viewport-fit metrics
# Authority: Browser-only interaction with local fixture preview; no API or writes
# Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Initial preview browser check
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: scripts/verify_v2_workspace_browser.py
# History: Git and revision/backup manifest
"""Verify shell navigation and viewport fit using a local headless Firefox."""
import argparse
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8877")
    args = parser.parse_args()
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]

    def request(method, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, method=method,
                                     headers={"Content-Type": "application/json"} if body else {})
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"webdriver_http_{exc.code}") from None

    def js(session, script, arguments=None):
        return request("POST", f"/session/{session}/execute/sync", {"script": script, "args": arguments or []})["value"]

    driver = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        for _ in range(100):
            if driver.poll() is not None:
                raise RuntimeError("geckodriver_stopped")
            try:
                request("GET", "/status")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(.1)
        else:
            raise RuntimeError("geckodriver_start_timeout")
        session = request("POST", "/session", {"capabilities": {"alwaysMatch": {"browserName": "firefox", "moz:firefoxOptions": {"args": ["-headless"]}}}})["value"]["sessionId"]
        request("POST", f"/session/{session}/url", {"url": args.base_url.rstrip("/") + "/"})
        errors = js(session, "window.__errors=[];addEventListener('error',e=>window.__errors.push(String(e.message||'error')));addEventListener('unhandledrejection',e=>window.__errors.push('rejection'))")
        samples = []
        for view in ("residents", "work", "resources", "knowledge", "overview") * 5:
            dt = js(session, "const b=document.querySelector('[data-view='+arguments[0]+']');const t=performance.now();b.click();return performance.now()-t", [view])
            samples.append(round(dt, 3))
        selected_before = js(session, "return document.querySelector('#selected-resident b').textContent")
        js(session, "document.querySelector('[data-resident-id=fixture-resident-02]').click()")
        selected_after = js(session, "return document.querySelector('#selected-resident b').textContent")
        js(session, "document.querySelector('[data-view=work]').click()")
        context_retained = js(session, "return document.querySelector('#selected-resident b').textContent")
        js(session, "document.querySelector('#conversation-toggle').click()")
        note_open = js(session, "return !document.querySelector('#conversation-note').hidden")
        desktop = js(session, "return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth}")
        request("POST", f"/session/{session}/window/rect", {"x": 0, "y": 0, "width": 390, "height": 844})
        mobile = js(session, "return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,navButton:getComputedStyle(document.querySelector('#mobile-menu')).display}")
        reloads = js(session, "return performance.timeOrigin")
        disabled = js(session, "return [...document.querySelectorAll('button:disabled')].length>=2")
        fixture_banner = js(session, "return document.querySelector('.preview-banner').innerText")
        report = {"browser": subprocess.check_output(["firefox", "--version"], text=True).strip(), "url": args.base_url,
                  "navigation_calls_ms": {"count": len(samples), "median": sorted(samples)[len(samples)//2], "max": max(samples)},
                  "resident_selection": {"before": selected_before, "selected": selected_after, "retained_after_view_switch": context_retained},
                  "conversation_context_expand": note_open, "desktop": desktop, "mobile": mobile,
                  "disabled_mutation_controls_present": disabled, "fixture_banner": fixture_banner,
                  "browser_errors": js(session, "return window.__errors"), "document_time_origin": reloads}
        print(json.dumps(report, sort_keys=True))
        if selected_after != "Resident fixture 02" or context_retained != selected_after or not note_open or desktop["overflow"] or mobile["overflow"] or mobile["navButton"] == "none" or not disabled or report["browser_errors"]:
            raise RuntimeError("v2_browser_check_failed")
    finally:
        if session:
            try:
                request("DELETE", f"/session/{session}")
            except Exception:
                pass
        driver.terminate()
        try:
            driver.wait(timeout=5)
        except subprocess.TimeoutExpired:
            driver.kill()
            driver.wait(timeout=5)


if __name__ == "__main__":
    main()
