// Reusable read adapter for the canonical resident-permissions API payload.
// Revision: 1.0.0
// The browser never owns a capability or grant catalogue.
(() => {
  "use strict";
  const byId = (items, key) => new Map((Array.isArray(items) ? items : [])
    .filter((item) => item && typeof item[key] === "string")
    .map((item) => [item[key], item]));
  const list = (value) => Array.isArray(value) ? value : [];
  const enabled = (item) => item && item.enabled !== false && item.catalog_status !== "unavailable";

  const create = (payload) => {
    const capabilities = list(payload && payload.capabilities);
    const resources = list(payload && payload.resources);
    const capabilityById = byId(capabilities, "capability_id");
    const resourceById = byId(resources, "resource_id");
    const knownIds = new Set(capabilityById.keys());
    const referenced = new Map();

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
      capability(id) { return capabilityById.get(id) || null; },
      resource(id) { return resourceById.get(id) || null; },
      status(id) {
        const item = capabilityById.get(id);
        if (!item) return "unavailable";
        return enabled(item) ? "registered" : "unavailable";
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
