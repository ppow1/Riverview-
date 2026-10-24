-- RIVERVIEW~ CONTROLLED MIGRATION
-- File: src/riverview_core/notifications/migrations/0007_notification_settings.sql
-- Component: NOTIFICATION-DELIVERY
-- Purpose: Persist Steward notification preferences and durable suppression decisions
-- Execution Model: Explicit transactional PostgreSQL migration
-- Authority: Notification-owned tables only
-- =============================================================================
CREATE TABLE notification_settings (
    settings_id SMALLINT PRIMARY KEY CHECK (settings_id = 1),
    level TEXT NOT NULL CHECK (level IN ('all','important','critical_only','paused')),
    quiet_hours_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    quiet_start TIME NOT NULL DEFAULT TIME '22:00',
    quiet_end TIME NOT NULL DEFAULT TIME '07:00',
    quiet_timezone TEXT NOT NULL DEFAULT 'UTC',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO notification_settings(settings_id,level) VALUES (1,'all');

CREATE TABLE notification_suppressions (
    source_event_id UUID PRIMARY KEY REFERENCES cme_monitor_events(event_id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'assignment_stalled','deadline_missed','assignment_attention',
        'recovery_requested','monitor_failed','attention_resolved')),
    reason TEXT NOT NULL CHECK (reason IN ('level','paused','quiet_hours')),
    suppressed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
