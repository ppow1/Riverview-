/*
Riverview~ Controlled Source
File: website/v2/assets/resource-monitor.js
Component: RIVERVIEW-V2-HARDWARE-AI-RESOURCE-MONITOR
Revision: 1.4.3
Purpose: Present an interactive manufacturer chassis reference with OCTO1 telemetry and a sanitized Grace request trace
Execution Model: Same-origin authenticated GETs; five-second polling only while the Resources view is open and visible
Observability: Source timestamps, freshness, bounded five-minute hardware and model-rate timelines, and request-correlated conversation events
Dependencies: Dashboard account session; rv.dashboard.status.v1; rv.dashboard.resource-telemetry.v1; rv.v2.grace-request-trace.v1
Inputs/Outputs: GPU readings and content-free events from the current authenticated Grace conversation
Authority: Read-only account-authenticated GETs; no host controls, model calls, or inferred GPU-to-bay/controller-channel mapping
Changed: 2026-10-21 UTC | RV-V2-OCTO1-GRACE-TRACE-001 | Display correlated durable Grace attempt metadata without asserting server-side GPU attribution
Changed: 2026-10-21 UTC | RV-V2-OCTO1-PHYSICAL-TWIN-001 | Add physical front-panel hotspots, manufacturer view toggle, and dynamic model/GPU highlighting
Changed: 2026-10-22 UTC | RV-V2-GPU-REFRESH-STABILITY | Retain last successful telemetry and update keyed GPU cards in place during refresh
Changed: 2026-10-22 UTC | RV-V2-HW-AI-ENHANCEMENTS-207 | Add in-place VRAM bars, measured provider response-rate graphs, slot context details, and four-item activity paging
Changed: 2026-10-22 UTC | RV-HW-LIVE-STREAM-ACTIVITY-001 | Plot content-free, timestamped streamed-character cadence separately from completed token throughput.
Changed: 2026-10-22 UTC | RV-V2-MOUNTED-STORAGE-001 | Render unique host-mounted capacity through the existing authenticated telemetry projection, preserving unavailable/stale states.
Changed: 2026-10-22 UTC | RV-V2-LIVE-HARDWARE-GRAPHS-001 | Plot measured GPU utilization and active inference-slot occupancy from bounded five-second telemetry samples; clear obsolete storage placeholder.
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: scripts/verify_v2_resource_monitor.cjs; scripts/verify_v2_octo1_browser.cjs
History: Git and .riverview-backups/manifest.jsonl
*/
(() => {
  "use strict";
  const POLL_MS = 5000;
  const HISTORY_LIMIT = 60;
  const ACTIVITY_PAGE_SIZE = 4;
  const RATE_WINDOW_MS = 5 * 60 * 1000;
  const RATE_HISTORY_LIMIT = 180;
  const HARDWARE_HISTORY_LIMIT = 60;
  const state = {status:"not-checked",dashboardStatus:null,telemetry:null,requestTrace:null,checkedAt:null,observedAt:null,freshness:"unknown",error:null,telemetryError:null,attempted:false,inFlight:false,viewActive:false,pollHandle:null,history:[],activityPage:0,rateHistory:[],rateKeys:new Set(),liveRateHistory:[],liveRateKeys:new Set(),hardwareHistory:[],hardwareKeys:new Set(),artworkView:"front",selected:{kind:"overview",id:"overview"}};
  const allowedStates = new Set(["healthy","degraded","partial","stale","unknown","unverified","unavailable","not_initialized","inactive","ready"]);
  const $ = (id) => document.getElementById(id);
  const safeState = (value) => allowedStates.has(value) ? value : "unknown";
  const safeError = (value) => /^[a-z0-9_.-]{1,48}$/i.test(String(value || "")) ? String(value) : "source_error";
  const safeCount = (value) => Number.isSafeInteger(value) && value >= 0 && value <= 1000000000 ? value : null;
  const isoTime = (value) => { if (typeof value !== "string") return null; const n=Date.parse(value); return Number.isFinite(n)?new Date(n).toISOString():null; };
  const visibleTime = (value) => { const t=isoTime(value); return t?`${t} · UTC`:"Not reported"; };
  const text = (id,value) => { const node=$(id); if(node) node.textContent=String(value); };
  const tag = (id,value,label=value) => { const item=$(id); if(!item)return; item.textContent=String(label).toUpperCase().replaceAll("_"," "); item.dataset.state=value; };
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
  const hostLabel = (id) => ({camrui:"Camrui",octominer1:"OCTO1",octominer2:"OCTO2","windows-development":"Windows development machine"}[id]||"Unverified host");
  const serviceLabel = (id) => ({"grace-reasoning-80b":"Grace reasoning 80B","grace-vision-30b":"Grace vision 30B","grace-autonomic-0.6b":"Grace autonomic 0.6B"}[id]||id.replaceAll("-"," "));
  const amount = (v,suffix="") => typeof v==="number"&&Number.isFinite(v)?`${v.toLocaleString()}${suffix}`:"Unavailable";
  const bytes = (v) => { if(!Number.isSafeInteger(v)||v<0)return "Unavailable";let n=v,u=0;const units=["B","KiB","MiB","GiB"];while(n>=1024&&u<units.length-1){n/=1024;u++;}return `${n.toFixed(u?1:0)} ${units[u]}`; };
  const vramReading = (gpu) => {
    const used=gpu?.memory_used_bytes,total=gpu?.memory_total_bytes;
    if(!Number.isSafeInteger(used)||used<0||!Number.isSafeInteger(total)||total<=0||used>total)return null;
    const percent=(used/total)*100;
    return {used,total,remaining:total-used,percent};
  };
  const vramLabel = (gpu) => {const value=vramReading(gpu);return value?`${bytes(value.used)} / ${bytes(value.total)} · ${value.percent.toFixed(1)}% used · ${bytes(value.remaining)} free`:"Unavailable · source did not provide a consistent used/total reading";};
  const safeTokenCount = (value) => Number.isSafeInteger(value)&&value>=0&&value<=100000000?value:null;
  const rateStageModel = (stage) => ({autonomic:"grace-autonomic-0.6b",interim_30b:"grace-vision-30b",reasoning:"grace-reasoning-80b"})[stage]||null;
  const ingestMeasuredRates = (trace) => {
    if(trace?.state!=="available"||!Array.isArray(trace.requests))return;
    const now=Date.now();
    trace.requests.slice(0,12).forEach(request=>{
      if(typeof request?.request_id!=="string"||!Array.isArray(request.attempts))return;
      request.attempts.slice(0,4).forEach((attempt,index)=>{
        const modelId=rateStageModel(attempt?.stage),elapsed=attempt?.elapsed_ms,tokens=safeTokenCount(attempt?.completion_tokens),ended=isoTime(attempt?.ended_at);
        if(!modelId||attempt?.outcome!=="succeeded"||!Number.isFinite(elapsed)||elapsed<=0||tokens===null||tokens===0||!ended)return;
        const key=`${request.request_id}:${index}:${attempt.stage}`;if(state.rateKeys.has(key))return;
        state.rateKeys.add(key);state.rateHistory.push({key,model_id:modelId,at:Date.parse(ended),tokens_per_provider_second:tokens/(elapsed/1000),completion_tokens:tokens,elapsed_ms:elapsed});
      });
    });
    const cutoff=now-RATE_WINDOW_MS;
    state.rateHistory=state.rateHistory.filter(point=>point.at>=cutoff).slice(-RATE_HISTORY_LIMIT);
    state.rateKeys=new Set(state.rateHistory.map(point=>point.key));
  };
  const ingestLiveStreamRates = (trace) => {
    if(trace?.state!=="available"||trace?.stream_activity_state!=="available"||!Array.isArray(trace.requests))return;
    const now=Date.now();
    trace.requests.slice(0,12).forEach(request=>{
      const stream=request?.stream_activity,modelId=rateStageModel(stream?.reasoning_stage);
      if(typeof request?.request_id!=="string"||!modelId||!stream||!Array.isArray(stream.deltas))return;
      const deltas=stream.deltas.filter(delta=>delta&&Number.isSafeInteger(delta.sequence)&&delta.sequence>=0&&Number.isSafeInteger(delta.generation)&&delta.generation===stream.generation&&Number.isSafeInteger(delta.characters)&&delta.characters>0&&delta.characters<=8192&&isoTime(delta.occurred_at)).sort((a,b)=>a.sequence-b.sequence).slice(-120);
      if(deltas.length<2)return;
      for(let index=1;index<deltas.length;index++){
        const previous=deltas[index-1],current=deltas[index],from=Date.parse(previous.occurred_at),to=Date.parse(current.occurred_at),elapsed=(to-from)/1000;
        if(current.sequence<=previous.sequence||!Number.isFinite(elapsed)||elapsed<=0||elapsed>300)continue;
        const key=`${request.request_id}:${stream.generation}:${current.sequence}`;if(state.liveRateKeys.has(key))continue;
        state.liveRateKeys.add(key);state.liveRateHistory.push({key,request_id:request.request_id,model_id:modelId,at:to,characters_per_second:current.characters/elapsed,characters:current.characters,elapsed_ms:elapsed*1000,status:stream.status});
      }
    });
    const cutoff=now-RATE_WINDOW_MS;
    state.liveRateHistory=state.liveRateHistory.filter(point=>point.at>=cutoff).slice(-600);
    state.liveRateKeys=new Set(state.liveRateHistory.map(point=>point.key));
  };
  const ingestMeasuredHardwareActivity = (payload) => {
    const host=Array.isArray(payload?.hosts)?payload.hosts.find(item=>item?.host_id==="octominer1"):null;
    if(!host)return;
    const freshnessMs=Math.max(1,Number(payload.freshness_window_seconds)||30)*1000,now=Date.now(),fresh=value=>{const time=isoTime(value),at=time?Date.parse(time):NaN;return Number.isFinite(at)&&at<=now+1000&&now-at<=freshnessMs?time:null;};
    const inventory=host.gpu_inventory,inventoryAt=inventory?.state==="healthy"?fresh(inventory.observed_at||host.observed_at):null;
    const gpus=[];
    if(inventoryAt&&Array.isArray(inventory.devices))inventory.devices.slice(0,32).forEach(gpu=>{
      if(!Number.isSafeInteger(gpu?.index)||gpu.index<0||gpu.index>31||!Number.isFinite(gpu.utilization_percent)||gpu.utilization_percent<0||gpu.utilization_percent>100)return;
      const at=fresh(gpu.observed_at)||inventoryAt;gpus.push({index:gpu.index,at,value:gpu.utilization_percent});
    });
    const models=[];
    (Array.isArray(host.inference_servers)?host.inference_servers:[]).slice(0,12).forEach(service=>{
      const active=service?.active_slots,total=service?.active_slots?.total,slots=service?.slot_context?.slots;
      if(typeof service?.service_id!=="string"||active?.state!=="measured"||safeCount(active.value)===null||safeCount(total)===null||total<1||active.value>total)return;
      const at=fresh(service.slot_context?.observed_at||service.observed_at||host.observed_at);if(!at)return;
      const processing=Array.isArray(slots)?slots.some(slot=>slot?.processing===true):null;
      models.push({service_id:service.service_id,at,active:active.value,total,processing});
    });
    if(!gpus.length&&!models.length)return;
    const key=[...gpus.map(item=>`gpu:${item.index}:${item.at}:${item.value}`),...models.map(item=>`slot:${item.service_id}:${item.at}:${item.active}/${item.total}:${item.processing}`)].join("|");
    if(state.hardwareKeys.has(key))return;
    state.hardwareKeys.add(key);state.hardwareHistory.push({key,gpus,models});state.hardwareHistory=state.hardwareHistory.slice(-HARDWARE_HISTORY_LIMIT);state.hardwareKeys=new Set(state.hardwareHistory.map(sample=>sample.key));
  };
  const svgNode = (name,className) => {const item=document.createElementNS("http://www.w3.org/2000/svg",name);if(className)item.setAttribute("class",className);return item;};
  const octoHost = () => Array.isArray(state.telemetry?.hosts)?state.telemetry.hosts.find(host=>host?.host_id==="octominer1")||null:null;
  const gpuInventory = (host=octoHost()) => host?.gpu_inventory&&Array.isArray(host.gpu_inventory.devices)?host.gpu_inventory.devices:[];
  const octoServices = (host=octoHost()) => Array.isArray(host?.inference_servers)?host.inference_servers.filter(item=>item&&typeof item.service_id==="string"):[];
  const servicePhase = (service) => {
    if(!service||service.state!=="ready"||!Array.isArray(service.loaded_models)||!service.loaded_models.length)return "unavailable";
    const active=service.active_slots?.state==="measured"?safeCount(service.active_slots.value):null;
    return active===null?"ready":active>0?"processing":"idle";
  };
  const assignedDevices = (serviceId) => gpuInventory().filter(gpu=>Array.isArray(gpu.active_services)&&gpu.active_services.includes(serviceId)).map(gpu=>gpu.index).filter(Number.isInteger).sort((a,b)=>a-b);
  const machineObserved = () => isoTime(octoHost()?.gpu_inventory?.observed_at||octoHost()?.observed_at);
  const observationAge = (observed) => { const n=observed?Date.now()-Date.parse(observed):NaN; return Number.isFinite(n)&&n>=0?`${Math.floor(n/1000)}s ago`:"Not reported"; };
  const ensureSelector = (root,id,className) => {
    let button=Array.from(root.children).find(child=>child.dataset.octoComponent===id);
    if(button)return button;
    button=node("button",className);button.type="button";button.dataset.octoComponent=id;
    for(const part of ["title","meta","vram","detail"]){const child=node(part==="detail"?"small":"span",part==="title"?"octo-device-title":part==="meta"?"octo-device-meta":part==="vram"?"octo-vram-bar":"");child.dataset.selectorPart=part;if(part==="vram"){child.setAttribute("role","progressbar");child.setAttribute("aria-valuemin","0");child.setAttribute("aria-valuemax","100");const fill=node("span","octo-vram-fill");fill.dataset.selectorPart="vram-fill";child.append(fill);}button.append(child);}
    root.querySelectorAll(":scope > p.octo-empty").forEach(item=>item.remove());root.append(button);return button;
  };
  const renderSelectionButtons = () => {
    const gpuRoot=$("octo1-gpu-selectors"),modelRoot=$("octo1-model-selectors"),gpuList=gpuInventory(),services=octoServices();
    const selectedModel=state.selected.kind==="model"?state.selected.id:null;
    const selectedGpu=state.selected.kind==="gpu"?Number(state.selected.id.slice(4)):null;
    const selectedGpuServices=new Set(gpuList.find(gpu=>gpu.index===selectedGpu)?.active_services||[]);
    if(gpuRoot){
      const seen=new Set();
      gpuList.slice(0,32).forEach(gpu=>{const id="gpu-"+gpu.index,active=Array.isArray(gpu.active_services)?gpu.active_services:[],button=ensureSelector(gpuRoot,id,"octo-device-button");seen.add(id);button.setAttribute("aria-pressed",state.selected.kind==="gpu"&&state.selected.id===id?"true":"false");button.dataset.modelHighlight=selectedModel&&active.includes(selectedModel)?"true":"false";button.dataset.state=state.telemetryError?"stale":state.inFlight?"checking":"current";button.querySelector('[data-selector-part="title"]').textContent=(gpu.name||"GPU")+" · device "+amount(gpu.index);button.querySelector('[data-selector-part="meta"]').textContent=amount(gpu.utilization_percent,"%")+" utilization";const reading=vramReading(gpu),bar=button.querySelector('[data-selector-part="vram"]'),fill=button.querySelector('[data-selector-part="vram-fill"]');bar.dataset.state=state.telemetryError?"stale":reading?"measured":"unavailable";bar.setAttribute("aria-label",`VRAM use: ${vramLabel(gpu)}`);if(reading){bar.setAttribute("aria-valuenow",String(reading.percent.toFixed(1)));fill.setAttribute("style",`width:${reading.percent.toFixed(1)}%`);}else{bar.removeAttribute("aria-valuenow");fill.setAttribute("style","width:0%");}bar.title=vramLabel(gpu);button.querySelector('[data-selector-part="detail"]').textContent=vramLabel(gpu)+(active.length?` · ${active.map(serviceLabel).join(" · ")}`:" · No authorized inference process mapped");});
      const buttons=Array.from(gpuRoot.children).filter(child=>child.matches("[data-octo-component]"));buttons.forEach(button=>{if(!seen.has(button.dataset.octoComponent))button.dataset.state="stale";});
      if(!gpuList.length&&!buttons.length&&!gpuRoot.querySelector(":scope > p"))gpuRoot.append(node("p","octo-empty","Authenticated OCTO1 GPU readings are unavailable; no devices are inferred."));
    }
    if(modelRoot){
      const seen=new Set();
      services.slice(0,12).forEach(service=>{const id="model-"+service.service_id,phase=servicePhase(service),button=ensureSelector(modelRoot,id,"octo-model-button");seen.add(id);button.setAttribute("aria-pressed",state.selected.kind==="model"&&state.selected.id===service.service_id?"true":"false");button.dataset.modelHighlight=selectedGpuServices.has(service.service_id)?"true":"false";button.dataset.state=state.telemetryError?"stale":state.inFlight?"checking":phase;button.querySelector('[data-selector-part="title"]').textContent=service.display_name||service.service_id;button.querySelector('[data-selector-part="meta"]').textContent=phaseLabel(phase);const devices=assignedDevices(service.service_id);button.querySelector('[data-selector-part="detail"]').textContent=devices.length?"GPU "+devices.join(", "):"GPU assignment unavailable";});
      const buttons=Array.from(modelRoot.children).filter(child=>child.matches("[data-octo-component]"));buttons.forEach(button=>{if(!seen.has(button.dataset.octoComponent))button.dataset.state="stale";});
      if(!services.length&&!buttons.length&&!modelRoot.querySelector(":scope > p"))modelRoot.append(node("p","octo-empty","OCTO1 model service readings are unavailable."));
    }
    const systems=$("octo1-system-selectors");systems?.querySelectorAll("[data-octo-component]").forEach(button=>{const active=state.selected.kind==="system"&&state.selected.id===button.dataset.octoComponent;button.setAttribute("aria-pressed",active?"true":"false");});
    $("octo1-front-hotspots")?.querySelectorAll("[data-octo-component]").forEach(button=>{const active=state.selected.kind==="system"&&state.selected.id===button.dataset.octoComponent;button.setAttribute("aria-pressed",active?"true":"false");});
  };
  const phaseLabel = (phase) => ({unavailable:"UNAVAILABLE",ready:"READY · SLOT DETAIL UNAVAILABLE",processing:"PROCESSING · ACTIVE SLOT",idle:"READY · IDLE"}[phase]||"UNKNOWN");
  const renderComponentDetail = () => {
    const title=$("octo1-detail-title"),description=$("octo1-detail-state"),metrics=$("octo1-detail-metrics"),source=$("octo1-detail-source");if(!title||!description||!metrics)return;metrics.replaceChildren();
    const observed=machineObserved();
    if(state.selected.kind==="gpu"){
      const gpu=gpuInventory().find(item=>`gpu-${item.index}`===state.selected.id);
      if(!gpu){title.textContent="GPU device";description.textContent="The selected device is not present in the latest authenticated inventory.";source.textContent="Source status is unavailable; no previous value is substituted.";return;}
      const serviceIds=Array.isArray(gpu.active_services)?gpu.active_services:[];const services=octoServices().filter(service=>serviceIds.includes(service.service_id));
      const reading=vramReading(gpu);title.textContent=`${gpu.name||"GPU"} · device ${gpu.index}`;description.textContent=serviceIds.length?`Mapped to ${services.map(service=>service.display_name||service.service_id).join(", ")}. Mapping comes from the live host process-to-GPU projection.`:"No allowlisted Grace inference service is mapped to this device.";
      addRow(metrics,"Utilization",amount(gpu.utilization_percent,"%"));addRow(metrics,"VRAM used / total",vramLabel(gpu));addRow(metrics,"VRAM remaining",reading?bytes(reading.remaining):"Unavailable");addRow(metrics,"Temperature",amount(gpu.temperature_celsius," °C"));addRow(metrics,"Power",amount(gpu.power_watts," W"));addRow(metrics,"GPU fan speed",amount(gpu.fan_percent,"%"));addRow(metrics,"Physical chassis bay","Unavailable · live GPU device ID is not mapped to a bay");addRow(metrics,"GPU observation",visibleTime(gpu.observed_at||observed));source.textContent=`Source: ${gpu.source||"NVIDIA telemetry projection"}. Device index and model allocation are dynamic; the manufacturer image does not identify this device's physical bay.`;return;
    }
    if(state.selected.kind==="model"){
      const service=octoServices().find(item=>item.service_id===state.selected.id);if(!service){title.textContent="Inference model";description.textContent="The selected service is not present in the latest authenticated projection.";source.textContent="Source status unavailable.";return;}
      const phase=servicePhase(service),devices=assignedDevices(service.service_id),slotView=service.slot_context?.state==="measured"&&Array.isArray(service.slot_context.slots)?service.slot_context.slots:[];title.textContent=service.display_name||service.service_id;description.textContent=phaseLabel(phase);addRow(metrics,"Loaded model",Array.isArray(service.loaded_models)&&service.loaded_models.length?service.loaded_models.join(", "):"Unavailable");addRow(metrics,"Service readiness",safeState(service.state||"unavailable"));addRow(metrics,"GPU allocation",devices.length?`GPU ${devices.join(", ")} · current service process mapping` : "Unavailable · no mapped process");addRow(metrics,"Active slots",service.active_slots?.state==="measured"?`${amount(service.active_slots.value)} / ${amount(service.active_slots.total)}`:"Unavailable");addRow(metrics,"Configured context per slot",slotView.length?Array.from(new Set(slotView.map(slot=>safeTokenCount(slot.context_tokens)).filter(value=>value!==null))).map(value=>amount(value," tokens")).join(" · ")||"Unavailable":"Unavailable · current projection has no slot context fields");const contextTotal=slotView.reduce((total,slot)=>total+(safeTokenCount(slot.context_tokens)||0),0);addRow(metrics,"Server context across slots",slotView.some(slot=>safeTokenCount(slot.context_tokens)!==null)?`${amount(contextTotal)} token-slots · sum of per-slot limits`:"Unavailable");slotView.forEach(slot=>{const context=safeTokenCount(slot.context_tokens),prompt=safeTokenCount(slot.prompt_tokens),processed=safeTokenCount(slot.prompt_tokens_processed),cached=safeTokenCount(slot.prompt_tokens_cached);const utilization=context&&prompt!==null?`${amount(prompt)} / ${amount(context)} tokens · ${(prompt/context*100).toFixed(1)}%${slot.processing===true?" · processing":slot.processing===false?" · idle/last reported":""}`:"Unavailable · source counters missing";addRow(metrics,`Slot ${slot.slot_id} prompt-context use`,utilization);if(processed!==null)addRow(metrics,`Slot ${slot.slot_id} prompt processed`,`${amount(processed)} tokens${slot.processing===true?" · in progress":" · reported"}`);if(cached!==null)addRow(metrics,`Slot ${slot.slot_id} cached prompt tokens`,amount(cached));});addRow(metrics,"KV-cache allocation",service.slot_context?.kv_cache_bytes?.state==="measured"&&Number.isSafeInteger(service.slot_context.kv_cache_bytes.value)?bytes(service.slot_context.kv_cache_bytes.value):"Unavailable · model server does not expose KV-cache bytes");addRow(metrics,"Queued requests",service.queued_requests?.state==="measured"?amount(service.queued_requests.value):"Unavailable · not exposed by current server");addRow(metrics,"Prompt/generation timing","Unavailable · server exposes no stage timing counters");addRow(metrics,"Observation",visibleTime(service.slot_context?.observed_at||service.observed_at));source.textContent=`Readiness: ${service.readiness_source||"Unavailable"}. Slot context: ${service.slot_context?.source||"Unavailable"}. Context limits and prompt counters come from numeric llama.cpp /slots fields; they are per-slot. No prompt text, task IDs, queue depth, or KV allocation bytes are exposed.`;return;
    }
    if(state.selected.kind==="system"){
      const system=state.selected.id;
      const fanMatch=/^fan-([1-5])$/.exec(system);
      if(fanMatch){const position=Number(fanMatch[1]);title.textContent=`Front fan · visual position ${position}`;description.textContent=`Physical front fan ${position} of five, counted left-to-right as viewed in the manufacturer front reference.`;addRow(metrics,"Fan RPM","Unavailable · OCTO1 controller feed not connected");addRow(metrics,"PWM, target, and mode","Unavailable · controller channel is not mapped");addRow(metrics,"Recent history","Unavailable · no verified OCTO1 fan readings");addRow(metrics,"Physical position","Manufacturer front-panel image · left-to-right visual index only");source.textContent="Visual position is not a controller channel number. No telemetry is inferred from the artwork.";return;}
      if(system==="front-panel"){title.textContent="Front display and controls";description.textContent="The right-side display and control area is shown in the original manufacturer front reference.";addRow(metrics,"Display status","Unavailable · no authorized OCTO1 front-panel feed");addRow(metrics,"Button/control state","Unavailable");source.textContent="The image establishes visual placement only; no controls are exposed in this read-only view.";return;}
      const labels={controller:"Manufacturer fan controller",thermal:"Environmental sensors",psu:"Power supplies",watchdog:"Hardware watchdog"};title.textContent=labels[system]||"Chassis component";description.textContent=system==="controller"?"A manufacturer board reference is available; its installation in OCTO1 has not been verified.":"No current OCTO1-authorized controller projection supplies this component’s readings.";
      const rows={controller:[["OCTO1 device identity","Unverified"],["Controller endpoint","Unavailable"],["Fan channels and mappings","Unavailable"],["RPM, PWM, and targets","Unavailable"],["Watchdog heartbeat","Unavailable"]],thermal:[["Available sensor readings","Unavailable"],["Configured thresholds","Unavailable"]],psu:[["Controller-reported power","Unavailable"],["PSU temperature","Unavailable"]],watchdog:[["OCTO1 watchdog presence","Unverified"],["Operating state and heartbeat","Unavailable"],["Timeout, reset counter, and history","Unavailable"]]};(rows[system]||[]).forEach(([key,value])=>addRow(metrics,key,value));source.textContent="Manufacturer capability images are reference material, not proof of OCTO1 hardware installation or a live controller connection.";return;
    }
    title.textContent="OCTO1 overview";const host=octoHost();description.textContent=host?`${gpuInventory(host).length} measured GPU devices · ${octoServices(host).length} configured inference services`:"OCTO1 telemetry has not been received.";addRow(metrics,"Machine identity","OctoMiner X12 Ultra · documented OCTO1 hardware");addRow(metrics,"GPU source",host?.gpu_inventory?.source||"Unavailable");addRow(metrics,"GPU inventory state",host?.gpu_inventory?.state||"Unavailable");addRow(metrics,"Physical GPU bay mapping","Unavailable · no verified device-to-bay mapping");addRow(metrics,"Observation",visibleTime(observed));source.textContent="Manufacturer front geometry is shown above. Internal GPU bay assignments remain separate from host GPU device indexes.";
  };
  const snapshotSample = () => {
    const host=octoHost();if(!host)return;const observed=machineObserved();const services=octoServices(host);
    state.history.unshift({captured_at:new Date().toISOString(),observed_at:observed,devices:gpuInventory(host).map(gpu=>({index:gpu.index,name:gpu.name,utilization_percent:gpu.utilization_percent,temperature_celsius:gpu.temperature_celsius,fan_percent:gpu.fan_percent,active_services:Array.isArray(gpu.active_services)?gpu.active_services.slice():[]})),models:services.map(service=>({service_id:service.service_id,phase:servicePhase(service),active_slots:service.active_slots?.state==="measured"?service.active_slots.value:null}))});state.history=state.history.slice(0,HISTORY_LIMIT);
  };
  const ensureHardwareActivityCard = (root,key,title,source) => {
    let card=directChild(root,"hardwareActivity",key);if(card)return card;
    card=node("article","octo-throughput-card octo-hardware-activity-card");card.dataset.hardwareActivity=key;
    const heading=node("div","octo-throughput-heading"),name=node("strong","",title),latest=node("span","octo-throughput-latest");latest.dataset.hardwareActivityLatest="";heading.append(name,latest);
    const chart=document.createElementNS("http://www.w3.org/2000/svg","svg");chart.setAttribute("class","octo-throughput-chart octo-hardware-activity-chart");chart.setAttribute("viewBox","0 0 320 112");chart.setAttribute("role","img");chart.setAttribute("aria-label",title+" · measured source observations over five minutes");const grid=svgNode("path","octo-rate-grid");grid.setAttribute("d","M24 10V88H310 M24 49H310");chart.append(grid);
    const legend=node("div","octo-hardware-activity-legend"),empty=node("p","octo-throughput-empty"),provenance=node("p","octo-throughput-source",source);empty.dataset.hardwareActivityEmpty="";legend.dataset.hardwareActivityLegend="";card.append(heading,chart,legend,empty,provenance);root.append(card);return card;
  };
  const renderHardwareActivity = (now) => {
    const root=$("octo1-throughput-chart-grid");if(!root)return;
    const start=now-RATE_WINDOW_MS,palette=["#438b7d","#b36a35","#5279a7","#8b6ba7","#b34f58","#758c3d"],gpuCard=ensureHardwareActivityCard(root,"gpu-utilization","GPU utilization · measured %","OCTO1 nvidia-smi source snapshots. System-level GPU load is not attributed to a specific Grace request or model.");
    const gpuSeries=new Map();state.hardwareHistory.forEach(sample=>sample.gpus.forEach(item=>{const at=Date.parse(item.at);if(at>=start&&at<=now){if(!gpuSeries.has(item.index))gpuSeries.set(item.index,[]);gpuSeries.get(item.index).push({at,value:item.value});}}));
    const gpuLegend=gpuCard.querySelector("[data-hardware-activity-legend]"),gpuSvg=gpuCard.querySelector("svg"),gpuActive=new Set();gpuLegend.replaceChildren();
    [...gpuSeries.entries()].sort((a,b)=>a[0]-b[0]).forEach(([index,raw],seriesIndex)=>{
      const points=[...new Map(raw.map(point=>[point.at,point])).values()].sort((a,b)=>a.at-b.at);if(!points.length)return;const id=String(index),color=palette[seriesIndex%palette.length],lineKey="gpu-"+id;gpuActive.add(lineKey);
      let line=Array.from(gpuSvg.children).find(item=>item.dataset.hardwareLine===lineKey);if(!line){line=svgNode("polyline","octo-rate-line");line.dataset.hardwareLine=lineKey;gpuSvg.append(line);}line.setAttribute("stroke",color);line.setAttribute("points",points.map(point=>`${(24+((point.at-start)/RATE_WINDOW_MS)*286).toFixed(1)},${(88-(point.value/100)*68).toFixed(1)}`).join(" "));
      let marker=Array.from(gpuSvg.children).find(item=>item.dataset.hardwareMarker===lineKey);if(!marker){marker=svgNode("circle","octo-rate-point");marker.setAttribute("r","3.5");marker.dataset.hardwareMarker=lineKey;gpuSvg.append(marker);}const last=points[points.length-1];marker.setAttribute("fill",color);marker.setAttribute("cx",(24+((last.at-start)/RATE_WINDOW_MS)*286).toFixed(1));marker.setAttribute("cy",(88-(last.value/100)*68).toFixed(1));
      const label=node("span","",`GPU ${id}`);label.setAttribute("data-hardware-series-label",lineKey);label.setAttribute("style",`color:${color}`);gpuLegend.append(label);
    });
    gpuSvg.querySelectorAll("[data-hardware-line]").forEach(item=>{if(!gpuActive.has(item.dataset.hardwareLine))item.remove();});gpuSvg.querySelectorAll("[data-hardware-marker]").forEach(item=>{if(!gpuActive.has(item.dataset.hardwareMarker))item.remove();});
    const gpuLatest=[...gpuSeries.entries()].flatMap(([index,points])=>points.map(point=>({index,point}))).sort((a,b)=>a.point.at-b.point.at).slice(-1)[0],gpuLabel=gpuCard.querySelector("[data-hardware-activity-latest]"),gpuEmpty=gpuCard.querySelector("[data-hardware-activity-empty]");
    if(gpuLatest){gpuLabel.textContent=`GPU ${gpuLatest.index}: ${gpuLatest.point.value}% · ${state.telemetryError||now-gpuLatest.point.at>30000?"STALE":"MEASURED"} · ${visibleTime(new Date(gpuLatest.point.at).toISOString())}`;gpuEmpty.textContent=`${gpuSeries.size} GPU utilization series · ${Math.max(...[...gpuSeries.values()].map(points=>points.length))} max source samples · rolling five-minute window.`;}else{gpuLabel.textContent="UNAVAILABLE";gpuEmpty.textContent="No fresh measured GPU utilization observations in the rolling five-minute window.";}
    const models=[["grace-reasoning-80b","Grace reasoning 80B"],["grace-vision-30b","Grace vision 30B"],["grace-autonomic-0.6b","Grace autonomic 0.6B"]];
    models.forEach(([modelId,label],seriesIndex)=>{
      const card=ensureHardwareActivityCard(root,"slots-"+modelId,`${label} · active inference slots`,`Current authenticated model-server slot occupancy. Slot processing and active count are system observations, not request-specific GPU attribution.`),series=[];
      state.hardwareHistory.forEach(sample=>sample.models.forEach(item=>{if(item.service_id===modelId&&Date.parse(item.at)>=start&&Date.parse(item.at)<=now)series.push({at:Date.parse(item.at),active:item.active,total:item.total,processing:item.processing});}));
      const points=[...new Map(series.map(point=>[point.at,point])).values()].sort((a,b)=>a.at-b.at),svg=card.querySelector("svg"),key="slots-"+modelId,color=palette[(seriesIndex+2)%palette.length];let line=Array.from(svg.children).find(item=>item.dataset.hardwareLine===key),marker=Array.from(svg.children).find(item=>item.dataset.hardwareMarker===key);
      if(!line){line=svgNode("polyline","octo-rate-line");line.dataset.hardwareLine=key;svg.append(line);}if(!marker){marker=svgNode("circle","octo-rate-point");marker.setAttribute("r","3.5");marker.dataset.hardwareMarker=key;svg.append(marker);}line.setAttribute("stroke",color);marker.setAttribute("fill",color);
      const legend=card.querySelector("[data-hardware-activity-legend]");legend.replaceChildren(node("span","",`${label} · active slot count`));legend.children[0].setAttribute("style",`color:${color}`);
      const latest=card.querySelector("[data-hardware-activity-latest]"),empty=card.querySelector("[data-hardware-activity-empty]");
      if(!points.length){line.setAttribute("points","");marker.setAttribute("visibility","hidden");latest.textContent="NO FRESH SLOT SAMPLE";empty.textContent="Unavailable · no fresh measured slot occupancy in the rolling five-minute window.";return;}
      const maximum=Math.max(1,...points.map(point=>point.total)),coords=points.map(point=>({x:24+((point.at-start)/RATE_WINDOW_MS)*286,y:88-(point.active/maximum)*68})),last=points[points.length-1],lastCoord=coords[coords.length-1],conflict=last.processing!==null&&last.processing!==(last.active>0),stateLabel=conflict?"SLOT STATE MISMATCH":last.processing===null?(last.active>0?"PROCESSING":"IDLE"):(last.processing?"PROCESSING":"IDLE");
      line.setAttribute("points",coords.map(point=>`${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" "));marker.setAttribute("cx",lastCoord.x.toFixed(1));marker.setAttribute("cy",lastCoord.y.toFixed(1));marker.setAttribute("visibility","visible");latest.textContent=`${stateLabel} · ${last.active}/${last.total} · ${state.telemetryError||now-last.at>30000?"STALE":"MEASURED"}`;empty.textContent=`${points.length} source observations · active slot count / configured slots · ${visibleTime(new Date(last.at).toISOString())}.`;
    });
  };
  const renderTimeline = () => {
    const root=$("octo1-activity-list");if(!root)return;
    const pages=Math.max(1,Math.ceil(state.history.length/ACTIVITY_PAGE_SIZE));state.activityPage=Math.max(0,Math.min(state.activityPage,pages-1));
    const start=state.activityPage*ACTIVITY_PAGE_SIZE,visible=state.history.slice(start,start+ACTIVITY_PAGE_SIZE),scrollTop=root.scrollTop||0;
    if(!visible.length){if(!root.querySelector(":scope > p.octo-empty")){root.replaceChildren(node("p","octo-empty","No telemetry samples captured in this browser session."));}const previous=$("octo1-activity-previous"),next=$("octo1-activity-next"),pageLabel=$("octo1-activity-page");if(previous)previous.disabled=true;if(next)next.disabled=true;if(pageLabel)pageLabel.textContent="Page 1 of 1 · no samples";return;}
    root.querySelectorAll(":scope > p.octo-empty").forEach(item=>item.remove());
    const wanted=new Set(visible.map(sample=>sample.captured_at));root.querySelectorAll(":scope > .octo-activity-sample").forEach(item=>{if(!wanted.has(item.dataset.activitySample))item.remove();});
    visible.forEach(sample=>{let item=directChild(root,"activitySample",sample.captured_at);if(!item){item=node("article","octo-activity-sample");item.dataset.activitySample=sample.captured_at;const head=node("div","octo-activity-head"),time=node("strong"),count=node("span"),readings=node("p","octo-activity-gpus"),models=node("p","octo-activity-models");time.dataset.activityTime="";count.dataset.activityCount="";readings.dataset.activityGpuReadings="";models.dataset.activityModelReadings="";head.append(time,count);item.append(head,readings,models);}item.querySelector("[data-activity-time]").textContent=visibleTime(sample.observed_at||sample.captured_at);item.querySelector("[data-activity-count]").textContent=`${sample.devices.length} GPU readings`;item.querySelector("[data-activity-gpu-readings]").textContent=sample.devices.map(gpu=>`GPU ${gpu.index}: ${amount(gpu.utilization_percent,"%")} · ${amount(gpu.temperature_celsius,"°C")} · GPU fan ${amount(gpu.fan_percent,"%")}`).join("  |  ")||"GPU readings unavailable";item.querySelector("[data-activity-model-readings]").textContent=sample.models.map(model=>`${model.service_id}: ${phaseLabel(model.phase)}${model.active_slots===null?"":" · slots "+model.active_slots}`).join("  |  ")||"Model status unavailable";root.append(item);});
    root.scrollTop=scrollTop;
    const previous=$("octo1-activity-previous"),next=$("octo1-activity-next"),pageLabel=$("octo1-activity-page");if(previous)previous.disabled=state.activityPage===0;if(next)next.disabled=state.activityPage>=pages-1;if(pageLabel)pageLabel.textContent=state.history.length?`Page ${state.activityPage+1} of ${pages} · ${state.history.length} recent samples`:"Page 1 of 1 · no samples";
  };
  const renderMeasuredRates = () => {
    const root=$("octo1-throughput-chart-grid");if(!root)return;
    const now=Date.now(),windowStart=now-RATE_WINDOW_MS,models=[
      ["grace-reasoning-80b","Grace reasoning 80B"],
      ["grace-vision-30b","Grace vision 30B"],
      ["grace-autonomic-0.6b","Grace autonomic 0.6B"]
    ];
    renderHardwareActivity(now);
    models.forEach(([modelId,label])=>{
      let card=directChild(root,"rateModel",modelId);
      if(!card){card=node("article","octo-throughput-card");card.dataset.rateModel=modelId;const heading=node("div","octo-throughput-heading"),name=node("strong","",label),latest=node("span","octo-throughput-latest");latest.dataset.rateLatest="";heading.append(name,latest);const chart=document.createElementNS("http://www.w3.org/2000/svg","svg");chart.setAttribute("class","octo-throughput-chart");chart.setAttribute("viewBox","0 0 320 112");chart.setAttribute("role","img");chart.setAttribute("aria-label",`${label} measured completion-token response rate over five minutes`);const grid=svgNode("path","octo-rate-grid");grid.setAttribute("d","M24 10V88H310 M24 49H310");const line=svgNode("polyline","octo-rate-line");line.dataset.rateLine="";const point=svgNode("circle","octo-rate-point");point.setAttribute("r","3.5");point.dataset.ratePoint="";chart.append(grid,line,point);const empty=node("p","octo-throughput-empty");empty.dataset.rateEmpty="";const source=node("p","octo-throughput-source","Measured completed output tokens ÷ router-recorded provider-call elapsed time. Includes service/network overhead; this is not server-only GPU token timing.");card.append(heading,chart,empty,source);const live=node("div","octo-live-stream");live.dataset.liveStreamModel=modelId;const liveHeading=node("div","octo-throughput-heading"),liveLabel=node("strong","","Live streamed output · characters/s"),liveLatest=node("span","octo-throughput-latest");liveLatest.dataset.liveRateLatest="";liveHeading.append(liveLabel,liveLatest);const liveChart=document.createElementNS("http://www.w3.org/2000/svg","svg");liveChart.setAttribute("class","octo-throughput-chart octo-live-stream-chart");liveChart.setAttribute("viewBox","0 0 320 112");liveChart.setAttribute("role","img");liveChart.setAttribute("aria-label",`${label} measured streamed response characters per second over five minutes`);const liveGrid=svgNode("path","octo-rate-grid");liveGrid.setAttribute("d","M24 10V88H310 M24 49H310");const liveLine=svgNode("polyline","octo-live-rate-line");liveLine.dataset.liveRateLine="";const livePoint=svgNode("circle","octo-live-rate-point");livePoint.setAttribute("r","3.5");livePoint.dataset.liveRatePoint="";liveChart.append(liveGrid,liveLine,livePoint);const liveEmpty=node("p","octo-throughput-empty");liveEmpty.dataset.liveRateEmpty="";const liveSource=node("p","octo-throughput-source","Application-side received text delta cadence. This is not model-server token throughput or GPU compute speed.");live.append(liveHeading,liveChart,liveEmpty,liveSource);card.append(live);root.append(card);}
      const points=state.rateHistory.filter(item=>item.model_id===modelId&&item.at>=windowStart&&item.at<=now).sort((a,b)=>a.at-b.at),line=card.querySelector("[data-rate-line]"),point=card.querySelector("[data-rate-point]"),latest=card.querySelector("[data-rate-latest]"),empty=card.querySelector("[data-rate-empty]");
      if(!points.length){line.setAttribute("points","");point.setAttribute("visibility","hidden");latest.textContent="No measured response in window";empty.textContent="Unavailable · no successful provider response with both token count and elapsed-time evidence in the last five minutes.";return;}
      const maximum=Math.max(1,...points.map(item=>item.tokens_per_provider_second)),coords=points.map(item=>{const x=24+((item.at-windowStart)/RATE_WINDOW_MS)*286,y=88-(item.tokens_per_provider_second/maximum)*68;return {x,y};});line.setAttribute("points",coords.map(item=>`${item.x.toFixed(1)},${item.y.toFixed(1)}`).join(" "));const last=coords[coords.length-1];point.setAttribute("cx",last.x.toFixed(1));point.setAttribute("cy",last.y.toFixed(1));point.setAttribute("visibility","visible");latest.textContent=`${points[points.length-1].tokens_per_provider_second.toFixed(1)} tokens/s · measured`;empty.textContent=points.length<2?"One measured point · a second completed response is needed to draw a line.":`${points.length} measured provider responses · rolling five-minute window`;
    });
    renderLiveStreamRates(models,now,windowStart);
  };
  const renderLiveStreamRates = (models,now,windowStart) => {
    models.forEach(([modelId,label])=>{
      const card=directChild($("octo1-throughput-chart-grid"),"rateModel",modelId),live=card&&directChild(card,"liveStreamModel",modelId);if(!live)return;
      const points=state.liveRateHistory.filter(item=>item.model_id===modelId&&item.at>=windowStart&&item.at<=now).sort((a,b)=>a.at-b.at),line=live.querySelector("[data-live-rate-line]"),point=live.querySelector("[data-live-rate-point]"),latest=live.querySelector("[data-live-rate-latest]"),empty=live.querySelector("[data-live-rate-empty]");
      const active=(state.requestTrace?.requests||[]).some(request=>request?.stream_activity?.status==="generating"&&rateStageModel(request.stream_activity.reasoning_stage)===modelId);
      if(!points.length){line.setAttribute("points","");point.setAttribute("visibility","hidden");latest.textContent=active?"GENERATION ACTIVE":"NO LIVE SAMPLE";const streamState=state.requestTrace?.stream_activity_state;if(streamState!=="available")empty.textContent="Unavailable · authorized stream activity was not returned.";else if(active){const matching=(state.requestTrace?.requests||[]).find(request=>request?.stream_activity?.status==="generating"&&rateStageModel(request.stream_activity.reasoning_stage)===modelId),count=matching?.stream_activity?.deltas?.length||0;empty.textContent=count<2?"Generation is active; waiting for a second timestamped text delta before calculating a rate.":"Generation is active; no positive timestamp interval was measured.";}else empty.textContent="Unavailable · no measured streamed text cadence in the rolling five-minute window.";return;}
      const maximum=Math.max(1,...points.map(item=>item.characters_per_second)),coords=points.map(item=>{const x=24+((item.at-windowStart)/RATE_WINDOW_MS)*286,y=88-(item.characters_per_second/maximum)*68;return {x,y};}),last=coords[coords.length-1],lastPoint=points[points.length-1],isLive=active&&now-lastPoint.at<=15000,isUnavailable=state.requestTrace?.stream_activity_state!=="available",rateState=isUnavailable||active&&!isLive?"STALE":isLive?"LIVE":"measured";line.setAttribute("points",coords.map(item=>`${item.x.toFixed(1)},${item.y.toFixed(1)}`).join(" "));point.setAttribute("cx",last.x.toFixed(1));point.setAttribute("cy",last.y.toFixed(1));point.setAttribute("visibility","visible");latest.textContent=`${lastPoint.characters_per_second.toFixed(1)} chars/s · ${rateState}`;empty.textContent=`${points.length} timestamped text-delta intervals · ${isUnavailable?"activity refresh unavailable; last measured points retained":active?(isLive?"stream active":"stream active, latest delta stale"):"completed/failed stream history"} · five-minute window`;
    });
  };
  const renderRequestTrace = () => {
    const root=$("octo1-request-trace-list"),trace=state.requestTrace,stateNode=$("octo1-request-trace-state");if(!root||!stateNode)return;root.replaceChildren();
    const statuses={available:"AVAILABLE",not_connected:"OPEN GRACE CHAT",empty:"NO SAVED REQUESTS",authentication_required:"SIGN-IN REQUIRED",denied:"ACCESS DENIED",unavailable:"UNAVAILABLE"};
    const traceState=trace&&typeof trace.state==="string"?trace.state:"unavailable";stateNode.textContent=statuses[traceState]||"UNAVAILABLE";stateNode.dataset.state=["available","not_connected","empty","authentication_required","denied","unavailable"].includes(traceState)?traceState:"unavailable";
    if(traceState!=="available"){const message={not_connected:"Open Grace chat through the existing Dashboard session to inspect its authorized current conversation.",empty:"The current authorized Grace conversation has no saved request events.",authentication_required:"The Dashboard account session expired; sign in through the existing Grace chat.",denied:"Dashboard denied access to the Grace conversation trace.",unavailable:"The durable Grace conversation trace is unavailable."}[traceState]||"No trace data is available.";root.append(node("p","octo-empty",message));return;}
    const requests=Array.isArray(trace.requests)?trace.requests.slice(0,12):[];
    if(!requests.length){root.append(node("p","octo-empty","No saved request events were returned for the current conversation."));return;}
    requests.forEach(request=>{if(!request||typeof request.request_id!=="string")return;const card=node("article","octo-request-trace-card"),head=node("div","octo-request-trace-head");head.append(node("strong","",request.request_id),node("span",`trace-state ${safeState(request.status)}`,String(request.status||"unknown").replaceAll("_"," ")));card.append(head);const lines=node("dl","octo-request-trace-fields");addRow(lines,"Request created",visibleTime(request.created_at));
      const attempts=Array.isArray(request.attempts)?request.attempts.slice(0,4):[];
      if(attempts.length){attempts.forEach((attempt,index)=>{const stage=({autonomic:"0.6B autonomic",interim_30b:"30B vision",reasoning:"80B reasoning"})[attempt.stage]||"route unavailable";const outcome=String(attempt.outcome||"unknown");addRow(lines,`Attempt ${index+1} · ${stage}`,`${attempt.provider||"Provider unavailable"} · ${outcome}`);addRow(lines,"Client call window",`${visibleTime(attempt.started_at)} → ${visibleTime(attempt.ended_at)}${typeof attempt.elapsed_ms==="number"?` · ${amount(attempt.elapsed_ms," ms")}`:""}`);if(attempt.error_code)addRow(lines,"Attempt result code",attempt.error_code);});}
      else addRow(lines,"Provider attempt","No provider-attempt event has been persisted yet.");
      if(request.status==="completed")addRow(lines,"Response persisted",visibleTime(request.response_persisted_at));
      if(request.reasoning_stage)addRow(lines,"Routed stage",({autonomic:"0.6B autonomic",interim_30b:"30B vision",reasoning:"80B reasoning"})[request.reasoning_stage]||"Unavailable");
      if(request.prompt_tokens!==null||request.completion_tokens!==null)addRow(lines,"Returned token counts",`${amount(request.prompt_tokens)} prompt · ${amount(request.completion_tokens)} completion`);
      if(request.finish_reason)addRow(lines,"Finish reason",request.finish_reason);if(request.error_code)addRow(lines,"Durable status code",request.error_code);card.append(lines);root.append(card);
    });
    if(!root.childElementCount)root.append(node("p","octo-empty","No valid request trace records were returned."));
  };
  const renderOctoConsole = () => {
    const host=octoHost(),inventory=host?.gpu_inventory;const observed=machineObserved();const sourceState=host?.state||"unavailable";tag("octo1-machine-state",safeState(sourceState),sourceState==="healthy"?"LIVE SOURCE":"SOURCE "+sourceState.replaceAll("_"," "));const root=$("octo1-console");if(root)root.dataset.hostState=safeState(sourceState);text("octo1-observed",observed?`GPU source observation ${visibleTime(observed)} · ${observationAge(observed)}.`:"No OCTO1 GPU source timestamp has been received.");text("octo1-gpu-count",inventory?.state==="healthy"?`${gpuInventory(host).length} measured`:(inventory?.state||"Unavailable").replaceAll("_"," "));text("octo1-model-count",octoServices(host).filter(service=>service.state==="ready").length?`${octoServices(host).filter(service=>service.state==="ready").length} ready · ${octoServices(host).length} known`:`${octoServices(host).length} known · readiness unavailable`);text("octo1-age",observed?observationAge(observed):"Not reported");renderSelectionButtons();renderComponentDetail();renderTimeline();renderRequestTrace();renderMeasuredRates();
  };
  const setArtworkView = (view) => {
    const stage=$("octo1-chassis-stage"),caption=$("octo1-chassis-caption"),note=$("octo-chassis-view-note"),image=$("octo1-chassis-artwork");if(!stage||!caption||!note||!image)return;
    state.artworkView=view==="open"?"open":"front";stage.dataset.artworkView=state.artworkView;
    document.querySelectorAll("[data-octo-artwork-view]").forEach(button=>button.setAttribute("aria-pressed",button.dataset.octoArtworkView===state.artworkView?"true":"false"));
    if(state.artworkView==="open"){
      note.textContent="Original manufacturer open-chassis view · GPU device-to-bay mapping is unavailable";
      caption.textContent="The manufacturer reference shows the X12 Ultra internal layout. Live GPU device IDs are not matched to physical riser bays; no GPU locations are overlaid.";
      image.alt="Original unmodified OctoMiner X12 Ultra manufacturer artwork showing an open-chassis perspective and internal riser-board layout. Physical host GPU device assignments are not overlaid because their bay mapping is unverified.";
    }else{
      note.textContent="Manufacturer front view · five physical intake fans";
      caption.textContent="Fan positions and the right-side front panel follow the manufacturer front image. Per-fan controller channels and internal GPU bay positions are not identified by OCTO1 telemetry.";
      image.alt="Original OctoMiner X12 Ultra manufacturer artwork showing the front face with five evenly spaced fans and the right-side display and controls. The open chassis view is available by selecting Open-chassis reference.";
    }
  };
  const directChild = (root, attribute, value) => Array.from(root.children).find(child=>child.dataset[attribute]===String(value))||null;
  const metricValue = (list,key,label) => {
    let row=directChild(list,"resourceMetric",key);
    if(!row){row=node("div");row.dataset.resourceMetric=key;row.append(node("dt","",label),node("dd"));list.append(row);}
    return row.querySelector("dd");
  };
  const setMetric = (list,key,label,value) => {metricValue(list,key,label).textContent=String(value);};
  const ensureHardwareCard = (root,host) => {
    let card=directChild(root,"resourceHostCard",host.host_id);if(card)return card;
    card=node("article","resource-card");card.dataset.resourceCard="";card.dataset.resourceKind="hardware";card.dataset.resourceHostCard=host.host_id;card.dataset.search=`${hostLabel(host.host_id)} gpu hardware`;
    const top=node("div","resource-card-top"),heading=node("div"),identity=node("p","eyebrow"),name=node("h3","",hostLabel(host.host_id)),badge=node("span","resource-tag");identity.dataset.hostIdentity="";badge.dataset.hostBadge="";heading.append(identity,name);top.append(heading,badge);card.append(top);
    const metrics=node("dl");metrics.dataset.hostMetrics="";card.append(metrics);const gpuRoot=node("div");gpuRoot.dataset.hostGpus="";card.append(gpuRoot);root.append(card);return card;
  };
  const ensureGpuCard = (root,gpu) => {
    let section=directChild(root,"resourceGpuIndex",gpu.index);if(section)return section;
    section=node("section","resource-gpu");section.dataset.resourceGpuIndex=String(gpu.index);const title=node("h4"),bar=node("div","resource-vram-bar"),fill=node("span","resource-vram-fill"),summary=node("p","resource-vram-summary"),metrics=node("dl");title.dataset.gpuTitle="";bar.dataset.vramBar="";bar.setAttribute("role","progressbar");bar.setAttribute("aria-valuemin","0");bar.setAttribute("aria-valuemax","100");fill.dataset.vramFill="";summary.dataset.vramSummary="";bar.append(fill);metrics.dataset.gpuMetrics="";section.append(title,bar,summary,metrics);root.append(section);return section;
  };
  const ensureInferenceCard = (root,host,service) => {
    const key=`${host.host_id}:${service.service_id||service.display_name||"inference"}`;let card=directChild(root,"resourceInferenceCard",key);if(card)return card;
    card=node("article","resource-card");card.dataset.resourceCard="";card.dataset.resourceKind="inference";card.dataset.resourceInferenceCard=key;card.dataset.search=`${hostLabel(host.host_id)} ${service.display_name||"inference"} model`;
    const top=node("div","resource-card-top"),heading=node("div"),eyebrow=node("p","eyebrow",hostLabel(host.host_id)),title=node("h3"),badge=node("span","resource-tag");title.dataset.inferenceTitle="";badge.dataset.inferenceBadge="";heading.append(eyebrow,title);top.append(heading,badge);card.append(top);const metrics=node("dl");metrics.dataset.inferenceMetrics="";card.append(metrics);root.append(card);return card;
  };
  const renderTelemetry = () => {
    const cards=$("resource-cards"),hosts=$("resource-host-cards");if(!cards||!hosts)return;const data=state.telemetry;
    if(!data||!Array.isArray(data.hosts)){
      let cardMessage=cards.querySelector(":scope > p");if(!cardMessage){cardMessage=node("p","");cards.append(cardMessage);}cardMessage.textContent=`Inference telemetry unavailable (${state.telemetryError||"not_observed"}).`;
      let hostMessage=hosts.querySelector(":scope > p");if(!hostMessage){hostMessage=node("p","");hosts.append(hostMessage);}hostMessage.textContent=state.telemetryError?"Host readings unavailable · "+safeError(state.telemetryError):"Host readings unavailable; no values are inferred.";return;
    }
    cards.querySelectorAll(":scope > p").forEach(item=>item.remove());hosts.querySelectorAll(":scope > p").forEach(item=>item.remove());
    const seenHosts=new Set(),seenServices=new Set();
    data.hosts.slice(0,8).forEach(host=>{
      const inv=host.gpu_inventory&&Array.isArray(host.gpu_inventory.devices)?host.gpu_inventory:{state:"unavailable",source:"Unavailable",devices:[]};const card=ensureHardwareCard(hosts,host);seenHosts.add(host.host_id);
      card.querySelector("[data-host-identity]").textContent=host.identity_state==="verified"?"VERIFIED HOST TELEMETRY":"DOCUMENTED · IDENTITY UNVERIFIED";
      const badge=card.querySelector("[data-host-badge]"),observed=isoTime(inv.observed_at||host.observed_at),age=observed?Date.now()-Date.parse(observed):Infinity,expired=!Number.isFinite(age)||age>(Number(data.freshness_window_seconds)||30)*1000,sourceUnavailable=inv.state!=="healthy";let badgeText="LIVE SOURCE",badgeState="healthy";
      if(state.telemetryError){badgeText="STALE";badgeState="stale";badge.title="Refresh failed: "+safeError(state.telemetryError);}
      else if(state.inFlight){badgeText=expired||sourceUnavailable?"STALE · REFRESHING":"REFRESHING";badgeState=expired||sourceUnavailable?"stale":"checking";}
      else if(sourceUnavailable||expired){badgeText=sourceUnavailable?`SOURCE ${safeState(inv.state).replaceAll("_"," ").toUpperCase()}`:"STALE SOURCE";badgeState=sourceUnavailable?safeState(inv.state):"stale";}
      else badge.title="";
      badge.textContent=badgeText;badge.dataset.state=badgeState;card.dataset.state=badgeState;
      const hostMetrics=card.querySelector("[data-host-metrics]");setMetric(hostMetrics,"inventory","GPU inventory",inv.state==="healthy"?`${inv.devices.length} device(s)`:"Unavailable");setMetric(hostMetrics,"source","Inventory source",inv.source||"Unavailable");setMetric(hostMetrics,"observed","Observed",observed?visibleTime(observed):"Not reported");
      const gpuRoot=card.querySelector("[data-host-gpus]"),seenGpus=new Set();
      inv.devices.slice(0,32).forEach(gpu=>{const section=ensureGpuCard(gpuRoot,gpu);seenGpus.add(String(gpu.index));section.dataset.state=badgeState==="healthy"?"current":badgeState==="checking"?"checking":"stale";section.querySelector("[data-gpu-title]").textContent=`${gpu.name||"GPU"} · device ${amount(gpu.index)}`;const reading=vramReading(gpu),bar=section.querySelector("[data-vram-bar]"),fill=section.querySelector("[data-vram-fill]"),summary=section.querySelector("[data-vram-summary]");bar.dataset.state=state.telemetryError?"stale":reading?"measured":"unavailable";bar.setAttribute("aria-label",`VRAM use: ${vramLabel(gpu)}`);if(reading){bar.setAttribute("aria-valuenow",String(reading.percent.toFixed(1)));fill.setAttribute("style",`width:${reading.percent.toFixed(1)}%`);}else{bar.removeAttribute("aria-valuenow");fill.setAttribute("style","width:0%");}summary.textContent=vramLabel(gpu);const metrics=section.querySelector("[data-gpu-metrics]");
        setMetric(metrics,"utilization","Utilization",amount(gpu.utilization_percent,"%"));setMetric(metrics,"vram","VRAM used / total",`${bytes(gpu.memory_used_bytes)} / ${bytes(gpu.memory_total_bytes)}`);setMetric(metrics,"temperature","Temperature",amount(gpu.temperature_celsius," °C"));setMetric(metrics,"power","Power",amount(gpu.power_watts," W"));setMetric(metrics,"fan","GPU fan",amount(gpu.fan_percent,"%"));setMetric(metrics,"services","Active services",Array.isArray(gpu.active_services)&&gpu.active_services.length?gpu.active_services.join(", "):"None identified");
      });
      gpuRoot.querySelectorAll("[data-resource-gpu-index]").forEach(section=>{if(!seenGpus.has(section.dataset.resourceGpuIndex))section.dataset.state="stale";});
      (Array.isArray(host.inference_servers)?host.inference_servers:[]).slice(0,12).forEach(service=>{const key=`${host.host_id}:${service.service_id||service.display_name||"inference"}`,serviceCard=ensureInferenceCard(cards,host,service);seenServices.add(key);serviceCard.querySelector("[data-inference-title]").textContent=service.display_name||service.service_id||"Inference service";const serviceBadge=serviceCard.querySelector("[data-inference-badge]"),serviceState=safeState(service.state||"unavailable");serviceBadge.textContent=state.telemetryError?"STALE":serviceState.toUpperCase();serviceBadge.dataset.state=state.telemetryError||service.state!=="ready"?"stale":serviceState;serviceCard.dataset.state=serviceBadge.dataset.state;
        const metrics=serviceCard.querySelector("[data-inference-metrics]");setMetric(metrics,"model","Loaded model",Array.isArray(service.loaded_models)&&service.loaded_models.length?service.loaded_models.join(", "):"Unavailable");setMetric(metrics,"readiness","Readiness source",service.readiness_source||"Unavailable");setMetric(metrics,"slots","Active slots",service.active_slots?.state==="measured"?`${amount(service.active_slots.value)} / ${amount(service.active_slots.total)}`:"Unavailable");setMetric(metrics,"queue","Queued requests",service.queued_requests?.state==="measured"?amount(service.queued_requests.value):"Unavailable · server exposes no queue depth");setMetric(metrics,"observed","Observed",service.observed_at?visibleTime(service.observed_at):"Not reported");
      });
    });
    hosts.querySelectorAll(":scope > [data-resource-host-card]").forEach(card=>{if(!seenHosts.has(card.dataset.resourceHostCard)){const badge=card.querySelector("[data-host-badge]");badge.textContent="STALE · HOST NOT RETURNED";badge.dataset.state="stale";card.dataset.state="stale";}});
    cards.querySelectorAll(":scope > [data-resource-inference-card]").forEach(card=>{if(!seenServices.has(card.dataset.resourceInferenceCard)){const badge=card.querySelector("[data-inference-badge]");badge.textContent="STALE · SERVICE NOT RETURNED";badge.dataset.state="stale";card.dataset.state="stale";}});
    if(!hosts.childElementCount)hosts.append(node("p","","No verified host measurements are available."));if(!cards.childElementCount)cards.append(node("p","","No inference endpoints are verified."));
  };
  const renderStorage = () => {
    const root=$("resource-storage-hosts"),stateTag=$("resource-storage-state"),summary=$("resource-storage-summary");
    if(!root||!stateTag||!summary)return;
    if(!Array.isArray(state.telemetry?.hosts)&&state.attempted){root.querySelectorAll(":scope > p").forEach(item=>{if(item.textContent.trim()==="Storage telemetry has not been requested."||item.dataset.storageInitialStatus==="true"){item.dataset.storageInitialStatus="true";item.textContent=state.inFlight?"Storage telemetry request in progress.":`Storage telemetry unavailable (${safeError(state.telemetryError||state.error||"source_error")}).`;}});}
    const hosts=Array.isArray(state.telemetry?.hosts)?state.telemetry.hosts:[];
    if(Array.isArray(state.telemetry?.hosts))root.querySelectorAll(":scope > p").forEach(item=>{if(item.textContent.trim()==="Storage telemetry has not been requested."||item.dataset.storageInitialStatus==="true")item.remove();});
    if(!hosts.length){stateTag.textContent=state.telemetryError?"UNAVAILABLE":"NOT OBSERVED";stateTag.dataset.state=state.telemetryError?"unavailable":"unknown";summary.textContent="No authenticated storage observation is available. Capacity is not assumed to be zero.";return;}
    const seenHosts=new Set(),unique=new Map();
    hosts.slice(0,8).forEach(host=>{
      if(!host||typeof host.host_id!=="string")return;
      seenHosts.add(host.host_id);
      const storage=host.storage&&typeof host.storage==="object"?host.storage:{state:"unavailable",volumes:[]};
      if(storage.state==="healthy"&&Array.isArray(storage.volumes))storage.volumes.slice(0,64).forEach(volume=>{
        if(!volume||typeof volume.filesystem_id!=="string"||!volume.filesystem_id||unique.has(volume.filesystem_id))return;
        const valid=[volume.total_bytes,volume.used_bytes,volume.available_bytes].every(value=>Number.isSafeInteger(value)&&value>=0)&&volume.total_bytes>0&&volume.used_bytes<=volume.total_bytes&&volume.available_bytes<=volume.total_bytes;
        if(valid)unique.set(volume.filesystem_id,{host,volume});
      });
      let card=directChild(root,"storageHost",host.host_id);
      if(!card){card=node("article","storage-host");card.dataset.storageHost=host.host_id;const head=node("div","storage-host-head"),title=node("h4","",hostLabel(host.host_id)),badge=node("span","resource-tag");badge.dataset.storageBadge="";head.append(title,badge);const list=node("div","storage-volume-list");list.dataset.storageVolumes="";card.append(head,list);root.append(card);}
      const badge=card.querySelector("[data-storage-badge]"),volumes=Array.isArray(storage.volumes)?storage.volumes:[];
      const hostFresh=storage.observed_at&&Date.now()-Date.parse(storage.observed_at)<=Number(state.telemetry.freshness_window_seconds||30)*1000;
      badge.textContent=state.telemetryError?"STALE":storage.state==="healthy"?(hostFresh?"MEASURED":"STALE"):String(storage.state||"unavailable").replaceAll("_"," ").toUpperCase();badge.dataset.state=state.telemetryError||!hostFresh?"stale":storage.state;
      const list=card.querySelector("[data-storage-volumes]"),existing=new Map(Array.from(list.querySelectorAll(":scope > [data-volume-key]")).map(item=>[item.dataset.volumeKey,item]));
      const validRows=[],rowsSeen=new Set();
      if(storage.state==="healthy")for(const volume of volumes){if(!volume||typeof volume.filesystem_id!=="string"||!unique.has(volume.filesystem_id)||rowsSeen.has(volume.filesystem_id))continue; if(unique.get(volume.filesystem_id).host.host_id!==host.host_id)continue;rowsSeen.add(volume.filesystem_id);validRows.push(volume);}
      validRows.forEach(volume=>{
        const key=volume.filesystem_id;let row=existing.get(key);
        if(!row){row=node("div","storage-volume");row.dataset.volumeKey=key;row.append(node("b","storage-volume-title"),node("span","storage-volume-usage"),node("small","storage-volume-observed"));list.append(row);}
        const mount=typeof volume.mount_point==="string"?volume.mount_point:"Mount point unavailable",filesystem=typeof volume.filesystem_type==="string"?volume.filesystem_type:"Filesystem unavailable";
        row.querySelector(".storage-volume-title").textContent=`${mount} · ${filesystem}${volume.device_id?` · ${volume.device_id}`:""}`;
        row.querySelector(".storage-volume-usage").textContent=`${bytes(volume.used_bytes)} used · ${bytes(volume.available_bytes)} available · ${bytes(volume.total_bytes)} total (${Number(volume.percent_used).toFixed(1)}% used)`;
        row.querySelector(".storage-volume-observed").textContent=`Last successful measurement: ${visibleTime(volume.observed_at||storage.observed_at)}`;
        existing.delete(key);
      });
      existing.forEach(item=>item.remove());
      let message=list.querySelector(":scope > [data-storage-unavailable]");
      if(!validRows.length){if(!message){message=node("p","storage-unavailable");message.dataset.storageUnavailable="true";list.append(message);}message.textContent=storage.state==="healthy"?"No unique supported mounted volume was returned.":`Capacity unavailable · ${safeState(storage.state||"unavailable").replaceAll("_"," ")}${storage.error_code?` (${safeError(storage.error_code)})`:""}.`;}else message?.remove();
    });
    root.querySelectorAll(":scope > [data-storage-host]").forEach(card=>{if(!seenHosts.has(card.dataset.storageHost)){const badge=card.querySelector("[data-storage-badge]");badge.textContent="NOT RETURNED · STALE";badge.dataset.state="stale";}});
    const totals=[...unique.values()].reduce((sum,item)=>({total:sum.total+item.volume.total_bytes,used:sum.used+item.volume.used_bytes,available:sum.available+item.volume.available_bytes}),{total:0,used:0,available:0});
    const count=unique.size,allHosts=hosts.length>=4,anyUnavailable=hosts.some(host=>host.storage?.state!=="healthy"),stale=hosts.some(host=>host.storage?.state==="healthy"&&(!host.storage.observed_at||Date.now()-Date.parse(host.storage.observed_at)>Number(state.telemetry.freshness_window_seconds||30)*1000));
    stateTag.textContent=stale?"STALE":count?(anyUnavailable?"PARTIAL · MEASURED":"MEASURED"):(state.telemetryError?"STALE · UNAVAILABLE":"UNAVAILABLE");stateTag.dataset.state=stale?"stale":count?(anyUnavailable||!allHosts?"partial":"healthy"):"unavailable";
    summary.textContent=count?`${bytes(totals.available)} available · ${bytes(totals.used)} used · ${bytes(totals.total)} total across ${count} unique measured filesystem(s). Duplicate views are excluded; unavailable hosts are not counted.`:"No supported mounted volumes were measured. Offline hosts and unavailable capacity are not treated as zero.";
  };
  const applyFilters=()=>{const filter=$("resource-filter")?.value||"all",search=($("resource-search")?.value||"").trim().toLowerCase();document.querySelectorAll("[data-resource-card]").forEach(card=>{const kind=filter==="all"||card.dataset.resourceKind===filter,match=!search||`${card.dataset.search||""} ${card.textContent||""}`.toLowerCase().includes(search);card.hidden=!(kind&&match);});};
  const render=()=>{
    const labels={"not-checked":"NOT CHECKED",checking:"CHECKING",partial:"PARTIAL","authentication-required":"SIGN-IN REQUIRED",unavailable:"UNAVAILABLE",denied:"ACCESS DENIED"};tag("resource-source-state",state.status,labels[state.status]||state.status.toUpperCase());const root=$("resource-monitor-workspace");if(root)root.dataset.state=state.status;const refresh=$("resource-refresh");if(refresh)refresh.disabled=state.inFlight;
    const projection=state.dashboardStatus?.projection_status,source=$("resource-dashboard-state");if(source){const label=projection==="healthy"?"AVAILABLE":projection==="not_initialized"?"NOT INITIALIZED":projection==="unavailable"?"UNAVAILABLE":state.status==="checking"?"CHECKING":state.status==="authentication-required"?"SIGN-IN REQUIRED":state.status==="denied"?"ACCESS DENIED":"NOT CHECKED";source.textContent=label;source.dataset.state=projection||state.status;}
    text("resource-refresh-status",state.status==="not-checked"?"Open Resources to read current host and model-server telemetry through the authenticated Dashboard.":state.status==="checking"?"Refreshing authenticated host and model-server readings…":state.status==="partial"?"Authorized sources responded. The OCTO1 view shows measured, stale, and unavailable states separately.":state.status==="authentication-required"?"Sign in through the existing Dashboard account session. No credentials are requested here.":state.status==="denied"?"The Dashboard denied this read. Existing access controls remain in force.":state.status==="unavailable"?`Dashboard telemetry is unavailable (${state.error||"source_error"}). No values are inferred.`:"Resource telemetry is not available in this context.");
    text("resource-dashboard-observed",state.observedAt?`Dashboard projection observed at ${visibleTime(state.observedAt)} · freshness ${state.freshness}.`:"No Dashboard observation has been received.");text("resource-worker-summary",state.dashboardStatus?workerSummary(state.dashboardStatus.workers):"Unavailable");text("resource-assignment-summary",state.dashboardStatus?assignmentSummary(state.dashboardStatus):"Unavailable");text("resource-cme-summary",state.dashboardStatus?safeState(state.dashboardStatus.cme?.status).replaceAll("_"," "):"Unavailable");text("resource-grace-summary",state.dashboardStatus?safeState(state.dashboardStatus.grace_execution?.status).replaceAll("_"," "):"Unavailable");text("resource-diagnostic-source",state.telemetry?"authenticated same-origin Dashboard telemetry API · read-only GET":"not connected");text("resource-diagnostic-freshness",state.freshness);text("resource-diagnostic-checked",visibleTime(state.checkedAt));text("resource-diagnostic-error",state.error||state.telemetryError||"none");renderOctoConsole();renderTelemetry();renderStorage();applyFilters();
  };
  const refreshData=async()=>{
    if(state.inFlight)return;if(location.protocol!=="https:"||!location.pathname.startsWith("/v2/")){state.status="unavailable";state.error="lan_https_preview_required";state.inFlight=false;render();return;}
    state.inFlight=true;state.attempted=true;state.checkedAt=new Date().toISOString();state.status="checking";state.error=null;state.telemetryError=null;render();
    try{
      const session=await fetchJson("/api/v1/auth/session");if(session.status!=="authenticated"){state.status="authentication-required";state.telemetryError="authentication_required";state.inFlight=false;render();return;}
      const traceReader=window.RiverviewGraceChat?.requestTraceSnapshot;
      const tracePromise=typeof traceReader==="function"?traceReader():Promise.resolve({schema_version:"rv.v2.grace-request-trace.v1",state:"not_connected",observed_at:null,requests:[]});
      const [statusResult,telemetryResult,traceResult]=await Promise.allSettled([fetchJson("/api/v1/status"),fetchJson("/api/v1/resources/telemetry"),tracePromise]);
      if(statusResult.status==="rejected")throw statusResult.reason;
      if(telemetryResult.status==="fulfilled"&&telemetryResult.value?.schema_version==="rv.dashboard.resource-telemetry.v1"){state.telemetry=telemetryResult.value;state.telemetryError=null;ingestMeasuredHardwareActivity(state.telemetry);}else state.telemetryError=telemetryResult.status==="rejected"?(telemetryResult.reason?.status?`http_${telemetryResult.reason.status}`:safeError(telemetryResult.reason?.message)):"invalid_telemetry_projection";
      state.requestTrace=traceResult.status==="fulfilled"&&traceResult.value?.schema_version==="rv.v2.grace-request-trace.v1"?traceResult.value:{schema_version:"rv.v2.grace-request-trace.v1",state:"unavailable",observed_at:null,requests:[]};ingestMeasuredRates(state.requestTrace);ingestLiveStreamRates(state.requestTrace);
      const payload=statusResult.value;if(!payload||payload.schema_version!=="rv.dashboard.status.v1"||!allowedStates.has(payload.projection_status))throw new Error("invalid_dashboard_status_schema");state.dashboardStatus=payload;state.observedAt=isoTime(payload.observed_at);state.freshness=["current","stale","unknown","unavailable"].includes(payload.freshness)?payload.freshness:"unknown";state.status=payload.projection_status==="unavailable"?"unavailable":"partial";if(payload.projection_status==="unavailable")state.error="dashboard_projection_unavailable";if(state.telemetry)snapshotSample();
    }catch(error){state.freshness=state.telemetry?"stale":"unavailable";state.status=error?.status===401?"authentication-required":error?.status===403?"denied":"unavailable";state.error=error?.status?`http_${error.status}`:safeError(error?.message);state.telemetryError=state.error;}
    state.inFlight=false;render();
  };
  const stopPolling=()=>{if(state.pollHandle!==null){window.clearInterval(state.pollHandle);state.pollHandle=null;}};
  const startPolling=()=>{stopPolling();if(!state.viewActive||document.visibilityState==="hidden")return;state.pollHandle=window.setInterval(()=>{if(state.viewActive&&document.visibilityState!=="hidden")refreshData();},POLL_MS);refreshData();};
  const selectComponent=(id)=>{if(id.startsWith("gpu-"))state.selected={kind:"gpu",id};else if(id.startsWith("model-"))state.selected={kind:"model",id:id.slice(6)};else state.selected={kind:"system",id};renderOctoConsole();};
  document.addEventListener("DOMContentLoaded",()=>{$("resource-refresh")?.addEventListener("click",refreshData);$("resource-filter")?.addEventListener("change",applyFilters);$("resource-search")?.addEventListener("input",applyFilters);$("octo1-activity-previous")?.addEventListener("click",()=>{state.activityPage=Math.max(0,state.activityPage-1);renderTimeline();});$("octo1-activity-next")?.addEventListener("click",()=>{const pages=Math.ceil(state.history.length/ACTIVITY_PAGE_SIZE);state.activityPage=Math.min(pages-1,state.activityPage+1);renderTimeline();});$("octo1-console")?.addEventListener("click",event=>{const viewButton=event.target.closest("[data-octo-artwork-view]");if(viewButton){setArtworkView(viewButton.dataset.octoArtworkView);return;}const button=event.target.closest("[data-octo-component]");if(button)selectComponent(button.dataset.octoComponent);});document.addEventListener("rvv2:view",event=>{const active=event.detail?.view==="resources";state.viewActive=active;$("workspace-main")?.classList.toggle("resources-selected",active);if(active)startPolling();else stopPolling();});document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="hidden")stopPolling();else if(state.viewActive)startPolling();});render();});
  window.RiverviewV2ResourceMonitor=Object.freeze({render,refresh:refreshData,snapshotDiagnostics:()=>({status:state.status,dashboard_projection:state.dashboardStatus?state.dashboardStatus.projection_status:"not_observed",freshness:state.freshness,observed_at:state.observedAt,checked_at:state.checkedAt,gpu_inventory:state.telemetry?.status||"unavailable",gpu_utilization:state.telemetry?"values_not_included_in_snapshot_diagnostics":"unavailable",vram:state.telemetry?"values_not_included_in_snapshot_diagnostics":"unavailable",gpu_thermals_power_fan:state.telemetry?"values_not_included_in_snapshot_diagnostics":"unavailable",loaded_models:state.telemetry?"projected":"unavailable",inference_server_readiness:state.telemetry?"projected":"unavailable",inference_jobs_and_queues:state.telemetry?"active_slot_occupancy_projected_queue_depth_unavailable":"unavailable",timeline_samples:state.history.length,hardware_activity_samples:state.hardwareHistory.length,request_trace:state.requestTrace?.state||"unavailable",live_stream_activity:state.requestTrace?.stream_activity_state||"unavailable",live_stream_rate_points:state.liveRateHistory.length,native_live_token_counter:"unavailable_from_current_model_server_api",request_attribution:"gpu_request_mapping_unavailable_from_model_server",trace_request_ids_in_snapshot:false,trace_message_bodies_in_snapshot:false,stream_text_in_snapshot:false,diagnostics_include_response_body:false,diagnostics_include_credentials:false})});
})();
