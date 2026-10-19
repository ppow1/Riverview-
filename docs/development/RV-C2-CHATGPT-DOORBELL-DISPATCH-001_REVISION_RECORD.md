# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/development/RV-C2-CHATGPT-DOORBELL-DISPATCH-001_REVISION_RECORD.md
# Component: CHATGPT-DOORBELL
# Revision: 1.0.5
# Purpose: Record implementation and isolated validation for the C2 wake dispatcher
# Execution Model: Engineering revision record
# Observability: Source, tests, and parent commits recorded without provider content
# Dependencies: C3 durable exchange contract; existing BrowserBridgeRunner
# Authority: Offline implementation only; no live wake or production activation
# Changed: 2026-10-18 UTC | RV-C2-DOORBELL-RUNTIME-WIRING-001 | Add fail-closed owner-session composition and integration evidence
# Changed: 2026-10-19 UTC | RV-C2-DOORBELL-RESUME-20261019 | Reconcile published C3/W2 dependencies, retain exact disposable PostgreSQL evidence, add eight-deliverable status.
# Contracts: docs/components/CHATGPT_DOORBELL_DISPATCH.md
# History: Git and .riverview-backups/manifest.jsonl

## Scope

Implement C2's bounded one-cycle adapter from the existing Grace external
reasoning exchange to the fixed local ChatGPT doorbell. This branch is based on
PR #119 at `97128626df967bc992696dca38eaa7116f3616e9`. It carries forward the
existing doorbell package unchanged from `main` because the #119 integration
parent contains the exchange but predates the already implemented bridge.

The worker consumes only C3's agreed metadata claim and writes only a fenced
metadata receipt. It never reads proposal/response text, changes the browser's
fixed wake, or receives browser page content. Provider and worker identity are
injected; no identity, credential, or grant is fabricated.

## Changed files

- `src/riverview_core/doorbell/dispatcher.py` — bounded worker and exchange
  protocol.
- `src/riverview_core/doorbell/runtime.py` — default-off composition that
  requires an already registered provider and exact existing target.
- `scripts/run_grace_execution_service.py` — injects the optional worker into
  Grace's existing owner cycle and fails closed if opted in without C3's hook.
- `process_graphs/resident-reasoning/runtime.json` — owner-loop, claim, fixed
  wake and durable receipt transitions.
- `tests/test_external_reasoning_doorbell_dispatcher.py` — synthetic claim,
  bridge, receipt, failure, retry-classification, and duplicate-cycle cases.
- `docs/components/CHATGPT_DOORBELL_DISPATCH.md` — contract and operational
  limits and troubleshooting guidance.
- `tests/test_grace_doorbell_runtime_wiring.py` — disabled-by-default,
  registered-provider matching, target binding and fail-closed setup.
- Existing doorbell package, fixed bridge, local runtime, tests, schema and
  component documentation copied unchanged from `origin/main` so this stacked
  integration branch contains the dependency it invokes.
- `.riverview-revisions.json` — registers the imported JSON status schema and
  advances this index's revision. Its predecessor is preserved in
  `.riverview-backups/manifest.jsonl` for this task.

## Validation

The initial GitHub exact-head run found that repository CI uses `unittest`, not
`pytest`. The focused tests use `unittest`. Runtime composition passed 5/5 and
the C2 dispatcher passed 12/12 on 2026-10-18. The C3 owner worktree's exchange
suite passed 2 unit tests; 18 PostgreSQL cases skipped because
`RIVERVIEW_TEST_PG_DSN` is unset. Its exchange methods and owner-cycle hook are
not yet published, so persistence is not yet validated on a combined head.

Focused commands:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_external_reasoning_doorbell_dispatcher.py'
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_grace_doorbell_runtime_wiring.py'
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_chatgpt_doorbell.py'
node tests/test_riverview_doorbell_bridge_node.cjs
python3 -m compileall -q src/riverview_core/doorbell
```

These use synthetic exchange/bridge state and local temporary files. No
PostgreSQL, browser, CDP, ChatGPT provider, or live mailbox request was used.

## Remaining integration gates

- C3 must commit and publish the implementation currently in its worktree:
  `claim_next_doorbell_request`, `record_doorbell_receipt`, and the optional
  `GraceExecutionService.doorbell_worker` hook.
- W3/W2 must integrate those changes and run the combined disposable PostgreSQL
  scenario against the C2 worker. C2's owner-session wiring is default-off and
  unit-tested; it is not enabled in a runtime.
- C4 must establish provider identity/routing and MCP readiness. A separately
  authorized real ChatGPT wake/review is still required for end-to-end proof.

## Predecessor and rollback

The exact predecessors for the runner, component contract and this record are
preserved in `.riverview-backups/manifest.jsonl` under task
`RV-C2-DOORBELL-RUNTIME-WIRING-001`. Restore using the matching manifest backup,
then regenerate/check graph projections. Reverting the source commit is the
source rollback; runtime activation remains off unless separately configured.

## Integration closure follow-up — 2026-10-18

W3's controlled integration branch contains C3 exact head
`d9506bf858ff72b2942f64171eb8c15b740cee20` and C2 runtime wiring
`479ea738e541dbf413236476a82b24811a7f5d44`; assembled head at verification was
`f2de2061778f0a69aa7af38d7e60ae987f4b17f6`. Source inspection confirms the C2
runtime injects `DoorbellWakeWorker` through the existing
`GraceExecutionService.doorbell_worker` hook; C3 claims with
`claim_next_doorbell_request` and writes fenced receipts with
`record_doorbell_receipt`. The durable receipt `actor_id` is
`service:grace-chatgpt-doorbell`. C2 `trigger_status` is `ready` after an empty
poll or submitted wake, `blocked` for invalid/ambiguous/failed wake, and
`unavailable` when claim or receipt access fails.

The C2 PR exact-head full-suite CI run exposed an expired synthetic claim: the
test fake constructed an 80-second claim at module import, so it expired before
its tests ran after the rest of the suite. The test now creates a fresh claim
when each fake exchange is constructed. Runtime lease validation was not
relaxed. See the component troubleshooting section for recurrence diagnosis.

Integrated isolated validation on the W3 head used a temporary PostgreSQL 16
cluster and the real C3 durable exchange with a synthetic bridge (no Chrome,
CDP, provider call, or external wake): 17 C2 dispatcher/runtime unit tests
passed; 38 C3 exchange/resident-reasoning tests passed; one focused C2 worker
integration test passed, proving a durable receipt attributed to the configured
owner, no duplicate receipt after polling again, terminal ambiguity without
resend, and a two-fence bounded retry after a known pre-send failure. The first
synthetic PostgreSQL attempt had a test-query typo (`created_at` instead of the
actual `sequence` event ordering column); after correcting the disposable test
query, it passed. The 38-test run completed on the same assembled W3 source.

The integration branch's pre-refresh manifest still describes C3 claim/receipt
as unavailable; W3 must append this acceptance and refresh the manifest before
treating its assembly record as current. C4 expiry MCP mapping and the combined
W2 acceptance remain separate integration gates. No production activation or
live ChatGPT interaction was performed.

## C2 resumption and exact combined checkout — 2026-10-19

**Definition of Ready:** Task `RV-C2-DOORBELL-RESUME-20261019`; owner C2;
component `CHATGPT-DOORBELL`; classification: integration verification and
documentation correction after dependency publication. Scope is the owned C2
adapter, its contract/cookbook, and acceptance evidence. The C3 exchange and
Grace owner-loop hook are dependencies only. C4's re-review implementation and
contract are outside scope. Execution is a bounded request-driven cycle called
by Grace's existing recurring owner loop, default-off unless
`RIVERVIEW_CHATGPT_DOORBELL_ENABLED=1` is explicitly configured.

**Dependency reconciliation:** C3 PR #135 publishes exchange head
`d9506bf858ff72b2942f64171eb8c15b740cee20`; its exact methods and optional
`GraceExecutionService.doorbell_worker` hook are present with C2 in W3 assembled
head `f7fae23d446ae62a95ca87791c54de421f03c290`. C2 PR #131 head is
`13d1730054628994daa8e2f46ee0bbe789ebd8f6`; that stacked C2 branch does not
contain C3's implementation by itself. W2 PR #140 head
`5df1705da353c7acc0ffc38c95b7a7f39c462954` is integrated into the assembled W3
lineage at merge `92db8078e08c3bff105e4659332f44c363ba3fbc`. Thus the earlier
missing C3 dependency is now available on the published assembled test head;
deployment still requires the exact combined release and its existing approval
gates.

**Owned-code review:** No C2 runtime defect was found. The prior default-off
composition, metadata-only claim, fixed-target browser call, safe result
classification, and fenced receipt interface remain consistent with C3. The
repair in this resumption is documentation/evidence: the C2 dispatch contract
still described C3 as unpublished, and the linked
`CHATGPT_DOORBELL_COOKBOOK.md` did not exist. Both are corrected without editing
C3's proposal-review contract or C4's re-review implementation.

**Exact checkout evidence:** artifacts are retained under
`evidence/checkouts/CHATGPT-DOORBELL/20261019T212319Z-f7fae23/`.

| Command / checkout | Result |
| --- | --- |
| PostgreSQL 16.15 disposable integration: `combined_c2_doorbell_postgres.py`, executed with `RIVERVIEW_TEST_SOURCE_ROOT=/tmp/riverview-w3-c2-validation` and a synthetic `DoorbellResult` bridge | **1 passed / 0 skipped / 0 failed**, exit 0. It created a durable request, claimed it through C3, invoked the C2 worker with unchanged request/correlation IDs and exact target, recorded owner-attributed fenced receipts, enforced known pre-send backoff, rejected an immediate duplicate claim, replayed the successful receipt idempotently, and reconstructed the worker after restart without a third bridge call. |
| `python3 -m unittest -v tests.test_external_reasoning_exchange tests.test_w2_p0_review_recovery tests.test_external_reasoning_doorbell_dispatcher tests.test_grace_doorbell_runtime_wiring tests.test_chatgpt_doorbell` on assembled W3 head | **49 passed / 0 skipped / 0 errors**, exit 0, 142.531 s. Includes C3 PostgreSQL receipt/fencing/retry/idempotency and exchange recovery; W2 delayed reply/duplicate delivery/restart; C2 dispatcher, runtime wiring, and bridge regressions. |
| C2 branch `python3 -m unittest -v tests.test_external_reasoning_doorbell_dispatcher tests.test_grace_doorbell_runtime_wiring tests.test_chatgpt_doorbell` | **26 passed / 0 skipped / 0 errors**, exit 0. |
| `node tests/test_riverview_doorbell_bridge_node.cjs` | **5 passed / 0 failed**, exit 0. Synthetic Node bridge contract only. |
| `python3 -m compileall -q src/riverview_core/doorbell` | exit 0. |
| `python3 scripts/process_graph.py check` on the C2 branch | **22 graphs / 573 nodes, PASS**, exit 0. |
| `git diff --check` | PASS, exit 0. |

The local combined run used the unique database `rvtest_c2_doorbell_20261019`
on the local PostgreSQL 16.15 cluster; the test suite created/dropped fixture
schemas. An initial attempt under OS/database user `admin1` retained one
environment error because that role cannot `SET ROLE riverview_core`. Its log
is retained. The unchanged suite passed when executed as PostgreSQL's local
superuser. No role permissions were broadened. The database is dropped after
the checkout. W2 was asked via mailbox issue #143 comment 6277460173 for an
independent run of the same exact assembled head; no independent response had
arrived when this record was written.

### Eight-deliverable Component DoD Rev 1.7 assessment

| Deliverable | Status | Evidence and remaining limit |
| --- | --- | --- |
| 1. Code and contracts | PASS | C2 worker, fixed-target bridge, default-off composition, metadata/fence boundary, error and idempotency contract are identified by commit and component docs; C3 APIs are referenced, not redefined. |
| 2. Functionality demonstrated | PARTIAL | Real PostgreSQL exchange and synthetic bridge integration, retry, deduplication, and restart pass. Deployed environment, authenticated browser, and real ChatGPT round trip are not exercised or authorized here. |
| 3. Complete versioned documentation | PASS | C2 dispatch contract updated to the published dependency state and links to the new versioned cookbook. Deployment and production boundaries are explicit. |
| 4. Troubleshooting and recovery cookbook | PASS | `docs/components/CHATGPT_DOORBELL_COOKBOOK.md` maps diagnostics, errors, retry, restart, rollback, and resume state. Diagnostics are read-only. |
| 5. Versioned visualization flowcharts | PASS | Canonical resident-reasoning graph already contains owner-loop, opt-in, claim, fixed wake, receipt, failure, and lease recovery nodes/edges; graph check passes. |
| 6. Steward-level live operational visualization | PARTIAL | Existing status is owner-local and schema-versioned. No live Steward dashboard consumes the doorbell status in this acceptance. |
| 7. Operational autonomy and blocker clearance | PARTIAL | Repeated owner cycles, bounded retry, deduplication, and restart recovery are tested. Worker remains off by default; service, browser, provider, grants, and unattended production recovery are not commissioned. |
| 8. Registered canonical process graph | PASS | `process_graphs/resident-reasoning/runtime.json` covers the implemented flow and its failures/recovery; `process_graph.py check` passes 22/573. |

**Cross-cutting:** request-driven execution and the recurring owner-loop hook
are documented and tested; deployed unattended operation is not verified.
External observability is **PARTIAL** because the owner-local status contract
exists but an independent Steward-facing live view is not connected. The
component remains **NOT DONE** under DoD Rev 1.7 and this draft PR does not claim
Steward acceptance or production readiness.

**Safety and ownership:** no production activation, service operation, live
browser wake, real ChatGPT provider call, credential/grant change, C3 contract
change, C4 re-review change, merge to `main`, or deployment was performed.
