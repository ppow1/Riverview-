// RIVERVIEW~ CONTROLLED TEST
// File: tests/test_riverview_doorbell_bridge_node.cjs
// Component: CHATGPT-DOORBELL
// Revision: 1.0.0
// Purpose: Verify fixed wake, fail-closed exact conversation resolution and verified send metadata
// Execution Model: Deterministic Node.js unit tests; no browser or network access
// Observability: node:test assertions and exit status
// Dependencies: Node.js built-in node:test and the Riverview bridge module
// Authority: Synthetic CDP targets only
// Changed: 2026-10-17 UTC | RV-C3-DOORBELL-001 | Add New-Core CDP bridge tests
// Contracts: docs/components/CHATGPT_DOORBELL.md
// Tests: This file
// History: Git and .riverview-revisions.json

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { FIXED_ACTION, OPERATION, WAKE_TEXT, selectExactTarget, validate, verified } = require('../tools/riverview_doorbell_bridge.cjs');

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

test('the operation and wake remain fixed, and only a composer transition proves submission', () => {
  assert.equal(OPERATION, 'ring_riverview_doorbell');
  assert.equal(WAKE_TEXT, 'Riverview doorbell v1: inspect the Riverview MCP mailbox.');
  assert.equal(verified({ submitted: true, click_invoked: true, composer_cleared: true }), true);
  assert.equal(verified({ submitted: true, click_invoked: true, composer_cleared: false }), false);
  assert.match(FIXED_ACTION, /data-testid="send-button"/);
  assert.match(FIXED_ACTION, /composer_cleared/);
  assert.doesNotMatch(FIXED_ACTION, /KeyboardEvent|fetch\(|XMLHttpRequest|responseText/);
});

test('request contract rejects extra fields, bad identities and unbounded timeout', () => {
  assert.doesNotThrow(() => validate({ operation: OPERATION, request_id: id, correlation_id: id, timeout_seconds: 60 }));
  assert.throws(() => validate({ operation: OPERATION, request_id: 'bad', correlation_id: id, timeout_seconds: 60 }), /RIV-PLY-0002/);
  assert.throws(() => validate({ operation: OPERATION, request_id: id, correlation_id: id, timeout_seconds: 121 }), /RIV-PLY-0002/);
  assert.throws(() => validate({ operation: OPERATION, request_id: id, correlation_id: id, timeout_seconds: 60, prompt: 'arbitrary' }), /RIV-PLY-0002/);
});
