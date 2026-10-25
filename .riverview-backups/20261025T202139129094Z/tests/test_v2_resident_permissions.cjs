// Revision: 1.0.0
// Focused contract checks for the V2 wrapper around the existing permission API.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..', 'website/v2/deployed');
const read = (name) => fs.readFileSync(path.join(root, name), 'utf8');

test('V2 navigation opens the resident permission workspace and refreshes its existing registry', () => {
  const html = read('index.html');
  const shell = read('assets/workspace.js');
  const client = read('assets/resident-permissions.js');
  assert.match(html, /data-view="resident-permissions"/);
  assert.match(html, /id="resident-permissions-workspace"[^>]*hidden/);
  assert.match(html, /id="resident-permission-refresh"/);
  assert.match(shell, /resident-permissions-workspace/);
  assert.match(shell, /rv:resident-permissions/);
  assert.match(client, /fetch\(path/);
  assert.match(client, /credentials:"same-origin"/);
  assert.match(client, /cache:"no-store"/);
  assert.match(client, /GET/);
  assert.match(client, /api\/v1\/resident-permissions/);
});

test('V2 retains existing pending revision, explicit activation, revoke and CAS operations', () => {
  const client = read('assets/resident-permissions.js');
  assert.match(client, /expected_revision:Number\(selected\.revision/);
  assert.match(client, /\/PUT"|"PUT"/);
  assert.match(client, /data-approve/);
  assert.match(client, /data-revoke/);
  assert.match(client, /transition\("approve"/);
  assert.match(client, /transition\("revoke"/);
  assert.match(client, /window\.confirm\(prompt\)/);
  assert.match(client, /Save creates a pending revision/);
  assert.match(client, /office\.manage/);
});

test('missing institutional identity and denied/unavailable API responses are explicit and do not fabricate data', () => {
  const client = read('assets/resident-permissions.js');
  assert.match(client, /steward_account_required/);
  assert.match(client, /Institutional Steward identity is unavailable/);
  assert.match(client, /resident_permission_registry_unavailable/);
  assert.match(client, /authenticated/);
  assert.match(client, /no records were returned and no change was made/i);
});

test('V2 permission screen is responsive and keeps the server as the authority boundary', () => {
  const html = read('index.html');
  const css = read('assets/resident-permissions.css');
  const server = fs.readFileSync(path.join(__dirname, '..', 'src/riverview_core/status_dashboard/server.py'), 'utf8');
  assert.match(html, /the exact <code>office\.manage<\/code> grant/);
  assert.match(server, /not identity or "steward" not in identity\.get\("roles", \(\)\)/);
  assert.match(server, /not identity\.get\("authority_principal_id"\)/);
  assert.match(server, /resident_permission_change_not_authorized/);
  assert.match(css, /@media\(max-width:600px\)/);
});
