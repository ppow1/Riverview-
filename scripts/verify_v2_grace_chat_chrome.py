#!/usr/bin/env python3
# Riverview~ Controlled Source
# File: scripts/verify_v2_grace_chat_chrome.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.1
# Purpose: Verify an authenticated real Grace round trip and durable reload in Chrome
# Execution Model: Request-driven acceptance runner attached to an existing local Chrome session
# Observability: Sanitized JSON report and redacted screenshot; no transcript or credentials persisted
# Dependencies: Python 3.10+, Node.js ws module, Chrome remote debugging, LAN HTTPS /v2 route
# Inputs/Outputs: Secure prompted Dashboard account if needed; event IDs/times and pass/fail evidence
# Authority: One Steward-initiated harmless message to real Grace; no retry of uncertain sends
# Changed: 2026-10-20 UTC | RV-WEB-V2-GRACE-CHAT-002 | Initial real-browser Grace round-trip verifier
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: tests/test_v2_workspace_shell.py
# History: Git and revision/backup manifest
"""Use the running Chrome profile for one real authenticated Grace round trip."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


NODE_RUNNER = r'''const WebSocket=require('ws'),fs=require('fs'),crypto=require('crypto');
const input=JSON.parse(fs.readFileSync(0,'utf8'));let browserSocket,pageSocket,targetId,seq=0;const pending=new Map();
function connect(url){return new Promise((resolve,reject)=>{const ws=new WebSocket(url);ws.once('open',()=>resolve(ws));ws.once('error',reject);});}
function wire(ws){ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error('cdp_'+m.error.code)):p.resolve(m.result);}});}
function call(ws,method,params={}){const id=++seq;return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(Error('cdp_timeout'));}},20000);});}
async function evaluate(expression,args=[]){const source=`(function(){return (${expression})}).apply(window,${JSON.stringify(args)})`;const r=await call(pageSocket,'Runtime.evaluate',{expression:source,awaitPromise:true,returnByValue:true,timeout:20000});if(r.exceptionDetails)throw Error('browser_script_error');return r.result?.value;}
async function waitFor(expression,timeout=30000){const end=Date.now()+timeout;while(Date.now()<end){const value=await evaluate(expression);if(value)return value;await new Promise(r=>setTimeout(r,250));}throw Error('browser_acceptance_timeout');}
async function hash(value){return crypto.createHash('sha256').update(String(value||'')).digest('hex').slice(0,16);}
(async()=>{let stage='connect local Chrome';try{
 const version=await fetch('http://127.0.0.1:'+input.port+'/json/version').then(r=>r.json());
 browserSocket=await connect(version.webSocketDebuggerUrl);wire(browserSocket);
 const created=await call(browserSocket,'Target.createTarget',{url:'about:blank'});targetId=created.targetId;
 let target;
 for(let n=0;n<40;n++){target=(await fetch('http://127.0.0.1:'+input.port+'/json/list').then(r=>r.json())).find(t=>t.id===targetId);if(target?.webSocketDebuggerUrl)break;await new Promise(r=>setTimeout(r,100));}
 if(!target?.webSocketDebuggerUrl)throw Error('chrome_target_unavailable');
 pageSocket=await connect(target.webSocketDebuggerUrl);wire(pageSocket);
 await call(pageSocket,'Page.enable');await call(pageSocket,'Runtime.enable');
 await call(pageSocket,'Page.addScriptToEvaluateOnNewDocument',{source:"(()=>{const original=window.fetch.bind(window);window.__rvV2ChatReceipt=null;window.fetch=async(...args)=>{const response=await original(...args);const url=String(args[0]);if(url.includes('/api/v1/resident/conversations/stream')&&response.ok){try{const data=await response.clone().json();window.__rvV2ChatReceipt={conversation_id:data.conversation_id,request_id:data.request_id,status:data.status};}catch(_){}}return response;};})();"});
 stage='open same-origin V2';await call(pageSocket,'Page.navigate',{url:input.url});
 await waitFor("document.readyState==='complete'&&!!document.querySelector('#grace-chat-root')",30000);
 let state=await evaluate("document.querySelector('#grace-chat-root').dataset.state");
 if(state==='disconnected'&&input.email&&input.password){
   stage='sign in through existing Dashboard form';
   await evaluate("(()=>{document.querySelector('#grace-email').value=arguments[0];document.querySelector('#grace-password').value=arguments[1];document.querySelector('#grace-login-form').requestSubmit();return true})()",[input.email,input.password]);
   state=await waitFor("(()=>{const s=document.querySelector('#grace-chat-root').dataset.state;return s==='connected'||s==='unavailable'?s:null})()",30000);
 }
 input.email='';input.password='';
 if(state!=='connected')throw Error('authorized_dashboard_session_unavailable');
 stage='start a new durable conversation';
 await evaluate("document.querySelector('#grace-new').click();return true");
 const prompt=input.prompt;
 await evaluate("(()=>{const box=document.querySelector('#grace-message');box.value=arguments[0];box.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#grace-chat-form').requestSubmit();return true})()",[prompt]);
 stage='wait for real Grace response';
 await waitFor("(()=>{const cards=[...document.querySelectorAll('#grace-chat-history .grace-message')];return cards.some(x=>x.querySelector('b')?.textContent==='You'&&x.querySelector('p')?.textContent==="+JSON.stringify(input.prompt)+")&&cards.some(x=>x.querySelector('b')?.textContent==='Grace'&&x.querySelector('p')?.textContent.trim().length>0)})()",300000);
 const before=await evaluate("(()=>{const cards=[...document.querySelectorAll('#grace-chat-history .grace-message')];return {state:document.querySelector('#grace-chat-root').dataset.state,events:cards.map(x=>({role:x.querySelector('b').textContent,meta:x.querySelector('small').textContent,body:x.querySelector('p').textContent})),receipt:window.__rvV2ChatReceipt,conversation_id:localStorage.getItem('rv.grace.conversation')}})()");
 if(!before.receipt?.request_id||!before.receipt?.conversation_id)throw Error('durable_send_receipt_unavailable');
 const user=before.events.find(x=>x.role==='You'&&x.body===prompt),grace=before.events.find(x=>x.role==='Grace'&&x.body.trim());
 if(!user||!grace||!user.meta.includes('Event ')||!grace.meta.includes('Event '))throw Error('actual_conversation_events_missing');
 const userSeq=user.meta.match(/^Event ([0-9]+)/)?.[1],graceSeq=grace.meta.match(/^Event ([0-9]+)/)?.[1];
 if(!userSeq||!graceSeq)throw Error('persisted_event_sequence_missing');
 const originalUrl=input.url;
 stage='reload and verify durable conversation history';await call(pageSocket,'Page.navigate',{url:originalUrl});
 await waitFor("document.readyState==='complete'&&document.querySelector('#grace-chat-root')?.dataset.state==='connected'",30000);
 await waitFor("(()=>{const cards=[...document.querySelectorAll('#grace-chat-history .grace-message')];return cards.some(x=>x.querySelector('b')?.textContent==='You'&&x.querySelector('p')?.textContent==="+JSON.stringify(input.prompt)+")&&cards.some(x=>x.querySelector('b')?.textContent==='Grace'&&x.querySelector('p')?.textContent.trim().length>0)})()",30000);
 const after=await evaluate("(()=>{const cards=[...document.querySelectorAll('#grace-chat-history .grace-message')];return {events:cards.map(x=>({role:x.querySelector('b').textContent,meta:x.querySelector('small').textContent,body:x.querySelector('p').textContent})),conversation_id:localStorage.getItem('rv.grace.conversation'),state:document.querySelector('#grace-chat-root').dataset.state}})()");
 const userAgain=after.events.find(x=>x.role==='You'&&x.body===prompt),graceAgain=after.events.find(x=>x.role==='Grace'&&x.body.trim());
 if(after.conversation_id!==before.conversation_id||userAgain?.meta!==user.meta||graceAgain?.meta!==grace.meta)throw Error('reload_history_not_identical');
 const report={browser:version.Browser,url:input.url,authenticated:true,auth_source:'existing Dashboard account session',dashboard_grants_checked_by_server:true,send_transport:'POST /api/v1/resident/conversations/stream',response_transport:'GET /api/v1/resident/conversations/{id}/responses/{request_id}',request_status:before.receipt.status||'accepted',conversation_id_sha256_16:await hash(before.conversation_id),request_id_sha256_16:await hash(before.receipt.request_id),user_event:{sequence:Number(userSeq),timestamp_text:user.meta},grace_event:{sequence:Number(graceSeq),timestamp_text:grace.meta,response_text_captured:false},reload:{same_conversation_id:after.conversation_id===before.conversation_id,user_event_same_sequence_and_timestamp:userAgain?.meta===user.meta,grace_event_same_sequence_and_timestamp:graceAgain?.meta===grace.meta,assistant_response_present:Boolean(graceAgain?.body.trim())},snapshot_no_transcript_expected:true};
 fs.writeFileSync(input.report,JSON.stringify(report,null,2)+'\n');
 // Remove message text from the retained screenshot after the real DOM checks above.
 await evaluate("document.querySelectorAll('#grace-chat-history .grace-message p').forEach(p=>p.textContent='[conversation text omitted from evidence]');return true");
 const redacted=await call(pageSocket,'Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(input.screenshot,Buffer.from(redacted.data,'base64'));
 await call(browserSocket,'Target.closeTarget',{targetId});pageSocket.close();browserSocket.close();process.exit(0);
}catch(e){input.email='';input.password='';console.error(stage+': '+String(e.message||e).replace(/password|token|cookie|email/ig,'[redacted]'));try{if(targetId)await call(browserSocket,'Target.closeTarget',{targetId});}catch(_){};try{pageSocket?.close();browserSocket?.close();}catch(_){}process.exit(2);}})();'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://192.168.1.155/v2/")
    parser.add_argument("--port", type=int, default=9225, help="existing local Chrome DevTools port")
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args()
    if not args.url.startswith("https://") or "/v2/" not in args.url:
        parser.error("--url must be the HTTPS /v2/ route")
    evidence = Path(args.evidence_dir).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    prompt = f"Riverview V2 acceptance check {uuid.uuid4()} — please reply with a brief confirmation only."
    env = os.environ.copy()
    env.pop("RV_DASHBOARD_EMAIL", None)
    env.pop("RV_DASHBOARD_PASSWORD", None)
    email = password = ""
    # Browser account credentials stay in hidden terminal input and subprocess stdin.
    payload = {"url": args.url, "port": args.port, "prompt": prompt,
               "report": str(evidence / "grace-chat-browser-report.json"),
               "screenshot": str(evidence / "grace-chat-browser-redacted.png"),
               "email": "", "password": ""}
    result = subprocess.run(["node", "-e", NODE_RUNNER], input=json.dumps(payload), text=True,
                            capture_output=True, timeout=360, env=env)
    if result.returncode and "authorized_dashboard_session_unavailable" in result.stderr:
        email = getpass.getpass("Dashboard Steward email (hidden): ").strip()
        password = getpass.getpass("Dashboard account password (hidden): ")
        payload["email"] = email
        payload["password"] = password
        result = subprocess.run(["node", "-e", NODE_RUNNER], input=json.dumps(payload), text=True,
                                capture_output=True, timeout=360, env=env)
    email = password = ""
    payload["email"] = payload["password"] = ""
    if result.returncode:
        print(result.stderr.strip() or "Chrome acceptance failed; no automatic message retry was attempted.", file=sys.stderr)
        return result.returncode
    report = json.loads((evidence / "grace-chat-browser-report.json").read_text())
    report["acceptance_prompt"] = "Unique harmless V2 acceptance check; body not retained in report"
    report["acceptance_time_utc"] = datetime.now(timezone.utc).isoformat()
    report["screenshot_sha256"] = hashlib.sha256((evidence / "grace-chat-browser-redacted.png").read_bytes()).hexdigest()
    (evidence / "grace-chat-browser-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
