# Riverview~ worker adapter contract

**Document Revision:** 1.0.22
**Component:** WORKER-ADAPTER
**Milestone:** M2.1–M2.3
**Status:** M3.3 scoped technical acceptance criteria PASS and ready for Steward review; no simultaneous executor-process throughput claim. Formal acceptance and full Component DoD remain open; M4.3 local-inference execution remains isolated.
**Implementation:** `src/riverview_core/worker_adapter/adapter.py`
**Changed:** 2026-10-11 UTC | RV-M4.1-LIVE-EXACT-GRANT | Record deployed database function ACL while retaining undeployed worker service status
**Changed:** 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Record verified isolated model execution and persistent-service limitation
**Changed:** 2026-10-11 UTC | RV-M3.3-ASSIGNMENT-INTAKE | Record isolated grant-gated assignment creation and undeployed service boundary
**Changed:** 2026-10-11 UTC | RV-M3.3-REPOSITORY-KNOWLEDGE | Specify pinned read-only repository provider and its fail-closed status
**Changed:** 2026-10-11 UTC | RV-M3.3-WORKER-SERVICE | Specify executor/verifier systemd runner contracts and commissioning state
**Changed:** 2026-10-16 UTC | RV-WORKER-HEALTH-REPORTING-001 | Clarify idle polling and distinguish assignment-lease heartbeat from process liveness.
**Changed:** 2026-10-11 UTC | RV-M3.3-LIVE-COMMISSIONING | Record live grant-bound repository test executor, verifier, artifact and recovery evidence
**Changed:** 2026-10-11 UTC | RV-M3.3-WAITING-ISOLATION | Record live unavailable-knowledge isolation while eligible work continues
**Changed:** 2026-10-11 UTC | RV-M3.3-WAITING-ISOLATION-STATUS | Align current scoped technical status and distinguish process concurrency claims
**Changed:** 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Document bounded artifact capability as deterministic infrastructure test adapter only
**Changed:** 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-001 | Specify separately registered Codex multi-file patch capability and exact execution grant
**Changed:** 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001-GUARD-DOCS | Specify same-assignment resume after fresh grounding/preflight and remaining-retry checks
**Changed:** 2026-10-16 UTC | RV-GRACE-SCOPE-LEASE-RECONCILE-001 | Authenticate recovery identity/scope, heartbeat long actions, and preserve validated late Codex artifacts for independent verification
**Changed:** 2026-10-20 UTC | RV-GRACE-S3-RECOVERY-DISPOSITION-001 | Specify the exact-grant, append-only, single-use disposition for one exhausted no-artifact assignment

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
function-only ACL are now live and independently verified. M3.3 also commissions
the repository-test executor and verifier services for one exact bounded work
scope; see the live commissioning record below. This does not commission the
M4.3 local-inference worker.

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
the shared authority schema. The scoped M3.3 test-work executor and verifier use
separately granted identities and systemd credential delivery; this does not
commission arbitrary capability execution or alter the migration/startup rule.

## Continuous worker and knowledge boundary

`ContinuousWorker.run_once()` consumes at most one authenticated, scope-matched
ready assignment per poll. Multiple workers claim independently through M1.4
`FOR UPDATE SKIP LOCKED` leases. A waiting or failed assignment is recorded as
`blocked` with workflow step `WAITING_FOR_EVIDENCE` or a failure step; later
claims continue. `run_forever()` is an in-process polling loop and accepts an
explicit Steward shutdown callback. Unexpected worker/process loss leaves
durable leases/attempts for expiry and reconciliation; the worker loop does not
claim to make a process immortal.

When fresh grounding becomes `VERIFIED` after a Codex assignment was blocked at
`WAITING_FOR_EVIDENCE`, the persistent worker may requeue that same assignment
through the evidence-recovery path. Candidate discovery authenticates the
registered worker and exact `assignment.execute` grant in the assignment's
scope. Recovery then requires the original `WORK_ORDER_CREATED` objective and
verified objective evidence, an expired or absent lease, a current non-verified
knowledge observation, fresh `VERIFIED` grounding and action preflight, a
remaining retry budget, no worker attempt/result/verifier/artifact, and only
typed Codex intents already recorded as `retry_safe`. It records both refreshed
provenance results and a causal transition to the canonical ready node; the
normal claim repeats the exact grant check before execution. An active lease,
unknown intent, existing attempt/output, stale objective, non-verified source,
or scope mismatch leaves the assignment blocked. This resumes the same durable
objective; it does not create an assignment or bypass the retry/authority
boundaries.

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

### Single-use disposition for an exhausted no-artifact assignment

`PostgresRecoveryCoordinator.authorize_one_no_artifact_retry` is a narrowly
scoped, authenticated recovery operation for one existing assignment. It does
not change `RIVERVIEW_GRACE_MAX_WORKER_RECOVERIES`, edit existing recovery
rows, alter a proposal, or create an assignment. The caller must present the
existing `service.recover` grant in `service-recovery.v1`, the active worker's
exact `assignment.execute` grant for the assignment scope, an auditable issue
authorization reference, and a unique idempotency key. The operation is not
invoked automatically by polling.

Before any state change, it locks the assignment and linked objective step and
requires the same objective/step/assignment link, one original dispatch event,
verified objective grounding and dependencies, an expired lease, exactly the
configured number of prior `retry_safe` decisions, and only matching failed
Codex no-artifact intents. It rejects any attempt, result, verifier record, or
adapter artifact. The caller supplies the SHA-256 of the canonical JSON
`artifact_requirements`; the code compares it with both the persisted proposal
step and original dispatch event. This binds the disposition to the assignment's
unchanged artifact contract without hard-coding file names or weakening artifact
validation.

One transaction appends `worker_recovery_dispositions`, appends a causal
assignment event, and returns the same assignment from `blocked` to `ready`.
The unique assignment constraint makes the disposition single-use. Its table
rejects update/delete; the three previous recovery decisions remain intact.
An identical authorized call returns the original receipt, including after
normal worker claim. Any changed idempotency key or request is rejected. The
ordinary worker claim then creates only the next lease generation and repeats
the registered worker, capability, scope, and exact-grant checks. A later failure
is subject to the unchanged global retry ceiling; this exception authorizes no
second disposition or automatic requeue.

Operationally, obtain the artifact-contract digest and metadata from the
read-only persisted assignment/proposal record, compare it with the dispatch
event, and inspect the exact assignment/recovery state before requesting a
separately authorized invocation. Keep artifact contents out of approval
records. If any predicate differs, leave the assignment blocked and preserve
its history. See the matching diagnostic and stop conditions in the worker
adapter cookbook.

`RepositoryKnowledgeProvider` is the first real repository-backed provider. It
is read-only and retrieves only a small allowlist of committed worker contract
files. Construction requires an exact full Git commit ID; `VERIFIED` requires
that `HEAD` equal this configured pin, each allowed file be clean, and all
source bytes fit the configured per-file and aggregate bounds. For an immutable
release package, it instead requires `SOURCE_COMMIT` and
`PACKAGE_SHA256SUMS` to match the configured pin and source bytes. The result
contains stable `repo://` references, the pinned revision, an aggregate
SHA-256, and `retrieval_complete=True`. Unknown contract/action references
return `NO_MATCH`; wrong pins or bytes return non-authorizing statuses; Git or
read failures return `UNAVAILABLE`. Learning writes are explicitly unavailable.
The provider never executes retrieved text and never supplies authority.

The supported `repo://riverview/worker-adapter-contract.v1` contract grounds
`deterministic.sha256.v1` only. It does not assert that local inference,
arbitrary commands, or any external interface is verified. A deployment must
pin its exact package revision; absence or mismatch leaves the assignment in
`WAITING_FOR_EVIDENCE`. See
[`Repository Knowledge Provider`](REPOSITORY_KNOWLEDGE_PROVIDER.md).

### Supervised M3.3 executor and verifier services

`scripts/run_worker_service.py` runs a continuous, grant-bound executor with the
pinned repository provider and existing scheduler. At startup it accepts only
the registered unit's systemd credentials, copies the protected PostgreSQL
passfile into an exclusive service-private runtime path, and either registers
the exact worker under its `worker.register` grant or checks that the active
identity, credential digest, capabilities and scope match. Any mismatch fails
startup. The commissioned capability is `engineering.repository-check.v1`,
which runs the bounded `tests.test_repository_knowledge` suite and writes a
0600 JSON report beneath `/var/lib/riverview-m33-worker/artifacts/`. It does not
run arbitrary shell commands, user-supplied code, network actions, or model
inference.

`scripts/run_verifier_service.py` runs under another systemd unit, bearer,
authorization principal, and exact `assignment.verify` grant. It polls durable
successful attempts and uses `RepositoryContractTestVerifier` to validate the
artifact metadata and independently rerun the registered test suite. Executor
and verifier are separate logical identities and credentials, although both
systemd processes run as the restricted Unix account `riverview`. The existing
leases, database locks and idempotency keys preserve safe transitions across
restart. The live units use PID 1 credential delivery, restart on unexpected
failure, and do not apply migrations. Their source definitions are
`deploy/systemd/riverview-m33-worker.service`,
`deploy/systemd/riverview-m33-verifier.service`, and
`deploy/systemd/riverview-assignment-intake.service`.

Camrui commissioning on 2026-10-11 deployed immutable source
`47a79adafe1524b3e819148b70c02a1857f50dbf` (package SHA-256
`ce2179ecc4e840dceb8316eea8a6c4117a4ef6cdcca6314d76ad19da4b617d41`). The
loopback intake, executor, verifier, event processor, CME monitor, notification
dispatcher, and dashboard were active at the captured post-check. One authorized
assignment and two recovery assignments completed with ACCEPTED independent
verification. A deliberate executor SIGKILL restarted without duplicating the
completed result; queued assignments and stall/resolution notices survived a
separate bounded outage and were processed after recovery. A separate live run returned `NO_MATCH` for an unregistered contract, persisted
that assignment at `WAITING_FOR_EVIDENCE`, and then completed and independently
verified a second eligible assignment while the first remained waiting. This
proves independent assignment progress and fail-closed knowledge behavior; it
does not claim simultaneous execution by multiple executor processes. Current
exact-scope grants are time-limited; inspect live authority records before
operating.
Evidence and outstanding M3.3 acceptance limits are in
`evidence/checkouts/M3.3-LIVE-E2E/20261011T1245Z-47a79ad/`,
`evidence/checkouts/M3.3-WAITING-ISOLATION/20261011T1310Z-47a79ad/`, and
`docs/development/M3.3-001_REVISION_RECORD.md`.

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
`PostgresRecoveryCoordinator.reconcile_expired(scope_ref, worker_id)` only after the current worker credential and capability have been authenticated. It scans expired leases owned by that worker inside its exact authority scope; it cannot sweep another worker's assignments. A lease heartbeat keeps bounded long-running actions leased through their result commit. Unknown outcomes remain held. A late Codex artifact is attached to the same durable attempt only when the original assignment, objective, expired lease, `ProcessInterrupted` intent, current exact grant, verified grounding, private assignment-bound artifact, and absence of prior attempts/results/verifications all match. Its original `outcome_unknown` recovery record remains unchanged, and the state advances only to `awaiting_verification`; the independent verifier remains mandatory. Any failed invariant leaves the assignment awaiting Steward review without replay. See the [M2.3 cookbook](WORKER_ADAPTER_COOKBOOK.md) and [RV-M2.3-001 record](../development/M2.3-001_REVISION_RECORD.md).

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
worker service consumes this contract. The isolated `AuthorizedAssignmentIntake`
checks exact `assignment.create`, derives actor identity from the authority
function, and holds that grant lock across assignment/event persistence. Its
isolated PostgreSQL tests pass; this does not restrict raw `PostgresLedger.create`
or direct SQL. No governed route or worker service uses it yet. M3.3 remains
blocked on route/service integration, commissioning of an approved real worker,
and the real knowledge provider.


## Grace bounded artifact capability

The additional engineering.bounded-artifact.v1 mapping is an explicit
capability/action grant mapping, not arbitrary code execution. The deterministic
BoundedLocalCodingWorker is used for model-independent infrastructure tests:
it accepts a persisted, verified proposal through the CME lease, writes one
assignment-derived JSON artifact to an owner-controlled mode-0700 directory,
and invokes no shell, command, network, or caller-selected path. The
BoundedArtifactVerifier lives in a separate module and reopens the file before
persisted completion. Exact assignment.execute and assignment.verify grants
remain required. This adapter produces a bounded work-product record; it is not
a general coding executor and does not establish a commissioned Grace worker
service or M4.4 operational acceptance.

`engineering.codex-cli-source-change.v1` is a separate exact capability. Its
typed request pins the repository revision, exact authorized path list,
acceptance criteria, fixed test targets, timeout and objective/assignment IDs.
The worker adapter recognizes it only when that capability is explicitly
registered and the same-scope `assignment.execute` grant is active. Its Codex
adapter produces an inventoried, digest-checked patch from a disposable clone;
an independent verifier replays that patch in a second clean clone and reruns
the fixed tests. It never applies patches to the configured checkout or a
production release. The persistent Grace service does not register or dispatch
this capability automatically in this increment: no per-assignment authorized
path-scope field exists in its current objective/work-order interface, so it
remains a tested capability boundary rather than a live dispatch option.

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
The isolated M4.3 acceptance task passed on Camrui: two concurrent local model
calls produced durable JSON artifacts, a separate verifier accepted each
artifact, and the assignments reached `completed`. The test used fixed,
checksum-pinned instruction-following prompts and a fixture knowledge provider;
it does not demonstrate general model reasoning or institutional retrieval.
The worker service remains uncommissioned as a persistent service, and this
result does not claim M3.3 acceptance, Grace, or full Component DoD. See
`docs/development/M4.3-001_REVISION_RECORD.md` and the linked checkout evidence.
