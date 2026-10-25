// Reusable read adapter for the canonical resident-permissions API payload.
// Revision: 1.0.1
// Changed: 2026-10-25 UTC | RV-V2-BATCH1-20261025 | Preserve disabled/deprecated lifecycle status in the dynamic catalog view.
// The browser never owns a capability or grant catalogue.
(() => {
  "use strict";
  const byId = (items, key) => new Map((Array.isArray(items) ? items : [])
    .filter((item) => item && typeof item[key] === "string")
    .map((item) => [item[key], item]));
  const list = (value) => Array.isArray(value) ? value : [];
  const declaredStatus = (item) => String(item && (item.catalog_status || item.lifecycle_status || item.status) || "").trim().toLowerCase();
  const disabledStatus = new Set(["disabled", "deprecated", "removed", "retired", "unavailable", "blocked", "withdrawn"]);
  const enabled = (item) => Boolean(item && item.enabled !== false && !disabledStatus.has(declaredStatus(item)));

  const create = (payload) => {
    const capabilities = list(payload && payload.capabilities);
    const resources = list(payload && payload.resources);
    const capabilityById = byId(capabilities, "capability_id");
    const resourceById = byId(resources, "resource_id");
    const knownIds = new Set(capabilityById.keys());
    const knownActions = new Set(capabilities.map((item) => item && item.authority_action).filter((value) => typeof value === "string"));
    const referenced = new Map();
    const unmatchedGrantActions = new Map();

    list(payload && payload.profiles).forEach((profile) => {
      [...list(profile.rules), ...list(profile.inherited_rules)].forEach((rule) => {
        if (!rule || typeof rule.capability_id !== "string" || knownIds.has(rule.capability_id)) return;
        if (!referenced.has(rule.capability_id)) referenced.set(rule.capability_id, []);
        referenced.get(rule.capability_id).push({
          principal_id: profile.principal_id,
          source: list(profile.rules).includes(rule) ? "explicit" : "inherited",
          rule,
        });
      });
      list(profile.standing_grants).forEach((grant) => {
        if (!grant || typeof grant.action !== "string" || knownActions.has(grant.action)) return;
        if (!unmatchedGrantActions.has(grant.action)) unmatchedGrantActions.set(grant.action, []);
        unmatchedGrantActions.get(grant.action).push({principal_id: profile.principal_id, grant});
      });
    });

    return {
      capabilities,
      resources,
      capabilityById,
      resourceById,
      assignableCapabilities: capabilities.filter(enabled),
      unavailableReferences: Array.from(referenced, ([capability_id, records]) => ({
        capability_id, records,
      })),
      unavailableGrantActions: Array.from(unmatchedGrantActions, ([action, records]) => ({action, records})),
      capability(id) { return capabilityById.get(id) || null; },
      resource(id) { return resourceById.get(id) || null; },
      status(id) {
        const item = capabilityById.get(id);
        if (!item) return "unavailable";
        if (!enabled(item)) return declaredStatus(item) || "disabled";
        const current = declaredStatus(item);
        return current || "registered";
      },
      profileReferences(profile) {
        const ids = new Set([
          ...list(profile && profile.rules).map((rule) => rule && rule.capability_id),
          ...list(profile && profile.inherited_rules).map((rule) => rule && rule.capability_id),
        ].filter((id) => typeof id === "string"));
        return Array.from(ids).sort().map((id) => ({
          capability_id: id,
          capability: capabilityById.get(id) || null,
          status: this.status(id),
        }));
      },
    };
  };

  window.RVResidentPermissionsModel = Object.freeze({ create });
})();
