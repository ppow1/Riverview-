# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_v2_manual_image_generation_browser.py
# Component: V2-MANUAL-IMAGE-GENERATION
# Revision: 1.0.5
# Purpose: Exercise the authenticated V2 manual image flow with a local API fixture
# Execution Model: Starts a temporary local HTTP fixture and isolated headless Firefox
# Observability: JSON report with route, form, preview, download, and browser-error results
# Dependencies: Python 3.10+, Firefox, geckodriver
# Authority: Synthetic fixture only; does not use production credentials or ComfyUI
# Changed: 2026-10-23 UTC | RV-V2-MANUAL-IMAGE-GENERATION-248 | Initial browser acceptance harness.
# Contracts: docs/components/RIVERVIEW_V2_MANUAL_IMAGE_GENERATION.md
# Tests: scripts/verify_v2_manual_image_generation_browser.py
# History: Git and revision/backup manifest
# =============================================================================
"""Run V2's actual manual-image UI against a bounded local account/API fixture."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg==")
REQUEST = {"record": None, "post": None, "downloads": 0}


class BrowserFixture(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def json(self, status, value):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/v1/auth/session":
            self.json(200, {"identity": {"account_id": "fixture-operator", "email": "operator@example.test", "roles": ["operator"]}})
            return
        if self.path == "/api/v1/manual-image-generations/catalog":
            self.json(200, {"schema_version": "rv.manual-image.catalog.v1", "gpu_selection_supported": False,
                "gpu_selection_reason": "Fixture: per-request allocation is disabled.",
                "worker": {"status": "ready", "device": {"name": "Fixture GPU", "gpu_uuid": None}},
                "workflows": [{"workflow_id": "fixture-dynamic-workflow.v9", "revision": "fixture-rev-9",
                    "parameters": [{"name": "prompt", "type": "text", "max_length": 500},
                                  {"name": "seed", "type": "integer", "min": 0, "max": 999999999, "default": 7}],
                    "fixed_resolution": {"width": 512, "height": 512}, "output_nodes": ["9"]}]})
            return
        if self.path == "/api/v1/resources/telemetry":
            self.json(200, {"hosts": []})
            return
        if self.path == "/api/v1/manual-image-generations?limit=50":
            self.json(200, {"items": [REQUEST["record"]] if REQUEST["record"] else []})
            return
        if REQUEST["record"] and self.path == "/api/v1/manual-image-generations/" + REQUEST["record"]["request_id"]:
            self.json(200, REQUEST["record"])
            return
        if REQUEST["record"] and self.path.startswith("/api/v1/manual-image-generations/") and "/image" in self.path:
            REQUEST["downloads"] += 1
            disposition = "attachment" if "download=1" in self.path else "inline"
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(PNG)))
            self.send_header("Content-Disposition", disposition + '; filename="fixture.png"')
            self.send_header("X-Content-SHA256", hashlib.sha256(PNG).hexdigest())
            self.end_headers()
            self.wfile.write(PNG)
            return
        rel = "index.html" if self.path == "/" else self.path.lstrip("/")
        path = (ROOT / "website/v2/deployed" / rel).resolve()
        static_root = (ROOT / "website/v2/deployed").resolve()
        if not path.is_relative_to(static_root) or not path.is_file():
            self.send_error(404)
            return
        raw = path.read_bytes()
        kind = "text/html; charset=utf-8" if path.suffix == ".html" else "text/css; charset=utf-8" if path.suffix == ".css" else "text/javascript; charset=utf-8" if path.suffix == ".js" else "image/svg+xml"
        self.send_response(200)
        self.send_header("Set-Cookie", "rv_account_csrf=fixture-csrf; Path=/; SameSite=Strict")
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.path != "/api/v1/manual-image-generations":
            self.send_error(404)
            return
        if self.headers.get("X-Riverview-CSRF") != "fixture-csrf":
            self.json(403, {"error": "csrf_required"})
            return
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        REQUEST["post"] = data
        rid = data["request_id"]
        REQUEST["record"] = {"request_id": rid, "actor_id": "fixture-operator", "execution_kind": "operator_manual",
            "status": "complete", "workflow_id": data["workflow_id"], "workflow_revision": "fixture-rev-9",
            "parameters": data["parameters"], "elapsed_seconds": 1.25, "created_at": "2026-10-23T00:00:00Z",
            "verification": {"decision": "ACCEPTED"}, "worker": {"device": {"name": "Fixture GPU"}},
            "artifact": {"download_url": f"/api/v1/manual-image-generations/{rid}/image", "absolute_path": "/tmp/fixture/manual.png",
                "host": "fixture-host", "media_type": "image/png", "size_bytes": len(PNG), "sha256": hashlib.sha256(PNG).hexdigest(),
                "width": 1, "height": 1, "device": {"name": "Fixture GPU", "gpu_uuid": None}}}
        self.json(202, {"request_id": rid, "status": "queued"})


def request(port, path, payload=None, method=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"webdriver_http_{exc.code}") from None


def main():
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0)); port = reserve.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), BrowserFixture)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True); server_thread.start()
    with tempfile.TemporaryDirectory(prefix="rv-v2-manual-image-") as temp:
        downloads = Path(temp) / "downloads"; downloads.mkdir()
        driver_port = port + 1
        driver = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(driver_port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        session = None
        try:
            for _ in range(100):
                if driver.poll() is not None: raise RuntimeError("geckodriver_stopped")
                try: request(driver_port, "/status"); break
                except (OSError, urllib.error.URLError): time.sleep(.1)
            else: raise RuntimeError("geckodriver_start_timeout")
            caps = {"alwaysMatch": {"browserName": "firefox", "moz:firefoxOptions": {
                "args": ["-headless"], "prefs": {"pdfjs.disabled": True}}}}
            session = request(driver_port, "/session", {"capabilities": caps})["value"]["sessionId"]
            def js(script, args=None): return request(driver_port, f"/session/{session}/execute/sync", {"script": script, "args": args or []})["value"]
            request(driver_port, f"/session/{session}/url", {"url": f"http://127.0.0.1:{port}/"})
            js("document.cookie='rv_account_session=fixture-session; Path=/; SameSite=Strict';window.__browserErrors=[];addEventListener('error',e=>window.__browserErrors.push(e.message||'error'))")
            request(driver_port, f"/session/{session}/refresh", {})
            deadline = time.time() + 10
            while time.time() < deadline and js("return document.getElementById('manual-image-workflow').value !== 'fixture-dynamic-workflow.v9'"):
                time.sleep(.1)
            js("document.querySelector('[data-view=\"image-generation\"]').click()")
            js("document.querySelector('#manual-image-parameters [data-parameter=prompt]').value='A small red cube on a plain white background';document.querySelector('#manual-image-parameters [data-parameter=seed]').value='7'")
            js("document.querySelector('#manual-image-form').requestSubmit()")
            deadline = time.time() + 15
            while time.time() < deadline and not js("return !!document.querySelector('#manual-image-preview img')"):
                time.sleep(.1)
            report = js("return {title:document.title,workflow:document.querySelector('#manual-image-workflow').value,seed:document.querySelector('#manual-image-parameters [data-parameter=seed]').value,prompt:document.querySelector('#manual-image-parameters [data-parameter=prompt]').value,gpuDisabled:document.querySelector('#manual-image-gpu-select').disabled,preview:!!document.querySelector('#manual-image-preview img'),previewWidth:document.querySelector('#manual-image-preview img')?.naturalWidth,previewHeight:document.querySelector('#manual-image-preview img')?.naturalHeight,download:document.querySelector('.manual-image-download')?.getAttribute('href'),csrf:document.cookie.includes('rv_account_csrf=fixture-csrf'),errors:window.__browserErrors}")
            link = js("return document.querySelector('.manual-image-download')?.getAttribute('href')")
            report["download_response"] = js("return fetch(document.querySelector('.manual-image-download').href,{credentials:'same-origin'}).then(async r=>({status:r.status,bytes:(await r.arrayBuffer()).byteLength,sha256:r.headers.get('X-Content-SHA256')}))")
            report["downloaded_file_bytes"] = report["download_response"]["bytes"]
            report["download_requests"] = REQUEST["downloads"]
            report["submission"] = REQUEST["post"]
            print(json.dumps(report, sort_keys=True))
            if (not report["preview"] or report["previewWidth"] != 1 or report["previewHeight"] != 1
                or not report["gpuDisabled"] or not report["csrf"] or not REQUEST["post"]
                or REQUEST["post"].get("workflow_id") != "fixture-dynamic-workflow.v9"
                or REQUEST["post"].get("parameters") != {"prompt":"A small red cube on a plain white background","seed":7}
                or report["downloaded_file_bytes"] != len(PNG) or report["errors"]):
                raise RuntimeError("manual_image_browser_acceptance_failed")
        finally:
            if session:
                try: request(driver_port, f"/session/{session}", None, method="DELETE")
                except Exception: pass
            driver.terminate()
            try: driver.wait(timeout=5)
            except subprocess.TimeoutExpired: driver.kill(); driver.wait(timeout=5)
    server.shutdown(); server.server_close(); server_thread.join(timeout=2)


if __name__ == "__main__":
    main()
