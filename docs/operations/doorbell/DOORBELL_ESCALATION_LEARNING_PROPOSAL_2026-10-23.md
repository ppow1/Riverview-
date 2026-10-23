# Proposal: Doorbell Escalation, Regrounding, Evaluation and Learning
**Status:** Proposed, not deployed | **Date:** 2026-10-23 | **Priority:** P0 transport first; incremental learning later

## Purpose
Make Riverview self-correcting: Grace executes authorized objectives; a separate deterministic supervisor detects stalled meaningful progress; durable mailbox + Camrui browser Doorbell wake ChatGPT; ChatGPT reads bounded evidence, returns actionable guidance; Grace resumes; after completion ChatGPT evaluates performance and promotes verified procedures into reusable runbooks. The Steward directs and approves consequential changes, not routine copy/paste.

## Fast-track current facts (Codex Camrui report, 2026-10-23)
- Dedicated Chrome profile was launched; configured ChatGPT conversation URL opened; CDP port 9225 live.
- 17 dispatcher/runtime tests and 5 Node bridge tests passed. MCP exchange responded with zero pending requests.
- Browser probe: `authenticated_session:false`; no wake sent.
- `RIVERVIEW_CHATGPT_DOORBELL_ENABLED=0`; provider ID not configured in service environment.
- Bridge status: mailbox and Grace result consumer not integrated; no live correlated response/receipt.
- One Python test failed to load due to missing `jsonschema`; `pytest` also absent. Treat as test-environment defects until rerun, not proof of product failure.
- No evidence of unattended post-reboot authentication or live end-to-end success. Do not claim commissioned.
- Related history: merged PR #99; unmerged/integration work #130, #131, #157. Reconcile deployed bytes against branches before editing.

## Delivery sequence (no parallel bureaucracy)
1. **Restore browser identity and persistence:** Steward signs in once to *the dedicated automation profile*, not a separate interactive profile. Check authenticated probe, correct target conversation, service launch and restart behavior; never store passwords or bypass MFA. Test browser restart and then reboot only with Steward permission. If auth expires, show an explicit needs-login blocker and notification.
2. **Enable authorized transport:** Discover existing provider identity and grants; do not invent provider IDs. Obtain Steward authorization for worker enablement/service changes and first real wake. Reuse existing PostgreSQL exchange, Comms5 provider, C2 dispatcher, Grace consumer. Fix only proven wiring/dependency gaps.
3. **One real acceptance:** Persist a harmless request, ring exactly once, ChatGPT claim/read, correlated bounded response, durable receipt, Grace consumes and advances objective. Record request IDs and timestamps. If blocked, report exact boundary immediately; avoid speculative expansion.
4. **Add independent supervisor:** Detect lack of meaningful state progress for ~180 seconds (configurable); explicit terminal errors may escalate immediately. Do not treat log chatter/reasoning attempts as progress. Rate-limit, deduplicate, lease and correlate; never allow unbounded loops.
5. **Add performance UI and learning:** Display active work, task history, attempts, escalations, response/comments, score, runbook versions and measured improvement. Extend existing objective/event/exchange schema rather than create parallel truth.

## Mandatory escalation preflight / reground
Every new ChatGPT escalation includes:
1. Short versioned **Doorbell Reground** rules, capped in size and independent of full `AI_HINTS.md`.
2. Original objective, latest approval and authority scope; never imply ChatGPT can grant new permissions.
3. Current persisted state and authoritative IDs; last meaningful progress timestamp.
4. Relevant recent actions, errors, evidence pointers, prior escalations and attempted fixes.
5. Precise question and expected bounded next step.
6. Explicit non-goals and scope boundaries.
7. Return contract: proposed next action, exact interface/actor, verification evidence, stop condition, and whether Steward decision required.

Preflight checks: valid objective and correlation IDs; source authenticity; no sensitive credentials in payload; deduplication; request not expired; authorization unchanged; runbook version/digest recorded. On missing facts, request minimal evidence rather than hallucinate.

## Escalation reasoning guardrails
- **Do not expand scope.** Fix the smallest blocker that advances the original approved objective.
- Prefer an existing verified runbook and existing tools; no new subsystem or framework unless evidence proves necessary.
- Separate observations, inferences and recommendations. Never fabricate work-order IDs, grants, completion, or tool results.
- Give one bounded corrective action with owner, input, expected result, evidence and next checkpoint. Avoid endless analysis/qualification chains.
- Honor authorization: advice is not an execution grant. Stop for credentials, production mutation, irreversible operations or policy decisions requiring Steward approval.
- If same correction fails twice, change strategy or report a genuine blocker; do not spam retries.
- Respond using a durable correlated schema; include request ID, objective ID, disposition (continue / needs_evidence / blocked / needs_steward), instruction, evidence requirement, next-check trigger and brief rationale.
- Keep message body short; link to evidence. Never preload full repo manuals, all logs or all history.

## Task grading and teaching
On completion or terminal failure, record an **A–F letter grade and 0–100%** with rubric version, objective outcome, and evidence. Proposed weights: correctness/completion 35; independent execution 20; recovery 15; efficiency/iterations 15; escalation/evidence 10; application of lessons 5. A task that failed must visibly remain failed; do not hide that with a high process score. Store each meaningful execution attempt, escalation count, time to recovery, ChatGPT guidance, Grace action and verification. Provide feedback to both Grace and Steward. Track independent completion, average iterations, repeated failures, grade trends and runbook reuse.

## Runbook lifecycle
Capture successful *verified* task path, failed approaches and known pitfalls. Draft a candidate runbook with prerequisites, authority, steps, checkpoints, failure recovery and provenance. Promote only after review or repeated successful application; version and supersede, never silently rewrite historical lessons. Grace retrieves matching runbooks before starting similar work. Feedback may improve prompts/procedures but is not model weight training.

## Website and persistence
Add a dedicated Riverview **Grace / Performance & Learning** page: Active Work, Task History (expandable timeline), Evaluations, Runbooks. Show original objective and approvals, attempt/iteration count, escalation messages and dispositions, ChatGPT comments, Grace responses, result artifacts, percent/letter grade and historical trends. Store append-only events keyed by existing objective/work-order/request IDs; add only missing evaluation/runbook relations. Respect sensitive-data redaction and access controls.

## Definition of done for P0
After approved restart/reboot and with no keyboard/mouse intervention, dedicated browser restores correct authenticated conversation (or clearly flags expired login); one real request completes mailbox→wake→ChatGPT→correlated response→Grace consumption. No synthetic-only pass is sufficient. Capture reproducible evidence. Do not block P0 on grading/dashboard/runbook implementation.

## Decision and scope control
This document is the proposal and continuity anchor, not authorization to deploy, alter production, log in on behalf of Steward, or ring ChatGPT. Maintain a separate tiny operational reground file; revise it only when a real omission is demonstrated. Keep implementation incremental and fast; one responsible integration owner and one real acceptance test.
