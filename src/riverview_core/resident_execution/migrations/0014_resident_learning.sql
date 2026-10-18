-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0014_resident_learning.sql
-- Component: RESIDENT-LEARNING-GOVERNANCE
-- Revision: 1.0.0
-- Purpose: Add append-only resident-scoped learning revisions and lifecycle evidence
-- Execution Model: Explicit additive migration; never applied by service startup
-- Observability: Resident learning event history and immutable content digests
-- Dependencies: PostgreSQL 16; resident_execution migration chain through 0013
-- Authority: Grants no runtime privileges, grants, identity, or approval authority
-- Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-IMPLEMENTATION-001 | Initial dormant learning persistence
-- Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md
-- Tests: tests/test_resident_learning_postgres.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================

CREATE TABLE resident_learning_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    originating_resident_id TEXT NOT NULL CHECK
        (originating_resident_id ~ '^resident:[A-Za-z0-9._:-]{1,220}$'),
    scope_ref TEXT NOT NULL CHECK
        (scope_ref='institution:riverview' OR scope_ref=originating_resident_id),
    classification TEXT NOT NULL CHECK
        (classification IN ('internal','confidential','restricted','local_only')),
    retention TEXT NOT NULL CHECK (retention='bounded_durable'),
    content_sha256 CHAR(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 240),
    created_at TIMESTAMPTZ NOT NULL,
    CHECK (scope_ref<>'institution:riverview' OR classification<>'local_only')
);

CREATE TABLE resident_learning_revisions (
    record_id UUID NOT NULL REFERENCES resident_learning_records(record_id),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 12000),
    content_sha256 CHAR(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    evidence JSONB NOT NULL CHECK
        (jsonb_typeof(evidence)='array' AND jsonb_array_length(evidence) BETWEEN 1 AND 50),
    provenance JSONB NOT NULL CHECK (jsonb_typeof(provenance)='object'),
    supersedes_record_id UUID REFERENCES resident_learning_records(record_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (record_id,revision)
);
CREATE INDEX resident_learning_scope_lookup
    ON resident_learning_records(scope_ref,created_at DESC);
CREATE INDEX resident_learning_revision_evidence
    ON resident_learning_revisions USING GIN(evidence);

CREATE TABLE resident_learning_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id UUID NOT NULL REFERENCES resident_learning_records(record_id),
    revision INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN
        ('candidate_created','validated','validation_inconclusive','approved','rejected',
         'correction_started','rollback_restored','rollback_superseded')),
    status_after TEXT NOT NULL CHECK
        (status_after IN ('candidate','validated','approved','rejected','superseded','withdrawn')),
    actor_id TEXT NOT NULL CHECK (length(actor_id) BETWEEN 1 AND 256),
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 240),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload)='object'),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (record_id,revision)
        REFERENCES resident_learning_revisions(record_id,revision)
);
CREATE INDEX resident_learning_event_history
    ON resident_learning_events(record_id,event_id);

CREATE FUNCTION resident_learning_reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'resident learning records and events are append-only'
        USING ERRCODE='55000';
END;
$$;
CREATE TRIGGER resident_learning_records_immutable
    BEFORE UPDATE OR DELETE ON resident_learning_records
    FOR EACH ROW EXECUTE FUNCTION resident_learning_reject_mutation();
CREATE TRIGGER resident_learning_revisions_immutable
    BEFORE UPDATE OR DELETE ON resident_learning_revisions
    FOR EACH ROW EXECUTE FUNCTION resident_learning_reject_mutation();
CREATE TRIGGER resident_learning_events_immutable
    BEFORE UPDATE OR DELETE ON resident_learning_events
    FOR EACH ROW EXECUTE FUNCTION resident_learning_reject_mutation();

-- Intentionally no GRANT statements. This migration is a storage contract only.
