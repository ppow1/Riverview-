<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/EXTERNAL-REVIEW-READINESS/20261018T2020Z-c1-p0-integration/checkout.md
Component: EXTERNAL-REVIEW-READINESS
File Revision: 1.0.1
Changed: 2026-10-18 UTC | RV-C1-P0-READINESS-INTEGRATION-001 | Correct evidence capture timestamp
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
remains pending W3/W2's assembled tree.
