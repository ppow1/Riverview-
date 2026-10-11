<!--
Riverview~ Controlled Document
File: docs/development/OPERATIONS-COOKBOOK-001_REVISION_RECORD.md
Component: RIVERVIEW-OPERATIONS
File Revision: 1.0.1
Purpose: Record the consolidated operational guide deliverable and evidence
Authority: Documentation and diagnostics; does not authorize shared-state mutation
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Record passing suite, live deployment, and browser evidence
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

## Revision history

- **1.0.0 — 2026-10-11:** Initial task record.
