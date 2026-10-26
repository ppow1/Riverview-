// Revision: 1.0.0
// Purpose: Convert existing authenticated operational APIs into safe V2 overview models.
(() => {
  "use strict";
  const STATES = new Set(["healthy", "degraded", "stale", "unknown", "unverified", "unavailable", "not_initialized", "active", "inactive", "available", "partial"]);
  const count = (value) => Number.isSafeInteger(value) && value >= 0 && value <= 1000000000 ? value : null;
  const date = (value) => {
    if (typeof value !== "string") return null;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const safeState = (value) => typeof value === "string" && STATES.has(value.toLowerCase()) ? value.toLowerCase() : "unknown";
  const freshness = (observedAt, now, windowSeconds = 60) => {
    const time = date(observedAt);
    if (time === null || time > now + 30000) return "unknown";
    return now - time > Math.max(1, windowSeconds) * 1000 ? "stale" : "current";
  };
  const statusError = (error) => {
    if (error?.status === 401) return {state: "unauthenticated", summary: "Sign in to view this source."};
    if (error?.status === 403) return {state: "denied", summary: "Access denied by the source."};
    return {state: "unavailable", summary: "Source unavailable; no values inferred."};
  };
  function dashboard(payload, now = Date.now()) {
    if (!payload || payload.schema_version !== "rv.dashboard.status.v1") return null;
    const timeState = freshness(payload.observed_at, now);
    const projection = safeState(payload.projection_status);
    const counts = payload.assignment_counts && typeof payload.assignment_counts === "object" && !Array.isArray(payload.assignment_counts)
      ? Object.entries(payload.assignment_counts).filter(([key, value]) => /^[a-z][a-z0-9_-]{0,31}$/i.test(key) && count(value) !== null).sort(([a], [b]) => a.localeCompare(b)).slice(0, 8)
      : [];
    const total = count(payload.assignments_total);
    const work = projection !== "healthy" || total === null
      ? {state: projection === "not_initialized" ? "not_initialized" : "unknown", summary: "Assignment summary unavailable."}
      : {state: timeState === "stale" ? "stale" : timeState === "current" ? "available" : "unknown",
        summary: `${total} recorded assignment${total === 1 ? "" : "s"}`,
        detail: counts.length ? counts.map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`).join(" · ") : "No state breakdown reported."};
    const worker = payload.workers && typeof payload.workers === "object" ? payload.workers : null;
    const workerState = worker ? safeState(worker.status) : "unknown";
    const workerNumbers = [count(worker?.active_workers), count(worker?.healthy_workers), count(worker?.stale_workers), count(worker?.unknown_workers)];
    const effectiveWorkerState = timeState === "stale" && workerState === "healthy" ? "stale" : timeState === "unknown" && workerState === "healthy" ? "unknown" : workerState;
    const workers = !worker || workerState === "unavailable" || workerState === "not_initialized"
      ? {state: workerState, summary: "Worker health unavailable."}
      : workerNumbers.every((value) => value !== null)
        ? {state: effectiveWorkerState, summary: `${workerNumbers[0]} active · ${workerNumbers[1]} healthy · ${workerNumbers[2]} stale · ${workerNumbers[3]} unknown`}
        : {state: "unknown", summary: "Worker counts not supplied."};
    const services = ["grace_execution", "cme"].map((key) => ({name: key === "cme" ? "CME monitor" : "Grace execution", state: safeState(payload[key]?.status)}));
    const serviceState = timeState === "stale" ? "stale" : timeState === "unknown" ? "unknown" : services.every((item) => item.state === "healthy") ? "healthy"
      : services.some((item) => item.state === "degraded") ? "degraded"
        : services.some((item) => item.state === "stale") ? "stale" : "unknown";
    return {observedAt: payload.observed_at, sourceCommit: typeof payload.source?.source_commit === "string" ? payload.source.source_commit : null,
      work, workers, services, projectionState: projection, serviceState, freshness: timeState};
  }
  function attention(payload, checkedAt) {
    if (!payload || !["available", "not_initialized"].includes(payload.status) || !Array.isArray(payload.items)) return null;
    const limit = count(payload.limit);
    const newest = payload.items.find((item) => date(item?.recorded_at) !== null);
    return {state: payload.status, count: payload.items.length, limit,
      summary: payload.status === "not_initialized" ? "Attention source not initialized." : `${payload.items.length} item${payload.items.length === 1 ? "" : "s"} in the latest returned window`,
      observedAt: newest?.recorded_at || null, checkedAt};
  }
  function telemetry(payload, now = Date.now()) {
    if (!payload || payload.schema_version !== "rv.dashboard.resource-telemetry.v1") return null;
    const status = safeState(payload.status);
    const hosts = Array.isArray(payload.hosts) ? payload.hosts.filter((host) => host && typeof host === "object") : [];
    const state = status === "available" || status === "partial"
      ? freshness(payload.observed_at, now, count(payload.freshness_window_seconds) || 30) === "stale" ? "stale" : freshness(payload.observed_at, now, count(payload.freshness_window_seconds) || 30)
      : status;
    return {state, status, hostCount: hosts.length, observedAt: payload.observed_at || null};
  }
  const api = Object.freeze({dashboard, attention, telemetry, statusError, freshness, safeState});
  if (typeof window !== "undefined") window.RiverviewV2OverviewAdapter = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
