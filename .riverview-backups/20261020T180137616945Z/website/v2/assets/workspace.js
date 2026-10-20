/* Riverview~ Controlled Document | File: website/v2/assets/workspace.js | Component: RIVERVIEW-V2-WORKSPACE-SHELL | File Revision: 1.0.0 | Purpose: In-memory navigation and fixture rendering | Authority: Presentation only; no external data access or mutation | Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Initial preview behavior */
(() => {
  "use strict";
  const fixtures = window.RIVERVIEW_V2_FIXTURES;
  const labels = { overview: "Workspace overview", residents: "Residents", work: "Work", resources: "Resources", knowledge: "Knowledge" };
  const nav = document.getElementById("primary-nav");
  const area = document.getElementById("view-content");
  const title = document.getElementById("page-title");
  const heading = document.getElementById("view-heading");
  let currentResident = fixtures.residents[0];

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
  render("overview");
})();
