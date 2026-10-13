<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/OPERATIONS-COOKBOOK/20261011T054342Z-scheduler-docs/checkout.md
Component: RIVERVIEW-OPERATIONS
File Revision: 1.0.0
Purpose: Preserve verification evidence for isolated scheduler operations documentation
Authority: Disposable test infrastructure and read-only live service checks only
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-SCHEDULER-DIAGNOSTICS | Capture full suite, query smoke, documentation route, graph, revision, and live service state
History: Adjacent artifacts.json SHA-256 manifest
-->
# RV-OPS-COOKBOOK-SCHEDULER-DIAGNOSTICS — checkout evidence

- **Timestamp:** 2026-10-11 05:43–05:47 UTC
- **Task:** Safe assignment claim, lease, and recovery diagnosis documentation
- **Source commit tested:** `ffea38e10c3205318d6fa040f2525629e6d08234` (`codex/m4.1-db-privilege-boundary`). The local PostgreSQL full suite preceded a final documentation wording clarification; the changed documentation route was rerun afterward. GitHub exact-head CI then ran the full suite, graph synchronization and revision audit against this exact committed tree and passed (run `38115920774`).
- **Host:** `admin1-Default-string`, Ubuntu 24.04.3 LTS. No shared or deployed Riverview state was modified.

## Executed verification

| Check | Result | Evidence |
| --- | --- | --- |
| Complete unittest suite | PASS — 133 passed, 0 failures, 0 errors, 0 skips, isolated PostgreSQL 16.15 | `full-suite.log` |
| Dashboard safe Markdown route regression | PASS — 1/1; verified new headings, table and code block | `dashboard-route.log` |
| Documented SQL query smoke | PASS — isolated `rvtest_scheduler`, applied ledger and lease migrations, created one synthetic ready assignment and lease generation 1; both read-only queries returned expected migration, lease and event metadata | `sql-smoke/` |
| Fixture cleanup | PASS — exact disposable schema teardown; zero remaining `rvtest_` schemas; full-suite cluster had zero `rvtest_` schemas and roles | `sql-smoke/fixture-teardown.txt`, `postgres-cleanup.txt` |
| PostgreSQL cluster lifecycle | PASS — two socket-only temporary clusters fast-stopped; private temporary directories removed after checking their postmaster processes were stopped | `postgres-start.log`, `postgres-stop.log`, `sql-smoke/stop.log` |
| Canonical process graph | PASS — 12 workflows, 226 nodes | `process-graph-check.json` |
| Controlled revision/predecessor audit | PASS — zero findings against the established baseline | `revision-audit.json` |
| Exact-head GitHub CI | PASS — full suite, graph sync, and controlled revision audit | `github-ci.json` |
| Python compilation | PASS — exit 0 | `compileall.txt` |
| Source diff whitespace | PASS — `git diff --check` exit 0 | recorded in task record / commit review |

The first focused test invocation used a nonexistent test class selector and exited 1 before any test executed. This harness-selection error was preserved in `test-selector-failure.log`; the corrected class selector passed. No code/test failure was suppressed.

## Live service preservation

At read-only inspection, PostgreSQL 16, the event processor, CME monitor, status dashboard, and notification dispatcher were active. The dashboard release symlink remained `/opt/riverview-status-dashboard/releases/7a9ff46e11edc54b1ffe46f63962754e6d2da765`; local shell response was HTTP 200. Evidence: `live-service-health.txt`, `live-dashboard-release.txt`, and `live-dashboard-http.txt`.

## Scope and limitations

The new scheduler SQL was exercised only against a private disposable database. M1.4 still has no shared `riverview_dev` migration or deployed scheduler/worker service. No M1.4 live commissioning, worker registration, assignment, authority grant, credential, migration, or shared data change is claimed. The document route regression exercised the working checkout handler; this change was not deployed to the installed dashboard package or browser-verified. M4.1 remains isolated engineering PASS / live commissioning OPEN; M3.3 remains blocked at real live authorization and institutional knowledge preflight. PR #20 remains a draft and unmerged.

**Decision:** PASS for this documentation enhancement and its isolated verification; no roadmap milestone or component is declared DONE.
