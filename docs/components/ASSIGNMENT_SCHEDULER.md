# Riverview~ assignment scheduler contract

**Document Revision:** 1.0.2
**Component:** ASSIGNMENT-SCHEDULER
**Milestone:** M1.4
**Status:** Isolated technical criteria verified; no operational commissioning; full component DoD OPEN
**Implementation:** `src/riverview_core/assignment_scheduler/scheduler.py`

## Purpose and boundary

The scheduler provides deterministic fair claims over ready assignments using
PostgreSQL row locking, expiring worker leases, and monotonically increasing
fencing generations. It is a library, not an autonomous worker service. The
M1.4 migration is separate from the M1.2 and M1.3 migrations and is never
applied automatically by the scheduler. No shared Camrui schema has received
M1.4 DDL.

Claims select the oldest ready assignment without a currently active lease,
ordered by `updated_at,id`, using `FOR UPDATE SKIP LOCKED`. A held lease on one
assignment therefore does not prevent another worker from claiming a different
ready assignment. The database clock controls expiry. Reclaim increments the
assignment's generation. Heartbeats and `start_assignment` require exact worker
identity, generation, and an unexpired lease. Starting the assignment and
appending its causally linked transition event occur in one transaction.

A stale lease token cannot start the assignment after a newer generation has
been issued. The current slice does not implement worker execution, automatic
recovery of assignments already in `running`, lease supervision service,
capability registration, or independent outcome verification. Those remain
separate roadmap requirements. The existing M1.3 processor remains unchanged.

## Explicit migration and API

Apply `src/riverview_core/assignment_scheduler/migrations/0001_assignment_leases.sql`
only to an isolated test schema during this engineering phase. The SQL checksum
is recorded in `schema_migrations`. Runtime startup does not apply DDL.

`PostgresAssignmentScheduler.claim_next(worker_id, lease_seconds=30)` returns a
lease row or `None`. `heartbeat(assignment_id, worker_id, generation, ...)`
extends only the exact current active token. `transition_with_lease(...)` fences
every scheduler-authorized assignment transition; `start_assignment(...)` is its
`ready` to `running` convenience operation. The assignment row lock serializes
heartbeat, reclaim, and state mutation under one lock order. `StaleLeaseError`
represents a lost, expired, or superseded token. Callers must treat the returned
generation as an opaque fencing value and include it in all authorized worker
writes.

The [workflow graph](ASSIGNMENT_SCHEDULER_FLOW.md) describes selection,
expiry/reclaim, fencing and the M1.3 readiness prerequisite. See the
[operational cookbook](ASSIGNMENT_SCHEDULER_COOKBOOK.md) and
[RV-M1.4-001 record](../development/M1.4-001_REVISION_RECORD.md).
