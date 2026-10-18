-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0013_bounded_deferred_retries.sql
-- Component: RESIDENT-CONVERSATION
-- Revision: 1.0.1
-- Purpose: Persist bounded retry/backoff state for deferred reasoning requests
-- Execution Model: Additive PostgreSQL migration
-- Observability: Safe attempt count, next retry, last error code and blocked state
-- Dependencies: Resident execution migrations 0001-0012; PostgreSQL 16
-- Authority: Retry scheduling only; does not grant conversation or model authority
-- Changed: 2026-10-18 UTC | RV-C3-GRACE-REASONING-RELIABILITY-001 | Add capped durable retry state
-- Changed: 2026-10-18 UTC | RV-PR115-0013-RUNTIME-ACL | Grant retry-table runtime access with no delete or truncate authority
-- Contracts: docs/components/RESIDENT_CONVERSATION.md
-- Tests: tests/test_resident_conversation.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE resident_deferred_retry_state (
    request_id UUID PRIMARY KEY,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    next_attempt_at TIMESTAMPTZ,
    last_error_code TEXT,
    blocked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (blocked_at IS NULL OR next_attempt_at IS NULL)
);

CREATE INDEX resident_deferred_retry_due
    ON resident_deferred_retry_state(next_attempt_at)
    WHERE blocked_at IS NULL;

DO $$
DECLARE runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=runtime_role) THEN
        EXECUTE format(
            'GRANT SELECT, INSERT, UPDATE (attempt_count,next_attempt_at,last_error_code,blocked_at,updated_at) ON %I.resident_deferred_retry_state TO %I',
            current_schema(), runtime_role);
    END IF;
END;
$$;
