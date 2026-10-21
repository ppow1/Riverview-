/*
Riverview~ Controlled Source
File: scripts/verify_v2_work_monitor.cjs
Component: RIVERVIEW-V2-WORK-EXECUTION-MONITOR
Revision: 1.0.0
Purpose: Test authenticated read-only work projections, safe rendering, and unavailable states
Execution Model: Isolated Node VM contract test; all responses are local fixtures
Observability: Named assertions and process exit status
Dependencies: Node.js built-in assert, fs, path, and vm modules
Inputs/Outputs: Synthetic Dashboard response fixtures; no credentials, production records, or network
Authority: Test only; no external or durable operations
Changed: 2026-10-21 UTC | RV-V2-CAPABILITY-INTEGRATION-P1 | Initial V2 work monitor tests
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md; docs/components/STATUS_DASHBOARD.md
Tests: scripts/verify_v2_work_monitor.cjs
History: Git and .riverview-backups/manifest.jsonl
*/
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(ROOT, "website/v2/assets/work-monitor.js"), "utf8");

function boot({protocol = "https:", pathname = "/v2/", responses = []} = {}) {
  const nodes = new Map();
  const documentListeners = new Map();
  const makeNode = (tag = "div") => ({
    tagName: tag.toUpperCase(), textContent: "", value: "", dataset: {}, hidden: false,
    children: [], listeners: {},
    addEventListener(name, fn) { this.listeners[name] = fn; },
    append(...items) { this.children.push(...items); },
    replaceChildren(...items) { this.children = items; }
  });
  const document = {
    getElementById(id) { if (!nodes.has(id)) nodes.set(id, makeNode()); return nodes.get(id); },
    createElement(tag) { return makeNode(tag); },
    addEventListener(name, fn) { documentListeners.set(name, fn); }
  };
  const calls = [];
  const queue = [...responses];
  const context = {
    document, location: {protocol, pathname}, window: {}, Date, Promise, String, Number, Boolean, Array,
    fetch: async (url, options) => {
      calls.push({url, options});
      const item = queue.shift();
      if (!item) throw new Error("unexpected_fetch");
      if (item.throw) throw item.throw;
      return {ok: item.status >= 200 && item.status < 300, status: item.status,
        async json() { return item.body; }};
    },
    console
  };
  vm.runInNewContext(source, context, {filename: "work-monitor.js"});
  documentListeners.get("DOMContentLoaded")?.();
  return {context, nodes, calls};
}

async function run() {
  const fixture = boot({protocol: "http:", pathname: "/"});
  await fixture.context.window.RiverviewV2WorkMonitor.refresh();
  assert.equal(fixture.calls.length, 0, "fixture preview must not call Dashboard API");
  assert.equal(fixture.context.window.RiverviewV2WorkMonitor.snapshotDiagnostics().status, "unavailable");
  assert.match(fixture.nodes.get("work-refresh-status").textContent, /No request was sent/);

  const online = boot({responses: [
    {status: 200, body: {status: "authenticated", identity: {roles: ["steward"]}}},
    {status: 200, body: {schema_version: "rv.dashboard.objectives.v1", status: "available", items: [{
      objective_id: "objective:example", request: "PRIVATE REQUEST MUST NOT RENDER", acceptance_criteria: ["PRIVATE CRITERIA MUST NOT RENDER"],
      status: "executing", assignment_id: "assignment:example", assignment_state: "running",
      verification: null, updated_at: "2026-10-21T12:00:00Z", artifact: {path: "/private/path"}
    }], truncated: false}},
    {status: 200, body: {status: "available", items: [{
      assignment_id: "assignment:example", state: "running", owner: "codex", workflow_id: "eng", workflow_step: "step-1",
      last_meaningful_progress: {event_type: "worker.heartbeat", recorded_at: "2026-10-21T12:01:00Z", payload: "MUST NOT RENDER"}
    }], truncated: false}}
  ]});
  await online.context.window.RiverviewV2WorkMonitor.refresh();
  assert.deepEqual(online.calls.map((call) => call.url), [
    "/api/v1/auth/session", "/api/v1/objectives?limit=25", "/api/v1/assignments?limit=25"
  ]);
  for (const call of online.calls) {
    assert.equal(call.options.method, "GET");
    assert.equal(call.options.credentials, "same-origin");
    assert.equal(call.options.cache, "no-store");
    assert.equal(call.options.body, undefined);
  }
  assert.equal(online.nodes.get("work-objectives-body").children.length, 1);
  assert.equal(online.nodes.get("work-assignments-body").children.length, 1);
  assert.match(online.nodes.get("work-objectives-body").children[0].children.map((node) => node.textContent).join(" "), /objective:example.*executing.*assignment:example.*running/);
  assert.match(online.nodes.get("work-assignments-body").children[0].children.map((node) => node.textContent).join(" "), /assignment:example.*running.*codex.*step-1.*worker.heartbeat/);
  const visibleText = ["work-objectives-body", "work-assignments-body", "work-refresh-status"]
    .map((id) => online.nodes.get(id).children.map((row) => row.textContent + " " + row.children.map((cell) => cell.textContent).join(" ")).join(" ") + online.nodes.get(id).textContent).join(" ");
  assert.doesNotMatch(visibleText, /PRIVATE REQUEST|PRIVATE CRITERIA|private\/path|MUST NOT RENDER/);
  const diagnostics = online.context.window.RiverviewV2WorkMonitor.snapshotDiagnostics();
  assert.equal(diagnostics.status, "available");
  assert.equal(diagnostics.includes_record_ids, false);
  assert.equal(diagnostics.includes_objective_text, false);
  assert.doesNotMatch(JSON.stringify(diagnostics), /objective:example|assignment:example|PRIVATE/);

  const unauthorized = boot({responses: [{status: 401, body: {error: "authentication_required"}}]});
  await unauthorized.context.window.RiverviewV2WorkMonitor.refresh();
  assert.equal(unauthorized.calls.length, 1, "do not request work data after session rejection");
  assert.equal(unauthorized.context.window.RiverviewV2WorkMonitor.snapshotDiagnostics().objectives_source, "authentication_required");

  const unavailable = boot({responses: [
    {status: 200, body: {status: "authenticated"}},
    {status: 200, body: {schema_version: "rv.dashboard.objectives.v1", status: "not_initialized", items: []}},
    {status: 503, body: {error: "projection_unavailable"}}
  ]});
  await unavailable.context.window.RiverviewV2WorkMonitor.refresh();
  assert.equal(unavailable.context.window.RiverviewV2WorkMonitor.snapshotDiagnostics().status, "unavailable");
  assert.match(unavailable.nodes.get("work-objectives-empty").textContent, /not_initialized/);
  assert.doesNotMatch(unavailable.nodes.get("work-objectives-empty").textContent, /0 objectives/);

  const partial = boot({responses: [
    {status: 200, body: {status: "authenticated"}},
    {status: 200, body: {schema_version: "rv.dashboard.objectives.v1", status: "available", items: []}},
    {status: 503, body: {error: "projection_unavailable"}}
  ]});
  await partial.context.window.RiverviewV2WorkMonitor.refresh();
  assert.equal(partial.context.window.RiverviewV2WorkMonitor.snapshotDiagnostics().status, "partial");
  assert.equal(partial.context.window.RiverviewV2WorkMonitor.snapshotDiagnostics().objectives_source, "available");
  assert.equal(partial.context.window.RiverviewV2WorkMonitor.snapshotDiagnostics().assignments_source, "unavailable");

  assert.doesNotMatch(source, /setInterval\s*\(|setTimeout\s*\(|POST|PUT|PATCH|DELETE|192\.168\.1\.|:8080|:18080/,
    "the Work view must not poll or call inference hosts or mutating routes");
  console.log("PASS: fixture-origin no-network guard; authenticated bounded GETs; safe objective/assignment rendering; snapshot redaction; authentication rejection; not-initialized, unavailable, and partial states; no polling/writes/host calls");
}

run().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
