<!--
Riverview~ Controlled Document
File: docs/development/OPERATIONS-COOKBOOK-001_REVISION_RECORD.md
Component: RIVERVIEW-OPERATIONS
File Revision: 1.0.8
Purpose: Record the consolidated operational guide deliverable and evidence
Authority: Documentation and diagnostics; does not authorize shared-state mutation
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Record passing suite, live deployment, and browser evidence
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-SCHEDULER-DIAGNOSTICS | Record safe isolated scheduler diagnostics and regression results
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-SCHEDULER-QUERY-CLARIFICATION | Record executed query smoke and final cookbook revision
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS | Record read-only worker/attempt/verification/recovery diagnostics
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-WORKER-CHECKOUT | Record full regression, persisted isolated worker/verifier cycle, and exact query execution
History: Git and revision/backup manifest
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-PG-SECRET-SAFETY | Record safe credential-free PostgreSQL documentation and live peer-query evidence
Changed: 2026-10-11 UTC | RV-M1.4-LIVE-DEPENDENCY-CORRECTION | Correct shared lease-migration status from read-only catalog evidence
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-DASHBOARD-PACKAGE-ROLLBACK | Preserve failed package check, restore prior release, and record remaining source-sync requirement
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

## 2026-10-11 UTC — RV-OPS-COOKBOOK-SCHEDULER-DIAGNOSTICS

Expanded `ASSIGNMENT_SCHEDULER_COOKBOOK.md` with bounded read-only queue,
lease-generation, event-causality and migration inspection, interpretation of
ready/current/expired/running states, stale-token recovery, and escalation
criteria. The guide explicitly limits these scheduler queries to a known
disposable schema because M1.4 is not deployed to shared `riverview_dev`.
Added a dashboard route regression that requires the new headings, table, and
code block to render through the safe Markdown endpoint.

Verification used a private Unix-socket-only PostgreSQL 16 cluster at port
55486 in `/tmp`; no shared database or installed service was changed. The
documented migration and lease queries were executed against disposable schema
`rvtest_scheduler` after applying the reviewed ledger and scheduler fixtures
and creating one synthetic ready assignment with a current lease. The read-only
output showed the migration checksums, worker/generation/expiry and causal event
metadata without objective or payload; explicit teardown left zero `rvtest_`
schemas. Full suite: 133 passed, zero failures/errors/skips. The focused dashboard document
route passed 1/1; process graph check passed (12 workflows/226 nodes),
revision audit passed with no findings, and compileall exited 0. Fixture
cleanup reported zero `rvtest_` schemas and roles; the cluster was fast-stopped
and its exact temporary directory removed. An initial test selector used a
nonexistent unittest class name and exited 1 before any test ran; the selector
was corrected to `DashboardHTTPTests` and the intended route test passed.
Exact logs and checksums are retained at
`evidence/checkouts/OPERATIONS-COOKBOOK/20261011T054342Z-scheduler-docs/`.

This change improves isolated scheduler diagnosis only. It does not imply M1.4
deployment, M3.3 acceptance, a live worker, or a change to the shared ledger.

## 2026-10-11 UTC — RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS

Expanded `WORKER_ADAPTER_COOKBOOK.md` with migration/relation preflight,
redacted worker registry and attempt/result/verification/intent/recovery
queries, fail-safe interpretation, credential/enrollment boundaries, and
unavailable-worker limitations. Added dashboard route assertions for the
worker diagnostic headings, table and code blocks. Verification used a private
socket-only PostgreSQL 16 cluster on port 55487. The complete local suite
passed **133/133 with zero skips/errors/failures**. An isolated, fully migrated
schema registered separate synthetic executor and verifier identities; the
ContinuousWorker persisted an actual deterministic result, the independent
verifier accepted it, and the assignment reached `completed`. The documented
read-only query returned both registry rows, the succeeded attempt and result
digest, the distinct verifier and `ACCEPTED` decision, the completed retry-safe
intent, and zero recovery rows. No bearer credential, result JSON, objective,
or evidence payload was emitted. The schema was explicitly dropped within the
disposable cluster; no test schemas or roles remained, and the cluster was
stopped and removed. Process graph validation passed (12 workflows/226 nodes),
controlled revision/predecessor audit reported zero issues, compileall and
source `git diff --check` passed. Exact outputs and checksums are in
`evidence/checkouts/OPERATIONS-COOKBOOK/20261011T055053Z-worker-docs/`.

This is isolated integration evidence only. No live worker service, shared
worker identity, credential, assignment, or database object was added. The
dashboard document route was tested against the working checkout, not deployed
to the installed dashboard package. M1.4 live commissioning and full worker
Component DoD remain open; exact-head GitHub CI is tracked on PR #20.

## Revision history

- **1.0.0 — 2026-10-11:** Initial task record.
- **1.0.1 — 2026-10-11:** Record consolidated guide commissioning and dashboard deployment.
- **1.0.2 — 2026-10-11:** Add the scheduler claim/lease diagnosis and route evidence.
- **1.0.3 — 2026-10-11:** Record query smoke evidence and final cookbook revision.
- **1.0.4 — 2026-10-11:** Register the worker diagnostic improvement.
- **1.0.5 — 2026-10-11:** Record isolated worker/verifier query smoke and checkout results.
- **1.0.6 — 2026-10-11:** Record PostgreSQL cookbook secret-safety review and correct M1.4 migration-presence statement using live read-only evidence; no scheduler commissioning claim.
- **1.0.7 — 2026-10-11:** Record dashboard candidate package 404, immediate symlink rollback, preserved services, and remaining M3.3 source-content integration requirement.
Changed: 2026-10-11 UTC | RV-M4.1-DASHBOARD-DOCS-LIVE | Record immutable live docs/graph overlay, startup rollback and bounded readiness recovery, and Firefox verification evidence
