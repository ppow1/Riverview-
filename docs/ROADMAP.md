# Riverview~ Implementation Roadmap

**Document Revision:** 1.1.14
**Status:** Active planning baseline — execution gates require evidence  
**Date:** 2026-10-11
**Component:** RV-ROADMAP  
**Owner:** Steward  
**Purpose:** Define the ordered implementation path and what the command **“go” or “next”** means.  
**Source contracts:** `README.md`, `docs/architecture/CORE_CONTRACT.md`, `docs/architecture/EVENT_AND_ASSIGNMENT_CONTRACT_v0.1.md`, `docs/architecture/LINUX_DEPLOYMENT_AND_HOSTING_v0.1.md`, `docs/architecture/OBSERVABILITY_AND_SPATIAL_CONTRACT_v0.1.md`, `docs/components/POSTGRES_LEDGER.md`, `docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md`.

## Mission and first proof

Build a **persistent, event-driven, Linux-native autonomous institution** whose assignments progress without chat turns; work is durable, concurrent, independently verified, observable, and recoverable. Camrui is the current development control-plane host; OctoMiner and other compute providers are replaceable execution resources.

**First vertical-slice proof:** An authorized assignment executes unattended; two assignments progress independently; an interruption is recovered without blindly duplicating external effects; results are independently verified; true state and diagnostics appear on a dashboard; and an attention condition produces a tracked notification. These are *acceptance criteria*, not claims of existing behavior.

## “Next” protocol

- **“Go” and “Next” are equivalent commands:** work on the **earliest unfinished numbered step** in the current milestone, subject to its dependencies. Do not reinterpret it as permission to begin unrelated infrastructure.
- At the start of a step: read `AI_HINTS.md` and relevant contracts; confirm actual host/repository state; identify the deliverable and a short test plan. Avoid repeated broad inventories when evidence is already current.
- At completion: record **PASS / FAIL / BLOCKED / NOT VERIFIED**, exact artifacts, tests and host, commit/deployment identifiers, remaining limitations, and the **next step ID**.
- Do not mark a step complete merely because files were written. On failure, repair the same step; on a real blocker, identify it and propose the smallest decisive experiment. Do not silently skip.
- Roadmap revisions require a file revision increment and preserved predecessor under the Development Lifecycle Standard. This roadmap controls sequencing; it does not override architecture contracts or create artificial runtime approvals.

## Completed foundation (historical evidence, not live-runtime acceptance)

- **F-01 — Clean-start repository and architecture:** `ppow1/Riverview-` established with core, event, Linux, observability, privacy and component contracts. **DOCUMENTED**.
- **F-02 — Developer ledger prototypes:** SQLite and PostgreSQL assignment/event ledger libraries and tests exist; PostgreSQL integration tests were previously reported passing on Camrui. These are **developer components, not autonomous services**.
- **F-03 — Controlled revisions:** 13 Markdown documents and 10 Python files inventoried; missing headers migrated in Groups 1 and 2. Group 2 commit `6ad9f63f618886bb3ae6d2d99c255ce5921e9ae2`. **COMPLETE for that migration scope**, not a full repository enforcement claim.
- **F-04 — Engineering guidance:** `AI_HINTS.md` Rev 1.0.0 and Development Lifecycle Standard Rev 1.0.0 established. **DOCUMENTED**.
- **F-05 — This roadmap:** planning artifact only. Does not prove a runtime.

## Milestone 1 — Make the durable control plane real

**M1.1 — Camrui runtime baseline and PostgreSQL readiness**  
Deliverable: verified host/service configuration, database connectivity and isolated development schema, exact deployment path, persistent storage ownership and service identity. Reuse existing evidence; verify only what changed.  
**PASS:** reproducible connection and schema test on Camrui; report identifies database and environment without leaking credentials.

**M1.2 — Durable assignment and event schema contract implemented**  
Deliverable: versioned PostgreSQL migrations and durable assignment/event storage aligned with the event contract; explicit authority reference, causality, idempotency and workflow metadata as required by the first slice. Existing `PostgresLedger` is the starting point, not automatically production-complete.  
**PASS:** schema creation/migration and atomic transition tests; rejected illegal and duplicate transitions; durable state survives reconnection.

**M1.3 — Always-on event processor**  
Deliverable: Linux-supervised service with durable outbox/inbox or equivalent persisted cursor, event replay, and resumable assignment progression.  
**PASS:** new assignment advances with no chat/UI turn; process restart resumes unfinished work; duplicate events are idempotent.

**M1.4 — Independent assignment scheduling**  
Deliverable: multiple concurrent assignments, fair dispatch, leases and stale-worker fencing appropriate to first-slice work.  
**PASS:** two assignments progress independently; a stalled assignment does not stop another; stale lease cannot commit as current.

## Milestone 2 — Execute, verify and recover real work

**M2.1 — Minimal registered worker adapter**  
Deliverable: one capability-registered worker with authenticated scope and durable attempt/result records. Use a deterministic local task first, not GPU integration.  
**PASS:** dispatch and results are attributable, repeatable and visible; worker loss is detectable.

**M2.2 — Independent outcome verification**  
Deliverable: verifier separate from the executor; evidence and acceptance criteria stored against the assignment. Do not equate caller `verified=True` with verification.  
**PASS:** invalid output is rejected and routed to rework; valid output reaches completed only with verifier evidence.

**M2.3 — Failure and restart recovery**  
Deliverable: retry/reconciliation policy, fenced attempts, restart behavior, and explicit external-effect uncertainty handling.  
**PASS:** forced process/worker interruption does not lose assignments or blindly duplicate effects; recovery outcome is auditable.

**M2.4 — CME monitoring service**  
Deliverable: simple, always-on, concurrent monitor for meaningful progress, deadlines, stalls and recovery requests. CME observes; it does not govern or replace workers.  
**PASS:** identifies a stalled assignment while unrelated work continues; emits a traceable recovery/attention event.

## Milestone 3 — Make actual operation visible and actionable

**M3.1 — Read-only status projection and browser dashboard**  
Deliverable: live assignment states, event cursor, workflow step, last meaningful progress, freshness/staleness, worker/CME health, diagnostics and source provenance. Diagnostic references render safely and readably; a browser workflow viewer projects the canonical process-graph JSON registry.

**PASS:** dashboard reflects real events and shows stale/unavailable distinctly from healthy; no invented progress percentages; canonical workflows and decisions are navigable; process position is highlighted only when an exact durable node identity is available, otherwise shown unknown; read-only/authorization boundaries pass security checks. A controlled real worker and independent verifier can produce and accept a durable PostgreSQL result artifact visible in the projection.

**M3.2 — Durable notification and decision requests**  
Deliverable: recorded attention events, delivery/acknowledgment state, and Steward decision requests; start with one demonstrable delivery channel, then add visual/audio/SMS as specified.  
**PASS:** defined attention condition delivers via the tested channel and records success/failure/acknowledgment truthfully.

**M3.3 — First end-to-end unattended demonstration**  
Deliverable: reproducible demo script and evidence bundle covering authorization, two concurrent assignments, worker execution, independent verification, restart/recovery, dashboard and notification.  
**PASS:** all first-slice proofs pass on Camrui with timestamps, commands, logs, observed output, and restart evidence. **This is the first meaningful runtime milestone.**

### Issue #13 milestone ownership and scope proposal

The Issue #13 amendment and draft PR #15 are requirements input; PR #15 remains
unmerged. This work keeps M3.1 read-only: readable operational documents,
canonical graph visualization, truthful live status, and cross-component proof
that a registered worker and distinct verifier can produce and accept a durable
result. It adds no browser command, work-order promotion, resident chat, or
resource mutation path.

M3.2 retains durable attention/decision delivery. M3.3 retains the repeatable
unattended first vertical slice. To preserve all Issue #13 requirements without
mislabeling M3.1, a proposed **M3.4 — Governed Operations Console and Resident
Conversation** should follow M4.1 identity/authority and M4.2 resident reasoning
dependencies and precede M4.4 operational acceptance. Its acceptance criteria
should include live browser conversation with Grace and another authorized
resident, durable resident-separated continuity across reload/restart, explicit
approval before specification/objective/work-order promotion, denied
unauthorized promotion, shared browser/AI/API command contracts, and evidence
for authorized lifecycle, denial, recovery, capability/resource and Steward
decision actions. This is a sequencing proposal recorded for Steward review,
not an accepted roadmap change or authorization to implement the command/chat
system in M3.1.

## Milestone 4 — Institutional identity and AI reasoning

**M4.1 — Office, occupant, implementation and state separation**  
Deliverable: persistent institutional identities, grants and delegated authority; occupant/model replacement without losing assignment or office continuity.  
**PASS:** identity and authority survive restart and occupant replacement; unauthorized actions are rejected.

**M4.2 — Resident regrounding and reasoning routing**  
Deliverable: residents load current rules and assignment state at consequential boundaries; provider-independent reasoning escalation, budgets and fallback.  
**PASS:** an interrupted resident resumes from authoritative state; a configured provider can be swapped without changing assignment authority.

**M4.3 — Local AI worker integration**  
Deliverable: capability discovery and replaceable adapters for OctoMiner-hosted models; support concurrent jobs with measurable queueing and failures.  
**PASS:** at least one actual local inference task completes through the durable worker contract and its results are independently checked. BIOS/GPU expansion is a separate hardware campaign, not a prerequisite for the deterministic first slice.

**M4.4 — Grace Operational Integration (mandatory system-level deliverable)**  
Deliverable: Grace is the first operational AI director of engineering work. She accepts a Steward objective; reasons and revises a durable plan; creates persistent assignments; delegates through the CME to real engineering execution capabilities; consumes progress and independent verification evidence; and autonomously replans or follows up until verified completion or a genuine Steward decision point. Persist objective, authority, plan, assignment relationships and progress across context/model/worker/process replacement. Keep office role and authority separate from occupant, model, personality, voice and avatar. The interface must permit additional residents, offices and specialist groups without redesigning the CME.  
Dependencies: M2.1 worker execution; M2.2 independent verification; M2.3 recovery; M2.4 CME monitoring; M3.1 live status projection; M3.2 durable attention/decision delivery; M4.1 institutional identity and authority; M4.2 reasoning and regrounding. Personality and presentation work are separate and do not gate operational Grace.  
**PASS:** sustained repeated objective-to-artifact-to-independent-verification-to-follow-up cycles on Camrui, including multiple concurrent assignments, actual coding-tool output, failure/wait isolation, restart and resident/model replacement recovery, live progress/evidence consumption, and automatic replanning, with durable logs and no routine turn-by-turn Steward prompting. A mock-only, scripted single run, or recommendation-only response does not pass.

## Milestone 5 — Institutional completeness and expansion

**M5.1 — Durable authority-aware interfaces and notification channels:** authenticate actions and responses across browser, visual/audio/SMS and later app/voice paths.  
**M5.2 — Spatial registry and castle/city view:** stable object IDs and policy-filtered projection shared with the dashboard; future 3D/VR reuses the same contract.  
**M5.3 — Undercurrent private trust domain:** separately designed keys, events, storage, exports, retention and purge, with tested non-leakage. No private payload enters ordinary projections by default.  
**M5.4 — Operations hardening:** migrations, database backup/restore, host recovery and fencing, diagnostic cookbooks, deployment rollback and Component Definition of Done evidence.  
**PASS:** each substep has its own contract-specific acceptance tests; no broad “production-ready” claim without operational evidence.

## Current cursor

**M1.1:** scoped technical commissioning accepted by the Steward against Camrui release `64e8f14`; full component DoD remains open.

**M1.2:** technical criteria verified, including isolated tests, CI/revision audit and authorized deployment of migration `0001_assignment_event_ledger` to `riverview_dev`; full component DoD remains open.

**M1.3:** Scoped technical commissioning PASS on Camrui at source commit `9ca7cb189d1e1f57c69395303a9367fabd979ff5`. Migration 0002, unattended event progression, causal ordering, durable cursor, restart, PostgreSQL session-loss recovery, rollback/redeployment, and M1.1 preservation are verified. The full component DoD remains OPEN; this is not a claim that the later dashboard, autonomy, external observability, or project completion criteria are satisfied.

**M1.4:** Isolated technical criteria verified at source commit `549bd08b9b1800981c6c4c006dbe59d8fed0a799`: age-ordered independent claims, an active stalled lease not blocking unrelated progress, concurrent distinct claims, expiry generation increment, stale token rejection, and idempotent start. Evidence is in the M1.4-001 engineering record. No shared-schema migration, service deployment, operational commissioning, or full component DoD is claimed.

**M2.1–M2.3 — Execution, independent verification, and restart recovery:** Integrated on `main` at `4f028a138c41665239bde2c11be65b0f841f02bf` by PRs #9, #10, and #12. The combined isolated PostgreSQL 16.15 suite passed 89/89 on Camrui; graph validation and the controlled revision audit passed, and GitHub main CI passed. This confirms the integrated engineering baseline only; the M2.1–M2.3 live deployments and full component DoD remain open.

**M2.4 — CME monitoring service:** Isolated technical criteria PASS at `a44091bc32e82580dd8a3350e1ecfa47b0157b36`, integrated by PR #14. The authorized shared `riverview_dev` migration chain and dedicated systemd monitor were commissioned on Camrui from `702f5db3f03669427a3625425eca04c023a0754c`. The live service reported healthy and recorded three genuine stale-assignment alerts; manual restart and systemd recovery after SIGKILL preserved those alert IDs without duplicates. Scoped operational criteria PASS. Full component DoD remains OPEN; no live worker is registered, and no unrelated live assignment progress was available to observe. See `docs/development/M2.4-001_REVISION_RECORD.md` and `evidence/checkouts/M3.1-CME-LIVE/20261010T223049Z-702f5db/`.

**M3.1 — Read-only status projection and browser dashboard:** Scoped technical implementation **ACCEPTED BY THE STEWARD on 2026-10-11 UTC** under the overnight work order, based on Camrui commissioning evidence at deployed release `008d942ea57116b0fbdead771c201d3f99305482`, records/CI commit `6926ac129cca8f733048cbf478d27d6bf00248dc`, live-worker/independent-verification evidence, passing full suite and CI, and the earlier external Windows snapshot. Acceptance is scoped to the M3.1 technical implementation only. The full component DoD remains OPEN: no post-change Windows visual confirmation of the graph/cookbook pages, no sustained operational-autonomy demonstration, and later console/chat/actionable-control requirements remain. PR #16 remains open/draft and unmerged; see its Steward acceptance comment and `docs/development/M3.1-001_REVISION_RECORD.md`.

**M3.2 — Durable notification and decision requests:** Scoped technical criteria PASS at `0fd10357ccdf2c9a0c87ba4a6f41e37ecff33ce9`. The additive `0006_durable_notifications` migration and dedicated dispatcher were commissioned on Camrui with a protected backup/restore drill. Three genuine persisted CME stall events produced three durable notices; browser rendering and explicit acknowledgment were recorded, and dispatcher restart retained the same notice identities without duplicates. Live dashboard/notification browser verification passed with no browser errors. Isolated full suite passed 125/125 with zero skips; CI, graph synchronization (11 workflows / 209 nodes), and revision audit passed. Live `awaiting_steward` decision-request creation was not exercised because no such assignment exists in the shared database; isolated tests cover request/no-authority-effect behavior. This is technical commissioning evidence, not full component DoD or Steward acceptance. See `docs/development/M3.2-001_REVISION_RECORD.md` and `evidence/checkouts/M3.2/20261011T040851Z-0fd1035/`.

**Current step: M3.3 — First end-to-end unattended demonstration — BLOCKED at live authority enforcement/commissioning.** M3.3 remains the earliest unaccepted roadmap step. The shared runtime still has no database-enforced Steward-grant validation on assignment/worker control, so no new live assignment can yet be represented as safely authorized. A bounded read-only repository-source provider is implemented and has passed isolated PostgreSQL worker/artifact/distinct-verifier tests; it pins source commit/checksums and supports only the deterministic worker contract. The provider is not configured in a live worker, has no learning store, and is not a general institutional knowledge provider. The worker default remains fail-closed. After the original 141/141 suite on `59114e1`, the real-provider parallel proof and complete suite passed 143/143 with zero skips on `39ab8fb`: unsupported contract `NO_MATCH` remained waiting while a peer produced an artifact accepted by a distinct verifier. This is isolated engineering evidence, not live M3.3 commissioning; evidence is `evidence/checkouts/M3.3-REAL-PROVIDER-PARALLEL/20261011T051252Z-39ab8fb/`. Dashboard-only release `7a9ff46` serves the bounded restart recovery instructions and repository-provider runbook; Firefox confirmed the live projection, healthy CME, persisted attention, graph rendering, zero browser errors and 21 reachable documentation links. Evidence is `evidence/checkouts/M3.3-DASHBOARD-KNOWLEDGE/20261011T050604Z-7a9ff46/`. No live authority identity/grant or assignment was created. M4.1 authority-boundary work continues as the unblocker; the M3.3 live two-assignment recovery demonstration must follow. See `docs/development/M3.3-001_REVISION_RECORD.md`, `docs/development/M4.1-001_REVISION_RECORD.md`, and the provider checkout evidence. PRs #17–#19 remain draft/open and unmerged.

**M4.1 deployment/view checkpoint (2026-10-11):** PR #18 source commit `b63f6d85e7837caaa03265aa19164b57c818c8d9` is deployed as a dashboard-only release so the M4.1 cookbook and canonical graph can be browsed. Firefox confirmed the graph and docs; no authority migration, identity, grant, credential, worker, or assignment was deployed or created. M4.1 remains IN PROGRESS and M3.3 remains BLOCKED at live authority/knowledge preflight. Evidence is `evidence/checkouts/M4.1-DASHBOARD-DOCS/20261011T043757Z-b63f6d8/`.

**Grace Operational Integration:** M4.4 is a mandatory project completion deliverable, not an optional enhancement. Its future reasoning, planning, delegation, CME observation, independent-verification feedback and replanning loops are registered in the canonical process graph. This directive records architecture and acceptance requirements only; Grace is not yet implemented or operationally verified. M3.3 remains the current unaccepted roadmap step; full Grace integration remains a later mandatory system-level gate.

## Revision history

- **1.1.10 — 2026-10-11:** Record M4.1 isolated privilege feasibility and dashboard-only graph/cookbook deployment; preserve M3.3 as blocked and unaccepted.
- **1.1.11 — 2026-10-11:** Record the pinned repository provider and isolated worker/verifier evidence; keep M3.3 blocked on live database-enforced authority.
- **1.1.12 — 2026-10-11:** Record the dashboard-only repository cookbook deployment and live browser evidence without advancing M3.3 past its authority gate.
- **1.1.13 — 2026-10-11:** Record the refreshed operations documentation release and browser verification while preserving M3.3's live authority gate.
- **1.1.14 — 2026-10-11:** Record the real-provider concurrent wait/progress integration evidence and 143-test suite without claiming live M3.3 completion.
- **1.0.1 — 2026-10-09:** Recognize “go” and “next” as equivalent roadmap advancement commands. Predecessor: `docs/history/ROADMAP_rev1.0.0.md`.

- **1.0.0 — 2026-10-09:** Initial ordered, test-gated roadmap grounded in current repository contracts.
- **1.0.2 — 2026-10-10:** Record scoped M1.1 Steward technical acceptance, M1.2 shared development migration verification, and M1.3 as the next eligible engineering milestone; no full component DoD waived.
- **1.0.3 — 2026-10-10:** Record M1.3 isolated implementation and test status; milestone remains in progress pending supervised deployment and operational acceptance.
- **1.0.4 — 2026-10-10:** Record M1.3 controlled commissioning, event-ordering correction, credential-delivery contract and recovery workflow; keep milestone active pending executed Camrui evidence.
- **1.0.5 — 2026-10-10:** Record scoped M1.3 technical commissioning PASS and advance the engineering cursor to isolated M1.4 work; full component DoD remains open.
- **1.0.6 — 2026-10-10:** Record M1.4 isolated roadmap technical criteria as verified and start M2.1 isolated worker-adapter engineering; M1.4 deployment and full component DoD remain open.
- **1.0.7 — 2026-10-10:** Add mandatory M4.4 Grace Operational Integration, system-level acceptance evidence and explicit dependencies; record it as not yet implemented without interrupting M2.1.
- **1.0.8 — 2026-10-10:** Record M2.1/M2.2 verified isolated PR state and begin M2.3 failure/restart recovery; preserve non-merged status and no deployment claim.
- **1.0.9 — 2026-10-10:** Record M2.3 isolated technical PASS and advance engineering cursor to M2.4 while preserving the open PR stack and deployment/full-DoD limitations.
- **1.1.0 — 2026-10-10:** Record PR #9/#10/#12 integration, combined isolated baseline verification, retirement of their fully merged feature branches, and M2.4 engineering from the integrated main commit.
- **1.1.1 — 2026-10-10:** Record M2.4 isolated roadmap technical PASS, retain its open live-service/full-DoD obligations, and identify M3.1 as the next milestone after M2.4 integration.
- **1.1.2 — 2026-10-10:** Reconcile M2.4 PR #14 integration on main and record M3.1 as active from the verified integrated baseline; preserve the unmerged draft PR #15 status.
- **1.1.3 — 2026-10-10:** Record authorized shared M2.4 migrations, installed monitor health/restart recovery, and actual live dashboard integration while retaining M3.1 as active and full DoD obligations open.
- **1.1.4 — 2026-10-10:** Include readable diagnostic documents and canonical graph visualization in M3.1 acceptance, record the Steward's external browser observation and live worker integration evidence, and propose (without accepting) M3.4 ownership for Issue #13's actionable console/resident-chat requirements.
- **1.1.5 — 2026-10-11:** Record the Steward's scoped technical acceptance of M3.1 without waiving full component DoD; advance the cursor to M3.2 durable notification and decision requests.
- **1.1.6 — 2026-10-11:** Remove trailing whitespace detected during acceptance-record checkout.
- **1.1.7 — 2026-10-11:** Correct the Grace section cursor reference to reflect M3.2 as the current step.
- **1.1.8 — 2026-10-11:** Record scoped M3.2 technical commissioning and advance the engineering cursor to M3.3; retain open full-DoD and live decision-request limitations.
- **1.1.9 — 2026-10-11:** Preserve M3.3 as the earliest unaccepted step while recording live authorization/knowledge preflight blockers and M4.1 unblocker engineering.
