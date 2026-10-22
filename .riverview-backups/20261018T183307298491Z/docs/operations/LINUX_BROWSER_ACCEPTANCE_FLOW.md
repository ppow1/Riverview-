<!--
Riverview~ Controlled Document
File: docs/operations/LINUX_BROWSER_ACCEPTANCE_FLOW.md
Component: LINUX-BROWSER-ACCEPTANCE
File Revision: 1.0.1
Purpose: Show the guarded Linux browser acceptance and evidence recovery workflow
Execution Model: Request-driven operator workflow
Observability: Local runner summary and private per-test error reports; no live dashboard consumer
Dependencies: Python Playwright runner; canonical process graph
Authority: Read-only local/staging browser checks; no production writes, approvals, or work execution
Changed: 2026-10-18 UTC | RV-C2-DOD-REMEDIATION-001 | Initial focused workflow view
Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
Tests: python3 scripts/process_graph.py check
History: Git and revision/backup manifest
-->
# Linux browser acceptance flow

This focused view is generated from `process_graphs/steward-dashboard/linux-browser-acceptance.json`; do not edit the diagram by hand. It distinguishes unsafe targets, browser failures, privacy-safe reporting, and manual evidence retention. It does not assert a live Grace deployment or a Steward-facing status page.

```mermaid
flowchart LR
  subgraph g_rv_steward_dashboard_linux_browser_acceptance["STEWARD-DASHBOARD / linux-browser-acceptance.v1"]
    g_rv_steward_dashboard_linux_browser_acceptance_request_e7d2fbf9(["Authorized browser smoke requested with origin and page assertion"])
    g_rv_steward_dashboard_linux_browser_acceptance_target_allowed_1d2f1b8a{"HTTP origin and read-only target satisfy loopback or explicit staging opt-in"}
    g_rv_steward_dashboard_linux_browser_acceptance_run_chromium_e45c2c83["Run isolated headless Chromium GET smoke and block non-GET requests"]
    g_rv_steward_dashboard_linux_browser_acceptance_collect_evidence_c0a99e80["Write private summary, errors, screenshot, and failure trace"]
    g_rv_steward_dashboard_linux_browser_acceptance_accept_864f151f["Accept only successful same-origin page render with no browser errors or blocked mutations"]
    g_rv_steward_dashboard_linux_browser_acceptance_fail_closed_896e3fb4[["Reject unsafe target or retain failure evidence without retrying mutations"]]
    g_rv_steward_dashboard_linux_browser_acceptance_synthetic_proposal_1cf54310["Synthetic browser fixture submits harmless request and displays proposal pending approval"]
    g_rv_steward_dashboard_linux_browser_acceptance_synthetic_approval_boundary_66dbefb1{"Synthetic-only approval button demonstrates UI gate and never grants real Steward authority"}
    g_rv_steward_dashboard_linux_browser_acceptance_synthetic_work_order_status_fc15fdcf["Mock work-order record remains pending actual execution authorization; no CME dispatch or execution"]
    g_rv_steward_dashboard_linux_browser_acceptance_staging_scope_check_1562a294{"Opt-in staged origin, exact-host private cookie state, test account, and seeded conversation pass fail-closed validation"}
    g_rv_steward_dashboard_linux_browser_acceptance_staging_boundary_inspection_8dc06e77["Read seeded Grace conversation, inspect exact-grant work-order dialog, read objective status, and stop before mutation"]
    g_rv_steward_dashboard_linux_browser_acceptance_staging_fixture_proof_b82ade25["Disposable loopback authenticated fixture proves cookie scope, mutation and cross-origin blocking, redacted private evidence, and skip reporting"]
    g_rv_steward_dashboard_linux_browser_acceptance_safe_error_report_dcceffa4["Record fixed error categories only; remove arbitrary exception text and all request URLs"]
    g_rv_steward_dashboard_linux_browser_acceptance_diagnose_private_run_97956923["Diagnose with safe error kind, assertion, exit status, and private local output; never copy raw authenticated content"]
    g_rv_steward_dashboard_linux_browser_acceptance_retain_reviewed_evidence_58f848ea["Keep private evidence through review and incident closure; delete only after required redacted evidence is linked"]
  end
  g_rv_steward_dashboard_linux_browser_acceptance_request_e7d2fbf9 --> g_rv_steward_dashboard_linux_browser_acceptance_target_allowed_1d2f1b8a
  g_rv_steward_dashboard_linux_browser_acceptance_target_allowed_1d2f1b8a -->|valid target| g_rv_steward_dashboard_linux_browser_acceptance_run_chromium_e45c2c83
  g_rv_steward_dashboard_linux_browser_acceptance_target_allowed_1d2f1b8a -->|diagnostic_branch: invalid or unauthorized target| g_rv_steward_dashboard_linux_browser_acceptance_fail_closed_896e3fb4
  g_rv_steward_dashboard_linux_browser_acceptance_run_chromium_e45c2c83 --> g_rv_steward_dashboard_linux_browser_acceptance_collect_evidence_c0a99e80
  g_rv_steward_dashboard_linux_browser_acceptance_collect_evidence_c0a99e80 -->|verification: successful smoke| g_rv_steward_dashboard_linux_browser_acceptance_accept_864f151f
  g_rv_steward_dashboard_linux_browser_acceptance_collect_evidence_c0a99e80 -->|diagnostic_branch: browser error or failed assertion| g_rv_steward_dashboard_linux_browser_acceptance_fail_closed_896e3fb4
  g_rv_steward_dashboard_linux_browser_acceptance_request_e7d2fbf9 -->|isolated fixture test only| g_rv_steward_dashboard_linux_browser_acceptance_synthetic_proposal_1cf54310
  g_rv_steward_dashboard_linux_browser_acceptance_synthetic_proposal_1cf54310 --> g_rv_steward_dashboard_linux_browser_acceptance_synthetic_approval_boundary_66dbefb1
  g_rv_steward_dashboard_linux_browser_acceptance_synthetic_approval_boundary_66dbefb1 -->|test-only synthetic approval; no actual authority| g_rv_steward_dashboard_linux_browser_acceptance_synthetic_work_order_status_fc15fdcf
  g_rv_steward_dashboard_linux_browser_acceptance_request_e7d2fbf9 -->|optional actual staging UI only| g_rv_steward_dashboard_linux_browser_acceptance_staging_scope_check_1562a294
  g_rv_steward_dashboard_linux_browser_acceptance_staging_scope_check_1562a294 -->|all scoped prerequisites pass| g_rv_steward_dashboard_linux_browser_acceptance_staging_boundary_inspection_8dc06e77
  g_rv_steward_dashboard_linux_browser_acceptance_staging_scope_check_1562a294 -->|diagnostic_branch: missing or unsafe staging precondition| g_rv_steward_dashboard_linux_browser_acceptance_fail_closed_896e3fb4
  g_rv_steward_dashboard_linux_browser_acceptance_staging_scope_check_1562a294 -->|verification: isolated fixture test uses synthetic host-scoped cookie and asserts blocked requests plus redacted evidence| g_rv_steward_dashboard_linux_browser_acceptance_staging_fixture_proof_b82ade25
  g_rv_steward_dashboard_linux_browser_acceptance_collect_evidence_c0a99e80 -->|redact browser diagnostics| g_rv_steward_dashboard_linux_browser_acceptance_safe_error_report_dcceffa4
  g_rv_steward_dashboard_linux_browser_acceptance_safe_error_report_dcceffa4 -->|verification: safe evidence emitted| g_rv_steward_dashboard_linux_browser_acceptance_accept_864f151f
  g_rv_steward_dashboard_linux_browser_acceptance_safe_error_report_dcceffa4 -->|diagnostic_branch: failure remains failed; no automatic retry| g_rv_steward_dashboard_linux_browser_acceptance_fail_closed_896e3fb4
  g_rv_steward_dashboard_linux_browser_acceptance_fail_closed_896e3fb4 -->|recovery_route: inspect local safe diagnostics| g_rv_steward_dashboard_linux_browser_acceptance_diagnose_private_run_97956923
  g_rv_steward_dashboard_linux_browser_acceptance_accept_864f151f -->|record evidence location and commit| g_rv_steward_dashboard_linux_browser_acceptance_retain_reviewed_evidence_58f848ea
  g_rv_steward_dashboard_linux_browser_acceptance_diagnose_private_run_97956923 -->|recovery_route: retain while review or incident is open| g_rv_steward_dashboard_linux_browser_acceptance_retain_reviewed_evidence_58f848ea
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```
