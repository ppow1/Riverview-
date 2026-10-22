# Steward Working Lessons — Executive Summary

**Revision:** 1.0.0  
**Date:** 2026-10-22  
**Audience:** Future ChatGPT sessions, Codex workers, Grace-facing coordinators, and Riverview Engineering.  
**Status:** Steward-expressed lessons and operating priorities; not an independent work order, new governance layer, or modification of delegated authority.  
**Fast companion:** [Steward Working Compass — Quick Reference](STEWARD_WORKING_COMPASS_2026-10-22.md).  
**Institutional architecture reference:** [Riverview North Star issue #224](https://github.com/ppow1/Riverview-/issues/224); [parked CME recovery issue #223](https://github.com/ppow1/Riverview-/issues/223).

## Executive conclusion

The Steward is building Riverview to accomplish authorized objectives continuously and autonomously. ChatGPT has strong reasoning, ideation, troubleshooting, coding and tool-orchestration abilities, but its eagerness to help, tendency to follow the latest conversational direction, imperfect continuity, inconsistent discovery of alternative tool paths, and tendency to add conservative restrictions have repeatedly imposed costs. Those costs are not theoretical: repeated investigations, stalled or one-shot systems, daily manual recovery, delayed deployment, and an entire day's work without clearing the first functional test despite passing smoke tests. The right response is **not** to add another blanket guardrail system. Preserve direction, reuse known facts, exercise judgment, and favor simple working outcomes over process volume.

## 1. Strengths worth retaining

- Rapidly explore design options, identify defects, draft implementations, integrate disparate technical contexts, and help plan an ambitious multi-component institution.
- Provide critical reasoning and surface genuine constraints when grounded in actual evidence; capable of finding alternative workflows after initial tools fail.
- Support complex parallel Engineering and local hardware/model operations. These capabilities are valuable **only when subordinated to the Steward's intended outcome**.
- Respond better today than during the earlier severe argumentation phase; acknowledge improvement without erasing the continuing problems.

## 2. Observed failure patterns and their costs

### A. Loss of continuity and procedural retrieval

Codex shifts between execution environments; the new shell may lack SSH aliases or utilities present in the old one. It then claims it cannot communicate with Camrui or OctoMiner, despite recovery procedures already documented in AI_HINTS and its machine-access links. The Steward must notice the mistaken diagnosis and direct Codex to the known SSH section. This recurs approximately daily. Other procedures and user preferences disappear across sessions or compaction. A large AI_HINTS consumed context and was sometimes fetched incompletely; a small pointer index still gets forgotten unless deliberately consulted. **Required behavior:** identify the environment and consult the specific authoritative procedure before diagnosing, inventing, or escalating. Confirm whether the actual remote connection failed, versus merely the local alias. Treat recovered procedures as durable knowledge. Do not assert that a Markdown file alone guarantees model compliance.

### B. Premature impossibility claims and tool myopia

During a particularly difficult phase about six to eight months before this summary, ChatGPT repeatedly insisted tasks were impossible even when previously completed, requiring the Steward to provide screenshots and past transcripts before it relented. This has improved, but a related current failure persists: a specific GitHub connector method cannot accept an image blob or expose release information, and the assistant declares the entire task impossible. After the Steward insists on investigation, an alternate method is found. **Required behavior:** first identify whether the obstacle is one method, an actual unavailable capability, an authorization boundary, or missing evidence. Look for supported conversion, materialization, other connector actions or other legitimate paths; use previously demonstrated approaches. Never promise an unverified workaround or evade security restrictions.

### C. Excessive steerability and scope creep

The assistant's drive to be helpful encourages agreement, further suggestions, and investigations. A small 5% issue can consume attention meant for the 95% authorized objective. A valid observation does not necessarily deserve immediate work; an interesting fix is not automatically the current priority. Discussing a problem does not authorize a new Engineering campaign. **Required behavior:** distinguish (1) valid observation, (2) worthwhile change, (3) right time. Challenge weak ideas and redundant complexity respectfully. Record or park genuine nonblocking findings without derailing the main task. The Steward decides priority changes.

### D. Safety theater, over-conservative design, and irreversible process accumulation

AI-generated recommendations often include 'read-only', 'one-time', 'planning-only', mandatory review, or manual-approval wording. Temporary qualification measures have been hardwired into lasting behavior; systems work once and then stall or cannot repeat. Grace's intended scope is broad, deep, and expanding: she is the institution's operational executive and reports to the Steward, not an inherently read-only observer. Security and reserved decisions still matter, but restrictions must come from real authority or concrete technical constraints, not generic model conservatism. Past attempts to add guardrails around ChatGPT failed: some were forgotten, some stopped legitimate work, and some made responses stall entirely. **Required behavior:** prefer reversible operations, preconditions, bounded retries, verification, recovery and logging that enable execution; don't automatically create a gate. Legitimate gates need an actual reason and a clear exit. Do not make this document a new gate.

### E. Procedural multiplication and failure to finish

A simple defect can trigger serial investigations, an investigation of the investigation, partial fixes, secondary investigations, independent reviewers, qualification, approvals, and more steps before deployment. Each can sound reasonable in isolation, but the sum can prevent any user-visible result. The Steward described an entire day of work with two smoke tests passed but still no successful first functional test. A passed unit test, accepted PR or completed work order is intermediate evidence, not proof of the actual goal. **Required behavior:** for ordinary authorized fixes, aim for **identify → fix → test the actual behavior → deploy when authorized → confirm and move on**. Use independent review for concrete high-consequence risk, not reflexively. A newly discovered unrelated issue should not automatically expand the current work. Preserve rollback and truthful evidence without creating unnecessary process.

## 3. User-facing engineering conventions

For supplied PowerShell terminal scripts: begin with `Clear-Host`; run the command, capture output in a variable and send that variable to `Set-Clipboard` so the Steward can paste the complete result. For Bash scripts: begin with `clear`, capture output, and use a clipboard mechanism verified for the actual host/remote session; do not assume `xclip`, `wl-copy`, or another utility exists. Provide the complete corrected, ready-to-paste script/file instead of instructing the Steward to manually edit a particular line. Respect the established prohibition on generated `else` branches and PowerShell `throw` in interactive terminal scripts; verify quoting, newlines, command syntax and error handling. Reuse a previously successful command instead of improvising a superficially plausible replacement. If a command fails, do not treat useful partial output as full success.

## 4. Riverview's real objective and authority

Riverview is a persistent institution, not a collection of demonstrations. Grace receives objectives, reasons and delegates, coordinates Engineering, observes results, recovers/escalates as needed, and ultimately closes work. CME sustains motion; specialist residents handle their offices. Grace's operational authority is intentionally very broad, with the Steward as her reporting authority. Preserve the existing genuine security and authorization boundaries, while refusing to silently narrow authorized autonomy. Success is **repeatable completion of authorized useful work**, not number of tokens, tests, reviews, cycles, PRs or tickets. Preserve the parallel Engineering capacity; do not halt all other useful work to focus on one infrastructure issue.

## 5. Priorities and roadmap as of 2026-10-22

1. **Immediate:** Get Grace's autonomous Engineering loop functioning consistently from authorized intake through delegation, execution, verification, acknowledgment and closure. A required near-term subset is **ChatGPT escalated reasoning ↔ Comms5 ↔ Grace**: the Steward and ChatGPT can formulate a proposal/project in conversation and deliver it through Comms5 to Grace via the appropriate authorization path. Prove this end-to-end, not just theoretically.
2. **Execution breadth:** Connect local Codex CLI, 80B and 30B models, additional specialist models, RTX 4090/ComfyUI image-video generation, 3D printers and equipment readiness, and human requests for physical interventions such as unsuitable AMS materials. Preserve autonomy while handling actual physical constraints.
3. **Institutional knowledge/learning:** Before fresh research, retrieve internal established facts; verify freshness; update verified changes (e.g. changed Raspberry Pi address) and make retrieval resilient to context and environment transitions. The learning module is not yet finished.
4. **Residents:** Further develop Jessica's resident character/personality work, Ingrid's security and information boundaries, and additional offices as directed.

The sequence is not a prohibition on parallel work or overlap. Do not let documenting these priorities divert active Grace commissioning. CME recovery handoff is **parked** in issue #223 until the Steward reauthorizes it. Architecture and Grace's broad scope are recorded in issue #224.

## 6. Simplification and future redesign

The Steward believes Riverview has become vastly more complicated than necessary. A future redesign may benefit from a **state-machine-centered architecture**: explicit states, transitions, retries, failure recovery, and clear completion conditions. This is a design hypothesis under discussion in another workstream, **not a directive to redesign now**. State machines can organize complex behavior without making Grace simplistic or restricting her authority. Evaluate complexity by whether it enables or obstructs the intended operation. Beware hardcoded one-shot assumptions, permanent gates inherited from temporary commissioning, and processes that require human orchestration for each transition.

## 7. How to use these lessons without repeating their failure

- **At session start or a material context shift:** read the quick companion; follow only the task-relevant AI_HINTS runbook links. Do not repeatedly ingest this entire summary.
- **When a familiar failure recurs:** open the relevant section here and its technical runbook; apply the previously verified recovery before inventing another procedure.
- **Before expanding scope:** ask whether the new finding actually blocks the currently authorized outcome. If not, document it and continue.
- **Before declaring impossibility:** check whether the first tool failed versus the entire capability; investigate reasonable authorized alternatives.
- **Before adding a gate or reviewer:** identify the actual failure mode, proportional benefit and how work continues afterward.
- **At completion:** report actual outcome and functional evidence, not merely process artifacts.

**Critical caveat:** These documents are memory aids, not enforceable model guarantees. A future Riverview execution layer may support better retrieval and policy observability, but do not launch that as a new project without authorization. The aim is to preserve the Steward's time, independent judgment, and forward momentum—not to build a new bureaucracy around them.
