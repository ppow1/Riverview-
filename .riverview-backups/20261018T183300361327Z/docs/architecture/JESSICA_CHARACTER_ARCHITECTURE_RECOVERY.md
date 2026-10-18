<!-- RIVERVIEW~ CONTROLLED DOCUMENT
File Revision: 1.0.5
Component: JESSICA-CHARACTER-ARCHITECTURE-RECOVERY
Status: Historical design recovered; isolated advisory package implemented; resident integration pending
Purpose: Record source evidence, original Jessica design, current gaps, and bounded implementation/test evidence
Authority: Historical evidence is preserved; resident canon changes require the existing review and publication authority
History: 1.0.1 supersedes the preliminary current-checkout-only inventory after recovery of THEESTATE/Riverview history
History: 1.0.2 adds an isolated evidence-gated advisory package and its acceptance boundary; no runtime activation
History: 1.0.3 adds a dormant, Steward-attested adapter to the existing authorized_import proposal contract
History: 1.0.4 traces current Steward account/principal binding and records the exact Jessica authorship gap
History: 1.0.5 records the parent visibility contract, standards divergence, graph sidecar blocker, and bounded recovery evidence
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

## 4. Isolated integration increment (2026-10-18)

`src/riverview_core/jessica_character_architecture.py` adds an **inactive advisory role profile** and a pure proposal-package builder. The role carries only the verified office responsibilities from C471, cites that source, has no authority grants, and marks biography, surname, backstory, appearance, expanded personality, personal history, and original memories unresolved. It does not establish a prompt/personality or register a resident.

The builder accepts a bounded request, subject resident ID, base revision, proposed content, exact evidence references, and evidence-linked claims. It emits content shaped for the existing `ProposalContent` contract, with source references and producer/request provenance. The revision helper produces a successor package and retains its predecessor revision and evidence context. These builder operations are in-memory only.

**Verified workflow evidence:** historical code uses inspect → propose → independent review → Steward review → publish, with versioned character canon and explicit review gates (historical commits listed in the inventory). **Current isolated behavior:** request → evidence-bounded proposal package → local successor revision. **Still not connected:** current HTTP proposal authoring is Steward-session-bound and Grace-conversation-bound. It does not accept Jessica as author. Existing registry APIs can persist/review/revise records but do not supply authorization, and direct use as Jessica would misrepresent the authenticated actor. A future adapter requires an approved identity/authorship contract and authority route; this increment intentionally does not create one.

The package builder rejects missing source evidence, claims whose evidence ID is absent or whose wording differs from its cited evidence record, unresolved personal fields presented as proposal facts, and proposals missing the mandatory advisory authority boundary. The builder is not a source retriever and cannot independently verify that a cited external artifact contains the supplied evidence statement; source resolution remains an integration acceptance requirement.

`create_advisory_import_draft` is a dormant persistence adapter to the existing registry's `authorized_import` origin. It requires a Steward principal attested by the existing trusted transport boundary, stores the Steward as `created_by`, records Jessica only as `advisory_producer`, and carries the source/request/revision provenance forward. It does not add an HTTP route, resident grant, Jessica credential, proposal origin kind, migration, review, approval, or promotion path. Calling the helper can create only a DRAFT proposal through `ProposalRegistry.create_draft`; existing exact Steward review and decision mechanisms remain in force. Tests use a recording fake registry, not a database. No central Grace conversation/reasoning code, resident table, learning store, process graph, or migration was changed.

### Trusted identity trace and exact integration gap

The current authenticated account path is `status_dashboard/server.py` `_authorized()` → `AccountAuthService.authenticate()` in `account_auth/__init__.py`, which validates the session (and CSRF for state-changing requests) and returns the account's stored `authority_principal_id`. The proposal route checks authenticated account session, the `steward` role, and the linked principal; it passes that server-derived ID through conversation authorization and persists drafts with that ID as `created_by`. The route only formalizes selected Steward-authored messages from a Grace conversation. `ResidentConversationService` then checks exact `resident.conversation.read` and `.send` grants scoped to its configured office, and source-message ownership is checked against that same principal.

Current evidence points to `steward:camrui` as the only bootstrap-linked account principal (`AccountAuthService.request_steward_bootstrap` and `verify_steward_bootstrap` constrain bootstrap to it). The live conversation service is Grace-office-bound. Repository search finds no Jessica principal/office binding or Jessica resident conversation route in current runtime code. The missing integration is therefore not a permission to add: there is no approved Jessica authenticated identity binding, resident office/implementation binding, or route that can submit Jessica-produced packages as such. The low-level proposal registry accepts `authorized_import`, but it does not authenticate actors; callers must provide the already-attested Steward identity. The dormant adapter uses that existing path transparently and deliberately records Steward as actor, Jessica as advisory producer. It is not a Jessica identity implementation. Any route that accepts Jessica-authored packages still needs an approved identity/authorship contract and authenticated caller path.

### Acceptance evidence

`tests/test_jessica_character_architecture.py` uses isolated synthetic requests and a recording fake registry, with no database. It covers inactive/non-authoritative role metadata, proposal and successor revision provenance, evidence-required behavior, rejection of unsupported historical claims and unresolved identity expansion, rejection of an omitted/revised authority boundary, mapping through the existing import origin while keeping the authenticated Steward actor distinct from Jessica's advisory authorship, and denial before any registry call for non-Steward actor labels. These tests do not establish that a caller actually authenticated its supplied principal; the trusted transport remains the actor-authentication boundary. They do not establish connected resident behavior or historical C471 validation/Steward acceptance.

### Minimal next integration plan

1. Obtain approval for any calling path that would accept or generate a Jessica advisory package, and confirm it uses the existing trusted Steward identity rather than asserting Jessica is authenticated.
2. If approved, integrate the dormant helper behind the existing authenticated proposal path, preserving append-only revisions/reviews and the exact Steward decision gate; do not add storage or lifecycle tables.
3. Add disposable-schema tests for authorized draft creation, immutable revision, review evidence, denial of authority changes, and no work-order promotion absent the existing separate exact grant.
4. Keep Jessica inactive until the separate resident framework and identity acceptance work are complete.

## PR and work-board update

This document is updated with an isolated, non-persistent advisory implementation and the current authoring boundary. PR #116 and issue #120 record the code, focused test evidence, and remaining integration dependency. No Estate or production changes, database migrations, merges, or deployments were made.

## Original-current-tree references

- `docs/architecture/GRACE_DIRECTOR_OF_OPERATIONS_RECONCILIATION.md` in `ppow1/Riverview-` references the historical Estate and Grace/Jessica baseline but is not itself the Jessica design source.
- `docs/architecture/CORE_CONTRACT.md`, `docs/components/RESIDENT_CONVERSATION.md`, `process_graphs/resident-conversation/browser-chat.json`, and `src/riverview_core/resident_execution/` in `ppow1/Riverview-` describe current Grace identity/conversation seams; Jessica is not registered in them.
- Prior PR #116 version 1.0.0 is preserved as `.riverview-backups/20261018T152357713027Z/docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md` with SHA-256 `84b6d03c918817fe7999e8884b87f39a77932ac6eee7963010082f1db5bc0c76`.

## Targeted DoD remediation — 2026-10-18

This increment follows current `origin/main` AI_HINTS 1.0.4 and Component DoD Rev 1.6. This PR's base contains AI_HINTS 1.0.5 and DoD Rev 1.7; that branch-local divergence is recorded here and neither standard is changed by this increment. The lifecycle and engineering-records standards remain Proposed in both reviewed trees.

The request-driven adapter has no process of its own and no independent health or heartbeat. Its parent visibility contract is therefore: (1) in-memory proposal packages remain caller-owned and are not reported as persisted work; (2) when the existing parent application invokes the dormant import adapter from a trusted, authenticated Steward context, the parent registry is authoritative for the resulting DRAFT; and (3) the Steward-authenticated proposal API (`GET /api/v1/institutional-proposals?q=&tag=&status=&limit=` and `GET /api/v1/institutional-proposals/{proposal_id}?revision=N`) is the existing visibility path. Jessica has no authenticated principal, account, route, independent status, or permission. The visible actor remains the trusted Steward; `advisory_producer` is provenance only. No Jessica proposal is currently connected to that API.

The W3 recovery cookbook is `docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md`. It records the implemented request/proposal/evidence/revision boundaries, read-only diagnostics, visible parent contract, known failures, recovery steps, and the Mermaid path. It does not claim a canonical registered graph: the required JSON graph registration and generated projections depend on `.riverview-revisions.json`, which W1's separately authorized remediation currently owns. The pre-existing `python scripts/process_graph.py check` failure is independently reproducible: the branch's schema bytes hash to `95596d4def44a2ff201b2b32be7ebe1890a2903c2beff8cdabbc857e31c1b41f`, while its sidecar records `0c03d29216d6d3cb08e58ab7bff12b545211f78fbdffb0767118553b52025da7`. That recorded hash matches the schema bytes and sidecar on current `origin/main` (`f6558554a1d360aebdb24036d3a8b7781e7e92b5`), so the failure is isolated to this branch's schema/sidecar divergence. Changing the schema's registry metadata here would modify W1's assigned shared file. W3 leaves it untouched, reports canonical graph validation as blocked, and requests W1 handoff of the metadata change before graph generation. The cookbook's Mermaid is a focused view of existing behavior, not a substitute for canonical graph registration.

No authorized isolated PostgreSQL DSN is configured (`RIVERVIEW_TEST_PG_DSN` is absent). Registry persistence and database integration are **NOT VERIFIED**. Existing isolated unit tests use a recording fake registry. No resident creation, Jessica identity, approval, production path, or permission was added.

The recovery cookbook and the checkout evidence published with this increment are the operational and revision/restore record for this remediation. The existing generic backup manifest remains in its historical format; missing source-commit and restore fields on older records are not retroactively fabricated. The new checkout evidence records the exact source commit, test commands/results, backing file hashes, and restore path for these W3 changes.
