# Riverview~ worker adapter contract

**Document Revision:** 1.0.8
**Component:** WORKER-ADAPTER
**Milestone:** M2.1–M2.3
**Status:** M4.3 local-inference code and isolated contract verification in progress; Camrui worker service remains uncommissioned
**Implementation:** `src/riverview_core/worker_adapter/adapter.py`
**Changed:** 2026-10-11 UTC | RV-M4.1-LIVE-EXACT-GRANT | Record deployed database function ACL while retaining undeployed worker service status

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
error is `GrantCheckUnavailable` and denies. Isolated database-boundary tests
confirm the runtime can execute this function but cannot read authority tables,
while the manager cannot call the function. The Camrui migration and
function-only ACL are now live and independently verified; the worker adapter
has not been deployed into a service, so no live-worker execution claim is made.

The default executable task is `deterministic.sha256.v1`: hash caller-provided
UTF-8 text and return its digest and byte count. The M4.3 `local.inference.v1`
capability is an opt-in loopback model call with separate exact `assignment.execute`
authority; its bounded model output is persisted as a JSON artifact. Other
capabilities still require an explicit implementation and grant mapping. No
shell, arbitrary subprocess, or remote inference endpoint is available through
this adapter. Deterministic input text and local inference prompts are retained
only by digest; the model's result artifact is persisted.

Each attempt records assignment, worker, fencing generation, capability,
idempotency key, input digest, status and timestamps. Results are separate
durable records with result digests. A repeated key returns the prior result only
when assignment, worker, generation, capability and input digest match; collision
is rejected. An unfinished attempt remains visible to `incomplete_attempts()`
for worker-loss detection. Result commit rechecks the active lease and records a
lost-lease failure rather than accepting a stale worker result.

The M2.1 migration is separate and explicit. No schema DDL is applied at adapter
startup. The adapter accepts a separate `authority_schema`; production must use
`riverview_authority`. Migration 0002 and its exact function ACL are applied to
the shared authority schema. No worker service is commissioned.
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
learning payloads are not stored in that observation record. Migrations are
applied explicitly to a selected schema; inspect the live migration ledger and
the M4.3 record before asserting environment state. Learning capture records
outcomes but does not auto-promote knowledge.
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
SQL separation. A protected live backup/restore, migration 0002, function ACL,
and rollback-only runtime-role allow/deny check now pass; see
`evidence/checkouts/M4.1-DB-BOUNDARY/20261011T090700Z-live-exact-grant/`. No
worker service consumes this contract. M3.3 and M4.1 remain IN PROGRESS pending
`assignment.create` authorization, deployment and commissioning of the worker
adapter with an approved real worker, plus the real knowledge provider for M3.3.


## M4.3 local inference capability

`local.inference.v1` is a separately registered execution capability. It is
allowed only through a worker identity with `assignment.execute` granted for the
assignment's exact authority reference; capability registration alone is not
authority. `ContinuousWorker` passes the selected capability to claim,
preflight, start, execution intent and result commit. The local adapter sends
only grounded content to an explicitly configured literal loopback HTTP `/v1`
endpoint. DNS names, non-loopback hosts, user-info, query strings and remote
plain-HTTP endpoints are rejected. Prompt and response sizes, token count and
call time are bounded; only a complete `finish_reason=stop` response is accepted.
Credential-shaped password, bearer, API-key, access-token, client-secret and
private-key material is rejected before the request leaves the worker process.

The actual model output is stored as a JSON result artifact, bounded to 65,536
UTF-8 bytes, with a canonical SHA-256 digest. The input/prompt is retained only
as a digest. A different registered verifier evaluates the persisted result
before the assignment can complete. Local generation has no expected external
effect and can be retried after the worker adapter's fenced recovery; endpoint
failure, timeout, invalid response, invalid knowledge or revoked authority
never produces a successful artifact. Existing deterministic SHA-256 behavior
remains the default.

`LocalInferenceAction` uses only Python standard-library HTTP facilities. It is
compatible with a llama.cpp OpenAI-compatible local server, but does not start,
install, or supervise that server. A development model/runtime can be pinned
and launched separately; no model weights belong in the repository or package.
See the [local-inference cookbook](WORKER_ADAPTER_COOKBOOK.md) for the tested
launch, health, shutdown, and result-diagnosis procedure. M4.3 is not operationally
commissioned until the actual model result is persisted and independently
verified through the durable worker cycle; this paragraph defines the contract
and does not claim Grace or an always-on inference service.
