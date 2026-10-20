/*
Riverview~ Controlled Source
File: website/v2/assets/grace-chat.js
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.0
Purpose: Connect V2 Grace chat to the authenticated, persistent Dashboard conversation API
Execution Model: Interactive browser; request-driven reads/sends with durable response polling
Observability: Visible auth, connection, pending, completed, and failure status from API responses
Dependencies: Same-origin rv.resident.conversation.v1 endpoints; secure account and CSRF cookies
Inputs/Outputs: Steward text and durable conversation events; message content is not browser-persisted
Authority: Exact resident.conversation.read/send grants are enforced by Dashboard on each request
Changed: 2026-10-20 UTC | RV-WEB-V2-GRACE-CHAT-002 | Initial real authenticated V2 conversation client
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: tests/test_v2_workspace_shell.py, scripts/verify_v2_grace_chat_browser.py
History: Git and revision/backup manifest
*/
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const root = $("grace-chat-root");
  if (!root) return;
  const state = {connected: false, historyLoaded: false, conversationId: "", pending: new Set(), history: []};
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

  function render(events) {
    state.history = Array.isArray(events) ? events : [];
    historyNode.replaceChildren();
    const visible = state.history.filter((event) => ["user_message", "assistant_message", "response_failed", "response_interrupted", "response_deferred"].includes(event.event_type));
    if (!visible.length) {
      historyNode.textContent = "No saved messages yet. Send a message to start a durable conversation.";
      return;
    }
    for (const event of visible) {
      const item = document.createElement("article");
      item.className = `grace-message ${event.event_type === "user_message" ? "from-steward" : "from-grace"}`;
      const role = document.createElement("b");
      role.textContent = event.event_type === "user_message" ? "You" : event.event_type === "assistant_message" ? "Grace" : "Response status";
      const meta = document.createElement("small");
      meta.textContent = `Event ${Number.isInteger(event.sequence) ? event.sequence : "unknown"} · ${timeLabel(event.occurred_at)}`;
      const content = document.createElement("p");
      content.textContent = event.body || event.error_code || (event.event_type === "response_deferred" ? "Grace response deferred." : "No response text was recorded.");
      item.append(role, meta, content);
      historyNode.append(item);
    }
    historyNode.scrollTop = historyNode.scrollHeight;
  }

  async function loadHistory() {
    if (!state.connected) return;
    state.historyLoaded = false;
    clearError();
    const page = await api("/api/v1/resident/conversations");
    const ids = (page.items || []).map((item) => item.conversation_id);
    if (!state.conversationId || !ids.includes(state.conversationId)) {
      state.conversationId = ids[0] || "";
      if (state.conversationId) localStorage.setItem(HISTORY_KEY, state.conversationId);
      else localStorage.removeItem(HISTORY_KEY);
    }
    if (!state.conversationId) {
      render([]);
      state.historyLoaded = true;
      setStatus("Connected · no saved conversation yet", "connected");
      return;
    }
    const record = await api(`/api/v1/resident/conversations/${encodeURIComponent(state.conversationId)}`);
    if (record.conversation_id !== state.conversationId) throw new Error("conversation_identity_mismatch");
    render(record.events || []);
    state.historyLoaded = true;
    setStatus(`Connected · ${state.history.length} durable events loaded`, "connected");
    resumePending(record.events || []);
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
    render([]);
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
      await loadHistory();
      pollResponse(result.conversation_id, result.request_id);
    } catch (error) {
      showError(error);
      setStatus("Send result requires history inspection", "degraded");
      if (error.status !== 401 && error.status !== 403) await loadHistory().catch(() => {});
    } finally { send.disabled = false; }
  });

  connect();
})();
