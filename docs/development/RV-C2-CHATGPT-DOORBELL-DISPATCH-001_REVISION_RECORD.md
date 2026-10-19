# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/development/RV-C2-CHATGPT-DOORBELL-DISPATCH-001_REVISION_RECORD.md
# Component: CHATGPT-DOORBELL
# Revision: 1.0.4
# Purpose: Record implementation and isolated validation for the C2 wake dispatcher
# Execution Model: Engineering revision record
# Observability: Source, tests, and parent commits recorded without provider content
# Dependencies: C3 durable exchange contract; existing BrowserBridgeRunner
# Authority: Offline implementation only; no live wake or production activation
# Changed: 2026-10-18 UTC | RV-C2-DOORBELL-RUNTIME-WIRING-001 | Add fail-closed owner-session composition and integration evidence
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
