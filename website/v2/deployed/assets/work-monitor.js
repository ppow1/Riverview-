/*
Riverview~ Controlled Source
File: website/v2/deployed/assets/work-monitor.js
Component: RIVERVIEW-V2-WORK-EXECUTION-MONITOR
Revision: 1.0.3
Purpose: Present bounded objective and assignment state with existing authorized cancellation actions
Execution Model: Request-driven same-origin browser reads; no background polling
Observability: Visible authorization, source status, fetched-at time, and persisted record timestamps
Dependencies: Authenticated rv.dashboard.status.v1 service; rv.dashboard.objectives.v1; assignment projection
Inputs/Outputs: GET summaries and same-origin cancellation request events; does not display request bodies, criteria, artifacts, or event payloads
Authority: Dashboard account authentication and server projection filters; cancellation delegates to the existing authorized lifecycle API
Changed: 2026-10-21 UTC | RV-V2-CAPABILITY-INTEGRATION-P1 | Initial read-only work status integration
Changed: 2026-10-23 UTC | RV-V2-MANUAL-IMAGE-GENERATION-248 | Preserve the deployed V2 source under its explicit production bundle path.
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md; docs/components/STATUS_DASHBOARD.md
Tests: scripts/verify_v2_work_monitor.cjs; tests/test_v2_workspace_shell.py
History: Git and .riverview-backups/manifest.jsonl
*/
(() => {
  "use strict";

  const evidenceAdapter = window.RiverviewV2WorkEvidenceAdapter;
  const evidenceView = window.RiverviewV2WorkEvidence;
  if (!evidenceAdapter || !evidenceView) return;

  const state = {
    status: "not_checked",
    objectivesStatus: "not_observed",
    assignmentsStatus: "not_observed",
    objectives: [],
    assignments: [],
    truncated: {objectives: false, assignments: false},
    fetchedAt: null,
    objectivesObservedAt: null,
    assignmentsObservedAt: null,
    inFlight: false,
    identity: null
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
      ? [item.objective_id, item.status, item.lifecycle_status, item.lifecycle_stage,
        item.operational_status?.label, item.operational_status?.event_type,
        ...(Array.isArray(item.related_outputs) ? item.related_outputs.flatMap((output) => [output.name, output.summary]) : []), item.assignment_id,
        state.assignments.find((assignment) => assignment.assignment_id === item.assignment_id)?.owner,
        item.assignment_state, item.latest_event?.event_type, item.rework?.rationale, item.verification?.decision]
      : [item.assignment_id, item.state, item.owner, item.workflow_id, item.workflow_step,
        item.last_meaningful_progress?.event_type];
    return fields.some((value) => String(value || "").toLowerCase().includes(query));
  }

  function sortRows(rows, kind) {
    const order = $("work-sort")?.value || "recent";
    const progressTime = (item) => {
      const timestamp = kind === "objective"
        ? (state.assignments.find((assignment) => assignment.assignment_id === item.assignment_id)?.last_meaningful_progress?.recorded_at || item.latest_event?.occurred_at)
        : item.last_meaningful_progress?.recorded_at;
      const parsed = Date.parse(timestamp || "");
      return Number.isFinite(parsed) ? parsed : null;
    };
    return [...rows].sort((left, right) => {
      if (order === "status") return String(left.lifecycle_status || left.state || left.status || "").localeCompare(String(right.lifecycle_status || right.state || right.status || "")) || String(left.objective_id || left.assignment_id).localeCompare(String(right.objective_id || right.assignment_id));
      if (order === "id") return String(left.objective_id || left.assignment_id).localeCompare(String(right.objective_id || right.assignment_id));
      const a = progressTime(left);
      const b = progressTime(right);
      if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
      return (order === "oldest" ? a - b : b - a) || String(left.objective_id || left.assignment_id).localeCompare(String(right.objective_id || right.assignment_id));
    });
  }

  function cell(row, value, className = "") {
    const node = document.createElement("td");
    node.textContent = value == null || value === "" ? "Unavailable" : String(value);
    if (className) node.className = className;
    row.append(node);
  }

  function linkButton(label, onClick, className = "work-record-link") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
  }

  function addEvidenceCell(row, record, assignment = null) {
    const target = document.createElement("td");
    target.append(evidenceView.createDetails(record, assignment, state.objectives));
    row.append(target);
  }

  function canCancelObjective(item) {
    if (!item || !state.identity?.roles?.includes("steward")) return false;
    if (item.status === "GROUNDED") return !item.assignment_id;
    return item.status === "WORK_ORDER_CREATED" && Boolean(item.assignment_id) &&
      ["queued", "ready"].includes(String(item.assignment_state || "").toLowerCase());
  }

  function renderRows() {
    const query = String($("work-search")?.value || "").trim().toLowerCase();
    const objectiveBody = $("work-objectives-body");
    const assignmentBody = $("work-assignments-body");
    if (!objectiveBody || !assignmentBody) return;
    objectiveBody.replaceChildren();
    assignmentBody.replaceChildren();
    const visibleObjectives = sortRows(state.objectives.filter((item) => matchesFilter(item, query, "objective")), "objective");
    const visibleAssignments = sortRows(state.assignments.filter((item) => matchesFilter(item, query, "assignment")), "assignment");

    for (const item of visibleObjectives) {
      const row = document.createElement("tr");
      row.dataset.objectiveId = item.objective_id;
      const assignment = item.assignment_id
        ? state.assignments.find((candidate) => candidate.assignment_id === item.assignment_id) || null
        : null;
      const model = evidenceAdapter.objectiveModel(item, assignment);
      cell(row, item.objective_id);
      cell(row, item.status || "Source lifecycle status unavailable");
      const operational = document.createElement("td");
      const operationalLabel = item.operational_status?.label || "Status unavailable";
      const operationalBadge = document.createElement("span");
      operationalBadge.className = "work-operational-status";
      operationalBadge.dataset.status = item.operational_status?.code || "status_unavailable";
      operationalBadge.textContent = operationalLabel;
      operational.append(operationalBadge);
      if (item.operational_status?.source) {
        const source = document.createElement("small");
        source.className = "work-operational-source";
        const when = item.operational_status.occurred_at ? ` · ${recordTime(item.operational_status.occurred_at)}` : "";
        source.textContent = `${item.operational_status.source}${when}`;
        operational.append(source);
      }
      row.append(operational);
      cell(row, model.stage);
      cell(row, model.blocker, "work-blocker-cell");
      const related = document.createElement("td");
      if (model.assignmentId) {
        const assignmentId = model.assignmentId;
        related.append(linkButton(assignmentId, () => {
          const linked = document.querySelector(`[data-assignment-row="${CSS.escape(assignmentId)}"]`);
          linked?.scrollIntoView({behavior: "smooth", block: "center"});
          linked?.classList.add("work-related-highlight");
          window.setTimeout(() => linked?.classList.remove("work-related-highlight"), 1400);
        }));
      }
      const outputs = Array.isArray(item.related_outputs) ? item.related_outputs : [];
      const primary = outputs[0] || null;
      const outputLabel = primary
        ? `${primary.name}${outputs.length > 1 ? ` · +${outputs.length - 1} outputs` : ""}${model.outputsTruncated ? " · older outputs omitted" : ""}`
        : (!model.outputsAvailable ? "Output status unavailable"
          : item.status === "COMPLETED" || item.assignment_state === "completed" ? "Completed work has no output record supplied"
          : ["WORK_ORDER_CREATED", "GROUNDED", "PROPOSED"].includes(item.status)
            ? "No deliverable recorded yet" : "Deliverable status unavailable");
      const deliverable = linkButton(outputLabel, () => {
        const detail = row.querySelector(".work-evidence-details");
        if (detail) {
          detail.open = true;
          detail.scrollIntoView({behavior: "smooth", block: "nearest"});
        }
      }, "work-record-link work-deliverable-link");
      deliverable.setAttribute("aria-label", primary
        ? `Open deliverable details for ${primary.name}` : `Open deliverable and evidence details: ${outputLabel}`);
      related.append(deliverable);
      if (primary?.summary) {
        const synopsis = document.createElement("small");
        synopsis.className = "work-output-synopsis";
        synopsis.textContent = primary.summary;
        related.append(synopsis);
      }
      row.append(related);
      cell(row, model.owner);
      cell(row, `${model.progressEvent || "No progress event recorded"} · ${model.progressAge}`);
      addEvidenceCell(row, item, assignment);
      const action = document.createElement("td");
      if (canCancelObjective(item)) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "engineering-cancel-button work-objective-cancel";
        button.textContent = "Cancel…";
        button.dataset.openObjectiveCancellation = item.objective_id;
        button.setAttribute("aria-label", `Cancel objective ${item.objective_id}`);
        action.append(button);
      }
      row.append(action);
      objectiveBody.append(row);
    }
    for (const item of visibleAssignments) {
      const row = document.createElement("tr");
      row.dataset.assignmentRow = item.assignment_id;
      cell(row, item.assignment_id);
      const model = evidenceAdapter.assignmentModel(item, state.objectives);
      cell(row, `${model.status} · ${model.stage}`);
      cell(row, model.owner);
      cell(row, model.progressEvent
        ? `${model.progressEvent} · ${recordTime(model.progressAt)} · ${model.progressAge}`
        : `No progress event recorded · ${model.progressAge}`);
      const related = document.createElement("td");
      if (model.linkedObjectiveIds.length) {
        model.linkedObjectiveIds.forEach((objectiveId) => related.append(linkButton(objectiveId, () => {
          const linked = document.querySelector(`[data-objective-id="${CSS.escape(objectiveId)}"]`);
          linked?.scrollIntoView({behavior: "smooth", block: "center"});
          linked?.classList.add("work-related-highlight");
          window.setTimeout(() => linked?.classList.remove("work-related-highlight"), 1400);
        })));
      } else related.textContent = "No objective link recorded";
      row.append(related);
      addEvidenceCell(row, item);
      assignmentBody.append(row);
    }

    const objectiveEmpty = $("work-objectives-empty");
    const assignmentEmpty = $("work-assignments-empty");
    if (objectiveEmpty) objectiveEmpty.textContent = visibleObjectives.length
      ? "" : state.objectivesStatus === "available"
        ? (query ? "No objectives match this filter." : "The authoritative objective projection returned no records.")
        : `Objective source: ${state.objectivesStatus}.`;
    if (assignmentEmpty) assignmentEmpty.textContent = visibleAssignments.length
      ? "" : state.assignmentsStatus === "available"
        ? (query ? "No assignments match this filter." : "The authoritative assignment projection returned no records.")
        : `Assignment source: ${state.assignmentsStatus}.`;
    if (objectiveEmpty) objectiveEmpty.hidden = visibleObjectives.length > 0;
    if (assignmentEmpty) assignmentEmpty.hidden = visibleAssignments.length > 0;
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
      const session = await getJson("/api/v1/auth/session");
      state.identity = session.identity || null;
    } catch (error) {
      state.objectives = [];
      state.assignments = [];
      state.identity = null;
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
    const apply = (result, target, statusKey, observedKey, label) => {
      if (result.status === "rejected") {
        if ([401, 403].includes(result.reason?.status)) {
          state[statusKey] = "authentication_required";
          state[target] = [];
          state[observedKey] = null;
        } else {
          state[statusKey] = state[observedKey] ? "stale" : "unavailable";
        }
        failures.push(`${label}: ${safeCode(result.reason?.message)}`);
        return;
      }
      const body = result.value;
      const nextStatus = body.status === "available" && Array.isArray(body.items)
        ? "available" : body.status === "not_initialized" ? "not_initialized" : "unavailable";
      if (nextStatus === "available") {
        state[statusKey] = nextStatus;
        state[target] = body.items.slice(0, 25);
        state[observedKey] = body.observed_at || state.fetchedAt;
      } else if (nextStatus === "not_initialized") {
        state[statusKey] = nextStatus;
        state[target] = [];
        state[observedKey] = null;
      } else {
        state[statusKey] = state[observedKey] ? "stale" : "unavailable";
      }
      state.truncated[target] = Boolean(body.truncated || body.next_cursor);
      if (state[statusKey] === "unavailable") failures.push(`${label}: unexpected source status`);
    };
    apply(objectivesResult, "objectives", "objectivesStatus", "objectivesObservedAt", "Objectives");
    apply(assignmentsResult, "assignments", "assignmentsStatus", "assignmentsObservedAt", "Assignments");
    const ready = [state.objectivesStatus, state.assignmentsStatus].filter((status) => status === "available").length;
    const notReady = [state.objectivesStatus, state.assignmentsStatus].some((status) => status !== "available");
    const hasStale = [state.objectivesStatus, state.assignmentsStatus].includes("stale");
    const label = ready === 2 && !hasStale ? "CURRENT" : ready || hasStale ? (hasStale ? "STALE / PARTIAL" : "PARTIAL") : "UNAVAILABLE";
    const status = hasStale ? "stale" : ready === 2 ? "available" : ready === 1 ? "partial" : "unavailable";
    const freshness = `Read at ${state.fetchedAt}; timestamps in rows are persisted source times.`;
    const detail = failures.length ? `${freshness} ${failures.join(" · ")}` : freshness;
    setStatus(status, label, detail);
    state.inFlight = false;
    renderRows();
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("work-refresh")?.addEventListener("click", refresh);
    $("work-search")?.addEventListener("input", renderRows);
    $("work-sort")?.addEventListener("change", renderRows);
    document.addEventListener("rvv2:view", (event) => {
      if (event.detail?.view === "work") refresh();
    });
    $("work-objectives-body")?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-open-objective-cancellation]");
      if (!button) return;
      const item = state.objectives.find((row) => row.objective_id === button.dataset.openObjectiveCancellation);
      if (!canCancelObjective(item)) {
        setStatus("available", "REFRESH REQUIRED", "The objective is no longer eligible for cancellation. Refreshing authoritative state.");
        refresh();
        return;
      }
      window.dispatchEvent(new CustomEvent("rvv2:cancel-objective", {detail: {objective: item, source: "work-objectives"}}));
    });
    window.addEventListener("rvv2:objective-cancelled", () => refresh());
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
