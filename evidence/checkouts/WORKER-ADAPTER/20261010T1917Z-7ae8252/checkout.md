# Riverview M2.3 isolated failure and restart recovery evidence

**Document Revision:** 1.0.0
**Task:** RV-M2.3-001
**Milestone:** M2.3 — failure and restart recovery
**Component:** WORKER-ADAPTER / CME recovery boundary
**Host:** Camrui, Ubuntu 24.04.3
**Database:** PostgreSQL 16.15, private temporary Unix-socket-only cluster
**Source commit:** `7ae8252469612920bd07dc84a6d65ef374aa8886`
**Status:** Isolated technical criteria passed; no shared deployment or operational commissioning claimed

The recovery coordinator was exercised against disposable `rvtest_*` PostgreSQL schemas. The worker process was terminated with SIGKILL after (a) a test effect committed and (b) a worker result committed but before assignment advancement. A restarted `ContinuousWorker.run_once()` reconciled before claiming more work. Unknown external outcomes entered `awaiting_steward` and were not repeated; unrelated work continued. A retry-safe intent was fenced and requeued under a higher lease generation. A committed result advanced to independent verification, was independently accepted, and remained completed on a later recovery pass.

**Full suite command:** `PYTHONPATH=.:src RIVERVIEW_TEST_PG_DSN=host=<private-socket> port=55439 dbname=postgres user=admin1 pytest -q tests` — 89 passed, 0 failed, 0 errors, 0 skipped.

**Post-run database check:** PostgreSQL 16.15; zero `rvtest_*` schemas remained. The temporary cluster was stopped and its directory removed. Shared `riverview_dev`, installed services, and production data were not used or changed.

**Additional checks:** revision audit passed with zero issues; process-graph validation and synchronization passed (10 workflows, 156 nodes); Python compile check and `git diff --check` passed. Full output and structured results are recorded in sibling artifacts.
