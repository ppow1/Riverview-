-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0011_external_reasoning_exchange.sql
-- Component: RESIDENT-REASONING
-- Revision: 1.0.1
-- Purpose: Persist bounded external reasoning requests, claims, advisory results and consumption
-- Execution Model: Additive PostgreSQL outbox and append-only exchange event ledger
-- Observability: Request/correlation IDs, state, fences, deadlines and sanitized diagnostics
-- Dependencies: Resident execution migrations 0001-0010; PostgreSQL 16
-- Authority: Exchange transport only; advisory results cannot approve or execute work
-- Rollback: Retain exchange history; disable the adapter. Do not delete rows.
-- Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Initial durable exchange schema
-- =============================================================================
CREATE TABLE external_reasoning_exchanges (
    request_id UUID PRIMARY KEY,
    correlation_id UUID NOT NULL UNIQUE,
    original_request_id TEXT NOT NULL,
    originating_resident_id TEXT NOT NULL CHECK (length(originating_resident_id) BETWEEN 1 AND 256),
    objective_id TEXT NOT NULL REFERENCES grace_objectives(objective_id),
    conversation_id UUID NOT NULL,
    message_sequence BIGINT NOT NULL CHECK (message_sequence > 0),
    proposal_id TEXT,
    proposal_revision INTEGER,
    request_schema TEXT NOT NULL CHECK (request_schema = 'rv.external-reasoning.request.v1'),
    response_schema TEXT NOT NULL CHECK (response_schema = 'rv.external-reasoning.response.v1'),
    reason TEXT NOT NULL CHECK (reason IN ('task_complexity','capability_gap','low_confidence')),
    context_sha256 TEXT NOT NULL CHECK (context_sha256 ~ '^[0-9a-f]{64}$'),
    classification TEXT NOT NULL CHECK (classification IN ('institutional','confidential','restricted','local_only')),
    provider_id TEXT NOT NULL CHECK (length(provider_id) BETWEEN 1 AND 160),
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 240),
    request_sha256 TEXT NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    request_payload JSONB NOT NULL CHECK (jsonb_typeof(request_payload) = 'object'),
    delivery_state TEXT NOT NULL CHECK (delivery_state IN
        ('awaiting_delivery','awaiting_external_claim','awaiting_response',
         'response_received','grace_consumed','expired','failed')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    deadline_at TIMESTAMPTZ NOT NULL,
    delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts BETWEEN 0 AND 5),
    next_delivery_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    delivery_owner TEXT,
    delivery_token UUID,
    delivery_fence BIGINT NOT NULL DEFAULT 0 CHECK (delivery_fence >= 0),
    delivery_lease_until TIMESTAMPTZ,
    claim_owner TEXT,
    claim_token UUID,
    claim_fence BIGINT NOT NULL DEFAULT 0 CHECK (claim_fence >= 0),
    claim_lease_until TIMESTAMPTZ,
    claim_attempts INTEGER NOT NULL DEFAULT 0 CHECK (claim_attempts >= 0),
    response_payload JSONB,
    response_sha256 TEXT CHECK (response_sha256 IS NULL OR response_sha256 ~ '^[0-9a-f]{64}$'),
    response_provenance JSONB CHECK (response_provenance IS NULL OR jsonb_typeof(response_provenance)='object'),
    response_idempotency_key TEXT UNIQUE,
    response_received_at TIMESTAMPTZ,
    consumption_key TEXT UNIQUE,
    consumption_owner TEXT,
    consumption_token UUID,
    consumption_fence BIGINT NOT NULL DEFAULT 0 CHECK (consumption_fence >= 0),
    consumption_lease_until TIMESTAMPTZ,
    consumed_at TIMESTAMPTZ,
    consumption_result JSONB CHECK (consumption_result IS NULL OR jsonb_typeof(consumption_result)='object'),
    last_error_code TEXT CHECK (last_error_code IS NULL OR last_error_code ~ '^[a-z0-9_]{1,80}$'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (deadline_at > requested_at),
    CHECK ((proposal_id IS NULL) = (proposal_revision IS NULL)),
    CHECK ((delivery_owner IS NULL) = (delivery_token IS NULL)),
    CHECK ((delivery_token IS NULL) = (delivery_lease_until IS NULL)),
    CHECK ((claim_owner IS NULL) = (claim_token IS NULL)),
    CHECK ((claim_token IS NULL) = (claim_lease_until IS NULL)),
    CHECK ((consumption_owner IS NULL) = (consumption_token IS NULL)),
    CHECK ((consumption_token IS NULL) = (consumption_lease_until IS NULL)),
    CHECK ((response_payload IS NULL AND response_sha256 IS NULL AND response_provenance IS NULL
            AND response_received_at IS NULL AND response_idempotency_key IS NULL)
        OR (response_payload IS NOT NULL AND response_sha256 IS NOT NULL
            AND response_provenance IS NOT NULL AND response_received_at IS NOT NULL
            AND response_idempotency_key IS NOT NULL)),
    CHECK ((delivery_state IN ('response_received','grace_consumed') AND response_payload IS NOT NULL)
        OR delivery_state NOT IN ('response_received','grace_consumed')),
    CHECK ((delivery_state='grace_consumed' AND consumed_at IS NOT NULL AND consumption_key IS NOT NULL)
        OR delivery_state<>'grace_consumed')
);

ALTER TABLE external_reasoning_exchanges
    ADD CONSTRAINT external_reasoning_proposal_revision_fk
    FOREIGN KEY (proposal_id,proposal_revision)
    REFERENCES institutional_proposal_revisions(proposal_id,revision);

CREATE INDEX external_reasoning_delivery_ready
    ON external_reasoning_exchanges(next_delivery_at,requested_at)
    WHERE delivery_state='awaiting_delivery';
CREATE INDEX external_reasoning_claim_expiry
    ON external_reasoning_exchanges(claim_lease_until)
    WHERE delivery_state='awaiting_response';
CREATE INDEX external_reasoning_objective_history
    ON external_reasoning_exchanges(objective_id,requested_at,request_id);
CREATE INDEX external_reasoning_conversation_history
    ON external_reasoning_exchanges(conversation_id,message_sequence);

CREATE TABLE external_reasoning_exchange_events (
    sequence BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES external_reasoning_exchanges(request_id),
    correlation_id UUID NOT NULL,
    event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 80),
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 240),
    actor_id TEXT NOT NULL CHECK (length(actor_id) BETWEEN 1 AND 256),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload)='object'),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX external_reasoning_events_history
    ON external_reasoning_exchange_events(request_id,sequence);

DO $$
DECLARE runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=runtime_role) THEN
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT SELECT,INSERT ON %I.external_reasoning_exchanges TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT UPDATE (delivery_state,delivery_attempts,next_delivery_at,delivery_owner,delivery_token,delivery_fence,delivery_lease_until,claim_owner,claim_token,claim_fence,claim_lease_until,claim_attempts,response_payload,response_sha256,response_provenance,response_idempotency_key,response_received_at,consumption_key,consumption_owner,consumption_token,consumption_fence,consumption_lease_until,consumed_at,consumption_result,last_error_code,updated_at) ON %I.external_reasoning_exchanges TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT SELECT,INSERT ON %I.external_reasoning_exchange_events TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT USAGE ON SEQUENCE %I.external_reasoning_exchange_events_sequence_seq TO %I',current_schema(),runtime_role);
    END IF;
END;
$$;
