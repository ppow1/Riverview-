# Grace Engineering objective submission — verified operating procedure

Status: documented from live smoke tests on 2026-10-21 (EDT). This is an operating procedure, not a change to authorization policy.

## Essential distinction

**Sending Grace a chat message does not create an Engineering objective.** A text response beginning “Proposal:” is conversational output, not a durable typed proposal or work order.

The Steward must submit the **original Steward message** through the authenticated Dashboard **Create Work Order / Create Engineering objective** action. This invokes `POST /api/v1/resident/conversations/{conversation_id}/work-orders`, which validates the selected message and authorization and persists an objective with an `objective.received` event linked to its source conversation and message sequence.

## Procedure

1. Open the desired Grace conversation and send one bounded Engineering request with a clear outcome, constraints, and independently verifiable deliverables.
2. Read Grace's conversational response for context; do not mistake its “Proposal” wording for an authenticated submission.
3. On the **original Steward message**, use the Dashboard's authenticated **Create Work Order** action. Confirm the selected source message/conversation is correct.
4. **Leave acceptance criteria blank** when using the deployed Grace-derived-criteria workflow (PR #190). Do not manually copy the conversational Acceptance line into the criteria field.
5. Submit exactly once. Confirm Engineering Progress shows the linked objective and a persisted `objective.received` event. If absent, investigate whether the Dashboard actually sent the work-order POST; do not resend the chat prompt or manufacture another objective.
6. Let the durable workflow advance: typed proposal and derived criteria → authorized work order → Engineering assignment → execution → independent verification → result publication → objective closure. Avoid duplicate dispatches.
7. Judge completion from persisted objective and verifier records, **not** the conversational response. Confirm accepted verification and `objective.completed`; record assignment count, artifact path, timestamps and elapsed time.

## Reusable request pattern

> Grace, I am authorizing a new autonomous end-to-end Engineering objective.
>
> **Objective:** [specific deliverable and exact contents/constraints].
>
> Execute this objective using your normal proposal, authorization, Engineering work-order, independent verification, and completion workflow.
>
> Requirements:
> - Use the authorized execution environment and artifact destination.
> - Establish independently verifiable acceptance criteria.
> - Close only after successful independent verification.
> - Do not create separate Engineering assignments for administrative lifecycle steps.
> - Do not claim completion without persisted execution and verification evidence.
>
> You are authorized to execute within the established Riverview authorization boundaries without redundant approval.
>
> When finished, report objective ID, Engineering assignment count, artifact location, verification result and total elapsed time. If blocked, report the exact stage and reason; do not substitute simulated or manually completed results.

The request pattern is guidance; **the Dashboard intake action is the required trigger**. Do not infer from this template that chat messages alone can authorize execution.

## Criteria contract

PR #190 allows omitted intake criteria and marks the objective for Grace-derived criteria. Formal acceptance criteria become durable when the validated **typed proposal** is persisted, and are bound to work-order steps. A model-generated conversational “Acceptance:” bullet is not the durable criteria record. Earlier design context: issue #160; criteria changes: PRs #188–#192.

## Evidence from two runs

| Evidence | Smoke test #1 | Smoke test #2 |
| --- | --- | --- |
| Conversation | `73a08d0d-80ea-4891-818a-5a65958e525a` | `e01d1bbd-48af-481a-9592-a6784bb10561` |
| Objective | `objective:grace-conversation:8416c5da-bde5-5294-9276-c0163418fae1` | `objective:grace-conversation:8b3eba72-a2e3-5faf-9bf0-aaeba7c56224` |
| Intake | Dashboard POST returned 202 ~13:58:27 EDT | Initially chat-only: no POST/objective; later Dashboard intake produced objective |
| Engineering | One assignment; independently accepted | One assignment `assignment:grace:3d7b76c3324324daf8337f1852776f4c8c11c383`; independently accepted |
| Closure | Completed 22:30:21 EDT | Result published 23:24:03; objective completed 23:24:13 EDT |

For test #2 the original chat message was at 22:59:02 EDT; elapsed time from that message to closure (~25m11s) **includes manual investigation and delayed intake**, so it is not representative of autonomous execution time.

## Troubleshooting decision

- Chat text but no objective: check authenticated `/work-orders` POST for the **selected conversation** and corresponding `objective.received` event. A missing POST is a missing intake action, not evidence that the model failed to write a proposal.
- Objective exists but no assignment: inspect typed proposal, criteria binding, authorization and lifecycle events.
- Assignment exists: inspect worker transitions, artifacts and independent verifier evidence.
- Verification accepted but objective open: inspect result publication and final objective closure.

## Verification boundaries

The exact deployed Dashboard control placement and dialogs should be captured in screenshots before publishing a click-by-click UI guide. No API replay, duplicate objective creation, authorization bypass or production modification is part of this document.
