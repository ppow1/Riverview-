-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/notifications/migrations/0006_durable_notifications.sql
-- Component: NOTIFICATION-DELIVERY
-- Revision: 1.0.1
-- Purpose: Persist idempotent attention notifications, requests, receipts, and health
-- Execution Model: Explicit ordered PostgreSQL migration; never applied at startup
-- Observability: Notification, decision-request, append-only receipt, and health rows
-- Dependencies: PostgreSQL 16; CME 0005; ledger, leases, worker recovery
-- Authority: DDL in explicitly selected schema; no assignment state mutation
-- Changed: 2026-10-11 UTC | RV-M3.2-001 | Add append-only receipt enforcement and an event-type scan index
-- Contracts: docs/components/NOTIFICATION_DELIVERY.md; docs/ROADMAP.md
-- Tests: tests/test_notifications.py
-- History: New file; Git and .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE steward_decision_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_event_id UUID NOT NULL UNIQUE REFERENCES cme_monitor_events(event_id),
    assignment_id TEXT NOT NULL REFERENCES assignments(id),
    assignment_version INTEGER NOT NULL CHECK (assignment_version > 0),
    request_type TEXT NOT NULL CHECK (request_type = 'assignment_review'),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status = 'pending'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX one_pending_steward_request_per_assignment
    ON steward_decision_requests(assignment_id) WHERE status='pending';

CREATE TABLE attention_notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_event_id UUID NOT NULL UNIQUE REFERENCES cme_monitor_events(event_id),
    decision_request_id UUID REFERENCES steward_decision_requests(request_id),
    assignment_id TEXT REFERENCES assignments(id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'assignment_stalled','deadline_missed','assignment_attention',
        'recovery_requested','monitor_failed','attention_resolved')),
    summary_code TEXT NOT NULL CHECK (summary_code=event_type),
    channel TEXT NOT NULL DEFAULT 'dashboard.visual.v1'
        CHECK (channel='dashboard.visual.v1'),
    source_recorded_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    delivered_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    CHECK (acknowledged_at IS NULL OR delivered_at IS NOT NULL)
);
CREATE INDEX attention_notifications_created_idx
    ON attention_notifications(created_at DESC,notification_id DESC);
CREATE INDEX attention_notifications_unacknowledged_idx
    ON attention_notifications(created_at,notification_id)
    WHERE acknowledged_at IS NULL;

CREATE TABLE notification_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES attention_notifications(notification_id),
    event_type TEXT NOT NULL CHECK (event_type IN
        ('notification_queued','delivery_confirmed','receipt_acknowledged')),
    actor_type TEXT NOT NULL CHECK (actor_type IN
        ('notification_dispatcher','authenticated_dashboard_client')),
    idempotency_key TEXT NOT NULL UNIQUE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX notification_events_notification_idx
    ON notification_events(notification_id,recorded_at,event_id);

CREATE FUNCTION reject_notification_event_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'notification_events is append-only';
END;
$$;
CREATE TRIGGER notification_events_append_only
    BEFORE UPDATE OR DELETE ON notification_events
    FOR EACH ROW EXECUTE FUNCTION reject_notification_event_mutation();

CREATE TABLE notification_dispatcher_health (
    service_id TEXT PRIMARY KEY,
    instance_id UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('healthy','degraded')),
    last_heartbeat_at TIMESTAMPTZ NOT NULL,
    last_scan_at TIMESTAMPTZ,
    last_error_type TEXT,
    source_events_scanned INTEGER NOT NULL DEFAULT 0 CHECK (source_events_scanned >= 0),
    notifications_created INTEGER NOT NULL DEFAULT 0 CHECK (notifications_created >= 0),
    decision_requests_created INTEGER NOT NULL DEFAULT 0 CHECK (decision_requests_created >= 0)
);

CREATE INDEX cme_monitor_notifications_scan_idx
    ON cme_monitor_events(event_type,recorded_at,event_id);
