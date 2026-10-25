/*
Revision: 1.0.0
Purpose: V2 view over existing account enrollment, roster, and session APIs.
Authority: Dashboard account service remains authoritative for Steward role, CSRF, and audit checks.
Changed: 2026-10-25 UTC | RV-V2-ACCOUNT-SESSION-ADMIN-20261025 | Reuse V1 account review and session-revocation operations.
*/
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const escape = (value) => String(value == null ? "" : value).replace(/[&<>"']/g,
    (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character]));
  let busy = false;
  let currentAccountId = "";

  async function request(path, method = "GET", body) {
    const headers = {Accept:"application/json"};
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      const cookie = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("rv_account_csrf="));
      if (cookie) headers["X-Riverview-CSRF"] = decodeURIComponent(cookie.slice("rv_account_csrf=".length));
    }
    const response = await fetch(path, {method, headers, credentials:"same-origin", cache:"no-store",
      body:body === undefined ? undefined : JSON.stringify(body)});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `http_${response.status}`);
    return result;
  }

  function explain(error) {
    if (error.message === "steward_account_required") return "Sign in with an authenticated Steward account to review accounts.";
    if (error.message === "not_authorized") return "Access denied. The current account does not have the Steward role.";
    if (error.message === "http_401") return "Sign in to Riverview to use account administration.";
    if (error.message === "account_auth_unavailable") return "The account service is unavailable.";
    return `Request failed (${error.message}). No account action was completed.`;
  }

  const setStatus = (message) => { $("account-admin-status").textContent = message; };
  const formatTime = (value) => {
    if (!value) return "Unavailable";
    const time = Date.parse(value);
    return Number.isFinite(time) ? new Date(time).toLocaleString() : "Unavailable";
  };

  async function loadEnrollments() {
    const host = $("account-enrollment-list");
    try {
      const page = await request("/api/v1/account/enrollments?limit=50");
      const items = Array.isArray(page.items) ? page.items : [];
      $("account-enrollment-count").textContent = `${items.length} pending`;
      host.innerHTML = items.length ? items.map((item) => {
        const verified = Boolean(item.email_verified_at);
        return `<article class="account-admin-row enrollment-row"><div class="account-admin-record"><strong>${escape(item.email)}</strong><span>Verified ${escape(formatTime(item.email_verified_at))} · requested ${escape(formatTime(item.created_at))}</span></div><label class="account-admin-role">Role for approval<select data-enrollment-role="${escape(item.enrollment_id)}"><option value="viewer">Viewer</option><option value="operator">Operator</option><option value="steward">Steward</option></select></label><div class="account-admin-actions"><button type="button" data-enrollment="${escape(item.enrollment_id)}" data-decision="approve" data-grant="one_time" ${verified ? "" : "disabled"}>Approve one time</button><button type="button" data-enrollment="${escape(item.enrollment_id)}" data-decision="approve" data-grant="90_days" ${verified ? "" : "disabled"}>Approve 90 days</button><button type="button" data-enrollment="${escape(item.enrollment_id)}" data-decision="approve" data-grant="one_year" ${verified ? "" : "disabled"}>Approve one year</button><button type="button" data-enrollment="${escape(item.enrollment_id)}" data-decision="approve" data-grant="permanent" ${verified ? "" : "disabled"}>Approve permanently</button><button type="button" class="account-admin-secondary" data-enrollment="${escape(item.enrollment_id)}" data-decision="deny">Deny</button></div></article>`;
      }).join("") : `<p class="account-admin-empty">No verified account requests are pending.</p>`;
      host.querySelectorAll("[data-enrollment]").forEach((button) => button.addEventListener("click", () => decideEnrollment(button)));
      return {ok:true,count:items.length};
    } catch (error) {
      $("account-enrollment-count").textContent = "Unavailable";
      host.textContent = explain(error);
      return {ok:false,error:error.message};
    }
  }

  async function loadAccounts() {
    const host = $("account-roster-list");
    try {
      const page = await request("/api/v1/account/users?limit=100");
      const items = Array.isArray(page.items) ? page.items : [];
      $("account-roster-count").textContent = `${items.length} accounts`;
      host.innerHTML = items.length ? items.map((account) => {
        const roles = Array.isArray(account.roles) ? account.roles : [];
        const disabled = account.disabled === true;
        const self = account.account_id === currentAccountId;
        const metadata = [roles.length ? roles.join(", ") : "no roles", account.disabled ? "disabled" : "active",
          account.grant_type || "grant type unavailable", account.grant_expires_at ? `expires ${formatTime(account.grant_expires_at)}` : "no expiry recorded",
          account.grant_revoked ? "grant revoked" : "grant active", account.one_time_used ? "one-time session used" : "one-time session not used"];
        const stateControl = self && !disabled
          ? `<button type="button" class="account-admin-secondary" disabled title="Stewards cannot disable their own account">Cannot disable own account</button>`
          : `<button type="button" class="${disabled ? "account-admin-secondary" : "account-admin-danger"}" data-account-state="${escape(account.account_id)}" data-disabled="${disabled}" data-account-email="${escape(account.email)}">${disabled ? "Enable account" : "Disable account"}</button>`;
        return `<article class="account-admin-row"><div class="account-admin-record"><strong>${escape(account.email)}</strong><span>${escape(metadata.join(" · "))}</span></div><div class="account-admin-actions"><button type="button" class="account-admin-secondary" data-revoke-sessions="${escape(account.account_id)}" data-account-email="${escape(account.email)}">Revoke sessions</button>${stateControl}</div></article>`;
      }).join("") : `<p class="account-admin-empty">No approved accounts were returned.</p>`;
      host.querySelectorAll("[data-revoke-sessions]").forEach((button) => button.addEventListener("click", () => revokeSessions(button)));
      host.querySelectorAll("[data-account-state]").forEach((button) => button.addEventListener("click", () => setAccountState(button)));
      return {ok:true,count:items.length};
    } catch (error) {
      $("account-roster-count").textContent = "Unavailable";
      host.textContent = explain(error);
      return {ok:false,error:error.message};
    }
  }

  async function decideEnrollment(button) {
    if (busy) return;
    const id = button.dataset.enrollment;
    const decision = button.dataset.decision;
    const select = document.querySelector(`[data-enrollment-role="${CSS.escape(id)}"]`);
    const role = select?.value || "viewer";
    const grantType = button.dataset.grant || "one_time";
    const summary = decision === "approve"
      ? `Approve this verified request as ${role} with a ${grantType.replaceAll("_", " ")} access grant?`
      : "Deny this verified account request?";
    if (!window.confirm(summary)) return;
    busy = true; button.disabled = true;
    try {
      await request(`/api/v1/account/enrollments/${encodeURIComponent(id)}/decision`, "POST",
        {decision, role, grant_type:grantType});
      setStatus("Enrollment decision recorded by the account service.");
      await Promise.all([loadEnrollments(), loadAccounts()]);
    } catch (error) {
      button.disabled = false;
      setStatus(`Enrollment decision failed. ${explain(error)}`);
    } finally { busy = false; }
  }

  async function revokeSessions(button) {
    if (busy) return;
    const email = button.dataset.accountEmail || "this account";
    if (!window.confirm(`Revoke all active sessions for ${email}? Existing audit history will be recorded.`)) return;
    busy = true; button.disabled = true;
    try {
      const result = await request(`/api/v1/account/users/${encodeURIComponent(button.dataset.revokeSessions)}/sessions`, "POST", {});
      setStatus(`Session revocation completed; ${Number(result.sessions_revoked) || 0} active session(s) revoked.`);
      await loadAccounts();
    } catch (error) {
      button.disabled = false;
      setStatus(`Session revocation failed. ${explain(error)}`);
    } finally { busy = false; }
  }

  async function setAccountState(button) {
    if (busy) return;
    const disabled = button.dataset.disabled === "false";
    const email = button.dataset.accountEmail || "this account";
    const prompt = disabled
      ? `Disable ${email}? This blocks new sign-ins, revokes active sessions, and records the change in account audit history.`
      : `Enable ${email}? This allows the account to sign in again and records the change in account audit history.`;
    if (!window.confirm(prompt)) return;
    busy = true; button.disabled = true;
    try {
      const result = await request(`/api/v1/account/users/${encodeURIComponent(button.dataset.accountState)}/disable`,
        "POST", {disabled});
      setStatus(`Account ${result.status}; the existing account service recorded the change.`);
      await loadAccounts();
    } catch (error) {
      button.disabled = false;
      setStatus(`Account state change failed. ${explain(error)}`);
    } finally { busy = false; }
  }

  async function load() {
    if (busy) return;
    setStatus("Loading the authenticated Steward account and approved account roster…");
    try {
      const session = await request("/api/v1/auth/session");
      currentAccountId = String(session.identity?.account_id || "");
    } catch (_) {
      currentAccountId = "";
    }
    const [enrollments, accounts] = await Promise.all([loadEnrollments(), loadAccounts()]);
    if (enrollments.ok && accounts.ok) setStatus("Account queue and roster loaded through the existing Steward-authorized APIs.");
    else if (!enrollments.ok && !accounts.ok && enrollments.error === accounts.error) setStatus(explain(new Error(enrollments.error)));
    else setStatus("Some account administration data is unavailable; each section reports its own result.");
  }

  $("account-admin-refresh")?.addEventListener("click", load);
  window.addEventListener("rv:account-administration", load);
})();
