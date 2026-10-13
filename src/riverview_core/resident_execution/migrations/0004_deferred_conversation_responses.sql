-- File Revision: 1.0.0
-- Task: RV-GRACE-MULTISTAGE-ROUTING-001
-- Purpose: Persist deferrals until a required reasoning capability becomes ready.
ALTER TABLE resident_conversation_events
    DROP CONSTRAINT resident_conversation_events_event_type_check;
ALTER TABLE resident_conversation_events
    ADD CONSTRAINT resident_conversation_events_event_type_check CHECK (event_type IN (
        'user_message','assistant_message','response_failed','response_interrupted',
        'response_deferred'));
ALTER TABLE resident_conversation_events
    DROP CONSTRAINT resident_conversation_events_check;
ALTER TABLE resident_conversation_events
    ADD CONSTRAINT resident_conversation_events_check CHECK (
        (event_type IN ('user_message','assistant_message') AND body IS NOT NULL
            AND error_code IS NULL)
        OR (event_type IN ('response_failed','response_interrupted','response_deferred')
            AND body IS NULL AND error_code IS NOT NULL));
ALTER TABLE resident_conversation_events
    DROP CONSTRAINT resident_conversation_events_error_code_check;
ALTER TABLE resident_conversation_events
    ADD CONSTRAINT resident_conversation_events_error_code_check CHECK (error_code IS NULL
        OR error_code IN ('model_provider_unavailable','model_binding_mismatch',
            'context_too_large','office_model_binding_changed','model_timeout',
            'model_unavailable','model_response_incomplete','model_response_invalid',
            'service_restarted','reasoning_model_not_ready'));
CREATE INDEX resident_conversation_deferred_resume
    ON resident_conversation_events(occurred_at,request_id)
    WHERE event_type='response_deferred';
