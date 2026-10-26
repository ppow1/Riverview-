// Revision: 1.0.0
// Purpose: Render current read-only operational summaries from existing Dashboard APIs.
(() => {
  "use strict";
  const adapter = window.RiverviewV2OverviewAdapter;
  const grid = document.getElementById("overview-live-grid");
  const status = document.getElementById("overview-live-state");
  if (!adapter || !grid || !status) return;
  const state = {active: false, inFlight: false, checkedAt: null, dashboard: null, attention: null, telemetry: null, errors: {}};
  const paths = {dashboard: "/api/v1/status", attention: "/api/v1/attention?limit=50", telemetry: "/api/v1/resources/telemetry"};
  const dateLabel = (value) => {
    const time = Date.parse(value || "");
    return Number.isFinite(time) ? new Intl.DateTimeFormat(undefined, {dateStyle: "medium", timeStyle: "short"}).format(time) : "Time not supplied";
  };
  const node = (tag, className, value) => {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (value !== undefined) item.textContent = String(value);
    return item;
  };
  const fetchJson = async (path) => {
    const response = await fetch(path, {method: "GET", headers: {Accept: "application/json"}, credentials: "same-origin", cache: "no-store", redirect: "error"});
    if (!response.ok) { const error = new Error(`http_${response.status}`); error.status = response.status; throw error; }
    return response.json();
  };
  const displayError = (error) => adapter.statusError(error);
  function card({title, state: cardState, summary, detail, source, observedAt, href}) {
    const article = node("article", "overview-live-card");
    article.dataset.state = cardState || "unknown";
    const head = node("div", "overview-live-card-head");
    head.append(node("h3", "", title), node("span", "overview-live-badge", (cardState || "unknown").replaceAll("_", " ")));
    article.append(head, node("strong", "overview-live-summary", summary || "Status unavailable."));
    if (detail) article.append(node("p", "overview-live-detail", detail));
    article.append(node("small", "overview-live-source", `Source: ${source}`));
    article.append(node("small", "overview-live-time", observedAt ? `Observed ${dateLabel(observedAt)}` : `Refresh attempted ${dateLabel(state.checkedAt)} · source observation time unavailable`));
    if (href) {
      const target = article.appendChild(node("button", "overview-live-link", `Open ${href.label}`));
      target.type = "button";
      target.dataset.openView = href.view;
    }
    return article;
  }
  function render() {
    const models = [];
    const dashboard = adapter.dashboard(state.dashboard);
    if (state.errors.dashboard) {
      const failure = displayError(state.errors.dashboard);
      for (const title of ["Engineering assignments", "Worker health", "Grace and CME"]) models.push(card({title, state: failure.state, summary: failure.summary, source: paths.dashboard, href: {view: "work", label: "Work"}}));
    } else if (!dashboard) models.push(card({title: "Dashboard projection", state: "unavailable", summary: "Status payload unavailable.", source: paths.dashboard, href: {view: "work", label: "Work"}}));
    else {
      models.push(card({title: "Engineering assignments", state: dashboard.work.state, summary: dashboard.work.summary, detail: dashboard.work.detail,
        source: paths.dashboard, observedAt: dashboard.observedAt, href: {view: "work", label: "Work"}}));
      models.push(card({title: "Worker health", state: dashboard.workers.state, summary: dashboard.workers.summary,
        source: paths.dashboard, observedAt: dashboard.observedAt, href: {view: "resources", label: "Hardware & AI"}}));
      models.push(card({title: "Grace and CME", state: dashboard.serviceState,
        summary: dashboard.services.map((item) => `${item.name}: ${item.state.replaceAll("_", " ")}`).join(" · "),
        detail: dashboard.freshness === "stale" ? "The latest dashboard observation is stale." : "Service states are from the Dashboard status projection.",
        source: paths.dashboard, observedAt: dashboard.observedAt, href: {view: "process-workflows", label: "Workflows"}}));
    }
    const attention = state.errors.attention ? displayError(state.errors.attention) : adapter.attention(state.attention, state.checkedAt);
    models.push(attention
      ? card({title: "Operational attention", state: attention.state, summary: attention.summary,
          detail: attention.observedAt ? `Newest record ${dateLabel(attention.observedAt)} · window limit ${attention.limit ?? "not supplied"}.` : `No source record time supplied; refresh attempted ${dateLabel(attention.checkedAt)}.`,
          source: paths.attention, observedAt: attention.observedAt, href: {view: "communications", label: "Communications"}})
      : card({title: "Operational attention", state: "unavailable", summary: "Attention data unavailable; no zero count inferred.", source: paths.attention, href: {view: "communications", label: "Communications"}}));
    const telemetry = state.errors.telemetry ? displayError(state.errors.telemetry) : adapter.telemetry(state.telemetry);
    models.push(telemetry
      ? card({title: "Host telemetry", state: telemetry.state, summary: telemetry.status === "available" || telemetry.status === "partial"
          ? `${telemetry.hostCount} host record${telemetry.hostCount === 1 ? "" : "s"} reported` : `Telemetry ${telemetry.status.replaceAll("_", " ")}`,
          detail: "No utilization value is shown here; open Hardware & AI for source-bound readings.", source: paths.telemetry,
          observedAt: telemetry.observedAt, href: {view: "resources", label: "Hardware & AI"}})
      : card({title: "Host telemetry", state: "unavailable", summary: "Telemetry source unavailable; no utilization inferred.", source: paths.telemetry, href: {view: "resources", label: "Hardware & AI"}}));
    grid.replaceChildren(...models);
    const failures = Object.keys(state.errors).length;
    status.textContent = state.checkedAt ? `Last refresh attempt ${dateLabel(state.checkedAt)}. ${failures ? `${failures} source${failures === 1 ? "" : "s"} unavailable; see each card.` : "Sources report their own freshness."}` : "No operational source has been checked yet.";
  }
  async function refresh() {
    if (state.inFlight) return;
    if (location.protocol !== "https:" || !location.pathname.startsWith("/v2/")) {
      status.textContent = "Operational sources require the authenticated Riverview V2 LAN HTTPS route.";
      return;
    }
    state.inFlight = true;
    state.checkedAt = new Date().toISOString();
    state.errors = {};
    status.textContent = "Refreshing existing authenticated operational sources…";
    const results = await Promise.all(Object.entries(paths).map(async ([key, path]) => {
      try { return {key, payload: await fetchJson(path)}; }
      catch (error) { return {key, error}; }
    }));
    for (const result of results) {
      if (result.error) state.errors[result.key] = result.error;
      else state[result.key] = result.payload;
    }
    state.inFlight = false;
    render();
  }
  document.getElementById("overview-live-refresh")?.addEventListener("click", refresh);
  document.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-open-view]");
    if (button) document.querySelector(`.nav-item[data-view="${button.dataset.openView}"]`)?.click();
  });
  document.addEventListener("rvv2:view", (event) => {
    state.active = event.detail?.view === "overview";
    if (state.active && !state.checkedAt) refresh();
  });
  document.addEventListener("visibilitychange", () => { if (state.active && document.visibilityState === "visible") refresh(); });
  window.setInterval(() => { if (state.active && document.visibilityState === "visible") refresh(); }, 60000);
  window.RiverviewV2Overview = Object.freeze({render, refresh});
})();
