# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_diagnostic_snapshot_browser.py
# Component: STEWARD-DASHBOARD
# Revision: 1.1.15
# Purpose: Verify archive-plus-local-download diagnostic ZIP in isolated Firefox with synthetic read-only APIs
# Execution Model: Request-driven isolated fixture; owns only a temporary HTTP server and geckodriver
# Observability: Sanitized JSON report and downloaded ZIP; no real account or production data
# Dependencies: Python 3.10+, Firefox, geckodriver
# Authority: Synthetic cookie fixture only; all fixture data are read-only
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Verify complete workflow, page, privacy, and offline package contracts
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Validate all canonical workflow JSON and SVG/PNG identity across the full source inventory.
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Verify safe request-field allowlisting and unresolved-reference reporting.
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Require sanitized browser navigation timing in the offline archive
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Exercise the actual repository dashboard DOM with synthetic read-only API fixtures.
# Changed: 2026-10-16 UTC | RV-WEBSITE-PR67-SNAPSHOT-CSP-FIX | Exercise the actual-dashboard fixture under the production image-source CSP.
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Match the dashboard API contracts and isolate expected unauthenticated checks from authenticated browser diagnostics.
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Require complete real-dashboard page capture and readable long-page tiles.
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Allow the bounded full export time for the second-viewport comparison too.
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Require the responsive narrow-viewport package to be complete as well.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Stress bounded raster omission and verify canonical offline payloads survive
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Allow the oversized raster test under the actual-dashboard Content Security Policy
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Assert separate raster, structured-member, and manifest reserves under overflow
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Retain full browser acceptance for the integrated bounded snapshot source.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Assert unauthenticated archive failure is clear and retains local ZIP download.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Exercise synthetic archive success/failure, identical ZIP digest, and local-download failure preservation.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Verify the Copy GitHub Link button copies the confirmed synthetic release URL.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Reject a synthetic mismatched GitHub digest while preserving the local ZIP download.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Exercise local-download failure through the real snapshot and authenticated archive flow without exposing test callbacks.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-V1-V2-COMPAT-20261020 | Verify V1 manifest identity and capture-specific archive filenames in browser receipts.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Serve stress hook as a CSP-allowed same-origin fixture asset
# Tests: scripts/verify_diagnostic_snapshot_browser.py
# History: Git
"""Exercise the downloadable diagnostic snapshot without connecting to Riverview services."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import socket
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "src/riverview_core/status_dashboard/static/diagnostic-snapshot.js"
STATIC = ROOT / "src/riverview_core/status_dashboard/static"

GRAPH_A = {
    "graph_id": "rv:test:alpha", "graph_revision": "1.0.0", "component_id": "TEST",
    "workflow_id": "alpha.v1", "source_references": [], "documentation_references": [],
    "verification_evidence": [],
    "nodes": [
        {"id": "rv:test:alpha:entry", "node_revision": "1.0.0", "type": "entry",
         "label": "Synthetic alpha entry", "source_references": [], "documentation_references": [], "verification_evidence": []},
        {"id": "rv:test:alpha:jump", "node_revision": "1.0.0", "type": "jump",
         "label": "Visit beta exit", "jump_target_id": "rv:test:beta:exit", "source_references": [], "documentation_references": [], "verification_evidence": []}],
    "edges": [
        {"from": "rv:test:alpha:entry", "to": "rv:test:alpha:jump", "type": "runtime_transition"},
        {"from": "rv:test:alpha:jump", "to": "rv:test:beta:exit", "type": "jump", "label": "Synthetic cross-workflow route"}],
}
GRAPH_B = {
    "graph_id": "rv:test:beta", "graph_revision": "2.0.0", "component_id": "TEST",
    "workflow_id": "beta.v1", "source_references": [], "documentation_references": [],
    "verification_evidence": [],
    "nodes": [{"id": "rv:test:beta:exit", "node_revision": "1.0.0", "type": "exit",
               "label": "Synthetic beta exit", "source_references": [], "documentation_references": [], "verification_evidence": []}],
    "edges": [],
}
GRAPHS = {GRAPH_A["graph_id"]: GRAPH_A, GRAPH_B["graph_id"]: GRAPH_B}
REGISTRY = {
    "schema_version": "rv.website.capabilities.v1", "registry_id": "rv:test:website-capabilities", "revision": "1.0.0",
    "pages": [
        {"id": "alpha", "title": "Alpha page", "selector": "#view-alpha", "navigation_selector": "[data-view='alpha']", "components": ["fixture"], "data_sources": [], "representations": []},
        {"id": "beta", "title": "Beta page", "selector": "#view-beta", "navigation_selector": "[data-view='beta']", "components": ["fixture"], "data_sources": [], "representations": []},
        {"id": "workflows", "title": "Workflow viewer", "selector": "#view-workflows", "navigation_selector": "[data-view='workflows']", "components": ["fixture"], "data_sources": ["GET /api/v1/graphs"], "representations": []}],
    "controls": [
        {"id": "navigation.alpha", "selector": "[data-view='alpha']", "action": "Show alpha page"},
        {"id": "navigation.beta", "selector": "[data-view='beta']", "action": "Show beta page"},
        {"id": "navigation.workflows", "selector": "[data-view='workflows']", "action": "Show workflow viewer"},
        {"id": "snapshot.download", "selector": "#snapshot", "action": "Download snapshot"},
        {"id": "alpha.action", "selector": "#alpha-action", "action": "Synthetic page control"},
        {"id": "beta.input", "selector": "#fixture-input", "action": "Synthetic form control"},
        {"id": "graph.fit", "selector": "#graph-fit", "action": "Fit the workflow"},
        {"id": "graph.zoom.in", "selector": "#graph-zoom-in", "action": "Zoom in"},
        {"id": "graph.zoom.out", "selector": "#graph-zoom-out", "action": "Zoom out"},
        {"id": "graph.reset", "selector": "#graph-reset", "action": "Reset the view"},
        {"id": "graph.fullscreen", "selector": "#graph-fullscreen", "action": "Toggle full screen"}],
    "workflow_surfaces": {"registry_source": "fixture", "authoritative_repository_path": "fixture", "definition_source": "fixture"},
}
SNAPSHOT = {"schema_version": "rv.dashboard.snapshot.v1", "captured_at": "2026-10-16T00:00:00Z",
            "source": {"source_commit": "a" * 40, "deployment_id": "synthetic-fixture"},
            "projection": {"source": {"source_commit": "a" * 40, "deployment_id": "synthetic-fixture"}},
            "assignments": {"status": "available", "items": []}, "redaction": {"conversation_content": "not collected"}}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory for report and downloaded fixture ZIP")
    parser.add_argument("--full-source-fixture", action="store_true", help="Use the repository capability registry and every canonical process graph")
    parser.add_argument("--actual-dashboard-fixture", action="store_true", help="Serve the repository dashboard HTML/CSS/scripts with synthetic read-only API responses")
    parser.add_argument("--package-bound-stress-fixture", action="store_true", help="Pad synthetic canvas output to force the current ZIP raster budget without production data")
    parser.add_argument("--single-capture", action="store_true", help="Skip the second-viewport comparison")
    parser.add_argument("--archive-fixture", choices=("success", "failure", "mismatch"), help="Exercise the archive API with a synthetic receipt, controlled failure, or mismatched digest")
    args = parser.parse_args()
    if args.actual_dashboard_fixture:
        args.full_source_fixture = True
    if args.package_bound_stress_fixture and not args.actual_dashboard_fixture:
        raise SystemExit("package_bound_stress_requires_actual_dashboard_fixture")
    source_graphs = None
    source_graph_paths = {}
    if args.full_source_fixture:
        global GRAPH_A, GRAPH_B, GRAPHS, REGISTRY
        graph_root = ROOT / "process_graphs"
        source_graphs = {}
        for graph_path in sorted(graph_root.glob("*/*.json")):
            if graph_path.parent.name in {"generated", "schema"}:
                continue
            value = json.loads(graph_path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and isinstance(value.get("graph_id"), str):
                source_graphs[value["graph_id"]] = value
                source_graph_paths[value["graph_id"]] = graph_path.relative_to(ROOT).as_posix()
        REGISTRY = json.loads((ROOT / "src/riverview_core/status_dashboard/static/capabilities.json").read_text(encoding="utf-8"))
        GRAPHS = source_graphs
        jumping = [(graph, node) for graph in GRAPHS.values() for node in graph.get("nodes", []) if node.get("type") == "jump" and node.get("jump_target_id")]
        if not jumping:
            raise SystemExit("canonical_fixture_has_no_jump_reference")
        GRAPH_A, jump_node = jumping[0]
        GRAPH_B = GRAPHS.get(jump_node["jump_target_id"].rsplit(":", 1)[0])
        if GRAPH_B is None:
            raise SystemExit("canonical_fixture_jump_target_workflow_missing")
    else:
        # Exercise honest unresolved-reference reporting without changing the
        # canonical repository graphs used by --full-source-fixture.
        GRAPH_A["nodes"].append({"id":"rv:test:alpha:unresolved-jump","node_revision":"1.0.0","type":"jump",
            "label":"Unresolved fixture target","jump_target_id":"rv:test:missing:node","source_references":[],"documentation_references":[],"verification_evidence":[]})
    if args.output.exists():
        raise SystemExit("output_directory_must_not_exist")
    args.output.mkdir(parents=True, mode=0o700)
    os.chmod(args.output, 0o700)
    download_dir = Path.home() / "Downloads" / f"rv-snapshot-fixture-{args.output.name}"
    download_dir.mkdir(mode=0o700, parents=True)
    requests = []
    archive_receipts = []
    index = {"schema_version": "rv.website.workflow-index.v1", "status": "available", "inventory_count": len(GRAPHS),
             "errors": [], "items": [{"graph_id": g["graph_id"], "component_id": g["component_id"],
             "workflow_id": g["workflow_id"], "graph_revision": g["graph_revision"],
             "source_file": source_graph_paths.get(g["graph_id"], f"process_graphs/test/{g['workflow_id']}.json"), "node_count": len(g["nodes"]),
             "edge_count": len(g["edges"])} for g in GRAPHS.values()]}
    if args.full_source_fixture:
        nav_html, view_html = [], []
        for page_number, page_meta in enumerate(REGISTRY["pages"]):
            page_id = page_meta["id"]
            nav_id = page_meta["navigation_selector"][1:] if page_meta["navigation_selector"].startswith("#") else ""
            nav_id_attr = f'id="{nav_id}"' if nav_id else ""
            nav_html.append(f'<button class="nav-item" {nav_id_attr} data-view="{page_id}">{page_meta["title"]}</button>')
            private = '<div class="conversation-timeline">PRIVATE FIXTURE CONVERSATION MUST NOT EXPORT</div>' if page_id == "grace-chat" else ""
            sensitive = '<input id="fixture-private-input" value="SENSITIVE FIXTURE FORM VALUE">' if page_id == "account" else ""
            fixture_controls = '<form><button id="fixture-registered-action" type="button">Fixture action</button></form><button id="fixture-unregistered">Unregistered fixture control</button>'
            hidden = "" if page_number == 0 else " hidden"
            active = " active" if page_number == 0 else ""
            viewer = '''<p id="graph-revision"></p><div id="graph-execution-position"></div><select id="graph-select"></select>
              <button id="graph-fit" disabled>Fit</button><button id="graph-zoom-out" disabled>Zoom out</button><button id="graph-zoom-in" disabled>Zoom in</button><button id="graph-reset" disabled>Reset</button><button id="graph-fullscreen" disabled>Full screen</button>
              <div id="graph-canvas" style="position:relative;overflow:hidden;width:620px;height:420px;border:1px solid #fff"><p>Select a workflow.</p></div>
              <div id="graph-jumps"></div><aside id="graph-node-detail">Node details</aside>''' if page_id == "workflows" else ""
            view_html.append(f'<section class="view{active}" id="view-{page_id}" aria-label="{page_meta["title"]}"{hidden}><h1>{page_meta["title"]}</h1>{fixture_controls}{private}{sensitive}{viewer}</section>')
        page = (
            '''<!doctype html><html lang="en"><head><meta charset="utf-8">
            <meta name="viewport" content="width=device-width"><title>Snapshot full source fixture</title>
            <style>.shell{font:16px Arial;background:#112;color:#fff;width:900px;min-height:1600px;display:grid;grid-template-columns:220px 1fr}.rail{padding:15px;display:grid;align-content:start;gap:6px}.view{padding:30px;min-height:400px;background:#223}.snapshot-banner{padding:8px}button{padding:10px}</style>
            <script>window.__jsErrors=[];addEventListener("error",e=>window.__jsErrors.push(String(e.message||"error")));addEventListener("unhandledrejection",()=>window.__jsErrors.push("rejection"));</script>
            <script src="/assets/diagnostic-snapshot.js" defer></script><script src="/assets/workflow.js" defer></script><script>
            window.RiverviewSnapshotApi=async path=>{const r=await fetch(path,{credentials:"same-origin"});if(!r.ok)throw new Error("http_"+r.status);return r.json()};
            document.addEventListener("click",e=>{const nav=e.target.closest("[data-view]");if(nav){document.querySelectorAll(".view").forEach(x=>{x.hidden=x.id!=="view-"+nav.dataset.view;x.classList.toggle("active",!x.hidden)});history.replaceState(null,"","#"+nav.dataset.view)}});</script></head><body>
            <div class="shell"><nav class="rail">''' + "".join(nav_html) +
            '<button id="snapshot">Download Snapshot</button></nav>' + "".join(view_html) + '</div></body></html>'
        ).encode()
    if args.actual_dashboard_fixture:
        page = (STATIC / "index.html").read_bytes()
        if args.package_bound_stress_fixture:
            stress = b'<script src="/assets/snapshot-stress.js"></script>'
            marker = b'<script src="/assets/diagnostic-snapshot.js"'
            if marker not in page:
                raise SystemExit("snapshot_script_injection_point_missing")
            page = page.replace(marker, stress + marker, 1)
    else:
        page = b'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Snapshot fixture</title>
        <style>.shell{font:16px Arial;background:#112;color:#fff;width:900px;min-height:1600px}.rail{padding:15px}.view{padding:30px;min-height:400px;background:#223}.snapshot-banner{padding:8px}button{padding:10px}</style>
        <script>window.__jsErrors=[];addEventListener('error',e=>window.__jsErrors.push(String(e.message||'error')));addEventListener('unhandledrejection',()=>window.__jsErrors.push('rejection'));</script>
        <script src="/assets/diagnostic-snapshot.js" defer></script><script src="/assets/workflow.js" defer></script><script>
        window.RiverviewSnapshotApi=async path=>{const r=await fetch(path,{credentials:'same-origin'});if(!r.ok)throw new Error('http_'+r.status);return r.json()};
        document.addEventListener('click',e=>{const nav=e.target.closest('[data-view]');if(nav){document.querySelectorAll('.view').forEach(x=>{x.hidden=x.id!=='view-'+nav.dataset.view;x.classList.toggle('active',!x.hidden)});history.replaceState(null,'','#'+nav.dataset.view)}});
        </script><div class="shell"><nav class="rail"><button data-view="alpha">Alpha</button><button data-view="beta">Beta</button><button data-view="workflows">Workflows</button><button id="snapshot">Download Snapshot</button></nav>
        <section class="view active" id="view-alpha" aria-label="Alpha page"><h1>Alpha</h1><button id="alpha-action">Alpha action</button><div class="conversation-timeline">PRIVATE FIXTURE CONVERSATION MUST NOT EXPORT</div></section>
        <section class="view" id="view-beta" aria-label="Beta page" hidden><h1>Beta</h1><input id="fixture-input" value="SENSITIVE FIXTURE FORM VALUE"></section>
        <section class="view" id="view-workflows" aria-label="Workflow viewer" hidden><h1>Workflows</h1><p id="graph-revision"></p><div id="graph-execution-position"></div><select id="graph-select"></select><button id="graph-fit" disabled>Fit</button><button id="graph-zoom-out" disabled>Zoom out</button><button id="graph-zoom-in" disabled>Zoom in</button><button id="graph-reset" disabled>Reset</button><button id="graph-fullscreen" disabled>Full screen</button><div id="graph-canvas" style="position:relative;overflow:hidden;width:620px;height:420px;border:1px solid #fff"><p>Select a workflow.</p></div><div id="graph-jumps"></div><aside id="graph-node-detail">Node details</aside></section></div>'''


    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def send_body(self, status, body, content_type="application/json; charset=utf-8", extra=()):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if args.actual_dashboard_fixture:
                self.send_header("Content-Security-Policy",
                                 "default-src 'none'; script-src 'self'; style-src 'self'; "
                                 "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
                                 "form-action 'self'; frame-ancestors 'none'")
            for key, value in extra:
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            requests.append({"path": self.path, "cookie_present": bool(self.headers.get("Cookie"))})
            if args.package_bound_stress_fixture and self.path == "/assets/snapshot-stress.js":
                return self.send_body(200, b'''window.__snapshotStressHook=true;(function(){const native=HTMLCanvasElement.prototype.toBlob;HTMLCanvasElement.prototype.toBlob=function(callback,type,...args){native.call(this,blob=>{if(!blob)return callback(blob);blob.arrayBuffer().then(buffer=>{const original=new Uint8Array(buffer),padded=new Uint8Array(Math.max(original.length,2*1024*1024));padded.set(original);callback(new Blob([padded],{type:type||blob.type}));});},type,...args);};})();''', "text/javascript; charset=utf-8")
            if self.path == "/":
                return self.send_body(200, page, "text/html; charset=utf-8")
            if args.actual_dashboard_fixture and self.path.startswith("/assets/"):
                asset_name = self.path.removeprefix("/assets/")
                asset = STATIC / asset_name
                if asset.parent == STATIC and asset.is_file():
                    content_type = "text/css; charset=utf-8" if asset.suffix == ".css" else "text/javascript; charset=utf-8"
                    return self.send_body(200, asset.read_bytes(), content_type)
                return self.send_body(404, b'{"error":"not_found"}')
            if self.path == "/assets/diagnostic-snapshot.js":
                return self.send_body(200, ASSET.read_bytes(), "text/javascript; charset=utf-8")
            if self.path == "/assets/workflow.js":
                return self.send_body(200, (ROOT / "src/riverview_core/status_dashboard/static/workflow.js").read_bytes(), "text/javascript; charset=utf-8")
            if self.path == "/assets/app.css":
                return self.send_body(200, b"body{background:#111;color:#eee}.view{display:block}", "text/css; charset=utf-8")
            if self.path == "/signin":
                cookies=[("Set-Cookie", "rv_account_session=synthetic-only; Path=/; SameSite=Strict")]
                if args.archive_fixture:
                    cookies.append(("Set-Cookie", "rv_account_csrf=synthetic-fixture; Path=/; SameSite=Strict"))
                return self.send_body(200, b"ok", extra=tuple(cookies))
            if not self.headers.get("Cookie", "").startswith("rv_account_session=synthetic-only"):
                return self.send_body(401, b'{"error":"authentication_required"}')
            from urllib.parse import urlsplit
            api_path = urlsplit(self.path).path
            values = {"/api/v1/capabilities": REGISTRY, "/api/v1/snapshot": SNAPSHOT,
                      "/api/v1/snapshot/workflow-index": index}
            if args.actual_dashboard_fixture:
                source = {"source_commit": "a" * 40, "deployment_id": "synthetic-fixture"}
                if api_path == "/api/v1/capabilities":
                    return self.send_body(200, json.dumps(REGISTRY).encode())
                if api_path == "/api/v1/snapshot":
                    fixture_snapshot = {"projection": {"source": source, "status": "healthy",
                        "observed_at": "2026-10-16T00:00:00Z"}}
                    return self.send_body(200, json.dumps(fixture_snapshot).encode())
                if api_path == "/api/v1/snapshot/workflow-index":
                    fixture_index = {**index, "schema_version": "rv.website.workflow-index.v1",
                        "status": "available", "inventory_count": len(GRAPHS),
                        "expected_node_count": sum(len(graph["nodes"]) for graph in GRAPHS.values()),
                        "expected_edge_count": sum(len(graph["edges"]) for graph in GRAPHS.values())}
                    return self.send_body(200, json.dumps(fixture_index).encode())
                if api_path == "/api/v1/auth/session":
                    return self.send_body(200, b'{"status":"authenticated","identity":{"account_id":"fixture","email":"steward@example.invalid","roles":["steward"]}}')
                if api_path == "/api/v1/status":
                    return self.send_body(200, json.dumps({"projection_status":"healthy","freshness":"current",
                        "observed_at":"2026-10-16T00:00:00Z","source":source,"relations":{"cme_monitor_events":False},
                        "assignment_counts":{},"assignments_total":0,"event_cursor":0,"cme":{"status":"not_initialized"},
                        "workers":{"status":"not_initialized"},"grace_execution":{"status":"not_initialized"}}).encode())
                if api_path == "/api/v1/graphs":
                    return self.send_body(200, json.dumps({"items": [{"graph_id": graph["graph_id"],
                        "component_id": graph["component_id"], "workflow_id": graph["workflow_id"],
                        "graph_revision": graph["graph_revision"]} for graph in GRAPHS.values()]}).encode())
                if api_path == "/api/v1/notifications":
                    return self.send_body(200, b'{"status":"not_initialized","dispatcher":{"status":"not_initialized"},"items":[]}')
                if api_path == "/api/v1/resident-permissions":
                    return self.send_body(200, b'{"profiles":[],"capabilities":[],"resources":[]}')
                if api_path == "/api/v1/account/email-settings":
                    return self.send_body(200, b'{"configured":false,"password_configured":false}')
                if api_path.startswith("/api/v1/graphs/"):
                    from urllib.parse import unquote
                    graph_id = unquote(api_path.removeprefix("/api/v1/graphs/"))
                    graph = GRAPHS.get(graph_id)
                    if graph is None:
                        return self.send_body(404, b'{"error":"not_found"}')
                    return self.send_body(200, json.dumps({"graph": {**graph,
                        "execution_position": {"status":"unknown"}}}).encode())
                if api_path.startswith("/api/v1/"):
                    return self.send_body(200, b'{"status":"not_initialized","items":[],"dispatcher":{"status":"not_initialized"}}')
            if self.path in values:
                return self.send_body(200, json.dumps(values[self.path]).encode())
            if self.path == "/api/v1/graphs":
                return self.send_body(200, json.dumps({"items": [{"graph_id": graph["graph_id"],
                    "component_id": graph["component_id"], "workflow_id": graph["workflow_id"]}
                    for graph in GRAPHS.values()]}).encode())
            if self.path.startswith("/api/v1/graphs/"):
                from urllib.parse import unquote
                graph_id = unquote(self.path.removeprefix("/api/v1/graphs/"))
                graph = GRAPHS.get(graph_id)
                if graph is None:
                    return self.send_body(404, b'{"error":"not_found"}')
                return self.send_body(200, json.dumps({"graph": {**graph, "execution_position": {"status": "unknown"}}}).encode())
            return self.send_body(404, b'{"error":"not_found"}')

        def do_POST(self):
            requests.append({"method":"POST","path":self.path,"cookie_present":bool(self.headers.get("Cookie"))})
            if self.path == "/api/v1/snapshot/archive" and args.archive_fixture:
                package=self.rfile.read(int(self.headers.get("Content-Length", "0")))
                digest=hashlib.sha256(package).hexdigest()
                with zipfile.ZipFile(io.BytesIO(package)) as bundle:
                    manifest=json.loads(bundle.read("manifest.json"))
                version=manifest.get("dashboard_version","v1")
                capture_id=manifest["capture_id"]
                asset_name=f"riverview-{version}-{manifest['captured_at'].replace(':','-')}-{capture_id}.zip"
                archive_receipts.append({"size_bytes":len(package),"sha256":digest,"csrf_present":bool(self.headers.get("X-Riverview-CSRF")),"cookie_present":bool(self.headers.get("Cookie")),"dashboard_version":version,"capture_id":capture_id,"asset_name":asset_name})
                if args.archive_fixture == "failure":
                    return self.send_body(503, b'{"error":"synthetic_github_failure"}')
                snapshot_id="rvdiag-20261020T000000Z-0123456789abcdef0123456789abcdef"
                response={"snapshot_id":snapshot_id,"dashboard_version":version,"capture_id":capture_id,"asset_name":asset_name,"archive_size_bytes":len(package),"archive_sha256":"0"*64 if args.archive_fixture=="mismatch" else digest,
                    "release_url":"https://github.com/ppow1/Riverview-Diagnostic-Archive/releases/tag/"+snapshot_id}
                return self.send_body(200,json.dumps(response).encode())
            if args.actual_dashboard_fixture and self.path.startswith("/api/v1/") and self.headers.get("Cookie", "").startswith("rv_account_session=synthetic-only"):
                return self.send_body(200, b'{"status":"fixture_only"}')
            return self.send_body(404, b'{"error":"not_found"}')

        def do_DELETE(self):
            requests.append({"method":"DELETE","path":self.path,"cookie_present":bool(self.headers.get("Cookie"))})
            return self.send_body(200, b'{"status":"fixture_only"}')

    server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    driver = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None

    def webdriver(method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                         headers={"Content-Type": "application/json"} if data else {})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"webdriver_http_{error.code}:{error.read().decode('utf-8', errors='replace')[:500]}") from None

    def js(source):
        return webdriver("POST", f"/session/{session}/execute/sync", {"script": source, "args": []})["value"]

    def click_css(selector):
        js("document.querySelector(" + json.dumps(selector) + ")?.scrollIntoView({block:'center',inline:'center'});")
        element = webdriver("POST", f"/session/{session}/element", {"using": "css selector", "value": selector})["value"]["element-6066-11e4-a52e-4f735466cecf"]
        try:
            webdriver("POST", f"/session/{session}/element/{element}/click", {})
        except RuntimeError:
            if selector != "#snapshot":
                raise
            # Firefox treats this fixed rail control as outside the scrolling
            # element despite scrollIntoView; invoke the same DOM click path
            # after the attempted native click, and require the app listener
            # to record it before continuing.
            js("document.querySelector('#snapshot').click()")

    def pointer_click_css(selector):
        point=js("const r=document.querySelector("+json.dumps(selector)+").getBoundingClientRect();return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}")
        webdriver("POST",f"/session/{session}/actions",{"actions":[{"type":"pointer","id":"snapshot-mouse","parameters":{"pointerType":"mouse"},"actions":[{"type":"pointerMove","duration":0,"origin":"viewport","x":point["x"],"y":point["y"]},{"type":"pointerDown","button":0},{"type":"pointerUp","button":0}]}]})

    report = {"schema_version": "rv.website.snapshot-browser-verification.v1", "synthetic_fixture_only": True,
              "dashboard_source": "repository_static_dashboard" if args.actual_dashboard_fixture else "synthetic_page_fixture",
              "production_data_accessed": False, "production_mutations": False, "api_requests": requests,
              "expected_workflows": len(GRAPHS),
              "expected_nodes": sum(len(graph.get("nodes", [])) for graph in GRAPHS.values()),
              "expected_edges": sum(len(graph.get("edges", [])) for graph in GRAPHS.values()),
              "registered_pages": len(REGISTRY["pages"]), "registered_controls": len(REGISTRY["controls"])}
    try:
        for _ in range(100):
            try:
                webdriver("GET", "/status")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(.2)
        prefs = {"browser.download.folderList": 2, "browser.download.dir": str(download_dir),
                 "browser.download.useDownloadDir": True, "browser.helperApps.neverAsk.saveToDisk": "application/zip",
                 "browser.download.manager.showWhenStarting": False}
        session = webdriver("POST", "/session", {"capabilities": {"alwaysMatch": {
            "browserName": "firefox", "moz:firefoxOptions": {"args": ["-headless"], "prefs": prefs}}}})["value"]["sessionId"]
        webdriver("POST", f"/session/{session}/window/rect", {"x": 0, "y": 0, "width": 1280, "height": 900})
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/v1/capabilities")
            unauthorized=200
        except urllib.error.HTTPError as error:
            unauthorized=error.code
        report["unauthenticated_registry_status"] = unauthorized
        webdriver("POST", f"/session/{session}/url", {"url": f"http://127.0.0.1:{server.server_port}/signin"})
        webdriver("POST", f"/session/{session}/url", {"url": f"http://127.0.0.1:{server.server_port}/"})
        for _ in range(100):
            if js("return !!window.RiverviewSnapshot && !!window.RiverviewSnapshotApi"):
                break
            time.sleep(.1)
        click_css(REGISTRY["pages"][next(i for i,p in enumerate(REGISTRY["pages"]) if p["id"]=="workflows")]["navigation_selector"])
        viewer_deadline=time.monotonic()+12
        while time.monotonic()<viewer_deadline and not js("return document.querySelector('#graph-canvas svg')?.style.transform.includes('scale(')"):
            time.sleep(.1)
        if not js("return !!document.querySelector('#graph-canvas svg')"):
            raise RuntimeError("workflow_viewer_graph_not_rendered")
        fit_state=js("const s=document.querySelector('#graph-canvas svg'),r=document.querySelector('#graph-canvas').getBoundingClientRect(),m=s.style.transform.match(/scale\\(([^)]+)\\)/);return {scale:m?Number(m[1]):1,width:r.width,height:r.height,transform:s.style.transform}")
        click_css("#graph-zoom-in")
        zoom_state=js("const m=document.querySelector('#graph-canvas svg').style.transform.match(/scale\\(([^)]+)\\)/);return m?Number(m[1]):1")
        click_css("#graph-reset")
        reset_state=js("const m=document.querySelector('#graph-canvas svg').style.transform.match(/scale\\(([^)]+)\\)/);return m?Number(m[1]):1")
        click_css("#graph-fit")
        fit_button_state=js("const m=document.querySelector('#graph-canvas svg').style.transform.match(/scale\\(([^)]+)\\)/);return m?Number(m[1]):1")
        pan_changed=js("const c=document.querySelector('#graph-canvas'),s=c.querySelector('svg'),before=s.style.transform;c.setPointerCapture=()=>{};c.hasPointerCapture=()=>true;c.releasePointerCapture=()=>{};c.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:7,isPrimary:true,button:0,buttons:1,clientX:80,clientY:80}));c.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerId:7,isPrimary:true,buttons:1,clientX:112,clientY:101}));c.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:7,isPrimary:true,button:0,buttons:0,clientX:112,clientY:101}));return s.style.transform!==before")
        pointer_click_css("#graph-fullscreen")
        time.sleep(.5)
        fullscreen_entered=js("return document.fullscreenElement===document.querySelector('#graph-canvas')")
        if fullscreen_entered:
            pointer_click_css("#graph-fullscreen")
            time.sleep(.2)
        report["workflow_viewer"]={"initial_fit_scale":fit_state["scale"],"initial_fit_applied":fit_state["scale"]<=1 and "scale(" in fit_state["transform"],
            "zoom_in_increased_scale":zoom_state>fit_state["scale"],"reset_restored_unit_scale":abs(reset_state-1)<.001,
            "fit_button_restored_fit":fit_button_state<=1,"pan_changed_transform":pan_changed,
            "fullscreen_entered":bool(fullscreen_entered),"fullscreen_supported":bool(js("return document.fullscreenEnabled"))}
        report["workflow_viewer"]["fullscreen_behavior_ok"]=(not report["workflow_viewer"]["fullscreen_supported"] or report["workflow_viewer"]["fullscreen_entered"])
        first_page_id, second_page_id = REGISTRY["pages"][0]["id"], REGISTRY["pages"][1]["id"]
        js("document.querySelector(arguments[0]).click();document.querySelector(arguments[1]).click();".replace("arguments[0]", json.dumps(REGISTRY["pages"][1]["navigation_selector"])).replace("arguments[1]", json.dumps(REGISTRY["pages"][0]["navigation_selector"])))
        time.sleep(.1)
        js("window.RiverviewDiagnostics.recordRequest({method:'POST',path:'/api/v1/objectives/12345678-1234-1234-1234-123456789abc?token=PRIVATE_QUERY',status:201,duration_ms:37,request_id:'fixture-correlation-17',headers:{Authorization:'Bearer PRIVATE_HEADER'},request_body:'PRIVATE_REQUEST_BODY'})")
        js("document.querySelector('#snapshot').scrollIntoView({block:'center',inline:'center'})")
        click_css("#snapshot")
        time.sleep(.25)
        if not js("return window.RiverviewDiagnostics.snapshot().interactions.some(item=>item.control_id==='snapshot')"):
            report["snapshot_control_debug"] = js("const e=document.querySelector('#snapshot'),r=e.getBoundingClientRect();return {rect:{x:r.x,y:r.y,width:r.width,height:r.height},viewport:{width:innerWidth,height:innerHeight},disabled:e.disabled,hidden:e.hidden,active_view:document.querySelector('.view.active')?.id,fullscreen:Boolean(document.fullscreenElement),suppress:window.RiverviewDiagnostics.snapshot().interactions.length,element_at_point:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML?.slice(0,240)}")
            (args.output / "browser-acceptance-debug.json").write_text(json.dumps(report, indent=2)+"\n")
            raise RuntimeError("snapshot_control_click_not_observed")
        # A full-source run exports every canonical graph and renders all
        # registered page and workflow visuals in Firefox. Allow enough time
        # for the bounded export instead of mistaking normal rasterization for
        # a failed download.
        deadline = time.monotonic() + 180
        archives = []
        while time.monotonic() < deadline:
            archives = list(download_dir.glob("*.zip"))
            if archives and not list(download_dir.glob("*.part")):
                break
            time.sleep(.25)
        if not archives:
            report["debug"] = js("return {loaded:!!window.RiverviewSnapshot,phase:window.__snapshotPhase,lastError:window.__snapshotLastError||null,package:window.__snapshotPackage||null,api:!!window.RiverviewSnapshotApi,toast:document.querySelector('#toast')?.textContent||null,errors:window.__jsErrors||[],history:window.RiverviewDiagnostics?.snapshot()||null,requests:window.__fixtureRequests||[]}")
            report["fixture_api_requests"] = requests
            js("const p=document.createElement('a');p.id='download-probe';p.href=URL.createObjectURL(new Blob(['probe'],{type:'application/zip'}));p.download='download-probe.zip';p.textContent='Probe download';p.style.cssText='position:fixed;left:20px;top:20px;z-index:999999;background:#fff;color:#000;padding:12px';document.body.append(p)")
            pointer_click_css("#download-probe")
            time.sleep(1)
            report["probe_download_saved"] = (download_dir/"download-probe.zip").is_file()
            (args.output / "browser-acceptance-debug.json").write_text(json.dumps(report, indent=2)+"\n")
            raise RuntimeError("snapshot_zip_download_timeout")
        archive_toast=js("return document.querySelector('#toast')?.textContent||''")
        report["archive_local_fallback"]={"clear_failure_message":"GitHub archival failed (steward_account_session_required)" in archive_toast,
            "local_zip_downloaded":bool(archives),"github_request_skipped_without_csrf":"/api/v1/snapshot/archive" not in [item.get("path") for item in requests]}
        if args.archive_fixture:
            if args.archive_fixture == "success":
                remote=archive_receipts[0] if archive_receipts else {}
                local_digest=hashlib.sha256(archives[0].read_bytes()).hexdigest() if archives else None
                local_manifest={}
                if archives:
                    with zipfile.ZipFile(archives[0]) as local_bundle:
                        local_manifest=json.loads(local_bundle.read("manifest.json"))
                expected_asset=f"riverview-v1-{local_manifest.get('captured_at','').replace(':','-')}-{local_manifest.get('capture_id','')}.zip"
                report["versioned_archive_identity"]={"manifest_version":local_manifest.get("dashboard_version"),"capture_id_present":bool(local_manifest.get("capture_id")),"local_filename":archives[0].name if archives else None,"archive_asset_name":remote.get("asset_name"),"matching_asset_name":bool(archives and archives[0].name==expected_asset==remote.get("asset_name")),"matching_capture_id":remote.get("capture_id")==local_manifest.get("capture_id"),"matching_dashboard_version":remote.get("dashboard_version")=="v1"}
                delivery_ui=js("return {label:document.querySelector('#snapshot .snapshot-label')?.textContent.trim(),copy:!!document.querySelector('.snapshot-copy-link'),release:[...document.querySelectorAll('#toast a')].some(a=>a.href.includes('github.com/ppow1/Riverview-Diagnostic-Archive/releases/tag/')),download:[...document.querySelectorAll('#toast a')].some(a=>a.download.endsWith('.zip')),pointerEvents:getComputedStyle(document.querySelector('#toast')).pointerEvents,text:document.querySelector('#toast').textContent}")
                js("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.__snapshotClipboard=text}}});document.querySelector('.snapshot-copy-link').click();return true")
                time.sleep(.1)
                copied_url=js("return window.__snapshotClipboard||null")
                report["archive_local_fallback"]={"archive_request_made":len(archive_receipts)>=1,"csrf_present":remote.get("csrf_present"),"authenticated_cookie_present":remote.get("cookie_present"),"local_zip_downloaded":bool(archives),"browser_download_visible":bool(archives),"archive_sha256":remote.get("sha256"),"local_sha256":local_digest,"same_zip_bytes":bool(remote and remote.get("size_bytes")==archives[0].stat().st_size if archives else False),"matching_zip_hashes":bool(local_digest and local_digest==remote.get("sha256")),"confirmed_release_link_visible":delivery_ui["release"],"copy_link_action_visible":delivery_ui["copy"],"copy_link_copied_confirmed_url":copied_url=="https://github.com/ppow1/Riverview-Diagnostic-Archive/releases/tag/rvdiag-20261020T000000Z-0123456789abcdef0123456789abcdef","download_retry_link_visible":delivery_ui["download"],"toast_interactive":delivery_ui["pointerEvents"]=="auto","ui_text":delivery_ui["text"]}
                # Run a second real capture against the synthetic authenticated endpoint and force only its local download trigger to throw.
                js("window.__snapshotNativeAnchorClick=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){if(this.dataset.snapshotDownload)throw new Error('synthetic_local_download_failure');return window.__snapshotNativeAnchorClick.call(this)}")
                try:
                    js("document.querySelector('#snapshot').scrollIntoView({block:'center',inline:'center'})")
                    click_css("#snapshot")
                    failure_deadline=time.monotonic()+300
                    while time.monotonic()<failure_deadline:
                        text_now=js("return document.querySelector('#toast')?.textContent||''")
                        if len(archive_receipts)>=2 and not js("return document.querySelector('#snapshot').disabled") and "browser download could not be started" in text_now:break
                        time.sleep(.25)
                finally:
                    js("HTMLAnchorElement.prototype.click=window.__snapshotNativeAnchorClick;delete window.__snapshotNativeAnchorClick")
                failure_ui=js("return {release:[...document.querySelectorAll('#toast a')].some(a=>a.href.includes('github.com')),download:[...document.querySelectorAll('#toast a')].some(a=>a.download.endsWith('.zip')),text:document.querySelector('#toast').textContent}")
                report["local_download_failure_after_archive"]={"archive_request_made":len(archive_receipts)>=2,"csrf_present":bool(archive_receipts and archive_receipts[-1]["csrf_present"]),"archive_confirmed":"Snapshot archived permanently" in failure_ui["text"],"local_download_requested":not "browser download could not be started" in failure_ui["text"],"release_link":failure_ui["release"],"download_retry_link":failure_ui["download"],"failure_reported":"browser download could not be started" in failure_ui["text"]}
            else:
                expected_archive_error="synthetic_github_failure" if args.archive_fixture=="failure" else "snapshot_archive_invalid_receipt"
                report["archive_local_fallback"]={"archive_request_made":len(archive_receipts)==1,"github_failure_reported":f"GitHub archival failed ({expected_archive_error})" in archive_toast,"local_zip_downloaded":bool(archives),"archive_not_claimed":"Snapshot archived permanently" not in archive_toast,"csrf_present":bool(archive_receipts and archive_receipts[0]["csrf_present"])}
        if args.archive_fixture == "success":
            delivery=report["archive_local_fallback"]
            archive_assertions=[delivery_ui["label"]=="Snapshot",delivery["archive_request_made"],delivery["csrf_present"],delivery["authenticated_cookie_present"],delivery["local_zip_downloaded"],delivery["same_zip_bytes"],delivery["matching_zip_hashes"],delivery["confirmed_release_link_visible"],delivery["copy_link_action_visible"],delivery["copy_link_copied_confirmed_url"],delivery["download_retry_link_visible"],delivery["toast_interactive"],report["versioned_archive_identity"]["manifest_version"]=="v1",report["versioned_archive_identity"]["matching_asset_name"],report["versioned_archive_identity"]["matching_capture_id"],report["versioned_archive_identity"]["matching_dashboard_version"],report["local_download_failure_after_archive"]["archive_request_made"],report["local_download_failure_after_archive"]["csrf_present"],report["local_download_failure_after_archive"]["archive_confirmed"],not report["local_download_failure_after_archive"]["local_download_requested"],report["local_download_failure_after_archive"]["release_link"],report["local_download_failure_after_archive"]["download_retry_link"],report["local_download_failure_after_archive"]["failure_reported"]]
        elif args.archive_fixture == "failure":
            delivery=report["archive_local_fallback"]
            archive_assertions=[delivery["archive_request_made"],delivery["csrf_present"],delivery["github_failure_reported"],delivery["local_zip_downloaded"],delivery["archive_not_claimed"]]
        elif args.archive_fixture == "mismatch":
            delivery=report["archive_local_fallback"]
            archive_assertions=[delivery["archive_request_made"],delivery["csrf_present"],delivery["github_failure_reported"],delivery["local_zip_downloaded"],delivery["archive_not_claimed"]]
        else:
            archive_assertions=[report["archive_local_fallback"]["clear_failure_message"],report["archive_local_fallback"]["local_zip_downloaded"],report["archive_local_fallback"]["github_request_skipped_without_csrf"]]
        archive = archives[0]
        evidence_archive = args.output / "downloads" / archive.name
        evidence_archive.parent.mkdir(mode=0o700, exist_ok=True)
        shutil.copy2(archive, evidence_archive)
        archive = evidence_archive
        report["package_bytes"] = archive.stat().st_size
        def workflow_stem(graph_id):
            return re.sub(r"[^a-zA-Z0-9._-]+", "_", graph_id)

        def workflow_file(graph_id, suffix):
            return f"workflows/{workflow_stem(graph_id)}.{suffix}"

        first_graph_id, second_graph_id = GRAPH_A["graph_id"], GRAPH_B["graph_id"]
        first_page_id, second_page_id = REGISTRY["pages"][0]["id"], REGISTRY["pages"][1]["id"]
        first_jump = next((node for node in GRAPH_A.get("nodes", [])
                           if node.get("type") == "jump" and node.get("jump_target_id")), None)
        expected_edges = sum(len(graph.get("edges", [])) for graph in GRAPHS.values())
        expected_nodes = sum(len(graph.get("nodes", [])) for graph in GRAPHS.values())
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            manifest = json.loads(bundle.read("manifest.json"))
            workflow_index = json.loads(bundle.read("workflows/workflow-index.json"))
            workflow_a_bytes = bundle.read(workflow_file(first_graph_id, "json"))
            workflow_a = json.loads(workflow_a_bytes)
            workflow_b = json.loads(bundle.read(workflow_file(second_graph_id, "json")))
            workflow_status = json.loads(bundle.read(workflow_file(first_graph_id, "status.json")))
            page_inventory = json.loads(bundle.read(f"website/pages/{first_page_id}.json"))
            svg_a = ElementTree.fromstring(bundle.read(workflow_file(first_graph_id, "svg")))
            first_png_path = workflow_file(first_graph_id, "png")
            png_a = bundle.read(first_png_path) if first_png_path in names else b""
            page_a = bundle.read(f"website/pages/{first_page_id}.html").decode()
            page_b = bundle.read(f"website/pages/{second_page_id}.html").decode()
            page_svg_a = ElementTree.fromstring(bundle.read(f"website/pages/{first_page_id}.svg"))
            controls = json.loads(bundle.read("diagnostics/control-coverage.json"))
            browser_history_bytes = bundle.read("diagnostics/browser-history.json")
            browser_history = json.loads(browser_history_bytes)
            interactions = browser_history["interactions"]
            controls = json.loads(bundle.read("diagnostics/control-coverage.json"))
            report["zip_integrity_test"] = bundle.testzip() is None
            json_graphs = [json.loads(bundle.read(entry["json"])) for entry in workflow_index["workflows"]]
            json_node_ids = [node["id"] for graph in json_graphs for node in graph["nodes"]]
            json_edge_ids = [(edge["from"], edge["to"], edge["type"]) for graph in json_graphs for edge in graph["edges"]]
            report["offline_json_node_edge_inventory_reconciles"] = (len(json_node_ids)==workflow_index["node_count"] and len(json_edge_ids)==workflow_index["edge_count"] and len(set(json_node_ids))==len(json_node_ids))
            canonical_json_matches = all(graph == GRAPHS[item["graph_id"]]
                for item, graph in zip(workflow_index["workflows"], json_graphs))
            visual_checks = []
            for item in workflow_index["workflows"]:
                graph = GRAPHS[item["graph_id"]]
                svg = ElementTree.fromstring(bundle.read(item["svg"]))
                png = bundle.read(item["png"]) if item.get("png") in names else b""
                status = json.loads(bundle.read(item["status"]))
                svg_nodes = [node.attrib.get("data-node-id") for node in svg.findall(".//*[@data-node-id]")]
                svg_edges = [(edge.attrib.get("data-edge-from"), edge.attrib.get("data-edge-to"), edge.attrib.get("data-edge-type"))
                             for edge in svg.findall(".//*[@data-edge-from]")]
                graph_edges = [(edge["from"], edge["to"], edge["type"]) for edge in graph.get("edges", [])]
                visual_checks.append(svg_nodes == [node["id"] for node in graph.get("nodes", [])]
                    and svg_edges == graph_edges and (not item.get("png") or png.startswith(b"\x89PNG\r\n\x1a\n"))
                    and status.get("graph_id") == graph["graph_id"])
            archive_payloads=[bundle.read(name) for name in names]
            report["synthetic_cookie_not_exported"] = not any(b"synthetic-only" in value for value in archive_payloads)
            report["manifest_files_valid"] = all(hashlib.sha256(bundle.read(x["path"])).hexdigest()==x["sha256"]
                                                 and len(bundle.read(x["path"]))==x["size_bytes"] for x in manifest["files"])
            report["manifest_capture_complete"] = manifest["capture_complete"]
            captured_pages = [page["id"] for page in REGISTRY["pages"]]
            page_htmls = [bundle.read(f"website/pages/{page}.html").decode() for page in captured_pages]
            page_svg_text = [bundle.read(f"website/pages/{page}.svg").decode() for page in captured_pages]
            page_pngs = [bundle.read(f"website/pages/{page}.png") if f"website/pages/{page}.png" in names else b"" for page in captured_pages]
            page_svgs = [ElementTree.fromstring(bundle.read(f"website/pages/{page}.svg")) for page in captured_pages]
            page_jsons = [json.loads(bundle.read(f"website/pages/{page}.json")) for page in captured_pages]
            report["all_registered_pages_captured"] = (manifest["inventory"]["captured_pages"] == len(captured_pages)
                and all(f"website/pages/{page}.html" in names and f"website/pages/{page}.svg" in names and f"website/pages/{page}.json" in names for page in captured_pages)
                and all(png.startswith(b"\x89PNG\r\n\x1a\n") for png in page_pngs if png))
            report["documentation_full_extent_tiles_complete"] = False
            if "documentation" in captured_pages:
                documentation_capture=json.loads(bundle.read("website/pages/documentation.json"))
                documentation_tiles=documentation_capture["representations"].get("detail_tiles",[])
                report["documentation_full_extent_tiles_complete"]=(not documentation_capture["capture_truncated"]
                    and bool(documentation_tiles) and all(tile in names and bundle.read(tile).startswith(b"\x89PNG\r\n\x1a\n") for tile in documentation_tiles))
            required_dashboard_assets = {"/assets/app.css", "/assets/diagnostic-snapshot.js", "/assets/app.js", "/assets/workflow.js"}
            observed_assets = {item.get("path", "").split("?", 1)[0] for item in requests}
            report["actual_dashboard_assets_served"] = (not args.actual_dashboard_fixture
                or required_dashboard_assets <= observed_assets)
            report["actual_dashboard_page_content_captured"] = (not args.actual_dashboard_fixture
                or ("Operations overview" in page_htmls[0] and 'id="view-overview"' in page_htmls[0]))
            report["page_private_content_redacted"] = all("PRIVATE FIXTURE CONVERSATION" not in value for value in page_htmls)
            report["sensitive_form_value_redacted"] = all("SENSITIVE FIXTURE FORM VALUE" not in value for value in page_htmls + page_svg_text)
            report["page_visuals_are_full_rendered_captures"] = all("<foreignObject" in value and "data-control-id=" in value for value in page_svg_text)
            report["offline_html_is_inert"] = all("<script" not in value.lower() and "href=\"" not in value.lower() and "href='" not in value.lower() for value in page_htmls)
            snapshot_control = next(control["id"] for control in REGISTRY["controls"] if control["id"] == "snapshot.download")
            first_controls = page_jsons[0].get("controls", [])
            report["page_control_correlation"] = (any(item.get("data-control-id") == snapshot_control for image in page_svgs for item in image.findall(".//*[@data-control-id]") )
                and any(item.get("control_id") == snapshot_control for item in first_controls))
        svg_ns = {"s": "http://www.w3.org/2000/svg"}
        svg_nodes = svg_a.findall(".//*[@data-node-id]")
        svg_edges = svg_a.findall(".//*[@data-edge-from]")
        expected_relationships = []
        expected_unresolved = []
        all_node_ids = {node["id"] for graph in GRAPHS.values() for node in graph.get("nodes", [])}
        for graph in GRAPHS.values():
            for node in graph.get("nodes", []):
                if node.get("type") == "jump" and node.get("jump_target_id"):
                    expected_relationships.append((graph["graph_id"], node["id"], node["jump_target_id"]))
                if node.get("type") == "jump" and (not node.get("jump_target_id") or node["jump_target_id"] not in all_node_ids):
                    expected_unresolved.append((graph["graph_id"],"jump_target",node["id"],node.get("jump_target_id")))
            local_node_ids={node["id"] for node in graph.get("nodes", [])}
            for edge in graph.get("edges", []):
                if edge.get("from") not in local_node_ids:
                    expected_unresolved.append((graph["graph_id"],"edge_source",edge.get("from"),edge.get("from")))
                if edge.get("to") not in all_node_ids:
                    expected_unresolved.append((graph["graph_id"],"edge_target",edge.get("from"),edge.get("to")))
        actual_relationships = [(item.get("source_graph_id"), item.get("source_node_id"), item.get("target_node_id"))
                                for item in workflow_index["cross_workflow_relationships"]]
        actual_unresolved = sorted((item.get("graph_id"),item.get("kind"),item.get("source_node_id"),item.get("target_id"))
                                   for item in workflow_index["unresolved_references"])
        report.update({"manifest_workflows": manifest["inventory"]["workflows"], "manifest_nodes": manifest["inventory"]["nodes"],
                       "manifest_edges": manifest["inventory"]["edges"], "workflow_index_relations": workflow_index["cross_workflow_relationships"],
                       "alpha_svg_node_ids": [x.attrib["data-node-id"] for x in svg_nodes],
                       "alpha_svg_edge_count": len(svg_edges), "alpha_png_signature_valid": png_a.startswith(b"\x89PNG\r\n\x1a\n"),
                       "workflow_runtime_status_exported": workflow_status["graph_id"]==first_graph_id and workflow_status["projection"]["status"]=="unknown",
                       "all_workflow_visuals_valid": len(visual_checks)==len(GRAPHS) and all(visual_checks),
                       "all_canonical_workflow_json_matches": canonical_json_matches,
                       "all_registered_pages_captured": report["all_registered_pages_captured"],
                       "page_private_content_redacted": report["page_private_content_redacted"],
                       "offline_html_is_inert": report["offline_html_is_inert"],
                       "sensitive_form_value_redacted": report["sensitive_form_value_redacted"],
                       "page_pngs_complete": report["all_registered_pages_captured"],
                       "page_control_correlation": report["page_control_correlation"],
                       "request_metadata_captured": any(item.get("method")=="POST" and item.get("path")=="/api/v1/objectives/{id}" and item.get("status")==201 and item.get("duration_ms")==37 and item.get("request_id")=="fixture-correlation-17" for item in browser_history["requests"]),
                       "navigation_timing_captured": bool(browser_history.get("navigation_timing")) and all("duration_ms" in item and "url" not in item and "name" not in item for item in browser_history["navigation_timing"]),
                       "diagnostic_privacy_filter_passed": all(secret not in browser_history_bytes for secret in (b"PRIVATE_QUERY",b"PRIVATE_HEADER",b"PRIVATE_REQUEST_BODY")) and all("headers" not in item and "request_body" not in item for item in browser_history["requests"]),
                       "offline_json_node_edge_inventory_reconciles": report["offline_json_node_edge_inventory_reconciles"],
                       "control_coverage_uncovered": controls["counts"]["uncovered"], "captured_interactions": len(interactions),
                       "cross_workflow_target_preserved": bool(first_jump and first_jump["jump_target_id"] in {node["id"] for graph in GRAPHS.values() for node in graph.get("nodes", [])} or first_jump and first_jump["jump_target_id"].rsplit(":",1)[0] in GRAPHS),
                       "cross_workflow_index_complete": sorted(actual_relationships)==sorted(expected_relationships),
                       "workflow_index_unresolved_references_complete": (workflow_index["unresolved_reference_count"]==len(expected_unresolved) and actual_unresolved==sorted(expected_unresolved)),
                       "node_identity_preserved": canonical_json_matches and len(set(json_node_ids))==len(json_node_ids),
                       "edge_identity_preserved": canonical_json_matches,
                       "page_visuals_are_full_rendered_captures": report["page_visuals_are_full_rendered_captures"],
                       "offline_index_has_file_refs": all(x["json"] in names and x["svg"] in names and (not x.get("png") or x["png"] in names) for x in workflow_index["workflows"]),
                       "browser_errors": js("return window.RiverviewDiagnostics.snapshot().errors")})
        if not args.single_capture:
            first_svg_payload = zipfile.ZipFile(archive).read(workflow_file(first_graph_id, "svg"))
            webdriver("POST", f"/session/{session}/window/rect", {"x": 0, "y": 0, "width": 720, "height": 500})
            second_view = js("window.scrollTo(0,document.body.scrollHeight);return {width:innerWidth,scroll_y:scrollY}")
            existing_downloads = {item.name for item in download_dir.glob("*.zip")}
            js("document.querySelector('#snapshot').scrollIntoView({block:'center',inline:'center'})")
            click_css("#snapshot")
            second_deadline = time.monotonic() + 180
            second_archives = []
            while time.monotonic() < second_deadline:
                second_archives = [item for item in download_dir.glob("*.zip") if item.name not in existing_downloads]
                if second_archives and not list(download_dir.glob("*.part")):
                    break
                time.sleep(.25)
            if not second_archives:
                raise RuntimeError("second_viewport_snapshot_timeout")
            second_archive = max(second_archives, key=lambda item: item.stat().st_mtime_ns)
            second_evidence = args.output / "downloads" / "viewport-2.zip"
            shutil.copy2(second_archive, second_evidence)
            with zipfile.ZipFile(second_archive) as second_bundle:
                second_svg_payload = second_bundle.read(workflow_file(first_graph_id, "svg"))
                second_manifest=json.loads(second_bundle.read("manifest.json"))
                second_documentation=json.loads(second_bundle.read("website/pages/documentation.json"))
            report["second_capture"] = {"viewport": second_view, "package_bytes": second_archive.stat().st_size,
                "workflow_svg_matches_first_viewport": second_svg_payload == first_svg_payload,
                "workflow_json_matches_first_viewport": zipfile.ZipFile(second_archive).read(workflow_file(first_graph_id, "json")) == workflow_a_bytes,
                "manifest_capture_complete": second_manifest["capture_complete"],
                "documentation_capture_complete": not second_documentation["capture_truncated"] and second_documentation["visual_status"]=="complete",
                "documentation_detail_tile_count": len(second_documentation["representations"].get("detail_tiles",[]))}
            report["workflow_visual_independent_of_viewport_and_scroll"] = (report["second_capture"]["viewport"]["width"] < 1280 and report["second_capture"]["viewport"]["scroll_y"] > 0 and report["second_capture"]["workflow_svg_matches_first_viewport"] and report["second_capture"]["workflow_json_matches_first_viewport"])
        report["passed"] = all([report["zip_integrity_test"], report["manifest_files_valid"],
            report["manifest_workflows"]==len(GRAPHS), report["manifest_nodes"]==expected_nodes, report["manifest_edges"]==expected_edges,
            report["alpha_svg_edge_count"]==len(GRAPH_A.get("edges", [])),
            report["alpha_png_signature_valid"], report["page_private_content_redacted"],
            report["sensitive_form_value_redacted"], report["page_pngs_complete"],
            report["captured_interactions"]>=2, report["cross_workflow_target_preserved"],
            report["cross_workflow_index_complete"], report["workflow_index_unresolved_references_complete"], report["node_identity_preserved"], report["edge_identity_preserved"], report["all_canonical_workflow_json_matches"], report["page_visuals_are_full_rendered_captures"], report["offline_index_has_file_refs"], report["offline_json_node_edge_inventory_reconciles"], report["page_control_correlation"], report["workflow_runtime_status_exported"], report["synthetic_cookie_not_exported"], report["all_workflow_visuals_valid"], report["offline_html_is_inert"], not report["browser_errors"], *archive_assertions])
        report["passed"] = bool(report["passed"] and all(report["workflow_viewer"][key] for key in ("initial_fit_applied","zoom_in_increased_scale","reset_restored_unit_scale","fit_button_restored_fit","pan_changed_transform","fullscreen_behavior_ok")))
        (args.output / "browser-acceptance.json").write_text(json.dumps(report, indent=2)+"\n")
        report["package_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        if not args.single_capture:
            report["passed"] = bool(report["passed"] and report["workflow_visual_independent_of_viewport_and_scroll"])
        report["passed"] = bool(report["passed"] and report["request_metadata_captured"] and report["navigation_timing_captured"] and report["diagnostic_privacy_filter_passed"])
        report["passed"] = bool(report["passed"] and report["actual_dashboard_assets_served"] and report["actual_dashboard_page_content_captured"])
        if args.package_bound_stress_fixture:
            report["stress_hook_loaded"] = js("return window.__snapshotStressHook === true")
        if args.package_bound_stress_fixture:
            with zipfile.ZipFile(archive) as bundle:
                names = set(bundle.namelist())
                uncompressed_bytes = sum(entry.file_size for entry in bundle.infolist())
                non_raster_bytes = sum(entry.file_size for entry in bundle.infolist() if not entry.filename.endswith(".png"))
                page_refs_valid = all((not item["representations"].get("png") or item["representations"]["png"] in names)
                                      and all(path in names for path in item["representations"].get("detail_tiles", []))
                                      for item in page_jsons)
                workflow_refs_valid = all(item["json"] in names and item["svg"] in names and item["status"] in names
                                          and (not item.get("png") or item["png"] in names)
                                          and all(path in names for path in item.get("detail_tiles", []))
                                          for item in workflow_index["workflows"])
                diagnostic_members_present = all(path in names for path in (
                    "manifest.json", "website/capabilities.json", "diagnostics/operational-snapshot.json",
                    "diagnostics/browser-history.json", "diagnostics/control-coverage.json",
                    "workflows/workflow-index.json"))
            omitted = manifest["package_bounds"].get("omitted_raster_visual_count", 0)
            raster_omissions = [item for item in manifest["omissions"] if item.get("kind") == "raster_visual"]
            omission_paths = [item["path"] for item in raster_omissions]
            report["package_bound_stress"] = {"current_limit_bytes": manifest["package_bounds"]["max_uncompressed_bytes"],
                "uncompressed_archive_bytes": uncompressed_bytes, "omitted_raster_visual_count": omitted,
                "manifest_lists_visual_omissions": any(item.get("kind") == "raster_visual" for item in manifest["omissions"]),
                "raster_budget_respected": manifest["package_bounds"]["raster_visual_bytes"] <= manifest["package_bounds"]["raster_visual_budget_bytes"],
                "structured_and_manifest_reserves_respected": non_raster_bytes <= manifest["package_bounds"]["structured_reserve_bytes"] + manifest["package_bounds"]["manifest_reserve_bytes"],
                "omitted_paths_absent_from_archive": len(omission_paths) == len(set(omission_paths)) and all(path not in names for path in omission_paths),
                "canonical_page_and_workflow_references_valid": page_refs_valid and workflow_refs_valid,
                "diagnostic_members_present": diagnostic_members_present,
                "capture_complete_truthfully_false": manifest["capture_complete"] is False}
            report["passed"] = all([report["zip_integrity_test"], report["manifest_files_valid"],
                report["package_bytes"] < manifest["package_bounds"]["max_uncompressed_bytes"], omitted > 0,
                report["package_bound_stress"]["manifest_lists_visual_omissions"],
                report["package_bound_stress"]["raster_budget_respected"],
                report["package_bound_stress"]["structured_and_manifest_reserves_respected"],
                report["package_bound_stress"]["omitted_paths_absent_from_archive"],
                report["stress_hook_loaded"],
                report["package_bound_stress"]["canonical_page_and_workflow_references_valid"],
                report["package_bound_stress"]["diagnostic_members_present"],
                report["package_bound_stress"]["capture_complete_truthfully_false"],
                report["all_canonical_workflow_json_matches"], report["offline_json_node_edge_inventory_reconciles"],
                report["page_private_content_redacted"], report["sensitive_form_value_redacted"],
                report["synthetic_cookie_not_exported"], report["diagnostic_privacy_filter_passed"],
                *archive_assertions])
        elif args.actual_dashboard_fixture:
            report["passed"] = bool(report["passed"] and report.get("manifest_capture_complete")
                and report.get("documentation_full_extent_tiles_complete")
                and (args.single_capture or report["second_capture"].get("manifest_capture_complete"))
                and (args.single_capture or report["second_capture"].get("documentation_capture_complete")))
        report["package_file"] = f"downloads/{archive.name}"
        (args.output / "snapshot.zip.sha256").write_text(report["package_sha256"]+"  "+archive.name+"\n")
        (args.output / "browser-acceptance.json").write_text(json.dumps(report, indent=2)+"\n")
        return 0 if report["passed"] else 1
    finally:
        if session:
            try:
                webdriver("DELETE", f"/session/{session}")
            except Exception:
                pass
        driver.terminate()
        try:
            driver.wait(timeout=5)
        except subprocess.TimeoutExpired:
            driver.kill()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
