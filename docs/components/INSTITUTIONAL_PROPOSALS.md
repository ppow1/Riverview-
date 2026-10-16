# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/INSTITUTIONAL_PROPOSALS.md
# Component: INSTITUTIONAL-PROPOSALS
# Revision: 1.0.0
# Purpose: Define the durable proposal and revision lifecycle before execution authorization
# Status: Development contract; migration 0010 is additive and not commissioned in production
# Authority: Steward retains proposal decision and work-order authority
# Dependencies: ResidentConversationService; AuthorityRegistry; PostgreSQL resident-execution schema
# Changed: 2026-10-16 UTC | RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001 | Initial proposal lifecycle contract
# Source: src/riverview_core/resident_execution/proposals.py; migration 0010
# Tests: tests/test_institutional_proposals.py; tests/test_resident_conversation.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================

## Boundary

A proposal is durable planning material. Drafting, saving, searching, reviewing, or
revising it does not create an objective, assignment, work order, repository grant,
or authority to execute. Existing `objective.submit`, `assignment.create`, the
Engineering pipeline, and independent verification remain the execution boundary.
CME observes continuity; it does not authorize proposals or dispatch work.

## Initial API contract (backend; website integration belongs to Codex 2)

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
- `GET /api/v1/institutional-proposals/{proposal_id}` retrieves a proposal,
  selected/current revision, revision-bound reviews, and lifecycle events.

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

Lifecycle transitions are checked in the registry. Steward approval is attached
to a specific current revision and defined purpose. A later material revision
returns to `DRAFT`; prior reviews remain attached to their historical revision
and do not carry forward. The low-level registry records a verified caller's
review/decision but does not itself confer authority; future HTTP approval and
work-order linkage must call existing AuthorityRegistry and objective-intake
checks before changing the proposal state or linking execution.

Resident review records identify office, principal, revision, outcome, findings,
conditions, evidence, authority reference, and idempotency key. The schema can
record future Security, Legal, HR/Resources, and Operations reviews. No uncommissioned
resident is activated or represented as having reviewed a proposal.

Privacy classification and retention are metadata in this increment. The current
proposal reasoning path is limited to the locally configured bound 80B; external
provider selection, local-only enforcement across future providers, and retention
jobs remain unimplemented and must be resolved before those providers/policies are
commissioned.

## Current phase and next integration

This increment provides durable drafts, text/tag retrieval, immutable revisions,
review contracts, and backend endpoints. The frontend controls and proposal-to-
work-order authorization transaction are interface work for a follow-on integration
with Codex 2's PR #42. Work-order creation must require `READY_FOR_STEWARD_DECISION`
then an authenticated exact-grant decision on the named revision and purpose, and
must converge on the existing objective intake pipeline. Conversational commands
must resolve an unambiguous approved proposal revision and invoke that same
operation. Codex/worker orchestration remains the existing PR #62/#63 path.
