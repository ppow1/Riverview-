<!-- Evidence file revision: 1.0.0; SHA-256 and artifact identity are in artifacts.json. -->
# RV-OPS-COOKBOOK-001 — Verification and commissioning

**Captured:** 2026-10-11 UTC  
**Source commit:** `9f752a7a380f58f4032a1c1b5cc097790cd989bc`  
**Branch:** `codex/m3.1-status-dashboard`  
**Target:** Camrui, Ubuntu 24.04.3, PostgreSQL 16.15  
**Deployment:** `/opt/riverview-status-dashboard/releases/9f752a7a380f58f4032a1c1b5cc097790cd989bc`  
**Archive SHA-256:** `a505d3b4d2e7f88389a53ed04d1859c0211c942af5ae8bb6c5c3492831d6108d`

## Executed checks

| Check | Command / method | Result |
|---|---|---|
| Full suite | `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='host=/tmp/riverview-ops-pgtest-20261011T033950Z-208647/socket port=55497 dbname=postgres user=admin1' python3 -m unittest discover -s tests -v` | **PASS — 118 tests, zero failures/errors/skips**, including PostgreSQL integration, process restart, idempotency, worker recovery, dashboard security and document route. Output: `full-suite.log`. |
| Test DB cleanup | Isolated PostgreSQL query of version/listen address/`rvtest_%` schema count | PostgreSQL 16.15, no TCP listener, zero leftover test schemas; test cluster then stopped. |
| Process graph | `python3 scripts/process_graph.py check` | **PASS — 10 workflows / 196 nodes**, generated views synchronized. |
| Revision audit | `python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json` | **PASS — zero issues.** |
| Whitespace | `git diff --check` | **PASS.** |
| Live browser | `python3 scripts/verify_status_dashboard_browser.py --assignment-id m31-real-worker-2533f1c7dd1c433c95bd2cfa8a314d7c --output evidence/checkouts/OPERATIONS-COOKBOOK/20261011T034600Z-9f752a7` | **PASS.** See `browser-acceptance.json` and screenshots. |
| GitHub CI | PR #16 controlled-checkout runs 38109386565 and 38109389114 | **PASS** for source commit `9f752a7`. |

## Live browser result

Firefox 156.0.1 read actual PostgreSQL/CME/dashboard state. Projection and CME were healthy; `/api/v1/attention` returned HTTP 200 with six persisted attention rows. The previously completed M3.1 assignment remained `completed`, with one persisted attempt and one independent verification. The guide rendered 16 headings, two tables, and 15 fenced code blocks. All 16 component-document links returned HTTP 200; no raw metadata, script, unsafe links, or browser errors were observed. Graph API showed 12 nodes, one decision, ten local edges and one cross-workflow edge; execution position remained correctly unknown because the ledger has no process-node identity. Navigation call timings were 86, 57, 174 and 190 ms; these are click-call timing samples, not full paint measurements.

## Deployment scope and health

The old dashboard release was `008d942ea57116b0fbdead771c201d3f99305482`; it remains on disk as the immediate rollback target. Release `9f752a7...` is selected by `/opt/riverview-status-dashboard/current`. The dashboard unit restarted successfully and is active with `NRestarts=0`, listening at `127.0.0.1:8766`. PostgreSQL 16/main, `riverview-event-processor.service`, `riverview-cme-monitor.service`, and SSH remained active. No systemd unit contents, credentials, migrations, database objects, assignment records, or shared data were changed. The live migration ledger was queried read-only and confirmed the previously commissioned chain; no new migration was applied.

## Status

The comprehensive operations guide and dashboard document presentation/navigation are **PASS**. This does not close the full M3.1 Component DoD or claim operational Grace. A post-change Windows-browser observation is still absent. Current roadmap work continues at M3.2.
