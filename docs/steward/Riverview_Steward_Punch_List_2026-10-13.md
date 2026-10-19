<!--
Riverview~ Controlled Document
File: docs/steward/Riverview_Steward_Punch_List_2026-10-13.md
Component: STEWARD-BACKLOG
File Revision: 1.0.4
Purpose: Preserve Steward-captured operational and website improvement observations
Authority: Backlog capture only; entries do not authorize implementation or change active scope
Changed: 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Add controlled revision metadata without changing captured items
Changed: 2026-10-18 UTC | RV-C3-GRACE-REASONING-RELIABILITY-001 | Link final source commit and review PR to the 80B deferred-recovery evidence
History: Git and .riverview-backups/manifest.jsonl
-->
# Riverview Steward Punch List

Captured: 2026-10-13. Proposed IDs only; not yet registered in GitHub or Riverview's database. This backlog must not interrupt the active Grace-to-Engineering work-production campaign.

## Handling policy
- Capture observations with evidence, impact, desired outcome, and acceptance criteria.
- Do not change the current Codex scope when new observations arrive.
- Promote items deliberately after the active milestone, except confirmed critical blockers.
- Status of all items below: CAPTURED (except 004: NEEDS AUDIT).

| ID | Area | Observation / desired outcome | Priority |
|---|---|---|---|
| PL-NEW-001 | Assignments | Show original task purpose, request, expected deliverable, actual result, acceptance and evidence in readable language. | High |
| PL-NEW-002 | Assignments | Blocked tasks explain missing evidence, responsible party, and unblock action. | High |
| PL-NEW-003 | Assignments | Human-readable titles alongside stable technical IDs. | Medium |
| PL-NEW-004 | Assignments | Audit canonical graph-node and diagnostic linkage in assignment detail. | High |
| PL-NEW-005 | Overview | Current Work shows human-readable task titles, purposes and status matching Assignments. | High |
| PL-NEW-006 | Overview | Help text for event cursor, authoritative projection, CME, worker states and Grace execution. | Medium |
| PL-NEW-007 | CME | Document actual heartbeat thresholds and health/staleness criteria in UI. | Medium |
| PL-NEW-008 | Workers | Reconcile worker summary with full inventory including inactive; distinguish registered, active, stale, unknown. | High |
| PL-NEW-009 | Workers | Inspect worker identity, capabilities, task, host, heartbeat, execution and failures. | High |
| PL-NEW-010 | Grace execution | Explain chat-operational vs execution-not-initialized status and actionable prerequisites. | High |
| PL-NEW-011 | Activity | Bidirectional database-backed pagination, including previous page and stable cursors. | High |
| PL-NEW-012 | Activity | Inspect event details with human-readable meaning, causation, task and diagnostic evidence. | High |
| PL-NEW-013 | Diagnostics | Audit code-to-graph, troubleshooting/cookbook documentation and complete diagnostic catalog coverage. | High |
| PL-NEW-014 | Dashboard | Explain projection refresh, cache, freshness and status transitions. | Medium |
| PL-NEW-015 | Grace objectives | Explain uninitialized schema/migrations, refresh semantics, commissioning prerequisites. | High |
| PL-NEW-016 | Navigation | Documentation tab/back navigation should not create duplicate dashboard tabs. | Medium |
| PL-NEW-017 | Chat | Future multi-resident selector. | Later |
| PL-NEW-018 | Chat | Meaningful editable conversation titles and searchable persistent history. | High |
| PL-NEW-019 | Chat | Fix transcript/composer scroll clipping and last-message visibility. | High |
| PL-NEW-020 | Chat | Explain or clean up Disconnect, Refresh history, Insert line break, recovery controls. | Medium |
| PL-NEW-021 | Chat | Authorize work-order creation and inspect resulting deliverables from conversation. | High |
| PL-NEW-022 | Chat | Secure file/image upload, drag/drop and vision routing with limits. | High |
| PL-NEW-023 | Chat | Distinguish available menu actions from future/unavailable actions. | Medium |
| PL-NEW-024 | Milestones | Distinguish dashboard M3.1 release label from roadmap, deployment and commissioning status. | Medium |

## Codex report received during review (not punch-list promotion)
- Dashboard release deployed: 3639f680c518a2f0fd8a91db537a16ac9ced8b64; account-cookie Workflows browser verification still pending.
- Deployed graph registry: 18 workflows, 386 nodes; source branch: 18 workflows, 398 nodes, including 12 uncommissioned nodes.
- Bounded Codex adapter contract committed but not connected or commissioned; no actual Codex-produced deliverable.
- Grace execution and escalated reasoning not live; synthetic escalation contract exists.
- 274 unit tests passed, 105 PostgreSQL integration tests skipped.
- The current objective remains a Grace-originated, authorized, independently verified real artifact.

## Remaining review areas
Workflows, Notifications, and Account access screens not yet fully reviewed in this walkthrough.


## Website review continuation — Workflows, Notifications, navigation and operations (2026-10-13)
These are observations, not implementation orders. Existing Codex Grace-to-Engineering mission remains unchanged. The Workflows failure is an acceptance concern to report at next checkpoint, not authorization to interrupt the current task.

| ID | Area | Observation / desired outcome | Priority |
|---|---|---|---|
| PL-NEW-025 | Workflows | Authenticated Steward session still shows Loading canonical registry; investigate actual account-cookie path and establish deployed browser acceptance evidence. | High / failed acceptance |
| PL-NEW-026 | Workflows | Document selector, graph canvas, node types/legend, node selection, revisions, and actual interaction semantics; distinguish interactive controls from legends. | Medium |
| PL-NEW-027 | Workflows | Cross-workflow jump points should navigate to target graph/node and offer return navigation, preserving context. | Medium |
| PL-NEW-028 | Notifications | Notification summary must identify originating assignment, required action, rationale, priority, deadline if any, and actionable details before acknowledgement. | High |
| PL-NEW-029 | Notifications | Separate delivered, seen, acknowledged, approved, denied and resolved; acknowledgement must not grant work authority. | High |
| PL-NEW-030 | Notifications | Reconcile legacy Windows/Estate audio delivery with Camrui control plane and authorized remote dev-PC audio presenter; report actual supported routes. | High |
| PL-NEW-031 | Notifications | Propose layered Steward attention: visible flashing/persistent dashboard attention, audio, and eventual phone notifications, with escalation/retry/quiet-hours and no notification storm. | High |
| PL-NEW-032 | Notifications | Inspectable notification history, details, source links, receipt states and safe bulk triage/archive. | Medium |
| PL-NEW-033 | Go-live lifecycle | Controlled test-to-production transition: archive/segregate prototype assignments, objectives, notifications, chat and events; retain immutable audit evidence and backups; no indiscriminate database flush. | High |
| PL-NEW-034 | Maintenance | Steward-authorized maintenance/settings interface for retention, archival, backups, cleanup previews, export, restore and permissioned irreversible actions. | High |
| PL-NEW-035 | Resources | Introduce Resources/Capabilities surface: hosts, models, tools, dependency graph, availability, performance, readiness, power and wake controls, initially read-only. | High / later milestone |
| PL-NEW-036 | Navigation | Collapsible sidebar with compact icon-only state and accessible expand control; preserve persistent health/snapshot affordances. | Medium |
| PL-NEW-037 | Global health | Multi-segment model/host readiness indicator (Camrui 0.6B, 30B vision, 80B reasoning) with explicit selected provider vs merely online; tooltip and accessible textual fallback. | Medium |
| PL-NEW-038 | Documentation | Replace fixed three diagnostic links with searchable indexed catalog of per-component troubleshooting, workflows, failure/recovery, provenance, freshness and test coverage. | High |
| PL-NEW-039 | Automated QA | Evaluate CueMastery role-based seeded test personas and scheduled audit as precedent for Riverview repeatable verification; add actual authenticated browser route/interaction tests as a separate stage. | High / proposal |
| PL-NEW-040 | Automated QA | Define test account lifecycle, safe permissions, scheduled and post-deployment runs, PASS/FAIL/WARNING/SKIPPED evidence, regression detection and historical reports. | High / proposal |

### Historical source findings — CueMastery (verified repository documents)
- `ppow1/CueMastery/docs/runbooks/cuemastery_seeded_test_personas.md`: durable passwordless test personas covering admin, user, coach, venue, sponsor, corporate and multi-role access; explicit non-destructive policy.
- `ppow1/CueMastery/docs/runbooks/cuemastery_test_persona_audit.md`: deterministic identity, route-policy, module-visibility and report-integrity checks; intended four-hour schedule, JSON/Markdown reports and admin Verification Center; `http_browser` explicitly SKIPPED in that implementation.
- `ppow1/CueMastery/server_artifacts/ionoge/public_html/bin/run_test_persona_audit.php`: actual CLI audit runner.
- `ppow1/CueMastery/docs/audits/2026-06-11-cuemastery-website-expansion-audit.md`: historical website audit notes lack of full live route/browser verification.
Thus, reuse the persona/role/route audit approach, but do not claim CueMastery already had full end-to-end browser regression automation. That is an additional Riverview requirement.

### Historical source findings — Riverview notifications
- `ppow1/Riverview/src/riverview/notifications_audio.py`: legacy bounded Windows/Estate presenter depends on Windows, PowerShell, System.Speech, default interactive audio device; delivering a notification does not acknowledge it.
- `ppow1/Riverview/docs/operations/RIVERVIEW_COMMS5_DEPLOYMENT.md`: authenticated external MCP transport exists in historical architecture; no evidence this equals Camrui's currently deployed notification-to-phone capability.

### Next review scope
Workflow registry remains unverified in the user's Steward session. Notifications reviewed. Account Access remains for later inspection. No changes to live Riverview or Codex were made by this punch-list update.

## Review addendum — 2026-10-13, after Steward refresh

- **PL-NEW-024 / Workflow rendering** (see existing workflow rows): previously failed to load, but Steward now confirms registered workflows render in authenticated session after refresh. Mark **observed working**, pending automated regression test; do not continue describing it as presently broken.
- **Workflow legend:** Process, Decision, Failure, Escalation, Recovery and Verification are a color key, not filters. Current behavior is understood; no defect claimed.
- **Workflow inspection:** selecting a node reveals stable ID, revision, source and documentation below viewport. Cross-workflow destinations navigate via the populated logical-jump-point section. Steward accepts existing implementation for now; consider discoverability/scroll cue later, not a blocker.
- **Workflow diagnostics:** three recurring diagnostic references may or may not be sufficient; keep coverage audit open, no unverified claim of missing docs.
- **Account Access:** page newly visible; Steward confirms session/login display, sign out, account session and grant controls, shared email delivery configuration, save/refresh and test-email action. Grant controls (disable, revoke sessions/grants, viewer/operator, remove Steward) require descriptive hover help and an explicit confirmation/impact summary before consequential action. Verify whether grants support shorter durations, including one-day or one-time, without assuming existing options.
- **Account Access email:** current display says configured, not tested; retain this distinction until delivery proof. Validate safe test-email result and error feedback without exposing SMTP secrets.
- **Global Settings and Maintenance:** existing Account Access email settings do not replace global Riverview settings and lifecycle maintenance pages. Keep PL-NEW-033/034 open.
- **Terminology:** registered canonical process graphs currently called Workflows. Reserve a distinct future term (e.g. resident procedures or skills) for specific approved methods residents may invoke; do not rename registry without a separate terminology review.
- **Review coverage:** all currently visible sidebar pages reviewed; Account Access now included. No live service, database, permissions, or Codex state changed by this document.

## Steward punch-list update — 2026-10-13: Dashboard snapshot completeness

| ID | Area | Observation / desired outcome | Priority |
|---|---|---|---|
| PL-NEW-041 | Dashboard snapshots / Workflows | Snapshot currently omits workflow content. Capture **every workflow's current status and its actual visual representation as displayed on the website**, together with structured graph definitions and all required dashboard sections. | P1 — after current Grace 80B commissioning repair |

### PL-NEW-041 — acceptance specification
- **Observed defect:** Snapshot no longer gathers everything displayed on the dashboard; workflows are a confirmed omission. Do not infer that the live workflow page itself is broken (Steward previously confirmed it renders after refresh).
- **Complete inventory:** Include every workflow available in the website's Workflows section, its name, stable identifier, revision, status, node/step state, connections, dependencies, labels, and displayed progress/health indicators.
- **Actual visual representation:** Capture the workflow **as the website presents it**—its graphical canvas, layout/positions, nodes, arrows/connectors, labels, colors, legend/status indicators, and relevant visible node details. A workflow name or text summary is insufficient. Provide an image/rendered capture of each workflow, not merely a generic regenerated diagram.
- **Recoverable structure:** Preserve the canonical workflow graph/structured definition alongside each visual capture so the visualization can be faithfully reconstructed and inspected after transfer.
- **API-accessible complete export:** Provide an authenticated, permission-checked, machine-readable API export of the entire canonical workflow registry (all workflows, nodes, edges, cross-workflow links, revisions, metadata, statuses, and relationships), with a documented schema/version and deterministic snapshot correlation. The snapshot must include the exported data or a durable copy, not merely a link to a potentially changing API response.
- **Globally unique persistent node identity:** Every individual node must have a globally unique, stable identifier across the entire registry, including across workflow boundaries. Export workflow IDs, node IDs, source/destination edge IDs, cross-workflow target IDs, and relevant revision/version identifiers. Identity must support unambiguous mapping among the API export, visual canvas, diagnostic references, execution events, and subsequent snapshots. Preserve identifiers across non-identity-changing edits; define explicit lineage/mapping when nodes are replaced or retired. Audit existing registry identifiers before introducing a new scheme; do not assume they are currently globally unique.
- **Visual/data cross-reference:** Each workflow's website-faithful visual capture must be keyed to the same workflow ID and revision as its API export, with a mapping from every displayed node to its globally unique node ID. Validate that rendered node and connector counts/references reconcile with exported graph data, and report any mismatch explicitly.
- **Other dashboard context:** Preserve project requirements, process-map links, current milestones, Engineering and Grace state, relevant release/configuration identities, and other dashboard sections that the snapshot is expected to cover.
- **Completeness validation:** Reconcile snapshot workflow count/IDs/revisions with the dashboard's actual workflow registry; report any missing workflows, missing renderings, failed data collection, stale captures, or partial sections explicitly rather than silently omitting them.
- **Acceptance test:** For each workflow shown in an authenticated Steward browser session, verify its structured data **and** visual rendering appear in the snapshot and correspond to the same website view/state; verify all other required dashboard sections are present. Ensure the resulting snapshot supports recovery and handoff to another conversation.
- **Status:** CAPTURED; do not redirect Codex from the active Grace 80B commissioning startup defect. This is a subsequent P1 item, not authorization for immediate implementation.

## Steward punch-list update — 2026-10-17: Grace 80B deferred-recovery reliability

| ID | Area | Observation / desired outcome | Priority | Owner | Status |
|---|---|---|---|---|---|
| PL-NEW-043 | Grace reasoning / deferred recovery | Deterministic provider request errors must be classified separately from provider readiness/outage, and durable deferred work must recover without identical unbounded retries or duplicate publication. Preserve the concurrent 0.6B, 30B and 80B capability routing. | P1 — reliability incident | Codex 3 (Grace runtime); coordinate model/provider ownership with Codex 1 where applicable | SOURCE IN REVIEW; operational acceptance remains open |

### PL-NEW-043 — acceptance criteria and incident evidence

- **Incident evidence:** Camrui dashboard journal contained 253 `grace_deferred_resume_attempt` records from 2026-10-17 20:18:12 through 20:42:33 EDT. Each logged a single 80B reasoning attempt, `outcome=failed`, sanitized `error_code=provider_error`, and router `readiness_state=UNAVAILABLE`; completion durations were sub-10 ms. The dashboard process restarted at 20:42:34 EDT and the 80B response resumed at 20:43:22 EDT. This evidence proves repeated fast completion failures followed by recovery after the dashboard release change; it does **not** prove an OctoMiner 1 reboot/unload or establish the provider's raw error, because historical OctoMiner 1 logs were unavailable.
- **Working diagnosis:** prompt size exceeded the configured 32 KiB provider request limit and the deterministic `prompt_too_large` completion error was surfaced as `provider_error`/`UNAVAILABLE`. Confidence: high, not definitive. The active dashboard release added byte-bounded conversation context and safe `prompt_too_large` diagnostics; verify its behavior through source tests and synthetic fixtures. Do not rewrite an already working active-release correction without a failing regression test.
- **Required acceptance:** (1) deterministic prompt overflow trims only eligible context while preserving protected instructions and current request identity, or returns an accurate non-retryable terminal disposition when safe trimming cannot fit; (2) timeout, transport, busy/503, malformed response, authorization and readiness failures retain distinct sanitized classifications; (3) transient retry/backoff is bounded and durable, with restart resumption and exactly-once correlated publication; (4) a synthetic conversation beyond 32 KiB reproduces the legacy failure and passes the corrected path; (5) disposable/mocked fault injection demonstrates one capability's failure does not mark Grace's other model capabilities unavailable; (6) focused and relevant regression tests pass, and graph/cookbook/documentation match implemented behavior.
- **Evidence references:** Camrui `riverview-status-dashboard.service` journal, filtered to sanitized `grace_deferred_resume_attempt` metadata for 2026-10-17 20:10–20:50 EDT; deployed release identities `0450c492…` (pre-fix) and `ac707ef71335f889dd21ae28210ce9906eec9d38` (recovery release); checkout evidence to be recorded by task `RV-C3-GRACE-REASONING-RELIABILITY-001`. No conversation body, credentials, or raw provider payload is retained here.
- **Troubleshooting references:** `docs/components/RESIDENT_CONVERSATION.md`, `docs/components/RESIDENT_CONVERSATION_FLOW.md`, and `docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md`.
- **Dependencies / blockers:** no historical OctoMiner 1 service logs were available; host access was blocked by SSH public-key authentication. Comms5 mailbox contract changes remain Codex 1's ownership; Grace execution behavior remains coordinated with Codex 2. No production deployment, service restart, model reload, endpoint change, or live inference is authorized by this item.
- **Exit condition:** attach immutable test evidence and source commit/PR; document unresolved host-level evidence limits; keep this item open until operational acceptance independently verifies bounded retries, durable recovery, exactly-once response publication, and per-capability readiness. This engineering work does not authorize deployment.


### PL-NEW-043 — source verification update (2026-10-18)

- **Implementation evidence:** Isolated branch `codex/grace-reasoning-reliability-active-20261017`, based on active release branch `codex/grace-conversation-ui-refinement` at `ac707ef71335f889dd21ae28210ce9906eec9d38`. Added sanitized HTTP status preservation and deterministic-vs-transient completion classification; durable retry schedule with five-attempt cap and 5/10/20/40-second backoff; terminal correlated failure for deterministic prompt/auth/contract errors; per-capability readiness isolation tests. The existing 32 KiB prompt trimming remains in place.
- **Focused tests:** `PYTHONPATH=src python3 -m pytest -q tests/test_resident_model_router.py tests/test_local_reasoning_provider.py tests/test_resident_conversation.py tests/test_status_dashboard.py` — PASS, 91 passed, 39 skipped, 11.37s.
- **Active suite:** `PYTHONPATH=src python3 -m pytest -q tests` — PASS, 391 passed, 203 skipped, 49.64s. PostgreSQL integration cases were skipped because `RIVERVIEW_TEST_PG_DSN` is not configured; no live database was used.
- **Workflow and source checks:** `python3 scripts/process_graph.py generate` and `python3 scripts/process_graph.py check` — PASS (22 graphs, 555 nodes); `PYTHONPATH=src python3 -m py_compile src/riverview_core/resident_execution/conversation.py src/riverview_core/resident_execution/model_router.py` — PASS; `git diff --check` — PASS.
- **Collection limitation:** Root `PYTHONPATH=src python3 -m pytest -q` did not collect because an archived historical test imports unavailable `runtime_baseline` from `docs/history/RV-M1.1-002/rev1.0.0/tests/test_runtime_baseline.py`. The active `tests/` suite passed as recorded above; archived material was not changed.
- **Operational boundary:** OctoMiner 1 SSH access and historical logs remain unavailable; live endpoint fault injection, deployment, restart, and model inference were not performed. Acceptance of durable PostgreSQL retry/restart behavior requires the isolated integration DSN plus authorized operational review. No production changes were made.
- **Final edge-case regression:** A post-review check found missing model bindings were being scheduled for retry and HTTP 401/403/400/422 outcomes had lost their specific terminal response class. Missing bindings now block immediately; authorization maps to `authorization_denied`, malformed input to `model_response_invalid`, with sanitized HTTP status retained. Dedicated tests cover these cases; final run results above include this correction.
- **Source revision and evidence:** Commit `373978d0` on `codex/grace-reasoning-reliability-active-20261017`; review PR [#111](https://github.com/ppow1/Riverview-/pull/111). Checkout evidence: `evidence/checkouts/RV-C3-GRACE-REASONING-RELIABILITY-001/20261018T0256Z/checkout.md`. Keep PL-NEW-043 open pending review and operational acceptance.
