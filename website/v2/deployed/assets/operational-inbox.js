// Revision: 1.1.0
// Changed: 2026-10-25 UTC | RV-WEB-V2-GRACE-RECOVERY-SESSION-CAPABILITY | Hide decision controls when server session says authority binding is unavailable
// Changed: 2026-10-26 UTC | RV-V2-NTFY-DEEP-LINKS-20261026 | Open an exact notification record from a same-origin authenticated view link without writing receipts.
/* Read-only V2 presentation for existing notification and event projections. */
(() => {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const adapter = window.RiverviewV2OperationalInboxAdapter;
  if (!adapter || !$("#operational-inbox")) return;
  const feeds = {
    notifications: {path: "/api/v1/notifications?limit=50", status: "not checked", lastSuccess: null, items: [], dispatcher: null},
    attention: {path: "/api/v1/attention?limit=50", status: "not checked", lastSuccess: null, items: []},
    events: {path: "/api/v1/events?limit=50", status: "not checked", lastSuccess: null, items: [], olderCursor: null, newerCursor: null, canLoadOlder: false, canLoadNewer: false}
  };
  let refreshedAt = null;
  let canWriteReceipts = false;
  let canRequestRecoveryDecision = false;
  let recoveryAccessMessage = "Sign in with a Steward account linked to institutional Steward authority to decide recovery requests.";
  const receiptRequests = new Set();
  const rawFocusNotificationId = new URLSearchParams(location.search).get("notification_id");
  const focusNotificationId = /^[0-9a-f-]{36}$/i.test(rawFocusNotificationId || "") ? rawFocusNotificationId : null;
  let focusedDeepLink = false;

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
    renderDispatcherHealth(feeds.notifications);
    const body = $("#inbox-rows");
    const eventFeed = feeds.events;
    $("#inbox-events-older").hidden = !eventFeed.canLoadOlder || eventFeed.status !== "available";
    $("#inbox-events-newer").hidden = !eventFeed.canLoadNewer || eventFeed.status !== "available";
    const seqs = eventFeed.items.map((event) => Number(event.seq)).filter(Number.isFinite);
    const seqNote = seqs.length ? `Loaded ${eventFeed.items.length} institutional events · sequence ${Math.min(...seqs)}–${Math.max(...seqs)}${eventFeed.canLoadOlder ? " · older history available" : " · earliest available page reached"}.` :
      eventFeed.status === "available" ? "No institutional events were returned by the authorized event source." : `Institution event history: ${stateLabel(eventFeed)}.`;
    $("#inbox-events-page-status").textContent = seqNote;
    const rows = visibleRows();
    body.replaceChildren(...rows.map((row) => {
      const tr = document.createElement("tr");
      if (row.notificationId) tr.dataset.notificationId = row.notificationId;
      const sourceState = row.deliveryState || "recorded";
      tr.append(
        node("td", dateLabel(row.timestamp)),
        node("td", row.severity || "Not supplied by source"),
        node("td", human(sourceState), `inbox-state inbox-state-${sourceState.replaceAll("_", "-")}`)
      );
      const eventCell = document.createElement("td");
      eventCell.append(node("strong", human(row.eventType)), node("span", row.description, "inbox-description"),
        node("small", row.sources.map((s) => s === "event" ? "Operational event" : s === "attention" ? "Attention" : "Notification").join(" · "), "inbox-meta"));
      const receiptAction = adapter.notificationReceiptAction(row, canWriteReceipts);
      if (receiptAction) {
        const actionButton = node("button", receiptAction === "delivered" ? "Confirm displayed" : "Acknowledge receipt", "inbox-receipt-action");
        actionButton.type = "button";
        actionButton.dataset.notificationReceiptAction = receiptAction;
        actionButton.dataset.notificationId = row.notificationId;
        actionButton.setAttribute("aria-label", `${receiptAction === "delivered" ? "Confirm dashboard display" : "Acknowledge receipt"} for ${human(row.eventType)}`);
        eventCell.append(actionButton);
      } else if (row.notificationId && row.deliveryState === "acknowledged") {
        eventCell.append(node("small", "Receipt acknowledged; no decision was made.", "inbox-receipt-note"));
      } else if (row.notificationId && ["queued", "delivered"].includes(row.deliveryState) && !canWriteReceipts) {
        eventCell.append(node("small", "An operator or Steward session is required to record a receipt.", "inbox-receipt-note"));
      }
      if (row.sources.includes("event")) {
        const details = document.createElement("details");
        const summary = node("summary", "Institution event record");
        const fields = document.createElement("dl");
        for (const [label, value] of [["Sequence", row.sequence], ["Event ID", row.eventId], ["Occurred", row.occurredAt], ["Recorded", row.recordedAt], ["Actor", row.actorId], ["Correlation ID", row.correlationId], ["Causation ID", row.causationId], ["Payload schema", row.payloadSchema]]) {
          const term = node("dt", label); const description = node("dd", value == null || value === "" ? "Not recorded" : value);
          fields.append(term, description);
        }
        details.append(summary, fields);
        eventCell.append(details);
      }
      if (row.notificationDetails) {
        const details = renderNotificationDetails(row.notificationDetails);
        if (focusNotificationId && row.notificationId === focusNotificationId) details.open = true;
        eventCell.append(details);
      }
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
      if (focusNotificationId && !focusedDeepLink && row.notificationId === focusNotificationId) {
        focusedDeepLink = true;
        tr.tabIndex = -1;
        tr.classList.add("inbox-deep-link-target");
        requestAnimationFrame(() => { tr.scrollIntoView({behavior: "smooth", block: "center"}); tr.focus({preventScroll: true}); });
      }
      return tr;
    }));
    const empty = $("#inbox-empty");
    empty.hidden = rows.length > 0;
    empty.textContent = rows.length ? "" : Object.values(feeds).every((feed) => feed.status === "not checked")
      ? "No source records have been loaded."
      : "No records match the selected filters, or all available sources returned no records.";
    document.querySelectorAll("[data-notification-receipt-action]").forEach((button) => button.addEventListener("click", () => recordNoticeReceipt(button)));
  }

  function renderDispatcherHealth(feed) {
    const target = $("#inbox-dispatcher-health");
    if (!target) return;
    const health = feed.dispatcher;
    if (!health) {
      target.textContent = feed.status === "unavailable" && feed.lastSuccess
        ? `Dispatcher status unavailable on refresh; last notification data is from ${dateLabel(feed.lastSuccess)}.`
        : feed.status === "unavailable" ? "Dispatcher status unavailable; notification API could not be read."
          : "Dispatcher health has not been read.";
      return;
    }
    const parts = [`Dispatcher ${human(health.status)}`];
    if (health.heartbeat_age_seconds != null && Number.isFinite(Number(health.heartbeat_age_seconds))) parts.push(`heartbeat ${ageLabel(Number(health.heartbeat_age_seconds))} ago`);
    else if (health.last_heartbeat_at) parts.push(`heartbeat ${dateLabel(health.last_heartbeat_at)}`);
    else parts.push("heartbeat not recorded");
    if (health.last_scan_at) parts.push(`last scan ${dateLabel(health.last_scan_at)}`);
    if (health.last_error_type) parts.push(`recorded error type ${human(health.last_error_type)}`);
    if (feed.status === "unavailable" && feed.lastSuccess) parts.push(`last successful API read ${dateLabel(feed.lastSuccess)} (stale)`);
    target.textContent = parts.join(" · ");
  }

  function ageLabel(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "unverified age";
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  }

  function renderNotificationDetails(item) {
    const details = document.createElement("details");
    details.className = "inbox-notification-details";
    const summary = node("summary", "Notification status and source details");
    const fields = document.createElement("dl");
    let recoveryActions = null;
    const statusMeaning = {
      queued: "Queued by Riverview; dashboard display is not confirmed. This does not confirm NTFY delivery.",
      delivered: "Dashboard display was explicitly confirmed; this does not confirm NTFY delivery or that a person saw it.",
      acknowledged: "Dashboard receipt was explicitly acknowledged; this is not a decision or proof of phone delivery."
    };
    const values = [
      ["Notification status", statusMeaning[item.delivery_status] || "Status not supplied by the notification API."],
      ["Configured notification channel (not delivery confirmation)", item.channel], ["Source event", item.source_event_id],
      ["Source event time", item.source_recorded_at], ["Notification queued", item.created_at],
      ["Dashboard display confirmation", item.delivered_at], ["Dashboard receipt acknowledgment", item.acknowledged_at],
      ["Linked decision request", item.decision_request_id], ["Decision status", item.decision_status],
      ["Decision assignment version", item.assignment_version]
    ];
    if (item.recovery_request_id) values.push(
      ["Bound recovery request", item.recovery_request_id], ["Recovery status", item.recovery_status],
      ["Recovery action", item.recovery_action], ["Recovery objective revision", item.recovery_objective_revision],
      ["Recovery attempt limit", item.attempt_limit], ["Recovery expiry", item.recovery_expires_at]
    );
    for (const [label, value] of values) appendField(fields, label, value);
    const transportNote = node("p", "This API does not report NTFY relay acceptance or iPhone delivery.", "inbox-receipt-note");
    const source = item.source_details;
    if (source) for (const [label, key] of [["Related objective", "objective_id"], ["Objective revision", "objective_revision"],
      ["Runtime revision", "runtime_revision"], ["Failure count", "failure_count"], ["Last error code", "last_error_code"],
      ["Blocked at", "blocked_at"], ["Last failure", "last_failure_at"], ["Recorded decision", "decision"],
      ["Recommended next action", "recommended_action"], ["Automatic recovery state", "automatic_recovery"]]) {
      if (source[key] != null && source[key] !== "") appendField(fields, label, source[key]);
    }
    if (item.recovery_request_id && item.recovery_status === "pending") {
      const actions = document.createElement("div");
      actions.className = "inbox-recovery-actions";
      if (canRequestRecoveryDecision) {
        for (const [decision, label] of [["approve", "Request: approve one retry"], ["defer", "Request: defer"], ["reject", "Request: reject"]]) {
          const button = node("button", label, decision === "approve" || decision === "reject" ? "inbox-recovery-decision inbox-recovery-consequential" : "inbox-recovery-decision");
          button.type = "button";
          button.dataset.recoveryDecision = decision;
          button.dataset.recoveryRequest = item.recovery_request_id;
          button.addEventListener("click", () => recordRecoveryDecision(button));
          actions.append(button);
        }
        actions.append(node("small", "The existing API additionally requires linked institutional Steward authority. Every choice requires confirmation and an audit reason; approval does not itself execute a retry."));
      } else {
        actions.append(node("small", recoveryAccessMessage, "inbox-recovery-unavailable"));
      }
      recoveryActions = actions;
    }
    details.append(summary, transportNote, fields);
    if (recoveryActions) details.append(recoveryActions);
    return details;
  }

  function appendField(fields, label, value) {
    const term = node("dt", label);
    const isTime = /time|queued|confirmation|acknowledgment|expiry|blocked at|last failure/i.test(label);
    const rendered = value == null || value === "" ? "Not recorded by source"
      : isTime && typeof value === "string" && Number.isFinite(Date.parse(value)) ? dateLabel(value)
        : typeof value === "object" ? JSON.stringify(value) : String(value);
    const description = node("dd", rendered);
    fields.append(term, description);
  }
  async function readReceiptAuthority() {
    try {
      const response = await fetch("/api/v1/auth/session", {method: "GET", credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"}});
      const session = response.ok ? await response.json() : null;
      const roles = session?.identity?.roles || [];
      canWriteReceipts = Array.isArray(roles) && (roles.includes("operator") || roles.includes("steward"));
      canRequestRecoveryDecision = adapter.canRequestRecoveryDecision(session?.identity);
      recoveryAccessMessage = !response.ok ? "A Steward account session is required for recovery decisions."
        : typeof session?.identity?.can_decide_grace_recovery !== "boolean"
          ? "Recovery decision eligibility is unavailable from this server session; no decision controls are enabled."
          : !session.identity.can_decide_grace_recovery
            ? roles.includes("steward")
              ? "This Steward account has no linked institutional Steward authority; recovery decisions are unavailable."
              : "Recovery decisions require a Steward account linked to institutional Steward authority."
            : "Eligible Steward session. The existing decision API rechecks authorization before recording each choice.";
    } catch (_) { canWriteReceipts = false; canRequestRecoveryDecision = false; recoveryAccessMessage = "Steward authorization status is unavailable; recovery decisions are disabled."; }
  }
  function csrfHeaders() {
    const raw = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("rv_account_csrf="))?.slice("rv_account_csrf=".length);
    if (!raw) throw new Error("csrf_token_missing");
    return {Accept: "application/json", "X-Riverview-CSRF": decodeURIComponent(raw)};
  }
  async function postNoticeReceipt(notificationId, action) {
    const response = await fetch(`/api/v1/notifications/${encodeURIComponent(notificationId)}/${action}`, {
      method: "POST", credentials: "same-origin", cache: "no-store", headers: csrfHeaders()
    });
    if (!response.ok) throw new Error(`http_${response.status}`);
    return response.json();
  }

  async function recordRecoveryDecision(button) {
    const requestId = button.dataset.recoveryRequest;
    const decision = button.dataset.recoveryDecision;
    if (!canRequestRecoveryDecision || !/^[0-9a-f-]{36}$/i.test(requestId || "") || !["approve", "defer", "reject"].includes(decision)) return;
    if (!window.confirm(`Confirm Steward decision “${decision}” for this exact one-attempt recovery request (${requestId})?`)) return;
    const reason = window.prompt("Required audit reason for this Steward recovery decision:");
    if (!reason?.trim()) return;
    button.disabled = true;
    $("#inbox-action-status").textContent = `Submitting Steward ${decision} decision…`;
    try {
      const response = await fetch(`/api/v1/grace-recovery/${encodeURIComponent(requestId)}/decision`, {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: {...csrfHeaders(), "Content-Type": "application/json"},
        body: JSON.stringify({decision, reason: reason.trim().slice(0, 1000),
          idempotency_key: `grace-recovery-decision:${requestId}:${decision}`})
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          canRequestRecoveryDecision = false;
          recoveryAccessMessage = "Recovery decision unavailable: the server rejected this Steward session or institutional authority. No decision was recorded.";
        }
        if (response.status === 409) await refresh();
        throw new Error(response.status === 401 || response.status === 403 ? "Steward authority required; no decision recorded"
          : response.status === 404 ? "Recovery request no longer exists"
            : response.status === 409 ? "Recovery request is already decided or expired"
              : response.status === 503 ? "Recovery decision service unavailable; no decision confirmed"
                : `http_${response.status}`);
      }
      await refresh();
      $("#inbox-action-status").textContent = result.status === "expired"
        ? "Recovery request expired; no decision was recorded."
        : `Steward ${decision} decision recorded. Existing bounded recovery processing determines whether or when anything is dispatched.`;
    } catch (error) {
      button.disabled = false;
      $("#inbox-action-status").textContent = `Recovery decision not confirmed (${error.message}).`;
      render();
    }
  }
  async function refreshNotifications() {
    await readFeed("notifications", feeds.notifications);
    render();
  }
  async function recordNoticeReceipt(button) {
    const notificationId = button.dataset.notificationId;
    const action = button.dataset.notificationReceiptAction;
    if (!canWriteReceipts || !notificationId || !["delivered", "acknowledge"].includes(action) || receiptRequests.has(notificationId)) return;
    receiptRequests.add(notificationId); button.disabled = true;
    $("#inbox-action-status").textContent = action === "delivered" ? "Recording dashboard display…" : "Recording receipt acknowledgment…";
    try {
      const receipt = await postNoticeReceipt(notificationId, action);
      await refreshNotifications();
      $("#inbox-action-status").textContent = action === "delivered"
        ? "Dashboard display receipt recorded. This does not confirm phone delivery or that a person saw it."
        : receipt.authority_effect === "none"
          ? "Receipt acknowledged. No decision or recovery authorization was made."
          : "Receipt response did not confirm that authority was unchanged.";
    } catch (error) {
      button.disabled = false;
      $("#inbox-action-status").textContent = `Receipt was not recorded (${error.message}).`;
    } finally { receiptRequests.delete(notificationId); }
  }
  async function readFeed(name, feed) {
    try {
      const response = await fetch(feed.path, {method: "GET", credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"}});
      if (response.status === 401) { feed.status = "unauthenticated"; feed.items = []; feed.lastSuccess = null; if (name === "notifications") feed.dispatcher = null; if (name === "events") { feed.olderCursor = null; feed.newerCursor = null; feed.canLoadOlder = false; feed.canLoadNewer = false; } return; }
      if (response.status === 403) { feed.status = "denied"; feed.items = []; feed.lastSuccess = null; if (name === "notifications") feed.dispatcher = null; if (name === "events") { feed.olderCursor = null; feed.newerCursor = null; feed.canLoadOlder = false; feed.canLoadNewer = false; } return; }
      if (!response.ok) throw new Error(`http_${response.status}`);
      const page = await response.json();
      feed.status = page.status || "available";
      if (!Array.isArray(page.items)) throw new Error("invalid_projection");
      if (name === "notifications") feed.dispatcher = page.dispatcher || {status: "not_initialized"};
      if (feed.status === "available") {
        feed.items = page.items;
        feed.lastSuccess = page.observed_at || new Date().toISOString();
        if (name === "events") {
          const merged = adapter.mergeEventPage({}, page, "latest");
          Object.assign(feed, merged);
        }
      } else {
        feed.items = [];
        feed.lastSuccess = null;
        if (name === "events") { feed.olderCursor = null; feed.newerCursor = null; feed.canLoadOlder = false; feed.canLoadNewer = false; }
      }
    } catch (_) {
      feed.status = "unavailable";
    }
  }
  async function pageEvents(direction) {
    const feed = feeds.events;
    const cursor = direction === "older" ? feed.olderCursor : feed.newerCursor;
    if (!cursor || feed.status !== "available") return;
    const button = direction === "older" ? $("#inbox-events-older") : $("#inbox-events-newer");
    button.disabled = true;
    try {
      const parameter = direction === "older" ? `before_seq=${encodeURIComponent(cursor)}` : `after_seq=${encodeURIComponent(cursor)}`;
      const response = await fetch(`/api/v1/events?${parameter}&limit=50`, {method: "GET", credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"}});
      if (response.status === 401 || response.status === 403) {
        feed.status = response.status === 401 ? "unauthenticated" : "denied";
        feed.items = []; feed.lastSuccess = null; feed.canLoadOlder = false; feed.canLoadNewer = false;
      } else if (!response.ok) throw new Error(`http_${response.status}`);
      else {
        const page = await response.json();
        if (!Array.isArray(page.items)) throw new Error("invalid_projection");
        if (page.status !== "available") { feed.status = page.status || "unavailable"; feed.items = []; feed.canLoadOlder = false; feed.canLoadNewer = false; }
        else {
          Object.assign(feed, adapter.mergeEventPage(feed, page, direction));
          feed.lastSuccess = page.observed_at || new Date().toISOString();
        }
      }
    } catch (_) { feed.status = "unavailable"; }
    finally { button.disabled = false; render(); }
  }
  async function refresh() {
    $("#operational-inbox-refresh").disabled = true;
    refreshedAt = new Date().toISOString();
    render();
    await Promise.all([...Object.entries(feeds).map(([name, feed]) => readFeed(name, feed)), readReceiptAuthority()]);
    render();
    $("#operational-inbox-refresh").disabled = false;
  }
  document.addEventListener("DOMContentLoaded", () => {
    $("#operational-inbox-refresh").addEventListener("click", refresh);
    $("#inbox-events-older").addEventListener("click", () => pageEvents("older"));
    $("#inbox-events-newer").addEventListener("click", () => pageEvents("newer"));
    for (const selector of ["#inbox-search", "#inbox-source", "#inbox-severity", "#inbox-status", "#inbox-sort"]) {
      $(selector).addEventListener(selector === "#inbox-search" ? "input" : "change", render);
    }
    document.addEventListener("rvv2:view", (event) => {
      if (event.detail?.view === "communications") {
        if (!refreshedAt) refresh();
        else render();
      }
    });
  });
  window.RiverviewV2OperationalInbox = Object.freeze({render, refresh});
})();
