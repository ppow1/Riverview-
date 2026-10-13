<!--
Riverview~ Controlled Document
File: docs/components/GRACE_EXECUTION_PIPELINE.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.3
Purpose: Specify the deterministic, governed objective-to-work-order infrastructure slice
Authority: Engineering contract; not evidence of production Grace commissioning
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Link persistent reconciliation and authenticated dashboard handoff
Changed: 2026-10-13 UTC | RV-GRACE-CONVERSATION-WORKORDER-CONTRACT | Document explicit message-origin objective intake and its exact Steward grant
Changed: 2026-10-13 UTC | RV-CODEX-CLI-ADAPTER-001 | Record the source-only bounded Codex artifact adapter and commissioning gates
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
2. ground_objective(objective_id) asks TaskRelevantRepositoryKnowledgeProvider for the resident contract at one pinned Git commit. Evidence must be VERIFIED, complete, cite repository sources, include the full source revision and SHA-256, and fit the 8 KiB serialized evidence limit. Missing evidence waits/fails closed; oversized evidence is rejected explicitly.
3. record_proposal(objective_id, PlanProposal) accepts only the existing typed plan. It stores the unapproved plan and hash. This method is a persistence boundary, not a reasoning engine.
4. authorize_and_dispatch(...) requires exact assignment.create, the same scope as intake, and complete verified evidence. It uses AuthorizedAssignmentIntake; assignment + creation event + objective/work-order link are one PostgreSQL transaction. The event processor remains responsible for queued-to-ready.
5. ContinuousWorker obtains a lease, rechecks its registered engineering.bounded-artifact.v1 capability, and writes one small JSON work product into a mode-0700 workspace. The worker has no shell, command, or caller-selected path.
6. BoundedArtifactVerifier reopens the artifact by an assignment-derived name, verifies bytes/provenance/shape independently, and the existing adapter persists verification before completion. The objective can be marked complete only from a completed assignment plus persisted ACCEPTED verification.

The authenticated chat UI exposes an explicit Steward action for a selected,
persisted user-authored conversation message. `POST
/api/v1/resident/conversations/{conversation_id}/work-orders` accepts only the
source sequence and Steward-entered acceptance criteria. The server rechecks the
account session, Steward website role, exact conversation read grant, source
message principal/ownership, and `objective.submit` on the fixed
`work-order:engineering` scope before persisting an objective with conversation
origin. Ordinary chat is never promoted automatically. This is objective intake;
it is not a Grace proposal, assignment dispatch, worker authorization, or proof
of execution. The currently deployed registry has no such objective grant, and
the new route is uncommissioned until the Steward approves the exact authority.

Cancellation is supported only before execution for queued/ready assignments and requires exact assignment.cancel. Running work cannot be force-cancelled by this slice; CME lease/recovery behavior remains authoritative.

## Interfaces and bounds

- Objective ID: objective: followed by 1–120 ASCII letters, digits, ., _, :, or -.
- Request: UTF-8, 1–4,096 bytes. Acceptance criteria: 1–20 strings, each at most 1,000 characters.
- Plan: the current resident_reasoning.PlanProposal and PlanStep contract.
- Dispatch currently accepts exactly one proposed step. It rejects multi-step
  proposals rather than silently discarding dependency/fanout information.
- Evidence: knowledge-provider v1 KnowledgeResult, complete retrieval only; max serialized evidence 8 KiB. Source refs, Git revision, and hash persist with objective.
- Work order: assignment ID, objective ref, exact authority scope, contract ref, workflow ID/step, and correlation ID persist in the assignment ledger.
- Conversation origin: selected message sequence and conversation ID are attached to `objective.received`; only the authenticated linked Steward principal can submit from the chat route.
- Worker request: CodingWorkOrder carries assignment/objective identity, pinned repository revision, bounded task scope, criteria, exact allowed operation (write_bounded_json_artifact), and a 1–90 second timeout.
- The worker is a deterministic infrastructure adapter, not a general coding
  executor. A real coding executor and resident service remain later integration work.
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
returns only the assignment, source revision, artifact digest, and a
`verification_required` result. Synthetic tests use a fake executable; they do
not prove real Codex authentication or model execution.

This adapter is **not selected by the persistent service**, registered in the
live capability records, integrated with assignment attempt/result persistence
and an independent verifier, or deployed. The current service still uses
`BoundedLocalCodingWorker`. A dedicated Riverview-owned Codex executable and
service identity, credential isolation review, exact registered capability,
resource readiness record, and the existing exact `worker.register` and
`assignment.execute` decisions are required before enablement. The Steward's
four in-principle grants do not create grant rows. The Grace execution service
is inactive, and the installed Codex binary is under admin1's personal home;
neither is used by this adapter. The first safe demonstration needs a
non-destructive assignment, an independent verifier, and durable return of its
artifact and evidence to Grace.

The generated workflow below is a projection of process_graphs/grace/operational-integration.json. Regenerate with python3 scripts/process_graph.py generate; verify with python3 scripts/process_graph.py check.
