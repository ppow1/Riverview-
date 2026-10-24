// Revision: 1.0.0
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
global.window = {};
const data = require('../website/v2/deployed/assets/living-roadmap-data.js');
const adapter = require('../website/v2/deployed/assets/living-roadmap-adapter.js');
const ROOT = path.join(__dirname, '..', 'website/v2/deployed');

test('primary roadmap workstreams remain visible with truthful Grace integration state', () => {
  const streams = data.items.filter((item) => ['grace-autonomy', 'website-visualization'].includes(item.id));
  assert.deepEqual(streams.map((item) => item.workstream), ['Grace Autonomy', 'Website Visualization']);
  assert.equal(streams[0].status, 'unknown');
  assert.match(streams[0].detail, /no authoritative live integration/i);
});

test('lifecycle metadata keeps parked, elaboration, Ready Bench, active, and complete separate', () => {
  const stages = new Set(data.items.map((item) => item.stage));
  assert([...stages].some((stage) => stage === 'Parking Lot'));
  assert([...stages].some((stage) => stage.startsWith('Steward-approved elaboration')));
  assert([...stages].some((stage) => stage.startsWith('Ready Bench')));
  assert([...stages].some((stage) => stage.startsWith('Active Work')));
  assert([...stages].some((stage) => stage === 'Complete'));
  const rb = data.items.find((item) => item.id === 'ready-bench-rb0001');
  assert.equal(rb.status, 'unknown');
  assert.match(rb.detail, /cannot reconcile these sources/i);
});

test('objective status view maps only recorded lifecycle/status fields and keeps cancellation distinct', () => {
  const cases = [
    [{status:'CANCELLED', lifecycle_status:'blocked'}, 'canceled'],
    [{status:'COMPLETED', lifecycle_status:'completed'}, 'completed'],
    [{assignment_state:'running', lifecycle_status:'working'}, 'active'],
    [{lifecycle_status:'blocked'}, 'blocked'],
    [{lifecycle_status:'stalled'}, 'stalled'],
    [{lifecycle_status:'waiting'}, 'waiting'],
    [{lifecycle_status:'parked'}, 'parked'],
    [{}, 'unknown']
  ];
  for (const [record, expected] of cases) assert.equal(adapter.statusMap(record), expected);
  const model = adapter.objective({objective_id:'objective:from-api', request:'A real authorized title', lifecycle_stage:'Engineering executing'});
  assert.equal(model.title, 'A real authorized title');
  assert.equal(model.objectiveId, 'objective:from-api');
  assert.equal(adapter.objective({}).title, 'Riverview objective');
});

test('keyword, tag, and priority filters compose without changing the source records', () => {
  const items = [
    {title:'Work evidence', priority:'P1', tags:['website','work']},
    {title:'Operator model', priority:'unassigned', tags:['grace','ready-bench']},
    {title:'Mobile acceptance', priority:'P2', tags:['website','mobile']}
  ];
  assert.deepEqual(adapter.filterItems(items,{query:'evidence'}).map(x=>x.title),['Work evidence']);
  assert.deepEqual(adapter.filterItems(items,{tag:'website'}).map(x=>x.title),['Work evidence','Mobile acceptance']);
  assert.deepEqual(adapter.filterItems(items,{tag:'website',priority:'P2'}).map(x=>x.title),['Mobile acceptance']);
  assert.deepEqual(adapter.filterItems(items,{query:'operator',tag:'website'}),[]);
  assert.equal(items[0].title,'Work evidence');
});

test('V2 navigation loads the interactive view and only reads the existing protected objective API', () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const shell = fs.readFileSync(path.join(ROOT, 'assets/workspace.js'), 'utf8');
  const view = fs.readFileSync(path.join(ROOT, 'assets/living-roadmap.js'), 'utf8');
  assert.match(html, /data-view="roadmap"/);
  assert.match(html, /id="living-roadmap-workspace"/);
  assert.match(html, /id="roadmap-search"/);
  assert.match(html, /id="roadmap-tag"/);
  for (const stage of ['Parking Lot', 'Steward-approved elaboration', 'Design\/Specification', 'Ready Bench', 'Active Work', 'Complete']) assert.ok(html.includes(stage));
  assert.match(shell, /RiverviewV2LivingRoadmap\?\.render/);
  assert.match(view, /identity\.roles\.includes\("steward"\)/);
  assert.match(view, /\/api\/v1\/objectives\?limit=25/);
  assert.doesNotMatch(view, /method\s*:\s*"(POST|PUT|PATCH|DELETE)"/);
});
