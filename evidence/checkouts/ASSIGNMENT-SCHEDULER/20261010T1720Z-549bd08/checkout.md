# Riverview~ M1.4 isolated engineering verification

**Document Revision:** 1.0.0
**Task:** RV-M1.4-001
**Component:** ASSIGNMENT-SCHEDULER
**Milestone:** M1.4 — independent assignment scheduling
**Environment:** Camrui, Ubuntu 24.04.3, PostgreSQL 16.15 disposable UTF-8 cluster
**Source commit:** `549bd08b9b1800981c6c4c006dbe59d8fed0a799`
**Status:** Roadmap technical criteria verified in isolated PostgreSQL; full component DoD open

## Functionality

The scheduler claims the oldest ready assignment without an active lease using
`FOR UPDATE SKIP LOCKED`. Worker lease, expiry and generation are persistent.
Reclaim increments the fencing generation. Heartbeats serialize with claim and
reclaim through an assignment row lock. Scheduler-authorized state transitions
atomically check worker, generation and database-clock expiry and append their
events in the same transaction. Start replay is idempotent.

## Verification

The complete suite passed **77 tests, zero failures, zero errors, zero skips**.
M1.4's three PostgreSQL integration tests demonstrated:

- An active stalled lease on the oldest assignment did not prevent a second
  assignment being claimed and started; the first remained independently ready.
- Concurrent workers claimed distinct ready assignments.
- Expiry/reclaim incremented generation; the stale worker's start, heartbeat,
  and later transition were rejected; the current generation started exactly
  once and duplicate start replay did not create a second event.

The full test log is `unittest.log`. After testing, `rvtest_*` schema count was
zero and the disposable cluster was stopped. DDL was applied only in those
disposable schemas; shared `riverview_dev` and the M1.1/M1.2/M1.3 services were
not modified.

Graph validation passed with 6 workflows and 94 nodes. The controlled-revision
audit against the repository baseline passed with no issues. GitHub checks for
source commit `549bd08` passed (push run 38070780092 and pull-request run
38070783426). The current documentation/evidence commit will receive its own CI
runs before PR merge.

M1.4 is verified against its roadmap technical criteria in isolated engineering.
No M1.4 runtime deployment or operational commissioning is claimed. The full
component DoD remains open for later operational visualization, worker runtime,
and system-level obligations.
