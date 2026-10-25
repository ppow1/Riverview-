# Riverview S1–S5 Process Definition and Acceptance Standard
**Published:** October 25, 2026  
**Scope:** Completed controlled five-step Grace qualification objective  
**Status:** Documentation reconstruction from the recorded qualification and integration reports; **not a recovered copy of the previously reported uncommitted document**.

> **Important:** S1–S5 are objective-local test step IDs, **not** five universal Riverview process phases. The reusable architecture is dependency-ordered objective execution with persisted criteria, authorization, Engineering execution, independent verification, recovery, and durable completion. Universal S1–S5 phase definitions are **UNDEFINED**.

## 1. Purpose and qualification boundary
The October 25, 2026 controlled qualification tested whether Grace could carry one objective through bounded work-order creation, local reasoning, escalated Luna reasoning, consumption of the returned response, and verified final outcome. It tested execution infrastructure, **not** delivery of an external CueMastery or other business artifact. An objective step passes only against **its own persisted acceptance criteria and artifact requirements**, with durable independent `ACCEPTED` verification. A step label or workflow advance is not sufficient proof.

## 2. The five objective-local steps

| Step | Tested capability | Process-level evidence required to assert PASS |
| --- | --- | --- |
| **S1 — Bounded work-order creation** | Create bounded authorized Engineering work through the established assignment/work-order mechanism. | Persisted S1 objective and work-order/assignment evidence satisfying S1's stored criteria, plus independent durable `ACCEPTED` verification. |
| **S2 — Local reasoning** | Execute the local reasoning path as part of the objective. | Persisted local reasoning/output evidence meeting S2's stored criteria, plus independent durable `ACCEPTED` verification. |
| **S3 — Luna escalation** | Invoke the escalated reasoning path with durable authorization/exchange handling. | Persisted escalation and exchange evidence meeting S3's stored criteria, plus independent durable `ACCEPTED` verification. |
| **S4 — Response consumption** | Consume the returned reasoning response and record the resulting workflow progress. | Persisted response-consumption evidence meeting S4's stored criteria, plus independent durable `ACCEPTED` verification. |
| **S5 — Outcome verification and completion** | Produce a grounded outcome record, verify it independently, and complete the objective when all required steps are accepted. | S5 persisted trigger/evidence, required final-outcome artifact, independent durable `ACCEPTED` verification, followed by durable objective `COMPLETED` state. |

**Limit of this published reconstruction:** The original detailed process document was reported created in another Codex window but was not accessible on the repository default branch. Consequently, the exact stored per-step selectors, field-level predicates, artifact schemas, and source line references for S1–S4 are **NOT REPRODUCED OR CLAIMED** here. They must be extracted from the live objective's immutable records or recovered original document before this can be considered a field-exact acceptance specification.

## 3. Shared process rules, independent of any step ID
1. **Entry:** A step's prerequisites/dependencies and applicable authorization must be satisfied. The step's actual persisted criteria, not a generic template, define its contract.
2. **Execution:** Grace coordinates permitted work through the established execution components; artifacts, attempts, reasoning exchanges, and state transitions are persisted.
3. **Verification:** An independent verifier evaluates the produced evidence against the step's persisted criteria. `ACCEPTED` is the only qualifying successful verification; `REJECTED`, missing evidence, or merely advancing a projection is not a pass.
4. **Failure/recovery:** Preserve failed attempts, rejected verifications, retry limits, and causality. Retry or resume only through permitted durable workflow mechanisms; do not rewrite history or manufacture acceptance.
5. **Exit:** A step can be reported verified only with a corresponding durable accepted verification. The objective is completed only when the required objective-level completion conditions are satisfied and its terminal event is persisted.
6. **Separation of concerns:** Process-level acceptance means the defined execution/evidence contract passed. It does not necessarily mean an underlying external business goal succeeded. A truthful diagnostic outcome may be accepted as a diagnostic test result.

## 4. Specific S5 requirements and observed recovery
The reported S5 requirements included: consuming escalated reasoning evaluation, demonstrating an observable transition or precise durable failure reason, producing CLI-accessible evidence for objective/authorization/reasoning/exchange/consumption/outcome, and generating a JSON `final_outcome_log` referencing earlier artifacts without exposing secrets. S5's persisted acceptance also included `artifact_semantic_outcome_not_negative`.

The first S5 verification was **REJECTED**. Recovery failed because the evidence reader recognized S4 escalation events but not S5's valid `resident.reasoning.cme_recovery_evaluated` trigger; the retry guard also disqualified a pre-execution rejected artifact. A narrow correction (`4eb3fb9ed2ca661ba8ef048b8fc82770f480d38a`) allowed a bounded retry of the existing assignment. A subsequent Engineering attempt produced an artifact independently **ACCEPTED**, without erasing the earlier rejection.

## 5. Completed objective mapping
- Objective: `objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2`.
- Terminal state: **COMPLETED**, revision **13**.
- All five steps reported independently accepted.
- S5 accepted verification: `40990485-d50a-4ad9-adcb-ebd086c31a9f`.
- S5 verified event: **309175**; objective completed event: **309176**.
- Accepted S5 artifact SHA-256: `15f0ba34720640ab8060a5a9dea2c29d3ffbb68375cac258c46a8646d1520a6f`.
- Protected history: **367 events** (sequences 308630–309187), reported unchanged after integration.
- Snapshot: `/var/lib/riverview/deployments/grace-s1-s5-success-20261025-4eb3fb9e`.
- Integration: [PR #306](https://github.com/ppow1/Riverview-/pull/306), merged `edffbda00e8d24423a0a265c2831f24ae23269de`, reported deployed to Grace and Dashboard.

## 6. What is reusable versus objective-specific
**Reusable process:** objective declaration and dependency ordering; persisted authorization and assignments; execution and reasoning exchanges; durable artifact capture; independent verification; bounded recovery; terminal completion.

**Objective-specific:** step IDs (S1–S5), their meanings, artifact requirements, acceptance selectors, dependencies, and test-specific outcome contracts. Do not hardcode these names into general lifecycle dashboards or require five steps for future objectives.

**Recommended reporting:** use universal lifecycle states for system-wide reporting, and show objective-local step names/criteria within the objective detail view. Do not change runtime behavior merely to rename the successful historical test.

## 7. Publication and evidence limitations
This document was published to close the missing-file gap on `main`. It is a **faithful summary of the available recorded reports**, not a claim to have retrieved the exact original detailed Codex draft. The detailed per-step criteria should be appended only after reading the original artifact or authoritative persisted objective records. No production, objective state, acceptance criteria, or verification history was modified by publishing this file.

Related: [Phase Completion Executive Summary](../progress/RIVERVIEW_PHASE_COMPLETION_EXECUTIVE_SUMMARY_2026-10-25.md).
