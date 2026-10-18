# Grace next-stage roadmap — temporary planning record
Date: 2026-10-18
Status: PARKED / PLANNING ONLY — Steward discussion; not implementation authorization
Repository: ppow1/Riverview-
Baseline: four-PR integration candidate PR #113; reasoning-adapter audit PR #114.
Purpose: preserve the next-stage requirements until the current operational acceptance gates are met.

## Definitions — do not conflate
- Grace's NORMAL reasoning uses the local 80B model. Local 0.6B is autonomic/routing capability and local 30B is an intermediate, vision-enabled capability.
- ESCALATED reasoning means consultation with external ChatGPT for help, second opinion, or difficult questions. It is advisory and must preserve Grace's institutional authority and authorization boundaries.
- Codex CLI artifact-execution transport and external ChatGPT advisory reasoning exchange have different contracts. Do not treat their outputs as interchangeable.

## Immediate acceptance gates — FIRST PRIORITY
1. Review/accept the integrated PR #113 (composed of #109, #110, #111, #112) and compatible PR #114. No merge/deployment is authorized by this planning document.
2. Commission and demonstrate genuine Grace -> external ChatGPT -> Grace escalated advisory reasoning, including authorized provider identity, correlated durable response, deferred return, and bounded failure recovery.
3. Demonstrate one real Engineering objective end-to-end: Steward request -> Grace interprets -> forms authorized work order -> dispatches to Local Execution Adapter -> collects evidence -> evaluates completion or requests rework -> independent audit/verification (or authorized escalated second opinion) -> closes and decides what to do with the output -> reports back. Demonstrate continuation across a rework loop, not only a happy-path one-shot.
4. Avoid additional architectural rewrites unless required by verified blockers. Production grants, credentials, migrations, deployments and live objectives need separate explicit Steward authorization.

## Next priority: model-aware task routing, queuing and context budgets
- Inventory actual deployed model identity, endpoint, health, maximum advertised context, configured server context, context PER CONCURRENT SLOT, prompt overhead, reserved generation budget, slot count, queue depth, active claims, estimated wait, throughput and memory pressure. Inspect live config and measured telemetry; do not invent numbers.
- Prior history: 80B approximately 65,536 configured context and 4 slots in one tested configuration, which MAY yield about 16,384 tokens/slot depending on runtime. Other 128K/262K attempts were not established as stable. User recalls 30B 8-way concurrency; verify. Historical 4K shared context caused overflows. 0.6B context unknown. Model advertised limits are not operational per-request limits.
- Before dispatch, classify task needs: vision, complexity, expected context input/output, tools, latency, urgency, privacy, provider availability and required quality. Route screenshots to the vision-capable 30B, not text-only 80B. For eligible text tasks, idle 30B can be useful when 80B is queued; never substitute a weaker model when task requirements exceed its capability.
- Context admission should count tokens including system prompts, tools, retrieved evidence, history, and output reserve. Reject oversized jobs BEFORE provider submission. Use bounded chunking, hierarchical summaries, task decomposition, provenance-preserving partial results, and final synthesis as needed.
- Maintain durable queue/claims with fairness, backpressure, prioritization, retries, timeouts, cancellation and crash recovery; distinguish queue waiting from inference errors. Avoid oversubscription and race conditions between planner selection and actual seat claims.
- Reuse existing ResourceRegistry, CapabilityRegistry, ResourcePlanner, DurableResourcePlanner, policy/seat claims and scheduler where present. Verify how much is actually wired to Grace; do not duplicate existing infrastructure. Earlier review noted resource selection and work-order claims may not be atomically coupled; recheck.
- Provide explainable dispatch decisions and metrics: why selected, actual allocated context, queue time, overflow/timeout rates, retries, throughput and result quality.

## Following priority: Grace's governed learning cycle
- When work yields reusable information, Grace should detect candidate knowledge, preserve source/evidence/provenance, distinguish observed claims from validated facts, propose durable known-fact updates, obtain required review/approval, and retrieve/use accepted knowledge on subsequent tasks.
- Support corrections, contradiction resolution, confidence/validity, supersession, and forgetting/retirement of obsolete facts. Do not silently turn unverified model output into canon.
- Reconcile against existing parking lot/punch list and knowledge/Cookbook/diagnostic infrastructure before implementation. Keep personal identity/canon updates separate from operational facts.

## Following priority: Jessica and character continuity
- Restore Jessica as Chief Character Architect with her professional doctrine, character store, evidence, proposals, review and publication boundaries. Bring her conversational cognition into contact with existing workflows.
- Jessica should develop and restore Grace's personality, history, conversational voice, relationships and continuity while preserving Grace's operational reliability and governed canon. Grace must become more than a work-only interface.
- Only then plan onboarding additional residents through Jessica's character architecture and governed residency lifecycle.
- Reuse existing Jessica roadmaps, character store, and character-development workflow; do not rebuild them.

## Backlog reconciliation task (READ-ONLY; before future implementation)
Inspect CURRENT repository parking lot, punch list, resident roadmap, architecture documents, model service configurations, and code. Produce a sourced matrix: already implemented/connected; implemented but disconnected; designed/parked; missing. Identify exact existing backlog IDs and file paths for all above items; reconcile duplicates; propose smallest staged work packages with prerequisites and acceptance tests. Do not claim this document replaces or exhaustively audits the live parking lot/punch list.

## Current evidence (2026-10-18 reports, not live deployment verification)
- PR #113 https://github.com/ppow1/Riverview-/pull/113 : integration of #109/#110/#111/#112, reported 615 passing isolated tests, GitHub CI pass, migration collision 0012/0013 resolved, package built but NOT installed. Head reported 6e18ff8fd1ea19b19ff769b559bd74e7411cd4bf.
- PR #114 https://github.com/ppow1/Riverview-/pull/114 : provider-specific compatibility audit, local conversational text-block joining and explicit rejection of unsupported mixed/tool-call output; Codex CLI execution and external MCP advisory adapters unchanged; controlled CI pass; no live model or external reasoning test. Head reported cda5581361eccf79d88c67494d76a62b6cc52978.
- Older full-system review: resource-planning substrate existed but was not fully connected to Grace; Jessica's character workflow was partly implemented but not connected to conversational cognition. Reverify against current source.
- This roadmap is a planning checkpoint, not proof that the acceptance gates have passed.

## Steward sequencing decision
NOW: external ChatGPT escalation + one complete real Grace Engineering cycle.
NEXT: model resource/context admission, queueing and explainable routing.
THEN: governed learning/known facts.
THEN: Jessica/Grace character restoration and additional residents.

## ADDENDUM 2026-10-18 — Grace process map and automated website acceptance
Steward requirement: explicitly add browser/UI testing to Grace's Engineering process map and release lifecycle. Riverview's website is expanding beyond feasible manual click-through verification. Investigate and reuse the existing CueMastery (and possibly Estate) website automation, likely Playwright, before creating a new framework. Existing test locations, completeness, and portability are NOT yet verified.

### Required process-map gates
- Work-order formation: identify whether the change affects website/UI, affected user journeys, required browser tests, and acceptance criteria.
- Engineering execution: run fast targeted unit/API tests and relevant UI/browser checks in a safe test environment; collect artifacts.
- Independent verification: execute browser flows from a distinct verification step, including navigation, sign-in/permissions where test accounts exist, forms, buttons, approval/rejection and proposal flows, deferred conversation returns, status refresh, and error/retry handling. Test exact affected workflows; do not claim full coverage from a smoke test.
- Rework loop: failures create actionable evidence (console/network errors, screenshots, trace, page URL, browser/version, exact commit) and return to Engineering for correction and re-verification; do not falsely close a work order.
- Pre-release gate: repeat relevant end-to-end tests against the staged candidate; block promotion on critical failures or missing evidence.
- Post-release gate: verify the deployed website with safe read-only/synthetic journeys and report drift or regressions. Avoid unapproved real work orders, irreversible UI actions, production test data changes, or production credentials.
- Continuous maintenance: maintain stable selectors/test IDs, versioned journey catalog, baseline screenshots where justified, flaky-test quarantine with accountability, and browser/dependency updates. Grace should know test coverage and remaining untested surfaces.

### Recovery and integration task — evidence first
1. Locate the actual existing Playwright/browser testing in CueMastery and Estate repositories, including test runners, fixtures, screenshots/traces, CI, environment setup and any prior Riverview reuse.
2. Compare it with the current Riverview website routes and workflows; produce a gap/coverage matrix and migration plan.
3. Reuse the minimum viable existing harness; prefer Linux/Ubuntu Camrui-compatible headless browser execution in isolated staging. Keep any live website tests explicitly non-destructive.
4. Wire browser acceptance evidence into the existing Engineering verification and Grace process graph through reviewed, tested source changes. Update canonical graphs, generated views, revisions and troubleshooting docs together; no unvalidated direct edits to generated graph outputs.
5. Add focused smoke tests for essential existing flows first; expand alongside website features. Include UI tests in PR/CI and release gates, with useful failure evidence and bounded retries.
6. Do not implement, deploy, merge or change production as a consequence of this temporary planning record; obtain separate authorization.

### Sequencing
This is a cross-cutting quality gate, not a distant feature after Jessica. Begin recovery/audit as soon as practical, and introduce the smallest reliable browser smoke suite BEFORE expanding or commissioning substantial new website functionality. It supports the immediate Engineering-cycle acceptance test as well as all later work (resource routing, learning UI, Jessica and resident onboarding).
