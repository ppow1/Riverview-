// =============================================================================
// RIVERVIEW~ CONTROLLED TEST
// File: tests/test_v2_operational_inbox.cjs
// Component: RIVERVIEW-V2-INSTITUTIONAL-ACTIVITY-LEDGER
// Revision: 1.0.0
// Purpose: Verify read-only event joining, identity metadata, paging, and authenticated API wiring.
// Execution Model: Node test runner
// Observability: Assertions over adapter output and source API contracts
// Dependencies: Node.js; website/v2/deployed/assets/operational-inbox-adapter.js
// Authority: No network or production mutations
// Changed: 2026-10-25 UTC | RV-INTEGRATE-295-297-302-20261025 | Port the exact PR #295 cursor and identity regressions.
// History: Git
// =============================================================================
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {mergeFeeds, mergeEventPage, filterRows} = require("../website/v2/deployed/assets/operational-inbox-adapter.js");

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

test("event adapter preserves the V1 ledger's redacted identity and causal metadata", () => {
  const [row] = mergeFeeds({events:[{
    event_id:"e-ledger", event_type:"assignment.updated", seq:81,
    occurred_at:"2026-10-25T11:59:00Z", recorded_at:"2026-10-25T12:00:00Z",
    assignment_id:"work-4", actor_id:"resident-2", correlation_id:"corr-5",
    causation_id:"e-parent", payload_schema:"rv.assignment.updated.v1"
  }]});
  assert.equal(row.sequence,81);
  assert.equal(row.occurredAt,"2026-10-25T11:59:00Z");
  assert.equal(row.recordedAt,"2026-10-25T12:00:00Z");
  assert.equal(row.actorId,"resident-2");
  assert.equal(row.correlationId,"corr-5");
  assert.equal(row.causationId,"e-parent");
  assert.equal(row.payloadSchema,"rv.assignment.updated.v1");
});

test("event paging merges older and newer cursor pages without duplicates", () => {
  const latest = mergeEventPage({}, {items:[{event_id:"e2",seq:2},{event_id:"e3",seq:3}],older_cursor:2}, "latest");
  assert.equal(latest.canLoadOlder,true);
  assert.equal(latest.newerCursor,3);
  const older = mergeEventPage(latest, {items:[{event_id:"e1",seq:1},{event_id:"e2",seq:2}],older_cursor:null}, "older");
  assert.deepEqual(older.items.map((item)=>item.event_id),["e1","e2","e3"]);
  assert.equal(older.canLoadOlder,false);
  assert.equal(older.olderCursor,null);
  const newer = mergeEventPage(older, {items:[{event_id:"e4",seq:4}],next_cursor:null}, "newer");
  assert.deepEqual(newer.items.map((item)=>item.seq),[1,2,3,4]);
  assert.equal(newer.canLoadNewer,false);
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
  for (const id of ["operational-inbox", "inbox-rows", "inbox-search", "inbox-source", "inbox-severity", "inbox-status", "inbox-sort", "inbox-events-older", "inbox-events-newer", "inbox-events-page-status"]) assert.match(html,new RegExp(`id="${id}"`));
  for (const endpoint of ["/api/v1/notifications?limit=50", "/api/v1/attention?limit=50", "/api/v1/events?limit=50"]) assert.ok(js.includes(endpoint));
  assert.match(js,/before_seq=\$\{encodeURIComponent\(cursor\)\}/);
  assert.match(js,/after_seq=\$\{encodeURIComponent\(cursor\)\}/);
  assert.match(js,/credentials:\s*"same-origin"/);
  assert.match(js,/method:\s*"GET"/);
  assert.doesNotMatch(js,/method:\s*"(POST|PUT|PATCH|DELETE)"/);
  assert.match(js,/credentials:\s*"same-origin"/);
});
