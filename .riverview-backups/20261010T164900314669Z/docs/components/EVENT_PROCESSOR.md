# Riverview~ M1.3 event processor contract

**Document Revision:** 1.0.0  
**Component:** EVENT-PROCESSOR  
**Task:** RV-M1.3-001  
**Status:** IN PROGRESS — isolated engineering only  
**Execution model:** event-driven continuous service  
**Owner:** office:operations

## Purpose and boundary

The processor consumes PostgreSQL ledger events in sequence. Its first action is
to move a newly created, still-queued assignment to `ready`, without a chat or UI
turn. It is a supervised prototype, not a worker adapter, independent verifier,
scheduler, CME, authority gateway, dashboard, or production service.

## Durable cursor and replay

The consumer cursor is stored in `event_processor_cursors` in the explicitly
selected schema. Event handling is at least once. A deterministic idempotency key
derived from consumer ID and event ID protects the state transition. Cursor
advancement happens after successful handling. A crash after the transition but
before cursor commit replays the event; the already-advanced assignment is not
transitioned again. The processor holds a PostgreSQL advisory lock for its
consumer while continuously running, and cursor rows are locked during each
checkpoint batch.

The cursor schema addition is migration
`src/riverview_core/event_processor/migrations/0002_event_processor_cursor.sql`.
It is separate from the M1.2 migration directory and has **not** been applied to
the shared `riverview_dev` schema. Applying migrations requires an explicit
deployment task with the standard preflight, backup and verification procedure.

## Configuration and observability

`scripts/run_event_processor.py` reads `RIVERVIEW_PG_DSN` (host/database/user,
without a password), `RIVERVIEW_PG_SCHEMA` and `RIVERVIEW_PROCESSOR_ID`. Libpq
credentials must come from a protected passfile selected with `PGPASSFILE`; the
entry point rejects a password in DSN options. JSON logs identify lifecycle,
consumer, event ID, cursor sequence, outcome, error class and bounded retry delay;
they do not log payloads or credentials. SIGTERM and SIGINT stop the loop and
release the database leadership lock. The independent live dashboard and
external freshness API remain M3.1 work.

## Failure and limitation

Dependency/handler errors leave the cursor before the failed event and retry with
bounded exponential delay, preserving replay evidence. A poison event can hold
this single ordered cursor and delay later events; per-assignment isolation and
fair scheduling are M1.4. No external side effects occur in this implementation.
Assignment processing is not independent verification: ledger `verified` input
remains an untrusted caller claim.

## Verification

Acceptance tests use unique disposable schemas and a local disposable PostgreSQL
cluster. They exercise continuous no-turn progression, clean stop/restart,
replay after the transition/cursor crash window, duplicate-event idempotency and
the durable cursor. Service deployment and Camrui unattended-run acceptance are
not yet performed. See the [canonical process graph](EVENT_PROCESSOR_FLOW.md),
[cookbook](EVENT_PROCESSOR_COOKBOOK.md), and
[engineering record](../development/M1.3-001_REVISION_RECORD.md).
