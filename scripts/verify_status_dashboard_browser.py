# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_status_dashboard_browser.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.3
# Purpose: Verify deployed dashboard in a real headless Firefox browser
# Execution Model: Request-driven acceptance utility; starts and stops only its own geckodriver
# Observability: Redacted JSON result; screenshots and no credentials
# Dependencies: Python 3.10+, Firefox, geckodriver
# Authority: Read-only dashboard APIs; no assignment or service mutations
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Verify operational guide navigation, rendering, and document links
# Contracts: docs/components/STATUS_DASHBOARD_API.schema.json
# Tests: Camrui deployed Firefox acceptance
# History: Git and .riverview-backups/manifest.jsonl
"""Run a read-only deployed dashboard browser acceptance check."""
import argparse
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    parser.add_argument("--token-file", type=Path,
                        default=Path("/home/admin1/.config/riverview/status-dashboard.token"))
    parser.add_argument("--assignment-id", required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory for redacted report and screenshots")
    args = parser.parse_args()
    token_path = args.token_file
    if not token_path.is_file() or token_path.is_symlink() or token_path.stat().st_mode & 0o077:
        raise SystemExit("protected_dashboard_token_unavailable")
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("protected_dashboard_token_empty")
    if args.output.exists():
        raise SystemExit("output_directory_must_not_exist")
    args.output.mkdir(parents=True, mode=0o700)
    os.chmod(args.output, 0o700)

    def webdriver(method, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", data=body, method=method,
            headers={"Content-Type": "application/json"} if body is not None else {})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            # Do not include request/response headers; they can contain credentials.
            raise RuntimeError(f"webdriver_http_{error.code}") from None

    def js(session_id, source, arguments=None):
        return webdriver("POST", f"/session/{session_id}/execute/sync",
                         {"script": source, "args": arguments or []})["value"]

    def wait_js(session_id, source, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = js(session_id, "return (" + source + ");")
            if value:
                return value
            time.sleep(0.2)
        raise RuntimeError("browser_condition_timeout")

    # Bind an ephemeral loopback listener and release it immediately before geckodriver.
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    driver = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session_id = None
    try:
        for _ in range(100):
            if driver.poll() is not None:
                raise RuntimeError("geckodriver_stopped")
            try:
                webdriver("GET", "/status")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.2)
        else:
            raise RuntimeError("geckodriver_start_timeout")
        capabilities = {"capabilities": {"alwaysMatch": {
            "browserName": "firefox", "moz:firefoxOptions": {"args": ["-headless"]}}}}
        session_id = webdriver("POST", "/session", capabilities)["value"]["sessionId"]
        webdriver("POST", f"/session/{session_id}/window/rect",
                  {"x": 0, "y": 0, "width": 1440, "height": 1000})
        webdriver("POST", f"/session/{session_id}/url", {"url": args.base_url.rstrip("/") + "/"})
        js(session_id, "window.__rvBrowserErrors=[];addEventListener('error',e=>window.__rvBrowserErrors.push(String(e.message||'error')));addEventListener('unhandledrejection',e=>window.__rvBrowserErrors.push(String(e.reason||'rejection')));")
        # This compile check catches a script parse failure even if its tab is never opened.
        js(session_id, "window.__rvWorkflowSyntax=fetch('/assets/workflow.js').then(r=>r.text()).then(t=>{try{new Function(t);return 'valid'}catch(e){return 'invalid'}})")
        js(session_id, "document.querySelector('#token').value=arguments[0];document.querySelector('#login-form').requestSubmit();", [token])
        wait_js(session_id, "!document.querySelector('#workspace').hidden && document.querySelector('#hero-status').textContent.includes('Connected')")
        status = js(session_id, "return fetch('/api/v1/status',{headers:{Authorization:'Bearer '+sessionStorage.getItem('rv.dashboard.token')}}).then(r=>r.json())")
        assignment = js(session_id, "return fetch('/api/v1/assignments/'+encodeURIComponent(arguments[0]),{headers:{Authorization:'Bearer '+sessionStorage.getItem('rv.dashboard.token')}}).then(r=>r.json())", [args.assignment_id])
        attention = js(session_id, "return fetch('/api/v1/attention?limit=10',{headers:{Authorization:'Bearer '+sessionStorage.getItem('rv.dashboard.token')}}).then(async r=>({status:r.status,body:await r.json()}))")

        nav_samples = []
        for view in ("assignments", "activity", "overview", "workflows"):
            start = js(session_id, "return performance.now()")
            js(session_id, "document.querySelector('[data-view='+arguments[0]+']').click()", [view])
            end = js(session_id, "return performance.now()")
            nav_samples.append({"view": view, "navigation_call_ms": round(end - start, 3)})
        graph_revision = wait_js(session_id, "document.querySelector('#graph-canvas svg') && document.querySelector('#graph-revision').textContent.includes('nodes')")
        graph = js(session_id, "const gid=document.querySelector('#graph-select').value;return Promise.all([fetch('/api/v1/graphs/'+encodeURIComponent(gid),{headers:{Authorization:'Bearer '+sessionStorage.getItem('rv.dashboard.token')}}).then(r=>r.json()),fetch('/assets/workflow.js').then(r=>r.text())]).then(([data,source])=>{let syntax;try{new Function(source);syntax='valid'}catch(e){syntax='invalid'}const ids=new Set(data.graph.nodes.map(n=>n.id));const external=data.graph.edges.filter(e=>!ids.has(e.from)||!ids.has(e.to));return {label:document.querySelector('#graph-revision').textContent,nodes:document.querySelectorAll('#graph-canvas .graph-node').length,decisions:document.querySelectorAll('#graph-canvas .graph-decision').length,edges:document.querySelectorAll('#graph-canvas .graph-edge').length,canonical_edges:data.graph.edges.length,external_edges:external.length,external_jump_sources:external.map(e=>e.from),jump_node_ids:data.graph.nodes.filter(n=>n.type==='jump').map(n=>n.id),position:document.querySelector('#graph-execution-position').textContent,syntax}})" )
        js(session_id, "document.querySelector('#graph-canvas .graph-node').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
        selected_node = wait_js(session_id, "document.querySelector('#graph-node-detail code') && document.querySelector('#graph-node-detail code').textContent")
        js(session_id, "const s=document.querySelector('#graph-select');s.value='rv:steward-dashboard:status';s.dispatchEvent(new Event('change',{bubbles:true}));")
        wait_js(session_id, "document.querySelector('#graph-revision').textContent.includes('STEWARD-DASHBOARD')")
        jump_count = js(session_id, "return document.querySelectorAll('#graph-jumps button').length")
        jump_navigation = js(session_id, "const b=[...document.querySelectorAll('#graph-jumps button')].find(x=>!x.disabled);if(!b)return false;b.click();return true")
        workflow_png = base64.b64decode(webdriver("GET", f"/session/{session_id}/screenshot")["value"])

        documentation_tab = webdriver("POST", f"/session/{session_id}/window/new", {"type": "tab"})["value"]["handle"]
        webdriver("POST", f"/session/{session_id}/window", {"handle": documentation_tab})
        webdriver("POST", f"/session/{session_id}/url",
                  {"url": args.base_url.rstrip("/") + "/docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md"})
        wait_js(session_id, "document.querySelector('article.readable-doc h1') && document.querySelector('article.readable-doc h1').textContent")
        docs = js(session_id, "const links=[...document.querySelectorAll('article.readable-doc a[href^=\"/docs/components/\"]')].map(a=>a.getAttribute('href'));return Promise.all(links.map(h=>fetch(h).then(r=>({href:h,status:r.status})))).then(results=>({title:document.title,headings:document.querySelectorAll('article.readable-doc h1,article.readable-doc h2,article.readable-doc h3').length,tables:document.querySelectorAll('article.readable-doc table').length,code_blocks:document.querySelectorAll('article.readable-doc pre code').length,document_links:results,raw_markdown:document.body.innerText.includes('<!-- Riverview~ Controlled Document'),scripts:document.querySelectorAll('article.readable-doc script').length,unsafe_links:[...document.querySelectorAll('article.readable-doc a')].filter(a=>!['http:','https:'].includes(a.protocol)&&!a.getAttribute('href').startsWith('/')).length}))")
        docs_png = base64.b64decode(webdriver("GET", f"/session/{session_id}/screenshot")["value"])
        browser_errors = js(session_id, "return window.__rvBrowserErrors||[]")
        (args.output / "workflow-view.png").write_bytes(workflow_png)
        (args.output / "cookbook-view.png").write_bytes(docs_png)
        report = {
            "browser": subprocess.check_output(["firefox", "--version"], text=True).strip(),
            "base_url": args.base_url,
            "source_commit": status.get("source", {}).get("source_commit"),
            "projection_status": status.get("projection_status"),
            "cme_status": status.get("cme", {}).get("status"),
            "assignment_id": args.assignment_id,
            "assignment_state": assignment.get("assignment", {}).get("state"),
            "attempts": len(assignment.get("attempts", [])),
            "independent_verifications": len(assignment.get("verifications", [])),
            "attention_http_status": attention["status"],
            "attention_status": attention["body"].get("status"),
            "attention_items": len(attention["body"].get("items", [])),
            "graph": graph,
            "selected_node_id": selected_node,
            "jump_points": jump_count,
            "jump_navigation": jump_navigation,
            "documentation": docs,
            "navigation": nav_samples,
            "browser_errors": browser_errors,
            "screenshots": {"workflow-view.png": len(workflow_png), "cookbook-view.png": len(docs_png)},
        }
        failed = []
        if report["projection_status"] != "healthy": failed.append("projection_status")
        if report["cme_status"] != "healthy": failed.append("cme_status")
        if report["assignment_state"] != "completed" or not report["attempts"]: failed.append("assignment_execution")
        if not report["independent_verifications"]: failed.append("independent_verification")
        if report["attention_http_status"] != 200: failed.append("attention_endpoint")
        if report["graph"]["syntax"] != "valid" or report["graph"]["nodes"] < 1 or report["graph"]["decisions"] < 1 or report["graph"]["edges"] < 1 or report["graph"]["canonical_edges"] != report["graph"]["edges"] + report["graph"]["external_edges"] or any(node_id not in report["graph"]["jump_node_ids"] for node_id in report["graph"]["external_jump_sources"]): failed.append("workflow_graph")
        if report["documentation"]["headings"] < 10 or report["documentation"]["tables"] < 2 or report["documentation"]["code_blocks"] < 8 or report["documentation"]["raw_markdown"] or report["documentation"]["scripts"] or report["documentation"]["unsafe_links"] or any(item["status"] != 200 for item in report["documentation"]["document_links"]): failed.append("readable_documentation")
        if not report["jump_navigation"]: failed.append("cross_workflow_navigation")
        if report["browser_errors"]: failed.append("browser_errors")
        report["failed_checks"] = failed
        (args.output / "browser-acceptance.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, sort_keys=True))
        if failed:
            raise RuntimeError("dashboard_browser_acceptance_failed:" + ",".join(failed))
    finally:
        if session_id:
            try:
                webdriver("DELETE", f"/session/{session_id}")
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
