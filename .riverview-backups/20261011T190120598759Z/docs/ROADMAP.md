# Riverview~ Implementation Roadmap

**Document Revision:** 1.1.39
**Status:** Active planning baseline — execution gates require evidence  
**Date:** 2026-10-11
**Component:** RV-ROADMAP  
**Owner:** Steward  
**Changed:** 2026-10-11 UTC | RV-M3.3-GOVERNED-INTAKE-ROUTE | Update M3.3 engineering and commissioning state after request API/provider integration
**Changed:** 2026-10-11 UTC | RV-M3.3-LIVE-COMMISSIONING | Record live governed request, worker, artifact, verifier, dashboard and recovery evidence; retain concurrency/full-DoD limits
**Changed:** 2026-10-11 UTC | RV-M3.3-WAITING-ISOLATION | Verify a real NO_MATCH assignment remains waiting while the scheduler executes and verifies an unrelated valid assignment
**Changed:** 2026-10-11 UTC | RV-M3.3-HISTORICAL-BLOCKER-CLARIFICATION | Label pre-commissioning M4.2 checkpoint status as historical and point to current M3.3 evidence
**Changed:** 2026-10-11 UTC | RV-M4.1-GRACE-BOOTSTRAP-STATUS | Reconcile current M3.3 status and resume dependent M4.1 engineering
**Changed:** 2026-10-11 UTC | RV-M4.1-GRACE-IDENTITY-COMMISSIONING | Record exact-commit Grace identity bootstrap and independent grant verification
**Changed:** 2026-10-11 UTC | RV-M3.3-COURSE-CORRECTION | Reconcile assignment-level concurrency evidence with M3.3 criteria and preserve its Steward-review gate
**Changed:** 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-CHECKPOINT | Record model-independent persistent service implementation without claiming live Grace acceptance
**Changed:** 2026-10-11 UTC | RV-M4.1-M4.2-OCCUPANT-REPLACEMENT-INTEGRATION | Record isolated cross-component office-state continuity and exact-grant replacement verification
**Changed:** 2026-10-11 UTC | RV-M4.1-CROSS-INTEGRATION-CI | Record passing exact-head CI for commit 89752f7
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

**M1.4:** Isolated technical criteria verified at source commit `549bd08b9b1800981c6c4c006dbe59d8fed0a799`: age-ordered independent claims, an active stalled lease not blocking unrelated progress, concurrent distinct claims, expiry generation increment, stale token rejection, and idempotent start. The live `riverview_dev` catalog was later confirmed to contain `0001_assignment_leases` as a dependency in the worker/monitor migration chain; its checksum matches the checked-in migration. That migration presence is not a separate M1.4 scheduler-service commissioning or acceptance. No standalone scheduler service or M1.4 operational acceptance/full Component DoD is claimed. The original isolated checkout evidence remains valid for its stated scope; see the dated live-state correction in `docs/development/M1.4-001_REVISION_RECORD.md` and the operations cookbook evidence.

**M2.1–M2.3 — Execution, independent verification, and restart recovery:** Integrated on `main` at `4f028a138c41665239bde2c11be65b0f841f02bf` by PRs #9, #10, and #12. The combined isolated PostgreSQL 16.15 suite passed 89/89 on Camrui; graph validation and the controlled revision audit passed, and GitHub main CI passed. This confirms the integrated engineering baseline only; the M2.1–M2.3 live deployments and full component DoD remain open.

**M2.4 — CME monitoring service:** Isolated technical criteria PASS at `a44091bc32e82580dd8a3350e1ecfa47b0157b36`, integrated by PR #14. The authorized shared `riverview_dev` migration chain and dedicated systemd monitor were commissioned on Camrui from `702f5db3f03669427a3625425eca04c023a0754c`. The live service reported healthy and recorded three genuine stale-assignment alerts; manual restart and systemd recovery after SIGKILL preserved those alert IDs without duplicates. Scoped operational criteria PASS. Full component DoD remains OPEN; no live worker is registered, and no unrelated live assignment progress was available to observe. See `docs/development/M2.4-001_REVISION_RECORD.md` and `evidence/checkouts/M3.1-CME-LIVE/20261010T223049Z-702f5db/`.

**M3.1 — Read-only status projection and browser dashboard:** Scoped technical implementation **ACCEPTED BY THE STEWARD on 2026-10-11 UTC** under the overnight work order, based on Camrui commissioning evidence at deployed release `008d942ea57116b0fbdead771c201d3f99305482`, records/CI commit `6926ac129cca8f733048cbf478d27d6bf00248dc`, live-worker/independent-verification evidence, passing full suite and CI, and the earlier external Windows snapshot. Acceptance is scoped to the M3.1 technical implementation only. The full component DoD remains OPEN: no post-change Windows visual confirmation of the graph/cookbook pages, no sustained operational-autonomy demonstration, and later console/chat/actionable-control requirements remain. PR #16 remains open/draft and unmerged; see its Steward acceptance comment and `docs/development/M3.1-001_REVISION_RECORD.md`.

**M3.2 — Durable notification and decision requests:** Scoped technical criteria PASS at `0fd10357ccdf2c9a0c87ba4a6f41e37ecff33ce9`. The additive `0006_durable_notifications` migration and dedicated dispatcher were commissioned on Camrui with a protected backup/restore drill. Three genuine persisted CME stall events produced three durable notices; browser rendering and explicit acknowledgment were recorded, and dispatcher restart retained the same notice identities without duplicates. Live dashboard/notification browser verification passed with no browser errors. Isolated full suite passed 125/125 with zero skips; CI, graph synchronization (11 workflows / 209 nodes), and revision audit passed. Live `awaiting_steward` decision-request creation was not exercised because no such assignment exists in the shared database; isolated tests cover request/no-authority-effect behavior. This is technical commissioning evidence, not full component DoD or Steward acceptance. See `docs/development/M3.2-001_REVISION_RECORD.md` and `evidence/checkouts/M3.2/20261011T040851Z-0fd1035/`.

**Current engineering cursor: M4.1 — Office, occupant, implementation and state separation.** M3.3 scoped technical criteria PASS and ready for Steward review; formal acceptance and full Component DoD remain OPEN. On Camrui, source/deployment `47a79adafe1524b3e819148b70c02a1857f50dbf` processed a real Steward-authorized governed request via the loopback `AuthorizedAssignmentIntake` route. An unauthorized request returned HTTP 403 without assignment/event persistence; authorized requests returned HTTP 200 and transactionally persisted assignment/event rows. A grant-bound persistent systemd executor used the real commit-pinned `RepositoryKnowledgeProvider`, ran the registered repository test task, wrote actual mode-0600 report artifacts, and a separately credentialed/granted verifier independently reran the tests and recorded ACCEPTED. PostgreSQL retains assignment lifecycle events, attempts/results, verification records, and VERIFIED grounding/preflight/regrounding provenance. Authenticated dashboard projections display completed and waiting work, correlation IDs and verifier outcomes. An executor SIGKILL/restart preserved a completed assignment without duplicate attempt; a separate five-minute executor outage left two assignments durable, emitted stall/attention events, and both completed after restart. A further live isolation check created an authorized unsupported-contract assignment; the real provider returned `NO_MATCH`, and the assignment remained `blocked/WAITING_FOR_EVIDENCE`. While it remained waiting, the same normal scheduler accepted, executed, artifacted and independently verified a distinct valid assignment. The dashboard API returned HTTP 200 for both projections and showed waiting and completed truthfully. This demonstrates the roadmap criterion of two concurrent durable assignments progressing independently, including a waiting assignment not blocking eligible work. The roadmap does not define simultaneous multi-executor throughput as a separate M3.3 criterion; no such throughput is claimed. Evidence is retained in `evidence/checkouts/M3.3-LIVE-E2E/20261011T1245Z-47a79ad/` and `evidence/checkouts/M3.3-WAITING-ISOLATION/20261011T1310Z-47a79ad/`. CI, full suite, process graphs and revision audit pass. No formal Steward acceptance or merge is claimed; PR #21 remains open/draft. Full Component DoD, including sustained Grace-directed autonomous operation and other later roadmap obligations, remains open.

**Current M4.1 identity-bootstrap result (2026-10-11):** Exact-head CI passed at `fb536bb647d7d7a655a56155f687c74bec219945` (run `38142915471`). The committed helper was installed root-owned and executed additively against the dedicated authority schema. The first run returned `PROVISIONED`, a fresh-process retry returned `ALREADY_PROVISIONED`, and independent grant verification passed for `office.state.write` on `office:office:grace`. The credential remains root:root 0600; all seven M3.3 services stayed active. Evidence: `evidence/checkouts/M4.1-GRACE-IDENTITY/20261011T1330Z-fb536bb/`. This is identity-bootstrap commissioning only; the resident service and Grace-directed execution cycle remain unimplemented.

**M4.1 deployment/view checkpoint (2026-10-11):** PR #18 source commit `b63f6d85e7837caaa03265aa19164b57c818c8d9` is deployed as a dashboard-only release so the M4.1 cookbook and canonical graph can be browsed. Firefox confirmed the graph and docs; no authority migration, identity, grant, credential, worker, or assignment was deployed or created. M4.1 remains IN PROGRESS and M3.3 remains BLOCKED at live authority/knowledge preflight. Evidence is `evidence/checkouts/M4.1-DASHBOARD-DOCS/20261011T043757Z-b63f6d8/`.

**M4.1 isolated boundary correction (2026-10-11):** The authority provisioner now requires a dedicated authority-only schema; rejects unrelated tables/functions and unsafe manager memberships; revokes `PUBLIC`/runtime schema access; and gives a NOINHERIT, no-membership manager only allowlisted table DML. The complete isolated PostgreSQL suite passed 135/135 (zero skips/failures/errors), teardown left zero test schemas/roles, process graph passed at 12 workflows / 227 nodes, the controlled revision audit had zero findings, and exact-head PR #20 CI passed (run 38119049973). A later helper diagnostic correction passed three focused PostgreSQL boundary tests and exact-head full CI run 38120458854; it now reports safe static reasons and SQLSTATE-only driver failures. A protected PostgreSQL 16.15 backup and disposable restore rehearsal also passed with matching catalog counts; the two failed preflight attempts and path correction are documented. Evidence is linked in `docs/development/M4.1-001_REVISION_RECORD.md` and `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T070500Z-backup-restore/`. A current read-only Camrui preflight confirms `riverview_authority`, its manager/owner roles and nine tables are absent; the mixed `riverview_dev` remains runtime-owned with 67 objects and runtime schema access. The helper fails closed and no `--apply` was run. This is not shared-schema commissioning: no role, credential, schema, identity, grant, worker state, or service was changed. Evidence: `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T070335Z-live-preflight/`. M4.1 remains IN PROGRESS; M3.3 still requires live authorization/worker integration and the separate real knowledge-provider requirement.

**M4.1 fresh-schema migration correction (2026-10-11):** The authority test fixture had precreated the general Core migration ledger, masking that an empty dedicated registry schema cannot record migration checksums. Added idempotent authority migration 0000 to bootstrap that ledger and verified the package from an empty schema. Full isolated PostgreSQL suite passed 137/137 (zero skips/errors/failures), cleanup left zero test schemas/roles, the private test server stopped, graph check passed 12 workflows/228 nodes, compileall passed and revision audit reported zero issues. Exact-head GitHub controlled-checkout run 38121104825 passed at `73613ce`, including complete tests, graph validation and revision/predecessor checks. Evidence: `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T072000Z-fresh-schema-ledger/`. Shared Camrui remains unchanged; dedicated authority schema/roles and runtime integration are still absent. M4.1 remains IN PROGRESS and M3.3 remains the earliest unaccepted roadmap item.

**Grace Operational Integration:** M4.4 remains a mandatory project completion deliverable, not an optional enhancement. The PR #23 infrastructure supplies durable objectives, bounded repository grounding, typed proposals, exact-grant CME assignment handoff, and a deterministic bounded artifact worker/verifier. The dependent persistent-execution increment adds a supervised reconciliation loop, exact-grant dashboard objective routes, durable heartbeat/failure projections, retry ceilings, and repeated PostgreSQL integration coverage. These are model-independent infrastructure capabilities only. No Grace execution unit or migration has been installed on Camrui; no live model reasoning, general coding executor, service credential/grant provisioning, or sustained operational Grace cycle is claimed. M4.4 and its full Component DoD remain OPEN, and the canonical process graph retains the remaining reasoning, follow-up, replacement, and live commissioning gates.

**M4.3 isolated local-inference technical criterion (2026-10-11):** On the existing M4.2 engineering branch, an optional loopback-only `local.inference.v1` action now uses the existing PostgreSQL worker capability, exact-grant, durable intent/artifact and independent-verification boundaries. At source commit `bbe9a6c1c63345861da5bfeb7cfb77931961e005`, a pinned CPU llama.cpp/Qwen3 test run processed two distinct assignments concurrently; both artifacts had independently recomputed SHA-256 digests, distinct verifier records, and completed states. The measured model calls overlapped for 18.551 seconds; the isolated schema and temporary server were removed. The complete suite passed 155/155 with zero skips; graph validation passed 13 workflows / 269 nodes; controlled revision audit had zero findings; and exact-head CI run 38129918014 passed. This advances M4.3 isolated technical engineering only: no persistent worker service, general reasoning quality, external knowledge provider, M3.3 completion, M4.3 full DoD, or Grace acceptance is claimed. The earliest roadmap cursor remains M3.3, blocked by authorized assignment intake, operational worker commissioning, and the real institutional knowledge provider. Evidence and a preserved failed classification attempt are in `evidence/checkouts/M4.3-LOCAL-INFERENCE/` and `docs/development/M4.3-001_REVISION_RECORD.md`.

**M1.4 live dependency correction (2026-10-11 UTC):** A read-only `sudo -u postgres psql` inspection found the shared `riverview_dev.schema_migrations` row `0001_assignment_leases` applied at `2026-10-10 18:27:04.341175-04:00`, with SHA-256 `ce29c2994904f54706db883f61127bf05ee195ecbdce90e7242886e86711b717`, matching `src/riverview_core/assignment_scheduler/migrations/0001_assignment_leases.sql`. This was applied as part of the later worker and monitor migration chain. It corrects the earlier “no shared migration” statement without claiming M1.4 runtime commissioning; the standalone scheduler service, full M1.4 exit gate and Component DoD remain open. Exact read-only output is in `evidence/checkouts/OPERATIONS-COOKBOOK/20261011T055428Z-pg-doc-safety/live-peer-inspection.txt`.

**M4.2 isolated engineering checkpoint (2026-10-11):** A provider-neutral resident reasoning/regrounding contract and PostgreSQL-backed office-state persistence are implemented on dependent branch `codex/m4.2-resident-reasoning`, based on PR #20's M4.1 boundary head. Focused tests passed 10/10 and the complete suite passed 147/147 on disposable PostgreSQL 16.15; cleanup reported zero test schemas/roles, graph validation passed (13 workflows/255 nodes), compileall passed, and the controlled revision audit reported zero issues. Exact-head GitHub controlled-checkout CI run 38122430742 passed on commit `bf9905af575da6b0254920e467476f0883156050`. PR #21 is draft/open/unmerged and depends on open PR #20. This proves isolated behavior only: no live authority registry, reasoning provider, resident service, dashboard conversation or operational plan delegation was deployed. M4.2 remains IN PROGRESS; its full acceptance and DoD are open. At that historical checkpoint M3.3 was blocked on live authority integration and real knowledge-provider availability. Those blockers were resolved by the later Camrui commissioning documented in the current M3.3 status above and `docs/development/M3.3-001_REVISION_RECORD.md`. No branch merge or operational-state modification was claimed at that checkpoint.

**M4.1/M3.3 exact-grant integration follow-up (2026-10-11):** Added migration `0002_exact_grant_authorization.sql`, a bounded security-definer function, and runtime `ExactGrantAuthorizer`; worker registration, execution and verification now check exact grants. The isolated PostgreSQL suite passed 150/150; graph validation (13 workflows/265 nodes), compileall, controlled revision audit, and exact-head CI passed. A fresh protected full backup restored to a unique disposable database with matching migration/assignment/event counts; after that rehearsal, live migration 0002 and the function-only runtime ACL were applied to `riverview_authority`. The provisioner returned `apply_required=false` on postflight. A rollback-only real runtime-role transaction verified exact-grant allow and wrong-action, direct-table, and manager-function denial; no test row persisted. Evidence is in `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T090500Z-exact-grant-worker-integration/` and `20261011T090700Z-live-exact-grant/`. All operational services stayed active; `riverview_dev` remains 9 migrations, 4 assignments, 11 events. This is scoped database-boundary commissioning, not M4.1 or M3.3 DONE. Worker-service integration, `assignment.create`, commissioned real worker, and actual external knowledge provider remain open. PR #21 remains draft/open/unmerged.

**M4.1 live authority bootstrap correction (2026-10-11):** A protected `riverview_dev` dump was restored successfully into a disposable database and removed after matching catalog checks. Exact source `d3a0ed4fdec3061923964451ce2fccff18fadca7` passed preflight/apply/postflight in the dedicated authority schema. The root-only token bootstrap returned `BOOTSTRAPPED`, then `ALREADY_BOOTSTRAPPED` on a fresh process; an independent database-role check matched its digest and confirmed three scoped active grants without displaying the token. Runtime direct reads and manager DDL remained denied; core state remained at 9 migrations, 4 assignments, 11 events. PostgreSQL, event processor, CME monitor, notification dispatcher, dashboard and SSH stayed active. Evidence: `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T081700Z-live-bootstrap/`. Exact-head CI run 38124331966 passed on `f807d95d688b8a486db34eb5aa4be9f78c8f998d`. This is scoped M4.1 DB/bootstrap verification, not M4.1 DONE: no resident/worker service yet consumes the registry. M3.3 still requires exact-grant assignment/worker integration and a real knowledge provider. PR #21 remains open/draft/unmerged.

**M4.1/M4.2 occupant-replacement integration regression (2026-10-11):** A new isolated PostgreSQL integration test composes the authority registry with `ResidentReasoner`: it persists a plan as the first occupant, replaces the bound occupant and implementation, confirms the former occupant's exact office-state grant is revoked, then constructs a replacement runtime that resumes the office-keyed plan under the new binding revision and provider. The focused ResidentReasoning suite passed 12/12; the complete isolated PostgreSQL 16 suite passed 212/212 with zero skips, errors or failures. Process graph validation passed at 16 workflows / 330 nodes and the controlled revision audit returned zero issues. The fixture schema count was zero and the private test cluster was stopped. Exact-head GitHub CI passed on commit `89752f79487cf9178484db6451a4c36fd107b80a` (run [38165302494](https://github.com/ppow1/Riverview-/actions/runs/38165302494)). This is isolated test evidence, not live occupant replacement or resident-service commissioning. M4.1 remains in progress; the M3.3 scoped technical gate remains ready for formal Steward acceptance, which is still open. Evidence and limits are recorded in `docs/development/M4.1-001_REVISION_RECORD.md`.

## Revision history

- **1.1.32 — 2026-10-11:** Clarify that the M4.2 checkpoint blocker statement predates and is superseded by M3.3 live commissioning.

- **1.1.31 — 2026-10-11:** Record live NO_MATCH isolation and valid-task continuation; update scoped M3.3 technical status without claiming Steward acceptance.

- **1.1.30 — 2026-10-11:** Record live M3.3 vertical-slice evidence and preserve the unverified concurrent-worker/full-DoD gate.

- **1.1.17 — 2026-10-11:** Record safe M4.1 preflight diagnostics, focused PostgreSQL regressions and exact-head CI; preserve live no-schema blocker.
- **1.1.19 — 2026-10-11:** Record exact-head passing CI for the fresh-schema migration correction; retain live provisioning and M3.3 gates.
- **1.1.20 — 2026-10-11:** Record M4.2 isolated PostgreSQL verification while preserving M3.3 as the earliest unaccepted cursor and retaining live authority/provider gates.
- **1.1.21 — 2026-10-11:** Record exact-head M4.2 CI success and draft PR #21 while retaining M3.3 and live commissioning gates.
- **1.1.22 — 2026-10-11:** Correct current M4.1 live-state and M3.3 dependency status using protected backup/restore, root-local bootstrap, postflight and exact-head CI evidence; retain service integration, real knowledge-provider, M4.2 and full DoD requirements.
- **1.1.23 — 2026-10-11:** Record isolated exact-grant enforcement at worker boundaries and narrow remaining M3.3 deployment, assignment-intake and real knowledge-provider blockers.
- **1.1.25 — 2026-10-11:** Record CI-gated live migration 0002 and exact function ACL commissioning, update the M3.3 blocker state, and retain service/provider gates.
- **1.1.26 — 2026-10-11:** Record M4.3 isolated local inference, concurrent durable results, independent verification, precise limitations, and preserve M3.3 as the current blocked cursor.
- **1.1.27 — 2026-10-11:** Record committed-source M4.3 re-execution, full local/CI test results, graph/revision validation, and retain M3.3 and full-DoD gates.
- **1.1.24 — 2026-10-11:** Record the corrected 150-test isolated suite, migration idempotency test, audit results, and exact-grant deployment/CI gates still open.
- **1.1.18 — 2026-10-11:** Record fresh-dedicated-schema migration-ledger defect and 137-test isolated correction; preserve live provisioning and M3.3 gates.

- **1.1.16 — 2026-10-11:** Record exact Camrui M4.1 catalog preflight and no-apply result; retain M4.1/M3.3 blockers.

- **1.1.15 — 2026-10-11:** Record protected PostgreSQL backup and isolated restore rehearsal; retain live M4.1 commissioning and M3.3 blockers.

- **1.1.14 — 2026-10-11:** Record exact-head M4.1 isolated 135-test verification and passing CI while retaining the open live commissioning and M3.3 blockers.

- **1.1.10 — 2026-10-11:** Record M4.1 isolated privilege feasibility and dashboard-only graph/cookbook deployment; preserve M3.3 as blocked and unaccepted.
- **1.1.11 — 2026-10-11:** Record the packaged, isolated M4.1 privilege-boundary implementation and test; preserve the live schema-owner blocker and M3.3 status.
- **1.1.12 — 2026-10-11:** Correct M1.4 shared migration status from read-only live evidence; retain the separate service commissioning and full-DoD gates.
- **1.1.13 — 2026-10-11:** Record the isolated M4.1 privilege boundary correction and process-graph/revision work without claiming live commissioning or advancing M3.3.
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

- **1.1.28 — 2026-10-11:** Record isolated atomic exact-grant assignment intake and its test evidence while keeping M3.3 blocked on governed application integration, live worker commissioning and real knowledge provider.

- **1.1.33 — 2026-10-11:** Reconcile M3.3 scoped technical status and resume M4.1 engineering without claiming acceptance.
- **1.1.34 — 2026-10-11:** Record exact-commit Grace identity bootstrap and independent exact-grant verification; retain M4.1/M4.4 open gates.
- **1.1.38 — 2026-10-11:** Add an isolated authority/reasoner occupant-replacement integration regression; preserve M3.3 formal-acceptance and full-DoD gates.
- **1.1.39 — 2026-10-11:** Link the passing exact-head CI result for the isolated occupant-replacement regression.
