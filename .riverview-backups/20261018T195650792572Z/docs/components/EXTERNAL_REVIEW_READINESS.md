<!--
Riverview~ Controlled Document
File: docs/components/EXTERNAL_REVIEW_READINESS.md
Component: EXTERNAL-REVIEW-READINESS
File Revision: 1.0.2
Purpose: Define C1's privacy-safe readiness projection for the Grace external review flow
Authority: Read-only projection; owning services retain all lifecycle and decision authority
Changed: 2026-10-18 UTC | RV-C1-EXTERNAL-REVIEW-READINESS-001 | Initial component contract
Changed: 2026-10-18 UTC | RV-C1-EXTERNAL-REVIEW-READINESS-001 | Record timeout projection and evidence boundaries
Changed: 2026-10-18 UTC | RV-C1-EXTERNAL-REVIEW-READINESS-001 | Distinguish durable Grace consumption from an evaluated decision
History: Git
-->
# Grace External Review Readiness Projection

## Responsibility and boundary

`src/riverview_core/external_review_readiness.py` converts existing mailbox,
doorbell, and provider metadata into a coarse operator status. It does not
create or mutate an exchange, ring the browser, authenticate a provider, accept
a review, or authorize Engineering work. Grace's exchange consumer remains the
owner of response evaluation; C2 owns browser wake; C3 owns exchange state; C4
owns provider MCP operations; W1 owns exact lineage reporting.

The projection never reads nested `review_subject`, request, response,
conversation, cookie, URL, token, or credential values. It does not copy request
or correlation IDs, attempt IDs, proposal IDs, digests, arbitrary error strings,
or browser target details to its result. It returns stable enum values and
source-presence/freshness booleans only.

## Inputs

The request-driven function `project_external_review_readiness(...)` accepts:

1. `exchange_status`: the existing `DurableExternalReasoningExchange.status()`
   projection (`delivery_state`, `deadline_at`; IDs may be present but are used
   only for an optional receipt consistency check).
2. `doorbell_status`: C2's `rv.chatgpt-doorbell.status.v1` metadata object.
   This projection reads `observed_at`, `freshness.state`,
   `freshness.stale_after_seconds`, `status`, `browser_health`,
   `local_browser_ready`, `cdp.status`, `authentication_status`,
   `target_resolution`, and `fixed_action_available` only. The actual doorbell
   schema is documented in the C2 component contract.
3. Optional `wake_receipt`: the C3 fenced, metadata-only receipt. The projection
   checks request/correlation equality when both source and receipt carry those
   fields, then maps only the `submitted|ambiguous|failed` outcome.
4. Optional `provider_submission`: a body-free C4 result. Only `accepted` or
   `rejected` is interpreted.
5. `trigger_status`: C2's independently reported trigger-worker state. Only
   `ready` permits the projection to report `ready_for_doorbell`; absent,
   unknown, or `not_configured` state cannot be inferred from a healthy browser
   process.

When a C3 receipt is not yet available, the existing doorbell status object's
`last_trigger` is used only if its request and correlation IDs exactly match the
current exchange. Matching `failed` and matching `succeeded` with
`submit_verified=true` are projected as retry/recovery and waiting-for-claim,
respectively. An older or unrelated trigger is ignored. Neither attempt ID nor
failure detail is included in the projection.

No value from these parameters is trusted as an authorization decision. Each
caller must fetch inputs through their owning service and retain the existing
service authentication. This module performs no database or network I/O.

## Output contract

Schema: `rv.grace.external-review-readiness.v1`.

The result contains `observed_at`, `readiness`, `state`, an allowlisted
`failure_code` (or null), `retryable`, a fixed `next_action` label, and an
`deadline_seconds_remaining` value while an exchange is pending, plus an
`evidence` map containing booleans only. A persisted `response_received` result
remains eligible for Grace consumption even if its request deadline later
passes; the deadline only expires exchanges still awaiting delivery, claim, or
response. Unknown, malformed, expired, stale, or
mismatched evidence fails closed. The current readiness labels include:

| Condition | State | Next action |
| --- | --- | --- |
| Durable exchange absent | `mailbox_unavailable` | Retry exchange status |
| Exchange response persisted | `response_received` | Grace consumes and evaluates |
| Exchange consumed by Grace | `grace_consumed` | Inspect the separately persisted Grace decision |
| Exchange deadline elapsed | `review_expired` | Record expiry through exchange owner |
| Doorbell source absent or stale | `doorbell_status_unavailable` / `doorbell_status_stale` | Restore or refresh source |
| Auth or exact target is not ready | `browser_authentication_unknown` / `browser_target_unresolved` | Resolve with browser owner |
| Failed/ambiguous wake receipt | `retry_recovery` | Retry with the same exchange identity |
| Provider rejection | `response_rejected` | Request a valid correlated response |

Failure values are generated from constants; untrusted error text is not
returned. Correlation mismatch is terminal for this projection and routed to
the owning exchange operator; it never attempts to repair or rewrite the
lineage.

## Recovery and limitations

Callers should re-read authoritative metadata after a retryable status and
respect exchange deadlines and C3's fenced lease/backoff decisions. The
projection does not schedule retries. A missing readiness object is not
interpreted as browser health. A stale status is never labelled ready. A
successful fixed browser wake only establishes that the fixed wake was
submitted; the external provider must still claim the exact exchange, submit a
correlated response, and Grace must consume it. Exchange consumption alone is
not proof of an accept/revise decision or objective completion.

This increment supplies the pure consumer contract and isolated fixtures. It is
not a Steward dashboard/API integration, deployed health endpoint, live browser
readiness check, or proof of a ChatGPT review. C2 must pass its trigger worker's
real status into `trigger_status` before this projection may report the initial
doorbell step ready. Those status integrations remain with their owning windows
and the final integration owner.

## Validation

Run `PYTHONPATH=src python -m unittest tests.test_external_review_readiness -v`.
Tests use synthetic metadata only and make no network, browser, PostgreSQL,
provider, or production calls.
