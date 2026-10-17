// Riverview~ controlled asset; component RESIDENT-PERMISSION-PROFILES.
// Revision: 1.0.4
// Purpose: Steward resident capability/resource checklist over existing account session.
// Authority: Server-side exact office.manage and profile CAS functions remain authoritative.
// Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PACKAGING | Fix rule-summary JavaScript syntax before release verification
(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const esc = (value) => String(value == null ? "" : value).replace(/[&<>"']/g,
    (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  let registry = null;
  let selected = null;
  const request = async (path, method, body) => {
    const headers = {Accept:"application/json"};
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      const csrf = document.cookie.split(";").map((x) => x.trim()).find((x) => x.startsWith("rv_account_csrf="));
      if (csrf) headers["X-Riverview-CSRF"] = decodeURIComponent(csrf.slice("rv_account_csrf=".length));
    }
    const response = await fetch(path,{method:method || "GET",headers,credentials:"same-origin",cache:"no-store",
      body:body === undefined ? undefined : JSON.stringify(body)});
    const value = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(value.error || ("http_" + response.status));
    return value;
  };
  const status = (value) => { byId("resident-permission-state").textContent = value; };
  const load = async () => {
    const host = byId("resident-permission-list");
    try {
      registry = await request("/api/v1/resident-permissions");
      const profiles = registry.profiles || [];
      status(profiles.length + " resident identities · " + (registry.capabilities || []).length +
        " capabilities · " + (registry.resources || []).length + " registered resources. Health and capacity are not implied by registry metadata.");
      if (!profiles.length) { host.textContent = "No resident identities are registered in AuthorityRegistry."; return; }
      host.innerHTML = profiles.map((p) => {
        const rules = p.rules || [];
        let buttons = "<button class=\"secondary\" data-edit=\"" + esc(p.principal_id) + "\">Edit checklist</button>";
        if (p.status === "pending") buttons += " <button class=\"secondary\" data-approve=\"" + esc(p.principal_id) + "\" data-revision=\"" + esc(p.revision) + "\">Activate profile</button>";
        if (p.status && p.status !== "revoked") buttons += " <button class=\"secondary\" data-revoke=\"" + esc(p.principal_id) + "\" data-revision=\"" + esc(p.revision) + "\">Revoke</button>";
        const ruleHtml = rules.length ? rules.map((r) => "<div class=\"row\"><span class=\"row-main\">" + esc(r.capability_id) + " → " + esc(r.resource_id) +
          "</span><span>" + esc(r.effect) + " · " + esc(r.access_level) + " · " + esc(r.data_classification) + " · export " + esc(r.export_mode) +
          " · approval " + (r.approval_required ? "required" : "not required") + " · expires " + esc(r.valid_until || "never") + "</span></div>").join("") : "<p>No explicit rules; no profile permissions are inferred from the tier.";
        const inherited = p.inherited_rules || [];
        const inheritedHtml = inherited.length ? "<h4>Inherited tier rules</h4>" + inherited.map((r) => "<div class=\"row-meta\">" + esc(r.capability_id) + " → " + esc(r.resource_id) + " · " + esc(r.effect) + " · " + esc(r.access_level) + "</div>").join("") : "<div class=\"row-meta\">No inherited allow rules are configured for this tier.</div>";
        const audits = (p.audit || []).map((a) => "<div class=\"row-meta\">" + esc(a.event_type) + " · " + esc(a.actor_id) + " · rev " + esc(a.revision) + " · " + esc(a.recorded_at) + "</div>").join("");
        const grants = p.standing_grants || [];
        const grantHtml = grants.length ? grants.map((g) => {
          const now = Date.now();
          const grantStatus = g.revoked_at ? "revoked" : g.valid_from && Date.parse(g.valid_from) > now ? "not yet valid" : g.valid_until && Date.parse(g.valid_until) <= now ? "expired" : "active";
          return "<div class=\"row-meta\">" + esc(g.action) + " @ " + esc(g.scope_ref) + " · " + esc(g.policy_ref) + " · " + esc(grantStatus) + " · starts " + esc(g.valid_from) + " · expires " + esc(g.valid_until || "never") + (g.revoked_at ? " · revoked " + esc(g.revoked_at) : "") + "</div>";
        }).join("") : "<div class=\"row-meta\">No exact authority grants recorded.</div>";
        return "<article class=\"panel permission-card\"><div class=\"panel-head\"><div><h3>" + esc(p.principal_id) + "</h3><span class=\"row-meta\">" +
          esc(p.office_role || p.office_id || "office unassigned") + " · identity " + esc(p.identity_status || "unknown") + " · " + esc(p.tier || "tier unassigned") + " · " + esc(p.status || "no profile") + (p.effective_status && p.effective_status !== p.status ? " · effective policy " + esc(p.effective_status) : "") + " · revision " + esc(p.revision || 0) +
          "</span></div><div class=\"account-actions\">" + buttons + "</div></div><div class=\"row-meta\">Classification ceiling: " + esc(p.classification_ceiling || "none") +
          " · export " + esc(p.export_mode || "deny") + "</div><h4>Standing exact authority grants</h4><div class=\"rows\">" + grantHtml + "</div><h4>Resident-specific rules</h4><div class=\"rows\">" + ruleHtml + "</div>" + inheritedHtml + "<details><summary>Audit history (" + (p.audit || []).length + ")</summary>" + audits + "</details></article>";
      }).join("");
      host.querySelectorAll("[data-edit]").forEach((button) => button.addEventListener("click", () => edit(button.dataset.edit)));
      host.querySelectorAll("[data-approve]").forEach((button) => button.addEventListener("click", () => transition("approve",button.dataset.approve,Number(button.dataset.revision),button)));
      host.querySelectorAll("[data-revoke]").forEach((button) => button.addEventListener("click", () => transition("revoke",button.dataset.revoke,Number(button.dataset.revision),button)));
    } catch (error) {
      status("Registry unavailable or the authenticated Steward lacks the exact management grant.");
      host.textContent = "Profile request failed (" + error.message + "). No permission change was made.";
    }
  };
  const transition = async (action, principal, revision, button) => {
    button.disabled = true;
    try {
      await request("/api/v1/resident-permissions/" + encodeURIComponent(principal) + "/" + action,"POST",{expected_revision:revision});
      await load();
    } catch (error) { button.disabled = false; status("Profile " + action + " failed: " + error.message); }
  };
  const edit = (principal) => {
    selected = (registry.profiles || []).find((p) => p.principal_id === principal);
    if (!selected) return;
    const caps = registry.capabilities || [];
    const resources = registry.resources || [];
    const proposedTier = selected.tier || "observer";
    let rows = "";
    caps.forEach((cap) => {
      const capabilityRules = (selected.rules || []).filter((r) => r.capability_id === cap.capability_id);
      const rule = capabilityRules[0];
      const inheritedRule = (selected.inherited_rules || []).find((r) => r.capability_id === cap.capability_id);
      const linked = (cap.resource_ids || []).map((id) => resources.find((resource) => resource.resource_id === id)).filter(Boolean);
      const selectedResources = new Set(capabilityRules.map((r) => r.resource_id));
      let options = "<option value=\"*\" " + (!capabilityRules.length || selectedResources.has("*") ? "selected" : "") + ">Any registered resource (exact grant still required)</option>";
      linked.forEach((resource) => { options += "<option value=\"" + esc(resource.resource_id) + "\" " + (selectedResources.has(resource.resource_id) ? "selected" : "") + ">" + esc(resource.resource_id) + " · " + esc(resource.classification) + "</option>"; });
      rows += "<div class=\"permission-edit-row\"><label><input type=\"checkbox\" data-enabled=\"" + esc(cap.capability_id) + "\" " + (capabilityRules.length ? "checked" : "") + "> " + esc(cap.capability_id) +
        "<small>" + esc(cap.description) + "</small></label><select multiple size=\"3\" aria-label=\"Resource scopes for " + esc(cap.capability_id) + "\" data-resource=\"" + esc(cap.capability_id) + "\">" + options + "</select><select data-effect=\"" + esc(cap.capability_id) + "\"><option value=\"allow\" " + (rule && rule.effect === "allow" ? "selected" : "") + ">Allow</option><option value=\"deny\" " + (rule && rule.effect === "deny" ? "selected" : "") + ">Deny</option></select><select data-level=\"" + esc(cap.capability_id) + "\">" +
        ["read","write","execute","administer","delegate"].map((v) => "<option " + (rule && rule.access_level === v ? "selected" : "") + ">" + v + "</option>").join("") +
        "</select><label><input type=\"checkbox\" data-approval=\"" + esc(cap.capability_id) + "\" " + ((rule ? rule.approval_required : inheritedRule ? inheritedRule.approval_required : cap.approval_default) ? "checked" : "") + "> Require approval</label><label>Expires<input type=\"datetime-local\" data-expiry=\"" + esc(cap.capability_id) + "\" value=\"" + (rule && rule.valid_until ? esc(new Date(rule.valid_until).toISOString().slice(0,16)) : "") + "\"></label></div>";
    });
    const tiers = ["observer","operator","administrator","institutional_administrator"];
    const classes = ["public","internal","confidential","restricted"];
    byId("resident-permission-list").innerHTML = "<article class=\"panel permission-card\"><h3>Permission checklist · " + esc(principal) +
      "</h3><p>Save creates a pending revision. It cannot take effect until a Steward explicitly activates it.</p><form id=\"permission-editor\"><label>Default tier<select id=\"permission-tier\">" + tiers.map((v) => "<option " + (proposedTier === v ? "selected" : "") + ">" + v + "</option>").join("") +
      "</select></label><p>A title does not set a permission tier. Resource health and capacity are evaluated by their owning services.</p><label>Classification ceiling<select id=\"permission-class\">" + classes.map((v) => "<option " + (selected.classification_ceiling === v ? "selected" : "") + ">" + v + "</option>").join("") +
      "</select></label><label>Export default<select id=\"permission-export\"><option value=\"deny\" " + (selected.export_mode !== "allow" ? "selected" : "") + ">Deny</option><option value=\"allow\" " + (selected.export_mode === "allow" ? "selected" : "") + ">Allow by rule</option></select></label><h4>Capabilities and resource scope</h4>" + rows +
      "<button class=\"primary\" type=\"submit\">Save pending revision</button> <button type=\"button\" class=\"secondary\" id=\"permission-cancel\">Cancel</button><div id=\"permission-error\" class=\"inline-error\"></div></form></article>";
    byId("permission-cancel").addEventListener("click",load);
    byId("permission-editor").addEventListener("submit",async (event) => {
      event.preventDefault();
      const rules = [];
      caps.forEach((cap) => {
        const id = cap.capability_id;
        const enabled = byId("resident-permission-list").querySelector("[data-enabled=\"" + CSS.escape(id) + "\"]");
        if (!enabled.checked) return;
        const resourceSelect = byId("resident-permission-list").querySelector("[data-resource=\"" + CSS.escape(id) + "\"]");
        const expiryInput = byId("resident-permission-list").querySelector("[data-expiry=\"" + CSS.escape(id) + "\"]");
        const common = {capability_id:id,
          effect:byId("resident-permission-list").querySelector("[data-effect=\"" + CSS.escape(id) + "\"]").value,
          access_level:byId("resident-permission-list").querySelector("[data-level=\"" + CSS.escape(id) + "\"]").value,
          approval_required:byId("resident-permission-list").querySelector("[data-approval=\"" + CSS.escape(id) + "\"]").checked,
          valid_until:(expiryInput.value ? new Date(expiryInput.value).toISOString() : null),
          data_classification:byId("permission-class").value,export_mode:byId("permission-export").value,
          provenance_ref:"steward-reviewed-dashboard-profile"};
        Array.from(resourceSelect.selectedOptions).forEach((option) => rules.push({...common,resource_id:option.value}));
      });
      const body = {expected_revision:Number(selected.revision || 0),profile:{tier:byId("permission-tier").value,
        classification_ceiling:byId("permission-class").value,export_mode:byId("permission-export").value,rules:rules}};
      try { await request("/api/v1/resident-permissions/" + encodeURIComponent(selected.principal_id),"PUT",body); await load(); }
      catch (error) { byId("permission-error").textContent = "Save failed (" + error.message + "). The previous revision remains current."; }
    });
  };
  window.addEventListener("rv:resident-permissions",load);
})();
