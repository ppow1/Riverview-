<!-- RIVERVIEW~ CONTROLLED DOCUMENT
File Revision: 1.0.0
Component: JESSICA-CHARACTER-ARCHITECTURE-RECOVERY
Status: Recovery inventory and integration-ready dependency package; source recovery pending
Purpose: Record located Jessica evidence, classify current capabilities, and bound the next safe recovery step
Authority: Historical evidence is preserved; resident canon changes require the existing review and publication authority
-->

# Jessica character architecture recovery

**Inventory date:** 2026-10-18
**Repository baseline:** `dev/jessica-recovery` at `6e18ff8`
**Scope:** Repository and available sibling checkout evidence. This document does not claim access to the separate historical Estate repository, its database, or files absent from this checkout.

## Finding

The current Riverview checkout contains no Jessica character store, Jessica runtime, onboarding code, Jessica process graph, or Jessica-specific tests. The strongest direct evidence is a planning record preserved in Git commit `3c0714e8263df6321f320979108fdb9353da2db0` (its file is absent from the current tree): it calls for restoring Jessica as Chief Character Architect, preserving her doctrine/store/evidence/proposal/review/publication boundaries, reconnecting her conversational cognition to existing workflows, and reusing existing Jessica roadmaps and character-development workflow. That record says an older full-system review found the workflow partly implemented but disconnected from conversational cognition. The named source artifacts are not present here, so their implementation details cannot be verified or safely copied.

The same planning record sequences Jessica after the immediate Grace operational acceptance gates, model routing/context work, and governed learning work. Active PRs #113 and #114 change the central reasoning integration. Accordingly this recovery package is a documentation-only, integration-ready handoff. It makes no Grace prompt, resident record, reasoning pipeline, learning store, database, production, or process graph changes.

## Capability inventory

| Capability | Classification in this checkout | Evidence and boundary |
|---|---|---|
| Jessica's office as Chief Character Architect; professional doctrine and governance boundaries | **Specified only** | `GRACE_NEXT_STAGE_TEMPORARY_PLAN_2026-10-18.md` states the role and required boundaries. No canonical Jessica role profile or doctrine source is present. |
| Character store and evidence/proposal/review/publication workflow | **Specified only; historical partial implementation reported** | The temporary plan reports an older full-system review found Jessica's character workflow partly implemented. No store, workflow code, graph, tests, or referenced historical review is available in the current checkout. |
| Jessica conversational cognition connected to character workflow | **Missing here; historically reported disconnected** | Temporary plan explicitly identifies the connection as unfinished. No Jessica conversation identity, router registration, or integration test was found in `src/`, `process_graphs/`, or `tests/`. |
| Grace's existing identity, history, personality, voice, and continuity | **Specified in part; runtime character continuity not established** | `CORE_CONTRACT.md`, `RESIDENT_CONVERSATION.md`, and `grace_role_context.py` establish Grace as one continuing office occupant and preserve role/authority across model stages. These operational role constraints do not supply a full personality or history canon, so absence of such a profile here is not permission to invent or replace it. |
| Resident conversation persistence and reasoning runtime | **Implemented and connected for Grace** | `src/riverview_core/resident_execution/conversation.py`, `model_router.py`, and `process_graphs/resident-conversation/browser-chat.json` cover Grace. They are not a Jessica character system and are under active reasoning integration in PRs #113/#114. |
| Additional resident onboarding through character architecture | **Specified as future; missing implementation in this checkout** | The temporary plan places onboarding after Jessica recovery. The current conversation documentation describes Grace's path; no onboarding lifecycle or Jessica-owned character approval path was found. |
| Shared resident learning contracts | **Separate workstream; no Jessica learning implementation** | `docs/architecture/INSTITUTIONAL_LEARNING_AND_RESOURCE_CAPABILITY_ROADMAP.md` says there is no commissioned general learning system and references missing PL-0016. The shared learning system is developed separately; Jessica must consume its approved contracts when available, not create another facts database. |
| Estate / archived Jessica material | **Referenced, unavailable for verification** | `GRACE_DIRECTOR_OF_OPERATIONS_RECONCILIATION.md` cites historical Estate repositories and the 2026-08-26 `GRACE_JESSICA_LIVE_ACCEPTANCE_BASELINE` file. That evidence file and the separate Estate source are not present in this workspace. Its title is not evidence of Jessica implementation or current deployment. |

## Smallest safe recovery and integration sequence

1. Recover and checksum the original Jessica roadmap, doctrine, character-store contract, process graph, tests, and relevant Estate/archived specifications from their authoritative history. Preserve their original revisions and provenance; do not reconstruct missing canon from this inventory.
2. Compare those artifacts against the present source and classify each concrete node/module as connected, disconnected, specified, or absent. Keep Grace's existing profile/history intact and treat any proposed canon edit as a separately reviewed proposal.
3. After PR #113/#114 reasoning contracts are accepted and stable, add Jessica as a separate resident implementation at the existing registry/routing and process-graph seams. Reuse the recovered character workflow and existing revision/review/publication rules. Do not modify Grace's central pipeline or add a learning database.
4. Integrate only through the approved shared resident-learning interfaces once published. Character canon and operational learned facts remain distinct authorities.
5. Add isolated tests for Jessica identity registration, character evidence/proposal/review/publication lifecycle, continuity and restart, denied unreviewed canon publication, and onboarding boundaries. Add no production records or migrations as part of source recovery.

## Dependencies and acceptance evidence

**Blocking inputs:** authoritative historical Jessica artifacts (including the referenced Estate repository/evidence), confirmation of the canonical character-store and publication owner, and stable post-#113/#114 resident reasoning extension contracts. The shared learning contract is a later integration dependency, not a reason to build local storage.

**Current work package:** this inventory and dependency map are isolated from the open central reasoning PRs and can be reviewed independently. Runtime integration should be a follow-up change after the missing sources and extension seams are available.

**Acceptance for the follow-up:** recovered artifacts are linked by revision/hash; Grace's existing identity and history remain intact; Jessica conversation reaches the recovered workflow through the supported seam; proposals cannot publish canon without required review; onboarding follows the existing resident authority/revision lifecycle; all tests use isolated fixtures; no parallel learning store, migration, production edit, or central reasoning rewrite is introduced.

## Source list reviewed

- Git commit `3c0714e8263df6321f320979108fdb9353da2db0`, historical file `docs/operations/roadmap/GRACE_NEXT_STAGE_TEMPORARY_PLAN_2026-10-18.md` (not present in current tree)
- `docs/architecture/GRACE_DIRECTOR_OF_OPERATIONS_RECONCILIATION.md`
- `docs/architecture/CORE_CONTRACT.md`
- `docs/components/RESIDENT_CONVERSATION.md`
- `docs/architecture/INSTITUTIONAL_LEARNING_AND_RESOURCE_CAPABILITY_ROADMAP.md`
- `process_graphs/resident-conversation/browser-chat.json`
- `src/riverview_core/resident_execution/`
- `docs/steward/Riverview_Steward_Punch_List_2026-10-13.md`
- Open GitHub PRs #113 and #114, listed as active in the repository at inventory time.
