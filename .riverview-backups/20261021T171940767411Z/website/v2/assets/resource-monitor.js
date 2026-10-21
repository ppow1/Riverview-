/*
Riverview~ Controlled Source
File: website/v2/assets/resource-monitor.js
Component: RIVERVIEW-V2-HARDWARE-AI-RESOURCE-MONITOR
Revision: 1.0.0
Purpose: Present authenticated Dashboard operational summaries and explicit unavailable hardware/inference telemetry
Execution Model: Explicit request-driven browser GETs to the same-origin Dashboard status API; no polling
Observability: Source state, Dashboard observation time, freshness, and sanitized error category
Dependencies: Existing Dashboard account session and rv.dashboard.status.v1 projection
Inputs/Outputs: Redacted worker/assignment aggregates; GPU/model/queue metrics remain unavailable until an authorized projection exists
Authority: Existing account session read-only GETs only; no inference-host calls or control operations
Changed: 2026-10-21 UTC | RV-WEB-V2-HW-AI-RESOURCE-001 | Initial truthful V2 resource monitor
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: scripts/verify_v2_resource_monitor.cjs, tests/test_v2_workspace_shell.py
History: Git and revision/backup manifest
*/
(() => {
  "use strict";

  const state = {
    status: "not-checked",
    dashboardStatus: null,
    checkedAt: null,
    observedAt: null,
    freshness: "unknown",
    error: null,
    attempted: false,
    inFlight: false
  };
  const allowedStates = new Set(["healthy", "degraded", "stale", "unknown", "unverified", "unavailable", "not_initialized", "inactive"]);
  const $ = (id) => document.getElementById(id);
  const safeState = (value) => allowedStates.has(value) ? value : "unknown";
  const safeError = (value) => /^[a-z0-9_.-]{1,48}$/i.test(String(value || "")) ? String(value) : "source_error";
  const safeCount = (value) => Number.isSafeInteger(value) && value >= 0 && value <= 1000000000 ? value : null;
  const isoTime = (value) => {
    if (typeof value !== "string") return null;
    const time = Date.parse(value);
    return Number.isFinite(time) ? new Date(time).toISOString() : null;
  };
  const visibleTime = (value) => {
    const time = isoTime(value);
    return time ? `${time} · UTC` : "Not reported";
  };
  const text = (id, value) => { const node = $(id); if (node) node.textContent = String(value); };
  const tag = (id, value) => {
    const node = $(id);
    if (!node) return;
    node.textContent = value.toUpperCase().replaceAll("_", " ");
    node.dataset.state = value;
  };
  const fetchJson = async (path) => {
    const response = await fetch(path, {
      method: "GET", headers: {Accept: "application/json"},
      credentials: "same-origin", cache: "no-store", redirect: "error"
    });
    if (!response.ok) {
      const error = new Error(`http_${response.status}`);
      error.status = response.status;
      throw error;
    }
    return response.json();
  };
  const workerSummary = (workers) => {
    if (!workers || !["healthy", "degraded", "stale", "unknown", "unverified", "unavailable", "not_initialized"].includes(workers.status)) return "Unavailable";
    const active = safeCount(workers.active_workers);
    const healthy = safeCount(workers.healthy_workers);
    const stale = safeCount(workers.stale_workers);
    const unknown = safeCount(workers.unknown_workers);
    if ([active, healthy, stale, unknown].some((value) => value === null)) return workers.status.replaceAll("_", " ");
    return `${active} active · ${healthy} healthy · ${stale} stale · ${unknown} unknown`;
  };
  const assignmentSummary = (payload) => {
    if (!payload || payload.projection_status !== "healthy" || !payload.assignment_counts || typeof payload.assignment_counts !== "object") return "Unavailable";
    const total = safeCount(payload.assignments_total);
    const entries = Object.entries(payload.assignment_counts)
      .filter(([key, value]) => /^[a-z][a-z0-9_-]{0,31}$/i.test(key) && safeCount(value) !== null)
      .slice(0, 8);
    if (total === null) return "Unavailable";
    if (entries.length === 0) return `${total} recorded · no state breakdown reported`;
    return `${total} recorded · ${entries.map(([key, value]) => `${key}: ${value}`).join(" · ")}`;
  };
  const render = () => {
    const stateLabels = {
      "not-checked": "NOT CHECKED", checking: "CHECKING", partial: "PARTIAL",
      "authentication-required": "SIGN-IN REQUIRED", unavailable: "UNAVAILABLE",
      denied: "ACCESS DENIED"
    };
    tag("resource-source-state", state.status);
    text("resource-source-state", stateLabels[state.status] || state.status.toUpperCase());
    const root = $("resource-monitor-workspace");
    if (root) root.dataset.state = state.status;
    const refreshButton = $("resource-refresh");
    if (refreshButton) refreshButton.disabled = state.inFlight;
    const sourceTag = $("resource-dashboard-state");
    if (sourceTag) {
      const projection = state.dashboardStatus?.projection_status;
      const label = projection === "healthy" ? "AVAILABLE" : projection === "not_initialized" ? "NOT INITIALIZED" : projection === "unavailable" ? "UNAVAILABLE" : state.status === "checking" ? "CHECKING" : state.status === "authentication-required" ? "SIGN-IN REQUIRED" : state.status === "denied" ? "ACCESS DENIED" : "NOT CHECKED";
      sourceTag.textContent = label;
      sourceTag.dataset.state = projection || state.status;
    }
    text("resource-refresh-status", state.status === "not-checked"
      ? "Use Refresh to check the existing authenticated Dashboard status projection. GPU and inference telemetry are not connected to V2."
      : state.status === "checking" ? "Checking the existing read-only Dashboard projection…"
        : state.status === "partial" ? "Dashboard work-fleet status was read. Hardware and inference telemetry remain unavailable."
          : state.status === "authentication-required" ? "Sign in through the existing Dashboard account session to read work-fleet status. No credentials are requested here."
            : state.status === "denied" ? "The Dashboard denied this read. Existing access controls remain in force."
              : state.status === "unavailable" ? `Dashboard telemetry is unavailable (${state.error || "source_error"}). No values are inferred.`
                : "Protected LAN HTTPS Dashboard telemetry is not used by the local fixture preview.");
    text("resource-dashboard-observed", state.observedAt
      ? `Dashboard projection observed at ${visibleTime(state.observedAt)} · freshness ${state.freshness}. This timestamp applies only to the Dashboard projection.`
      : "No Dashboard observation has been received.");
    text("resource-worker-summary", state.dashboardStatus ? workerSummary(state.dashboardStatus.workers) : "Unavailable");
    text("resource-assignment-summary", state.dashboardStatus ? assignmentSummary(state.dashboardStatus) : "Unavailable");
    text("resource-cme-summary", state.dashboardStatus ? safeState(state.dashboardStatus.cme?.status).replaceAll("_", " ") : "Unavailable");
    text("resource-grace-summary", state.dashboardStatus ? safeState(state.dashboardStatus.grace_execution?.status).replaceAll("_", " ") : "Unavailable");
    text("resource-diagnostic-source", state.dashboardStatus ? "same-origin Dashboard status API · read-only GET" : "not connected");
    text("resource-diagnostic-freshness", state.freshness);
    text("resource-diagnostic-checked", visibleTime(state.checkedAt));
    text("resource-diagnostic-error", state.error || "none");
    applyFilters();
  };
  const applyFilters = () => {
    const filter = $("resource-filter")?.value || "all";
    const search = ($("resource-search")?.value || "").trim().toLowerCase();
    document.querySelectorAll("[data-resource-card]").forEach((card) => {
      const kindMatch = filter === "all" || card.dataset.resourceKind === filter;
      const textMatch = !search || `${card.dataset.search || ""} ${card.textContent || ""}`.toLowerCase().includes(search);
      card.hidden = !(kindMatch && textMatch);
    });
  };
  const refresh = async () => {
    if (state.inFlight) return;
    state.inFlight = true;
    state.attempted = true;
    state.checkedAt = new Date().toISOString();
    state.status = "checking";
    state.dashboardStatus = null;
    state.observedAt = null;
    state.freshness = "unknown";
    state.error = null;
    render();
    if (location.protocol !== "https:" || !location.pathname.startsWith("/v2/")) {
      state.status = "unavailable";
      state.error = "lan_https_preview_required";
      state.inFlight = false;
      render();
      return;
    }
    try {
      const session = await fetchJson("/api/v1/auth/session");
      if (session.status !== "authenticated") {
        state.status = "authentication-required";
        render();
        return;
      }
      const payload = await fetchJson("/api/v1/status");
      if (!payload || payload.schema_version !== "rv.dashboard.status.v1" || !allowedStates.has(payload.projection_status)) {
        throw new Error("invalid_dashboard_status_schema");
      }
      state.dashboardStatus = payload;
      state.observedAt = isoTime(payload.observed_at);
      state.freshness = ["current", "stale", "unknown", "unavailable"].includes(payload.freshness) ? payload.freshness : "unknown";
      state.status = payload.projection_status === "unavailable" ? "unavailable" : "partial";
      if (payload.projection_status === "unavailable") state.error = "dashboard_projection_unavailable";
    } catch (error) {
      state.dashboardStatus = null;
      state.observedAt = null;
      state.freshness = "unavailable";
      state.status = error?.status === 401 ? "authentication-required" : error?.status === 403 ? "denied" : "unavailable";
      state.error = error?.status ? `http_${error.status}` : safeError(error?.message);
    }
    state.inFlight = false;
    render();
  };

  document.addEventListener("DOMContentLoaded", () => {
    $("resource-refresh")?.addEventListener("click", refresh);
    $("resource-filter")?.addEventListener("change", applyFilters);
    $("resource-search")?.addEventListener("input", applyFilters);
    document.addEventListener("rvv2:view", (event) => {
      if (event.detail?.view === "resources" && !state.attempted) refresh();
    });
    render();
  });

  window.RiverviewV2ResourceMonitor = Object.freeze({
    render,
    refresh,
    snapshotDiagnostics: () => ({
      status: state.status,
      dashboard_projection: state.dashboardStatus ? state.dashboardStatus.projection_status : "not_observed",
      freshness: state.freshness,
      observed_at: state.observedAt,
      checked_at: state.checkedAt,
      gpu_inventory: "unavailable",
      gpu_utilization: "unavailable",
      vram: "unavailable",
      gpu_thermals_power_fan: "unavailable",
      loaded_models: "unavailable_in_v2",
      inference_server_readiness: "unavailable_in_v2",
      inference_jobs_and_queues: "unavailable",
      diagnostics_include_response_body: false,
      diagnostics_include_credentials: false
    })
  });
})();
