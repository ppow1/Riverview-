<!--
Riverview~ Controlled Document
File: docs/components/GRACE_EXECUTION_PIPELINE.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.0
Purpose: Specify the deterministic, governed objective-to-work-order infrastructure slice
Authority: Engineering contract; not evidence of production Grace commissioning
Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Define persisted objective, evidence, proposal, worker, and verifier interfaces
-->
# Grace Execution Pipeline — infrastructure slice

**Status:** Implemented for deterministic, isolated integration; not a commissioned operational Grace resident.

**Source:** src/riverview_core/resident_execution/ and the existing assignment, scheduler, worker, and verifier modules.

## Lifecycle and authority

1. GraceExecutionPipeline.submit_objective(...) requires the exact objective.submit grant for the supplied scope. It writes the bounded human request, criteria, authenticated submitter, and objective.received event together.
2. ground_objective(objective_id) asks TaskRelevantRepositoryKnowledgeProvider for the resident contract at one pinned Git commit. Evidence must be VERIFIED, complete, cite repository sources, include the full source revision and SHA-256, and fit the 8 KiB serialized evidence limit. Missing evidence waits/fails closed; oversized evidence is rejected explicitly.
3. record_proposal(objective_id, PlanProposal) accepts only the existing typed plan. It stores the unapproved plan and hash. This method is a persistence boundary, not a reasoning engine.
4. authorize_and_dispatch(...) requires exact assignment.create, the same scope as intake, and complete verified evidence. It uses AuthorizedAssignmentIntake; assignment + creation event + objective/work-order link are one PostgreSQL transaction. The event processor remains responsible for queued-to-ready.
5. ContinuousWorker obtains a lease, rechecks its registered engineering.bounded-artifact.v1 capability, and writes one small JSON work product into a mode-0700 workspace. The worker has no shell, command, or caller-selected path.
6. BoundedArtifactVerifier reopens the artifact by an assignment-derived name, verifies bytes/provenance/shape independently, and the existing adapter persists verification before completion. The objective can be marked complete only from a completed assignment plus persisted ACCEPTED verification.

Cancellation is supported only before execution for queued/ready assignments and requires exact assignment.cancel. Running work cannot be force-cancelled by this slice; CME lease/recovery behavior remains authoritative.

## Interfaces and bounds

- Objective ID: objective: followed by 1–120 ASCII letters, digits, ., _, :, or -.
- Request: UTF-8, 1–4,096 bytes. Acceptance criteria: 1–20 strings, each at most 1,000 characters.
- Plan: the current resident_reasoning.PlanProposal and PlanStep contract.
- Dispatch currently accepts exactly one proposed step. It rejects multi-step
  proposals rather than silently discarding dependency/fanout information.
- Evidence: knowledge-provider v1 KnowledgeResult, complete retrieval only; max serialized evidence 8 KiB. Source refs, Git revision, and hash persist with objective.
- Work order: assignment ID, objective ref, exact authority scope, contract ref, workflow ID/step, and correlation ID persist in the assignment ledger.
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

The generated workflow below is a projection of process_graphs/grace/operational-integration.json. Regenerate with python3 scripts/process_graph.py generate; verify with python3 scripts/process_graph.py check.
