// Revision: 1.0.0
/* Normalizes authorized objective projections without asserting workstream relationships. */
(() => {
  "use strict";
  const statusMap = (item = {}) => {
    const status = String(item.status || "").toLowerCase();
    const lifecycle = String(item.lifecycle_status || "").toLowerCase();
    const assignment = String(item.assignment_state || "").toLowerCase();
    if (status === "cancelled" || lifecycle === "cancelled") return "canceled";
    if (["completed", "complete"].includes(lifecycle) || status === "completed") return "completed";
    if (lifecycle === "stalled" || status === "stalled") return "stalled";
    if (lifecycle === "blocked" || status === "failed" || assignment === "blocked") return "blocked";
    if (lifecycle === "waiting" || ["received", "grounded", "proposed", "waiting_for_evidence"].includes(status) || assignment === "awaiting_verification") return "waiting";
    if (["working", "in_progress"].includes(lifecycle) || assignment === "running") return assignment === "running" ? "active" : "in_progress";
    if (lifecycle === "active") return "active";
    if (lifecycle === "parked") return "parked";
    return "unknown";
  };
  const titleFor = (item = {}) => {
    const raw = typeof item.request === "string" ? item.request.replace(/\s+/g, " ").trim() : "";
    return raw ? raw.slice(0, 160) + (raw.length > 160 ? "…" : "") : "Riverview objective";
  };
  const objective = (item = {}) => Object.freeze({
    status: statusMap(item), title: titleFor(item),
    stage: item.lifecycle_stage || "Stage unavailable in objective projection",
    updatedAt: item.updated_at || null,
    objectiveId: item.objective_id || null,
    assignmentId: item.assignment_id || null,
    summary: item.rework?.rationale || item.latest_event?.event_type || "No blocker or progress reason recorded in this projection."
  });
  const filterItems = (items = [], {query = "", tag = "", priority = ""} = {}) => {
    const needle = String(query).trim().toLowerCase();
    return items.filter((item) => {
      const searchable = [item.title, item.summary, item.detail, item.workstream, item.stage, item.status,
        ...(Array.isArray(item.tags) ? item.tags : []),
        ...(Array.isArray(item.links) ? item.links.map((link) => link.label) : [])].join(" ").toLowerCase();
      return (!needle || searchable.includes(needle)) &&
        (!tag || (Array.isArray(item.tags) && item.tags.includes(tag))) &&
        (!priority || item.priority === priority);
    });
  };
  const api = Object.freeze({statusMap, objective, filterItems});
  window.RiverviewV2LivingRoadmapAdapter = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
