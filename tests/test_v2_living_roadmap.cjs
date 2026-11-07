// Riverview~ Controlled Source
// File: tests/test_v2_living_roadmap.cjs
// Component: RIVERVIEW-V2-LIVING-ROADMAP
// Revision: 1.0.0
// Purpose: Check traceable roadmap completion and truthful unknown objective fields
// Execution Model: Local Node test runner; reads static source modules only
// Observability: TAP assertions identify mismatched source status/field claims
// Dependencies: Node.js built-in test/assert modules
// Inputs/Outputs: Versioned roadmap/objective projection; no live data or writes
// Authority: Read-only test of UI projection semantics; no permission or lifecycle changes
// Tests: node --test tests/test_v2_living_roadmap.cjs
// History: Git and revision/backup manifest
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

global.window = {};
const data = require('../website/v2/deployed/assets/living-roadmap-data.js');
const adapter = require('../website/v2/deployed/assets/living-roadmap-adapter.js');
const source = fs.readFileSync(path.join(__dirname, '../website/v2/deployed/assets/living-roadmap.js'), 'utf8');

test('delivered proposal migration is identified as complete with traceable V2 and PR links', () => {
  const item = data.items.find((entry) => entry.id === 'institutional-proposals');
  assert.equal(item.status, 'completed');
  assert.equal(item.stage, 'Complete · V2 interface deployed');
  assert.ok(item.links.some((link) => link.href === '#institutional-proposals'));
  assert.ok(item.links.some((link) => link.href.endsWith('/pull/281')));
});

test('RB-0001 source conflict remains unknown and unassigned', () => {
  const item = data.items.find((entry) => entry.id === 'ready-bench-rb0001');
  assert.equal(item.status, 'unknown');
  assert.equal(item.priority, 'unassigned');
  assert.match(item.blockers, /Conflicting source records/);
});

test('objective projection fields do not invent priority or roadmap workstream', () => {
  const objective = adapter.objective({
    objective_id: 'objective:example', request: 'Example request', status: 'grounded',
    lifecycle_stage: 'Awaiting authorized work order', updated_at: '2026-10-25T12:00:00Z'
  });
  assert.equal(Object.hasOwn(objective, 'priority'), false);
  assert.equal(Object.hasOwn(objective, 'workstream'), false);
  assert.equal(objective.status, 'waiting');
  assert.match(source, /Unassigned — the canonical objective projection does not contain a P0–P3 priority field/);
  assert.match(source, /No canonical objective-to-roadmap workstream relation is available/);
});
