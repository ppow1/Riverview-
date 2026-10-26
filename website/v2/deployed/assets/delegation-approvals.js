/*
Revision: 1.1.0
Purpose: V2 request, review and revocation view over canonical Steward delegation APIs.
Authority: The Dashboard account session, CSRF check, and institutional authority registry remain authoritative.
Changed: 2026-10-26 UTC | RV-V2-DELEGATION-PROJECTION-001 | Add request decisions, grant inspection and confirmed revoke controls.
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
    if (error.message === "http_403" || error.message === "authenticated_steward_required" || error.message === "steward_authority_denied") return "Unavailable: this account is not the institutionally linked Steward with authority.grant at institution scope.";
    if (error.message === "http_503" || error.message === "delegation_authority_unavailable") return "The canonical delegation authority service is unavailable. No decision or revocation was made.";
    return `Request failed (${error.message}). No authority change is reported.`;
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
      return `<article class="delegation-record"><header><div><strong>${esc(item.grant_id)}</strong><span class="delegation-state-chip" data-state="${esc(item.state)}">${esc(item.state)}</span></div><span>${esc(item.principal_id)}</span></header><dl><dt>Authority</dt><dd><code>${esc(item.action)}</code> · scope <code>${esc(item.scope_ref)}</code> · policy <code>${esc(item.policy_ref)}</code></dd><dt>Validity</dt><dd>${esc(time(item.approved_at))} → ${esc(item.valid_until ? time(item.valid_until) : "No expiry")}</dd><dt>Usage</dt><dd>${esc(item.used_count)} / ${item.max_uses == null ? "unlimited" : esc(item.max_uses)}</dd><dt>Approved by</dt><dd>${esc(item.approved_by)} · ${esc(item.approval_ref || "No approval reference")}</dd><dt>Revoked at</dt><dd>${esc(time(item.revoked_at))}</dd></dl><details><summary>Audit references</summary><ul>${audits}</ul></details>${item.state === "active" ? `<div class="delegation-actions"><button type="button" class="account-admin-secondary" data-delegation-revoke="${esc(item.grant_id)}">Revoke…</button></div>` : ""}</article>`;
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
      const [requests, grants] = await Promise.all([
        request(`/api/v1/steward/delegation-grant-requests?status=${encodeURIComponent(requestStatus)}&limit=100`),
        request(`/api/v1/steward/delegated-grants?state=${encodeURIComponent(grantState)}&limit=100`),
      ]);
      renderRequests(requests.items || []);
      renderGrants(grants.items || []);
      state.textContent = `Loaded ${requests.items.length} ${requestStatus} request(s) and ${grants.items.length} ${grantState} grant(s) from canonical authority. The display is a bounded latest-100 projection.`;
      await loadRequestOptions();
    } catch (error) {
      $("delegation-request-list").textContent = explain(error);
      $("delegation-grant-list").textContent = explain(error);
      state.textContent = explain(error);
    } finally { loading = false; }
  }

  async function loadRequestOptions() {
    const hostSelect = $("delegation-request-host");
    const capabilitySelect = $("delegation-request-capability");
    const submit = $("delegation-request-submit");
    try {
      const result = await request("/api/v1/steward/delegation-grant-requests/options");
      requestOptions = Array.isArray(result.hosts) ? result.hosts : [];
      $("delegation-request-requester").textContent = result.requester_principal_id || "Unavailable";
      $("delegation-request-target").textContent = result.target_principal_id || "Unavailable";
      hostSelect.innerHTML = '<option value="">Choose a registered verified host</option>' + requestOptions.map(host =>
        `<option value="${esc(host.host_id)}">${esc(host.display_name)} · ${esc(host.scope_ref)}</option>`).join("");
      updateCapabilities();
      submit.disabled = !requestOptions.length;
    } catch (error) {
      hostSelect.innerHTML = '<option value="">Registered targets unavailable</option>';
      capabilitySelect.innerHTML = '<option value="">No request options loaded</option>';
      capabilitySelect.disabled = true;
      submit.disabled = true;
      $("delegation-request-result").textContent = explain(error);
    }
  }

  function updateCapabilities() {
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
    const host = requestOptions.find(item => item.host_id === $("delegation-request-host").value);
    const action = $("delegation-request-capability").value;
    const purpose = $("delegation-request-purpose").value.trim();
    if (!host || !action || purpose.length < 8) return;
    const days = Number($("delegation-request-expiry").value);
    const validUntil = new Date(Date.now() + days * 86400000).toISOString();
    const idempotencyKey = crypto.randomUUID();
    const button = $("delegation-request-submit");
    button.disabled = true;
    $("delegation-request-result").textContent = "Submitting to the canonical delegation registry…";
    try {
      const result = await request("/api/v1/steward/delegation-grant-requests", "POST", {
        host_id:host.host_id, action, purpose, valid_until:validUntil, idempotency_key:idempotencyKey,
      });
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
    $("delegation-request-host")?.addEventListener("change", updateCapabilities);
    $("delegation-request-form")?.addEventListener("submit", submitRequest);
  });
})();
