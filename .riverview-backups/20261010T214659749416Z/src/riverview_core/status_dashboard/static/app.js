// Riverview~ controlled asset; component STEWARD-DASHBOARD.
// Revision: 1.0.0
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const state = {token: sessionStorage.getItem("rv.dashboard.token") || "", status: null,
    assignments: [], events: [], attention: [], assignmentCursor: null, eventCursor: 0, olderEventCursor: null,
    recentErrors: [], navSamples: [], lastFetch: 0, timer: null};
  const esc = (value) => String(value ?? "—").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const human = (value) => String(value || "unknown").replaceAll("_", " ").replaceAll(".", " · ");
  const api = async (path, timeout = 2600) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(path, {headers: {Authorization: `Bearer ${state.token}`, Accept: "application/json"},
        cache: "no-store", credentials: "omit", signal: controller.signal});
      if (!response.ok) throw new Error(`http_${response.status}`);
      return await response.json();
    } catch (error) {
      state.recentErrors.push({at: new Date().toISOString(), code: String(error.message || "request_failed").slice(0, 48), route: path.split("?")[0]});
      state.recentErrors = state.recentErrors.slice(-20);
      throw error;
    } finally { clearTimeout(timer); }
  };
  const toast = (text) => { $("toast").textContent = text; $("toast").classList.add("show"); setTimeout(() => $("toast").classList.remove("show"), 2300); };
  const when = (value) => { if (!value) return "time unavailable"; const d = new Date(value); return Number.isNaN(d.valueOf()) ? "time unavailable" : d.toLocaleString(); };
  const stateClass = (v) => `status-${String(v || "unknown").toLowerCase().replace(/[^a-z0-9_-]/g, "_")}`;
  const item = (label, value) => `<div class="detail-item"><div class="detail-label">${esc(label)}</div><div class="detail-value">${esc(value)}</div></div>`;
  const noData = (text) => `<div class="row"><span class="row-meta">${esc(text)}</span></div>`;
  function renderStatus(s) {
    state.status = s; state.lastFetch = performance.now();
    const health = s.projection_status || "unavailable";
    $("rail-health").textContent = human(health);
    $("pulse-dot").className = `pulse-dot ${stateClass(health).replace("status-", "")}`;
    $("freshness").textContent = `${human(s.freshness)} · ${when(s.observed_at)}`;
    $("hero-status").textContent = ({healthy:"Connected to authoritative state", not_initialized:"Ledger not initialized", unavailable:"Source unavailable"})[health] || human(health);
    $("hero-copy").textContent = health === "healthy" ? "Live database projection. CME and worker freshness are reported separately." :
      health === "not_initialized" ? "PostgreSQL is reachable, but the required ledger tables are not present in this schema." :
      `The projection cannot confirm current state${s.unavailable_reason ? ` (${s.unavailable_reason})` : ""}. Last-known state is not shown as healthy.`;
    $("hero-badge").textContent = health.toUpperCase().slice(0, 12);
    $("source-name").textContent = `${s.source?.database || "PostgreSQL"} / ${s.source?.schema || "schema unknown"}`;
    $("source-commit").textContent = `Source ${s.source?.source_commit || "unknown"} · ${s.source?.deployment_id || "unidentified deployment"}`;
    const assignments = Object.entries(s.assignment_counts || {}).map(([k,v]) => `${human(k)} ${v}`).join(" · ") || "No rows observed";
    $("metrics").innerHTML = [
      ["Assignments", String(s.assignments_total ?? "—"), assignments],
      ["Event cursor", s.event_cursor ?? "—", "Institution events only"],
      ["CME monitor", human(s.cme?.status), s.cme?.heartbeat_age_seconds == null ? "Heartbeat not observed" : `${s.cme.heartbeat_age_seconds}s since heartbeat`],
      ["Workers", human(s.workers?.status), `${s.workers?.active_workers ?? "—"} active · ${s.workers?.active_leases ?? "—"} leases`]
    ].map(([label,value,sub]) => `<article class="metric"><div class="metric-label">${esc(label)}</div><div class="metric-value ${stateClass(value)}">${esc(value)}</div><div class="metric-sub">${esc(sub)}</div></article>`).join("");
    const cme = s.cme || {};
    $("cme-pill").className = `pill ${stateClass(cme.status || "unknown").replace("status-", "")}`;
    $("cme-pill").textContent = human(cme.status || "unknown").toUpperCase();
    $("cme-detail").innerHTML = item("Service", cme.service_id || "cme.monitor.v1") +
      item("Instance", cme.instance_id || "not reported") + item("Last scan", when(cme.last_scan_at)) +
      item("Last error", cme.last_error_type || "none reported");
    const attention = state.attention;
    $("attention-list").innerHTML = attention.length ? attention.slice(0,4).map((a) => `<div class="row"><span class="row-main">${esc(human(a.event_type))}</span><span class="row-meta">${esc(a.assignment_id || "service")}</span><span class="row-meta">${esc(when(a.recorded_at))}</span></div>`).join("") : noData(cme.status === "not_initialized" ? "CME tables are not installed in this schema." : "No attention records in the observed page.");
  }
  function renderAssignments(target, items) {
    const host = $(target);
    host.innerHTML = items.length ? items.map((a) => `<button class="row row-button" data-assignment="${esc(a.assignment_id)}"><span class="row-main">${esc(a.assignment_id)}</span><span class="status-text ${stateClass(a.state)}">${esc(human(a.state))}</span><span class="row-meta">${esc(a.workflow_id)} / ${esc(a.workflow_step)}</span><span class="row-meta">${esc(a.owner)}</span><span class="row-meta">Progress event ${esc(a.last_meaningful_progress?.event_seq ?? "not observed")}</span><span class="row-meta">${esc(when(a.last_meaningful_progress?.recorded_at))}</span></button>`).join("") : noData("No visible institutional assignments were returned.");
    host.querySelectorAll("[data-assignment]").forEach((button) => button.addEventListener("click", () => loadDetail(button.dataset.assignment)));
  }
  function eventRows(events) {
    return events.length ? events.map((e) => `<article class="event-card"><div class="event-head"><span class="event-type">${esc(human(e.event_type))}</span><time class="event-time">${esc(when(e.recorded_at))}</time></div><div class="event-ids"><span>seq ${esc(e.seq)}</span><span>event ${esc(e.event_id)}</span>${e.assignment_id ? `<button data-assignment="${esc(e.assignment_id)}">assignment ${esc(e.assignment_id)}</button>` : ""}<span>corr ${esc(e.correlation_id)}</span><span>cause ${esc(e.causation_id || "root")}</span></div></article>`).join("") : noData("No institution events in this page.");
  }
  function bindEventLinks() { document.querySelectorAll("#event-list [data-assignment],#overview-events [data-assignment]").forEach((b) => b.addEventListener("click", () => loadDetail(b.dataset.assignment))); }
  async function refreshStatus() {
    if (!state.token) return;
    $("request-state").textContent = "Refreshing projection";
    try {
      const result = await api("/api/v1/status");
      const attention = await api("/api/v1/attention?limit=10").catch(() => ({items:[]}));
      state.attention = attention.items || [];
      renderStatus(result);
      $("request-state").textContent = "Projection current";
      if (result.projection_status === "unavailable") recordUiError("source_unavailable", "/api/v1/status");
    } catch (error) { $("request-state").textContent = `Refresh failed: ${error.message}`; $("freshness").textContent = "Source unavailable · last-known data not marked current"; }
  }
  async function loadAssignments(append = false) {
    try {
      const path = `/api/v1/assignments?limit=25${append && state.assignmentCursor ? `&after=${encodeURIComponent(state.assignmentCursor)}` : ""}`;
      const page = await api(path);
      state.assignments = append ? state.assignments.concat(page.items || []) : (page.items || []);
      state.assignmentCursor = page.next_cursor;
      renderAssignments("assignment-list", state.assignments);
      renderAssignments("overview-assignments", state.assignments.slice(0,5));
      $("assignment-page-note").textContent = `${state.assignments.length} observed · page limit 25`;
      $("more-assignments").hidden = !state.assignmentCursor;
    } catch (error) { $("assignment-list").innerHTML = noData(`Assignments unavailable (${error.message}).`); $("overview-assignments").innerHTML = noData(`Unavailable (${error.message}).`); }
  }
  async function loadEvents(append = false) {
    try {
      const after = append ? state.eventCursor : null;
      const page = await api(`/api/v1/events?${append ? `after_seq=${after}&` : ""}limit=25`);
      state.events = append ? state.events.concat(page.items || []) : (page.items || []);
      state.eventCursor = page.next_cursor || (state.events.at(-1)?.seq || state.eventCursor);
      state.olderEventCursor = append ? state.olderEventCursor : page.older_cursor;
      $("event-cursor").textContent = `Observed through sequence ${state.status?.event_cursor ?? state.eventCursor}`;
      $("event-list").innerHTML = eventRows(state.events);
      $("overview-events").innerHTML = eventRows(state.events.slice(-5).reverse());
      $("more-events").hidden = !state.olderEventCursor;
      bindEventLinks();
    } catch (error) { $("event-list").innerHTML = noData(`Event source unavailable (${error.message}).`); $("overview-events").innerHTML = noData(`Unavailable (${error.message}).`); }
  }
  async function loadOlderEvents() {
    if (!state.olderEventCursor) return;
    try {
      const page = await api(`/api/v1/events?before_seq=${state.olderEventCursor}&limit=25`);
      state.events = (page.items || []).concat(state.events);
      state.olderEventCursor = page.older_cursor;
      $("event-list").innerHTML = eventRows(state.events);
      $("more-events").hidden = !state.olderEventCursor;
      bindEventLinks();
    } catch (error) { recordUiError(error.message,"/api/v1/events"); toast(`Older events unavailable: ${error.message}`); }
  }
  async function loadDetail(id) {
    $("assignment-detail").hidden = false; $("assignment-detail").innerHTML = "<span class='muted'>Loading bounded assignment evidence…</span>";
    try {
      const detail = await api(`/api/v1/assignments/${encodeURIComponent(id)}`);
      const a = detail.assignment;
      $("assignment-detail").innerHTML = `<div class="eyebrow">ASSIGNMENT DETAIL · READ ONLY</div><h3>${esc(a.assignment_id)} <span class="status-text ${stateClass(a.state)}">${esc(human(a.state))}</span></h3><div class="detail-stack">${item("Workflow", `${a.workflow_id} / ${a.workflow_step}`)}${item("Owner", a.owner)}${item("Correlation", a.correlation_id)}${item("Version", a.version)}${item("Observed update", when(a.updated_at))}${item("Diagnostic reference", detail.diagnostic_ref)}</div><h4>Independent verification</h4>${detail.verifications.length ? detail.verifications.map((v) => `<div class="row"><span>${esc(v.decision)}</span><span>${esc(v.verifier_id)} ${esc(v.verifier_revision)}</span><span class="row-meta">${esc(v.evidence_count)} evidence references · ${esc(when(v.recorded_at))}</span></div>`).join("") : noData("No verification record was returned.")}<h4>Worker attempts</h4>${detail.attempts.length ? detail.attempts.map((x) => `<div class="row"><span>${esc(x.worker_id)}</span><span>${esc(x.status)}</span><span class="row-meta">${esc(x.capability)} · lease ${esc(x.lease_generation)} · ${esc(when(x.started_at))}</span></div>`).join("") : noData("No attempt rows returned.")}<h4>Recent lifecycle events</h4>${eventRows(detail.events)}</div>`;
    } catch (error) { $("assignment-detail").innerHTML = `<div class="inline-error">Diagnostic detail unavailable (${esc(error.message)}).</div>`; }
  }
  function recordUiError(code, route) { state.recentErrors.push({at:new Date().toISOString(),code:String(code).slice(0,48),route:String(route).split("?")[0].slice(0,96)}); state.recentErrors=state.recentErrors.slice(-20); }
  function showWorkspace() { $("login").hidden = true; $("workspace").hidden = false; }
  async function connect(token) {
    state.token = token;
    try {
      const s = await api("/api/v1/status");
      if (s.projection_status === "unavailable") throw new Error("source_unavailable");
      sessionStorage.setItem("rv.dashboard.token", token);
      $("login-error").textContent = ""; showWorkspace(); renderStatus(s);
      await Promise.all([loadAssignments(), loadEvents()]);
      await refreshStatus();
    state.timer = setInterval(() => { refreshStatus(); if (document.visibilityState === "visible") { loadEvents(true); } }, 5000);
    } catch (error) { state.token = ""; $("login-error").textContent = `Connection failed: ${error.message}. Check the source and credential.`; }
  }
  function navigate(name) {
    const start = performance.now();
    const view = ["overview","assignments","activity"].includes(name) ? name : "overview";
    document.querySelectorAll(".view").forEach((node) => { const active = node.id === `view-${view}`; node.hidden = !active; node.classList.toggle("active", active); });
    document.querySelectorAll(".nav-item").forEach((node) => node.classList.toggle("selected", node.dataset.view === view));
    $("page-title").textContent = ({overview:"Operations overview",assignments:"Assignments",activity:"Activity"})[view];
    history.replaceState(null,"",`#${view}`);
    const duration = performance.now() - start;
    state.navSamples.push({view,ms:duration}); state.navSamples=state.navSamples.slice(-100);
    document.body.dataset.lastNavigationMs = duration.toFixed(2);
    if (state.lastFetch && performance.now() - state.lastFetch > 10000) refreshStatus();
    if (view === "assignments" && !state.assignments.length) loadAssignments();
    if (view === "activity" && !state.events.length) loadEvents();
  }
  document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => navigate(b.dataset.view)));
  document.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => navigate(b.dataset.go)));
  $("login-form").addEventListener("submit", (event) => { event.preventDefault(); connect($("token").value.trim()); $("token").value = ""; });
  $("refresh").addEventListener("click", () => { refreshStatus(); loadAssignments(); loadEvents(); });
  $("auth-open").addEventListener("click", () => { sessionStorage.removeItem("rv.dashboard.token"); state.token=""; if(state.timer)clearInterval(state.timer); $("workspace").hidden=true; $("login").hidden=false; $("token").focus(); });
  $("more-assignments").addEventListener("click", () => loadAssignments(true));
  $("more-events").addEventListener("click", () => loadOlderEvents());
  $("snapshot").addEventListener("click", async () => {
    try {
      const bundle = await api("/api/v1/snapshot");
      bundle.browser = {captured_at:new Date().toISOString(), navigation_samples:state.navSamples.slice(-100),
        recent_ui_errors:state.recentErrors.slice(-20), active_view:location.hash.slice(1) || "overview"};
      const text = JSON.stringify(bundle,null,2);
      if (text.length > 128 * 1024) throw new Error("snapshot_bound_exceeded");
      const url=URL.createObjectURL(new Blob([text],{type:"application/json"})); const a=document.createElement("a");
      a.href=url;a.download=`riverview-status-${new Date().toISOString().replaceAll(":","-")}.json`;a.click();URL.revokeObjectURL(url);toast("Redacted bounded snapshot downloaded.");
    } catch(error) { recordUiError(error.message,"/api/v1/snapshot");toast(`Snapshot unavailable: ${error.message}`); }
  });
  const existing = state.token;
  if (existing) connect(existing); else { $("login").hidden = false; $("token").focus(); }
  const initialHash = location.hash.slice(1);
  if (initialHash) navigate(initialHash);
})();
