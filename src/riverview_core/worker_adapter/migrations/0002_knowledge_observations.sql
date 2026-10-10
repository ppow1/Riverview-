-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/worker_adapter/migrations/0002_knowledge_observations.sql
-- Component: WORKER-ADAPTER
-- Revision: 1.0.1
-- Purpose: Persist fail-closed knowledge lookup and action preflight provenance
-- Execution Model: Explicit PostgreSQL migration; never applied by adapter
-- Observability: knowledge_observations status, operation and source provenance
-- Dependencies: PostgreSQL 16; worker-adapter migration 0001
-- Authority: DDL limited to explicitly selected schema
-- Changed: 2026-10-10 UTC | RV-M1.3-CONTINUOUS-KNOWLEDGE | Initial observation ledger
-- Contracts: docs/components/WORKER_ADAPTER.md
-- Tests: tests/test_worker_adapter.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE knowledge_observations (
    observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id TEXT NOT NULL REFERENCES assignments(id),
    worker_id TEXT NOT NULL REFERENCES worker_registry(worker_id),
    operation TEXT NOT NULL CHECK (operation IN
        ('ground_assignment','preflight_action','reground_assignment','record_learning')),
    status TEXT NOT NULL CHECK (status IN
        ('VERIFIED','NO_MATCH','UNAVAILABLE','INCOMPLETE','CONTRADICTORY','UNVERIFIED')),
    action TEXT,
    source_references JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(source_references)='array'),
    source_revision TEXT,
    source_sha256 CHAR(64) CHECK (source_sha256 IS NULL OR source_sha256 ~ '^[0-9a-f]{64}$'),
    retrieval_complete BOOLEAN,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX knowledge_observations_assignment_idx
    ON knowledge_observations(assignment_id,recorded_at,observation_id);
