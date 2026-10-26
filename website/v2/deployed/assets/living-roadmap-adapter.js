// Revision: 1.0.0
/* Normalizes authorized objective projections without asserting workstream relationships. */
// File Revision: 1.0.0
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
  const requestTextFor = (item = {}) =>
    typeof item.request === "string" ? item.request.replace(/\s+/g, " ").trim() : "";
  const titleFor = (item = {}) => {
    const raw = requestTextFor(item);
    if (!raw) return "Riverview objective";
    const sentence = raw.split(/(?<=[.!?])\s+/)[0].trim();
    const concise = sentence.length <= 76 ? sentence : sentence.slice(0, 73).trimEnd() + "…";
    return concise;
  };
  const objective = (item = {}) => {
    const status = statusMap(item);
    const rationale = typeof item.rework?.rationale === "string" && item.rework.rationale.trim() ? item.rework.rationale.trim() : "";
    let blocker = "No blocker recorded in the objective projection.";
    if (item.steward_action_required) blocker = rationale || "Steward action is required; rationale is unavailable in this projection.";
    else if (status === "blocked") blocker = rationale || "The record is blocked; a reason is unavailable in this projection.";
    else if (status === "waiting") blocker = item.lifecycle_stage || "Waiting reason unavailable in this projection.";
    const latestEvent = item.latest_event && typeof item.latest_event === "object" ? { type: item.latest_event.event_type || null, occurredAt: item.latest_event.occurred_at || null } : null;
    const verification = item.verification && typeof item.verification === "object" ? { decision: item.verification.decision || null, summary: item.verification.summary || null } : null;
    return Object.freeze({ status, title: titleFor(item), fullRequest: requestTextFor(item), stage: item.lifecycle_stage || "Stage unavailable in objective projection", assignmentState: item.assignment_state || null, blocker, latestEvent, verification, updatedAt: item.updated_at || null, objectiveId: item.objective_id || null, assignmentId: item.assignment_id || null, dependencies: null, summary: rationale || latestEvent?.type || "No blocker or progress reason recorded in this projection." });
  };
  const filterItems = (items = [], {query = "", tag = "", priority = ""} = {}) => {
    const needle = String(query).trim().toLowerCase();
    return items.filter((item) => {
      const searchable = [item.title, item.fullRequest, item.summary, item.detail, item.workstream, item.stage, item.status,
        ...(Array.isArray(item.tags) ? item.tags : []),
        ...(Array.isArray(item.links) ? item.links.map((link) => link.label) : [])].join(" ").toLowerCase();
      return (!needle || searchable.includes(needle)) &&
        (!tag || (Array.isArray(item.tags) && item.tags.includes(tag))) &&
        (!priority || item.priority === priority);
    });
  };
  const api = Object.freeze({statusMap, titleFor, objective, filterItems});
  window.RiverviewV2LivingRoadmapAdapter = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
