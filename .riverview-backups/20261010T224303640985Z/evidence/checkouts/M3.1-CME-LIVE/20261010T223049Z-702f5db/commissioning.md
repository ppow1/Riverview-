<!-- Riverview~ Controlled Evidence
File: evidence/checkouts/M3.1-CME-LIVE/20261010T223049Z-702f5db/commissioning.md
Component: STEWARD-DASHBOARD / CME
File Revision: 1.0.0
Task: RV-M3.1-002 / RV-M2.4-002
Authority: Scoped live engineering evidence; no formal component acceptance
Changed: 2026-10-10 UTC | RV-M3.1-002 | Record M2.4 shared commissioning and M3.1 live integration
History: New record; evidence manifest checksums
-->
# Camrui CME and dashboard live commissioning

**Repository:** `ppow1/Riverview-`  
**Branch:** `codex/m3.1-status-dashboard`  
**Code/deployment commit:** `702f5db3f03669427a3625425eca04c023a0754c`  
**PR:** [#16](https://github.com/ppow1/Riverview-/pull/16), open draft; not merged.  
**Host:** Camrui, Ubuntu 24.04.3, PostgreSQL 16.15.  
**Source database:** `riverview`, schema `riverview_dev`.

## Controlled migration and preservation

The shared schema initially contained ledger migrations `0001_assignment_event_ledger` and `0002_event_processor_cursor`, three assignments, six institution events, and no M2.4 relations. Before applying DDL, the full custom-format database archive at `/var/backups/riverview-m31-m24-20261010T222218Z/riverview.full.dump` was validated with `pg_restore --list`, SHA-256 `b4d152d8db77506c5780289b55ee1a5ec40d9cf11ebfd30a5fb19ce489bb0277`, size 10,878 bytes, with root-only mode 0600 inside a root-only 0700 directory. It was restored into a disposable database, where the full migration chain succeeded and the original 3 assignments / 6 events were verified. The disposable database and temporary restore copy were removed; no rollback was needed.

As database role `riverview_core`, migrations were applied in dependency order:

1. `assignment_scheduler/migrations/0001_assignment_leases.sql`
2. `worker_adapter/migrations/0001_worker_attempts.sql` through `0004_failure_recovery.sql`
3. `cme/migrations/0005_cme_monitoring.sql`

An immediate full rerun returned no pending migrations. The original assignment and institution-event counts remained 3 and 6. Exact migration checksums and post-deployment observations are in `live-state.json`.

## Installed services and actual state

The root-owned release `/opt/riverview-cme-monitor/releases/702f5db3f03669427a3625425eca04c023a0754c` backs the separate `riverview-cme-monitor.service`. It runs as OS account `riverview`; its unit uses the existing protected systemd `LoadCredential` passfile, and its launcher validates the unit credential, rejects ambient libpq overrides/password-bearing DSNs, and copies the credential into a private 0700 RuntimeDirectory as mode 0600. The configured stall threshold is 300 seconds and scan interval is five seconds. The dashboard remains loopback-only at `127.0.0.1:8766`.

Live PostgreSQL reported three READY assignments with their last durable progress over five hours old. CME observed all three and persisted three `assignment_stalled` alerts. It reported healthy heartbeat/scan state and zero registered workers. The worker registry has zero rows and the independent-verification relation has zero records. The dashboard's bounded API returned HTTP 200 for status, attention, worker, event and assignment projections; state is `healthy/current`, CME is healthy, attention is available, worker count is zero/unknown, and the source identity matches this commit. No shared assignment state or institution event was changed.

Both a normal `systemctl restart` and a live `SIGKILL`/systemd restart were verified. Each recovery produced a new healthy monitor instance and preserved the same three stall-event IDs without duplicates. After SIGKILL, systemd showed `NRestarts=1`. The dashboard, event processor, PostgreSQL, and SSH services remained active. The M1.1 baseline oneshot was rerun and exited successfully with `baseline_ready=true` and no blocker.

## Dashboard and 503 correction

The Steward's PR #16 comment reports four HTTP 503 responses from `/api/v1/attention` at five-second intervals before the migration. The uploaded JSON is not in the repository; only the Steward's transcribed observations are used. Source inspection proved that the route mapped the projection's correct `not_initialized` status to HTTP 503 while the browser polled the absent optional relation on every refresh. The API now returns HTTP 200 with explicit `status=not_initialized` for that domain state, and the browser defers polling until status confirms the relation exists. Real query failures still return HTTP 503. Regression tests cover this behavior.

Firefox 156.0.1 loaded the deployed source and displayed PostgreSQL/CME state and all actual attention events. Six local tab transitions measured 5–46 ms with median 11.5 ms. The client snapshot path captured 8,611 bytes, reported observed state, explicitly excluded credentials/private events/payload bodies/conversation content, and recorded zero browser UI errors. A new browser session after monitor SIGKILL recovery reconnected to healthy CME and the same attention rows; its two navigation samples were 12 ms and 6 ms. Screenshots and exact measurements are retained here.

The prior Steward Windows-over-SSH browser visit confirms external reachability of the same port/entry point before migration. No external post-migration snapshot was transferred, so external observation of this exact deployed source remains unverified.

## Verification results

- Complete applicable suite: **114 passed, 0 failed, 0 errors, 0 skipped** on an isolated Unix-socket-only PostgreSQL 16.15 cluster; zero test schemas remained and the cluster was stopped. See `full-test-suite.log`.
- Isolated PostgreSQL integration continues to verify concurrent independent claim/progress, failure/recovery, and duplicate suppression. Shared `riverview_dev` has no registered worker, so unrelated live assignment progress was not available and was not manufactured by mutating the shared ledger.
- `systemd-analyze verify deploy/systemd/riverview-cme-monitor.service`: PASS.
- `python3 scripts/process_graph.py check`: PASS, 10 workflows / 188 nodes (including synchronized focused and aggregate views).
- Controlled revision audit: PASS, zero issues against the recorded checkout baseline.
- GitHub controlled-checkout CI on code commit `702f5db3f03669427a3625425eca04c023a0754c`: PASS, runs [38091527456](https://github.com/ppow1/Riverview-/actions/runs/38091527456) and [38091531540](https://github.com/ppow1/Riverview-/actions/runs/38091531540).
- Backup and restore evidence: `backup-restore.json`; service recovery evidence: `service-recovery.json`; accurate post-recovery PostgreSQL/dashboard snapshot: `live-state.json` and `live-snapshot-post-recovery.json`; 503 cause and correction: `attention-503-diagnosis.json`.

## Status and limits

**M2.4 scoped operational commissioning: PASS.** Full M2.4 component DoD remains open for sustained unattended operation, a live unrelated-progressing worker, external post-deployment observer evidence, later integrations, and formal component acceptance.

**M3.1 implementation and Camrui live integration: PASS. Full acceptance readiness: NOT READY.** The current live projection is real, redacted and operational, and the browser reconnects after CME recovery. M3.1 cannot satisfy its complete acceptance evidence yet because no live unrelated progressing assignment or verification result exists (there are zero workers), and the exact post-migration source has not been re-observed externally. These are evidence/dependency limits, not simulated successes. No M3.1 acceptance or merge is claimed; PR #16 remains draft as directed.
