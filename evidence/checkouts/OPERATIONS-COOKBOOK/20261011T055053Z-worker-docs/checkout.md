<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/OPERATIONS-COOKBOOK/20261011T055053Z-worker-docs/checkout.md
Component: RIVERVIEW-OPERATIONS
File Revision: 1.0.0
Purpose: Preserve verification for isolated worker lifecycle and recovery documentation
Authority: Disposable PostgreSQL only and read-only installed-service inspection
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS | Capture isolated execution, redacted SQL, browser route, and recovery evidence
History: Adjacent artifacts.json SHA-256 manifest
-->
# RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS — checkout evidence

- **Timestamp:** 2026-10-11 05:50–05:52 UTC
- **Source:** `ff99fe92cc5f82cd6177f21bbd72ae137e3118fa`, branch `codex/m4.1-db-privilege-boundary`
- **Host:** Ubuntu 24.04.3, private PostgreSQL 16.15 test cluster bound to a Unix socket only. The local hostname string is recorded in the preceding scheduler-doc checkout.
- **Authority:** No installed unit, shared database, live credential, role, assignment, or deployment path was changed.

## Verification

| Check | Result | Evidence |
| --- | --- | --- |
| Full unittest suite | **PASS 133/133**, 0 failures/errors/skips on disposable PostgreSQL | `full-suite.log` |
| Dashboard safe-document route | **PASS 1/1**, worker cookbook headings, table, code blocks, and credential warning rendered safely | `dashboard-route.log` |
| Worker/verifier fixture | **PASS isolated integration**: two distinct synthetic registered identities; `ContinuousWorker` persisted deterministic result; separate SHA-256 verifier returned `ACCEPTED`; fixture assignment reached `completed` | `worker-fixture.log` |
| Cookbook relation preflight and redacted row query | **PASS**: all six expected relations resolved; registry, succeeded attempt/result digest, distinct accepted verifier, completed retry-safe intent and empty recovery view returned. No token, input, event payload, evidence reference, summary, or result JSON was selected. | `relation-preflight.log`, `worker-query.log` |
| Isolated cleanup | **PASS**: exact `rvtest_worker` fixture teardown; zero remaining `rvtest_` schemas/roles; cluster fast-stopped and temporary directory removed | `fixture-teardown.txt`, `postgres-stop.log` |
| Process graph | **PASS** — 12 workflows, 226 nodes | `process-graph-check.json` |
| Controlled revisions/predecessors | **PASS** — zero findings against established baseline | `revision-audit.json` |
| Compile and whitespace checks | **PASS**, exit 0 | `compileall.txt`, `source-diff-check.txt` |
| Installed service preservation | PostgreSQL, event processor, CME monitor, dashboard, and notification dispatcher all active; dashboard HTTP 200; release symlink unchanged at `7a9ff46e11edc54b1ffe46f63962754e6d2da765` | `live-service-health.txt`, `live-dashboard-http.txt`, `live-dashboard-release.txt` |

The deterministic worker/verifier run is an isolated contract exercise. It is not a live worker, code-writing agent, institutional knowledge service, M1.4 commissioning, M3.3 demonstration, or Grace operational evidence. GitHub exact-head CI is tracked separately on PR #20.

## Limits

`WORKER_ADAPTER_COOKBOOK.md` documents protected enrollment as an authority workflow but no live enrollment CLI or always-on worker service exists. Shared `riverview_dev` was not queried or mutated in this task. The updated documentation route was exercised in the checkout handler, not deployed into the installed dashboard package or independently browser-verified. Full component DoD and M4.1 live commissioning remain open; no milestone acceptance is asserted.

**Decision:** PASS for this documentation enhancement and isolated verification; roadmap/system completion remains OPEN.
