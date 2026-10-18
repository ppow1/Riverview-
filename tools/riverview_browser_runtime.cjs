// RIVERVIEW~ CONTROLLED SOURCE
// File: tools/riverview_browser_runtime.cjs
// File Revision: 1.0.1
// Component: CHATGPT-DOORBELL | Revision: 1.0.1
// Purpose: Supervise the configured Riverview Chrome profile and expose owner-local runtime status
// Inputs/Outputs: Private config and graphical session / bounded status JSON and Chrome lifecycle
// Execution Model: Persistent systemd user service or explicit local start
// Observability: Metadata-only preflight, PID/runtime status, and status.v1 schema
// Dependencies: Node.js; Chrome/Chromium; graphical user session
// Authority: Dedicated profile; localhost CDP; no browser content access
// Changed: 2026-10-18 UTC | RV-C3-DOORBELL-DOD-001 | Add process-safe runtime state to status contract
// Contracts: docs/components/CHATGPT_DOORBELL.md
// Tests: tests/test_riverview_doorbell_bridge_node.cjs
// History: Git and .riverview-revisions.json

'use strict';

const fs = require('node:fs');
const os = require('node:os');
const { spawn } = require('node:child_process');
const path = require('node:path');
const bridge = require('./riverview_doorbell_bridge.cjs');

const XDG_DATA = process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share');
const XDG_STATE = process.env.XDG_STATE_HOME || path.join(os.homedir(), '.local', 'state');
const PROFILE = process.env.RIVERVIEW_BROWSER_PROFILE || path.join(XDG_DATA, 'riverview', 'browser', 'profile');
const STATE = path.join(XDG_STATE, 'riverview', 'browser');
const PID_FILE = path.join(STATE, 'runtime.json');

async function cdpAvailable(config) {
  try {
    const response = await fetch(`http://127.0.0.1:${config.cdp_port}/json/version`);
    return response.ok;
  } catch { return false; }
}
async function preflight(config) {
  return {
    runtime_version: '1.0.0',
    browser_runtime: fs.existsSync(config.browser_executable),
    cdp_available: await cdpAvailable(config),
    cdp_address: '127.0.0.1',
    cdp_port: config.cdp_port,
    dedicated_profile: PROFILE,
  };
}
function launchArgs(config) {
  return [
    `--remote-debugging-port=${config.cdp_port}`,
    '--remote-debugging-address=127.0.0.1',
    `--user-data-dir=${PROFILE}`,
    '--no-first-run',
    '--no-default-browser-check',
    `https://chatgpt.com/c/${config.conversation_id}`,
  ];
}
function writeRuntime(pid, config) {
  fs.mkdirSync(STATE, { recursive: true, mode: 0o700 });
  fs.writeFileSync(PID_FILE, JSON.stringify({ pid, cdp_address: '127.0.0.1',
    cdp_port: config.cdp_port, profile: PROFILE, started_at: new Date().toISOString() }) + '\n', { mode: 0o600 });
}
function clearRuntime(pid) {
  try {
    const current = JSON.parse(fs.readFileSync(PID_FILE, 'utf8'));
    if (current.pid === pid) fs.unlinkSync(PID_FILE);
  } catch { /* no state to clear */ }
}
function runtimeInfo() {
  try {
    const value = JSON.parse(fs.readFileSync(PID_FILE, 'utf8'));
    if (!Number.isInteger(value.pid) || value.pid < 1) return { state: 'stale', started_at: null };
    process.kill(value.pid, 0);
    const command = fs.readFileSync(`/proc/${value.pid}/cmdline`, 'utf8').replaceAll('\0', ' ');
    if (!command.includes(`--user-data-dir=${PROFILE}`)) return { state: 'stale', started_at: null };
    return { state: 'running', started_at: value.started_at || null };
  } catch (error) {
    return { state: error.code === 'ENOENT' ? 'not_running' : 'stale', started_at: null };
  }
}
async function serve(config) {
  if (await cdpAvailable(config)) throw Error('RIV-PLY-0015');
  if (!fs.existsSync(config.browser_executable)) throw Error('RIV-PLY-0013');
  fs.mkdirSync(PROFILE, { recursive: true, mode: 0o700 });
  const child = spawn(config.browser_executable, launchArgs(config), { detached: false, stdio: 'ignore' });
  const stopped = new Promise((resolve, reject) => {
    child.once('spawn', () => writeRuntime(child.pid, config));
    child.once('error', () => reject(Error('RIV-PLY-0013')));
    child.once('close', (code, signal) => {
      clearRuntime(child.pid);
      if (signal) resolve({ code: 1, signal });
      else resolve({ code: code ?? 1, signal: null });
    });
  });
  const result = await stopped;
  if (result.code !== 0) throw Error('RIV-PLY-0012');
}
async function start(config) {
  const status = await preflight(config);
  if (status.cdp_available) return { status: 'already_ready', cdp_port: config.cdp_port };
  if (!status.browser_runtime) throw Error('RIV-PLY-0013');
  fs.mkdirSync(PROFILE, { recursive: true, mode: 0o700 });
  const child = spawn(config.browser_executable, launchArgs(config), { detached: true, stdio: 'ignore' });
  writeRuntime(child.pid, config);
  child.unref();
  return { status: 'started', pid: child.pid, cdp_address: '127.0.0.1', cdp_port: config.cdp_port, profile: PROFILE };
}
async function main() {
  if (process.argv.includes('--status')) {
    let config = null;
    try { config = bridge.loadConfig(); } catch { /* status remains machine-readable when config is missing */ }
    const readiness = config ? await preflight(config) : {
      bridge_version: '1.0.2', browser_runtime: false, cdp_available: false,
      authenticated_session: false, designated_target_configured: false, exact_target_resolvable: false,
      fixed_action_available: false, ready: false, failure_class: 'RIV-PLY-0010',
    };
    const status = await bridge.statusSnapshot({
      readiness,
      browser_runtime: config ? fs.existsSync(config.browser_executable) : false,
      cdp_port: config?.cdp_port || null,
      process: runtimeInfo(),
      profile_lock_present: fs.existsSync(path.join(PROFILE, 'SingletonLock')),
    });
    console.log(JSON.stringify(status));
    return;
  }
  let config;
  try { config = bridge.loadConfig(); }
  catch { console.log(JSON.stringify({ ready: false, failure_class: 'RIV-PLY-0010' })); process.exitCode = 2; return; }
  try {
    if (process.argv.includes('--preflight')) { console.log(JSON.stringify(await preflight(config))); return; }
    if (process.argv.includes('--start')) { console.log(JSON.stringify(await start(config))); return; }
    if (process.argv.includes('--serve')) { await serve(config); return; }
    throw Error('RIV-PLY-0012');
  } catch (error) {
    console.log(JSON.stringify({ status: 'failed', failure_class: error.message }));
    process.exitCode = 2;
  }
}
if (require.main === module) main();
module.exports = { launchArgs, preflight, runtimeInfo };
