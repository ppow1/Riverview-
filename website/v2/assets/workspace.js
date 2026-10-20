/*
Riverview~ Controlled Source
File: website/v2/assets/workspace.js
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.2
Purpose: Render in-memory navigation and fixture selection
Execution Model: Interactive browser event handlers; page lifecycle is browser-owned
Observability: Visible selected context and browser events; no operational health endpoint
Dependencies: Browser DOM APIs and window.RIVERVIEW_V2_FIXTURES
Inputs/Outputs: User clicks/keys; updates local DOM and in-memory resident selection
Authority: Presentation only; no fetch, external service, credential, or persistent write
Changed: 2026-10-20 UTC | RV-WEB-V2-USABILITY-001 | Persist theme selection and independently cycle/restore three sidebar states
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: tests/test_v2_workspace_shell.py, scripts/verify_v2_workspace_browser.py, scripts/verify_v2_workspace_mobile.cjs
History: Git and revision/backup manifest
*/
(() => {
  "use strict";
  const fixtures = window.RIVERVIEW_V2_FIXTURES;
  const labels = { overview: "Workspace overview", residents: "Residents", work: "Work", resources: "Resources", knowledge: "Knowledge" };
  const nav = document.getElementById("primary-nav");
  const area = document.getElementById("view-content");
  const title = document.getElementById("page-title");
  const heading = document.getElementById("view-heading");
  let currentResident = fixtures.residents[0];
  const shell = document.querySelector(".app-shell");
  const themes = ["light", "dark", "system"];
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const readTheme = () => { try { const value=localStorage.getItem("rv.v2.theme"); return themes.includes(value)?value:"system"; } catch (_) { return "system"; } };
  const applyTheme = (choice) => {
    const effective = choice === "system" ? (media.matches ? "dark" : "light") : choice;
    document.documentElement.dataset.theme = effective;
    document.getElementById("theme-select").value = choice;
    try { localStorage.setItem("rv.v2.theme", choice); } catch (_) { /* Theme remains active for this page. */ }
  };
  const sidebarStates = ["expanded", "compact", "hidden"];
  const setSidebar = (side, state) => {
    shell.dataset[`${side}State`] = state;
    const sidebar=document.getElementById(`${side}-sidebar`);
    if (sidebar) sidebar.dataset.state=state;
    const restore=document.getElementById(`${side}-restore`);
    restore.hidden=state!=="hidden";
    const button=document.getElementById(`${side}-state`);
    button.setAttribute("aria-label",`Change ${side} sidebar state (currently ${state})`);
    button.dataset.tooltip=`${side === "left" ? "Navigation" : "Context panel"}: ${state}; activate to cycle`;
  };
  const initTooltips = () => document.querySelectorAll("[data-tooltip]").forEach((node) => { node.setAttribute("title",node.dataset.tooltip); node.setAttribute("aria-description",node.dataset.tooltip); });
  applyTheme(readTheme());
  media.addEventListener?.("change",()=>{if(readTheme()==="system")applyTheme("system");});
  document.getElementById("theme-select").addEventListener("change",(event)=>applyTheme(event.target.value));
  setSidebar("left","expanded"); setSidebar("right","expanded");
  for (const side of ["left","right"]) {
    document.getElementById(`${side}-state`).addEventListener("click",()=>{const states=sidebarStates;const current=shell.dataset[`${side}State`];setSidebar(side,states[(states.indexOf(current)+1)%states.length]);});
    document.getElementById(`${side}-restore`).addEventListener("click",()=>setSidebar(side,"expanded"));
  }

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const card = (item, extra = "") => {
    const row = el("article", `list-card ${extra}`);
    const dot = el("span", "item-mark", "·");
    const body = el("div", "list-card-body");
    body.append(el("h3", "", item.name || item.title), el("p", "", item.role || item.detail));
    const meta = el("span", "item-meta", item.status || item.state || item.kind);
    row.append(dot, body, meta);
    return row;
  };
  const render = (view) => {
    title.textContent = labels[view];
    heading.textContent = view === "overview" ? "Resident directory" : labels[view];
    area.replaceChildren();
    if (view === "overview" || view === "residents") {
      const list = el("div", "list-stack");
      fixtures.residents.forEach((resident) => {
        const item = card(resident, "resident-row");
        item.dataset.residentId = resident.id;
        item.tabIndex = 0;
        item.setAttribute("role", "button");
        item.setAttribute("aria-label", `Select ${resident.name}`);
        if (resident.id === currentResident.id) item.classList.add("selected");
        item.addEventListener("click", () => selectResident(resident));
        item.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectResident(resident); } });
        list.append(item);
      });
      area.append(list);
    } else if (view === "work") {
      const list = el("div", "list-stack");
      fixtures.work.forEach((item) => list.append(card(item)));
      area.append(list);
    } else {
      const list = el("div", "list-stack");
      fixtures[view].forEach((item) => list.append(card(item)));
      area.append(list);
    }
    document.querySelectorAll(".nav-item").forEach((button) => {
      const active = button.dataset.view === view;
      button.classList.toggle("active", active);
      button.setAttribute("aria-current", active ? "page" : "false");
    });
    initTooltips();
    document.dispatchEvent(new CustomEvent("rvv2:view", { detail: { view } }));
  };
  const selectResident = (resident) => {
    currentResident = resident;
    const target = document.getElementById("selected-resident");
    target.querySelector(".avatar").textContent = resident.initials;
    target.querySelector(".avatar").className = `avatar ${resident.realIdentity ? "grace" : "fixture"}`;
    target.querySelector("b").textContent = resident.name;
    target.querySelector("small").textContent = resident.role;
    document.querySelectorAll(".resident-row").forEach((row) => row.classList.toggle("selected", row.dataset.residentId === resident.id));
    document.dispatchEvent(new CustomEvent("rvv2:resident", { detail: { residentId: resident.id } }));
  };
  nav.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-view]");
    if (button) render(button.dataset.view);
  });
  document.getElementById("conversation-toggle").addEventListener("click", (event) => {
    const note = document.getElementById("conversation-note");
    const open = note.hidden;
    note.hidden = !open;
    event.currentTarget.setAttribute("aria-expanded", String(open));
    event.currentTarget.firstChild.textContent = open ? "Hide context note " : "Show context note ";
  });
  document.getElementById("mobile-menu").addEventListener("click", () => document.querySelector(".rail").classList.toggle("mobile-open"));
  initTooltips();
  render("overview");
})();
