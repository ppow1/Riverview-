// Riverview~ controlled asset; component STEWARD-DASHBOARD.
// Revision: 1.0.0
// Task: RV-GRACE-DUAL-CAPABILITY-001
// Purpose: Present the existing authenticated institutional proposal lifecycle to Steward users.
// Authority: Server-side account session, CSRF validation, proposal registry and exact objective.submit grant.
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? "—").replace(/[&<>"']/g,
    (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const api = (...args) => {
    if (typeof window.RiverviewSnapshotApi !== "function") throw new Error("dashboard_api_unavailable");
    return window.RiverviewSnapshotApi(...args);
  };
  let selected = null;
  let current = null;

  function setActionButtons(enabled) {
    document.querySelectorAll("[data-proposal-decision]").forEach((button) => { button.disabled = !enabled; });
    $("proposal-revise").disabled = !enabled;
    $("proposal-promote").disabled = !enabled;
    $("proposal-content").disabled = !enabled;
  }

  async function loadList() {
    $("proposal-state").textContent = "Loading…";
    try {
      const query = new URLSearchParams({q:$("proposal-search").value.trim(), limit:"50"});
      if ($("proposal-status-filter").value) query.set("status", $("proposal-status-filter").value);
      const page = await api(`/api/v1/institutional-proposals?${query}`);
      const rows = page.items || [];
      $("proposal-list").innerHTML = rows.length ? rows.map((item) =>
        `<button class="row" type="button" data-proposal-id="${esc(item.proposal_id)}"><strong>${esc(item.title)}</strong><span class="pill">${esc(item.lifecycle_status)}</span><span class="row-meta">${esc(item.proposal_id)} · revision ${esc(item.current_revision)}</span><span class="row-meta">${esc(item.summary)}</span></button>`).join("") : `<div class="row row-meta">No matching institutional proposals.</div>`;
      $("proposal-state").textContent = `${rows.length} proposal(s) · ${esc(page.status)}`;
      $("proposal-list").querySelectorAll("[data-proposal-id]").forEach((button) =>
        button.addEventListener("click", () => loadDetail(button.dataset.proposalId)));
    } catch (error) {
      $("proposal-state").textContent = `Unavailable (${error.payload?.error || error.message})`;
    }
  }

  async function loadDetail(proposalId, revision) {
    $("proposal-detail-state").textContent = "Loading revision…";
    setActionButtons(false);
    try {
      const suffix = revision ? `?revision=${encodeURIComponent(revision)}` : "";
      const response = await api(`/api/v1/institutional-proposals/${encodeURIComponent(proposalId)}${suffix}`);
      current = response.proposal || response;
      const record = current.proposal || current;
      const rev = current.revision || record.revision;
      if (!rev || !record.proposal_id) throw new Error("proposal_response_invalid");
      selected = {id:record.proposal_id, revision:rev.revision,
        digest:rev.content_sha256, status:rev.lifecycle_status || record.lifecycle_status};
      $("proposal-detail-title").textContent = `${rev.title || record.proposal_id} · revision ${rev.revision}`;
      $("proposal-detail-state").textContent = `${selected.status || "status unavailable"} · ${record.privacy_classification || "privacy not classified"}`;
      const links = current.work_orders || [];
      const reviewRows = (current.reviews || []).map((item) =>
        `<div class="row"><span>${esc(item.review_outcome)}</span><span>${esc(item.reviewer_principal)}</span><span class="row-meta">${esc(item.findings)}</span></div>`).join("");
      $("proposal-detail").innerHTML = `<p>${esc(rev.summary)}</p><p class="row-meta">ID ${esc(record.proposal_id)} · creator ${esc(record.created_by)} · content SHA-256 ${esc(rev.content_sha256)}</p><h4>Reviews</h4>${reviewRows || `<p class="row-meta">No review records for this revision.</p>`}<h4>Engineering links</h4>${links.length ? links.map((item) => `<div class="row">${esc(item.objective_id)} · ${esc(item.objective_status)} · assignment ${esc(item.assignment_id)}</div>`).join("") : `<p class="row-meta">No objective created from this proposal revision.</p>`}`;
      const content = Object.fromEntries(["title","summary","objective","scope","proposed_approach","constraints","acceptance_criteria","tags"].map((key) => [key, rev[key]]));
      $("proposal-content").value = JSON.stringify(content, null, 2);
      $("proposal-action-state").textContent = "";
      setActionButtons(true);
    } catch (error) {
      current = selected = null;
      $("proposal-detail-state").textContent = `Unavailable (${error.payload?.error || error.message})`;
      $("proposal-detail").textContent = "Proposal revision could not be loaded.";
    }
  }

  async function draftSelectedMessage() {
    const dialog = $("proposal-draft-dialog");
    const sequence = Number(dialog.dataset.sourceSequence);
    if (!Number.isInteger(sequence) || !/^[0-9a-f-]{36}$/i.test(localStorage.getItem("rv.grace.conversation") || "")) {
      $("proposal-draft-error").textContent = "Select a persisted Steward message in an active Grace conversation.";
      return;
    }
    const button = $("proposal-draft-submit");
    button.disabled = true;
    $("proposal-draft-error").textContent = "Saving DRAFT…";
    try {
      const conversationId = localStorage.getItem("rv.grace.conversation");
      const result = await api("/api/v1/institutional-proposals", 30000, "POST", {body:{
        conversation_id:conversationId, source_sequences:[sequence],
        idempotency_key:`dashboard-proposal:${conversationId}:${sequence}`,
        instruction:$("proposal-draft-instruction").value.trim()}});
      if (result.status === "clarification_required") {
        $("proposal-draft-error").textContent = `Grace needs clarification: ${result.question || result.message || "review the conversation and retry"}`;
        return;
      }
      dialog.close();
      window.RiverviewDashboardNavigate?.("institutional-proposals");
      await loadList();
      if (result.proposal?.proposal_id) await loadDetail(result.proposal.proposal_id);
      else if (result.proposal_id) await loadDetail(result.proposal_id);
    } catch (error) {
      $("proposal-draft-error").textContent = `Draft was not confirmed (${error.payload?.error || error.message}).`;
    } finally { button.disabled = false; }
  }

  async function revise() {
    if (!selected) return;
    const content = JSON.parse($("proposal-content").value);
    await api(`/api/v1/institutional-proposals/${encodeURIComponent(selected.id)}`, 15000, "PUT", {
      body:{expected_revision:selected.revision, content}});
    await loadDetail(selected.id);
    await loadList();
  }

  async function decide(decision) {
    if (!selected) return;
    const reason = $("proposal-reason").value.trim();
    if (!reason) throw new Error("decision_reason_required");
    const purpose = $("proposal-purpose").value.trim();
    if (decision === "APPROVE" && !purpose) throw new Error("approved_purpose_required");
    const body = {revision:selected.revision, decision, reason,
      idempotency_key:`dashboard-proposal-decision:${selected.id}:${selected.revision}:${crypto.randomUUID()}`,
      content_sha256:selected.digest};
    if (decision === "APPROVE") body.approved_purpose = purpose;
    await api(`/api/v1/institutional-proposals/${encodeURIComponent(selected.id)}/decision`,
      15000, "POST", {body});
    await loadDetail(selected.id);
    await loadList();
  }

  async function promote() {
    if (!selected) return;
    const result = await api(`/api/v1/institutional-proposals/${encodeURIComponent(selected.id)}/work-orders`,
      15000, "POST", {body:{revision:selected.revision}});
    $("proposal-action-state").textContent = `Objective ${result.objective_id} · ${result.status}; execution and assignment authorization remain separate.`;
    await loadDetail(selected.id);
    await loadList();
  }

  async function runAction(action) {
    $("proposal-action-state").textContent = "";
    try { await action(); }
    catch (error) { $("proposal-action-state").textContent = `Action not confirmed (${error.payload?.error || error.message}).`; }
  }
  document.addEventListener("rv:institutional-proposals", loadList);
  $("refresh-proposals").addEventListener("click", loadList);
  $("proposal-search-submit").addEventListener("click", loadList);
  $("proposal-search").addEventListener("keydown", (event) => { if (event.key === "Enter") loadList(); });
  $("proposal-draft-submit").addEventListener("click", draftSelectedMessage);
  $("proposal-revise").addEventListener("click", () => runAction(revise));
  document.querySelectorAll("[data-proposal-decision]").forEach((button) =>
    button.addEventListener("click", () => runAction(() => decide(button.dataset.proposalDecision))));
  $("proposal-promote").addEventListener("click", () => runAction(promote));
})();
