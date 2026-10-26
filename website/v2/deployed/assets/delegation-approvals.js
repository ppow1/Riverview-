/*
Revision: 1.3.1
Purpose: V2 request, review and revocation view over canonical Steward delegation APIs.
Authority: The Dashboard account session, CSRF check, and institutional authority registry remain authoritative.
Changed: 2026-10-26 UTC | RV-V2-DELEGATION-ACTIVATION-DURATION | Let the canonical approval transaction start the exact 24-hour grant duration.
Changed: 2026-10-26 UTC | RV-V2-CHATGPT-PRINCIPAL-REGISTRATION | Add explicit canonical service identity registration with server-only credential storage.
*/
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value == null ? "" : value).replace(/[&<>"']/g,
    (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character]));
  const time = (value) => value ? new Date(value).toLocaleString() : "Not recorded";
  const exactId = (value, prefix) => {
    if (typeof value !== "string" || !value.startsWith(prefix) || !/^[A-Za-z0-9:._-]{1,160}$/.test(value)) throw new Error("invalid_exact_authority_id");
    return value;
  };
  let loading = false;
  let requestOptions = [];
  let authorizationTypes = [];
  let unavailableTypeNote = "";

  async function request(path, method = "GET", body) {
    const headers = {Accept:"application/json"};
    if (body !== undefined) {
      const csrf = document.cookie.split(";").map((part) => part.trim())
        .find((part) => part.startsWith("rv_account_csrf="));
      if (csrf) headers["X-Riverview-CSRF"] = decodeURIComponent(csrf.slice("rv_account_csrf=".length));
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(path, {method, headers, credentials:"same-origin", cache:"no-store",
      body:body === undefined ? undefined : JSON.stringify(body)});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `http_${response.status}`);
    return result;
  }

  function explain(error) {
    if (error.message === "http_401" || error.message === "authentication_required") return "Sign in with an authenticated Steward account to review delegation requests.";
    if (error.message === "steward_identity_management_denied") return "Registration denied: this authenticated Steward lacks identity.manage at institution scope. No principal or credential was created.";
    if (error.message === "http_403" || error.message === "authenticated_steward_required" || error.message === "steward_authority_denied") return "Unavailable: this account is not the institutionally linked Steward with authority.grant at institution scope.";
    if (error.message === "http_503" || error.message === "delegation_authority_unavailable") return "The canonical delegation authority service is unavailable. No decision or revocation was made.";
    if (error.message === "protected_credential_destination_unavailable") return "Registration is unavailable because the protected server-side credential destination is not ready. No identity or credential was created.";
    if (error.message === "service_principal_registration_conflict") return "Registration could not proceed because the canonical service identity already exists in a conflicting state. No replacement credential was issued.";
    return `Request failed (${error.message}). No authority change is reported.`;
  }

  function unavailableReason(code) {
    if (code === "target_principal_not_registered_active") return "the existing Comms5 service principal is not active in the canonical identity registry";
    if (code === "codex_task_operation_not_registered") return "the active Dashboard Comms5 executor does not register the Codex task submission operation";
    if (code === "delegation_adapter_unavailable") return "the canonical delegation adapter is unavailable";
    return code || "the registered target is unavailable";
  }

  function renderAuthorizationTypeDetails() {
    const host = $("delegation-authorization-type-details");
    if (!host) return;
    host.innerHTML = authorizationTypes.map((type) => {
      const target = type.target_principal_id || "Unavailable";
      const scope = type.scope_ref || (type.scope_kind === "host"
        ? "Select an individually registered host below" : "Unavailable");
      const authority = type.action ? `<code>${esc(type.action)}</code>` :
        type.scope_kind === "host" ? "Select one registered capability and operation" : "Unavailable";
      const usage = type.usage_limits_supported === false
        ? "Unlimited uses (canonical policy)"
        : type.non_expiring_requires_usage_limit
          ? "Finite use count, expiry, or both; no-expiry grants require a finite use count"
          : "Use policy unavailable";
      const duration = type.effective_expiry_hours_after_approval
        ? `${esc(type.effective_expiry_hours_after_approval)} hours after activation`
        : type.max_expiry_days ? `Optional expiry up to ${esc(type.max_expiry_days)} days` : "Expiry policy unavailable";
      const additional = Array.isArray(type.additional_authority_required) && type.additional_authority_required.length
        ? `<p>Separate authorization remains required: ${type.additional_authority_required.map(esc).join(", ")}.</p>` : "";
      const registration = type.type_id === "comms5_codex" && type.status === "unavailable"
        ? `<p class="delegation-policy-warning">Required action: register <code>service:chatgpt</code> as an active <code>service</code> principal through the confirmed identity-management control above. This requires the authenticated Steward's <code>identity.manage</code> authority at <code>institution</code> scope. Registration alone does not grant this capability.</p>` : "";
      const state = type.status === "unavailable"
        ? `Unavailable: ${esc(unavailableReason(type.unavailable_reason))}` : "Registered authorization type";
      const hostScopes = type.scope_kind === "host" ? requestOptions.map((item) =>
        `<li><strong>${esc(item.display_name)}</strong> · <code>${esc(item.scope_ref)}</code>: ${(item.capabilities || []).map((cap) => esc(cap.capability_id)).join(", ") || "no registered operations"}</li>`).join("") : "";
      return `<article class="delegation-policy-card"><h5>${esc(type.label)} <span>${state}</span></h5><dl><dt>Principal</dt><dd><code>${esc(target)}</code></dd><dt>Capability</dt><dd>${authority}</dd><dt>Scope</dt><dd><code>${esc(scope)}</code></dd><dt>Usage</dt><dd>${usage}</dd><dt>Duration</dt><dd>${duration}</dd></dl>${hostScopes ? `<ul>${hostScopes}</ul>` : ""}${registration}${additional}</article>`;
    }).join("");
  }

  function renderChatgptRegistration(info) {
    const button = $("chatgpt-principal-register");
    const state = $("chatgpt-principal-registration-state");
    if (!button || !state || !info) return;
    if (info.status === "registered") {
      button.disabled = true;
      button.hidden = true;
      state.textContent = "service:chatgpt is active in the canonical identity registry. No credential is shown in the browser.";
      return;
    }
    button.hidden = false;
    button.disabled = info.available !== true;
    if (info.available === true) {
      state.textContent = "Registration is available. It requires identity.manage at institution scope and a separate confirmation.";
    } else if (info.unavailable_reason === "identity_manage_required") {
      state.textContent = "Registration unavailable: the authenticated Steward lacks identity.manage at institution scope.";
    } else {
      state.textContent = "Registration unavailable: the protected server-side credential destination is not ready.";
    }
  }

  async function registerChatgptPrincipal() {
    const button = $("chatgpt-principal-register");
    if (!button || button.disabled) return;
    if (!confirm("Register exactly service:chatgpt as an active service principal? This uses identity.manage at institution scope. Its one-time credential will be stored only in Riverview's protected server-side credential store and will not be shown or sent to this browser. This creates no delegation grant. Continue?")) return;
    button.disabled = true;
    const state = $("chatgpt-principal-registration-state");
    state.textContent = "Registering the confirmed service identity through the canonical Authority Registry…";
    try {
      const result = await request("/api/v1/steward/service-principals/chatgpt/register", "POST",
        {confirmation:"REGISTER service:chatgpt"});
      state.textContent = result.status === "registered"
        ? "service:chatgpt is registered. Its one-time credential was saved in the protected server-side store and was not returned to this browser. No delegation grant was created."
        : "service:chatgpt is already active. No new credential or grant was issued.";
      await refresh();
    } catch (error) {
      state.textContent = explain(error);
      button.disabled = false;
    }
  }

  function renderRequests(items) {
    const host = $("delegation-request-list");
    if (!items.length) { host.innerHTML = '<p class="delegation-empty">No delegation requests match this view.</p>'; return; }
    host.innerHTML = items.map((item) => {
      const canDecide = item.status === "pending";
      const audits = (item.audit_events || []).map((event) => `<li><code>${esc(event.event_id)}</code> · ${esc(event.event_type)} · ${esc(time(event.recorded_at))}</li>`).join("") || "<li>No linked audit event returned.</li>";
      const expiry = item.valid_until ? time(item.valid_until) : "No recorded expiry";
      return `<article class="delegation-record" id="delegation-${esc(item.request_id)}"><header><div><strong>${esc(item.request_id)}</strong><span class="delegation-state-chip" data-state="${esc(item.status)}">${esc(item.status === "rejected" ? "denied" : item.status)}</span></div><time>${esc(time(item.created_at))}</time></header><dl><dt>Requester → grantee</dt><dd>${esc(item.requester_id)} → ${esc(item.grantee_id)}</dd><dt>Requested authority</dt><dd><code>${esc(item.action)}</code> · scope <code>${esc(item.scope_ref)}</code> · policy <code>${esc(item.policy_ref)}</code></dd><dt>Justification / source reference</dt><dd>${esc(item.request_ref)}</dd><dt>Expiration / use bound</dt><dd>${esc(expiry)} · ${item.max_uses == null ? "No use-count limit recorded" : `${esc(item.max_uses)} uses`}</dd><dt>Expected request SHA-256</dt><dd><code class="delegation-hash">${esc(item.request_sha256)}</code></dd><dt>Decision / grant</dt><dd>${esc(item.decision || "No decision recorded")} · ${esc(item.grant_id || "No grant")}${item.approval_ref ? ` · ${esc(item.approval_ref)}` : ""}</dd><dt>Decision actor / time</dt><dd>${esc(item.decision_by || "Not recorded")} · ${esc(time(item.decision_at))}</dd></dl><details><summary>Audit references</summary><ul>${audits}</ul></details>${canDecide ? `<div class="delegation-actions"><button type="button" data-delegation-decision="approve" data-request-id="${esc(item.request_id)}" data-request-hash="${esc(item.request_sha256)}">Approve…</button><button type="button" class="account-admin-secondary" data-delegation-decision="reject" data-request-id="${esc(item.request_id)}" data-request-hash="${esc(item.request_sha256)}">Deny…</button></div>` : ""}</article>`;
    }).join("");
    host.querySelectorAll("[data-delegation-decision]").forEach((button) => button.addEventListener("click", () => decide(button)));
  }

  function renderGrants(items) {
    const host = $("delegation-grant-list");
    if (!items.length) { host.innerHTML = '<p class="delegation-empty">No delegated grants match this view.</p>'; return; }
    host.innerHTML = items.map((item) => {
      const audits = (item.audit_events || []).map((event) => `<li><code>${esc(event.event_id)}</code> · ${esc(event.event_type)} · ${esc(time(event.recorded_at))}</li>`).join("") || "<li>No linked audit event returned.</li>";
      const used = Number(item.used_count) || 0;
      const allowance = item.max_uses == null ? "unlimited" : String(item.max_uses);
      const remaining = item.max_uses == null ? "unlimited" : String(Math.max(0, Number(item.max_uses) - used));
      return `<article class="delegation-record"><header><div><strong>${esc(item.grant_id)}</strong><span class="delegation-state-chip" data-state="${esc(item.state)}">${esc(item.state)}</span></div><span>${esc(item.principal_id)}</span></header><dl><dt>Authority</dt><dd><code>${esc(item.action)}</code> · scope <code>${esc(item.scope_ref)}</code> · policy <code>${esc(item.policy_ref)}</code></dd><dt>Validity</dt><dd>${esc(time(item.approved_at))} → ${esc(item.valid_until ? time(item.valid_until) : "No expiry")}</dd><dt>Usage</dt><dd>${esc(used)} used of ${esc(allowance)} · ${esc(remaining)} remaining</dd><dt>Approved by</dt><dd>${esc(item.approved_by)} · ${esc(item.approval_ref || "No approval reference")}</dd><dt>Revoked at</dt><dd>${esc(time(item.revoked_at))}</dd></dl><details><summary>Audit references</summary><ul>${audits}</ul></details>${item.state === "active" ? `<div class="delegation-actions"><button type="button" class="account-admin-secondary" data-delegation-revoke="${esc(item.grant_id)}">Revoke…</button></div>` : ""}</article>`;
    }).join("");
    host.querySelectorAll("[data-delegation-revoke]").forEach((button) => button.addEventListener("click", () => revoke(button)));
  }

  async function refresh() {
    if (loading) return;
    loading = true;
    const state = $("delegation-state");
    state.textContent = "Reading the canonical delegation registry…";
    try {
      const requestStatus = $("delegation-request-filter").value;
      const grantState = $("delegation-grant-filter").value;
      const outcomes = await Promise.allSettled([
        request(`/api/v1/steward/delegation-grant-requests?status=${encodeURIComponent(requestStatus)}&limit=100`),
        request(`/api/v1/steward/delegated-grants?state=${encodeURIComponent(grantState)}&limit=100`),
        loadRequestOptions(),
      ]);
      const [requests, grants, options] = outcomes;
      if (requests.status === "fulfilled") renderRequests(requests.value.items || []);
      else $("delegation-request-list").textContent = explain(requests.reason);
      if (grants.status === "fulfilled") renderGrants(grants.value.items || []);
      else $("delegation-grant-list").textContent = explain(grants.reason);
      const counts = [
        requests.status === "fulfilled" ? `${requests.value.items.length} ${requestStatus} request(s)` : `requests unavailable (${requests.reason.message})`,
        grants.status === "fulfilled" ? `${grants.value.items.length} ${grantState} grant(s)` : `grants unavailable (${grants.reason.message})`,
        options.status === "fulfilled" ? "authorization options loaded" : `options unavailable (${options.reason.message})`,
      ];
      state.textContent = `${counts.join(" · ")}. The lists are bounded latest-100 projections.`;
    } catch (error) {
      state.textContent = explain(error);
    } finally { loading = false; }
  }

  async function loadRequestOptions() {
    const typeSelect = $("delegation-request-type");
    const hostSelect = $("delegation-request-host");
    const capabilitySelect = $("delegation-request-capability");
    const submit = $("delegation-request-submit");
    try {
      const result = await request("/api/v1/steward/delegation-grant-requests/options");
      requestOptions = Array.isArray(result.hosts) ? result.hosts : [];
      authorizationTypes = Array.isArray(result.authorization_types) ? result.authorization_types : [];
      $("delegation-request-requester").textContent = result.requester_principal_id || "Unavailable";
      renderChatgptRegistration(result.chatgpt_registration);
      typeSelect.innerHTML = '<option value="">Choose authorization type</option>' + authorizationTypes.map(item =>
        `<option value="${esc(item.type_id)}" ${item.status === "unavailable" ? "disabled" : ""}>${esc(item.label)}${item.status === "unavailable" ? " · unavailable" : ""}</option>`).join("");
      if (!$("delegation-request-expiry").value) {
        const defaultExpiry = new Date(Date.now() + 7 * 86400000);
        defaultExpiry.setMinutes(defaultExpiry.getMinutes() - defaultExpiry.getTimezoneOffset());
        $("delegation-request-expiry").value = defaultExpiry.toISOString().slice(0,16);
      }
      hostSelect.innerHTML = '<option value="">Choose a registered verified host</option>' + requestOptions.map(host =>
        `<option value="${esc(host.host_id)}">${esc(host.display_name)} · ${esc(host.scope_ref)}</option>`).join("");
      const unavailable = authorizationTypes.filter(item => item.status === "unavailable");
      unavailableTypeNote = unavailable.map(item =>
        `${item.label} unavailable: ${unavailableReason(item.unavailable_reason)}.`).join(" ");
      $("delegation-request-type-note").textContent = unavailableTypeNote;
      renderAuthorizationTypeDetails();
      updateRequestType();
      submit.disabled = true;
      return result;
    } catch (error) {
      hostSelect.innerHTML = '<option value="">Registered targets unavailable</option>';
      capabilitySelect.innerHTML = '<option value="">No request options loaded</option>';
      capabilitySelect.disabled = true;
      typeSelect.innerHTML = '<option value="">Authorization options unavailable</option>';
      submit.disabled = true;
      $("delegation-request-result").textContent = explain(error);
      throw error;
    }
  }

  function updateRequestType() {
    const type = authorizationTypes.find(item => item.type_id === $("delegation-request-type").value);
    const gpu = type?.type_id === "gpu_host";
    const codex = type?.type_id === "comms5_codex";
    $("delegation-request-host-label").hidden = !gpu;
    $("delegation-request-capability-label").hidden = !gpu;
    $("delegation-request-limit-label").hidden = !gpu;
    $("delegation-request-expiry-label").hidden = codex;
    $("delegation-request-host").required = gpu;
    $("delegation-request-capability").required = gpu;
    // Either a finite use count or an expiry is required by the canonical API.
    // A value of one is a single execution; the registry enforces the bound.
    $("delegation-request-max-uses").required = false;
    $("delegation-request-expiry").disabled = codex;
    $("delegation-request-expiry").required = !gpu && !codex;
    $("delegation-request-target").textContent = type?.target_principal_id || "Unavailable";
    if (!gpu && type?.type_id === "comms5_codex") {
      $("delegation-request-max-uses").value = "";
      const maxExpiry = new Date(Date.now() + 86400000);
      maxExpiry.setMinutes(maxExpiry.getMinutes() - maxExpiry.getTimezoneOffset());
      $("delegation-request-expiry").max = maxExpiry.toISOString().slice(0,16);
      if ($("delegation-request-expiry").value > $("delegation-request-expiry").max)
        $("delegation-request-expiry").value = $("delegation-request-expiry").max;
      $("delegation-request-type-note").textContent = "Capability comms5.operations.non_destructive.v1 · scope project:Riverview · principal service:chatgpt · unlimited use · expires 24 hours after activation. Separate objective and assignment authorization remains required for task execution. A delegation request remains pending until separately approved.";
    } else if (gpu) {
      if (!$("delegation-request-max-uses").value) $("delegation-request-max-uses").value = "1";
      $("delegation-request-expiry").removeAttribute("max");
      $("delegation-request-type-note").textContent = `${unavailableTypeNote} The selected host is validated against the registered controller. A finite use count may be used alone, an expiry may be used alone, or both may be combined. The canonical delegated-grant reservation path enforces finite use limits; unlimited non-expiring grants are rejected.`.trim();
    }
    updateCapabilities();
  }

  function updateCapabilities() {
    if ($("delegation-request-type").value !== "gpu_host") {
      const type = authorizationTypes.find(item => item.type_id === $("delegation-request-type").value);
      const select = $("delegation-request-capability");
      select.innerHTML = type ? `<option value="${esc(type.action)}">${esc(type.action)} · ${esc(type.scope_ref)}</option>` : '<option value="">Choose authorization type</option>';
      select.disabled = true;
      const requestable = type?.status !== "unavailable" && Boolean(type);
      $("delegation-request-submit").disabled = !requestable;
      return;
    }
    const host = requestOptions.find(item => item.host_id === $("delegation-request-host").value);
    const select = $("delegation-request-capability");
    select.innerHTML = host ? '<option value="">Choose exact capability and operation</option>' +
      (host.capabilities || []).map(item => `<option value="${esc(item.action)}">${esc(item.capability_id)} · ${esc(host.scope_ref)}</option>`).join("") :
      '<option value="">Select a registered host</option>';
    select.disabled = !host;
    $("delegation-request-submit").disabled = !host || !(host.capabilities || []).length;
  }

  async function submitRequest(event) {
    event.preventDefault();
    const type = authorizationTypes.find(item => item.type_id === $("delegation-request-type").value);
    const host = requestOptions.find(item => item.host_id === $("delegation-request-host").value);
    const action = $("delegation-request-capability").value;
    const purpose = $("delegation-request-purpose").value.trim();
    if (!type || purpose.length < 8) return;
    if (type.type_id === "gpu_host" && (!host || !action)) return;
    const expiryInput = $("delegation-request-expiry").value;
    const maxUsesInput = $("delegation-request-max-uses").value.trim();
    const maxUses = type.type_id === "gpu_host" && maxUsesInput ? Number(maxUsesInput) : null;
    if ((!expiryInput && type.type_id !== "gpu_host") || (!expiryInput && maxUses == null)) return;
    const validUntil = type.type_id === "comms5_codex"
      ? null
      : expiryInput ? new Date(expiryInput).toISOString() : null;
    const idempotencyKey = crypto.randomUUID();
    const button = $("delegation-request-submit");
    button.disabled = true;
    $("delegation-request-result").textContent = "Submitting to the canonical delegation registry…";
    try {
      const body = {authorization_type_id:type.type_id, action:type.type_id === "gpu_host" ? action : type.action,
        purpose, valid_until:validUntil,
        max_uses:maxUses,
        idempotency_key:idempotencyKey};
      if (type.type_id === "gpu_host") body.host_id = host.host_id;
      const result = await request("/api/v1/steward/delegation-grant-requests", "POST", body);
      const out = $("delegation-request-result");
      out.textContent = `Pending request recorded: ${result.request_id}. It does not grant authority until explicitly approved.`;
      $("delegation-request-filter").value = "pending";
      await refresh();
      const record = document.getElementById(`delegation-${result.request_id}`);
      if (record) {record.scrollIntoView({behavior:"smooth",block:"start"});record.focus({preventScroll:true});}
    } catch (error) {
      $("delegation-request-result").textContent = explain(error);
    } finally {button.disabled = false;}
  }

  async function decide(button) {
    const decision = button.dataset.delegationDecision;
    const requestId = button.dataset.requestId;
    const requestHash = button.dataset.requestHash;
    if (!confirm(`${decision === "approve" ? "Approve" : "Deny"} exactly ${requestId}? The canonical authority service will record this decision.`)) return;
    let approvalRef;
    if (decision === "approve") {
      approvalRef = prompt("Steward approval reference or justification (required):", "");
      if (!approvalRef || !approvalRef.trim()) { $("delegation-state").textContent = "Approval not submitted: an approval reference is required."; return; }
    }
    button.disabled = true;
    $("delegation-state").textContent = `Submitting ${decision} for ${requestId}…`;
    try {
      const body = {decision, expected_request_sha256:requestHash, idempotency_key:crypto.randomUUID()};
      if (approvalRef) body.approval_ref = approvalRef.trim();
      const result = await request(`/api/v1/steward/delegation-grant-requests/${exactId(requestId, "delegation-request:")}/decision`, "POST", body);
      $("delegation-state").textContent = `${result.status} recorded for ${result.request_id}; grant ${result.grant_id || "not issued"}. Refreshing audit state…`;
      await refresh();
    } catch (error) { $("delegation-state").textContent = explain(error); button.disabled = false; }
  }

  async function revoke(button) {
    const grantId = button.dataset.delegationRevoke;
    if (!confirm(`Revoke exactly ${grantId}? This uses the canonical authority registry and appends an audit event.`)) return;
    button.disabled = true;
    try {
      const result = await request(`/api/v1/steward/delegated-grants/${exactId(grantId, "grant:")}/revoke`, "POST", {confirm:true, reason_code:"steward_revoked"});
      $("delegation-state").textContent = `Grant ${result.grant_id} revoked by the canonical authority registry. Refreshing…`;
      await refresh();
    } catch (error) { $("delegation-state").textContent = explain(error); button.disabled = false; }
  }

  // workspace.js dispatches this while its deferred script is initializing,
  // before DOMContentLoaded. Register now so direct links to this view load too.
  window.addEventListener("rv:resident-permissions", refresh);

  document.addEventListener("DOMContentLoaded", () => {
    $("delegation-refresh")?.addEventListener("click", refresh);
    $("delegation-request-filter")?.addEventListener("change", refresh);
    $("delegation-grant-filter")?.addEventListener("change", refresh);
    $("delegation-request-type")?.addEventListener("change", updateRequestType);
    $("delegation-request-host")?.addEventListener("change", updateCapabilities);
    $("delegation-request-form")?.addEventListener("submit", submitRequest);
    $("chatgpt-principal-register")?.addEventListener("click", registerChatgptPrincipal);
  });
})();
