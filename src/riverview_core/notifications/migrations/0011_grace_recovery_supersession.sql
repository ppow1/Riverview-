-- RIVERVIEW~ CONTROLLED MIGRATION
-- File: src/riverview_core/notifications/migrations/0011_grace_recovery_supersession.sql
-- Component: NOTIFICATION-DELIVERY
-- Revision: 1.0.0
-- Purpose: Preserve pending Steward recovery history when a bounded policy recovery supersedes it
-- Execution Model: Explicit ordered PostgreSQL migration; never applied at startup
-- Authority: Expands lifecycle vocabulary only; no decision or execution grant
-- Tests: tests/test_notifications.py; tests/test_grace_execution.py
-- =============================================================================
ALTER TABLE grace_recovery_decision_requests
    DROP CONSTRAINT grace_recovery_decision_requests_status_check;
ALTER TABLE grace_recovery_decision_requests
    ADD CONSTRAINT grace_recovery_decision_requests_status_check
    CHECK (status IN ('pending','approved','deferred','rejected','expired','dispatched','consumed','superseded'));

ALTER TABLE grace_recovery_decision_events
    DROP CONSTRAINT grace_recovery_decision_events_decision_check;
ALTER TABLE grace_recovery_decision_events
    ADD CONSTRAINT grace_recovery_decision_events_decision_check
    CHECK (decision IN ('approve','defer','reject','supersede'));
