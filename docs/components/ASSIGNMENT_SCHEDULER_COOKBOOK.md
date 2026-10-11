<!--
Riverview~ Controlled Document
File: docs/components/ASSIGNMENT_SCHEDULER_COOKBOOK.md
Component: ASSIGNMENT-SCHEDULER
File Revision: 1.0.9
Purpose: Diagnose isolated assignment claims, leases, and stale fencing safely
Authority: Read-only diagnosis; never edits the shared ledger
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-SCHEDULER-DIAGNOSTICS | Add reproducible read-only claim and lease diagnosis
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-SCHEDULER-QUERY-CLARIFICATION | Clarify schema substitution and global event sequence gaps
Changed: 2026-10-11 UTC | RV-M1.4-LIVE-DEPENDENCY-CORRECTION | Correct shared dependency migration status; distinguish presence from scheduler commissioning
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-CROSS-BRANCH-DOC-PORT | Preserve M3.3 documentation and register observed shared lease dependency accurately
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-CROSS-BRANCH-REVISION-ALIGNMENT | Align document revision metadata with the globally monotonic file revision
History: Git and revision backup manifest
-->
# Riverview~ assignment scheduler cookbook

**Document Revision:** 1.0.9
**Component:** ASSIGNMENT-SCHEDULER
**Task:** RV-M1.4-001
**Status:** Isolated technical criteria verified; dependency migration present in shared schema; standalone scheduler commissioning remains open

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
effect is executed by these tests. The exact-commit full-suite evidence and
cleanup results are retained in the [M1.4 checkout record](../../evidence/checkouts/ASSIGNMENT-SCHEDULER/20261010T1715Z-03f6d78/checkout.md).

## Failure diagnosis

- `SchedulerError` for a missing assignment or ineligible state: inspect
  assignment history; do not edit its state directly.
- `StaleLeaseError`: discard the token, query the current durable generation,
  and reacquire through `claim_next`; never retry a write with the old token.
- No claim: query ready assignments and lease expiries with database time. A
  healthy scheduler call is not evidence that work is progressing.
- Migration missing or checksum mismatch: stop and verify the recorded and
  source checksums; do not let application startup repair schema state.

The M1.4 lease migration is present in shared `riverview_dev` as a dependency
of the later worker and monitoring migration chain. A read-only catalog check
on 2026-10-11 found `0001_assignment_leases` with checksum
`ce29c2994904f54706db883f61127bf05ee195ecbdce90e7242886e86711b717`, matching
the checked-in migration file, applied at `2026-10-10 18:27:04.341175-04:00`.
This records the migration's shared-schema presence only; no standalone
M1.4 scheduler service, live lease-claim behavior, or end-to-end scheduler
commissioning is claimed. The
M2.3 worker recovery coordinator owns reconciliation of expired running
assignments; inspect its durable decision before resuming them.

## Revision history

- **1.0.9 — 2026-10-11:** Align the document revision with the cross-branch file revision.
- **1.0.8 — 2026-10-11:** Carry forward the live migration correction in the M3.3 branch; no scheduler commissioning claim.

- **1.0.7 — 2026-10-11:** Consolidate migration correction metadata and retain explicit non-commissioning boundary.

## Read-only claim and lease inspection

The scheduler's direct acceptance tests remain isolated PostgreSQL tests; the
shared migration's presence does not prove live claim behavior. There is no
standalone M1.4 scheduler service on Camrui. The read-only service and schema
inventory in the [consolidated operations guide](RIVERVIEW_OPERATIONS_COOKBOOK.md)
is the appropriate live inspection. Use the detailed queries below only against
an authorized disposable fixture database/schema, after confirming that its
migrations are installed. For that database, set
`PGHOST`, `PGDATABASE`, and `PGUSER` to that test target and use an existing
protected `.pgpass` file; never put a password or full credential DSN in a
command argument.

First confirm the database identity and migration inventory. Replace
`rvtest_scheduler` below with the exact unique schema name created by the
fixture. Select the disposable database through libpq environment or a
protected passfile, not by editing this query to point at shared production
state:

```bash
psql -X --set=ON_ERROR_STOP=1 -d "$PGDATABASE" -c \
  'BEGIN READ ONLY; SELECT current_database(), current_user, version(); SELECT version, checksum, applied_at FROM rvtest_scheduler.schema_migrations ORDER BY applied_at, version; COMMIT;'
```

Use the exact schema name returned by the fixture/test evidence. It must be a
known disposable `rvtest_*` schema before querying it. If the `schema_migrations`
relation is absent, or M1.4's `0001_assignment_leases` row is missing, stop and
use the fixture setup; do not create relations manually. A migration checksum
different from the checked-in SQL is integrity drift and must be escalated.

Use that same replaced schema identifier to inspect queue eligibility, lease
fencing, and causal progress without selecting
assignment objectives, event payloads, credential hashes, or artifact contents:

```bash
psql -X --set=ON_ERROR_STOP=1 -d "$PGDATABASE" -c \
  'BEGIN READ ONLY; SELECT a.id, a.state, a.workflow_id, a.workflow_step, a.updated_at, l.worker_id, l.generation, l.heartbeat_at, l.expires_at, max(e.recorded_at) AS last_event_at FROM rvtest_scheduler.assignments a LEFT JOIN rvtest_scheduler.assignment_leases l ON l.assignment_id=a.id LEFT JOIN rvtest_scheduler.events e ON e.assignment_id=a.id GROUP BY a.id,l.worker_id,l.generation,l.heartbeat_at,l.expires_at ORDER BY a.updated_at,a.id; SELECT seq,event_id,assignment_id,event_type,correlation_id,causation_id,recorded_at FROM rvtest_scheduler.events ORDER BY seq DESC LIMIT 50; COMMIT;'
```

Interpret the result as follows:

| Observation | Meaning | Safe next action |
| --- | --- | --- |
| `ready`, no lease | Claim-eligible only if the worker scope matches; the query itself does not prove a capable worker is active. | Check the registered worker's active state and exact capability/scope through the worker adapter contract. |
| `ready`, lease expiry in the future | Not claim-eligible; another worker owns a current generation. | Check the owning attempt and heartbeat. Do not clear or overwrite the lease. |
| `ready`, expired lease | Scheduler may replace it atomically and increments the generation. | Allow the configured scheduler/worker to reclaim; an old token must fail. |
| `running`, expired lease | Requires M2.3 reconciliation, not an ordinary `ready` claim. | Inspect execution intent, attempt, result, and recovery record through the worker recovery cookbook. Preserve uncertainty and escalate an external effect without evidence. |
| No ready row and no lease | No claim is available, or work is in another lifecycle state. | Inspect lifecycle events and the workflow owner; do not force a state transition. |
| A causation reference is missing, or the event chain contains an impossible/duplicate transition | Possible ledger inconsistency, wrong database/schema, or stale caller. Global event sequence gaps alone are normal when unrelated assignments interleave. | Stop state changes; retain query output and compare event causality and migration identity. |

The scheduler's `StaleLeaseError` means the assignment/worker/generation/expiry
tuple is no longer current. Discard the old token; query the current generation
and let the authorized worker claim again. Never retry a state write using a
stale token, manually update `assignment_leases`, advance event sequence/cursor,
delete an event, or set an assignment to `ready` to make it claimable.

## Isolated failure and recovery verification

Run only against the disposable test database configured by
`RIVERVIEW_TEST_PG_DSN`; the test owns its unique schema and tears it down:

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<disposable PostgreSQL test DSN>' \
  python3 -m unittest tests.test_assignment_scheduler -v
```

Expected checks include independent concurrent claims, an active lease not
blocking a separate eligible assignment, lease expiration/generation advance,
stale heartbeat/start rejection, and atomic causal transition. These are
isolated integration results, not evidence that the scheduler or a worker is
deployed. Confirm the fixture removed its own schema afterward; if the process
was interrupted, identify the exact test-owned schema and owner before any
cleanup. Never use a wildcard `DROP`.

Escalate rather than repair in place if the target identity is not the
disposable test database, migration history disagrees with source, lease
generation moves backward, an old token can commit, a `running` external effect
has unknown outcome, or cleanup ownership is unclear.
