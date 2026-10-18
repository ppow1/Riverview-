<!--
Riverview Controlled Document
File: docs/operations/PR115_119_COMMISSIONING_OPERATOR_DECISION.md
Component: GRACE-COMMISSIONING
File Revision: 1.0.2
Task: RV-C4-PR115-119-READINESS-001
Purpose: Record the read-only commissioning preflight and operator decision gates for PRs #115/#119
Changed: 2026-10-18 UTC | RV-C4-PR115-119-READINESS-001 | Reconcile current PR/CI/package evidence with the recorded commissioning blockers
Changed: 2026-10-18 UTC | RV-C4-PR115-119-READINESS-001-REMEDIATION | Add prospective file-control correction, structured blocker register, OAuth route comparison, and durable isolated evidence references
Changed: 2026-10-18 UTC | RV-C4-PROVIDER-COMMISSIONING-DOSSIER-001 | Distinguish Comms5 ingress and external MCP OAuth identity/configuration; record decision options
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

## Standards and historical file-control exception

The authority set used for this record is the requested current main baseline at
commit f6558554a1d360aebdb24036d3a8b7781e7e92b5: AI_HINTS 1.0.4, active
Component Definition of Done Rev 1.6, Development Lifecycle 1.0.0 (proposed),
Engineering Records 1.0.0 (proposed), Codex Campaign 1.0.1, and Process Graph
README 1.0.1. The #119-based feature checkout carries AI_HINTS 1.0.5 and DoD
1.7. Those branch-local copies are newer but are not accepted main authority;
they were not overwritten. This record follows main Rev 1.6 as directed.

The first PR #126 versions of this operator document and its revision record
were added as 1.0.0 in commit c3ebe6138ccd08174fcd6676552ffb6f6b8345d1.
Both contents then changed in commits 8590e441ce40c4ad7cf8bcf6211c070527745c1e,
52a6c0152e6460bd877525819121e12f30164612, and
e38368e4acba0e24820f3ba64e5ec0d69f683a94 without revision increments or
pre-change backup-manifest records. The prior Git blobs remain retrievable;
that does not satisfy the requirement for an independently recorded backup
before those changes. No retroactive backups are claimed. For this prospective
correction, the exact immediate predecessors were copied and readback-verified
before editing, with hashes, revision transitions, source commit and restore
instructions in .riverview-backups/manifest.jsonl. This correction increments
each document from its declared 1.0.0 to 1.0.1. Earlier omissions remain a
historical compliance exception.

PR #119 also has retrievable predecessor copies for migration 0013 and
RESIDENT_CONVERSATION.md. Their original manifest records omitted the new
revision, source commit and restoration instructions. A separately timestamped
metadata-correction record now supplies those facts from the preserved backup
files and commit. It explicitly records that this metadata was completed
prospectively, not at the original change time.

## Comms5 route and external-reasoning OAuth trace

The current source and deployment contracts were compared read-only:

| Boundary | Comms5 authenticated inbound route | External reasoning provider exchange |
|---|---|---|
| Public/resource path | Caddy on Ionoge accepts `/comms5/mcp`; the documented path crosses the dedicated reverse SSH forward to the Camrui adapter at `127.0.0.1:11826/mcp`. | The external-reasoning MCP adapter serves `/mcp`; its Camrui unit defaults to `127.0.0.1:11827`, with public HTTPS routing left to a separately reviewed proxy. |
| OAuth role | The Ionoge Comms5 OAuth service advertises issuer `https://riverview-comms.ionoge.com` and configured resource/audience `https://riverview-comms.ionoge.com/comms5/mcp`. Caddy forward-auth verifies the caller and forwards the Comms5 principal; a separate protected upstream token authenticates the proxy-to-Camrui hop. | The adapter is an OAuth resource server, not an issuer. `RIVERVIEW_MCP_AUTHORIZATION_SERVER_URL` selects issuer metadata and `RIVERVIEW_MCP_RESOURCE_URL` is the exact expected token audience and advertised protected resource. It validates issuer, audience, expiry, scope, subject and client ID, then maps the exact subject/client pair through the protected systemd `provider-auth-map` to a fixed provider and exchange principal. |
| Identity and authority | Successful Comms5 forwarding supplies the Comms5 `steward` principal for Comms5 tools. Its legacy bearer, OAuth login credential, proxy trust key, and backend-hop token have distinct roles and are not an external-provider identity mapping. | OAuth subject/client IDs map to an external `provider_id` and exchange `principal_id` in the protected adapter credential. Grace separately loads `RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP` as non-secret JSON mapping the same provider ID to its exchange principal; the launcher cross-checks those identities. Neither map grants authority. The active Grace resident still needs the exact `resident.reasoning.escalate` grant scoped to `provider:<provider_id>`. Advice cannot approve a proposal or authorize execution. |
| Listener boundary | Comms5 OAuth unit defaults to loopback `127.0.0.1:11827` on its documented Ionoge host. | The external reasoning unit defaults to `127.0.0.1:11827` on Camrui. This is a bind collision only if the two units share a host/network namespace. The documented intended topology places them on separate hosts, but this assignment made no live topology inspection; verify host identity before activation. If co-located, select and configure distinct loopback ports and proxy routes. |

**Reuse result: NOT VERIFIED.** The Comms5 issuer and OAuth implementation are
candidate infrastructure only. The currently configured Comms5 audience is
`https://riverview-comms.ionoge.com/comms5/mcp`; the external adapter requires
an exact separately chosen MCP resource audience. The Comms5 `steward` principal
and its legacy/upstream proxy credentials are not the provider principal or
provider-map credential. The checked-in external adapter validates issuer,
audience and exact subject/client/scope, but the historical Comms5 OAuth server
implementation is not present in this source tree; its deployed unit exposes one
configured resource value. It is therefore **not verified** that the current
Comms5 issuer can issue a second resource audience or register a separate
ChatGPT MCP client. Reuse requires code/configuration evidence for both. Do not
reuse the Comms5 route, principal, or credentials as-is.

Still missing for ChatGPT: Steward-approved provider ID; issuer URL and issuer
metadata; exact OAuth subject and client ID mapping; exact audience/resource
URL; routable HTTPS endpoint and host/origin allowlist; token scopes and
credential custody/renewal procedure; provider-auth-map credential; separate
Grace provider identity reference; and the exact resident.reasoning.escalate
grant scoped to provider:<approved-provider-id>. No value was guessed, read
from a live secret store, or activated.

### Verified separation options and minimum configuration decisions

**Code-level contract:** the external adapter has independent resource-server settings: `RIVERVIEW_MCP_RESOURCE_URL`, `RIVERVIEW_MCP_AUTHORIZATION_SERVER_URL`, `RIVERVIEW_MCP_ALLOWED_HOSTS`, and `RIVERVIEW_MCP_ALLOWED_ORIGINS`; its listener uses `RIVERVIEW_MCP_LISTEN_HOST` / `RIVERVIEW_MCP_LISTEN_PORT` (defaults loopback `127.0.0.1:11827`). The checked-in example values are placeholders. The systemd unit delivers `provider-auth-map.json` using `LoadCredential`; the launcher requires the credential directory and protected file owner/mode, validates issuer metadata/JWKS, exact resource audience, subject, client ID and scope, and cross-checks provider/principal IDs against Grace's separate provider registry. The registered scopes are `reasoning:exchange` and `reasoning:exchange:confidential`; the latter is needed only for confidential exchange. The authorization server must provide HTTPS metadata, authorization code + PKCE S256, and a supported public-client registration method (CIMD or DCR). The repository contains no external public Caddy route or concrete provider values.

| Choice | Verified contract / constraint | Minimum Steward/owner decision |
|---|---|---|
| A. Dedicated external issuer/client registration (separate identity boundary) | Supported by the adapter's independent issuer/resource configuration, subject/client allowlist, and provider map. No issuer, endpoint, or client is preselected. | Approve issuer and metadata URL; ChatGPT MCP client registration method and exact client ID; exact token subjects; provider ID and distinct provider exchange principal; required scope ceiling; credential custody/rotation owner. |
| B. Reuse the Comms5 authorization service with a distinct MCP resource (conditional) | Comms5 currently advertises one configured resource `.../comms5/mcp`; its OAuth implementation source is external to this checkout. It must be proven to issue a token whose `aud` is the separately approved external `RIVERVIEW_MCP_RESOURCE_URL`, for the intended ChatGPT client and scope. The Comms5 `steward` principal cannot stand in for the provider principal. | Provide source/version evidence and a nonproduction issuer test proving discovery, PKCE/client registration, exact external audience, subject/client claims and scopes; approve a separate provider map and exact Grace registry match. If the issuer cannot satisfy these checks, select option A. |
| C. Listener and public route | Both units default to loopback `127.0.0.1:11827`; documented Comms5 OAuth is on Ionoge and external MCP is packaged for Camrui, so the collision is conditional on co-location. The external unit has configurable host/port; public TLS proxy config is not checked in. | Verify deployment host/network namespace. If co-located, select distinct loopback ports and a reviewed proxy route. Select an approved HTTPS host/path, DNS/TLS owner, Host/Origin allowlists, and ensure RFC 9728 `resource` and token `aud` equal the exact resource URL. |
| D. Identity and authority binding | External adapter credential maps exact JWT subject + client ID + scopes to `(provider_id, principal_id)`; Grace's `RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP` independently maps that same pair. Durable request admission/consumption additionally checks the active resident's `resident.reasoning.escalate` grant on `provider:<provider_id>`. | Approve the same exact provider/principal pair across both maps; approve the separate provider-scoped resident grant through the authorized process. Never map to the Comms5 Steward identity. |

The shortest safe technical path is: choose A or prove B; decide C after topology verification; define the exact URL/issuer/client/scope and paired identity mapping; validate those values in disposable fixtures; then request the distinct grant and provider credential through their owners. None of these steps activates a provider. Missing live identity, secret, grant, or Steward decision keeps commissioning blocked.

### Exact Steward decision list

1. Select dedicated issuer/client registration (A) or require evidence that Comms5 supports a separate external MCP audience and client (B).
2. Approve the external MCP HTTPS resource URL, issuer URL, ChatGPT OAuth client-registration method, exact client ID/subject mapping, and allowed `reasoning:exchange` scope set.
3. Approve a unique external `provider_id` and exchange `principal_id`, the protected `provider-auth-map` owner and renewal process, and the matching non-secret Grace provider-map entry. No value is currently known.
4. Have operations verify whether the two listener units share a host/network namespace; if they do, approve distinct loopback ports and the corresponding TLS proxy route/Host/Origin allowlists.
5. Separately authorize the exact `resident.reasoning.escalate` grant for the selected provider ID. Keep source-worker `worker.register` and `assignment.execute` grants separate.
6. Approve or decline the pinned harmless Engineering objective, including repository, allowed artifact path, expected output, independent verifier and cleanup.
7. Before deployment, require a protected production snapshot and restore proof, release-specific rollback/service plan, named operator, maintenance window, and separate change authorization.

Items 5–7 are not implied by selecting OAuth settings. This dossier records the decisions needed; it grants none of them.

## Structured commissioning blocker register

This is a truthful operator register, not a claim that an automated live
blocker service exists. Current durable status is in the C4 commissioning
monitor and issue #120. Issue reporting is manual; no alert timer or automatic
resume is installed for this preflight.

| ID / type | Detection signal | Owning office / authority required | Timeout | Durable state / alert | Retry or resume trigger | Evidence |
|---|---|---|---|---|---|---|
| C4-PROVIDER / credential, permission, dependency | Provider map absent/unverified; OAuth issuer/audience/subject-client mismatch; provider not registered; exact escalation grant denied/unavailable | Steward and identity/authority administrator; owner assignment is not recorded. Approve issuer, mapping, audience, route, credential custody and exact provider-scoped grant. | Production timeout and escalation threshold are not configured. Each exchange would use its own finite durable deadline only after commissioning. | Commissioning monitor BLOCKED at 1/5; report to issue #120. No live provider exchange or alert delivery. | Resume only after an approved identity/map/credential and exact grant are independently read-only verified, then repeat isolated checks. Live invocation still requires deployment and provider-call authority. | External exchange contract and OAuth adapter; current C4 monitor; this record's route trace. |
| C4-SOURCE-WORKER / permission, credential | Worker principal absent/unverified, registration missing, or worker.register / assignment.execute denied for exact work-order scope | Steward and authority administrator; identity and grant owner are not recorded. Approve a distinct source-worker principal, bound credential and exact scoped grants. | Not configured. | Commissioning monitor BLOCKED; issue #120 manual reporting. No source worker activated. | Resume after identity-bound credential and exact grants are verified, with a separately approved harmless objective. | Grace execution contract and current C4 monitor; no live worker evidence. |
| C4-OBJECTIVE / approval | Exact objective remains AWAITING_STEWARD_APPROVAL | Steward; approve or decline the pinned repository, allowed artifact path, acceptance criteria, executor, verifier and cleanup. | No decision deadline is configured. | Status remains in the C4 monitor; issue #120 is the manual decision record. No objective submitted. | Resume only on a durable approval for that exact objective and revalidation of executor/verifier authorization. | Prepared objective referenced by the C4 monitor; no execution evidence. |
| C4-DEPLOYMENT / commissioning, manual action | Fresh protected snapshot/restore, current migration/checksum preflight, service rollback, maintenance window or separate change authorization absent | Camrui Operations and Steward; exact authorized operator/change owner must be named before a window. | No window or timeout is scheduled. | Commissioning monitor BLOCKED at 1/5; issue #120 manual report. No production release/migration/service state changed. | Resume only after every deployment gate is evidenced, rollback is rehearsed for the target release/services, and separate written authorization is recorded. Failure returns to NO-GO; no automatic retry. | Isolated package/migration/pointer rehearsal only; production rollback remains unverified. |

## Isolated evidence and rollback boundary

The durable checkout record for the 2026-10-18 rehearsal is
evidence/checkouts/GRACE-COMMISSIONING/20261018T1756Z-e38368e/acceptance.json; the
adjacent artifacts manifest lists exact hashes for raw logs. The worker suite
was rerun using a fresh disposable PostgreSQL 16 cluster. Its command, raw output,
source commit, duration, and artifact hashes are recorded in the adjacent evidence inventory. Earlier operator report hash correction is
preserved: .codex-monitor/engineering-worker-test-evidence-20261018.md has
SHA-256 fcf1111d7fa6e6bb26a2de8817562505bc7e66657ddd994733663e0c5b699e50.
The database tests use synthetic identities and local fixtures.

The only rollback procedure exercised here is a synthetic release-tree pointer
switch from a predecessor to the verified package and back. In an isolated
directory, retain immutable predecessor and candidate release directories,
write the candidate path to a temporary symlink, atomically rename it over the
test current pointer, verify the resolved target, then atomically restore the
predecessor and verify it. The rehearsal uses no systemd unit, production path,
credential or database. Its captured test output records each target and
result. Do not apply this as a production runbook: production snapshot/restore,
service-specific stop/restart ordering, database compatibility after rollback,
maintenance window and rollback authorization are still unverified.

For a read-only candidate check, inspect git status and exact commit, run
scripts/verify_camrui_package.py on the immutable archive, then run
scripts/process_graph.py check. Isolated database validation must use a fresh
disposable PostgreSQL instance with RIVERVIEW_TEST_PG_DSN pointing only at that
instance. Record the full command and output in the checkout directory. Never
substitute a production DSN, attempt a live provider call, change a grant, or
start a production service as part of this cookbook.
