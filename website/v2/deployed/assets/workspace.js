/*
Riverview~ Controlled Source
File: website/v2/deployed/assets/workspace.js
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.4.0
Purpose: Render workspace navigation, resident selection, and V2 monitor views
Execution Model: Interactive browser event handlers; page lifecycle is browser-owned
Observability: Selected view and resident state in DOM; Snapshot reports the active view
Dependencies: Browser DOM APIs and window.RIVERVIEW_V2_FIXTURES
Inputs/Outputs: User navigation/selection; renders fixture or authenticated-chat workspace
Authority: Presentation only; Grace messages use the separate Dashboard-granted client
Changed: 2026-10-21 UTC | RV-V2-CAPABILITY-INTEGRATION-P1 | Route the existing Work view to live read-only objective and assignment status
Changed: 2026-10-23 UTC | RV-V2-MANUAL-IMAGE-GENERATION-248 | Add the authenticated image-generation workspace navigation state.
Changed: 2026-10-23 UTC | RV-V2-MANUAL-IMAGE-GENERATION-248 | Preserve the deployed V2 source under its explicit production bundle path.
Changed: 2026-10-25 UTC | RV-V2-INSTITUTIONAL-PROPOSALS-20261025 | Route the read-only proposal registry through the existing authenticated API.
Changed: 2026-10-25 UTC | RV-V2-RESIDENT-PERMISSIONS-20261025 | Add V2 navigation to the existing resident permission profile API.
Changed: 2026-10-25 UTC | RV-V2-ACCOUNT-SESSION-ADMIN-20261025 | Route the bounded account administration view through the existing account APIs.
Changed: 2026-10-25 UTC | RV-V2-BATCH1-20261025 | Add the live authority-backed Residents view and tabbed central Settings workspace.
Changed: 2026-10-26 UTC | RV-V2-LIVE-OVERVIEW-20261026 | Route Overview to live operational projections and suppress obsolete workspace fixture summaries.
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: tests/test_v2_workspace_shell.py, scripts/verify_v2_workspace_mobile.cjs
History: Git and revision/backup manifest
*/
(() => {
  "use strict";
  const fixtures = window.RIVERVIEW_V2_FIXTURES;
  const labels = { overview: "Operational overview", residents: "Residents", settings: "Settings", work: "Work and Engineering Progress", "institutional-proposals": "Institutional proposals", "resident-permissions": "Resident permissions", "account-administration": "Account administration", "process-workflows": "Process workflows", documentation: "Documentation and diagnostics", roadmap: "Living Roadmap", "image-generation": "Manual image generation", resources: "Hardware & AI resources", knowledge: "Knowledge", communications: "Communications activity", "notification-settings": "Notification settings", grace: "Grace conversation" };
  const nav = document.getElementById("primary-nav");
  const area = document.getElementById("view-content");
  const title = document.getElementById("page-title");
  const heading = document.getElementById("view-heading");
  const content = document.getElementById("workspace-main");
  let currentResident = fixtures.residents[0];
  let currentView = "overview";
  const shell = document.querySelector(".app-shell");
  const themes = ["light", "dark", "system"];
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const readTheme = () => { try { const value = localStorage.getItem("rv.v2.theme"); return themes.includes(value) ? value : "system"; } catch (_) { return "system"; } };
  const applyTheme = (choice) => {
    const effective = choice === "system" ? (media.matches ? "dark" : "light") : choice;
    document.documentElement.dataset.theme = effective;
    document.getElementById("theme-select").value = choice;
    const settingsTheme = document.getElementById("settings-theme-select");
    if (settingsTheme) settingsTheme.value = choice;
    try { localStorage.setItem("rv.v2.theme", choice); } catch (_) { /* Theme remains active for this page. */ }
  };
  const sidebarStates = ["expanded", "compact", "hidden"];
  const setSidebar = (side, state) => {
    shell.dataset[`${side}State`] = state;
    try { localStorage.setItem(`rv.v2.sidebar.${side}`, state); } catch (_) { /* Sidebar remains set for this page. */ }
    const sidebar = document.getElementById(`${side}-sidebar`);
    if (sidebar) sidebar.dataset.state = state;
    const restore = document.getElementById(`${side}-restore`);
    restore.hidden = state !== "hidden";
    const button = document.getElementById(`${side}-state`);
    button.setAttribute("aria-label", `Change ${side} sidebar state (currently ${state})`);
    button.dataset.tooltip = `${side === "left" ? "Navigation" : "Context panel"}: ${state}; activate to cycle`;
  };
  const initTooltips = () => document.querySelectorAll("[data-tooltip]").forEach((node) => {
    node.setAttribute("title", node.dataset.tooltip);
    node.setAttribute("aria-description", node.dataset.tooltip);
  });
  applyTheme(readTheme());
  media.addEventListener?.("change", () => { if (readTheme() === "system") applyTheme("system"); });
  document.getElementById("theme-select").addEventListener("change", (event) => applyTheme(event.target.value));
  const readSidebar = (side) => { try { const value = localStorage.getItem(`rv.v2.sidebar.${side}`); return sidebarStates.includes(value) ? value : "expanded"; } catch (_) { return "expanded"; } };
  setSidebar("left", readSidebar("left")); setSidebar("right", readSidebar("right"));
  window.RiverviewV2WorkspacePreferences = Object.freeze({setSidebar, getSidebar:(side) => shell.dataset[`${side}State`] || "expanded", applyTheme});
  for (const side of ["left", "right"]) {
    document.getElementById(`${side}-state`).addEventListener("click", () => {
      const current = shell.dataset[`${side}State`];
      setSidebar(side, sidebarStates[(sidebarStates.indexOf(current) + 1) % sidebarStates.length]);
    });
    document.getElementById(`${side}-restore`).addEventListener("click", () => setSidebar(side, "expanded"));
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
  const updateResidentContext = (resident) => {
    const target = document.getElementById("selected-resident");
    target.querySelector(".avatar").textContent = resident.initials;
    target.querySelector(".avatar").className = `avatar ${resident.realIdentity ? "grace" : "fixture"}`;
    target.querySelector("b").textContent = resident.name;
    target.querySelector("small").textContent = resident.role;
    target.dataset.tooltip = resident.realIdentity ? "Open Residents to select Grace's authenticated conversation" : "Selected synthetic preview resident; no live conversation is connected";
    target.setAttribute("aria-label", `Selected resident: ${resident.name}. Open resident directory`);
    initTooltips();
  };
  const render = (view) => {
    if (currentView === "settings" && view !== "settings") window.RiverviewV2AuthorityExplorer?.restoreSettingsPanels();
    currentView = view;
    content.dataset.currentView = view;
    title.textContent = labels[view] || labels.residents;
    const isGrace = view === "grace";
    const isCommunications = view === "communications";
    const isResources = view === "resources";
    const isWork = view === "work";
    const isRoadmap = view === "roadmap";
    const isProposals = view === "institutional-proposals";
    const isResidentPermissions = view === "resident-permissions";
    const isAccountAdministration = view === "account-administration";
    const isImageGeneration = view === "image-generation";
    const isNotificationSettings = view === "notification-settings";
    const isProcessWorkflows = view === "process-workflows";
    const isDocumentation = view === "documentation";
    const isResidents = view === "residents";
    const isSettings = view === "settings";
    document.querySelector(".welcome-row").hidden = isRoadmap || isResidents || isSettings;
    document.getElementById("snapshot-status").hidden = isRoadmap || isResidents || isSettings;
    document.getElementById("overview-content").hidden = isGrace || isResources || isImageGeneration || isNotificationSettings || isRoadmap || isProposals || isResidentPermissions || isAccountAdministration || isProcessWorkflows || isDocumentation || isResidents || isSettings;
    document.getElementById("website-verification").hidden = view !== "overview";
    document.getElementById("overview-live").hidden = view !== "overview";
    document.getElementById("operational-drilldown-heading").hidden = view === "overview";
    document.getElementById("manual-image-workspace").hidden = !isImageGeneration;
    document.getElementById("grace-workspace").hidden = !isGrace;
    document.getElementById("communications-workspace").hidden = !isCommunications;
    document.getElementById("resource-monitor-workspace").hidden = !isResources;
    document.getElementById("work-monitor-workspace").hidden = !isWork;
    document.getElementById("notification-settings-workspace").hidden = !isNotificationSettings;
    document.getElementById("living-roadmap-workspace").hidden = !isRoadmap;
    document.getElementById("institutional-proposals-workspace").hidden = !isProposals;
    document.getElementById("resident-permissions-workspace").hidden = !isResidentPermissions;
    document.getElementById("account-administration-workspace").hidden = !isAccountAdministration;
    document.getElementById("process-workflows-workspace").hidden = !isProcessWorkflows;
    document.getElementById("documentation-workspace").hidden = !isDocumentation;
    document.getElementById("resident-directory-workspace").hidden = !isResidents;
    document.getElementById("capability-registry-workspace").hidden = true;
    document.getElementById("settings-workspace").hidden = !isSettings;
    area.hidden = view === "overview" || isWork;
    heading.textContent = labels[view] || labels.residents;
    if (view !== "grace" && !isCommunications && !isResources && !isNotificationSettings && !isRoadmap && !isProposals && !isResidentPermissions && !isAccountAdministration && !isProcessWorkflows && !isDocumentation && !isResidents && !isSettings) {
      area.replaceChildren();
      if (view === "overview") {
        const list = el("div", "list-stack");
        fixtures.residents.forEach((resident) => {
          const item = card(resident, "resident-row");
          item.dataset.residentId = resident.id;
          item.tabIndex = 0;
          item.setAttribute("role", "button");
          item.setAttribute("aria-label", `Select ${resident.name}${resident.realIdentity ? " to open the authenticated Grace conversation" : " preview record"}`);
          item.setAttribute("aria-pressed", String(resident.id === currentResident.id));
          if (resident.id === currentResident.id) item.classList.add("selected");
          item.addEventListener("click", () => selectResident(resident));
          item.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectResident(resident); }
          });
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
    }
    if (view === "overview") window.RiverviewV2Overview?.render();
    if (isResources) window.RiverviewV2ResourceMonitor?.render();
    if (isWork) window.RiverviewV2WorkMonitor?.render();
    if (isRoadmap) window.RiverviewV2LivingRoadmap?.render();
    if (isProposals) window.RiverviewV2InstitutionalProposals?.render();
    if (isResidentPermissions) window.dispatchEvent(new Event("rv:resident-permissions"));
    if (isAccountAdministration) window.dispatchEvent(new Event("rv:account-administration"));
    if (isCommunications) window.RiverviewV2Communications?.render();
    if (isNotificationSettings) window.RiverviewV2NotificationSettings?.render();
    if (isProcessWorkflows || isDocumentation) window.dispatchEvent(new CustomEvent("rvv2:view", { detail: { view } }));
    if (isResidents) window.RiverviewV2AuthorityExplorer?.renderResidents();
    if (isSettings) {
      const settingsTheme = document.getElementById("settings-theme-select");
      if (settingsTheme) settingsTheme.value = document.getElementById("theme-select").value;
      const selectedTab = document.querySelector('[role="tab"][aria-selected="true"][data-settings-tab]')?.dataset.settingsTab || "preferences";
      window.RiverviewV2AuthorityExplorer?.activateSettingsTab(selectedTab);
    }
    document.querySelectorAll(".nav-item").forEach((button) => {
      const active = button.dataset.view === view || (view === "grace" && button.dataset.view === "residents");
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    });
    initTooltips();
    document.dispatchEvent(new CustomEvent("rvv2:view", { detail: { view } }));
  };
  const dateNode = document.getElementById("v2-current-date");
  if (dateNode) dateNode.textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "long", month: "long", day: "numeric", year: "numeric"
  }).format(new Date()).toUpperCase();
  const selectResident = (resident) => {
    currentResident = resident;
    updateResidentContext(resident);
    document.querySelectorAll(".resident-row").forEach((row) => {
      const selected = row.dataset.residentId === resident.id;
      row.classList.toggle("selected", selected);
      row.setAttribute("aria-pressed", String(selected));
    });
    render(resident.realIdentity ? "grace" : "residents");
    document.dispatchEvent(new CustomEvent("rvv2:resident", { detail: { residentId: resident.id } }));
  };
  nav.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-view]");
    if (button) {
      render(button.dataset.view);
      document.querySelector(".rail").classList.remove("mobile-open");
    }
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("button.inline-view-link[data-view]");
    if (button) render(button.dataset.view);
  });
  document.getElementById("selected-resident").addEventListener("click", () => render("residents"));
  document.getElementById("mobile-menu").addEventListener("click", () => document.querySelector(".rail").classList.toggle("mobile-open"));
  updateResidentContext(currentResident);
  initTooltips();
  render("overview");
})();
