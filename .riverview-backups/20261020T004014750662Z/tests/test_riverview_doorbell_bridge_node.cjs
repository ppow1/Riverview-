// RIVERVIEW~ CONTROLLED TEST
// File: tests/test_riverview_doorbell_bridge_node.cjs
// Component: CHATGPT-DOORBELL
// Revision: 1.0.2
// Purpose: Verify fixed wake, exact targeting, status contract, and failure evidence metadata
// Inputs/Outputs: Synthetic targets, payloads and temporary runtime paths / node:test assertions only
// Execution Model: Deterministic Node.js unit tests; no browser or network access
// Observability: node:test assertions and exit status
// Dependencies: Node.js built-in node:test and the Riverview bridge module
// Authority: Synthetic CDP targets only
// Changed: 2026-10-18 UTC | RV-C3-DOORBELL-DOD-001 | Verify status contract and durable failure record
// Changed: 2026-10-19 UTC | RV-C2-DOORBELL-SELECTOR-20261019 | Add synthetic Ask ChatGPT readiness-selector regression; predecessor SHA-256 218beaa7cf136349afaf67348b2a32217fbff5253852b852481ced0cdfda9953
// Contracts: docs/components/CHATGPT_DOORBELL.md
// Tests: This file
// History: Git and .riverview-revisions.json

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'rv-doorbell-test-'));
process.env.RIVERVIEW_RUNTIME_ROOT = tempRoot;
const { FIXED_ACTION, OPERATION, READINESS, WAKE_TEXT, selectExactTarget, statusSnapshot, validate, verified } = require('../tools/riverview_doorbell_bridge.cjs');

const id = '00000000-0000-4000-8000-000000000000';
const page = value => ({ type: 'page', url: `https://chatgpt.com/c/${value}`, webSocketDebuggerUrl: 'ws://127.0.0.1:9225/devtools/page/test' });
const projectPage = value => ({ type: 'page', url: `https://chatgpt.com/g/riverview-project/c/${value}`, webSocketDebuggerUrl: 'ws://127.0.0.1:9225/devtools/page/test' });

test('conversation selection accepts only one exact ChatGPT page', () => {
  assert.equal(selectExactTarget([page(id)], id).url, page(id).url);
  assert.equal(selectExactTarget([projectPage(id)], id).url, projectPage(id).url);
  assert.throws(() => selectExactTarget([], id), /RIV-PLY-0005/);
  assert.throws(() => selectExactTarget([page(id), page(id)], id), /RIV-PLY-0006/);
  assert.throws(() => selectExactTarget([page('11111111-1111-4111-8111-111111111111')], id), /RIV-PLY-0005/);
  assert.throws(() => selectExactTarget([{ ...page(id), url: `https://example.com/c/${id}` }], id), /RIV-PLY-0005/);
});

test('readiness and fixed action accept the observed Ask ChatGPT composer selector', () => {
  const askChatGptSelector = 'div[contenteditable="true"][aria-label="Ask ChatGPT"]';
  const composer = { disabled: false, getBoundingClientRect: () => ({ width: 420, height: 56 }) };
  const result = vm.runInNewContext(READINESS, {
    location: { hostname: 'chatgpt.com', pathname: `/c/${id}` },
    document: {
      querySelector(selector) {
        return selector.includes(askChatGptSelector) ? composer : null;
      },
    },
  });
  assert.equal(result.authenticated, true);
  assert.equal(result.composer, true);
  assert.equal(FIXED_ACTION.includes(askChatGptSelector), true);
  assert.equal(WAKE_TEXT, 'Riverview doorbell v1: inspect the Riverview MCP mailbox.');
  assert.doesNotMatch(READINESS, /innerText|document\.body|textContent/);
});

test('the operation and wake remain fixed, and only a composer transition proves submission', () => {
  assert.equal(OPERATION, 'ring_riverview_doorbell');
  assert.equal(WAKE_TEXT, 'Riverview doorbell v1: inspect the Riverview MCP mailbox.');
  assert.equal(verified({ submitted: true, click_invoked: true, composer_cleared: true }), true);
  assert.equal(verified({ submitted: true, click_invoked: true, composer_cleared: false }), false);
  assert.match(FIXED_ACTION, /data-testid="send-button"/);
  assert.match(FIXED_ACTION, /composer_cleared/);
  assert.doesNotMatch(READINESS, /innerText|document\.body|textContent/);
  assert.doesNotMatch(FIXED_ACTION, /KeyboardEvent|fetch\(|XMLHttpRequest|responseText/);
});

test('request contract rejects extra fields, bad identities and unbounded timeout', () => {
  assert.doesNotThrow(() => validate({ operation: OPERATION, request_id: id, correlation_id: id, timeout_seconds: 60 }));
  assert.throws(() => validate({ operation: OPERATION, request_id: 'bad', correlation_id: id, timeout_seconds: 60 }), /RIV-PLY-0002/);
  assert.throws(() => validate({ operation: OPERATION, request_id: id, correlation_id: id, timeout_seconds: 121 }), /RIV-PLY-0002/);
  assert.throws(() => validate({ operation: OPERATION, request_id: id, correlation_id: id, timeout_seconds: 60, prompt: 'arbitrary' }), /RIV-PLY-0002/);
});

test('status contract reports local readiness, external blockers and freshness without page content', async () => {
  const readiness = { bridge_version: '1.0.2', browser_runtime: true, cdp_available: true,
    authenticated_session: false, designated_target_configured: true, exact_target_resolvable: true,
    fixed_action_available: true, ready: false, failure_class: null };
  const status = await statusSnapshot({ readiness, browser_runtime: true, cdp_port: 9225,
    process: { state: 'running', started_at: '2026-10-17T00:00:00.000Z' } });
  assert.equal(status.schema_version, 'rv.chatgpt-doorbell.status.v1');
  assert.equal(status.component_id, 'CHATGPT-DOORBELL');
  assert.equal(status.status, 'blocked');
  assert.equal(status.ready, false);
  assert.equal(status.authentication_status, 'login_required');
  assert.equal(status.cdp.address, '127.0.0.1');
  assert.equal(status.freshness.stale_after_seconds, 60);
  assert.equal(status.workflow_position, null);
  assert.ok(status.blockers.some(item => item.code === 'COMMS5_MAILBOX_CONTRACT_NOT_INTEGRATED'));
  assert.equal(JSON.stringify(status).includes(WAKE_TEXT), false);
});

test('failed request persists only its identity and stable error class', () => {
  const configPath = path.join(tempRoot, 'missing-config.json');
  const payload = { operation: OPERATION, request_id: id, correlation_id: id, timeout_seconds: 5 };
  const run = spawnSync(process.execPath, [path.resolve(__dirname, '../tools/riverview_doorbell_bridge.cjs'), '--ring'], {
    input: JSON.stringify(payload), encoding: 'utf8', env: { ...process.env, RIVERVIEW_DOORBELL_CONFIG: configPath },
  });
  assert.equal(run.status, 2);
  const output = JSON.parse(run.stdout);
  assert.equal(output.request_id, id);
  assert.equal(output.correlation_id, id);
  assert.equal(output.failure_class, 'RIV-PLY-0010');
  const journalPath = path.join(tempRoot, 'doorbell', 'diagnostics', 'evidence.json');
  const journal = JSON.parse(fs.readFileSync(journalPath, 'utf8'));
  const attempt = journal[`${id}:${id}`];
  assert.equal(attempt.status, 'failed');
  assert.equal(attempt.failure_class, 'RIV-PLY-0010');
  assert.equal(fs.statSync(journalPath).mode & 0o777, 0o600);
});
