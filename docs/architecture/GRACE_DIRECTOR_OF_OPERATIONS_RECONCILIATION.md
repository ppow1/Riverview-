# Grace Director of Operations: Historical and Current-State Reconciliation

**File Revision:** 1.0.0
**Date:** 2026-10-14
**Status:** Evidence-based architecture reconciliation; no production or authority changes authorized by this document.
**Scope:** Reconcile the historical Estate/Riverview design with the current `ppow1/Riverview-` engineering implementation and identify the smallest restoration sequence.

## 1. Executive finding

Grace's canonical institutional office is **Director of Operations**. She coordinates institutional progression, the Continuous Motion Engine (CME), Engineering, resource-aware routing, monitoring, recovery, and exception escalation. Alfred is the separately designated Chief of Staff. The Steward retains final institutional authority. Grace's models are implementations of one office occupant; they do not determine or replace the office, its authority, or its responsibilities.

The historical operations repository records this role explicitly. The current engineering documentation and live office-role metadata have drifted: current `CORE_CONTRACT.md` and `ROADMAP.md` describe Grace as an “AI director of engineering work,” and the live office role was observed as “AI director of engineering.” That wording narrows and misstates the canonical office. It must be reconciled through the normal documentation and AuthorityRegistry processes; this report does not alter the live binding or authority.

Today, the deployed conversation path can route Grace's text turn among the 0.6B, 30B, and 80B providers while retaining one persisted conversation and provider provenance. It does not yet give the model a complete, authoritative Director of Operations role profile or a bounded occupational capability set in its conversation context. The 0.6B inference service is running, and the 30B and 80B APIs were observed healthy during the October 14 investigation; a dedicated autonomic control loop and a persistent Grace-to-Engineering execution service are not commissioned. The Codex execution path exists in source but its service unit is not installed. Therefore, model availability and successful conversation do not establish operational autonomy.

## 2. Evidence and confidence boundaries

Historical source references below are from the separate operations repository `ppow1/Riverview` (without the trailing hyphen), cloned at commit `08c1162c4ad04a21df71ed7814a3e22bd9ba41a2`. The current engineering source is `ppow1/Riverview-` (with trailing hyphen); the live production release observed during this reconciliation is `98287c9a344f8ead203b55d50366b02014d9ce62`. Source presence is not proof of deployment. Live checks are explicitly identified as observations made on 2026-10-14; transient service status can change.

The historical Estate material available for this review consists of archived repository documentation, source, and tests. No separate Estate database or archive outside those records was available. This report does not infer missing Estate history.

### Principal historical sources

| Source | Revision/date and relevance |
|---|---|
| `docs/governance/RIVERVIEW_CHARTER.md` | Version 1.1.0, 2026-08-14; institutional authority and governance baseline. |
| `docs/architecture/RIVERVIEW_GRACE_DIRECTOR_OF_OPERATIONS_TOOLBOX_RECONCILIATION_2026-08-27.md` | 2026-08-27 forensic reconciliation; defines Grace as an operational coordinator and examines her occupational toolbox. |
| `docs/architecture/RIVERVIEW_RESIDENT_OFFICE_CAPABILITY_ARCHITECTURE_AUDIT_2026-08-27.md` | 2026-08-27 architecture audit; records a design-time capability integration gap. It predates later source in the same repository that contains the occupational broker and HOME integration. |
| `docs/architecture/riverview_resident_localization_master_roadmap.md` | 2026-08-19 planning source; names Grace Director of Operations/CME and Alfred Chief of Staff/coordination, and distinguishes operational from cognitive escalation. |
| `docs/operations/RIVERVIEW_ENGINEERING_INTERACTION_CONTRACT.md` | Version 1.3.0; canonical bounded Engineering/CME, provider, capability, and execution contract. |
| `docs/operations/roadmap/evidence/GRACE_JESSICA_LIVE_ACCEPTANCE_BASELINE_2026-08-26.md` | Historical live acceptance evidence for Grace's Operations Director HOME; not evidence of today's deployment. |
| `docs/operations/roadmap/evidence/GRACE_PARALLEL_ENGINEERING_MILESTONE_2026-08-20.md` | Historical milestone evidence; its own evidence boundary does not establish that Grace personally owned every parallel task. |
| `docs/operations/roadmap/evidence/RV-014.1_RESIDENT_REGISTRY.json` | Historical registry snapshot; it labels Alfred “Manager of Administration,” an earlier/alternate record that differs from the later roadmap designation and the Steward-confirmed Chief of Staff title. |

### Current engineering sources examined

`AI_HINTS.md`, `docs/ROADMAP.md`, `docs/architecture/CORE_CONTRACT.md`, `docs/components/RESIDENT_CONVERSATION.md`, `docs/components/GRACE_EXECUTION_PIPELINE.md`, `process_graphs/grace/operational-integration.json`, `process_graphs/resident-conversation/browser-chat.json`, and the corresponding `src/riverview_core/resident_execution/` implementation were reviewed. These sources distinguish office, occupant, implementation, authority, and durable state, but some role and milestone descriptions are stale or inconsistent with live evidence.

## 3. Canonical institutional definition

### Office and relationships

- **Office/title:** Director of Operations.
- **Occupant:** Grace, one continuing institutional resident.
- **Chief of Staff:** Alfred, a distinct office/resident. The older resident registry snapshot's “Manager of Administration” label should be preserved as historical provenance and reconciled, not silently overwritten.
- **Final authority:** The Steward. Grace coordinates delegated operations and applies authorized decisions; she does not create authority for herself or supersede Steward decisions.
- **Implementation:** Multiple model systems and deterministic services may cooperate as Grace's implementation. A model identity, model change, or provider failure does not create a new occupant or office.

### Responsibilities supported by historical sources

The August 27 toolbox reconciliation and localization roadmap describe Grace as the operational coordinator responsible for:

1. Maintaining progression of authorized institutional objectives through CME.
2. Evaluating durable objective, assignment, dependency, worker, resource, and verification state.
3. Coordinating Engineering intake, capability selection, dispatch, progress observation, and completion.
4. Routing work according to required capability, provider readiness, resource capacity, policy, and cost constraints.
5. Recognizing failure, timeout, degraded resources, stale evidence, blocked dependencies, and recovery opportunities.
6. Resuming safe, idempotent work after interruption without losing objective identity or duplicating terminal outcomes.
7. Escalating genuine authority decisions, unresolved risk, resource allocation decisions, and exceptions to the Steward.
8. Reporting evidence-based status and verified outcomes to the Steward and relevant residents.

The Engineering Interaction Contract §§5, 7, 10, 12–14 requires event-driven, dependency-aware, bounded, resumable and idempotent progression; separates information from action; makes model output insufficient as authority; and permits named, allowlisted execution capabilities. Its acceptance invariant requires a resident to select a bounded capability for a novel job-related task, consume authoritative results with provenance/freshness/authority evidence, and continue reasoning. Routine actions already within delegated authority are intended to progress without repeated Steward selection of the mechanism. Exceptions remain escalated.

### Delegated authority boundary

Grace may interpret an objective, retrieve authorized facts, create a proposal, monitor progress, choose among already authorized capabilities, dispatch work where exact grants and policy allow, evaluate verifier evidence, and continue or recover an assignment within its declared limits. A model response alone cannot approve an account, grant a permission, authorize a consequential action, widen scope, or certify its own work. Steward-only decisions and exact-grant checks remain enforced at the responsible service boundary. This boundary preserves both operational initiative and institutional control.

## 4. Intended operational workflow

The sources support the following closed loop. The workflow is a reconciliation of the documented contract, not a claim that every edge is currently commissioned.

1. **Objective intake:** The Steward or another authorized source records a durable objective with identity, scope, acceptance criteria, source conversation/message, and correlation identifiers. The authenticated submitter and exact `objective.submit`/related grants are checked by the existing authority service.
2. **Ground and plan:** Grace reads relevant verified institutional facts, current CME/assignment state, resource/capability status, prior evidence, and applicable process graph. She distinguishes known facts from assumptions and identifies missing evidence.
3. **Capability and authority assessment:** Grace determines whether an existing named capability and resource can satisfy the objective. Capability existence is distinct from present readiness. The service validates exact grants, scope, dependencies, limits, and current office binding.
4. **Progress without unnecessary handoff:** If the action is routine and already authorized, Grace selects the suitable bounded capability and advances the durable objective. If scope, risk, authority, resource allocation, or evidence is unresolved, she records the blocker and asks the Steward for that specific decision.
5. **Engineering dispatch:** CME creates/updates an assignment correlated to the objective and graph node, selects a registered adapter, obtains a durable lease, and dispatches only the bounded inputs and destination approved for the work. Models do not receive arbitrary shell authority.
6. **Observation:** CME consumes worker/service events, progress, resource readiness, and sanitized diagnostics. Grace uses authoritative state, not a claimed completion in model text.
7. **Failure and recovery:** A failure follows the declared graph transition. CME classifies retryability, checks idempotency and leases, preserves pending work, resumes only after revalidating authority and capability, and escalates non-routine decisions. No smaller model silently substitutes for a required capability.
8. **Independent verification:** A verifier checks the real artifact/output against acceptance criteria and records evidence. Executor success alone does not mean mission completion.
9. **Grace continuation and acceptance:** Grace evaluates verifier evidence against the objective, accepts, requests a bounded correction, or escalates. The decision and evidence are durably linked to the originating objective/conversation; the Steward receives the verified outcome.

## 5. Historical occupational toolbox

The historical operations checkout at `08c1162…` contains more than the 2026-08-27 audit snapshot. The audit correctly recorded an integration gap at its date; later source in the same repository contains `src/riverview/reasoning/occupational.py`, `src/riverview/residents/occupational_packages.py`, and `src/riverview/reasoning/resident_home.py`, including a bounded capability broker and tool-result continuation. Their presence proves historical source implementation, not that these components were deployed or carried into the new engineering repository.

| Capability | Historical evidence/status | Current new-core status |
|---|---|---|
| Grace operations identity and HOME | Operations Director behavior appears in `src/riverview/residents/gateway.py`, `src/riverview/reasoning/speech.py`, the Grace HOME/package, and the 2026-08-26 acceptance baseline. **Historically implemented and tested** in that repository. | One office/occupant binding and one conversation store exist; generic prompts do not provide Grace's canonical office responsibilities. Live office-role metadata conflicts with the historical title. **Partially integrated; role context incomplete.** |
| Occupational capability catalog and bounded broker | Historical `src/riverview/reasoning/occupational.py` validates resident/occupant/office/implementation, package, call budget, capability class and authority; HOME invokes bounded model-selected capability requests and then reasons over tool results. **Implemented in historical source**, while the Aug 27 audit records an earlier gap. | Current capability/authority/assignment components exist, but the browser conversation path is not wired to that historical broker/tool-result continuation. **Disconnected.** |
| Work/objective progression and CME | Historical objective, momentum, CME state, worker and event implementations are present in source and milestone evidence; retry/recovery are constrained by durable state. **Implemented in historical source; live status is historical only.** | Current objective/assignment/pipeline/CME components and process graph exist. A persistent Grace execution systemd unit is absent (`LoadState=not-found` in the latest available live check), so end-to-end autonomous progression is **not commissioned**. |
| Engineering interaction and proposal | Historical direct Grace/Engineering interaction has typed specifications, explicit authenticated Steward envelope where required, and a durable objective/authority path. Contract requires resident initiative within existing grants. **Implemented in historical source, with approval boundary.** | A Steward-mediated objective promotion/intake path and a typed execution pipeline exist. The chat prompt explicitly says not to create/claim work orders, and a Grace-authored proposal-to-order action is not connected to the conversation. **Partially implemented; no autonomous chat-to-dispatch loop.** |
| Engineering execution | Historical `runner.py`, Relay, named tool adapters and acceptance evidence describe bounded execution. The contract rejects arbitrary model-provided shell. **Implemented in historical source; operational evidence varies by milestone.** | Codex adapter and verification contracts are present in source. The persistent executor service is not installed; no current production artifact cycle was verified. **Source-only / not commissioned.** |
| Resource/capability assessment | Historical `src/riverview/resources/`, occupational packages, policy and capacity/claim mechanisms include resource and command selection. Aug 27 audit classified portions as present but not wired at that snapshot. **Implemented in source, with historical integration gaps.** | Current registry/readiness mechanisms exist. The conversation router selects a reasoning stage/model, not an Engineering executor or general resource plan. **Not integrated into Grace's operational conversation.** |
| Diagnostics, cookbook, attention and recovery | Historical occupational packages include work, CME, resource policy, diagnostics, host resources, attention and roadmap capabilities; operational docs specify failure/recovery. **Historical implementations exist.** | Current diagnostics, events, graph identities, worker states and health projections exist in parts. They are not exposed as a unified, bounded Grace occupational toolbox. **Partial and disconnected.** |
| Operations escalation vs cognitive escalation | Localization roadmap §5.7 distinguishes an operational exception that Grace routes to authority from a reasoning-provider escalation that may improve analysis but cannot grant authority. **Documented.** | Provider routing and deferred reasoning exist. This does not itself implement the Director of Operations exception workflow or capability dispatch. **Reasoning routing implemented; operational escalation integration incomplete.** |
| Hardware/resource controls | Historical records discuss resource planning and named controls; documented WoL/SSH procedures exist in older operations material. This does not establish present readiness or authorize use. | No evidence in this reconciliation that Grace's current operational pipeline invokes those controls. **Not verified as integrated; out of immediate restoration scope.** |

## 6. Three cooperating model systems, one Grace

The model arrangement is an implementation topology, not an institutional hierarchy:

- **0.6B autonomic layer:** continuously available for acknowledgments, low-cost status, monitoring signals, queue preservation, and deterministic readiness coordination. It must not invent complex answers or construct arbitrary commands. Its control loop should rely on persisted state and allowlisted service operations.
- **30B vision/interim layer:** supports actual image-grounded tasks when the image input path is enabled and cautious evidence-grounded interim conversation when suitable. It marks provisional results and defers complex or consequential reasoning to 80B. In the current browser conversation contract, the input is text; the 30B vision model is available at an inference endpoint but browser image-grounding is not established by this path.
- **80B reasoning layer:** preferred for substantive reasoning, Engineering planning, and evaluation. It receives the same Grace office identity, conversation/objective correlation, relevant authoritative facts, CME state, capability results, and authority boundaries as the other stages, filtered to the current task. It may recommend an action or request a capability; server-side authority services decide whether that action can occur.

All three share one persisted conversation, objective/assignment records, process correlations, and event/state authority. Each response records the actual provider/model and whether it is provisional or final. A model transition retains the original objective, relevant context and provenance, but never carries implicit execution permission from one model to another. An unavailable or busy 80B leaves a request pending when that capability is required; it does not silently downgrade the requirement. Vision observations should enter as typed, provenance-bearing results rather than as an unqualified model-to-model chat.

### Current coordination finding

The deployed readiness router has 0.6B, 30B and 80B providers attached to the same conversation service. The 80B real conversation path has succeeded and persisted served-model provenance. The router uses capability/stage selection and deferred-request persistence. This establishes model routing and continuity for text conversation, not full three-system operational coordination.

Current conversation prompts identify Grace generically (“the resident bound to this office”) and provide limited recent text history. The 80B stage prompt identifies a “substantive reasoning layer” and prohibits claiming actions/authority. It does not inject the historical Director of Operations profile, current verified duties, resource/CME state, or results from autonomic/vision capabilities. The conversation code's ordinary-chat prompt also says not to create, approve, or claim a work order. The prohibition is appropriate for preventing unauthorized actions but is too broad if it is interpreted to prevent Grace from formulating an authorized proposal. Since the active office metadata itself says “AI director of engineering,” the observed denial of operations/Chief of Staff duties is best explained by missing/misleading role context and restrictive generic prompt construction, not by historical authority defining a different office. This is an evidence-based diagnosis; the exact model-internal cause cannot be proven from the response alone.

## 7. Current implementation and live evidence

### Verified live during the latest available check (2026-10-14)

- Dashboard release `98287c9a344f8ead203b55d50366b02014d9ce62` was the last confirmed active release.
- Grace's office binding points to `implementation:grace:readiness-router:608aa519346c` at binding revision 9; the occupant remains `occupant:grace:initial`.
- Live office role text was observed as **“AI director of engineering”**, inconsistent with the canonical historical role.
- Camrui 0.6B service was active and health returned HTTP 200 with model `qwen3-0.6b-q8_0-local`.
- OCTO1 30B and 80B model APIs returned HTTP 200 and their model-discovery responses identified the expected configured model paths. This was API readiness evidence at observation time, not independent proof of remote systemd supervision.
- The standalone `riverview-grace-execution.service` was not installed (`LoadState=not-found`).
- One prior 80B deferred request was completed and persisted with the actual 80B served-model provenance. That proves the browser/conversation model path, not the full Engineering workflow.

These are time-bounded observations, not guarantees about present service state.

### Implemented in current source, but not equivalent to operational commissioning

- Office/occupant/implementation are separate concepts in the Authority Registry.
- Conversation authorization checks current office binding and exact grants server-side.
- Conversation messages and response provenance persist.
- The readiness router can select 0.6B, 30B, and 80B, defer an 80B-required request, and resume it with bounded completion and duplicate controls.
- Objective, assignment, resource/capability, worker, verification, and process-graph components exist in source.
- The Codex adapter is bounded and intended to run with supervised ChatGPT-subscription-authenticated CLI execution, not an API key.

### Missing, incomplete, or unverified

- Canonical Director of Operations identity is not consistently recorded in current engineering docs/live office metadata.
- A single authoritative role-and-responsibility profile is not included in prompts or task context.
- Conversation reasoning cannot yet select and invoke the current bounded occupational capabilities with typed results and continuation.
- Live state and verified institutional facts from CME, resources and diagnostics are not routinely grounded into Grace's conversation.
- 30B browser image input and provenance-bearing vision observation flow are not established.
- Persistent Grace execution service is not installed; actual autonomous chat-originated objective → Engineering dispatch → Codex artifact → independent verifier → Grace evaluation has not been commissioned.
- Production use of hardware wake/shutdown capabilities through the current authorized dispatcher is not verified and is not part of the immediate sequence.

## 8. Migration gap matrix and restoration sequence

| Gap | Evidence | Smallest restoration |
|---|---|---|
| Office title and role drift | Historical role sources say Director of Operations; current `CORE_CONTRACT.md`, roadmap and observed live office text say AI director of engineering. | Correct canonical engineering docs first. Reconcile live `office_role` through an audited AuthorityRegistry operation with current revision/CAS and preserve occupant, grants, implementation binding and history. Do not use direct SQL or alter authority scope. |
| Role context absent at inference | Current prompts carry generic identity/stage guidance; they omit institutional duties and boundaries. | Add a versioned, authoritative Grace role profile to the existing prompt/context builder. Include responsibilities and delegation boundaries, not raw grants or secrets. Apply consistently to all model stages. |
| Chat disconnected from occupational capabilities | Historical repository has bounded occupational broker/tool-result continuation; new-core chat does not use it. | Port/adapt only the required named read/plan capabilities to current `CapabilityRegistry` and existing authority/CME APIs. Reuse schemas and event mechanisms; do not recreate historical tables or a parallel broker. |
| Grace cannot autonomously progress through Engineering | Current pipeline/Codex adapter source exists, but persistent runtime is absent and chat proposal action is disconnected. | Commission the existing persistent worker path with exact service identity/grants; connect Grace-authored proposal → Steward review/approval where required → existing intake → dispatch. Already authorized routine steps should continue without repeated mechanism approval. |
| No unified observation/recovery loop in chat | CME/events/diagnostics exist in parts, but no verified operational loop joins them to Grace conversation and assignment continuation. | Have Grace consume typed event/state projections; add durable correlation, lease/idempotency checks, exception transitions, verifier result and same-conversation continuation using existing graphs. |
| 30B is not proven as vision in website flow | 30B endpoint is healthy; current chat input is textual. | Add a narrowly scoped, permission-checked image request path and typed result provenance only when needed; do not delay Director-of-Operations text/work restoration. |
| Three model contexts are not coordinated | Shared conversation exists, but model stage prompts lack shared role/operational facts and no vision/autonomic result contract is wired. | Keep one resident and shared durable IDs; pass task-scoped, provenance-bearing facts/results between stages; record provider/model, stage, provisional/final status, objective correlation and authorization decisions. |

### Recommended order

1. **Document and canonically name the office** in the new engineering repository. Reconcile the live title only through an authorized AuthorityRegistry update; leave current binding and grants unchanged.
2. **Supply role context** through the existing prompt builder, separating role, office responsibility, task facts, model stage and authority restrictions. Test that Grace accurately identifies herself and the boundaries without claiming unperformed actions.
3. **Reconnect bounded occupational capabilities** by adapting the historical package/broker pattern to current APIs. Start with verified read-only CME/objective/resource/diagnostic projections and typed proposal creation. Every call must remain grant-checked server-side.
4. **Commission existing execution path** under its dedicated service identity and exact grants. Connect proposal review to intake, then CME lease/dispatch, supervised Codex execution, artifact capture, independent verification and return to the original conversation.
5. **Add model-result coordination**: autonomic status/events, optional vision observations, and 80B reasoning share correlated records and provenance. Maintain the required 80B stage; defer instead of downgrading.
6. **Verify one operational cycle** with a natural-language Steward objective, Grace-authored plan, approved work order, real executor artifact, independent evidence, and Grace's accept/correct/escalate continuation. Then expand only as the established roadmap authorizes.

## 9. Safety and decision boundaries

This reconciliation makes no authority grant, office binding change, role metadata change, production deployment, service activation, model reconfiguration, or conversation-record mutation. It does not claim the missing persistent execution service is safe to activate without identity, exact grants, commissioning, and verification. Historical code is evidence of prior design and implementation, not automatic authorization to revive old permissions or schemas.

The first concrete institutional correction is to restore the Director of Operations title and responsibility context through the documented source and authorized registry workflow. The first operational restoration is to connect Grace's bounded capability selection and CME observation to the already-existing assignment and execution path. Both retain the Steward's final authority and current exact-grant enforcement.
