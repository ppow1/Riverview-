// Revision: 1.0.0
/* Read-only adapters for the existing authenticated Riverview operational APIs. */
(() => {
  "use strict";
  const text = (value) => typeof value === "string" ? value : "";
  const isoTime = (value) => {
    const ms = Date.parse(value || "");
    return Number.isFinite(ms) ? ms : null;
  };

  function mergeFeeds({notifications = [], attention = [], events = []} = {}) {
    const byEvent = new Map();
    const rowFor = (eventId) => {
      const key = eventId ? `event:${eventId}` : `record:${byEvent.size}`;
      if (!byEvent.has(key)) byEvent.set(key, {
        key, eventId: eventId || null, eventType: "Unknown event", description: "Description not supplied by source",
        timestamp: null, assignmentId: null, notificationId: null, deliveryState: null,
        sources: new Set(), severity: null, sequence: null, occurredAt: null,
        recordedAt: null, actorId: null, correlationId: null, causationId: null,
        payloadSchema: null, notificationDetails: null
      });
      return byEvent.get(key);
    };
    for (const event of events) {
      const row = rowFor(text(event.event_id));
      row.sources.add("event");
      row.eventType = text(event.event_type) || row.eventType;
      row.description = text(event.event_type) || row.description;
      row.timestamp = text(event.recorded_at) || row.timestamp;
      row.assignmentId = text(event.assignment_id) || row.assignmentId;
      row.sequence = event.seq ?? row.sequence;
      row.occurredAt = text(event.occurred_at) || row.occurredAt;
      row.recordedAt = text(event.recorded_at) || row.recordedAt;
      row.actorId = text(event.actor_id) || row.actorId;
      row.correlationId = text(event.correlation_id) || row.correlationId;
      row.causationId = text(event.causation_id) || row.causationId;
      row.payloadSchema = text(event.payload_schema) || row.payloadSchema;
    }
    for (const item of attention) {
      const row = rowFor(text(item.event_id));
      row.sources.add("attention");
      row.eventType = text(item.event_type) || row.eventType;
      row.description = text(item.failure_type) || text(item.event_type) || row.description;
      row.timestamp = text(item.recorded_at) || row.timestamp;
      row.assignmentId = text(item.assignment_id) || row.assignmentId;
    }
    for (const item of notifications) {
      const row = rowFor(text(item.source_event_id));
      row.sources.add("notification");
      row.eventType = text(item.event_type) || row.eventType;
      row.description = text(item.summary) || row.description;
      row.timestamp = text(item.source_recorded_at) || text(item.created_at) || row.timestamp;
      row.assignmentId = text(item.assignment_id) || row.assignmentId;
      row.notificationId = text(item.notification_id) || null;
      row.deliveryState = text(item.delivery_status) || "unknown";
      row.notificationDetails = notificationDetails(item);
    }
    return [...byEvent.values()].map((row) => ({...row, sources: [...row.sources]}))
      .sort((a, b) => (isoTime(b.timestamp) ?? -Infinity) - (isoTime(a.timestamp) ?? -Infinity));
  }

  function notificationDetails(item = {}) {
    const fields = ["notification_id", "source_event_id", "assignment_id", "event_type", "channel", "delivery_status",
      "source_recorded_at", "created_at", "delivered_at", "acknowledged_at", "decision_request_id",
      "decision_status", "assignment_version", "recovery_request_id", "recovery_status",
      "recovery_objective_id", "recovery_objective_revision", "recovery_action", "attempt_limit",
      "recovery_expires_at", "summary"];
    const result = Object.fromEntries(fields.map((key) => [key, item[key] ?? null]));
    const safeSourceFields = ["objective_id", "objective_revision", "runtime_revision", "failure_count",
      "last_error_code", "blocked_at", "last_failure_at", "decision", "recommended_action", "automatic_recovery"];
    const source = item.source_details && typeof item.source_details === "object" ? item.source_details : null;
    result.source_details = source ? Object.fromEntries(safeSourceFields.map((key) => [key, source[key] ?? null])) : null;
    return result;
  }

  function mergeEventPage(current = {}, page = {}, direction = "latest") {
    const byId = new Map((current.items || []).map((item) => [item.event_id, item]));
    for (const item of page.items || []) byId.set(item.event_id, item);
    const items = [...byId.values()].sort((a, b) => Number(a.seq) - Number(b.seq));
    const seqs = items.map((item) => Number(item.seq)).filter(Number.isFinite);
    return {
      items,
      olderCursor: direction === "older" ? (page.older_cursor ?? null) : (page.older_cursor ?? current.olderCursor ?? null),
      newerCursor: seqs.length ? Math.max(...seqs) : (current.newerCursor ?? null),
      canLoadOlder: direction === "older" ? Boolean(page.older_cursor) : direction === "latest" ? Boolean(page.older_cursor) : Boolean(current.canLoadOlder),
      canLoadNewer: direction === "newer" ? Boolean(page.next_cursor) : seqs.length > 0
    };
  }

  function notificationReceiptAction(row, canWrite) {
    if (!canWrite || !row?.notificationId) return null;
    if (row.deliveryState === "queued") return "delivered";
    if (row.deliveryState === "delivered") return "acknowledge";
    return null;
  }

  function filterRows(rows, {query = "", source = "all", severity = "all", status = "all", sort = "newest"} = {}) {
    const needle = query.trim().toLocaleLowerCase();
    return rows.filter((row) => {
      if (source !== "all" && !row.sources.includes(source)) return false;
      if (severity === "specified" && !row.severity) return false;
      if (severity === "unknown" && row.severity) return false;
      const state = row.deliveryState || "recorded";
      if (status !== "all" && state !== status) return false;
      return !needle || [row.eventType, row.description, row.assignmentId, row.eventId, row.notificationId]
        .some((value) => text(value).toLocaleLowerCase().includes(needle));
    }).sort((a, b) => {
      const delta = (isoTime(a.timestamp) ?? -Infinity) - (isoTime(b.timestamp) ?? -Infinity);
      return sort === "oldest" ? delta : -delta;
    });
  }

  const api = Object.freeze({mergeFeeds, mergeEventPage, notificationReceiptAction, notificationDetails, filterRows});
  if (typeof window !== "undefined") window.RiverviewV2OperationalInboxAdapter = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
