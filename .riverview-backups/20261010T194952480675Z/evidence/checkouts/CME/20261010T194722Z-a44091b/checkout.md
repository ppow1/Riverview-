# CME M2.4 isolated technical acceptance

**Document Revision:** 1.0.0  
**Task:** RV-M2.4-001  
**Component:** CME monitoring service  
**Milestone status:** Isolated technical acceptance PASS; full component DoD remains OPEN.  
**Repository:** `ppow1/Riverview-`  
**Branch:** `codex/m2.4-cme-monitor`  
**Source commit tested:** `a44091bc32e82580dd8a3350e1ecfa47b0157b36`  
**Host:** Camrui, Ubuntu 24.04.3  
**Database:** private PostgreSQL 16.15 Unix-socket-only temporary cluster  
**Run time:** 2026-10-10 19:47 UTC  
**Classification:** Isolated PostgreSQL integration/runtime tests; no shared-schema deployment or live operational commissioning claimed.

## Test and acceptance results

- Exact committed source suite: `RIVERVIEW_TEST_PG_DSN='host=<private-socket> port=55440 dbname=postgres user=admin1' PYTHONPATH=src python3 -m unittest discover -s tests -v` — **95 passed, 0 failures, 0 errors, 0 skipped**.
- M2.4 cases: **6/6 passed**—deadline input validation; no-lease worker is unknown and disabled worker unavailable; fresh/stale CME health; stall, overdue deadline and expired lease detection; progress resolution; independent scheduler progress; persistent idempotent event keys; unavailable database status; real monitor subprocess SIGKILL and restart with fresh instance identity and no duplicate alert.
- Runtime observation: three disposable assignments were scanned. The running assignment remained unchanged and was identified as stalled, overdue work emitted a deadline event, one expired lease emitted one recovery request, the unrelated ready assignment remained claimable, and the worker was accurately reported stale. A second scan emitted zero additional recovery requests. Full event payloads and the machine status snapshot are in `runtime-observation.json`.
- PostgreSQL cleanup: all test fixtures used `rvtest_*` schemas; post-run count was **0**. The private cluster was stopped. Shared `riverview_dev`, installed services, and unrelated databases were not used or changed.
- Process graph: `python3 scripts/process_graph.py check` — **PASS**, 10 workflows, 161 nodes.
- Controlled revision audit: `python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json` — **PASS**, zero issues.
- Python syntax: `python3 -m py_compile src/riverview_core/cme/*.py tests/test_cme_monitor.py tests/test_worker_adapter.py` — PASS.
- Graph records the service lock, whole-set scan, deadline and worker-health measurement, attention/recovery request events, database failure/backoff, and future Grace evidence jump.

## Scope and operational limits

The monitor writes only CME-owned deadline, health and attention tables. It does not change assignment state, schedule or execute work, or actuate recovery. Recovery requests are durable observations; M2.3 remains the recovery owner. Migration `0005_cme_monitoring.sql` was applied only in disposable schemas.

No systemd unit was installed; no migration was applied to shared `riverview_dev`; no long-duration unattended host run, dependency restart drill on the installed service, live Steward dashboard, alert delivery, or independent browser/API consumer was commissioned. The monitor's subprocess restart and API health tests establish software behavior in the isolated environment only.

The full Component Definition of Done remains OPEN, including the M3.1 live Steward visualization, installed unattended operation and external observer evidence, broader blocker clearance, and Steward acceptance. This record is technical milestone evidence, not formal component acceptance.

Failed initial harness runs and their corrective actions are retained in `failed-attempts.md`; the passing result above supersedes none of those records.
