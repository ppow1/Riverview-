-- File Revision: 1.0.0
-- Durable Steward decisions for one exact CME Grace-blocked escalation.
-- The request authorizes at most one bounded retry; a receipt is not a decision.
CREATE TABLE grace_recovery_decision_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_event_id UUID NOT NULL UNIQUE REFERENCES cme_monitor_events(event_id),
    notification_id UUID NOT NULL UNIQUE REFERENCES attention_notifications(notification_id),
    objective_id TEXT NOT NULL,
    objective_revision INTEGER NOT NULL CHECK (objective_revision > 0),
    recovery_action TEXT NOT NULL CHECK (recovery_action='retry_reasoning_once'),
    attempt_limit SMALLINT NOT NULL CHECK (attempt_limit=1),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','deferred','rejected','expired','dispatched','consumed')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    decided_at TIMESTAMPTZ,
    CHECK ((status='pending' AND decided_at IS NULL) OR
           (status<>'pending' AND decided_at IS NOT NULL))
);
CREATE TABLE grace_recovery_decision_events (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES grace_recovery_decision_requests(request_id),
    source_event_id UUID NOT NULL REFERENCES cme_monitor_events(event_id),
    objective_id TEXT NOT NULL,
    objective_revision INTEGER NOT NULL,
    recovery_action TEXT NOT NULL CHECK (recovery_action='retry_reasoning_once'),
    decision TEXT NOT NULL CHECK (decision IN ('approve','defer','reject')),
    actor_principal_id TEXT NOT NULL,
    authority_reference TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 1000),
    idempotency_key TEXT NOT NULL UNIQUE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION reject_grace_recovery_decision_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'grace recovery decisions are append-only'; END; $$;
CREATE TRIGGER grace_recovery_decision_events_append_only
    BEFORE UPDATE OR DELETE ON grace_recovery_decision_events
    FOR EACH ROW EXECUTE FUNCTION reject_grace_recovery_decision_mutation();

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT SELECT,INSERT,UPDATE (status,decided_at) ON %I.grace_recovery_decision_requests TO riverview_core',current_schema());
        EXECUTE format('GRANT SELECT,INSERT ON %I.grace_recovery_decision_events TO riverview_core',current_schema());
    END IF;
END $$;

-- Backfill the already delivered escalation without changing its notification or source event.
INSERT INTO grace_recovery_decision_requests
    (source_event_id,notification_id,objective_id,objective_revision,recovery_action,
     attempt_limit,expires_at)
SELECT e.event_id,n.notification_id,e.details->>'objective_id',
       (e.details->>'objective_revision')::integer,'retry_reasoning_once',1,
       clock_timestamp()+interval '24 hours'
FROM cme_monitor_events e
JOIN attention_notifications n ON n.source_event_id=e.event_id
WHERE e.event_type='grace_objective_blocked'
  AND jsonb_typeof(e.details->'objective_revision')='number'
ON CONFLICT (source_event_id) DO NOTHING;
