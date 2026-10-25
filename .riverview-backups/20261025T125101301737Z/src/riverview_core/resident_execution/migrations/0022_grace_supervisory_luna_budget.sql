-- Durable financial authorization paired with the existing AuthorityRegistry grant.
CREATE TABLE grace_supervisory_authorizations (
    authorization_id UUID PRIMARY KEY,
    authority_grant_id TEXT NOT NULL UNIQUE,
    authorized_by TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    total_budget_usd NUMERIC(12,8) NOT NULL CHECK (total_budget_usd=5.00000000),
    per_request_limit_usd NUMERIC(12,8) NOT NULL CHECK (per_request_limit_usd=0.05000000),
    scope JSONB NOT NULL CHECK (scope='{"functions":["cme_diagnostic_recovery","performance_evaluation"],"provider_id":"gpt-6-luna"}'::jsonb),
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    activated_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('pending','active','revoked','exhausted'))
);
CREATE UNIQUE INDEX grace_supervisory_single_pending_active
    ON grace_supervisory_authorizations ((status)) WHERE status IN ('pending','active');
CREATE TABLE grace_supervisory_authorization_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    authorization_id UUID NOT NULL REFERENCES grace_supervisory_authorizations(authorization_id),
    event_type TEXT NOT NULL CHECK (event_type IN ('activated','luna_reserved','luna_settled','revoked','budget_exhausted')),
    idempotency_key TEXT NOT NULL UNIQUE,
    objective_id TEXT,
    request_id UUID,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload)='object'),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX grace_supervisory_authorization_events_order
    ON grace_supervisory_authorization_events(authorization_id,occurred_at,event_id);
CREATE FUNCTION reject_grace_supervisory_authorization_event_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'supervisory authorization events are append-only'; END; $$;
CREATE TRIGGER grace_supervisory_authorization_events_append_only
    BEFORE UPDATE OR DELETE ON grace_supervisory_authorization_events
    FOR EACH ROW EXECUTE FUNCTION reject_grace_supervisory_authorization_event_mutation();
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT SELECT,INSERT,UPDATE (activated_at,status) ON %I.grace_supervisory_authorizations TO riverview_core',current_schema());
        EXECUTE format('GRANT SELECT,INSERT ON %I.grace_supervisory_authorization_events TO riverview_core',current_schema());
    END IF;
END $$;
