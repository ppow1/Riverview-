/*
Riverview~ Controlled Source
File: website/v2/deployed/assets/grace-chat.js
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.9
Purpose: Connect V2 Grace chat and expose a content-free trace of its durable request lifecycle
Execution Model: Interactive browser; request-driven reads/sends with durable response polling
Observability: Visible auth/status plus request IDs, provider attempts, timestamps, and persistence state
Dependencies: Same-origin rv.resident.conversation.v1 endpoints; secure account and CSRF cookies
Inputs/Outputs: Steward text and durable conversation events; message content is not browser-persisted
Authority: Exact resident.conversation.read/send grants are enforced by Dashboard on each request
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
  const state = {connected: false, historyLoaded: false, conversationId: "", pending: new Set(), history: [], identity: null, workOrderSequence: null, historyInFlight: false};
  const HISTORY_KEY = "rv.grace.conversation";
  const errorNode = $("grace-chat-error");
  const statusNode = $("grace-chat-state");
  const historyNode = $("grace-chat-history");
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
  document.addEventListener("rvv2:view", event => { if (event.detail?.view !== "grace") closeMenus(); });

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
      return;
    }
    const record = await api(`/api/v1/resident/conversations/${encodeURIComponent(state.conversationId)}`);
    if (record.conversation_id !== state.conversationId) throw new Error("conversation_identity_mismatch");
    render(record.events || [], {scrollToBottom, reset: previousConversationId !== state.conversationId});
    state.historyLoaded = true;
    setStatus(`Connected · ${state.history.length} durable events loaded`, "connected");
    resumePending(record.events || []);
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
