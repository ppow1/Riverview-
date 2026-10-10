-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/event_processor/migrations/0002_event_processor_cursor.sql
-- Component: EVENT-PROCESSOR
-- Revision: 1.0.0
-- Purpose: Persist an ordered event-consumer checkpoint per processor identity
-- Execution Model: Explicit transaction through the versioned migration runner
-- Observability: Durable last_seq and updated_at per consumer
-- Dependencies: PostgreSQL 16; POSTGRES-LEDGER migration 0001
-- Authority: DDL limited to explicitly selected target schema
-- Changed: 2026-10-10 UTC | RV-M1.3-001 | Initial durable event processor cursor
-- Contracts: docs/development/M1.3-001_REVISION_RECORD.md
-- Tests: tests/test_event_processor.py
-- History: Git
-- =============================================================================
CREATE TABLE event_processor_cursors (
    consumer_id TEXT PRIMARY KEY,
    last_seq BIGINT NOT NULL DEFAULT 0 CHECK (last_seq >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
