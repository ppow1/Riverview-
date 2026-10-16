-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/worker_adapter/migrations/0006_verifier_revision_rechecks.sql
-- Component: WORKER-ADAPTER
-- Revision: 1.0.0
-- Purpose: Preserve append-only verifier decisions across a corrected verifier revision
-- Execution Model: Explicit PostgreSQL migration; never applied by adapter
-- Observability: Each decision retains its verifier revision and idempotency identity
-- Dependencies: PostgreSQL 16; worker-adapter migration 0003
-- Authority: DDL limited to explicitly selected schema
-- Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Allow one preserved decision per verifier revision for the same attempt
-- Contracts: docs/components/WORKER_ADAPTER.md; docs/components/GRACE_EXECUTION_PIPELINE.md
-- Tests: tests/test_worker_adapter.py; tests/test_grace_execution.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
-- This is deliberately fail-closed: the predecessor schema must contain the
-- named single-attempt unique constraint and the replacement must not exist.
DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid=c.conrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace
        WHERE n.nspname=current_schema()
          AND t.relname='verification_records'
          AND c.conname='verification_records_attempt_id_key'
          AND c.contype='u'
    ) THEN
        RAISE EXCEPTION 'expected predecessor verifier uniqueness constraint is missing';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid=c.conrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace
        WHERE n.nspname=current_schema()
          AND t.relname='verification_records'
          AND c.conname='verification_records_attempt_revision_key'
    ) THEN
        RAISE EXCEPTION 'verifier revision uniqueness constraint already exists';
    END IF;
    ALTER TABLE verification_records
        DROP CONSTRAINT verification_records_attempt_id_key;
    ALTER TABLE verification_records
        ADD CONSTRAINT verification_records_attempt_revision_key
        UNIQUE (attempt_id, verifier_revision);
END
$migration$;
