-- File Revision: 1.0.0
-- Component: RESIDENT-CONVERSATION
-- Purpose: Add owner-scoped titles, archive/deletion tombstones, and image attachment storage.
-- Authority: Existing exact conversation grants; no grants or identities are created here.
-- Retention: Conversation events remain immutable. Deletion is a reversible/access tombstone.
ALTER TABLE resident_conversations
    ADD COLUMN title TEXT NOT NULL DEFAULT 'New conversation'
        CHECK (length(title) BETWEEN 1 AND 120),
    ADD COLUMN archived_at TIMESTAMPTZ,
    ADD COLUMN deleted_at TIMESTAMPTZ,
    ADD COLUMN deleted_by TEXT;

CREATE INDEX resident_conversations_visible_recent
    ON resident_conversations(office_id,owner_principal_id,archived_at,updated_at DESC)
    WHERE deleted_at IS NULL;

CREATE TABLE resident_conversation_attachments (
    attachment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    event_sequence BIGINT NOT NULL CHECK (event_sequence > 0),
    media_type TEXT NOT NULL CHECK (media_type IN ('image/png','image/jpeg','image/webp')),
    file_name TEXT NOT NULL CHECK (length(file_name) BETWEEN 1 AND 160),
    sha256 TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    byte_length INTEGER NOT NULL CHECK (byte_length BETWEEN 1 AND 4194304),
    image_bytes BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (conversation_id,event_sequence)
        REFERENCES resident_conversation_events(conversation_id,sequence),
    UNIQUE (conversation_id,event_sequence,sha256),
    CHECK (octet_length(image_bytes)=byte_length)
);
CREATE INDEX resident_conversation_attachments_event
    ON resident_conversation_attachments(conversation_id,event_sequence);

CREATE TABLE resident_conversation_management_events (
    management_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES resident_conversations(conversation_id),
    actor_principal_id TEXT NOT NULL CHECK (length(actor_principal_id) BETWEEN 1 AND 256),
    event_type TEXT NOT NULL CHECK (event_type IN ('renamed','archived','restored','deleted')),
    details JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details)='object'),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX resident_conversation_management_history
    ON resident_conversation_management_events(conversation_id,recorded_at DESC);
CREATE FUNCTION reject_resident_conversation_management_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'resident conversation management events are append-only'; END;
$$;
CREATE TRIGGER resident_conversation_management_append_only
    BEFORE UPDATE OR DELETE ON resident_conversation_management_events
    FOR EACH ROW EXECUTE FUNCTION reject_resident_conversation_management_mutation();

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE 'GRANT SELECT, INSERT ON resident_conversation_attachments TO riverview_core';
        EXECUTE 'GRANT SELECT, INSERT ON resident_conversation_management_events TO riverview_core';
        EXECUTE 'GRANT UPDATE (title,archived_at,deleted_at,deleted_by,revision,updated_at) ON resident_conversations TO riverview_core';
    END IF;
END;
$$;
