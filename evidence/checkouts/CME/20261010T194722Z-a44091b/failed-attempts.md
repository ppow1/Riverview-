# RV-M2.4-001 failed verification attempts and corrections

**Document Revision:** 1.0.0  
**Source commit:** `a44091bc32e82580dd8a3350e1ecfa47b0157b36`  
**Status:** Failures corrected and retested; final full suite PASS.

1. The first CME fixture run failed in setup because the explicit migration loader accepts only SQL entries, while a Python `__init__.py` had been placed inside the migration directory. The file was preserved in `.riverview-backups/20261010T193543249339Z/` and removed from that SQL-only directory. Migration loading then passed.
2. Initial fixture operations used a PostgreSQL connection whose search path remained `public`; affected statements could not find the disposable schema's `events` table. The fixture now sets its own schema explicitly. Row assertions use `dict_row` consistently.
3. Initial lease aging violated the scheduler's `expires_at > acquired_at` constraint. The test now backdates all three timestamps consistently, preserving the production constraint.
4. A monitor attention-resolution query initially looked for deadline data on `assignments`; deadline metadata is intentionally CME-owned. The query was corrected to join `cme_assignment_deadlines`, then the progress-resolution test passed.
5. One complete-suite run exposed an existing worker-provider timeout regression test with a fragile `<100 ms` wall-time assertion; observed elapsed time was 101 ms while the behavior was correct. The test now synchronizes on provider start/release and proves the worker returns while the provider remains blocked. It still asserts `UNAVAILABLE` and `WAITING_FOR_EVIDENCE`; it no longer treats unrelated scheduler latency as provider behavior.
6. Early fixture setup failures occurred before unittest could call teardown and left eight `rvtest_*` schemas in the private temporary cluster. Those schemas were enumerated and dropped only in that disposable cluster. The final exact-commit suite and runtime probe each verified zero residual `rvtest_*` schemas, and the cluster was stopped.

The restart test also had one transient failure in an earlier full-suite attempt. The isolated restart test was rerun successfully; the exact-commit full suite passed 95/95. It force-kills a real monitor child process, starts a replacement process, and verifies a new instance heartbeat without duplicate attention events.
