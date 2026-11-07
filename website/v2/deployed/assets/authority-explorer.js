/*
Riverview~ Controlled Source
File: website/v2/deployed/assets/authority-explorer.js
Component: RIVERVIEW-V2-AUTHORITY-EXPLORER
Revision: 1.0.1
Changed: 2026-10-26 UTC | RV-V2-CHAT-VISION-20261026 | Link the verified Grace resident record to its authorized conversation workspace.
Purpose: Render current residents and searchable capabilities/resources from the existing authenticated Authority API
Authority: No grants or operations are created; server-side permission evaluation and execution checks remain authoritative
Evidence: Historical reference data is source-pinned in resident-history-reference.json and is explicitly non-authoritative for current status
*/
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  let payload = null;
  let history = null;
  let loading = null;
  let settingsTab = "preferences";
  const showError = (error) => error.message === "http_401" || error.message === "http_403" ?
    "A signed-in Steward with the existing institutional authority is required. No directory or registry data was exposed." :
    "The authoritative directory and registry are unavailable. Refresh to retry; no status was inferred.";
  async function load(force = false) {
    if (payload && history && !force) return {payload, history};
    if (!loading) loading = (async () => {
      const [api, refs] = await Promise.all([
        fetch("/api/v1/resident-permissions", {credentials:"same-origin", cache:"no-store", headers:{Accept:"application/json"}}),
        fetch("assets/resident-history-reference.json", {credentials:"same-origin", cache:"no-store", headers:{Accept:"application/json"}}),
      ]);
      if (!api.ok) throw new Error("http_" + api.status);
      if (!refs.ok) throw new Error("history_reference_unavailable");
      const [current, historical] = await Promise.all([api.json(), refs.json()]);
      if (!window.RVResidentPermissionsModel) throw new Error("authority_adapter_unavailable");
      payload = current; history = historical;
      return {payload, history};
    })().finally(() => { loading = null; });
    return loading;
  }
  const profileName = (p) => {
    const explicit = p.display_name || p.name || p.resident_name;
    if (explicit) return explicit;
    const principal = p.principal_id || "Resident identity";
    return principal.startsWith("resident:") ? principal.slice("resident:".length).replace(/[-_]+/g," ").replace(/\b\w/g, (x) => x.toUpperCase()) : principal;
  };
  const liveCard = (p, catalog) => {
    const effective = Array.isArray(p.effective_permissions) ? p.effective_permissions : [];
    const grants = Array.isArray(p.standing_grants) ? p.standing_grants : [];
    const identity = p.identity_status || "unknown";
    const office = p.office_role || p.office_id || p.office || "Office unavailable";
    const role = p.office_role || p.role || p.title || "Role unavailable in the current resident API";
    const caps = effective.length ? effective.map((x) => {
      const cap = catalog.capability(x.capability_id);
      const liveStatus = cap ? catalog.status(x.capability_id) : "unavailable in active catalog";
      return `${esc(x.effective_status || "unknown")} · ${esc(cap?.description || x.capability_id)} — ${esc(x.access_level || "access unavailable")} @ ${esc(x.resource_id || "scope unavailable")} · exact grant ${esc(x.exact_grant_status || "not supplied")} · catalog ${esc(liveStatus)}${x.condition ? " · " + esc(x.condition) : ""}`;
    }).join("</li><li>") : "No effective-permission evaluations were returned by the authority API.";
    return `<article class="authority-card"><h3>${esc(profileName(p))}</h3><p class="authority-state">Current Riverview authority record · identity ${esc(identity)}</p>${(p.office_id||p.office_role)==="office:grace"?'<button type="button" data-open-resident-chat="office:grace">Open Grace conversation</button>':""}<dl><dt>Principal</dt><dd>${esc(p.principal_id || "Unavailable")}</dd><dt>Office</dt><dd>${esc(office)}</dd><dt>Role</dt><dd>${esc(role)}</dd><dt>Identity lifecycle</dt><dd>${esc(identity)}</dd><dt>Permission profile</dt><dd>${esc(p.status || "not configured")} · ${esc(p.tier || "no tier recorded")}</dd></dl><h4>Effective permissions</h4><ul><li>${caps}</li></ul><p>${grants.length} exact-grant record(s) returned; see Resident Permissions for inherited rules, restrictions, conditions, and audit history. This is discovery, not proof that a future invocation will succeed.</p></article>`;
  };
  const historicalCard = (r) => `<article class="authority-card historical"><h3>${esc(r.name)}</h3><p class="authority-state">${esc(r.reference_state || "Historical reference · current state unknown")}</p><dl><dt>Documented office</dt><dd>${esc(r.office || "not recorded")}</dd><dt>Documented scope</dt><dd>${esc(r.description || r.capabilities || "No capability detail recorded")}</dd><dt>Current Riverview access</dt><dd>No current principal or grants were established from this historical record.</dd></dl>${r.conflict ? `<p class="authority-conflict">Source conflict: ${esc(r.conflict)}</p>` : ""}<a href="${esc(r.source)}" target="_blank" rel="noopener noreferrer">Open pinned source record</a></article>`;
  const renderResidents = async (force = false) => {
    const state = $("resident-directory-status");
    if (!state) return;
    state.textContent = "Checking the protected Authority API…";
    try {
      const data = await load(force);
      const catalog = window.RVResidentPermissionsModel.create(data.payload);
      const query = ($("resident-directory-search").value || "").trim().toLowerCase();
      const live = (data.payload.profiles || []).filter((p) => JSON.stringify(p).toLowerCase().includes(query) || profileName(p).toLowerCase().includes(query));
      $("resident-directory-live").innerHTML = live.map((p) => liveCard(p, catalog)).join("") || "<p>No current resident authority records match.</p>";
      const refs = data.history.records || [];
      const hist = refs.filter((r) => JSON.stringify(r).toLowerCase().includes(query));
      $("resident-history-notice").textContent = data.history.notice || "Historical source-pinned records; current authority is not inferred.";
      $("resident-directory-history").innerHTML = hist.map(historicalCard).join("") || "<p>No historical reference records match.</p>";
      const historyPanel = document.querySelector(".authority-history");
      if (historyPanel && query && hist.length) historyPanel.open = true;
      state.textContent = `${live.length} current authority resident record(s) · ${hist.length} historical/uncommissioned references. Effective access is the server-evaluated projection; the source API remains authoritative.`;
    } catch (error) { state.textContent = showError(error); $("resident-directory-live").replaceChildren(); $("resident-directory-history").replaceChildren(); }
  };
  const renderCapabilities = async (force = false) => {
    const state = $("capability-registry-status");
    if (!state) return;
    state.textContent = "Checking the protected canonical registry…";
    try {
      const data = await load(force);
      const catalog = window.RVResidentPermissionsModel.create(data.payload);
      const query = ($("capability-registry-search").value || "").trim().toLowerCase();
      const profiles = data.payload.profiles || [];
      const residentText = (capabilityId) => profiles.filter((p) =>
        [...(p.effective_permissions || []), ...(p.rules || []), ...(p.inherited_rules || [])].some((entry) => entry.capability_id === capabilityId))
        .map((p) => profileName(p) + " " + JSON.stringify(p.effective_permissions || []) + " " + JSON.stringify(p.rules || []) + " " + JSON.stringify(p.inherited_rules || [])).join(" ");
      const capabilities = catalog.capabilities.filter((c) => (JSON.stringify(c) + " " + residentText(c.capability_id)).toLowerCase().includes(query));
      const resourceText = (resourceId) => profiles.map((p) => profileName(p) + " " + JSON.stringify([...(p.effective_permissions || []), ...(p.rules || []), ...(p.inherited_rules || [])].filter((entry) => entry.resource_id === resourceId))).join(" ");
      const resources = catalog.resources.filter((r) => (JSON.stringify(r) + " " + resourceText(r.resource_id)).toLowerCase().includes(query));
      const rows = capabilities.map((c) => {
        const access = profiles.map((p) => {
          const matches = (p.effective_permissions || []).filter((e) => e.capability_id === c.capability_id);
          const rules = [...(p.rules || []), ...(p.inherited_rules || [])].filter((r) => r.capability_id === c.capability_id);
          const ruleDetails = rules.map((r) => `${esc(r.effect)} ${esc(r.access_level)} @ ${esc(r.resource_id)} · ${esc(r.data_classification || "class unavailable")} · ${r.approval_required ? "approval required" : "no separate approval noted"} · ${esc(r.valid_until || "no expiry recorded")} · ${esc(r.provenance_ref || "provenance unavailable")}`).join("; ");
          return `<li>${esc(profileName(p))}: ${matches.length ? matches.map((m) => `${esc(m.effective_status)} · ${esc(m.access_level)} @ ${esc(m.resource_id)} · exact grant ${esc(m.exact_grant_status || "not supplied")}${m.condition ? ` · ${esc(m.condition)}` : ""}`).join(", ") : "no effective evaluation"}${ruleDetails ? ` · policy: ${ruleDetails}` : ""}</li>`;
        }).join("");
        const resourcesFor = (c.resource_ids || []).map((id) => catalog.resource(id)).filter(Boolean);
        return `<details class="authority-registry-entry"><summary><span>${esc(c.description || c.capability_id)}</span><b>${esc(catalog.status(c.capability_id))}</b></summary><dl><dt>Operation</dt><dd><code>${esc(c.capability_id)}</code></dd><dt>Authority action</dt><dd>${esc(c.authority_action || "unavailable")}</dd><dt>Authority requirements</dt><dd><code>${esc(c.authorization_contract ? JSON.stringify(c.authorization_contract) : "Not provided by the active catalog API; exact grant/action evaluation remains server-enforced.")}</code></dd><dt>Input schema</dt><dd><code>${esc(c.input_schema ? JSON.stringify(c.input_schema) : "Not provided by the active catalog API.")}</code></dd><dt>Owner / implementation</dt><dd>${esc(c.owner_office || "not recorded")} · ${esc(c.implementation_ref || "not recorded")}</dd><dt>Discovery declaration</dt><dd>${esc(c.declaration_source || "not supplied")} · ${esc(c.declaration_source_commit || "source revision unavailable")}</dd><dt>Availability</dt><dd>${esc(c.availability_policy || "Policy not supplied; executor/runtime availability is not reported.")}${c.registration_blocker ? ` · blocker: ${esc(c.registration_blocker)}` : ""}</dd><dt>Resources</dt><dd>${resourcesFor.length ? resourcesFor.map((r) => `${esc(r.resource_id)} (${esc(r.resource_kind)}, ${esc(r.classification)}, ${esc(r.owner_office || "owner not recorded")}; runtime availability ${esc(r.availability_status || r.availability || r.catalog_status || "not reported")})`).join("; ") : "No registered resource binding"}</dd></dl><h4>Resident access projection</h4><ul>${access || "<li>No current resident identities returned.</li>"}</ul><p>Executor identity and live health are not provided by this registry response. Authorized invocation rechecks exact grants server-side.</p></details>`;
      }).join("");
      const resourceRows = resources.map((r) => `<article class="authority-resource"><h3>${esc(r.description || r.resource_id)}</h3><p><code>${esc(r.resource_id)}</code></p><p>${esc(r.resource_kind || "kind unavailable")} · ${esc(r.classification || "classification unavailable")} · owner ${esc(r.owner_office || "not recorded")} · availability ${esc(r.availability_status || r.availability || r.catalog_status || (r.enabled === false ? "unavailable" : "registered; runtime health not supplied"))}</p></article>`).join("");
      const missing = catalog.unavailableReferences.map((x) => `<p class="authority-conflict">${esc(x.capability_id)} remains referenced by ${x.records.length} resident rule(s), but is absent from the active catalog. History is preserved; current availability reason is not supplied by this API.</p>`).join("");
      const missingActions = catalog.unavailableGrantActions.filter((x) => !query || (x.action + " " + JSON.stringify(x.records)).toLowerCase().includes(query)).map((x) => `<p class="authority-conflict">Authority action ${esc(x.action)} remains in ${x.records.length} exact grant record(s) but has no active capability declaration in this API response. Grant/audit history remains available in Resident Permissions; the API does not identify whether this action was removed, deprecated, or disabled.</p>`).join("");
      $("capability-registry-results").innerHTML = `<h3>Registered operations (${capabilities.length})</h3>${rows || "<p>No operation matches this search.</p>"}<h3>Registered resources (${resources.length})</h3>${resourceRows || "<p>No resource matches this search.</p>"}${missing}${missingActions}`;
      state.textContent = `${catalog.capabilities.length} registered operation(s), ${catalog.resources.length} resource(s), and ${profiles.length} resident access projection(s) loaded from the canonical API. Search filters this view; unavailable status is not inferred.`;
    } catch (error) { state.textContent = showError(error); $("capability-registry-results").replaceChildren(); }
  };
  const tabTargets = {preferences:null, notifications:"notification-settings-workspace", accounts:"account-administration-workspace", residents:"resident-directory-workspace", permissions:"resident-permissions-workspace", capabilities:"capability-registry-workspace", hardware:"resource-monitor-workspace"};
  const originalPlaces = new Map();
  const restoreSettingsPanels = () => {
    originalPlaces.forEach((place, id) => {
      const node = $(id);
      if (node && place.parent && node.parentNode !== place.parent) place.parent.insertBefore(node, place.next && place.next.parentNode === place.parent ? place.next : null);
      if (node) node.hidden = true;
    });
  };
  const activateSettingsTab = async (tab) => {
    settingsTab = Object.prototype.hasOwnProperty.call(tabTargets, tab) ? tab : "preferences";
    Object.keys(tabTargets).forEach((key) => document.querySelector(`[data-settings-tab="${key}"]`)?.setAttribute("aria-selected", String(key === settingsTab)));
    restoreSettingsPanels();
    const content = $("settings-tab-content");
    content.replaceChildren();
    const targetId = tabTargets[settingsTab];
    if (!targetId) {
      const panel = $("settings-preferences-panel");
      content.append(panel);
      return;
    }
    const node = $(targetId);
    if (!originalPlaces.has(targetId)) originalPlaces.set(targetId, {parent:node.parentNode, next:node.nextSibling});
    content.append(node);
    node.hidden = false;
    if (settingsTab === "residents") await renderResidents();
    if (settingsTab === "capabilities") await renderCapabilities();
    if (settingsTab === "notifications") window.RiverviewV2NotificationSettings?.render();
    if (settingsTab === "accounts") window.dispatchEvent(new Event("rv:account-administration"));
    if (settingsTab === "permissions") window.dispatchEvent(new Event("rv:resident-permissions"));
    if (settingsTab === "hardware") window.RiverviewV2ResourceMonitor?.render();
  };
  document.addEventListener("DOMContentLoaded", () => {
    $("resident-directory-refresh")?.addEventListener("click", () => renderResidents(true));
    $("resident-directory-live")?.addEventListener("click",event=>{if(event.target.closest("[data-open-resident-chat=\'office:grace\']")){window.RiverviewV2Workspace?.openGraceConversation();}});
    $("resident-directory-search")?.addEventListener("input", () => renderResidents());
    $("capability-registry-refresh")?.addEventListener("click", () => renderCapabilities(true));
    $("capability-registry-search")?.addEventListener("input", () => renderCapabilities());
    document.querySelectorAll("[data-settings-tab]").forEach((button) => button.addEventListener("click", () => activateSettingsTab(button.dataset.settingsTab)));
    $("settings-theme-select")?.addEventListener("change", (event) => {
      const main = $("theme-select"); main.value = event.target.value; main.dispatchEvent(new Event("change", {bubbles:true}));
    });
    for (const side of ["left", "right"]) {
      $(`settings-${side}-sidebar`)?.addEventListener("change", (event) => window.RiverviewV2WorkspacePreferences?.setSidebar(side, event.target.value));
    }
    const currentTheme = $("theme-select")?.value || "system";
    if ($("settings-theme-select")) $("settings-theme-select").value = currentTheme;
    for (const side of ["left", "right"]) if ($(`settings-${side}-sidebar`)) $(`settings-${side}-sidebar`).value = window.RiverviewV2WorkspacePreferences?.getSidebar(side) || "expanded";
    window.RiverviewV2AuthorityExplorer = Object.freeze({renderResidents, renderCapabilities, activateSettingsTab, restoreSettingsPanels});
  });
})();
