<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/STEWARD-DASHBOARD/20261010T2145Z-ba831a7/commissioning.md
Component: STEWARD-DASHBOARD
File Revision: 1.0.0
Task: RV-M3.1-001
Source Commit: ba831a7339e1f4491cf1296eeac271b246409664
Deployment: m3.1-camrui
Authority: Read-only local commissioning; no shared-schema changes
-->
# M3.1 checkout evidence — Camrui

## Outcome

Technical implementation and local operational verification are in progress. The dashboard is active at 127.0.0.1:8766 and reads the existing PostgreSQL ledger. The complete M3.1 gate is not DONE: the shared schema has no M2.4 CME monitor tables, so live CME/worker health and attention are honestly shown as not_initialized. No shared-schema migration or monitor service installation was performed. External browser verification from a second development machine is also not verified.

## Environment and source

- Repository: ppow1/Riverview-
- Baseline: main at e9c66afabe88fe02403a35c8ede83eba54bca2e2; PR #14 is integrated.
- Feature branch: codex/m3.1-status-dashboard.
- Deployed source: ba831a7339e1f4491cf1296eeac271b246409664.
- Dashboard service: riverview-status-dashboard.service, active and enabled.
- Listener: 127.0.0.1:8766 only. The preflight scan found no listener or configured Riverview owner in 8700–8799; 8765 was not altered. Separate client-machine port inventory was unavailable.
- PostgreSQL: database riverview, schema riverview_dev, latest migration 0002_event_processor_cursor.
- Live ledger observation: three assignments, six events, six correlation IDs. No assignment bodies or event payloads were retained in this report.
- Live CME/worker status: not_initialized. riverview-cme-monitor.service was not installed and M2.4 monitor relations were not present. Attention endpoint returned its explicit not_initialized result. Shared state was not modified.
- Runtime passfile: /run/riverview-status-dashboard/pgpass, mode 0600, owner riverview:riverview. No credential contents were read into evidence.
- Owner-authorized token file is outside the repository. Its content and value are not recorded.

## Tests and measurements

- Full repository suite: 108 tests passed, zero skips, using a disposable PostgreSQL 16.15 cluster. The test log is included.
- Dashboard PostgreSQL integration: assignment/event projection, stale/future heartbeats, privacy filtering, independent verification detail, keyset paging, missing/unavailable source, and CME stall attention passed.
- Isolated browser observation: a disposable PostgreSQL/CME fixture showed one stalled assignment, a separate progressing assignment, and the persisted attention row in Firefox. This is labelled test data in the screenshot and is not live host state.
- Live browser: Firefox 156.0.1 showed three Camrui PostgreSQL assignments and source commit ba831a7339e1f4491cf1296eeac271b246409664.
- 100 client navigation samples: median 2 ms; p95 5 ms; maximum 143 ms. A local view change during a deliberately delayed 1.5-second status fetch completed in 1 ms. The intentional delay is a responsiveness test, not an operational dependency.
- Recorded API resources: median 96 ms; maximum 219 ms across 13 observed API resources.
- Live browser snapshot: 14,978 bytes, observed_state true, projection healthy, bounded assignment/event counts, no credential/token values; see browser-observation.json for its snapshot checksum.
- Authenticated status recovered after a systemd restart in under one second. The event processor remained active.
- Process graph validation: 10 graphs / 180 nodes, PASS. Generated JSON/Mermaid synchronization: PASS.
- Controlled revision audit against the e56f25c pre-change baseline: PASS. Baseline and machine-readable result are retained.
- systemd-analyze verify: PASS.

## Deployment corrections

The first unit start exposed a relative current-symlink target error (systemd CHDIR failure); current now points to releases/<commit>. The next start exposed that libpq rejects systemd's root-owned read-only 0440 credential mount as a passfile. The dashboard launcher now reuses the established runtime_baseline exact-unit credential validation/copy helper, storing the passfile as 0600 in a private systemd RuntimeDirectory. The active service reports source commit ba831a7339e1f4491cf1296eeac271b246409664. Failed-start diagnostics remain in the systemd journal; secrets were not logged.

## Status and open criteria

Status: IN PROGRESS, not DONE. Live PostgreSQL/dashboard integration, browser responsiveness, snapshot, local service restart, test suite, graph synchronization, and revision controls are verified. Live CME integration awaits M2.4 monitor schema/service commissioning on the shared development schema; no authorization to change shared state was inferred from M3.1. External-browser/independent-observer verification remains outstanding. Full component DoD, later console capabilities, and formal acceptance are not claimed.
