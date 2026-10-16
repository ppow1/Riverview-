# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_diagnostic_snapshot_browser.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.0
# Purpose: Verify one-click offline diagnostic ZIP in isolated Firefox with synthetic read-only APIs
# Execution Model: Request-driven isolated fixture; owns only a temporary HTTP server and geckodriver
# Observability: Sanitized JSON report and downloaded ZIP; no real account or production data
# Dependencies: Python 3.10+, Firefox, geckodriver
# Authority: Synthetic cookie fixture only; all fixture data are read-only
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Verify complete workflow, page, privacy, and offline package contracts
# Tests: scripts/verify_diagnostic_snapshot_browser.py
# History: Git
"""Exercise the downloadable diagnostic snapshot without connecting to Riverview services."""
from __future__ import annotations

import hashlib
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
        {"id": "beta", "title": "Beta page", "selector": "#view-beta", "navigation_selector": "[data-view='beta']", "components": ["fixture"], "data_sources": [], "representations": []}],
    "controls": [
        {"id": "navigation.alpha", "selector": "[data-view='alpha']", "action": "Show alpha page"},
        {"id": "navigation.beta", "selector": "[data-view='beta']", "action": "Show beta page"},
        {"id": "snapshot.download", "selector": "#snapshot", "action": "Download snapshot"},
        {"id": "alpha.action", "selector": "#alpha-action", "action": "Synthetic page control"},
        {"id": "beta.input", "selector": "#fixture-input", "action": "Synthetic form control"}],
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
    args = parser.parse_args()
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
    if args.output.exists():
        raise SystemExit("output_directory_must_not_exist")
    args.output.mkdir(parents=True, mode=0o700)
    os.chmod(args.output, 0o700)
    download_dir = Path.home() / "Downloads" / f"rv-snapshot-fixture-{args.output.name}"
    download_dir.mkdir(mode=0o700, parents=True)
    requests = []
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
            view_html.append(f'<section class="view{active}" id="view-{page_id}" aria-label="{page_meta["title"]}"{hidden}><h1>{page_meta["title"]}</h1>{fixture_controls}{private}{sensitive}</section>')
        page = (
            '''<!doctype html><html lang="en"><head><meta charset="utf-8">
            <meta name="viewport" content="width=device-width"><title>Snapshot full source fixture</title>
            <style>.shell{font:16px Arial;background:#112;color:#fff;width:900px;min-height:1600px;display:grid;grid-template-columns:220px 1fr}.rail{padding:15px;display:grid;align-content:start;gap:6px}.view{padding:30px;min-height:400px;background:#223}.snapshot-banner{padding:8px}button{padding:10px}</style>
            <script>window.__jsErrors=[];addEventListener("error",e=>window.__jsErrors.push(String(e.message||"error")));addEventListener("unhandledrejection",()=>window.__jsErrors.push("rejection"));</script>
            <script src="/assets/diagnostic-snapshot.js" defer></script><script>
            window.RiverviewSnapshotApi=async path=>{const r=await fetch(path,{credentials:"same-origin"});if(!r.ok)throw new Error("http_"+r.status);return r.json()};
            document.addEventListener("click",e=>{const nav=e.target.closest("[data-view]");if(nav){document.querySelectorAll(".view").forEach(x=>{x.hidden=x.id!=="view-"+nav.dataset.view;x.classList.toggle("active",!x.hidden)});history.replaceState(null,"","#"+nav.dataset.view)}});</script></head><body>
            <div class="shell"><nav class="rail">''' + "".join(nav_html) +
            '<button id="snapshot">Download Snapshot</button></nav>' + "".join(view_html) + '</div></body></html>'
        ).encode()
    else:
        page = b'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Snapshot fixture</title>
        <style>.shell{font:16px Arial;background:#112;color:#fff;width:900px;min-height:1600px}.rail{padding:15px}.view{padding:30px;min-height:400px;background:#223}.snapshot-banner{padding:8px}button{padding:10px}</style>
        <script>window.__jsErrors=[];addEventListener('error',e=>window.__jsErrors.push(String(e.message||'error')));addEventListener('unhandledrejection',()=>window.__jsErrors.push('rejection'));</script>
        <script src="/assets/diagnostic-snapshot.js" defer></script><script>
        window.RiverviewSnapshotApi=async path=>{const r=await fetch(path,{credentials:'same-origin'});if(!r.ok)throw new Error('http_'+r.status);return r.json()};
        document.addEventListener('click',e=>{const nav=e.target.closest('[data-view]');if(nav){document.querySelectorAll('.view').forEach(x=>{x.hidden=x.id!=='view-'+nav.dataset.view;x.classList.toggle('active',!x.hidden)});history.replaceState(null,'','#'+nav.dataset.view)}});
        </script><div class="shell"><nav class="rail"><button data-view="alpha">Alpha</button><button data-view="beta">Beta</button><button id="snapshot">Download Snapshot</button></nav>
        <section class="view active" id="view-alpha" aria-label="Alpha page"><h1>Alpha</h1><button id="alpha-action">Alpha action</button><div class="conversation-timeline">PRIVATE FIXTURE CONVERSATION MUST NOT EXPORT</div></section>
        <section class="view" id="view-beta" aria-label="Beta page" hidden><h1>Beta</h1><input id="fixture-input" value="SENSITIVE FIXTURE FORM VALUE"></section></div>'''


    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def send_body(self, status, body, content_type="application/json; charset=utf-8", extra=()):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for key, value in extra:
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            requests.append({"path": self.path, "cookie_present": bool(self.headers.get("Cookie"))})
            if self.path == "/":
                return self.send_body(200, page, "text/html; charset=utf-8")
            if self.path == "/assets/diagnostic-snapshot.js":
                return self.send_body(200, ASSET.read_bytes(), "text/javascript; charset=utf-8")
            if self.path == "/assets/app.css":
                return self.send_body(200, b"body{background:#111;color:#eee}.view{display:block}", "text/css; charset=utf-8")
            if self.path == "/signin":
                return self.send_body(200, b"ok", extra=(("Set-Cookie", "rv_account_session=synthetic-only; Path=/; SameSite=Strict"),))
            if not self.headers.get("Cookie", "").startswith("rv_account_session=synthetic-only"):
                return self.send_body(401, b'{"error":"authentication_required"}')
            values = {"/api/v1/capabilities": REGISTRY, "/api/v1/snapshot": SNAPSHOT,
                      "/api/v1/snapshot/workflow-index": index}
            if self.path in values:
                return self.send_body(200, json.dumps(values[self.path]).encode())
            if self.path.startswith("/api/v1/graphs/"):
                from urllib.parse import unquote
                graph_id = unquote(self.path.removeprefix("/api/v1/graphs/"))
                graph = GRAPHS.get(graph_id)
                if graph is None:
                    return self.send_body(404, b'{"error":"not_found"}')
                return self.send_body(200, json.dumps({"graph": {**graph, "execution_position": {"status": "unknown"}}}).encode())
            return self.send_body(404, b'{"error":"not_found"}')

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

    report = {"schema_version": "rv.website.snapshot-browser-verification.v1", "synthetic_fixture_only": True,
              "production_data_accessed": False, "production_mutations": False, "api_requests": requests,
              "expected_workflows": 2, "expected_nodes": 3, "expected_edges": 2}
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
        webdriver("POST", f"/session/{session}/url", {"url": f"http://127.0.0.1:{server.server_port}/"})
        for _ in range(100):
            if js("return !!window.RiverviewSnapshot && !!window.RiverviewSnapshotApi"):
                break
            time.sleep(.1)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/v1/capabilities")
            unauthorized=200
        except urllib.error.HTTPError as error:
            unauthorized=error.code
        report["unauthenticated_registry_status"] = unauthorized
        webdriver("POST", f"/session/{session}/url", {"url": f"http://127.0.0.1:{server.server_port}/signin"})
        webdriver("POST", f"/session/{session}/url", {"url": f"http://127.0.0.1:{server.server_port}/"})
        first_page_id, second_page_id = REGISTRY["pages"][0]["id"], REGISTRY["pages"][1]["id"]
        js("document.querySelector(arguments[0]).click();document.querySelector(arguments[1]).click();".replace("arguments[0]", json.dumps(REGISTRY["pages"][1]["navigation_selector"])).replace("arguments[1]", json.dumps(REGISTRY["pages"][0]["navigation_selector"])))
        time.sleep(.1)
        snapshot_element = webdriver("POST", f"/session/{session}/element", {"using": "css selector", "value": "#snapshot"})["value"]["element-6066-11e4-a52e-4f735466cecf"]
        webdriver("POST", f"/session/{session}/element/{snapshot_element}/click", {})
        deadline = time.monotonic() + 18
        archives = []
        while time.monotonic() < deadline:
            archives = list(download_dir.glob("*.zip"))
            if archives and not list(download_dir.glob("*.part")):
                break
            time.sleep(.25)
        if not archives:
            report["debug"] = js("return {loaded:!!window.RiverviewSnapshot,phase:window.__snapshotPhase,lastError:window.__snapshotLastError||null,package:window.__snapshotPackage||null,api:!!window.RiverviewSnapshotApi,toast:document.querySelector('#toast')?.textContent||null,errors:window.__jsErrors||[],history:window.RiverviewDiagnostics?.snapshot()||null,requests:window.__fixtureRequests||[]}")
            report["fixture_api_requests"] = requests
            js("const p=document.createElement('a');p.id='download-probe';p.href=URL.createObjectURL(new Blob(['probe'],{type:'application/zip'}));p.download='download-probe.zip';p.textContent='Probe download';document.body.append(p)")
            probe_id=webdriver("POST",f"/session/{session}/element",{"using":"css selector","value":"#download-probe"})["value"]["element-6066-11e4-a52e-4f735466cecf"]
            webdriver("POST",f"/session/{session}/element/{probe_id}/click",{})
            time.sleep(1)
            report["probe_download_saved"] = (download_dir/"download-probe.zip").is_file()
            (args.output / "browser-acceptance-debug.json").write_text(json.dumps(report, indent=2)+"\n")
            raise RuntimeError("snapshot_zip_download_timeout")
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
            png_a = bundle.read(workflow_file(first_graph_id, "png"))
            page_a = bundle.read(f"website/pages/{first_page_id}.html").decode()
            page_b = bundle.read(f"website/pages/{second_page_id}.html").decode()
            page_svg_a = ElementTree.fromstring(bundle.read(f"website/pages/{first_page_id}.svg"))
            controls = json.loads(bundle.read("diagnostics/control-coverage.json"))
            interactions = json.loads(bundle.read("diagnostics/browser-history.json"))["interactions"]
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
                png = bundle.read(item["png"])
                status = json.loads(bundle.read(item["status"]))
                svg_nodes = [node.attrib.get("data-node-id") for node in svg.findall(".//*[@data-node-id]")]
                svg_edges = [(edge.attrib.get("data-edge-from"), edge.attrib.get("data-edge-to"), edge.attrib.get("data-edge-type"))
                             for edge in svg.findall(".//*[@data-edge-from]")]
                graph_edges = [(edge["from"], edge["to"], edge["type"]) for edge in graph.get("edges", [])]
                visual_checks.append(svg_nodes == [node["id"] for node in graph.get("nodes", [])]
                    and svg_edges == graph_edges and png.startswith(b"\x89PNG\r\n\x1a\n")
                    and status.get("graph_id") == graph["graph_id"])
            archive_payloads=[bundle.read(name) for name in names]
            report["synthetic_cookie_not_exported"] = not any(b"synthetic-only" in value for value in archive_payloads)
            report["manifest_files_valid"] = all(hashlib.sha256(bundle.read(x["path"])).hexdigest()==x["sha256"]
                                                 and len(bundle.read(x["path"]))==x["size_bytes"] for x in manifest["files"])
            captured_pages = [page["id"] for page in REGISTRY["pages"]]
            page_htmls = [bundle.read(f"website/pages/{page}.html").decode() for page in captured_pages]
            page_pngs = [bundle.read(f"website/pages/{page}.png") for page in captured_pages]
            page_svgs = [ElementTree.fromstring(bundle.read(f"website/pages/{page}.svg")) for page in captured_pages]
            page_jsons = [json.loads(bundle.read(f"website/pages/{page}.json")) for page in captured_pages]
            report["all_registered_pages_captured"] = (manifest["inventory"]["captured_pages"] == len(captured_pages)
                and all(f"website/pages/{page}.png" in names and f"website/pages/{page}.svg" in names for page in captured_pages)
                and all(png.startswith(b"\x89PNG\r\n\x1a\n") for png in page_pngs))
            report["page_private_content_redacted"] = all("PRIVATE FIXTURE CONVERSATION" not in value for value in page_htmls)
            report["sensitive_form_value_redacted"] = all("SENSITIVE FIXTURE FORM VALUE" not in value for value in page_htmls)
            report["offline_html_is_inert"] = all("<script" not in value.lower() and "href=\"" not in value.lower() and "href='" not in value.lower() for value in page_htmls)
            snapshot_control = next(control["id"] for control in REGISTRY["controls"] if control["id"] == "snapshot.download")
            first_controls = page_jsons[0].get("controls", [])
            report["page_control_correlation"] = (any(item.get("data-control-id") == snapshot_control for image in page_svgs for item in image.findall(".//*[@data-control-id]") )
                and any(item.get("control_id") == snapshot_control for item in first_controls))
        svg_ns = {"s": "http://www.w3.org/2000/svg"}
        svg_nodes = svg_a.findall(".//*[@data-node-id]")
        svg_edges = svg_a.findall(".//*[@data-edge-from]")
        expected_relationships = []
        for graph in GRAPHS.values():
            for node in graph.get("nodes", []):
                if node.get("type") == "jump" and node.get("jump_target_id"):
                    expected_relationships.append((graph["graph_id"], node["id"], node["jump_target_id"]))
        actual_relationships = [(item.get("source_graph_id"), item.get("source_node_id"), item.get("target_node_id"))
                                for item in workflow_index["cross_workflow_relationships"]]
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
                       "offline_json_node_edge_inventory_reconciles": report["offline_json_node_edge_inventory_reconciles"],
                       "control_coverage_uncovered": controls["counts"]["uncovered"], "captured_interactions": len(interactions),
                       "cross_workflow_target_preserved": bool(first_jump and first_jump["jump_target_id"] in {node["id"] for graph in GRAPHS.values() for node in graph.get("nodes", [])} or first_jump and first_jump["jump_target_id"].rsplit(":",1)[0] in GRAPHS),
                       "cross_workflow_index_complete": sorted(actual_relationships)==sorted(expected_relationships),
                       "node_identity_preserved": all(graph["nodes"] and workflow_b.get("nodes") for graph in [GRAPH_B]),
                       "offline_index_has_file_refs": all(x["json"] in names and x["svg"] in names and x["png"] in names for x in workflow_index["workflows"]),
                       "browser_errors": js("return window.RiverviewDiagnostics.snapshot().errors")})
        first_svg_payload = zipfile.ZipFile(archive).read(workflow_file(first_graph_id, "svg"))
        webdriver("POST", f"/session/{session}/window/rect", {"x": 0, "y": 0, "width": 720, "height": 500})
        second_view = js("window.scrollTo(0,document.body.scrollHeight);return {width:innerWidth,scroll_y:scrollY}")
        existing_downloads = {item.name for item in download_dir.glob("*.zip")}
        snapshot_element = webdriver("POST", f"/session/{session}/element", {"using": "css selector", "value": "#snapshot"})["value"]["element-6066-11e4-a52e-4f735466cecf"]
        webdriver("POST", f"/session/{session}/element/{snapshot_element}/click", {})
        second_deadline = time.monotonic() + 30
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
        report["second_capture"] = {"viewport": second_view, "package_bytes": second_archive.stat().st_size,
            "workflow_svg_matches_first_viewport": second_svg_payload == first_svg_payload,
            "workflow_json_matches_first_viewport": zipfile.ZipFile(second_archive).read(workflow_file(first_graph_id, "json")) == workflow_a_bytes}
        report["workflow_visual_independent_of_viewport_and_scroll"] = (report["second_capture"]["viewport"]["width"] < 1280 and report["second_capture"]["viewport"]["scroll_y"] > 0 and report["second_capture"]["workflow_svg_matches_first_viewport"] and report["second_capture"]["workflow_json_matches_first_viewport"])
        report["passed"] = all([report["zip_integrity_test"], report["manifest_files_valid"],
            report["manifest_workflows"]==len(GRAPHS), report["manifest_nodes"]==expected_nodes, report["manifest_edges"]==expected_edges,
            report["alpha_svg_edge_count"]==len(GRAPH_A.get("edges", [])),
            report["alpha_png_signature_valid"], report["page_private_content_redacted"],
            report["sensitive_form_value_redacted"], report["page_pngs_complete"],
            report["captured_interactions"]>=2, report["cross_workflow_target_preserved"],
            report["cross_workflow_index_complete"], report["node_identity_preserved"], report["all_canonical_workflow_json_matches"], report["offline_index_has_file_refs"], report["offline_json_node_edge_inventory_reconciles"], report["page_control_correlation"], report["workflow_runtime_status_exported"], report["synthetic_cookie_not_exported"], report["all_workflow_visuals_valid"], report["offline_html_is_inert"], not report["browser_errors"]])
        (args.output / "browser-acceptance.json").write_text(json.dumps(report, indent=2)+"\n")
        report["package_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        report["passed"] = bool(report["passed"] and report["workflow_visual_independent_of_viewport_and_scroll"])
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
