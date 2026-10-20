/*
Riverview~ Controlled Source
File: scripts/verify_v2_workspace_mobile.cjs
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.5
Purpose: Verify responsive behavior at an actual 390 by 844 CSS-pixel viewport
Execution Model: Request-driven acceptance utility; starts and stops its own Chrome process
Observability: JSON stdout containing viewport fit and browser errors; no credentials or remote requests
Dependencies: Node.js, Google Chrome, system-installed ws module, local V2 preview
Inputs/Outputs: --url; writes no files; drives only the specified local preview
Authority: Browser test only; no production API, persistent storage, or state mutation
Changed: 2026-10-20 UTC | RV-WEB-V2-USABILITY-001 | Keep mobile sidebar state controls visible and verify accessible navigation name
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

const baseUrl = process.argv.includes("--url") ? process.argv[process.argv.indexOf("--url") + 1] : "http://127.0.0.1:8877/";
if (!/^http:\/\/127\.0\.0\.1:\d+\//.test(baseUrl)) throw new Error("preview_url_must_be_loopback");
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
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await send("Page.navigate", { url: baseUrl });
    for (let i = 0; i < 100; i += 1) {
      if (await evaluate("document.readyState === 'complete' && !!window.RIVERVIEW_V2_FIXTURES")) break;
      await sleep(100);
    }
    const samples = [];
    for (const view of ["residents", "work", "resources", "knowledge", "overview"]) {
      samples.push(await evaluate(`(()=>{const b=document.querySelector('[data-view="${view}"]');const t=performance.now();b.click();return performance.now()-t})()`));
    }
    const result = await evaluate(`(()=>{document.querySelector('[data-resident-id="fixture-resident-02"]').click();document.querySelector('[data-view="work"]').click();const theme=document.querySelector('#theme-select');theme.value='dark';theme.dispatchEvent(new Event('change'));document.querySelector('#left-state').click();document.querySelector('#right-state').click();const checked={width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,menuDisplay:getComputedStyle(document.querySelector('#mobile-menu')).display,stateControlsVisible:getComputedStyle(document.querySelector('#left-state')).display!=='none'&&getComputedStyle(document.querySelector('#right-state')).display!=='none',navName:document.querySelector('[data-view="overview"]').getAttribute('aria-label'),resident:document.querySelector('#selected-resident b').textContent,contextRetained:document.querySelector('#selected-resident b').textContent==='Resident fixture 02',fixtureBanner:document.querySelector('.preview-banner').innerText,disabledButtons:[...document.querySelectorAll('button:disabled')].length,theme:document.documentElement.dataset.theme,leftState:document.querySelector('.app-shell').dataset.leftState,rightState:document.querySelector('.app-shell').dataset.rightState,snapshotDisabled:document.querySelector('#snapshot-action').disabled};document.querySelector('#left-restore').click();document.querySelector('#right-restore').click();return checked})()`);
    const sorted = [...samples].sort((a, b) => a - b);
    const report = { chrome: debuggerVersion.Browser, viewport: result,
      navigation_call_ms: { count: samples.length, median: Number(sorted[Math.floor(sorted.length / 2)].toFixed(3)), max: Number(Math.max(...samples).toFixed(3)) },
      browser_errors: errors };
    process.stdout.write(`${JSON.stringify(report)}\n`);
    if (result.width !== 390 || result.height !== 844 || result.overflow || result.menuDisplay === "none" || !result.stateControlsVisible || result.navName !== "Overview" || !result.contextRetained || result.disabledButtons < 2 || result.theme !== "dark" || result.leftState !== "compact" || result.rightState !== "compact" || !result.snapshotDisabled || errors.length) throw new Error("mobile_viewport_check_failed");
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
