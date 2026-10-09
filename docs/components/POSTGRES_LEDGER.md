<!--
Riverview~ Controlled Document
File: docs/components/POSTGRES_LEDGER.md
Revision: 1.0.0
Migration: ENG-REV-002
-->
# PostgreSQL assignment ledger — component contract

**Status: tested developer backend; NOT production complete.** Code: `src/riverview_core/postgres_ledger.py`; tests: `tests/test_postgres_ledger.py`. Runtime host: Camrui, PostgreSQL 16. The existing SQLite `Ledger` is a separate developer prototype.

## Purpose and boundaries
PostgresLedger records assignment state and append-only event records in the same PostgreSQL transaction. It is a library, **not** an always-on service, worker dispatcher, authorization gateway, independent verifier, CME agent, or durable outbox.

## API
`PostgresLedger(dsn, schema="public")` initializes tables in the selected schema. `create(assignment_id, owner, idempotency_key)` creates a queued assignment. `transition(assignment_id, to_state, step, idempotency_key, verified=False)` validates transitions against `TRANSITIONS` in `ledger.py`. `get(id)`, `list_assignments()`, `events(after_seq=0)`, and `close()` are read/cleanup operations. Rows are Python dictionaries, with PostgreSQL timestamps and UUID values. `events` returns ordered `seq` values.

## Persistence and concurrency
Psycopg 3 connection uses autocommit for reads; explicit `db.transaction()` groups each state mutation and corresponding event atomically. `SELECT ... FOR UPDATE` serializes changes to one assignment; advisory transaction locks serialize duplicate idempotency keys. Unique constraints protect event identifiers and idempotency keys. A successful test confirmed state survives closing and reopening the connection. This is not a benchmark or comprehensive concurrency proof.

## Schema
`assignments`: id (PK), state, owner, workflow_step, updated_at, version.
`events`: seq (identity PK), event_id (unique UUID), idempotency_key (unique), assignment_id, event_type, occurred_at, payload (JSONB).

## Limitations and open work
- `verified=True` is only an untrusted caller assertion, **not independent verification**. Never expose this API to untrusted callers or connect it directly to hardware dispatch.
- No authentication or authorization layer, audit of readers, migrations/versioned schema, connection pooling, automatic reconnect, backups/restore drills, outbox, worker, service, or health endpoint.
- The API does not yet enforce that replayed creation keys match the original owner, or that replayed transitions match all original arguments. Treat idempotency replay as key-scoped, not a complete semantic identity check.
- Schema initialization runs on construction and requires DDL rights; separate migrations are needed for production.
- `list_assignments()` and `events()` are unbounded and intended for small development datasets; use pagination for real dashboard use.
- Steward readout currently is an **on-demand snapshot**, not a continuously refreshed Steward dashboard.

## Evidence and acceptance
On Camrui, `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN=<test DSN> python3 -m unittest discover -s tests -v` produced six passing tests (three SQLite, three PostgreSQL) on 2026-10-09. PostgreSQL tests create and drop isolated temporary schemas. Before release require independent verification, service, live Steward integration, fault/restart/concurrency tests, backups and migration procedure. See `POSTGRES_LEDGER_COOKBOOK.md` and `POSTGRES_LEDGER_FLOW.md`.
