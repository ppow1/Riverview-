-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/worker_adapter/migrations/0003_independent_verification.sql
-- Component: OUTCOME-VERIFIER
-- Revision: 1.0.0
-- Purpose: Persist independent artifact verification and gate completion
-- Execution Model: Explicit PostgreSQL migration; never applied by adapter
-- Observability: Verification decision, criteria, provenance, and verifier identity
-- Dependencies: PostgreSQL 16; worker-adapter migrations 0001 and 0002
-- Authority: DDL limited to explicitly selected schema
-- Changed: 2026-10-10 UTC | RV-M2.2-001 | Initial independent verification ledger
-- Contracts: docs/components/WORKER_ADAPTER.md; docs/architecture/EVENT_AND_ASSIGNMENT_CONTRACT_v0.1.md
-- Tests: tests/test_worker_adapter.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE verification_records (
    verification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id TEXT NOT NULL REFERENCES assignments(id),
    attempt_id UUID NOT NULL UNIQUE REFERENCES worker_attempts(attempt_id),
    executor_id TEXT NOT NULL REFERENCES worker_registry(worker_id),
    verifier_id TEXT NOT NULL REFERENCES worker_registry(worker_id),
    verifier_revision TEXT NOT NULL CHECK (length(verifier_revision)>0),
    decision TEXT NOT NULL CHECK (decision IN ('ACCEPTED','REJECTED','INCONCLUSIVE')),
    criteria JSONB NOT NULL CHECK (jsonb_typeof(criteria)='object'),
    evidence_references JSONB NOT NULL CHECK (jsonb_typeof(evidence_references)='array'),
    summary TEXT NOT NULL CHECK (length(summary)>0),
    idempotency_key TEXT NOT NULL UNIQUE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (executor_id<>verifier_id)
);
CREATE INDEX verification_records_assignment_idx
    ON verification_records(assignment_id,recorded_at,verification_id);

CREATE FUNCTION require_independent_verification_for_completion()
RETURNS trigger LANGUAGE plpgsql AS $rv$
BEGIN
    IF NEW.state='completed' AND OLD.state IS DISTINCT FROM NEW.state THEN
        IF NOT EXISTS (
            SELECT 1 FROM verification_records v
            WHERE v.assignment_id=NEW.id AND v.decision='ACCEPTED'
        ) THEN
            RAISE EXCEPTION 'completion requires persisted independent verification';
        END IF;
    END IF;
    RETURN NEW;
END;
$rv$;
CREATE TRIGGER assignment_completion_requires_verification
    BEFORE UPDATE OF state ON assignments
    FOR EACH ROW EXECUTE FUNCTION require_independent_verification_for_completion();
