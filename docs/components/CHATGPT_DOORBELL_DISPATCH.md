# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/CHATGPT_DOORBELL_DISPATCH.md
# Component: CHATGPT-DOORBELL
# Revision: 1.0.1
# Purpose: Contract for waking the provider-scoped external review mailbox
# Authority: No production activation or live ChatGPT send is authorized by this document

## C2 durable exchange wake adapter

`DoorbellWakeWorker.run_once()` is a bounded adapter for the existing Grace
external-reasoning exchange. The existing owner-session execution loop may call
one cycle; this module creates no resident, mailbox, scheduler, or service.

For each cycle it calls the exchange's provider-scoped
`claim_next_doorbell_request(provider_id, owner_id, lease_seconds)`. An empty
claim returns `idle`. A claim must carry request and correlation UUIDs, the exact
provider ID, attempt ID, lease token, and positive fence. Missing or mismatched
metadata is rejected before browser invocation; the durable exchange lease is
left to expire. The adapter does not request or inspect `request_payload`,
`review_subject`, or any response body.

For a valid claim, the adapter calls the existing
`BrowserBridgeRunner.ring(DoorbellRequest, designated_conversation_id)`. The
runner's fixed wake message and exact configured target remain authoritative.
No proposal text, reply, browser DOM output, arbitrary URL, or prompt is supplied
by this worker.

The adapter writes the outcome to the same exchange with
`record_doorbell_receipt(request_id, correlation_id, provider_id, owner_id,
attempt_id, lease_token, fence, outcome, safe_error_code)`. The exchange remains
the source of truth for idempotency, lease fencing, durable events, retry timing,
and expiry. Receipt outcomes are:

| Outcome | Meaning | Automatic retry |
| --- | --- | --- |
| `submitted` | Fixed wake was verified by the bridge, including idempotent replay of a known success. | No; exchange can expose the request to the external provider. |
| `failed` | Bridge returned a known pre-send failure. | Exchange's bounded retry/expiry policy. |
| `ambiguous` | Send may have occurred, bridge response lineage was lost, or bridge raised unexpectedly. | No automatic resend based on this receipt. |

Timeout (`RIV-PLY-0009`), uncertain CDP transport (`RIV-PLY-0003`), CDP command
error (`RIV-PLY-0004`), lineage mismatch (`RIV-PLY-0014`), unknown codes, and unexpected exceptions are
`ambiguous`. Only known failures before the fixed send action are `failed` and
eligible for the exchange's bounded retry policy. Diagnostics are stable codes;
exception messages and provider content are never persisted by this adapter.

`owner_id`, `provider_id`, and `designated_conversation_id` are required injected
configuration. This code does not choose or provision their values. A deployment
must use the approved provider identity already used by MCP and a distinct
internal owner identity supplied by the resident runtime. Configuration
validation fails closed when required identity or target values are absent.

Each cycle result also exposes C2's bounded trigger status for the owner-side
readiness projection: `ready` after an empty successful poll or recorded wake,
`blocked` after invalid claim metadata or failed/ambiguous wake, and
`unavailable` when the exchange or receipt write cannot be reached. If the owner
loop has not constructed/registered this optional worker, it must report
`not_configured`; browser health alone is not evidence that this trigger runs.

## Isolated validation

Run the fake-exchange and fake-bridge tests with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_external_reasoning_doorbell_dispatcher.py'
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_chatgpt_doorbell.py'
node tests/test_riverview_doorbell_bridge_node.cjs
```

These tests do not connect to PostgreSQL, Chrome/CDP, the ChatGPT website, or an
external provider. They demonstrate adapter behavior only. A disposable database
integration test must be supplied by the exchange owner for lease fencing and
receipt persistence. A separately authorized smoke test is required to prove a
real ChatGPT review; this worker's implementation or tests do not send one.
