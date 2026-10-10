-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/assignment_scheduler/migrations/0001_assignment_leases.sql
-- Component: ASSIGNMENT-SCHEDULER
-- Revision: 1.0.0
-- Purpose: Persist assignment worker lease owner, generation, and expiry
-- Execution Model: Explicit transaction through postgres_migrations.py
-- Observability: assignment_leases rows and schema_migrations checksum
-- Dependencies: PostgreSQL 16; M1.2 assignments table
-- Authority: DDL limited to explicit target schema; never applied by scheduler
-- Changed: 2026-10-10 UTC | RV-M1.4-001 | Initial isolated lease schema
-- Contracts: docs/development/M1.4-001_REVISION_RECORD.md
-- Tests: tests/test_assignment_scheduler.py
-- History: Git
-- =============================================================================
CREATE TABLE assignment_leases (
    assignment_id TEXT PRIMARY KEY REFERENCES assignments(id),
    worker_id TEXT NOT NULL,
    generation BIGINT NOT NULL CHECK (generation > 0),
    acquired_at TIMESTAMPTZ NOT NULL,
    heartbeat_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    CHECK (expires_at > acquired_at)
);

CREATE INDEX assignment_leases_expiry_idx ON assignment_leases(expires_at, assignment_id);
