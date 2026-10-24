-- RIVERVIEW~ CONTROLLED MIGRATION
-- File: src/riverview_core/notifications/migrations/0010_notification_phone_delivery.sql
-- Component: NOTIFICATION-DELIVERY
-- Purpose: Persist retryable phone delivery state for durable notifications
-- Execution Model: Explicit transactional PostgreSQL migration
-- Authority: Notification-owned tables only
-- =============================================================================
CREATE TABLE notification_phone_deliveries (
    notification_id UUID PRIMARY KEY REFERENCES attention_notifications(notification_id),
    delivery_state TEXT NOT NULL DEFAULT 'pending'
        CHECK (delivery_state IN ('pending','sending','sent','failed','suppressed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    ntfy_message_id TEXT,
    last_failure_type TEXT,
    suppression_reason TEXT CHECK (suppression_reason IN ('level','paused','quiet_hours')),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    lease_until TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK ((delivery_state = 'sent') = (ntfy_message_id IS NOT NULL)),
    CHECK ((delivery_state = 'suppressed') = (suppression_reason IS NOT NULL))
);
CREATE INDEX notification_phone_retry_idx
    ON notification_phone_deliveries(next_attempt_at,notification_id)
    WHERE delivery_state IN ('pending','failed','sending');
