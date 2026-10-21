/*
Riverview~ Controlled Source
File: website/v2/assets/work-monitor.js
Component: RIVERVIEW-V2-WORK-EXECUTION-MONITOR
Revision: 1.0.0
Purpose: Present bounded objective and assignment state from existing Dashboard projections
Execution Model: Request-driven same-origin browser reads; no background polling
Observability: Visible authorization, source status, fetched-at time, and persisted record timestamps
Dependencies: Authenticated rv.dashboard.status.v1 service; rv.dashboard.objectives.v1; assignment projection
Inputs/Outputs: Read-only GET summaries; does not display request bodies, criteria, artifacts, or event payloads
Authority: Dashboard account authentication and server projection filters; no mutation or execution controls
Changed: 2026-10-21 UTC | RV-V2-CAPABILITY-INTEGRATION-P1 | Initial read-only work status integration
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md; docs/components/STATUS_DASHBOARD.md
Tests: scripts/verify_v2_work_monitor.cjs; tests/test_v2_workspace_shell.py
History: Git and .riverview-backups/manifest.jsonl
*/
(() => {
  "use strict";

  const state = {
    status: "not_checked",
    objectivesStatus: "not_observed",
    assignmentsStatus: "not_observed",
    objectives: [],
    assignments: [],
    truncated: {objectives: false, assignments: false},
    fetchedAt: null,
    inFlight: false
  };
  const $ = (id) => document.getElementById(id);
  const safeCode = (value) => String(value || "request_failed").replace(/[^a-z0-9_.-]/gi, "_").slice(0, 64);
  const secureV2Route = () => location.protocol === "https:" && location.pathname.startsWith("/v2/");

  async function getJson(path) {
    const response = await fetch(path, {
      method: "GET",
      headers: {Accept: "application/json"},
      credentials: "same-origin",
      cache: "no-store"
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(safeCode(body.error || `http_${response.status}`));
      error.status = response.status;
      throw error;
    }
    return body;
  }

  function setStatus(status, label, detail) {
    state.status = status;
    const root = $("work-monitor-workspace");
    if (root) root.dataset.state = status;
    const badge = $("work-source-state");
    if (badge) {
      badge.dataset.state = status;
      badge.textContent = label;
    }
    const message = $("work-refresh-status");
    if (message) message.textContent = detail;
  }

  function recordTime(value) {
    if (!value) return "Not recorded";
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? "Timestamp unavailable" : date.toLocaleString();
  }

  function matchesFilter(item, query, kind) {
    if (!query) return true;
    const fields = kind === "objective"
      ? [item.objective_id, item.status, item.assignment_id, item.assignment_state, item.verification?.decision]
      : [item.assignment_id, item.state, item.owner, item.workflow_id, item.workflow_step,
        item.last_meaningful_progress?.event_type];
    return fields.some((value) => String(value || "").toLowerCase().includes(query));
  }

  function cell(row, value, className = "") {
    const node = document.createElement("td");
    node.textContent = value == null || value === "" ? "Unavailable" : String(value);
    if (className) node.className = className;
    row.append(node);
  }

  function renderRows() {
    const query = String($("work-search")?.value || "").trim().toLowerCase();
    const objectiveBody = $("work-objectives-body");
    const assignmentBody = $("work-assignments-body");
    if (!objectiveBody || !assignmentBody) return;
    objectiveBody.replaceChildren();
    assignmentBody.replaceChildren();
    const visibleObjectives = state.objectives.filter((item) => matchesFilter(item, query, "objective"));
    const visibleAssignments = state.assignments.filter((item) => matchesFilter(item, query, "assignment"));

    for (const item of visibleObjectives) {
      const row = document.createElement("tr");
      cell(row, item.objective_id);
      cell(row, item.status);
      cell(row, item.assignment_id ? `${item.assignment_id} · ${item.assignment_state || "state unavailable"}` : "No linked assignment");
      cell(row, item.verification?.decision || "Not verified");
      cell(row, recordTime(item.updated_at));
      objectiveBody.append(row);
    }
    for (const item of visibleAssignments) {
      const row = document.createElement("tr");
      cell(row, item.assignment_id);
      cell(row, item.state);
      cell(row, [item.owner, item.workflow_step || item.workflow_id].filter(Boolean).join(" · "));
      const progress = item.last_meaningful_progress || {};
      cell(row, progress.event_type ? `${progress.event_type} · ${recordTime(progress.recorded_at)}` : "No progress event recorded");
      assignmentBody.append(row);
    }

    const objectiveEmpty = $("work-objectives-empty");
    const assignmentEmpty = $("work-assignments-empty");
    if (objectiveEmpty) objectiveEmpty.textContent = state.objectivesStatus === "available"
      ? (visibleObjectives.length ? "" : query ? "No objectives match this filter." : "The authoritative objective projection returned no records.")
      : `Objective source: ${state.objectivesStatus}.`;
    if (assignmentEmpty) assignmentEmpty.textContent = state.assignmentsStatus === "available"
      ? (visibleAssignments.length ? "" : query ? "No assignments match this filter." : "The authoritative assignment projection returned no records.")
      : `Assignment source: ${state.assignmentsStatus}.`;
    if (objectiveEmpty) objectiveEmpty.hidden = state.objectivesStatus === "available" && visibleObjectives.length > 0;
    if (assignmentEmpty) assignmentEmpty.hidden = state.assignmentsStatus === "available" && visibleAssignments.length > 0;
  }

  function render() {
    renderRows();
  }

  async function refresh() {
    if (state.inFlight) return;
    if (!secureV2Route()) {
      state.objectives = [];
      state.assignments = [];
      state.objectivesStatus = "secure_lan_v2_required";
      state.assignmentsStatus = "secure_lan_v2_required";
      state.fetchedAt = null;
      setStatus("unavailable", "HTTPS REQUIRED", "Live institutional records are available only from the authenticated LAN HTTPS /v2/ route. No request was sent.");
      renderRows();
      return;
    }
    state.inFlight = true;
    setStatus("loading", "CHECKING", "Checking the existing Dashboard session before requesting any operational records…");
    try {
      await getJson("/api/v1/auth/session");
    } catch (error) {
      state.objectives = [];
      state.assignments = [];
      state.objectivesStatus = error.status === 401 ? "authentication_required" : safeCode(error.message);
      state.assignmentsStatus = state.objectivesStatus;
      state.fetchedAt = new Date().toISOString();
      const auth = error.status === 401 || error.status === 403;
      setStatus(auth ? "authentication_required" : "unavailable",
        auth ? "SIGN IN REQUIRED" : "SOURCE UNAVAILABLE",
        auth ? "Sign in through Talk with Grace, then return to Work. No operational records were requested." : `Dashboard session check failed (${safeCode(error.message)}).`);
      state.inFlight = false;
      renderRows();
      return;
    }

    const [objectivesResult, assignmentsResult] = await Promise.allSettled([
      getJson("/api/v1/objectives?limit=25"),
      getJson("/api/v1/assignments?limit=25")
    ]);
    state.fetchedAt = new Date().toISOString();
    const failures = [];
    const apply = (result, target, statusKey, label) => {
      if (result.status === "rejected") {
        state[statusKey] = result.reason?.status === 401 ? "authentication_required" : "unavailable";
        state[target] = [];
        failures.push(`${label}: ${safeCode(result.reason?.message)}`);
        return;
      }
      const body = result.value;
      state[statusKey] = body.status === "available" && Array.isArray(body.items)
        ? "available" : body.status === "not_initialized" ? "not_initialized" : "unavailable";
      state[target] = state[statusKey] === "available" ? body.items.slice(0, 25) : [];
      state.truncated[target] = Boolean(body.truncated || body.next_cursor);
      if (state[statusKey] === "unavailable") failures.push(`${label}: unexpected source status`);
    };
    apply(objectivesResult, "objectives", "objectivesStatus", "Objectives");
    apply(assignmentsResult, "assignments", "assignmentsStatus", "Assignments");
    const ready = [state.objectivesStatus, state.assignmentsStatus].filter((status) => status === "available").length;
    const notReady = [state.objectivesStatus, state.assignmentsStatus].some((status) => status !== "available");
    const label = ready === 2 ? "CURRENT" : ready === 1 ? "PARTIAL" : "UNAVAILABLE";
    const status = ready === 2 ? "available" : ready === 1 ? "partial" : "unavailable";
    const freshness = `Read at ${state.fetchedAt}; timestamps in rows are persisted source times.`;
    const detail = failures.length ? `${freshness} ${failures.join(" · ")}` : freshness;
    setStatus(status, label, detail);
    state.inFlight = false;
    renderRows();
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("work-refresh")?.addEventListener("click", refresh);
    $("work-search")?.addEventListener("input", renderRows);
    document.addEventListener("rvv2:view", (event) => {
      if (event.detail?.view === "work") refresh();
    });
    renderRows();
  });

  window.RiverviewV2WorkMonitor = Object.freeze({
    render,
    refresh,
    snapshotDiagnostics: () => ({
      status: state.status,
      objectives_source: state.objectivesStatus,
      assignments_source: state.assignmentsStatus,
      fetched_at: state.fetchedAt,
      includes_record_ids: false,
      includes_objective_text: false,
      includes_acceptance_criteria: false,
      includes_artifacts: false,
      includes_event_payloads: false
    })
  });
})();
