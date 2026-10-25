-- Allow one append-audited, Steward-gated increase to the exact r2 Luna cap.
ALTER TABLE grace_experiment_authorizations
    DROP CONSTRAINT grace_experiment_authorizations_max_luna_requests_check;
ALTER TABLE grace_experiment_authorizations
    ADD CONSTRAINT grace_experiment_authorizations_max_luna_requests_check
    CHECK (max_luna_requests IN (2,4));

ALTER TABLE grace_experiment_authorization_events
    DROP CONSTRAINT grace_experiment_authorization_events_event_type_check;
ALTER TABLE grace_experiment_authorization_events
    ADD CONSTRAINT grace_experiment_authorization_events_event_type_check
    CHECK (event_type IN ('activated','recovery_claimed','reasoning_outcome',
        'luna_reserved','luna_settled','amended'));

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT UPDATE (max_luna_requests) ON %I.grace_experiment_authorizations TO riverview_core',
                       current_schema());
    END IF;
END $$;
