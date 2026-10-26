/*
Revision: 1.0.0
Purpose: V2 view over existing account enrollment, roster, and session APIs.
Authority: Dashboard account service remains authoritative for Steward role, CSRF, and audit checks.
Changed: 2026-10-25 UTC | RV-V2-ACCOUNT-EMAIL-20261025 | Reuse the existing encrypted shared-email settings APIs.
*/
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const escape = (value) => String(value == null ? "" : value).replace(/[&<>"']/g,
    (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character]));
  let busy = false;
  let currentAccountId = "";
  let emailSettingsConfigured = false;

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
        const roleControls = self
          ? `<span class="account-admin-control-note">Role changes are unavailable for your current account.</span>`
          : account.disabled
            ? `<span class="account-admin-control-note">Enable this account before changing roles.</span>`
          : ["viewer", "operator", "steward"].map((role) => {
            const grant = !roles.includes(role);
            return `<button type="button" class="account-admin-secondary" data-account-role="${escape(account.account_id)}" data-role="${role}" data-grant="${grant}" data-account-email="${escape(account.email)}">${grant ? "Grant " : "Remove "}${role}</button>`;
          }).join("");
        const grantControl = account.grant_revoked
          ? `<span class="account-admin-control-note">Access grant revoked</span>`
          : self
            ? `<button type="button" class="account-admin-secondary" disabled title="Stewards cannot revoke their own access grant">Cannot revoke own grant</button>`
            : `<button type="button" class="account-admin-secondary" data-revoke-grant="${escape(account.account_id)}" data-account-email="${escape(account.email)}">Revoke access grant</button>`;
        const stateControl = self && !disabled
          ? `<button type="button" class="account-admin-secondary" disabled title="Stewards cannot disable their own account">Cannot disable own account</button>`
          : `<button type="button" class="${disabled ? "account-admin-secondary" : "account-admin-danger"}" data-account-state="${escape(account.account_id)}" data-disabled="${disabled}" data-account-email="${escape(account.email)}">${disabled ? "Enable account" : "Disable account"}</button>`;
        return `<article class="account-admin-row"><div class="account-admin-record"><strong>${escape(account.email)}</strong><span>${escape(metadata.join(" · "))}</span></div><div class="account-admin-actions"><button type="button" class="account-admin-secondary" data-revoke-sessions="${escape(account.account_id)}" data-account-email="${escape(account.email)}">Revoke sessions</button>${stateControl}${grantControl}${roleControls}</div></article>`;
      }).join("") : `<p class="account-admin-empty">No approved accounts were returned.</p>`;
      host.querySelectorAll("[data-revoke-sessions]").forEach((button) => button.addEventListener("click", () => revokeSessions(button)));
      host.querySelectorAll("[data-account-state]").forEach((button) => button.addEventListener("click", () => setAccountState(button)));
      host.querySelectorAll("[data-account-role]").forEach((button) => button.addEventListener("click", () => changeAccountRole(button)));
      host.querySelectorAll("[data-revoke-grant]").forEach((button) => button.addEventListener("click", () => revokeAccessGrant(button)));
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

  async function changeAccountRole(button) {
    if (busy) return;
    const role = button.dataset.role;
    const grant = button.dataset.grant === "true";
    const email = button.dataset.accountEmail || "this account";
    const action = grant ? `Grant ${role}` : `Remove ${role} from`;
    const prompt = `${action} ${email}? The account service will record the role change${grant ? "." : " and revoke active sessions."}`;
    if (!window.confirm(prompt)) return;
    busy = true; button.disabled = true;
    try {
      await request(`/api/v1/account/users/${encodeURIComponent(button.dataset.accountRole)}/roles`,
        "POST", {role, grant});
      setStatus(`Role ${grant ? "granted" : "removed"}; the existing account service recorded the change.`);
      await loadAccounts();
    } catch (error) {
      button.disabled = false;
      setStatus(`Role change failed. ${explain(error)}`);
    } finally { busy = false; }
  }

  async function revokeAccessGrant(button) {
    if (busy) return;
    const email = button.dataset.accountEmail || "this account";
    if (!window.confirm(`Revoke the access grant for ${email}? This blocks future sign-ins, revokes active sessions, and records the change in account audit history.`)) return;
    busy = true; button.disabled = true;
    try {
      await request(`/api/v1/account/users/${encodeURIComponent(button.dataset.revokeGrant)}/grant`,
        "POST", {revoked:true});
      setStatus("Access grant revoked; the existing account service recorded the change and invalidated sessions.");
      await loadAccounts();
    } catch (error) {
      button.disabled = false;
      setStatus(`Access-grant change failed. ${explain(error)}`);
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
    await loadEmailSettings();
  }

  async function loadEmailSettings() {
    try {
      const value = await request("/api/v1/account/email-settings");
      emailSettingsConfigured = value.configured === true;
      const status = value.configured
        ? `Configured · ${value.delivery_status || "delivery untested"}${value.last_test_at ? ` · tested ${formatTime(value.last_test_at)}` : ""}`
        : "Not configured";
      $("email-config-status").textContent = status;
      for (const [id,key] of [["smtp-host","smtp_host"],["smtp-port","smtp_port"],
        ["smtp-tls-mode","tls_mode"],["sender-email","sender_email"],
        ["sender-name","sender_name"],["admin-email","admin_email"],
        ["reply-to-email","reply_to_email"],["smtp-username","smtp_username"]]) {
        $(id).value = value[key] ?? (id === "smtp-port" ? 587 : id === "smtp-tls-mode" ? "starttls" : "");
      }
      $("smtp-password").value = "";
      $("smtp-password-state").textContent = value.password_configured
        ? "Stored securely; blank retains it" : "Not configured";
      $("test-email-settings").disabled = !emailSettingsConfigured;
      $("email-settings-message").textContent = value.last_test_error
        ? `Last test error: ${value.last_test_error}` : "The password is never returned by this API.";
    } catch (error) {
      emailSettingsConfigured = false;
      $("email-config-status").textContent = `Unavailable (${error.message})`;
      $("email-settings-message").textContent = explain(error);
      $("smtp-password").value = "";
      $("test-email-settings").disabled = true;
    }
  }

  $("refresh-email-settings")?.addEventListener("click", loadEmailSettings);
  $("email-settings-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    const settings = {
      smtp_host:$("smtp-host").value.trim(), smtp_port:Number($("smtp-port").value),
      tls_mode:$("smtp-tls-mode").value, sender_email:$("sender-email").value.trim(),
      sender_name:$("sender-name").value.trim(), admin_email:$("admin-email").value.trim(),
      reply_to_email:$("reply-to-email").value.trim(), smtp_username:$("smtp-username").value.trim(),
      password:$("smtp-password").value,
    };
    if (!window.confirm("Save shared email delivery settings? This affects account verification and institutional email. A blank password retains the existing stored password.")) return;
    busy = true; $("save-email-settings").disabled = true;
    try {
      const result = await request("/api/v1/account/email-settings", "PUT", settings);
      $("email-config-status").textContent = `Saved · ${result.delivery_status || "delivery untested"}`;
      $("email-settings-message").textContent = "Settings saved by the existing account service.";
      await loadEmailSettings();
    } catch (error) {
      $("email-settings-message").textContent = `Save failed. ${explain(error)}`;
      $("smtp-password").value = "";
    } finally { busy = false; $("save-email-settings").disabled = false; }
  });
  $("test-email-settings")?.addEventListener("click", async () => {
    if (busy) return;
    const recipient = $("admin-email").value.trim() || "the configured administrator address";
    if (!window.confirm(`Send one test email to ${recipient} using the configured SMTP relay?`)) return;
    busy = true; $("test-email-settings").disabled = true;
    try {
      const result = await request("/api/v1/account/email-settings/test", "POST");
      $("email-settings-message").textContent = result.delivery_status === "sent"
        ? "The SMTP relay accepted the test. Confirm receipt at the configured mailbox."
        : `Test delivery failed (${result.error || "unknown"}).`;
      await loadEmailSettings();
    } catch (error) {
      $("email-settings-message").textContent = `Test unavailable. ${explain(error)}`;
    } finally { busy = false; $("test-email-settings").disabled = !emailSettingsConfigured; }
  });

  $("account-admin-refresh")?.addEventListener("click", load);
  window.addEventListener("rv:account-administration", load);
})();
