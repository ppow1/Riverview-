# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/INSTITUTIONAL_PROPOSALS.md
# Component: INSTITUTIONAL-PROPOSALS
# Revision: 1.1.0
# Purpose: Define the durable proposal and revision lifecycle before execution authorization
# Status: Development contract; migration 0010 is additive and not commissioned in production
# Authority: Steward retains proposal decision and work-order authority
# Dependencies: ResidentConversationService; AuthorityRegistry; PostgreSQL resident-execution schema
# Changed: 2026-10-16 UTC | RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001 | Initial proposal lifecycle contract
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Define revision-bound Steward decisions and existing-pipeline promotion API
# Source: src/riverview_core/resident_execution/proposals.py; migration 0010
# Tests: tests/test_institutional_proposals.py; tests/test_proposal_work_order_lifecycle.py; tests/test_resident_conversation.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================

## Boundary

A proposal is durable planning material. Drafting, saving, searching, reviewing, or
revising it does not create an objective, assignment, work order, repository grant,
or authority to execute. Existing `objective.submit`, `assignment.create`, the
Engineering pipeline, and independent verification remain the execution boundary.
CME observes continuity; it does not authorize proposals or dispatch work.

## Versioned API contract `rv.institutional.proposals.v1`

All endpoints require an authenticated Steward account session. State-changing
requests also require the existing same-origin and CSRF checks.

- `POST /api/v1/institutional-proposals` formalizes explicitly selected messages
  from an existing Grace conversation. JSON fields: `conversation_id` (UUID),
  `source_sequences` (1–20 unique persisted Steward message sequence numbers),
  `idempotency_key` (client-generated stable key), and optional `instruction`.
  The server rechecks `resident.conversation.read` and `.send`, office binding,
  and the configured 80B reasoning route. It verifies each source message belongs
  to the authenticated Steward. The result is either `draft_saved` with a
  persisted `DRAFT` proposal/revision or `clarification_required`. It does not
  create or submit a work order.
- `GET /api/v1/institutional-proposals?q=&tag=&status=&limit=` searches the
  current non-archived, non-expired revision using PostgreSQL full-text search,
  tags, and status.
- `GET /api/v1/institutional-proposals/{proposal_id}?revision=N` retrieves the
  requested immutable revision (current revision when omitted), its revision-bound
  reviews, lifecycle events, and linked work-order/execution status when the
  objective pipeline is configured. `revision` must occur once and be a positive
  integer; malformed or repeated values are rejected.
- `POST /api/v1/institutional-proposals/{proposal_id}/decision` records one
  Steward decision for the exact current revision. Required fields are
  `revision`, `decision` (`APPROVE`, `REQUEST_CHANGES`, `DEFER`, or `REJECT`),
  `reason`, `idempotency_key`, and the reviewed `content_sha256`. `APPROVE` also
  requires `approved_purpose`; review conditions must be explicitly accepted.
  The authenticated Steward account and linked institutional principal supply
  actor and authority provenance; clients cannot supply those fields. The
  decision event is append-only and retries must match the original request.
- `POST /api/v1/institutional-proposals/{proposal_id}/work-orders` accepts
  `{ "revision": N }`. It requires the current approved revision, its matching
  approval event, and the existing exact `objective.submit` grant at
  `work-order:engineering`. It then submits/reuses one deterministic objective
  through `GraceExecutionPipeline`; it does not create an assignment or dispatch
  a worker. Missing `objective.submit` leaves the proposal approved and reports
  an authorization error. A later missing `assignment.create` remains a
  dispatch failure in the existing execution ledger and appears in proposal
  status; it does not undo approval or objective intake.
- `POST /api/v1/institutional-proposals/conversational-command` accepts the
  conversation ID and source sequence. The backend re-reads the persisted
  Steward-authored message and accepts only explicit commands naming a proposal
  ID, revision, and (for approval) purpose. For example: “Grace, approve proposal
  proposal:<uuid> revision 2 for internal prototype” or “Grace, create
  Engineering work order from proposal proposal:<uuid> revision 2”. A plain
  “yes”, “looks good”, or general agreement is inert. This route invokes the same
  decision/promotion operations as the direct API and checks conversation access.

Decision and promotion are separate transactions. Proposal approval records a
purpose for one immutable revision. Promotion is a distinct exact-grant operation
through the existing objective pipeline. Existing CME dispatch separately checks
`assignment.create`; neither proposal status nor a model response grants it.

Repeating a draft request with the same idempotency key returns the saved record
only if the principal and source conversation/sequences match. A changed source
binding conflicts. Search and retrieval do not invent records.

## Persistence and lifecycle

Migration `0010_institutional_proposal_registry.sql` adds stable IDs, immutable
content revisions, full-text and tag indexes, append-only lifecycle events,
revision-scoped review records, privacy/retention metadata, and an explicit
proposal-to-objective/assignment provenance link. Runtime privileges are limited
to proposal tables and selected mutable lifecycle columns; no deletion or
authority-ledger access is granted.

Lifecycle transitions are checked in the registry. Only the dedicated
`steward_decision` operation can approve, reject, defer, or request changes;
generic reviewer lifecycle transitions cannot set a Steward decision status.
Steward approval is attached to a specific current revision and defined purpose. A later material revision
returns to `DRAFT`; prior reviews remain attached to their historical revision
and do not carry forward. The low-level registry records a verified caller's
review/decision, but does not itself confer authority. HTTP handlers require an
authenticated Steward account session; promotion rechecks `objective.submit` in
the existing AuthorityRegistry-backed pipeline. No new grant or authority table
was introduced.

Resident review records identify office, principal, revision, outcome, findings,
conditions, evidence, authority reference, and idempotency key. The schema can
record future Security, Legal, HR/Resources, and Operations reviews. No uncommissioned
resident is activated or represented as having reviewed a proposal.

Privacy classification and retention are metadata in this increment. The current
proposal reasoning path is limited to the locally configured bound 80B; external
provider selection, local-only enforcement across future providers, and retention
jobs remain unimplemented and must be resolved before those providers/policies are
commissioned.

## Execution linkage and recovery

The objective's immutable `objective.received` event stores the proposal ID and
revision, content digest, approval-event key, exact `objective.submit` grant ID,
approved purpose, source references, privacy classification, and retention
policy. Deterministic objective identity and validation of every persisted field
make repeated promotion idempotent and reject identity collisions. Grounding,
reasoning, dispatch, leasing, execution, and independent verification remain the
existing pipeline. The Grace execution service periodically reconciles assignment
links and sanitized execution/verification evidence from durable ledger records;
repeating the cycle after a restart is idempotent.

Codex 2 can build the UI against the versioned endpoints above without duplicating
authorization or lifecycle logic. Backend implementation and isolated PostgreSQL
checks do not prove production migration application, deployment, authenticated
website integration, or a live Codex execution. Migration `0010` remains a
deployment prerequisite where it is not already applied.
