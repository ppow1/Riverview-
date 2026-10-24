// Revision: 1.0.0
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {mergeFeeds, filterRows} = require("../website/v2/deployed/assets/operational-inbox-adapter.js");

test("adapter joins notification, attention, and event history by authoritative event ID", () => {
  const rows = mergeFeeds({
    notifications: [{notification_id:"n-1",source_event_id:"e-1",event_type:"service_alert",summary:"Service needs review",delivery_status:"delivered",source_recorded_at:"2026-10-24T12:00:00Z",assignment_id:"wo-7"}],
    attention: [{event_id:"e-1",event_type:"service_alert",recorded_at:"2026-10-24T12:00:00Z",assignment_id:"wo-7",failure_type:"timeout"}],
    events: [{event_id:"e-1",event_type:"service_alert",recorded_at:"2026-10-24T12:00:00Z",assignment_id:"wo-7",seq:42}]
  });
  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0].sources.sort(), ["attention", "event", "notification"]);
  assert.equal(rows[0].eventId, "e-1");
  assert.equal(rows[0].deliveryState, "delivered");
  assert.equal(rows[0].assignmentId, "wo-7");
  assert.equal(rows[0].severity, null);
  assert.equal(rows[0].description, "Service needs review");
});

test("filters search, source, supplied severity, delivery state, and sort without mutating", () => {
  const rows = mergeFeeds({
    notifications: [
      {notification_id:"n-old",source_event_id:"e-old",event_type:"alert",summary:"Old alert",delivery_status:"queued",source_recorded_at:"2026-10-20T12:00:00Z"},
      {notification_id:"n-new",source_event_id:"e-new",event_type:"alert",summary:"Dog food alarm",delivery_status:"acknowledged",source_recorded_at:"2026-10-23T12:00:00Z"}
    ]
  });
  assert.equal(filterRows(rows,{query:"dog food",source:"notification",status:"acknowledged"}).length,1);
  assert.equal(filterRows(rows,{severity:"specified"}).length,0);
  assert.deepEqual(filterRows(rows,{sort:"oldest"}).map((row)=>row.eventId),["e-old","e-new"]);
  assert.deepEqual(rows.map((row)=>row.eventId),["e-new","e-old"]);
});

test("inbox is wired only to the authenticated GET projections and performs no writes", () => {
  const root = path.resolve(__dirname, "../website/v2/deployed");
  const html = fs.readFileSync(path.join(root,"index.html"),"utf8");
  const js = fs.readFileSync(path.join(root,"assets/operational-inbox.js"),"utf8");
  for (const id of ["operational-inbox", "inbox-rows", "inbox-search", "inbox-source", "inbox-severity", "inbox-status", "inbox-sort"]) assert.match(html,new RegExp(`id="${id}"`));
  for (const endpoint of ["/api/v1/notifications?limit=50", "/api/v1/attention?limit=50", "/api/v1/events?limit=50"]) assert.ok(js.includes(endpoint));
  assert.match(js,/method:\s*"GET"/);
  assert.doesNotMatch(js,/method:\s*"(POST|PUT|PATCH|DELETE)"/);
  assert.match(js,/credentials:\s*"same-origin"/);
});
