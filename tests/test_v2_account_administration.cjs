// Revision: 1.0.0
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..', 'website/v2/deployed');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

test('V2 exposes account administration as a distinct view and loads its versioned assets', () => {
  const html = read('index.html');
  const workspace = read('assets/workspace.js');
  assert.match(html, /data-view="account-administration"/);
  assert.match(html, /id="account-administration-workspace"[^>]*hidden/);
  assert.match(html, /account-administration\.js\?rev=/);
  assert.match(html, /account-administration\.css\?rev=/);
  assert.match(workspace, /rv:account-administration/);
  assert.match(workspace, /account-administration-workspace/);
});

test('account view reuses existing enrollment, account-list, session and account-admin APIs', () => {
  const client = read('assets/account-administration.js');
  assert.match(client, /\/api\/v1\/account\/enrollments\?limit=50/);
  assert.match(client, /\/api\/v1\/account\/users\?limit=100/);
  assert.match(client, /\/api\/v1\/account\/users\/.*\/sessions/);
  assert.match(client, /\/api\/v1\/account\/users\/.*\/disable/);
  assert.match(client, /\/api\/v1\/account\/users\/.*\/roles/);
  assert.match(client, /\/api\/v1\/account\/users\/.*\/grant/);
  assert.match(client, /\/api\/v1\/account\/enrollments\/.*\/decision/);
  assert.match(client, /\{disabled\}/);
  assert.match(client, /\{role, grant\}/);
  assert.match(client, /\{revoked:true\}/);
  assert.match(client, /currentAccountId/);
  assert.match(client, /Cannot disable own account/);
  assert.match(client, /Role changes are unavailable for your current account/);
  assert.match(client, /credentials:"same-origin"/);
  assert.match(client, /cache:"no-store"/);
  assert.match(client, /X-Riverview-CSRF/);
});

test('mutating account operations require explicit confirmation and preserve backend-owned authority', () => {
  const client = read('assets/account-administration.js');
  assert.match(client, /window\.confirm\(summary\)/);
  assert.match(client, /window\.confirm\(`Revoke all active sessions/);
  assert.match(client, /window\.confirm\(prompt\)/);
  assert.match(client, /Grant \$\{role\}.*window\.confirm/s);
  assert.match(client, /window\.confirm\(`Revoke the access grant/);
  assert.match(client, /blocks new sign-ins, revokes active sessions/);
  assert.match(client, /await loadAccounts\(\)/);
  assert.match(read('index.html'), /cannot change identity bindings/);
  assert.match(client, /Stewards cannot disable their own account/i);
  assert.match(read('index.html'), /self-disable, self-grant revocation, and self-role changes are unavailable/i);
  assert.match(client, /Steward role, CSRF, and audit checks/);
  assert.match(client, /data-decision="approve"/);
  assert.match(client, /data-decision="deny"/);
});

test('email configuration reuses protected APIs, never reads the password, and confirms global actions', () => {
  const client = read('assets/account-administration.js');
  const html = read('index.html');
  assert.match(html, /Shared email delivery/);
  assert.match(client, /\/api\/v1\/account\/email-settings/);
  assert.match(client, /\/api\/v1\/account\/email-settings\/test/);
  assert.match(client, /window\.confirm\("Save shared email delivery settings/);
  assert.match(client, /window\.confirm\(`Send one test email/);
  assert.match(client, /password_configured/);
  assert.match(client, /password"\)\.value = ""/);
  assert.doesNotMatch(client, /password_ciphertext|account-email-config-key/);
  assert.match(client, /X-Riverview-CSRF/);
});

test('unauthenticated and non-Steward denials are presented plainly and the view is responsive', () => {
  const client = read('assets/account-administration.js');
  const css = read('assets/account-administration.css');
  assert.match(client, /steward_account_required/);
  assert.match(client, /not_authorized/);
  assert.match(client, /does not have the Steward role/);
  assert.match(client, /http_401/);
  assert.match(css, /@media\(max-width:600px\)/);
});
