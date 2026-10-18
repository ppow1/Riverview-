<!-- Riverview~ Controlled Document
File: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md
Component: RESIDENT-LEARNING-GOVERNANCE
Document Revision: 1.0.0
Purpose: Define resident-wide learning retention, evidence, authority, sharing, correction, and rollback rules
Execution Model: Governance contract only; no runtime learning workflow is commissioned
Observability: Versioned records and append-only decision/correction event references when implemented
Dependencies: AuthorityRegistry; resident permission profiles; existing knowledge and proposal contracts
Authority: Grants no permission; all access remains subject to existing exact grants and approved profiles
Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-GOVERNANCE-001 | Initial resident-wide governance contract
Contracts: docs/components/RESIDENT_PERMISSION_PROFILES.md; docs/components/RESIDENT_REASONING.md; docs/components/INSTITUTIONAL_PROPOSALS.md
Tests: tests/test_resident_learning_contract.py
History: Git; new file
-->

# Resident-wide learning governance contract

**Status:** Proposed governance contract; documentation and schema only. No learning store, automatic extractor, grant, profile, or runtime route is enabled by this change.

## 1. Scope and identity

This policy applies consistently to every active resident principal. Each record has one immutable origin resident and an explicit retrieval scope: `resident:<principal>` or `institution:riverview`. The current authenticated principal and existing authority decision determine which records may be read or changed. Office title, model identity, profile tier, capability registration, conversation participation, and prior access to a source never substitute for an exact permission.

Grace is the Director of Operations. Her role context explicitly grants no permission, and her proposed `institutional_administrator` onboarding tier is not active. This policy gives Grace no special learning authority. The checked out source contains no Evelyn resident, office, or implementation, so this contract makes no claim about Evelyn's identity or authority. The same rules apply if and when any resident is registered.

## 2. Automatic learning and retention

Residents and their reasoning implementations may automatically:

- use information in the current request and authorized conversation context to answer that request;
- retrieve and use source material through an existing authorized, provenance-bearing provider, while preserving its `VERIFIED`, `UNVERIFIED`, `INCOMPLETE`, `NO_MATCH`, or `UNAVAILABLE` status; and
- record operational observations only in the existing component ledger that owns those observations, under that component's existing purpose, access, and retention contract.

These operations do not create a verified fact, a reusable cross-session memory, or an institutional record. A conversation transcript remains conversation history, not independent evidence that its claims are true. Model output, resident inference, worker self-report, and repeated mention are never sufficient to promote a claim.

No resident may currently create a new durable personal-learning or shared-learning record through this contract. Durable resident-private preferences or facts require an explicit resident confirmation, a suitable existing store and retention policy, and an already-authorized exact write scope. Durable cross-resident or institution-wide knowledge requires the approval and evidence gates below. No such learning-specific capability or exact grant is registered by this change.

## 3. Candidate, validation, and approval gates

| Record/use | Minimum gate |
|---|---|
| Request-local working context | Existing conversation/request access; ends with that context and follows the conversation owner's retention policy. It is not retrievable as verified knowledge. |
| Authorized operational observation | Existing owner component may persist its typed observation under its current exact grants, provenance, and lifecycle. It remains an observation with time/freshness, not a general fact. |
| Resident-private durable preference explicitly stated by that resident | Explicit confirmation tied to the resident principal, source event, content digest, retention period, and the existing exact write grant and active profile allow. A model's interpretation alone is insufficient. |
| Resident-private factual claim intended for reuse | Candidate evidence record plus validation by an authorized source owner or independent reviewer. The resident's statement may prove only that the resident stated it. |
| Institutional/shared durable knowledge | Candidate evidence record; validation by the authoritative owner of the fact or a qualified independent reviewer; review for privacy/classification; and explicit Steward approval of the exact content revision, sharing scope, purpose, and retention. |
| Policy, identity, authority, safety, or resident-rights claim | Authoritative owner validation and explicit Steward decision; apply any required Security/Legal/HR review only when those offices and their grants are commissioned. No absent reviewer is presumed. |
| Execution, access, or resource action | The established action-specific exact grant and existing governed workflow. Learning approval never substitutes for action authorization. |

Approval is revision-bound. Any material content, evidence, classification, purpose, or sharing change invalidates the prior approval for use; the revised candidate returns to validation and approval. Rejection keeps the candidate out of factual retrieval. Deferral or missing evidence also keeps it out of factual retrieval. A record can be used only after all gates for its scope and classification pass on each read.

## 4. Evidence and provenance

A candidate record must retain:

- stable record ID, originating resident principal, exact scope, classification, retention rule, lifecycle status, and content digest;
- one or more source references, captured time, source type, and source digest or immutable revision where available;
- method and recorder/provider identity, implementation revision, and a clear indication whether content is a direct observation, resident assertion, imported source, or model-generated interpretation;
- validation result, validator principal/owner, validation time, cited evidence, and the authority event that permits that validation; and
- for each approval/rejection, the exact record revision and digest, decision maker, decision time, purpose, scope, reason, and authoritative event reference.

Provenance is append-only. A digest proves byte identity, not truth. A `VERIFIED` provider result proves only its documented source-integrity contract; it does not automatically validate the truth of every statement in that source.

## 5. Correction, supersession, and rollback

A correction creates a new immutable revision/record and a correction event linked to the old record, replacement, reason, source evidence, actor, and time. The old record is marked superseded for current retrieval but remains in audit history subject to its approved retention and privacy obligations. A correction never silently edits the prior content or carries approval forward.

A false or unsafe shared fact must be withdrawn from current retrieval promptly through the existing authorized owner and decision workflow. Its replacement follows the full validation/Steward approval path. If an approved change must be rolled back, record a rollback event naming the failed revision and the prior approved revision; re-check that the prior revision's source, validity, classification, and approval remain current before restoring it for retrieval. Rollback is a new auditable decision, not deletion or time travel. Expired, revoked, stale, rejected, or superseded records fail closed. Any legally/policy-required purge must use a separate authorized retention operation and preserve a non-sensitive audit tombstone where permitted.

## 6. Permission versus capability

A **capability** describes an operation an implementation supports, such as `learning.candidate.record.v1` or `learning.knowledge.retrieve.v1`. Registration says the operation exists and identifies its owner/dependencies. It does not authorize a principal or establish readiness.

A **permission** is the existing exact, active `(principal, action, scope)` grant checked by AuthorityRegistry. Where a resident permission profile is active, its registered capability/resource allow and classification/export constraints further restrict that grant. Missing, expired, revoked, mismatched, approval-required-without-an-approval-path, or unavailable authority fails closed. Account role, Grace's title, a permission-profile tier, model response, proposal approval, and capability presence do not issue or widen a grant.

This contract registers no capability, resource binding, grant, profile, approval event, table, endpoint, or background process. It defines the gates a later implementation must meet and leaves all existing authority owners in place.

## 7. Uniform resident application and isolation

Use the same lifecycle, evidence minimums, retention ceiling, decision meanings, and correction rules for all residents. A resident's office may determine which already-authorized source is authoritative for a fact; it does not make that resident's private records visible to others or silently confer validation/approval powers. `resident:<principal>` data is invisible outside that principal unless a separately authorized disclosure is recorded. `institution:riverview` data is readable only when the caller's current exact grants, active profile (if applicable), classification, export mode, and approved purpose permit it.

No default cross-resident retrieval, implicit sharing by office, identity inference from names, or fallback from a denied private lookup to a shared lookup is allowed. Retrieval results must identify the applied scope and preserve source/status provenance. Unknown identity or scope, missing profile-required approval, and authority-store errors deny access.

## 8. Lifecycle and implementation boundary

```text
observation/source -> evidence-bearing candidate -> independent validation
                   -> authorized revision-bound approval -> scoped retrieval/use
                   -> append-only correction/supersession or rollback event
```

The JSON Schema at `docs/schemas/resident-learning-record.schema.json` describes the non-authorizing record envelope. It cannot verify caller identity, exact grants, approval signatures, evidence truth, retention jobs, or database isolation. Isolated tests in this change validate structural and policy invariants only. Before runtime implementation, add disposable-database tests for cross-resident denial, shared-scope approval, rejection, correction/supersession, provenance, retention, and rollback, then separately review/commission the storage and authorization changes.