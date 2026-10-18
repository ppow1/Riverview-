<!--
Riverview Controlled Document
File: docs/development/P0_CONTROLLED_INTEGRATION_MANIFEST.md
Component: P0-CONTROLLED-INTEGRATION
File Revision: 1.0.0
Status: Disposable integration manifest; no merge/deployment authority
Date: 2026-10-18 UTC
Purpose: Record exact integration parent, published component heads, ownership, order and verification state for P0 Grace-to-ChatGPT review
Authority: Steward dispatch issue #120 comment 6254574126; W3 may assemble branches and run offline tests only
History: New file; no predecessor
-->

# P0 controlled integration manifest

## Integration checkout

| Item | Value |
|---|---|
| Repository | `ppow1/Riverview-` |
| Integration branch | `codex/w3-p0-controlled-integration-20261018` |
| Disposable worktree | `A:\AI\Riverview-Development\W3-P0-Controlled-Integration` |
| Selected parent | PR #119 head `97128626df967bc992696dca38eaa7116f3616e9` (`codex/riverview-pr115-migration-acl-fix-20261018`) |
| Initial integration HEAD | `97128626df967bc992696dca38eaa7116f3616e9` |
| State | Offline source assembly only; PR #119 and all component PRs remain open/unmerged; no production changes |

The integration worktree is separate from W3 PR #129, W3's former Jessica-recovery worktree, and all component-owner worktrees. Owner branches are inputs; W3 will not amend, force-push, or rewrite them. Preserve each complete source commit, backup artifact, owner revision record, and provenance. W3 may cherry-pick only its owned workflow document from PR #129 because that branch was based on `main`, not the selected PR #119 parent.

## Published component input manifest

Refs and exact heads were checked with `git ls-remote` and GitHub PR metadata before assembly. Order follows the dispatch: C3/C4/C2 critical path, then W2 acceptance, C1 readiness, W1 trace, W3 workflow documentation.

| Order | Owner / responsibility | Published input | Exact head at dispatch | Owned paths (summary) | Integration state |
|---:|---|---|---|---|---|
| 0 | Base / selected integration parent | PR #119 | `97128626df967bc992696dca38eaa7116f3616e9` | Deferred-retry ACL correction atop selected reasoning integration | Selected parent; open PR |
| 1 | C3 / exact proposal subject, durable exchange, doorbell claim/receipt and Grace owner loop | `codex/c3-exact-proposal-review-20261018` | `5c4a00512e5acd6f72aa766ea866a8828184b151` | `resident_reasoning.py`; resident execution exchange/service/pipeline; typed proposal/exchange tests and docs | Published branch; owner says remaining atomic doorbell/owner-loop work is in progress; integrate available head and leave slot explicit |
| 2 | C4 / provider MCP subject validator and digest echo | PR #130, `codex/c4-external-review-mcp-20261018` | `01fb2cea51158352a71b0191a94582ce567dbe10` | `external_reasoning_mcp.py`, MCP tests, runner, preflight/docs/evidence | Published, exact-head CI reported pass; assemble after C3 |
| 3 | C2 / eligible exchange to existing fixed browser wake | PR #131, `codex/c2-chatgpt-doorbell-worker-20261018` | `1123f3f356c121376591e9a3aa478b95939d2f58` | Doorbell bridge/dispatcher, Node runtime, tests, component docs | Published, exact-head CI reported pass; assemble after C3 API |
| 4 | W2 / disposable PostgreSQL full-flow and recovery acceptance | PR #132, `codex/w2-p0-review-recovery-20261018` | `ab87e2fba4c2ca592ffebe991ec783ee23e673b0` | `tests/test_w2_p0_review_recovery.py` | Published, reported CI pass; execute on combined head |
| 5 | C1 / redacted failure/readiness projection | PR #133, `codex/c1-review-readiness-20261018` | `01bbf1587446c6b5975cc6cfe5c5af0138c3a957` | `external_review_readiness.py`, focused tests/docs | Published, reported CI pass; check against C2 trigger status and C4 provider metadata |
| 6 | W1 / read-only correlation trace | PR #134, `feature/w1-external-review-trace-pr119` | `a5343630ab6b5c292691daea7c3b72a53297d950` | `external_review_trace.py`, CLI, tests/docs | Published, focused 21 tests reported; assemble after owner event names are verified |
| 7 | W3 / workflow and acceptance proposal | PR #129, `codex/w3-p0-graph-acceptance-20261018` | `86808acb25da937c6af406c2d592563da69f08f1` | Only `docs/architecture/GRACE_EXACT_PROPOSAL_REVIEW_WORKFLOW_PROPOSAL.md` | Published, both controlled-checkout jobs pass; cherry-pick only the W3-owned document |

Reported owner CI/results in this table are provenance at dispatch, not integration evidence. Re-verify fetched ref hashes before each import. Record the imported commit(s), exact combined HEAD, focused test command/result and any conflict disposition below or in the integration issue handoff. Never mark an input integrated from a component-only CI result.

## Assembly order and gates

1. Verify base and owner ref hashes; preserve this manifest and exact selected parent.
2. Integrate the current published C3 branch without cherry-picking over uncommitted owner work. Inspect its exact API/event names and run focused exchange/Grace tests.
3. Integrate C4 validator/MCP shape correction; verify typed steps remain intact, canonical digest is preserved, and focused provider tests pass.
4. Integrate C2 worker only after its claim/receipt calls match C3's current published signatures; run dispatcher/browser offline tests with synthetic store/runner. Do not wake the real browser.
5. Integrate W2 test module and run the combined disposable PostgreSQL end-to-end/recovery scenario; record test fixture DSN provenance without printing credentials.
6. Integrate C1 and W1 after matching their projections to current C2/C3/C4 metadata/event names; run focused redaction/trace tests.
7. Import W3's single document only. Reconcile the proposed workflow against actual source and update exact event names. Canonical graph registration and generated projections require an integration-owner review of the combined tree, revision sidecar repair provenance, and graph checks; do not silently rewrite shared history.
8. Run affected suites, graph and revision checks, exact-head CI, diff/secret checks, and document skipped tests and live commissioning gates. Keep this branch offline and unmerged.

## Integration ledger

| Stage | Exact imported commit(s) | Combined HEAD | Focused verification | Status / blocker |
|---|---|---|---|---|
| Base established | `97128626df967bc992696dca38eaa7116f3616e9` | `97128626df967bc992696dca38eaa7116f3616e9` | Ref verification; working tree clean | PASS; waiting on owner import sequence |

## Boundaries

- No merge to `main`, production deployment/migration/service restart, credentials/grants change, or live browser/ChatGPT request.
- Existing resident and proposal authorities stay intact. External review is advisory; only Grace may evaluate exact proposal versions; existing Steward approval and execution authorities remain separate.
- Component interfaces and status are reported only when observed at the assembled exact HEAD. Missing integration remains an explicit slot/blocker, not a green status.
- The eventual live smoke remains a separate approval with exact payload digest, destination, authority, one-message side effects, timing and stop conditions.
