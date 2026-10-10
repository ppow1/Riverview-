# Riverview~ assignment scheduler cookbook

**Document Revision:** 1.0.0
**Component:** ASSIGNMENT-SCHEDULER
**Task:** RV-M1.4-001
**Status:** IN PROGRESS — isolated PostgreSQL verification only

## Isolated schema verification

Use only a unique `rvtest_*` schema on the disposable database identified by
`RIVERVIEW_TEST_PG_DSN`. The test fixture creates and removes that schema. The
base ledger is installed first; the scheduler migration is applied explicitly
from its separate directory. Never target the shared `riverview_dev` schema for
these tests.

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<disposable PostgreSQL DSN>' python3 -m unittest tests.test_assignment_scheduler -v
```

The first integration tests cover oldest-first selection, an active stalled
lease not blocking another assignment, simultaneous claims by separate worker
connections, expiration and generation increment, stale heartbeat/start
rejection, and atomic causally linked `running` transition. No worker external
effect is executed by these tests.

## Failure diagnosis

- `SchedulerError` for a missing assignment or ineligible state: inspect
  assignment history; do not edit its state directly.
- `StaleLeaseError`: discard the token, query the current durable generation,
  and reacquire through `claim_next`; never retry a write with the old token.
- No claim: query ready assignments and lease expiries with database time. A
  healthy scheduler call is not evidence that work is progressing.
- Migration missing or checksum mismatch: stop and verify the recorded and
  source checksums; do not let application startup repair schema state.

M1.4 has not been deployed or commissioned. The recovery path for expired leases
on assignments already in `running` requires an explicit later engineering step.
