<!--
Riverview~ Controlled Engineering Record
File: docs/development/RV-C3-CHATGPT-EXACT-REVIEW-001_ACCEPTANCE_RECORD.md
Component: RESIDENT-REASONING
File Revision: 1.0.1
Purpose: Record C3 exact proposal review implementation evidence, scope and operational gates
Execution Model: Offline source review and disposable test infrastructure
Observability: Linked issue, pull request, revision-keyed backups, and checkout evidence
Dependencies: PR #119 exchange integration; C2 doorbell; C4 provider MCP; W2 recovery tests; W3 canonical graph
Authority: No live provider request, browser wake, production operation, merge or deployment authorized here
Changed: 2026-10-18 UTC | RV-C3-EXACT-PROPOSAL-REVIEW-001 | Record implementation and truthful commissioning limits
Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Add durable doorbell claim/receipt wrappers, Grace cycle hook and regression evidence
Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md; docs/components/RESIDENT_REASONING.md
Tests: tests/test_external_reasoning_exchange.py; tests/test_resident_reasoning.py; tests/test_local_reasoning_provider.py
History: Git and .riverview-backups/manifest.jsonl
-->
# C3 exact proposal review acceptance record

**Task:** RV-C3-EXACT-PROPOSAL-REVIEW-001  
**Status:** Implemented and tested offline in a draft PR; integration acceptance is PARTIAL. Component is NOT DONE.  
**Owner:** C3  
**Implementation base commit:** 5c4a00512e5acd6f72aa766ea866a8828184b151; doorbell follow-up commit is recorded in Git after this record is updated.  
**PR:** https://github.com/ppow1/Riverview-/pull/135 (draft and unmerged)  
**Parent:** PR #119 head 97128626df967bc992696dca38eaa7116f3616e9  
**Checkout evidence:** evidence/checkouts/RESIDENT-REASONING/20261018T2010Z-5c4a005/checkout.md

## Implemented contract

Grace persists a typed local proposal selected for escalation as review_subject in the existing external_reasoning_exchanges.request_payload. The subject has schema rv.grace.proposal-review-subject.v1, UUID identity, bounded revision, complete execution-relevant proposal summary/step objects, and a canonical SHA-256. The digest is over UTF-8 canonical JSON {subject_id, revision, proposal} with sorted keys, compact separators, ensure_ascii=false, and allow_nan=false; schema and digest fields are excluded.

The existing delivery state, lease fencing, retries, claim, response and Grace consumption remain authoritative. Provider listing can expose the subject; body-free status returns review_subject_sha256; response submission must explicitly echo the digest, which the durable exchange revalidates. The browser worker receives only bounded metadata and continues to send the fixed wake message.

Grace evaluates the exact subject and advisory separately through its configured local reasoning provider. Escalated candidates are not stored as final office-state plans. Grace finishes only when the resulting full typed summary and step content match the reviewed subject and no new escalation is requested. A changed result creates a new immutable revision with the same subject UUID and a durable parent/child exchange link. The chain is capped at three revisions; a blocked or exhausted chain leaves the objective grounded and suppresses repeated local inference. Durable objective events are resident.reasoning.external_proposal_reviewed, resident.reasoning.external_proposal_revised, and resident.reasoning.external_proposal_review_blocked. Restart after child admission recovers the existing child link without repeating reasoning; final proposal persistence is idempotent with exchange acknowledgement.

No SQL migration or second mailbox was added. Requests without a review subject retain the previous advisory behavior. C3 added a metadata-only `claim_next_doorbell_request()` and an atomic `record_doorbell_receipt()` wrapper over the existing exchange lease and state machine. Deterministic attempt IDs are fenced by delivery fence; duplicate receipt replay verifies the owner, outcome, safe code, fence, and one-way SHA-256 of the lease token. Only C2's known pre-send failures retry through existing bounded backoff; ambiguous sends terminate without blind resend. GraceExecutionService has an optional injected `doorbell_worker.run_once()` hook in its existing owner cycle; it returns only status and isolates worker exceptions. C2 still owns constructing/injecting the browser worker in its runtime bootstrap. No browser code, MCP adapter, credentials, grants, model configuration, production service or process graph was changed by C3.

## Changed files and predecessor restoration

| File | Previous → current | Predecessor SHA-256 |
|---|---:|---|
| src/riverview_core/resident_reasoning.py | 1.0.18 → 1.0.19 | 281d107eb2f0b7b4066c0a1ba43dd189d66d6b04d63b2795ae16dc46938aa86a |
| src/riverview_core/local_reasoning_provider.py | 1.3.12 → 1.3.13 | f77bc2387f029149a0cbccc2c9496fedf984cd0d7e2364181e3b01c61dadc08d |
| src/riverview_core/resident_execution/external_reasoning.py | 1.0.4 → 1.0.5 | adad2b6350720491e924317eec8122cff0065ec1468f6f2638f8154cf96f3124 |
| src/riverview_core/resident_execution/service.py | 1.0.18 → 1.0.19 | 7a47b1a041c8c323a69292b318f2bfb1c6833bf880c58d2a833e5e467a4d1d5e |
| src/riverview_core/resident_execution/pipeline.py | 1.1.9 → 1.1.10 | 8786bfaac9c4eff98dde92d4f830f31717cb1183ebb6cabe7fa4cd83eadbc456 |
| tests/test_external_reasoning_exchange.py | 1.0.8 → 1.0.9 | c2bc9585118714182d903c7c45d020c1ac19abf1df07312c37a5f32f67022e8d |
| tests/test_local_reasoning_provider.py | 1.1.13 → 1.1.14 | ffcdfef3d547c2023ea35c3c56e7789ba7758f68f7489e8b593a7b3d59a03350 |
| docs/components/EXTERNAL_REASONING_EXCHANGE.md | 1.1.4 → 1.1.5 | 5c27a2040b7f402dbf54a583be60e2587cfbae31c19bfeb0e9e2c385e4dd3269 |
| docs/components/EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md | 1.1.5 → 1.1.6 | 4bd683546add896e5d8a7b85e7d6670a4db50469820edde54cd965ebf2db582d |
| docs/components/RESIDENT_REASONING.md | 1.0.11 → 1.0.12 | 7cb5738e1f9ca633b608358f21b7854cc765b525b4bd1759eb4246cb3d86e7a0 |

Follow-up revisions in the same isolated PR: `external_reasoning.py` 1.0.5→1.0.8; `service.py` 1.0.19→1.0.20; `test_external_reasoning_exchange.py` 1.0.9→1.0.12; and this exchange contract 1.1.5→1.1.6. Each intermediate predecessor revision is preserved in `.riverview-backups/manifest.jsonl`; the C3 follow-up acceptance record and checkout evidence have their own predecessor snapshots. The subsequent exact predecessor hashes are recorded in the checkout evidence revision audit.

All 10 predecessor copies are stored in .riverview-backups/, referenced in its manifest, and passed byte/hash comparison against base commit 97128626df967bc992696dca38eaa7116f3616e9. Detailed output is linked in checkout evidence. The new record and evidence files have no predecessor.

## Verification

At exact source commit 5c4a00512e5acd6f72aa766ea866a8828184b151 on Camrui Ubuntu 24.04 / Python 3.12.3 (initial exact-review change):

- Disposable PostgreSQL 16.15 via pg_virtualenv: exchange + resident suites 33 passed, 0 failed.
- Mocked local provider suite: 31 passed, 0 failed, including exact subject/advisory prompt binding.
- python3 -m compileall -q src/riverview_core: exit 0.
- git diff --check HEAD^ HEAD: exit 0.
- python3 scripts/revision_control.py check against the pre-edit inventory: PASS, zero findings.
- All temporary PostgreSQL schemas and the temporary cluster were destroyed after the tests.

The tests prove only offline synthetic behavior. They do not prove a real ChatGPT request, browser submission, production OAuth subject/client map, real resident.reasoning.escalate grant, Steward-visible live status, or an actual Grace cycle.

Follow-up isolated run on the current C3 branch: `pg_virtualenv -t sh -c 'export RIVERVIEW_TEST_PG_DSN=temporary-cluster; PYTHONPATH=src python3 -m unittest tests.test_external_reasoning_exchange tests.test_resident_reasoning -v'` — **37 passed, 0 failed** on disposable PostgreSQL 16.15. The new coverage verifies the metadata-only wake claim, single durable receipt, lease-token-bound idempotent replay, known pre-send retry, terminal ambiguous send, and owner-cycle worker seam. Three focused receipt tests also passed separately. `scripts/revision_control.py check` against the saved pre-edit baseline reports **PASS, zero issues**; compileall and `git diff --check` pass. Exact commit and full logs are in the updated checkout evidence.

## Component DoD Rev 1.7 status

| Gate | Status | Evidence / remaining requirement |
|---|---|---|
| 1. Code and contracts | PARTIAL | Implemented in commit/PR #135; draft PR and cross-owner typed-step contract alignment remain. |
| 2. Functionality demonstrated | PARTIAL | Disposable database and mocked provider finish/revise/restart/error tests pass; no genuine live ChatGPT round trip. |
| 3. Complete versioned documentation | PARTIAL | Exchange and resident specs/cookbook updated; full commissioned architecture and deployment/rollback remain unverified. |
| 4. Troubleshooting and recovery cookbook | PARTIAL | Exact-subject read-only diagnosis and recovery documented; production incident signals and live recovery remain unverified. |
| 5. Versioned visualization flowcharts | PARTIAL | W3 owns canonical graph and projections; C3 did not alter them. |
| 6. Steward-level live operational visualization | NOT VERIFIED | W1 PR #134 is an offline metadata projection, not an integrated live Steward view. |
| 7. Operational autonomy and blocker clearance | PARTIAL | Bounded revision/terminal recovery logic is tested; unattended service, authentication, external reachability and real recovery are not commissioned. |
| 8. Registered canonical process graph | NOT VERIFIED | W3 owns graph registration and validation; C3 makes no graph completion claim. |

## Outstanding integration and commissioning blockers

1. **C4 typed subject alignment is implemented in PR #130.** C4 updated its validator to preserve the complete typed PlanStep fields and canonical digest (issue #120 comment 6254616149). Combined exact-head acceptance remains pending.
2. **C2 runtime wiring.** PR #131 owns browser worker construction. It must inject its worker into `GraceExecutionService(doorbell_worker=...)`; the C3 owner-cycle hook and receipt APIs now exist, but the runner/bootstrap is not wired on this C3 branch.
3. **W2 combined recovery test.** Stack C2/C3/C4 and verify exact digest tamper rejection, revised successor recovery, final proposal idempotency and restart behavior.
4. **W3 canonical workflow.** Register the actual event/transition nodes and regenerate/validate projections; C3 supplied the event contract in issue #120 comment 6254390507.
5. **W1 live status integration.** PR #134 is a metadata projection only; connect it to the established Steward surface against authoritative state.
6. **Production identity and authority.** Steward/operator must provide and verify the actual ChatGPT provider ID, OAuth subject/client mapping, endpoint and existing exact escalation grant. This work created no identity or permission.
7. **Separate live authorization.** A Steward must approve one exact harmless payload, destination/conversation, effects and time window before any real browser wake. Authentication/MFA and target conversation verification must first be complete.
8. **Actual acceptance.** Independently verify durable request, C2 exact-target fixed wake receipt, ChatGPT MCP access/claim, response digest persistence, Grace finish/revise event and durable proposal. No such live evidence exists in this record.

No deployment, merge, restart, live provider request, browser wake, credential/grant change, or production database operation was performed. Keep this component NOT DONE until every applicable DoD gate is PASS with independently reproducible live evidence and Steward acceptance.
