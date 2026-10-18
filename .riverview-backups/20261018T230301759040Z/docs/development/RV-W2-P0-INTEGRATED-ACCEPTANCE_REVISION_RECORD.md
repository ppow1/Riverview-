<!--
Riverview Controlled Document
File: docs/development/RV-W2-P0-INTEGRATED-ACCEPTANCE_REVISION_RECORD.md
Component: W2-P0-INTEGRATED-REVIEW-ACCEPTANCE
File Revision: 1.0.9
Purpose: Preserve W2 integrated acceptance scope, source lineage, evidence and remaining gates
Authority: Offline synthetic test only; no production or provider authority
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Record initial C3/C4 acceptance increment
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Correct isolated provider registration after first CI fixture failure
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Assert either privacy-safe wrong-provider denial and no exchange state change
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Import MCP privacy denial from its defining module after CI fixture failure
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Make tampered-subject assertion validate rejection, not internal error wording
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Add synthetic C2 owner-hook wake and C3 single-receipt acceptance
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Fix trace timestamp, expiry boundary assertion, and use C3 successor API
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Correct per-round trace attribution and retry durable successor recovery after restart
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Record local W2 correction verification and environment limits
Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Record exact-head combined run, W1 trace handoff, and C2/C3 dependencies
History: Git; no predecessor existed for the new W2 acceptance test or cookbook
-->
# RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE revision record

## Change identity

- Component: `W2-P0-INTEGRATED-REVIEW-ACCEPTANCE`
- Owner: W2
- Revision: 1.0.6
- Source branch: `codex/w2-p0-integrated-acceptance-20261018`
- Integration base: W3 branch `codex/w3-p0-controlled-integration-20261018`, assembled head `f2de2061778f0a69aa7af38d7e60ae987f4b17f6` (C3 atomic receipt/owner loop plus C2 Grace runtime wiring)
- Selected parent: PR #119 head `97128626df967bc992696dca38eaa7116f3616e9`
- Imported components in base: C3 `5c4a00512e5acd6f72aa766ea866a8828184b151`; C4 typed subject fix `49f5dcfb674d67416a68e43f1d756230c7372e46`; prior W2 recovery test `ab87e2fba4c2ca592ffebe991ec783ee23e673b0`
- New W2 files: `tests/test_w2_p0_integrated_review_acceptance.py`, `docs/development/W2_P0_CONTROLLED_ACCEPTANCE.md`
- Predecessor backups: initial new-file versions had no predecessor. Revision 1.0.0 of the test and this record are backed up before the 1.0.1 fixture correction at `.riverview-backups/20261018T202428968484Z/tests/test_w2_p0_integrated_review_acceptance.py` (SHA-256 `03d5ae2a28c091d2a3c6283da7a8cc79327c25e740e01440025e2da2d8cd8353`) and `.riverview-backups/20261018T202429080246Z/docs/development/RV-W2-P0-INTEGRATED-ACCEPTANCE_REVISION_RECORD.md` (SHA-256 `b01cd17ec28a172e9f33ab1f3832fee3eb28d10cfe7f7ecfda5363ab0f6a2b3d`). No owner source file was edited.

## Evidence and status (revision 1.0.9)

This is a partial integrated acceptance increment, not component or system completion.

- Python compilation: PASS locally.
- Focused local unittest invocation: 3 cases discovered, all skipped because
  `RIVERVIEW_TEST_PG_DSN` is unset.
- Local Docker PostgreSQL: unavailable; Docker CLI reports that the Linux engine
  pipe is not present.
- Local C3/C4 unit import: unavailable because `PyJWT` (`jwt`) is not installed
  in this Python environment; the controlled checkout installs the declared
  dependency.
- W2 fix verification: `py_compile` PASS; `tests.test_external_review_trace`
  **22/22 PASS**; W2 PostgreSQL acceptance **3 cases discovered / 3 skipped**
  because `RIVERVIEW_TEST_PG_DSN` is unset; `git diff --check` PASS; revision
  sidecar hashes and captured predecessor backups PASS. Local process graph
  check is unverified because this Windows `core.autocrlf=true` checkout
  materializes CRLF bytes while the graph sidecar pins LF blob hashes. The
  controlled Linux exact-head workflow must run graph/revision checks after the
  PostgreSQL tests pass.
- Controlled disposable PostgreSQL CI on W2 head `37093dc5` (run `39173980276`) executed **708 tests / 4 skips**, with 14 failures. W2's trace export and finish case passed and emitted `rv.external-review-trace-input.v1`; the actual DB-derived body-free bundle was handed to W1 in issue #120 comment `6256185021`. The earlier owner attribution error and W2 expiry path are fixed. Thirteen failures remain in C2-owned dispatcher tests. One W2 restart/revision assertion is still failing: after the injected exception immediately following successor admission and a new exchange/Grace instance, retry called the reasoner again (3 provider requests versus 2 expected). W2 preserved the no-duplicate-reasoning assertion and reported this concrete C3 recovery boundary to mailbox #145 in issue comment `6256183481`, and to W3 mailbox #144 in comment `6256183665`; W2 does not modify C2/C3-owned runtime code. Graph/revision steps were skipped after the test failure, so exact-head graph/revision acceptance remains pending W3's corrected assembled run.
- First controlled run `39162955178`: **FAIL** after 690 tests / 4 skips, with 3 errors in W2 setUp. All three errors were `MCPConfigurationError(provider_not_registered)` because the negative-test provider token was not registered in the isolated exchange router. No W2 lifecycle assertion ran. Revision 1.0.1 registers that synthetic provider only in the disposable fixture; rerun pending.
- Current test scope: Grace typed review subject → durable C3 exchange → C2
  synthetic owner-loop wake → one fenced C3 receipt → C4 provider MCP
  list/claim/digest-bound submit → Grace finish or bounded successor → restart
  recovery. Negative provider, tampered typed step, wrong/missing digest,
  duplicate submission, deadline expiry, duplicate wake, and no-premature-
  finalization checks are included. The assembled exact-head PostgreSQL run
  determines acceptance.
- C4 expiry mapping was corrected in PR #130 commit `45807c642040ba3b48fdb51e6f5f3d1219e23a06` and integrated into W3's head. The W2 run verified `state=expired` and no response digest; the no-Grace-finalization assertion is now scoped to absence of reviewed/revised proposal events and a still-GROUNDED objective.
- Process graph: no runtime source behavior was changed by this test harness;
  W3 owns registering the acceptance stages and generated view in the canonical
  integration graph.
- Live browser/ChatGPT, production database, service, credential, grant, merge,
  and deployment actions: not performed.

## Verification commands

```powershell
$env:PYTHONPATH = 'src'
python -m py_compile tests/test_w2_p0_integrated_review_acceptance.py
python -m unittest tests.test_w2_p0_integrated_review_acceptance -v
git diff --check
```

Controlled PG acceptance must run only with the workflow's isolated PostgreSQL
service and unique `rvtest_*` fixture schema. Never copy a production DSN into
the test environment. The standalone workflow, failure signals, and recovery
instructions are in `docs/development/W2_P0_CONTROLLED_ACCEPTANCE.md`.

## Rollback

These are new test/documentation files, so there are no predecessor bytes to
restore. Roll back only by reverting the W2 test commit from this W2-owned
branch. Do not remove the W3 integration branch or component commits. The test
fixture owns teardown of its exact disposable schema.

## Component DoD status

The integration harness is an offline engineering acceptance artifact, not a
deployed operational component. Its implementation and local static checks are
partial evidence only. The controlled PostgreSQL run, C2/C3 worker integration,
W3 canonical graph registration, full exact-head revision/graph verification,
and remaining system-level Steward acceptance are still open. Do not report
this record or PR as satisfying the Component DoD release rule.
