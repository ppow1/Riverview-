/*
Riverview~ Controlled Source
File: website/v2/deployed/assets/grace-chat.js
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.11
Changed: 2026-10-24 UTC | RV-V2-GRACE-CANCELLATION-INTEGRATION | Resolve exact objective/work-order chat commands through the Steward session and shared lifecycle confirmation.
Changed: 2026-10-23 UTC | RV-ISSUE-253-V2-ENGINEERING-PROGRESS | Show live conversation-linked objectives with safe cancellation and preserve a single panel across responsive sidebar transitions.
Purpose: Connect V2 Grace chat and expose a content-free trace of its durable request lifecycle
Execution Model: Interactive browser; request-driven reads/sends with durable response polling
Observability: Visible auth/status plus request IDs, provider attempts, timestamps, and persistence state
Dependencies: Same-origin rv.resident.conversation.v1 endpoints; secure account and CSRF cookies
Inputs/Outputs: Steward text and durable conversation events; message content is not browser-persisted
Authority: Existing resident conversation grants and the exact assignment.cancel grant are enforced by Dashboard on each request
Changed: 2026-10-21 UTC | RV-V2-OCTO1-GRACE-TRACE-001 | Expose only sanitized trace metadata from authenticated durable history
Changed: 2026-10-22 UTC | RV-HW-LIVE-STREAM-ACTIVITY-001 | Attach the owner-scoped content-free activity projection to same-conversation request traces.
Changed: 2026-10-22 UTC | RV-V2-GRACE-MESSAGE-ACTIONS-001 | Keyed append-only history reconciliation preserves open action menus, scroll, and composer state; wire authorized work-order intake and transcript copy.
Changed: 2026-10-23 UTC | RV-V2-MANUAL-IMAGE-GENERATION-248 | Preserve the deployed V2 source under its explicit production bundle path.
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: tests/test_v2_workspace_shell.py, scripts/verify_v2_grace_chat_chrome.py
History: Git and revision/backup manifest
*/
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const root = $("grace-chat-root");
  if (!root) return;
  const state = {connected: false, historyLoaded: false, conversationId: "", pending: new Set(), history: [], identity: null, workOrderSequence: null, historyInFlight: false, engineeringProgressLoading: false, engineeringProgressItems: null, engineeringProgressStatus: "not_checked", engineeringProgressConversationId: "", engineeringProgressObservedAt: null, engineeringProgressError: "", engineeringProgressTimer: null, cancelObjective: null, cancelInFlight: false};
  const HISTORY_KEY = "rv.grace.conversation";
  const errorNode = $("grace-chat-error");
  const statusNode = $("grace-chat-state");
  const historyNode = $("grace-chat-history");
  const engineeringProgress = $("engineering-progress-panel");
  const engineeringProgressFallback = $("engineering-progress-fallback");
  const engineeringProgressList = $("engineering-progress-list");
  const engineeringProgressState = $("engineering-progress-state");
  const workspaceShell = document.querySelector(".app-shell");
  const rightSidebar = $("right-sidebar");
  const graceWorkspace = $("grace-workspace");
  const desktopContext = window.matchMedia("(min-width: 761px)");
  const safeError = (value) => String(value || "request_failed").replace(/[^a-z0-9_.-]/gi, "_").slice(0, 64);

  function csrfToken() {
    const item = document.cookie.split(";").map((part) => part.trim())
      .find((part) => part.startsWith("rv_account_csrf="));
    if (!item) return "";
    try { return decodeURIComponent(item.slice("rv_account_csrf=".length)); }
    catch (_) { return ""; }
  }

  async function api(path, {method = "GET", body} = {}) {
    const headers = {Accept: "application/json"};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (method !== "GET" && method !== "HEAD") {
      const csrf = csrfToken();
      if (csrf) headers["X-Riverview-CSRF"] = csrf;
    }
    const response = await fetch(path, {method, headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin", cache: "no-store"});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(safeError(result.error || `http_${response.status}`));
      error.status = response.status;
      error.payload = result;
      throw error;
    }
    return result;
  }

  async function apiWithTransientRetry(path, options = {}) {
    const delays = [0, 300, 800, 1500];
    let lastError;
    for (const delay of delays) {
      if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
      try { return await api(path, options); }
      catch (error) {
        lastError = error;
        if (![502, 503, 504].includes(error.status)) throw error;
      }
    }
    throw lastError || new Error("notification_settings_unavailable");
  }

  function appendProgressField(grid, label, value) {
    const term = document.createElement("dt"); term.textContent = label;
    const detail = document.createElement("dd"); detail.textContent = value || "Unavailable";
    grid.append(term, detail);
  }

  function canCancelObjective(item) {
    if (!item || !state.identity?.roles?.includes("steward")) return false;
    if (item.status === "GROUNDED") return !item.assignment_id;
    return item.status === "WORK_ORDER_CREATED" && Boolean(item.assignment_id) &&
      ["queued", "ready"].includes(String(item.assignment_state || "").toLowerCase());
  }

  function createEngineeringProgressCard() {
    const card = document.createElement("article"); card.className = "engineering-progress-item";
    const title = document.createElement("div"); title.className = "engineering-progress-title";
    const identity = document.createElement("strong");
    const badge = document.createElement("span"); badge.className = "engineering-progress-status";
    title.append(identity, badge);
    const grid = document.createElement("dl"); grid.className = "engineering-progress-grid";
    const activeNote = document.createElement("p"); activeNote.className = "engineering-progress-note";
    activeNote.textContent = "This assignment is running or blocked. The existing cancellation operation cannot stop active or stalled worker execution.";
    const cancel = document.createElement("button"); cancel.type = "button";
    cancel.className = "engineering-cancel-button"; cancel.textContent = "Cancel…";
    card.append(title, grid, activeNote, cancel);
    return card;
  }

  function updateEngineeringProgressCard(card, item) {
    card.dataset.objectiveId = String(item.objective_id || "");
    const identity = card.querySelector(".engineering-progress-title strong");
    const badge = card.querySelector(".engineering-progress-status");
    identity.textContent = `Objective ${item.objective_id || "identity unavailable"}`;
    badge.textContent = item.lifecycle_status || item.status || "status unavailable";
    const fields = [
      ["Lifecycle", item.lifecycle_stage || item.status],
      ["Current assignment", item.assignment_id
        ? `${item.assignment_id} · ${item.assignment_state || "state unavailable"}` : "No assignment created"],
      ["Latest activity", item.latest_event
        ? `${item.latest_event.event_type || "Event"} · ${item.latest_event.occurred_at ? timeLabel(item.latest_event.occurred_at) : "time unavailable"}`
        : "No lifecycle event recorded"]
    ];
    if (item.verification?.decision) fields.push(["Independent verification",
      `${item.verification.decision}${item.verification.summary ? ` · ${item.verification.summary}` : ""}`]);
    if (item.cancellation && item.status === "CANCELLED") {
      fields.push(["Cancellation reason", item.cancellation.reason || "Reason not recorded"]);
      fields.push(["Cancelled", item.cancellation.cancelled_at ? timeLabel(item.cancellation.cancelled_at) : "Time unavailable"]);
      if (item.cancellation.actor_id) fields.push(["Recorded by", item.cancellation.actor_id]);
    }
    const grid = card.querySelector(".engineering-progress-grid");
    grid.replaceChildren();
    fields.forEach(([label, value]) => appendProgressField(grid, label, value));
    const activeNote = card.querySelector(".engineering-progress-note");
    activeNote.hidden = !(item.status === "WORK_ORDER_CREATED" && ["running", "blocked"].includes(String(item.assignment_state || "").toLowerCase()));
    const cancel = card.querySelector(".engineering-cancel-button");
    cancel.hidden = !canCancelObjective(item);
    cancel.dataset.cancelObjective = String(item.objective_id || "");
    cancel.setAttribute("aria-label", `Cancel ${item.objective_id}, currently ${item.status}`);
  }

  function renderEngineeringProgress() {
    const items = Array.isArray(state.engineeringProgressItems) ? state.engineeringProgressItems : null;
    if (state.engineeringProgressStatus === "not_checked") {
      engineeringProgressState.textContent = state.connected
        ? "Waiting for a saved conversation to load." : "Sign in with an authorized Steward account to inspect Engineering Progress.";
      engineeringProgressList.replaceChildren();
      return;
    }
    if (state.engineeringProgressStatus === "not_initialized") {
      engineeringProgressState.textContent = "Objective progress storage is not initialized.";
      engineeringProgressList.replaceChildren();
      const message = document.createElement("p"); message.className = "engineering-progress-empty";
      message.textContent = "No authoritative Engineering status is available."; engineeringProgressList.append(message);
      return;
    }
    if (!items) {
      engineeringProgressState.textContent = state.engineeringProgressError
        ? `Engineering progress unavailable (${state.engineeringProgressError}).`
        : "Loading authoritative Engineering progress…";
      engineeringProgressList.replaceChildren();
      const message = document.createElement("p"); message.className = state.engineeringProgressError
        ? "engineering-progress-error" : "engineering-progress-empty";
      message.textContent = state.engineeringProgressError
        ? "The request failed before an authoritative observation was received. Refresh to retry."
        : "Loading progress linked to the current Grace conversation.";
      engineeringProgressList.append(message);
      return;
    }
    const observed = state.engineeringProgressObservedAt ? timeLabel(state.engineeringProgressObservedAt) : "Observation time unavailable";
    const stale = Boolean(state.engineeringProgressError);
    const refreshText = stale ? ` · STALE · ${state.engineeringProgressError}` : "";
    engineeringProgressState.textContent = `${items.length} linked objective${items.length === 1 ? "" : "s"} · observed ${observed}${refreshText}`;
    if (!items.length) {
      engineeringProgressList.replaceChildren();
      const message = document.createElement("p"); message.className = "engineering-progress-empty";
      message.textContent = "No objectives are linked to this conversation."; engineeringProgressList.append(message);
      return;
    }
    const focusedCancel = document.activeElement?.closest?.("button[data-cancel-objective]")?.dataset.cancelObjective;
    const existing = new Map(Array.from(engineeringProgressList.children)
      .map((card) => [card.dataset.objectiveId, card]));
    const cards = new Map();
    for (const item of items) {
      const id = String(item.objective_id || "");
      const card = existing.get(id) || createEngineeringProgressCard();
      updateEngineeringProgressCard(card, item);
      cards.set(id, card);
    }
    for (const [id, card] of existing) if (!cards.has(id)) card.remove();
    const currentOrder = Array.from(engineeringProgressList.children).map((card) => card.dataset.objectiveId);
    const desiredOrder = items.map((item) => String(item.objective_id || ""));
    if (currentOrder.join("\u0000") !== desiredOrder.join("\u0000")) {
      desiredOrder.forEach((id, index) => {
        const card = cards.get(id), before = engineeringProgressList.children[index] || null;
        if (card && card !== before) engineeringProgressList.insertBefore(card, before);
      });
    }
    if (focusedCancel) engineeringProgressList.querySelector(`button[data-cancel-objective="${CSS.escape(focusedCancel)}"]`)?.focus({preventScroll: true});
  }

  async function loadEngineeringProgress() {
    if (state.engineeringProgressLoading) return;
    if (!state.connected || !state.conversationId || !state.identity?.roles?.includes("steward")) {
      state.engineeringProgressItems = null;
      state.engineeringProgressStatus = "not_checked";
      state.engineeringProgressError = "";
      renderEngineeringProgress();
      return;
    }
    const conversationId = state.conversationId;
    if (state.engineeringProgressConversationId !== conversationId) {
      state.engineeringProgressItems = null;
      state.engineeringProgressStatus = "not_checked";
      state.engineeringProgressObservedAt = null;
      state.engineeringProgressError = "";
      renderEngineeringProgress();
    }
    state.engineeringProgressLoading = true;
    try {
      const page = await api(`/api/v1/objectives?limit=25&conversation_id=${encodeURIComponent(conversationId)}`);
      if (conversationId !== state.conversationId) return;
      if (!page || !["available", "not_initialized"].includes(page.status) || !Array.isArray(page.items || [])) {
        throw new Error("objective_progress_contract_invalid");
      }
      state.engineeringProgressItems = page.items || [];
      state.engineeringProgressStatus = page.status;
      state.engineeringProgressConversationId = conversationId;
      state.engineeringProgressObservedAt = page.observed_at || null;
      state.engineeringProgressError = "";
    } catch (error) {
      if (conversationId !== state.conversationId) return;
      state.engineeringProgressError = safeError(error.payload?.error || error.message);
      if (!state.engineeringProgressItems) state.engineeringProgressStatus = "unavailable";
    } finally {
      state.engineeringProgressLoading = false;
      if (conversationId === state.conversationId) renderEngineeringProgress();
    }
  }

  function syncEngineeringProgressPlacement() {
    if (!engineeringProgress || !engineeringProgressFallback || !rightSidebar) return;
    const isGrace = document.getElementById("workspace-main")?.dataset.currentView === "grace";
    const sidebarExpanded = desktopContext.matches && workspaceShell?.dataset.rightState === "expanded";
    const destination = sidebarExpanded ? rightSidebar : engineeringProgressFallback;
    if (engineeringProgress.parentElement !== destination) {
      const historyScrollTop = historyNode.scrollTop;
      const pageX = window.scrollX, pageY = window.scrollY;
      const focused = document.activeElement;
      const focusInsidePanel = engineeringProgress.contains(focused);
      const composer = $("grace-message");
      const composerFocused = document.activeElement === composer;
      const selection = composerFocused ? {start: composer.selectionStart, end: composer.selectionEnd, direction: composer.selectionDirection} : null;
      destination.append(engineeringProgress);
      requestAnimationFrame(() => {
        historyNode.scrollTop = historyScrollTop;
        if (composerFocused && composer.isConnected) {
          composer.focus({preventScroll: true});
          if (selection) composer.setSelectionRange(selection.start, selection.end, selection.direction);
        } else if (focusInsidePanel && focused?.isConnected) focused.focus({preventScroll: true});
        window.scrollTo(pageX, pageY);
      });
    }
    engineeringProgress.hidden = !isGrace;
    engineeringProgressFallback.hidden = sidebarExpanded;
  }

  function startEngineeringProgressPolling() {
    if (state.engineeringProgressTimer) return;
    state.engineeringProgressTimer = window.setInterval(() => {
      if (state.connected && document.visibilityState === "visible" &&
          document.getElementById("workspace-main")?.dataset.currentView === "grace") {
        loadEngineeringProgress();
      }
    }, 5000);
  }

  function openCancellationDialog(item) {
    if (!canCancelObjective(item)) {
      $("grace-chat-action-status").textContent = "This objective is no longer in a safely cancellable state. Refreshing authoritative progress.";
      loadEngineeringProgress();
      return;
    }
    state.cancelObjective = {objective_id: item.objective_id, status: item.status,
      assignment_id: item.assignment_id || null, assignment_state: item.assignment_state || null};
    $("engineering-cancel-target").textContent = `Target ${item.objective_id} · state ${item.status} · assignment ${item.assignment_id || "none"} (${item.assignment_state || "not created"}).`;
    $("engineering-cancel-reason").value = "";
    $("engineering-cancel-reason").required = item.status === "GROUNDED";
    $("engineering-cancel-reason").previousElementSibling.textContent = item.status === "GROUNDED" ? "Reason (required)" : "Reason (optional)";
    $("engineering-cancel-status").textContent = "Confirm explicitly. The authoritative service rechecks current state and Steward authorization on submission.";
    $("engineering-cancel-dialog").showModal();
    if (item.status === "GROUNDED") $("engineering-cancel-reason").focus();
  }

  async function handleConversationalCancellation(message) {
    const text = String(message || "").trim();
    const stalled = /^(?:grace\s*[, :]\s*)?cancel\s+(?:the\s+)?stalled\s+engineering\s+objective[.!?]*$/i.test(text);
    const match = /^(?:grace\s*[, :]\s*)?cancel\s+(objective|work\s+order)\s+(.+?)[.!?]*$/i.exec(text);
    if (!stalled && !match) return false;
    const status = $("grace-chat-action-status");
    try {
      const page = await api("/api/v1/objectives?limit=100");
      if (page.status !== "available" || !Array.isArray(page.items)) throw new Error("objective_list_unavailable");
      if (stalled) {
        const running = page.items.filter((item) => item.status === "WORK_ORDER_CREATED" &&
          ["running", "blocked"].includes(String(item.assignment_state || "").toLowerCase()));
        const ids = running.slice(0, 5).map((item) => `${item.objective_id} (${item.assignment_state})`).join(" · ");
        const candidateNote = ids ? `Current running or blocked candidates: ${ids}.` : "No running or blocked candidates were returned.";
        const truncationNote = page.truncated ? " The objective list is truncated, so candidates may be incomplete." : "";
        status.textContent = `I can’t safely infer which work is stalled: the authoritative objective list has no stalled flag. ${candidateNote}${truncationNote} Running and blocked assignments cannot be cancelled by the existing safe cancellation operation. Please provide an exact eligible objective ID or queued/ready work-order ID.`;
        return true;
      }
      const kind = match[1].toLowerCase().startsWith("work") ? "work-order" : "objective";
      const rawTarget = match[2].trim().replace(/^['"“”]|['"“”]$/g, "").replace(/[.!?]+$/, "").trim();
      const normalized = rawTarget.toLowerCase();
      const candidates = page.items.filter((item) => {
        const target = kind === "objective" ? item.objective_id : item.assignment_id;
        return typeof target === "string" && (target.toLowerCase() === normalized ||
          (kind === "objective" && target.split(":").at(-1).toLowerCase() === normalized));
      });
      if (candidates.length !== 1) {
        const reason = candidates.length > 1 ? "matches more than one record" : "did not match an exact objective or assignment ID";
        status.textContent = `I could not resolve that cancellation request: ${reason}. Please provide the exact ${kind} ID. No cancellation was sent.`;
        return true;
      }
      const item = candidates[0];
      if (!canCancelObjective(item)) {
        status.textContent = `Objective ${item.objective_id} is ${item.status}${item.assignment_state ? ` (${item.assignment_state})` : ""} and is not safely cancellable through the existing lifecycle. Running or stalled worker work has no stop operation in this control.`;
        return true;
      }
      status.textContent = `Resolved ${kind} to objective ${item.objective_id}. Review the exact target and confirm cancellation.`;
      openCancellationDialog(item);
    } catch (error) {
      status.textContent = `I could not resolve the cancellation request (${safeError(error.payload?.error || error.message)}). No cancellation was sent.`;
    }
    return true;
  }

  async function handleConversationalNotificationSettings(message) {
    const text = String(message || "").trim();
    const read = /^(?:grace\s*[, :]\s*)?(?:(?:what(?:'s|\s+(?:is|are))|tell me|show|read|get|check|how are)\s+)?(?:(?:the|my)\s+)?(?:(?:current|saved|active|configured)\s+)?notification(?:s)?(?:\s+(?:setting|settings|level|preferences|configuration|configured))?[?.!]*$/i.test(text)
      || /^(?:grace\s*[, :]\s*)?(?:what(?:'s|\s+(?:is|are))|tell me|show|check)\s+(?:(?:the|my)\s+)?(?:(?:current|saved|active)\s+)?notification\s+(?:setting|settings|level|preferences|configuration)[?.!]*$/i.test(text);
    const levelMatch = /^(?:grace\s*[, :]\s*)?(?:set\s+)?notification(?:\s+level)?\s+(?:to|=)\s*(all|important|critical\s+only|paused)[.!]*$/i.exec(text);
    const quietMatch = /^(?:grace\s*[, :]\s*)?(?:set\s+)?quiet hours\s+(on|off|enabled|disabled)[.!]*$/i.exec(text);
    const hoursMatch = /^(?:grace\s*[, :]\s*)?set quiet hours to (\d{2}:\d{2})\s*(?:-|to)\s*(\d{2}:\d{2})\s+in\s+([A-Za-z_]+(?:\/[A-Za-z0-9_+.-]+)+)[.!]*$/i.exec(text);
    if (!read && !levelMatch && !quietMatch && !hoursMatch) return false;
    const status = $("grace-chat-action-status");
    if (!state.identity?.roles?.includes("steward")) {
      status.textContent = "Notification settings require an authenticated Steward session. No settings were read or changed.";
      return true;
    }
    try {
      const current = await apiWithTransientRetry("/api/v1/notification-settings");
      const description = (settings) => `Level: ${settings.level.replaceAll("_", " ")}. Quiet hours: ${settings.quiet_hours.enabled ? "on" : "off"}, ${settings.quiet_hours.start}–${settings.quiet_hours.end}; time zone: ${settings.quiet_hours.timezone}. Critical alerts always pass, including during Paused and quiet hours.`;
      if (read) { status.textContent = description(current); return true; }
      const next = {level: current.level, quiet_hours: {...current.quiet_hours}};
      if (levelMatch) next.level = levelMatch[1].toLowerCase().replace(/\s+/g, "_");
      if (quietMatch) next.quiet_hours.enabled = /^(on|enabled)$/i.test(quietMatch[1]);
      if (hoursMatch) {
        next.quiet_hours.enabled = true;
        next.quiet_hours.start = hoursMatch[1];
        next.quiet_hours.end = hoursMatch[2];
        next.quiet_hours.timezone = hoursMatch[3];
      }
      if (!window.confirm(`Grace resolved this settings change. Confirm updating the shared Riverview settings?\n\n${description(next)}`)) {
        status.textContent = "Settings change cancelled; current preferences are unchanged.";
        return true;
      }
      const saved = await apiWithTransientRetry("/api/v1/notification-settings", {method: "PUT", body: {
        level: next.level, quiet_hours: next.quiet_hours
      }});
      status.textContent = `Settings saved to Riverview. ${description(saved)}`;
      window.dispatchEvent(new CustomEvent("rvv2:notification-settings-updated", {detail: saved}));
    } catch (error) {
      status.textContent = `Notification settings request failed (${safeError(error.payload?.error || error.message)}). No success is claimed.`;
    }
    return true;
  }

  function setStatus(text, code) {
    statusNode.textContent = text;
    root.dataset.state = code;
  }

  function showError(error) {
    errorNode.hidden = false;
    const reason = safeError(error?.payload?.error || error?.message);
    const messages = {
      resident_conversation_not_authorized: "This Dashboard account lacks the active exact Grace conversation grants.",
      authentication_required: "Sign in with an authorized Dashboard account to access Grace.",
      csrf_or_session_check_failed: "The Dashboard session expired or its request check failed. Sign in again.",
      account_auth_unavailable: "Dashboard account authentication is unavailable. Retry after service recovery.",
      resident_conversation_unavailable: "The durable Grace conversation service is unavailable. No message was confirmed.",
      cross_origin_request_denied: "Dashboard rejected the request origin. Reopen V2 from the trusted HTTPS address."
    };
    errorNode.textContent = messages[reason] || `Grace conversation request failed (${reason}). Refresh history before retrying; an uncertain send is never repeated automatically.`;
  }

  function clearError() {
    errorNode.hidden = true;
    errorNode.textContent = "";
  }

  function timeLabel(value) {
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? "Timestamp unavailable" : `${date.toLocaleString()} · ${date.toISOString()}`;
  }

  function render(events, {scrollToBottom = false, reset = false} = {}) {
    const incoming = Array.isArray(events) ? events : [];
    if (reset) state.history = incoming;
    else {
      const merged = new Map(state.history.map(event => [String(event.sequence ?? `${event.event_type}:${event.request_id || "unknown"}:${event.occurred_at || ""}`), event]));
      incoming.forEach(event => merged.set(String(event.sequence ?? `${event.event_type}:${event.request_id || "unknown"}:${event.occurred_at || ""}`), event));
      state.history = [...merged.values()].sort((left, right) => (Number(left.sequence) || 0) - (Number(right.sequence) || 0));
    }
    const visible = state.history.filter((event) => ["user_message", "assistant_message", "response_failed", "response_interrupted", "response_deferred"].includes(event.event_type));
    const previousScroll = historyNode.scrollTop;
    const keyed = new Map(Array.from(historyNode.querySelectorAll(":scope > [data-history-key]")).map((item) => [item.dataset.historyKey, item]));
    const wanted = new Set();
    for (const event of visible) {
      const key = String(event.sequence ?? `${event.event_type}:${event.request_id || "unknown"}:${event.occurred_at || ""}`);
      wanted.add(key);
      let item = keyed.get(key);
      if (!item) item = createMessage(event, key);
      item.className = `grace-message ${event.event_type === "user_message" ? "from-steward" : "from-grace"}`;
      const role = item.querySelector("[data-message-role]");
      role.textContent = event.event_type === "user_message" ? "You" : event.event_type === "assistant_message" ? "Grace" : "Response status";
      item.querySelector("[data-message-meta]").textContent = `Event ${Number.isInteger(event.sequence) ? event.sequence : "unknown"} · ${timeLabel(event.occurred_at)}`;
      item.querySelector("[data-message-content]").textContent = event.body || event.error_code || (event.event_type === "response_deferred" ? "Grace response deferred." : "No response text was recorded.");
      item.dataset.sequence = Number.isInteger(event.sequence) ? String(event.sequence) : "";
      item.querySelector("[data-create-work-order]").hidden = !(event.event_type === "user_message" && Number.isInteger(event.sequence) && state.identity?.roles?.includes("steward"));
      item.querySelector("[data-create-work-order]").dataset.sequence = Number.isInteger(event.sequence) ? String(event.sequence) : "";
      if (!keyed.has(key)) historyNode.append(item);
    }
    if (reset) keyed.forEach((item, key) => { if (!wanted.has(key)) item.remove(); });
    if (!visible.length && !historyNode.querySelector("[data-history-key]")) {
      let empty = historyNode.querySelector("[data-history-empty]");
      if (!empty) { empty = document.createElement("p"); empty.dataset.historyEmpty = "true"; historyNode.append(empty); }
      empty.textContent = "No saved messages yet. Send a message to start a durable conversation.";
    } else historyNode.querySelector("[data-history-empty]")?.remove();
    // Preserve the viewport across background reconciliation. New messages only scroll when the user explicitly sent one.
    historyNode.scrollTop = scrollToBottom ? historyNode.scrollHeight : previousScroll;
  }

  function createMessage(event, key) {
    const item = document.createElement("article"); item.dataset.historyKey = key;
    const role = document.createElement("b"); role.dataset.messageRole = "true";
    const meta = document.createElement("small"); meta.dataset.messageMeta = "true";
    const content = document.createElement("p"); content.dataset.messageContent = "true";
    const details = document.createElement("details"); details.className = "grace-message-actions";
    const summary = document.createElement("summary"); summary.setAttribute("aria-label", "Conversation message actions"); summary.title = "Message actions"; summary.textContent = "⋯";
    const menu = document.createElement("div"); menu.className = "grace-message-menu"; menu.setAttribute("role", "menu");
    const copy = document.createElement("button"); copy.type = "button"; copy.setAttribute("role", "menuitem"); copy.setAttribute("data-copy-conversation", "true"); copy.textContent = "Copy Conversation Text";
    const work = document.createElement("button"); work.type = "button"; work.setAttribute("role", "menuitem"); work.setAttribute("data-create-work-order", "true"); work.textContent = "Create Work Order…";
    menu.append(copy, work); details.append(summary, menu); item.append(role, meta, content, details); return item;
  }

  function conversationText() {
    return state.history.filter(event => ["user_message", "assistant_message"].includes(event.event_type))
      .map(event => `${event.event_type === "user_message" ? "You" : "Grace"}: ${event.body || ""}`).join("\n\n");
  }

  async function copyText(value) {
    if (!value) throw new Error("conversation_text_unavailable");
    try { await navigator.clipboard.writeText(value); }
    catch (_) { const box=document.createElement("textarea");box.value=value;box.setAttribute("readonly", "");box.style.position="fixed";box.style.opacity="0";document.body.append(box);box.select();const ok=document.execCommand("copy");box.remove();if(!ok)throw new Error("clipboard_unavailable"); }
    $("grace-chat-action-status").textContent = "Conversation text copied.";
  }

  function closeMenus() { historyNode.querySelectorAll(".grace-message-actions[open]").forEach(menu => { menu.open = false; }); }
  historyNode.addEventListener("click", async event => {
    const copy = event.target.closest("[data-copy-conversation]");
    const work = event.target.closest("[data-create-work-order]");
    if (!copy && !work) return;
    const row = event.target.closest("[data-history-key]");
    if (copy) { try { await copyText(conversationText()); } catch (error) { $("grace-chat-action-status").textContent = `Copy failed (${safeError(error.message)}).`; } closeMenus(); return; }
    const sequence = Number(work.dataset.sequence);
    const source = state.history.find(item => item.event_type === "user_message" && item.sequence === sequence);
    if (!source || !state.identity?.roles?.includes("steward")) { $("grace-chat-action-status").textContent = "A saved Steward message and Steward session are required."; closeMenus(); return; }
    state.workOrderSequence = sequence;
    $("grace-work-order-source").textContent = source.body || "";
    $("grace-work-order-criteria").value = "";
    $("grace-work-order-error").textContent = "";
    $("grace-work-order-dialog").showModal(); closeMenus();
  });
  historyNode.addEventListener("toggle", event => { if (event.target.matches("details[open]")) historyNode.querySelectorAll("details[open]").forEach(menu => { if (menu !== event.target) menu.open = false; }); }, true);
  document.addEventListener("rvv2:view", event => {
    if (event.detail?.view !== "grace") closeMenus();
    syncEngineeringProgressPlacement();
    if (event.detail?.view === "grace") loadEngineeringProgress();
  });

  $("grace-work-order-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (!state.connected || !state.conversationId || !Number.isInteger(state.workOrderSequence)) return;
    const submit = $("grace-work-order-submit"), errorNode = $("grace-work-order-error");
    const criteria = $("grace-work-order-criteria").value.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
    submit.disabled = true; errorNode.textContent = "Submitting through the existing Steward-authorized intake…";
    try {
      const result = await api(`/api/v1/resident/conversations/${encodeURIComponent(state.conversationId)}/work-orders`, {method:"POST", body:{source_sequence:state.workOrderSequence, acceptance_criteria:criteria}});
      $("grace-work-order-dialog").close(); $("grace-chat-action-status").textContent = `Objective ${safeError(result.objective_id || "recorded")} submitted (${safeError(result.status || "accepted")}). Execution still requires its existing authorization.`;
      state.workOrderSequence = null;
    } catch (error) { errorNode.textContent = `${safeError(error.payload?.error || error.message)} · no approval or execution is implied.`; }
    finally { submit.disabled = false; }
  });
  document.querySelector("[data-close-work-order]").addEventListener("click", () => $("grace-work-order-dialog").close());

  engineeringProgressList.addEventListener("click", event => {
    const button = event.target.closest("button[data-cancel-objective]");
    if (button) {
      const item = (state.engineeringProgressItems || []).find((row) => row.objective_id === button.dataset.cancelObjective);
      openCancellationDialog(item);
    }
  });
  window.addEventListener("rvv2:cancel-objective", (event) => {
    openCancellationDialog(event.detail?.objective);
  });
  $("engineering-progress-refresh").addEventListener("click", loadEngineeringProgress);
  $("engineering-cancel-dismiss").addEventListener("click", () => $("engineering-cancel-dialog").close());
  $("engineering-cancel-dialog").addEventListener("close", () => { state.cancelObjective = null; state.cancelInFlight = false; });
  $("engineering-cancel-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (!state.identity?.roles?.includes("steward") || !state.cancelObjective || state.cancelInFlight) return;
    const reason = $("engineering-cancel-reason").value.trim();
    const target = state.cancelObjective;
    if (target.status === "GROUNDED" && !reason) { $("engineering-cancel-reason").focus(); return; }
    const submit = $("engineering-cancel-submit");
    state.cancelInFlight = true; submit.disabled = true;
    $("engineering-cancel-status").textContent = "Submitting the confirmed request; authorization and current lifecycle state are rechecked by Riverview…";
    try {
      const result = await api(`/api/v1/objectives/${encodeURIComponent(target.objective_id)}/cancel`,
        {method: "POST", body: reason ? {reason} : {}});
      $("engineering-cancel-dialog").close();
      $("grace-chat-action-status").textContent = `Cancellation recorded for ${result.objective_id || target.objective_id}: ${result.status || "authoritative status returned"}.`;
      window.dispatchEvent(new CustomEvent("rvv2:objective-cancelled", {detail: {objective_id: target.objective_id}}));
      await loadEngineeringProgress();
    } catch (error) {
      $("engineering-cancel-status").textContent = `Cancellation was not confirmed (${safeError(error.payload?.error || error.message)}). The objective remains unchanged in this view until the authoritative refresh completes.`;
      await loadEngineeringProgress();
    } finally {
      state.cancelInFlight = false; submit.disabled = false;
    }
  });
  const placementObserver = new MutationObserver(syncEngineeringProgressPlacement);
  if (workspaceShell) placementObserver.observe(workspaceShell, {attributes: true, attributeFilter: ["data-right-state"]});
  window.addEventListener("resize", syncEngineeringProgressPlacement, {passive: true});
  desktopContext.addEventListener?.("change", syncEngineeringProgressPlacement);
  syncEngineeringProgressPlacement();

  function requestTraceFromEvents(events, observedAt) {
    const requests = new Map();
    const allowedStages = new Set(["autonomic", "interim_30b", "reasoning"]);
    const safeTime = (value) => {
      const date = typeof value === "string" ? new Date(value) : null;
      return date && Number.isFinite(date.valueOf()) ? date.toISOString() : null;
    };
    const safeCount = (value) => Number.isSafeInteger(value) && value >= 0 && value <= 1000000 ? value : null;
    const safeCode = (value) => typeof value === "string" && /^[a-z0-9_.-]{1,80}$/i.test(value) ? value : null;
    const safeAttempts = (value) => Array.isArray(value) ? value.slice(0, 4).map((attempt) => {
      if (!attempt || typeof attempt !== "object") return null;
      const stage = allowedStages.has(attempt.reasoning_stage) ? attempt.reasoning_stage : null;
      const outcome = ["succeeded", "failed", "deferred"].includes(attempt.outcome) ? attempt.outcome : "unknown";
      return {
        stage,
        provider: typeof attempt.selected_provider === "string" && /^[a-z0-9_.-]{1,80}$/i.test(attempt.selected_provider) ? attempt.selected_provider : "Unavailable",
        started_at: safeTime(attempt.started_at),
        ended_at: safeTime(attempt.ended_at),
        elapsed_ms: typeof attempt.elapsed_ms === "number" && Number.isFinite(attempt.elapsed_ms) && attempt.elapsed_ms >= 0 && attempt.elapsed_ms <= 300000 ? attempt.elapsed_ms : null,
        outcome,
        error_code: safeCode(attempt.error_code),
        finish_reason: safeCode(attempt.finish_reason),
        completion_tokens: safeCount(attempt.completion_tokens)
      };
    }).filter(Boolean) : [];
    for (const event of Array.isArray(events) ? events : []) {
      if (!event || typeof event.request_id !== "string" || !event.request_id ||
          !["user_message", "assistant_message", "response_failed", "response_interrupted", "response_deferred"].includes(event.event_type)) continue;
      let trace = requests.get(event.request_id);
      if (!trace) {
        trace = {request_id: event.request_id, created_at: null, status: "awaiting_response", attempts: [], response_persisted_at: null, prompt_tokens: null, completion_tokens: null, finish_reason: null, reasoning_stage: null, error_code: null};
        requests.set(event.request_id, trace);
      }
      if (event.event_type === "user_message") trace.created_at = safeTime(event.occurred_at);
      if (["assistant_message", "response_failed", "response_interrupted", "response_deferred"].includes(event.event_type)) {
        const metadata = event.metadata && typeof event.metadata === "object" ? event.metadata : {};
        trace.status = ({assistant_message: "completed", response_failed: "failed", response_interrupted: "interrupted", response_deferred: "deferred"})[event.event_type];
        trace.attempts = safeAttempts(metadata.provider_attempts);
        trace.reasoning_stage = allowedStages.has(metadata.reasoning_stage) ? metadata.reasoning_stage : null;
        trace.prompt_tokens = safeCount(metadata.prompt_tokens);
        trace.completion_tokens = safeCount(metadata.completion_tokens);
        trace.finish_reason = safeCode(metadata.finish_reason);
        trace.error_code = safeCode(event.error_code);
        if (event.event_type === "assistant_message") trace.response_persisted_at = safeTime(event.occurred_at);
      }
    }
    return {schema_version: "rv.v2.grace-request-trace.v1", state: "available", observed_at: safeTime(observedAt), requests: [...requests.values()].filter((item) => item.created_at).slice(-12).reverse()};
  }

  async function requestTraceSnapshot() {
    if (!state.connected || !state.conversationId) {
      return {schema_version: "rv.v2.grace-request-trace.v1", state: state.connected ? "empty" : "not_connected", observed_at: null, requests: []};
    }
    try {
      const record = await api(`/api/v1/resident/conversations/${encodeURIComponent(state.conversationId)}`);
      if (record.conversation_id !== state.conversationId || !Array.isArray(record.events)) throw new Error("conversation_identity_mismatch");
      const trace=requestTraceFromEvents(record.events, new Date().toISOString());
      try {
        const activity=await api(`/api/v1/resident/conversations/${encodeURIComponent(state.conversationId)}/stream-activity?limit=12`);
        if(activity.schema_version!=="rv.resident.stream-activity.v1"||activity.conversation_id!==state.conversationId||!Array.isArray(activity.streams))throw new Error("stream_activity_contract_invalid");
        const byRequest=new Map(activity.streams.filter(item=>item&&typeof item.request_id==="string").map(item=>[item.request_id,item]));
        trace.requests=trace.requests.map(request=>({...request,stream_activity:byRequest.get(request.request_id)||null}));
        trace.stream_activity_state="available";
      } catch(error) {
        trace.stream_activity_state=error.status===401?"authentication_required":error.status===403?"denied":"unavailable";
      }
      return trace;
    } catch (error) {
      return {schema_version: "rv.v2.grace-request-trace.v1", state: error.status === 401 ? "authentication_required" : error.status === 403 ? "denied" : "unavailable", observed_at: null, requests: []};
    }
  }

  async function loadHistory({scrollToBottom = false} = {}) {
    if (!state.connected || state.historyInFlight) return;
    state.historyInFlight = true;
    state.historyLoaded = false;
    clearError();
    try {
    const previousConversationId = state.conversationId;
    const page = await api("/api/v1/resident/conversations");
    const ids = (page.items || []).map((item) => item.conversation_id);
    if (!state.conversationId || !ids.includes(state.conversationId)) {
      state.conversationId = ids[0] || "";
      if (state.conversationId) localStorage.setItem(HISTORY_KEY, state.conversationId);
      else localStorage.removeItem(HISTORY_KEY);
    }
    if (!state.conversationId) {
      render([], {scrollToBottom, reset: previousConversationId !== ""});
      state.historyLoaded = true;
      setStatus("Connected · no saved conversation yet", "connected");
      state.engineeringProgressItems = [];
      state.engineeringProgressStatus = "available";
      state.engineeringProgressConversationId = "";
      state.engineeringProgressObservedAt = new Date().toISOString();
      state.engineeringProgressError = "";
      renderEngineeringProgress();
      return;
    }
    if (previousConversationId !== state.conversationId && state.engineeringProgressConversationId !== state.conversationId) {
      state.engineeringProgressItems = null;
      state.engineeringProgressStatus = "not_checked";
      state.engineeringProgressObservedAt = null;
      state.engineeringProgressError = "";
      renderEngineeringProgress();
    }
    const record = await api(`/api/v1/resident/conversations/${encodeURIComponent(state.conversationId)}`);
    if (record.conversation_id !== state.conversationId) throw new Error("conversation_identity_mismatch");
    render(record.events || [], {scrollToBottom, reset: previousConversationId !== state.conversationId});
    state.historyLoaded = true;
    setStatus(`Connected · ${state.history.length} durable events loaded`, "connected");
    resumePending(record.events || []);
    await loadEngineeringProgress();
    } finally { state.historyInFlight = false; }
  }

  async function pollResponse(conversationId, requestId) {
    if (state.pending.has(requestId)) return;
    state.pending.add(requestId);
    setStatus("Grace response pending · checking durable status", "pending");
    const start = Date.now();
    let delay = 1500;
    try {
      while (Date.now() - start < 300000 && state.connected && conversationId === state.conversationId) {
        await new Promise((resolve) => setTimeout(resolve, delay));
        const result = await api(`/api/v1/resident/conversations/${encodeURIComponent(conversationId)}/responses/${encodeURIComponent(requestId)}`);
        if (["completed", "failed", "interrupted"].includes(result.status)) {
          await loadHistory();
          if (result.status === "completed") setStatus("Grace replied · exchange saved", "connected");
          else setStatus(`Response ${result.status} · saved history refreshed`, result.status);
          return;
        }
        if (result.status === "deferred") setStatus("Grace response deferred · durable request remains pending", "pending");
        delay = Math.min(Math.round(delay * 1.4), 5000);
      }
      if (state.connected && conversationId === state.conversationId) setStatus("Response is still pending · refresh history to inspect its durable state", "pending");
    } catch (error) {
      if (state.connected && conversationId === state.conversationId) showError(error);
    } finally { state.pending.delete(requestId); }
  }

  function resumePending(events) {
    const terminal = new Set(events.filter((event) => ["assistant_message", "response_failed", "response_interrupted"].includes(event.event_type)).map((event) => event.request_id));
    for (const event of events.filter((item) => item.event_type === "user_message" && item.request_id && !terminal.has(item.request_id))) {
      pollResponse(state.conversationId, event.request_id);
    }
  }

  window.RiverviewGraceChat = {
    requestTraceSnapshot,
    refreshHistory: () => loadHistory(),
    menuState: () => ({open: historyNode.querySelector("details[open]") !== null, conversation_id: state.conversationId}),
    snapshotDiagnostics() {
      return {
        status: state.connected ? "connected" : (root.dataset.state || "checking"),
        durable_history_loaded: state.connected && state.historyLoaded,
        persisted_event_count: state.connected && state.historyLoaded ? state.history.length : null,
        messages_captured: false,
        message_ids_captured: false,
        error_details_captured: false
      };
    }
  };

  async function connect() {
    clearError();
    setStatus("Checking Dashboard account and Grace grants…", "checking");
    try {
      const session = await api("/api/v1/auth/session");
      state.identity = session.identity || null;
      if (!session.identity?.roles?.includes("steward")) throw new Error("steward_account_required");
      await api("/api/v1/resident/conversation-session", {method: "POST"});
      state.connected = true;
      state.conversationId = localStorage.getItem(HISTORY_KEY) || "";
      $("grace-login-form").hidden = true;
      $("grace-chat-connected").hidden = false;
      $("grace-account-label").textContent = "Dashboard Steward session · exact grants checked by server";
      startEngineeringProgressPolling();
      await loadHistory();
    } catch (error) {
      state.connected = false;
      $("grace-login-form").hidden = false;
      $("grace-chat-connected").hidden = true;
      if (error.status === 401 || error.message === "steward_account_required") {
        setStatus("Dashboard sign-in required", "disconnected");
        if (error.message === "steward_account_required") showError(error);
      } else {
        setStatus("Grace connection unavailable", "unavailable");
        showError(error);
      }
    }
  }

  if (location.protocol !== "https:" || !location.pathname.startsWith("/v2/")) {
    setStatus("Open the LAN HTTPS Dashboard at /v2/ to use authenticated Grace chat", "unavailable");
    $("grace-login-form").hidden = true;
    return;
  }

  $("grace-login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("grace-login-form").querySelector("button");
    button.disabled = true;
    clearError();
    setStatus("Signing in through Dashboard…", "checking");
    try {
      await api("/api/v1/auth/session", {method: "POST", body: {
        email: $("grace-email").value.trim(), password: $("grace-password").value
      }});
      $("grace-password").value = "";
      await connect();
    } catch (error) {
      $("grace-password").value = "";
      setStatus("Dashboard sign-in failed", "disconnected");
      showError(error);
    } finally { button.disabled = false; }
  });

  $("grace-refresh").addEventListener("click", async () => {
    try { await loadHistory(); }
    catch (error) { showError(error); setStatus("History unavailable", "unavailable"); }
  });

  $("grace-new").addEventListener("click", () => {
    state.conversationId = "";
    localStorage.removeItem(HISTORY_KEY);
    render([], {reset:true});
    setStatus("New conversation · the first message creates its durable history", "connected");
    $("grace-message").focus();
  });

  $("grace-chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = $("grace-message").value.trim();
    if (!state.connected || !message) return;
    const send = $("grace-send");
    send.disabled = true;
    clearError();
    if (await handleConversationalNotificationSettings(message)) {
      $("grace-message").value = "";
      setStatus("Settings request handled through the authenticated notification API", "connected");
      send.disabled = false;
      return;
    }
    if (await handleConversationalCancellation(message)) {
      $("grace-message").value = "";
      setStatus("Cancellation request handled through the authorized objective lifecycle", "connected");
      send.disabled = false;
      return;
    }
    setStatus("Submitting message to Grace…", "pending");
    try {
      const result = await api("/api/v1/resident/conversations/stream", {method: "POST", body: {
        conversation_id: state.conversationId || null,
        client_message_id: crypto.randomUUID(),
        message
      }});
      if (!result.conversation_id || !result.request_id) throw new Error("conversation_receipt_incomplete");
      state.conversationId = result.conversation_id;
      localStorage.setItem(HISTORY_KEY, state.conversationId);
      $("grace-message").value = "";
      setStatus("Message durably accepted · waiting for Grace", "pending");
      await loadHistory({scrollToBottom:true});
      pollResponse(result.conversation_id, result.request_id);
    } catch (error) {
      showError(error);
      setStatus("Send result requires history inspection", "degraded");
      if (error.status !== 401 && error.status !== 403) await loadHistory().catch(() => {});
    } finally { send.disabled = false; }
  });

  connect();
})();
