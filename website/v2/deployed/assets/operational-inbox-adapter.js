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
        sources: new Set(), severity: null
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
    }
    return [...byEvent.values()].map((row) => ({...row, sources: [...row.sources]}))
      .sort((a, b) => (isoTime(b.timestamp) ?? -Infinity) - (isoTime(a.timestamp) ?? -Infinity));
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

  const api = Object.freeze({mergeFeeds, filterRows});
  if (typeof window !== "undefined") window.RiverviewV2OperationalInboxAdapter = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
