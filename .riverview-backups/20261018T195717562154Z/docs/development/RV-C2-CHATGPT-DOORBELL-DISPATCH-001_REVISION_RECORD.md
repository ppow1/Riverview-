# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/development/RV-C2-CHATGPT-DOORBELL-DISPATCH-001_REVISION_RECORD.md
# Component: CHATGPT-DOORBELL
# Revision: 1.0.0
# Purpose: Record implementation and isolated validation for the C2 wake dispatcher
# Execution Model: Engineering revision record
# Observability: Source, tests, and parent commits recorded without provider content
# Dependencies: C3 durable exchange contract; existing BrowserBridgeRunner
# Authority: Offline implementation only; no live wake or production activation
# Changed: 2026-10-18 UTC | RV-C2-CHATGPT-DOORBELL-DISPATCH-001 | Initial record
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
- `tests/test_external_reasoning_doorbell_dispatcher.py` — synthetic claim,
  bridge, receipt, failure, retry-classification, and duplicate-cycle cases.
- `docs/components/CHATGPT_DOORBELL_DISPATCH.md` — contract and operational
  limits.
- Existing doorbell package, fixed bridge, local runtime, tests, schema and
  component documentation copied unchanged from `origin/main` so this stacked
  integration branch contains the dependency it invokes.
- `.riverview-revisions.json` — registers the imported JSON status schema and
  advances this index's revision. Its predecessor is preserved in
  `.riverview-backups/manifest.jsonl` for this task.

## Validation

Pending final exact-head checks. Focused commands:

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_external_reasoning_doorbell_dispatcher.py tests/test_chatgpt_doorbell.py
node tests/test_riverview_doorbell_bridge_node.cjs
python3 -m compileall -q src/riverview_core/doorbell
```

These use synthetic exchange/bridge state and local temporary files. No
PostgreSQL, browser, CDP, ChatGPT provider, or live mailbox request was used.

## Remaining integration gates

- C3 must complete the agreed `claim_next_doorbell_request` and
  `record_doorbell_receipt` methods in the exchange implementation.
- The existing owner-session loop must construct this worker using the
  Steward-approved provider ID, internal owner ID, and already-configured exact
  target; C2 does not enroll it or activate a service.
- C4 must establish provider identity/routing and MCP readiness. A separately
  authorized real ChatGPT wake/review is still required for end-to-end proof.
