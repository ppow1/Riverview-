<!--
Riverview~ Controlled Document
File: docs/components/EXTERNAL_REVIEW_TRACE.md
Component: EXTERNAL-REVIEW-OBSERVABILITY
File Revision: 1.0.0
Purpose: Define the read-only review lineage report and operator procedure
Authority: Observation only; no provider, mailbox, browser, Grace, or work-order mutation
Changed: 2026-10-18 UTC | RV-EXTERNAL-REVIEW-TRACE-001 | Initial report contract
Tests: tests/test_external_review_trace.py
History: Git and .riverview-backups/manifest.jsonl
-->

# External proposal review trace

The W1 report is a bounded, read-only projection for the exact review lifecycle:
proposal subject → durable review request → browser wake receipt → provider claim
and response → Grace evaluation → revision or accepted/consumed result. It is
not a scheduler, mailbox, browser driver, provider client, or authority check.
The report never displays proposal or response text, prompt/context, credentials,
claim tokens, cookies, or arbitrary fields from an input snapshot.

## Input contract

`rv.external-review-trace-input.v1` is a local metadata snapshot supplied by an
authorized read-only operator/source adapter. It has a `doorbell_owner_id` from
C2 configuration and `execution_kind`
(`synthetic`, `external`, or `unknown`) and one through twelve ordered `rounds`.
Each round contains:

- `review_subject`: `schema_version`, stable `subject_id`, positive `revision`,
  immutable SHA-256 `sha256`, and an optional nested proposal object that is
  discarded by the projection.
- `exchange`: UUID `request_id`, UUID `correlation_id`, durable `state`, and
  optional `eligible`, `eligible_at`, and existing `events()` metadata. The projection
  derives wake information from `delivery_started` / `delivery_acknowledged` /
  `delivery_failed` (or compatibility receipt events); only events whose `actor_id` exactly matches
  `doorbell_owner_id` count as doorbell evidence. This prevents MCP's own
  `mark_delivered` call from being misreported as a browser wake; an
  unattributed receipt with no owner-matched receipt produces an explicit
  `doorbell_owner_mismatch` blocker. A retryable
  delivery failure remains in progress, while terminal `failed`/`expired` is
  blocked.
- Optional normalized doorbell metadata may be supplied by C2. A
  `delivery_claimed` event means only a fenced delivery lease was acquired;
  `delivery_started` records that the attempt began, and
  `delivery_acknowledged` by the configured doorbell owner is the submitted
  wake receipt. C3 delivery events must be attributed to
  the configured C2 `owner_id`; MCP-owned `mark_delivered` events never count.
- `provider`: the same IDs, `state` or the exchange's `delivery_state`,
  provider identity, reviewed-subject and
  response digests (`review_subject_sha256` is the C4 echo), and claim/response
  times.
- `grace`: either normalized evaluation fields or bounded objective `events`
  named `resident.reasoning.external_proposal_reviewed`,
  `resident.reasoning.external_proposal_revised`, and
  `resident.reasoning.external_proposal_review_blocked`. The event mapper
  expects `payload.request_id`, `correlation_id`, `subject_revision`,
  `subject_sha256`, and `decision`; a revision event additionally maps
  `successor_revision`, `successor_sha256`, `successor_request_id`, and
  `successor_correlation_id`. Durable `grace_consumed` time is taken from the
  correlated exchange event. These are the W1 snapshot adapter keys; C3 must
  confirm them against its emitted event records before runtime use.

The W1 projector accepts only these metadata fields. Future owner adapters must
map their authoritative records to this shape without weakening correlation or
adding private bodies. In particular, a `submitted` browser receipt means only
that the fixed wake operation reported submission; it is never evidence that
ChatGPT reasoned, claimed, or replied. Provider `response_received` means a
correlated provider response was durably accepted, not that its advice is
approved or executable.

## Outcome rules

- `in_progress`: one or more required upstream stages have not produced a
  record yet. Missing evidence is never inferred as success.
- `blocked`: terminal exchange/provider failure, digest or ID mismatch,
  acceptance without matching evaluation and durable consumption, or a revise
  decision with no recorded successor subject. A `grace_consumed` state with
  no matching evaluation is blocked. Acceptance and revision also
  require an eligible/claimed request, a submitted wake receipt, matching
  provider `response_received` and subject digest, exchange `grace_consumed`, a
  matching Grace evaluation, and its durable consumed timestamp.
- `review_required`: Grace durably evaluated a revision request and recorded a
  changed version/hash; that new exact subject still needs its own review round.
- `complete`: only a matching exact subject has a Grace `accept` decision, an
  evaluation timestamp, and a durable consumption timestamp. A later round
  after acceptance is rejected as contradictory input.
- A following review round after `revise` must use exactly the recorded
  successor version/hash and a new request/correlation pair.
- A `delivery_claimed` event is reported as a fenced lease only; it does not
  prove the browser operation started. `delivery_started` records the attempt;
  `delivery_acknowledged` is the
  metadata evidence that fixed-wake submission was reported successful only
  when the event actor equals the configured doorbell owner ID.

The output contains only IDs, versions, digests, approved state labels,
timestamps, bounded attempt identifiers, sanitized blocker codes, a fixed
next-action code, declared execution kind, and a report digest.
`execution_kind_verified` is always false because this projection does not
authenticate source records. A complete synthetic trace proves only simulated
metadata consistency. The JSON input is capped at 256 KiB and the round count
at twelve.

## Operator command

First obtain/export the metadata snapshot through the separately authorized,
read-only interfaces owned by Grace/exchange, browser doorbell, and provider
adapter. Do not query protected records with an unapproved identity. Save the
snapshot to a restricted local path and run:

```powershell
$env:PYTHONPATH = 'src'
python scripts/report_external_review.py C:\restricted\review-trace.json
```

On Linux, from the checkout root:

```sh
PYTHONPATH=src python3 scripts/report_external_review.py /restricted/review-trace.json
```

Exit code 0 means the supplied trace records exact-subject Grace acceptance
and consumption. Exit code 1 means incomplete, revised-needs-review, or
blocked. Exit code 2 means invalid/unavailable input. Read the JSON `outcome`
and `blockers`; `wake_submitted` alone is never completion. The report hashes
its sanitized output for evidence comparison. The input snapshot may contain
private fields from its source; the report will not copy unknown fields, but the
operator remains responsible for handling/deleting the input safely.

## Installation, rollback, and limits

This is an offline source addition. No service, migration, credential, grant,
database, browser profile, or production configuration is changed. The CLI
requires the repository source package on `PYTHONPATH` and uses only the Python
standard library. Rollback is removal/reversion of the two source files, the
test, and this document on the feature branch; no runtime state needs rollback.

At this revision, upstream source adapters have not been integrated. The CLI
consumes a bounded snapshot rather than opening a database or network client.
It therefore reports only facts present in that input. A synthetic fixture
proves projection behavior and redaction, not external ChatGPT execution or
current runtime readiness. See issue #120 for C2/C3/C4 field agreement and the
separate Steward authorization required before a live doorbell.
