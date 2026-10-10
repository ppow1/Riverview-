-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/migrations/0001_assignment_event_ledger.sql
-- Component: POSTGRES-LEDGER
-- Revision: 1.0.0
-- Purpose: Create contract-aligned durable assignment, event, and migration tables
-- Execution Model: Applied transactionally by postgres_migrations.py
-- Observability: schema_migrations and append-only event rows
-- Dependencies: PostgreSQL 16; caller-selected isolated schema
-- Authority: DDL is restricted to the explicitly selected schema
-- Changed: 2026-10-10 UTC | RV-M1.2-001 | Initial M1.2 durable ledger schema
-- Contracts: docs/components/POSTGRES_LEDGER.md; docs/architecture/EVENT_AND_ASSIGNMENT_CONTRACT_v0.1.md
-- Tests: tests/test_postgres_ledger.py
-- History: Git
-- =============================================================================
CREATE TABLE schema_migrations (
    version TEXT PRIMARY KEY,
    checksum TEXT NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE assignments (
    id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK (state IN (
        'queued','ready','running','awaiting_verification','rework_required',
        'blocked','awaiting_steward','completed','cancelled')),
    owner TEXT NOT NULL,
    occupant_id TEXT,
    authority_ref TEXT NOT NULL,
    objective_ref TEXT NOT NULL,
    contract_ref TEXT,
    workflow_id TEXT NOT NULL,
    workflow_step TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0)
);

CREATE TABLE events (
    seq BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    "schema" TEXT NOT NULL CHECK ("schema" = 'rv.event.v1'),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'assignment.created','assignment.transitioned')),
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    assignment_id TEXT NOT NULL REFERENCES assignments(id),
    actor_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    causation_id UUID REFERENCES events(event_id),
    idempotency_key TEXT NOT NULL UNIQUE,
    authority_ref TEXT NOT NULL,
    privacy_domain TEXT NOT NULL,
    payload_schema TEXT NOT NULL,
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object')
);

CREATE INDEX events_assignment_seq_idx ON events(assignment_id, seq);
CREATE INDEX events_correlation_idx ON events(correlation_id, seq);
