// Revision: 1.0.0
/* Reusable, read-only Living Roadmap view over canonical planning references and protected work state. */
// File Revision: 1.0.0
(() => {
  "use strict";
  const data = window.RiverviewV2LivingRoadmapData;
  const adapter = window.RiverviewV2LivingRoadmapAdapter;
  if (!data || !adapter) return;
  const statusMeta = {
    active: ["●", "Active"], in_progress: ["◐", "In progress"], stalled: ["Ⅱ", "Stalled"],
    blocked: ["⚑", "Blocked"], waiting: ["◷", "Waiting"], parked: ["◇", "Parked"],
    canceled: ["×", "Canceled"], completed: ["✓", "Completed"], unknown: ["?", "Unknown"]
  };
  const $ = (id) => document.getElementById(id);
  const state = {objectives: [], status: "not_checked", fetchedAt: null, loading: false};
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text != null) element.textContent = String(text);
    return element;
  };
  const statusNode = (status) => {
    const safe = statusMeta[status] ? status : "unknown";
    const badge = node("span", null, `roadmap-status roadmap-status-${safe}`);
    badge.title = statusMeta[safe][1];
    badge.setAttribute("aria-label", statusMeta[safe][1]);
    badge.append(node("span", statusMeta[safe][0], "roadmap-status-icon"), node("span", statusMeta[safe][1]));
    return badge;
  };
  const priorityNode = (priority) => node("span", priority === "unassigned" ? "Priority unassigned" : `Priority ${priority}`, `roadmap-priority roadmap-priority-${priority}`);
  function renderLegend() {
    const legend = $("roadmap-status-legend");
    legend.replaceChildren();
    Object.keys(statusMeta).forEach((status) => legend.append(statusNode(status)));
  }
  function links(parent, items) {
    const list = node("div", null, "roadmap-links");
    for (const item of items || []) {
      const link = node("a", item.label);
      link.href = item.href;
      if (item.href.startsWith("#")) link.dataset.roadmapView = item.href.slice(1);
      else { link.target = "_blank"; link.rel = "noopener noreferrer"; }
      list.append(link);
    }
    if (list.childElementCount) parent.append(list);
  }
  function card(item, live = false) {
    const details = node("details", null, "roadmap-item");
    details.dataset.status = item.status;
    details.dataset.stage = item.stage;
    details.title = `${item.summary} · ${item.stage}`;
    const summary = node("summary", null, "roadmap-item-summary");
    summary.append(statusNode(item.status), node("strong", item.title, "roadmap-item-title"), priorityNode(item.priority));
    details.append(summary);
    const body = node("div", null, "roadmap-item-body");
    body.append(node("p", live ? "Verified live operational record · Live execution evidence from the authenticated objective projection; not a roadmap milestone." : (item.evidenceLabel || (item.status === "completed" ? "Historical delivery evidence" : item.status === "parked" ? "Documented Parking Lot intent" : "Documented roadmap intent · not live execution status")), live ? "roadmap-evidence-label" : "roadmap-record-kind"));
    const meta = node("p", null, "roadmap-item-meta");
    meta.append(node("span", item.workstream || (live ? "Current Riverview objective" : "Planning item")),
      node("span", `Stage: ${item.stage}`));
    body.append(meta, node("p", item.detail || item.summary));
    if (!live) {
      const facts = node("dl", null, "roadmap-item-facts");
      const addFact = (label, value) => { facts.append(node("dt", label), node("dd", value || "Not recorded in the roadmap summary; consult the linked source.")); };
      addFact("Priority", item.sourcePriority ? `${item.priority === "unassigned" ? "Unassigned" : item.priority} · source: ${item.sourcePriority}` : item.priority === "unassigned" ? "Unassigned in source" : item.priority);
      addFact("Lifecycle stage", item.stage || "Not recorded in source"); addFact("Dependencies", item.dependencies); addFact("Blockers", item.blockers); body.append(facts);
    } else {
      const facts = node("dl", null, "roadmap-live-facts");
      const addFact = (label, value) => { facts.append(node("dt", label), node("dd", value || "Unavailable in this API projection")); };
      addFact("Authoritative lifecycle stage", item.stage); addFact("Assignment state", item.assignmentState);
      addFact(item.status === "blocked" || item.status === "waiting" ? "Recorded blocker / waiting reason" : "Blocker", item.blocker);
      addFact("Dependencies", item.dependencies || "Not exposed by the authenticated objective API; none inferred.");
      addFact("Latest event", item.latestEvent?.type ? `${item.latestEvent.type}${item.latestEvent.occurredAt ? ` · ${new Date(item.latestEvent.occurredAt).toLocaleString()}` : " · timestamp unavailable"}` : "No event returned by the API.");
      if (item.verification) addFact("Latest verification", `${item.verification.decision || "Decision unavailable"}${item.verification.summary ? ` · ${item.verification.summary}` : ""}`);
      body.append(facts); if (item.fullRequest) body.append(node("p", `Full objective request: ${item.fullRequest}`, "roadmap-full-request"));
    }
    if (item.sourcePriority) body.append(node("p", `Source priority: ${item.sourcePriority} (the source board does not use P0–P3).`));
    if (item.tags?.length) {
      const tags = node("div", null, "roadmap-tags");
      item.tags.forEach((tag) => tags.append(node("span", `#${tag}`, "roadmap-tag")));
      body.append(tags);
    }
    links(body, item.links);
    details.append(body);
    return details;
  }
  function fillTagFilter() {
    const select = $("roadmap-tag");
    const selected = select.value;
    const tags = [...new Set(["live", "objective", "engineering", ...data.items.flatMap((item) => item.tags || [])])].sort();
    select.replaceChildren(new Option("All tags", ""), ...tags.map((tag) => new Option(`#${tag}`, tag)));
    if (tags.includes(selected)) select.value = selected;
  }
  function renderStatic() {
    const workstreams = $("roadmap-workstreams");
    workstreams.replaceChildren();
    const filters = {query:$("roadmap-search")?.value || "", tag:$("roadmap-tag")?.value || "", priority:$("roadmap-priority")?.value || ""};
    const filtered = adapter.filterItems(data.items, filters);
    const parents = data.items.filter((entry) => ["grace-autonomy", "website-visualization"].includes(entry.id));
    for (const item of parents) {
      const milestones = filtered.filter((entry) => entry.workstream === item.workstream && entry.id !== item.id);
      if (!filtered.some((entry) => entry.id === item.id) && !milestones.length) continue;
      const section = node("article", null, "roadmap-workstream-card");
      const heading = node("div", null, "roadmap-workstream-heading");
      heading.append(node("h4", item.workstream), statusNode(item.status), priorityNode(item.priority));
      section.append(heading, node("p", item.summary));
      const more = node("details", null, "roadmap-workstream-detail");
      more.append(node("summary", "Workstream notes"), node("p", item.detail));
      links(more, item.links);
      section.append(more);
      const milestoneTitle = node("h5", "Goals & milestones", "roadmap-milestone-heading");
      section.append(milestoneTitle);
      if (milestones.length) milestones.forEach((milestone) => section.append(card(milestone)));
      else section.append(node("p", "No milestones match the current filters.", "roadmap-empty"));
      workstreams.append(section);
    }
    if (!workstreams.childElementCount) workstreams.append(node("p", "No workstreams match the current filters.", "roadmap-empty"));
  }
  function renderLive() {
    const target = $("roadmap-live-items");
    target.replaceChildren();
    const current = state.objectives.map((item) => ({...adapter.objective(item), workstream:"Current Riverview objective", priority:"unassigned", tags:["live", "objective", "engineering"]}));
    const currentMatches = adapter.filterItems(current, {
      query: $("roadmap-search")?.value || "",
      tag: $("roadmap-tag")?.value || "",
      priority: $("roadmap-priority")?.value || ""
    });
    for (const match of currentMatches) {
      const raw = state.objectives.find((item) => item.objective_id === match.objectiveId) || {};
      const view = adapter.objective(raw);
      const item = {
        ...view, workstream:"Current Riverview objective", priority:"unassigned", tags:["live", "objective", "engineering"],
        assignmentState:view.assignmentState,
        evidenceLabel:state.status === "available" ? "Verified live operational record · authenticated Riverview objective projection (not a canonical roadmap item)." : "Stale last-read operational record · refresh to verify current status.",
        detail:[view.summary, view.updatedAt ? `Last updated ${new Date(view.updatedAt).toLocaleString()}.` : "Updated time unavailable."].join(" "),
        links:[
          ...(view.objectiveId ? [{label:"Open objective record", href:`/api/v1/objectives/${encodeURIComponent(view.objectiveId).replaceAll("%3A", ":")}`}] : []),
          ...(view.assignmentId ? [{label:"Open related work record", href:`/api/v1/assignments/${encodeURIComponent(view.assignmentId)}`}] : []),
          {label:"Work view", href:"#work"}
        ]
      };
      target.append(card(item, true));
    }
    if (!target.childElementCount) target.append(node("p", state.status === "available"
      ? "The authorized objective projection returned no records matching these filters."
      : "No current work records are shown. Check the source status above.", "roadmap-empty"));
  }
  async function refresh() {
    if (state.loading) return;
    state.loading = true;
    const label = $("roadmap-live-status");
    label.textContent = "Checking Steward authorization…";
    $("roadmap-source-state").textContent = "Checking authenticated source…";
    try {
      const session = await fetch("/api/v1/auth/session", {credentials:"same-origin", cache:"no-store"});
      if (!session.ok) {
        state.objectives = [];
        state.status = session.status === 401 ? "authentication_required" : `session_http_${session.status}`;
        label.textContent = session.status === 401 ? "Sign in through the existing Riverview account session to see active objective state." : `Session source unavailable (HTTP ${session.status}).`;
        $("roadmap-source-state").textContent = session.status === 401 ? "SIGN IN REQUIRED" : "SOURCE UNAVAILABLE";
        return;
      }
      const identity = (await session.json()).identity || {};
      if (!Array.isArray(identity.roles) || !identity.roles.includes("steward")) {
        state.objectives = [];
        state.status = "steward_authorization_required";
        label.textContent = "Current operational objectives require the existing Steward role. Planning references remain viewable.";
        $("roadmap-source-state").textContent = "STEWARD ROLE REQUIRED";
        return;
      }
      const response = await fetch("/api/v1/objectives?limit=25", {credentials:"same-origin", cache:"no-store", headers:{Accept:"application/json"}});
      const body = await response.json().catch(() => ({}));
      if (!response.ok || body.status !== "available" || !Array.isArray(body.items)) throw new Error(`objective_source_${response.status || body.status || "unavailable"}`);
      state.objectives = body.items.slice(0, 25);
      state.status = "available";
      state.fetchedAt = body.observed_at || new Date().toISOString();
      label.textContent = `Authenticated objective projection available · ${state.objectives.length} records · read at ${new Date(state.fetchedAt).toLocaleString()}${body.truncated ? " · first page only" : ""}. Workstream and priority links are not supplied by this API.`;
      $("roadmap-source-state").textContent = `LIVE OBJECTIVES · ${new Date(state.fetchedAt).toLocaleTimeString()}`;
    } catch (error) {
      state.status = state.objectives.length ? "stale" : "unavailable";
      label.textContent = `Current objective data unavailable (${String(error.message).replace(/[^a-z0-9_.-]/gi, "_")}). Planning stage is not a live work status.`;
      $("roadmap-source-state").textContent = state.status === "stale" ? "STALE · LAST READ RETAINED" : "SOURCE UNAVAILABLE";
    } finally {
      state.loading = false;
      renderLive();
    }
  }
  function render() {
    renderLegend();
    fillTagFilter();
    renderStatic();
  }
  document.addEventListener("DOMContentLoaded", () => {
    ["roadmap-search", "roadmap-tag", "roadmap-priority"].forEach((id) => $(id)?.addEventListener(id.endsWith("search") ? "input" : "change", () => { renderStatic(); renderLive(); }));
    $("roadmap-refresh")?.addEventListener("click", refresh);
    $("roadmap-live-details")?.addEventListener("toggle", (event) => {
      if (event.target.open && state.status === "not_checked") refresh();
    });
    $("living-roadmap-workspace")?.addEventListener("click", (event) => {
      const link = event.target.closest("a[data-roadmap-view]");
      if (!link) return;
      event.preventDefault();
      if (link.dataset.roadmapView === "grace") {
        document.querySelector('#primary-nav [data-view="residents"]')?.click();
        const grace = [...document.querySelectorAll(".resident-row")].find((row) =>
          row.getAttribute("aria-label")?.includes("authenticated Grace conversation"));
        grace?.click();
        return;
      }
      const target = link.dataset.roadmapView;
      document.querySelector(`#primary-nav [data-view="${CSS.escape(target)}"]`)?.click();
    });
  });
  window.RiverviewV2LivingRoadmap = Object.freeze({render, refresh});
})();
