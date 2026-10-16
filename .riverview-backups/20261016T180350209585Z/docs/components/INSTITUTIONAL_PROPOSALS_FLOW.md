# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/INSTITUTIONAL_PROPOSALS_FLOW.md
# Component: INSTITUTIONAL-PROPOSALS
# Revision: 1.0.0
# Purpose: Troubleshoot proposal formalization, persistence, search, and review flow
# Status: Development contract; production acceptance not performed
# Authority: Steward retains proposal decision and execution authorization
# Dependencies: PostgreSQL proposal registry; authenticated Grace conversation
# Changed: 2026-10-16 UTC | RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001 | Initial proposal flow
# Source: process_graphs/grace/institutional-proposal-lifecycle.json
# Verification: python3 scripts/process_graph.py check; tests/test_institutional_proposals.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================

## Workflow

```mermaid
flowchart LR
  subgraph g_rv_grace_institutional_proposal_lifecycle["INSTITUTIONAL-PROPOSALS / institutional-proposal.v1"]
    g_rv_grace_institutional_proposal_lifecycle_steward_source_2126342a(["Authenticated Steward selects persisted conversation messages for proposal formalization"])
    g_rv_grace_institutional_proposal_lifecycle_authorize_and_bind_335cfb84["Recheck Steward account role, conversation read/send grants, owner, source messages, and current model binding"]
    g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869{"Bound 80B returns typed proposal content or a material clarification; missing execution grants do not block planning"}
    g_rv_grace_institutional_proposal_lifecycle_persist_draft_1089ff46["Persist idempotent DRAFT proposal revision, source provenance, model provenance, privacy, retention, and tags"]
    g_rv_grace_institutional_proposal_lifecycle_search_revise_review_a47d8d46["Steward searches, retrieves, revises under compare-and-swap, and records reviews against exact revisions"]
    g_rv_grace_institutional_proposal_lifecycle_steward_decision_56f0e6c6{"Steward may decide an exact current revision for a stated purpose; proposal approval alone does not dispatch work"}
    g_rv_grace_institutional_proposal_lifecycle_provider_failure_6e66d82b[["Provider unavailable, non-80B, incomplete, provisional, malformed, or binding changed: do not persist an executable proposal"]]
    g_rv_grace_institutional_proposal_lifecycle_idempotent_recovery_0e763a7f["Retry returns the same saved draft only for matching principal, conversation, and selected source sequence set"]
    g_rv_grace_institutional_proposal_lifecycle_proposal_ready_3603d90f(["Draft is searchable and reviewable; separate authorized proposal-to-work-order transaction remains a later integration"])
  end
  g_rv_grace_institutional_proposal_lifecycle_steward_source_2126342a --> g_rv_grace_institutional_proposal_lifecycle_authorize_and_bind_335cfb84
  g_rv_grace_institutional_proposal_lifecycle_authorize_and_bind_335cfb84 --> g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869
  g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869 -->|typed proposal| g_rv_grace_institutional_proposal_lifecycle_persist_draft_1089ff46
  g_rv_grace_institutional_proposal_lifecycle_persist_draft_1089ff46 --> g_rv_grace_institutional_proposal_lifecycle_search_revise_review_a47d8d46
  g_rv_grace_institutional_proposal_lifecycle_search_revise_review_a47d8d46 --> g_rv_grace_institutional_proposal_lifecycle_steward_decision_56f0e6c6
  g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869 -->|diagnostic_branch: required capability or response contract fails| g_rv_grace_institutional_proposal_lifecycle_provider_failure_6e66d82b
  g_rv_grace_institutional_proposal_lifecycle_provider_failure_6e66d82b -->|recovery_route| g_rv_grace_institutional_proposal_lifecycle_idempotent_recovery_0e763a7f
  g_rv_grace_institutional_proposal_lifecycle_idempotent_recovery_0e763a7f -->|retry same request only| g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869
  g_rv_grace_institutional_proposal_lifecycle_steward_decision_56f0e6c6 -->|decision belongs to exact revision and purpose| g_rv_grace_institutional_proposal_lifecycle_proposal_ready_3603d90f
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

## Troubleshooting checkpoints

- `resident_conversation_not_authorized`: verify the authenticated Steward owns the conversation and retains exact `resident.conversation.read` and `resident.conversation.send` grants for Grace's office.
- `proposal_drafting_unavailable`: verify the active binding still matches the configured provider digest, the bound provider is 80B-capable, generation ended normally, and the strict proposal contract was returned. The API does not silently use the 0.6B fallback for substantive proposal drafting.
- `proposal_idempotency_conflict`: preserve the existing record. Confirm the original proposal key was not reused for another principal, conversation, source message set, or content.
- Empty search results mean no matching current non-archived proposal was found. No synthetic proposal is generated by retrieval.
- A proposal in `DRAFT`, `READY_FOR_REVIEW`, or `UNDER_REVIEW` cannot be treated as a work order. Current objective intake and exact grants remain independently enforced.
