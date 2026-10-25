// Revision: 1.1.0
/* V2 client for existing authenticated proposal reads and exact-revision Steward decisions. */
// Changed: 2026-10-25 UTC | RV-V2-PROPOSAL-DECISION-20261025 | Add explicitly confirmed, digest-bound Steward decisions without exposing revision or promotion writes.
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const adapter = window.RiverviewV2ProposalAdapter;
  const root = $("institutional-proposals-workspace");
  if (!root || !adapter) return;
  let listGeneration = 0;
  let selectedId = null;
  let loaded = false;
  const element = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== null && text !== undefined) item.textContent = String(text);
    if (className) item.className = className;
    return item;
  };
  const formatTime = (value) => {
    const date = new Date(value || "");
    return Number.isNaN(date.valueOf()) ? "Time unavailable" : date.toLocaleString();
  };
  async function get(path) {
    const response = await fetch(path, {method:"GET", credentials:"same-origin", cache:"no-store", headers:{Accept:"application/json"}});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(body.error || `http_${response.status}`);
      error.status = response.status;
      throw error;
    }
    return body;
  }
  async function post(path, payload) {
    const cookie = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("rv_account_csrf="));
    if (!cookie) throw new Error("csrf_token_missing");
    const response = await fetch(path, {method:"POST", credentials:"same-origin", cache:"no-store",
      headers:{Accept:"application/json", "Content-Type":"application/json",
        "X-Riverview-CSRF":decodeURIComponent(cookie.slice("rv_account_csrf=".length))},
      body:JSON.stringify(payload)});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(body.error || `http_${response.status}`);
      error.status = response.status;
      throw error;
    }
    return body;
  }
  function unavailable(error) {
    if (error.status === 401) return "Sign in to Riverview with an authorized Steward account to read proposal records.";
    if (error.status === 403) return "Access denied. This registry requires Steward account and institutional authority.";
    if (error.status === 503) return "The existing institutional proposal registry is unavailable.";
    return `Proposal records could not be loaded (${String(error.message || "unavailable").replace(/[^a-z0-9_.-]/gi, "_")}).`;
  }
  function renderRows(items) {
    const target = $("proposal-list");
    target.replaceChildren();
    for (const raw of items) {
      const item = adapter.listItem(raw);
      if (!item.proposalId) continue;
      const button = element("button", null, "proposal-row");
      button.type = "button";
      button.dataset.proposalId = item.proposalId;
      button.setAttribute("aria-pressed", String(item.proposalId === selectedId));
      const heading = element("span", null, "proposal-row-heading");
      heading.append(element("strong", item.title), element("span", item.status, "proposal-state-pill"));
      const meta = element("span", `Revision ${item.revision ?? "unavailable"} · updated ${formatTime(item.updatedAt)}`, "proposal-row-meta");
      button.append(heading, meta, element("span", item.summary, "proposal-row-summary"));
      button.addEventListener("click", () => loadDetail(item.proposalId));
      target.append(button);
    }
    if (!target.childElementCount) target.append(element("p", "No proposals match this search and lifecycle filter.", "proposal-empty"));
  }
  function addField(target, label, value) {
    target.append(element("dt", label), element("dd", value || "Not recorded in this proposal revision."));
  }
  function renderDetail(detail) {
    const target = $("proposal-detail");
    target.replaceChildren();
    const heading = element("h4", `${detail.title} · revision ${detail.revision ?? "unavailable"}`);
    target.append(heading);
    const fields = document.createElement("dl");
    fields.className = "proposal-fields";
    addField(fields, "Lifecycle status", detail.status);
    addField(fields, "Proposal ID", detail.proposalId);
    addField(fields, "Summary", detail.summary);
    addField(fields, "Objective", detail.objective);
    addField(fields, "Scope", detail.scope);
    addField(fields, "Proposed approach", detail.proposedApproach);
    addField(fields, "Constraints", detail.constraints);
    addField(fields, "Acceptance criteria", detail.acceptanceCriteria.length ? detail.acceptanceCriteria.map((item, i) => `${i + 1}. ${item}`).join("\n") : null);
    addField(fields, "Tags", detail.tags.length ? detail.tags.join(", ") : null);
    addField(fields, "Source references", detail.sourceReferences.length ? detail.sourceReferences.map((ref) => typeof ref === "string" ? ref : JSON.stringify(ref)).join("\n") : null);
    target.append(fields);
    const reviews = element("section", null, "proposal-evidence");
    reviews.append(element("h4", "Review history"));
    if (!detail.reviews.length) reviews.append(element("p", "No review records were returned for this revision."));
    for (const review of detail.reviews) {
      const card = element("article", null, "proposal-evidence-card");
      card.append(element("strong", review.outcome || "Review outcome unavailable"));
      card.append(element("p", [review.office, review.findings, review.conditions.join(" · ")].filter(Boolean).join(" · ") || "No findings recorded."));
      card.append(element("small", formatTime(review.recordedAt)));
      reviews.append(card);
    }
    target.append(reviews);
    const links = element("section", null, "proposal-evidence");
    links.append(element("h4", "Linked engineering work"));
    if (!detail.workOrders.length) links.append(element("p", "No work orders are linked to this proposal revision."));
    for (const item of detail.workOrders) {
      const record = element("p", `${item.objectiveId || "Objective unavailable"} · ${item.objectiveStatus || "status unavailable"} · assignment ${item.assignmentId || "unavailable"}`);
      links.append(record);
    }
    target.append(links);
    const events = element("section", null, "proposal-evidence");
    events.append(element("h4", "Recorded lifecycle events"));
    if (!detail.events.length) events.append(element("p", "No lifecycle events were returned."));
    for (const event of detail.events) events.append(element("p", `${event.type || "Event type unavailable"} · revision ${event.revision ?? "unavailable"} · ${formatTime(event.occurredAt)}`));
    target.append(events);
    renderDecisionControls(target, detail);
  }
  function renderDecisionControls(target, detail) {
    const panel = element("section", null, "proposal-decision-panel");
    panel.append(element("h4", "Steward decision on this exact revision"));
    const allowedStates = new Set(["DRAFT", "READY_FOR_REVIEW", "UNDER_REVIEW", "READY_FOR_STEWARD_DECISION"]);
    if (!allowedStates.has(detail.status) || !detail.revision || !/^[a-f0-9]{64}$/.test(detail.contentSha256 || "")) {
      panel.append(element("p", `No V2 decision is offered for ${detail.status || "the unavailable lifecycle state"}. The existing server remains authoritative for eligibility.`));
      target.append(panel);
      return;
    }
    panel.append(element("p", `The existing decision API validates Steward institutional authority, current lifecycle, revision ${detail.revision}, and its content digest. Approval does not create or dispatch an Engineering work order.`));
    const decisionLabel = element("label", "Decision");
    const decision = document.createElement("select");
    decision.id = "proposal-decision-choice";
    decision.required = true;
    decision.append(new Option("Choose a decision", ""));
    if (detail.status === "READY_FOR_STEWARD_DECISION") decision.append(new Option("Approve", "APPROVE"));
    decision.append(new Option("Request changes", "REQUEST_CHANGES"), new Option("Defer", "DEFER"), new Option("Reject", "REJECT"));
    decisionLabel.append(decision);
    const reasonLabel = element("label", "Required audit reason");
    const reason = document.createElement("textarea");
    reason.id = "proposal-decision-reason";
    reason.maxLength = 1000;
    reason.required = true;
    reason.rows = 3;
    reasonLabel.append(reason);
    const purposeLabel = element("label", "Approved purpose (required for approval)");
    const purpose = document.createElement("input");
    purpose.id = "proposal-approved-purpose";
    purpose.type = "text";
    purpose.maxLength = 1000;
    purposeLabel.append(purpose);
    decision.addEventListener("change", () => { purposeLabel.hidden = decision.value !== "APPROVE"; });
    purposeLabel.hidden = true;
    const submit = element("button", "Review and record decision");
    submit.type = "button";
    submit.className = "proposal-decision-submit";
    submit.addEventListener("click", async () => {
      const choice = decision.value;
      const auditReason = reason.value.trim();
      const approvedPurpose = purpose.value.trim();
      if (!choice) { $("proposal-detail-status").textContent = "Choose a decision first."; return; }
      if (!auditReason) { $("proposal-detail-status").textContent = "Enter the required audit reason."; return; }
      if (choice === "APPROVE" && !approvedPurpose) { $("proposal-detail-status").textContent = "Enter the approved purpose before approval."; return; }
      const confirmation = `Record ${choice} for proposal ${detail.proposalId}, revision ${detail.revision}? This will append an auditable Steward decision.`;
      if (!window.confirm(confirmation)) return;
      submit.disabled = true;
      $("proposal-detail-status").textContent = "Submitting the exact-revision decision to Riverview…";
      const body = {revision:detail.revision, decision:choice, reason:auditReason,
        idempotency_key:`v2-proposal-decision:${detail.proposalId}:${detail.revision}:${crypto.randomUUID()}`,
        content_sha256:detail.contentSha256};
      if (choice === "APPROVE") body.approved_purpose = approvedPurpose;
      try {
        await post(`/api/v1/institutional-proposals/${encodeURIComponent(detail.proposalId)}/decision`, body);
        await refresh();
        await loadDetail(detail.proposalId);
        $("proposal-detail-status").textContent = `Steward decision ${choice} recorded for revision ${detail.revision}.`;
      } catch (error) {
        $("proposal-detail-status").textContent = error.status === 403
          ? "Decision denied: this session lacks the required institutional Steward authority. No decision was recorded."
          : error.status === 409
            ? "Decision not recorded: the proposal lifecycle or exact revision changed. Refresh the record before retrying."
            : `Decision not confirmed (${String(error.message || "unavailable").replace(/[^a-z0-9_.-]/gi, "_")}). No success is claimed.`;
      } finally { submit.disabled = false; }
    });
    panel.append(decisionLabel, reasonLabel, purposeLabel, submit);
    target.append(panel);
  }
  async function refresh() {
    const generation = ++listGeneration;
    selectedId = null;
    $("proposal-detail").replaceChildren();
    $("proposal-detail-status").textContent = "Select a proposal record to inspect its revision and evidence.";
    $("proposal-status").textContent = "Reading the existing proposal registry…";
    const params = new URLSearchParams({q:$("proposal-search").value.trim(), limit:"50"});
    if ($("proposal-status-filter").value) params.set("status", $("proposal-status-filter").value);
    try {
      const page = await get(`/api/v1/institutional-proposals?${params}`);
      if (generation !== listGeneration) return;
      if (page.status !== "available" || !Array.isArray(page.items)) throw new Error("proposal_projection_invalid");
      renderRows(page.items);
      $("proposal-status").textContent = `${page.items.length} proposal records · refreshed ${new Date().toLocaleTimeString()}.`;
      loaded = true;
    } catch (error) {
      if (generation !== listGeneration) return;
      $("proposal-list").replaceChildren(element("p", unavailable(error), "proposal-empty"));
      $("proposal-status").textContent = unavailable(error);
      loaded = false;
    }
  }
  async function loadDetail(proposalId) {
    selectedId = proposalId;
    for (const row of $("proposal-list").querySelectorAll("[data-proposal-id]")) row.setAttribute("aria-pressed", String(row.dataset.proposalId === proposalId));
    $("proposal-detail-status").textContent = "Loading authorized proposal revision and evidence…";
    $("proposal-detail").replaceChildren();
    try {
      const payload = await get(`/api/v1/institutional-proposals/${encodeURIComponent(proposalId)}`);
      const detail = adapter.detail(payload);
      if (!detail.proposalId || !detail.revision) throw new Error("proposal_detail_invalid");
      renderDetail(detail);
      $("proposal-detail-status").textContent = `${detail.status || "Status unavailable"} · revision ${detail.revision}`;
    } catch (error) {
      $("proposal-detail-status").textContent = unavailable(error);
    }
  }
  function render() { if (!loaded) refresh(); }
  $("proposal-refresh").addEventListener("click", refresh);
  $("proposal-search-submit").addEventListener("click", refresh);
  $("proposal-search").addEventListener("keydown", (event) => { if (event.key === "Enter") refresh(); });
  $("proposal-status-filter").addEventListener("change", refresh);
  window.RiverviewV2InstitutionalProposals = Object.freeze({render, refresh});
})();
