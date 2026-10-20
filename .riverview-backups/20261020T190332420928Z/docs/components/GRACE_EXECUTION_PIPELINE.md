<!--
Riverview~ Controlled Document
File: docs/components/GRACE_EXECUTION_PIPELINE.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.1.26
Changed: 2026-10-20 UTC | RV-GRACE-MULTISTEP-PROVENANCE-RECOVERY-001 | Specify durable per-step assignment provenance for concurrent Codex execution and same-assignment no-artifact recovery.
Changed: 2026-10-20 UTC | RV-GRACE-ACCEPTED-STEP-REWORK-001 | Make independent verifier acceptance advance persisted dependent steps and specify bounded rejection correction/escalation.
Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Preserve production behavior while integrating the authenticated bounded re-review caller.
Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Clarify globally unique review idempotency keys and due-generation selection before batching.
Changed: 2026-10-19 UTC | RV-C4-GRACE-RESULT-RETURN-ARTIFACT-STATUS | Document the sanitized optional artifact availability field in the bound 80B result-review contract.
Changed: 2026-10-19 UTC | RV-C1-GRACE-REJECTION-ROLE-CLARIFICATION | Assign artifact integrity, provenance, authorization and structure to the independent verifier; pass the actual digest-checked artifact and immutable rejection evidence to Grace for substantive acceptance/rework decisions.
Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Specify latest-rejection review, lease-fenced same-assignment retry, verifier selection and conversation progress projection.
Changed: 2026-10-19 UTC | RV-GRACE-REREVIEW-OPERATOR-CALLER-001 | Specify the authenticated audited dashboard entry point for evidence revision requests.
Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-GENERATIONS-001 | Add bounded durable re-review generations after additional-evidence decisions
Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Define immutable source-target provenance and capability-fenced concurrent owner-session execution.
Purpose: Specify the deterministic, governed objective-to-work-order infrastructure slice
Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Document corrected acceptance interpretation and append-only same-attempt verifier recovery
Changed: 2026-10-20 UTC | RV-GRACE-ACCEPTED-STEP-REWORK-001 | Clarify verifier acceptance and persisted dependencies as the advancement gate; retain model review as nonblocking summary.
Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-REASONING-BUDGET-001 | Set bounded owner-session plan generation to 768 tokens after 256-token live 80B truncation
Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-OBJECTIVE-CONTEXT | Pass original bounded objective context to each step without widening exact file scope
Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-STEP-CONTINUATION | Resolve a model-selected existing dependent step to its durable canonical proposal before dispatch checks
Changed: 2026-10-16 UTC | RV-GRACE-REVIEW-OBJECTIVE-PROGRESS | Give Grace's 80B review authoritative persisted objective and per-step completion state
Changed: 2026-10-17 UTC | RV-GRACE-ACCEPTANCE-CRITERIA-001 | Resolve verifier criteria from the immutable dispatched objective step, not only worker result echo
Authority: Engineering contract; not evidence of production Grace commissioning
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Link persistent reconciliation and authenticated dashboard handoff
Changed: 2026-10-13 UTC | RV-GRACE-CONVERSATION-WORKORDER-CONTRACT | Document explicit message-origin objective intake and its exact Steward grant
Changed: 2026-10-13 UTC | RV-CODEX-CLI-ADAPTER-001 | Record the source-only bounded Codex artifact adapter and commissioning gates
Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Wire a registered Codex capability through leased execution and independent Markdown verification
Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH-CREDENTIAL | Bind the Codex API key to a protected systemd credential and exact Engineering scope
Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Replace API-key execution with a bounded one-objective ChatGPT-session mode
Changed: 2026-10-13 UTC | RV-SUPERVISED-CODEX-DISPATCH-001 | Pin supervised reasoning, dispatch, claim, verification, and completion to one objective
Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Route proposals through the bound 80B and return independently verified results to source chat
Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RETRY-003 | Reuse immutable acceptance criteria on authorized same-origin retries
Changed: 2026-10-15 UTC | RV-GRACE-GROUNDING-BOUNDED-001 | Rank complete task-relevant passages within the evidence envelope
Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-REGROUND-001 | Allow a verified same-origin retry to advance WAITING_FOR_EVIDENCE atomically
Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-CONTEXT-001 | Include the exact resident reasoning contract in durable assignment context
Changed: 2026-10-15 UTC | RV-GRACE-PROPOSAL-TIMEOUT-001 | Bound 80B proposal inference to a shared 60-second request deadline
Changed: 2026-10-15 UTC | RV-GRACE-AUTHORIZED-SNAPSHOT-001 | Revalidate resident authority through the restricted office-state capability
Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Separate verified knowledge-source provenance from the pinned Codex checkout revision and recover confirmed no-launch failures
Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Keep immutable objective evidence provenance distinct from current grounding and recover bounded durable no-launch failures
Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Persist dependency-ordered step assignments and add an explicitly scoped source-change patch capability
Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Record typed post-verification decisions and same-objective continuation; constrain owner-session Codex state and fail closed when its Code Mode host is absent
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-SYSTEMD-NETLINK-001 | Permit AF_NETLINK for bubblewrap isolated loopback setup and test that exact namespace during preflight
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-CODE-MODE-ENABLE-001 | Explicitly enable code_mode_host when the persistent CLI adapter requires that companion
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-CODE-MODE-MDWE-001 | Keep the Code Mode filesystem and network sandbox while allowing its required executable-memory runtime in the owner service
-->
# Grace Execution Pipeline — infrastructure slice

**Status:** Implemented for deterministic, isolated integration; not a commissioned operational Grace resident.

The persistent reconciliation loop, governed dashboard routes, objective projections,
restart behavior, and the bounded-retry dispatch policy are specified in
[`GRACE_PERSISTENT_EXECUTION.md`](GRACE_PERSISTENT_EXECUTION.md). Diagnosis and recovery
steps are in [`GRACE_EXECUTION_COOKBOOK.md`](GRACE_EXECUTION_COOKBOOK.md). Neither document
claims live installation or Camrui commissioning.

## Authorized verified-result rereview request

The supported operator entry point is the authenticated dashboard route
`POST /api/v1/objectives/{objective_id}/result-rereview`. It requires the normal
dashboard bearer plus the existing `X-Riverview-Authority` credential, then
passes the exact path objective ID, completion cycle, evidence revision,
bounded evidence list, and caller idempotency key to
`request_conversation_result_rereview`. The pipeline rechecks the exact
objective-scoped `objective.submit` grant and accepted verifier completion;
the HTTP handler does not call dispatch. A successful response returns the
durable review generation, evidence digest, and whether the idempotent request
was reused. `403` means authority failed, `409` means objective/generation or
idempotency state rejected the request, `400` means bounded input is invalid,
and `503` means authority or pipeline state is unavailable. The append-only
`conversation.result_review_requested` objective event is the audit receipt;
its actor, scope, revision, digest, generation, and idempotency key support
later correlation.

**Source:** src/riverview_core/resident_execution/ and the existing assignment, scheduler, worker, and verifier modules.

## Lifecycle and authority

1. GraceExecutionPipeline.submit_objective(...) requires the exact objective.submit grant for the supplied scope. It writes the bounded human request, criteria, authenticated submitter, and objective.received event together.
2. ground_objective(objective_id) asks TaskRelevantRepositoryKnowledgeProvider for the resident contract at one pinned Git commit. The provider verifies the full allowlisted source set and selects ranked, complete paragraphs within a 7 KiB selection budget, leaving room for the provenance envelope under the 8 KiB serialized evidence limit. It records the selection policy and query-term coverage; it does not claim every lexical match was passed to the model. Paragraphs are never clipped. Missing sources or a selection with no complete passage that fits waits/fails closed.
   A same-origin retry may call grounding again while the durable objective is `WAITING_FOR_EVIDENCE`. Verified evidence atomically advances either `RECEIVED` or `WAITING_FOR_EVIDENCE` to `GROUNDED`; the state predicate prevents a second concurrent retry from overwriting an already grounded or later-stage objective. Incomplete evidence remains pending with a new revision and event.
3. record_proposal(objective_id, PlanProposal) accepts only the existing typed plan. It stores the unapproved plan and hash. This method is a persistence boundary, not a reasoning engine.
4. authorize_and_dispatch(...) requires exact assignment.create, the same scope as intake, and complete verified evidence. It uses AuthorizedAssignmentIntake; assignment + creation event + objective/work-order link are one PostgreSQL transaction. The event processor remains responsible for queued-to-ready.
   Acceptance criteria originate in authenticated objective intake, are checked against Grace's typed proposal, and are persisted with both the proposal and `grace_objective_steps` before dispatch. The `work_order.dispatched` event links the assignment to that durable step.
5. ContinuousWorker obtains a lease and rechecks the registered capability and exact authority. The existing bounded-artifact capability writes one small assignment-derived work product. The separate source-change adapter can produce a patch for explicitly allowlisted files in a pinned disposable clone; it returns patch evidence only and never applies changes to the configured checkout or production.
6. The verifier independently reopens the bounded artifact or reapplies a source patch in a separate clean clone, checks scope, digest and provenance, and reruns fixed tests. For Codex Markdown it resolves criteria from the persisted step linked to the assignment and confirms any worker echo matches that binding; missing durable criteria remain a rejection. It does not grade substantive prose. A dependent objective step becomes dispatchable after its persisted dependencies are independently accepted; the normal CME dispatch path still rechecks the exact `assignment.create` grant and existing Steward approval scope. A 80B result review may return a nonblocking summary, but cannot override verifier acceptance, hold an accepted dependent step, or complete the objective by itself. The objective becomes `COMPLETED` only after all persisted steps are verified (including existing verified rework successors).
7. For a `grace.readiness_router.v1` binding, ResidentReasoner proposals use the router's typed `propose()` method, which checks the router revision and calls only the authorized 80B provider. The 0.6B and 30B cannot substitute for an Engineering proposal. Provider, served model, digest and reasoning stage are persisted with the plan.
8. Conversation-origin objectives with an independently accepted completion enter a PostgreSQL-backed result outbox. The persistent service rechecks Grace's current office binding and exact `resident.conversation.send` grant, may ask the bound 80B for a nonblocking summary, and appends one assistant response to the original conversation. A stable objective-derived response ID makes retries idempotent; the outbox is acknowledged only after the conversation event is durable. Provider or authorization failure leaves the summary/return pending, while persisted dependent-step dispatch proceeds independently through CME.

## Accepted-step progression and rejected-work bound

Independent verifier `ACCEPTED` is the sole completion decision for a step.
The service selects the first persisted pending step whose `depends_on` set is
verified; the dependency list was approved in the original persisted plan.
Dispatch still uses the existing assignment intake, exact objective scope,
`assignment.create` recheck, proposal/step identity, and idempotency checks.
An accepted s1 does not mark the objective complete while other persisted steps
remain pending. The conversation result review is informational and does not
create additional acceptance criteria.

For a verifier `REJECTED`, Grace may propose correction only for an exact subset
of that step's stored criteria. The existing assignment is lease-fenced and
requeued, then independently verified again; the verifier rejection and each
correction receipt remain append-only. At most three `REWORK_PROPOSED`
corrections are persisted for the assignment. If the review provider is not
commissioned/unavailable, or the retry limit is reached, the owner cycle records
`engineering.rework_escalation_pending` with a reason, step/assignment and
verification IDs, retry count, and actionable Steward next step. This event
does not requeue, create or dispatch an assignment. An uncommissioned external
escalation provider is never treated as active; the Dashboard shows the durable
pending state for Steward action.
9. The structured review may return `OBJECTIVE_COMPLETE`, `ADDITIONAL_EVIDENCE_REQUIRED`, `ENGINEERING_STEP_PROPOSED`, or `STEWARD_AUTHORIZATION_REQUIRED`. A continuation is accepted only within the original objective and accepted-criteria envelope; the current binding is revalidated before and after model reasoning. It appends a durable step and uses the ordinary CME assignment-creation authorization and lease/verification path. Model output never supplies authority.
10. A durable verified-result review may be reconsidered only after a new evidence revision is submitted with the exact objective-scoped `objective.submit` grant. At most four generations exist per completion cycle. Each request stores evidence, revision, digest, actor, and idempotency key as an append-only objective event; generation-specific deterministic response IDs preserve earlier decisions and receipts while retries within a generation remain idempotent. Event idempotency keys are globally unique; cross-objective reuse fails closed. The outbox query selects unpublished initial reviews or pending generations before applying its batch limit, so older acknowledged results do not starve later requests. Evidence revision does not create a continuation or dispatch work. Any later `ENGINEERING_STEP_PROPOSED` remains subject to the existing exact-step, binding, verification, and `assignment.create` checks.

`read_reasoning_context(...)` includes the exact `repo://riverview/resident-engineering.v1`
contract reference expected by the resident knowledge adapter. Without it, the
generic repository path returns `NO_MATCH` and the persistent service waits before
calling the bound reasoning provider. With it, the existing pinned resident source
set is selected and revalidated; the reference grants no authority. Both grounding
and regrounding must still be complete and verified before a proposal is requested.
The owner-session 80B proposal HTTP call and ResidentReasoner caller share the
explicit `RIVERVIEW_RESIDENT_REASONING_TIMEOUT` deadline, bounded to 1–60 seconds.
The commissioned default is 60 seconds; model output remains subject to the
bounded 768-token proposal budget, typed schema, binding revalidation, and CME
authorization. Chat routing retains its separate per-stage limits.
After inference, the reasoner revalidates the active occupant, exact office-state
grant and binding revision through the runtime-authorized office-state function.
It does not directly read protected AuthorityRegistry tables.

The authenticated chat UI exposes an explicit Steward action for a selected,
persisted user-authored conversation message. `POST
/api/v1/resident/conversations/{conversation_id}/work-orders` accepts only the
source sequence and Steward-entered acceptance criteria. The server rechecks the
account session, Steward website role, exact conversation read grant, source
message principal/ownership, and `objective.submit` on the fixed
`work-order:engineering` scope before persisting an objective with conversation
origin. A same-source retry revalidates that exact grant, reuses the durable
objective, and retains the original acceptance criteria; retry input cannot
rewrite them. A blank criteria field is accepted only when the same source
already has an objective. Ordinary chat is never promoted automatically. This
is objective intake; it is not a Grace proposal, assignment dispatch, worker
authorization, or proof of execution.

The return-to-chat path is source implemented, not production commissioned. It returns artifact reference, digest and independent verifier evidence for Grace's 80B review; the reviewer does not reopen arbitrary files. PostgreSQL integration tests require `RIVERVIEW_TEST_PG_DSN`; this checkout has no such DSN. The execution service and exact resident-send, assignment-create, executor and verifier grants remain commissioning prerequisites. No code in this increment creates or broadens grants.

```mermaid
flowchart TD
    A[Steward message selected in Grace chat] --> B{Session ownership and exact objective.submit?}
    B -- No --> F[Denied and diagnosed]
    B -- Yes --> C[Persist grounded objective and source conversation]
    C --> D[Grace proposes through bound 80B]
    D --> E{Provenance and criteria valid?}
    E -- No --> W[Durable wait or failure]
    E -- Yes --> G[Existing assignment.create intake and CME]
    G --> H[Authorized Codex executor]
    H --> I[Independent artifact verifier]
    I -- ACCEPTED --> J[Objective completion and result outbox]
    I -- REJECTED --> R[Grace receives verifier evidence and digest-checked artifact]
    R --> Q{80B substantive decision}
    Q -- OBJECTIVE_SATISFIED --> V[Persist review; recheck same attempt under current verifier]
    Q -- REWORK_PROPOSED --> X[Recheck existing assignment.create grant; queue same assignment]
    Q -- STEWARD_AUTHORIZATION_REQUIRED --> W
    X --> H
    V --> I
    J --> K{Current binding and resident.conversation.send?}
    K -- No --> W
    K -- Yes --> L[Bound 80B reviews verifier evidence]
    L --> M[Idempotent result appended to source chat]
    M --> N[Durable outbox receipt; history reloadable]
    W --> J
```

This source increment is not proof of the live demonstration: no production deployment or migration occurred and no new production Codex artifact was produced here. Multi-step persistence requires additive migration `0009_durable_objective_steps.sql`, not applied to production.

Cancellation is supported only before execution for queued/ready assignments and requires exact assignment.cancel. Running work cannot be force-cancelled by this slice; CME lease/recovery behavior remains authoritative.

### Concurrent step assignment provenance and recovery

An objective's `assignment_id` is a single latest-dispatch projection. It is
not the identity of every concurrent step assignment: dispatching a sibling
step may replace that pointer while an earlier step remains leased or waiting
for recovery. Codex execution therefore resolves each assignment through
`grace_objective_steps.assignment_id` and its persisted `work_order.dispatched`
event, then uses that exact proposal step's objective and acceptance criteria.
The objective must still be `WORK_ORDER_CREATED` with the same immutable,
verified evidence and persisted proposal. A missing or ambiguous step link
fails closed.

Bounded Codex no-artifact recovery selects by the assignment's exact
`objective_ref`, then requires its unique persisted step assignment link, a
matching `work_order.dispatched` event and a matching step in the persisted
proposal. The objective's latest `assignment_id` is not a recovery selector.
Lease expiry, exact worker/scope/capability/effect checks, verified objective
provenance, absence of artifacts, attempts, results and verifier records, the
existing retry ceiling, one recovery record per generation, and ordinary
claim-time exact grants remain required. Recovery transitions the same
assignment to `ready`; it does not create a work order or increment the step's
dispatch count. Independent verification and the usual CME dependency checks
remain unchanged.

## Interfaces and bounds

- Objective ID: objective: followed by 1–120 ASCII letters, digits, ., _, :, or -.
- Request: UTF-8, 1–4,096 bytes. Acceptance criteria: 1–20 strings, each at most 1,000 characters.
- Plan: the current resident_reasoning.PlanProposal and PlanStep contract.
- Resident proposal generation accepts 1–20 dependency-ordered steps. PostgreSQL
  persists each step and assignment identity. CME dispatches only the first
  pending step whose dependencies have independent verification; it uses the
  existing worker lease, recovery, authorization and verifier path. The overall
  objective completes only after every persisted step is verified.
- Evidence: knowledge-provider v1 KnowledgeResult, full pinned-source verification plus deterministic ranked passage selection; max serialized evidence 8 KiB. All source refs, Git revision/hash, selection policy and term-coverage counts persist with the objective.
- Work order: assignment ID, objective ref, exact authority scope, contract ref, workflow ID/step, and correlation ID persist in the assignment ledger.
- Conversation origin: selected message sequence and conversation ID are attached to `objective.received`; only the authenticated linked Steward principal can submit from the chat route.
- Worker request: each durable step maps to its own assignment, retaining the original objective and correlation ID. Existing bounded-artifact work remains constrained to its assignment-derived output. The separate source-change capability requires immutable repository revision, explicit path allowlist, exact criteria, fixed test targets and bounded runtime.
- The source-change adapter stores a digest-verified patch and changed-file inventory only; the independent verifier replays it in an isolated clone. It does not merge, commit, or apply a patch to production. The capability is not registered or commissioned by this source increment.
- Result: status, workspace URI/name, SHA-256, size, source revision/hash. No credential or objective authorization is inferred from a worker result.
- Failure, unavailable provider, serialization failure, oversized context, rejected authorization, incomplete verification, and cancellation do not produce objective completion.

## Verification

Run deterministic selector tests:

\`\`\`bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_resident_knowledge.py' -v
\`\`\`

Run PostgreSQL integration tests with a disposable test DSN:

\`\`\`bash
RIVERVIEW_TEST_PG_DSN='postgresql://…' PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_grace_execution.py' -v
\`\`\`

Tests include authorized and unauthorized intake, commit-pinned selection, missing and oversized evidence, worker failure, incomplete verification, actual filesystem artifact creation, independent artifact reading, persisted ledger completion, and objective event history. These are model-independent infrastructure tests; they do not demonstrate live model reasoning, a resident service, a human dashboard interaction, or operational Grace acceptance.

### Codex CLI adapter — source-only checkpoint

`resident_execution.codex_cli.CodexCLIExecutionAdapter` accepts a typed
assignment, one operator-configured repository reference and pinned commit, and
a fixed `deliverable.md` output. It creates a fresh local clone, invokes the
configured Codex executable with `workspace-write`, network access disabled, a
noninteractive approval policy, bounded wall time and file size, and discarded
stdout/stderr. It rejects the interactive user's `~/.codex` directory and
returns only the assignment, knowledge-source revision, pinned repository
revision, artifact digest, and a `verification_required` result. These are
separate provenance fields: repository HEAD selects the Codex worktree, while
the verified source revision and digest identify the evidence Grace used. The
root-owned pinned checkout is inspected using a private per-command Git config
that trusts only that exact checkout and its `.git` directory. Persistent user
and host Git configuration is unchanged. Synthetic tests use a fake executable; they do
not prove real Codex authentication or model execution.

`scripts/run_grace_execution_service.py` can now select this adapter only when
`RIVERVIEW_ENGINEERING_ADAPTER=codex-cli` is explicitly set. It registers the
exact `engineering.codex-cli-artifact.v1` capability through the existing
worker registry; worker registration and every claim/execution still require
the exact `worker.register` and `assignment.execute` grants in the assignment
scope. Startup preflight requires a configured executable, dedicated
`CODEX_HOME`, isolated workspace, pinned repository, and artifact directory.
The normal CME lease, preflight/regrounding, execution-intent, attempt/result,
and independent verification records remain the execution path. The
`CodexMarkdownVerifier` independently reopens the assignment-bound file,
checks ownership/mode/size/digest, objective binding, both provenance
dimensions, and literal acceptance criteria. The result path and digest are retained in the
worker result and Grace objective completion event/projection.

The separate `engineering.codex-cli-source-change.v1` mode reuses the same
owner-session Codex CLI, leased worker, capability registration, assignment
execution grant, and verifier lifecycle. The mode is selected by the operator;
its configured JSON `RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS` is a maximum ceiling,
not an authority source. Every exact source/test path in a persisted source
step must also appear in the Steward's original request or accepted criteria.
The proposal parser and `PlanStep` contract reject malformed scopes, and the
pipeline refuses model-proposed paths absent from that human-approved text.
The adapter checks the per-step scope against the operator ceiling and pinned
repository revision, creates a patch in a fresh disposable clone, inventories
every changed path, checks patch integrity and runs only fixed assignment test
targets in an offline bubblewrap sandbox. Its verifier applies the patch to a
separate clean clone, compares the changed-file inventory and patch digest,
and reruns those tests. It returns verifier evidence only; it never applies a
patch to the configured source checkout or a production release. The active
Camrui runtime has not been switched to this mode; release source wiring is
not evidence of production registration or commissioning.

An interrupted source action is recoverable only through the same assignment's
deterministic owner-only patch file: the adapter reopens it without following
symlinks, reapplies it to the immutable base in a new clone, checks the exact
path scope, and reruns fixed tests before returning it for normal independent
verification. If no patch exists, the existing retry coordinator may requeue
only after the failed intent has expired and no result, attempt, verifier
record, or patch is present. Source patches remain pending verification after
worker recovery; recovery never marks work complete. Each Codex step receives
the original bounded objective as task context together with its model-proposed
step objective. This preserves concrete requirements through dispatch while
leaving the exact Steward-approved file/test allowlist unchanged; oversized
context fails closed.

Grace's verified-result review now records a typed decision and may append a
same-objective continuation only through the existing bounded pipeline. When
Grace selects an already-proposed dependent step, the conversation service
resolves that step ID to the immutable persisted step definition and discards
the model's mutable restatement; the pipeline then rechecks the durable parent
verification, pending child, exact objective link, and grants. A genuinely new
step must still fit the accepted criteria and path envelope. Each
source continuation keeps the original accepted path/criteria envelope, names
an earlier verified dependency, receives a new durable step assignment, and
reuses the latest independently verified cumulative patch as input. The
continuation remains subject to the original accepted scope, dependency
verification, current binding, and existing dispatch/worker grants; a model
response cannot grant its own authority. Source and isolated PostgreSQL
coverage are not evidence of live multi-step commissioning. Production use
still requires an explicitly staged runtime configuration selecting the source
mode and an existing exact worker-registration/execution grant for its
registered capability; this development change does not change either.

The capability registry records capability, active worker, and exact authority
scope; startup preflight plus the current Grace execution health heartbeat
provide dependency/readiness evidence. The Codex adapter no longer accepts or
passes `OPENAI_API_KEY`. Its supervised ChatGPT mode is available only to the
owning `admin1` identity from a TTY, uses that user's existing `CODEX_HOME`
directly without copying credentials, requires one explicit objective ID and
an exact terminal confirmation, and returns after that one bounded execution
cycle. It also requires the configured reasoning model identity to contain
`80b`; otherwise the run fails closed. The cycle dispatches and claims only the
selected assignment, then invokes the existing independent verifier and
completion reconciliation for that objective. A worker claim still requires
the existing exact `assignment.execute` grant, and dispatch still requires
`assignment.create` for the configured work-order scope.

The owner-session service and exact executor, verifier, resident, and dispatch
credentials/grants are provisioned on Camrui, but this does not itself prove a
completed assignment. A ChatGPT login is used in place by the owning `admin1`
session; no account files are copied and no API key is used. Synthetic tests
verify adapter contracts but are not evidence of a live artifact.

Pre-execution failures explicitly distinguish whether the Codex process
started. A failure proven to precede process launch is persisted as failed and
blocked, not `ACTION_OUTCOME_UNKNOWN`. Objective source revision and digest are
validated against that objective's immutable verified evidence; the current
worker-contract grounding revision and digest are a separate provenance pair
and may be newer after a release upgrade. Startup recovery may resume either a
legacy outcome-unknown intent after reproducing the root-owned Git refusal or a
durable `WORKER_PRE_EXECUTION_FAILED` intent when all checks prove no effect:
expired lease, verified objective, source/repository pin distinction, no worker
attempt, no verifier record, no assignment-bound artifact, and remaining
configured retry budget. The recovery event records the proof and graph node.
Normal claim-time authorization still revalidates the exact
`assignment.execute` grant before any retried action.

#### Corrected verifier revision recovery — source implementation

The bounded Markdown verifier interprets known acceptance instructions as
structured checks: exact heading and phrase, exact declared citation count and
paths, task-content requirements, the one-file source-worktree inventory, and
the source-versus-production distinction. Unknown criteria remain literal
requirements. The executor persists the checked source filename and changed
path list only after the pinned clone's exact change-set check. This prevents
the verifier from demanding that a deliverable reproduce task instructions
verbatim while preserving file-scope enforcement.

When a verifier rule is corrected, the original decision is immutable. Worker
adapter migration `0006_verifier_revision_rechecks.sql` replaces the one-row
per-attempt constraint with one row per attempt and verifier revision. The
service rechecks the current exact verifier grant and only selects a successful
attempt whose latest decision is REJECTED by this verifier under an older
revision. The adapter requires the deterministic
`grace-verifier-revalidation:<attempt-id>:<new-revision>` key, repeats
authorization, locks the assignment and attempt, reopens the same stored result,
and appends the new decision. It does not re-run Codex or alter the old row.
Completion still requires a persisted ACCEPTED verifier record. PostgreSQL
integration tests exercise the schema change, rejection preservation,
idempotency, and same-attempt revalidation. Production migration and
revalidation remain pending deployment.

### Governed verifier rejection and same-assignment rework

A rejected verifier result remains immutable and is exposed to Grace with its verifier identity/revision, failed checks, summary, evidence references and artifact digest. The independent verifier enforces artifact identity, integrity, provenance, authorized scope, criteria binding and mandatory structure; it does not decide whether prose substantively satisfies acceptance criteria. For Codex Markdown, the persistent Grace owner cycle reopens only the assignment-bound artifact whose owner, mode, size and digest still match, then gives the bounded text and verifier evidence to the currently bound 80B. If artifact bytes cannot safely be reopened, Grace receives the rejection evidence without the bytes and cannot declare the objective satisfied. Grace decides `OBJECTIVE_SATISFIED`, `REWORK_PROPOSED`, or `STEWARD_AUTHORIZATION_REQUIRED`; a verifier rejection alone never queues Codex rework. A satisfaction decision is durable and authorizes only an independent recheck of that same immutable attempt; it does not change the rejection or mark the objective complete. A rework proposal must reference a subset of the original step criteria and pass the existing exact `assignment.create` grant check. Model output never grants authority.

An authorized rework decision is appended under an idempotency key derived from the original verification ID. The completed worker lease is expired/fenced before the same assignment transitions from `rework_required` to `ready`; the next scheduler claim receives a new lease generation. Codex writes a verification-specific artifact filename so the rejected predecessor is preserved. Independent verification selects the new successful attempt only when no verifier record already exists for that attempt. A later rejection becomes a new Grace decision target. At most three correction proposals are permitted per assignment; provider absence or retry exhaustion creates a durable escalation-pending event and requires Steward action. A stop decision leaves the assignment rework-required and records that Steward direction is needed.

`GET /api/v1/objectives?conversation_id=<uuid>` is the persistent authenticated progress projection used by Talk with Grace. It filters by the immutable `objective.received` origin and returns bounded IDs, lifecycle stage, latest event type/time, verifier summary, rework counts/decision, and explicit Steward-action-needed state. It never reads conversation message bodies. The browser refreshes the panel with the existing 4-second conversation refresh cadence; reload rehydrates it from PostgreSQL. A toast or chat response is not execution evidence.

The generated workflow below is a projection of process_graphs/grace/operational-integration.json. Regenerate with python3 scripts/process_graph.py generate; verify with python3 scripts/process_graph.py check.


### Verified-step review is nonblocking for dependent dispatch

For a multi-step proposal, the existing Grace result-review publisher may receive each independently verified step through the durable objective-event outbox. The currently bound 80B may summarize the verified result and original accepted scope, but its response is not a dispatch prerequisite and cannot overturn the independent verifier. The next step already persisted in the accepted plan becomes dispatchable when its recorded dependencies are verified. CME rechecks the existing `assignment.create` grant, approval scope, step identity and idempotency before dispatch. A typed model proposal cannot add file paths, acceptance criteria, capabilities, or dependencies beyond the original proposal. The objective becomes complete only after every persisted step is verified; final result publication remains idempotent by completion cycle.

The review context also includes the objective's authoritative status and ordered persisted step statuses. Grace must use that state to distinguish an intermediate verified step from a fully completed objective. A model cannot infer that a planned step remains pending when the ledger records it as verified; context validation rejects inconsistent `COMPLETED` state unless every persisted step is verified.

### Resident grounding and source-target provenance

`grace_objectives.source_revision` and `source_sha256` identify the resident's
verified knowledge grounding only. They do not identify a Codex checkout. Each
new source-change plan step carries the Steward-authorized
`repository_reference` and immutable `repository_revision`; both must appear in
the original objective request or its accepted criteria. The dispatch event
stores a versioned source binding containing objective/assignment/step,
capability, repository identity, commit, authorized paths, test targets and the
canonical proposal-step digest. The runner compares this snapshot to the
proposal and exact configured repository checkout before execution. The
structured result and independent verifier must match the same binding and
replay the patch against that commit. No database migration is needed because
the binding is immutable payload on the existing `work_order.dispatched` event.
Unbound historical source attempts remain readable but cannot be executed or
silently mapped to a target commit; artifact objectives retain their former
grounding and dispatch behavior.

### Concurrent capability loops

The owner-session process can run its existing artifact worker plus one
separately credentialed source-change worker. The executor identity and grant
remain distinct, each adapter claims only its registered attempt capability,
and independent verifier dispatch uses the persisted attempt capability. The
worker cycle catches errors per capability; a failed or unavailable source
worker does not stop artifact polling. Source work remains undispatched when
its enrollment, target mapping, exact scope, path ceiling or immutable checkout
pin is missing. The installed base unit remains artifact-only until an
approved operator stages the separate source-worker drop-in.

Institutional proposals use a distinct Steward-only dashboard view and
message-menu draft action. Draft/revise/approve/promotion call the existing
proposal API and lifecycle. Approval applies to one revision and purpose;
promotion separately calls the existing pipeline under exact `objective.submit`.
The existing “Create Engineering work order” conversation action remains a
direct authenticated objective intake path and is not a proposal approval.

Verified Codex result return accepts the outbox's optional
`artifact_review_unavailable` status only when it is null or the fixed value
`integrity_check_failed`. The status is included as sanitized verifier context.
If artifact bytes cannot be reopened and digest-checked, Grace receives no
artifact text; verifier metadata remains available for its governed review.
Unknown status values and any unverified artifact text fail closed.
