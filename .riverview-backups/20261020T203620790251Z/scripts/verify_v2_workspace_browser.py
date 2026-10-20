#!/usr/bin/env python3
# Riverview~ Controlled Source
# File: scripts/verify_v2_workspace_browser.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.6
# Purpose: Exercise V2 theme, sidebars, tooltips, navigation, and responsive layout
# Execution Model: Request-driven acceptance utility; starts/stops only its own geckodriver
# Observability: Sanitized JSON stdout; no credentials or write operations
# Dependencies: Python 3.10+, Firefox, geckodriver, local V2 preview
# Inputs/Outputs: Loopback preview URL; navigation timings and viewport-fit metrics
# Authority: Browser-only interaction with local fixture preview; no API or writes
# Changed: 2026-10-20 UTC | RV-WEB-V2-SNAPSHOT-001 | Assert V2 snapshot is enabled and truthful about local fixture scope
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: scripts/verify_v2_workspace_browser.py
# History: Git and revision/backup manifest
"""Verify shell navigation and viewport fit using a local headless Firefox."""
import argparse
import getpass
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8877")
    parser.add_argument("--password-prompt", action="store_true", help="authenticate to LAN preview with a hidden prompt")
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
        authenticated = js(session, "return !!document.querySelector('#password')")
        if authenticated:
            if not args.password_prompt:
                raise RuntimeError("preview_authentication_required_use_password_prompt")
            password = getpass.getpass("V2 preview password (hidden): ")
            js(session, "document.querySelector('#password').value=arguments[0];document.querySelector('form').requestSubmit();return true", [password])
            password = ""
            for _ in range(50):
                if js(session, "return document.title === 'Riverview V2 Workspace Preview'"): break
                time.sleep(.1)
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
        theme = js(session, "const s=document.querySelector('#theme-select');s.value='dark';s.dispatchEvent(new Event('change'));const dark=document.documentElement.dataset.theme;s.value='light';s.dispatchEvent(new Event('change'));const light=document.documentElement.dataset.theme;const saved=localStorage.getItem('rv.v2.theme');s.value='system';s.dispatchEvent(new Event('change'));const systemEffective=document.documentElement.dataset.theme;const systemOS=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';s.value='dark';s.dispatchEvent(new Event('change'));return {dark,light,saved,systemEffective,systemOS,storedBeforeReload:localStorage.getItem('rv.v2.theme')}")
        request("POST", f"/session/{session}/refresh", {})
        for _ in range(50):
            ready = js(session, "return document.readyState === 'complete' && !!document.querySelector('#theme-select')")
            if ready: break
            time.sleep(.1)
        js(session, "window.__errors=[];addEventListener('error',e=>window.__errors.push(String(e.message||'error')));addEventListener('unhandledrejection',e=>window.__errors.push('rejection'))")
        theme["reload_restored"] = js(session, "return {theme:document.querySelector('#theme-select').value,effective:document.documentElement.dataset.theme}")
        sidebars = js(session, "const shell=document.querySelector('.app-shell');const cycle=id=>{const b=document.getElementById(id);const values=[];for(let i=0;i<3;i++){b.click();values.push(shell.dataset[id==='left-state'?'leftState':'rightState']);}return values};const left=cycle('left-state'),right=cycle('right-state');document.querySelector('#left-restore').click();document.querySelector('#right-restore').click();return {left,right,leftRestored:shell.dataset.leftState==='expanded',rightRestored:shell.dataset.rightState==='expanded'}")
        integration = js(session, "const s=document.querySelector('#snapshot-action');const nav=document.querySelector('[data-view=overview]');return {tooltip:nav.getAttribute('aria-description'),navName:nav.getAttribute('aria-label'),snapshotLabel:s.textContent.trim(),snapshotDisabled:s.disabled,snapshotExplanation:document.querySelector('#snapshot-status').textContent.trim(),chatDisabled:document.querySelector('.new-chat').disabled}")
        desktop = js(session, "return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth}")
        request("POST", f"/session/{session}/window/rect", {"x": 0, "y": 0, "width": 390, "height": 844})
        mobile = js(session, "return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,navButton:getComputedStyle(document.querySelector('#mobile-menu')).display}")
        reloads = js(session, "return performance.timeOrigin")
        disabled = js(session, "return [...document.querySelectorAll('button:disabled')].length>=2")
        fixture_banner = js(session, "return document.querySelector('.preview-banner').innerText")
        report = {"browser": subprocess.check_output(["firefox", "--version"], text=True).strip(), "url": args.base_url, "authenticated_preview": authenticated,
                  "navigation_calls_ms": {"count": len(samples), "median": sorted(samples)[len(samples)//2], "max": max(samples)},
                  "resident_selection": {"before": selected_before, "selected": selected_after, "retained_after_view_switch": context_retained},
                  "conversation_context_expand": note_open, "theme": theme, "sidebars": sidebars,
                  "integration_boundaries": integration, "desktop": desktop, "mobile": mobile,
                  "disabled_mutation_controls_present": disabled, "fixture_banner": fixture_banner,
                  "browser_errors": js(session, "return window.__errors"), "document_time_origin": reloads}
        print(json.dumps(report, sort_keys=True))
        if selected_after != "Resident fixture 02" or context_retained != selected_after or not note_open or theme["dark"] != "dark" or theme["light"] != "light" or theme["saved"] != "light" or theme["systemEffective"] != theme["systemOS"] or theme["storedBeforeReload"] != "dark" or theme["reload_restored"]["theme"] != "dark" or theme["reload_restored"]["effective"] != "dark" or len(sidebars["left"]) != 3 or len(sidebars["right"]) != 3 or not sidebars["leftRestored"] or not sidebars["rightRestored"] or not integration["tooltip"] or integration["navName"] != "Overview" or integration["snapshotLabel"] != "Snapshot" or integration["snapshotDisabled"] or "fixture view" not in integration["snapshotExplanation"] or not integration["chatDisabled"] or desktop["overflow"] or mobile["overflow"] or mobile["navButton"] == "none" or not disabled or report["browser_errors"]:
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
