/* Riverview controlled asset | File: website/v2/assets/manual-image-generation.js
 * Component: V2-MANUAL-IMAGE-GENERATION | File Revision: 1.0.3
 * Purpose: Authenticated V2 operator image generation, preview and history
 * Authority: Same-origin Dashboard account session and CSRF-protected API only
 */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const root = $("manual-image-workspace");
  if (!root) return;
  const api = "/api/v1/manual-image-generations";
  let catalog = null;
  let session = null;
  let submitting = false;
  let currentRequestId = null;
  const escText = (value) => String(value ?? "");
  const csrf = () => {
    const match = document.cookie.match(/(?:^|;\s*)rv_account_csrf=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  };
  const jsonRequest = async (url, options = {}) => {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (options.method && options.method !== "GET") {
      headers.set("Content-Type", "application/json");
      headers.set("X-Riverview-CSRF", csrf());
    }
    const response = await fetch(url, {...options, headers, credentials: "same-origin", cache: "no-store"});
    let body = {};
    try { body = await response.json(); } catch (_) { /* Use a bounded status below. */ }
    if (!response.ok) {
      const error = new Error(body.error || `http_${response.status}`);
      error.status = response.status;
      throw error;
    }
    return body;
  };
  const message = (node, value, isError = false) => {
    node.textContent = value;
    node.dataset.state = isError ? "error" : "info";
  };
  const setBusy = (busy) => {
    submitting = busy;
    $("manual-image-generate").disabled = busy || !session || !catalog || catalog.worker?.status !== "ready";
    $("manual-image-workflow").disabled = busy || !catalog;
    $("manual-image-parameters").querySelectorAll("input,textarea,select").forEach((el) => { el.disabled = busy; });
  };
  const create = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const selectedWorkflow = () => catalog?.workflows.find((item) => item.workflow_id === $("manual-image-workflow").value);
  const buildParameters = (workflow) => {
    const host = $("manual-image-parameters");
    host.replaceChildren();
    if (!workflow) return;
    for (const binding of workflow.parameters || []) {
      const field = create("div", undefined, "manual-image-field");
      const id = `manual-param-${binding.name}`;
      const label = create("label", binding.name.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase()));
      label.htmlFor = id;
      let input;
      if (binding.type === "text" && binding.name === "prompt") {
        input = document.createElement("textarea");
        input.rows = 4;
        input.placeholder = "Describe the image you want to create";
        input.required = true;
      } else if (binding.type === "choice") {
        input = document.createElement("select");
        for (const choice of binding.choices || []) input.add(new Option(choice, choice));
      } else {
        input = document.createElement("input");
        input.type = "number";
        input.step = binding.type === "integer" ? "1" : "any";
        if (Number.isFinite(binding.min)) input.min = String(binding.min);
        if (Number.isFinite(binding.max)) input.max = String(binding.max);
        if (binding.type === "integer") input.step = "1";
      }
      input.id = id;
      input.dataset.parameter = binding.name;
      input.dataset.type = binding.type;
      if (binding.max_length) input.maxLength = binding.max_length;
      if (binding.default !== undefined && binding.type !== "text") input.value = String(binding.default);
      field.append(label, input);
      host.append(field);
    }
    if (workflow.fixed_resolution) {
      host.append(create("p", `Registered output size: ${workflow.fixed_resolution.width} × ${workflow.fixed_resolution.height} pixels`, "manual-image-note"));
    }
  };
  const renderCatalog = () => {
    const select = $("manual-image-workflow");
    select.replaceChildren();
    for (const workflow of catalog.workflows || []) {
      select.add(new Option(`${workflow.workflow_id} · ${workflow.revision}`, workflow.workflow_id));
    }
    if (!select.options.length) {
      select.add(new Option("No registered image workflow is available", ""));
      select.disabled = true;
      return;
    }
    select.disabled = false;
    buildParameters(selectedWorkflow());
    select.addEventListener("change", () => buildParameters(selectedWorkflow()));
    const gpuSelect = $("manual-image-gpu-select");
    const device = catalog.worker?.device;
    gpuSelect.replaceChildren(new Option(device?.name
      ? `Configured ComfyUI worker · ${device.name}`
      : "Configured ComfyUI worker · device identity unavailable", "configured-worker"));
    gpuSelect.disabled = true;
    message($("manual-image-gpu-status"), catalog.gpu_selection_reason || "GPU selection is not supported by this execution backend.");
  };
  const renderInventory = (telemetry) => {
    const host = $("manual-image-gpu-inventory");
    host.replaceChildren(create("h4", "GPU telemetry and reservations"));
    const devices = [];
    for (const machine of telemetry?.hosts || []) {
      for (const gpu of machine.gpu_inventory?.devices || []) devices.push({machine, gpu});
    }
    if (!devices.length) {
      host.append(create("p", "GPU inventory is unavailable. No GPU is selectable."));
      return;
    }
    const list = document.createElement("ul");
    for (const {machine, gpu} of devices) {
      const total = gpu.memory_total_bytes;
      const used = gpu.memory_used_bytes;
      const memory = Number.isFinite(total) && Number.isFinite(used)
        ? `${(used / 1073741824).toFixed(1)} / ${(total / 1073741824).toFixed(1)} GiB used`
        : "memory unavailable";
      const owners = Array.isArray(gpu.active_services) && gpu.active_services.length
        ? `owner: ${gpu.active_services.join(", ")}`
        : `reservation: ${gpu.reservation_state || "unknown"}`;
      const identity = gpu.gpu_uuid ? `UUID ${gpu.gpu_uuid}` : `UUID ${gpu.identity_state || "unavailable"}`;
      list.append(create("li", `${machine.display_name || machine.host_id} · ${gpu.name || gpu.device_id} · ${memory} · ${owners} · ${identity} · not selectable`));
    }
    host.append(list);
  };
  const renderResult = (record) => {
    const meta = $("manual-image-result-meta");
    const preview = $("manual-image-preview");
    meta.replaceChildren();
    if (record.status !== "complete" || !record.artifact) {
      preview.replaceChildren(create("p", record.error_code ? `Generation failed: ${record.error_code}` : `Request ${record.status}.`));
      return;
    }
    const artifact = record.artifact;
    const image = document.createElement("img");
    image.alt = `Generated output from ${record.workflow_id}`;
    image.src = `${artifact.download_url}?download=0`;
    image.addEventListener("error", () => {
      preview.replaceChildren(create("p", "The verified image could not be loaded. Use the authenticated Download PNG link or refresh history."));
    }, {once: true});
    preview.replaceChildren(image);
    const rows = [
      ["Workflow", record.workflow_id], ["Seed", record.parameters?.seed ?? "workflow default"],
      ["Execution time", `${record.elapsed_seconds ?? "Unavailable"} seconds`],
      ["Image", `${artifact.width} × ${artifact.height} PNG · ${artifact.size_bytes} bytes`],
      ["GPU", artifact.device?.name || record.worker?.device?.name || "Configured ComfyUI worker · identity unavailable"],
      ["GPU UUID", artifact.device?.gpu_uuid || "Unavailable from ComfyUI telemetry"],
      ["Verified output path", artifact.absolute_path], ["Host", artifact.host],
      ["SHA-256", artifact.sha256], ["Independent verification", record.verification?.decision || "Unavailable"],
      ["Provenance", "Operator manual · no Grace or Engineering work order"],
    ];
    for (const [label, value] of rows) {
      const row = create("p", undefined, "manual-image-meta-row");
      row.append(create("b", `${label}: `), create("span", escText(value)));
      meta.append(row);
    }
    const link = create("a", "Download PNG", "manual-image-download");
    link.href = `${artifact.download_url}?download=1`;
    link.setAttribute("download", `riverview-manual-${record.request_id}.png`);
    meta.append(link);
  };
  const renderHistory = (items) => {
    const host = $("manual-image-history-list");
    host.replaceChildren();
    if (!items?.length) { host.append(create("p", "No image requests have been recorded for this account.")); return; }
    const list = document.createElement("div");
    list.className = "manual-image-history-list";
    for (const record of items) {
      const card = create("article", undefined, "manual-image-history-item");
      const title = create("b", `${record.workflow_id} · ${record.status}`);
      const detail = create("p", `${record.created_at} · ${record.parameters?.seed !== undefined ? `seed ${record.parameters.seed} · ` : ""}${record.elapsed_seconds !== null ? `${record.elapsed_seconds}s` : "waiting"}`);
      card.append(title, detail);
      if (record.error_code) card.append(create("p", `Error: ${record.error_code}`));
      if (record.artifact) {
        const button = create("button", "View result");
        button.type = "button";
        button.addEventListener("click", () => { currentRequestId = record.request_id; renderResult(record); });
        card.append(button);
      }
      list.append(card);
    }
    host.append(list);
  };
  const loadHistory = async () => {
    const result = await jsonRequest(`${api}?limit=50`);
    renderHistory(result.items || []);
    const latest = result.items?.find((item) => item.request_id === currentRequestId) || result.items?.[0];
    if (latest) { currentRequestId = latest.request_id; renderResult(latest); }
  };
  const refreshCatalogAndHistory = async () => {
    if (!session) return;
    try {
      catalog = await jsonRequest(`${api}/catalog`);
      renderCatalog();
      try {
        const telemetry = await jsonRequest("/api/v1/resources/telemetry");
        renderInventory(telemetry);
      } catch (_) { renderInventory(null); }
      await loadHistory();
      message($("manual-image-auth-note"), `Signed in as ${session.identity.email}. Manual image mode is ready.`);
      setBusy(false);
      if (catalog.worker?.status !== "ready") {
        message($("manual-image-form-status"), "The configured ComfyUI worker is unavailable. Generation is disabled until its health check succeeds.", true);
      }
    } catch (error) {
      message($("manual-image-auth-note"), error.status === 401 || error.status === 403
        ? "An authenticated operator or Steward Dashboard session is required. Sign in through the Dashboard, then reopen V2."
        : `Could not load the registered image service (${error.message}).`, true);
    }
  };
  const collectParameters = () => {
    const result = {};
    for (const field of $("manual-image-parameters").querySelectorAll("[data-parameter]")) {
      if (field.dataset.type === "integer") {
        if (field.value === "" || !Number.isSafeInteger(Number(field.value))) throw new Error(`Enter a valid integer for ${field.dataset.parameter}.`);
        result[field.dataset.parameter] = Number(field.value);
      } else if (field.dataset.type === "number") {
        if (field.value === "" || !Number.isFinite(Number(field.value))) throw new Error(`Enter a valid number for ${field.dataset.parameter}.`);
        result[field.dataset.parameter] = Number(field.value);
      } else result[field.dataset.parameter] = field.value;
    }
    return result;
  };
  const waitForResult = async (requestId) => {
    const deadline = Date.now() + 15 * 60 * 1000;
    while (Date.now() < deadline) {
      const record = await jsonRequest(`${api}/${encodeURIComponent(requestId)}`);
      message($("manual-image-form-status"), `Request ${record.status}${record.progress?.outputs_saved ? ` · ${record.progress.outputs_saved} output saved` : ""}${record.elapsed_seconds ? ` · ${record.elapsed_seconds}s` : ""}`);
      if (["complete", "failed"].includes(record.status)) return record;
      await new Promise((resolve) => window.setTimeout(resolve, 800));
    }
    throw new Error("Generation is still running. Refresh history to resume status updates.");
  };
  $("manual-image-workflow").addEventListener("change", () => buildParameters(selectedWorkflow()));
  $("manual-image-refresh").addEventListener("click", async () => {
    try { await refreshCatalogAndHistory(); }
    catch (error) { message($("manual-image-form-status"), `Refresh failed: ${error.message}`, true); }
  });
  $("manual-image-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submitting || !session || !catalog) return;
    setBusy(true);
    const requestId = crypto.randomUUID();
    currentRequestId = requestId;
    try {
      const parameters = collectParameters();
      const workflowId = $("manual-image-workflow").value;
      message($("manual-image-form-status"), `Submitting ${workflowId}…`);
      await jsonRequest(api, {method: "POST", body: JSON.stringify({request_id: requestId,
        workflow_id: workflowId, parameters})});
      const record = await waitForResult(requestId);
      renderResult(record);
      await loadHistory();
      if (record.status === "failed") message($("manual-image-form-status"), `Generation failed: ${record.error_code || "unknown_error"}`, true);
      else message($("manual-image-form-status"), `Verified PNG ready · request ${requestId} · ${record.elapsed_seconds}s`);
    } catch (error) {
      message($("manual-image-form-status"), `Generation request ${requestId} was not confirmed: ${error.message}. Refresh history before retrying.`, true);
    } finally { setBusy(false); }
  });
  document.addEventListener("rvv2:view", (event) => {
    if (event.detail?.view === "image-generation") {
      $("overview-content").hidden = true;
      $("page-title").textContent = "Manual image generation";
      if (!session) void initialize();
    }
  });
  async function initialize() {
    try {
      session = await jsonRequest("/api/v1/auth/session");
      const roles = session.identity?.roles || [];
      if (!roles.includes("operator") && !roles.includes("steward")) throw new Error("manual_generation_not_authorized");
      await refreshCatalogAndHistory();
    } catch (error) {
      session = null;
      message($("manual-image-auth-note"), error.status === 401 || error.status === 403
        ? "Sign in through the existing Dashboard account session as an operator or Steward to use Manual Image Generation."
        : `Manual image service is unavailable: ${error.message}.`, true);
      $("manual-image-generate").disabled = true;
      $("manual-image-workflow").disabled = true;
    }
  }
  root.hidden = true;
  void initialize();
})();
