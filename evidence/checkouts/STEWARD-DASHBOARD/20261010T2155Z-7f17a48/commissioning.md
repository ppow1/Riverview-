<!--
Riverview~ Controlled Evidence
File: commissioning.md
Component: STEWARD-DASHBOARD
File Revision: 1.0.2
Purpose: Record M3.1 isolated, local operational commissioning evidence
Authority: Read-only dashboard observations; not Steward acceptance
Changed: 2026-10-10 UTC | RV-M3.1-001 | Capture worker health UI, full suite, Camrui deployment and PR CI
History: Git and artifact sidecar manifest
-->
# M3.1 commissioning checkpoint

**Classification:** local operational commissioning plus isolated integration tests; component status IN PROGRESS.
**Source commit:** `7f17a48f6fa47f151453c7e2e468532576942b19`; branch `codex/m3.1-status-dashboard`.
**Main baseline:** `e9c66afabe88fe02403a35c8ede83eba54bca2e2` with M2.4 PR #14 integrated. Issue #13 and draft PR #15 were reviewed as requirements. PR #15 remains unmerged.
**Port:** loopback `127.0.0.1:8766`; preflight found no listener in 8700–8799. Port 8765 was not changed. Separate development-client port state was unavailable.
**Legacy review:** selectively reused vNext's shell-first, local-navigation projection approach, bounded snapshot/redaction concepts, and resident/session boundary research; did not import old applications, databases, credentials or obsolete dependencies. See `docs/components/STATUS_DASHBOARD.md`.

## Runtime observations

The active root-owned versioned release is `/opt/riverview-status-dashboard/releases/7f17a48f6fa47f151453c7e2e468532576942b19`. Systemd serves the authenticated UI/API on loopback and reads PostgreSQL `riverview.riverview_dev` without mutating it. At capture, the projection was healthy/current with 3 assignments, event cursor 6, and migration `0002_event_processor_cursor`; these are observed Camrui values. The event processor remained active.

The shared schema did not contain `cme_monitor_health`, `cme_monitor_events`, `worker_registry`, `assignment_leases`, `worker_attempts`, or `verification_records`. Accordingly, live CME, workers, verification, and attention were shown as `not_initialized` (worker route HTTP 503 with explicit status). No shared-schema migration was run and no M2.4 service was installed. Isolated PG integration did verify actual CME stall detection, attention, event correlation, independent assignment progress, and per-worker health; fixture results are not live host state.

Firefox 156.0.1 rendered the live dashboard and identified the exact deployed source SHA. Across 100 local view changes, JavaScript navigation was median 2 ms, p95 5 ms, maximum 110 ms. While a status API request was delayed 1.5 s, navigation took 2 ms. Fourteen API resource samples had median 110.5 ms and maximum 267 ms. Initial shell navigation took 633.45 ms. These are a reproducible local baseline, not a promise about remote networks. The visible dashboard showed three actual ready assignments and truthful uninitialized CME/worker states.

The browser snapshot was 15,095 bytes, represented an observed healthy projection, included three assignments and six institution events, declared workers not initialized, and passed token/auth-header absence and 128 KiB bound checks. The browser added only bounded local navigation/error metadata. Snapshot references and omitted-data statements distinguish observations from unavailable resident/work-order/capability facilities.

A restart of only `riverview-status-dashboard.service` recovered authenticated PostgreSQL status in 846.66 ms. Its release identity matched the full SHA. The listener remained on 127.0.0.1:8766, the private passfile was mode 0600, and the M1.3 event processor stayed active. No existing services were reconfigured. An initial activation under a short release path was detected because source identity showed unknown; that release was not kept active and the deployment was corrected to a full-SHA path.

## Verification

- Full suite: 109 tests passed, 0 failures/errors/skips, on isolated PostgreSQL 16.15 at private socket `/tmp/rv-m31-pgsocket:55432`; unique disposable schemas were cleaned by tests. Command: `PYTHONPATH=.:src RIVERVIEW_TEST_PG_DSN='host=/tmp/rv-m31-pgsocket port=55432 dbname=postgres user=admin1' python3 -m unittest discover -s tests -v`.
- Process graph: 10 graphs, 182 nodes; schema/reference validation and generated-view synchronization passed. Canonical file `process_graphs/steward-dashboard/status.json`; generated aggregate view retained.
- Controlled revisions/backups: audit passed against baseline inventory of deployed predecessor commit `ba831a7339e1f4491cf1296eeac271b246409664`. The retained inventory file carried an earlier `e56` filename; its `.riverview-revisions.json` entry matches ba831a7's exact SHA and revision. This record uses the verified deployed baseline identity.
- `systemd-analyze verify deploy/riverview-status-dashboard.service`, Python compileall, and source `git diff --check` passed. GitHub PR #16 controlled-checkout runs 38089528144 and 38089536901 passed on exact head `f5b35cdc7492b6688477a857ca6dc179b368c5dc`, including the full suite, graph synchronization/validation, and controlled revision/predecessor checks. The full suite is isolated integration evidence; the live browser/systemd/PostgreSQL observations are local Camrui commissioning, not independent external verification.

## Acceptance state

**PASS:** read-only authenticated dashboard, live base PostgreSQL assignments/events, freshness/unavailable distinctions, bounded pages/snapshot, privacy behavior, local browser navigation and slow-request isolation, loopback port ownership, systemd restart recovery, process graph synchronization, local test suite.

**PR state:** https://github.com/ppow1/Riverview-/pull/16 is an unmerged draft; no merge is authorized by this commissioning record.

**NOT VERIFIED / OPEN:** live M2.4 CME/worker/attention/verification relations and event display require authorized M2.4 shared-schema/service commissioning; external browser/observer verification is unavailable; resident chat, work-order promotion, capability/resource registry, AI/API/browser parity, sustained unattended operational cycle, and full Steward acceptance remain later roadmap/full Definition of Done work. No M3.1 DONE or formal Steward acceptance is claimed.
