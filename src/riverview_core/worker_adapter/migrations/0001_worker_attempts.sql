-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/worker_adapter/migrations/0001_worker_attempts.sql
-- Component: WORKER-ADAPTER
-- Revision: 1.0.0
-- Purpose: Persist scoped workers, execution attempts, and deterministic results
-- Execution Model: Explicit PostgreSQL migration; never applied by adapter
-- Observability: worker_registry, worker_attempts, worker_results
-- Dependencies: PostgreSQL 16; M1.2 assignment/event schema; M1.4 leases
-- Authority: DDL limited to explicitly selected schema
-- Changed: 2026-10-10 UTC | RV-M2.1-001 | Initial isolated worker ledger
-- Contracts: docs/development/M2.1-001_REVISION_RECORD.md
-- Tests: tests/test_worker_adapter.py
-- History: Git
-- =============================================================================
CREATE TABLE worker_registry (
    worker_id TEXT PRIMARY KEY,
    credential_sha256 BYTEA NOT NULL CHECK (octet_length(credential_sha256)=32),
    capabilities JSONB NOT NULL CHECK (jsonb_typeof(capabilities)='array'),
    scope_ref TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE worker_attempts (
    attempt_id UUID PRIMARY KEY,
    assignment_id TEXT NOT NULL REFERENCES assignments(id),
    worker_id TEXT NOT NULL REFERENCES worker_registry(worker_id),
    lease_generation BIGINT NOT NULL CHECK (lease_generation>0),
    capability TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    input_sha256 CHAR(64) NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
    status TEXT NOT NULL CHECK (status IN ('running','succeeded','failed','lease_lost')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    failure_class TEXT,
    CHECK ((status='running' AND finished_at IS NULL) OR
           (status<>'running' AND finished_at IS NOT NULL))
);
CREATE INDEX worker_attempts_assignment_idx ON worker_attempts(assignment_id,started_at,attempt_id);
CREATE INDEX worker_attempts_status_idx ON worker_attempts(status,started_at);

CREATE TABLE worker_results (
    attempt_id UUID PRIMARY KEY REFERENCES worker_attempts(attempt_id),
    result JSONB NOT NULL CHECK (jsonb_typeof(result)='object'),
    result_sha256 CHAR(64) NOT NULL CHECK (result_sha256 ~ '^[0-9a-f]{64}$'),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
