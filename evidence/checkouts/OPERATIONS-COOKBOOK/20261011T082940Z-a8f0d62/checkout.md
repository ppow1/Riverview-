<!--
Riverview~ Checkout Evidence
File: evidence/checkouts/OPERATIONS-COOKBOOK/20261011T082940Z-a8f0d62/checkout.md
Component: RIVERVIEW-OPERATIONS / STEWARD-DASHBOARD
Document Revision: 1.0.0
Purpose: Record exact-source dashboard deployment and live cookbook/browser verification
Source Commit: a8f0d6276b45bf51f523825527f5f9e3c80cd250
Deployed Commit: a8f0d6276b45bf51f523825527f5f9e3c80cd250
Host: Camrui / Ubuntu 24.04.3
Timestamp: 2026-10-11T08:29:40Z
Task: RV-OPS-COOKBOOK-LIVE-DOCS-DEPLOYMENT
History: Evidence manifest and Git
-->
# Live operations cookbook deployment verification

- **Result:** PASS for dashboard-only documentation deployment and browser checks. This is not M3.3 or M4.1 milestone acceptance.
- **Source:** PR #19 branch `codex/m3.3-repository-knowledge`, commit `a8f0d6276b45bf51f523825527f5f9e3c80cd250`; exact-head CI run 38124873054 passed.
- **Package:** `/var/lib/riverview/deployments/dashboard/a8f0d6276b45bf51f523825527f5f9e3c80cd250/source.tar.gz`; SHA-256 `739e38068929f16a9bffcf165a0fec0e4a4587ee64987105313be8da3c9d607b`. Independent package verifier passed; all 1,279 checksummed package entries verified before installation.
- **Release transition:** prior `c85faf9180a934e61d4e382a98687a09fbfaf0f3` retained; new full-SHA release installed root:root read-only and activated through the `current` symlink. The systemd unit checksum is unchanged. Only the dashboard unit was restarted.
- **Service health:** dashboard active/running, `ExecMainStatus=0`, `NRestarts=0`, bound to `127.0.0.1:8766`; PostgreSQL, event processor, CME monitor, notification dispatcher and SSH all active. No migration, database, credential, worker, assignment, or other service changes.
- **Browser:** Firefox 156.0.1 read actual completed assignment `m31-real-worker-2533f1c7dd1c433c95bd2cfa8a314d7c`, healthy/current projection and CME, six attention items, and one independent verification. Browser errors and failed checks: zero.
- **Rendered guide:** 18 headings, 2 tables, 18 code blocks; raw Markdown absent; no scripts or unsafe links. All 21 linked component documents returned HTTP 200. The current runbook includes the observed PostgreSQL backup-path permission failure, its safe PostgreSQL-owned backup/restore procedure, and all six active Camrui services including the notification dispatcher.
- **Workflow view:** 12 nodes, 11 canonical edges, one decision, valid cross-workflow jump. Live execution position correctly remained unknown because no node identity is persisted.
- **Navigation handler measurements:** Assignments 170 ms, Activity 138 ms, Overview 312 ms, Workflows 108 ms in this sample. These are client navigation-call timings, not paint time or sustained performance results.
- **Rollback:** prior immutable release remains at the recorded path. No rollback was required.
- **Evidence:** browser JSON/screenshots, service state, package verifier output, deployment metadata and hashes are in this directory; see `artifacts.json`.
