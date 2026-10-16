<!--
Riverview~ Controlled Document
File: docs/components/GRACE_EXECUTION_PIPELINE.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.1.11
Purpose: Specify the deterministic, governed objective-to-work-order infrastructure slice
Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Document corrected acceptance interpretation and append-only same-attempt verifier recovery
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

**Source:** src/riverview_core/resident_execution/ and the existing assignment, scheduler, worker, and verifier modules.

## Lifecycle and authority

1. GraceExecutionPipeline.submit_objective(...) requires the exact objective.submit grant for the supplied scope. It writes the bounded human request, criteria, authenticated submitter, and objective.received event together.
2. ground_objective(objective_id) asks TaskRelevantRepositoryKnowledgeProvider for the resident contract at one pinned Git commit. The provider verifies the full allowlisted source set and selects ranked, complete paragraphs within a 7 KiB selection budget, leaving room for the provenance envelope under the 8 KiB serialized evidence limit. It records the selection policy and query-term coverage; it does not claim every lexical match was passed to the model. Paragraphs are never clipped. Missing sources or a selection with no complete passage that fits waits/fails closed.
   A same-origin retry may call grounding again while the durable objective is `WAITING_FOR_EVIDENCE`. Verified evidence atomically advances either `RECEIVED` or `WAITING_FOR_EVIDENCE` to `GROUNDED`; the state predicate prevents a second concurrent retry from overwriting an already grounded or later-stage objective. Incomplete evidence remains pending with a new revision and event.
3. record_proposal(objective_id, PlanProposal) accepts only the existing typed plan. It stores the unapproved plan and hash. This method is a persistence boundary, not a reasoning engine.
4. authorize_and_dispatch(...) requires exact assignment.create, the same scope as intake, and complete verified evidence. It uses AuthorizedAssignmentIntake; assignment + creation event + objective/work-order link are one PostgreSQL transaction. The event processor remains responsible for queued-to-ready.
5. ContinuousWorker obtains a lease and rechecks the registered capability and exact authority. The existing bounded-artifact capability writes one small assignment-derived work product. The separate source-change adapter can produce a patch for explicitly allowlisted files in a pinned disposable clone; it returns patch evidence only and never applies changes to the configured checkout or production.
6. The verifier independently reopens the bounded artifact or reapplies a source patch in a separate clean clone, checks scope, digest and provenance, and reruns fixed tests. A dependent objective step is not dispatched until its predecessor has an independently accepted verification.
7. For a `grace.readiness_router.v1` binding, ResidentReasoner proposals use the router's typed `propose()` method, which checks the router revision and calls only the authorized 80B provider. The 0.6B and 30B cannot substitute for an Engineering proposal. Provider, served model, digest and reasoning stage are persisted with the plan.
8. Conversation-origin objectives with an independently accepted completion enter a PostgreSQL-backed result outbox. The persistent service rechecks Grace's current office binding and exact `resident.conversation.send` grant, asks the bound 80B to review verifier evidence, and appends one assistant response to the original conversation. A stable objective-derived response ID makes retries idempotent; the outbox is acknowledged only after the conversation event is durable. Provider or authorization failure leaves it pending for retry.
9. The structured review may return `OBJECTIVE_COMPLETE`, `ADDITIONAL_EVIDENCE_REQUIRED`, `ENGINEERING_STEP_PROPOSED`, or `STEWARD_AUTHORIZATION_REQUIRED`. A continuation is accepted only within the original objective and accepted-criteria envelope; the current binding is revalidated before and after model reasoning. It appends a durable step and uses the ordinary CME assignment-creation authorization and lease/verification path. Model output never supplies authority.

`read_reasoning_context(...)` includes the exact `repo://riverview/resident-engineering.v1`
contract reference expected by the resident knowledge adapter. Without it, the
generic repository path returns `NO_MATCH` and the persistent service waits before
calling the bound reasoning provider. With it, the existing pinned resident source
set is selected and revalidated; the reference grants no authority. Both grounding
and regrounding must still be complete and verified before a proposal is requested.
The owner-session 80B proposal HTTP call and ResidentReasoner caller share the
explicit `RIVERVIEW_RESIDENT_REASONING_TIMEOUT` deadline, bounded to 1–60 seconds.
The commissioned default is 60 seconds; model output remains subject to the
existing 256-token proposal budget, typed schema, binding revalidation, and CME
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
    I --> J[Objective completion and result outbox]
    J --> K{Current binding and resident.conversation.send?}
    K -- No --> W
    K -- Yes --> L[Bound 80B reviews verifier evidence]
    L --> M[Idempotent result appended to source chat]
    M --> N[Durable outbox receipt; history reloadable]
    W --> J
```

This source increment is not proof of the live demonstration: no production deployment or migration occurred and no new production Codex artifact was produced here. Multi-step persistence requires additive migration `0009_durable_objective_steps.sql`, not applied to production.

Cancellation is supported only before execution for queued/ready assignments and requires exact assignment.cancel. Running work cannot be force-cancelled by this slice; CME lease/recovery behavior remains authoritative.

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

The separate `engineering.codex-cli-source-change.v1` adapter accepts an
explicit exact-file allowlist and immutable base revision, creates a patch in a
fresh disposable clone, inventories every changed path, checks the patch and
runs only fixed assignment test targets in an offline bubblewrap sandbox. Its
verifier applies the patch to a separate clean clone, compares the changed-file
inventory and patch digest, and reruns those tests. It returns a verifier
evidence record only; it never applies a patch to the configured source checkout
or a production release. The capability is not registered by the live service
and remains unavailable to production assignments pending exact capability
registration and its authority grant.

Grace's verified-result review now records a typed decision and may append a
same-objective continuation only through the existing bounded pipeline. The
continuation remains subject to the original accepted scope, dependency
verification, current binding, and existing dispatch/worker grants; a model
response cannot grant its own authority. Source and isolated PostgreSQL
coverage are not evidence of live multi-step commissioning.

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

The generated workflow below is a projection of process_graphs/grace/operational-integration.json. Regenerate with python3 scripts/process_graph.py generate; verify with python3 scripts/process_graph.py check.
