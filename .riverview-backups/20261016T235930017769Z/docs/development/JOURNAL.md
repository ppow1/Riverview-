# Riverview~ development journal

**Document Revision:** 1.0.158
**Component:** ENG-RECORDS
**Date:** 2026-10-12 UTC
**Changed:** 2026-10-16 UTC | RV-M33-DECOMMISSION-001 | Record exact-run M33 decommission and preserve production acceptance evidence
**Changed:** 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Record guarded M33 registration retirement source and production execution boundary
**Changed:** 2026-10-16 UTC | RV-WORKER-HEALTH-REPORTING-001 | Investigate stale/unknown worker projection and distinguish lease activity from process liveness.
**Changed:** 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Record offline diagnostic snapshot source, verification evidence and production boundary
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PR67-SNAPSHOT-CSP-FIX | Record controlled f957 release, verified migration and live service, partial diagnostic export, and isolated CSP correction evidence
**Changed:** 2026-10-16 UTC | RV-PROPOSAL-AUTHORING-GUIDANCE | Link the AI startup hints to a concise proposal authoring playbook
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PR71-PRODUCTION-ACCEPTANCE | Record PR #71 reconciliation, exact CI, immutable Camrui release, strict-TLS snapshot acceptance, and access-limited verification
**Changed:** 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Record PR #65 integration reconciliation, full-inventory browser fixture package results, proposal readiness, and Windows CA findings
**Changed:** 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Record final exact-graph-set ZIP integrity and synthetic page-shell versus live-dashboard acceptance boundary
**Changed:** 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Correct final archive byte count from independently inspected ZIP
**Changed:** 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Verify actual dashboard DOM and complete desktop/mobile snapshot package exports
**Changed:** 2026-10-13 UTC | RV-GRACE-ROUTER-ACL-READINESS-001 | Correct router startup readiness for restricted authority-ledger ACLs and record regression evidence
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Recover website punch list and implement cross-workflow destination focus/return
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL027 | Record final workflow map revision, controlled-source repair, and verification outcome
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PUNCH-LIST-001 | Clarify PR #40 documentation overlap and website ownership boundaries
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL025 | Add cookie-only Firefox workflow regression and record production SSH denial
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL026 | Clarify workflow viewer interaction and legend semantics
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL025 | Record final styled Firefox evidence and focused suite results
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL013 | Record exact-match code-to-workflow/cookbook coverage audit
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL028 | Record missing notification summary fields as cross-scope blocker
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL004 | Record graph linkage implementation, browser evidence, revision audit and PR #42 reconciliation
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL006/008/011 | Record overview guidance, worker inventory, activity paging, evidence and integration-owned blockers
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL025 | Record clean controlled-revision and evidence-manifest checks
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL025 | Record PR #42 update and exact-head CI result
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL012 | Record Activity provenance UI and event-source limitations
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL014 | Record projection status guidance, browser verification and source semantics
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL016 | Verify documentation tab reuse and return without duplicate dashboard windows
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL010/015/020/023/024 | Record readiness, control, menu and milestone usability verification
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL019 | Record narrow-screen conversation overflow defect, correction, and evidence
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL036 | Record accessible persistent navigation collapse and browser evidence
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PL003 | Record exact canonical task-title lookup and assignment-contract gaps
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PL029 | Clarify notification delivery/receipt and record seen/decision API blockers
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PL038 | Record searchable catalog behavior, isolated browser evidence, and freshness/coverage source boundary
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PR45-RECONCILE | Preserve merged same-source work-order retry behavior while reconciling website changes
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PL038-POST-PR45 | Record final integrated browser/test/graph verification
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PR45-REVISION-AUDIT | Record and repair predecessor evidence gaps found after integration
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PR46-RECONCILE | Reconcile current integration head and preserve resident-knowledge changes unchanged
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PR42-INTEGRATION-RECONCILE | Reconcile website work with latest integration through PR #63 and record release gates.
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PR42-EXACT-CI | Record exact-head CI and browser verification after integration reconciliation.
**Changed:** 2026-10-16 UTC | RV-WEBSITE-PR42-PRODUCTION-ACCEPTANCE | Record direct Camrui installation, SSH-path diagnosis, production acceptance, and remaining Steward-only checks.
**Changed:** 2026-10-15 UTC | RV-WEBSITE-PR42-RECONCILE | Preserve PR #44 integration journal entry and record current base reconciliation
## 2026-10-16 UTC — RV-WEBSITE-PR42-PRODUCTION-ACCEPTANCE

PR #42 source `928649bd1ff695fe9a95915647a49943ffe921fe` was merged as
`50ed988f84398bde7aa9df5bb3f163d753748fed` and installed using the documented
versioned dashboard release procedure. This runner is `admin1-Default-string`,
Ubuntu 24.04.3 LTS, and owns Camrui's `192.168.1.155` address. Routing and TCP
checks showed the target is this same host. The direct SSH attempt selected the
default `admin1` Ed25519 identity, which the local SSH service rejected; no SSH
agent or configured host alias was available, and batch mode did not attempt a
password. This was an identity mismatch, not a network or service failure. The
existing `sudo -n` authorization allowed the approved release procedure to run
locally; SSH policy and credentials were not changed.

Immutable release `website-pr42-928649bd1ff695fe9a95915647a49943ffe921fe` is
active at `/opt/riverview-status-dashboard/releases/928649bd1ff695fe9a95915647a49943ffe921fe`;
the previous working release remains available and the dashboard-only rollback
plan is recorded with root-owned deployment evidence. The package SHA-256 is
`19890d22e18caa4896a6e944cf021397d11d95a54ba96a4928e86e2529b46c6b`. Dashboard
health, TLS, read-only projections, navigation, graph rendering, catalog search,
documentation links, objective/assignment visibility, and service continuity
passed live browser/HTTP checks at `https://192.168.1.155/`. The public DNS name
currently serves a separate site, so it is not the Camrui dashboard URL.

The production browser reported no console errors or failed requests; graph
selection completed with 42 nodes, 4 decisions, and 51 rendered SVG edges out of
55 canonical edges. Search narrowed the workflow registry from 19 to 5 results.
The requested 390px viewport was constrained to 500px by the available Firefox
harness; no overflow occurred at 500px. Positive production account-cookie login
remains pending Steward sign-in. End-to-end SSE/reconnect/deferred-response
acceptance remains unverified because exercising it requires submitting a
production conversation message; the read-only boundary was preserved. No
objective or conversation was created or modified, no rollback was needed, and
the process workflow map was unchanged because no process semantics changed.
Full evidence: `evidence/checkouts/WEBSITE-PR42-PRODUCTION/20261016T172206Z-928649b/`.

## 2026-10-16 UTC — RV-WEBSITE-SNAPSHOT-041

PR #64's exact tested head `a8626602f1c5bb237b362256a28a8b6d27a04cc4` passed controlled-checkout CI and was merged as `8fed8d4b78d9a1d7bb8dc451a6e292d6049831b8`; the website was not redeployed for this documentation-only integration. Positive authenticated-cookie production acceptance and live production SSE/reconnect/deferred-response acceptance remain explicitly unverified. No production conversation, objective, or database record was created or changed.

The website source now has an authenticated versioned capability registry and dynamically inventories version-controlled `process_graphs/*/*.json`. That is the canonical graph source; PostgreSQL contributes only the dashboard's existing read-only execution-position projection. The one-button ZIP includes the current authorized operational snapshot, per-page sanitized offline HTML and visual maps with control IDs, bounded request/interaction/error history, original graph JSON, separate runtime status, workflow index/cross-workflow jump references, full graph SVG/PNG and detail tiles. No global combined graph or proposed automated QA system was added. Package and privacy omissions are represented in the manifest; live user permissions remain enforced.

The synthetic Firefox run downloaded a 214,159-byte ZIP containing 2 workflows, 3 nodes and 2 edges; the archive and each listed hash passed, both page and workflow PNGs decoded, all canonical node/edge references reconciled, the cross-workflow jump remained resolvable, page controls correlated to stable IDs, and synthetic conversation/form values and cookie material were excluded. It is a fixture-only pass, not production acceptance. Current source inventory reconciles to 19 workflows, 478 nodes, and 637 edges; inventory is discovered dynamically, not enforced as a constant. Evidence: the current full-inventory sanitized browser report is linked below; this earlier two-graph smoke fixture is preserved in the working evidence directory.

### Final diagnostic export verification and acceptance boundary

A rerun against the current source completed in isolated Firefox at `evidence/checkouts/WEBSITE-SNAPSHOT-041/20261016T-snapshot-fullsource-final5/`. The downloaded ZIP is 32,092,323 bytes (SHA-256 `abb117743a0f1e0876c51d10d3acd94292ed31a608613ae75a869914dd5c47e3`); independent Python ZIP inspection found 126 files, passed CRC and manifest file hashes, and reconciled 20/20 workflow JSON/SVG/PNG exports, 487 nodes, 646 edges, and zero unresolved references. The manifest reports 10/10 page records and visual representations, 54 registry controls, 20 observed controls, no omissions, and complete capture. The inventory and definitions are from this repository's canonical registry and version-controlled process graph files.

The browser run's page shell is synthetic. It exercises the actual snapshot JavaScript and workflow viewer JavaScript against the real capability registry and full graph inventory, but it does not load the dashboard's production `index.html`, `app.js`, or production CSS. Therefore it demonstrates the downloadable export contract and viewer interactions in an isolated browser, not visual fidelity of actual dashboard pages. The ZIP's `source_commit` and `deployment_id` are synthetic fixture identifiers. Actual-dashboard browser capture, authenticated-cookie behavior, and production acceptance remain unverified; the production website has not been changed. The 32 MB fixture ZIP remains preserved locally for independent offline inspection; only its checksum, browser report, and archive-inspection summary are committed as review evidence.

The current focused dashboard tests pass (37 passed, 8 skipped); process graph validation and graph check pass at 20 workflows/487 nodes. Production proposal registry readiness remains unchanged: Camrui is on PR #42 release/source `928649bd1ff695fe9a95915647a49943ffe921fe`, latest applied migration is `0006_verifier_revision_rechecks`, migration `0010` and both registry tables/routes are absent, and there are no proposal registry records. This is read-only evidence; Codex 1 owns activation. Camrui's TLS chain is valid locally for the LAN IP and the Riverview private root CA; missing root trust in Windows remains the likely, unconfirmed client cause because Windows was not inspected. The strict CurrentUser root import procedure and expected fingerprint are in the status dashboard cookbook.

### PR #65 source reconciliation and full-inventory website snapshot

The website branch was reconciled with the latest integration head `6c33969684e5fa84c35b2456262f187c004c4b0c` (PR #65). The merge preserved its proposal lifecycle API, migration source, and workflow without editing their contracts. The current canonical graph inventory is 20 workflows, 487 nodes and 646 edges; generated process maps and the status dashboard workflow map were refreshed and graph validation passed.

The earlier full-inventory synthetic-shell run discovered the same 10 page declarations, 54 registered controls, 20 workflows, 487 nodes and 646 edges, with all per-workflow JSON/SVG/PNG exports and cross-viewport graph identity checks passing. Its historical package is separate from the final rerun recorded above; its source/deployment values were synthetic, not production provenance. The current final report and archive-inspection evidence are at `evidence/checkouts/WEBSITE-SNAPSHOT-041/20261016T-snapshot-fullsource-final5/`. A separate read-only Camrui production-readiness report is at `evidence/checkouts/WEBSITE-SNAPSHOT-041/20261016T-snapshot-fullsource-final4/production-readiness.json`; no production mutation was performed.

Focused dashboard/proposal/conversation pytest selection: 37 passed and 43 skipped because PostgreSQL integration is not configured in this checkout. Process graph validation passed at 20 workflows/487 nodes; controlled revision audit and exact-head GitHub CI remain release gates for the new PR. No website deployment or production mutation occurred.

Read-only Camrui check: active release is `website-pr42-928649bd1ff695fe9a95915647a49943ffe921fe` from source `928649bd1ff695fe9a95915647a49943ffe921fe`; service is active and strict HTTPS returns 200. Database `riverview`, schema `riverview_dev`, has latest migration row by `applied_at` `0006_verifier_revision_rechecks`; `0009_durable_objective_steps` exists, `0010_institutional_proposal_registry` and its tables do not. The installed release has no institutional proposal create/search/revision routes and no institutional registry records. One legacy objective has a non-null proposal field; it is not a registry row. PR #65 routes and migration source are merged but not activated. No migration/restart/deploy/write was performed.

Camrui's HTTPS certificate validates locally through the installed Riverview root. Leaf SAN includes `192.168.1.155`, so no server name mismatch is evident. Root CA SHA-256 is `D7823E13473A2F1F86A50781071CA7D6E08CA0B8D960C327739C85BA14DDC32D`. Windows itself was not inspected; missing root trust is the likely cause of the reported PowerShell exception, not a confirmed Windows-side finding. The cookbook records strict transfer, fingerprint validation, and CurrentUser Trusted Root import commands; TLS bypass is not recommended.

## 2026-10-16 UTC — RV-GRACE-VERIFIED-GROUNDING-RESUME-001

The existing objective `objective:grace-conversation:2c573041-cc5e-4b54-9f93-8163de91e52c` and assignment
`assignment:grace:6759a4f47a95aad779e0bd76699fed9a71098ae8` remained intact
after the owner-session release correction. Read-only metadata showed five
retry-safe Codex intents/recovery records, zero worker attempts/results/
verifications, and no assignment artifact. The worker last persisted
`ground_assignment=UNVERIFIED` and left the same assignment at
`blocked/WAITING_FOR_EVIDENCE`.

The active knowledge root is the immutable Grace execution release
`63798c237ff8231191de5efa315ed7f11547e8bc`; its 1,093 listed package files
passed checksum verification. The protected runtime environment still pinned
knowledge to predecessor `4a51865201b0e578937aab4fb1cc370ab6e5fe71`, which
made the provider reject the active package identity. The pin was updated to
the verified active release after preserving the prior root-owned environment
file in `/var/backups/riverview-grace-env.20261016TJnbUpN/`. A read-only provider
call then returned VERIFIED with complete retrieval, the active release ID,
and five references. The owner-session service stayed healthy; no dashboard,
database, authority grant, migration, OCTO model, objective, or assignment data
was modified.

That runtime pin correction alone could not resume the durable assignment:
`claim_next()` admits only `ready` work, while the assignment was blocked at
`WAITING_FOR_EVIDENCE`. A bounded recovery path is therefore being integrated
in the existing worker loop. It rechecks the registered worker and exact
execution grant, requires fresh verified grounding and action preflight, the
original verified work order, expired/absent lease, remaining retry budget,
only previously reconciled typed Codex intents, and no attempt/result/
verification/artifact before atomically transitioning that same assignment to
the canonical ready node. The ordinary claim rechecks authority before action.
The regression verifies retry-ceiling enforcement, same-objective completion
to the claimed execution boundary, and revoked-grant denial.

The new isolated PostgreSQL worker suite passed 25/25. The complete isolated
PostgreSQL regression passed 436 tests with one intentional skip and no
failures; process graph synchronization reports 19 workflows/464 nodes and
controlled revision audit had zero findings before the final record update.
This implementation is not yet integrated or deployed. The production
assignment remains blocked pending the reviewed release and its ordinary
lease/recovery path; no replacement objective, direct SQL state edit, or
synthetic production artifact was created.

**Document Revision:** 1.0.120
**Component:** ENG-RECORDS
**Date:** 2026-10-12 UTC
**Changed:** 2026-10-15 UTC | RV-GRACE-AUTHORIZED-SNAPSHOT-001 | Revalidate resident reasoning through the protected office-state capability
**Changed:** 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001 | Record exact source-pin mismatch, same-assignment evidence recovery, regression, and production boundary
**Changed:** 2026-10-13 UTC | RV-M1.1-PACKAGE-BASH-001 | Allow the explicitly reviewed supervised Bash runner in exact-source packages while retaining strict checks for other scripts
**Changed:** 2026-10-11 UTC | RV-M4.2-HTTP-FIXTURE-CORRECTION | Isolate local reasoning contract tests from sockets and assert HTTPError stream closure
**Changed:** 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Record responsive conversation interface implementation and isolated real-model browser acceptance
**Changed:** 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Record dashboard-only Camrui deployment and post-deployment browser/runtime evidence
**Changed:** 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Diagnose transient credential loss, confirm exact Steward grants, and test persistent same-origin cookie authorization
**Changed:** 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Commission dashboard release and verify real model turn, exact denial, PostgreSQL persistence, and service restart recovery
**Changed:** 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Record deployed 390 CSS-pixel responsive iframe verification; retain physical Windows check as pending
**Changed:** 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION-CHECKPOINT | Record persistent objective execution evidence and non-commissioning boundary
**Changed:** 2026-10-11 UTC | RV-M4.1-M4.2-OCCUPANT-REPLACEMENT-INTEGRATION | Record isolated cross-component Grace identity replacement regression and limits
**Changed:** 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Diagnose shared psycopg connection transaction interleaving; serialize database scopes and add independent-connection concurrency regressions
**Changed:** 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Record passing Camrui Firefox recommission, independent PostgreSQL commit checks, protected backup/restore, and transient CPU-model boundary
**Changed:** 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Verify live dashboard restart marks pending turn interrupted, and follow-up is committed and browser-visible despite a 30-second test wait timeout
**Changed:** 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Reproduce exact 6 API versus 4 independent committed events on preserved pre-fix code under an overlapping transaction scope
**Changed:** 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Preserve reproducible pre-fix script, checksummed 6/4 output, and corrected temporary-worktree setup attempt
**Changed:** 2026-10-11 UTC | RV-M4.1-CROSS-INTEGRATION-CI | Record exact-head CI run 38165302494 at commit 89752f7
**Changed:** 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Record committed-source browser acceptance, full tests, graph and revision audit

## 2026-10-11 UTC — RV-M3.4-GRACE-CHAT / isolated resident website conversation

Verified clean PR #24 baseline `c5d694909bc88fb94c09658d57b8cc00d8f88d3b` and
created `codex/m3.4-grace-web-conversation` stacked on that draft. The canonical
roadmap describes M3.4 as a proposal; this implementation records the requested
chat work as isolated engineering and does not claim formal proposal acceptance.
The dashboard already separated its bearer from an `X-Riverview-Authority`
credential on governed objective routes, and `AuthorityRegistry` already exposes
office-bound occupant/model bindings. Reused those contracts and the existing
loopback, model-name, and SHA-pinned local inference adapter. Conversation rows
and append-only events were added to the resident-execution migration family.

The website path now has explicit office-scoped read/send grants, server-side
model binding resolution, message idempotency, bounded recent-history context,
durable response/failure state, startup recovery for incomplete turns, and a
chat view integrated into the existing dashboard shell. Ordinary chat has no
objective or worker promotion call. Prior to edits, exact predecessor bytes and
checksums were preserved by `scripts/revision_control.py` for the touched
dashboard, provider, contract and journal files; new files start at revision
1.0.0. The local Qwen3-0.6B GGUF and pinned llama.cpp binary are already present.
No shared service, database, secret, external model endpoint, or 235B process was
modified. Commit `1fa9d6104fc07609e3d8bbda8bf836b0b22e19c1` passed the complete
unittest suite (224 tests, no skips/failures) and a committed-source Firefox
commissioning run. The browser run produced two actual model responses at 31.95s
and 27.92s, retained the same conversation through refresh and isolated server/
runtime reconstruction, persisted one controlled interruption, and verified
zero objective promotion. The PostgreSQL counts were 3 user events, 2 assistant
events, 1 interruption, and 0 objectives. Evidence:
`evidence/checkouts/RESIDENT-CONVERSATION/20261011T-committed-source-browser-verified/`.
The database cluster, schema, browser session, server and model process were
test-owned and cleaned up. PostgreSQL-focused/provider tests passed 16/16; graph
validation/synchronization passed at 17 workflows / 348 nodes; the revision
audit against PR #24 head reported zero findings. Existing resource warnings
from unrelated suite fixtures were emitted but did not fail tests. This is not
shared-service deployment, a systemd process restart test, formal M3.4 proposal
acceptance, or full Component DoD.

## 2026-10-11 UTC — RV-M3.3-COURSE-CORRECTION / M3.3 commissioning and M4.2 checkpoint

Reconciled M3.3 commissioning evidence against the canonical criterion. Live
records prove a governed authorized request, denied unauthorized request with
no writes, durable assignment/event creation, scheduled execution by the
commissioned service, a protected repository-test report artifact, distinct
independent verification, PostgreSQL lifecycle/provenance, dashboard status,
and restart recovery. A separate NO_MATCH assignment remained in
WAITING_FOR_EVIDENCE while another normal-route assignment completed and was
verified. This satisfies the roadmap requirement for two concurrent durable
assignments progressing independently; simultaneous throughput across multiple
executor processes was not measured and is not stated as a separate criterion.
Existing isolated suite, CI, graph, and revision-audit evidence is retained in
the M3.3 commissioning directories. Scoped technical criteria are ready for
Steward review; no formal acceptance, merge, or full Component DoD is claimed.

Completed the M4.2 local provider boundary checkpoint already in progress. Six
isolated HTTP contract tests passed. A real Qwen3-0.6B loopback call did not
produce a complete plan within the bounded 30-second request and returned
sanitized UNAVAILABLE; no resident call or authority-state write occurred.
Explicitly close `HTTPError` response resources and replace the threaded
socket-backed M4.2 contract fixture after the six focused tests pass with
`ResourceWarning` promoted to an error. The full suite passed 196/196 with no
skips, failures, or errors. Tracemalloc localized its remaining
`ResourceWarning` to the existing M4.3 `tests/test_local_inference.py` threaded
HTTP fixture when it replaces the test server; that out-of-scope fixture was
not changed during this M3.3-priority checkpoint. No service, shared database,
resident identity, credential, or M3.3 worker state was changed. Evidence:
`evidence/checkouts/M4.2-LOCAL-REASONING/20261011T1340Z-fce3c30/`.

## 2026-10-11 UTC — RV-M3.3-AUTHORITY-COOKBOOK-COMMISSIONING / dashboard route

Expanded the institutional authority cookbook with the isolated `assignment.create` transaction boundary, exact denial/unavailable handling, a throwaway-database regression command, post-recovery checks and escalation conditions. Corrected its current-state text to distinguish the deployed exact-grant database function from an application intake that has no live route. The dashboard documentation endpoint returned HTTP 200 and safe readable HTML with headings and command blocks; evidence paths remain plain text because the dashboard deliberately serves only `docs/components/*.md`. The first added browser-test assertion expected Markdown backticks in the rendered output; actual HTML correctly used a `<code>` element. Corrected the assertion, then the focused route test passed 1/1 and the complete dashboard HTTP class passed 12/12. Evidence retains the initial assertion failure and corrected results. No runtime, shared database, or service changed. M3.3 remains blocked on governed request-path/worker integration, commissioned real worker and real repository-backed knowledge provider.

## 2026-10-11 UTC — RV-M3.3-ASSIGNMENT-INTAKE / isolated authorized creation

Added `AuthorizedAssignmentIntake`, which requires a current exact `assignment.create` grant, derives the assignment actor from the protected grant result, and holds the grant-row lock across the ledger write and created event in one PostgreSQL transaction. Focused isolated PostgreSQL integration tests passed 4/4, including idempotent replay and missing, wrong, revoked, unavailable, and forged-actor rejection. The disposable schema was removed. This is a callable application entry point, not a deployed route: raw `PostgresLedger.create` and direct SQL are still persistence-level bypass paths unless callers are constrained to this API. The shared schema/runtime privileges and live services were not changed. M3.3 remains BLOCKED pending governed request-path integration, a commissioned approved worker, and a real repository-backed institutional knowledge provider. Evidence: `evidence/checkouts/M3.3-ASSIGNMENT-INTAKE/`.

## 2026-10-11 UTC — RV-M4.3-LOCAL-INFERENCE / real concurrent CPU inference

Implemented an optional `local.inference.v1` worker action using the existing exact-grant, lease, execution-intent, PostgreSQL artifact, and independent-verifier path. Standard-library HTTP is restricted to literal loopback `/v1` endpoints; request/response sizes and duration are bounded, credential-shaped prompt content is rejected, and incomplete output cannot succeed. Existing deterministic SHA-256 execution remains the default. Added four loopback/error regression tests and a PostgreSQL-backed structured-artifact/independent-verification test.

Built llama.cpp v0.6.0 from pinned commit `d81235049384534c167caea52b85a694f6103d14`; Qwen3-0.6B Q8_0 was sourced at immutable model revision `23749fefcc72300e3a2ad315e1317431b06b590a` and verified against publisher SHA-256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`. A successful actual-model run created two unique PostgreSQL assignments, claimed distinct leases in parallel, persisted `AUTH` and `RESOURCE` JSON results, passed independent exact-label verification, and completed both assignments. Model calls overlapped 18.545 seconds; event-to-lease queue delays were 185.0 ms and 134.3 ms. The acceptance JSON verified result hashes and temporary server/schema cleanup.

The first classification attempt was a genuine model-quality failure: it emitted `AUTH` for both prompts and the independent verifier rejected the full-disk result. A harness timestamp bug also interrupted report completion and the first cleanup omitted `CASCADE`; these defects were diagnosed, the evidence was preserved, and only the identified disposable test schema was inspected and explicitly removed. A corrected isolated instruction-following task then passed. This is not evidence of general model reasoning. The UTF-8 private PostgreSQL test cluster was user-owned and isolated; no shared database, installed service, worker credential, or production configuration changed. The external knowledge provider, operational worker service, M3.3, and Grace M4.4 remain outstanding. M3.3 remains the roadmap cursor. Evidence: `evidence/checkouts/M4.3-LOCAL-INFERENCE/20261011T094446Z-cpu-e2e/` (failed attempt) and `20261011T094654Z-cpu-e2e/` (successful precommit run).

The feature/evidence source is committed and pushed as `bbe9a6c1c63345861da5bfeb7cfb77931961e005` on `codex/m4.2-resident-reasoning`. The committed-source acceptance was repeated with a clean tracked tree; two concurrent model calls again completed with independently accepted results and verified digests. The full suite passed 155/155 with no skips, the canonical graph check passed at 13 workflows / 269 nodes, the revision audit reported zero findings, and exact-head CI run 38129918014 passed. Evidence: `evidence/checkouts/M4.3-LOCAL-INFERENCE/20261011T095229Z-committed-source-e2e/`.

## 2026-10-11 UTC — RV-OVERNIGHT-20261011-CHECKPOINT / M4.1 live bootstrap and M4.2 CI

Completed scoped M4.1 database-boundary and Steward-token bootstrap verification on Camrui. A protected PostgreSQL dump restored into a disposable database with matching catalog counts; the disposable database was removed. Exact committed source `d3a0ed4fdec3061923964451ce2fccff18fadca7` passed preflight, apply and postflight. Bootstrap returned `BOOTSTRAPPED`, then `ALREADY_BOOTSTRAPPED` on a fresh process. The root-owned token was checked in-process against the digest and three scoped active grants without printing the token. Runtime registry reads and manager DDL were denied. `riverview_dev` remained at 9 migrations, 4 assignments and 11 events; PostgreSQL, event processor, CME monitor, notification dispatcher, dashboard and SSH stayed active. Evidence: `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T081700Z-live-bootstrap/`.

M4.1 remains IN PROGRESS because no resident/worker assignment control consumes the registry. M3.3 still requires that integration and a real institutional knowledge provider. M4.2 is isolated engineering only; no reasoning provider/resident service exists. Exact-head CI run 38124331966 passed on `f807d95d688b8a486db34eb5aa4be9f78c8f998d`. PR #21 is open/draft/unmerged. No Steward acceptance beyond M3.1 is claimed. Next: correct the roadmap and M4.2 records, then continue safe independent cookbook and resident/model integration work without substituting mocks for live proof.

## 2026-10-11 UTC — RV-M4.2-001 / isolated resident reasoning verification

Implemented a provider-neutral resident reasoning slice on `codex/m4.2-resident-reasoning`, based on the unmerged M4.1 DB-boundary PR #20 head. It reuses the exact `AuthorityRegistry` office binding/state grant and frozen worker knowledge-provider v1 contract. Current assignment/rules are regrounded before each bounded provider route; missing or unverified knowledge waits and is durably recorded; only explicit configured fallback targets are eligible. Provider output is a bounded typed plan proposal, never executable authority. The exact office-state grant and assignment revision are rechecked before CAS persistence; a new runtime instance reloads the previous persisted plan. Input redaction, request size, concurrency, timeout, and per-route token budgets are bounded.

The focused current resident suite passed 10/10 and the complete suite passed 147/147 with no skips/errors/failures against disposable socket-only PostgreSQL 16.15 clusters. The focused and complete fixture cleanup left zero `rvtest_*` schemas/roles; the final cluster stopped cleanly. Graph validation passed at 13 workflows/255 nodes, compileall passed, and the controlled revision audit passed with zero issues. An earlier full-suite attempt exposed the newly added JSON graph's missing revision-sidecar registration; its failure/cleanup evidence is retained and the sidecar was corrected before the passing run. Full evidence is `evidence/checkouts/RESIDENT-REASONING/20261011T074000Z-isolated/`; earlier failures are retained in sibling timestamped directories.

No shared DB, identity, credentials, services, assignments, or deployment changed. The test provider is a mock only; no live provider/resident integration is claimed. Exact-head GitHub controlled-checkout run 38122430742 passed on `bf9905af575da6b0254920e467476f0883156050`. PR #21 is draft/open/unmerged on top of PR #20; neither PR was merged. M4.2 remains in progress pending operational provider/authority integration and acceptance. M3.3 remains the earliest unaccepted roadmap step, gated on live authorization and the real institutional knowledge provider.

## 2026-10-11 UTC — RV-M4.1-FRESH-SCHEMA-CI-RESULT / controlled checkout passed

Exact-head GitHub controlled-checkout run 38121104825 passed on `73613cea5d0e1c179d33eebf576ef3931efdf5a3`, covering the complete suite, canonical graph validation and controlled revision/predecessor audit after the fresh-schema ledger correction and its retained backups. The implementation suite passed 137/137 on isolated PostgreSQL 16.15, zero skips/failures/errors. PR #20 stays open/draft and unmerged. No live authority schema or credential was provisioned; deployed services and shared state remain unchanged.

## 2026-10-11 UTC — RV-M4.1-FRESH-SCHEMA-MIGRATION-LEDGER / empty-schema acceptance defect

The authority integration fixture had applied Core migrations before the dedicated authority migrations, masking a fresh-install defect: the dedicated schema had no `schema_migrations` checksum ledger. Added idempotent authority migration `0000_authority_migration_ledger.sql` and changed the registry fixture to begin with a genuinely empty schema. Focused registry tests passed 7/7; the full isolated PostgreSQL 16.15 suite passed 137/137 with zero skips, failures or errors. Test cleanup left zero fixture schemas/roles; the private cluster socket was absent after shutdown. Canonical graph synchronization/check passed (12 workflows/228 nodes), compileall passed and controlled revision audit had zero issues. Evidence is in `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T072000Z-fresh-schema-ledger/`. The live Camrui authority schema/roles remain absent; no shared database, identity, credential, service, assignment or deployment was changed. This repairs isolated installation readiness, not M4.1 commissioning or M3.3's live gate.

## 2026-10-11 UTC — RV-OPS-COOKBOOK-DASHBOARD-PACKAGE-ROLLBACK / live compatibility correction

Attempted a versioned dashboard-only deployment of `6403e45` after package manifest and shell checks passed. The new release started and the deployed Firefox run showed live healthy PostgreSQL/CME, a completed persisted assignment with one independent verification, 19 pre-existing documentation links returning HTTP 200, and no browser errors. An additional shell-link check then found that the M4.1 package omitted three repository-knowledge documents present in the active M3.3 release; the candidate link returned HTTP 404. Restored the recorded `7a9ff46` release through the dashboard symlink and restarted only the dashboard. After its brief readiness interval, dashboard was active/HTTP 200; PostgreSQL, event processor, CME monitor, notification dispatcher and SSH remained active; unit checksum unchanged. Candidate release/archive and browser screenshots were retained under `evidence/checkouts/OPERATIONS-COOKBOOK/20261011T060100Z-dashboard-doc-release/`. No shared database or credential changed.

The full-source package on the M4.1 branch cannot yet replace the active dashboard release without synchronizing the M3.3 documentation and canonical graph. The current deployed PostgreSQL cookbook still includes placeholder `PGPASSWORD`/credential-DSN examples. The corrected branch cookbook is safe, its local route regression passes, and the full 133-test suite passed CI before the package trial, but those revised pages have not been live deployed. Regression coverage now requires every documentation link in the static dashboard shell to resolve from the packaged tree. Continue with source/graph dependency reconciliation before retrying a deployment; preserve the previous live release meanwhile.

## 2026-10-11 UTC — RV-OPS-COOKBOOK-PG-SECRET-SAFETY / M1.4 live-state correction

Revised the PostgreSQL ledger cookbook to remove password-bearing `PGPASSWORD` and credential-DSN examples and accurately identify the `riverview_dev` application schema. Added route regression assertions; the focused safe Markdown route passed. Read-only peer inspection of the commissioned local PostgreSQL instance confirmed nine migrations, including `0001_assignment_leases` applied at `2026-10-10 18:27:04.341175-04:00`; its recorded SHA-256 matches the checked-in migration. This corrects prior roadmap/M1.4 record/cookbook claims that it was absent. The observed migration was applied as a later worker/monitor dependency and does not prove a standalone scheduler service or M1.4 commissioning. No shared DB mutation occurred.

On an isolated socket-only PostgreSQL 16.15 cluster, full suite passed 133/133 with no skips; focused documentation route passed 1/1. Isolated cluster teardown left zero `rvtest_*` schemas/roles. Graph validation and controlled revision audit are being rerun after these final record edits. Evidence, including the exact peer query result and test log, is retained in `evidence/checkouts/OPERATIONS-COOKBOOK/20261011T055428Z-pg-doc-safety/`. The earlier scheduler and worker cookbook query/test evidence remains in their linked checkout folders. Existing live services and database were not changed.

## 2026-10-11 UTC — RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS / persisted worker records

Continued in `codex/m4.1-db-privilege-boundary` after scheduler cookbook checkout. Added a controlled worker cookbook revision with isolated-schema preflight and redacted read-only views of registry capabilities, attempts/results, independent verification, execution intents, and recovery decisions. Added a dashboard-route assertion for its rendered documentation. Existing architecture confirms there is no commissioned live worker service or enrollment CLI; the guide directs enrollment only through the trusted control-plane workflow and prohibits manual live row insertion or bearer export.

On a private PostgreSQL 16 socket-only test cluster, all 133 tests passed with zero failures/errors/skips. An isolated schema with the full ledger/scheduler/worker migration chain registered separate synthetic executor and verifier identities; `ContinuousWorker` wrote a deterministic persisted result; independent SHA-256 verification accepted it and the test assignment reached `completed`. The exact diagnostic query showed both identities, one succeeded attempt/result digest, distinct accepted verifier, successful `retry_safe` intent, and no recovery row, without returning tokens, input, event payload, evidence references or result JSON. The fixture schema was explicitly removed, catalog counts reported zero `rvtest_` schemas/roles, and the cluster was stopped and deleted. The safe dashboard route passed 1/1; graph validation passed 12 workflows/226 nodes; controlled revision audit passed with zero findings; compileall and source diff-check passed. Evidence: `evidence/checkouts/OPERATIONS-COOKBOOK/20261011T055053Z-worker-docs/`. Exact-head CI and PR status will follow the final commit. No shared database or service changed, and this isolated worker execution is not live commissioning or Grace acceptance.

## 2026-10-11 UTC — RV-OPS-COOKBOOK-SCHEDULER-DIAGNOSTICS / safe operator diagnosis

On `codex/m4.1-db-privilege-boundary` at `fe4aa3cf5919485c5c5620d76a5ec766213b289f`, confirmed PR #20 remains open/draft and exact-head CI run 38115573864 passed. The shared PostgreSQL/CME/event-processor/dashboard/notification services remained active. Reviewed the scheduler cookbook and identified that its generic “query ready assignments and lease expiries” instruction lacked a concrete bounded read-only query and decision table. Added those diagnostics with an explicit isolated-schema boundary: M1.4 has not been deployed into `riverview_dev`.

Preserved predecessor bytes and checksums for the cookbook, dashboard route test, operations record, and journal before changes. The first focused unittest selector named a nonexistent test class and returned exit 1 before running tests. Corrected the selector to `DashboardHTTPTests`; focused HTML route test passed 1/1. A private socket-only PostgreSQL 16 cluster on port 55486 ran the complete suite: 133 passed, zero failures/errors/skips. The suite left zero `rvtest_` schemas/roles; the cluster was fast-stopped and its disposable directory removed. A separate isolated cluster executed the documented migration and lease queries against one synthetic ready assignment/current lease and returned the expected safe metadata; explicit fixture teardown left zero test schemas. Graph validation reported 12 workflows/226 nodes PASS, controlled revision audit had no findings, and compileall returned exit 0. Immutable logs/checksums are linked in `docs/development/OPERATIONS-COOKBOOK-001_REVISION_RECORD.md` and under `evidence/checkouts/OPERATIONS-COOKBOOK/20261011T054342Z-scheduler-docs/`.

No live shared-schema, credential, role, service, assignment, or worker state changed. M4.1 remains isolated-engineering PASS / live commissioning OPEN, M3.3 remains blocked on real live authorization and knowledge preflight, and PR #20 remains unmerged. Next safe work: preserve the tested docs route through a compatible versioned package and continue M4.1 contract/commissioning preparation without changing the shared database boundary.

## 2026-10-11 UTC — RV-M3.2-001 / durable visual notification design

Started M3.2 on `codex/m3.2-durable-notifications` from the M3.1 accepted
commissioned branch tip `c8d93bc`; PR #16 remains open/draft and unmerged, so
the M3.2 change remains a short dependency branch. The roadmap's sole explicit
M3.2 pass criterion is truthful delivery and acknowledgment for a defined
attention condition using a tested channel. The Core Contract requires durable
decision requests and channels but places authority in the Steward-delegated
institutional service. Decision: use one authenticated in-dashboard visual
channel and durable Postgres records; use the existing service bearer only for
transport authentication. A rendered-delivery receipt and client receipt
acknowledgment must never be called a Steward decision. Create pending requests
only from an authoritative `awaiting_steward` assignment; M4.1 identity/authority
must own future request resolution. Keep CME as source, isolate the delivery
worker, redact source details and privacy-domain data, and preserve the existing
dashboard origin. No migration had been applied at intake.

## 2026-10-11 UTC — RV-M3.2-001 / isolated notification implementation

Implemented migration 0006, a separate bounded dispatcher, the visual notice
projection and two receipt-only API operations. Receipt acknowledgment cannot
change the pending decision-request status or assignment state. The browser
records delivery only when the Notifications view is visible. Notice summaries
are fixed and private-domain events are excluded. The database protects the
receipt-event ledger against update/delete and provides an event scan index.

Verification to date: seven notification tests passed in an isolated PostgreSQL
16.15 UTF8 cluster; the complete suite passed 125 tests with zero failures,
errors or skips. No `rvtest_*` schema remained and the socket-only cluster was
stopped and removed. Process graphs validate at 11 workflows / 209 nodes and the
controlled revision audit passes with zero issues. The first full-suite attempt
was invalid: a no-locale cluster returned text as bytes, and a 40-connection
cap exhausted during test setup. A corrected UTF8 cluster with the established
100-connection cap passed; neither attempt touched production.

Shared-schema preflight is read-only and compatible: PostgreSQL 16.15, eight
existing migrations through 0005, four assignments, eleven ledger events, six
CME monitor events, schema owner `riverview_core`; CME and dashboard are active.
The event processor was observed inactive and was not modified. A protected
custom-format backup was created at
`/var/lib/postgresql/riverview-backup.m32-20261011T035934Z.ttrGjJUx/riverview.dump`
(SHA-256 `129a405b72e20f5b0a736e8f02965da33fab6943dada52bac867a400c1466519`).
The archive listed and restored successfully to a unique disposable database;
pre/post row counts matched (4 assignments, 11 events, 8 migrations, 6 CME
events), and only that disposable restore database was removed. Migration 0006
remains unapplied to `riverview_dev`; no service or shared row was changed.
Next: verify the migration under the existing database role on a restored clone,
commit/build the root-owned release, then apply only after the exact preflight
has passed and commission the dedicated dispatcher/dashboard integration.

## 2026-10-11 UTC — RV-OPS-COOKBOOK-001 / consolidated operations guide

Checkout outcome: the complete PostgreSQL-backed suite passed 118 tests with zero skips on a disposable 16.15 cluster; graph synchronization passed 10 workflows / 196 nodes; revision audit passed; GitHub CI passed for `9f752a7`; and live Firefox confirmed the operational guide, all 16 component-doc links, healthy actual PostgreSQL/CME projection, completed assignment with independent verification, and no browser errors. The dashboard-only deployment at `9f752a7` is active while PostgreSQL, CME, event processor, and SSH remain active. The live database was only queried read-only.

Corrective experiments retained: (1) a no-`PYTHONPATH` invocation failed import; (2) the first disposable PostgreSQL socket was inaccessible because of path/socket group mismatch; (3) after private socket access was corrected, the harness role `admin1` was absent. The isolated cluster was corrected with an owner-only parent directory, local socket mode, and test-only superuser role; final full suite passed. A targeted HTML check also expected an un-attributed `<h1>`; the renderer emits a safe heading ID, so the assertion was corrected. A live doc-link check found the Markdown parser removed one trailing target character; RV-OPS-COOKBOOK-001 fixed and regression-tested it. No live DB or unrelated service was altered.

## 2026-10-11 UTC — RV-OPS-COOKBOOK-001 / consolidated operations guide

Decision: publish one dashboard-readable operational entry point while keeping
component cookbooks authoritative for their contracts. Commands were checked
against the live Camrui units, actual service boundaries, source migrations,
existing M1.2/M1.3/M2.4 commissioning evidence, and worker/scheduler contracts.
The guide distinguishes deployed PostgreSQL/event processor/CME/dashboard from
library-only scheduler/worker code, documents only read-only SQL in diagnostics,
and separates controlled backup/restore/migration actions from service restarts.
Static dashboard links and route/render tests were added. No service, database,
credential, migration, or assignment state was changed. Next: run the targeted
dashboard tests, graph/revision checks, then begin M3.2 requirements/design.

## 2026-10-11 UTC — RV-M3.1-ACCEPTANCE / scoped Steward acceptance

The Steward accepted the scoped M3.1 technical implementation based on the
commissioning record, passing CI, live worker/verifier evidence and the external
Windows dashboard snapshot. This records acceptance only for the scoped
technical implementation; it does not close the component Definition of Done,
waive the new-view Windows recheck or full autonomy/Issue #13 obligations, or
authorize merging PR #16. The roadmap now advances to M3.2 durable notification
and decision requests. PR #16 remains open/draft; its discussion records this
decision. Evidence and deployed provenance remain unchanged.

## 2026-10-10 UTC — RV-M3.1-004 / deployed graph and documentation browser verification

The first browser run exposed a missing `}` in the graph viewer's SVG class
interpolation; the JavaScript asset did not parse, so the view stayed on its
loading placeholder while the existing HTTP tests passed. Preserved the 1.0.0
predecessor of `workflow.js`, incremented it to 1.0.1, corrected the expression,
committed `008d942ea57116b0fbdead771c201d3f99305482`, built and verified its
package (SHA-256 `e3211717073e2965ce3db0e2eb1e291acd24d8f56415324f7c6749af87f7d681`),
and installed a new immutable release. Only the dashboard service was
restarted. Firefox 156.0.1 then showed the live graph, safe formatted cookbook,
healthy projection/CME, six attention records, and completed worker assignment
with its independent verification; browser errors were zero. The graph API's
11 edges comprised 10 local rendered edges and one cross-workflow jump edge
whose stable target is exposed through its jump node/navigation control. Position
remained explicitly unknown because the ledger has no node identity.

Added `scripts/verify_status_dashboard_browser.py` as a reproducible read-only
Camrui check. Local UI navigation handler measurements were 114/152/220/64 ms
for Assignments/Activity/Overview/Workflows on one run; these are not full paint
or refresh latency benchmarks. The complete suite against an isolated socket-
only PostgreSQL 16 cluster passed 118 tests, zero skipped. Evidence (including
attested prior Windows observation, live assignment data, screenshots, isolated
suite logs, and deployment check) is in
`evidence/checkouts/M3.1-DASHBOARD-COMPLETION/20261010T231800Z-ada58c2/`.
The evidence sidecar is complete; graph synchronization passed for 10 workflows /
196 nodes; the local controlled-revision audit passed with zero issues. GitHub controlled-checkout runs 38095593247 and 38095595476 passed on `fc07a985c875c46066b627698a36393a1292ec1d`; the run details are retained in `github-ci.json`. The final evidence update is on PR #16. PR #16 remains draft and unmerged; formal Steward acceptance has not been claimed. The external Windows observation
predates the new graph/cookbook views, so those new views have local browser
verification but no post-change external Windows review.

## 2026-10-10 UTC — RV-M3.1-003 / dashboard usability and live worker proof

Resumed the M3.1 branch at `ada58c221f086b6b31bc029f4d9c123d56c76aae`. Read
Steward PR comments 6103058810 and 6103101551, Issue #13, roadmap, graph registry,
and active Component DoD. Recorded the Steward's post-migration Windows-over-SSH
observation as an attested summary; the original downloadable snapshot was not
available in the repository, so no raw capture was reconstructed.

Created one new scoped assignment without touching the three original M1.3
assignments. A registered PostgreSQL worker executed `deterministic.sha256.v1`
through `ContinuousWorker`, persisted a successful result artifact, and a distinct
verifier process independently accepted all criteria. Assignment completed at
version 5; commissioning workers were disabled and credentials removed. Evidence
is `evidence/checkouts/M3.1-DASHBOARD-COMPLETION/20261010T231800Z-ada58c2/`.

Implemented controlled Markdown-to-HTML rendering for component diagnostics and
a read-only SVG viewer that reads the canonical process graph registry. No browser
commands were added; node-level live highlighting remains unknown because the
ledger does not store canonical graph node identities. Process-graph validation
passes at 10 workflows / 196 nodes and the full isolated PostgreSQL suite passes
118/118 with zero skips. The revision audit passes against the established
baseline.

Issue #13 ownership is recorded: keep M3.1 read-only; M3.2 owns notifications;
M3.3 owns the repeatable first vertical slice; propose M3.4, after M4.1/M4.2 and
before M4.4, for governed commands and resident conversations. This is a proposal
pending Steward review, not an accepted roadmap change. PR #16 remains open/draft
and is not merged. The newly implemented dashboard UI still requires final
deployed browser verification before M3.1 technical readiness can be reported.

## 2026-10-10 UTC — RV-M3.1-002 / shared CME and dashboard commissioning

Actor: Codex. Resumed PR #16 branch `codex/m3.1-status-dashboard` at
`6d64b23becac008733790d51ebb51b95c07f61bf`; clean tree; PR #16 open/draft and
PR #15 left unmerged. Read the Steward's PR #16 instruction (comment 6102785527).
It confirmed prior Windows-over-SSH access and a live snapshot but explicitly
said its JSON file was not in the repository.

Diagnosed repeated `/api/v1/attention` 503s from the route translating the
projection's valid `not_initialized` state to an HTTP failure while the client
polled every five seconds. Added truthful HTTP 200 domain-state handling,
optional-relation polling suppression, and regression tests. Added a separate
systemd CME unit/launcher using protected `LoadCredential`, validated
non-root runtime identity, private mode-0600 pgpass copy, and the existing CME
monitor only. Added service contract tests, operator guidance, and graph nodes.

Took and validated a root-only custom PostgreSQL backup; a restore drill into a
disposable database applied the full dependency migration chain and preserved
3 assignments/6 events. Applied the same chain to shared `riverview_dev` as
`riverview_core`; reruns were empty and pre-existing rows remained 3/6. Deployed
the full-SHA commit `702f5db3f03669427a3625425eca04c023a0754c` to a root-owned
dashboard release and installed only `riverview-cme-monitor.service`. The live
monitor observed 3 stale READY assignments, 0 workers and 0 verification rows,
and persisted 3 deduplicated stall alerts without mutating assignment states or
institution events. Both graceful restart and actual SIGKILL/systemd recovery
created new healthy instances with alert IDs unchanged. Dashboard, event
processor, PostgreSQL and SSH stayed active. M1.1 baseline probe still reports
ready.

Firefox 156.0.1 exercised the live post-migration dashboard and client snapshot;
6 tab transitions measured 5–46 ms (median 11.5 ms), snapshot size was 8,611
bytes, redaction flags excluded credentials/private payloads/conversations, and
client UI errors were zero. The final isolated PostgreSQL suite passed 115/115
with zero skips, including both HTTP statuses for missing optional relations vs.
real projection failures; it removed all test schemas and stopped its private cluster.
Graph validation passed at 10 workflows/188 nodes; systemd unit validation and
controlled revision audit passed. The actual database state has no live worker,
so unrelated live assignment progress cannot be evidenced without changing
shared work; existing isolated PostgreSQL tests verify concurrent independent
claim/progress. Current source has no transferred external post-migration
Windows snapshot; no formal component acceptance or merge is claimed. See
`evidence/checkouts/M3.1-CME-LIVE/20261010T223049Z-702f5db/`.

## 2026-10-10 UTC — RV-M1.1-001 / RUNTIME-BASELINE

Actor: Codex. Repository baseline: ppow1/Riverview-, branch work,
`7dd9d472ad3c44ea71f2914392dd2696943c943b`, initially clean. Loaded full campaign,
roadmap, AI hints, lifecycle/records/DoD and all checked-in architecture/component
and privacy contracts. Issue #1 API retrieval denied by the egress proxy; browser
path returned 404, not proof that issue does not exist. Git read authentication
works. No issue text has been claimed as read.

Decision: follow checked-in M1.1 assignment and the user's supplied Camrui
configuration; introduce only new revision-1.0.0 files. No controlled predecessor
is overwritten; baseline tracked-file hashes are compared before final handoff.
Deployment helpers preserve exact existing unit bytes/checksum and release link
before replacement; rollback remains live NOT VERIFIED.

Existing database readiness evidence is reused. Remote development checkout
`/home/admin1/riverview-core` remains untouched; root-owned immutable runtime
releases under /opt avoid letting an unprivileged service modify its own code.
Use OS riverview identity distinct from DB riverview_core, systemd credential
delivery, read-only connection/schema diagnostics and freshness-aware consumers.
The request-driven baseline check does not weaken persistent execution or CME.

Experiment: normal cloud SSH stopped at unsafe installed system SSH configuration.
An isolated `ssh -F /dev/null` check with strict host-key checking and BatchMode
then returned connection refused to admin1@192.168.1.155:22. No remote operation
ran. User directed continuation via a Windows-transferable package; no credentials
were requested in chat. Camrui live tests remain NOT VERIFIED.

Development tests exercise simulated DB contracts, credential/identity failures,
stale/unavailable observers, package bytes/checksums and acceptance failure
retention. They do not prove PostgreSQL TCP authentication or systemd credential
delivery on Camrui. Direct systemd template verification failed solely because
the deployment interpreter path is absent locally; a temporary path substitution
is used for structural validation and reported distinctly.

Next: build exact committed package, provide evidence and PR when API access
permits. Execute Camrui commissioning via existing Windows SSH, capture outcomes,
resolve dependent DoD/Steward acceptance; keep roadmap cursor at M1.1.

## 2026-10-10 UTC — RV-M1.1-001 / resolved GitHub access and delivery

Append-only correction to the initial blocker: GitHub API access subsequently
worked. Issue #1 was read in full and matches the scoped implementation and
Steward sequencing. Commit f76507801c7f438ad50f8b507ca5e49db9556a4b was pushed
to codex/m1.1-runtime-commissioning, and draft PR #2 was created and confirmed:
https://github.com/ppow1/Riverview-/pull/2. No merge or deployment was performed.
The first committed package extracted cleanly, all 50 manifest checksums passed,
and both extracted shell scripts passed syntax checks. Documentation updates
record resolved access and preserve exact predecessor bytes/hashes in docs/history
and M1.1_REVISION_RECORD.md before incrementing each file to 1.0.1. Rebuild the
final package from the updated committed PR head; SOURCE_COMMIT is authoritative.
Camrui commissioning, credential delivery and rollback remain NOT VERIFIED.

## 2026-10-10 UTC — RV-M1.1-002 / Windows archive repair

Read PR comment 6091930352: actual installation failed at set -eu, exit 2,
following successful SSH/sudo/commit/manifest checks; no acceptance ran. Original
Windows archive is not available in cloud (user confirmed), so do not claim its
bytes were inspected. Executed preserved old builder under core.autocrlf=true:
both packaged shell files acquire CRLF while their committed blobs are LF.
Linux /bin/sh executing line 15 reproduces the exact Illegal option error.
Manifest still passes because it hashes converted bytes. This demonstrates the
packaging defect independently of any conjectured transfer problem.

Decision: read immutable Git blob bytes in one cat-file batch, add LF Git
attributes for deployment files, reject unsafe shell bytes before output, and
provide read-only archive-byte verifier. Keep install/rollback source unchanged;
test actual tarball bytes, manifest agreement, Linux syntax and guarded execution
for both. Preserve predecessors before all revisions; retain failed attempt and
old builder as executable regression fixture. New uniquely named Windows archive
and fresh staging preserve failed artifacts. No manual host edits or database
changes. M1.1 remains NOT DONE, live retry and Steward acceptance pending.


## 2026-10-10 UTC — RV-M1.1-003 / current checkout verification

Actor: Codex. Reused the existing M1.1 commissioning branch at `892b4893a584bd5a6aefbcac7e73bedbc5f53314`; branch baseline was clean. Verified Ubuntu 24.04.3 and PostgreSQL 16.15 are present and the local cluster is online. The full suite passed with the documented `PYTHONPATH=src` (36 tests, 3 PostgreSQL integration skips, 0 failures); both deployment shell scripts passed `sh -n`. The initial suite invocation omitted `PYTHONPATH` and failed one import; corrected invocation passed. Exact host evidence is retained in `evidence/checkouts/RUNTIME-BASELINE/20261010T034142Z-892b489/checkout.md`.

The runtime probe truthfully reported `IDENTITY_MISSING`. The protected runtime paths and OS identity are absent on this execution host. `camrui` did not resolve; strict SSH to the documented IP stopped because its host key is not known. Local noninteractive sudo is unavailable, and local socket login as `admin1` is rejected because that database role does not exist. No remote/privileged operation, schema change, credential access/reset, or deployment ran. M1.1 remains BLOCKED pending verified host identity, trusted host-key/access path, and authorized Camrui terminal commissioning. Existing database readiness evidence is not upgraded by this run. Steward acceptance and M1.2 remain pending. Exact predecessor preservation is recorded in `M1.1-003_REVISION_RECORD.md`.


## 2026-10-10 UTC — RV-M1.1-004 / local Camrui execution review

Actor: Codex. Resumed at `6fc346e78198e6ce76642927f7edb9f9245341f2` on `codex/m1.1-runtime-commissioning`. The Steward confirms this process is running directly on Camrui; the reported OS hostname is `admin1-Default-string`. Ubuntu 24.04.3 and PostgreSQL 16.15 cluster `16/main` are present and PostgreSQL is accepting local connections.

Reviewed the roadmap, campaign, runtime contract, installer, acceptance collector and cookbook. Roadmap M1.1 requires a reproducible database/schema check on Camrui; neither it nor the campaign makes SSH a gate. The campaign asks for a consolidated SSH runner only if needed. The Windows alias is only a transfer/remote-observer convenience. Local package build, verified staging, local installer and local systemd acceptance collector are the correct path on the target host. SSH remains strict-host-key verified if a separate remote observer is used.

Read-only checks: `riverview` account and `/etc/riverview`, `/etc/riverview/pgpass`, `/var/lib/riverview`, `/opt/riverview-core` are absent; the runtime unit is `LoadState=not-found`; no `PGPASSFILE`, `RIVERVIEW_PG_DSN` or PostgreSQL test DSN is set. Read-only TCP login as `riverview_core` failed because no password was supplied; no credential file was inspected. No DB objects or privileged configuration were changed. Full local test suite is eligible because the PostgreSQL test DSN is unset and integration tests skip before creating temporary schemas.

Decision: document local build/install/acceptance commands and privilege effects. Do not run `sudo sh <verified-stage>/deploy/install_baseline.sh`: installer requires root to create/use service identity and write `/opt`, `/etc/riverview`, `/var/lib/riverview`, and systemd configuration, and may prompt to provision an absent secure passfile. User has not authorized privileged configuration changes. Do not run the root-only acceptance collector until authorized installation exists. Exact review and test evidence is retained under the RV-M1.1-004 checkout record. M1.1 is still blocked on authorized commissioning and database authentication; local SSH resolution/key failures are not blockers. Steward acceptance remains pending; do not advance to M1.2. Predecessors and checksums are in `M1.1-004_REVISION_RECORD.md`.

## 2026-10-10 UTC — RV-M1.1-006 / disposable PostgreSQL integration verification

Actor: Codex. Source commit `b459bf1691b9d92811185b0a5b7013a28ac40752`, branch
`codex/m1.1-runtime-commissioning`, target host Camrui (`admin1-Default-string`,
Ubuntu 24.04.3). To execute the three integration tests previously skipped for
lack of a test DSN, initialized a disposable PostgreSQL 16.15 cluster under
`/tmp/rv-pgtest.uEU8h2I0`, with trust authentication confined to its private Unix
socket and no TCP listeners. The installed `16/main` cluster was not used or
modified.

Executed `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN="host=/tmp/rv-pgtest.uEU8h2I0/socket port=5432 dbname=postgres user=admin1" python3 -m unittest discover -s tests -v`.
Result: 36 tests passed, 0 failures, 0 skipped; all three `test_postgres_ledger`
cases executed. After the run, restarted only the disposable cluster and queried
`server_version`, `listen_addresses`, and remaining `rvtest_%` schemas; result
`16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)||0`. The server was then stopped. Raw
initialization, test, server, cleanup, and shutdown logs are retained in the linked
checkout evidence directory. No credentials were logged.

This closes the skipped-test gap only. It does not verify authentication,
permissions or schema behavior against the installed service cluster, systemd
service installation, rollback, or external observation. M1.1 remains IN
PROGRESS/BLOCKED on the local privileged commissioning step and access to the
existing `riverview_core` database credential, then independent Steward acceptance.
No M1.2 work is started. Journal predecessor bytes were preserved and verified;
`M1.1-006_REVISION_RECORD.md` records the revision change.

## 2026-10-10 UTC — RV-M1.1-007 / hidden credential TTY and partial install repair

Actor: Codex on Camrui. Source commit `0cab252eb4aae6736433d71e154ea1e26b1426c5`,
branch `codex/m1.1-runtime-commissioning`. User reported the authorized M1.1
installer passed package verification and dependency installation, then failed in
`scripts/provision_pgpass.py` at `open("/dev/tty", "r+")` with
`io.UnsupportedOperation: File or stream is not seekable`. Reproduced this exact
failure locally in a pseudo-terminal with `open("/dev/tty", "r+")`; Python
3.12.3 raises the same exception.

Read-only host inspection found the `riverview` nologin account, root-owned
`/etc/riverview` mode 0700, and root-owned release directory
`/opt/riverview/releases/b15b093642f65f6de36c1b977571ae2b79f04850` mode 0700.
`/etc/riverview/pgpass`, `/var/lib/riverview`, `/opt/riverview-core`, and the
systemd unit are absent. PostgreSQL 16/main is online. No credential contents
were read. This state is safely rerunnable: the installer reuses the account
and versioned release; provisioning fails before creating the passfile, state
directory, active link, unit, or rollback record. Inspection also found that
`cp -a` copied the private staging root's 0700 mode onto the release root,
blocking the service account from traversing the code.

Implementation: call `getpass.getpass()` without a caller-supplied TTY stream,
and convert `GetPassWarning` to an error to fail closed if hidden input is not
available. Add a pseudo-terminal regression test that generates a runtime-only
sentinel, confirms the input is returned, and verifies it is not echoed. On
rerun, require an existing release to be a real root-owned directory with
root-owned contents; normalize files to readable and directories to traversable
while removing group/other write permission. This repairs the retained partial
release without changing file bytes or ownership and refuses an unsafe release.
Update the component contract, cookbook and flowchart with retry/error behavior.

Verification: the first pseudo-terminal test iteration found the harness assumed LF-only terminal output; PTY canonical mode emitted CRLF. The assertion now normalizes captured line endings. The focused runtime suite passed (19 tests); the full suite against the isolated local PostgreSQL cluster passed (38 tests, 0 failures, 0 skips), including all three PostgreSQL ledger tests. The temporary test schemas were absent after cleanup (`16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)||0`); the test cluster was stopped. Test, cleanup and lifecycle logs are retained in the RV-M1.1-007 checkout evidence.

Next: commit the corrected source and records, build and verify a new uniquely named package from that commit, then retry commissioning through the corrected package. The failed staged package remains untouched. M1.1 remains IN PROGRESS/BLOCKED pending live acceptance evidence and Steward acceptance; no M1.2 or later dependent milestone is claimed complete.

## 2026-10-10 UTC — RV-M1.1-008 / deployed storage-path failure diagnosis

Actor: Codex on Camrui (`admin1-Default-string`, Ubuntu 24.04.3). The active unit
is loaded from `/etc/systemd/system/riverview-baseline.service`, runs as static
`riverview` (UID 997/GID 984), sets `StateDirectory=riverview` and mode 0700,
`DynamicUser=no`, `ProtectSystem=strict`, `ProtectHome=yes`, and `PrivateTmp=yes`.
The active release source is commit `3d7e58fc19ae38b6fd378fd0f0421ebb36fdb266`;
the installed `runtime_baseline.py` SHA-256 matches this checkout's source.
Host-context checks show `/var/lib/riverview` is a non-symlink directory owned
997:984 with mode 0700; `Path.absolute()` and `Path.resolve()` both produce the
same path. `/opt/riverview-core` is a symlink to the versioned release, but the
storage check receives the fixed `/var/lib/riverview` default, so that symlink
is not itself evidence of the storage failure.

The installed sanitized report cannot be read by `admin1`; the unit journal
contains only status 2. `sudo -n -l` reports that a password is required, so no
service-context rerun or privileged state/configuration change was performed.
The precise source condition is one of `path.resolve() != path.absolute()`,
non-directory `lstat` type, or owner UID mismatch. Host-context evidence rules
out the latter two and the resolution mismatch on the host, but not within the
unit's mount namespace. The change adds safe `path_failure_reason` diagnostics
and tests for those predicates plus the deployed unit/storage contract; it does
not relax path validation. Live root-authorized confirmation and repair remain
open. No credential or database content was read; no services/configuration
were modified.

Verification: the focused runtime-baseline suite passed 22 tests. The full
checkout suite passed 41 tests: 38 passed, 3 PostgreSQL integration tests
skipped because `RIVERVIEW_TEST_PG_DSN` is unset. The three integration tests
were previously executed successfully against a disposable local PostgreSQL
cluster under RV-M1.1-006; this source-only path-diagnostic change does not
affect that database code. `sudo -n -l` confirmed no passwordless privilege, so
the protected live report and the new service-context predicate have not been
verified. No installation or service restart was attempted.

Next: record and commit this diagnostic change, build and verify a uniquely
named package from that commit, then arrange one authorized package install
with its scoped service start. Compare the service-context reason and correct
only a demonstrated mismatch. M1.1 and all dependent roadmap milestones remain
blocked pending root-cause repair, successful live acceptance and Steward
disposition.

Contract traceability review for RV-M1.1-008 added `path_failure_reason` to the
component specification (Rev 1.0.4). The initial diagnostic package at source
commit `e6b46c362326900c09f9e5c59d27d18137004847` predates this specification
update and is retained unchanged; it is superseded for deployment by a newly
built package from the next committed source. No system installation has run.

Privilege-path recheck during goal continuation: `sudo -n -l` reports a
password is required; `systemctl --no-ask-password start
riverview-baseline.service` returns “Interactive authentication required.” No
passwordless sudo or polkit route exists for the needed deployment. The
commit-addressed diagnostic package and exact local install command are ready;
an authorized interactive sudo session is the remaining external condition.
Roadmap M1.2 is sequenced after M1.1 acceptance, so there is no independent
numbered roadmap item to advance while M1.1 is blocked. Do not mark M1.1 DONE or
install the superseded `e6b46c3` package.

## 2026-10-10 UTC — RV-M1.1-009 / RUNTIME-BASELINE privileged path and UNSAFE_PATH

Actor: Codex on Camrui. The owner explicitly authorized root-level New
Riverview development operations; `sudo -n id` returned uid 0. Repository at
task intake was `3e60476` on `codex/m1.1-runtime-commissioning`, clean. The
deployed unit failed with `UNSAFE_PATH`, step `storage`, source `3d7e58f`.

Experiment: inspected the actual sanitized report, unit, host path metadata and
the deployed source predicate. `/var/lib/riverview` passed its service-context
private-state check. A transient unit reproducing the deployed systemd sandbox
showed PID 1 creates `CREDENTIALS_DIRECTORY` as root:root 0550 and `pgpass` as
root:root 0440, both readable/traversable to `riverview`. The probe incorrectly
reused its runtime-owned-directory validator on this systemd-managed parent;
it emitted `UNSAFE_PATH` with a misleading storage step. This is an ownership
contract mismatch, not a symlink or state-directory defect. The correction
validates the fixed systemd credential location, no symlink traversal, root
ownership, exact non-writable delivery modes and effective service read access,
while retaining the stricter runtime ownership/mode checks on state.

Decision: introduce a root-owned fixed-operation broker. It admits only an
exact registered package ID, fixed service actions, sanitized report, acceptance
capture, or a constrained rollback record ID. Its root policy pins the archive
digest and Git source commit. It rejects arbitrary paths/commands, unsafe tar
members and mutable/incorrect release content; only the exact hash-verified
archive is extracted root-owned, then its fixed installer is invoked. New
release digests need an explicit root-policy update. No user checkout script is
run as root. Bootstrap, installation and recovery are within the user's explicit
Camrui authorization; no credentials were read or changed.

Verification: privilege/runtime focused suite currently passes 28 tests; a
fixed-command construction test was added afterward and is pending rerun. Full
checkout suite and root deployment remain pending. The installed service failure
was reproduced. Transient systemd checks confirmed path metadata without
printing passfile contents. Prior M1.1 completion evidence, PostgreSQL checks,
optional SSH status, rollback and Steward gates remain unchanged. Next: rerun
verification, commit, build the exact package, bootstrap the broker, redeploy,
verify live database acceptance and rollback, then evaluate full M1.1 DoD.
Status remains IN PROGRESS; Steward acceptance and later live dashboard/autonomy
gates remain required.

## 2026-10-10 UTC — RV-M1.1-010 / libpq passfile mode mismatch

Live deployment of source commit a25aa71 corrected the prior misleading
UNSAFE_PATH report; the service then failed during database authentication.
The journal showed libpq rejected `/run/credentials/riverview-baseline.service/pgpass`
because systemd correctly delivered a root-owned mode-0440 credential. This is
not a reason to loosen the systemd source contract: libpq requires a passfile
mode of 0600 or stricter.

Implementation places an ephemeral, mode-0700 `RuntimeDirectory` under systemd
control. The unprivileged probe validates the fixed root-owned systemd source,
copies through O_NOFOLLOW and O_EXCL descriptors to a service-owned mode-0600
passfile, validates the copy, and passes only the copy to Psycopg. Existing
destination/symlink paths fail closed. systemd cleans the directory on service
stop. No credential bytes are logged, exposed in reports, or placed in source.

Task RV-M1.1-010 predecessor backups for runtime source, unit, tests, component
specification, cookbook, flowchart and this journal are listed in
`.riverview-backups/manifest.jsonl`; files were verified before edits. Regression
coverage checks the root-owned source contract, installed unit paths, exclusive
copy, owner/mode and symlink refusal. The focused runtime suite passed (26 tests).
The full suite passed (52 tests, zero failures/skips) against a temporary
socket-only PostgreSQL cluster, with zero leftover test schemas; cluster/data
were removed. At this checkpoint M1.1-010 remained IN PROGRESS pending package
and live deployment verification.

Checkout was repeated against commit b40c77fdca48c556af9d25a8cd25e7ca192b9748:
52 tests passed, including PostgreSQL integration; no schemas remained. The
exact package SHA-256 is
`bedf5f94e0ae0cb107fb7d2ce69eab37f8eb9cc709b0fa05d0933fe79e7025ab`, and
manifest/shell verification passed. Evidence is retained in
`evidence/checkouts/RUNTIME-BASELINE/20261010T1450Z-b40c77f/`. The installed
root-owned broker remains constrained to its original `initial-m11` package;
updating its allowlist requires authenticated sudo, which is not available
noninteractively in this execution context. Live deployment and rollback remain
pending that one bootstrap action.
The current package registry is still pinned to a25aa71. Steward acceptance
remains pending; M1.2 is not eligible.

## 2026-10-10 UTC — RV-M1.1-009 / predeployment checkout closure

After adding regression coverage for the four expected Python virtualenv
symlinks, the final checkout run executed 50 tests: 50 passed, zero failed,
zero skipped. The three PostgreSQL ledger integration tests ran against a fresh
PostgreSQL 16 cluster under a mode-0700 temporary directory, Unix socket only,
no TCP listener. All generated rvtest schemas were dropped; post-run count was
0; the temporary cluster was stopped and its directory removed. The live
commissioned PostgreSQL cluster and riverview database were not used.

Targeted runtime/broker tests: 31 passed; py_compile and git diff --check passed.
The changed-file revision subset passed: six existing controlled files each
incremented monotonically with an independently verified predecessor backup;
three new controlled files have revision 1.0.0. The repository-wide validator
still reports 30 unchanged legacy files with missing revisions, including
.gitignore, the unversioned Engineering Records Standard, and prior generated
evidence; it reports no changed-file revision or backup defect. Preserve that
FAIL as a pre-existing repository governance gap rather than modifying unrelated
files or claiming global checkout compliance.

Next: commit this source/docs/test increment, build and inspect its exact package,
bootstrap the hash-pinned helper and narrow the existing project sudoers rule,
then deploy and verify fresh live baseline/acceptance plus recovery. The package
is not yet approved or installed; M1.1 remains IN PROGRESS.

## 2026-10-10 UTC — RV-M1.1-011 / privilege broker retirement and PostgreSQL inet diagnosis

The owner restored unrestricted passwordless sudo. Verified `sudo -n id` and a
separate root operation returned UID 0; `sudo -n -l` confirmed `(ALL : ALL)
NOPASSWD: ALL`. `visudo -c` parsed `/etc/sudoers.d/90-riverview-codex` successfully.
This authorization file remains intact.

Before removing active broker state, preserved checksummed copies of the
root-owned helper, private policy and package registry under
`/var/backups/riverview-privctl-retired-20261010T150152068992Z`. Removed their
active copies; no broker-specific sudoers rule remained, and root access still
passed independent verification. Historical task records, predecessor copies,
and rollback records are retained.

Deployed the exact verified b40c77f package into its immutable release. The
private systemd passfile copy succeeded. A live read-only DB query showed the
identity check failed because `inet_server_addr()::text` yields
`127.0.0.1/32`; the configured endpoint and database role were correct. RV-M1.1-011
changes that projection to `host(inet_server_addr())` and adds regression coverage.
M1.1 remains IN PROGRESS pending corrected deployment, fresh acceptance evidence,
recovery verification, and Steward decision. M1.2 remains gated.


Correction to the superseded RV-M1.1-010 next-step note above: the owner has
restored unrestricted passwordless Camrui administration. No privilege broker
bootstrap or sudoers narrowing is authorized or required. RV-M1.1-011 retires
the broker and proceeds using the owner-authorized administrator. The full
source suite was executed with the documented `PYTHONPATH=src` and an isolated
socket-only PostgreSQL cluster: 45 tests passed, including all PostgreSQL ledger
integration tests; no `rvtest_%` schemas remained. The live baseline defect is
addressed by querying `host(inet_server_addr())`; package build/deployment and
live recovery evidence remain pending at this checkpoint.


RV-M1.1-011 live verification completed from package source commit
`a2b94e24715a670262859e1af31a0ea417ed37cb`. The package digest and source
manifest passed. Full suite passed 45/45 against an isolated socket-only
PostgreSQL cluster; installer suite passed 45 with its three DSN-dependent tests
skipped, which the separate full run covers. Live read-only PostgreSQL reported
`riverview_core` / `riverview` / `127.0.0.1` and transaction read-only `on`.
The systemd service ran as `riverview`, result success/exit 0, and returned a
fresh baseline-ready report for `riverview_dev`. Collector evidence includes two
distinct successful observations and explicitly remains `PENDING_STEWARD`.
Service restart passed. Rollback checksum and restoration passed, the known b40
predessor reproduced its database identity defect, and rerunning the corrected
package restored a2b94e2 readiness. No DB object or credential was modified.
The installed broker, policy and registry are absent; unrestricted sudo and
visudo checks still pass. Technical M1.1 acceptance is PASS; formal Steward
acceptance/sequencing remains pending and M1.2 is not started.


Final RV-M1.1-011 release was rebuilt from committed source
`64e8f14ad6d71102a864755739a1c8a61506235c` (archive SHA-256
`0635519b4b3de40b5b10e6935fc370e6276ba685046dfdbc73c86e7f8a4c28a8`). This
package includes the broker-retirement clarification in the installed component
contract. Deployment to immutable release `64e8f14ad6d71102a864755739a1c8a61506235c`
returned systemd success/exit 0. The live report is current and ready, collector
again produced two distinct ready observations with `PENDING_STEWARD`, and the
active broker paths remain absent. Evidence: `evidence/checkouts/RUNTIME-BASELINE/
20261010T1511Z-64e8f14/`.


RV-ENG-REV-003 audit found 58 `missing_revision` checkout messages. Fifty-six
were false negatives from the checker not consuming the evidence sidecar formats
(`artifacts` and legacy `files` mappings); the two actual omissions were `.gitignore`
and file-level metadata on the Rev 1.0 Engineering Records Standard. All existing
evidence sidecar entries had matching checksum, size, and revision. Work is correcting
the checker and baseline metadata with preserved predecessors.

M1.1 technical acceptance remains PASS, with Steward acceptance and later DoD
items outstanding. The current directive permits M1.2 schema/migration design,
implementation, and isolated tests while that gate is pending; shared development
schema migration and M1.2 acceptance remain gated.

2026-10-10 15:26 UTC — RV-ENG-REV-003 / ENG-REVISION-CONTROL: Current baseline
revision checker reports zero issues across 149 tracked baseline files. Its
original 58 findings were 56 sidecar-versioned evidence files and two actual
file-level metadata omissions. Regression tests cover both sidecar formats,
tampering and text evidence headers. M1.2 isolated engineering began under
RV-M1.2-001 per the current owner directive. A checksum-pinned migration runner
and event-contract-aligned PostgreSQL schema were implemented; migration,
transaction rollback, transition, idempotency, causality and reconnect tests
passed on an isolated PostgreSQL 16 UTF-8 cluster. Initial row-factory and
SQL_ASCII test-harness failures were repaired and retained in the task record.
The commissioned `riverview_dev` schema and `riverview-baseline.service` were not
modified. M1.1 scoped Steward acceptance, M1.2 shared-schema deployment and
acceptance, and M1.3 dependencies remain pending; no formal acceptance is claimed.

2026-10-10 15:29 UTC — RV-M1.2-001 / POSTGRES-LEDGER: Commit
`27a8c555501588dd0fd2a5d488018ad0c295199a` implements the versioned migration
runner and contract-aligned assignment/event schema. The branch was pushed
fast-forward to the existing PR #2 branch; `git ls-remote` and `gh pr view` both
reported the exact commit as remote head. A post-commit isolated PostgreSQL 16
UTF-8 run passed all 53 tests (6 PostgreSQL integration tests, 15 revision
control tests, no skips), then stopped and removed the temporary cluster. Output
and failure-correction history are retained under
`evidence/checkouts/POSTGRES-LEDGER/20261010T1529Z-27a8c55/`. No M1.2 migration
was applied to `riverview_dev`; formal M1.1/M1.2 acceptance remains with the
Steward.

2026-10-10 15:32 UTC — RV-ENG-REV-004 / ENG-REVISION-CONTROL: The Development
Lifecycle Standard requires repository checkout enforcement. PR #2 had no
reported checks. Added a read-only GitHub Actions workflow to run the full suite
against an ephemeral PostgreSQL 16 test service and execute the revision checker
against the preserved baseline. No branch protection or approval settings were
changed. Local YAML parse and baseline revision check passed; external Actions
execution was pending at this entry's timestamp.

2026-10-10 15:36 UTC — RV-ENG-REV-004 / ENG-REVISION-CONTROL: GitHub Actions
workflow is verified on final commit `e2d7fee8baa137a6ebf16466a5a1354d04fc0c74`.
The push run 38064245175 and PR run 38064247105 both passed all 53 tests with
zero skips, including all PostgreSQL tests, and the revision checker returned
zero issues. Initial successful runs exposed Node 20 and upcoming runner-image
warnings; the workflow was revised to Node 24 action majors and Ubuntu 24.04,
then rerun successfully. Logs, URLs, checksums, and run metadata are in
`evidence/checkouts/ENG-REVISION-CONTROL/20261010T1536Z-e2d7fee/`. PR #2 remains
open; no merge or branch protection change was performed. CI task is DONE.
M1.1 Steward acceptance and M1.2 shared-schema/acceptance gates remain pending.

## 2026-10-10 UTC — RV-GOV-001 / Steward authority, M1.1–M1.2 checkpoint and graph standard

Actor: Codex recording the project owner's directive as Riverview's Steward.
Decision: project owner is the Steward; no separate Steward approval mechanism
is required. Preserve the proposed/pending-acceptance status of the Development
Lifecycle Standard; this authority decision does not falsely mark that standard
accepted. The Component Definition of Done Rev 1.4 is updated with the Steward's
explicit universal process graph requirement.

M1.1 scoped technical commissioning is accepted by the Steward against verified
Camrui deployed commit `64e8f14ad6d71102a864755739a1c8a61506235c`. The full
component DoD remains NOT DONE, with M3.1 live dashboard, autonomous processor,
independent verification and later obligations open. Historical acceptance
collector JSON retains its original PENDING_STEWARD value and is linked, not
rewritten.

M1.2 isolated technical engineering is verified on the six PostgreSQL integration
tests, 53/53 suite with zero skips, passing CI, and clean revision audit. PR #2
was synchronized at `29b085b0e95d789914f5f33c8e6ea8dedc959654`; both visible
controlled-checkout runs passed, merge commit was enabled in repository metadata,
and the PR was merged as `3fd6fd291d27157697752e7fd02896e514c7388a`.

The explicitly authorized migration passed preflight: Camrui Ubuntu 24.04.3,
PostgreSQL 16.15, database `riverview`, role/schema owner `riverview_core`,
required USAGE/CREATE, empty `riverview_dev`, and compatible migration source.
Full database backup `/var/backups/riverview/M1.2-20261010T161521Z/riverview-before-m12.dump`
is root:root 0600 in root:root 0700 directory; SHA-256
`e0f3d6126c7f10cc584b4844637904d7a28dc8ad89886f171b372fe25edb4491`. Archive
listing and a full restore into a disposable database passed; temporary restore
database and copy were removed. Migration 0001 was applied, checksum recorded,
rerun no-op verified, and the empty PostgresLedger connection passed. The M1.1
service remained success/exit 0 and freshly reported ready at deployed commit
64e8f14. No live assignment/event rows, credentials, system service definitions,
or M1.1 release bytes were changed. Exact evidence is in
`evidence/checkouts/POSTGRES-LEDGER/20261010T1615Z-3fd6fd2/checkout.md`.

Established RV-PROCESS-GRAPH Rev 1.0.0 before regenerating component views.
Canonical files cover M1.1 commissioning, M1.2 migrations and assignment
lifecycle, plus an explicitly planned M3.1 jump destination. Four graph records,
66 nodes and typed edges are validated; the two existing component Mermaid views
are regenerated from canonical JSON. Future diagnosis/evidence/escalation
extension points are documented but not implemented. M1.3 is the next eligible
milestone and begins as isolated engineering; no M1.2 or M1.3 full component DoD
claim is made.

Evidence qualification: an initial restore invocation as the postgres OS user
could not read the root-only backup; the exact backup was copied under a
postgres-owned 0600 temporary path, restored successfully, and the copy removed.
An initial post-migration read-only verification snippet used a nonexistent
context-manager interface; corrected to `close()` in `finally`, after which
ledger reads passed. These failed snippets did not modify the live target.

## 2026-10-10 UTC — RV-GRAPH-001 / process graph design and implementation

Design decision: workflow JSON files are canonical, with immutable node IDs of
the form `rv:<component>:<workflow>:<semantic-node>` and independent node and
graph revisions. Built-in and namespaced extension node/edge types are schema
validated. Runtime transitions are local/observed; prerequisites remain a
separate edge type. Typed cross-component jump targets must resolve in the
aggregate registry. `scripts/process_graph.py` validates every source/document/
evidence reference, uniqueness, graph/schema consistency and jump/edge rules,
then regenerates the aggregate JSON and Mermaid fences in the existing flow
documents. CI fails on invalid graphs or stale generated views. M1.1/M1.2 diagrams
and cookbook links are retained and mapped; M1.3 is the first native graph.

Verification is pending the complete test and CI run for this change. The graph
record reserves links for cookbook diagnostics, fault isolation, persistent
troubleshooting evidence, verification loops, variable pass limits, escalation
hierarchy and institutional learning without implementing that future system.

## 2026-10-10 UTC — RV-GRAPH-001 / verification and RV-M1.3-001 isolated start

Correction to the preceding pending-verification entry: the final complete local
suite passed **66 tests, 0 failures, 0 errors, 0 skips** on the Camrui development
host using a disposable PostgreSQL 16.15 cluster restricted to a Unix socket.
All temporary `rvtest_*` schemas were absent after the suite; the cluster was
stopped and removed. Graph validation and generated-view synchronization passed;
the final revision audit will be recorded with the commit/CI result. Detailed test
names/output are retained in
`evidence/checkouts/EVENT-PROCESSOR/20261010T1628Z-3fd6fd2/`.

M1.3 isolated engineering began after M1.2 shared-schema deployment verification.
The implemented consumer uses a durable cursor, ordered replay, idempotent
assignment progression, error retry, and advisory leadership. Thread-based
continuous and stop/restart tests passed. M1.3 remains IN PROGRESS because no
systemd unit with secure credential delivery has been installed or exercised;
there is no M1.3 live deployment/acceptance claim. The full component DoD remains
open.

PR #2 was merged after the visible branch checks passed and repository metadata
allowed merge commits. GitHub's branch-protection API returned 403 because the
private repository plan does not expose that endpoint; the merge itself was
accepted by GitHub with the PR in CLEAN/MERGEABLE state. This limitation is
recorded rather than interpreted as a failed check.


## 2026-10-10 UTC — RV-GRAPH-001 / final 67-test verification and live baseline preservation

After reducing the generated aggregate Mermaid to a compact workflow map with
typed jump/prerequisite links, graph checks passed 10/10. The final complete
repository suite passed **67 tests, 0 failures, 0 errors, 0 skips** on a fresh
disposable PostgreSQL 16.15 cluster. All unique `rvtest_*` schemas were removed,
the cluster stopped and deleted, and the exact suite output is in
`evidence/checkouts/EVENT-PROCESSOR/20261010T1628Z-3fd6fd2/`.

At `2026-10-10T16:30:18Z`, `sudo -n id` still returned root UID 0. A fresh
`riverview-baseline.service` run returned success/exit 0; its report was ready
with no blocker at deployed commit
`64e8f14ad6d71102a864755739a1c8a61506235c`. Read-only shared database checks
confirmed `riverview_dev` has only migration 0001 (checksum
`7f3580aacc057b977f8dd6f880584d1fed678488523b0d2ce6737c1107487492`), exactly
three M1.2 tables, zero assignment/event rows, and no M1.3 cursor table. M1.1
release/service and M1.2 data were not changed by isolated M1.3 verification.


## 2026-10-10 UTC — RV-GRAPH-001 / PR #4 CI verification

Commit `5be1484eee1ac23ca6f04d78aef659f200419139` was pushed to
`codex/m1.1-runtime-commissioning` and PR #4 opened against `main`. Both GitHub
Actions `controlled-checkout` runs passed: push run
[38068399375](https://github.com/ppow1/Riverview-/actions/runs/38068399375) and PR
run [38068402439](https://github.com/ppow1/Riverview-/actions/runs/38068402439).
The checks include the 67-test suite, process graph schema/synchronization, and
revision checkout. PR #4 is open; no merge is claimed. M1.3 remains IN PROGRESS
pending supervised service/credential deployment and operational verification.


## 2026-10-10 UTC — RV-M1.3-002 / controlled Camrui commissioning complete

PR #5 was merged at `9ca7cb189d1e1f57c69395303a9367fabd979ff5`; its push and pull-request controlled-checkout runs (38069688433, 38069691322) and post-merge main run (38069730995) passed. The exact merged tree passed 74 tests with zero failures, errors, or skips on isolated PostgreSQL 16.15. Package manifest/member/shell validation passed for SHA-256 `090d4d2965196db246b5f614d58e82cf692eb82216eea7d8f2c58acafb6d5750`.

Live M1.3 migration 0002 was applied after a verified backup and restore drill. The separate event processor service completed three unattended queued-to-ready transitions with causal event pairs through cursor 6; systemd restart resumed at cursor 2; deliberate database backend loss recovered to one leadership lock at cursor 4. The M1.3 rollback/redeployment was exercised; M1.1 remained ready on deployed commit `64e8f14`. Evidence: [`M1.3 Camrui checkout`](../../evidence/checkouts/EVENT-PROCESSOR/20261010T1700Z-9ca7cb1/checkout.md), [`runtime acceptance`](../../evidence/checkouts/EVENT-PROCESSOR/20261010T1700Z-9ca7cb1/runtime_acceptance.json).

M1.3 scoped technical commissioning is PASS; full component DoD remains OPEN. The roadmap cursor is now M1.4 isolated engineering; later dashboard, autonomy, external observability and project-wide obligations remain intact.
# 2026-10-10 UTC — RV-M2.3-001 / failure and restart recovery intake

Roadmap M2.3 requires forced process/worker interruption recovery without lost
assignments or blind duplicate external effects, with an auditable decision.
Inspection found that M2.1 persisted worker attempts and lease fencing, but a
`running` assignment with an expired lease was not reconciled; the existing
incomplete-attempt test inserted a row rather than terminating a worker. The
continuous adapter also invoked injected action code before writing an attempt,
so an external effect could precede durable evidence of the action boundary.

Decision: add a durable pre-action execution intent. The built-in deterministic
action is retry-safe; custom actions default to external-uncertain. Recovery
preserves a committed result, retries only explicit retry-safe work after fencing
its prior generation, and moves all other incomplete/legacy work to
`awaiting_steward`. The migration, state events, and recovery record are
transactional in the selected schema. Development is on a short-lived branch
from PR #10's pinned head, with no merge or rewrite of the PR #9/#10 stack.
Verification uses disposable `rvtest_*` schemas only. See
[`RV-M2.3-001`](M2.3-001_REVISION_RECORD.md) and the generated worker flow.

## 2026-10-10 UTC — RV-M2.3-001 / isolated recovery acceptance

At source commit `7ae8252469612920bd07dc84a6d65ef374aa8886`, the full Camrui
suite passed 89/89 with no skips on a private PostgreSQL 16.15 Unix-socket-only
cluster. Forced subprocess termination covered retry-safe intent, a committed
external test effect, and a committed result before assignment advancement.
Recovery requeued only retry-safe work at a newer lease generation, held
uncertain effects in `awaiting_steward` without replay, preserved durable output
for independent verification, and allowed unrelated assignment progress. The
independent verifier accepted preserved output and a later recovery pass left
the completed assignment terminal. Post-run inspection found zero remaining
test schemas; the temporary cluster was stopped and removed. Revision and graph
checks passed (10 workflows, 156 nodes). Evidence and corrected failed attempts
are retained in `evidence/checkouts/WORKER-ADAPTER/20261010T1917Z-7ae8252/`.

M2.3 roadmap technical criteria are PASS for isolated engineering only. This is
not live operational commissioning: M2.1/M2.2 remain unmerged on PRs #9/#10, no
M2.3 migration is in shared `riverview_dev`, and the full component DoD remains
open. The roadmap cursor advances to M2.4 CME monitoring service. No PR was
merged and no shared service/database was changed.

## 2026-10-10 UTC — RV-M2-BASELINE-001 / integrated M2.1–M2.3 baseline

Fetched `origin/main` and verified exact integration commit
`4f028a138c41665239bde2c11be65b0f841f02bf`, including PR #9, #10 and #12 merge
commits. Kept the prior clean M2.3 checkout available while testing a detached
worktree at `origin/main`. The complete isolated PostgreSQL 16.15 suite passed
89 tests with zero failures, errors, or skips. Post-run inspection found zero
`rvtest_*` schemas and the private Unix-socket cluster was stopped. Process graph
validation passed for 10 workflows/156 nodes; the revision audit passed with no
issues; GitHub's main CI run 38079898010 succeeded at the same source commit.
The v1.0.0 knowledge provider contract and mandatory Grace M4.4 requirements
remain intact. The exact run evidence is in
`evidence/checkouts/INTEGRATED-M2-BASELINE/20261010T194058Z-4f028a1/`.

Ancestry checks proved the PR #9, #10 and #12 source branches had zero commits
absent from main. Those exact three feature branches were deleted normally;
archive and historical branches were preserved. The original clean checkout was
fast-forwarded to integrated `main`, and M2.4 work began on a branch from it.

## 2026-10-10 UTC — RV-M2.4-001 / design and implementation intake

The M2.4 contract requires an always-on observer for progress, deadlines, stalls
and recovery requests; it does not give CME worker execution, HR, or resource
scheduling authority. The implementation keeps deadlines and attention history
in CME-owned tables, uses stable database event keys for restart-safe dedupe,
and reports missing worker heartbeats as unknown rather than healthy. CME emits
recovery requests as durable records only; M2.3 remains the recovery owner. The
monitor is designed to scan every nonterminal assignment without an assignment
blocking another. M2.4 remains under isolated engineering verification until the
checkout record and required gates are complete.

## 2026-10-10 UTC — RV-M2.4-001 / isolated technical acceptance

Commit `a44091bc32e82580dd8a3350e1ecfa47b0157b36` passed all 95 repository tests
with zero failures, errors, or skips on a private PostgreSQL 16.15 Unix-socket
cluster. The M2.4 subprocess restart test sent SIGKILL to a running monitor,
started a replacement, and verified a fresh instance identity with stable alert
event counts. A separate disposable-schema runtime probe captured one deadline
miss, one stalled running assignment, one expired-lease recovery request, a
stale worker health result, and an unrelated ready assignment claim; a repeated
scan created no duplicate request. Zero `rvtest_*` schemas remained and the
cluster was stopped. Graph validation passed (10 workflows, 161 nodes), the
controlled revision audit had zero issues, and Python compilation passed.

An existing worker knowledge-timeout test was made scheduler-load independent
after an observed 101 ms run exceeded its 100 ms wall-clock assertion despite
correct fail-closed behavior. The replacement uses synchronization to prove the
worker returns while the provider remains blocked; its regression test and the
entire suite pass. Initial fixture issues and their corrections are documented
in the checkout's `failed-attempts.md`. See
`evidence/checkouts/CME/20261010T194722Z-a44091b/`.

M2.4 roadmap technical criteria are PASS, but the component remains IN PROGRESS
against full DoD: no shared migration, installed service, live Steward view,
independent live observer, long-duration unattended run, or formal component
acceptance is claimed. M3.1 is next after integration. No merge is authorized
by this record.

## 2026-10-10 UTC — RV-M2.4-001 / branch CI

GitHub Actions controlled-checkout run 38081294773 passed on exact source commit
a44091bc32e82580dd8a3350e1ecfa47b0157b36. The workflow completed the full suite,
canonical graph checks, and controlled revision audit. The M2.4 branch remains
unmerged pending Steward authorization. No live service commissioning or full
component acceptance is claimed.


## 2026-10-11 UTC — RV-M3.2-001 / live delivery and restart verification

Deployed the package from `0fd10357ccdf2c9a0c87ba4a6f41e37ecff33ce9` as separate root-owned dashboard and notification-dispatcher releases; neither existing CME nor event processor unit was modified. Applied migration 0006 only after a protected full database backup, restore drill, and clone migration. Firefox 156 rendered the three actual notices derived from three persisted CME stall events; delivery and explicit acknowledgment receipts persisted. Restarted only the notification dispatcher; its new instance remained healthy and the same three notification IDs remained, with no repeated notice insertion. Read-only SQL after recovery: 3 notices, 9 append-only receipt events (3 queued, 3 delivered, 3 acknowledged), 0 pending requests, 4 assignments and 11 source events. Post-restart Firefox acceptance also confirmed attention HTTP 200, healthy CME/status projection, safe readable linked cookbooks, navigable workflow graph, no browser errors, and existing completed independently verified M3.1 worker artifact. Browser navigation calls were 45–62 ms in this run.

A first scratch browser predicate incorrectly inspected only the oldest row, which had already been acknowledged, and timed out while another row remained delivered. Corrected the test predicate to evaluate all rendered notice states; subsequent real-browser receipt tests passed. This was an acceptance harness defect, not a product delivery defect. The shared schema had no `awaiting_steward` assignment, so zero live decision requests were expected; request lifecycle remains integration-tested only. Evidence: `evidence/checkouts/M3.2/20261011T040851Z-0fd1035/`. M3.2 technical criteria pass; full DoD remains open and no later Steward acceptance is claimed. Next eligible work is M3.3 first unattended end-to-end demonstration.


## 2026-10-11 UTC — RV-M3.3-001 / live authority and knowledge preflight

M3.3 requires two authorized concurrent live assignments with a worker and independent verification, restart/recovery, dashboard and notification. Inspected the worker contract and runtime path. `PostgresWorkerAdapter` verifies a free-form matching scope reference but does not bind it to a durable Steward grant; the registry path is an explicitly trusted control-plane operation. `ContinuousWorker` defaults to `UnavailableKnowledgeProvider`; the only packaged provider besides that fail-closed default is a contract-test mock. Because authority and verified knowledge are prerequisites to an actual action, no live assignments, identities, grants, credentials, or services were modified to manufacture M3.3 results. Exact blockers and safe return conditions are recorded in `docs/development/M3.3-001_REVISION_RECORD.md`.

Proceeding with isolated M4.1 authority engineering as a safe unblocker while the M3.3 cursor remains unaccepted. Added PostgreSQL-backed principals and hashed credentials, exact grants/revocation, office/occupant/implementation separation, office-keyed state, and append-only authority events with a canonical graph. First isolated test pass exposed incorrect event subject references and an ambiguous office-state join; after fixes, a later credential-revocation query typo was found and corrected. Latest focused integration run: 7/7 passed on disposable PostgreSQL 16 UTF8/socket-only test cluster; schemas were dropped per test. No shared migration or runtime deployment has occurred; current shared application DB owner can bypass library authorization with SQL, so live security acceptance remains open pending a separately enforced DB role boundary and worker/assignment integration.


## 2026-10-11 UTC — RV-M4.1-001 / isolated regression checkpoint

After registering the M4.1 workflow and linking its cookbook from the operations index, ran `RIVERVIEW_TEST_PG_DSN='host=/tmp/rv-m41-pgsock-20261011 port=55461 dbname=postgres user=admin1' PYTHONPATH=src python3 -m unittest discover -s tests -v` against a disposable PostgreSQL 16 UTF8 socket-only cluster. Result: 132 tests passed, 0 failures/errors/skips in 58.411 seconds. `rvtest_*` schema count was zero; cluster fast-stopped and reported database system shut down. `python3 -m compileall -q src scripts tests`, graph check (12 workflows / 221 nodes), and controlled revision audit all passed. No M4.1 migration/deployment to shared `riverview_dev`; the current DB owner can bypass library-level authorization, so M3.3 still cannot safely execute live assignments. M4.1 full DoD and PR/CI remain open.

## 2026-10-11 UTC — RV-M4.1-001 / isolated authority evidence checkpoint

Committed the isolated identity and scoped-authority registry at source commit
`5f54fd9abaf7cc27f514e41461ee188c0d57ea91`. The complete applicable suite
passed 132/132 with zero skips on a disposable PostgreSQL 16 socket-only cluster;
compileall, process graph validation (12 workflows / 221 nodes), and the
controlled-revision audit passed. Durable logs, tool versions, isolated cluster
shutdown, and read-only M3.3 preflight state are retained under
`evidence/checkouts/M4.1/20261011T042719Z-5f54fd9/` and
`evidence/checkouts/M3.3/20261011T042719Z-5f54fd9/`.

No shared schema migration, authority identity/grant creation, worker/assignment
change, or service restart was performed. Live M4.1 remains NOT VERIFIED because
the shared application role owns the schema and can bypass library checks;
worker/assignment integration and protected database-role separation remain
open. M3.3 therefore remains BLOCKED at live authorization and real-knowledge
preflight. The next safe step is to review CI on the M4.1 branch, then design and
exercise the database privilege boundary on disposable PostgreSQL before any
shared deployment.

## 2026-10-11 UTC — RV-M4.1-001 / PR #18 CI result

PR #18 was opened as draft at head `e0fd888a979e32b4f11c848b22a54fdf8c32bbb7`,
base `codex/m3.2-durable-notifications`; no merge was requested or performed.
GitHub controlled-checkout run 38111731347 passed on the exact head, including
the full test suite, canonical graph synchronization, and controlled revision /
predecessor verification. Evidence: `evidence/checkouts/M4.1/20261011T042919Z-e0fd888/github-ci.json`.
M4.1 is still not operationally commissioned; live DB-role separation and
worker/assignment integration remain open.

## 2026-10-11 UTC — RV-M4.1-001 / isolated database privilege feasibility

On a disposable PostgreSQL 16.15 Unix-socket cluster, applied the base ledger and
M4.1 authority migration to an isolated schema. The application-like test role
owned the schema but not the authority tables. A separate NOLOGIN relation owner
owned the protected tables; the application-like role received no relation
privileges, while the service-like role was granted owner membership. Direct
SELECT and INSERT as the application-like role both returned
`InsufficientPrivilege`; the service-like SELECT succeeded. The cluster shut down
normally. Evidence is `evidence/checkouts/M4.1/20261011T043200Z-d281463/`.

This verifies the PostgreSQL role mechanism in isolation only. No provisioning
script, deployable migration, service credential, runtime integration, or shared
`riverview_dev` change was made. Two scratch-cluster launch attempts failed before
server start from temporary-directory/log ownership; corrected ownership then
allowed the isolated experiment to pass. The failure was confined to `/tmp`; no
Riverview or PostgreSQL service was affected. Next engineering step: produce a
reviewable versioned role provisioning and authority-writer credential boundary,
then test it with the actual registry connection before considering shared-schema
commissioning.


## 2026-10-11 UTC — RV-M4.1-001 / exact-head CI and cookbook correction

GitHub controlled-checkout run 38111853146 passed on PR #18 source head
`d281463be36d203c2727c0e4c8e16df7b2e2990b`, including tests, graph generation
and revision/predecessor checks. The authority cookbook now documents the
observed live role/schema ownership and limited isolated privilege-boundary
result. A review found over-escaped SQL quotes in its read-only role preflight;
the example was corrected and the exact Bash command was executed and exited 0; it reported the current
schema owner and absent registry without changing state. Evidence: `evidence/checkouts/M4.1/20261011T043300Z-d281463/`.


## 2026-10-11 UTC — RV-M4.1-001 / live read-only role preflight

Executed the newly documented authority role diagnostic against Camrui using the
`bash` shell so its line continuation remained intact. It exited 0 and observed
`current_user=postgres`, schema owner `riverview_core`, the app role flags all
false (not superuser/CREATEROLE/CREATEDB/BYPASSRLS), and a null authority
registry relation. The earlier Python `shlex` harness split the shell line
continuation incorrectly and produced a failed connection attempt; rerunning the
exact snippet in Bash passed. No database state was changed. Captured stdout is
`evidence/checkouts/M4.1/20261011T043300Z-d281463/authority-live-preflight.txt`.


The dashboard documentation renderer allows links only to approved component
Markdown and safe external HTTPS destinations. The new cookbook initially used
Markdown links to evidence files, which correctly rendered as inert text. Those
references are now plain readable repository paths instead of nonfunctional
links. The HTML rendering check follows.


## 2026-10-11 UTC — RV-M4.1-001 / dashboard-only docs and graph release

Deployed the verified `b63f6d85e7837caaa03265aa19164b57c818c8d9` archive as an
immutable root-owned dashboard release. CI run 38112124146 passed on that exact
source commit. The dashboard application code was unchanged relative to the
previous 0fd1035 release; this release adds the M4.1 cookbook and process graph
content. The previous release and unit remained available/unchanged, a checksum-
verified archive copy is retained root-only under
`/var/lib/riverview/deployments/dashboard/b63f6d85e7837caaa03265aa19164b57c818c8d9/`,
and only the dashboard unit was restarted. No migration, credential, identity,
grant, assignment, worker, or other service was changed.

Firefox 156 confirmed the live status projection, actual existing completed
worker assignment and independent verification, six attention records, all 19
linked component documents returning HTTP 200, zero browser errors, and local
navigation calls of 47–55 ms. A focused browser check selected the exact M4.1
canonical graph, rendered 12 nodes/13 edges/one decision, opened a stable node
reference, and showed live execution position unknown with zero highlights.
The full report, screenshot and archive checksums are retained under
`evidence/checkouts/M4.1-DASHBOARD-DOCS/20261011T043757Z-b63f6d8/`.

Two test-harness issues are retained: an immediate one-shot curl raced the
service's sub-second socket bind (journal readiness followed one second later;
subsequent checks passed), and an initial SVG `.click()` WebDriver call returned
500. The established bubbling MouseEvent dispatch passed. The corrected checker
reports decoded screenshot bytes. This dashboard deployment does not commission
the authority registry: the shared database has no authority tables, and no
identity/grant was created. M4.1 remains IN PROGRESS; M3.3 remains blocked on
deployable database-enforced authority and a real verified knowledge provider.

## 2026-10-11 UTC — RV-M4.1-DB-BOUNDARY / isolated PostgreSQL owner separation

On `codex/m4.1-db-privilege-boundary`, implemented a dry-run-first provisioner
for the fixed nine authority tables and append-only trigger function. Testing
revealed PostgreSQL schema ownership can permit dropping contained objects
even after relation ownership is transferred. Corrected the contract and
preflight to require runtime and manager be distinct from, and unable to
assume, schema ownership; the fixture models that distinct owner and tests
runtime SQL denial and fail-closed schema-owner rejection. The corrected
focused integration passed 1/1 and the complete disposable-PostgreSQL suite
passed 133/133 with no skips, failures, or errors. `rvtest_*` schema/role counts
were both zero after cleanup. Graph synchronization passed at 12 workflows/226
nodes; Python compilation and controlled-revision audit passed. All checks are
isolated; shared `riverview_dev` is unchanged. This is not a live boundary: the
current Camrui runtime owns the shared schema, and no protected manager
credential/service, migration, identity or grant was installed. The exact
checkout evidence will be recorded after the coherent commit is finalized.
Corrective experiments retained: initial post-apply catalog verification used
untyped parameters with PostgreSQL's variadic `format()` and failed with
`IndeterminateDatatype`; verification now checks relation OIDs and explicitly
casts role parameters. A subsequent Psycopg test query contained a literal `%`
in a `LIKE` pattern and failed its placeholder parser; it now uses a parameterized
catalog name list. The first schema-owner reproduction fixture lost runtime
schema usage after transferring ownership and exposed a `dict_row` indexing
mistake; the fixture regrants only its test role the needed schema access and
uses the named result. A verification assertion initially ran after the
intentional `DROP ... CASCADE`; it was reordered before that destructive
fixture-only proof. The focused test passed 1/1 and final full suite 133/133,
zero skipped/failed/errored. One restart attempt initially found the private
cluster already stopped; it was started from the same temporary data directory
and tests passed. No issue involved the shared database.

Next: capture commit-bound evidence, run GitHub CI, open (do not merge) a
focused dependent PR, then continue M4.1 integration only after its documented
role, credential, backup and compatibility prerequisites are met.

Commit `411bff91f383f9a518cd5fda8116e6cbf7bc9c86` was rechecked on the exact
committed tree: full PostgreSQL-backed suite 133/133, zero skipped/failed/
errored; compileall exit 0; canonical graph 12 workflows/226 nodes; controlled
revision audit zero findings; test schema and role cleanup zero. PostgreSQL
test cluster stopped cleanly. Immutable logs, commands and SHA-256 manifest:
`evidence/checkouts/M4.1-DB-BOUNDARY/20261011T053022Z-411bff9/`. The process
graph verification node references the checkout report. M4.1 stays in
progress and no shared live objects or services changed.

## 2026-10-11 UTC — RV-M4.1-DASHBOARD-ROUTE / preserve deployed interface

Added an HTTP-handler regression for the expanded authority cookbook and its
component link. The first assertion expected the phrase `DROP TABLE`, while the
actual warning is `DROP ... CASCADE`; corrected the assertion to match the
documented command warning. The focused dashboard route test now passes 1/1,
checking HTTP 200, rendered headings/table/code, expected security guidance,
and absence of source metadata comments.

Before any dashboard deployment, compared the committed M4.1 package against
the active root-owned release. The M4.1 source branch's `static/index.html` is
revision 1.0.5; Camrui's deployed M3.3 release `7a9ff46` contains revision 1.0.6
with additional repository-knowledge cookbook links. Installing the M4.1
archive would roll back the active shell. Package archive/path/checksum/shell
verification passed, but deployment was correctly withheld; no active symlink,
service, DB, or credential changed. The new cookbook route was tested in the
source handler, not claimed live in the browser. Refresh from the current
dashboard source before deployment. PR #20 remains draft; no merge performed.

Post-change verification on commit `9c96e7869c57165705392525b8be0f80575112ed`:
full isolated suite passed 133/133 with no skips/errors/failures; dashboard
cookbook route focus passed 1/1; compileall, graph sync (12/226), and controlled
revision audit passed. Exact-head GitHub CI run 38115330159 passed. Read-only
Camrui status at 05:37 UTC showed PostgreSQL, event processor, CME monitor,
notification dispatcher and dashboard active; baseline oneshot `Result=success`;
dashboard HTTP 200 on existing release 7a9ff46. Ledger counts: nine
migrations, four assignments, 11 events, one attempt, one verification, six
monitor events, three notices. An initial read-only query used the guessed
`assignment_events` name and failed; `pg_tables` confirmed the canonical table
is `events`, and the corrected read-only query returned these counts.

Attempted to create a follow-up exact-commit Camrui package before committing
the required predecessor records; `build_camrui_package.py` refused its clean
working-tree precondition because the backup manifest was intentionally dirty.
It created no archive. Commit records/backups first, then rebuild and verify the
exact committed source. This is a safe packaging precondition, not a test or
deployment failure; no active host path changed.

## 2026-10-11 UTC — RV-M4.1-167 / exact commit verification checkpoint

Committed and pushed the latest records as `167e63b9969a5cdbb1e4d3abee33e3e503bba11f`.
From its clean tree, built and verified the exact-source Camrui archive
(SHA-256 `04abf2a8a6ce4efcc3c741548df76fac77ea7b7b0833b439fe9580d9458f5d52`);
manifest, shell bytes, and path scan passed. Repeated the PostgreSQL-backed
suite (133/133, zero skips), focused docs route test (1/1), compileall, graph
check (12 workflows/226 nodes), revision audit (zero findings), and fixture
cleanup (zero `rvtest_*` schema/roles). Exact-head CI run 38115448463 passed.
Evidence is `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T054020Z-167e63b/`.

Deployment remains deliberately withheld because the verified full archive
would downgrade the installed dashboard shell and drop working repository-
knowledge links. Existing release 7a9ff46 and all operational services remain
unchanged and healthy; shared authority tables/roles/credentials remain absent.
M4.1 is isolated-engineering PASS, not live commissioning or component DONE.


## 2026-10-11 UTC — RV-M4.1-ROLE-SCOPE-REVIEW / least-privilege correction

Reviewed the M4.1 database boundary before live deployment. The prior design's
manager membership in the `NOLOGIN` table-owner role granted DDL and could
bypass registry controls. Reworked the helper to require a dedicated schema
with only authority relations, migration ledger and trigger function; deny
`PUBLIC`/ordinary-runtime schema access; require a NOINHERIT manager with no role
memberships; and grant manager DML on the nine allowlisted tables only. Added
fail-closed checks for unrelated tables/functions, manager membership and
manager DDL, while retaining exact registry behavior and the schema-owner
DROP-CASCADE proof in a disposable schema. The focused PostgreSQL integration
passed and teardown left zero test schemas/roles; the prior complete isolated
suite was 133/133. The process-graph tests passed 12/12, including new file-level
revision generation tests. A first fixture run exposed the migration runner's
required `schema_migrations` ledger; the fixture now creates that ledger inside
its isolated schema. A subsequent source indentation error was caught at test
collection and fixed before execution; no shared database was touched. No live
roles, schema, credentials or identity state changed. Exact-head CI and final
checkpoint evidence are pending.

## 2026-10-11 UTC — RV-OVERNIGHT-20261011-DASHBOARD-DOCS-CHECK / live browser evidence

Ran the controlled read-only Firefox check against the currently deployed dashboard release `8dcec2ada7d811a78f6cb28a1b81e6f8f59b1a9b`; all services remained active. The actual completed M3.1 assignment showed healthy/current projection, healthy CME, six attention records, one independent verification, and no failed checks or browser errors. The Operations Cookbook rendered 17 headings, 2 tables and 17 code blocks; all 21 linked component documents returned HTTP 200, with no raw Markdown, scripts or unsafe links. Graph view showed 12 nodes, 11 canonical edges and one decision, with correct unknown execution position. Navigation handler timings were 84/332/90/242 ms for Assignments/Activity/Overview/Workflows in this single run; not paint latency or a sustained benchmark. Durable report/screenshots and checksums: `evidence/checkouts/OPERATIONS-COOKBOOK/20261011T082220Z-4b7c23d/`.

The deployed release is based on the M3.3 repository-knowledge branch, while the present M4.2 PR source is based on the M4.1 database-boundary branch. The deployed cookbook has a repository-knowledge diagnosis absent in this checkout; this checkout has the observed PostgreSQL backup-path permission-failure procedure absent in the deployed package. Do not hot-edit or replace the working dashboard. Reconcile those controlled documents in the owning source branch before a later compatible package release. The current live read confirms documentation route health, but does not clear the docs/source divergence. Next: preserve the live run artifacts, then address the cookbook divergence through its owning source branch without altering database or service state.

## 2026-10-11 UTC — RV-M4.1-GRANT-ENFORCEMENT / exact-grant worker integration

Added a protected `authorize_exact_grant(bytea,text,text)` database function,
DB-boundary ACL integration, and `ExactGrantAuthorizer` on the existing worker
transaction. Worker registration now requires a grant-bound `worker.register`
credential; action and verification re-check exact `assignment.execute` and
`assignment.verify` scope grants. No grant, expired/revoked credential, unknown
function or database failure authorizes work. The existing deterministic worker
and CME integration fixtures now issue isolated grants rather than relying on a
free-form worker scope string.

The first boundary test run failed because its assertion expected runtime
schema USAGE to remain absent; the revised invariant is USAGE plus execute on
one function with all authority tables inaccessible. A follow-up test run
exposed that a revocation assertion had also revoked the same test credential
used by a later registry check; the test now revokes a separate credential.
Final focused PostgreSQL run passed 22/22 tests with no skips/failures/errors.
Process graph regeneration and validation passed at 13 workflows/265 nodes and
all 13 graph unit tests passed. Camrui read-only inspection confirms migrations
0000/0001 only, absent migration 0002/function, and runtime schema USAGE=false.
No live schema, grants, identities, credentials, assignments or services were
changed. M3.3 remains blocked on live deployment, an authorized assignment
intake path, a commissioned worker and the external real knowledge provider;
M4.1 remains in progress and M4.2 remains isolated. Next: complete full-suite,
revision and CI gates, checkpoint evidence, then evaluate protected additive
deployment without altering M1.1/runtime services.

## 2026-10-11 UTC — RV-M4.1-GRANT-FULL-SUITE / migration expectation correction

The first complete suite after adding authority migration 0002 found one stale
idempotency assertion still expecting only migrations 0000 and 0001. Updated
the test to assert all three migrations; the focused regression passed 1/1 and
the complete PostgreSQL-backed suite then passed **150/150**, zero
skips/errors/failures. Fixture cleanup found no `rvtest_*` schema or role and
the isolated PostgreSQL cluster stopped cleanly. `compileall`, process graph
(13 workflows/265 nodes), and controlled revision/predecessor audit passed.
Evidence and artifact checksums:
`evidence/checkouts/M4.1-DB-BOUNDARY/20261011T090500Z-exact-grant-worker-integration/`.
Camrui was only read-only preflighted: the 0002 function remains absent and
runtime schema USAGE remains false; no shared state or service changed. PR #21
is open/draft and exact-head CI for these changes remains pending. The next
safe step is exact-head CI, followed by protected backup/restore rehearsal and
only then an additive deployment decision; M3.3 also requires assignment
creation authorization, a commissioned worker, and the external real
knowledge provider.

## 2026-10-11 UTC — RV-M4.1-LIVE-EXACT-GRANT / additive boundary commissioning

Exact-head CI passed on `36622e573f9e030aba909967be76fc4cd646b620` (run
`38126965396`). Took a fresh PostgreSQL-owned 0600 full backup of `riverview`
(SHA-256 `f25af3984fa29f7f0a035c9fc0b01a6086e9eadbcb3b26ea77f2a7181255e4c7`),
validated the custom archive, restored it to a unique disposable DB, matched
Core/authority migration counts plus assignments/events/authority relation
counts, then removed only that restore DB and verified absence. Source
`36622e5` was extracted from its Git archive into a root-owned read-only-to-
admin source directory. Its checksum migration runner applied only authority
migration 0002. The boundary helper dry-run selected exactly the authority
relations and reported `apply_required=true`; apply returned `APPLIED`; an
idempotency rerun returned no pending migration; postflight returned
`apply_required=false`.

Live catalog checks verified the security-definer owner, pinned search path,
runtime execution grant, manager denial, runtime schema USAGE without CREATE,
and no runtime table SELECT. In a single rollback-only DB transaction, a
synthetic exact grant was allowed to the real `riverview_core` role, a wrong
action was denied, direct table access was denied, and the manager was denied
function execution; all rows were rolled back and verified absent. The initial
post-restore count query used the wrong ledger schema and failed read-only; a
corrected query established the expected counts. PostgreSQL, event processor,
CME monitor, notification dispatcher, dashboard and SSH remained active.
`riverview_dev` still has 9 migrations, 4 assignments and 11 events. Evidence:
`evidence/checkouts/M4.1-DB-BOUNDARY/20261011T090700Z-live-exact-grant/`.
This is database-function/ACL commissioning, not worker-service integration or
full M4.1/M3.3 acceptance. The next engineering tasks are `assignment.create`
authorization and controlled deployment of the actual worker adapter; M3.3
also requires the externally owned real institutional knowledge provider.


## 2026-10-11 UTC — RV-M4.1-DASHBOARD-DOCS-LIVE / deployment and browser evidence

Deployed an immutable documentation and synchronized-process-graph overlay at
`/opt/riverview-status-dashboard/releases/8556598b19a7da4aa191a600c767d79d24432afe-docs-d2c145c`. The executable, scripts, static assets, systemd security controls, and PostgreSQL state were retained byte-for-byte from the prior release; the overlay is sourced from docs/process-graph commit `d2c145cb9c7fbfb983ea842199e204d03bfdf731`. Source identity and docs identity are separately recorded in the package manifest and systemd deployment ID. Package checksums passed.

The first immediate HTTP probe raced systemd startup; the rollback guard restored the prior symlink and unit. A bounded readiness retry then passed without touching other services or database state. The service is active with `NRestarts=0`, `/api/v1/attention` returns 200, and the current release is the immutable docs overlay. Firefox 156.0.1 live-browser evidence shows a completed real assignment, one persisted attempt and independent verification, healthy CME projection, six attention items, 19 documentation links returning 200, rendered headings/tables/code blocks, no browser errors or unsafe links, and graph structure/navigation with live execution position truthfully shown as unknown. View-handler navigation timings in this single run were 64–210 ms; they are not paint benchmarks. Evidence, screenshots, service state, database read-only counts, checksums, and release manifest are retained in `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T091800Z-dashboard-docs-live/`. This is operational dashboard documentation deployment evidence, not full dashboard Component DoD or milestone acceptance.


## 2026-10-11 UTC — RV-M3.3-LIVE-COMMISSIONING / authorized unattended execution

Deployed M3.3 release `47a79adafe1524b3e819148b70c02a1857f50dbf` with a
loopback governed intake, exact-grant executor/verifier services, and immutable
repository-backed knowledge package. An unauthorized request returned HTTP 403
with zero target rows; the authorized route created a durable assignment and
event. The scheduled executor ran the repository knowledge test suite, created a
real protected report artifact, and the separately credentialed verifier
independently reran and accepted it. PostgreSQL evidence includes complete
VERIFIED grounding/preflight/regrounding; `record_learning` is UNAVAILABLE and
was not claimed.

The first service starts exposed the credential final-newline parser defect;
systemd retries were stopped, source was corrected and regression-tested, package
rebuilt, and the corrected release passed live execution. Later SIGKILL/restart
left an already completed result with one attempt and one verification. During a
separate bounded executor stop, two assignments remained queued, triggered durable
CME stall/attention notices, and completed after restart with accepted independent
verification; browser delivery receipts were persisted. No shared data was reset.

Full isolated PostgreSQL suite passed 184/184 (zero skips); graph validation and
synchronization passed at 16 workflows/311 nodes; exact-head GitHub CI passed.
The recovered pair did not establish simultaneous multi-executor throughput, so
the canonical M3.3 independent-concurrency criterion remains NOT VERIFIED.
Evidence is `evidence/checkouts/M3.3-LIVE-E2E/20261011T1245Z-47a79ad/`. PR #21
remains draft/open/unmerged; no Steward acceptance is inferred.


## 2026-10-11 UTC — RV-M3.3-WAITING-ISOLATION / fail-closed scheduler continuation

Submitted an authorized unknown-contract assignment through the live loopback
request API. Its assignment and events persisted, the repository knowledge
provider returned `NO_MATCH`, and the scheduler persisted
`blocked/WAITING_FOR_EVIDENCE` with no attempt. While it remained waiting,
submitted a separate authorized repository-test assignment. The normal scheduler
dispatched it; the credentialed worker produced a new report artifact; the
independent verifier accepted it; the dashboard live status/detail endpoints
returned HTTP 200 and displayed the waiting and completed assignments. No direct
state manipulation or service/credential configuration change occurred.
Evidence: `evidence/checkouts/M3.3-WAITING-ISOLATION/20261011T1310Z-47a79ad/`.
This supplies the canonical live evidence that two durable assignments progress
independently and missing knowledge cannot authorize an action. Scoped M3.3
technical criteria are ready for Steward review; formal acceptance and full
Component DoD remain open.

## 2026-10-11 UTC — RV-M4.1-GRACE-BOOTSTRAP-STATUS / controlled identity preparation

Resumed M4.1 after the live M3.3 technical commissioning. Read-only Camrui
inspection confirmed PostgreSQL 16.15, the dedicated authority schema, five
existing principals, and no Grace office, implementation, or binding. The
M3.3 intake, worker, verifier, and dashboard services remained active. Added a
fixed-scope root-local Grace bootstrap helper and safety tests; six focused
tests passed and the helper compiles. The full disposable-PostgreSQL test suite
passed 190/190 (zero skips/errors/failures) in 57.095 seconds; process graph
validation passed at 16 workflows/311 nodes, and the revision audit returned
zero issues. A recovery defect found in review was
corrected: if the database credential committed but token-file delivery was
interrupted, retries revoke orphaned bearers before issuing a new credential.
The interrupted-delivery regression passes. The provisioner has not been run
against the live registry. Isolated full-suite, graph, revision, exact-head CI,
and immutable-package verification remain pending; no live identity or service
was changed. Next: run the full private-PostgreSQL suite and controlled audits,
then commit/push before considering live provisioner execution.

## 2026-10-11 UTC — RV-M4.1-GRACE-IDENTITY-COMMISSIONING / additive live bootstrap

Exact-head CI passed on commit `fb536bb647d7d7a655a56155f687c74bec219945`
(run `38142915471`). The committed helper was extracted from that commit,
archived and SHA-256 verified, installed root-owned, then run locally against
the dedicated authority schema. It created only the stable Grace office,
resident, occupant, local-model binding and exact office-state grant. An
independent fresh process verified the grant using the protected resident
credential and a retry returned `ALREADY_PROVISIONED`. Credential metadata is
root:root 0600, no token was emitted, all seven existing M3.3 services remained
active, and M3.3 assignment data was not touched. Evidence is
`evidence/checkouts/M4.1-GRACE-IDENTITY/20261011T1330Z-fb536bb/`. Graph
registration and synchronized views now pass with 16 workflows/318 nodes.
This advances M4.1 identity bootstrap only; a continuous resident service and
Grace-directed end-to-end execution are still absent. Proceed with authority-
bound resident service integration and restart/replacement verification.

## 2026-10-11 UTC — RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE / deterministic infrastructure slice

Implemented bounded, commit-pinned resident evidence selection and distinct
CONTEXT_TOO_LARGE versus KNOWLEDGE_NOT_SERIALIZABLE reasoning outcomes.
Added a PostgreSQL objective/event record and a typed proposal bridge that keeps
objective submission (objective.submit) separate from assignment dispatch
(assignment.create). Assignment creation, its ledger event, and the objective
link share the existing ledger transaction. Added one fixed, no-shell artifact
worker capability and an independent verifier that reopens the on-disk artifact.

Verified in a private temporary PostgreSQL 16 cluster and random disposable
schemas. Positive flow persisted a scoped objective, commit-pinned evidence,
unapproved proposal, authorized assignment, worker attempt, actual mode-0600
artifact file, accepted independent verification, and completed objective. Denied
authorization, missing evidence, over-budget context, worker failure, and
completion before persisted verification were rejected. Selector tests passed
against a temporary committed Git repository. No live model, service, shared
database, or OctoMiner endpoint was contacted. This is infrastructure test
evidence only; real resident reasoning, commissioned coding worker service,
dashboard interaction, unattended repetition, and M4.4 acceptance remain open.

The complete test suite subsequently passed 205/205 with zero skips against the
same isolated PostgreSQL 16 cluster. Process-graph synchronization and validation
passed for 16 workflows / 323 nodes. The controlled-source revision audit against
the clean 6a326279 baseline returned zero issues. These results qualify this
working-tree implementation only; CI and a reviewable feature commit are still
required before a merge-ready claim.

## 2026-10-11 UTC — RV-M4.4-PERSISTENT-EXECUTION / supervised execution infrastructure

Added a continuously supervised, model-independent Grace service over the
existing PostgreSQL objective pipeline, exact grants, event processor, leased
worker adapter, bounded artifact worker, verifier, and dashboard. Governed
objective submission, proposal, cancellation, durable health/progress,
idempotent dispatch, bounded retry/recovery, and status projection are covered.
The service unit targets its own immutable Grace release path; deployment,
credentials, and migration application remain separate controlled operations.

The complete suite passed 211/211 with zero failures, errors, or skips against
private PostgreSQL 16.15 in 118.438 seconds. A spawned-process restart test
proved queued durable work was resumed with exactly one execution attempt and
one accepted independent verification. Graph check/validation passed for 16
graphs and 330 nodes; static unit validation, compilation, and revision audit
passed. Exact output and source checksums are in
`evidence/checkouts/M4.4-PERSISTENT-EXECUTION/20261011T1740Z-cc548e6/`.
Commit `da0b724` is a dependent draft change based on PR #23 head `cc548e6`.
No live service was installed or started and no shared database or production
service was changed; operational commissioning and full M4.4 DoD remain open.

## 2026-10-11 UTC — RV-M4.1-M4.2-OCCUPANT-REPLACEMENT-INTEGRATION

Added a cross-component regression proving M4.1 office state follows the
institutional office when occupant/implementation change while
`office.state.write` authority follows the replacement occupant. A new
`ResidentReasoner` instance resumed the persisted plan using the current binding
and provider; the former credential was denied. Focused PostgreSQL suite:
12/12 PASS. The complete suite passed 212/212 with zero skips, errors, or
failures on an isolated socket-only PostgreSQL 16 cluster. Process graph
validation passed (16 workflows / 330 nodes), and the controlled revision audit
returned zero issues. The fixture-schema check found no leftovers and the
private cluster was stopped. No shared or operational state was changed. This
is an M4.1/M4.2 isolated integration proof only; live resident operation, model
proposal, and full Component DoD remain open. M3.3 is technically ready for
Steward review with formal acceptance pending. Next work remains M4.1 runtime
integration in dependency order. Exact-head GitHub CI passed for source commit
`89752f79487cf9178484db6451a4c36fd107b80a` in run
[38165302494](https://github.com/ppow1/Riverview-/actions/runs/38165302494).


## 2026-10-12 UTC — RV-GRACE-CHAT-UX-001

Refined the existing Talk with Grace workspace without changing its conversation API,
identity, grants, provider binding, or PostgreSQL writes. The browser now renders full
multiline history as role-distinct bubbles, preserves an unsent browser-session draft,
provides Enter/Shift+Enter and touch line-break controls, response states, factual detail
dialogs, per-message details/copy, and explicitly disabled future actions. A historical
interruption is retained in the transcript but no longer appears as the current error
after a subsequent successful response. The canonical browser-chat graph and generated
focused/aggregate views were synchronized.

The isolated Firefox/WebDriver acceptance run reused the existing loopback
`qwen3-0.6b-q8_0-local` service (4096 context; it was not restarted or reconfigured) and
a dedicated disposable PostgreSQL 16 cluster. A 770-character multiline Steward input
was rendered exactly; two actual model responses (89 characters each) completed at
11.38 s and 14.91 s browser elapsed time. A controlled pending turn was reconciled as
interrupted across a supporting dashboard restart; the following turn succeeded.
PostgreSQL independently contained 3 user events, 2 assistant events, and 1 interruption,
with zero objectives. The test passed unauthorized access as HTTP 403; Chat Details
matched persisted conversation/model/status and included UTC; message Details and Copy
passed; future capabilities were disabled; composer sizing/duplicate protection/newline
behavior passed; long-content layout did not truncate or overflow; 500-pixel narrow and
1280-pixel desktop layouts kept controls visible without horizontal page overflow. Firefox
headless clamped the requested 390-pixel window to a 500-pixel CSS viewport, so a physical
390-pixel Windows/mobile browser check remains outstanding.

Full repository suite: 228 passed, 0 failures, 0 skips in 140.169 s with isolated
PostgreSQL configured. Graph validation/synchronization: 17 graphs / 353 globally unique
nodes, PASS. Controlled revision audit against clean baseline `ed0ea269` reported no
issues. Exact evidence is in
`evidence/checkouts/RESIDENT-CONVERSATION/20261012T-ui-refinement-isolated-13/`; the
browser report contains no message body or credential value. The first test-harness
iteration exposed stale expected status text, prior-interruption presentation, untrusted
synthetic clipboard clicks, and a modal/scroll interaction; each was diagnosed, corrected
in the harness or UI, and retested. The successful result is not Windows-browser
commissioning or Steward acceptance. The currently deployed dashboard has not yet been
replaced; rollback deployment remains to be performed only after packaging and provenance
checks.


## 2026-10-12 UTC — RV-GRACE-CHAT-UX-001 / controlled deployment

PR #27 (`5cbf315b95b5b644296910b4c7a16e5ae358e55b`) passed controlled-checkout CI
(run `38193890852`) and was deployed without merge as a versioned dashboard-only release.
The prior dashboard release and symlink target are retained. The release's three changed
static files were checksum-matched to the committed branch, and a revision 1.0.0
root-owned drop-in updates dashboard source/deployment identity. A single dashboard service
restart succeeded; the dashboard remained active, PostgreSQL projection and CME reported
healthy, attention returned HTTP 200, and the deployed Firefox browser check found no
errors. The check verified a real completed assignment/attempt/independent-verification
projection, workflow navigation, and documentation rendering/link status. A second live
Firefox check exercised the actual Talk with Grace shell, composer/menu/details, and
invalid-grant HTTP 403. Evidence is
`evidence/checkouts/RESIDENT-CONVERSATION/20261012T-ui-live-deployed/`; operational
Firefox screenshots and report are retained under the private
`/home/admin1/.local/state/riverview/commissioning/grace-chat-ui-5cbf315/` directory.

No PostgreSQL migration, human or resident credential, conversation content, model server,
CME/worker/verifier, event processor, or notification service was modified. The existing
loopback Qwen CPU inference service remains on the same process and configuration. The
Steward's Windows browser could not be controlled from this Camrui session; no message was
sent with a human credential. The isolated real-model and PostgreSQL integration evidence
remains distinct from live website interaction. A 390-pixel same-origin responsive iframe fixture passed with complete text, visible controls, and no horizontal overflow. Windows refresh-and-send confirmation and physical-device verification remain outstanding. Technical UI deployment is verified;
formal Steward acceptance and full Component DoD are not claimed.

## 2026-10-13 UTC — RV-GRACE-ROUTER-ACL-READINESS-001

Corrected the dashboard router startup preflight after the approved
`ddfe62c` commissioning release treated the runtime-invisible
`riverview_authority.schema_migrations` ledger as absent. The dashboard now
checks the deferred-response migration only in its runtime-owned
`riverview_dev` ledger and verifies the current router binding through the
existing exact-grant `AuthorityRegistry.authorize_office_state` API. Startup
fails closed on a missing resident migration, unavailable authority capability,
or provider/digest mismatch. Authority migration checks remain the deployment
runner's checksum-verified responsibility; database permissions were not
expanded.

Added a disposable PostgreSQL role regression reproducing Camrui's ACL
behavior: `information_schema.tables` hides the authority ledger and SELECT is
denied, while valid readiness succeeds through the authorized capability.
Missing migration, unavailable authority API, and mismatched binding each fail
closed. The full suite passed 303/303 with zero skips; canonical graph check
passed at 18 workflows / 410 nodes; controlled revision audit passed with zero
issues. The test used a socket-only disposable PostgreSQL 16 cluster; no
production service or database was changed by this correction. The new release
is not deployed. Camrui remains on dashboard release `3639f680`, with Grace
bound to the 0.6B implementation at binding revision 3. The corrected release
still needs PR/CI and a new immutable candidate archive before a later
commissioning attempt. The real authenticated 80B browser acceptance remains
open.

## 2026-10-15 UTC — RV-WEBSITE-PUNCH-LIST-001

**Classification:** website backlog recovery and workflow navigation enhancement.
**Owner:** STEWARD-DASHBOARD / website presentation.
**Branch:** `codex/website-improvements`.
**Integration baseline:** `codex/grace-conversation-ui-refinement` at PR #41 merge `218cb58491bcb939466a1eebb51bd666fd97005`; PR #40's durable SSE and deferred-response recovery are included. The website branch contains the two later Steward punch-list documentation commits replayed onto this integration point. PR #40 touched the shared dashboard `server.py`, `static/app.js`, dashboard tests/docs, and Grace runtime. This change avoids the shared behavior-code and test files; its only same-file documentation overlaps are additive workflow-navigation paragraphs in the dashboard contract and cookbook. Stream behavior and stream-specific documentation remain intact.

**Production baseline:** NOT VERIFIED from this environment. The punch list's last reported dashboard release is `3639f680` (captured 2026-10-13); it is historical reporting, not a current live check. The authorized read-only SSH check failed because this environment could not resolve `camrui`. No production service or database was contacted or changed.

Recovered PL-NEW-001 through PL-NEW-041 into `docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`. Original IDs, source priorities, later observations, and the distinction between captured observations, roadmap requirements, existing implementations, and proposals are retained. PL-NEW-027 was selected as an independent, explicit website usability improvement. PL-NEW-041 remains P1 as captured and is queued after the Grace commissioning repair; the current 128 KiB snapshot cap and the larger canonical workflow export are recorded as design constraints, not as a new requirement.

The workflow viewer now follows the exact registered `jump_target_id`, focuses the destination node and its accessible detail, and exposes a return control that restores the originating graph and jump node. A failed target request retains the return control. The canonical dashboard graph advanced to revision 1.1.3; generated aggregate and focused flow views were synchronized, including the normal no-jump-selected path. The captured source punch list received a controlled file revision header after its original bytes were backed up; no captured item text was changed. The dashboard contract/cookbook and this journal were updated. No SSE, deferred-resume, Grace, engineering-execution, authorization, CME, schema, or deployment code was changed.

**Verification:** `PYTHONPATH=.:src pytest -q tests/test_status_dashboard.py tests/test_process_graph.py` — 32 passed, 8 skipped. The skips are database-dependent cases; this work did not connect to production PostgreSQL. `python3 scripts/process_graph.py check` — PASS, 19 workflows / 458 nodes. An isolated Firefox/geckodriver loopback fixture loaded all 19 canonical graphs and passed exact target focus/detail plus return-to-source focus/detail; report and screenshots: `evidence/checkouts/WEBSITE-PL027/20261015T193400Z-workflow-navigation/`. The first browser fixture attempt lacked its local test token and timed out before loading the graph list; the setup error and correction are retained in the adjacent evidence directory. Production account-cookie transport and live browser acceptance remain NOT VERIFIED.

**Next:** review the complete diff and evidence manifests, commit to the assigned branch, and prepare a draft PR against `codex/grace-conversation-ui-refinement`. PL-NEW-025 account-cookie browser regression is the next website verification item; PL-NEW-041 remains sequenced after the independently owned Grace commissioning repair.

## 2026-10-15 UTC — RV-WEBSITE-PL025 / RV-WEBSITE-PL026

**Classification:** account-cookie browser verification and workflow-viewer usability documentation.
**Owner:** STEWARD-DASHBOARD / website presentation.
**Branch:** `codex/website-improvements`, resumed from `2578626` on PR #42.
**Baseline:** production/integration worktree base is `codex/grace-conversation-ui-refinement` at PR #41 merge `218cb58491bcb939466a1eebb51bd666fd97005`; PR #42 was open as a draft and its prior CI run passed. PR #40 stream behavior remains in the baseline.

PL-NEW-025's acceptance calls for investigating the actual account-cookie path and establishing deployed browser acceptance evidence for the prior “Loading canonical registry” failure. The existing workflow client already uses `credentials:"same-origin"` and makes bearer authorization conditional on a recovery token. Added `scripts/verify_workflow_account_cookie_browser.py`, which runs the checked-out workflow client and stylesheet in Firefox against a loopback fixture that issues a synthetic HttpOnly account cookie and requires it for both registry and graph-detail reads. The browser sent no bearer authorization, rendered the expected graph node and details, and reported no browser errors. Final report and screenshot: `evidence/checkouts/WEBSITE-PL025/20261015T-account-cookie-browser-final/`. Earlier failed harness attempts are retained in sibling evidence directories and explained in the checkout note.

The requested read-only SSH check using `admin1@192.168.1.155` reached the host-key prompt but failed authentication with `Permission denied (publickey,password)`. No production service, database, or account was contacted. Therefore isolated cookie transport is verified, while deployed account-cookie acceptance and the current live production release remain unverified. No browser or service was pointed at production.

PL-NEW-026's requested distinctions are now explained beside the viewer controls and in the dashboard cookbook: the workflow selector switches graphs, mouse or keyboard selection opens node identity/revision/references, graph and node revisions are separately labeled, and legend chips are static visual keys. The existing canonical dashboard flow already describes same-origin account-session workflow transport, so its runtime graph needed no semantic change. The recovery backlog now records PL-025's remaining deployed-evidence blocker, PL-026's branch implementation, and PL-013's coverage audit as the next independent item.

**Verification:** isolated Firefox account-cookie test PASS (`scripts/verify_workflow_account_cookie_browser.py`); browser error list empty; index and detail requests both included the synthetic account cookie and omitted Authorization. `PYTHONPATH=.:src pytest -q -rs tests/test_status_dashboard.py tests/test_process_graph.py` — 32 passed, 8 skipped because `RIVERVIEW_TEST_PG_DSN` is unset. `python3 scripts/process_graph.py check` — PASS, 19 workflows / 458 nodes. Python compile and focused `git diff --check` passed. Controlled revision audit — PASS, zero issues; final browser evidence manifest — PASS, three checksummed artifacts. The browser test verifies transport/rendering against a fixture; it does not substitute for live account authentication or deployment acceptance. PR #42 was updated; exact-head CI run `38797619074` on `b46bf33` passed the full suite, graph checks and controlled revision checks. PL-013 audit is recorded below.

## 2026-10-15 UTC — RV-WEBSITE-PL014

**Classification:** dashboard refresh, freshness, and projection-state guidance.
**Owner:** STEWARD-DASHBOARD / website presentation.

The overview now states that status reads bypass browser cache and that the
displayed timestamp comes from the API's `observed_at`. It defines healthy
as a successful required ledger read, not initialized as reachable PostgreSQL
with required ledger tables absent, and unavailable as inability to confirm
current state. It also clarifies that event/detail refreshes are separate
bounded requests and an optional relation's `not_initialized` value is a
domain state. The troubleshooting cookbook records the same behavior against
the implemented fetch and projection code.

The isolated browser fixture and focused tests validate the visible guidance.
No API route, state transition, or workflow node changed, so the canonical
dashboard graph remains accurate. No cache policy, server, or status contract
was changed. Focused browser assertions passed with the adjacent PL-NEW-012
regression; the broader dashboard/process-graph suite passed 37 tests with 8
PostgreSQL-dependent skips because `RIVERVIEW_TEST_PG_DSN` is unset. The
canonical graph check passed (19 workflows / 458 nodes), and the controlled
revision audit reported zero findings. Evidence and checksums are stored in
`evidence/checkouts/WEBSITE-PL014/20261015T204600Z-projection-guidance/`.

## 2026-10-15 UTC — RV-WEBSITE-PL012

**Classification:** Activity event presentation and source-boundary audit.
**Owner:** STEWARD-DASHBOARD / website presentation.

The canonical event projection already carries event type, recorded time,
sequence and event IDs, nullable assignment ID, actor ID, correlation and
causation IDs, and payload schema. Activity cards previously omitted actor
and payload schema and presented identifiers with terse labels. They now show
the available provenance, humanized event type, explicit root-event state,
assignment link when available, and a dashboard troubleshooting link. Cards
state that payload bodies and event-specific diagnostic references are absent.
The assignment ID is the only task reference exposed; no separate task ID is
available. No missing field is inferred from event type.

The fixture browser and focused test verify provenance rendering and the
payload/diagnostic boundary. Existing dashboard process graph already covers
event paging and links its failure branches to the troubleshooting cookbook;
no new route, state transition or graph node was introduced, so no graph file
changed. PL-NEW-012 is implemented for available projection fields and remains
partial pending an integration-owned event detail/diagnostic source contract.
No server, event schema, authorization, CME, or streaming behavior changed.

## 2026-10-15 UTC — RV-WEBSITE-PL013

**Classification:** bounded dashboard diagnostic coverage audit.
**Owner:** STEWARD-DASHBOARD / website diagnostics.
**Evidence:** [`PL-NEW-013 diagnostic coverage audit`](PL-NEW-013-DIAGNOSTIC-COVERAGE_AUDIT.md).

Read-only inspection found 59 distinct literal HTTP error identifiers in the dashboard handler and one dynamic `exc.code` path. Exact-match analysis found five identifiers in the dashboard contract/cookbook and none in the canonical dashboard workflow JSON. Broad failure/recovery nodes and area-level cookbook procedures exist; the audit makes no claim that each unmatched string lacks semantic guidance. No dedicated dashboard diagnostic catalog or route was found. PL-NEW-013's audit deliverable is complete with the traceability limits and evidence recorded. Building a complete searchable catalog remains a separate PL-NEW-038 captured proposal and requires a governed mapping source.

No canonical workflow map change was needed: its broad failure and recovery branches already point to the relevant dashboard troubleshooting material. No server, authorization, CME, production, or schema code changed.

## 2026-10-15 UTC — RV-WEBSITE-PL028 preflight

Read-only inspection of `NotificationService.list_notifications`, its dashboard projection route, and the notification renderer found assignment ID, event type, a fixed generic summary, source/queued timestamps, delivery status, and optional decision request ID/status. The projection does not expose priority, rationale, actionable details, or an explicit required-action field. PL-NEW-028 requires these details before receipt acknowledgment. The website cannot provide truthful values from its current payload. Adding the missing source fields requires a notification service/CME/API contract change outside this assignment's backend/CME boundary. The item is recorded as blocked pending an integration-owned contract; no changes were made to notification, backend, CME, authority, or shared streaming behavior.

## 2026-10-15 UTC — RV-WEBSITE-PL004/006/008/011 / PR #42 reconciliation

**Classification:** assignment-detail linkage, overview guidance, worker inventory usability, activity pagination, and controlled branch reconciliation.
**Owner:** STEWARD-DASHBOARD / website presentation and navigation.
**Branch / PR:** `codex/website-improvements` / draft PR #42, base `codex/grace-conversation-ui-refinement`.
**Integration baseline:** PR #43 merge `665ae8100a50faa26985b0cfee8834e68bf2a847`, which includes Codex 1's Grace Engineering proposal-guidance change. The PR #42 head that previously passed CI was `d4d7ba57b249dd477f811ae3c155f139c37c06a7`; it had become conflicting after PR #43. Rebased the website worktree onto the new base. Source changes did not conflict with PR #43. The only rebase conflict was the append-only `.riverview-backups/manifest.jsonl`; both integration and website records were retained. No PR #43 source file was modified. PR #42 remains draft/open pending push and exact-head controlled CI; it is not merged or deployed.

PL-NEW-004 audit confirmed the assignment projection already returns nullable persisted `process_graph_id` and `process_node_id`, but the detail renderer omitted them and printed the diagnostic path as unlinked text. Detail now shows both IDs, explicit not-recorded states, a restricted `/docs/components/<name>.md` link, and the boundary that these references do not establish current execution position. A synthetic Firefox run verified populated and null-linked records, safe diagnostic routing, cookie-only requests, and no browser errors. Evidence: `evidence/checkouts/WEBSITE-PL004/20261015T203000Z-assignment-linkage/`.

PL-NEW-008 uses only the existing worker fields. The overview now counts records in loaded pages, distinguishes active/inactive/unknown registration from healthy/stale/unknown/unverified heartbeat status, marks inactive registrations as such, and reports whether more cursor pages remain. The 390px Firefox fixture had no worker-row overflow. PL-NEW-006 added overview text for the event sequence cursor, projection/freshness, independent CME/worker heartbeats, and Grace execution versus chat availability. No runtime configuration value was inferred.

PL-NEW-011 adds explicit older and newer Activity controls using existing exclusive `before_seq` and `after_seq` cursors. Older events prepend, newer events append, and overlapping event IDs are deduplicated. The isolated browser sequence 2–3 → older 1–3 → newer 1–4 remained ordered with no duplicates. Existing canonical dashboard nodes already describe bounded event paging and worker listing; no new API path, state transition, or workflow node was needed. PR #40 streaming and deferred-response code was not changed.

PL-NEW-028 is blocked pending an integration-owned notification/CME/API contract. The current notice payload has `assignment_id`, `event_type`, a static generic `summary`, timestamps, delivery/acknowledgment state, and optional decision request ID/status/version. It lacks `required_action`, `rationale`, `priority`, optional `deadline` with an explicit absent state, and structured `actionable_details`. `source_event_id` identifies the CME event, but its authoritative details are not exposed by the notification API. The integration owner must source condition rationale/details from the CME event and action/priority/deadline from applicable assignment or decision policy, define a versioned API shape and provenance, then satisfy the acceptance criteria recorded in `docs/steward/WEBSITE_PUNCH_LIST_RECOVERED.md`. The website does not synthesize notification content or modify CME/backend contracts.

PL-NEW-007 is separately blocked because `RIVERVIEW_STALE_AFTER_SECONDS` has a 30-second code default but `/api/v1/status` does not return the effective runtime value, and CME has a separate freshness setting. PL-NEW-009 is blocked because the worker projection omits capabilities, host, task identity/context, execution detail, and failure history. Exact source requirements and acceptance are in the recovered punch list. PL-NEW-025's isolated account-cookie evidence remains preserved; production acceptance is **UNVERIFIED** because SSH authentication to the requested host failed before a service check. This is not evidence of production service failure.

**Verification:** `PYTHONPATH=.:src pytest -q -rs tests/test_status_dashboard.py tests/test_process_graph.py` — 36 passed, 8 PostgreSQL-dependent skips (`RIVERVIEW_TEST_PG_DSN` is unset). `python3 scripts/process_graph.py check` — PASS, 19 workflows / 458 nodes. `git diff --check` — PASS. The staged controlled revision audit passes with zero findings. Isolated Firefox reports and screenshots: `evidence/checkouts/WEBSITE-PL004/20261015T203000Z-assignment-linkage/` and `evidence/checkouts/WEBSITE-PL-UI-REGRESSIONS/20261015T203000Z-overview-workers-activity/`. No production service, database, schema, grant, CME, worker, OCTO1/OCTO2 configuration, or deployment was touched.

**Next:** push the rebased website branch with lease protection, refresh PR #42's scope/evidence, and confirm exact-head checks before marking it ready for controlled integration review. Do not merge or deploy in this website task. Next independent punch-list audit: PL-NEW-012 event meaning and diagnostic evidence, using only available projection fields.

## 2026-10-15 UTC — RV-GRACE-WORKORDER-RECOVERY-001 (integration journal)

Preserved the integration journal entry from PR #44: its work-order recovery
changes bind packaged knowledge to the matching release by default, preserve
durable wait receipts, and use authenticated conversation/message origin for
idempotent retries. The entry records that production retry and subsequent
CME/Codex/verifier work remain pending controlled review. This website branch
does not implement, alter, or commission that behavior.

## 2026-10-15 UTC — RV-WEBSITE-PR42-RECONCILE

The integration base advanced from PR #43 merge
`665ae8100a50faa26985b0cfee8834e68bf2a847` to PR #44 merge
`29d196f879d0a3a1dad5f782b305d9d52a0baadd` while PR #42 exact-head CI was
running. The website branch now merges the current base and retains Codex 1's
Grace work-order recovery source, graph, generated graph, component docs, and
test coverage. Shared revision, journal, and dashboard-test records were
resolved additively. No Grace execution behavior was changed in this
reconciliation.


## 2026-10-15 UTC — RV-WEBSITE-PL016

**Classification:** documentation and back-navigation behavior.
**Owner:** STEWARD-DASHBOARD / website navigation.

Dashboard documentation links now target a reusable named documentation
browsing context. The rendered documentation header returns to the named
dashboard context. Same-origin links omit `rel=noreferrer` because its implicit
`noopener` would force new browsing contexts and defeat name reuse. No route,
API, authority, event stream, or server behavior changed. The existing dashboard
process graph's render-documentation node now records this test evidence; its
node revision was incremented, and generated graph views were synchronized.

The focused test passed (`1 passed`). The isolated Firefox fixture passed all
checks, including documentation tab reuse, return to the original dashboard,
second document reuse, cookie-only API requests, no bearer header and no browser
errors. Evidence is in
`evidence/checkouts/WEBSITE-PL016/20261015T212500Z-documentation-navigation/`.
An earlier run exposed the implicit-`noopener` defect; its failed report is
preserved in the adjacent `20261015T211500Z-documentation-navigation/`
directory. Production acceptance remains pending controlled integration and
deployment. No production service, database, schema, grant, CME, worker, OCTO
configuration, or deployment was touched.


## 2026-10-15 UTC — RV-WEBSITE-PL010/015/020/023/024

**Classification:** Grace execution readiness, objective commissioning, chat
controls, menu availability, and dashboard milestone semantics.
**Owner:** STEWARD-DASHBOARD / website presentation.

The overview and Objectives view now state that conversation access and durable
execution have separate readiness. An uninitialized objective source directs the
Steward to verify the selected database/schema and reviewed resident-execution
migrations; Refresh is read-only and does not commission CME or workers. The
conversation view explains Disconnect (session ends, persisted history remains),
Refresh history, Enter/Shift+Enter, and Insert line break. Existing future or
unavailable menu choices remain disabled and are explicitly labeled. The header
identifies M3.1 as the dashboard milestone and separates roadmap, deployed
release, and commissioning status.

Focused tests passed 2/2. Isolated Firefox account-cookie browser verification
passed 25/25 checks with no browser errors, including a synthetic objective
`not_initialized` response, all menu states, and mobile layout. The canonical
process graph already represents these existing view and refresh paths; no state
transition or route changed. No PR #40 streaming code, backend, authorization,
CME, database, service, or production configuration changed. Production
acceptance remains pending. Evidence will be checksummed under
`evidence/checkouts/WEBSITE-CLARITY/20261015T215000Z-guidance-and-controls/`.


## 2026-10-15 UTC — RV-WEBSITE-PL019

**Classification:** conversation transcript and composer visibility.
**Owner:** STEWARD-DASHBOARD / website presentation.

A synthetic 40-message Firefox run exposed an overlay: the sticky composer
covered the lower portion of the separately scrollable transcript. The same run
found document-wide horizontal overflow from the narrow top bar's account
controls. The composer now follows the transcript in document flow, and the
narrow top bar stacks and wraps. The transcript remains vertically scrollable
and auto-scrolls to the newest message. No conversation API, SSE delivery,
deferred-response handling, or persistence behavior changed.

Focused layout test passed 1/1. The corrected browser run passed all checks,
including final-message visibility, composer below transcript, and no horizontal
overflow. Firefox clamped the requested 390px window to a 500px CSS viewport,
so narrower physical-device verification is not claimed. Initial failed and
corrected reports are preserved under `evidence/checkouts/WEBSITE-PL019/`.
No production service or deployment was touched.


## 2026-10-15 UTC — RV-WEBSITE-PL036

**Classification:** dashboard navigation rail usability.
**Owner:** STEWARD-DASHBOARD / website navigation.

Added an accessible expand/collapse control with an explicit `aria-expanded`
state, durable browser preference, named navigation controls, and responsive
compact default for screens at or below 920 CSS pixels when no preference exists.
The compact rail retains a health indicator with a current accessible label and
the bounded diagnostic snapshot control. No route, state transition, or API
changed; the existing dashboard shell node now references the passing browser
evidence.

The focused test passed 1/1 and the isolated Firefox fixture passed all 29
checks with no browser errors, including both rail states, health/snapshot
affordances, and a narrow viewport. Evidence:
`evidence/checkouts/WEBSITE-PL036/20261015T231000Z-collapsible-navigation/`.
Production acceptance remains unverified.


## 2026-10-15 UTC — RV-WEBSITE-PL003

**Classification:** assignment title presentation and source-contract audit.
**Owner:** STEWARD-DASHBOARD / website presentation; assignment payload ownership
remains with integration/Engineering intake.

Assignment rows and details now display the canonical workflow-node label only
when the existing authenticated graph API returns an exact match for the
persisted process graph and node IDs. Stable assignment, graph and node IDs
remain visible. Missing or unregistered references display an explicit
unavailable state; `workflow_step` is not repurposed as a title. The same
canonical assignment page behavior supplies Current Work title/state content.

The integration-owned assignment projection does not include purpose, original
request, expected deliverable, result, acceptance criteria, evidence records, or
blocked reason/missing evidence/owner/unblock action. Those source fields and
acceptance criteria are recorded as blockers for PL-NEW-001/002/005. No
Engineering intake, backend, CME, or authorization changes were made.

The focused test passed 1/1. Isolated Firefox passed the title lookup, stable ID,
missing-reference, account-cookie and no-browser-error checks; evidence is
`evidence/checkouts/WEBSITE-PL003/20261015T233000Z-canonical-task-title/`.
The process graph's bounded assignment-page node now links this verification.
Production acceptance remains pending.


## 2026-10-16 UTC — RV-WEBSITE-PL029

**Classification:** notification lifecycle semantics and source-contract audit.
**Owner:** STEWARD-DASHBOARD / website presentation; notification/decision API
ownership remains with integration.

Notification cards now show dashboard rendering confirmation, person-seen as
not reported, receipt acknowledgment state, and linked decision request status
as separate concepts. The interface states that acknowledgment cannot resolve
a decision. A source event labelled `attention_resolved` is presented as a
condition event and not as a decision outcome.

The current integration contract contains no `seen_at` or `seen_by` field and
no decision-resolution operation/outcome contract for approved/denied/resolved
with actor/time/provenance. PL-NEW-029 is therefore partially addressed and
blocked on that external contract. No notification service, CME, decision API,
or backend changes were made. The focused test passed 1/1; isolated Firefox
passed all browser checks with no errors. Evidence:
`evidence/checkouts/WEBSITE-PL029/20261016T001000Z-notification-state-clarity/`.


## 2026-10-16 UTC — RV-WEBSITE-PL038

**Classification:** searchable workflow and documentation traceability catalog.
**Owner:** STEWARD-DASHBOARD / website presentation and client-side search.

Added an on-demand catalog view fed by the existing authenticated canonical
graph index/detail APIs. It lists each returned workflow's component and graph
revision, typed process/failure/recovery nodes, allowlisted component-doc links,
source references, and declared verification references. Search narrows matching
workflow entries and their nodes/references. Activity and Workflows diagnostic
shortcuts now open this catalog. No backend, API, authorization, CME, or graph
contract was changed. PR #40 conversation streaming and deferred-response
recovery code was not changed.

The browser fixture passed all checks in Firefox 156.0.1, including workflow
index/detail loading with the synthetic account cookie and no Authorization
header, a search resolving to the matching recovery node, documentation-tab
reuse, and no browser errors. The focused dashboard test file passed 33 tests;
8 PostgreSQL tests were skipped because `RIVERVIEW_TEST_PG_DSN` is unset.
Process graph validation passed at 19 workflows / 458 nodes. Evidence,
including retained failed attempts, is under
`evidence/checkouts/WEBSITE-PL038/`; the passing report is
`20261016T020000Z-searchable-workflow-catalog/browser-acceptance.json`.

The catalog exposes only metadata already declared by the graph registry. A
documented source freshness value and semantic test-coverage result are not
present in that contract, so the UI links to freshness guidance and states that
evidence paths do not establish a pass or prove coverage. This qualifies the
catalog rather than inventing either value. Production acceptance remains
unverified; this branch has not been deployed.

Final local verification passed: dashboard plus process-graph tests 46 passed,
8 PostgreSQL-dependent skips; graph check 19 workflows / 458 nodes; controlled
revision audit against integration commit `29d196f` passed with zero findings;
`git diff --check` passed. PR #42's previous exact-head CI failed only because
the retained PL-016 failed browser attempt lacked `artifacts.json`; that
timestamped evidence directory now has a checksum manifest without changing or
deleting its artifacts. The integration branch advanced with merged PR #45
after the PR #44 baseline; this website branch is being reconciled before the
next exact-head CI run.


## 2026-10-16 UTC — RV-WEBSITE-PR45-RECONCILE

Fetched the integration branch and found merged PR #45 at
`ef73c6d6410cd30e00ebda6d68ee76e5a35a10f6`, after the previously recorded PR
#44 baseline. Merged that integration head into `codex/website-improvements`.
Resolved shared dashboard JavaScript, HTML, test, and revision-manifest
conflicts by retaining the website improvements and PR #45's same-source
work-order retry behavior. The regression test for immutable criteria reuse,
authority recheck, and origin conflict is retained. Codex 1's server and
resident-execution changes were brought in from the integration branch without
being edited in the website worktree. Canonical graph generation now reports
19 workflows / 459 nodes. Post-merge dashboard and process-graph tests passed
47 tests with 8 PostgreSQL-dependent skips; the Firefox account-cookie regression
passed all 35 checks with zero browser errors. Revision audit against PR #45 and
source diff checks passed. The first revision audit identified missing exact
predecessors for the revision manifest, generated graph, shared client script,
and dashboard tests. Restored those exact PR #45 integration-head bytes long
enough to capture verified backups, then reran the audit with zero findings.


## 2026-10-16 UTC — RV-WEBSITE-PR46-RECONCILE

Before controlled PR #42 review, fetched the integration branch again and found
merged PR #46 at `8f95c83af4e3a6269b25d96e1092baf8175e431c`. Its changes add
bounded repository grounding in `resident_knowledge.py` and update related
reasoning/Engineering documents, tests, and process graph. Merged this current
integration head into the website branch. The resident-knowledge implementation
and its tests/docs were included unchanged from integration; no resident
reasoning behavior was edited in the website worktree. The graph generator and
controlled revision audit pass after reconciliation. A new exact-head CI run is
required for the updated website PR head.
## 2026-10-15 UTC — RV-GRACE-WORKORDER-RECOVERY-001

The authenticated production intake for conversation
`269535bd-8556-41f2-9d42-3b722837fbab`, source sequence 6, returned HTTP 409
`work_order_conflict` after persisting objective
`objective:grace-conversation:2c573041-cc5e-4b54-9f93-8163de91e52c` and its
`objective.received` event. Metadata showed `WAITING_FOR_EVIDENCE`, zero source
references, `retrieval_complete=false`, and repository source revision
`64e8f14ad6d71102a864755739a1c8a61506235c`; no assignment or proposal existed.
The active dashboard was release `665ae8100a50faa26985b0cfee8834e68bf2a847`,
but its default knowledge root resolved through `/opt/riverview-core` to the
older 64e8… checkout. Because that checkout did not match the dashboard's
verified package revision, the knowledge provider correctly failed closed.
The route then incorrectly translated the post-persistence grounding wait into
a conflict response. No prior objective collision caused this incident.

The bounded correction makes a packaged dashboard use its own immutable
release as the default knowledge root (an explicit configured root still wins),
returns the existing durable wait state as a receipt, and resolves retries by
authenticated conversation/message origin so the same objective is reused.
Exact source, criteria, scope, submitter, current authorization, and evidence
verification remain required. A different request for the same origin fails
closed. No production row was deleted or rewritten, no assignment was
fabricated, and no production configuration was changed during diagnosis.
Regression coverage verifies package-root selection, same-origin retry without
duplicate submission, and changed-criteria conflict. Production retry and the
subsequent CME/Codex/verifier cycle remain pending a reviewed release and the
Steward's same-message retry through the authenticated website.

## 2026-10-15 UTC — RV-GRACE-WORKORDER-RECOVERY-001

The authenticated production intake for conversation
`269535bd-8556-41f2-9d42-3b722837fbab`, source sequence 6, returned HTTP 409
`work_order_conflict` after persisting objective
`objective:grace-conversation:2c573041-cc5e-4b54-9f93-8163de91e52c` and its
`objective.received` event. Metadata showed `WAITING_FOR_EVIDENCE`, zero source
references, `retrieval_complete=false`, and repository source revision
`64e8f14ad6d71102a864755739a1c8a61506235c`; no assignment or proposal existed.
The active dashboard was release `665ae8100a50faa26985b0cfee8834e68bf2a847`,
but its default knowledge root resolved through `/opt/riverview-core` to the
older 64e8… checkout. Because that checkout did not match the dashboard's
verified package revision, the knowledge provider correctly failed closed.
The route then incorrectly translated the post-persistence grounding wait into
a conflict response. No prior objective collision caused this incident.

The bounded correction makes a packaged dashboard use its own immutable
release as the default knowledge root (an explicit configured root still wins),
returns the existing durable wait state as a receipt, and resolves retries by
authenticated conversation/message origin so the same objective is reused.
Exact source, criteria, scope, submitter, current authorization, and evidence
verification remain required. A different request for the same origin fails
closed. No production row was deleted or rewritten, no assignment was
fabricated, and no production configuration was changed during diagnosis.
Regression coverage verifies package-root selection, same-origin retry without
duplicate submission, and changed-criteria conflict. Production retry and the
subsequent CME/Codex/verifier cycle remain pending a reviewed release and the
Steward's same-message retry through the authenticated website.


## 2026-10-15 UTC — RV-GRACE-AUTHORIZED-SNAPSHOT-001

After deployment of the 60-second proposal deadline, the existing objective
`2c573041-cc5e-4b54-9f93-8163de91e52c` reached model inference but proposal
persistence failed during post-inference authority revalidation. The owner
service reported only the sanitized `RegistryUnavailable` category. A read-only
reproduction with the production runtime role confirmed SQLSTATE 42501 when it
selected protected office-binding tables directly; the role is intentionally
limited to the approved `read_authorized_office_state` and
`write_authorized_office_state` functions. No authority ACL was widened and no
objective or conversation row was changed.

The correction replaces the direct post-provider `office_snapshot` call with
`authorize_office_state`, so the original exact office-state grant, current
occupant, active binding and implementation revisions are rechecked through the
existing narrow security-definer API before the proposal is persisted. A
restricted-login PostgreSQL regression denies direct `office_bindings` reads
while the proposal succeeds and persists through the allowed functions. Focused
resident reasoning tests pass 15/15; full isolated-suite verification is in
progress. The live objective remains grounded with no assignment until this
correction is integrated and deployed.

## 2026-10-16 UTC — RV-GRACE-VERIFIER-REVALIDATION-001

Read-only production metadata for the existing objective and assignment showed
one successful Codex attempt, one immutable REJECTED decision under verifier
revision 1.0.0, and an assignment still requiring rework. The artifact digest,
pinned source/repository provenance, assignment binding, file mode, and size
checks passed. The acceptance check failed because task instructions were tested
as literal artifact prose, including the citation heading and its separately
listed file paths. The stored result predates source-file inventory fields, but
its exact registered capability has a fixed deliverable.md output contract and
persisted only after the pinned clone's changed-path check.

The development correction adds strict structured checks for the known task
contract, requires the exact declared citation count, and retains literal
matching for unknown criteria. It preserves the old decision and appends a
new verifier-revision decision only after the same exact verifier grant, same
assignment/attempt, deterministic idempotency key, and independent artifact
reopen checks pass. A durable accepted decision with an interrupted state
transition is retried idempotently without rerunning Codex. A disposable
PostgreSQL regression reproduced the rejection, revalidated the same artifact,
and confirmed original-decision preservation and one attempt. No production
records were modified.


## 2026-10-16 UTC — RV-WEBSITE-PR42-INTEGRATION-RECONCILE

Fetched the current integration branch after PR #46 and found it advanced through
merged PRs #47–#63 to `af87c1a1b8ef4deeb8770c64da8bb4556bc85866`. The branch
contains PRs #44–#46 and the later Engineering commissioning corrections. The
website change has no functional source or test-file overlap with commits after
PR #46; the shared records are the revision manifest, revision index, journal,
and generated aggregate graph. Reconciled the append-only records and regenerated
the aggregate graph without editing the integrated Engineering implementation.

The combined tree passed full unittest discovery: 466 passed, 160
PostgreSQL-dependent tests skipped because `RIVERVIEW_TEST_PG_DSN` is not
configured. Process graph validation passed at 19 workflows / 478 nodes; the
controlled revision audit passed with zero findings. The account-cookie Firefox fixture was rerun after the merge and passed with no
browser errors: both registry/detail reads carried the synthetic account cookie,
omitted Authorization, and rendered the fixture node. Report: `evidence/checkouts/WEBSITE-PR42-INTEGRATION/20261016T164500Z-account-cookie/`. Exact-head controlled CI run `38934516118` passed on merge commit
`7ba28efa8591ffd91fbb55f62c1024457f427936`: 466 tests passed, 2 skipped;
process graph and controlled revision checks passed. The independent Firefox
account-cookie report is checksummed under
`evidence/checkouts/WEBSITE-PR42-INTEGRATION/20261016T164500Z-account-cookie/`.
A following documentation-only commit requires its own exact-head CI run.

PR #42 remains draft with no submitted review or requested reviewer. Its base
branch advanced, and GitHub reported the former head as dirty. The punch list
records the current integration baseline and release gates. No production
package, service, objective, or database was changed.


## 2026-10-16 UTC — RV-WEBSITE-PR42-EXACT-CI

The current integration merge `7ba28efa8591ffd91fbb55f62c1024457f427936`
passed exact-head controlled CI run `38934516118` (466 tests, 2 skipped; graph
19 workflows / 478 nodes; revision audit PASS). Isolated Firefox account-cookie
verification passed against the reconciled website source with no browser errors;
registry and detail requests carried the synthetic account cookie without an
Authorization header. This is fixture evidence, not production acceptance. A
documentation-only follow-up is being committed separately, so its new commit
needs its own exact-head CI. PR #42 remains draft and unapproved.


## 2026-10-16 UTC — RV-WEBSITE-SNAPSHOT-041 actual-dashboard snapshot verification

The isolated Firefox harness now serves the repository's actual dashboard HTML,
CSS, and application scripts with synthetic, read-only API and account-session
fixtures. The completed desktop and 720-pixel browser runs each produced a
complete CRC-valid ZIP under the 96 MiB bound. They captured all 10 registered
pages, 55 controls with zero uncovered rendered controls, and the 20 canonical workflows (494 nodes, 656 edges, 26
cross-workflow references) without browser errors. The documentation page was
captured to its full 20,067-pixel desktop and 42,192-pixel narrow extents using
12 and 25 readable detail tiles respectively. Workflow JSON and SVG remained
byte-identical across viewport and scroll changes. Focused dashboard tests
passed 37/37; 8 PostgreSQL-dependent tests were skipped. Evidence:
`evidence/checkouts/WEBSITE-SNAPSHOT-041/20261016T-snapshot-actual-dashboard-final9/`.
The API/session values and release identifiers are synthetic; Camrui was not
accessed and production account/session acceptance remains unverified.

## 2026-10-16 UTC — RV-M33-DECOMMISSION-001 — expired commissioning decommission

With explicit Steward authorization, stopped only the assignment intake, M33
executor, and M33 verifier, then ran the deployed M33 revocation helper for
commissioning run `e92ec51590b34cd3b04d05c000f3eab4`. The helper revoked its five
exact grants and all worker credentials for the run, removed the four expected
protected credential/config files, and retained the state record as `revoked`.
Four completed and one `WAITING_FOR_EVIDENCE` assignment remained unchanged; no
ready, running, or awaiting-verification assignment existed. The services
remain stopped. PostgreSQL read-only verification, Grace, CME, event processor,
notification dispatcher, dashboard, and unrelated Grace workers remained
operational. No timestamps, schemas, assignments, Grace authority, or unrelated
credentials were changed. Pre/post metadata, unit/dependency checks, assignment
comparison, and redacted helper outcome are recorded in
`evidence/checkouts/M33-DECOMMISSION/20261016T231925Z-e92ec515/`; the exact
predecessor state JSON is protected under `/var/lib/riverview-m33-worker/`.
The M33 run was a finite test commissioning, not standing production authority.
The existing helper does not support another run after revocation; future
activation requires separate reviewed commissioning work and authorization.

## 2026-10-16 UTC — RV-WORKER-REGISTRY-RETIRE-001 — fixed M33 registration retirement

The Steward supplied a live seven-row inventory: five active registrations
(three Grace, two revoked-run M33) and two inactive historical M31 rows. Added a
fixed root-local retirement operation that requires the exact revoked M33 state,
active Steward `identity.manage` authority, all three M33 units stopped, no
effective M33 worker authority/credentials, no active lease or executable M33
assignment, and the expected exact inventory. Its database transaction changes
only the two M33 `active` flags and appends two authority events; it verifies the
three Grace IDs are the only active rows afterward. Authority migration 0009
adds only the event type. Regression tests, troubleshooting procedure, and a
canonical process graph were added. The Linux session still has no usable
Windows SSH bridge and direct SSH remains denied, so the migration and helper
were not run on production; live registry count remains unverified after this
source change. Predecessors are recorded in `.riverview-backups/manifest.jsonl`.

## 2026-10-16 UTC — RV-WEBSITE-PR67-SNAPSHOT-CSP-FIX

Installed the Steward-authorized f957 integration release after validating and
restoring the protected database backup into a disposable database. Applied
checksum-matched migration 0010 and verified its production ledger row, five
registry tables, scoped grants, zero proposal rows, unchanged existing
assignments/objectives, and service continuity. The immutable release is active;
the PR #42 release and rollback evidence remain intact. Strict HTTPS and the
authenticated read-only dashboard projection are healthy. Live Firefox verified
the existing completed objective/assignment projections, attention, CME,
workflow rendering/navigation, and documentation links without browser errors.
Steward account-cookie APIs, proposal reads, SSE/reconnect, and mutating objective
intake were not tested without a legitimate existing account/conversation
session.

The production one-button snapshot generated a CRC-valid ZIP with all canonical
workflow JSON, SVGs, node/edge identities, and cross-workflow links, but its
manifest correctly reported incomplete page and PNG capture. Evidence isolated
the PNG failure to the page CSP (`img-src 'self' data:`) rejecting the collector's
Blob URL; a captured restricted-page outcome also lacked its expected omissions
array. PL-NEW-043 records these corrections. The collector now uses the already
allowed data image scheme and normalizes inaccessible page outcomes. The actual
dashboard browser harness was updated to run under the production CSP; Firefox
verified all 10 pages, 55 controls, 20 workflows (494 nodes / 656 edges), valid
page/workflow PNGs, complete manifest hashes, viewport-independent workflow
visuals, and zero browser errors. This isolated API-fixture pass does not claim
the code correction is deployed. Sanitized release and regression evidence is
under `evidence/checkouts/WEBSITE-PR67-SNAPSHOT-CSP/20261016T211638Z/`.

## 2026-10-16 UTC — RV-PROPOSAL-AUTHORING-GUIDANCE

Added `docs/operations/INSTITUTIONAL_PROPOSAL_AUTHORING.md` as a concise
source-to-registry guide and linked it from `AI_HINTS.md` revision 1.0.5. The
playbook follows the eight proposal content fields and separate source-reference
and server-provenance contract in `docs/components/INSTITUTIONAL_PROPOSALS.md`.
It covers validation, idempotent retries, immutable revisions, Steward-only
registry access, and the distinction between proposals and execution authority.
The predecessor copies for `AI_HINTS.md` and this journal are recorded in
`.riverview-backups/manifest.jsonl`. Documentation checks, `git diff --check`,
and the controlled revision audit against the f957 integration inventory passed.
This is a separate documentation PR and is not included in the Camrui release.

## 2026-10-16 UTC — RV-WEBSITE-PR71-PRODUCTION-ACCEPTANCE

PR #71’s former `DIRTY/CONFLICTING` state was traced to append-only conflicts in
`.riverview-backups/manifest.jsonl` and `docs/development/JOURNAL.md` after PR #70.
The branch was reconciled against PR #70’s merged target, retaining both backup
records, both journal entries, AI_HINTS and the proposal-authoring playbook. The
predecessor journal bytes were preserved and checksum-registered. The merged PR
#71 head was `fd09129bbadd44738ac38fde837e37164f243964`; exact-head controlled CI
run `38972694228` passed (484 tests, 2 skipped; 20 graphs / 494 nodes; revision
audit zero issues). The reviewed change was confined to CSP-safe `data:` SVG
rasterization, explicit unavailable-page outcomes, and the production-CSP fixture.
PR #71 merged as `50e1e44b498927e5df67e5c08aec3cda8267dd72`; PR #69 remains open
and was not part of the package.

Package `c60f7fca6325ed2a746c8a611cb0b9b5fc4afb64508401166c2770ab4f106a53` passed
`verify_camrui_package.py` and was installed immutably at
`/opt/riverview-status-dashboard/releases/50e1e44b498927e5df67e5c08aec3cda8267dd72`.
The previous f957 release remains the rollback target at
`/opt/riverview-status-dashboard/releases/f957bddb5eda39d4fbd5860ee29f7c32831553b7`;
root-only release/prestate evidence is at
`/var/backups/riverview-status-dashboard/website-pr71-20261016T220335Z/`. Only the
dashboard release link, release-identity drop-in and dashboard service changed.
No migration, database record, grant, or other service was changed. All 21
production migration entries matched integrated migration sources; 0010 was
already applied. Read-only counts remained one objective, ten assignments and
zero proposals. The dashboard and all checked units were active with zero
dashboard restarts. Grace and CME projections were healthy; the worker projection
remained stale both before and after while worker units were active.

Strict HTTPS passed both curl (200, verification result 0) and headless Firefox.
Firefox’s temporary profile imported only the verified local Riverview CA;
`acceptInsecureCerts=false`. Using the existing protected dashboard recovery
token, the browser navigated all eight visible dashboard views and downloaded a
57,940,967-byte CRC-valid ZIP (SHA-256
`5e908c300943ad4daeff5021633531ece87b6435991852c6e377abd6f4d90c12`). Manifest
hashes passed; all 20 canonical workflow JSON/SVG/PNG exports matched node/edge
identity (494 / 656), with 26 cross-workflow references and zero unresolved
references. All 28 page PNGs had valid signatures. The manifest correctly states
8/10 pages and `capture_complete=false`: Account and Resident Permissions are
hidden from this recovery-token session. The ZIP did not contain the token; 37
recorded API calls were GET and there were no JavaScript errors. Two initial 401s
were unauthenticated pre-login probes; the account-cookie-only conversations GET
returned 403. No session-creation POST, SSE request, objective, conversation,
proposal or other production mutation was made. Account-cookie login and production
SSE/reconnect acceptance remain unverified. No rollback was needed. Evidence:
`evidence/checkouts/WEBSITE-PR71-PRODUCTION/20261016T220708Z-50e1e44/`. The canonical
workflow graph was unchanged because this fix did not alter workflow semantics.

### RV-WORKER-HEALTH-REPORTING-001 — Worker health investigation

Production `/api/v1/workers` and status observations on 2026-10-16 reported five active registry entries: two with stale latest lease heartbeats and three without a lease heartbeat, all with zero active leases. Available assignment data contained historical successful attempts for two entries, no attempts for three, three old ready assignments, and one blocked assignment. This does not establish the current process state of any worker. The status source is explicitly `assignment_leases`; continuous workers poll while idle and only heartbeat a lease while holding work. SSH read-only access to `admin1@192.168.1.155` failed public-key/password authentication, so systemd unit state, journals, and the processor's durable consumer cursor could not be inspected. The event cursor is the newest committed institution event and is not a consumer cursor. The projection was not proven incorrect as a lease-health projection; its overview presentation could imply process health. Corrected dashboard labels/docs and added regression coverage without introducing a new heartbeat subsystem. Production process-state diagnosis and normal-cookie browser acceptance remain blocked on authorized access.


## 2026-10-16 UTC — RV-EXTERNAL-MCP-ADAPTER-001 integrated verification

PR #69 was reconciled against the latest integration base `5221da72286aea73bed2fb1ac9aa043a120df2bd` at merge commit `1359019ed377b791ac5b4004a6ca09d735e6797a`. The append-only backup manifest and revision inventory conflicts were resolved by preserving records from both branches. The integrated repository suite passed **501 tests, 0 failures, 0 skips** against a disposable PostgreSQL 16.15 cluster on port 55494 (416.430 seconds). Canonical process graph check passed at 20 graphs / 513 nodes; controlled revision audit passed with zero issues; changed Python compilation and `git diff --check` passed. Independent loopback MCP client and durable PostgreSQL exchange tests passed. Evidence is recorded at `evidence/checkouts/EXTERNAL-MCP-ADAPTER/20261016T230300Z-1359019/`. PR #69 remains open and unmerged; no production migration, deployment, public route, or ChatGPT configuration occurred. External-network reachability is unverified. Predecessor journal: `.riverview-backups/20261016T230217899962Z/docs/development/JOURNAL.md`.

