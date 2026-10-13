-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0000_authority_migration_ledger.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Bootstrap a checksum ledger for fresh dedicated authority schemas
-- Execution Model: Applied transactionally by postgres_migrations.py before authority tables
-- Observability: Versioned migration checksums and timestamps
-- Dependencies: PostgreSQL 16; caller-selected dedicated authority schema
-- Authority: Creates only the local schema_migrations table when absent
-- Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
-- Tests: tests/test_institutional_authority.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    checksum TEXT NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
