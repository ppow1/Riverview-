<!--
Riverview~ Controlled Document
File: docs/components/EXTERNAL_REASONING_EXCHANGE.md
Component: RESIDENT-REASONING
File Revision: 1.0.1
Purpose: Define the durable transport-neutral external reasoning exchange contract
Authority: Existing resident.reasoning.escalate exact grant; advisory-only result
Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Initial phase-one contract
Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Connect typed advice to existing ResidentReasoner input
History: Git and .riverview-backups/manifest.jsonl
-->
# Durable external reasoning exchange

## Scope and authority

This phase adds a PostgreSQL-backed exchange envelope around
`ReasoningEscalationRouter`. It does not install an MCP endpoint, browser
automation, provider API, scheduler, or worker dispatcher. Grace's objective,
proposal, assignment, CME, and verification records remain authoritative.
An external response is typed **advice** only. It cannot approve a proposal,
create an assignment, invoke a tool, or mark work verified.

The adapter calls `authorize_for_durable_exchange` before it inserts an exchange.
That method reuses the router's configured provider identity, context
fingerprint, and exact `resident.reasoning.escalate` authorization for
`provider:<provider_id>`. A denial or unavailable authority service creates no
row. The request is durably committed before any delivery lease can be taken.

## Durable contract

Migration `0011_external_reasoning_exchange.sql` adds
`external_reasoning_exchanges` and the append-only
`external_reasoning_exchange_events` ledger. A row is tied by foreign key to an
existing Grace objective and, when supplied, to one exact proposal revision.
Conversation/message references are provenance links, not another conversation
store. The bounded request snapshot is retained with its context digest so a
restarted consumer can recover the original reasoning context. Restricted and
local-only classifications are rejected for external admission in this phase.

The caller supplies a stable idempotency key and finite deadline (1 second to
24 hours). Duplicate admission with identical content returns the original
request and correlation IDs. Reusing the key with different content fails.
Events are committed with each state transition both in the exchange ledger and
the existing objective event history; event payloads contain IDs, digests,
state, and sanitized codes, never request or response bodies.

States and available internal operations:

| State | Meaning | Recovery/next operation |
|---|---|---|
| `awaiting_delivery` | Persisted outbox item; no transport attempt yet | `eligible_requests`, then local `begin_delivery` lease |
| `awaiting_external_claim` | Delivery was acknowledged by the transport | External `claim` |
| `awaiting_response` | Provider owns a bounded claim lease and fencing token | Submit one correlated response; expired claim can be reclaimed |
| `response_received` | Valid advisory and provenance are durable | Grace `consume` obtains a resumable lease/result |
| `grace_consumed` | Existing Grace reasoning workflow durably recorded its result reference | Retry returns the same advisory and stable consumption key |
| `expired` | Finite deadline elapsed before a response | Terminal; no replay or deadline extension |
| `failed` | Delivery exhausted its bounded attempts or was explicitly non-retryable | Terminal diagnostic; preserve row and events |

Delivery and Grace-consumption leases are bounded and fenced. A reclaimed lease
increments its fence, invalidating stale owners. Delivery retry uses bounded
backoff and at most five attempts. Provider claims are scoped to the selected
provider principal. Response schema, request/correlation identity, provider,
claim token, fence, deadline, size and evidence-reference bounds are validated
before the response transaction commits. Identical response retries return the
stored digest; conflicting responses fail.

Grace consumption revalidates the original exact grant and context. It returns
the original typed `ReasoningRequest`, separate advisory payload, and a stable
`consumption_key`. The existing reasoning caller must use that key for its own
durable idempotent continuation, then acknowledge the durable result reference.
This two-stage boundary permits recovery after response persistence or after a
consumer crash without claiming that a model response is a verified fact.

`DurableExternalReasoningExchange.status()` is a read-only diagnostic
projection: IDs, state label, provider, context/response digests, timestamps,
attempt counts, provenance, and sanitized error code. It does not include
request or response bodies. `events()` returns the append-only exchange
transition history for a correlated request.

## Typed interface for a future MCP adapter

The phase-one service exposes these transport-neutral methods:

- `eligible_requests(provider_id, principal_id, limit)` — bounded outbox
  metadata/payload; provider principal is checked against the registered
  provider identity (a future adapter may bind a distinct trusted principal).
- `begin_delivery(...)`, `mark_delivered(...)`, and `fail_delivery(...)` —
  internal leased outbox operations; no network call is made by this module.
- `claim(request_id, correlation_id, provider_id, principal_id, lease_seconds)`.
- `submit_response(..., claim_token, fence, idempotency_key, response)`.
- `status(request_id, correlation_id)` and `events(...)`.
- `consume(request_id, correlation_id, principal_id, authorize, lease_seconds)`
  followed by `acknowledge_consumed(..., consumption_key, ..., authorize)`.

The Grace consumer passes `ExchangeConsumption.advisory` to
`ResidentReasoner.propose(..., external_advisory=...)` as a typed, unverified
input, separate from retrieved verified knowledge. The reasoner revalidates its
normal office binding and exact grant, records provider/correlation/digest
provenance with its durable outcome, and produces only its normal unapproved
proposal. A consumer acknowledges the exchange only after that reasoning outcome
has been durably recorded. A crash before acknowledgment is recoverable through
the stable consumption key; retries cannot authorize an action.

An MCP adapter must derive provider identity from authenticated server-side
transport context, never from an untrusted body field. It should expose only
provider-scoped eligible requests, claim, submit, and status. It must not expose
Grace consumption to the external provider. MCP installation, authentication,
and deployment are explicitly deferred to the next increment.

## Troubleshooting and safeguards

See [the external-exchange operations cookbook](EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md).
The process graph `rv:resident-reasoning:runtime` records admission, delivery,
claim, response commit, Grace consumption, expiry, and recovery checkpoints.
The exchange operation itself invokes no provider or Engineering execution API.
The typed consumer seam resumes `ResidentReasoner.propose` with the correlated
advisory, then records the reasoning outcome through existing resident/objective
state before acknowledging consumption.

## Migration and rollback

Migration 0011 is additive and checksum-pinned. It grants the existing runtime
role access only to the new exchange relations and the already-authorized
objective event write path; it does not grant access to authority ledgers or
unrelated tables. For rollback, disable the adapter and retain the tables and
records. Do not drop exchange history or rewrite objective events.
