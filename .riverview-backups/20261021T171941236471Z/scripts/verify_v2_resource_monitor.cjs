/*
Riverview~ Controlled Source
File: scripts/verify_v2_resource_monitor.cjs
Component: RIVERVIEW-V2-HARDWARE-AI-RESOURCE-MONITOR
Revision: 1.0.0
Purpose: Exercise the V2 monitor's authorization, provenance, stale/unavailable, and no-host-polling behavior
Execution Model: Deterministic Node VM fixture; no network access
Observability: Named assertions and process exit status
Dependencies: Node.js built-in assert and vm modules
Inputs/Outputs: Synthetic sanitized Dashboard status payloads; no credentials or production data
Authority: Isolated UI contract test only
Changed: 2026-10-21 UTC | RV-WEB-V2-HW-AI-RESOURCE-001 | Initial monitor behavior verification
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: scripts/verify_v2_resource_monitor.cjs
History: Git and revision/backup manifest
*/
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(ROOT, "website/v2/assets/resource-monitor.js"), "utf8");

function boot({protocol = "https:", pathname = "/v2/", responses = []} = {}) {
  const nodes = new Map();
  const cards = ["hardware", "inference", "dashboard"].map((kind, index) => ({
    dataset: {resourceKind: kind, search: `${kind} ${index}`}, textContent: `${kind} card`, hidden: false
  }));
  const documentListeners = new Map();
  const makeNode = (id) => ({
    id, textContent: "", value: "all", dataset: {}, hidden: false, disabled: false,
    listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; }
  });
  const document = {
    getElementById(id) { if (!nodes.has(id)) nodes.set(id, makeNode(id)); return nodes.get(id); },
    querySelectorAll(selector) { return selector === "[data-resource-card]" ? cards : []; },
    addEventListener(name, fn) { documentListeners.set(name, fn); }
  };
  const calls = [];
  const queue = [...responses];
  const context = {
    document, location: {protocol, pathname}, window: {}, Date, Set, Number, String,
    fetch: async (url, options) => {
      calls.push({url, options});
      const item = queue.shift();
      if (!item) throw new Error("unexpected_fetch");
      if (item.throw) throw item.throw;
      return {ok: item.status >= 200 && item.status < 300, status: item.status,
        async json() { return item.body; }};
    },
    URL, console
  };
  vm.runInNewContext(source, context, {filename: "resource-monitor.js"});
  documentListeners.get("DOMContentLoaded")?.();
  return {context, nodes, cards, calls, documentListeners};
}

async function run() {
  const offline = boot({protocol: "http:", pathname: "/"});
  await offline.context.window.RiverviewV2ResourceMonitor.refresh();
  assert.equal(offline.calls.length, 0, "fixture HTTP preview must never call Dashboard or model endpoints");
  assert.equal(offline.context.window.RiverviewV2ResourceMonitor.snapshotDiagnostics().gpu_inventory, "unavailable");

  const observedAt = "2026-10-21T11:00:00Z";
  const online = boot({responses: [
    {status: 200, body: {status: "authenticated", identity: {roles: ["steward"]}}},
    {status: 200, body: {
      schema_version: "rv.dashboard.status.v1", projection_status: "healthy", freshness: "current", observed_at: observedAt,
      workers: {status: "stale", active_workers: 4, healthy_workers: 2, stale_workers: 1, unknown_workers: 1},
      assignment_counts: {queued: 2, executing: 1}, assignments_total: 3,
      cme: {status: "healthy"}, grace_execution: {status: "unknown"}
    }}
  ]});
  await online.context.window.RiverviewV2ResourceMonitor.refresh();
  assert.deepEqual(online.calls.map((call) => call.url), ["/api/v1/auth/session", "/api/v1/status"]);
  for (const call of online.calls) {
    assert.equal(call.options.credentials, "same-origin");
    assert.equal(call.options.cache, "no-store");
    assert.equal(call.options.method, "GET");
  }
  assert.match(online.nodes.get("resource-worker-summary").textContent, /4 active/);
  assert.match(online.nodes.get("resource-assignment-summary").textContent, /queued: 2/);
  assert.match(online.nodes.get("resource-dashboard-observed").textContent, /2026-10-21T11:00:00.000Z/);
  assert.equal(online.context.window.RiverviewV2ResourceMonitor.snapshotDiagnostics().gpu_utilization, "unavailable");
  assert.equal(online.context.window.RiverviewV2ResourceMonitor.snapshotDiagnostics().diagnostics_include_response_body, false);

  const unauthorized = boot({responses: [{status: 401, body: {error: "authentication_required"}}]});
  await unauthorized.context.window.RiverviewV2ResourceMonitor.refresh();
  assert.equal(unauthorized.calls.length, 1, "do not request status after session rejection");
  assert.equal(unauthorized.nodes.get("resource-worker-summary").textContent, "Unavailable");

  const unavailable = boot({responses: [
    {status: 200, body: {status: "authenticated"}},
    {status: 200, body: {schema_version: "rv.dashboard.status.v1", projection_status: "unavailable", freshness: "unavailable", observed_at: observedAt}}
  ]});
  await unavailable.context.window.RiverviewV2ResourceMonitor.refresh();
  assert.equal(unavailable.nodes.get("resource-assignment-summary").textContent, "Unavailable");
  assert.doesNotMatch(unavailable.nodes.get("resource-assignment-summary").textContent, /0 recorded/);

  assert.doesNotMatch(source, /192\.168\.1\.(160|162)|:8080|:18080|setInterval\s*\(/,
    "V2 must not poll inference hosts or continuously query the status API");
  console.log("PASS: fixture-origin guard; authenticated same-origin Dashboard summary; timestamps; stale/unknown counts; auth rejection; unavailable metrics; no host polling");
}

run().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
