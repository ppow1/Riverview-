<!--
Riverview~ Controlled Document
File: docs/development/OPERATIONS-COOKBOOK-001_REVISION_RECORD.md
Component: RIVERVIEW-OPERATIONS
File Revision: 1.0.0
Purpose: Record the consolidated operational guide deliverable and evidence
Authority: Documentation and diagnostics; does not authorize shared-state mutation
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Initial work record
History: Git and revision/backup manifest
-->
# RV-OPS-COOKBOOK-001 — Consolidated operations and recovery guide

**Classification:** Documentation enhancement and dashboard discoverability
**Owner:** Operations / Steward Dashboard
**Status:** IN PROGRESS pending execution of documented-render, regression, revision, and graph checks
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

To be appended after exact-commit verification. The documentation references actual commissioning records for M1.2 ledger/backup, M1.3 event processor, and M2.4 monitor. The historic M3.1 worker result was a bounded deterministic hash task with independent verification and is explicitly not represented as generalized autonomous engineering or operational Grace.

## Revision history

- **1.0.0 — 2026-10-11:** Initial task record.
