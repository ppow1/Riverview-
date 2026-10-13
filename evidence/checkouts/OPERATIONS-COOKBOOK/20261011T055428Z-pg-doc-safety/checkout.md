<!-- Riverview~ Controlled Evidence -->
<!-- File Revision: 1.0.1 -->
# PostgreSQL operations documentation safety and M1.4 live-state correction

- **Task:** RV-OPS-COOKBOOK-PG-SECRET-SAFETY / RV-M1.4-LIVE-DEPENDENCY-CORRECTION
- **Component:** OPERATIONS-COOKBOOK / ASSIGNMENT-SCHEDULER / POSTGRES-LEDGER
- **Source branch:** `codex/m4.1-db-privilege-boundary`
- **Source commit:** `efc687769ebe683adb5e0f3e3c14dbd15480f3e3`
- **Observed:** 2026-10-11 UTC on Camrui
- **Scope:** Documentation, dashboard route regression, read-only catalog inspection. No shared database mutation or service deployment.

## Results

The PostgreSQL cookbook now uses local peer-authenticated read-only inspection and password-free isolated test connection examples; it contains neither `PGPASSWORD=` nor a password-bearing PostgreSQL URL. It identifies `riverview_dev` as the application schema and warns against destructive operations on shared state.

Read-only PostgreSQL inspection found nine applied migrations in `riverview_dev`, including `0001_assignment_leases` at `2026-10-10 18:27:04.341175-04:00`. The stored SHA-256 `ce29c2994904f54706db883f61127bf05ee195ecbdce90e7242886e86711b717` matches the checked-in SQL. This corrects prior claims that the migration was absent. It does **not** demonstrate a standalone M1.4 scheduler service, live claim behavior, or M1.4 operational acceptance. The record states the migration was brought in through the later worker/monitor migration chain; no new migration was applied during this inspection.

- Full isolated PostgreSQL 16.15 suite on the pre-correction working tree after the password-safety changes: **133 passed, 0 failures, 0 errors, 0 skips**. See `full-suite.log`; its isolated cluster was stopped and cleanup showed zero `rvtest_*` schemas/roles. The exact-head CI below reran the complete suite after the migration-status correction and route assertion.
- Updated dashboard document-route suite on this exact source commit: **11/11 passed**. See `dashboard-route-final.log`.
- Canonical process graphs: **12 workflows / 226 nodes, PASS**. See `process-graph.json`.
- Controlled file revision/predecessor audit against the parent commit: **PASS, zero issues**. See `revision-audit.json`.
- Compileall and source diff checks: exit 0.
- Current Camrui PostgreSQL, event processor, CME monitor, notification dispatcher, and dashboard services were active; dashboard loopback returned HTTP 200. See `live-service-check.txt`.
- Exact read-only database output and migration file checksum comparison: `live-peer-inspection.txt`.

GitHub exact-head workflow for `efc687769ebe683adb5e0f3e3c14dbd15480f3e3` passed as run `38116541595`: complete test suite, graph validation, and controlled revision/predecessor audit all succeeded. No claim is made here for M4.1 live commissioning, M1.4 commissioning, or full component DoD.

## Evidence files

Logs and machine-readable outputs in this folder are hashed in `artifacts.json`. Earlier isolated scheduler and worker cookbook evidence remains under `evidence/checkouts/OPERATIONS-COOKBOOK/20261011T054342Z-scheduler-docs/` and `20261011T055053Z-worker-docs/`.
