-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0020_external_reasoning_source_kinds.sql
-- Component: RESIDENT-REASONING
-- Revision: 1.0.0
-- Purpose: Correlate durable external reasoning to non-conversation objective events
-- Execution Model: Additive schema change to the existing exchange
-- Observability: Explicit source kind; nullable conversation fields only for event sources
-- Authority: Existing resident.reasoning.escalate grant remains required
-- Rollback: Retain exchange history; source_kind defaults existing requests to conversation
-- =============================================================================
ALTER TABLE external_reasoning_exchanges
    ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'conversation';

ALTER TABLE external_reasoning_exchanges
    DROP CONSTRAINT external_reasoning_exchanges_message_sequence_check,
    ALTER COLUMN conversation_id DROP NOT NULL,
    ALTER COLUMN message_sequence DROP NOT NULL,
    ADD CONSTRAINT external_reasoning_source_kind_check
        CHECK (source_kind IN ('conversation','cme_diagnostic_recovery','performance_evaluation')),
    ADD CONSTRAINT external_reasoning_source_correlation_check
        CHECK ((source_kind='conversation' AND conversation_id IS NOT NULL AND message_sequence > 0)
            OR (source_kind<>'conversation' AND conversation_id IS NULL AND message_sequence IS NULL));

ALTER TABLE external_reasoning_exchanges
    ADD CONSTRAINT external_reasoning_request_type_check
    CHECK (request_payload->>'request_type' IN
        ('objective_reasoning','proposal_review','cme_diagnostic_recovery','performance_evaluation'));

DO $$
DECLARE runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=runtime_role) THEN
        EXECUTE format('GRANT INSERT (source_kind) ON %I.external_reasoning_exchanges TO %I',current_schema(),runtime_role);
    END IF;
END;
$$;
