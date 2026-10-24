/* Pure view models over Riverview's authoritative objective and assignment projections. */
(() => {
  "use strict";
  const value = (item) => typeof item === "string" && item.trim() ? item.trim() : null;
  const validDate = (input) => {
    const time = Date.parse(input || "");
    return Number.isFinite(time) ? time : null;
  };
  function ageLabel(timestamp, now = Date.now()) {
    const time = validDate(timestamp);
    if (time === null) return "Progress time not recorded";
    const delta = now - time;
    if (delta < 0) return "Recorded time is in the future; age unavailable";
    const minutes = Math.floor(delta / 60000);
    if (minutes < 1) return "Less than a minute ago";
    if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days === 1 ? "" : "s"} ago`;
  }
  function exactLinkedObjectives(assignmentId, objectives = []) {
    const id = value(assignmentId);
    return id ? objectives.filter((objective) => value(objective.assignment_id) === id)
      .map((objective) => value(objective.objective_id)).filter(Boolean) : [];
  }
  function blockerReason(objective, assignment) {
    const lifecycle = String(objective?.lifecycle_status || "").toLowerCase();
    const assignmentState = String(assignment?.state || objective?.assignment_state || "").toLowerCase();
    const rework = value(objective?.rework?.rationale);
    if (lifecycle === "blocked" || assignmentState === "blocked" || ["failed", "cancelled"].includes(String(objective?.status || "").toLowerCase())) {
      if (rework) return rework;
      if (Number(objective?.dispatch_failures) > 0) return `${objective.dispatch_failures} dispatch failure${objective.dispatch_failures === 1 ? "" : "s"}; detailed cause unavailable.`;
      if (Number(objective?.verification_failures) > 0) return `${objective.verification_failures} verification failure${objective.verification_failures === 1 ? "" : "s"}; detailed cause unavailable.`;
      return "Blocked state is recorded; a specific reason is not present in this projection.";
    }
    if (lifecycle === "waiting" || assignmentState === "awaiting_verification" || assignmentState === "rework_required") {
      return value(objective?.lifecycle_stage) || "Waiting state is recorded; reason unavailable.";
    }
    return "No blocker is recorded in the available projection.";
  }
  function objectiveModel(objective = {}, assignment = null, now = Date.now()) {
    const progress = assignment?.last_meaningful_progress || null;
    const timestamp = progress?.recorded_at || objective?.latest_event?.occurred_at || null;
    return Object.freeze({
      kind: "objective",
      id: value(objective.objective_id),
      status: value(objective.lifecycle_status) || value(objective.status) || "Status unavailable",
      stage: value(objective.lifecycle_stage) || value(objective.status) || "Stage not supplied",
      blocker: blockerReason(objective, assignment),
      dependencies: null,
      dependencyAvailability: "Dependency links are not exposed by the current objective projection.",
      assignmentId: value(objective.assignment_id),
      owner: value(assignment?.owner),
      worker: null,
      progressEvent: value(progress?.event_type) || value(objective?.latest_event?.event_type),
      progressAt: timestamp,
      progressAge: ageLabel(timestamp, now),
      evidenceEventId: value(progress?.event_id),
      evidenceEventSeq: Number.isSafeInteger(progress?.event_seq) ? progress.event_seq : null,
      objectiveHref: objective.objective_id ? `/api/v1/objectives/${encodeURIComponent(objective.objective_id).replaceAll("%3A", ":")}` : null,
      assignmentHref: objective.assignment_id ? `/api/v1/assignments/${encodeURIComponent(objective.assignment_id)}` : null,
      updatedAt: value(objective.updated_at)
    });
  }
  function assignmentModel(assignment = {}, objectives = [], now = Date.now()) {
    const progress = assignment.last_meaningful_progress || {};
    const linked = exactLinkedObjectives(assignment.assignment_id, objectives);
    return Object.freeze({
      kind: "assignment",
      id: value(assignment.assignment_id),
      status: value(assignment.state) || "Status unavailable",
      stage: value(assignment.workflow_step) || value(assignment.workflow_id) || "Stage not supplied",
      blocker: String(assignment.state || "").toLowerCase() === "blocked"
        ? "Assignment is marked blocked; the assignment summary does not provide a reason."
        : "No blocker is recorded in the assignment summary.",
      dependencies: null,
      dependencyAvailability: "Dependency links are not exposed by the current assignment projection.",
      assignmentId: value(assignment.assignment_id),
      owner: value(assignment.owner),
      worker: null,
      progressEvent: value(progress.event_type),
      progressAt: value(progress.recorded_at),
      progressAge: ageLabel(progress.recorded_at, now),
      evidenceEventId: value(progress.event_id),
      evidenceEventSeq: Number.isSafeInteger(progress.event_seq) ? progress.event_seq : null,
      linkedObjectiveIds: linked,
      assignmentHref: assignment.assignment_id ? `/api/v1/assignments/${encodeURIComponent(assignment.assignment_id)}` : null,
      updatedAt: value(assignment.updated_at)
    });
  }
  const api = Object.freeze({ageLabel, exactLinkedObjectives, blockerReason, objectiveModel, assignmentModel});
  if (typeof window !== "undefined") window.RiverviewV2WorkEvidenceAdapter = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
