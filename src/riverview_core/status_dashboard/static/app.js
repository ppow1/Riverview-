// Riverview~ controlled asset; component STEWARD-DASHBOARD.
// Revision: 1.3.1
// Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Add account login and Steward access controls
// Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Use linked Steward account session for exact-grant Grace connection
// Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Add password login, grant decisions and email configuration UI
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const state = {token: sessionStorage.getItem("rv.dashboard.token") || "", accountIdentity: null, status: null,
    assignments: [], events: [], attention: [], attentionStatus: "unknown", workers: [], assignmentCursor: null,
    workerCursor: null, eventCursor: 0, olderEventCursor: null, notifications: [], notificationStatus: "unknown", activeView: "overview",
    objectives: [], recentErrors: [], navSamples: [], lastFetch: 0, timer: null,
    chatConversationId: localStorage.getItem("rv.grace.conversation") || "", chatEvents: [], chatMeta: null, selectedEventId: null, chatInFlight: false, chatDialogReturnFocus: null, chatAuthRejected:false, chatLoading:false};
  const esc = (value) => String(value ?? "—").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const human = (value) => String(value || "unknown").replaceAll("_", " ").replaceAll(".", " · ");
  const api = async (path, timeout = 2600, method = "GET", options = {}) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const headers = {Accept: "application/json"};
      if (state.token && !options.public) headers.Authorization = `Bearer ${state.token}`;
      if (!options.public && !["GET", "HEAD"].includes(method)) {
        const csrf = document.cookie.split(";").map((part) => part.trim())
          .find((part) => part.startsWith("rv_account_csrf="))?.slice("rv_account_csrf=".length);
        if (csrf) headers["X-Riverview-CSRF"] = decodeURIComponent(csrf);
      }
      if (options.authority) headers["X-Riverview-Authority"] = options.authority;
      if (options.body !== undefined) headers["Content-Type"] = "application/json";
      const response = await fetch(path, {method, headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        cache: "no-store", credentials: "same-origin", signal: controller.signal});
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) { const error = new Error(payload.error || `http_${response.status}`); error.payload = payload; throw error; }
      return payload;
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
      ["Workers", human(s.workers?.status), `${s.workers?.healthy_workers ?? 0} healthy · ${s.workers?.stale_workers ?? 0} stale · ${s.workers?.unknown_workers ?? 0} unknown`],
      ["Grace execution", human(s.grace_execution?.status), s.grace_execution?.heartbeat_age_seconds == null ? "No heartbeat observed" : `${s.grace_execution.heartbeat_age_seconds}s since heartbeat · ${s.grace_execution.cycles_completed} cycles`]
    ].map(([label,value,sub]) => `<article class="metric"><div class="metric-label">${esc(label)}</div><div class="metric-value ${stateClass(value)}">${esc(value)}</div><div class="metric-sub">${esc(sub)}</div></article>`).join("");
    const cme = s.cme || {};
    $("cme-pill").className = `pill ${stateClass(cme.status || "unknown").replace("status-", "")}`;
    $("cme-pill").textContent = human(cme.status || "unknown").toUpperCase();
    $("cme-detail").innerHTML = item("Service", cme.service_id || "cme.monitor.v1") +
      item("Instance", cme.instance_id || "not reported") + item("Last scan", when(cme.last_scan_at)) +
      item("Last error", cme.last_error_type || "none reported");
    const attention = state.attention;
    const attentionEmpty = state.attentionStatus === "not_initialized" ? "CME attention relation is not initialized in this schema." :
      state.attentionStatus === "unavailable" ? "Attention source unavailable; current state is not confirmed." :
      "No attention records in the observed page.";
    $("attention-list").innerHTML = attention.length ? attention.slice(0,4).map((a) => `<div class="row"><span class="row-main">${esc(human(a.event_type))}</span><span class="row-meta">${esc(a.assignment_id || "service")}</span><span class="row-meta">${esc(when(a.recorded_at))}</span></div>`).join("") : noData(attentionEmpty);
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
    if (!state.token && !state.accountIdentity) return;
    $("request-state").textContent = "Refreshing projection";
    try {
      const result = await api("/api/v1/status");
      if (result.relations?.cme_monitor_events !== true) {
        state.attention = []; state.attentionStatus = "not_initialized";
      } else {
        const attention = await api("/api/v1/attention?limit=10");
        state.attention = attention.items || []; state.attentionStatus = attention.status || "available";
      }
      renderStatus(result);
      loadWorkers();
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
  function renderWorkers() {
    const host = $("worker-list");
    host.innerHTML = state.workers.length ? state.workers.map((w) => `<div class="row"><span class="row-main">${esc(w.worker_id)}</span><span class="status-text ${stateClass(w.status)}">${esc(human(w.status))}</span><span class="row-meta">${esc(w.active_leases)} active leases · heartbeat ${esc(when(w.last_heartbeat_at))}</span></div>`).join("") : noData("No worker identities are present in this page.");
    $("worker-page-note").textContent = state.workers.length ? `${state.workers.length} observed · page limit 25` : "";
    $("more-workers").hidden = !state.workerCursor;
  }
  function renderNotifications(page) {
    state.notifications = page.items || [];
    state.notificationStatus = page.status || "unavailable";
    const health = page.dispatcher?.status || "not_initialized";
    $("notification-state").textContent = `Source ${human(page.status)} · dispatcher ${human(health)}`;
    const rows = state.notifications.map((n) => {
      const request = n.decision_request_id ? `<div class="row-meta">Decision request ${esc(n.decision_request_id)} · ${esc(n.decision_status || "unknown")}; receipt cannot resolve it.</div>` : "";
      const receipt = n.delivery_status === "delivered" ? `<button class="secondary" data-acknowledge="${esc(n.notification_id)}">Acknowledge receipt</button>` :
        `<span class="status-text status-accepted">${esc(human(n.delivery_status))}</span>`;
      return `<article class="notification-row"><div><strong>${esc(human(n.event_type))}</strong><p>${esc(n.summary)}</p><div class="row-meta">${esc(n.assignment_id || "Service event")} · source ${esc(when(n.source_recorded_at))} · queued ${esc(when(n.created_at))}</div>${request}</div><div class="notification-actions"><span class="status-text ${stateClass(n.delivery_status)}">${esc(human(n.delivery_status))}</span>${receipt}</div></article>`;
    });
    const messages = {not_initialized:"Notification migration is not initialized.", unavailable:"Notification source is unavailable; no delivery is claimed.", available:"No durable notices in this bounded page."};
    $("notification-list").innerHTML = rows.length ? rows.join("") : noData(messages[state.notificationStatus] || "No notification state observed.");
    document.querySelectorAll("[data-delivered]").forEach((button) => button.addEventListener("click", async () => {
      button.disabled = true;
      try { await api(`/api/v1/notifications/${encodeURIComponent(button.dataset.delivered)}/delivered`, 2600, "POST"); await loadNotifications(); }
      catch (error) { button.disabled = false; toast(`Render receipt not recorded: ${error.message}`); }
    }));
    document.querySelectorAll("[data-acknowledge]").forEach((button) => button.addEventListener("click", async () => {
      button.disabled = true;
      try { const receipt = await api(`/api/v1/notifications/${encodeURIComponent(button.dataset.acknowledge)}/acknowledge`, 2600, "POST"); await loadNotifications(); toast(receipt.authority_effect === "none" ? "Receipt recorded; no decision was made." : "Receipt result unavailable."); }
      catch (error) { button.disabled = false; toast(`Receipt not recorded: ${error.message}`); }
    }));
    if (state.activeView === "notifications") requestAnimationFrame(() => {
      if (state.activeView !== "notifications" || document.visibilityState !== "visible") return;
      state.notifications.filter((n) => n.delivery_status === "queued").forEach(async (n) => {
        try { await api(`/api/v1/notifications/${encodeURIComponent(n.notification_id)}/delivered`, 2600, "POST"); await loadNotifications(); }
        catch (_) { /* Keep queued truthful; the next visible refresh may retry. */ }
      });
    });
  }
  async function loadNotifications() {
    if (!state.token && !state.accountIdentity) return;
    try { renderNotifications(await api("/api/v1/notifications?limit=25")); }
    catch (error) { state.notificationStatus = "unavailable"; $("notification-state").textContent = "Notification source unavailable"; $("notification-list").innerHTML = noData(`No delivery is claimed (${error.message}).`); }
  }
  async function loadObjectives() {
    if (!state.token && !state.accountIdentity) return;
    try {
      const page = await api("/api/v1/objectives?limit=25");
      state.objectives = page.items || [];
      $("objective-state").textContent = `Source ${human(page.status)} · ${state.objectives.length} observed`;
      $("objective-list").innerHTML = state.objectives.length ? state.objectives.map((o) =>
        `<article class="row"><div><strong>${esc(o.objective_id)}</strong><div class="row-meta">${esc(o.request)}</div></div><span class="pill ${stateClass(o.status)}">${esc(human(o.status))}</span><span class="row-meta">Assignment ${esc(o.assignment_state || "not dispatched")} · Verification ${esc(o.verification?.decision || "not recorded")} · dispatch failures ${esc(o.dispatch_failures || 0)} · verification failures ${esc(o.verification_failures || 0)}</span>${o.artifact ? `<span class="row-meta">Artifact ${esc(o.artifact.sha256)} · ${esc(o.artifact.reference)}</span>` : ""}<span class="row-meta">Source ${esc(o.source_revision || "unavailable")} · updated ${esc(when(o.updated_at))}</span></article>`).join("") : noData(page.status === "not_initialized" ? "Grace objective migrations are not initialized in this schema." : "No objectives have been recorded.");
    } catch (error) {
      $("objective-state").textContent = "Unavailable";
      $("objective-list").innerHTML = noData(`Objective projection unavailable (${error.message}).`);
    }
  }
  async function loadWorkers(append = false) {
    if (!state.token && !state.accountIdentity) return;
    if (state.status?.workers?.status === "not_initialized") {
      state.workers = []; state.workerCursor = null;
      $("worker-list").innerHTML = noData("Worker registry and lease health are not initialized in this schema.");
      $("worker-page-note").textContent = "Not initialized"; $("more-workers").hidden = true;
      return;
    }
    try {
      const path = `/api/v1/workers?limit=25${append && state.workerCursor ? `&after=${encodeURIComponent(state.workerCursor)}` : ""}`;
      const page = await api(path);
      state.workers = append ? state.workers.concat(page.items || []) : (page.items || []);
      state.workerCursor = page.next_cursor; renderWorkers();
    } catch (error) {
      $("worker-list").innerHTML = noData(`Worker health unavailable (${error.message}).`);
      $("worker-page-note").textContent = "Unavailable"; $("more-workers").hidden = true;
    }
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
  function showWorkspace() {
    $("login").hidden = true; $("workspace").hidden = false;
    const steward = state.accountIdentity?.roles?.includes("steward") === true;
    $("account-nav").hidden = !steward;
    $("account-label").textContent = state.accountIdentity ? `${state.accountIdentity.email} · ${state.accountIdentity.roles.join(", ")}` : "";
    $("sign-out").hidden = !state.accountIdentity;
  }
  async function connect(token) {
    state.token = token;
    state.accountIdentity = null;
    try {
      const s = await api("/api/v1/status");
      if (s.projection_status === "unavailable") throw new Error("source_unavailable");
      sessionStorage.setItem("rv.dashboard.token", token);
      $("login-error").textContent = ""; showWorkspace(); renderStatus(s);
      await Promise.all([loadAssignments(), loadEvents()]);
      await loadObjectives();
      await refreshStatus();
    state.timer = setInterval(() => { refreshStatus(); if (document.visibilityState === "visible") { loadEvents(true); } }, 5000);
    } catch (error) { state.token = ""; $("login-error").textContent = `Connection failed: ${error.message}. Check the source and credential.`; }
  }
  async function accountRequest(path, body) {
    return api(path, 10000, "POST", {body, public:true});
  }
  async function connectAccountSession() {
    try {
      const result = await api("/api/v1/auth/session");
      state.accountIdentity = result.identity;
      state.chatAuthRejected=false;
      showWorkspace();
      await connectAccountWorkspace();
      if(state.pendingEnrollmentId&&state.accountIdentity.roles.includes("steward")) navigate("account");
      else if(state.pendingEnrollmentId) { toast("Steward sign-in is required to review that request."); history.replaceState(null,"",location.pathname+location.search); }
    } catch (_) {
      $("login").hidden = false;
      $("account-email").focus();
    }
  }
  async function connectAccountWorkspace() {
    try {
      const s = await api("/api/v1/status");
      if (s.projection_status === "unavailable") throw new Error("source_unavailable");
      renderStatus(s);
      await Promise.all([loadAssignments(), loadEvents(), loadObjectives(), refreshStatus()]);
      state.timer = setInterval(() => { refreshStatus(); if (document.visibilityState === "visible") loadEvents(true); }, 5000);
    } catch (error) {
      $("request-state").textContent = `Connection failed: ${error.message}`;
    }
  }
  async function loadEnrollments() {
    try {
      const page = await api("/api/v1/account/enrollments?limit=50");
      const items = page.items || [];
      $("enrollment-state").textContent = `${items.length} pending`;
      $("enrollment-list").innerHTML = items.length ? items.map((request) =>
        `<article class="account-row ${request.enrollment_id===state.pendingEnrollmentId?"approval-highlight":""}"><div><strong>${esc(request.email)}</strong><div class="row-meta">Verified ${esc(when(request.email_verified_at))} · requested ${esc(when(request.created_at))}</div><label>Role <select data-approval-role="${esc(request.enrollment_id)}"><option value="viewer">Viewer</option><option value="operator">Operator</option><option value="steward">Steward</option></select></label></div><div class="account-actions"><button class="secondary" data-enroll="${esc(request.enrollment_id)}" data-decision="approve" data-grant="one_time">Approve one-time</button><button class="secondary" data-enroll="${esc(request.enrollment_id)}" data-decision="approve" data-grant="90_days">Approve 90 days</button><button class="secondary" data-enroll="${esc(request.enrollment_id)}" data-decision="approve" data-grant="one_year">Approve one year</button><button class="secondary" data-enroll="${esc(request.enrollment_id)}" data-decision="approve" data-grant="permanent">Approve permanently</button><button class="secondary" data-enroll="${esc(request.enrollment_id)}" data-decision="deny">Deny</button></div></article>`).join("") : noData("No verified requests are pending.");
      document.querySelectorAll("[data-enroll]").forEach((button) => button.addEventListener("click", async () => {
        button.disabled = true;
        try { const selector=document.querySelector(`[data-approval-role="${CSS.escape(button.dataset.enroll)}"]`); await api(`/api/v1/account/enrollments/${encodeURIComponent(button.dataset.enroll)}/decision`, 10000, "POST", {body:{decision:button.dataset.decision,role:selector?.value||"viewer",grant_type:button.dataset.grant||"permanent"}}); await loadEnrollments(); await loadAccounts(); }
        catch (error) { button.disabled = false; toast(`Decision failed: ${error.message}`); }
      }));
    } catch (error) { $("enrollment-state").textContent = "Unavailable"; $("enrollment-list").innerHTML = noData(`Request queue unavailable (${error.message}).`); }
  }
  async function loadAccounts() {
    try {
      const page = await api("/api/v1/account/users?limit=100");
      const items = page.items || [];
      $("account-state").textContent = `${items.length} accounts`;
      $("account-list").innerHTML = items.length ? items.map((account) =>
        `<article class="account-row"><div><strong>${esc(account.email)}</strong><div class="row-meta">${esc(account.roles.join(", ") || "no roles")} · ${account.disabled ? "disabled" : "active"} · ${esc(account.grant_type)}${account.grant_expires_at?` · expires ${esc(when(account.grant_expires_at))}`:""}${account.grant_revoked?" · grant revoked":""}${account.one_time_used?" · one-time session consumed":""}</div></div><div class="account-actions"><button class="secondary" data-account="${esc(account.account_id)}" data-action="${account.disabled ? "enable" : "disable"}">${account.disabled ? "Enable" : "Disable"}</button><button class="secondary" data-account="${esc(account.account_id)}" data-action="sessions">Revoke sessions</button><button class="secondary" data-account="${esc(account.account_id)}" data-action="grant">Revoke access grant</button>${["viewer","operator","steward"].map((role) => `<button class="secondary" data-account="${esc(account.account_id)}" data-action="role" data-role="${role}" data-grant="${!account.roles.includes(role)}">${account.roles.includes(role) ? "Remove " : "Grant "}${role}</button>`).join("")}</div></article>`).join("") : noData("No accounts have been approved.");
      document.querySelectorAll("[data-account]").forEach((button) => button.addEventListener("click", async () => {
        button.disabled = true;
        const id = encodeURIComponent(button.dataset.account);
        try {
          if (button.dataset.action === "role") await api(`/api/v1/account/users/${id}/roles`, 10000, "POST", {body:{role:button.dataset.role,grant:button.dataset.grant === "true"}});
          else if (button.dataset.action === "sessions") await api(`/api/v1/account/users/${id}/sessions`, 10000, "POST", {body:{}});
          else if (button.dataset.action === "grant") await api(`/api/v1/account/users/${id}/grant`, 10000, "POST", {body:{revoked:true}});
          else await api(`/api/v1/account/users/${id}/disable`, 10000, "POST", {body:{disabled:button.dataset.action === "disable"}});
          await loadAccounts();
        } catch (error) { button.disabled = false; toast(`Account update failed: ${error.message}`); }
      }));
    } catch (error) { $("account-state").textContent = "Unavailable"; $("account-list").innerHTML = noData(`Account list unavailable (${error.message}).`); }
  }
  async function loadEmailSettings() {
    try {
      const value=await api("/api/v1/account/email-settings");
      $("email-config-status").textContent=value.configured?`Configured · ${value.delivery_status}${value.last_test_at?` · tested ${when(value.last_test_at)}`:""}`:"Not configured";
      for (const [id,key] of [["smtp-host","smtp_host"],["smtp-port","smtp_port"],["smtp-tls-mode","tls_mode"],["sender-email","sender_email"],["sender-name","sender_name"],["admin-email","admin_email"],["reply-to-email","reply_to_email"],["smtp-username","smtp_username"]]) $(id).value=value[key]??(id==="smtp-port"?587:"");
      $("smtp-password").value=""; $("smtp-password-state").textContent=value.password_configured?" · password stored securely; blank keeps it":" · not configured";
      if(value.last_test_error) $("email-config-status").textContent+=` · ${value.last_test_error}`;
    } catch(error) { $("email-config-status").textContent=`Unavailable (${error.message})`; }
  }
  function navigate(name) {
    const start = performance.now();
    const view = ["overview","assignments","objectives","grace-chat","activity","workflows","notifications","account"].includes(name) ? name : "overview";
    if (view === "account" && !state.accountIdentity?.roles?.includes("steward")) { navigate("overview"); return; }
    state.activeView = view;
    document.querySelectorAll(".view").forEach((node) => { const active = node.id === `view-${view}`; node.hidden = !active; node.classList.toggle("active", active); });
    document.querySelectorAll(".nav-item").forEach((node) => node.classList.toggle("selected", node.dataset.view === view));
    $("page-title").textContent = ({overview:"Operations overview",assignments:"Assignments",objectives:"Grace objectives","grace-chat":"Talk with Grace",activity:"Activity",workflows:"Process workflows",notifications:"Notifications",account:"Account access"})[view];
    history.replaceState(null,"",`#${view}`);
    const duration = performance.now() - start;
    state.navSamples.push({view,ms:duration}); state.navSamples=state.navSamples.slice(-100);
    document.body.dataset.lastNavigationMs = duration.toFixed(2);
    if (state.lastFetch && performance.now() - state.lastFetch > 10000) refreshStatus();
    if (view === "assignments" && !state.assignments.length) loadAssignments();
    if (view === "objectives") loadObjectives();
    if (view === "activity" && !state.events.length) loadEvents();
    if (view === "notifications") loadNotifications();
    if (view === "grace-chat") loadGraceConversation();
    if (view === "account") { loadEnrollments(); loadAccounts(); loadEmailSettings(); }
  }
  document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => navigate(b.dataset.view)));
  document.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => navigate(b.dataset.go)));
  $("login-form").addEventListener("submit", (event) => { event.preventDefault(); connect($("token").value.trim()); $("token").value = ""; });
  $("account-login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = $("account-auth-message"); message.textContent = "Signing in…";
    try { const result=await accountRequest("/api/v1/auth/session",{email:$("account-email").value,password:$("account-password").value}); state.accountIdentity=result.identity; $("account-password").value=""; await connectAccountSession(); }
    catch (error) { $("account-password").value=""; message.textContent=error.message==="not_authorized"?"Email or password is incorrect, or the access grant is inactive.":`Sign-in unavailable (${error.message}).`; }
  });
  $("account-request-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = $("account-auth-message"); message.textContent = "Submitting access request…";
    try { await accountRequest("/api/v1/auth/enrollment", {email:$("request-email").value}); message.textContent = "If the request can be accepted, check email to verify ownership. After verification, the request waits for Steward approval."; }
    catch (error) { message.textContent = error.message === "email_delivery_unavailable" ? "Email delivery is not configured; verification links cannot be sent yet." : `Access request unavailable (${error.message}).`; }
  });
  $("password-reset-request").addEventListener("click",async()=>{
    const message=$("account-auth-message");
    try { await accountRequest("/api/v1/auth/password-reset",{email:$("account-email").value}); message.textContent="If this address has an active account, a password reset link will arrive by email."; }
    catch(error) { message.textContent=`Password recovery unavailable (${error.message}).`; }
  });
  $("verify-enrollment").addEventListener("click", async () => {
    const message = $("account-auth-message"); message.textContent = "Verifying email ownership…";
    try { const result = await accountRequest("/api/v1/auth/enrollment/verify", {challenge_id:$("challenge-id").value.trim(),token:$("challenge-token").value.trim()}); message.textContent = result.status==="pending_steward_review"?"Email verified. Pending Steward Approval. Portal access is unavailable until a Steward approves the request.":`Email verified: ${result.status.replaceAll("_", " ")}.`; $("email-challenge-form").hidden=true; }
    catch (error) { message.textContent = `Verification failed (${error.message}).`; }
  });
  $("verify-bootstrap").addEventListener("click", async () => {
    const message = $("account-auth-message"); message.textContent = "Verifying authorized Steward bootstrap…";
    try { const result = await accountRequest("/api/v1/auth/steward-bootstrap/verify", {challenge_id:$("challenge-id").value.trim(),token:$("challenge-token").value.trim()}); message.textContent = `${result.status.replaceAll("_", " ")}. Set the password from the separate email link before signing in.`; $("email-challenge-form").hidden=true; }
    catch (error) { message.textContent = `Steward verification failed (${error.message}).`; }
  });
  $("set-account-password").addEventListener("click",async()=>{
    const message=$("account-auth-message");message.textContent="Setting password…";
    try { await accountRequest("/api/v1/auth/password",{challenge_id:$("challenge-id").value.trim(),token:$("challenge-token").value.trim(),password:$("new-password").value}); $("new-password").value=""; $("email-challenge-form").hidden=true; message.textContent="Password set. You can now sign in with your email and password."; }
    catch(error) { $("new-password").value="";message.textContent=`Password could not be set (${error.message}).`; }
  });
  $("refresh-enrollments").addEventListener("click", loadEnrollments);
  $("refresh-accounts").addEventListener("click", loadAccounts);
  $("refresh-email-settings").addEventListener("click",loadEmailSettings);
  $("email-settings-form").addEventListener("submit",async(event)=>{
    event.preventDefault();
    const settings={smtp_host:$("smtp-host").value.trim(),smtp_port:Number($("smtp-port").value),tls_mode:$("smtp-tls-mode").value,sender_email:$("sender-email").value.trim(),sender_name:$("sender-name").value.trim(),admin_email:$("admin-email").value.trim(),reply_to_email:$("reply-to-email").value.trim(),smtp_username:$("smtp-username").value.trim(),password:$("smtp-password").value};
    try { const result=await api("/api/v1/account/email-settings",10000,"PUT",{body:settings}); $("smtp-password").value=""; $("email-config-status").textContent=`Saved · ${result.delivery_status}`; await loadEmailSettings(); }
    catch(error) { $("smtp-password").value="";$("email-config-status").textContent=`Save failed (${error.message})`; }
  });
  $("test-email-settings").addEventListener("click",async()=>{
    try { const result=await api("/api/v1/account/email-settings/test",10000,"POST"); $("email-config-status").textContent=result.delivery_status==="sent"?"Test accepted by SMTP relay; confirm mailbox receipt.":`Test failed (${result.error})`; await loadEmailSettings(); }
    catch(error) { $("email-config-status").textContent=`Test unavailable (${error.message})`; }
  });
  $("sign-out").addEventListener("click", async () => {
    try { await api("/api/v1/auth/session", 5000, "DELETE"); }
    catch (error) { toast(`Sign out could not be confirmed (${error.message}).`); }
    sessionStorage.removeItem("rv.dashboard.token"); location.reload();
  });
  $("refresh").addEventListener("click", () => { refreshStatus(); loadAssignments(); loadEvents(); loadWorkers(); loadObjectives(); });
  $("auth-open").addEventListener("click", () => { sessionStorage.removeItem("rv.dashboard.token"); state.token=""; if(state.timer)clearInterval(state.timer); $("workspace").hidden=true; $("login").hidden=false; $("token").focus(); });
  $("more-assignments").addEventListener("click", () => loadAssignments(true));
  $("more-events").addEventListener("click", () => loadOlderEvents());
  $("more-workers").addEventListener("click", () => loadWorkers(true));
  $("refresh-notifications").addEventListener("click", loadNotifications);
  $("refresh-objectives").addEventListener("click", loadObjectives);
  function chatAuthority() { return $("chat-authority").value.trim(); }
  const chatTime = (value) => {
    if (!value) return {local:"Unavailable",utc:"Unavailable"};
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) return {local:"Unavailable",utc:"Unavailable"};
    return {local:date.toLocaleString(),utc:date.toISOString()};
  };
  function eventDuration(events,event) {
    if (!event.request_id || event.event_type === "user_message") return null;
    const user=events.find((candidate)=>candidate.request_id===event.request_id&&candidate.event_type==="user_message");
    if (!user?.occurred_at || !event.occurred_at) return null;
    const ms=new Date(event.occurred_at)-new Date(user.occurred_at);
    return Number.isFinite(ms)&&ms>=0 ? `${(ms/1000).toFixed(1)} seconds` : null;
  }
  function conversationStatus(events) {
    const terminal=new Set(events.filter((e)=>["assistant_message","response_failed","response_interrupted"].includes(e.event_type)).map((e)=>e.request_id));
    const pending=events.some((e)=>e.event_type==="user_message"&&!terminal.has(e.request_id));
    if (state.chatInFlight || pending) return "Generating response";
    const last=[...events].reverse().find((e)=>["assistant_message","response_failed","response_interrupted"].includes(e.event_type));
    if (!last) return events.length ? "Conversation open" : "No messages yet";
    return last.event_type==="assistant_message" ? "Response complete" : last.event_type==="response_interrupted" ? "Response interrupted" : "Response failed";
  }
  function closeChatMenus(except=null) {
    document.querySelectorAll(".message-actions[open],.chat-more[open]").forEach((menu)=>{if(menu!==except)menu.open=false;});
  }
  async function copyChatText(text) {
    try { await navigator.clipboard.writeText(text); toast("Copied to clipboard."); }
    catch (_) { const box=document.createElement("textarea");box.value=text;box.setAttribute("readonly","");box.style.position="fixed";box.style.opacity="0";document.body.append(box);box.select();const ok=document.execCommand("copy");box.remove();if(!ok)throw new Error("clipboard_unavailable");toast("Copied to clipboard."); }
  }
  function openChatDetails() {
    state.chatDialogReturnFocus=document.activeElement;
    const events=state.chatEvents||[];const latest=[...events].reverse().find((e)=>e.event_type==="assistant_message");
    const interrupted=[...events].reverse().find((e)=>e.event_type==="response_interrupted");
    const lastPersisted=events.length?events[events.length-1].occurred_at:null;
    const created=chatTime(state.chatMeta?.created_at),updated=chatTime(state.chatMeta?.updated_at||lastPersisted);
    const values=[
      ["Conversation ID",state.chatConversationId||"Unavailable"],
      ["Created",`${created.local} · UTC ${created.utc}`],
      ["Last activity",`${updated.local} · UTC ${updated.utc}`],
      ["Status",conversationStatus(events)],
      ["Model identity",latest?.model_id||"Unavailable"],
      ["Model revision",latest?.implementation_revision||"Unavailable"],
      ["Provider",latest?.provider_ref||"Unavailable"],
      ["Most recent response duration",latest?eventDuration(events,latest)||"Unavailable":"Unavailable"],
      ["Last interrupted response",interrupted?`${chatTime(interrupted.occurred_at).local} · UTC ${chatTime(interrupted.occurred_at).utc} · ${interrupted.error_code||"reason unavailable"}`:"None recorded"],
      ["Recovery",interrupted?"Interrupted turn persisted; response is not automatically replayed.":"No interruption recorded in loaded history."]
    ];
    $("chat-details-content").innerHTML=values.map(([label,value])=>`<div class="chat-detail"><div class="chat-detail-label">${esc(label)}</div><div class="chat-detail-value">${esc(value)}</div></div>`).join("");
    $("chat-details-dialog").showModal();
  }
  function showMessageDetails(event) {
    const time=chatTime(event.occurred_at),duration=eventDuration(state.chatEvents,event);
    const values=[["Message ID",event.sequence??"Unavailable"],["Request ID",event.request_id||"Unavailable"],
      ["Role",event.event_type||"Unavailable"],["Timestamp",`${time.local} · UTC ${time.utc}`],
      ["Model",event.model_id||"Not applicable"],["Provider",event.provider_ref||"Not applicable"],
      ["Model revision",event.implementation_revision||"Not applicable"],["Response duration",duration||"Unavailable"],
      ["Outcome",event.error_code|| (event.event_type==="assistant_message"?"completed":event.event_type==="user_message"?"submitted":"unavailable")],
      ["Message",event.body||event.error_code||"No response content was recorded."]];
    $("message-details-content").innerHTML=values.map(([label,value])=>`<div class="chat-detail"><div class="chat-detail-label">${esc(label)}</div><div class="chat-detail-value ${label==="Message"?"message-detail-copy":""}">${esc(value)}</div></div>`).join("");
    $("message-details-dialog").showModal();
  }
  function closeMessageMenus() {
    document.querySelectorAll(".message-actions[open]").forEach((menu)=>{menu.open=false;});
  }
  function renderConversation(events) {
    state.chatEvents=events;
    const host=$("chat-history"), wasNearBottom=host.scrollHeight-host.scrollTop-host.clientHeight<120;
    const timeline=events.filter((event)=>["user_message","assistant_message","response_failed","response_interrupted"].includes(event.event_type));
    const pendingIds=new Set(timeline.filter((e)=>e.event_type==="user_message").map((e)=>e.request_id));
    for(const event of timeline.filter((e)=>["assistant_message","response_failed","response_interrupted"].includes(e.event_type)))pendingIds.delete(event.request_id);
    host.innerHTML=timeline.length?timeline.map((event,index)=>{
      const isUser=event.event_type==="user_message", failed=["response_failed","response_interrupted"].includes(event.event_type);
      const role=isUser?"steward":failed?"system":"grace";
      const label=isUser?"You":failed?(event.event_type==="response_interrupted"?"Interrupted":"Response status"):"Grace";
      const time=chatTime(event.occurred_at),duration=eventDuration(events,event);
      const status=isUser?(pendingIds.has(event.request_id)?"Awaiting response":"Submitted"):failed?(event.event_type==="response_interrupted"?"Interrupted":"Failed"):"Completed";
      const body=failed?`Response ${event.error_code||"unavailable"}; your message remains saved.`:event.body||"";
      const provenance=!isUser&&!failed?`${event.model_id||"Model unavailable"}${event.provider_ref?` · ${event.provider_ref}`:""}`:"";
      return `<article class="message-row ${role}${pendingIds.has(event.request_id)?" pending":""}" data-message-row="${index}" data-event-id="${esc(event.sequence??event.request_id)}"><div class="message-bubble"><div class="message-meta"><strong class="message-speaker">${label}</strong><time datetime="${esc(event.occurred_at||"")}" title="UTC ${esc(time.utc)}">${esc(time.local)}</time>${duration?`<span>${esc(duration)}</span>`:""}<span class="message-state">${esc(status)}</span>${provenance?`<span>${esc(provenance)}</span>`:""}</div><div class="message-content">${esc(body)}</div></div><details class="message-actions"><summary aria-label="More options for ${label} message" title="Message options">⋯</summary><div class="message-action-menu" role="menu"><button type="button" role="menuitem" data-message-details="${index}">View message details</button><button type="button" role="menuitem" data-message-copy="${index}">Copy message text</button><button type="button" role="menuitem" data-message-id-copy="${index}" ${event.sequence==null?"disabled":""}>Copy message ID</button><button type="button" role="menuitem" disabled>Edit and resubmit — future capability</button><button type="button" role="menuitem" disabled>Forward / create engineering request — unavailable</button></div></details></article>`;
    }).join(""):noData("No persisted messages in this conversation.");
    if(state.chatInFlight||pendingIds.size){host.insertAdjacentHTML("beforeend",`<article class="message-row grace pending" aria-label="Grace is generating a response"><div class="message-bubble"><div class="message-state"><span>Grace is responding</span><span class="typing-dots" aria-hidden="true"><i class="typing-dot"></i><i class="typing-dot"></i><i class="typing-dot"></i></span></div></div></article>`);}
    $("chat-state").textContent=conversationStatus(events);
    const lastFailure=timeline.length&&["response_failed","response_interrupted"].includes(timeline[timeline.length-1].event_type)?timeline[timeline.length-1]:null;
    $("chat-error").textContent=lastFailure?.error_code||"";
    if(wasNearBottom||!host.dataset.initialized)host.scrollTop=host.scrollHeight;
    host.dataset.initialized="true";
    host.querySelectorAll("[data-message-row]").forEach((row)=>row.addEventListener("click",(event)=>{if(event.target.closest("details"))return;state.selectedEventId=row.dataset.eventId;host.querySelectorAll(".message-row").forEach((r)=>r.classList.toggle("selected",r===row));}));
    host.querySelectorAll("[data-message-details]").forEach((button)=>button.addEventListener("click",()=>{const ev=timeline[Number(button.dataset.messageDetails)];state.chatDialogReturnFocus=button;if(ev)showMessageDetails(ev);closeMessageMenus();}));
    host.querySelectorAll("[data-message-copy]").forEach((button)=>button.addEventListener("click",()=>{const ev=timeline[Number(button.dataset.messageCopy)];state.selectedEventId=String(ev?.sequence??ev?.request_id??"");if(ev)copyChatText(ev.body||ev.error_code||"").catch(()=>toast("Clipboard access unavailable."));closeMessageMenus();}));
    host.querySelectorAll("[data-message-id-copy]").forEach((button)=>button.addEventListener("click",()=>{const ev=timeline[Number(button.dataset.messageIdCopy)];if(ev?.sequence!=null)copyChatText(String(ev.sequence)).catch(()=>toast("Clipboard access unavailable."));closeMessageMenus();}));
  }
  function showChatAuthorization(message) {
    state.chatAuthRejected=true;
    $("chat-authority").value="";
    $("chat-auth-form").hidden=Boolean(state.accountIdentity);
    $("chat-disconnect").hidden=true;
    $("chat-state").textContent=message;
    $("chat-error").textContent="Conversation access needs to be reconnected. Automatic retries are paused.";
  }
  async function loadGraceConversation() {
    if (state.chatAuthRejected || state.chatLoading) return;
    state.chatLoading=true;
    $("chat-state").textContent = "Loading persisted conversations…";
    try {
      if (state.accountIdentity) {
        await api("/api/v1/resident/conversation-session",10000,"POST");
      }
      const page = await api("/api/v1/resident/conversations", 10000);
      $("chat-auth-form").hidden=true;$("chat-disconnect").hidden=false;
      if (!state.chatConversationId && page.items?.length) state.chatConversationId = page.items[0].conversation_id;
      if (!state.chatConversationId) {
        state.chatMeta=null;state.chatEvents=[];
        $("chat-title").textContent = "New Grace conversation";
        $("chat-history").innerHTML = noData("A conversation is created when you send the first message.");
      } else {
        localStorage.setItem("rv.grace.conversation", state.chatConversationId);
        state.chatMeta=(page.items||[]).find((item)=>item.conversation_id===state.chatConversationId)||null;
        const history = await api(`/api/v1/resident/conversations/${encodeURIComponent(state.chatConversationId)}`, 10000);
        $("chat-title").textContent = `Conversation ${history.conversation_id}`;
        renderConversation(history.events || []);
        if (!$("chat-message").value) $("chat-message").value=sessionStorage.getItem("rv.grace.draft."+state.chatConversationId)||"";
        resizeChatComposer();
      }
      if (!state.chatEvents.length) $("chat-state").textContent = "No saved messages yet.";
    } catch (error) {
      if(error.payload?.error==="resident_conversation_not_authorized") showChatAuthorization(state.accountIdentity?"Your Steward account does not have both active exact Grace conversation grants.":"Grace access is not authorized or has expired. Connect with the Steward conversation credential.");
      else { $("chat-state").textContent = "Conversation status unavailable.";$("chat-error").textContent = `History could not be loaded: ${error.message}.`; }
    } finally { state.chatLoading=false; }
  }
  $("chat-authority").addEventListener("input",()=>{state.chatAuthRejected=false;$("chat-error").textContent="";});
  $("chat-auth-form").addEventListener("submit",async(event)=>{
    event.preventDefault();const authority=chatAuthority();if(!authority)return;
    const button=$("chat-connect");button.disabled=true;button.textContent="Connecting…";
    try{
      await api("/api/v1/resident/conversation-session",10000,"POST",{authority});
      $("chat-authority").value="";state.chatAuthRejected=false;$("chat-error").textContent="";
      $("chat-auth-form").hidden=true;$("chat-disconnect").hidden=false;
      await loadGraceConversation();
    }catch(error){
      $("chat-authority").value="";
      if(error.payload?.error==="resident_conversation_not_authorized")showChatAuthorization("This credential does not have both active Grace conversation grants. Automatic retries are paused.");
      else{$("chat-state").textContent="Connection unavailable.";$("chat-error").textContent=`Grace connection failed (${error.message}); no credential was retained.`;}
    }finally{button.disabled=false;button.textContent="Connect";}
  });
  $("chat-disconnect").addEventListener("click",async()=>{
    try{await api("/api/v1/resident/conversation-session",5000,"DELETE");}catch(_){}
    state.chatAuthRejected=true;state.chatEvents=[];$("chat-history").innerHTML=noData("Connect to load private conversation history.");
    $("chat-auth-form").hidden=false;$("chat-disconnect").hidden=true;$("chat-state").textContent="Disconnected from Grace.";
    $("chat-error").textContent="";$("chat-authority").focus();
  });
  $("chat-refresh").addEventListener("click", loadGraceConversation);
  $("chat-new").addEventListener("click", () => {
    state.chatConversationId = "";state.chatMeta=null;state.chatEvents=[]; localStorage.removeItem("rv.grace.conversation");
    $("chat-title").textContent = "New Grace conversation";
    $("chat-history").innerHTML = noData("A new persisted conversation will begin with your next message.");
    $("chat-error").textContent = "";
  });
  $("chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = $("chat-message").value;
    if (state.chatAuthRejected || !message.trim()) { $("chat-error").textContent = "Connect to Grace before sending a message."; return; }
    const send = $("chat-send"); send.disabled = true;state.chatInFlight=true;send.textContent="Sending…";$("chat-state").textContent = "Your message is being processed."; $("chat-error").textContent = "";renderConversation(state.chatEvents);
    const clientMessageId = crypto.randomUUID();
    try {
      const result = await api("/api/v1/resident/conversations", 150000, "POST", {
        body:{conversation_id:state.chatConversationId || null, client_message_id:clientMessageId, message}});
      state.chatConversationId = result.conversation_id; localStorage.setItem("rv.grace.conversation", state.chatConversationId);
      sessionStorage.removeItem("rv.grace.draft."+state.chatConversationId);
      sessionStorage.removeItem("rv.grace.draft.new");
      $("chat-message").value = ""; $("chat-state").textContent = `Response ${result.status}; request ${result.request_id}.`;
      await loadGraceConversation();
    } catch (error) {
      if(error.payload?.error==="resident_conversation_not_authorized"){
        showChatAuthorization("Grace access was denied. Reconnect before retrying; no automatic retry will be made.");
        return;
      }
      const result = error.payload || {};
      if (result.conversation_id) { state.chatConversationId = result.conversation_id; localStorage.setItem("rv.grace.conversation", state.chatConversationId); }
      $("chat-state").textContent = "Message result requires inspection.";
      $("chat-error").textContent = `Grace response failed (${result.error_code || error.message}). The request may be persisted; refresh history before retrying.`;
      if(error.payload?.error!=="resident_conversation_not_authorized")await loadGraceConversation();
    } finally { state.chatInFlight=false;send.disabled = false;send.textContent="Send message";renderConversation(state.chatEvents); }
  });
  function resizeChatComposer() {
    const box=$("chat-message");box.style.height="auto";
    box.style.height=Math.min(box.scrollHeight,Math.floor(window.innerHeight*.35))+"px";
  }
  const composer=$("chat-message");
  composer.addEventListener("input",()=>{resizeChatComposer();sessionStorage.setItem(state.chatConversationId?"rv.grace.draft."+state.chatConversationId:"rv.grace.draft.new",composer.value);});
  composer.addEventListener("keydown",(event)=>{
    if(event.key==="Enter"&&!event.shiftKey&&!event.isComposing){
      event.preventDefault();
      if($("chat-send").disabled)return;
      if($("chat-form").requestSubmit)$("chat-form").requestSubmit();else $("chat-send").click();
    }
  });
  $("chat-newline").addEventListener("click",()=>{
    const start=composer.selectionStart,end=composer.selectionEnd,value=composer.value;
    composer.value=value.slice(0,start)+"\n"+value.slice(end);
    composer.selectionStart=composer.selectionEnd=start+1;
    composer.dispatchEvent(new Event("input"));composer.focus();
  });
  if(!state.chatConversationId&&!composer.value)composer.value=sessionStorage.getItem("rv.grace.draft.new")||"";
  resizeChatComposer();
  document.querySelectorAll("[data-chat-option]").forEach((button)=>button.addEventListener("click",async()=>{
    document.querySelectorAll(".chat-more[open]").forEach((menu)=>{menu.open=false;});
    const option=button.dataset.chatOption;
    if(option==="details"){state.chatDialogReturnFocus=button;openChatDetails();}
    if(option==="copy-selected"){
      const event=state.chatEvents.find((item)=>String(item.sequence??item.request_id)===String(state.selectedEventId));
      if(!event){toast("Select a message before copying.");return;}
      try{await copyChatText(event.body||event.error_code||"");}catch(_){toast("Clipboard access unavailable.");}
    }
    if(option==="copy-conversation"){
      const transcript=state.chatEvents.filter((item)=>["user_message","assistant_message","response_failed","response_interrupted"].includes(item.event_type))
        .map((item)=>(item.event_type==="user_message"?"Steward":"Grace")+" · "+chatTime(item.occurred_at).local+"\n"+(item.body||item.error_code||"")).join("\n\n");
      try{await copyChatText(transcript);}catch(_){toast("Clipboard access unavailable.");}
    }
  }));
  document.querySelectorAll("[data-close-dialog]").forEach((button)=>button.addEventListener("click",()=>button.closest("dialog").close()));
  document.querySelectorAll("dialog.chat-dialog").forEach((dialog)=>{
    dialog.addEventListener("click",(event)=>{if(event.target===dialog)dialog.close();});
    dialog.addEventListener("close",()=>{if(state.chatDialogReturnFocus?.isConnected)state.chatDialogReturnFocus.focus();else {const trigger=document.querySelector("[data-chat-option='details']");if(trigger)trigger.focus();}state.chatDialogReturnFocus=null;});
  });
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
  const approvalLink=location.hash.match(/^#account-approval\?enrollment_id=([0-9a-fA-F-]{36})$/);
  if(approvalLink) state.pendingEnrollmentId=approvalLink[1];
  const authLink = location.hash.match(/^#account-verify\?(.*)$/);
  if (authLink) {
    const values = new URLSearchParams(authLink[1]);
    $("challenge-id").value = values.get("challenge_id") || "";
    $("challenge-token").value = values.get("token") || "";
    const purpose = values.get("purpose");
    $("email-challenge-form").hidden=false;
    $("verify-enrollment").hidden = purpose !== "enrollment";
    $("verify-bootstrap").hidden = purpose !== "steward_bootstrap";
    const isPassword=purpose==="password_setup"||purpose==="password_reset";
    $("set-account-password").hidden=!isPassword;
    $("new-password").hidden=!isPassword;
    $("new-password-label").hidden=!isPassword;
    $("new-password").required=isPassword;
    history.replaceState(null, "", location.pathname + location.search);
  } else {
    $("verify-bootstrap").hidden = true;
  }
  const existing = state.token;
  if (existing) connect(existing); else connectAccountSession();
  const initialHash = location.hash.slice(1);
  if(!state.pendingEnrollmentId&&initialHash) navigate(initialHash);
})();
