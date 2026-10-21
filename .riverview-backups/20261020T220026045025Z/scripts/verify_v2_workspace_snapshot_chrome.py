#!/usr/bin/env python3
# Riverview~ Controlled Source
# File: scripts/verify_v2_workspace_snapshot_chrome.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.6
# Purpose: Verify authenticated Chrome Snapshot download and ZIP content on the LAN preview
# Execution Model: Request-driven Chrome DevTools Protocol acceptance runner
# Observability: Sanitized JSON report, downloaded package, and screenshot
# Dependencies: Python 3.10+, Node.js ws module, Google Chrome, local V2 preview
# Inputs/Outputs: Preview URL and hidden password prompt; local evidence directory
# Authority: Browser-only read access to V2 preview; no upload or server mutation
# Changed: 2026-10-20 UTC | RV-WEB-V2-GRACE-CHAT-001 | Verify Chrome handoff URL, telemetry state, and redacted ZIP diagnostics
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: scripts/verify_v2_workspace_snapshot_chrome.py
# History: Git and revision/backup manifest
"""Use real Chrome to download a V2 ZIP, then validate and inspect its members."""
import argparse
import getpass
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODE_RUNNER = r'''const fs=require('fs'),http=require('http'),WebSocket=require('ws');
const profile=process.env.RV_CHROME_PROFILE, downloadPath=process.env.RV_CHROME_DOWNLOADS;let previewPassword=process.env.RV_V2_PREVIEW_PASSWORD;
delete process.env.RV_V2_PREVIEW_PASSWORD;
const child=require('child_process').spawn(process.env.RV_CHROME_BINARY,['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--remote-debugging-port=0','--user-data-dir='+profile,'--no-first-run','--no-default-browser-check','about:blank'],{stdio:'ignore'});
let socket,seq=0,stage='start';const pending=new Map(),events=[];
function waitFile(p,ms){return new Promise((resolve,reject)=>{let start=Date.now();let t=setInterval(()=>{if(fs.existsSync(p)){clearInterval(t);resolve(fs.readFileSync(p,'utf8').trim().split(/\s+/)[0]);}else if(child.exitCode!==null||Date.now()-start>ms){clearInterval(t);reject(Error('chrome_debug_endpoint_unavailable'));}},100);});}
function call(method,params={}){return new Promise((resolve,reject)=>{let id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(Error('cdp_timeout_'+method));}},15000);});}
async function evaluate(expression,awaitPromise=true){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise});if(r.exceptionDetails)throw Error('browser_script_error');return r.result?.value;}
async function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
(async()=>{try{
 stage='start Chrome';const port=await waitFile(profile+'/DevToolsActivePort',12000),version=await fetch('http://127.0.0.1:'+port+'/json/version').then(r=>r.json());
 socket=new WebSocket(version.webSocketDebuggerUrl);await new Promise((r,j)=>{socket.once('open',r);socket.once('error',j)});
 socket.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){let p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error('cdp_command_failed_'+m.error.code)):p.resolve(m.result);}else if(m.method)events.push(m);});
 await call('Target.createTarget',{url:'about:blank'});const targets=await fetch('http://127.0.0.1:'+port+'/json/list').then(r=>r.json());const target=targets.find(x=>x.type==='page');
 socket.close();socket=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{socket.once('open',r);socket.once('error',j)});
 socket.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){let p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error('cdp_command_failed_'+m.error.code)):p.resolve(m.result);}else if(m.method)events.push(m);});
 await call('Page.enable');await call('Runtime.enable');await call('Page.setDownloadBehavior',{behavior:'allow',downloadPath,eventsEnabled:true});
 stage='open LAN preview';await call('Page.navigate',{url:process.env.RV_V2_BASE_URL});await sleep(900);
 const auth=await evaluate('document.querySelector("#password")!==null');
 if(!auth)throw Error('LAN_preview_did_not_require_password');
 stage='submit password form';
 try{await evaluate('(()=>{const p=document.querySelector("#password");p.value='+JSON.stringify(previewPassword)+';document.querySelector("form").requestSubmit();return true})()');}catch(_){/* The expected 303 navigation can destroy the submitting document context. */}
 previewPassword='';await sleep(1800);
 stage='verify authenticated page';const title=await evaluate('document.title');if(title!=='Riverview V2 Workspace Preview')throw Error('preview_login_or_page_failed');
 stage='select representative V2 state';
 await evaluate('(()=>{document.querySelector("[data-resident-id=fixture-resident-02]").click();document.querySelector("[data-view=work]").click();document.querySelector("#theme-select").value="dark";document.querySelector("#theme-select").dispatchEvent(new Event("change"));document.querySelector("#right-state").click();return true})()');
 const expected=await evaluate('(()=>{const link=document.querySelector("#grace-chat-handoff"),status=document.querySelector("#comms5-status"),details=document.querySelector("#comms5-diagnostics");return {view:document.querySelector("#primary-nav [aria-current=page]").dataset.view,resident:document.querySelector("#selected-resident b").textContent,theme:document.querySelector("#theme-select").value,right:document.querySelector(".app-shell").dataset.rightState,button:document.querySelector("#snapshot-action").disabled,handoff:{href:link.href,target:link.target,rel:link.rel,label:link.querySelector("b").textContent.trim()},commsState:status.dataset.state,commsText:details.innerText}})()');
 if(expected.view!=='work'||expected.resident!=='Resident fixture 02'||expected.theme!=='dark'||expected.right!=='compact'||expected.button||expected.handoff.href!=='https://192.168.1.155/#grace-chat'||expected.handoff.target!=='_blank'||expected.handoff.rel!=='noopener noreferrer'||expected.handoff.label!=='Talk with Grace'||expected.commsState!=='unverified'||!expected.commsText.includes('Traffic counts: UNVERIFIED')||!expected.commsText.includes('not reported as zero'))throw Error('prepared_v2_state_mismatch');
 stage='click Snapshot';const before=events.length,rect=await evaluate('(()=>{const r=document.querySelector("#snapshot-action").getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()');
 await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:rect.x,y:rect.y});await call('Input.dispatchMouseEvent',{type:'mousePressed',x:rect.x,y:rect.y,button:'left',clickCount:1});await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:rect.x,y:rect.y,button:'left',clickCount:1});let event;
 for(let i=0;i<100&&!event;i++){await sleep(100);event=events.slice(before).find(x=>x.method==='Page.downloadWillBegin');}
 if(!event)throw Error('chrome_download_not_completed');
 const downloadFile=downloadPath+'/'+event.params.suggestedFilename;
 for(let i=0;i<100;i++){await sleep(100);if(fs.existsSync(downloadFile)&&!fs.existsSync(downloadFile+'.crdownload'))break;}
 if(!fs.existsSync(downloadFile)||fs.existsSync(downloadFile+'.crdownload'))throw Error('chrome_download_file_not_complete');
 const download=await evaluate('({status:document.querySelector("#snapshot-status").textContent,filename:document.querySelector("#snapshot-status").textContent})');
 const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(process.env.RV_CHROME_SCREENSHOT,Buffer.from(shot.data,'base64'));
 const report={browser:version.Browser,preview_url:process.env.RV_V2_BASE_URL,authenticated:auth,active_state:expected,download_completed:true,download_name:event.params.suggestedFilename,download_status:download.status};
 fs.writeFileSync(process.env.RV_CHROME_REPORT,JSON.stringify(report,null,2)+'\n');
 socket.close();child.kill('SIGTERM');process.exit(0);
}catch(e){console.error(stage+': '+String(e.message||e).replace(/password|token|cookie/ig,'[redacted]'));if(socket)socket.close();child.kill('SIGTERM');process.exit(2);}})();'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://192.168.1.155:8877/")
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--password-prompt", action="store_true", help="read preview password without echo")
    args = parser.parse_args()
    if not args.password_prompt:
        parser.error("--password-prompt is required; password is never accepted as a command argument")
    password = getpass.getpass("V2 preview password (hidden): ")
    if not password:
        raise SystemExit("empty preview password")
    evidence = Path(args.evidence_dir).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    downloads = evidence / "downloads"
    downloads.mkdir(exist_ok=True)
    for child in downloads.iterdir():
        if child.is_file():
            child.unlink()
    profile = tempfile.mkdtemp(prefix="rv-v2-chrome-profile-")
    env = os.environ.copy()
    env.update({"RV_CHROME_PROFILE": profile, "RV_CHROME_DOWNLOADS": str(downloads), "RV_CHROME_BINARY": shutil.which("google-chrome") or "google-chrome",
                "RV_V2_BASE_URL": args.base_url, "RV_V2_PREVIEW_PASSWORD": password,
                "RV_CHROME_SCREENSHOT": str(evidence / "v2-snapshot-browser.png"), "RV_CHROME_REPORT": str(evidence / "browser-report.json")})
    password = ""
    started = time.time()
    try:
        result = subprocess.run(["node", "-e", NODE_RUNNER], env=env, text=True, capture_output=True, timeout=90)
    finally:
        env.pop("RV_V2_PREVIEW_PASSWORD", None)
        shutil.rmtree(profile, ignore_errors=True)
    if result.returncode:
        raise SystemExit(result.stderr.strip() or "Chrome acceptance runner failed")
    zips = list(downloads.glob("*.zip"))
    if len(zips) != 1:
        raise SystemExit(f"expected one browser ZIP; found {len(zips)}")
    archive = zips[0]
    with zipfile.ZipFile(archive) as package:
        bad = package.testzip()
        if bad:
            raise SystemExit(f"corrupt ZIP member: {bad}")
        names = set(package.namelist())
        expected = {"workspace-state.json", "rendered-view.txt", "README.txt", "manifest.json"}
        if names != expected:
            raise SystemExit(f"unexpected ZIP member set: {sorted(names)}")
        manifest = json.loads(package.read("manifest.json"))
        state = json.loads(package.read("workspace-state.json"))
        records = {item["name"]: item for item in manifest["members"]}
        for name in expected - {"manifest.json"}:
            content = package.read(name)
            if hashlib.sha256(content).hexdigest() != records[name]["sha256"] or len(content) != records[name]["size_bytes"]:
                raise SystemExit(f"member SHA-256/size mismatch: {name}")
        if state["current_view"] != "work" or state["selected_context"]["resident_name"] != "Resident fixture 02" or state["appearance"]["selected_theme"] != "dark" or state["sidebars"]["context"] != "compact":
            raise SystemExit("ZIP state does not match the selected Chrome workspace view")
        if state["data_connection"]["live_backend_connected"] is not False or state["server_diagnostics"]["status"] != "not available":
            raise SystemExit("ZIP overstates live/server data")
        diagnostics = state.get("communication_diagnostics", {})
        grace = diagnostics.get("grace_chat", {})
        comms5 = diagnostics.get("comms5", {})
        if grace != {"status": "not_connected", "handoff_available": True,
                     "history_owner": "authenticated V1 Dashboard", "messages_captured": False}:
            raise SystemExit("ZIP Grace connection diagnostics are missing or overstate V2 access")
        if (comms5.get("status") != "unverified" or comms5.get("outbound_count") is not None
                or comms5.get("inbound_count") is not None or comms5.get("inspectable_messages") is not False
                or comms5.get("correlation_ids") != "unavailable"):
            raise SystemExit("ZIP Comms5 diagnostics invent counts or message access")
        if any(word in package.read("workspace-state.json").decode().lower() for word in ("authorization:", "cookie=", "sessionid")):
            raise SystemExit("credential-like field appeared in package")
    report_path = evidence / "browser-report.json"
    report = json.loads(report_path.read_text())
    report.update({"zip_name": archive.name, "zip_size_bytes": archive.stat().st_size,
                   "zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "zip_members": sorted(expected),
                   "manifest_member_checks": "PASS", "state_matches_selected_view": True,
                   "communication_diagnostics": "PASS: Grace handoff only; Comms5 counts null and UNVERIFIED; no messages captured",
                   "chrome_version": report.get("browser"), "elapsed_seconds": round(time.time() - started, 3)})
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
