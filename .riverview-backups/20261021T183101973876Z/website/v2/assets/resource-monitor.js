/*
Riverview~ Controlled Source
File: website/v2/assets/resource-monitor.js
Component: RIVERVIEW-V2-HARDWARE-AI-RESOURCE-MONITOR
Revision: 1.1.0
Purpose: Present authenticated live Dashboard operational, GPU and inference summaries
Execution Model: Explicit same-origin authenticated GETs; no polling
Observability: Per-source state, observations, freshness, and sanitized error categories
Dependencies: Existing Dashboard account session; rv.dashboard.status.v1 and rv.dashboard.resource-telemetry.v1
Inputs/Outputs: Redacted work-fleet, GPU and model-server projections; unsupported queue depth remains unavailable
Authority: Existing account session read-only GETs only; no inference-host calls or control operations
Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Render live host telemetry from the authenticated Dashboard projection
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: scripts/verify_v2_resource_monitor.cjs, tests/test_v2_workspace_shell.py
History: Git and revision/backup manifest
*/
(() => {
  "use strict";
  const state = {status:"not-checked",dashboardStatus:null,telemetry:null,checkedAt:null,observedAt:null,freshness:"unknown",error:null,telemetryError:null,attempted:false,inFlight:false};
  const allowedStates = new Set(["healthy","degraded","partial","stale","unknown","unverified","unavailable","not_initialized","inactive","ready"]);
  const $ = (id) => document.getElementById(id);
  const safeState = (value) => allowedStates.has(value) ? value : "unknown";
  const safeError = (value) => /^[a-z0-9_.-]{1,48}$/i.test(String(value || "")) ? String(value) : "source_error";
  const safeCount = (value) => Number.isSafeInteger(value) && value >= 0 && value <= 1000000000 ? value : null;
  const isoTime = (value) => { if (typeof value !== "string") return null; const n=Date.parse(value); return Number.isFinite(n)?new Date(n).toISOString():null; };
  const visibleTime = (value) => { const t=isoTime(value); return t?`${t} · UTC`:"Not reported"; };
  const text = (id,value) => { const node=$(id); if(node) node.textContent=String(value); };
  const tag = (id,value) => { const node=$(id); if(!node)return; node.textContent=value.toUpperCase().replaceAll("_"," "); node.dataset.state=value; };
  const fetchJson = async (path) => {
    const response=await fetch(path,{method:"GET",headers:{Accept:"application/json"},credentials:"same-origin",cache:"no-store",redirect:"error"});
    if(!response.ok){const error=new Error(`http_${response.status}`);error.status=response.status;throw error;} return response.json();
  };
  const workerSummary = (workers) => {
    if(!workers||!["healthy","degraded","stale","unknown","unverified","unavailable","not_initialized"].includes(workers.status))return "Unavailable";
    const a=safeCount(workers.active_workers),h=safeCount(workers.healthy_workers),s=safeCount(workers.stale_workers),u=safeCount(workers.unknown_workers);
    return [a,h,s,u].some(v=>v===null)?workers.status.replaceAll("_"," "):`${a} active · ${h} healthy · ${s} stale · ${u} unknown`;
  };
  const assignmentSummary = (payload) => {
    if(!payload||payload.projection_status!=="healthy"||!payload.assignment_counts||typeof payload.assignment_counts!=="object")return "Unavailable";
    const total=safeCount(payload.assignments_total); const entries=Object.entries(payload.assignment_counts).filter(([k,v])=>/^[a-z][a-z0-9_-]{0,31}$/i.test(k)&&safeCount(v)!==null).slice(0,8);
    return total===null?"Unavailable":entries.length?`${total} recorded · ${entries.map(([k,v])=>`${k}: ${v}`).join(" · ")}`:`${total} recorded · no state breakdown reported`;
  };
  const node = (name, className, value) => { const e=document.createElement(name); if(className)e.className=className; if(value!==undefined)e.textContent=String(value); return e; };
  const addRow = (dl,label,value) => { const row=node("div");row.append(node("dt","",label),node("dd","",value));dl.append(row); };
  const hostLabel = (id) => ({camrui:"Camrui",octominer1:"OCTOMINER1",octominer2:"OctoMiner2"}[id]||"Unverified host");
  const amount = (v,suffix="") => typeof v==="number"&&Number.isFinite(v)?`${v.toLocaleString()}${suffix}`:"Unavailable";
  const bytes = (v) => { if(!Number.isSafeInteger(v)||v<0)return "Unavailable";let n=v,u=0;const units=["B","KiB","MiB","GiB"];while(n>=1024&&u<units.length-1){n/=1024;u++;}return `${n.toFixed(u?1:0)} ${units[u]}`; };
  const renderTelemetry = () => {
    const cards=$("resource-cards"),hosts=$("resource-host-cards");if(!cards||!hosts)return;cards.replaceChildren();hosts.replaceChildren();
    const data=state.telemetry;
    if(!data||!Array.isArray(data.hosts)){cards.append(node("p","",`Inference telemetry unavailable (${state.telemetryError||"not_observed"}).`));hosts.append(node("p","","Host readings unavailable; no values are inferred."));return;}
    data.hosts.slice(0,8).forEach(host=>{
      const name=hostLabel(host.host_id),inv=host.gpu_inventory&&Array.isArray(host.gpu_inventory.devices)?host.gpu_inventory:{devices:[]};
      const card=node("article","resource-card"),top=node("div","resource-card-top"),title=node("div");card.dataset.resourceCard="";card.dataset.resourceKind="hardware";card.dataset.search=`${name} gpu hardware`;
      title.append(node("p","eyebrow",host.identity_state==="verified"?"VERIFIED HOST TELEMETRY":"DOCUMENTED · IDENTITY UNVERIFIED"),node("h3","",name));const stateName=safeState(host.state||"unavailable"),badge=node("span","resource-tag",stateName.toUpperCase());badge.dataset.state=stateName;top.append(title,badge);card.append(top);
      const dl=node("dl");addRow(dl,"GPU inventory",inv.state==="healthy"?`${inv.devices.length} device(s)`:"Unavailable");addRow(dl,"Inventory source",inv.source||"Unavailable");const observed=isoTime(inv.observed_at||host.observed_at);addRow(dl,"Observed",observed?visibleTime(observed):"Not reported");card.append(dl);
      inv.devices.slice(0,32).forEach(gpu=>{const section=node("section","resource-gpu");section.append(node("h4","",`${gpu.name||"GPU"} · device ${amount(gpu.index)}`));const metrics=node("dl");addRow(metrics,"Utilization",amount(gpu.utilization_percent,"%"));addRow(metrics,"VRAM used / total",`${bytes(gpu.memory_used_bytes)} / ${bytes(gpu.memory_total_bytes)}`);addRow(metrics,"Temperature",amount(gpu.temperature_celsius," °C"));addRow(metrics,"Power",amount(gpu.power_watts," W"));addRow(metrics,"Fan",amount(gpu.fan_percent,"%"));addRow(metrics,"Active services",Array.isArray(gpu.active_services)&&gpu.active_services.length?gpu.active_services.join(", "):"None identified");section.append(metrics);card.append(section);});
      const stale=!observed||Date.now()-Date.parse(observed)>(Number(data.freshness_window_seconds)||30)*1000;if(stale&&observed){badge.textContent="STALE SOURCE";badge.dataset.state="stale";}hosts.append(card);
    });
    data.hosts.forEach(host=>(Array.isArray(host.inference_servers)?host.inference_servers:[]).slice(0,12).forEach(service=>{
      const card=node("article","resource-card"),top=node("div","resource-card-top"),heading=node("div");card.dataset.resourceCard="";card.dataset.resourceKind="inference";card.dataset.search=`${hostLabel(host.host_id)} ${service.display_name||"inference"} model`;
      heading.append(node("p","eyebrow",hostLabel(host.host_id)),node("h3","",service.display_name||service.service_id||"Inference service"));const s=safeState(service.state||"unavailable"),badge=node("span","resource-tag",s.toUpperCase());badge.dataset.state=s;top.append(heading,badge);card.append(top);
      const dl=node("dl");addRow(dl,"Loaded model",Array.isArray(service.loaded_models)&&service.loaded_models.length?service.loaded_models.join(", "):"Unavailable");addRow(dl,"Readiness source",service.readiness_source||"Unavailable");addRow(dl,"Active slots",service.active_slots?.state==="measured"?`${amount(service.active_slots.value)} / ${amount(service.active_slots.total)}`:"Unavailable");addRow(dl,"Queued requests",service.queued_requests?.state==="measured"?amount(service.queued_requests.value):"Unavailable · server exposes no queue depth");addRow(dl,"Observed",service.observed_at?visibleTime(service.observed_at):"Not reported");card.append(dl);cards.append(card);
    }));
    if(!hosts.childElementCount)hosts.append(node("p","","No verified host measurements are available."));if(!cards.childElementCount)cards.append(node("p","","No inference endpoints are verified."));
  };
  const applyFilters=()=>{const filter=$("resource-filter")?.value||"all",search=($("resource-search")?.value||"").trim().toLowerCase();document.querySelectorAll("[data-resource-card]").forEach(card=>{const kind=filter==="all"||card.dataset.resourceKind===filter,match=!search||`${card.dataset.search||""} ${card.textContent||""}`.toLowerCase().includes(search);card.hidden=!(kind&&match);});};
  const render=()=>{
    const labels={"not-checked":"NOT CHECKED",checking:"CHECKING",partial:"PARTIAL","authentication-required":"SIGN-IN REQUIRED",unavailable:"UNAVAILABLE",denied:"ACCESS DENIED"};tag("resource-source-state",state.status);text("resource-source-state",labels[state.status]||state.status.toUpperCase());const root=$("resource-monitor-workspace");if(root)root.dataset.state=state.status;const refresh=$("resource-refresh");if(refresh)refresh.disabled=state.inFlight;
    const projection=state.dashboardStatus?.projection_status,source=$("resource-dashboard-state");if(source){const label=projection==="healthy"?"AVAILABLE":projection==="not_initialized"?"NOT INITIALIZED":projection==="unavailable"?"UNAVAILABLE":state.status==="checking"?"CHECKING":state.status==="authentication-required"?"SIGN-IN REQUIRED":state.status==="denied"?"ACCESS DENIED":"NOT CHECKED";source.textContent=label;source.dataset.state=projection||state.status;}
    text("resource-refresh-status",state.status==="not-checked"?"Use Refresh to read live host and model-server telemetry through the authenticated Dashboard.":state.status==="checking"?"Checking authenticated Dashboard, GPU host, and inference sources…":state.status==="partial"?"Authenticated projections were read. Each source reports measured, stale, or unavailable state.":state.status==="authentication-required"?"Sign in through the existing Dashboard account session. No credentials are requested here.":state.status==="denied"?"The Dashboard denied this read. Existing access controls remain in force.":state.status==="unavailable"?`Dashboard telemetry is unavailable (${state.error||"source_error"}). No values are inferred.`:"Resource telemetry is not available in this context.");
    text("resource-dashboard-observed",state.observedAt?`Dashboard projection observed at ${visibleTime(state.observedAt)} · freshness ${state.freshness}.`:"No Dashboard observation has been received.");text("resource-worker-summary",state.dashboardStatus?workerSummary(state.dashboardStatus.workers):"Unavailable");text("resource-assignment-summary",state.dashboardStatus?assignmentSummary(state.dashboardStatus):"Unavailable");text("resource-cme-summary",state.dashboardStatus?safeState(state.dashboardStatus.cme?.status).replaceAll("_"," "):"Unavailable");text("resource-grace-summary",state.dashboardStatus?safeState(state.dashboardStatus.grace_execution?.status).replaceAll("_"," "):"Unavailable");text("resource-diagnostic-source",state.telemetry?"authenticated same-origin Dashboard telemetry API · read-only GET":"not connected");text("resource-diagnostic-freshness",state.freshness);text("resource-diagnostic-checked",visibleTime(state.checkedAt));text("resource-diagnostic-error",state.error||state.telemetryError||"none");renderTelemetry();applyFilters();
  };
  const refreshData=async()=>{
    if(state.inFlight)return;state.inFlight=true;state.attempted=true;state.checkedAt=new Date().toISOString();state.status="checking";state.dashboardStatus=null;state.telemetry=null;state.error=null;state.telemetryError=null;state.observedAt=null;state.freshness="unknown";render();
    if(location.protocol!=="https:"||!location.pathname.startsWith("/v2/")){state.status="unavailable";state.error="lan_https_preview_required";state.inFlight=false;render();return;}
    try{
      const session=await fetchJson("/api/v1/auth/session");if(session.status!=="authenticated"){state.status="authentication-required";state.inFlight=false;render();return;}
      const [statusResult,telemetryResult]=await Promise.allSettled([fetchJson("/api/v1/status"),fetchJson("/api/v1/resources/telemetry")]);
      if(statusResult.status==="rejected")throw statusResult.reason;
      if(telemetryResult.status==="fulfilled"&&telemetryResult.value?.schema_version==="rv.dashboard.resource-telemetry.v1")state.telemetry=telemetryResult.value;else state.telemetryError=telemetryResult.status==="rejected"?(telemetryResult.reason?.status?`http_${telemetryResult.reason.status}`:safeError(telemetryResult.reason?.message)):"invalid_telemetry_projection";
      const payload=statusResult.value;if(!payload||payload.schema_version!=="rv.dashboard.status.v1"||!allowedStates.has(payload.projection_status))throw new Error("invalid_dashboard_status_schema");state.dashboardStatus=payload;state.observedAt=isoTime(payload.observed_at);state.freshness=["current","stale","unknown","unavailable"].includes(payload.freshness)?payload.freshness:"unknown";state.status=payload.projection_status==="unavailable"?"unavailable":"partial";if(payload.projection_status==="unavailable")state.error="dashboard_projection_unavailable";
    }catch(error){state.dashboardStatus=null;state.observedAt=null;state.freshness="unavailable";state.status=error?.status===401?"authentication-required":error?.status===403?"denied":"unavailable";state.error=error?.status?`http_${error.status}`:safeError(error?.message);state.telemetry=null;state.telemetryError=state.error;}
    state.inFlight=false;render();
  };
  document.addEventListener("DOMContentLoaded",()=>{$("resource-refresh")?.addEventListener("click",refreshData);$("resource-filter")?.addEventListener("change",applyFilters);$("resource-search")?.addEventListener("input",applyFilters);document.addEventListener("rvv2:view",event=>{if(event.detail?.view==="resources"&&!state.attempted)refreshData();});render();});
  window.RiverviewV2ResourceMonitor=Object.freeze({render,refresh:refreshData,snapshotDiagnostics:()=>({status:state.status,dashboard_projection:state.dashboardStatus?state.dashboardStatus.projection_status:"not_observed",freshness:state.freshness,observed_at:state.observedAt,checked_at:state.checkedAt,gpu_inventory:state.telemetry?.status||"unavailable",gpu_utilization:state.telemetry?"values_not_included_in_snapshot_diagnostics":"unavailable",vram:state.telemetry?"values_not_included_in_snapshot_diagnostics":"unavailable",gpu_thermals_power_fan:state.telemetry?"values_not_included_in_snapshot_diagnostics":"unavailable",loaded_models:state.telemetry?"values_not_included_in_snapshot_diagnostics":"unavailable",inference_server_readiness:state.telemetry?"projected":"unavailable",inference_jobs_and_queues:state.telemetry?"active_slots_projected_queue_depth_unavailable":"unavailable",diagnostics_include_response_body:false,diagnostics_include_credentials:false})});
})();
