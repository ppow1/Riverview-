<!--
Riverview~ Controlled Document
File: docs/development/OPERATIONS-COOKBOOK-001_REVISION_RECORD.md
Component: RIVERVIEW-OPERATIONS
File Revision: 1.0.9
Purpose: Record the consolidated operational guide deliverable and evidence
Authority: Documentation and diagnostics; does not authorize shared-state mutation
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Record passing suite, live deployment, and browser evidence
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-CROSS-BRANCH-DOC-PORT | Port safe database, scheduler, and worker guidance without dropping M3.3 knowledge docs/graph
Changed: 2026-10-11 UTC | RV-M1.4-LIVE-DEPENDENCY-CORRECTION | Correct live lease migration status while preserving the M1.4 acceptance boundary
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-DEPLOY-8DCEC2A | Commission updated operational cookbooks as a dashboard-only immutable release and verify in Firefox
History: Git and revision/backup manifest
-->
# RV-OPS-COOKBOOK-001 — Consolidated operations and recovery guide

**Classification:** Documentation enhancement and dashboard discoverability
**Owner:** Operations / Steward Dashboard
**Status:** PASS for the consolidated guide, dashboard rendering/navigation, full applicable test suite, controlled revisions, and process-graph checks; full Dashboard component DoD remains OPEN
**Target:** Camrui operational guide, served by the existing read-only dashboard Markdown route
**Authority boundary:** Read-only diagnostics; service-local restarts only after diagnosis; migrations, credentials, worker enrollment, shared assignment changes, and destructive recovery are outside this documentation task.

## Source requirements and decisions

- Steward overnight directive requires actionable recovery documentation covering PostgreSQL, migrations, CME, event processor, dashboard/browser, worker registration, scheduling, leases, assignments, verification, stalled assignments, services, and backup/recovery.
- Governing Component DoD requires commands, expected output, symptoms, failure codes, safe recovery, verification, escalation, and destructive-operation warnings.
- Existing component cookbooks and commissioning records remain authoritative; this guide indexes/consolidates them and does not claim absent components are operational.
- Dashboard Markdown renderer is the single presentation path. The static shell links the controlled Markdown document; no parallel HTML source is introduced.

## Acceptance criteria

1. Commands and state semantics match source contracts and commissioned Camrui units.
2. Database examples are read-only; secrets and private payloads are not exposed.
3. Restore guidance cannot be mistaken for permission to overwrite shared data.
4. Dashboard route renders headings, tables, code fences, and safe internal links.
5. Existing dashboard/security/regression tests, canonical graph validation, and controlled revision audit pass.
6. Runtime deployment is limited to the dashboard application release if needed to expose the documentation; no database DDL or data mutation.

## Results and evidence

Source commit `9f752a7a380f58f4032a1c1b5cc097790cd989bc` is deployed as `/opt/riverview-status-dashboard/releases/9f752a7a380f58f4032a1c1b5cc097790cd989bc`; tar archive SHA-256 is `a505d3b4d2e7f88389a53ed04d1859c0211c942af5ae8bb6c5c3492831d6108d`. Only the dashboard symlink and unit were changed; its predecessor release remains `008d942ea57116b0fbdead771c201d3f99305482`. Dashboard restart returned active, loopback port 8766 responded, and PostgreSQL, CME, event processor, and SSH remained active.

The full suite passed `118` tests with `0` failures/errors/skips on isolated PostgreSQL 16.15 at `/tmp/riverview-ops-pgtest-20261011T033950Z-208647`; the test schemas were removed and cluster stopped. Canonical graph check passed 10 workflows / 196 nodes; controlled revision audit passed with zero issues. Firefox 156.0.1 verified live source `9f752a7`, healthy projection/CME, existing completed assignment `m31-real-worker-2533f1c7dd1c433c95bd2cfa8a314d7c` with one independent verification, 16 document links all HTTP 200, 16 headings, 2 tables, 15 code blocks, no unsafe links/scripts, and zero browser errors. Navigation-call samples were 86, 57, 174, and 190 ms (client-side click-call measurements, not full paint time).

The two earlier disposable-cluster failures and their socket-permission/missing-role corrections are retained in `evidence/checkouts/OPERATIONS-COOKBOOK/20261011T034600Z-9f752a7/failed-attempts.md`. The live database remained read-only during this work. The documentation references actual commissioning records for M1.2 ledger/backup, M1.3 event processor, and M2.4 monitor. The historic M3.1 worker result was a bounded deterministic hash task with independent verification and is explicitly not represented as generalized autonomous engineering or operational Grace.

## 2026-10-11 UTC — cross-branch operations documentation update

Ported the password-safe PostgreSQL cookbook and expanded scheduler and worker
diagnostics from the M4.1 operations work onto the existing M3.3 branch. Kept
the branch's repository-knowledge provider cookbook, component contract, flow,
canonical JSON graph, consolidated operations guide, and dashboard navigation.
The dashboard HTTP class passed 12/12, including rendered headings, tables,
code blocks, safe PostgreSQL examples, the shared lease-migration boundary,
worker recovery guidance, repository-knowledge rendering, and resolution of
every static-shell documentation link.

A fresh local socket-only PostgreSQL 16.15 cluster ran the complete suite:
**143 passed, zero failures/errors/skips**. Teardown reported zero `rvtest_*`
schemas and roles; the cluster was stopped and removed. Canonical graph
validation passed **13 workflows / 235 nodes**. Compileall and source diff
check returned zero. Evidence is at
`evidence/checkouts/OPERATIONS-COOKBOOK/20261011T061300Z-m33-doc-update/`.

Read-only catalog evidence confirms `0001_assignment_leases` is present in
`riverview_dev` as a later worker/monitor dependency, with checksum matching
the checked-in SQL. This does not represent standalone M1.4 scheduler
commissioning. No shared data changed. These documents are committed on the
M3.3 source branch so a future package can preserve its knowledge documents
and graph. Deployment has not yet been attempted or claimed.

## Revision history

- **1.0.0 — 2026-10-11:** Initial task record.
- **1.0.8 — 2026-10-11:** Port the safe PostgreSQL/scheduler/worker guidance onto M3.3, record full isolated testing and graph evidence, and retain no-deployment status.


## 2026-10-11 UTC — dashboard cookbook update deployment

The verified documentation update was installed from exact source commit
`8dcec2ada7d811a78f6cb28a1b81e6f8f59b1a9b` as a root-owned, read-only
immutable dashboard release. Archive SHA-256:
`047ee8e2a0bf4e64415199c9bff07cb79961b03bcba1b08dd3f28ea2275b0f60`. The
prior release `7a9ff46e11edc54b1ffe46f63962754e6d2da765` remains intact. Only
`riverview-status-dashboard.service` was restarted; it returned active/running,
`ExecMainStatus=0`, `NRestarts=0`. PostgreSQL, event processor, CME monitor,
notification dispatcher, and SSH remained active. One immediate HTTP probe raced
listener bind; a bounded retry returned HTTP 200 without a service restart or
other corrective action.

Firefox 156.0.1 verified the live projection and readable operations cookbook:
healthy projection and CME, six persisted attention items, completed actual worker
assignment `m31-real-worker-2533f1c7dd1c433c95bd2cfa8a314d7c`, one independent
verification, 17 headings, 2 tables, 17 code blocks, 21 documentation-link
requests all HTTP 200, zero unsafe links/scripts/browser errors, and graph view
position correctly unknown. Navigation calls measured 88–143 ms in this sample.
Evidence and checksums are in
`evidence/checkouts/OPERATIONS-COOKBOOK/20261011T062000Z-deployment-8dcec2a/`.
No shared database state, credentials, workers, or assignments were changed.
