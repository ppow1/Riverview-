<!-- Riverview~ Controlled Document
File: docs/development/RESIDENT_LEARNING_FOUNDATION_ASSESSMENT_20261018.md
Component: RESIDENT-LEARNING
File Revision: 1.0.0
Purpose: Record existing shared learning foundations, verified gaps, and safe implementation boundary
Execution Model: N/A, repository assessment
Observability: Findings linked to current contracts and focused regression tests
Dependencies: Existing resident knowledge, proposal lifecycle, authority registry, permission profiles
Authority: Assessment only; introduces no learning authority, store, grant, or production action
Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-001 | Initial capability and gap assessment
Contracts: docs/architecture/INSTITUTIONAL_LEARNING_AND_RESOURCE_CAPABILITY_ROADMAP.md
Tests: Existing focused knowledge and proposal test evidence recorded below
History: Git; no predecessor (new file)
-->

# Resident learning foundation assessment

**Task:** RV-RESIDENT-LEARNING-001
**Scope:** Shared infrastructure usable by any resident; no Grace-only knowledge authority.

## Existing capabilities

| Capability | Existing implementation | Boundary |
|---|---|---|
| Bounded source retrieval | `RepositoryKnowledgeProvider` and `TaskRelevantRepositoryKnowledgeProvider` | Reads commit-pinned repository sources and returns typed status, source references, revision, and SHA-256. It is read-only; `record_learning` returns `UNAVAILABLE`. |
| Worker lookup evidence | `knowledge_observations` migration | Records lookup/preflight status and provenance against an assignment and worker. It is not a general resident fact store and does not hold retrieved source text. |
| Resident reasoning | `ResidentReasoner` and office-state plans | Regrounds work and stores bounded plans/outcomes. This is not a verified cross-session learning API. |
| Candidate material and review | Institutional proposal registry and lifecycle | Persists immutable revisions, source references, provenance, review outcomes, Steward decisions, rejection, and supersession. Approval is purpose- and revision-bound. |
| Execution authorization | Institutional authority registry and resident permission profiles | Keeps identity, office, grants, resource scope, and approval authority in the existing authority system. A proposal does not grant execution authority. |

## Disconnected or missing lifecycle links

The repository currently has useful parts of the requested lifecycle, but no commissioned path joins them into resident learning:

1. Assignment observations and verified repository retrieval do not create candidate knowledge records.
2. Proposal records can hold candidate material and provenance, but their current HTTP API is authenticated Steward-only and is intended for institutional planning and Engineering intake. It is not a resident-scoped knowledge API.
3. No registered learning actions define which resident can propose, read, validate, approve, share, or correct resident knowledge. Permission profiles fail closed when separate approval is required; there is no learning grant to reuse.
4. No retrieval contract enforces `resident:<principal>` isolation while allowing separately approved institutional knowledge. Proposal search is not such a contract.
5. There is no typed evidence-to-candidate link or knowledge-specific validation authority. Proposal source references and review evidence are useful primitives, not proof that a candidate is true.
6. Existing proposal revision and supersession history can inform correction handling, but it does not by itself define correction semantics for approved reusable knowledge.

The existing `PL-0016` reference in the learning roadmap has no matching source document in this checkout, so this assessment cannot claim conformance to it.

## Verification performed

Command, with `PYTHONPATH=src`:

```text
python -m unittest tests.test_resident_knowledge tests.test_repository_knowledge tests.test_institutional_proposals tests.test_proposal_work_order_lifecycle -v
```

Result: 28 tests run, 14 passed, 14 skipped, 0 failures. All resident-knowledge and repository-provider tests passed, including complete provenance, bounded retrieval, pinned-source verification, and explicit learning-write unavailability. The explicit proposal-command parser test passed. Fourteen proposal registry/lifecycle tests were skipped because `RIVERVIEW_TEST_PG_DSN` is not configured. Therefore rejection, supersession, provenance persistence, and database-backed access behavior were not re-exercised in this checkout. No resident-isolation or shared-learning permission test exists in the inspected focused suites.

A prior invocation without `PYTHONPATH=src` failed to import the package; it is not counted as verification. No database, credentials, services, resident data, or central conversation/reasoning adapters were changed.

## Safe next implementation boundary

Do not make a new learning store or treat proposal search as resident knowledge retrieval. A future bounded integration should extend the existing typed knowledge-provider interface and proposal/evidence lifecycle only after the institution defines and approves:

- stable resident and institutional scope identifiers;
- exact propose/read/validate/approve/correct/share actions and their grant owners;
- which independent validation evidence is sufficient for each knowledge type;
- retrieval filtering across resident-private, approved institutional, and restricted material;
- approved-knowledge correction/supersession semantics and audit events.

Once that contract exists, add an adapter that records source and validation provenance through the existing owner, checks its exact authority on every read/write, and remains fail-closed for missing or stale authority. Add disposable-PostgreSQL tests for cross-resident denial, approved shared access, rejection, correction/supersession, and provenance before registering or commissioning it.

**Outcome:** Inventory and architecture assessment complete. A resident-wide implementation is not safe to claim or commission from the current contracts. This change is assessment-only and does not complete the requested implementation.
