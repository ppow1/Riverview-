<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/EXTERNAL-REVIEW-READINESS/20261018T2020Z-c1-p0-integration/checkout.md
Component: EXTERNAL-REVIEW-READINESS
File Revision: 1.0.4
Changed: 2026-10-18 UTC | RV-C1-P0-READINESS-INTEGRATION-001 | Correct evidence capture timestamp
Changed: 2026-10-18 UTC | RV-C1-P0-INTEGRATION-CLOSURE-002 | Record integrated-head readiness and expired-sentinel regression evidence
Changed: 2026-10-18 UTC | RV-C1-P0-INTEGRATION-CLOSURE-002 | Verify latest W3 C4 fix and exact integrated expiry result shape
Changed: 2026-10-18 UTC | RV-C1-P0-INTEGRATION-CLOSURE-002 | Capture W3 current head and failed combined PostgreSQL acceptance boundary
Task: RV-C1-P0-READINESS-INTEGRATION-001
History: Git and issue #120
-->
# C1 P0 readiness contract integration

**Recorded:** 2026-10-18 20:17 UTC
**Branch:** `codex/c1-review-readiness-20261018`
**Base:** PR #119 commit `97128626df967bc992696dca38eaa7116f3616e9`
**Input contracts inspected:** C2 PR #131 commit `e2a9cad0356d6dbdf38c7b422f299e1de0fc49fb` (doorbell worker result); C3 PR #135 commit `5c4a00512e5acd6f72aa766ea866a8828184b151` (exchange status); C4 PR #130 current follow-up commit `49f5dcfb674d67416a68e43f1d756230c7372e46` (MCP status/result contract). These are source references, not evidence of integrated runtime behavior.

## Correction

C1 now accepts C4's body-free status (`delivery_state`, request/correlation IDs,
provider ID, response digest, and optional review-subject digest), and the
correlated submit result (`state` plus response digest). It checks those values
against C3 status and fails closed on malformed digests, mismatched identity,
or mismatched provider/review digests. C2's `DoorbellCycleResult.trigger_status`
is named explicitly; only `ready` permits the initial doorbell-ready state.
Private identifiers, digests, error text, subjects, and responses remain absent
from the returned readiness object.

## Verification

- `PYTHONPATH=src python3 -m unittest tests.test_external_review_readiness -v` — **16 passed**, 0 failed.
- `python3 -m compileall -q src/riverview_core/external_review_readiness.py tests/test_external_review_readiness.py` — PASS.
- `python3 scripts/process_graph.py check` — PASS, **22 graphs / 565 nodes** on the current PR #133 branch. W3 owns the integration graph update for the new C2/C3/C4 status edges.
- `python3 scripts/revision_control.py check --baseline /tmp/c1-readiness-baseline.json` — PASS, zero findings. Baseline was inventoried from a clean worktree at the PR #119 integration parent.
- `git diff --cached --check` — PASS.

All new provider/exchange tests use synthetic metadata only. No PostgreSQL,
browser, provider, external ChatGPT, production, credential, grant, merge, or
deployment operation was performed. The full combined integration scenario
remains pending W2's disposable PostgreSQL trace export and a combined C2/C3
doorbell receipt exercise.

## Integration closure addendum

The latest published W3 integration head inspected for this closure is
`5e7f9b77ffa8f4bff760714733d872863e72cd38`. It contains C2 owner-session
composition, C3 atomic exchange claim/receipt and Grace owner-loop wiring, and
C4's corrected expiry mapping (integrated commit `dafde93f`). The C2
`DoorbellCycleResult.trigger_status` contract was checked in source: `ready` is
returned for idle/no claim and a submitted receipt, `blocked` for invalid or
failed receipt, and `unavailable` for claim/receipt failures. C3 status carries
correlation/provider identity, durable delivery state, digests, and deadline.
The C1 projection compares those fields without copying private values to its
output.

The expired exchange regression remains fail-closed when presented with C4's
prior incorrect `response_received`/`expired` sentinel mapping. It also rejects
an `expired` sentinel as a response digest. These tests ran on C1's branch (19
passed) and on a disposable overlay of W3 `5e7f9b77` plus C1 commits
`b370ef3c`, `42863b56`, and `d9a83320` (19 passed). The overlay source compiled
and graph validation passed (22 graphs / 573 nodes); it is not a published W3
commit. The corrected C4 result shape `{"state":"expired","accepted":false}`
with no digest was also projected against C3 `delivery_state=expired`: the
result was `blocked/review_expired`, `next_action=record_expiry`, with no
identifiers or response data emitted.

PR #133 exact head `d9a8332006d59c443473ea7ef8b1b45e0271bbb6` CI run
39164359352 passed: 643 tests, 4 skipped; graph validation 22 graphs / 565
nodes; revision/predecessor audit passed with zero findings. This is C1 branch
CI, distinct from W3 integration testing. W2's updated PR #136 commit
`8b4dcd0f9291f2c7c61bf47047063c8f33ffbea1` exercises the integrated C2 worker,
durable C3 receipt, provider MCP and Grace, and emits a sanitized trace
snapshot. Its controlled PostgreSQL run 39164555744 was still in progress at
this capture; C1 has not yet inspected its resulting trace. Therefore the
readiness projection contract is **PASS**, while complete offline integrated
acceptance remains **NO-GO** pending that disposable PostgreSQL result/trace.
No live ChatGPT/browser operation is claimed.


## Final closure checkpoint — 2026-10-18 20:48 UTC

W3's latest published head is `b6d475a468b57c4743b9bd60b0f24e6843d45e76`.
It includes C2/C3/C4, W2's integrated acceptance changes, and C1 readiness.
On that exact head in a detached checkout, C1 readiness tests passed 19/19,
compileall passed, `git diff --check` passed, and graph validation passed (22
graphs / 573 nodes). This validates the projection against the assembled
source, not a successful production or complete acceptance trace.

C1 PR #133 latest head `85adf1af377d03e9b0e2cab1cabbf2ad883522ad` exact CI
39164795472 passed: 643 tests, 4 skipped; graphs 22/565; revision/predecessor
audit had zero findings. Earlier code-bearing PR #133 head `d9a83320` also
passed exact-head CI 39164359352 with the same counts.

W2's combined disposable-PostgreSQL CI 39164629198 on W3 merge head
`d138e35269252d5bab0d0ee99be4fd3ec1c5cfc6` failed (702 tests, 15 failures, 1
error, 4 skipped). The observed failures include C2 doorbell dispatcher results
returning `invalid_claim`/missing outcomes; a W2 expiry assertion that treated a
terminal expired exchange as absence of any terminal review; a typed revision
assertion with no successor; and the W1 trace exporter selecting nonexistent
`created_at` from the exchange event table (the table uses `occurred_at`). No
`W2_TRACE_SNAPSHOT_JSON` was emitted. W2 and C2/W3 are correcting their owned
failures and must rerun on a new combined head.

C1 readiness status: **PASS** (redacted fail-closed projection and corrected
C4 expiry shape). Complete offline integration: **NO-GO** until the corrected
combined PostgreSQL run passes and emits the trace for C1/W1 verification.
Live ChatGPT/browser and production readiness remain untested; no live wake,
provider action, credential/grant change, merge to main, or deployment occurred.
