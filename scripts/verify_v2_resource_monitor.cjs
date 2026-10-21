/*
Riverview~ Controlled Source
File: scripts/verify_v2_resource_monitor.cjs
Component: RIVERVIEW-V2-HARDWARE-AI-RESOURCE-MONITOR
Revision: 1.1.0
Purpose: Verify same-origin authentication, safe telemetry rendering, source timestamps, and explicit unavailable states
Execution Model: Deterministic Node VM fixtures; no network access
Observability: Named assertions and process exit status
Dependencies: Node.js built-in assert and vm modules
Inputs/Outputs: Synthetic sanitized Dashboard projections; no credentials or production records
Authority: Isolated UI contract test only
Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Cover live projection rendering and stale/unavailable states
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: scripts/verify_v2_resource_monitor.cjs
History: Git and revision/backup manifest
*/
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const ROOT=path.resolve(__dirname,"..");
const source=fs.readFileSync(path.join(ROOT,"website/v2/assets/resource-monitor.js"),"utf8");
function element(id=""){return {id,textContent:"",value:"all",dataset:{},hidden:false,disabled:false,children:[],listeners:{},append(...items){this.children.push(...items);},replaceChildren(...items){this.children=[...items];},get childElementCount(){return this.children.length;},addEventListener(name,fn){this.listeners[name]=fn;}};}
function boot({protocol="https:",pathname="/v2/",responses=[]}={}){
  const nodes=new Map(),cards=["hardware","inference","dashboard"].map(kind=>Object.assign(element(),{dataset:{resourceKind:kind,search:kind}})),listeners=new Map();
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,element(id));return nodes.get(id);},createElement:name=>element(name),querySelectorAll(){return cards;},addEventListener(name,fn){listeners.set(name,fn);}};
  const calls=[],queue=[...responses];const context={document,location:{protocol,pathname},window:{},Date,Set,Number,String,fetch:async(url,options)=>{calls.push({url,options});const item=queue.shift();if(!item)throw Error("unexpected_fetch");if(item.throw)throw item.throw;return {ok:item.status>=200&&item.status<300,status:item.status,async json(){return item.body;}};},URL,console};
  vm.runInNewContext(source,context,{filename:"resource-monitor.js"});listeners.get("DOMContentLoaded")?.();return {context,nodes,cards,calls};
}
const statusPayload={schema_version:"rv.dashboard.status.v1",projection_status:"healthy",freshness:"current",observed_at:"2026-10-21T11:00:00Z",workers:{status:"stale",active_workers:4,healthy_workers:2,stale_workers:1,unknown_workers:1},assignment_counts:{queued:2,executing:1},assignments_total:3,cme:{status:"healthy"},grace_execution:{status:"unknown"}};
const telemetry={schema_version:"rv.dashboard.resource-telemetry.v1",status:"partial",observed_at:"2026-10-21T11:00:00Z",freshness_window_seconds:30,hosts:[{host_id:"octominer1",state:"healthy",gpu_inventory:{state:"healthy",source:"nvidia-smi via restricted SSH",observed_at:"2026-10-21T11:00:00Z",devices:[{index:0,name:"Tesla P100",utilization_percent:20,memory_used_bytes:13931372544,memory_total_bytes:17179869184,temperature_celsius:48,power_watts:60.4,fan_percent:null,active_services:["grace-reasoning-80b"]}]},inference_servers:[{service_id:"grace-reasoning-80b",display_name:"Grace reasoning 80B",state:"ready",observed_at:"2026-10-21T11:00:00Z",loaded_models:["Qwen3-Next-80B.gguf"],active_slots:{state:"measured",value:1,total:1},queued_requests:{state:"unavailable",value:null}}]},{host_id:"octominer2",state:"unavailable",identity_state:"documented_unverified",gpu_inventory:{state:"unavailable",devices:[]},inference_servers:[]}]};
async function run(){
  const offline=boot({protocol:"http:",pathname:"/"});await offline.context.window.RiverviewV2ResourceMonitor.refresh();assert.equal(offline.calls.length,0,"fixture context never contacts Dashboard");
  const online=boot({responses:[{status:200,body:{status:"authenticated"}},{status:200,body:statusPayload},{status:200,body:telemetry}]});await online.context.window.RiverviewV2ResourceMonitor.refresh();
  assert.deepEqual(online.calls.map(c=>c.url),["/api/v1/auth/session","/api/v1/status","/api/v1/resources/telemetry"]);
  online.calls.forEach(c=>{assert.equal(c.options.credentials,"same-origin");assert.equal(c.options.cache,"no-store");assert.equal(c.options.method,"GET");});
  assert.match(online.nodes.get("resource-worker-summary").textContent,/4 active/);assert.match(online.nodes.get("resource-assignment-summary").textContent,/queued: 2/);
  const cards=online.nodes.get("resource-cards"),flatten=(e)=>`${e.textContent||""} ${(e.children||[]).map(flatten).join(" ")}`,serialized=cards.children.map(flatten).join(" ");
  assert.match(serialized,/Qwen3-Next-80B.gguf/);assert.match(serialized,/server exposes no queue depth/);assert.equal(online.nodes.get("resource-host-cards").children.length,2);
  const diag=online.context.window.RiverviewV2ResourceMonitor.snapshotDiagnostics();assert.equal(diag.gpu_inventory,"partial");assert.equal(diag.diagnostics_include_response_body,false);assert.equal(diag.diagnostics_include_credentials,false);assert.equal(diag.gpu_utilization,"values_not_included_in_snapshot_diagnostics");
  const denied=boot({responses:[{status:401,body:{error:"authentication_required"}}]});await denied.context.window.RiverviewV2ResourceMonitor.refresh();assert.equal(denied.calls.length,1);assert.match(denied.nodes.get("resource-cards").children[0].textContent,/http_401/);
  const telemFail=boot({responses:[{status:200,body:{status:"authenticated"}},{status:200,body:statusPayload},{status:503,body:{error:"unavailable"}}]});await telemFail.context.window.RiverviewV2ResourceMonitor.refresh();assert.match(telemFail.nodes.get("resource-cards").children[0].textContent,/http_503/);
  assert.doesNotMatch(source,/192\.168\.1\.(160|162)|:8080|:18080|setInterval\s*\(/,"browser must use same-origin on-demand API only");assert.doesNotMatch(source,/innerHTML/);
  console.log("PASS: authenticated same-origin GPU/model projection; safe DOM rendering; timestamps; unavailable queue/host state; auth and telemetry failures; no host polling or snapshot values");
}
run().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
