# Riverview~ M1.4 isolated engineering verification

**Document Revision:** 1.0.0
**Task:** RV-M1.4-001
**Component:** ASSIGNMENT-SCHEDULER
**Milestone:** M1.4 — independent assignment scheduling
**Environment:** Camrui, Ubuntu 24.04.3, PostgreSQL 16.15 disposable UTF-8 cluster
**Source commit:** `03f6d782dc54d797faff146f98fd3259136a8a60`
**Status:** Isolated implementation verified; CI and commissioning remain open

## Implementation and tests

The scheduler claims the oldest ready assignment without an active lease with
`FOR UPDATE SKIP LOCKED`; lease ownership, generation, heartbeat and expiry are
persisted in the isolated M1.4 migration. A replacement claim increments its
fencing generation. Heartbeats serialize with reclaim through the assignment
row lock. `transition_with_lease` atomically checks the current worker,
generation, and database-time expiry before committing assignment state and its
causally linked event. Replayed start requests are idempotent, and stale workers
cannot perform scheduler-authorized transitions.

The full suite passed **77 tests, zero failures, zero errors, zero skips** on the
exact source commit. This included all three M1.4 PostgreSQL tests: an active
stalled assignment did not block another claim; parallel workers claimed
separate assignments; and expiry/reclaim incremented generation while stale
start, heartbeat and transition calls were rejected. Current generation
transitioned the assignment to running once, and duplicate start replay did not
append a second event.

After the run, the number of `rvtest_*` schemas was zero and the disposable
PostgreSQL cluster was stopped. Full output is `unittest.log`.

## Graph and revision checks

Canonical graph `rv:assignment-scheduler:independent-claims` is included in the
aggregate graph. The graph suite reports 6 workflows and 94 nodes;
`python3 scripts/process_graph.py check` passed. The repository revision audit
against the established baseline passed with no issues.

M1.4 DDL was applied only to disposable schemas. It was not applied to
`riverview_dev`, no service was deployed, and no M1.4 operational acceptance is
claimed. M1.1, M1.2 and M1.3 live state was not modified.
