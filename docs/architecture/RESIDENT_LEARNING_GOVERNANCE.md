<!-- Riverview~ Controlled Document
File: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md
Component: RESIDENT-LEARNING-GOVERNANCE
Document Revision: 1.5.0
Purpose: Define resident-wide learning retention, evidence, authority, sharing, correction, and rollback rules
Execution Model: Dormant request-driven library and additive schema; no runtime route or grants commissioned
Observability: Versioned records and append-only decision/correction event references when implemented
Dependencies: AuthorityRegistry; resident permission profiles; existing knowledge and proposal contracts
Authority: Grants no permission; all access remains subject to existing exact grants and approved profiles
Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-GOVERNANCE-001 | Initial resident-wide governance contract
Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-GOVERNANCE-001 | Clarify schema authority limits and prohibit local-only institutional sharing
Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-IMPLEMENTATION-001 | Document dormant lifecycle API, authorization adapter, storage schema, and rollback
Changed: 2026-10-18 UTC | RV-W2-LEARNING-ADAPTER-001 | Document the dormant resident binding adapter and exact identity handoff
Changed: 2026-10-18 UTC | RV-W2-PG16-QUALIFICATION-001 | Record focused scope/authority regressions and successful exact-head PostgreSQL 16 controlled checkout
Changed: 2026-10-18 UTC | RV-W2-DOD-001 | Add implementer cookbook, focused failure recovery contract, and explicit unresolved-authority blockers
Contracts: docs/components/RESIDENT_PERMISSION_PROFILES.md; docs/components/RESIDENT_REASONING.md; docs/components/INSTITUTIONAL_PROPOSALS.md; docs/components/RESIDENT_LEARNING_COOKBOOK.md; docs/components/RESIDENT_LEARNING_FLOW.md
Tests: tests/test_resident_learning_contract.py
History: Git; new file
-->

# Resident-wide learning governance contract

**Status:** Governance contract plus dormant source implementation. No runtime route, learning grant, production migration, or automatic extractor is enabled. The service requires an injected authorization adapter and is not wired into resident execution.

## 1. Scope and identity

This policy applies consistently to every active resident principal. Each record has one immutable origin resident and an explicit retrieval scope: `resident:<principal>` or `institution:riverview`. The current authenticated principal and existing authority decision determine which records may be read or changed. Office title, model identity, profile tier, capability registration, conversation participation, and prior access to a source never substitute for an exact permission.

Grace is the Director of Operations. Her role context explicitly grants no permission, and her proposed `institutional_administrator` onboarding tier is not active. This policy gives Grace no special learning authority. The checked out source contains no Evelyn resident, office, or implementation, so this contract makes no claim about Evelyn's identity or authority. The same rules apply if and when any resident is registered.

## 2. Automatic learning and retention

Residents and their reasoning implementations may automatically:

- use information in the current request and authorized conversation context to answer that request;
- retrieve and use source material through an existing authorized, provenance-bearing provider, while preserving its `VERIFIED`, `UNVERIFIED`, `INCOMPLETE`, `NO_MATCH`, or `UNAVAILABLE` status; and
- record operational observations only in the existing component ledger that owns those observations, under that component's existing purpose, access, and retention contract.

These operations do not create a verified fact, a reusable cross-session memory, or an institutional record. A conversation transcript remains conversation history, not independent evidence that its claims are true. Model output, resident inference, worker self-report, and repeated mention are never sufficient to promote a claim.

The new library can persist candidates only when a caller supplies an authorization adapter that returns a matching exact allow receipt. It does not register grant mappings or infer authority. No production caller is wired. Durable resident-private preferences or facts require explicit resident confirmation, a suitable retention policy, and an already-authorized exact write scope. Durable institutional knowledge requires evidence, independent validation, and Steward approval as below.

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

The source exposes a Python capability but registers no grant, profile, endpoint, background process, or production table. Its `AuthorizationPort.require(principal_id, operation, scope_ref)` must be adapted to owner-approved exact-grant checks and fail closed. The returned receipt must bind the same principal and include grant and authority references. No operation-to-grant mappings are supplied; integrating owners must provide them without broadening authority. The additive migration creates append-only candidate, revision, and event tables and includes no privilege grants. It must be applied only to an explicitly isolated database until separately reviewed and commissioned.

## 7. Uniform resident application and isolation

Use the same lifecycle, evidence minimums, retention ceiling, decision meanings, and correction rules for all residents. A resident's office may determine which already-authorized source is authoritative for a fact; it does not make that resident's private records visible to others or silently confer validation/approval powers. `resident:<principal>` data is invisible outside that principal unless a separately authorized disclosure is recorded. `institution:riverview` data is readable only when the caller's current exact grants, active profile (if applicable), classification, export mode, and approved purpose permit it.

No default cross-resident retrieval, implicit sharing by office, identity inference from names, or fallback from a denied private lookup to a shared lookup is allowed. Retrieval results must identify the applied scope and preserve source/status provenance. Unknown identity or scope, missing profile-required approval, and authority-store errors deny access.

## 8. Lifecycle and implementation boundary

```text
observation/source -> evidence-bearing candidate -> independent validation
                   -> authorized revision-bound approval -> scoped retrieval/use
                   -> append-only correction/supersession or rollback event
```

The JSON Schema at `docs/schemas/resident-learning-record.schema.json` describes the non-authorizing record envelope. It cannot verify caller identity, exact grants, cross-field scope/digest equality, approval signatures, evidence truth, retention jobs, or database isolation. A `local_only` classification cannot be used for institutional scope. `ResidentLearningService` separates candidate creation, independent validation, private confirmation, Steward approval, rejection, scoped retrieval, correction, supersession, and rollback. Each operation records its authority receipt and event reference; retrieval lists only currently approved records in the exact requested scope. Corrections create a new candidate and supersede the previous approval; approval does not transfer. Rollback appends restoration and supersession events and requires fresh supported evidence plus authorization. Records and event rows reject update/delete at the database layer.

The library takes evidence references from its caller and never treats generated text as verified evidence. Candidate and validation evidence must reference existing source or observation records; observations remain owned by their existing components. Request-local context is not persisted by this library. A separate retention/purge operation has not been implemented; bounded retention is recorded but enforcement requires an owner-approved retention service before deployment.

The dormant `ResidentLearningAdapter` is the boundary for a resident-facing caller. Its binding callback must perform the existing authenticated office lookup for each call (for Grace this is `AuthorityRegistry.authorize_office_state`); the adapter validates resident principal kind, principal ID, occupant, and binding revision. It derives the principal from that snapshot instead of accepting a principal string from a model or request body. It exposes candidate creation in the caller's own private scope or institutional candidate scope, and approved retrieval in those same scopes. It has no validation or approval method. The `ResidentLearningService` still checks exact operation/scope authorization through its injected port, and no action-to-grant map is bundled.

Example construction (both the exact authorization adapter and current binding callback are mandatory and supplied by the integrating authority owner):

```python
store = PostgresResidentLearningStore(dsn, schema="isolated_learning_test")
learning = ResidentLearningService(store, existing_exact_grant_adapter)
resident_learning = ResidentLearningAdapter(
    learning,
    lambda: authority_registry.authorize_office_state(resident_credential, office_id),
)
candidate = resident_learning.create_candidate(
    content=content,
    evidence=evidence_references,
    provenance=provenance,
    classification=classification,
    retention="bounded_durable",
    idempotency_key=request_id,
)
approved_knowledge = resident_learning.retrieve()
```

The example is an integration contract only. No runner, conversation server, Grace reasoning provider, or resident service constructs this adapter in the current change. A later caller must provide the current registry binding and exact-grant authorization callback, then receive its own runtime and authority review before wiring.

Rollback is an append-only decision, not deletion. In an isolated test schema, close the store, preserve the audit evidence, then drop only the uniquely named test schema created by that test. Do not run the learning migration against production or delete learning rows to simulate rollback. For an already commissioned store, use the authorized rollback API with the exact record/replacement IDs, expected revision, fresh independent evidence, and current authority; the prior fact becomes retrievable only if this decision succeeds. Data purge remains subject to the separate retention owner and policy.

Unit tests cover adapter identity/provenance rejection, mismatched authorization receipts, resident denial at the Steward approval boundary, scope isolation, denied writes/sharing, validation, rejection, correction, rollback, and service resumption using an in-memory store. The PostgreSQL integration test creates and drops a unique schema only when `RIVERVIEW_TEST_PG_DSN` points to an explicitly disposable database. It passed against a fresh local PostgreSQL 18 cluster, including restart retrieval, scope filtering, and append-only trigger checks.

For the implementer walkthrough, isolated diagnosis, exact backup verification, and safe restoration procedure, see [`RESIDENT_LEARNING_COOKBOOK.md`](../components/RESIDENT_LEARNING_COOKBOOK.md). The generated [lifecycle flow](../components/RESIDENT_LEARNING_FLOW.md) records denied authorization/evidence, rejection, store outage, read-only diagnosis, and authorized recovery routes. Errors remain fail-closed; a store outage never authorizes a broader retry or promotion.

### Unresolved integration blockers

This code intentionally does not define grant-to-operation mappings, a real Steward principal, private retention authority, or a retention/purge owner. The repository provides no approved authority input from which to derive those values. Do not guess them. Until the responsible authority owners register exact grants and approve an integration, the injected authorization and identity binding adapters remain mandatory, no runtime caller may wire this service, and no institutional or private durable-write permission exists by implication. The source contracts and tests establish isolated software behavior only; they do not establish operational approval or deployment readiness.
**PostgreSQL 16 compatibility: VERIFIED on 2026-10-18.** Controlled checkout run [39145862119](https://github.com/ppow1/Riverview-/actions/runs/39145862119) executed commit `5a99c034fae4690db64611f6e77fc6a3df1da230` using the workflow's ephemeral PostgreSQL 16 service. The complete suite ran **639 tests (4 skipped, 0 failures)**; `test_persist_and_resume_approved_shared_record` passed against PG16. Process graphs passed (23 graphs / 570 nodes), and controlled revision/predecessor verification passed. To repeat the full qualification, run the existing `Controlled checkout` workflow with `workflow_dispatch` on the candidate ref; it sets `RIVERVIEW_TEST_PG_DSN=postgresql://riverview_test@127.0.0.1:5432/riverview_test` and invokes `python -m unittest discover -s tests -v`. To run only the learning persistence test in that same disposable job, use `PYTHONPATH=src python -m unittest tests.test_resident_learning_postgres -v`. The job is read-only and uses only its ephemeral service database. No runtime use is commissioned by these tests.
