<!--
Riverview~ Controlled Document
File: docs/components/POSTGRES_LEDGER.md
Revision: 1.0.1
Migration: ENG-REV-002
-->
# PostgreSQL assignment ledger — component contract

**Status: tested developer backend; NOT production complete.** Code: `src/riverview_core/postgres_ledger.py`; tests: `tests/test_postgres_ledger.py`. Runtime host: Camrui, PostgreSQL 16. The existing SQLite `Ledger` is a separate developer prototype.

## Purpose and boundaries
PostgresLedger records assignment state and append-only event records in the same PostgreSQL transaction. It is a library, **not** an always-on service, worker dispatcher, authorization gateway, independent verifier, CME agent, or durable outbox.

## API and authority boundary
`apply_migrations(dsn, schema=...)` explicitly applies ordered SQL files from `src/riverview_core/migrations/`. The runner serializes migrations per schema, records SHA-256 checksums, treats an identical rerun as a no-op, and refuses changed bytes for an applied version. `PostgresLedger(dsn, schema=...)` requires an already migrated schema; construction does not issue DDL.

`create(assignment_id, owner, idempotency_key, *, authority_ref, objective_ref, actor_id, ...)` persists required authority and objective references plus contract, workflow, occupant, correlation, and initial-step metadata. `transition(assignment_id, to_state, step, idempotency_key, *, actor_id, verified=False)` records actor, authority reference inherited from the assignment, correlation, causation, privacy domain, payload schema, and event payload. It validates state changes against `TRANSITIONS` in `ledger.py`. `get(id)`, `list_assignments()`, `events(after_seq=0)`, and `close()` are query/lifecycle operations. Rows are Python dictionaries, with PostgreSQL timestamps, UUIDs, and JSON values.

Authority references are stored, not validated. `verified=True` is an untrusted caller assertion retained as `verified_claim`; it is not independent verification. Authentication, authorization, grant validation, and independent outcome verification remain outside this persistence component.

## Persistence, idempotency, and concurrency
Psycopg 3 uses autocommit for reads; explicit transactions group each state mutation and corresponding event atomically. `SELECT ... FOR UPDATE` serializes changes to one assignment; advisory transaction locks serialize duplicate idempotency keys. Unique constraints protect event identifiers and idempotency keys. A failed event insert rolls back its state change. Idempotency replay compares assignment, event type, payload, actor, authority, correlation, and payload schema; conflicting reuse is rejected. Integration tests confirm causality and state survive close/reopen. This is not a benchmark or comprehensive concurrency proof.

## Schema
`schema_migrations`: version (PK), immutable source-file SHA-256 checksum, applied timestamp.
`assignments`: id (PK), constrained state, owner, occupant_id, authority_ref, objective_ref, contract_ref, workflow_id, workflow_step, correlation_id, updated_at, version.
`events`: seq (identity PK), unique event_id, `rv.event.v1` schema, type, occurred/recorded times, assignment, actor, correlation/causation, unique idempotency key, authority reference, privacy domain, payload schema, and JSONB payload.

## Limitations and open work
- `verified=True` is only an untrusted caller assertion, **not independent verification**. Never expose this API to untrusted callers or connect it directly to hardware dispatch.
- No authentication or authorization layer, authority grant validation, independent verifier, audit of readers, connection pooling, automatic reconnect, backups/restore drills, outbox, worker, service, or health endpoint.
- Migration DDL is not yet applied to shared `riverview_dev`; deployment there and M1.2 acceptance remain gated by M1.1 Steward acceptance.
- `list_assignments()` and `events()` are unbounded and intended for small development datasets; use pagination for real dashboard use.
- Steward readout currently is an **on-demand snapshot**, not a continuously refreshed Steward dashboard.

## Evidence and acceptance
RV-M1.2-001 ran five PostgreSQL integration tests against a disposable PostgreSQL 16 UTF-8 cluster and unique temporary schemas. Migration apply/rerun/drift, atomic rollback on injected event failure, legal/illegal and duplicate transitions, idempotency collision, causality, reconnect persistence, and independent assignment progress passed. The cluster and test schemas were removed. These are technical M1.2 results, not Steward acceptance or full component DoD. See `POSTGRES_LEDGER_COOKBOOK.md`, `POSTGRES_LEDGER_FLOW.md`, and linked checkout evidence.
