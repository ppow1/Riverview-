const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ROOT = path.join(__dirname, '..', 'website/v2/deployed');

test('V2 process workflow view uses existing authenticated canonical graph APIs', () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const shell = fs.readFileSync(path.join(ROOT, 'assets/workspace.js'), 'utf8');
  const viewer = fs.readFileSync(path.join(ROOT, 'assets/process-workflows.js'), 'utf8');
  assert.match(html, /data-view="process-workflows"/);
  assert.match(html, /id="process-workflows-workspace"[^>]*hidden/);
  for (const id of ['graph-select', 'graph-execution-position', 'graph-canvas', 'graph-node-detail', 'graph-jumps']) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(shell, /rvv2:view/);
  assert.match(viewer, /\/api\/v1\/graphs/);
  assert.match(viewer, /credentials:"same-origin"/);
  assert.match(viewer, /position\?\.status==="current"/);
  assert.match(viewer, /position\.node_id===item\.id/);
  assert.match(viewer, /openJump/);
  assert.match(viewer, /documentation_references/);
});

test('V2 documentation catalog is searchable, read-only, and limits links to declared component docs', () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const catalog = fs.readFileSync(path.join(ROOT, 'assets/documentation-catalog.js'), 'utf8');
  assert.match(html, /data-view="documentation"/);
  assert.match(html, /id="documentation-workspace"[^>]*hidden/);
  assert.match(html, /id="documentation-search"/);
  assert.match(catalog, /\/api\/v1\/graphs/);
  assert.match(catalog, /docs\\\/components/);
  assert.match(catalog, /detail unavailable/i);
  assert.match(catalog, /no workflow nodes or references are inferred/i);
  assert.doesNotMatch(catalog, /method\s*:/);
  assert.doesNotMatch(catalog, /\.innerHTML\s*=/);
});
