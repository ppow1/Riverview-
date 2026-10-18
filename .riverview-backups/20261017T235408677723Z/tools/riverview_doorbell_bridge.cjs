// RIVERVIEW~ CONTROLLED SOURCE
// File: tools/riverview_doorbell_bridge.cjs
// File Revision: 1.0.0
// Component: CHATGPT-DOORBELL | Revision: 1.0.1
// Purpose: Submit one fixed wake to one exact configured ChatGPT conversation
// Execution Model: Request-driven local CDP operation
// Observability: Metadata-only JSON result and private evidence journal
// Dependencies: Node.js; Chrome/Chromium; native WebSocket or system node-ws package
// Authority: Localhost CDP only; fixed text/action; never reads assistant output
// Changed: 2026-10-17 UTC | RV-C3-DOORBELL-001 | Port proven CDP bridge and preserve exact failure classes
// Contracts: docs/components/CHATGPT_DOORBELL.md
// Tests: tests/test_riverview_doorbell_bridge_node.cjs
// History: Git and .riverview-revisions.json

'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const VERSION = '1.0.0';
const OPERATION = 'ring_riverview_doorbell';
const WAKE_TEXT = 'Riverview doorbell v1: inspect the Riverview MCP mailbox.';
const CONFIG = process.env.RIVERVIEW_DOORBELL_CONFIG || path.join(os.homedir(), '.config', 'riverview', 'doorbell.json');
const RUNTIME_ROOT = process.env.RIVERVIEW_RUNTIME_ROOT || path.join(os.homedir(), '.local', 'state', 'riverview');
const JOURNAL = path.join(RUNTIME_ROOT, 'doorbell', 'diagnostics', 'evidence.json');
const CHATGPT_CONVERSATION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function now() { return new Date().toISOString(); }
function targetRef(id) { return `target-sha256:${crypto.createHash('sha256').update(id).digest('hex')}`; }
function loadConfig() {
  const raw = JSON.parse(fs.readFileSync(CONFIG, 'utf8'));
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
    socket.onopen = resolve;
    socket.onerror = () => reject(Error('RIV-PLY-0004'));
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const key = ++id;
    const timer = setTimeout(() => { pending.delete(key); reject(Error('RIV-PLY-0009')); }, timeout);
    pending.set(key, { resolve, reject, timer });
    socket.send(JSON.stringify({ id: key, method, params }));
  });
  return { socket, opened, call };
}

const READINESS = `(()=>{const b=document.body?.innerText||'';const blocked=/log in|sign in|verify you are human|captcha|something went wrong/i.test(b);const e=document.querySelector('#prompt-textarea[contenteditable="true"],div[contenteditable="true"][aria-label="Chat with ChatGPT"]');const r=e?.getBoundingClientRect?.();return {authenticated:!blocked,composer:!!e&&!!r&&r.width>0&&r.height>0&&!e.disabled};})()`;
const FIXED_ACTION = `(async()=>{const e=document.querySelector('#prompt-textarea[contenteditable="true"],div[contenteditable="true"][aria-label="Chat with ChatGPT"]');if(!e)return {failure_class:'RIV-PLY-0007'};e.focus();e.replaceChildren();const p=document.createElement('p');p.textContent=${JSON.stringify(WAKE_TEXT)};e.appendChild(p);e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:${JSON.stringify(WAKE_TEXT)}}));const b=document.querySelector('button[data-testid="send-button"],button[aria-label="Send prompt"],button[aria-label="Send message"]');const enabled=!!b&&!b.disabled&&b.getAttribute('aria-disabled')!=='true';if(!enabled)return {failure_class:'RIV-PLY-0008',composer_populated:true,send_control_found:!!b,send_control_enabled:false};b.click();await new Promise(resolve=>setTimeout(resolve,750));const remaining=(e.innerText||e.textContent||'').trim().length;return {submitted:true,composer_populated:true,send_control_found:true,send_control_enabled:true,click_invoked:true,composer_cleared:remaining===0};})()`;
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
    bridge_version: VERSION, designated_target_ref: targetRef(config.conversation_id),
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
    fixed_action_available: true, ready: false };
  try {
    const config = loadConfig();
    out.designated_target_configured = true;
    out.browser_runtime = fs.existsSync(config.browser_executable);
    const target = await exactTarget(config);
    out.cdp_available = true;
    out.exact_target_resolvable = !!target;
    const connection = connect(target, 5000);
    await connection.opened;
    const probe = await connection.call('Runtime.evaluate', { returnByValue: true, expression: READINESS });
    out.authenticated_session = probe?.result?.value?.authenticated === true && probe?.result?.value?.composer === true;
    connection.socket.close();
  } catch { /* bounded metadata-only preflight */ }
  out.ready = out.browser_runtime && out.cdp_available && out.authenticated_session &&
    out.designated_target_configured && out.exact_target_resolvable;
  return out;
}
async function ring(input) {
  validate(input);
  const started = now();
  const config = loadConfig();
  input.started_at = started;
  const key = `${input.request_id}:${input.correlation_id}`;
  const journal = readJournal();
  if (journal[key]?.status === 'succeeded' && journal[key]?.submit_verified === true) {
    return { ...journal[key], status: 'already_succeeded' };
  }
  const target = await exactTarget(config);
  const connection = connect(target, input.timeout_seconds * 1000);
  await connection.opened;
  const probe = await connection.call('Runtime.evaluate', { returnByValue: true, expression: READINESS });
  if (!probe?.result?.value?.authenticated) throw Error('RIV-PLY-0004');
  if (!probe?.result?.value?.composer) throw Error('RIV-PLY-0007');
  const action = await connection.call('Runtime.evaluate', { awaitPromise: true, returnByValue: true, expression: FIXED_ACTION });
  connection.socket.close();
  if (!verified(action?.result?.value)) throw Error(action?.result?.value?.failure_class || 'RIV-PLY-0014');
  const output = result(input, 'succeeded', null, `riverview://doorbell/${crypto.randomUUID()}`, config, true);
  journal[key] = output;
  writeJournal(journal);
  return output;
}
async function main() {
  try {
    if (process.argv.includes('--preflight')) { console.log(JSON.stringify(await preflight())); return; }
    if (!process.argv.includes('--ring')) throw Error('RIV-PLY-0002');
    let text = '';
    for await (const chunk of process.stdin) text += chunk;
    console.log(JSON.stringify(await ring(JSON.parse(text))));
  } catch (error) {
    console.log(JSON.stringify({ operation: OPERATION, bridge_version: VERSION,
      status: 'failed', failure_class: /^RIV-PLY-\d{4}$/.test(error.message) ? error.message : 'RIV-PLY-0003' }));
    process.exitCode = 2;
  }
}
if (require.main === module) main();
module.exports = { FIXED_ACTION, OPERATION, WAKE_TEXT, loadConfig, selectExactTarget, validate, verified };
