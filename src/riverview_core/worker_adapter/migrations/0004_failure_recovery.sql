-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/worker_adapter/migrations/0004_failure_recovery.sql
-- Component: WORKER-ADAPTER
-- Revision: 1.0.0
-- Purpose: Persist pre-action effect classification and restart reconciliation
-- Execution Model: Explicit PostgreSQL migration; never applied by adapter
-- Observability: Durable execution intents and one recovery decision per lease
-- Dependencies: PostgreSQL 16; worker-adapter migration 0001 and scheduler lease
-- Authority: DDL limited to explicitly selected schema
-- Changed: 2026-10-10 UTC | RV-M2.3-001 | Add durable recovery records
-- Contracts: docs/ROADMAP.md; docs/components/WORKER_ADAPTER.md
-- Tests: tests/test_worker_adapter.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE worker_execution_intents (
    intent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id TEXT NOT NULL REFERENCES assignments(id),
    worker_id TEXT NOT NULL REFERENCES worker_registry(worker_id),
    lease_generation BIGINT NOT NULL CHECK (lease_generation > 0),
    capability TEXT NOT NULL,
    effect_class TEXT NOT NULL CHECK (effect_class IN ('retry_safe','external_uncertain')),
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN
        ('running','succeeded','failed','retry_scheduled','outcome_unknown')),
    attempt_id UUID REFERENCES worker_attempts(attempt_id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    failure_class TEXT,
    UNIQUE (assignment_id,lease_generation),
    CHECK ((status='running' AND finished_at IS NULL) OR
           (status<>'running' AND finished_at IS NOT NULL))
);
CREATE INDEX worker_execution_intents_status_idx
    ON worker_execution_intents(status,started_at);

CREATE TABLE worker_recovery_records (
    recovery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id TEXT NOT NULL REFERENCES assignments(id),
    lease_generation BIGINT NOT NULL CHECK (lease_generation > 0),
    intent_id UUID REFERENCES worker_execution_intents(intent_id),
    attempt_id UUID REFERENCES worker_attempts(attempt_id),
    decision TEXT NOT NULL CHECK (decision IN
        ('retry_safe','outcome_unknown','result_preserved')),
    previous_state TEXT NOT NULL,
    resulting_state TEXT NOT NULL,
    observed_expiry TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (assignment_id,lease_generation)
);
CREATE INDEX worker_recovery_records_assignment_idx
    ON worker_recovery_records(assignment_id,recorded_at,recovery_id);
