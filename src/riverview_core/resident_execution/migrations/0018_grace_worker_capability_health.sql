-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0018_grace_worker_capability_health.sql
-- Component: RESIDENT-ORCHESTRATION
-- Revision: 1.0.0
-- Purpose: Persist configured in-process worker capabilities with Grace health
-- Execution Model: Additive, checksum-pinned PostgreSQL migration
-- Observability: Grace health row and Dashboard worker readiness projection
-- Dependencies: Resident execution migration 0002; PostgreSQL 16
-- Authority: Narrow column-scoped write grant to the Grace runtime role
-- Changed: 2026-10-23 UTC | RV-WORKER-HEALTH-SNAPSHOT-20261023 | Distinguish idle workers from workers without runtime evidence
-- Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md; docs/components/STATUS_DASHBOARD.md
-- Tests: tests/test_status_dashboard.py
-- History: Git and protected predecessor backup
-- =============================================================================
ALTER TABLE grace_execution_health
    ADD COLUMN worker_capabilities JSONB NOT NULL DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(worker_capabilities) = 'array');

DO $$
DECLARE
    runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = runtime_role) THEN
        EXECUTE format(
            'GRANT INSERT (worker_capabilities), UPDATE (worker_capabilities) ON %I.grace_execution_health TO %I',
            current_schema(), runtime_role);
    END IF;
END;
$$;
