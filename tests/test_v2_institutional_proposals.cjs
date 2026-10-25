// File Revision: 1.0.0
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
global.window = {};
require('../website/v2/deployed/assets/institutional-proposals-adapter.js');
const adapter = global.window.RiverviewV2ProposalAdapter;
const ROOT = path.join(__dirname, '..', 'website/v2/deployed');

test('proposal list adapter preserves authoritative status and handles absent fields explicitly', () => {
  const item = adapter.listItem({proposal_id:'proposal:123', title:'Review network upgrade', lifecycle_status:'READY_FOR_STEWARD_DECISION', current_revision:3, summary:'Request is ready.'});
  assert.equal(item.proposalId, 'proposal:123');
  assert.equal(item.status, 'READY_FOR_STEWARD_DECISION');
  assert.equal(item.revision, 3);
  assert.equal(item.updatedAt, null);
  assert.deepEqual(item.tags, []);
});

test('proposal detail adapter joins exact review, work-order, and lifecycle evidence without deriving state', () => {
  const detail = adapter.detail({
    proposal:{proposal_id:'proposal:123', lifecycle_status:'APPROVED'},
    revision:{revision:2, title:'Network upgrade', lifecycle_status:'APPROVED', acceptance_criteria:['Verified'], source_references:['docs/network.md']},
    reviews:[{review_outcome:'ACCEPTED', reviewer_office:'Engineering', findings:'Meets scope.', conditions:['Schedule window'], created_at:'2026-10-24T12:00:00Z'}],
    work_order_links:[{objective_id:'objective:abc', objective_status:'GROUNDED', assignment_id:'work-order:def'}],
    events:[{event_type:'proposal.steward_decision', revision:2, occurred_at:'2026-10-24T12:01:00Z'}]
  });
  assert.equal(detail.status, 'APPROVED');
  assert.deepEqual(detail.acceptanceCriteria, ['Verified']);
  assert.equal(detail.reviews[0].outcome, 'ACCEPTED');
  assert.equal(detail.workOrders[0].assignmentId, 'work-order:def');
  assert.equal(detail.events[0].type, 'proposal.steward_decision');
  assert.equal(adapter.detail({}).status, null);
});

test('V2 exposes the proposal registry through an isolated Steward-facing workspace and existing API', () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const shell = fs.readFileSync(path.join(ROOT, 'assets/workspace.js'), 'utf8');
  const client = fs.readFileSync(path.join(ROOT, 'assets/institutional-proposals.js'), 'utf8');
  assert.match(html, /data-view="institutional-proposals"/);
  assert.match(html, /id="institutional-proposals-workspace"[^>]*hidden/);
  assert.match(html, /proposal-status-filter/);
  assert.match(html, /proposal-refresh/);
  assert.match(shell, /RiverviewV2InstitutionalProposals\?\.render/);
  assert.match(client, /\/api\/v1\/institutional-proposals/);
  assert.match(client, /credentials:"same-origin"/);
  assert.match(client, /cache:"no-store"/);
});

test('V2 proposal client is read-only, renders untrusted records as text, and surfaces authorization failures', () => {
  const client = fs.readFileSync(path.join(ROOT, 'assets/institutional-proposals.js'), 'utf8');
  const css = fs.readFileSync(path.join(ROOT, 'assets/institutional-proposals.css'), 'utf8');
  assert.doesNotMatch(client, /method\s*:\s*"(POST|PUT|PATCH|DELETE)"/);
  assert.match(client, /textContent\s*=/);
  assert.doesNotMatch(client, /\.innerHTML\s*=/);
  assert.match(client, /error\.status === 401/);
  assert.match(client, /error\.status === 403/);
  assert.match(client, /institutional authority/);
  assert.match(css, /@media\(max-width:760px\)/);
  assert.match(css, /@media\(max-width:440px\)/);
});
