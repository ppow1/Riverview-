// RIVERVIEW~ CONTROLLED SOURCE
// File: tools/riverview_doorbell_bridge.cjs
// File Revision: 1.0.3
// Component: CHATGPT-DOORBELL | Revision: 1.0.2
// Purpose: Submit one fixed wake, persist safe attempt metadata, and report local status
// Inputs/Outputs: Fixed operation with request/correlation UUIDs / status contract and submission metadata
// Execution Model: Request-driven local CDP operation
// Observability: Owner-local rv.chatgpt-doorbell.status.v1 JSON and private metadata journal
// Dependencies: Node.js; Chrome/Chromium; native WebSocket or system node-ws package
// Authority: Localhost CDP only; fixed text/action; auth uses route/control selectors, never response text
// Changed: 2026-10-18 UTC | RV-C3-DOORBELL-DOD-001 | Add machine-readable status and durable failure metadata
// Changed: 2026-10-19 UTC | RV-C2-DOORBELL-SELECTOR-20261019 | Recognize current Ask ChatGPT composer selector; predecessor SHA-256 75da3b47937776addb01912e1de1f11dd1b5cf859a4df55850958172cfa3e5c3
// Changed: 2026-10-20 UTC | RV-C4-DOORBELL-SELECTOR-VISIBILITY-FIX-001 | Select the visible enabled composer when hidden matches precede it
// Contracts: docs/components/CHATGPT_DOORBELL.md
// Tests: tests/test_riverview_doorbell_bridge_node.cjs
// History: Git and .riverview-revisions.json

'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const VERSION = '1.0.2';
const OPERATION = 'ring_riverview_doorbell';
const WAKE_TEXT = 'Riverview doorbell v1: inspect the Riverview MCP mailbox.';
const CONFIG = process.env.RIVERVIEW_DOORBELL_CONFIG || path.join(os.homedir(), '.config', 'riverview', 'doorbell.json');
const RUNTIME_ROOT = process.env.RIVERVIEW_RUNTIME_ROOT || path.join(os.homedir(), '.local', 'state', 'riverview');
const JOURNAL = path.join(RUNTIME_ROOT, 'doorbell', 'diagnostics', 'evidence.json');
const CHATGPT_CONVERSATION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const COMPOSER_SELECTOR = '#prompt-textarea[contenteditable="true"],div[contenteditable="true"][aria-label="Chat with ChatGPT"],div[contenteditable="true"][aria-label="Ask ChatGPT"]';

function now() { return new Date().toISOString(); }
function targetRef(id) { return `target-sha256:${crypto.createHash('sha256').update(id).digest('hex')}`; }
function loadConfig() {
  let raw;
  try { raw = JSON.parse(fs.readFileSync(CONFIG, 'utf8')); }
  catch { throw Error('RIV-PLY-0010'); }
  const allowed = ['adapter_version', 'browser_executable', 'cdp_port', 'conversation_id'];
  if (!raw || Object.keys(raw).sort().join(',') !== allowed.join(',')) throw Error('RIV-PLY-0011');
  if (!CHATGPT_CONVERSATION_ID.test(raw.conversation_id) || !Number.isInteger(raw.cdp_port) || raw.cdp_port < 9225 || raw.cdp_port > 9325) throw Error('RIV-PLY-0011');
  if (typeof raw.browser_executable !== 'string' || !path.isAbsolute(raw.browser_executable)) throw Error('RIV-PLY-0011');
  return raw;
}
function selectExactTarget(targets, conversationId) {
  const matches = targets.filter(item => { try {
    const url = new URL(item.url);
    const segments = url.pathname.split('/').filter(Boolean);
    const index = segments.length - 1;
    return item.type === 'page' && url.hostname === 'chatgpt.com' &&
      segments[index] === conversationId && segments[index - 1] === 'c' && item.webSocketDebuggerUrl;
  } catch { return false; } });
  if (!matches.length) throw Error('RIV-PLY-0005');
  if (matches.length > 1) throw Error('RIV-PLY-0006');
  return matches[0];
}
async function exactTarget(config) {
  const response = await fetch(`http://127.0.0.1:${config.cdp_port}/json/list`);
  if (!response.ok) throw Error('RIV-PLY-0003');
  return selectExactTarget(await response.json(), config.conversation_id);
}
function connect(target, timeout) {
  const WebSocketImpl = globalThis.WebSocket || require('ws');
  const socket = new WebSocketImpl(target.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    const item = pending.get(message.id);
    if (!item) return;
    pending.delete(message.id);
    clearTimeout(item.timer);
    message.error ? item.reject(Error('RIV-PLY-0004')) : item.resolve(message.result);
  };
  const opened = new Promise((resolve, reject) => {
    const timer = setTimeout(() => { reject(Error('RIV-PLY-0009')); socket.close(); }, timeout);
    socket.onopen = () => { clearTimeout(timer); resolve(); };
    socket.onerror = () => { clearTimeout(timer); reject(Error('RIV-PLY-0004')); };
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const key = ++id;
    const timer = setTimeout(() => { pending.delete(key); reject(Error('RIV-PLY-0009')); }, timeout);
    pending.set(key, { resolve, reject, timer });
    socket.send(JSON.stringify({ id: key, method, params }));
  });
  return { socket, opened, call };
}

const READINESS = `(()=>{const route=location.hostname==='chatgpt.com'&&location.pathname.includes('/c/');const blocked=/\\/auth\\//i.test(location.pathname)||!!document.querySelector('input[type="password"],input[name="username"],[data-testid*="captcha"],iframe[src*="recaptcha"]');const e=[...document.querySelectorAll(${JSON.stringify(COMPOSER_SELECTOR)})].find(node=>{const r=node?.getBoundingClientRect?.();return !!r&&r.width>0&&r.height>0&&!node.disabled&&node.getAttribute?.('aria-disabled')!=='true'});return {authenticated:route&&!blocked,composer:!!e};})()`;
const FIXED_ACTION = `(async()=>{const e=[...document.querySelectorAll(${JSON.stringify(COMPOSER_SELECTOR)})].find(node=>{const r=node?.getBoundingClientRect?.();return !!r&&r.width>0&&r.height>0&&!node.disabled&&node.getAttribute?.('aria-disabled')!=='true'});if(!e)return {failure_class:'RIV-PLY-0007'};e.focus();e.replaceChildren();const p=document.createElement('p');p.textContent=${JSON.stringify(WAKE_TEXT)};e.appendChild(p);e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:${JSON.stringify(WAKE_TEXT)}}));const b=document.querySelector('button[data-testid="send-button"],button[aria-label="Send prompt"],button[aria-label="Send message"]');const enabled=!!b&&!b.disabled&&b.getAttribute('aria-disabled')!=='true';if(!enabled)return {failure_class:'RIV-PLY-0008',composer_populated:true,send_control_found:!!b,send_control_enabled:false};b.click();await new Promise(resolve=>setTimeout(resolve,750));const remaining=(e.innerText||e.textContent||'').trim().length;return {submitted:true,composer_populated:true,send_control_found:true,send_control_enabled:true,click_invoked:true,composer_cleared:remaining===0};})()`;
function readJournal() { try { return JSON.parse(fs.readFileSync(JOURNAL, 'utf8')); } catch { return {}; } }
function writeJournal(value) {
  fs.mkdirSync(path.dirname(JOURNAL), { recursive: true, mode: 0o700 });
  const tmp = `${JOURNAL}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(value, null, 2) + '\n', { mode: 0o600 });
  fs.renameSync(tmp, JOURNAL);
}
function verified(action) { return action?.submitted === true && action?.click_invoked === true && action?.composer_cleared === true; }
function result(input, status, failure, evidence, config, submitVerified = false) {
  return {
    attempt_id: crypto.randomUUID(), request_id: input.request_id, correlation_id: input.correlation_id,
    bridge_version: VERSION, designated_target_ref: config ? targetRef(config.conversation_id) : null,
    started_at: input.started_at, completed_at: now(), status, failure_class: failure || null,
    submit_verified: submitVerified, evidence_ref: evidence || null,
  };
}
function validate(input) {
  const keys = Object.keys(input || {}).sort().join(',');
  if (keys !== 'correlation_id,operation,request_id,timeout_seconds' || input.operation !== OPERATION ||
      !CHATGPT_CONVERSATION_ID.test(input.request_id) || !CHATGPT_CONVERSATION_ID.test(input.correlation_id) ||
      !Number.isInteger(input.timeout_seconds) || input.timeout_seconds < 1 || input.timeout_seconds > 120) throw Error('RIV-PLY-0002');
}
async function preflight() {
  const out = { bridge_version: VERSION, browser_runtime: false, cdp_available: false,
    authenticated_session: false, designated_target_configured: false, exact_target_resolvable: false,
    fixed_action_available: true, ready: false, failure_class: null };
  let connection;
  try {
    const config = loadConfig();
    out.designated_target_configured = true;
    out.browser_runtime = fs.existsSync(config.browser_executable);
    if (!out.browser_runtime) throw Error('RIV-PLY-0013');
    const version = await fetch(`http://127.0.0.1:${config.cdp_port}/json/version`);
    if (!version.ok) throw Error('RIV-PLY-0003');
    out.cdp_available = true;
    const target = await exactTarget(config);
    out.exact_target_resolvable = true;
    connection = connect(target, 5000);
    await connection.opened;
    const probe = await connection.call('Runtime.evaluate', { returnByValue: true, expression: READINESS });
    out.authenticated_session = probe?.result?.value?.authenticated === true && probe?.result?.value?.composer === true;
  } catch (error) {
    out.failure_class = failureClass(error);
  } finally {
    try { connection?.socket.close(); } catch { /* best-effort local socket close */ }
  }
  out.ready = out.browser_runtime && out.cdp_available && out.authenticated_session &&
    out.designated_target_configured && out.exact_target_resolvable;
  return out;
}

function failureClass(error) {
  const value = String(error?.message || '');
  return /^RIV-PLY-\d{4}$/.test(value) ? value : 'RIV-PLY-0003';
}

function latestAttempt() {
  const attempts = Object.values(readJournal()).filter(item => item &&
    typeof item.completed_at === 'string' && typeof item.status === 'string');
  attempts.sort((left, right) => right.completed_at.localeCompare(left.completed_at));
  const item = attempts[0];
  if (!item) return null;
  return {
    attempt_id: item.attempt_id || null,
    request_id: item.request_id || null,
    correlation_id: item.correlation_id || null,
    occurred_at: item.completed_at,
    status: item.status,
    failure_class: item.failure_class || null,
    submit_verified: item.submit_verified === true,
  };
}

async function statusSnapshot(runtime = {}) {
  const readiness = runtime.readiness || await preflight();
  const observedAt = now();
  const lastTrigger = latestAttempt();
  const blockers = [];
  if (!readiness.browser_runtime) blockers.push({ code: 'BROWSER_BINARY_UNAVAILABLE', owner: 'Codex3' });
  if (!readiness.cdp_available) blockers.push({ code: 'CDP_UNAVAILABLE', owner: 'Codex3' });
  if (readiness.cdp_available && !readiness.authenticated_session)
    blockers.push({ code: 'CHATGPT_AUTHENTICATION_REQUIRED', owner: 'Steward' });
  if (readiness.cdp_available && !readiness.exact_target_resolvable)
    blockers.push({ code: 'DESIGNATED_CONVERSATION_UNRESOLVED', owner: 'Steward' });
  blockers.push({ code: 'COMMS5_MAILBOX_CONTRACT_NOT_INTEGRATED', owner: 'Codex1', reference: 'issue:96' });
  blockers.push({ code: 'GRACE_RESULT_CONSUMER_NOT_INTEGRATED', owner: 'Codex2', reference: 'issue:96' });
  const localReady = readiness.browser_runtime && readiness.cdp_available && readiness.authenticated_session &&
    readiness.designated_target_configured && readiness.exact_target_resolvable;
  const localUnavailable = !readiness.browser_runtime || !readiness.cdp_available;
  return {
    schema_version: 'rv.chatgpt-doorbell.status.v1',
    component_id: 'CHATGPT-DOORBELL',
    component_version: VERSION,
    status: localUnavailable ? 'unavailable' : blockers.length ? 'blocked' : 'healthy',
    ready: false,
    local_browser_ready: localReady,
    observed_at: observedAt,
    freshness: { state: 'fresh', stale_after_seconds: 60 },
    browser_health: readiness.browser_runtime ? (readiness.cdp_available ? 'healthy' : 'unavailable') : 'unavailable',
    browser_runtime: runtime.browser_runtime || readiness.browser_runtime,
    browser_session: readiness.cdp_available ? 'running' : 'not_running',
    cdp: { status: readiness.cdp_available ? 'connected' : 'unavailable', address: '127.0.0.1', port: runtime.cdp_port || null },
    authentication_status: readiness.exact_target_resolvable ? (readiness.authenticated_session ? 'composer_ready' : 'login_required') : 'unknown',
    target_resolution: readiness.exact_target_resolvable ? 'exact_match' : 'unresolved',
    fixed_action_available: readiness.fixed_action_available,
    last_trigger: lastTrigger,
    last_error: lastTrigger?.failure_class ? { code: lastTrigger.failure_class, occurred_at: lastTrigger.occurred_at } :
      (readiness.failure_class ? { code: readiness.failure_class, occurred_at: observedAt } : null),
    blockers,
    external_dependencies: {
      comms5_mailbox: { owner: 'Codex1', state: 'not_integrated', contract_reference: 'issue:96' },
      grace_result_consumer: { owner: 'Codex2', state: 'not_integrated', contract_reference: 'issue:96' },
    },
    workflow_position: null,
    workflow_position_reason: 'No durable runtime event source currently records a canonical active node.',
    browser_process: runtime.process || { state: 'unknown', started_at: null },
    profile_lock_present: runtime.profile_lock_present === true,
  };
}
async function ring(input) {
  validate(input);
  const started = now();
  input.started_at = started;
  const key = `${input.request_id}:${input.correlation_id}`;
  const journal = readJournal();
  if (journal[key]?.status === 'succeeded' && journal[key]?.submit_verified === true) {
    return { ...journal[key], status: 'already_succeeded' };
  }
  let config;
  let connection;
  try {
    config = loadConfig();
    const target = await exactTarget(config);
    connection = connect(target, input.timeout_seconds * 1000);
    await connection.opened;
    const probe = await connection.call('Runtime.evaluate', { returnByValue: true, expression: READINESS });
    if (!probe?.result?.value?.authenticated) throw Error('RIV-PLY-0004');
    if (!probe?.result?.value?.composer) throw Error('RIV-PLY-0007');
    const action = await connection.call('Runtime.evaluate', { awaitPromise: true, returnByValue: true, expression: FIXED_ACTION });
    if (!verified(action?.result?.value)) throw Error(action?.result?.value?.failure_class || 'RIV-PLY-0014');
    const output = result(input, 'succeeded', null, `riverview://doorbell/${crypto.randomUUID()}`, config, true);
    journal[key] = output;
    writeJournal(journal);
    return output;
  } catch (error) {
    const output = result(input, 'failed', failureClass(error), null, config, false);
    try {
      journal[key] = output;
      writeJournal(journal);
    } catch {
      output.failure_class = 'RIV-PLY-0014';
    }
    return output;
  } finally {
    try { connection?.socket.close(); } catch { /* best-effort local socket close */ }
  }
}
async function main() {
  try {
    if (process.argv.includes('--preflight')) { console.log(JSON.stringify(await preflight())); return; }
    if (!process.argv.includes('--ring')) throw Error('RIV-PLY-0002');
    let text = '';
    for await (const chunk of process.stdin) text += chunk;
    const output = await ring(JSON.parse(text));
    console.log(JSON.stringify(output));
    if (output.status === 'failed') process.exitCode = 2;
  } catch (error) {
    console.log(JSON.stringify({ operation: OPERATION, bridge_version: VERSION,
      status: 'failed', failure_class: /^RIV-PLY-\d{4}$/.test(error.message) ? error.message : 'RIV-PLY-0003' }));
    process.exitCode = 2;
  }
}
if (require.main === module) main();
module.exports = { COMPOSER_SELECTOR, FIXED_ACTION, OPERATION, READINESS, WAKE_TEXT, loadConfig, selectExactTarget, statusSnapshot, validate, verified };
