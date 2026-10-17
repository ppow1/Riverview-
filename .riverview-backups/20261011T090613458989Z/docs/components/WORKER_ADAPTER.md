# Riverview~ worker adapter contract

**Document Revision:** 1.0.6
**Component:** WORKER-ADAPTER
**Milestone:** M2.1–M2.3
**Status:** Isolated M4.1 exact-grant integration added; Camrui worker/service deployment remains unverified
**Implementation:** `src/riverview_core/worker_adapter/adapter.py`

## Scope and trust boundaries

The adapter registers a worker identity, capability list, and exact assignment
authority scope. Registration now requires a Steward-issued identity bearer
whose exact `worker.register` grant matches that scope. The same bearer is
stored only as a SHA-256 digest and checked against an active exact
`assignment.execute` or `assignment.verify` grant before each corresponding
action. The worker's scope must also equal the assignment's `authority_ref`.
The adapter does not generate an independently authorized worker credential or
accept a free-form scope claim as authority.

`ExactGrantAuthorizer` calls the protected SQL function on the caller's active
transaction cursor. The function returns only principal/grant IDs, locks the
credential/principal/grant rows through transaction completion, and never
reveals credential digests. A missing grant denies; a missing function or DB
error is `GrantCheckUnavailable` and denies. The separate database-boundary
tests confirm the runtime can execute this function but cannot read authority
tables, while the manager cannot call the function. The live Camrui migration
and function ACL have not yet been deployed, so this is isolated application
integration, not a live-worker authorization claim.

The only executable task is `deterministic.sha256.v1`: hash caller-provided UTF-8
text and return its digest and byte count. No shell, subprocess, network,
filesystem, GPU, or arbitrary code execution occurs. The input content is not
stored; only its digest and the deterministic result are persisted.

Each attempt records assignment, worker, fencing generation, capability,
idempotency key, input digest, status and timestamps. Results are separate
durable records with result digests. A repeated key returns the prior result only
when assignment, worker, generation, capability and input digest match; collision
is rejected. An unfinished attempt remains visible to `incomplete_attempts()`
for worker-loss detection. Result commit rechecks the active lease and records a
lost-lease failure rather than accepting a stale worker result.

The M2.1 migration is separate and explicit. No schema DDL is applied at adapter
startup. The adapter accepts a separate `authority_schema`; production must use
`riverview_authority`. Migration 0002 and its exact function ACL have not yet
been applied to the shared authority schema. No worker service is commissioned.
Steward-issued credential storage and worker process credential delivery remain
explicit commissioning work.

## Continuous worker and knowledge boundary

`ContinuousWorker.run_once()` consumes at most one authenticated, scope-matched
ready assignment per poll. Multiple workers claim independently through M1.4
`FOR UPDATE SKIP LOCKED` leases. A waiting or failed assignment is recorded as
`blocked` with workflow step `WAITING_FOR_EVIDENCE` or a failure step; later
claims continue. `run_forever()` is an in-process polling loop and accepts an
explicit Steward shutdown callback. Unexpected worker/process loss leaves
durable leases/attempts for expiry and reconciliation; the worker loop does not
claim to make a process immortal.

The stable, provider-neutral contract lives in
[`knowledge_provider_v1`](../../src/riverview_core/worker_adapter/knowledge_provider_v1/README.md).
Its operations are `ground_assignment(assignment)`,
`preflight_action(assignment, action)`,
`reground_assignment(assignment, trigger)`, and
`record_learning(assignment, outcome)`. Grounding occurs before work, preflight
before action, and regrounding immediately before action. Only `VERIFIED` with
complete retrieval and at least one source reference permits progress. Missing
provider/exception/timeout becomes `UNAVAILABLE`; unknown result objects become
`UNVERIFIED`. Other non-verified statuses also put only that assignment in
`WAITING_FOR_EVIDENCE`. There is no guessed-contract fallback.

Lookup status, operation, action, source references, source revision/hash,
retrieval completeness and timestamp are persisted by the explicit M2.1 worker
migration `0002_knowledge_observations.sql`. Provider values and arbitrary
learning payloads are not stored in that observation record. Migration 0002 is
still applied only to isolated test schemas; no live/shared deployment is
claimed. Learning capture records outcomes but does not auto-promote knowledge.
The provider interface is injectable and the scheduler does not depend on its
implementation.

See the [workflow graph](WORKER_ADAPTER_FLOW.md),
[operational cookbook](WORKER_ADAPTER_COOKBOOK.md), and
[RV-M2.1-001 record](../development/M2.1-001_REVISION_RECORD.md).

## Independent result verification (M2.2)

The worker leaves successful artifacts in `awaiting_verification`. A separately
registered verifier with `assignment.verify.v1`, matching authority scope, and a
different worker identity evaluates the stored attempt and result. The initial
`DeterministicSha256Verifier` independently checks the recorded input digest,
result shape, and canonical result digest. It records criterion-level decisions,
the attempt, verifier identity and revision, and evidence references in
`verification_records`.

Accepted evidence permits the transition to `completed`; rejected evidence
routes the assignment to `rework_required`; inconclusive evidence blocks it for
reassessment. A database trigger rejects direct completion in schemas with M2.2
migration `0003_independent_verification.sql` unless an ACCEPTED record exists.
Verification requests are idempotent and can resume the state transition after
a process interruption. This verifier covers the deterministic M2.1 artifact
contract only; it is not a general code review or software acceptance service.
Migration 0003 remains isolated to disposable test schemas and is not deployed.

See [the M2.2 verification workflow](OUTCOME_VERIFIER_FLOW.md) and
[RV-M2.2-001 engineering record](../development/M2.2-001_REVISION_RECORD.md).

## Failure and restart recovery (M2.3)

The continuous worker persists an execution intent before invoking an action.
The built-in deterministic action is `retry_safe`; a caller-supplied action
defaults to `external_uncertain` unless its contract explicitly classifies it
otherwise. On expired lease, a committed result advances to
`awaiting_verification` without rerunning; a `retry_safe` incomplete intent is
fenced and requeued; and an unknown external outcome moves to
`awaiting_steward`. The recovery record and assignment events commit atomically.
Legacy `running` assignments without an intent are treated as uncertain because
older code did not persist the action boundary.

Migration `0004_failure_recovery.sql` adds durable execution-intent and recovery
tables. Apply it explicitly to a selected schema; the adapter never applies DDL
at startup. `ContinuousWorker.run_once()` invokes
`PostgresRecoveryCoordinator.reconcile_expired()` before each new claim. It scans
only expired `running` assignments, preserves persisted results for independent
verification, and does not inspect external systems or claim that an uncertain
action did not take effect. Uncertain work requires authoritative reconciliation
before it can be resumed. See the [M2.3 cookbook](WORKER_ADAPTER_COOKBOOK.md)
and [RV-M2.3-001 record](../development/M2.3-001_REVISION_RECORD.md).

## M4.1 exact-grant integration (isolated)

`register_worker(..., credential=...)` requires an active credential with the
exact `worker.register` scope grant. `claim_next`, `start_assignment`, action
preflight and result commit re-check `assignment.execute`; verification
re-checks `assignment.verify`. Revocation prevents a later action even if the
worker registry row remains active. Worker-local hashes do not replace the
authority check. The function migration is
`src/riverview_core/institutional_authority/migrations/0002_exact_grant_authorization.sql`;
the boundary provisioner grants the runtime only schema `USAGE` and execution
of this function.

Isolated PostgreSQL tests passed 22/22 across boundary, worker and CME suites on
2026-10-11. They cover granted worker operations, wrong scope/action, missing
registration grant, post-registration credential revocation, and manager/runtime
SQL separation. The live schema lacks the new function and no production worker
uses this contract yet. M3.3 and M4.1 remain IN PROGRESS until live migration,
protected backup/restore, ACL checks and real approved worker commissioning pass.
