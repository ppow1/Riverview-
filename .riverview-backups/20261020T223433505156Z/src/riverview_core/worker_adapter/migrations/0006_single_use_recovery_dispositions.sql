-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/worker_adapter/migrations/0006_single_use_recovery_dispositions.sql
-- Component: WORKER-ADAPTER
-- Revision: 1.0.0
-- Purpose: Record one authorized, append-only retry disposition per assignment
-- Execution Model: Explicit checksum-pinned PostgreSQL migration
-- Observability: worker_recovery_dispositions and assignment recovery events
-- Dependencies: Worker adapter migrations 0001-0005; assignment/event ledger
-- Authority: No grant is created; runtime requires existing service.recover authority
-- Changed: 2026-10-20 UTC | RV-GRACE-S3-RECOVERY-DISPOSITION-001 | Add unique immutable exact-assignment recovery authorization records
-- Tests: tests/test_worker_adapter.py
-- History: Git and protected predecessor snapshot
-- =============================================================================

ALTER TABLE events DROP CONSTRAINT events_event_type_check;
ALTER TABLE events ADD CONSTRAINT events_event_type_check CHECK (event_type IN (
    'assignment.created','assignment.transitioned','assignment.recovery_dispositioned'));

CREATE TABLE worker_recovery_dispositions (
    disposition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id TEXT NOT NULL UNIQUE REFERENCES assignments(id),
    objective_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    artifact_contract_sha256 CHAR(64) NOT NULL
        CHECK (artifact_contract_sha256 ~ '^[0-9a-f]{64}$'),
    prior_retry_count INTEGER NOT NULL CHECK (prior_retry_count > 0),
    authorized_generation BIGINT NOT NULL CHECK (authorized_generation > 0),
    worker_id TEXT NOT NULL REFERENCES worker_registry(worker_id),
    authorization_reference TEXT NOT NULL CHECK (length(authorization_reference) BETWEEN 1 AND 240),
    authorization_principal_id TEXT NOT NULL,
    authorization_grant_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 16 AND 200),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION reject_worker_recovery_disposition_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'worker recovery dispositions are append-only';
END;
$$;

CREATE TRIGGER worker_recovery_dispositions_append_only
    BEFORE UPDATE OR DELETE ON worker_recovery_dispositions
    FOR EACH ROW EXECUTE FUNCTION reject_worker_recovery_disposition_mutation();

REVOKE ALL ON worker_recovery_dispositions FROM PUBLIC;
REVOKE ALL ON FUNCTION reject_worker_recovery_disposition_mutation() FROM PUBLIC;

DO $$
DECLARE runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=runtime_role) THEN
        EXECUTE format('GRANT SELECT, INSERT ON worker_recovery_dispositions TO %I', runtime_role);
    END IF;
END;
$$;
