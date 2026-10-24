-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/notifications/migrations/0007_grace_objective_blocked_notification.sql
-- Component: NOTIFICATION-DELIVERY
-- Revision: 1.0.0
-- Purpose: Allow the existing visual notice ledger to project Grace block events
-- Execution Model: Explicit additive migration; no startup DDL
-- Observability: Existing notification/outbox records and receipts
-- Authority: Notification projection only; no objective or recovery decision changes
-- =============================================================================
ALTER TABLE attention_notifications DROP CONSTRAINT attention_notifications_event_type_check;
ALTER TABLE attention_notifications ADD CONSTRAINT attention_notifications_event_type_check
    CHECK (event_type IN (
        'assignment_stalled','deadline_missed','assignment_attention',
        'recovery_requested','monitor_failed','attention_resolved',
        'grace_objective_blocked'));
