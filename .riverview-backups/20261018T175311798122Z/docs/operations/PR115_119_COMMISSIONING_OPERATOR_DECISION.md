<!--
Riverview Controlled Document
File: docs/operations/PR115_119_COMMISSIONING_OPERATOR_DECISION.md
Component: GRACE-COMMISSIONING
File Revision: 1.0.0
Task: RV-C4-PR115-119-READINESS-001
Purpose: Record the read-only commissioning preflight and operator decision gates for PRs #115/#119
Changed: 2026-10-18 UTC | RV-C4-PR115-119-READINESS-001 | Reconcile current PR/CI/package evidence with the recorded commissioning blockers
Authority: Read-only review; production activation requires a separately authorized change
History: New file; no predecessor existed
-->

# PR #115/#119 commissioning operator decision

**Preflight observed:** 2026-10-18 12:05 EDT.
**Decision:** **NO-GO — commissioning remains blocked at readiness milestone 1/5.**
**Candidate:** PR #119 `97128626df967bc992696dca38eaa7116f3616e9`, stacked on PR #115 `94592f26ad9af35b8cf609fce39e786c8c3f6e19`.
**Scope:** Read-only provenance, evidence, and operator gates. This document grants no approval to merge, migrate, configure, restart, deploy, or execute Engineering work.

## Candidate provenance and current CI

The live GitHub review state was checked for PRs #109–#115 and #119 on 2026-10-18. Each was OPEN and MERGEABLE, with its controlled-checkout check successful.

| PR | Candidate role | Current head | Base |
|---|---|---|---|
| #109 | Comms5 completion and durable external reasoning | `9a42634ac0e97e3de2cc57b64743581bc617f025` | `codex/grace-conversation-ui-refinement` |
| #110 | Grace external-reasoning initiation, based on #109 | `9960aec3342a7d8dc1588086cb3a95ba44e1baa4` | #109 branch |
| #111 | Bounded deferred-reasoning recovery | `ce451684c5154fe395b55d07c6d262e223f8f6f9` | `codex/grace-conversation-ui-refinement` |
| #112 | Concurrent artifact/source-change execution | `f58508dfc8745d4c658047a4ee08a2a721247c7f` | `codex/grace-conversation-ui-refinement` |
| #113 | Four-PR integrated candidate | `6e18ff8fd1ea19b19ff769b559bd74e7411cd4bf` | `codex/grace-conversation-ui-refinement` |
| #114 | Local reasoning response corrections | `cda5581361eccf79d88c67494d76a62b6cc52978` | `codex/grace-conversation-ui-refinement` |
| #115 | Integrated reasoning candidate retaining #113 contracts and selected #114 fixes | `94592f26ad9af35b8cf609fce39e786c8c3f6e19` | #113 branch |
| #119 | Restricted-role ACL correction for migration 0013 | `97128626df967bc992696dca38eaa7116f3616e9` | #115 branch |

Fetched-head ancestry was verified in the isolated worktree: the current heads of #109, #110, #111 and #112 are ancestors of #113; #113 is an ancestor of #115; #115 is an ancestor of #119. The current #114 head is **not** an ancestor of #115; #115 carries only the reviewed provider-response corrections, as intended, while retaining #113's contracts. PRs #109–#114 are dependency/source evidence; #115 is the review candidate and #119 adds the ACL fix on top. Their passing checks establish source-candidate CI only. The most recent relevant controlled-checkout runs are [#115 run 39132606066](https://github.com/ppow1/Riverview-/actions/runs/39132606066) and [#119 run 39136300985](https://github.com/ppow1/Riverview-/actions/runs/39136300985). No merge has occurred.

## Verified technical evidence

| Gate | Evidence | Decision |
|---|---|---|
| Migration order and compatibility | The integrated application ledger uses shared migrations `0012_resource_selection_policy` then `0013_bounded_deferred_retries`. A disposable restore of the preserved production snapshot applied both in order and reapplied them idempotently; 33 existing `riverview_dev` table counts were unchanged and the ledger advanced 22 to 24. A fresh private PostgreSQL rehearsal applied the complete migration directories from the extracted #119 package in order (core 2, scheduler 1, worker 6, authority 10, resident execution 13); 0012 preceded 0013, and reapplying each directory returned no new migrations. The disposable schema was dropped. | PASS in isolated restores/rehearsal; recheck against a fresh protected snapshot before any deployment. |
| Restricted runtime ACL | Under the actual `riverview_core` role in both the recorded test and the new package-migration rehearsal, retry-state reads, inserts/upserts, and bounded updates passed. Updates to `request_id`, DELETE, and TRUNCATE were denied. Test data and schema were rolled back/dropped. | PASS in isolation; no production grant was changed. |
| Regression and integration tests | Recorded full isolated suite: 624 passed, 0 failed, 0 errors, 0 skipped. The C4 follow-up ran Grace execution, worker adapter, assignment intake, and assignment scheduler modules: 57 passed, 0 failed, 0 errors, 0 skipped against private disposable PostgreSQL 16. This rehearsal reran migration 0013 restricted ACL, approved objective through independent verification/closure, and independent verifier gating, plus the loopback dashboard → authorized proposal → reconstructed Grace service → worker → verifier → closure flow: 4 passed, 0 failed, 0 skipped. Evidence: [issue #120 C4 test report](https://github.com/ppow1/Riverview-/issues/120#issuecomment-6251767330) and [service-level rehearsal](https://github.com/ppow1/Riverview-/issues/120#issuecomment-6252173237). | PASS; synthetic fixture identities/grants only; no live worker or external ChatGPT provider was invoked. |
| Process graphs and revisions | The preceding candidate review recorded 22 graphs / 565 nodes and revision/predecessor checks PASS. This preflight reran graph validation: 22 graphs / 565 nodes PASS and the controlled revision/predecessor check returned no issues. | PASS for the reviewed candidate; this document's updated revision check is included in this PR's CI. |
| Rollback | An isolated atomic code-pointer rollback rehearsal passed for dashboard, Grace execution, and Comms5 roots. This C4 rehearsal extracted the hash-verified #119 archive into a disposable release tree and atomically switched a synthetic `current` pointer from predecessor to candidate and back; the predecessor pointer was restored. No systemd unit was started for the pointer test. A separate loopback integration service was started for the lifecycle test and shut down cleanly. Code rollback must retain additive 0012/0013 schema, grants, ledger rows, and data; no destructive downgrade is approved. | PARTIAL: package pointer behavior rehearsed; production snapshot and service-specific stop/restart rollback preconditions must be freshly verified before commissioning. |
| Deployment package | Existing package `/tmp/riverview-pr115-acl-fix-97128626.tar.gz` is bound to source commit `97128626df967bc992696dca38eaa7116f3616e9`. Its current SHA-256 is `8a3c4f50f4331bfc298d1e15a2bd188462c9f5b85065afbee37f993b38a96fc7`; `verify_camrui_package.py` returned manifest PASS and shell-compatibility PASS. The package is not installed. | PASS for artifact identity/integrity; not an installation or runtime acceptance. |
| Local 80B | Prior readiness evidence recorded HTTP 200 and the expected Qwen3-Next-80B model. This preflight did not make a new live endpoint request. | Previously observed; recheck availability and configuration in a separately authorized deployment window. |

Detailed prior evidence and caveats are in the C4 readiness report on [issue #120](https://github.com/ppow1/Riverview-/issues/120#issuecomment-6251639180). No production service, database, credential, grant, or OctoMiner configuration was accessed or changed for this preflight.

## Missing external provider identity and credentials

External ChatGPT advisory reasoning is a separate durable MCP exchange. It remains advisory and cannot authorize or promote an Engineering proposal. These required production values remain unestablished in the recorded audit:

- Steward-approved external provider ID and OAuth issuer-to-provider identity mapping.
- Verified OAuth subject and client ID mapping to the provider, with approved scopes.
- Protected provider credential and approved route/resource configuration: `RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP`, `RIVERVIEW_MCP_RESOURCE_URL`, `RIVERVIEW_MCP_AUTHORIZATION_SERVER_URL`, `RIVERVIEW_MCP_ALLOWED_HOSTS`, and `RIVERVIEW_MCP_ALLOWED_ORIGINS`.
- Exact `resident.reasoning.escalate` grant scoped to `provider:<approved-provider-id>`.

Do not guess these values from an OAuth client label, ChatGPT account name, prior registration, or a reachable endpoint. Keep the MCP provider inactive until identity, audience/resource, routing, credential custody, and the exact grant are jointly verified.

## Worker authorization and Steward decisions

- The artifact-only executor and distinct verifier have recorded exact registrations/grants for their existing bounded artifact path. Their presence does not approve an objective or service activation.
- The source-change worker still lacks a verified institutional principal, its exact `worker.register` and `assignment.execute` grants on `work-order:engineering`, and a protected credential bound to the registered worker identity. Do not use the artifact worker for source changes or infer authority from a service template.
- The prepared harmless artifact-only objective remains `AWAITING_STEWARD_APPROVAL` in the C4 monitoring record. No execution is authorized by its preparation or by this document.
- Steward review is required for PRs #115/#119. Separate explicit decisions are required for provider identity/configuration/grant, approval of the exact objective, and any production deployment, migration, or service change. A source-changing acceptance additionally needs the source-worker identity and exact grants/credential.

## Operator decision record

| Decision | Current state | Required evidence before proceeding |
|---|---|---|
| Accept PR #115/#119 candidate | WAITING | Steward review; verify current heads, required checks, and dependency order at decision time. |
| Bind ChatGPT MCP provider | BLOCKED | Provider ID, issuer, OAuth subject/client mapping, route/resource/audience, scopes, protected credential procedure, and provider-scoped escalation grant approved and verified. |
| Authorize an artifact-only objective | WAITING | Steward approval of the exact pinned repository, allowed artifact path, acceptance criteria, executor, verifier, and cleanup in the prepared objective. |
| Authorize source-changing work | BLOCKED | Separate source worker principal, identity-bound protected credential, exact `worker.register` / `assignment.execute` grants and objective scope approved. |
| Authorize deployment/migrations/services | NOT GRANTED | Separate production change authorization; fresh protected backup plus successful disposable restore; current migration/checksum and service/configuration preflight; verified rollback decision and maintenance window. |

## Isolated checks available without production authority

The isolated suites may continue using disposable PostgreSQL databases, local repository fixtures, and synthetic fixture credentials/grants. Package manifest verification, source/graph/revision checks, and rollback rehearsal in a disposable release tree are also safe. Such results do not count as live provider acceptance, production grant verification, deployment, or Engineering execution.

## Exact activation boundary

Until every applicable gate above has fresh evidence and the required separate approval is recorded: do not merge either PR; install the package; apply migrations 0012 or 0013; alter production configuration, credentials, grants, or OctoMiner settings; activate the external provider; restart or start services/workers; or submit/execute an Engineering objective. If a future approved attempt applies the additive migrations, rollback the code pointer only when predecessor compatibility is established and retain all additive schema and durable records. On any failed or uncertain gate, stop before the next activation step and preserve sanitized evidence.

**Current operator decision: NO-GO.** Verified isolated technical prerequisites do not resolve the external provider, exact authorization, Steward approval, or fresh deployment-boundary checks. The milestone remains **1/5** and capability remains **NOT COMMISSIONED**.
