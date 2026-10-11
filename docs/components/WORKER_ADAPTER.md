# Riverview~ worker adapter contract

**Document Revision:** 1.0.6
**Component:** WORKER-ADAPTER
**Milestone:** M2.1–M2.3
**Status:** M2.3 IN PROGRESS — isolated engineering; no service deployment
**Implementation:** `src/riverview_core/worker_adapter/adapter.py`

## Scope and trust boundaries

The first adapter slice registers a worker identity, capability list, and exact
assignment authority scope. Registration creates a random high-entropy bearer
credential, returns it once, and stores only its SHA-256 digest. Execution
compares credentials in constant time, checks the registered capability and
requires worker scope to equal the assignment's `authority_ref`. Registration
itself is a trusted control-plane operation; this library does not authenticate
its registrar or validate the authority grant externally.

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
startup and no M2.1 migration has been applied to shared `riverview_dev`. Secret
provisioning for a deployed worker and external worker transport/authentication
remain future operational integration work.

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

### Commit-pinned repository knowledge provider

`RepositoryKnowledgeProvider` is a read-only, real-source implementation for a
small exact allowlist. It currently supports the worker adapter contract and
`deterministic.sha256.v1`. It reads fixed documentation and implementation files
from a clean Git checkout whose full `HEAD` equals the configured commit, or
from an immutable package whose `SOURCE_COMMIT` and `PACKAGE_SHA256SUMS` verify
the same content. The result includes the source paths, exact commit, aggregate
SHA-256, and the retrieved contract text. User-supplied paths and arbitrary
actions are not accepted.

This provider's `VERIFIED` status proves bounded source retrieval only; the
worker still requires its independent authority and outcome-verification
boundaries. Unknown references/actions return `NO_MATCH`, a contract/action
mismatch returns `CONTRADICTORY`, dirty or mismatched source returns
`UNVERIFIED`, oversized content returns `INCOMPLETE`, and read/metadata errors
return `UNAVAILABLE`. `record_learning` is explicitly unavailable because this
read-only provider has no learning store; the worker persists that result in
the existing observation ledger. The provider is tested in isolation and in an
actual disposable-PostgreSQL worker/verifier cycle but is not configured in a
Camrui service. It is not the complete institutional knowledge/learning
provider required for project completion.

See the [provider contract](REPOSITORY_KNOWLEDGE_PROVIDER.md),
[workflow graph](REPOSITORY_KNOWLEDGE_FLOW.md), and
[troubleshooting cookbook](REPOSITORY_KNOWLEDGE_COOKBOOK.md).

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
