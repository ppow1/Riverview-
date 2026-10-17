# Riverview — AI Proposal Authoring and Submission Playbook

**Document revision:** 1.0.0 (proposed)  
**Component:** INSTITUTIONAL-PROPOSALS  
**Status:** Authoring guide for review; repository merge and live acceptance not yet verified  
**Authority:** Steward retains all proposal decisions and Engineering work-order authority  
**Primary contract:** `docs/components/INSTITUTIONAL_PROPOSALS.md` (verified on PR #70 branch; verify presence on target branch before linking)

## 1. Purpose and entry point

This document tells a new AI how to prepare, submit, locate, and track a Riverview institutional proposal without confusing proposal creation with authorization to execute work.

On entering Riverview, read root `AI_HINTS.md`, this playbook, the institutional proposals contract, and the applicable engineering lifecycle standards. Confirm the active repository and deployed API contract before sending requests. If this playbook or its referenced API is not present in the deployed release, report **NOT AVAILABLE**; do not invent a substitute endpoint.

## 2. What counts as a proposal

A proposal is durable planning material. It is **not** an objective, assignment, executable work order, authorization grant, or instruction to change production. Drafting, saving, searching, reviewing, or revising it does not confer execution authority.

Write proposals in language a human Steward and independent reviewer can evaluate. Explicitly separate known facts, assumptions, alternatives, risks, costs, dependencies, and unresolved questions. Do not represent an unperformed test or uncommissioned resident review as complete.

## 3. Authoring contract

A proposal revision has exactly these eight content fields:

| Field | Type | Limit | Required content |
|---|---|---|---|
| `title` | string | 200 characters | Specific, distinguishable title |
| `summary` | string | 1,000 characters | Concise executive overview |
| `objective` | string | 4,000 characters | Measurable desired outcome and motivation |
| `scope` | string | 4,000 characters | Included and excluded work |
| `proposed_approach` | string | 6,000 characters | Suggested design, phases, alternatives and dependencies |
| `constraints` | string array | Up to 24, each up to 1,000 characters | Hard limits, security and operational boundaries |
| `acceptance_criteria` | string array | Up to 24, each up to 1,000 characters | Observable tests/evidence needed for success |
| `tags` | string array | Up to 24, each up to 64 characters | Searchable classifications |

All five text fields must be nonempty. Tags are normalized to lowercase and must conform to the repository's tag validation. Lists may be empty, but meaningful acceptance criteria are strongly recommended. The registry rejects extra or missing fields.

**Illustrative proposal content (not a submission request):**

```json
{
  "title": "Improve Riverview proposal discovery",
  "summary": "Make institutional proposal instructions discoverable from the root AI entry point.",
  "objective": "Allow an unfamiliar AI to find the authoritative proposal process and prepare a valid draft without private instructions.",
  "scope": "Include AI_HINTS navigation and documentation acceptance testing. Exclude production changes and Engineering dispatch.",
  "proposed_approach": "Link the authoring playbook from AI_HINTS, verify the endpoint contract, and run a draft-only acceptance test using an authorized Steward session.",
  "constraints": ["No implicit execution authorization", "No fabricated API results"],
  "acceptance_criteria": ["A new AI locates the playbook from AI_HINTS", "An authorized draft submission returns a persisted proposal ID and revision"],
  "tags": ["documentation", "proposal", "ai-onboarding"]
}
```

The API's conversation-based creation endpoint does **not** accept this JSON object directly. It derives the proposal from selected persisted conversation messages. The content example is a writing/validation template, not an undocumented HTTP contract.

## 4. Supported submission path — authenticated Steward conversation

The verified versioned contract is `rv.institutional.proposals.v1`. It requires an authenticated Steward account session. State-changing HTTP requests also require same-origin and CSRF protections. An AI without that authorized session must prepare a proposal for Steward submission, not bypass authentication.

1. Discuss the proposed work in an existing Grace conversation. Present the eight content fields, including uncertainties and measurable acceptance criteria.
2. Have the Steward explicitly select the persisted Steward-authored message(s) that contain the proposal. Obtain the actual `conversation_id` (UUID) and 1–20 distinct persisted `source_sequences`. **Do not invent message sequence numbers or submit AI-only messages as Steward-authored messages.**
3. Generate a stable `idempotency_key` for this specific submission; retain it for safe retries.
4. Using the authenticated website/API client, submit:

```http
POST /api/v1/institutional-proposals
Content-Type: application/json
[Existing authenticated Steward session and required CSRF protection]

{
  "conversation_id": "<actual-conversation-uuid>",
  "source_sequences": [<actual-persisted-steward-sequence>],
  "idempotency_key": "<stable-unique-key-for-this-submission>",
  "instruction": "Formalize the selected proposal as a draft; preserve constraints and acceptance criteria."
}
```

5. Inspect the server response. `draft_saved` means the server persisted a `DRAFT` proposal/revision. Record its actual proposal ID, revision, and returned status. `clarification_required` means the AI must obtain the requested clarification; do not report submission success.
6. Repeating the same idempotency key is safe only for the same principal, conversation, and selected sequences. Changed bindings conflict; create a new submission only for a genuinely new request.

The server rechecks conversation access, office binding, and the configured local 80B reasoning route. If any check fails, report the actual error without claiming a saved draft.

## 5. Find, retrieve, and track a proposal

With the authenticated client:

```http
GET /api/v1/institutional-proposals?q=<search>&tag=<tag>&status=<status>&limit=<limit>
GET /api/v1/institutional-proposals/<actual-proposal-id>?revision=<positive-integer>
```

Search retrieves current eligible revisions; retrieval returns the requested immutable revision, its reviews, lifecycle events, and any linked objective/execution status when configured. Keep proposal IDs in their actual `proposal:<uuid>` format. Do not invent proposal records, reviews, status transitions, or work-order links.

The registry lifecycle includes `DRAFT`, `READY_FOR_REVIEW`, `UNDER_REVIEW`, `CHANGES_REQUIRED`, `READY_FOR_STEWARD_DECISION`, `APPROVED`, `DEFERRED`, `REJECTED`, `SUPERSEDED`, and `ARCHIVED`. These are distinct states, not synonyms for executable work. Revision or review operations beyond the documented endpoints require inspecting the actual versioned implementation; this playbook does not invent a generic revision endpoint.

## 6. Review and Steward decision

The Steward reviews the **exact current revision** and its `content_sha256`. Decision and promotion are separate operations. The documented decision endpoint is:

```http
POST /api/v1/institutional-proposals/<actual-proposal-id>/decision
Content-Type: application/json
[Existing authenticated Steward session and required CSRF protection]

{
  "revision": <actual-current-revision>,
  "decision": "APPROVE",
  "reason": "<Steward's actual reason>",
  "idempotency_key": "<stable-decision-key>",
  "content_sha256": "<actual-server-returned-revision-digest>",
  "approved_purpose": "<Steward's explicitly approved purpose>"
}
```

The allowed decisions are `APPROVE`, `REQUEST_CHANGES`, `DEFER`, and `REJECT`. Approval requires the purpose and explicit acceptance of applicable review conditions. The exact request representation for accepted conditions must be verified against the deployed handler before sending a conditional approval. An AI must not generate or send a Steward decision without explicit Steward authorization.

Material revision changes return the proposal to draft; earlier reviews/approval do not automatically apply to the new revision. A stale revision or digest must be reread, not silently overridden.

## 7. Promotion to Engineering is separate

Only after an authorized Steward approval of the current revision may the separate promotion operation be requested:

```http
POST /api/v1/institutional-proposals/<actual-proposal-id>/work-orders
Content-Type: application/json
[Existing authenticated Steward session and required CSRF protection]

{"revision": <actual-approved-current-revision>}
```

Promotion requires the existing exact `objective.submit` grant at `work-order:engineering`. It submits/reuses a deterministic objective through the existing Grace execution pipeline; it does not itself create an assignment or dispatch a worker. The existing `assignment.create` boundary is independently enforced later. A missing grant is a stop, not a reason to bypass the authority system.

The conversational command route exists for **explicit** persisted Steward commands naming proposal ID and revision; general agreement such as “yes” or “looks good” is not authorization.

## 8. Handoff format for an AI

After a real submission, report: actual proposal ID; revision; server-confirmed lifecycle status; title and summary; selected conversation and source sequences; outstanding clarification/reviews; approval state; whether an Engineering objective was separately authorized and created; and evidence/links to the retrieved record. Label any missing live verification as **NOT VERIFIED**.

If no authorized session or commissioned endpoint is available, deliver the complete eight-field proposal as a **submission-ready draft** and explicitly state **NOT SUBMITTED**. Never fabricate an ID or mark it `APPROVED`.

## 9. Acceptance test for the playbook

Give a new AI only the root `AI_HINTS.md` and normal authorized repository access. Verify that it discovers this document, constructs the eight-field proposal, identifies the actual conversation-based API contract, and accurately describes authentication and execution boundaries. In a suitable authorized test environment, select persisted Steward messages, submit one harmless draft, verify `draft_saved` and retrieval by actual ID, then confirm no objective/assignment was created. Do not execute this production test without Steward authorization.

## 10. Documentation and deployment caveat

This playbook is based on the `INSTITUTIONAL_PROPOSALS.md` contract and `ProposalContent.parse` implementation inspected on PR #70's head, not on a demonstrated production submission. At drafting time, the root `AI_HINTS.md` on `main` (revision 1.0.3) lacked a proposal link, and the referenced component contract was not found on `main` at its expected path. Before claiming onboarding complete, integrate the relevant contract and this playbook into the approved branch and update `AI_HINTS.md`.

### Required addition to root `AI_HINTS.md`

Add under the startup guidance (with normal Riverview predecessor preservation and file-revision increment):

> **Institutional proposal authoring:** If the task is to suggest, formalize, submit, review, or track a Riverview proposal, read `docs/development/PROPOSAL_AUTHORING_PLAYBOOK.md` and `docs/components/INSTITUTIONAL_PROPOSALS.md` before acting. A proposal draft is not execution authority. Use only the documented authenticated Steward conversation submission flow; never invent proposal IDs, API routes, or grants. Explicit Steward approval and separate authorized promotion are required before Engineering objective intake.
