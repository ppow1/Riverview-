-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/notifications/migrations/0007_external_push_delivery.sql
-- Component: NOTIFICATION-DELIVERY
-- Revision: 1.0.0
-- Purpose: Add durable provider-specific push outbox and delivery event ledger
-- Execution Model: Explicit additive migration; never applied at startup
-- Observability: Queue state, leases, retry schedule, provider acceptance and Pushover receipt
-- Dependencies: PostgreSQL 16; notification migration 0006
-- Authority: Notification delivery only; no assignment, decision, or work-order mutations
-- Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial push outbox schema
-- Contracts: docs/components/NOTIFICATION_IPHONE_DELIVERY.md
-- Tests: tests/test_notification_push.py
-- History: Git + .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE notification_delivery_queue (
    delivery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES attention_notifications(notification_id),
    provider TEXT NOT NULL CHECK (provider IN ('ntfy','pushover')),
    severity TEXT NOT NULL CHECK (severity IN ('info','warning','critical')),
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    message TEXT NOT NULL CHECK (length(message) BETWEEN 1 AND 1024),
    idempotency_key TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued','sending','retry','accepted','acknowledged','expired','failed')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL CHECK (max_attempts BETWEEN 1 AND 10),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    lease_id UUID,
    lease_until TIMESTAMPTZ,
    provider_receipt TEXT,
    provider_accepted_at TIMESTAMPTZ,
    next_receipt_check_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    last_error_code TEXT CHECK (last_error_code IS NULL OR length(last_error_code)<=80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(notification_id,provider),
    CHECK ((state='sending' AND lease_id IS NOT NULL AND lease_until IS NOT NULL)
        OR (state<>'sending' AND lease_id IS NULL AND lease_until IS NULL)),
    CHECK (acknowledged_at IS NULL OR
        (provider='pushover' AND severity='critical' AND provider_receipt IS NOT NULL))
);
CREATE INDEX notification_delivery_due_idx
    ON notification_delivery_queue(state,next_attempt_at,created_at)
    WHERE state IN ('queued','retry','sending');
CREATE INDEX notification_delivery_receipt_idx
    ON notification_delivery_queue(next_receipt_check_at)
    WHERE provider='pushover' AND severity='critical' AND state='accepted'
      AND provider_receipt IS NOT NULL AND acknowledged_at IS NULL;

CREATE TABLE notification_delivery_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id UUID NOT NULL REFERENCES notification_delivery_queue(delivery_id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'delivery_queued','delivery_claimed','provider_accepted','retry_scheduled',
        'delivery_failed','emergency_acknowledged','emergency_expired')),
    actor_type TEXT NOT NULL CHECK (actor_type='notification_delivery_worker'),
    idempotency_key TEXT NOT NULL UNIQUE,
    details JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details)='object'),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX notification_delivery_events_delivery_idx
    ON notification_delivery_events(delivery_id,recorded_at,event_id);
CREATE FUNCTION reject_notification_delivery_event_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'notification_delivery_events is append-only';
END;
$$;
CREATE TRIGGER notification_delivery_events_append_only
    BEFORE UPDATE OR DELETE ON notification_delivery_events
    FOR EACH ROW EXECUTE FUNCTION reject_notification_delivery_event_mutation();

CREATE TABLE notification_delivery_health (
    service_id TEXT PRIMARY KEY,
    instance_id UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('healthy','degraded')),
    last_heartbeat_at TIMESTAMPTZ NOT NULL,
    last_cycle_at TIMESTAMPTZ,
    last_error_code TEXT,
    notices_scanned BIGINT NOT NULL DEFAULT 0 CHECK (notices_scanned>=0),
    deliveries_queued BIGINT NOT NULL DEFAULT 0 CHECK (deliveries_queued>=0),
    provider_accepted BIGINT NOT NULL DEFAULT 0 CHECK (provider_accepted>=0),
    emergency_acknowledged BIGINT NOT NULL DEFAULT 0 CHECK (emergency_acknowledged>=0)
);

CREATE TABLE notification_delivery_settings (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    enabled_since TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO notification_delivery_settings(singleton) VALUES (TRUE);

DO $grant$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE 'GRANT SELECT (notification_id,event_type,assignment_id,created_at) ON attention_notifications TO riverview_core';
        EXECUTE 'GRANT SELECT (assignment_id,privacy_domain) ON events TO riverview_core';
        EXECUTE 'GRANT SELECT ON notification_delivery_queue TO riverview_core';
        EXECUTE 'GRANT INSERT (notification_id,provider,severity,title,message,idempotency_key,max_attempts) ON notification_delivery_queue TO riverview_core';
        EXECUTE 'GRANT UPDATE (state,attempt_count,next_attempt_at,lease_id,lease_until,provider_receipt,provider_accepted_at,next_receipt_check_at,acknowledged_at,last_error_code,updated_at) ON notification_delivery_queue TO riverview_core';
        EXECUTE 'GRANT SELECT, INSERT ON notification_delivery_events TO riverview_core';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE ON notification_delivery_health TO riverview_core';
        EXECUTE 'GRANT SELECT ON notification_delivery_settings TO riverview_core';
    END IF;
END
$grant$;
