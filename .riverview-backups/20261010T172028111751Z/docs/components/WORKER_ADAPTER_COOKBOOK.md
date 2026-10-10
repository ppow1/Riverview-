# Riverview~ worker adapter cookbook

**Document Revision:** 1.0.0
**Component:** WORKER-ADAPTER
**Task:** RV-M2.1-001
**Status:** IN PROGRESS — disposable PostgreSQL only

## Isolated verification

The M2.1 fixture creates a unique `rvtest_*` schema on
`RIVERVIEW_TEST_PG_DSN`, applies M1.2, M1.4, and M2.1 migrations explicitly,
and drops only that schema. Never point it at shared `riverview_dev`.

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<disposable PostgreSQL DSN>' python3 -m unittest tests.test_worker_adapter -v
```

The tests verify token authentication, capability and assignment-scope checks,
credential digest storage, deterministic result persistence and replay, input
collision rejection, and visibility of an unfinished attempt.

## Operational boundaries

M2.1 has no systemd worker service or network listener. The test credential is
kept in process memory and is not logged. Do not deploy this adapter until an
approved secret-delivery mechanism, worker process lifecycle, and operational
recovery procedure have been verified. An attempt left `running` is evidence of
incomplete work, not proof of whether a future external effect occurred. The
current deterministic task has no external side effects.
