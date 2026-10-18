<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/EXTERNAL-REVIEW-READINESS/20261018T2020Z-c1-p0-integration/checkout.md
Component: EXTERNAL-REVIEW-READINESS
File Revision: 1.0.2
Changed: 2026-10-18 UTC | RV-C1-P0-READINESS-INTEGRATION-001 | Correct evidence capture timestamp
Changed: 2026-10-18 UTC | RV-C1-P0-INTEGRATION-CLOSURE-002 | Record integrated-head readiness and expired-sentinel regression evidence
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

The current published W3 integration head inspected for this closure is
`f2de2061778f0a69aa7af38d7e60ae987f4b17f6`. It contains C2 owner-session
composition, C3 atomic exchange claim/receipt and Grace owner-loop wiring, and
the C1 readiness projection. C1's readiness projection accepts C2's actual
`trigger_status` field and checks C3/C4 request/response identity and digest
contracts without copying private values into its output.

Two additional fail-closed regressions cover the observed C4 defect shape:
an expired C3 exchange accompanied by a provider result incorrectly mapped to
`response_received` remains `blocked/review_expired`; an `expired` sentinel
cannot be treated as a durable response digest. These tests ran on C1's branch
(19 tests passed) and were applied to a detached W3 checkout (19 tests passed).
The W3 checkout also passed `compileall` and process-graph validation (22
graphs / 573 nodes). It is a disposable verification checkout, not a published
W3 integration commit.

C4 published the correction in PR #130 head
`45807c642040ba3b48fdb51e6f5f3d1219e23a06` after the W3 head above was
published. The correction returns an explicit non-success `expired` result and
omits `response_sha256`. Its integration and exact-head CI were pending at the
time of this evidence capture. Therefore C1's offline projection is safe
against the regression, but the combined integrated behavior is **NO-GO** until
W3 includes the C4 correction and W2 exercises the actual doorbell receipt
chain with a disposable PostgreSQL trace export. No actual DB trace export was
available to C1 at capture time. No live ChatGPT/browser operation is claimed.
