# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/operations/INSTITUTIONAL_PROPOSAL_AUTHORING.md
# Component: INSTITUTIONAL-PROPOSAL-AUTHORING
# Revision: 1.0.0
# Purpose: Guide an AI in preparing Steward-requested institutional proposals
# Status: Operational guidance
# Authority: Proposal registry contract; Steward retains proposal and execution authority
# Dependencies: docs/components/INSTITUTIONAL_PROPOSALS.md; authenticated Steward registry interface
# Changed: 2026-10-16 UTC | RV-PROPOSAL-AUTHORING-GUIDANCE | Add concise source-to-proposal workflow
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================

## When to use this playbook

Use this procedure only when the Steward asks to preserve, register, revise, or
review an idea as an institutional proposal. First read
[`INSTITUTIONAL_PROPOSALS.md`](../components/INSTITUTIONAL_PROPOSALS.md), which
defines the authoritative fields, API, revision rules, and authority boundary.
This playbook explains how to prepare source material; it does not replace that
contract.

## Prepare the proposal content

1. Identify the Steward-selected conversation messages, research documents, and
   other sources. Keep their stable references (conversation ID and message
   sequences, document title and URL or repository path, and relevant date or
   version). Do not cite material that was not actually consulted.
2. Draft each required content field from that material: `title` names the idea;
   `summary` states it briefly; `objective` describes the intended outcome;
   `scope` bounds included work; `proposed_approach` describes a plausible
   route; `constraints` records limits and dependencies; `acceptance_criteria`
   describes observable completion; and `tags` supplies concise search terms.
3. Separate source facts, Steward decisions, and AI-generated synthesis. Preserve
   quotations and attribution where needed. Mark uncertainty and missing evidence
   explicitly; do not invent facts, citations, approval, or implementation details.
4. Carry source references into the registry's separate `source_references`
   parameter. Provenance is assigned by the trusted server from the authenticated
   Steward and selected source messages; never fabricate or submit actor,
   authority, or provenance fields.
5. Check the complete payload against the field limits and validation rules in
   the component contract. If required content is absent or ambiguous, ask the
   Steward for clarification instead of filling the gap by assumption.

## Save, revise, and review

Use only the authorized registry interface documented by the component contract
and only with an authenticated Steward session. For conversation formalization,
submit explicitly selected persisted Steward message sequences and a stable
idempotency key as specified. Check the returned validation result and persisted
revision; a validation error or `clarification_required` result is not a saved
proposal. On retry, reuse the same idempotency key and request. Revise through
the defined revision operation, preserve applicable source references, and
verify the new immutable revision and content digest. Review decisions must name
the exact current revision and follow the contract's explicit decision fields.

If the interface or required backend contract is unavailable, prepare a clearly
labelled draft for Steward review and report that it has not been registered.
Never claim that drafting, saving, or reviewing authorizes execution. Proposal
approval and Engineering work-order promotion are separate, explicit actions;
execution still requires the existing authorization checks.

## Completion note

Report the proposal ID and revision only after the registry confirms persistence.
Otherwise report the draft status, missing information or interface, and source
references so the Steward can decide the next step.
