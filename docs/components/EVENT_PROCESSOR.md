# Riverview~ M1.3 event processor contract

**Document Revision:** 1.0.2
**Component:** EVENT-PROCESSOR
**Task:** RV-M1.3-001
**Status:** Scoped technical commissioning PASS; full component DoD OPEN
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

PostgreSQL identity sequence values can be allocated before their transactions
commit. `PostgresLedger` therefore takes a transaction-scoped event-log advisory
lock before assigning each event sequence; the lock is held through commit. This
keeps committed event visibility monotonic for the single global cursor. It
serializes event appends and is a known first-slice throughput limit to revisit
with M1.4 scheduling. The consumer verifies the deployed base and cursor
migration checksums before processing and reconnects/reacquires leadership after
a database-session loss.

The cursor schema addition is migration
`src/riverview_core/event_processor/migrations/0002_event_processor_cursor.sql`.
It is separate from M1.2 migration 0001. It was applied to `riverview_dev` only
after checksum preflight, root-only backup, and successful restore drill. The
M1.3 service is commissioned on Camrui at source commit
`9ca7cb189d1e1f57c69395303a9367fabd979ff5`; the exact outcomes and retained
evidence are in [M1.3-002](../development/M1.3-002_REVISION_RECORD.md).

## Configuration and observability

`scripts/run_event_processor.py` reads `RIVERVIEW_PG_DSN` (host/database/user,
without a password), `RIVERVIEW_PG_SCHEMA` and `RIVERVIEW_PROCESSOR_ID`. The
dedicated `riverview-event-processor.service` uses systemd `LoadCredential` to
deliver the existing root-owned passfile, validates the exact credential mount,
and copies it to a private mode-0600 runtime passfile. The entry point rejects
password-bearing DSNs and ambient libpq overrides. JSON logs identify lifecycle,
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
the durable cursor, commit-order races, migration drift rejection, database
session-loss recovery, and credential delivery. See the
[canonical process graph](EVENT_PROCESSOR_FLOW.md),
[cookbook](EVENT_PROCESSOR_COOKBOOK.md), and
[commissioning record](../development/M1.3-002_REVISION_RECORD.md). The full
component DoD remains open for later obligations, including the M3.1 live
dashboard, external status projection and subsequent autonomy integrations.
