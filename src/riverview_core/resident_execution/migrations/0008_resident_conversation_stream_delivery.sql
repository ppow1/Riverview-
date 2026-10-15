-- File Revision: 1.0.0
-- Task: RV-GRACE-LIVE-STREAMING-001
-- Purpose: Persist bounded, resumable conversation stream events until the final response is recorded.
-- Authority: Dashboard runtime may read/insert/update only this stream projection; canonical messages remain in the conversation ledger.
CREATE TABLE resident_conversation_streams (
    request_id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES resident_conversations(conversation_id),
    status TEXT NOT NULL CHECK (status IN ('queued','generating','completed','deferred','failed','interrupted')),
    generation INTEGER NOT NULL DEFAULT 0 CHECK (generation >= 0),
    event_sequence BIGINT NOT NULL DEFAULT 0 CHECK (event_sequence >= 0),
    output_bytes INTEGER NOT NULL DEFAULT 0 CHECK (output_bytes BETWEEN 0 AND 8192),
    events JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(events) = 'array'),
    provider_ref TEXT,
    model_id TEXT,
    reasoning_stage TEXT CHECK (reasoning_stage IS NULL OR reasoning_stage IN ('autonomic','interim_30b','reasoning')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX resident_conversation_streams_recent
    ON resident_conversation_streams(conversation_id,updated_at DESC);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE ON resident_conversation_streams TO riverview_core';
    END IF;
END;
$$;
