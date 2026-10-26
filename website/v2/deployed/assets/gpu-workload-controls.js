/* Authenticated UI for the fixed OCTOMINER1 vision/ComfyUI controller. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const ROOT = "/api/v1/hardware/workloads";
  const state = { active: false, busy: false, interval: null, pollTimer: null, job: null, permissions: null };
  const safe = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const csrf = () => {
    const value = document.cookie.split(";").map(x => x.trim()).find(x => x.startsWith("rv_account_csrf="));
    return value ? decodeURIComponent(value.slice("rv_account_csrf=".length)) : "";
  };
  const request = async (path, options = {}) => {
    const headers = {Accept:"application/json", ...(options.headers || {})};
    if (options.method && options.method !== "GET") {
      const token = csrf();
      if (!token) throw Object.assign(new Error("csrf_token_missing"), {status:403});
      headers["X-Riverview-CSRF"] = token;
    }
    const response = await fetch(path, {...options, headers, credentials:"same-origin", cache:"no-store"});
    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (!response.ok) throw Object.assign(new Error(body.error || `http_${response.status}`), {status:response.status, code:body.error});
    return body;
  };
  const message = (text, error = false) => {
    const node = $("gpu-workload-state");
    if (node) { node.textContent = text; node.dataset.state = error ? "error" : "normal"; }
  };
  const serviceText = (service, queue) => {
    if (!service || typeof service.active !== "boolean") return "Unavailable";
    const work = queue?.state === "available"
      ? Number.isSafeInteger(queue.running) ? ` · ${queue.running} running / ${queue.pending} queued`
        : ` · ${queue.active_requests} active request(s)`
      : queue?.state === "inactive" ? " · no active requests" : " · activity unavailable";
    const readiness = queue?.readiness === "ready" ? " · ready" : service.active ? " · readiness unavailable" : "";
    return `${service.active ? "Active" : "Inactive"} · ${service.sub_state || service.active_state || "state unknown"}${work}${readiness}`;
  };
  const render = (data) => {
    if (data.services) {
      $("gpu-workload-vision").textContent = serviceText(data.services.vision, data.queues?.vision);
      $("gpu-workload-comfyui").textContent = serviceText(data.services.comfyui, data.queues?.comfyui);
    }
    const gpu = data.gpu;
    $("gpu-workload-vram").textContent = gpu?.state === "available" && Number.isSafeInteger(gpu.used_mib) && Number.isSafeInteger(gpu.total_mib)
      ? `${(gpu.used_mib/1024).toFixed(1)} / ${(gpu.total_mib/1024).toFixed(1)} GiB used · ${(Math.max(0,gpu.total_mib-gpu.used_mib)/1024).toFixed(1)} GiB free`
      : "Unavailable · target RTX 4090 not verified";
    $("gpu-workload-observed").textContent = data.observed_at ? new Date(data.observed_at).toLocaleString() : "Not observed";
    state.permissions = data.permissions || state.permissions;
    document.querySelectorAll("[data-gpu-action]").forEach(button => {
      const action = button.dataset.gpuAction;
      button.disabled = state.busy || !state.permissions?.[action];
      if (!state.permissions?.[action]) button.title = `Requires exact hardware.gpu.workload.${action} grant at host:octominer1`;
    });
  };
  const explain = (error) => {
    if (error.status === 401) return "Sign in with the Steward account to inspect workload controls.";
    if (error.status === 403) return "Steward session or exact host:octominer1 capability grant is required; no operation was started.";
    if (error.code === "active_requests_or_jobs") return "Refused: the service has active inference requests or queued/running ComfyUI jobs.";
    if (error.code === "unrelated_gpu_process_active") return "Refused: another GPU process is using the shared RTX 4090.";
    if (error.code === "target_gpu_memory_not_released_or_unrelated_process_active") return "Refused: RTX 4090 memory was not released; the target service was not started.";
    return `Workload control unavailable (${safe(error.code || error.message || "unknown_error")}).`;
  };
  const refresh = async () => {
    if (!state.active || document.visibilityState === "hidden" || state.busy) return;
    try {
      const data = await request(ROOT);
      render(data);
      if (data.active_job?.job_id && !state.job) {
        state.job = data.active_job.job_id;
        await pollJob(state.job);
      } else message("Service-manager state and queue observations are current.");
    }
    catch (error) { message(explain(error), true); }
  };
  const pollJob = async (jobId) => {
    state.busy = true;
    const poll = async () => {
      if (!state.active || document.visibilityState === "hidden") { state.busy = false; state.job = jobId; return; }
      try {
        const job = await request(`${ROOT}/jobs/${encodeURIComponent(jobId)}`);
        message(`${String(job.state || "unknown").replaceAll("_", " ")}${job.error_code ? ` · ${job.error_code}` : ""}`,
          ["failed"].includes(job.state));
        if (["succeeded", "failed"].includes(job.state)) {
          state.busy = false; state.job = null; await refresh(); return;
        }
      } catch (error) { message(explain(error), true); state.busy = false; state.job = jobId; return; }
      state.pollTimer = window.setTimeout(poll, 1500);
    };
    await poll();
  };
  const submit = async (button) => {
    const action = button.dataset.gpuAction, service = button.dataset.gpuService;
    const verb = action === "switch" ? `Switch to ${service === "vision" ? "vision" : "ComfyUI"}` : `${action} ${service === "vision" ? "30B vision" : "ComfyUI"}`;
    if (!confirm(`${verb}? The controller checks active requests/jobs, refuses unrelated GPU use, verifies memory release, and confirms readiness. This can make the other service unavailable.`)) return;
    state.busy = true; document.querySelectorAll("[data-gpu-action]").forEach(item => { item.disabled = true; });
    message(`Submitting authorized ${verb.toLowerCase()} operation…`);
    try {
      const response = await request(`${ROOT}/${action}`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({service})});
      state.job = response.job_id; message("Operation accepted · checking progress…"); await pollJob(response.job_id);
    } catch (error) { state.busy = false; message(explain(error), true); await refresh(); }
  };
  const start = () => {
    if (!state.active || document.visibilityState === "hidden") return;
    if (state.job) pollJob(state.job); else refresh();
    if (state.interval) window.clearInterval(state.interval);
    state.interval = window.setInterval(() => { if (!state.busy) refresh(); }, 5000);
  };
  const stop = () => {
    if (state.interval) { window.clearInterval(state.interval); state.interval = null; }
    if (state.pollTimer) { window.clearTimeout(state.pollTimer); state.pollTimer = null; }
  };
  document.addEventListener("rvv2:view", event => {
    state.active = event.detail?.view === "resources";
    if (state.active) start(); else stop();
  });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") stop(); else if (state.active) start(); });
  document.addEventListener("DOMContentLoaded", () => {
    $("gpu-workload-refresh")?.addEventListener("click", refresh);
    $("gpu-workload-controls")?.addEventListener("click", event => {
      const button = event.target.closest("[data-gpu-action]");
      if (button && !button.disabled) submit(button);
    });
    state.active = document.querySelector("#workspace-main")?.dataset.currentView === "resources";
    if (state.active) start();
  });
})();
