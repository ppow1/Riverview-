/* Dynamic host-scoped controls over the registered hardware controller API. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const ROOT = "/api/v1/hardware/workloads";
  const state = {active:false,busy:false,interval:null,pollTimer:null,job:null,hosts:[],selected:null};
  const safe = (value) => String(value ?? "").replace(/[&<>\"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const csrf = () => {
    const value = document.cookie.split(";").map(x => x.trim()).find(x => x.startsWith("rv_account_csrf="));
    return value ? decodeURIComponent(value.slice("rv_account_csrf=".length)) : "";
  };
  const request = async (path, options = {}) => {
    const headers = {Accept:"application/json",...(options.headers || {})};
    if (options.method && options.method !== "GET") {
      const token = csrf();
      if (!token) throw Object.assign(new Error("csrf_token_missing"),{status:403});
      headers["X-Riverview-CSRF"] = token;
    }
    const response = await fetch(path,{...options,headers,credentials:"same-origin",cache:"no-store"});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw Object.assign(new Error(body.error || `http_${response.status}`),{status:response.status,code:body.error});
    return body;
  };
  const message = (text,error=false) => {
    const node = $("gpu-workload-state");
    if (node) {node.textContent=text;node.dataset.state=error?"error":"normal";}
  };
  const explain = (error) => {
    if (error.status===401) return "Sign in with an authenticated Steward account to inspect workload controls.";
    if (error.status===403) return "The exact operation grant is missing for this host. Submit a permission request in Settings → Permissions; no operation was started.";
    if (error.code==="active_requests_or_jobs") return "Refused: the service has active inference requests or queued/running jobs.";
    if (error.code==="unrelated_gpu_process_active") return "Refused: another process is using a GPU resource on this host.";
    if (error.code==="target_gpu_memory_not_released_or_unrelated_process_active") return "Refused: GPU memory was not released; the requested workload was not started.";
    if (error.code==="gpu_host_identity_unverified") return "This host is documented but its live identity has not been verified.";
    if (error.code==="gpu_controller_not_registered") return "No workload controller is registered for this host.";
    return `Workload control unavailable (${safe(error.code || error.message || "unknown_error")}).`;
  };
  const serviceText = (service, queue) => {
    if (!service || typeof service.active!=="boolean") return "Unavailable";
    const work = queue?.state==="available"
      ? Number.isSafeInteger(queue.running) ? ` · ${queue.running} running / ${queue.pending} queued` : ` · ${queue.active_requests} active request(s)`
      : queue?.state==="inactive" ? " · no active requests" : " · activity unavailable";
    const ready = queue?.readiness==="ready" ? " · ready" : service.active ? " · readiness unavailable" : "";
    return `${service.active?"Active":"Inactive"} · ${service.sub_state || service.active_state || "state unknown"}${work}${ready}`;
  };
  const selectedHost = () => state.hosts.find(host => host.host_id===state.selected) || null;
  const renderHostOptions = () => {
    const select = $("gpu-workload-host");
    if (!select) return;
    const previous = state.selected;
    select.innerHTML = state.hosts.map(host => {
      const usable = host.controller_state==="registered" && host.identity_state==="verified";
      const status = usable ? "registered" : host.controller_state==="unverified_host" ? "identity unverified" : "controller not registered";
      return `<option value="${safe(host.host_id)}" ${usable?"":"disabled"}>${safe(host.display_name || host.host_id)} · ${status}</option>`;
    }).join("");
    const first = state.hosts.find(host => host.controller_state==="registered" && host.identity_state==="verified");
    state.selected = state.hosts.some(host=>host.host_id===previous && host.controller_state==="registered") ? previous : first?.host_id || null;
    if (state.selected) select.value=state.selected;
    select.disabled=!state.selected;
  };
  const render = () => {
    renderHostOptions();
    const host=selectedHost(),facts=$("gpu-workload-facts"),actions=$("gpu-workload-actions");
    if (!host) {
      facts.innerHTML=state.hosts.map(item=>`<span>${safe(item.display_name || item.host_id)}<b>${safe(item.identity_state)} · ${safe(item.controller_state)}</b></span>`).join("") || "<span>No registered hosts<b>Unavailable</b></span>";
      actions.innerHTML=""; return;
    }
    const services=host.services || {}, queues=host.queues || {}, gpu=host.gpu;
    const gpuText=gpu?.state==="available" && Number.isSafeInteger(gpu.used_mib) && Number.isSafeInteger(gpu.total_mib)
      ? `${safe(gpu.name || "GPU")} · ${Number.isFinite(gpu.utilization_percent)?`${gpu.utilization_percent}% busy · `:""}${(gpu.used_mib/1024).toFixed(1)} / ${(gpu.total_mib/1024).toFixed(1)} GiB used · ${(Math.max(0,gpu.total_mib-gpu.used_mib)/1024).toFixed(1)} GiB free`
      : "Unavailable";
    const serviceCatalog=host.service_catalog || [];
    facts.innerHTML=serviceCatalog.map(meta=>`<span>${safe(meta.display_name || meta.service_id)}<b>${safe(serviceText(services[meta.controller_service],queues[meta.controller_service]))}</b></span>`).join("")+
      `<span>GPU allocation and memory<b>${gpuText}</b></span><span>Controller job<b>${safe(host.active_job?.state ? `${host.active_job.operation || "operation"} · ${host.active_job.state}` : "No active controller job")}</b></span><span>Observed<b>${safe(host.observed_at ? new Date(host.observed_at).toLocaleString() : "Not observed")}</b></span>`;
    actions.innerHTML=serviceCatalog.map(meta=>{
      const service=meta.service_id, label=meta.display_name || service;
      return `<section><h6>${safe(label)}</h6>${[["start","Start"],["stop","Stop"],["switch",`Switch to ${label}`]].map(([action,text])=>`<button type="button" data-gpu-action="${action}" data-gpu-service="${safe(service)}" ${state.busy || !host.permissions?.[action]?"disabled":""} title="${host.permissions?.[action]?"":`Requires exact hardware.gpu.workload.${action} grant at host:${safe(host.host_id)}`}">${safe(text)}</button>`).join("")}</section>`;
    }).join("");
  };
  const refresh = async () => {
    if (!state.active || document.visibilityState==="hidden" || state.busy) return;
    try {
      const data=await request(ROOT);
      state.hosts=Array.isArray(data.hosts)?data.hosts:[];
      render();
      const host=selectedHost();
      if (host?.active_job?.job_id && !state.job) {state.job={id:host.active_job.job_id,host_id:host.host_id};await pollJob(state.job);}
      else message(`Read ${state.hosts.length} host record(s) from the registered hardware projection. Actions remain host-scoped.`);
    } catch(error) {message(explain(error),true);}
  };
  const pollJob=async job=>{
    state.busy=true;render();
    const poll=async()=>{
      if (!state.active || document.visibilityState==="hidden"){state.busy=false;state.job=job;render();return;}
      try {
        const value=await request(`${ROOT}/jobs/${encodeURIComponent(job.id)}?host_id=${encodeURIComponent(job.host_id)}`);
        message(`${safe(job.host_id)} · ${String(value.state || "unknown").replaceAll("_"," ")}${value.error_code?` · ${safe(value.error_code)}`:""}`,value.state==="failed");
        if (["succeeded","failed"].includes(value.state)){state.busy=false;state.job=null;await refresh();return;}
      } catch(error){message(explain(error),true);state.busy=false;state.job=job;render();return;}
      state.pollTimer=window.setTimeout(poll,1500);
    };
    await poll();
  };
  const submit=async button=>{
    const host=selectedHost(); if(!host)return;
    const action=button.dataset.gpuAction,service=button.dataset.gpuService;
    const meta=(host.service_catalog||[]).find(item=>item.service_id===service);
    const verb=action==="switch"?`Switch ${host.display_name} to ${meta?.display_name || service}`:`${action} ${meta?.display_name || service} on ${host.display_name}`;
    if(!confirm(`${verb}? The registered controller checks active requests/jobs, host-local GPU conflicts, memory release, and readiness.`))return;
    state.busy=true;render();message(`Submitting ${verb.toLowerCase()}…`);
    try {
      const value=await request(`${ROOT}/${action}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({host_id:host.host_id,service})});
      state.job={id:value.job_id,host_id:value.host_id};message("Operation accepted · checking host-local progress…");await pollJob(state.job);
    }catch(error){state.busy=false;message(explain(error),true);await refresh();}
  };
  const start=()=>{
    if(!state.active || document.visibilityState==="hidden")return;
    if(state.job)pollJob(state.job);else refresh();
    if(state.interval)window.clearInterval(state.interval);
    state.interval=window.setInterval(()=>{if(!state.busy)refresh();},5000);
  };
  const stop=()=>{
    if(state.interval){window.clearInterval(state.interval);state.interval=null;}
    if(state.pollTimer){window.clearTimeout(state.pollTimer);state.pollTimer=null;}
  };
  document.addEventListener("rvv2:view",event=>{state.active=event.detail?.view==="resources";if(state.active)start();else stop();});
  document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="hidden")stop();else if(state.active)start();});
  document.addEventListener("DOMContentLoaded",()=>{
    $("gpu-workload-refresh")?.addEventListener("click",refresh);
    $("gpu-workload-host")?.addEventListener("change",event=>{state.selected=event.target.value;render();});
    $("gpu-workload-actions")?.addEventListener("click",event=>{const button=event.target.closest("[data-gpu-action]");if(button&&!button.disabled)submit(button);});
    state.active=document.querySelector("#workspace-main")?.dataset.currentView==="resources";
    if(state.active)start();
  });
})();
