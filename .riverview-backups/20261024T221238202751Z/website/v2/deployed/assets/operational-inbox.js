/* Read-only V2 presentation for existing notification and event projections. */
(() => {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const adapter = window.RiverviewV2OperationalInboxAdapter;
  if (!adapter || !$("#operational-inbox")) return;
  const feeds = {
    notifications: {path: "/api/v1/notifications?limit=50", status: "not checked", lastSuccess: null, items: []},
    attention: {path: "/api/v1/attention?limit=50", status: "not checked", lastSuccess: null, items: []},
    events: {path: "/api/v1/events?limit=50", status: "not checked", lastSuccess: null, items: []}
  };
  let refreshedAt = null;

  const node = (tag, value, className) => {
    const item = document.createElement(tag);
    if (className) item.className = className;
    item.textContent = value == null || value === "" ? "Not supplied" : String(value);
    return item;
  };
  const dateLabel = (value) => {
    const time = Date.parse(value || "");
    return Number.isFinite(time) ? new Intl.DateTimeFormat(undefined, {dateStyle: "medium", timeStyle: "short"}).format(time) : "Timestamp not supplied";
  };
  const human = (value) => String(value || "Unknown").replaceAll("_", " ");
  const stateLabel = (feed) => {
    if (feed.status === "available") return `Available · refreshed ${dateLabel(feed.lastSuccess)}`;
    if (feed.status === "not_initialized") return "Not initialized by this server";
    if (feed.status === "denied") return "Access denied by server";
    if (feed.status === "unauthenticated") return "Sign in to view this source";
    if (feed.status === "unavailable" && feed.lastSuccess) return `Refresh failed · showing last successful data from ${dateLabel(feed.lastSuccess)} (stale)`;
    if (feed.status === "unavailable") return "Unavailable · no current data";
    return "Not checked";
  };
  function visibleRows() {
    const rows = adapter.mergeFeeds({
      notifications: feeds.notifications.items,
      attention: feeds.attention.items,
      events: feeds.events.items
    });
    return adapter.filterRows(rows, {
      query: $("#inbox-search").value,
      source: $("#inbox-source").value,
      severity: $("#inbox-severity").value,
      status: $("#inbox-status").value,
      sort: $("#inbox-sort").value
    });
  }
  function render() {
    const freshness = $("#operational-inbox-freshness");
    freshness.textContent = refreshedAt ? `Last refresh attempt ${dateLabel(refreshedAt)}. Each source below reports its own result and age.` : "Inbox has not been refreshed in this session.";
    const sources = $("#operational-inbox-sources");
    sources.replaceChildren(...Object.entries(feeds).map(([name, feed]) => {
      const label = name === "events" ? "Operational events" : name === "attention" ? "Attention" : "Notifications";
      return node("span", `${label}: ${stateLabel(feed)}`, `inbox-source inbox-source-${feed.status.replaceAll("_", "-")}`);
    }));
    const body = $("#inbox-rows");
    const rows = visibleRows();
    body.replaceChildren(...rows.map((row) => {
      const tr = document.createElement("tr");
      const sourceState = row.deliveryState || "recorded";
      tr.append(
        node("td", dateLabel(row.timestamp)),
        node("td", row.severity || "Not supplied by source"),
        node("td", human(sourceState), `inbox-state inbox-state-${sourceState.replaceAll("_", "-")}`)
      );
      const eventCell = document.createElement("td");
      eventCell.append(node("strong", human(row.eventType)), node("span", row.description, "inbox-description"),
        node("small", row.sources.map((s) => s === "event" ? "Operational event" : s === "attention" ? "Attention" : "Notification").join(" · "), "inbox-meta"));
      tr.append(eventCell);
      const related = document.createElement("td");
      if (row.assignmentId) {
        const button = node("button", `Work ${row.assignmentId}`, "inbox-work-link");
        button.type = "button";
        button.addEventListener("click", () => {
          const workNav = document.querySelector('#primary-nav [data-view="work"]');
          workNav?.click();
          const search = $("#work-search");
          if (search) { search.value = row.assignmentId; search.dispatchEvent(new Event("input", {bubbles: true})); }
        });
        related.append(button);
      } else related.append(node("span", "No resident, service, objective, or work-order link supplied by this API."));
      tr.append(related);
      const evidence = document.createElement("td");
      if (row.eventId) evidence.append(node("code", `event ${row.eventId}`));
      if (row.notificationId) evidence.append(node("code", `notice ${row.notificationId}`));
      if (!row.eventId && !row.notificationId) evidence.append(node("span", "No evidence identifier supplied."));
      tr.append(evidence);
      return tr;
    }));
    const empty = $("#inbox-empty");
    empty.hidden = rows.length > 0;
    empty.textContent = rows.length ? "" : Object.values(feeds).every((feed) => feed.status === "not checked")
      ? "No source records have been loaded."
      : "No records match the selected filters, or all available sources returned no records.";
  }
  async function readFeed(name, feed) {
    try {
      const response = await fetch(feed.path, {method: "GET", credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"}});
      if (response.status === 401) { feed.status = "unauthenticated"; feed.items = []; feed.lastSuccess = null; return; }
      if (response.status === 403) { feed.status = "denied"; feed.items = []; feed.lastSuccess = null; return; }
      if (!response.ok) throw new Error(`http_${response.status}`);
      const page = await response.json();
      feed.status = page.status || "available";
      if (!Array.isArray(page.items)) throw new Error("invalid_projection");
      if (feed.status === "available") {
        feed.items = page.items;
        feed.lastSuccess = page.observed_at || new Date().toISOString();
      } else {
        feed.items = [];
        feed.lastSuccess = null;
      }
    } catch (_) {
      feed.status = "unavailable";
    }
  }
  async function refresh() {
    $("#operational-inbox-refresh").disabled = true;
    refreshedAt = new Date().toISOString();
    render();
    await Promise.all(Object.entries(feeds).map(([name, feed]) => readFeed(name, feed)));
    render();
    $("#operational-inbox-refresh").disabled = false;
  }
  document.addEventListener("DOMContentLoaded", () => {
    $("#operational-inbox-refresh").addEventListener("click", refresh);
    for (const selector of ["#inbox-search", "#inbox-source", "#inbox-severity", "#inbox-status", "#inbox-sort"]) {
      $(selector).addEventListener(selector === "#inbox-search" ? "input" : "change", render);
    }
    document.addEventListener("rvv2:view", (event) => {
      if (event.detail?.view === "communications" && !refreshedAt) refresh();
    });
  });
  window.RiverviewV2OperationalInbox = Object.freeze({render, refresh});
})();
