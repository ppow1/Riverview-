<!--
Riverview~ Controlled Document
File: docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md
Component: STEWARD-DASHBOARD / WEBSITE
File Revision: 1.0.4
Purpose: Consolidate traceable website improvement observations and separate them from accepted requirements and completed work
Authority: Backlog recovery only; no new product requirement or acceptance decision
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Recover and prioritize documented website observations
Changed: 2026-10-15 UTC | RV-WEBSITE-PL027 | Record completed branch implementation and pending integration review
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Clarify additive documentation overlap with PR #40 and active ownership boundaries
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Record controlled document revision history
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Note source ID mismatch in workflow rendering addendum
History: Git
-->
# Recovered Riverview website punch list

**Captured source:** [`Riverview_Steward_Punch_List_2026-10-13.md`](Riverview_Steward_Punch_List_2026-10-13.md), including its 2026-10-13 review addenda.  
**Baseline:** integration branch `codex/grace-conversation-ui-refinement` at PR #41 merge `218cb58491bcb939466a1eebb51bd666fd97005e`; website work branch `codex/website-improvements`.  
**Purpose:** consolidate the recorded website observations without promoting them to accepted requirements. The original PL-NEW identifiers and stated priorities are retained.

## Requirement and implementation boundaries

- The active roadmap requirement for M3.1 is the read-only status projection, truthful status/freshness, safe diagnostic rendering, canonical workflow visualization, and navigable decisions. See [`ROADMAP.md`](../ROADMAP.md) and [`M3.1-001_REVISION_RECORD.md`](../development/M3.1-001_REVISION_RECORD.md). Scoped M3.1 technical acceptance is recorded; the full component DoD remains open.
- PL-NEW-001 through PL-NEW-041 are captured observations and desired outcomes from the Steward punch list. The source says they are not implementation orders; PL-NEW-041 also has an explicit acceptance specification. A listed item is not treated as an accepted roadmap requirement unless another governing record says so.
- One review addendum calls the previously failing workflow-rendering observation “PL-NEW-024,” while the source ID table assigns PL-NEW-024 to milestone labeling and PL-NEW-025 to workflow loading. This recovery maps the observation by subject to PL-NEW-025 and preserves PL-NEW-024's table-defined milestone scope.
- Existing implementations are listed separately below. Their existence does not close a punch-list item unless the recorded outcome and acceptance evidence match it.
- PR #40 implements durable SSE conversation streaming and deferred-response recovery. It is part of this branch's integration baseline and is compatibility-sensitive; this website work does not rebuild it.

## Prioritized traceable backlog

Priority labels and wording below follow the source punch list. “Captured” means recorded, not approved or complete. Where the source addenda provide a later observation, that observation is called out without silently rewriting the original row.

| ID | Area | Recorded outcome | Priority | Record state / qualification |
|---|---|---|---|---|
| PL-NEW-001 | Assignments | Show purpose, request, expected deliverable, result, acceptance, and evidence in readable language. | High | Captured |
| PL-NEW-002 | Assignments | Explain blocked-task evidence gaps, owner, and unblock action. | High | Captured |
| PL-NEW-003 | Assignments | Pair human-readable titles with stable technical IDs. | Medium | Captured |
| PL-NEW-004 | Assignments | Audit canonical graph-node and diagnostic linkage in assignment detail. | High | Needs audit |
| PL-NEW-005 | Overview | Match Current Work titles, purposes, and status to Assignments. | High | Captured |
| PL-NEW-006 | Overview | Explain event cursor, authoritative projection, CME, worker states, and Grace execution. | Medium | Captured |
| PL-NEW-007 | CME | Document heartbeat thresholds and health/staleness criteria in the UI. | Medium | Captured |
| PL-NEW-008 | Workers | Reconcile summary and full inventory, including inactive workers and registered/active/stale/unknown distinctions. | High | Captured |
| PL-NEW-009 | Workers | Show worker identity, capabilities, task, host, heartbeat, execution, and failures. | High | Captured |
| PL-NEW-010 | Grace execution | Explain chat-operational versus execution-not-initialized status and prerequisites. | High | Captured |
| PL-NEW-011 | Activity | Add bidirectional database-backed pagination with stable cursors. | High | Captured |
| PL-NEW-012 | Activity | Show human-readable event meaning, causation, task, and diagnostic evidence. | High | Captured |
| PL-NEW-013 | Diagnostics | Audit code-to-graph, cookbook, and diagnostic-catalog coverage. | High | Captured; source says coverage is unverified, not known missing |
| PL-NEW-014 | Dashboard | Explain projection refresh, cache, freshness, and status transitions. | Medium | Captured |
| PL-NEW-015 | Grace objectives | Explain schema/migration initialization, refresh semantics, and commissioning prerequisites. | High | Captured |
| PL-NEW-016 | Navigation | Prevent documentation-tab/back navigation from creating duplicate dashboard tabs. | Medium | Captured |
| PL-NEW-017 | Chat | Add a future multi-resident selector. | Later | Captured; explicitly future |
| PL-NEW-018 | Chat | Add meaningful editable conversation titles and searchable persistent history. | High | Captured |
| PL-NEW-019 | Chat | Fix transcript/composer clipping and last-message visibility. | High | Captured |
| PL-NEW-020 | Chat | Explain or remove Disconnect, Refresh history, line-break, and recovery controls. | Medium | Captured |
| PL-NEW-021 | Chat | Support authorized work-order creation and deliverable inspection from conversation. | High | Captured; authorization and promotion rules remain governing constraints |
| PL-NEW-022 | Chat | Provide secure bounded file/image upload, drag/drop, and vision routing. | High | Captured |
| PL-NEW-023 | Chat | Distinguish available menu actions from unavailable/future actions. | Medium | Captured |
| PL-NEW-024 | Milestones | Distinguish dashboard M3.1 release label from roadmap, deployment, and commissioning status. | Medium | Captured |
| PL-NEW-025 | Workflows | Verify authenticated account-cookie registry loading and preserve deployed browser acceptance evidence. | High / failed acceptance | Addendum later reports workflows rendered after refresh; automated regression remains pending |
| PL-NEW-026 | Workflows | Document selector, canvas, node types/legend, selection, revisions, and interaction semantics. | Medium | Captured; addendum confirms legend is a color key and current node details are accepted for now |
| PL-NEW-027 | Workflows | Navigate cross-workflow jumps to the exact target and provide return navigation preserving context. | Medium | Captured; current work implements this item |
| PL-NEW-028 | Notifications | Show source assignment, required action, reason, priority/deadline, and details before acknowledgment. | High | Captured |
| PL-NEW-029 | Notifications | Distinguish delivered, seen, acknowledged, approved, denied, and resolved; acknowledgment grants no authority. | High | Captured |
| PL-NEW-030 | Notifications | Reconcile legacy Windows/Estate audio with Camrui and report supported routes. | High | Captured; source evidence says these are not established as equivalent |
| PL-NEW-031 | Notifications | Propose layered visible/audio/phone attention with escalation, retries, quiet hours, and storm prevention. | High | Captured proposal |
| PL-NEW-032 | Notifications | Provide history, detail, source links, receipt states, and safe bulk triage/archive. | Medium | Captured |
| PL-NEW-033 | Go-live lifecycle | Define controlled test-to-production transition with archive, audit, and backup; no indiscriminate flush. | High | Captured |
| PL-NEW-034 | Maintenance | Add authorized settings for retention, archive, backup, cleanup preview, export/restore, and permissioned irreversible actions. | High | Captured |
| PL-NEW-035 | Resources | Add an initially read-only Resources/Capabilities surface for hosts, models, tools, dependencies, readiness, performance, power, and wake controls. | High / later milestone | Captured; later-milestone qualifier retained |
| PL-NEW-036 | Navigation | Add collapsible sidebar with compact icon state and accessible expansion; retain health/snapshot affordances. | Medium | Captured |
| PL-NEW-037 | Global health | Show segmented model/host readiness, selected versus merely online provider, and accessible textual explanation. | Medium | Captured |
| PL-NEW-038 | Documentation | Replace fixed diagnostic links with searchable indexed troubleshooting, workflow, provenance, freshness, and coverage catalog. | High | Captured |
| PL-NEW-039 | Automated QA | Evaluate seeded role-based audit precedent and add authenticated browser route/interaction tests as a distinct stage. | High / proposal | Captured proposal; CueMastery source findings are historical evidence only |
| PL-NEW-040 | Automated QA | Define test-account lifecycle, safe permissions, scheduled/post-deploy runs, outcome states, regression detection, and historical reports. | High / proposal | Captured proposal |
| PL-NEW-041 | Dashboard snapshots / Workflows | Include every website workflow's status and website-faithful visual, structured definitions, cross-references, and all required dashboard sections in a recoverable snapshot. | P1 — after active Grace 80B commissioning repair | Captured; detailed acceptance specification remains in the source record |

### Current implementation order

1. **PL-NEW-027 — implemented on this branch; integration review pending:** exact target-node focus plus a return path to the source jump node. This is isolated to the canonical workflow viewer asset and its workflow map; Firefox evidence is in `evidence/checkouts/WEBSITE-PL027/20261015T193400Z-workflow-navigation/`.
2. **PL-NEW-025 — next verification:** run an authenticated browser regression against an isolated environment, including account-cookie registry loading. The addendum records a successful manual refresh, not automated acceptance.
3. **PL-NEW-041 — queued by the source priority:** snapshot completeness is P1 but explicitly sequenced after the active Grace 80B commissioning repair. The snapshot currently has a 128 KiB browser-side bound and the canonical graph JSON alone is larger than that; snapshot format, size handling, and visual capture need a deliberate design before implementation.
4. **Remaining captured items:** group by shared UI surface and dependencies, then audit against the current branch before implementation. High priority does not itself authorize changing Grace, Engineering execution, authorization, CME, or production services in this website track.

## Existing implementation evidence (not punch-list closure)

| Existing behavior | Evidence | Boundary |
|---|---|---|
| Read-only dashboard, bounded pages, truthful source/CME/worker states, safe cookbook rendering, and redacted operational snapshot | [`STATUS_DASHBOARD.md`](../components/STATUS_DASHBOARD.md), [`M3.1-001_REVISION_RECORD.md`](../development/M3.1-001_REVISION_RECORD.md) | M3.1 technical scope accepted; full dashboard DoD remains open |
| Authenticated canonical graph index/detail APIs and SVG workflow viewer with node identities, revisions, typed transitions, selection, and cross-workflow jump controls | Same M3.1 record; `server.py`, `workflow.js`; process-graph checks | Manual deployed workflow rendering was evidenced; PL-NEW-025 automated account-cookie regression remains pending |
| Durable conversation SSE, reconnect/replay, terminal states, and deferred-response recovery | PR #40 merge `e897c52`; [`RESIDENT_CONVERSATION.md`](../components/RESIDENT_CONVERSATION.md); integration browser evidence | Existing compatibility behavior. Website changes must retain it; it is not a new website feature request here |
| Persistent account sessions and protected Steward/account views | Integration baseline `218cb584`; account-authentication component docs and tests | Account-session workflow loading needs its own PL-NEW-025 browser check |

## Ownership and integration map

The website track owns dashboard presentation and navigation, primarily `status_dashboard/static/workflow.js`, `app.css`, `index.html`, and dashboard tests/docs. PR #40 also touched `status_dashboard/server.py`, `status_dashboard/static/app.js`, `tests/test_status_dashboard.py`, and dashboard component documentation for stream compatibility. This change avoids its shared behavior-code and test files; the only same-file overlaps are additive paragraphs in `STATUS_DASHBOARD.md` and `STATUS_DASHBOARD_COOKBOOK.md` describing workflow navigation. Stream documentation and behavior were left intact. Grace conversation runtime, model routing, migrations, Grace verification, Engineering execution, CME, authority, and deployment configuration remain outside this change. No production service or database was changed.

## Revision history

- **1.0.4 — 2026-10-15:** Note the source addendum's workflow-item ID mismatch and explicit mapping. Predecessor: `.riverview-backups/20261015T193955730621Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.3 — 2026-10-15:** Record the complete revision history and latest ownership note. Predecessor: `.riverview-backups/20261015T193849598668Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.2 — 2026-10-15:** Clarify the additive documentation overlap with PR #40 and scope boundaries. Predecessor: `.riverview-backups/20261015T193831619982Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.1 — 2026-10-15:** Record PL-NEW-027 implementation status and pending integration review. Predecessor: `.riverview-backups/20261015T193717811237Z/docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`.
- **1.0.0 — 2026-10-15:** Recover and prioritize PL-NEW-001–041; separate roadmap requirements, captured observations, existing implementations, and current website work.
