<!--
Riverview Controlled Document
File: docs/development/P0_CONTROLLED_INTEGRATION_MANIFEST.md
Component: P0-CONTROLLED-INTEGRATION
File Revision: 1.0.4
Status: Disposable integration manifest; no merge/deployment authority
Date: 2026-10-18 UTC
Purpose: Record exact integration parent, published component heads, ownership, order and verification state for P0 Grace-to-ChatGPT review
Authority: Steward dispatch issue #120 comment 6254574126; W3 may assemble branches and run offline tests only
History: 1.0.0–1.0.2 predecessors backed up in .riverview-backups/manifest.jsonl; 1.0.3 records latest C1 import and hosted acceptance findings
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


## W3 integration checkpoint — 2026-10-18

The disposable branch now assembles the published owner inputs in the dispatch
order. Exact integrated commits and merges are preserved in Git history. The
branch head after the W3 workflow proposal cherry-pick is
`683be8b581c1d14b78c3d91ae1aa5aa61b497f81`.

| Owner | Integrated source head | Integration note |
|---|---|---|
| C3 | `5c4a00512e5acd6f72aa766ea866a8828184b151` | Exact-proposal exchange and Grace consumption path integrated. Doorbell claim/receipt exchange methods and owner-loop registration remain missing at this head. |
| C4 | `49f5dcfb` (`Align MCP review subjects with typed proposals`) | Latest C4 branch integrated after the original PR #130 head; validator normalizes complete typed `PlanStep` objects into a `PlanProposal`. |
| C2 | `1123f3f356c121376591e9a3aa478b95939d2f58` | Offline dispatcher and bridge integration; depends on the missing C3 methods. |
| W2 | `ab87e2fba4c2ca592ffebe991ec783ee23e673b0` | Combined PostgreSQL acceptance test added. |
| C1 | `01bbf1587446c6b5975cc6cfe5c5af0138c3a957` | Readiness projection integrated. |
| W1 | `c871ff069f99abe1d25dbf9d695ef64aa5ed2140` | Latest published trace branch integrated. |
| W3 | `86808acb25da937c6af406c2d592563da69f08f1` | Only the owned workflow proposal document was cherry-picked. |

Backup-manifest conflicts were resolved append-only: each resolution retained the
current integration file byte-for-byte and appended only unique owner records in
their original order. No existing record was removed or reordered.

### Isolated validation at this checkpoint

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_external_reasoning_mcp tests.test_external_reasoning_doorbell_dispatcher tests.test_w2_p0_review_recovery tests.test_external_review_trace tests.test_grace_router_readiness -v
```

Result: 33 passed, 6 skipped, 1 import error. All 11 synthetic doorbell dispatcher
cases and all W1 trace cases passed. The C4 MCP test module could not import because
`PyJWT` (`jwt`) is absent from this disposable Python environment. The six skipped
tests require `RIVERVIEW_TEST_PG_DSN`, which is not configured here. No dependency
was installed and no live browser wake was sent.

### Open integration dependency and next action

C2's dispatcher calls `claim_next_doorbell_request` and
`record_doorbell_receipt`, but those methods are not implemented by the integrated
C3 exchange. The Grace owner loop invokes `consume_external_reasoning()` but does
not register the doorbell dispatcher. This blocks the end-to-end test and remains
assigned to C3. Integrate the published C3 follow-up when it appears, then run
W2's combined PostgreSQL test against an isolated DSN and rerun the C4 MCP tests
in an environment with declared test dependencies. Existing graph registration,
revision audit, and the Steward-authorized live smoke remain separate gates.


## Integration closure checkpoint — 2026-10-18 20:44 UTC

Latest available owner branches have been assembled on the W3 integration
branch. The code and graph verification checkpoint is `d138e35269252d5bab0d0ee99be4fd3ec1c5cfc6`.

| Owner | Exact integrated head | Closure result |
|---|---|---|
| C3 | PR #135 `d9506bf858ff72b2942f64171eb8c15b740cee20` | Durable body-free doorbell claim and receipt are implemented; optional owner-cycle hook is present. C3 integrated verification response is still requested. |
| C2 | PR #131 `479ea738e541dbf413236476a82b24811a7f5d44` | Default-off Grace owner-session composition is integrated. Synthetic runtime test proves one claim and one receipt; actual C2 owner verification is still requested. |
| C4 | PR #130 `45807c642040ba3b48fdb51e6f5f3d1219e23a06` | Expired MCP submissions now return explicit non-success without response digest. Regression passed. |
| W2 | PR #136 `8b4dcd0f9291f2c7c61bf47047063c8f33ffbea1` | Updated integrated acceptance tests are included. The branch CI was pending at this checkpoint; local PostgreSQL acceptance was skipped without a test DSN. |
| W1 | PR #134 `c871ff069f99abe1d25dbf9d695ef64aa5ed2140` | Trace component is integrated; actual trace evidence from the W2 disposable event/status snapshot remains pending. |
| C1 | PR #133 `01bbf1587446c6b5975cc6cfe5c5af0138c3a957` | Readiness component is integrated; actual readiness evidence on the closure branch remains pending. |

### Combined validation

The following focused command ran on the assembled closure branch with PyJWT 2.10.1
in a temporary test-only dependency directory:

```powershell
$env:PYTHONPATH="$env:TEMP\rv-p0-pydeps;src"; python -m unittest tests.test_external_reasoning_mcp tests.test_external_reasoning_exchange tests.test_external_reasoning_doorbell_dispatcher tests.test_grace_doorbell_runtime_wiring tests.test_w2_p0_integrated_review_acceptance -v
```

Result: **56 tests ran, 34 passed, 22 skipped**. Skips are all PostgreSQL tests
because `RIVERVIEW_TEST_PG_DSN` was not configured. The C4 expired-response MCP
regression, C3 typed-subject unit checks, C2 synthetic dispatcher cases and C2
owner-session runtime tests passed. No real browser or ChatGPT wake occurred.

`python scripts/process_graph.py generate` synchronized the canonical runtime
graph with the generated aggregate and resident reasoning view. Graph validation
and generated-view check pass: 22 graphs / 573 nodes. Revision-control audit against
the selected PR #119 baseline passes. `git diff --check` passes in the LF validation
checkout; this avoids Windows `core.autocrlf` changing checksummed JSON bytes.

### Remaining acceptance evidence

- W2 must execute the combined PostgreSQL tests on a disposable test database and
  report the exact integration SHA.
- C2 and C3 must confirm the integrated owner-loop / exchange connection against
  this exact branch.
- W1 must run its projector against the actual W2 synthetic event/status snapshot.
- C1 must produce its redacted go/no-go from the actual integrated runtime state.
- These offline integration checks do not demonstrate an actual ChatGPT review.
  No live doorbell, production activation, deployment, credential or grant change
  was performed.


## Latest closure evidence — 2026-10-18 20:47 UTC

Published W3 head: `8203370f8deb518e87d7822cf54e090d077400d3`. This includes C1's
latest PR #133 head `d9a8332006d59c443473ea7ef8b1b45e0271bbb6` with expiry-specific
fail-closed readiness regressions. C3 #135 (`d9506bf8`), C2 #131 (`479ea738`), C4
#130 (`45807c64`), and W2 #136 (`8b4dcd0f`) remain integrated.

Expanded integrated unit selection:

```powershell
$env:PYTHONPATH="$env:TEMP\rv-p0-pydeps;src"; python -m unittest tests.test_external_reasoning_mcp tests.test_external_reasoning_exchange tests.test_external_reasoning_doorbell_dispatcher tests.test_grace_doorbell_runtime_wiring tests.test_w2_p0_integrated_review_acceptance tests.test_external_review_readiness tests.test_external_review_trace -v
```

Result: **97 tests ran, 75 passed, 22 skipped**. The 22 skips are PostgreSQL-backed
cases because the local Windows environment has no `RIVERVIEW_TEST_PG_DSN`. C4
expiry regression, C1 expired-readiness regressions, C2 synthetic dispatcher/runtime
wiring, C3 subject/owner-hook unit checks, and W1 trace projector cases passed.
Graph check passes at 22 graphs / 573 nodes; revision audit against PR #119 base
passes with zero findings; LF checkout `git diff --check` passes.

Hosted W2 run #39164629198 on the prior assembled code checkpoint failed (702 tests,
15 failures, 1 error). It found: the W1 trace snapshot query selects missing event
column `created_at`; C2's dispatcher fixture uses `claim=Claim()` as a function
default, so its 80-second lease expires before those tests run in full-suite order;
W2's expiry test asserts no terminal review even though exchange expiry itself is a
terminal state; and the revise/restart acceptance cannot find the successor row.
These are assigned to W1/W2/C2/C3 owners. W2's trace snapshot failed before export,
so W1's actual database-backed projection and C1's actual integrated runtime
readiness are not yet evidenced. Owners must rerun on current W3 head after fixes.


## Mailbox #144 owner-fix integration checkpoint — 2026-10-18

Exact owner fixes imported into the controlled branch from C2 PR #131 head
`13d1730054628994daa8e2f46ee0bbe789ebd8f6` and W2 PR #140 head
`37093dc5ba15e8d7e2b61e16e51eb6976162eee3`. W3 merge commit `5c71bb6119f41a8cdec763c91d16f227a25602db`
preserves the owner commit history. C2's change is test-fixture-only: each fake
exchange gets a fresh claim lease; runtime fencing and retry semantics are unchanged.
W2's changes add the per-round `doorbell_owner_id` snapshot field and exercise
post-crash retry/restart before successor assertions.

On this assembled source state, focused local verification ran 97 tests: 75 passed,
22 PostgreSQL cases skipped because local `RIVERVIEW_TEST_PG_DSN` is unset. The
exact W2-head hosted run #39173980276 is not combined-head evidence: it ran before
C2 `13d17300` was included and failed 708 tests / 4 skips with 14 failures, 13 in
the known stale C2 claim fixture and one remaining W2 restart assertion (`3 != 2`).
C2's exact fix is now in the controlled branch; W2's remaining assertion must be
corrected by W2 before the complete hosted PostgreSQL acceptance can pass. The next
controlled run must target the combined W3 head.

The C2/W2 conflict in `.riverview-backups/manifest.jsonl` was resolved append-only:
all 3,104 records from the integration first parent were retained and 4 unique C2
records appended. The `.riverview-revisions.json` merge retained the higher owner
revision for each changed file. Before resolving either shared registry, exact first
parent bytes were backed up under `.riverview-backups/20261018T225343901244Z/` and
read-back hashes verified. The stale sidecar entry for the generated resident
reasoning flow was reconciled to its existing file revision 1.0.19 and canonical LF
SHA-256; the document content itself was not changed.

The prior LF validation checkout reported graph 22/573 PASS, revision check PASS
against PR #119, and `git diff --check` PASS. Re-run the checks against this updated
combined head after publishing. No production or live browser action occurred.
