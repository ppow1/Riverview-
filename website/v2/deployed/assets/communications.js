/*
Riverview~ Controlled Source
File: website/v2/deployed/assets/communications.js
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.1
Purpose: Present only authoritative, redacted communications activity and an explicit unavailable state
Execution Model: Browser presentation; no backend request until an authorized source contract is connected
Observability: Visible source state, local configuration-check time, and null unknown counters
Dependencies: Browser DOM APIs
Inputs/Outputs: No communication events are configured; no payload or credential data is read
Authority: Read-only V2 presentation; no Comms5 operation or privileged API is invoked
Changed: 2026-10-21 UTC | RV-WEB-V2-COMMS-ACTIVITY-001 | Initial activity monitor
Changed: 2026-10-23 UTC | RV-V2-MANUAL-IMAGE-GENERATION-248 | Preserve the deployed V2 source under its explicit production bundle path.
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: tests/test_v2_workspace_shell.py
History: Git and revision/backup manifest
*/
(() => {
  "use strict";

  const state = {
    status: "unverified",
    sourceConfigured: false,
    events: [],
    counts: { outbound: null, inbound: null, pending: null, failed: null, completed: null },
    lastLocalCheckAt: null
  };
  const text = (selector, value) => {
    const node = document.querySelector(selector);
    if (node) node.textContent = value;
  };

  const render = () => {
    text("#communications-source-state", state.status === "unverified" ? "UNVERIFIED" : state.status.toUpperCase());
    const alert = document.querySelector("#communications-source-alert");
    if (alert) alert.dataset.state = state.status;
    text("#communications-source-detail", state.lastLocalCheckAt
      ? `Source: not configured · Local configuration checked ${state.lastLocalCheckAt} · No activity request was sent.`
      : "Source: not configured · No activity request has been sent.");
    text("#communications-refresh-status", state.lastLocalCheckAt
      ? `Local source configuration check completed at ${state.lastLocalCheckAt}. No network request was sent because no authorized feed is configured.`
      : "No activity request has been sent because no authorized source is configured.");
    for (const key of Object.keys(state.counts)) text(`[data-count="${key}"]`, "Unavailable");

    const body = document.querySelector("#communications-ledger-body");
    if (body) body.replaceChildren();
    const empty = document.querySelector("#communications-ledger-empty");
    if (empty) {
      const hasSource = state.sourceConfigured;
      empty.textContent = hasSource
        ? "No events match the selected search, time window, status, or direction."
        : "No ledger records are available because the authoritative source is not connected. This is not evidence of zero traffic.";
    }
    const detail = document.querySelector("#communications-detail");
    if (detail) detail.open = false;
  };

  const localCheck = () => {
    state.lastLocalCheckAt = new Date().toISOString();
    render();
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelector("#communications-refresh")?.addEventListener("click", localCheck);
    for (const selector of ["#communications-search", "#communications-window", "#communications-status", "#communications-direction"]) {
      document.querySelector(selector)?.addEventListener("input", render);
      document.querySelector(selector)?.addEventListener("change", render);
    }
    document.addEventListener("rvv2:view", (event) => {
      if (event.detail?.view === "communications") render();
    });
    render();
  });

  window.RiverviewV2Communications = Object.freeze({
    render,
    snapshotDiagnostics: () => ({
      status: state.status,
      source_configured: state.sourceConfigured,
      outbound_count: state.counts.outbound,
      inbound_count: state.counts.inbound,
      pending_count: state.counts.pending,
      failed_count: state.counts.failed,
      completed_count: state.counts.completed,
      last_local_check_at: state.lastLocalCheckAt
    })
  });
})();
