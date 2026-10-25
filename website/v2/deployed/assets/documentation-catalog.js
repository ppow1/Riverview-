/* Read-only view models for the canonical process-graph documentation and evidence registry. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const root = $("documentation-workspace");
  if (!root) return;
  let loaded = false, busy = false, entries = [];
  const clean = (value) => typeof value === "string" ? value : "";
  const request = async (path) => {
    const headers = {Accept:"application/json"};
    const token = sessionStorage.getItem("rv.dashboard.token");
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(path, {credentials:"same-origin", cache:"no-store", headers});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `http_${response.status}`);
    return result;
  };
  const appendList = (host, title, values) => {
    const section = document.createElement("section"); section.className = "documentation-catalog-group";
    const heading = document.createElement("h4"); heading.textContent = `${title} (${values.length})`; section.append(heading);
    if (!values.length) { const empty = document.createElement("p"); empty.textContent = "No references declared."; section.append(empty); }
    else {
      const list = document.createElement("ul");
      for (const value of values) {
        const row = document.createElement("li"), path = clean(value);
        if (title === "Documentation" && /^docs\/components\/[A-Za-z0-9_-]+\.md$/.test(path)) {
          const link = document.createElement("a"); link.href = `/${path}`; link.target = "rv-v2-documentation"; link.rel = "noopener"; link.textContent = path; row.append(link);
        } else { const code = document.createElement("code"); code.textContent = path; row.append(code); }
        list.append(row);
      }
      section.append(list);
    }
    host.append(section);
  };
  function render() {
    const query = $("documentation-search").value.trim().toLowerCase();
    const rows = entries.filter((entry) => !query || entry.search.includes(query));
    $("documentation-catalog-state").textContent = busy ? "Loading authorized canonical references…" : loaded ? `${rows.length} of ${entries.length} registered workflows · source: existing process graph API` : "Catalog has not been loaded.";
    const host = $("documentation-catalog"); host.replaceChildren();
    if (!loaded && !busy) return;
    if (!rows.length && loaded) { const message = document.createElement("p"); message.textContent = entries.length ? "No registered references match this search." : "The canonical graph registry returned no workflow records."; host.append(message); }
    for (const entry of rows) {
      const card = document.createElement("article"); card.className = "documentation-catalog-entry";
      const heading = document.createElement("h3"); heading.textContent = `${entry.component} · ${entry.workflow}`; card.append(heading);
      const revision = document.createElement("p"); revision.className = "muted"; revision.textContent = `Graph revision ${entry.revision} · ${entry.nodes.length} nodes`; card.append(revision);
      if (entry.status !== "available") { const unavailable = document.createElement("p"); unavailable.className = "documentation-unavailable"; unavailable.textContent = "Graph details unavailable from the authenticated API; no workflow nodes or references are inferred."; card.append(unavailable); }
      const steps = document.createElement("ol"); steps.className = "documentation-catalog-nodes";
      for (const node of entry.nodes.filter((node) => !query || `${node.type} ${node.label} ${node.id}`.toLowerCase().includes(query))) {
        const item = document.createElement("li"); item.textContent = `${node.type}: ${node.label}`; steps.append(item);
      }
      if (steps.childElementCount) card.append(steps);
      const identityMatch = `${entry.component} ${entry.workflow} ${entry.revision}`.toLowerCase().includes(query);
      appendList(card, "Documentation", entry.documentation.filter((ref) => !query || identityMatch || ref.toLowerCase().includes(query)));
      appendList(card, "Source", entry.sources.filter((ref) => !query || identityMatch || ref.toLowerCase().includes(query)));
      appendList(card, "Declared evidence", entry.evidence.filter((ref) => !query || identityMatch || ref.toLowerCase().includes(query)));
      host.append(card);
    }
  }
  async function load() {
    if (loaded || busy) { render(); return; }
    busy = true; render();
    try {
      const index = await request("/api/v1/graphs");
      if (!Array.isArray(index.items)) throw new Error("graph_index_invalid");
      const summaries = index.items.slice(0, 100);
      const details = await Promise.allSettled(summaries.map((item) => request(`/api/v1/graphs/${encodeURIComponent(item.graph_id)}`)));
      entries = details.map((result, i) => {
        const graph = result.status === "fulfilled" ? result.value.graph : null, summary = summaries[i];
        const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
        const unique = (items) => [...new Set(items.filter((value) => typeof value === "string" && value))].sort();
        const entry = {status:result.status === "fulfilled" ? "available" : "detail unavailable",
          component:clean(graph?.component_id || summary.component_id || "Component unavailable"),
          workflow:clean(graph?.workflow_id || summary.workflow_id || summary.graph_id),
          revision:graph?.graph_revision ?? summary.graph_revision ?? "unavailable",
          nodes:nodes.map((node) => ({id:clean(node.id), type:clean(node.type || "unknown"), label:clean(node.label || node.id || "Unlabelled node")})),
          documentation:unique([...(graph?.documentation_references || []), ...nodes.flatMap((node) => node.documentation_references || [])]),
          sources:unique([...(graph?.source_references || []), ...nodes.flatMap((node) => node.source_references || [])]),
          evidence:unique([...(graph?.verification_evidence || []), ...nodes.flatMap((node) => node.verification_evidence || [])])};
        entry.search = JSON.stringify(entry).toLowerCase(); return entry;
      });
      loaded = true;
    } catch (error) {
      $("documentation-catalog-state").textContent = `Canonical documentation index unavailable (${String(error.message || "unavailable").replace(/[^a-z0-9_.-]/gi,"_")}). No references are inferred.`;
    } finally { busy = false; render(); }
  }
  $("documentation-search").addEventListener("input", render);
  window.addEventListener("rvv2:view", (event) => { if (event.detail?.view === "documentation") load(); });
})();
