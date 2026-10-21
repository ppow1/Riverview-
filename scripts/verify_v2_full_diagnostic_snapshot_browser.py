#!/usr/bin/env python3
# Riverview~ Controlled Source
# File: scripts/verify_v2_full_diagnostic_snapshot_browser.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.0
# Purpose: Verify full V2 screen/workflow capture, authenticated archive receipt, and identical browser download
# Execution Model: Isolated HTTP fixture with headless Chrome CDP
# Observability: ZIPs, hashes, archive receipt, browser state, and JSON evidence report
# Dependencies: Python 3.10+, Node.js ws module, Google Chrome
# Authority: Synthetic local Steward session only; no production credential or repository upload
# Tests: tests/test_v2_workspace_shell.py
# History: Git and revision/backup manifest
"""Run actual V2 browser capture against a controlled authenticated archive fixture."""
import argparse
import hashlib
import http.server
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.v2_snapshot_acceptance import validate_v2_full_diagnostic_archive
NODE = r'''const fs=require('fs'),http=require('http'),WebSocket=require('ws');
const profile=process.env.RV_PROFILE,downloads=process.env.RV_DOWNLOADS;let child,socket,seq=0;const pending=new Map(),events=[];
function waitFile(path,ms){return new Promise((resolve,reject)=>{const start=Date.now(),timer=setInterval(()=>{if(fs.existsSync(path)){clearInterval(timer);resolve(fs.readFileSync(path,'utf8').trim().split(/\s+/)[0]);}else if(Date.now()-start>ms){clearInterval(timer);reject(Error('chrome_start_timeout'));}},100);});}
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(Error('cdp_timeout_'+method));}},20000);});}
async function evaluate(expression,awaitPromise=true){const out=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise});if(out.exceptionDetails)throw Error('page_evaluation_failed');return out.result?.value;}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{try{
 child=require('child_process').spawn(process.env.RV_CHROME,['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--remote-debugging-port=0','--user-data-dir='+profile,'--no-first-run','--no-default-browser-check','about:blank'],{stdio:'ignore'});
 const port=await waitFile(profile+'/DevToolsActivePort',15000),version=await fetch('http://127.0.0.1:'+port+'/json/version').then(r=>r.json());
 async function connect(url){socket=new WebSocket(url);await new Promise((resolve,reject)=>{socket.once('open',resolve);socket.once('error',reject);});socket.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error('cdp_error_'+m.error.code)):p.resolve(m.result);}else if(m.method)events.push(m);});}
 await connect(version.webSocketDebuggerUrl);await call('Target.createTarget',{url:'about:blank'});const target=(await fetch('http://127.0.0.1:'+port+'/json/list').then(r=>r.json())).find(x=>x.type==='page');socket.close();await connect(target.webSocketDebuggerUrl);
 await call('Page.enable');await call('Runtime.enable');await call('Page.setDownloadBehavior',{behavior:'allow',downloadPath:downloads,eventsEnabled:true});
 await call('Page.navigate',{url:process.env.RV_BASE_URL});await sleep(1200);
 const initial=await evaluate('({path:location.pathname,mode:document.querySelector("meta[name=rv-v2-snapshot-mode]")?.content,screenCount:document.querySelectorAll("#primary-nav button[data-view]").length})');
 if(initial.mode!=='authenticated-dashboard')throw Error('dashboard_snapshot_mode_marker_missing');
 await evaluate('(()=>{document.querySelector("[data-resident-id=fixture-resident-02]").click();document.querySelector("[data-view=work]").click();document.querySelector("#theme-select").value="dark";document.querySelector("#theme-select").dispatchEvent(new Event("change"));document.querySelector("#right-state").click();return true})()');
 const desired=await evaluate('({view:document.querySelector("#primary-nav [aria-current=page]").dataset.view,resident:document.querySelector("#selected-resident b").textContent,theme:document.querySelector("#theme-select").value,right:document.querySelector(".app-shell").dataset.rightState})');
 if(desired.view!=='work'||desired.resident!=='Resident fixture 02'||desired.theme!=='dark'||desired.right!=='compact')throw Error('prepared_state_mismatch');
 async function clickAndWait(){const before=events.length,rect=await evaluate('(()=>{const r=document.querySelector("#snapshot-action").getBoundingClientRect();return{x:r.left+r.width/2,y:r.top+r.height/2}})()');
   await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:rect.x,y:rect.y});await call('Input.dispatchMouseEvent',{type:'mousePressed',x:rect.x,y:rect.y,button:'left',clickCount:1});await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:rect.x,y:rect.y,button:'left',clickCount:1});
   for(let i=0;i<300;i++){await sleep(100);const item=events.slice(before).find(e=>e.method==='Page.downloadWillBegin');if(item)return item;}throw Error('snapshot_download_not_started');}
 const first=await clickAndWait();await sleep(1200);
 const afterSuccess=await evaluate('({status:document.querySelector("#snapshot-status").innerText,copy:[...document.querySelectorAll("#snapshot-status button")].some(b=>b.textContent==="Copy GitHub Link"),view:document.querySelector("#primary-nav [aria-current=page]").dataset.view,resident:document.querySelector("#selected-resident b").textContent})');
 if(!afterSuccess.copy||!afterSuccess.status.includes('archived')||afterSuccess.view!=='work'||afterSuccess.resident!=='Resident fixture 02')throw Error('archive_or_state_restore_failed:'+JSON.stringify(afterSuccess));
 const second=await clickAndWait();await sleep(1200);const afterFailure=await evaluate('document.querySelector("#snapshot-status").innerText');
 if(!afterFailure.includes('archival failed')||!afterFailure.includes('requested'))throw Error('archive_failure_did_not_preserve_local_download');
 await sleep(1500);const result={browser:version.Browser,path:initial.path,mode:initial.mode,screens_found:initial.screenCount,prepared_state:desired,after_success:afterSuccess,archive_failure_status:afterFailure,downloads:[first.params.suggestedFilename,second.params.suggestedFilename]};
 fs.writeFileSync(process.env.RV_REPORT,JSON.stringify(result,null,2)+'\n');socket.close();child.kill('SIGTERM');process.exit(0);
}catch(error){console.error(String(error.message||error));if(socket)socket.close();if(child)child.kill('SIGTERM');process.exit(2);}})();'''


class Fixture(http.server.ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address):
        super().__init__(address, Handler)
        self.uploads = []
        self.request_evidence = []
        self.archive_attempts = 0
        self.fail_archive_attempt = 2
        self.graphs = []
        for path in sorted((ROOT / "process_graphs").glob("*/*.json")):
            if path.parent.name in {"generated", "schema"}:
                continue
            try:
                graph = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(graph, dict) and isinstance(graph.get("graph_id"), str):
                self.graphs.append(graph)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *_args):
        pass

    def send(self, status, body, content_type="application/json; charset=utf-8", headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or []):
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def json(self, status, value):
        self.send(status, json.dumps(value,separators=(",",":")).encode())

    def authorized(self):
        return ("rv_account_session=fixture-steward" in self.headers.get("Cookie", "")
                and "rv_account_csrf=fixture-csrf" in self.headers.get("Cookie", ""))

    def do_GET(self):
        path=self.path.split("?",1)[0]
        if path in {"/v2/", "/v2/index.html"}:
            page=(ROOT/"website/v2/index.html").read_bytes()
            page=page.replace(b"</head>",b'<meta name="rv-v2-snapshot-mode" content="authenticated-dashboard"></head>',1)
            self.send(200,page,"text/html; charset=utf-8",[("Set-Cookie","rv_account_session=fixture-steward; Path=/; HttpOnly; SameSite=Strict"),("Set-Cookie","rv_account_csrf=fixture-csrf; Path=/; SameSite=Strict")]);return
        if path.startswith("/v2/assets/"):
            name=path.rsplit("/",1)[-1]
            files={"workspace.css":("workspace.css","text/css"),"fixtures.js":("fixtures.js","text/javascript"),"workspace.js":("workspace.js","text/javascript"),"snapshot.js":("snapshot.js","text/javascript"),"favicon.svg":("favicon.svg","image/svg+xml")}
            if name not in files:self.send(404,b"not found","text/plain");return
            rel,kind=files[name];self.send(200,(ROOT/"website/v2/assets"/rel).read_bytes(),kind);return
        if path.startswith("/api/v1/") and not self.authorized():self.json(401,{"error":"session_required"});return
        if path=="/api/v1/status":self.json(200,{"status":"healthy","source":{"source_commit":"controlled-candidate","deployment_id":"browser-fixture"}});return
        if path=="/api/v1/snapshot":self.json(200,{"schema_version":"rv.dashboard.snapshot.v1","dashboard":"available","redaction":{"conversation_bodies":"excluded"}});return
        if path=="/api/v1/snapshot/workflow-index":
            items=[{"graph_id":g["graph_id"],"component_id":g.get("component_id"),"workflow_id":g.get("workflow_id"),"graph_revision":g.get("graph_revision"),"node_count":len(g.get("nodes",[])),"edge_count":len(g.get("edges",[]))} for g in self.server.graphs]
            self.json(200,{"schema_version":"rv.website.workflow-index.v1","status":"available","inventory_count":len(items),"items":items,"errors":[]});return
        if path=="/api/v1/graphs":
            items=[{"graph_id":g["graph_id"],"component_id":g.get("component_id"),"workflow_id":g.get("workflow_id"),"graph_revision":g.get("graph_revision"),"node_count":len(g.get("nodes",[])),"edge_count":len(g.get("edges",[]))} for g in self.server.graphs]
            self.json(200,{"schema_version":"rv.dashboard.graph-index.v1","status":"available","items":items});return
        if path.startswith("/api/v1/graphs/"):
            graph_id=unquote(path.removeprefix("/api/v1/graphs/"));graph=next((g for g in self.server.graphs if g["graph_id"]==graph_id),None)
            if graph is None:self.json(404,{"error":"process_graph_not_found"});return
            data=dict(graph);data["execution_position"]={"status":"unknown","reason":"controlled fixture has no production execution projection"}
            self.json(200,{"schema_version":"rv.dashboard.graph.v1","status":"available","graph":data});return
        self.send(404,b"not found","text/plain")

    def do_POST(self):
        if self.path!="/api/v1/snapshot/archive":self.send(404,b"not found","text/plain");return
        self.server.archive_attempts+=1
        self.server.request_evidence.append({"attempt":self.server.archive_attempts,"authorized":self.authorized(),"csrf_header_matches":self.headers.get("X-Riverview-CSRF")=="fixture-csrf"})
        if not self.authorized() or self.headers.get("X-Riverview-CSRF")!="fixture-csrf":self.json(403,{"error":"csrf_or_session_check_failed"});return
        length=int(self.headers.get("Content-Length","0"));data=self.rfile.read(length)
        self.server.request_evidence[-1]["body_size_bytes"]=len(data)
        if self.server.archive_attempts==self.server.fail_archive_attempt:
            self.json(502,{"error":"snapshot_archive_failed"});return
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:manifest=json.loads(archive.read("manifest.json"))
        except Exception as exc:self.server.request_evidence[-1]["parse_error"]=type(exc).__name__;self.json(400,{"error":"invalid_zip"});return
        digest=hashlib.sha256(data).hexdigest();name=f"riverview-v2-{manifest['captured_at'].replace(':','-')}-{manifest['capture_id']}.zip"
        self.server.uploads.append({"bytes":data,"sha256":digest,"manifest":manifest,"asset_name":name})
        self.server.request_evidence[-1].update({"accepted":True,"asset_name":name,"size_bytes":len(data),"sha256":digest})
        self.json(200,{"status":"archived","dashboard_version":"v2","capture_id":manifest["capture_id"],"asset_name":name,"archive_size_bytes":len(data),"archive_sha256":digest,"release_url":f"https://github.com/ppow1/Riverview-Diagnostic-Archive/releases/download/fixture/{name}"})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir",required=True)
    args=parser.parse_args()
    evidence=Path(args.evidence_dir).resolve();downloads=evidence/"downloads";profile=evidence/"chrome-profile"
    evidence.mkdir(parents=True,exist_ok=True);downloads.mkdir(exist_ok=True)
    for stale in downloads.glob("*.zip"):stale.unlink()
    for stale in downloads.glob("*.crdownload"):stale.unlink()
    server=Fixture(("127.0.0.1",0))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    env=os.environ.copy();env.update({"RV_PROFILE":str(profile),"RV_DOWNLOADS":str(downloads),"RV_CHROME":shutil.which("google-chrome") or "google-chrome","RV_BASE_URL":f"http://127.0.0.1:{server.server_port}/v2/index.html","RV_REPORT":str(evidence/"browser-report.json")})
    result=subprocess.run(["node","-e",NODE],env=env,text=True,capture_output=True,timeout=180)
    try:
        if result.returncode:
            print(json.dumps({"browser_error":result.stderr.strip(),"archive_attempts":server.archive_attempts,"server_evidence":server.request_evidence},indent=2))
            raise SystemExit(result.stderr.strip() or "V2 browser acceptance failed")
        files=sorted(downloads.glob("*.zip"))
        if len(files)!=2:raise SystemExit(f"expected 2 browser ZIPs, got {len(files)}")
        manifests=[validate_v2_full_diagnostic_archive(path.read_bytes()) for path in files]
        if server.archive_attempts!=2 or len(server.uploads)!=1:raise SystemExit("controlled archive attempt counts mismatch")
        downloaded_hashes=[hashlib.sha256(path.read_bytes()).hexdigest() for path in files]
        if downloaded_hashes[0]!=server.uploads[0]["sha256"]:raise SystemExit("archive bytes differ from first browser download")
        if manifests[0]["capture_id"]!=server.uploads[0]["manifest"]["capture_id"]:raise SystemExit("archive capture identity mismatch")
        if manifests[0]["expected"]["screens"]!=5 or manifests[0]["expected"]["workflows"]!=len(server.graphs):raise SystemExit("V2 capture inventory incomplete")
        report=json.loads((evidence/"browser-report.json").read_text())
        report.update({"result":"PASS","archive_upload_sha256":server.uploads[0]["sha256"],"archive_upload_size_bytes":len(server.uploads[0]["bytes"]),"download_sha256":downloaded_hashes,"download_size_bytes":[path.stat().st_size for path in files],"zip_entries":[len(zipfile.ZipFile(path).namelist()) for path in files],"manifest_capture_ids":[manifest["capture_id"] for manifest in manifests],"workflow_count":manifests[0]["expected"]["workflows"],"v2_screen_count":manifests[0]["expected"]["screens"],"synthetic_archive_attempts":server.archive_attempts,"synthetic_archive_successes":len(server.uploads)})
        (evidence/"browser-report.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report,indent=2))
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)
        if profile.exists():shutil.rmtree(profile,ignore_errors=True)
        if result.returncode:print(result.stderr)


if __name__=="__main__":
    main()
