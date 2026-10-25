// Revision: 1.0.0
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const adapter = require("../website/v2/deployed/assets/overview-adapter.js");
const root = path.resolve(__dirname, "../website/v2/deployed");

test("overview maps live assignment, worker, and service states without changing source values", () => {
  const model = adapter.dashboard({schema_version:"rv.dashboard.status.v1",projection_status:"healthy",
    observed_at:"2026-10-25T12:00:00Z",assignments_total:5,assignment_counts:{running:2,blocked:1,queued:2},
    workers:{status:"healthy",active_workers:3,healthy_workers:2,stale_workers:1,unknown_workers:0},
    grace_execution:{status:"healthy"},cme:{status:"degraded"},source:{source_commit:"abc123"}},Date.parse("2026-10-25T12:00:10Z"));
  assert.equal(model.work.summary,"5 recorded assignments");
  assert.equal(model.work.detail,"blocked: 1 · queued: 2 · running: 2");
  assert.equal(model.workers.summary,"3 active · 2 healthy · 1 stale · 0 unknown");
  assert.equal(model.serviceState,"degraded");
  assert.equal(model.observedAt,"2026-10-25T12:00:00Z");
});

test("stale or incomplete dashboard observations do not look healthy", () => {
  const stale = adapter.dashboard({schema_version:"rv.dashboard.status.v1",projection_status:"healthy",
    observed_at:"2026-10-25T11:00:00Z",assignments_total:0,assignment_counts:{},workers:{status:"healthy",
    active_workers:0,healthy_workers:0,stale_workers:0,unknown_workers:0},grace_execution:{status:"healthy"},cme:{status:"healthy"}},Date.parse("2026-10-25T12:00:00Z"));
  assert.equal(stale.work.state,"stale");
  assert.equal(stale.serviceState,"stale");
  const missingTime = adapter.dashboard({schema_version:"rv.dashboard.status.v1",projection_status:"healthy",
    assignments_total:1,assignment_counts:{running:1}});
  assert.equal(missingTime.work.state,"unknown");
  assert.equal(adapter.dashboard({schema_version:"other"}),null);
});

test("attention and telemetry distinguish a real empty window from unavailable data", () => {
  assert.equal(adapter.attention({status:"available",items:[],limit:50},"2026-10-25T12:00:00Z").summary,
    "0 items in the latest returned window");
  assert.equal(adapter.attention({status:"not_initialized",items:[],limit:50},null).state,"not_initialized");
  assert.equal(adapter.attention({status:"unavailable",items:[]},null),null);
  const unavailable = adapter.telemetry({schema_version:"rv.dashboard.resource-telemetry.v1",status:"unavailable",hosts:[],observed_at:null});
  assert.equal(unavailable.state,"unavailable");
  assert.equal(unavailable.hostCount,0);
  assert.equal(adapter.telemetry({schema_version:"wrong"}),null);
});

test("authorization errors remain explicit and source UI uses existing read APIs", () => {
  assert.equal(adapter.statusError({status:401}).state,"unauthenticated");
  assert.equal(adapter.statusError({status:403}).state,"denied");
  assert.equal(adapter.statusError({}).state,"unavailable");
  const html=fs.readFileSync(path.join(root,"index.html"),"utf8");
  const js=fs.readFileSync(path.join(root,"assets/overview.js"),"utf8");
  const workspace=fs.readFileSync(path.join(root,"assets/workspace.js"),"utf8");
  assert.match(html,/overview-adapter\.js\?rev=live-operations-20261026/);
  assert.match(html,/overview\.js\?rev=live-operations-20261026/);
  assert.match(html,/overview\.css\?rev=live-operations-20261026/);
  assert.doesNotMatch(html,/Preview fixture count|Sample only · no live status|Sample overview/);
  assert.match(js,/credentials: "same-origin"/);
  assert.match(js,/cache: "no-store"/);
  assert.match(js,/\/api\/v1\/status/);
  assert.match(js,/\/api\/v1\/attention\?limit=50/);
  assert.match(js,/\/api\/v1\/resources\/telemetry/);
  assert.match(workspace,/RiverviewV2Overview\?\.render\(\)/);
});
