<!--
Riverview~ Controlled Document
File: docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md
Component: STEWARD-DASHBOARD / WEBSITE
File Revision: 1.0.29
Purpose: Consolidate traceable website improvement observations and separate them from accepted requirements and completed work
Authority: Backlog recovery only; no new product requirement or acceptance decision
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Recover and prioritize documented website observations
Changed: 2026-10-15 UTC | RV-WEBSITE-PL027 | Record completed branch implementation and pending integration review
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Clarify additive documentation overlap with PR #40 and active ownership boundaries
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Record controlled document revision history
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Note source ID mismatch in workflow rendering addendum
Changed: 2026-10-15 UTC | RV-WEBSITE-PL025 | Record isolated account-cookie browser regression and live acceptance access blocker
Changed: 2026-10-15 UTC | RV-WEBSITE-PL026 | Record in-view workflow interaction documentation
Changed: 2026-10-15 UTC | RV-WEBSITE-PL025 | Link final styled browser evidence and record focused validation results
Changed: 2026-10-15 UTC | RV-WEBSITE-PL013 | Record bounded diagnostic coverage audit findings
Changed: 2026-10-15 UTC | RV-WEBSITE-PL028 | Record notification summary contract gap and website-scope blocker
Changed: 2026-10-15 UTC | RV-WEBSITE-PL004 | Complete assignment graph/node and diagnostic-linkage audit and record scoped UI correction
Changed: 2026-10-15 UTC | RV-WEBSITE-PL028 | Specify missing notification fields, contract source and acceptance criteria
Changed: 2026-10-15 UTC | RV-WEBSITE-PR42-RECONCILE | Reconcile website branch with PR #43 integration head without merging PR #42
Changed: 2026-10-15 UTC | RV-WEBSITE-PL008 | Reconcile loaded worker inventory counts and separate registration from heartbeat state
Changed: 2026-10-15 UTC | RV-WEBSITE-PL006 | Explain overview projection and subsystem status semantics
Changed: 2026-10-15 UTC | RV-WEBSITE-PL011 | Add explicit older/newer event pagination and stable sequence handling
Changed: 2026-10-15 UTC | RV-WEBSITE-PL007 | Record effective heartbeat threshold as unavailable to website and block on source contract
Changed: 2026-10-15 UTC | RV-WEBSITE-PL012 | Show available event provenance and record task/diagnostic source limits
Changed: 2026-10-15 UTC | RV-WEBSITE-PL014 | Explain status projection refresh and explicit source transitions
Changed: 2026-10-15 UTC | RV-WEBSITE-PL016 | Complete same-tab documentation return behavior in the isolated browser.
Changed: 2026-10-15 UTC | RV-WEBSITE-PL010/015/020/023/024 | Record readiness, control, menu and milestone guidance implementation.
Changed: 2026-10-15 UTC | RV-WEBSITE-PL019 | Fix composer overlap and narrow-screen overflow with isolated browser evidence.
Changed: 2026-10-15 UTC | RV-WEBSITE-PL036 | Add accessible collapsible navigation and retain compact health/snapshot controls.
Changed: 2026-10-15 UTC | RV-WEBSITE-PL003 | Resolve canonical task titles from exact graph/node references and preserve stable identifiers.
Changed: 2026-10-16 UTC | RV-WEBSITE-PL029 | Separate visible rendering and receipt from person-seen and decision state; record missing API lifecycle fields.
Changed: 2026-10-16 UTC | RV-WEBSITE-PL038 | Add a searchable registry traceability catalog and record freshness/coverage source limits.
Changed: 2026-10-16 UTC | RV-WEBSITE-PUNCH-LIST-AUDIT | Classify all 41 captured items against implementation, evidence, ownership, and external dependencies.
Changed: 2026-10-16 UTC | RV-WEBSITE-PR45-RECONCILE | Reconcile the website branch with current integration PR #45 while preserving its retry behavior.
Changed: 2026-10-16 UTC | RV-WEBSITE-PL038-POST-PR45 | Record integrated browser regression and updated 459-node graph baseline.
Changed: 2026-10-16 UTC | RV-WEBSITE-PR46-RECONCILE | Update PR #42's integration baseline through PR #46 without editing resident-reasoning changes.
Changed: 2026-10-16 UTC | RV-WEBSITE-PR42-INTEGRATION-RECONCILE | Reconcile through PR #63, distinguish review/deployment gates, and prepare production acceptance.
Changed: 2026-10-16 UTC | RV-WEBSITE-PR42-EXACT-CI | Record exact-head CI/browser evidence and current draft review gate.
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Record the authenticated self-describing snapshot implementation, workflow exports, evidence and production boundary.
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Reconcile documentation baseline to PR #64 and record final cross-viewport browser evidence.
Changed: 2026-10-16 UTC | RV-WEBSITE-PR42-PRODUCTION-ACCEPTANCE | Record feature-level production acceptance and correct stale release checklist language.
History: Git
-->
# Recovered Riverview website punch list

**Captured source:** [`Riverview_Steward_Punch_List_2026-10-13.md`](Riverview_Steward_Punch_List_2026-10-13.md), including its 2026-10-13 review addenda.  
**Baseline:** integration branch `codex/grace-conversation-ui-refinement` at PR #64 merge `8fed8d4b78d9a1d7bb8dc451a6e292d6049831b8`, retaining PRs #44–#46 and #62/#63; website work branch `codex/website-improvements`.
**Purpose:** consolidate the recorded website observations without promoting them to accepted requirements. The original PL-NEW identifiers and stated priorities are retained.

## Requirement and implementation boundaries

- The active roadmap requirement for M3.1 is the read-only status projection, truthful status/freshness, safe diagnostic rendering, canonical workflow visualization, and navigable decisions. See [`ROADMAP.md`](../ROADMAP.md) and [`M3.1-001_REVISION_RECORD.md`](../development/M3.1-001_REVISION_RECORD.md). Scoped M3.1 technical acceptance is recorded; the full component DoD remains open.
- PL-NEW-001 through PL-NEW-041 are captured observations and desired outcomes from the Steward punch list. The source says they are not implementation orders; PL-NEW-041 also has an explicit acceptance specification. The later assignment commissions PL-NEW-041 and adds PL-NEW-042 as a distinct follow-up; this does not turn the other captured rows into new roadmap requirements.
- One review addendum calls the previously failing workflow-rendering observation “PL-NEW-024,” while the source ID table assigns PL-NEW-024 to milestone labeling and PL-NEW-025 to workflow loading. This recovery maps the observation by subject to PL-NEW-025 and preserves PL-NEW-024's table-defined milestone scope.
- Existing implementations are listed separately below. Their existence does not close a punch-list item unless the recorded outcome and acceptance evidence match it.
- PR #40 implements durable SSE conversation streaming and deferred-response recovery. It is part of this branch's integration baseline and is compatibility-sensitive; this website work does not rebuild it.

## Prioritized traceable backlog

Priority labels and wording below follow the source punch list. “Captured” means recorded, not approved or complete. Where the source addenda provide a later observation, that observation is called out without silently rewriting the original row.

| ID | Area | Recorded outcome | Priority | Record state / qualification |
|---|---|---|---|---|
| PL-NEW-001 | Assignments | Show purpose, request, expected deliverable, result, acceptance, and evidence in readable language. | High | **Blocked on integration-owned assignment/work-order source contract.** `/api/v1/assignments` and detail omit `purpose`, `original_request`, `expected_deliverable`, `result`, `acceptance_criteria`, and structured `evidence[]`. Required source: persisted assignment intake/verification record with field provenance, privacy limits and explicit absence states. Acceptance: show those fields from authoritative persisted sources, with unavailable/empty states distinguished; never infer them from workflow state/event names. No Engineering intake/CME/backend contract change is made here |
| PL-NEW-002 | Assignments | Explain blocked-task evidence gaps, owner, and unblock action. | High | **Blocked on integration-owned assignment/blocker source contract.** Current assignment projection lacks `blocked_reason`, `missing_evidence[]`, `responsible_party`, and `unblock_action` plus source references/provenance. Required source: persisted blocker/decision record from assignment intake and the Engineering integration. Acceptance: display owner and the specific evidence/action from that record; show explicit absence/unavailable states; never synthesize a reason from assignment state. No Engineering intake/backend change is made here |
| PL-NEW-003 | Assignments | Pair human-readable titles with stable technical IDs. | Medium | Implemented: exact persisted graph/node IDs resolve their registered canonical node label in list and detail; stable assignment/graph/node IDs remain visible; absent/unresolved mappings stay explicit. Isolated Firefox verified; production acceptance pending. Evidence: [`PL-NEW-003 browser report`](../../evidence/checkouts/WEBSITE-PL003/20261015T233000Z-canonical-task-title/browser-acceptance.json) |
| PL-NEW-004 | Assignments | Audit canonical graph-node and diagnostic linkage in assignment detail. | High | Audit complete; persisted IDs and safe diagnostic link now appear in website assignment detail on this branch; isolated browser and focused checks recorded; integration review pending |
| PL-NEW-005 | Overview | Match Current Work titles, purposes, and status to Assignments. | High | Title/state use the same assignment projection and canonical graph label; purpose remains unavailable with PL-NEW-001. **Blocked on the assignment purpose/source contract** described there; production acceptance pending |
| PL-NEW-006 | Overview | Explain event cursor, authoritative projection, CME, worker states, and Grace execution. | Medium | Implemented in overview guidance and cookbook on this branch; isolated Firefox and focused checks pending final evidence package; integration review pending |
| PL-NEW-007 | CME | Document heartbeat thresholds and health/staleness criteria in the UI. | Medium | **Blocked on integration-owned runtime-threshold contract.** Dashboard code uses `RIVERVIEW_STALE_AFTER_SECONDS` (default 30) for active worker/CME/Grace heartbeat classification, but the effective environment value is not returned by `/api/v1/status`; the separate CME monitor also has its own worker-freshness setting. The website cannot claim the production/configured threshold from the default. Required source: effective server and CME freshness values exposed by their owning API/config contract, with provenance. Acceptance: show each effective threshold beside the corresponding policy and document stale/unknown/unverified/inactive meanings; verify values against the running configuration in the controlled integration process. No backend/CME/runtime configuration change is made here |
| PL-NEW-008 | Workers | Reconcile summary and full inventory, including inactive workers and registered/active/stale/unknown distinctions. | High | Implemented on this branch; loaded-page counts reconcile after pagination; registration and heartbeat states are separate; responsive Firefox evidence and focused test recorded; integration review pending |
| PL-NEW-009 | Workers | Show worker identity, capabilities, task, host, heartbeat, execution, and failures. | High | **Blocked on integration-owned worker inventory contract.** Current `/api/v1/workers` exposes `worker_id`, `active`, derived `status`, `last_heartbeat_at`, `heartbeat_age_seconds`, `active_leases`, and `source=assignment_leases`. Missing: capabilities, host/worker location, current task identity/context, execution detail/progress, and failure/recovery history. The worker registry/lease integration owner must define authoritative sources, privacy boundaries, field provenance and versioned API shape. Acceptance: each field is sourced from that owner, absent values are explicit, task/host/failure details are privacy-filtered, worker registration remains distinct from heartbeat health, and the dashboard reports bounded/paginated totals truthfully. No backend/worker contract change is made here |
| PL-NEW-010 | Grace execution | Explain chat-operational versus execution-not-initialized status and prerequisites. | High | Implemented in overview/objective guidance; isolated Firefox verifies separate chat/execution state and safe prerequisites; production acceptance pending |
| PL-NEW-011 | Activity | Add bidirectional database-backed pagination with stable cursors. | High | Implemented on this branch using existing exclusive `before_seq` / `after_seq` API cursors; page order and duplicate suppression pass isolated Firefox and focused tests; integration review pending |
| PL-NEW-012 | Activity | Show human-readable event meaning, causation, task, and diagnostic evidence. | High | Event cards now show humanized event type, timestamp, sequence/event ID, actor, correlation/causation, payload schema, and assignment link when present. Event API has no separate task ID, payload body, or event-specific diagnostic reference; those remain explicitly unavailable and cannot be inferred. Dashboard cookbook is linked as a general troubleshooting entry. Browser and focused checks pass; further event-specific diagnostics require an integration-owned source contract |
| PL-NEW-013 | Diagnostics | Audit code-to-graph, cookbook, and diagnostic-catalog coverage. | High | Audit complete; exact-match traceability gaps recorded in [`PL-NEW-013 diagnostic coverage audit`](../development/PL-NEW-013-DIAGNOSTIC-COVERAGE_AUDIT.md); semantic coverage is not exhaustively classified |
| PL-NEW-014 | Dashboard | Explain projection refresh, cache, freshness, and status transitions. | Medium | Implemented in overview guidance and dashboard troubleshooting: documents no-store refresh, source observation time, healthy/not-initialized/unavailable meanings, and separate event/detail fetches; isolated Firefox and focused tests pass; integration review pending |
| PL-NEW-015 | Grace objectives | Explain schema/migration initialization, refresh semantics, and commissioning prerequisites. | High | Implemented in objectives view with explicit `not_initialized` state and migration/CME/worker commissioning boundary; isolated Firefox verified; production acceptance pending |
| PL-NEW-016 | Navigation | Prevent documentation-tab/back navigation from creating duplicate dashboard tabs. | Medium | Implemented and isolated Firefox verified; exact two-tab reuse passes. Production acceptance awaits controlled integration/deployment. Evidence: [`PL-NEW-016 browser report`](../../evidence/checkouts/WEBSITE-PL016/20261015T212500Z-documentation-navigation/browser-acceptance.json) |
| PL-NEW-017 | Chat | Add a future multi-resident selector. | Later | Captured; explicitly future |
| PL-NEW-018 | Chat | Add meaningful editable conversation titles and searchable persistent history. | High | Captured |
| PL-NEW-019 | Chat | Fix transcript/composer clipping and last-message visibility. | High | Composer remains in document flow below the independently scrollable transcript; 40-message isolated Firefox run confirms final message visibility and no horizontal overflow at a 500px CSS viewport. Production acceptance pending. Evidence: [`PL-NEW-019 passing run`](../../evidence/checkouts/WEBSITE-PL019/20261015T224500Z-conversation-layout/browser-acceptance.json) |
| PL-NEW-020 | Chat | Explain or remove Disconnect, Refresh history, line-break, and recovery controls. | Medium | Control effects and newline shortcuts explained in-view; isolated Firefox verified; production acceptance pending |
| PL-NEW-021 | Chat | Support authorized work-order creation and deliverable inspection from conversation. | High | Captured; authorization and promotion rules remain governing constraints |
| PL-NEW-022 | Chat | Provide secure bounded file/image upload, drag/drop, and vision routing. | High | Captured |
| PL-NEW-023 | Chat | Distinguish available menu actions from unavailable/future actions. | Medium | Existing menu explicitly disables unavailable/future actions; isolated Firefox verifies all seven action states; production acceptance pending |
| PL-NEW-024 | Milestones | Distinguish dashboard M3.1 release label from roadmap, deployment, and commissioning status. | Medium | Header now calls M3.1 the dashboard milestone and overview separates roadmap/deployment/commissioning; isolated Firefox verified; production acceptance pending |
| PL-NEW-025 | Workflows | Verify authenticated account-cookie registry loading and preserve deployed browser acceptance evidence. | High / acceptance pending | Isolated cookie-only registry/detail regression passes; [integration browser report](../../evidence/checkouts/WEBSITE-PR42-INTEGRATION/20261016T164500Z-account-cookie/browser-acceptance.json). PR #42 is deployed. Production dashboard bearer workflow reads and graph rendering pass, but a positive account-cookie session has not been tested; unauthenticated reads correctly returned 401. Production account-cookie acceptance remains **UNVERIFIED**. [Production evidence](../../evidence/checkouts/WEBSITE-PR42-PRODUCTION/20261016T172206Z-928649b/production-dashboard-browser-acceptance.json) |
| PL-NEW-026 | Workflows | Document selector, canvas, node types/legend, selection, revisions, and interaction semantics. | Medium | Implemented in viewer and cookbook on this branch; integration review pending |
| PL-NEW-027 | Workflows | Navigate cross-workflow jumps to the exact target and provide return navigation preserving context. | Medium | Implemented on this branch: exact target workflow/node focus and return to the source jump; isolated browser evidence recorded; production acceptance pending |
| PL-NEW-028 | Notifications | Show source assignment, required action, reason, priority/deadline, and details before acknowledgment. | High | **Blocked on integration-owned notification/CME/API contract.** Current response has `assignment_id`, `event_type`, fixed generic `summary`, source/queue/delivery/acknowledgment timestamps, and optional decision request ID/status/version. Missing: explicit `required_action`; `rationale`; `priority`; optional `deadline` with an explicit absent state; and structured `actionable_details` (what evidence or step is needed). `source_event_id` identifies a source event but the API omits its authoritative detail payload. The source owner must define these fields from the CME source event/condition and applicable assignment or decision policy, expose a versioned contract through the notification API, and document field provenance. Acceptance: before enabling acknowledgment, every notice shows its source assignment (or an explicit service-level label), required action, rationale, priority, deadline value or explicit no-deadline state, and actionable details; unavailable fields stay explicitly unavailable; values link to the source event/contract; no text is inferred from event type; acknowledgment remains receipt-only and cannot resolve a decision. No website/CME/backend contract changes are made while blocked |
| PL-NEW-029 | Notifications | Distinguish delivered, seen, acknowledged, approved, denied, and resolved; acknowledgment grants no authority. | High | Available UI states are separately displayed and browser verified. **Full outcome blocked:** notification source lacks `seen_at`/`seen_by` and the decision API lacks terminal outcome plus actor/time/provenance and a decision-resolution operation. `attention_resolved` is a condition event, not decision resolution. Acceptance requires authoritative lifecycle states and source provenance; receipt must remain separate. No contract is invented |
| PL-NEW-030 | Notifications | Reconcile legacy Windows/Estate audio with Camrui and report supported routes. | High | Captured; source evidence says these are not established as equivalent |
| PL-NEW-031 | Notifications | Propose layered visible/audio/phone attention with escalation, retries, quiet hours, and storm prevention. | High | Captured proposal |
| PL-NEW-032 | Notifications | Provide history, detail, source links, receipt states, and safe bulk triage/archive. | Medium | Captured |
| PL-NEW-033 | Go-live lifecycle | Define controlled test-to-production transition with archive, audit, and backup; no indiscriminate flush. | High | Captured |
| PL-NEW-034 | Maintenance | Add authorized settings for retention, archive, backup, cleanup preview, export/restore, and permissioned irreversible actions. | High | Captured |
| PL-NEW-035 | Resources | Add an initially read-only Resources/Capabilities surface for hosts, models, tools, dependencies, readiness, performance, power, and wake controls. | High / later milestone | Captured; later-milestone qualifier retained |
| PL-NEW-036 | Navigation | Add collapsible sidebar with compact icon state and accessible expansion; retain health/snapshot affordances. | Medium | Implemented persisted compact/expanded state, accessible labels/ARIA, and visible health/snapshot affordances; Firefox verified; production acceptance pending. Evidence: [`PL-NEW-036 browser report`](../../evidence/checkouts/WEBSITE-PL036/20261015T231000Z-collapsible-navigation/browser-acceptance.json) |
| PL-NEW-037 | Global health | Show segmented model/host readiness, selected versus merely online provider, and accessible textual explanation. | Medium | Captured |
| PL-NEW-038 | Documentation | Replace fixed diagnostic links with searchable indexed catalog of per-component troubleshooting, workflows, failure/recovery, provenance, freshness and test coverage. | High | **Partial website implementation; full acceptance blocked on authoritative freshness/coverage sources.** Searchable workflow, typed node, component-document, provenance, and declared test/evidence references are implemented and isolated-browser verified. Existing registry references do not provide freshness policy/value or semantic test-coverage outcomes. Required source: integration-owned versioned graph/evidence metadata or an authoritative linked coverage record with provenance. Acceptance: searchable, component-linked freshness guidance and attributable test coverage/outcomes; declared paths alone remain traceability, not a pass/coverage claim. Post-PR #45 regression evidence: [`PL-038 report`](../../evidence/checkouts/WEBSITE-PL038/20261016T023000Z-post-PR45-regression/browser-acceptance.json). Production acceptance of the implemented UI is also pending |
| PL-NEW-039 | Automated QA | Evaluate seeded role-based audit precedent and add authenticated browser route/interaction tests as a distinct stage. | High / proposal | Captured proposal; CueMastery source findings are historical evidence only |
| PL-NEW-040 | Automated QA | Define test-account lifecycle, safe permissions, scheduled/post-deploy runs, outcome states, regression detection, and historical reports. | High / proposal | Captured proposal |
| PL-NEW-041 | Dashboard snapshots / Workflows | Include every website workflow's status and website-faithful visual, structured definitions, cross-references, and all required dashboard sections in a recoverable snapshot. | P1 | Implemented as one authenticated downloadable offline ZIP; isolated Firefox fixture passed. Production installation/acceptance is pending; the current user's permissions are preserved and omitted/unavailable captures are explicit. |
| PL-NEW-042 | Workflow viewer | Add initial fit-to-screen, zoom, pan, reset, and preferably full-screen navigation. | Medium / follow-up | Added as a separate bounded viewer improvement; deferred until after PL-NEW-041 snapshot delivery. Full-graph export does not depend on viewer zoom or scroll. |

### Full punch-list audit (41 recovered source IDs plus PL-NEW-042)

Disposition uses the requested categories. “Implemented but awaiting production acceptance” means the branch implementation passed its isolated checks; it is not a claim of release acceptance. A blocked row may still have a useful partial website presentation. Captured proposals and later milestones remain visible in the source list, but are not promoted to implementation requirements.

| ID | Audited disposition | Evidence, qualification, or exact dependency |
|---|---|---|
| PL-NEW-001 | Blocked by documented external dependency | Assignment intake/verification source must provide `purpose`, `original_request`, `expected_deliverable`, `result`, `acceptance_criteria`, structured `evidence[]`, provenance/privacy boundaries, and explicit absent states. Assignment/Engineering integration owns the source. |
| PL-NEW-002 | Blocked by documented external dependency | Assignment blocker record must provide `blocked_reason`, `missing_evidence[]`, `responsible_party`, `unblock_action`, and provenance. Assignment intake/Engineering integration owns it. |
| PL-NEW-003 | Implemented but awaiting production acceptance | Exact registered graph/node match supplies canonical title; IDs retained; isolated Firefox: [`PL-003 report`](../../evidence/checkouts/WEBSITE-PL003/20261015T233000Z-canonical-task-title/browser-acceptance.json). |
| PL-NEW-004 | Implemented but awaiting production acceptance | Nullable graph/node IDs and safe diagnostic reference are shown without inferring live position; isolated browser and focused tests recorded under `evidence/checkouts/WEBSITE-PL004/`. |
| PL-NEW-005 | Blocked by documented external dependency | Title/state share assignment projection; purpose and outcome fields remain blocked by PL-001's assignment source. |
| PL-NEW-006 | Implemented but awaiting production acceptance | Overview explains event cursor, read-only projection, independent subsystem health and Grace chat/execution boundary; synthetic Firefox evidence in `WEBSITE-CLARITY`. |
| PL-NEW-007 | Blocked by documented external dependency | Effective runtime heartbeat thresholds and their provenance are not returned by status/CME sources. Integration must expose each actual policy value; dashboard default is not production truth. |
| PL-NEW-008 | Implemented but awaiting production acceptance | Loaded-page totals and registration/heartbeat distinctions pass isolated Firefox and focused test in `evidence/checkouts/WEBSITE-PL-UI-REGRESSIONS/`. |
| PL-NEW-009 | Blocked by documented external dependency | Worker source lacks capabilities, host/location, current task/context, execution/progress, and failure/recovery records. Worker registry/lease integration must define provenance, privacy, and versioned fields. |
| PL-NEW-010 | Implemented but awaiting production acceptance | Overview/objective guidance distinguishes responsive chat from durable execution and names safe prerequisites; isolated Firefox verified in `WEBSITE-CLARITY`. |
| PL-NEW-011 | Implemented but awaiting production acceptance | Older/newer pagination uses existing exclusive sequence cursors, stable ascending order and deduplication; isolated Firefox evidence in `WEBSITE-PL-UI-REGRESSIONS`. |
| PL-NEW-012 | Blocked by documented external dependency | Available event provenance is displayed. Event source must add a separate task identity and event-specific diagnostic reference with source provenance; event payload/type cannot be used to infer either. |
| PL-NEW-013 | Verified complete | Bounded exact-match audit is recorded in [`PL-013 diagnostic coverage audit`](../development/PL-NEW-013-DIAGNOSTIC-COVERAGE_AUDIT.md). It explicitly does not claim semantic coverage from identifier matches. |
| PL-NEW-014 | Implemented but awaiting production acceptance | Refresh/cache/freshness and source-state meanings are documented in the overview and cookbook; isolated Firefox evidence in `WEBSITE-CLARITY`. |
| PL-NEW-015 | Implemented but awaiting production acceptance | Not-initialized guidance explains safe migration/schema checks and separate commissioning; isolated Firefox verified in `WEBSITE-CLARITY`. |
| PL-NEW-016 | Implemented but awaiting production acceptance | Named dashboard/documentation tabs and return navigation pass exact two-tab Firefox assertions; [`PL-016 report`](../../evidence/checkouts/WEBSITE-PL016/20261015T212500Z-documentation-navigation/browser-acceptance.json). |
| PL-NEW-017 | Superseded or no longer applicable | The captured source explicitly labels multi-resident selection “Later”; no present single-resident Grace workflow requirement authorizes adding it. |
| PL-NEW-018 | Blocked by documented external dependency | Existing list returns at most 25 conversations with IDs/timestamps and no title/search/pagination contract. Persistent editable titles and complete history search require an owner-scoped title update plus searchable/paginated history-summary contract. Resident conversation integration owns it; no local-only title is represented as durable metadata. |
| PL-NEW-019 | Implemented but awaiting production acceptance | 40-message synthetic Firefox run verifies transcript scroll, final-message visibility, composer flow and no horizontal overflow at Firefox's 500px viewport; [`PL-019 report`](../../evidence/checkouts/WEBSITE-PL019/20261015T224500Z-conversation-layout/browser-acceptance.json). |
| PL-NEW-020 | Implemented but awaiting production acceptance | Disconnect, refresh, newline and session/history effects are explained; Firefox verified in `WEBSITE-CLARITY`. |
| PL-NEW-021 | Blocked by documented external dependency | Work-order intake/promotion and deliverable inspection are owned by Codex 1 Engineering integration. Preserve the integrated PR #44 behavior; no changes to its execution or authorization. |
| PL-NEW-022 | Blocked by documented external dependency | Secure upload/vision needs an approved upload route, type/size and content validation, storage/retention/privacy contract, authorization boundary, and vision-routing source. Integration/backend/worker owners must define these. |
| PL-NEW-023 | Implemented but awaiting production acceptance | Seven chat menu actions are verified; unsupported actions remain disabled and labeled; isolated Firefox in `WEBSITE-CLARITY`. |
| PL-NEW-024 | Implemented but awaiting production acceptance | M3.1 is identified as dashboard milestone; roadmap, deployed release and commissioning are separately worded; isolated Firefox in `WEBSITE-CLARITY`. |
| PL-NEW-025 | Implemented but awaiting production account-session acceptance | Isolated account-cookie browser checks pass. The production release is installed and its dashboard bearer flow is browser-verified; an unauthenticated account-session request returned the expected 401. Positive login and cookie-only graph access remain unverified pending Steward sign-in. Evidence: [`production browser report`](../../evidence/checkouts/WEBSITE-PR42-PRODUCTION/20261016T172206Z-928649b/production-dashboard-browser-acceptance.json) and `evidence/checkouts/WEBSITE-PL025/20261015T-account-cookie-browser-final/`. |
| PL-NEW-026 | Implemented but awaiting production acceptance | Selector, canvas, node/legend/revision semantics and interactions are described in the viewer/cookbook; isolated evidence is recorded in the PL-026 checkout. |
| PL-NEW-027 | Implemented but awaiting production acceptance | Exact cross-workflow target focus and return-to-source behavior are implemented; isolated browser evidence: `evidence/checkouts/WEBSITE-PL027/20261015T193400Z-workflow-navigation/`. |
| PL-NEW-028 | Blocked by documented external dependency | CME/notification source must provide `required_action`, `rationale`, `priority`, `deadline` with an explicit no-deadline state, and structured `actionable_details`, sourced from the authoritative event/assignment/decision policy. Full acceptance criteria remain in the row above. |
| PL-NEW-029 | Blocked by documented external dependency | Partial lifecycle UI verified. Notification source lacks `seen_at`/`seen_by`; decision source lacks terminal outcome, actor/time/provenance and resolve operation. `attention_resolved` is not decision closure. |
| PL-NEW-030 | Blocked by documented external dependency | Ops/integration must provide an authoritative support/capability matrix for legacy Windows, Estate, Camrui and remote-PC audio routes; their equivalence is not established. |
| PL-NEW-031 | Superseded or no longer applicable | The source labels layered visible/audio/phone escalation as a proposal. No approved notification product/operations design or supported route authorizes implementation. |
| PL-NEW-032 | Blocked by documented external dependency | Notification integration must provide paginated history/detail/source linkage plus explicit receipt and safe bulk/archive operation contracts. |
| PL-NEW-033 | Blocked by documented external dependency | Controlled test-to-production transition requires a governed lifecycle API, audit/backup evidence, and Steward/database operations authorization. No production data operation is within this website change. |
| PL-NEW-034 | Blocked by documented external dependency | Retention/archive/backup/cleanup/export/restore requires an authorized maintenance API, preview/irreversible-operation rules, Steward approval, and database operations ownership. |
| PL-NEW-035 | Superseded or no longer applicable | Source marks the Resources/Capabilities surface as a later milestone; host/model/power/wake observations also depend on prohibited OCTO resource data. No such surface is currently authorized. |
| PL-NEW-036 | Implemented but awaiting production acceptance | Persisted accessible collapsed/expanded rail retains health and snapshot controls; [`PL-036 report`](../../evidence/checkouts/WEBSITE-PL036/20261015T231000Z-collapsible-navigation/browser-acceptance.json). |
| PL-NEW-037 | Blocked by documented external dependency | Host/model integration lacks a source for selected provider versus merely online state and segmented readiness. Any OCTO changes are prohibited. |
| PL-NEW-038 | Blocked by documented external dependency | Searchable workflow/documentation/provenance/evidence-reference UI is partially implemented and Firefox verified: [`PL-038 report`](../../evidence/checkouts/WEBSITE-PL038/20261016T020000Z-searchable-workflow-catalog/browser-acceptance.json). Full acceptance requires authoritative per-component freshness and attributable semantic test-coverage data; current graph API declares only references. |
| PL-NEW-039 | Superseded or no longer applicable | The source marks seeded role/persona evaluation and scheduled audit as a proposal, not an accepted deployment requirement. Authenticated route/interaction testing exists separately (PL-025 and this checkout); no role lifecycle or schedule is created by this punch item. |
| PL-NEW-040 | Superseded or no longer applicable | The source marks test-account lifecycle, permissions, schedules, regression and history as a proposal. It has no accepted operating owner/design; route fixtures remain ephemeral synthetic accounts. |
| PL-NEW-041 | Implemented but awaiting production acceptance | One authenticated Download Snapshot builds a versioned offline ZIP from the dynamic capability registry, the existing sanitized read-only operational snapshot, and the version-controlled `process_graphs/*/*.json` definitions. It includes per-page inventories/visual representations, bounded privacy-filtered interaction/request/error history, original graph JSON, separate authenticated runtime status, full graph SVG/PNG/detail tiles, workflow index and cross-workflow jumps. Isolated Firefox synthetic fixture passed archive/file hash checks, page/control correlation, privacy, workflow node/edge identity and offline index reconstruction; production acceptance is pending and is not claimed. See `evidence/checkouts/WEBSITE-SNAPSHOT-041/20261016T-snapshot-fixture-final3/browser-acceptance.json`. |
| PL-NEW-042 | Incomplete and actionable | The user-directed follow-up is fit-to-screen, zoom, pan, reset, and preferably full-screen workflow navigation. It is explicitly separate and does not block full-extent snapshot rendering. |

### Current implementation order and readiness

1. **PR #42:** merged as `50ed988f84398bde7aa9df5bb3f163d753748fed` against integration `af87c1a1b8ef4deeb8770c64da8bb4556bc85866`. Its tested source head is `928649bd1ff695fe9a95915647a49943ffe921fe`; exact-head CI run `38934832848` and integration merge CI run `38936851141` passed. The merge retained PRs #44–#46 and #62/#63 Engineering functionality. The versioned release is installed on Camrui as `website-pr42-928649bd1ff695fe9a95915647a49943ffe921fe`; production evidence and rollback plan are linked under `WEBSITE-PR42-PRODUCTION/20261016T172206Z-928649b/`.
2. **PL-NEW-038:** searchable graph registry and declared traceability UI are implemented and isolated-browser verified. Full item remains blocked on authoritative freshness metadata and attributable semantic test-coverage outcomes; the canonical API exposes references only. Its browser report is linked in the audit table.
3. **Independent website-scope implementations already on this branch:** PL-003/004/006/008/010/011/014/015/016/019/020/023/024/026/027/036. Isolated evidence is linked in the item rows and journal; deployed functionality was also browser-checked where it was safe and read-only. The per-item rows retain distinctions between source implementation, production evidence, and any incomplete account/backend acceptance.
4. **Next high-priority source contracts:** PL-018 resident conversation titles/history search (conversation integration); PL-001/002/005 assignment intent and blocker records (assignment intake/Engineering); PL-007/009 worker thresholds and inventory (worker/CME integration); PL-012 event task/diagnostic linkage (event integration); PL-028/029/032 notification/decision lifecycle (notification/CME integration). The exact known gaps are recorded in the audit table. No fabricated fields or backend edits are allowed in this website track.
5. **Other external blockers and deferred proposals:** PL-021 and PL-041 are Codex 1 Engineering-owned; PL-022 and PL-030/037 depend on integration/Ops resource contracts; PL-033/034 need governance and database-maintenance authority; PL-035 is a later milestone with OCTO data prohibited; PL-017/031/039/040 are captured later/proposal items, not accepted requirements.
6. **Production acceptance:** PR #42 is deployed. Camrui is this session's Ubuntu 24.04.3 runner, so the authorized release procedure ran locally with existing `sudo -n`; the earlier SSH rejection was a same-host key-auth mismatch, not a service failure. The actual LAN URL is `https://192.168.1.155/`; public DNS `riverview.ionoge.com` resolves to a separate site. Live health, navigation, graph rendering, catalog search, docs, assignment/objective visibility, and browser console checks passed. Positive account-cookie login and live conversation streaming/recovery remain unverified pending a Steward account session and safe existing-conversation acceptance.

**Snapshot exclusions and parking lot:** Do not build a global combined workflow visualization or the proposed PL-NEW-039/040 automated QA system under PL-NEW-041. Preserve the individual graph JSON/SVG/PNG/status files and cross-workflow relationship index for a future global-visualization initiative.

### Production release and acceptance checklist

The dashboard cookbook documents the manual immutable-release procedure in
[`STATUS_DASHBOARD_COOKBOOK.md`](../components/STATUS_DASHBOARD_COOKBOOK.md). PR
#42 has been merged and installed on Camrui under the Steward's explicit release
authorization. The production evidence is tied to source commit
`928649bd1ff695fe9a95915647a49943ffe921fe` and deployment ID
`website-pr42-928649bd1ff695fe9a95915647a49943ffe921fe`. The release and service
health checks below passed; remaining interactive or mutating checks are not
claimed.

Remaining production acceptance checks:

- **Authentication — PENDING:** a real account session signs in; workflow catalog index and
  detail requests authenticate through the account cookie and do not depend on a
  bearer token. Confirm the production account's permitted dashboard views.
- **Conversation streaming — PENDING:** use an existing authorized conversation; verify
  incremental SSE rendering, reconnect/replay, terminal response state, and
  deferred-response recovery. Do not create an objective as part of this check.
- **Catalog search — VERIFIED:** the production Firefox run loaded 19 workflows,
  narrowed to 5 for `grace`, and opened linked documentation/provenance. Confirm
  any additional Steward-selected search terms during interactive review.
- **Responsive layout/navigation — PARTIALLY VERIFIED:** desktop navigation and
  the narrow production view passed without horizontal overflow at Firefox's
  actual 500px minimum width. The requested 390px window was constrained to
  500px; authenticated transcript/composer behavior still needs a Steward
  session.
- **Process graph — VERIFIED:** production Firefox rendered the Steward status
  graph (42 nodes, 55 canonical edges) after awaiting the asynchronous graph
  selection; cross-workflow navigation and docs rendered with no browser errors.
- **Objective and assignment visibility — VERIFIED READ-ONLY:** one existing
  objective was `COMPLETED`; 10 assignments projected as 6 completed, 3 ready,
  and 1 blocked. A completed assignment displayed one attempt and one independent
  verification. No ID or message text is needed to claim this count.
- **Objective intake (read-only production boundary) — VERIFIED READ-ONLY:** the
  existing objective and intake state were inspected without submitting,
  retrying, or editing it. New intake success and duplicate prevention remain
  isolated-fixture checks; no production mutation was attempted.
  Production duplicate prevention or new-intake success must not be tested by
  creating a production objective; exercise those mutations only in an isolated
  PostgreSQL fixture.
- **Integration continuity — PARTIALLY VERIFIED:** current Engineering projection,
  existing objective/assignment, and all dependent services remained visible and
  active. PR #40 migrations/checksums and the exact stream-table grants match;
  live SSE/reconnect behavior was not exercised because sending a conversation
  message would mutate production state.
- **Conversation streaming:** remains unverified; use an existing authorized
  conversation only after Steward acceptance authorizes the production message.
  Isolated SSE and deferred-response recovery compatibility remains covered by
  PR #40 tests/evidence.
- **Release health/recovery — VERIFIED:** immutable package identity, previous
  release, dashboard unit state, dependent service state, and dashboard-only
  rollback plan are recorded. No rollback was required.

Production acceptance is **PARTIALLY VERIFIED** for the installed release. Live
browser acceptance verified the LAN TLS endpoint, dashboard session, navigation,
responsive layout at the harness-supported 500px viewport, workflow graph
rendering, catalog search, documentation links, current objective/assignment
visibility, and service continuity. No browser console errors were observed and
the browser acceptance report lists zero failed checks. Positive account-cookie sign-in is **UNVERIFIED**; the
no-cookie 401 was verified. End-to-end streaming/reconnect is **UNVERIFIED**
because sending a production conversation message was outside the read-only
acceptance boundary. Release identity, checksums, predecessor, rollback plan,
and service state are preserved in the production evidence. The current browser
and operational evidence is in
[`PR #42 production evidence`](../../evidence/checkouts/WEBSITE-PR42-PRODUCTION/20261016T172206Z-928649b/).
External data contracts remain blockers as listed per punch-list item; website rendering does not supply unavailable
`required_action`, `rationale`, `priority`, `deadline`, `actionable_details`,
worker-threshold/inventory, event-diagnostic, conversation-history, or catalog
freshness/semantic-coverage fields.

## Existing implementation evidence (not punch-list closure)

| Existing behavior | Evidence | Boundary |
|---|---|---|
| Read-only dashboard, bounded pages, truthful source/CME/worker states, safe cookbook rendering, and redacted operational snapshot | [`STATUS_DASHBOARD.md`](../components/STATUS_DASHBOARD.md), [`M3.1-001_REVISION_RECORD.md`](../development/M3.1-001_REVISION_RECORD.md) | M3.1 technical scope accepted; full dashboard DoD remains open |
| Authenticated canonical graph index/detail APIs and SVG workflow viewer with node identities, revisions, typed transitions, selection, and cross-workflow jump controls | Same M3.1 record; `server.py`, `workflow.js`; process-graph checks | Production graph rendered 42 nodes, 4 decisions, and 51 SVG edges without browser errors; positive account-cookie session remains unverified |
| Durable conversation SSE, reconnect/replay, terminal states, and deferred-response recovery | PR #40 merge `e897c52`; [`RESIDENT_CONVERSATION.md`](../components/RESIDENT_CONVERSATION.md); integration browser evidence | Existing compatibility behavior. Website changes must retain it; it is not a new website feature request here |
| Persistent account sessions and protected Steward/account views | Integration baseline `218cb584`; account-authentication component docs and tests; production unauthenticated-session denial returned 401 | Successful production login and account-cookie graph access need Steward sign-in; not inferred from dashboard bearer acceptance |
| Workflow registry/detail client sends same-origin credentials without requiring a recovery bearer token | `workflow.js`; isolated Firefox evidence under `evidence/checkouts/WEBSITE-PL025/` | Synthetic cookie fixture proves browser transport/rendering; production positive account-cookie acceptance remains unverified |
| Dashboard diagnostic coverage was audited across literal server errors, workflow nodes, and dashboard documentation | [`PL-NEW-013 diagnostic coverage audit`](../development/PL-NEW-013-DIAGNOSTIC-COVERAGE_AUDIT.md) | Exact-match traceability audit only; semantic coverage gaps are not presumed from missing identifier strings |

## Ownership and integration map

The website track owns dashboard presentation and navigation, primarily `status_dashboard/static/workflow.js`, `app.css`, `index.html`, and dashboard tests/docs. PR #40 also touched `status_dashboard/server.py`, `status_dashboard/static/app.js`, `tests/test_status_dashboard.py`, and dashboard component documentation for stream compatibility. This change avoids its shared behavior-code and test files; the only same-file overlaps are additive paragraphs in `STATUS_DASHBOARD.md` and `STATUS_DASHBOARD_COOKBOOK.md` describing workflow navigation. Stream documentation and behavior were left intact. Grace conversation runtime, model routing, migrations, Grace verification, Engineering execution, CME, authority, and deployment configuration remain outside this change. No production service or database was changed.

## Revision history

- **1.0.29 — 2026-10-16:** Record PL-NEW-041 offline diagnostic ZIP implementation and isolated evidence; add PL-NEW-042 workflow-viewer fit/pan/zoom follow-up and global-workflow visualization parking lot. Predecessor preserved in `.riverview-backups/20261016T180006556096Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.28 — 2026-10-16:** Record feature-level production acceptance and correct stale release checklist language after PR #42 installation on Camrui. Predecessor preserved in `.riverview-backups/20261016T172402152476Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md` (revision 1.0.26).

- **1.0.22 — 2026-10-16:** Reconcile the recorded integration baseline through PR #45 and confirm the work-order retry UI remains Codex 1-owned behavior. Predecessor preserved in `.riverview-backups/20261015T212921860469Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.23 — 2026-10-16:** Add the post-PR #45 isolated browser run and update the validated graph count. Predecessor preserved in `.riverview-backups/20261015T213030949991Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.24 — 2026-10-16:** Reconcile the documented integration baseline through PR #46 while leaving its resident-knowledge implementation untouched. Predecessor preserved in `.riverview-backups/20261015T213508120442Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.25 — 2026-10-16:** Reconcile the current integration through PR #63 and distinguish PR review, manual deployment procedure, and production acceptance. Predecessor preserved in `.riverview-backups/20261016T164347017851Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.26 — 2026-10-16:** Record exact-head CI/browser evidence and the renewed review gate after the PR #63 reconciliation. Predecessor preserved in `.riverview-backups/20261016T164818266451Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.21 — 2026-10-16:** Record PL-038 searchable catalog implementation and full audit dispositions for PL-NEW-001–041; retain the freshness/coverage contract blocker and production-acceptance boundary. Predecessor preserved in `.riverview-backups/20261015T211442725960Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.20 — 2026-10-16:** Record PL-NEW-029 available-state UI and exact notification lifecycle blocker; select PL-NEW-038. Predecessor preserved in `.riverview-backups/20261015T211246926854Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.19 — 2026-10-15:** Record PL-NEW-003 canonical task labels, PL-NEW-001/002/005 source-contract blockers, and select PL-NEW-029. Predecessor preserved in `.riverview-backups/20261015T211018076902Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.18 — 2026-10-15:** Record PL-NEW-036 accessible collapsible navigation and isolated Firefox evidence; select PL-NEW-003 for canonical title mapping. Predecessor preserved in `.riverview-backups/20261015T210814858330Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.17 — 2026-10-15:** Record PL-NEW-019 layout correction and isolated Firefox evidence; queue PL-NEW-036. Predecessor preserved in `.riverview-backups/20261015T210728014115Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.16 — 2026-10-15:** Record PL-NEW-010/015/020/023/024 implementation and update integration baseline to PR #44. Predecessor preserved in `.riverview-backups/20261015T210335865979Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.15 — 2026-10-15:** Complete PL-NEW-016 named-tab navigation and record isolated Firefox evidence; production acceptance remains pending. Predecessor preserved in `.riverview-backups/20261015T205656097722Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.14 — 2026-10-15:** Record PL-NEW-014 projection refresh guidance and PL-NEW-016 as next eligible. Predecessor preserved in `.riverview-backups/20261015T203611503172Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.13 — 2026-10-15:** Record PL-NEW-012 available event provenance implementation and event-specific diagnostic source gap. Predecessor preserved in `.riverview-backups/20261015T203354306114Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.9 — 2026-10-15:** Reconcile PR #42 with PR #43 integration, record PL-NEW-004 outcome, clarify PL-NEW-025's unverified production acceptance, and define PL-NEW-028 contract blocker fields/source/acceptance. Predecessor preserved in `.riverview-backups/20261015T201227715209Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.10 — 2026-10-15:** Record PL-NEW-008 completion, PL-NEW-009's exact source-contract blocker, and PL-NEW-006 as next eligible item. Predecessor preserved in `.riverview-backups/20261015T202051419052Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.11 — 2026-10-15:** Record PL-NEW-006 completion and PL-NEW-007 as the next candidate after threshold-source audit. Predecessor preserved in `.riverview-backups/20261015T202136269723Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.12 — 2026-10-15:** Record PL-NEW-011 implementation, PL-NEW-007's effective threshold source blocker, and PL-NEW-012 as the next bounded audit. Predecessor preserved in `.riverview-backups/20261015T202534604192Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.

- **1.0.4 — 2026-10-15:** Note the source addendum's workflow-item ID mismatch and explicit mapping. Predecessor: `.riverview-backups/20261015T193955730621Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.3 — 2026-10-15:** Record the complete revision history and latest ownership note. Predecessor: `.riverview-backups/20261015T193849598668Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.2 — 2026-10-15:** Clarify the additive documentation overlap with PR #40 and scope boundaries. Predecessor: `.riverview-backups/20261015T193831619982Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.1 — 2026-10-15:** Record PL-NEW-027 implementation status and pending integration review. Predecessor: `.riverview-backups/20261015T193717811237Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.0 — 2026-10-15:** Recover and prioritize PL-NEW-001–041; separate roadmap requirements, captured observations, existing implementations, and current website work.
