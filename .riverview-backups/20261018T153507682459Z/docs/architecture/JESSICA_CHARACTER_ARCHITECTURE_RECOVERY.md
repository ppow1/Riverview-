<!-- RIVERVIEW~ CONTROLLED DOCUMENT
File Revision: 1.0.1
Component: JESSICA-CHARACTER-ARCHITECTURE-RECOVERY
Status: Historical design and implementation recovered; current Riverview integration pending
Purpose: Record source evidence, original Jessica design, current gaps, and a bounded implementation/test plan
Authority: Historical evidence is preserved; resident canon changes require the existing review and publication authority
History: 1.0.1 supersedes the preliminary current-checkout-only inventory after recovery of THEESTATE/Riverview history
-->

# Jessica character architecture recovery

**Inventory date:** 2026-10-18
**Current worktree:** `ppow1/Riverview-` local `dev/jessica-recovery`, PR #116
**Scope:** Read-only archaeology across the Riverview recovery worktree, the nested historical `ppow1/Riverview` repository, `ppow1/theestate`, its conversation archive, and dated Estate exports. No source from these other worktrees was changed.

## Finding and evidence boundary

The prior PR #116 inventory was too narrow: it searched the current hyphenated `ppow1/Riverview-` checkout and missed `A:\theestate\Riverview`, a nested clone of the historical `ppow1/Riverview` repository. Its Jessica roadmap, C464/C471 recovery artifacts, workflow source, and tests are available in local Git refs. This revision supersedes the earlier claim that those named artifacts were unavailable. The old repository is a different codebase from current `ppow1/Riverview-`; its files are evidence and design inputs, not code already integrated into the current runtime.

The historical source is concrete. Riverview contains an explicit Jessica residency roadmap, a bounded Estate archaeology corpus, identity/continuity contracts, professional doctrine and methods, resident-context interfaces, character-store/workflow code, and tests. Its planning and acceptance records also put clear limits on what was accepted or live. In particular, Jessica's individual personality canon is intentionally sparse: only the Steward-established name, office/title, and name-origin are fixed in this evidence set. The roadmap explicitly defers biography, surname, backstory, appearance, visual canon, expanded personality, and personal history. Jessica Rabbit is the name's stated inspiration only; the source expressly says not to import fictional traits.

### Provenance cautions

- `A:\theestate\Riverview` is on local `main` at `87b0090`, 258 commits behind `origin/main` at inspection, and had pre-existing tracked modifications and untracked files, including the local Jessica acceptance-baseline report. I did not edit, reset, or clean that worktree. Historical branch refs named below are available locally.
- The C464/C465/C466/C468/C471/C475 refs are Riverview evidence branches with exact commits listed below. The C464 report identifies Estate evidence commit `21af737b1610e6b54e4c77f2513cd971db9f9a34`; this object is present in the separate Estate repo.
- The local `GRACE_JESSICA_LIVE_ACCEPTANCE_BASELINE_2026-08-26.md` in the stale nested checkout is untracked there. It self-reports authoritative source SHA `ec9075bfec7655fe67e7c4455bfd9c644b2d2d52`, but the report file is not in that commit's tree. I use it only as a recovered local report, not as committed or independently verified acceptance evidence.
- Source presence, tests, and historical acceptance reports do not establish deployment or current live behavior.

## 1. Source inventory

| Source and exact path | Source commit / provenance | What it establishes |
|---|---|---|
| `ppow1/theestate`: `operations/governance/WP-0136_office_of_character_architecture_report.md`; `docs/governance/offices/Office_of_Character_Architecture.md`; `constitution/constitution.md` | Estate commit `a55a8997ee212f30718f0ca413ee5b853d7098b7` (2026-07-06), “Establish Office of Character Architecture”; present in local `A:\theestate` | Canonical office title and scope, duties, recommendations, Engineering/Governance coordination, and explicit non-sovereign authority boundary. Historical Estate governance is provenance, not current Riverview authority. |
| `ppow1/Riverview`: `docs/architecture/riverview_resident_localization_master_roadmap.md` | Initial roadmap `67329cecf171886da7448fb0c034203d7c4aa551`; later C481 roadmap integration `96a2af097b35067ed261d58679f7b50d3cc32b4a` | Jessica is the existing officeholder to recover, not a newly invented resident. Separates office/occupant/implementation/state; sets evidence classes and staged localization; gates implementation on accepted Grace autonomous engineering; broadens the substrate beyond Jessica. |
| `ppow1/Riverview`: `docs/architecture/jessica_localization_campaign_execution_spec.md`; `docs/work_packages/resident_localization_tranche_0_A_work_packages.md`; `docs/architecture/jessica_localization_campaign_manifest.yaml` | Spec `42cf32d6ac3872af6d56f6bdff663fae5371048d`; work packages `4a761c8a73998d5cc7fc91250fc843c5566868ff`; campaign manifest entered with Tranche 0/A planning | Event-driven DAG and progressive elaboration; archaeology before contracts/storage/runtime/professional recovery; explicit stop/Steward gates; no execution authorization in the plan itself. |
| `ppow1/Riverview`: `docs/architecture/resident_localization/jessica_recovery_corpus_manifest_v1.json`; `docs/architecture/resident_localization/jessica_recovery_corpus_report_v1.md`; `docs/architecture/resident_localization/jessica_officeholder_continuity_inventory_v1.md`; `docs/architecture/resident_localization/jessica_estate_office_source_inventory_v1.md`; `docs/architecture/resident_localization/jessica_artifact_disposition_v1.md`; `docs/architecture/resident_localization/jessica_character_architecture_methods_inventory_v1.md` | C464 `76f712148944a8cf3d995b5538997cc01e63867a`, branch `codex/c464-jessica-archaeology-corpus`; based on Riverview `f390496e8d8fe712ab68a7048ec09c78564a3606` and Estate evidence revision `21af737b1610e6b54e4c77f2513cd971db9f9a34` | Bounded 26-source archaeology, dispositions, gaps, explicit contradiction handling, and 12 method families in the initial manifest (later corrected to 13). It states there is no Jessica biography, appearance, surname, expanded personality, or private-source corpus in the recovered set. |
| `ppow1/Riverview`: `docs/architecture/resident_localization/jessica_identity_continuity_contract_v1.md`; `docs/architecture/resident_localization/jessica_identity_continuity_contract_v1.json`; corrected C464 manifest `docs/architecture/resident_localization/jessica_recovery_corpus_manifest_v1_1_c465_correction.json` | C465 `7bde793a23598831386d22851aefcb556f3d5b16`, branch `codex/c465-jessica-continuity-contract` | Steward-authorized identity anchors and source-classification/continuity rules. Name-origin does not import fictional traits. Historical Chief Architect IDs and mailboxes remain unresolved rather than normalized. |
| `ppow1/Riverview`: `docs/architecture/resident_localization/resident_continuity_persistence_model_v1.md`; `docs/architecture/resident_localization/resident_continuity_postgresql_architecture_v1.md`; `docs/architecture/resident_localization/resident_continuity_schema_contract_v1.json` | C466 `04b6908d3309e01dae81628879ebbdbe4903df33`, branch `codex/c466-resident-continuity-persistence` | A proposed resident-general persistence boundary for office, occupant, implementation, state, evidence, references, relationships, and lifecycle. This is architecture, not proof that its schema was applied in production. |
| `ppow1/Riverview`: `docs/architecture/resident_localization/resident_rehydration_context_architecture_v1.md`; `docs/architecture/resident_localization/resident_context_bundle_contract_v1.json`; `docs/architecture/resident_localization/resident_context_profiles_v1.md` | C468 `523cd5646c8259bfea9316192fffa73a1da8b685`, branch `codex/c468-resident-rehydration-context` | Bounded, provenance-aware context assembly and profiles as replaceable implementation inputs; identity and continuity are not model prompt state. |
| `ppow1/Riverview`: `docs/architecture/resident_localization/jessica_character_architecture_professional_doctrine_v1.md`; `docs/architecture/resident_localization/jessica_professional_capability_manifest_v1.json`; `docs/architecture/resident_localization/character_resident_identity_design_method_v1.md`; `docs/architecture/resident_localization/relationship_cognition_behavior_continuity_method_v1.md`; `docs/architecture/resident_localization/visual_canon_character_bible_method_v1.md`; `docs/architecture/resident_localization/character_architecture_advisory_engineering_interface_v1.md` | C471 `eaade03a4632cb355df524a410b6ecb01a640e49`, branch `codex/c471-jessica-professional-recovery` | Thirteen recovered office-level doctrine principles and professional method/interface families. The source explicitly says these are not Jessica's personal biography or personality. Capability status is “recovered for validation”; validation and Steward residency acceptance are not complete. |
| `ppow1/Riverview`: `docs/architecture/graph_views/06_character_development.mmd` | `404e527bea304c42d5e7b94753bf02c68b9457d6`, 2026-08-18 | Static architecture view contains a “Versioned accepted character canon” node. It is not a stage-by-stage Jessica workflow graph; the executable advisory stages are in `src/riverview/characters/workflow.py`. |
| `ppow1/Riverview`: `src/riverview/characters/store.py`, `src/riverview/characters/workflow.py`, `src/riverview/operator/openwebui.py`, `src/riverview/residents/gateway.py`, `tests/test_character_development.py` | Generic character/gateway base at `64ab4964bf3e6e9f2a4bbd79f4e3faad835db10f`; Jessica workflow/surface `f9a4f131a3959a90d4b90bbe6ab1f5008dde2894`; independent and Steward review gates `4c68a2ba07dc7fe0c54faf9f1216e2050f339245`; Grace/operator integration `b7ba9946423f339c61741bf37b1acf4b1568c343` | Historical source implementation and regression tests. Jessica workflow metadata is advisory; Grace coordinates. Store separates versioned canon, proposals, session history, and continuity candidates. Accepted review is required before publish; later hardening requires independent review followed by distinct Steward review and rejects authority/identity-anchor changes. Tests use disposable `tmp_path` stores. |
| `ppow1/Riverview`: `docs/operations/roadmap/evidence/GRACE_JESSICA_LIVE_ACCEPTANCE_BASELINE_2026-08-26.md` | Local untracked recovery file only; it reports baseline SHA `ec9075bfec7655fe67e7c4455bfd9c644b2d2d52`, not present in its asserted tree | Reports 30 targeted tests passed and says gateway contract was exposed, but no live Jessica conversation was accepted and no interactive inspect/discuss/propose character surface was accepted. Treat as unverified supplemental evidence, not proof of live acceptance. |
| `ppow1/theestate-chatgpt-conversation-archive`: `collaboration/codex_campaigns/CCA-CAMPAIGN-08-RESIDENT-PERSONALITY-FIDELITY.md`, `CCA-CAMPAIGN-09-RESIDENT-AUDIBLE-VOICE-COMMISSIONING.md`, `CCA-POST-HARDENING-VALIDATION-AND-REPAIR.md` | Separate archive clone at `472f476b`; these are historical campaign artifacts, not a direct Jessica identity source | Additional character-method and validation provenance. They must be dispositioned through the C464 corpus; their campaign titles do not establish Jessica personal traits or accepted runtime behavior. |

## 2. Recovered design

### Office responsibilities (verified historical role doctrine)

WP-0136 and its office record establish that the Chief Character Architect is responsible for resident and worker identity design; character traits and behavioral boundaries; developmental arcs; intelligence profiles and skill domains; relationship maps and collaboration patterns; identity continuity across implementation changes; model/cognition and implementation recommendations; character briefs and continuity notes; new-character coherence review; and coordination with Engineering and Governance. Jessica's office can recommend prompts, structured memory, APIs, services, models, and runtime state. Those recommendations are not operational access or authority.

The role may not grant authority, execute privileged actions, bypass Steward approval, override an office's powers, or assign model/service/API access when another authority path must approve it. Technical behavior changes route through Engineering; authority/autonomy changes route through Governance and Steward review.

### Jessica's established individual identity (verified; deliberately limited)

The C464/C465 continuity records define the established personal facts as:

- Name: Jessica.
- Office/title: occupant of the Office of Character Architecture; Chief Character Architect.
- Name origin: chosen by the Steward as a nod to Jessica Rabbit.

The source explicitly excludes inference from that reference. Surname, biography, backstory, physical/visual identity, expanded personality, and personal-history detail are deferred. The archaeology did not find a sufficiently direct historical self-description that can be assigned to Jessica without conflating her with the office, Chief Architect #5/#6, Evelyn, or a particular implementation. We therefore have a recovered professional design architecture, not a recovered set of Jessica temperament traits or catchphrases.

### Character architecture doctrine and methods (verified professional capability, not personality canon)

C471's 13 doctrine principles can be summarized without converting them into personal traits:

1. Keep office, occupant, implementation, state, and canon distinct.
2. Label accepted fact, historical evidence, inference, uncertainty, and supersession.
3. Keep stable identity anchors, allowed variation, and unknown/deferred canon separate.
4. Treat relationships and permissions as independent dimensions.
5. Differentiate residents through decisions, boundaries, and uncertainty handling, not stereotypes or a universal prompt.
6. Preserve methods across provider/model/host changes; treat model choice as a recommendation.
7. Separate design, implementation, validation, and acceptance evidence.
8. Preserve bounded useful continuity across replacement without treating transcripts as canon.
9. Append and review revisions; do not silently self-canonize or destructively overwrite.
10. Decompose broad character work into bounded deliverables and acceptance criteria.
11. Validate visual canon with references, anchors, allowed variance, and recognizability checks.
12. Treat professional advice as non-sovereign.
13. Keep protected material behind explicit classification and retrieval policy.

The method inventory covers identity decomposition and source classification; character-bible composition; behavioral differentiation; relationships; visual/voice design; resident-specific cognition; continuity renewal; conflict/supersession; work-package decomposition; review/critique; and implementation transition. Evelyn artifacts provide method evidence only; her canon is not Jessica's.

### Interfaces and historical behavior

**Professional request/response interface (C471 design):** use a stable request/correlation ID; identify requester and subject; provide a bounded question, relevant versioned artifact references, accepted constraints, explicit unknowns/conflicts, classification/egress policy, authority boundary, and expected deliverable/acceptance evidence. Jessica's professional outputs can be a recommendation, identity-design spec, canon-conflict analysis, character-bible or relationship proposal, cognition/implementation recommendation, critique, migration interpretation, or acceptance recommendation. Outputs must state provenance, confidence/uncertainty, scope, and whether they are advice or a proposal.

**Engineering handoff (C471 design):** supply identity/office/state invariants; schema/interface and context/artifact needs; provider capability/classification constraints; event/diagnostic evidence; tests/failure cases; unresolved questions and Steward gates. The historical interface explicitly denies arbitrary shell access, core-table mutation, protected access, or model selection authority.

**Character development workflow (historical code):** `jessica-character-development-v1` is `advisory_workflow`, coordinated by Grace, with inspect → propose → independent review → Steward review → publish. Proposals carry source evidence, rationale, and the base character version. The file-backed prototype uses JSON, retains prior versions, rejects authority/identity-anchor expansion, and keeps session history/continuity candidates separate. Publication requires accepted review state. Code is present in the 2026-08 `ppow1/Riverview` history; it has not been ported into the current hyphenated Riverview core.

**Resident continuity substrate (C466/C468 design):** resident-general stable identities and references, evidence classification, implementation bindings, bounded context assembly, relationship/state/artifact references, and rehydration. This is not a Jessica-only schema and not a parallel learning database. Adopt only contracts approved by the separate current Resident Learning/continuity workstream.

**Historical live connection boundary:** the local 2026-08-26 baseline report says the workflow contract was exposed in the resident gateway, but the live Jessica conversation and interactive character-development surface were not accepted. Its untracked provenance limits prevent treating this as authoritative live evidence. No evidence found establishes current `ppow1/Riverview-` integration.

## 3. Gap analysis

| Area | Recovered state | Remaining gap |
|---|---|---|
| Office doctrine and authority boundary | Verified Estate governance record plus C464/C471 Riverview recovery artifacts | Filter old Estate process machinery through current Riverview contracts; do not import Estate authority. |
| Jessica person-specific canon | Name, office/title, and name-origin only | Directly attributable historical self-description/reflection, surname, biography, history, and expanded personality remain unknown/deferred. No invention is permitted. |
| Character methods | C471 doctrine, capability manifest, methods inventory, and review interface exist in history | Professional capability was “recovered for validation”; validation/Steward residency acceptance remained `NOT_STARTED` in C471. Current acceptance needs confirmation. |
| Workflow/store | Historical prototype and tests exist in `ppow1/Riverview` commits | Prototype is not present in current `ppow1/Riverview-`; JSON persistence and endpoint/Operator surfaces need compatibility/security review before reuse. |
| Conversation integration | Historical gateway exposure and Grace coordination are present in older source | No accepted live Jessica conversation or interactive inspect/discuss/propose surface in the recovered baseline; no present-day connection to current reasoning seam is verified. |
| Continuity/persistence | C466/C468 schema/context designs and resident tests/contracts exist | Do not apply their schema in this task; reconcile with approved shared contracts and current revision/migration lifecycle first. |
| Additional resident onboarding | Reusable resident substrate and population guardrails specified | Character-approved onboarding lifecycle is not demonstrated in the current `ppow1/Riverview-` checkout; Jessica must be validated before using her as authority for other migrations. |
| Estate source conflicts | C464 preserves numbered-architect and mailbox contradictions, chat ingestion gaps, and protected-layer boundaries | Missing WP-4095–WP-4130 chat-derived source material and direct Jessica reflections require explicit sourcing/Steward resolution, not normalization. |
| Current Grace continuity | Current Riverview has separate Grace role and conversation architecture | Jessica recovery does not authorize edits to Grace canon, personality, history, or central reasoning pipeline. |

## 4. Minimal implementation plan and safe tests

No runtime implementation is needed to recover the original design: the design and a historical prototype already exist. The smallest safe current PR change is this evidence correction and source-linked handoff. Runtime porting should be a separate, bounded follow-up after the current reasoning integration and shared resident-continuity contracts stabilize.

1. **Lock evidence:** add stable references and hashes for the C464/C471 artifacts, retain dispositions and unknowns, and do not copy the Estate runtime or private material wholesale.
2. **Review interface compatibility:** compare the historical request/response and character proposal contract against current resident identity, exact-grant, proposal/revision, process-graph, and approved learning interfaces. Record differences before coding.
3. **Port only the smallest seam:** if approved, register Jessica as a distinct resident and expose the recovered advisory workflow through the stable resident extension seam. Preserve Grace's existing implementation and behavior; let Grace coordinate rather than acting as a substitute Jessica identity. Avoid migrations unless the shared contract requires one.
4. **Keep state authorities separate:** authored character canon remains versioned and review-gated; operational learning uses the approved shared contract; conversation history is not canon. Do not add a second facts store.
5. **Defer onboarding expansion:** validate Jessica's rehydration and professional usefulness first; do not bulk-onboard additional residents in this change.

Safe isolated acceptance tests for that follow-up:

- Load only the sourced Jessica anchors and verify no unsourced biography/personality/visual fields are seeded; missing fields remain unknown.
- Verify artifact references resolve to pinned commits/hashes and source classifications survive context assembly.
- Propose a canon change with evidence, rationale, and base version; assert current canon remains unchanged before review.
- Assert self-review, missing independent review, missing Steward approval, stale base version, authority expansion, and identity-anchor replacement are rejected.
- Accept an isolated fixture proposal through required reviews; assert append-only version lineage and that rejected/unreviewed candidates never become runtime truth.
- Restart from disposable persistence and verify resident isolation, bounded context, and accepted-only canon rehydration.
- Exercise a mocked resident reasoning provider and assert an advisory recommendation cannot create work authority or bypass existing proposal/objective grants.
- Test onboarding against a draft fixture: character review can recommend/prepare; activation and authority still require the existing resident lifecycle/Steward gates.

Historical test evidence: `tests/test_character_development.py` at `4c68a2b` tests proposal/review/publish, continuity approval, Grace ownership, non-self-review, and authority-boundary behavior. Its character fixture is Helen, not Jessica, so it validates workflow mechanics, not Jessica canon or personality. The local untracked acceptance-baseline report claims 30 targeted tests passed but is not independently attributable to a committed source tree. No tests were run in this recovery turn because no runtime source was changed.

## PR and work-board update

This document is the focused update to PR #116. Issue #120 is updated separately with the newly located sources and the remaining evidence/implementation boundaries. No Estate or production changes, database migrations, merges, or deployments were made.

## Original-current-tree references

- `docs/architecture/GRACE_DIRECTOR_OF_OPERATIONS_RECONCILIATION.md` in `ppow1/Riverview-` references the historical Estate and Grace/Jessica baseline but is not itself the Jessica design source.
- `docs/architecture/CORE_CONTRACT.md`, `docs/components/RESIDENT_CONVERSATION.md`, `process_graphs/resident-conversation/browser-chat.json`, and `src/riverview_core/resident_execution/` in `ppow1/Riverview-` describe current Grace identity/conversation seams; Jessica is not registered in them.
- Prior PR #116 version 1.0.0 is preserved as `.riverview-backups/20261018T152357713027Z/docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md` with SHA-256 `84b6d03c918817fe7999e8884b87f39a77932ac6eee7963010082f1db5bc0c76`.
