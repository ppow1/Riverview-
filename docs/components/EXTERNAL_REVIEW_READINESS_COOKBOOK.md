<!--
Riverview~ Controlled Document
File: docs/components/EXTERNAL_REVIEW_READINESS_COOKBOOK.md
Component: EXTERNAL-REVIEW-READINESS
File Revision: 1.0.0
Purpose: Diagnose redacted Grace external-review readiness projections
Authority: Read-only diagnostics; owning services retain all action authority
Changed: 2026-10-18 UTC | RV-C1-P0-READINESS-INTEGRATION-001 | Initial operator cookbook
-->
# External Review Readiness Cookbook

## Scope

This projection reports metadata consistency only. It does not prove that a
browser session is currently authenticated, invoke ChatGPT, submit an exchange,
or establish production readiness. Obtain each input from its owner: C2's
doorbell status and `DoorbellCycleResult.trigger_status`, C3's durable exchange
status/receipt, and C4's provider-scoped status or submit result.

## Offline verification

From the repository root, run:

```sh
PYTHONPATH=src python3 -m unittest tests.test_external_review_readiness -v
```

The suite uses synthetic metadata and makes no network, browser, database,
provider, or production call.

## Read-only interpretation

Pass only the status objects returned by their owning components to
`project_external_review_readiness`. Do not pass request/response bodies,
cookies, URLs, tokens, credentials, or model content. The projection checks
the exact request and correlation pair on C3 receipts, the C3 subject/response
digests, and C4's provider status digests. It emits only fixed labels and
boolean source-presence/freshness fields.

- `ready_for_doorbell` requires a fresh C2 status and `trigger_status="ready"`.
- `wake_submitted_waiting_for_claim` means the same exchange's fixed wake was
  durably receipted; it does not mean ChatGPT claimed the request.
- `response_received` means C3 persisted a correlated response and Grace may
  consume it under existing authority.
- `provider_status_mismatch` or `correlation_mismatch` is a stop condition for
  this projection. Re-read owner status and have the owning service diagnose
  lineage; never repair identifiers in the projection.
- `grace_consumed` does not prove a finish/revise decision. Inspect the durable
  Grace decision event through its authorized owner.

## Recovery boundaries

For stale/unavailable inputs, refresh only the owning component's read-only
status. For an expired or malformed exchange, use C3's documented recovery
path. For browser authentication or target problems, the authorized browser
owner must resolve them. Do not trigger a live wake as a diagnostic step.
