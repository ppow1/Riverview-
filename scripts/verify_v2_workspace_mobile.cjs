/*
Riverview~ Controlled Source
File: scripts/verify_v2_workspace_mobile.cjs
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.8
Purpose: Verify V2 workspace navigation, Communications Activity honesty, and desktop/mobile Chrome layout
Execution Model: Request-driven acceptance utility; starts and stops its own Chrome process
Observability: JSON stdout containing viewport fit and browser errors; no credentials or remote requests
Dependencies: Node.js, Google Chrome, system-installed ws module, local V2 preview
Inputs/Outputs: --url; writes no files; drives only the specified local preview
Authority: Browser test only; no production API, persistent storage, or state mutation
Changed: 2026-10-21 UTC | RV-WEB-V2-COMMS-ACTIVITY-001 | Verify Communications state, null counters, and no unauthenticated feed request
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: scripts/verify_v2_workspace_mobile.cjs
History: Git and revision/backup manifest
*/
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const net = require("net");
const { spawn } = require("child_process");
const WebSocket = require("ws");

const arg = (name, fallback) => process.argv.includes(name) ? process.argv[process.argv.indexOf(name) + 1] : fallback;
const baseUrl = arg("--url", "http://127.0.0.1:8877/");
const width = Number(arg("--width", "390"));
const height = Number(arg("--height", "844"));
if (!/^http:\/\/127\.0\.0\.1:\d+\//.test(baseUrl)) throw new Error("preview_url_must_be_loopback");
if (!Number.isInteger(width) || !Number.isInteger(height) || width < 320 || height < 500) throw new Error("invalid_viewport");
let profile;
let browserProcess;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function json(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`chrome_debug_http_${response.status}`);
  return response.json();
}

async function main() {
  const reservation = net.createServer();
  await new Promise((resolve, reject) => { reservation.once("error", reject); reservation.listen(0, "127.0.0.1", resolve); });
  const debugPort = reservation.address().port;
  await new Promise((resolve) => reservation.close(resolve));
  profile = fs.mkdtempSync(path.join(os.tmpdir(), "rv-v2-chrome-"));
  const browser = spawn("google-chrome", ["--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore" });
  browserProcess = browser;
  let debuggerVersion;
  for (let i = 0; i < 100; i += 1) {
    if (browser.exitCode !== null) throw new Error("chrome_stopped_before_ready");
    try { debuggerVersion = await json(`http://127.0.0.1:${debugPort}/json/version`); break; }
    catch (_) { await sleep(100); }
  }
  if (!debuggerVersion) throw new Error("chrome_debug_port_timeout");
  const target = await json(`http://127.0.0.1:${debugPort}/json/new?about:blank`, { method: "PUT" });
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let nextId = 0;
  const pending = new Map();
  ws.on("message", (data) => {
    const message = JSON.parse(data.toString());
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message)); else resolve(message.result);
    }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error("browser_evaluation_failed");
    return result.result.value;
  };
  const errors = [];
  ws.on("message", (data) => {
    const message = JSON.parse(data.toString());
    if (message.method === "Runtime.exceptionThrown") errors.push("uncaught_exception");
    if (message.method === "Log.entryAdded" && message.params.entry.level === "error") errors.push({ level: "error", message: message.params.entry.text.slice(0, 180), url: message.params.entry.url });
  });
  try {
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Log.enable");
    await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width <= 760 });
    await send("Page.navigate", { url: baseUrl });
    for (let i = 0; i < 100; i += 1) {
      if (await evaluate("document.readyState === 'complete' && !!window.RIVERVIEW_V2_FIXTURES")) break;
      await sleep(100);
    }
    const result = await evaluate(`(()=>{
      const checks={};
      checks.initialView=document.querySelector('#workspace-main').dataset.currentView;
      checks.overviewTitle=document.querySelector('#page-title').textContent;
      document.querySelector('[data-view="communications"]').click();
      checks.communications={view:document.querySelector('#workspace-main').dataset.currentView,state:document.querySelector('#communications-source-state').textContent.trim(),outbound:document.querySelector('[data-count="outbound"]').textContent.trim(),inbound:document.querySelector('[data-count="inbound"]').textContent.trim(),empty:document.querySelector('#communications-ledger-body').children.length===0,sourceMessage:document.querySelector('#communications-ledger-empty').textContent};
      document.querySelector('#communications-search').value='test';document.querySelector('#communications-search').dispatchEvent(new Event('input'));
      document.querySelector('#communications-refresh').click();
      checks.communications.refreshMessage=document.querySelector('#communications-refresh-status').textContent;
      checks.communications.sourceDetail=document.querySelector('#communications-source-detail').textContent;
      checks.communications.noFeedRequest=!performance.getEntriesByType('resource').some(entry=>entry.name.includes('/api/v1/comms')||entry.name.includes('/api/v1/events'));
      document.querySelector('[data-view="overview"]').click();
      document.querySelector('[data-view="residents"]').click();
      document.querySelector('[data-resident-id="grace-preview"]').click();
      const chat=document.querySelector('#grace-chat-root');
      const box=chat.getBoundingClientRect();
      const context=document.querySelector('#right-sidebar');
      const composer=document.querySelector('#grace-chat-form');
      checks.graceView={view:document.querySelector('#workspace-main').dataset.currentView,title:document.querySelector('#page-title').textContent,visible:!document.querySelector('#grace-workspace').hidden,insideCenter:document.querySelector('#workspace-main').contains(chat),insideContext:context.contains(chat),width:Math.round(box.width),height:Math.round(box.height),history:!!document.querySelector('#grace-chat-history'),composer:!!composer,placeholder:composer.querySelector('textarea').getAttribute('placeholder'),state:chat.dataset.state};
      checks.selectedResident=document.querySelector('#selected-resident b').textContent;
      document.querySelector('[data-view="overview"]').click();
      checks.overviewRestored=document.querySelector('#workspace-main').dataset.currentView==='overview'&&!document.querySelector('#overview-content').hidden&&document.querySelector('#grace-workspace').hidden;
      document.querySelector('[data-view="residents"]').click();
      document.querySelector('[data-resident-id="fixture-resident-02"]').click();
      checks.fixtureDoesNotOpenLiveChat=document.querySelector('#workspace-main').dataset.currentView==='residents'&&document.querySelector('#grace-workspace').hidden;
      checks.fixtureStatus=document.querySelector('[data-resident-id="fixture-resident-02"] .item-meta').textContent;
      document.querySelector('[data-resident-id="grace-preview"]').click();
      const snapshot=document.querySelector('#snapshot-action');
      const integration={label:snapshot.textContent.trim(),status:document.querySelector('#snapshot-status').textContent.trim(),chatHistoryLabel:document.querySelector('#grace-chat-history').getAttribute('aria-label'),chatStatus:document.querySelector('#grace-chat-state').textContent.trim()};
      const theme=document.querySelector('#theme-select');theme.value='dark';theme.dispatchEvent(new Event('change'));
      document.querySelector('#left-state').click();document.querySelector('#right-state').click();
      const app=document.querySelector('.app-shell');
      const states={left:app.dataset.leftState,right:app.dataset.rightState};
      document.querySelector('#left-restore').click();document.querySelector('#right-restore').click();
      const bounds=chat.getBoundingClientRect();
      const viewport={width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,menuDisplay:getComputedStyle(document.querySelector('#mobile-menu')).display,stateControlsVisible:getComputedStyle(document.querySelector('#left-state')).display!=='none'&&getComputedStyle(document.querySelector('#right-state')).display!=='none',chatWidth:Math.round(bounds.width),chatLeft:Math.round(bounds.left),chatRight:Math.round(bounds.right)};
      return {checks,integration,states,viewport};
    })()`);
    const report = { chrome: debuggerVersion.Browser, url: baseUrl, viewport: result.viewport, checks: result.checks, integration: result.integration, sidebar_states: result.states, browser_errors: errors };
    process.stdout.write(`${JSON.stringify(report)}\n`);
    const minimumChatWidth = width <= 760 ? 300 : 600;
    if (result.checks.initialView !== "overview" || result.checks.overviewTitle !== "Workspace overview" || result.checks.communications.view !== "communications" || result.checks.communications.state !== "UNVERIFIED" || result.checks.communications.outbound !== "Unavailable" || result.checks.communications.inbound !== "Unavailable" || !result.checks.communications.empty || !result.checks.communications.sourceMessage.includes("not evidence of zero traffic") || !result.checks.communications.refreshMessage.includes("No network request was sent") || !result.checks.communications.sourceDetail.includes("No activity request was sent") || !result.checks.communications.noFeedRequest || result.checks.graceView.view !== "grace" || result.checks.graceView.title !== "Grace conversation" || !result.checks.graceView.visible || !result.checks.graceView.insideCenter || result.checks.graceView.insideContext || !result.checks.graceView.history || !result.checks.graceView.composer || result.checks.selectedResident !== "Grace" || !result.checks.overviewRestored || !result.checks.fixtureDoesNotOpenLiveChat || !result.checks.fixtureStatus.includes("Example workspace") || result.integration.label !== "Snapshot" || result.integration.chatHistoryLabel !== "Persisted messages with Grace" || result.integration.chatStatus !== "Open the LAN HTTPS Dashboard at /v2/ to use authenticated Grace chat" || result.viewport.width !== width || result.viewport.height !== height || result.viewport.overflow || result.viewport.chatWidth < minimumChatWidth || (width <= 760 ? result.viewport.menuDisplay === "none" : result.viewport.menuDisplay !== "none") || !result.viewport.stateControlsVisible || result.states.left !== "compact" || result.states.right !== "compact" || errors.length) throw new Error("grace_workspace_browser_check_failed");
  } finally {
    ws.close();
  }
}

main().catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }).finally(async () => {
  if (browserProcess && browserProcess.exitCode === null) {
    browserProcess.kill("SIGTERM");
    await new Promise((resolve) => browserProcess.once("exit", resolve));
  }
  if (profile) {
    try { fs.rmSync(profile, { recursive: true, force: true, maxRetries: 8, retryDelay: 100 }); } catch (_) {}
  }
});
