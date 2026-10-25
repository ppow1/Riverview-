-- Durable envelope for the single authenticated Grace/Luna experiment approval.
CREATE TABLE grace_experiment_authorizations (
    authorization_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_key TEXT NOT NULL UNIQUE CHECK (experiment_key='grace-autonomy-luna-r2'),
    objective_id TEXT NOT NULL CHECK (objective_id='objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2'),
    objective_revision INTEGER NOT NULL CHECK (objective_revision=2),
    source_event_id UUID NOT NULL UNIQUE,
    authority_grant_id TEXT NOT NULL UNIQUE,
    luna_authority_grant_id TEXT NOT NULL,
    authorized_by TEXT NOT NULL,
    authority_reference TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    total_budget_usd NUMERIC(12,8) NOT NULL CHECK (total_budget_usd=5.00000000),
    prior_spend_usd NUMERIC(12,8) NOT NULL CHECK (prior_spend_usd=0.04104010),
    max_recovery_attempts SMALLINT NOT NULL CHECK (max_recovery_attempts=5),
    max_luna_requests SMALLINT NOT NULL CHECK (max_luna_requests=2),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','active','revoked','expired')),
    CHECK (expires_at>activated_at AND expires_at<=activated_at+interval '24 hours')
);
CREATE TABLE grace_experiment_authorization_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    authorization_id UUID NOT NULL REFERENCES grace_experiment_authorizations(authorization_id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'activated','recovery_claimed','reasoning_outcome','luna_reserved','luna_settled')),
    idempotency_key TEXT NOT NULL UNIQUE,
    objective_id TEXT NOT NULL,
    request_id UUID,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload)='object'),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX grace_experiment_authorization_events_order
    ON grace_experiment_authorization_events(authorization_id,occurred_at,event_id);
CREATE FUNCTION reject_grace_experiment_authorization_event_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'experiment authorization events are append-only'; END; $$;
CREATE TRIGGER grace_experiment_authorization_events_append_only
    BEFORE UPDATE OR DELETE ON grace_experiment_authorization_events
    FOR EACH ROW EXECUTE FUNCTION reject_grace_experiment_authorization_event_mutation();
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT SELECT,INSERT,UPDATE (status) ON %I.grace_experiment_authorizations TO riverview_core',current_schema());
        EXECUTE format('GRANT SELECT,INSERT ON %I.grace_experiment_authorization_events TO riverview_core',current_schema());
    END IF;
END $$;
