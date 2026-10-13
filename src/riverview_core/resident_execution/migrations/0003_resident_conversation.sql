-- File Revision: 1.0.0
-- Task: RV-M3.4-GRACE-CHAT
-- Purpose: Persist office-scoped resident conversation events and response outcomes.
CREATE TABLE resident_conversations (
    conversation_id UUID PRIMARY KEY,
    office_id TEXT NOT NULL CHECK (length(office_id) BETWEEN 1 AND 256),
    owner_principal_id TEXT NOT NULL CHECK (length(owner_principal_id) BETWEEN 1 AND 256),
    revision BIGINT NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX resident_conversations_owner_recent
    ON resident_conversations(office_id, owner_principal_id, updated_at DESC);

CREATE TABLE resident_conversation_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES resident_conversations(conversation_id),
    sequence BIGINT NOT NULL CHECK (sequence > 0),
    request_id UUID NOT NULL,
    client_message_id UUID,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'user_message','assistant_message','response_failed','response_interrupted')),
    actor_kind TEXT NOT NULL CHECK (actor_kind IN ('principal','resident','service')),
    actor_id TEXT NOT NULL CHECK (length(actor_id) BETWEEN 1 AND 256),
    occupant_id TEXT,
    implementation_id TEXT,
    implementation_revision TEXT,
    provider_ref TEXT,
    model_id TEXT,
    body TEXT CHECK (body IS NULL OR length(body) <= 8192),
    error_code TEXT CHECK (error_code IS NULL OR error_code IN (
        'model_provider_unavailable','model_binding_mismatch','context_too_large',
        'office_model_binding_changed','model_timeout','model_unavailable',
        'model_response_incomplete','model_response_invalid','service_restarted')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (conversation_id, sequence),
    UNIQUE (request_id, event_type),
    CHECK ((event_type IN ('user_message','assistant_message') AND body IS NOT NULL
               AND error_code IS NULL)
        OR (event_type IN ('response_failed','response_interrupted') AND body IS NULL
               AND error_code IS NOT NULL)),
    CHECK ((event_type='user_message' AND client_message_id IS NOT NULL)
        OR (event_type<>'user_message' AND client_message_id IS NULL))
);
CREATE UNIQUE INDEX resident_conversation_client_message_once
    ON resident_conversation_events(client_message_id)
    WHERE event_type='user_message' AND client_message_id IS NOT NULL;
CREATE INDEX resident_conversation_events_recent
    ON resident_conversation_events(conversation_id,sequence DESC);
CREATE INDEX resident_conversation_events_response_status
    ON resident_conversation_events(request_id,event_type);
