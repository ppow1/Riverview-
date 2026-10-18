# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/INSTITUTIONAL_PROPOSALS_FLOW.md
# Component: INSTITUTIONAL-PROPOSALS
# Revision: 1.1.0
# Purpose: Troubleshoot proposal formalization, persistence, search, and review flow
# Status: Development contract; production acceptance not performed
# Authority: Steward retains proposal decision and execution authorization
# Dependencies: PostgreSQL proposal registry; authenticated Grace conversation
# Changed: 2026-10-16 UTC | RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001 | Initial proposal flow
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Extend proposal decisions into existing authorized Engineering lifecycle
# Source: process_graphs/grace/institutional-proposal-lifecycle.json
# Verification: python3 scripts/process_graph.py check; tests/test_institutional_proposals.py; tests/test_proposal_work_order_lifecycle.py
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
    g_rv_grace_institutional_proposal_lifecycle_steward_decision_56f0e6c6{"Authenticated Steward decides an exact current content digest and revision for a stated purpose; approval is not execution authorization"}
    g_rv_grace_institutional_proposal_lifecycle_provider_failure_6e66d82b[["Provider unavailable, non-80B, incomplete, provisional, malformed, or binding changed: do not persist an executable proposal"]]
    g_rv_grace_institutional_proposal_lifecycle_idempotent_recovery_0e763a7f["Retry returns the same saved draft only for matching principal, conversation, and selected source sequence set"]
    g_rv_grace_institutional_proposal_lifecycle_proposal_ready_3603d90f(["Draft remains independently searchable and reviewable; only an authenticated exact-revision decision can set approval"])
    g_rv_grace_institutional_proposal_lifecycle_decision_eligibility_67ec26c6["Recheck Steward session, current proposal revision and content digest; reject stale, blocked, expired, or unresolved conditional reviews"]
    g_rv_grace_institutional_proposal_lifecycle_promotion_authority_f023dfd6["Check current approved revision and exact objective.submit grant before reserving work-order intake"]
    g_rv_grace_institutional_proposal_lifecycle_objective_intake_e519020e["Submit or recover one deterministic existing pipeline objective with immutable proposal revision, approval, grant, source, privacy, retention, purpose, and criteria provenance"]
    g_rv_grace_institutional_proposal_lifecycle_dispatch_verification_125e3873["Existing Grace/CME service performs separately authorized assignment dispatch, worker execution, independent verification, and durable proposal linkage"]
    g_rv_grace_institutional_proposal_lifecycle_missing_authority_0d73e08c[["Missing objective.submit prevents promotion; missing assignment.create is surfaced from dispatch diagnostics while approval remains durable"]]
    g_rv_grace_institutional_proposal_lifecycle_promotion_retry_6a2109e7["Retry deterministic objective intake after service restart only after validating actor, proposal digest, criteria, grant, source and approval event; do not duplicate objective or assignment"]
    g_rv_grace_institutional_proposal_lifecycle_verified_result_5a07306c(["Worker, verification, artifacts and outcomes are durably linked to the exact approved proposal revision; verification is not Steward acceptance"])
    g_rv_grace_institutional_proposal_lifecycle_steward_website_ui_e4e19bf8["Steward dashboard exposes proposal drafting, revision review, exact-revision decision, and promotion controls through authenticated existing API routes; proposal approval and objective submission remain separate grants"]
  end
  g_rv_grace_institutional_proposal_lifecycle_authorize_and_bind_335cfb84 --> g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869
  g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869 -->|typed proposal| g_rv_grace_institutional_proposal_lifecycle_persist_draft_1089ff46
  g_rv_grace_institutional_proposal_lifecycle_persist_draft_1089ff46 --> g_rv_grace_institutional_proposal_lifecycle_search_revise_review_a47d8d46
  g_rv_grace_institutional_proposal_lifecycle_search_revise_review_a47d8d46 --> g_rv_grace_institutional_proposal_lifecycle_steward_decision_56f0e6c6
  g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869 -->|diagnostic_branch: required capability or response contract fails| g_rv_grace_institutional_proposal_lifecycle_provider_failure_6e66d82b
  g_rv_grace_institutional_proposal_lifecycle_provider_failure_6e66d82b -->|recovery_route| g_rv_grace_institutional_proposal_lifecycle_idempotent_recovery_0e763a7f
  g_rv_grace_institutional_proposal_lifecycle_idempotent_recovery_0e763a7f -->|retry same request only| g_rv_grace_institutional_proposal_lifecycle_reason_or_clarify_951aa869
  g_rv_grace_institutional_proposal_lifecycle_steward_decision_56f0e6c6 -->|decision belongs to exact revision and purpose| g_rv_grace_institutional_proposal_lifecycle_proposal_ready_3603d90f
  g_rv_grace_institutional_proposal_lifecycle_steward_decision_56f0e6c6 --> g_rv_grace_institutional_proposal_lifecycle_decision_eligibility_67ec26c6
  g_rv_grace_institutional_proposal_lifecycle_decision_eligibility_67ec26c6 -->|revision-bound APPROVE, REQUEST_CHANGES, DEFER, or REJECT is appended| g_rv_grace_institutional_proposal_lifecycle_proposal_ready_3603d90f
  g_rv_grace_institutional_proposal_lifecycle_proposal_ready_3603d90f -->|separate explicit promotion request| g_rv_grace_institutional_proposal_lifecycle_promotion_authority_f023dfd6
  g_rv_grace_institutional_proposal_lifecycle_promotion_authority_f023dfd6 -->|exact objective.submit grant passes| g_rv_grace_institutional_proposal_lifecycle_objective_intake_e519020e
  g_rv_grace_institutional_proposal_lifecycle_promotion_authority_f023dfd6 -->|escalation: missing or denied objective.submit| g_rv_grace_institutional_proposal_lifecycle_missing_authority_0d73e08c
  g_rv_grace_institutional_proposal_lifecycle_objective_intake_e519020e -->|grounding and existing Grace execution continue from durable objective state| g_rv_grace_institutional_proposal_lifecycle_dispatch_verification_125e3873
  g_rv_grace_institutional_proposal_lifecycle_dispatch_verification_125e3873 -->|verification: worker completion is independently verified and linked to approved revision| g_rv_grace_institutional_proposal_lifecycle_verified_result_5a07306c
  g_rv_grace_institutional_proposal_lifecycle_dispatch_verification_125e3873 -->|escalation: assignment.create denied; approval and proposal history remain unchanged| g_rv_grace_institutional_proposal_lifecycle_missing_authority_0d73e08c
  g_rv_grace_institutional_proposal_lifecycle_objective_intake_e519020e -->|diagnostic_branch: interrupted intake or evidence grounding| g_rv_grace_institutional_proposal_lifecycle_promotion_retry_6a2109e7
  g_rv_grace_institutional_proposal_lifecycle_promotion_retry_6a2109e7 -->|recovery_route: idempotent recovery after exact authority recheck| g_rv_grace_institutional_proposal_lifecycle_objective_intake_e519020e
  g_rv_grace_institutional_proposal_lifecycle_steward_website_ui_e4e19bf8 --> g_rv_grace_institutional_proposal_lifecycle_authorize_and_bind_335cfb84
  g_rv_grace_institutional_proposal_lifecycle_steward_source_2126342a --> g_rv_grace_institutional_proposal_lifecycle_steward_website_ui_e4e19bf8
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

## Troubleshooting checkpoints

- `resident_conversation_not_authorized`: verify the authenticated Steward owns the conversation and retains exact `resident.conversation.read` and `resident.conversation.send` grants for Grace's office.
- `proposal_drafting_unavailable`: verify the active binding still matches the configured provider digest, the bound provider is 80B-capable, generation ended normally, and the strict proposal contract was returned. The API does not silently use the 0.6B fallback for substantive proposal drafting.
- `proposal_idempotency_conflict`: preserve the existing record. Confirm the original proposal key was not reused for another principal, conversation, source message set, or content.
- Empty search results mean no matching current non-archived proposal was found. No synthetic proposal is generated by retrieval.
- A proposal in `DRAFT`, `READY_FOR_REVIEW`, or `UNDER_REVIEW` cannot be treated as a work order. Current objective intake and exact grants remain independently enforced.
- Approval requires `READY_FOR_STEWARD_DECISION`, exact revision/digest and explicit purpose; generic transition cannot approve, defer, reject, or request changes.
- Plain agreement in chat has no authorization effect. The conversational command contract requires an authenticated persisted message that names proposal ID and revision; promotion names the same exact revision.
- Promotion checks `objective.submit` before reserving intake and then calls the same `GraceExecutionPipeline.submit_objective`; it creates no assignment. The existing persistent Grace execution service later applies `assignment.create`.
- Repeated promotion rechecks the grant and validates immutable proposal reference, source references, criteria, actor and objective state before reusing the deterministic objective identity.
- The execution-service reconciliation links actual assignments and sanitized worker/verifier evidence to the proposal revision. A worker success without an independent verifier record is not represented as accepted.
