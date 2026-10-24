-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/cme/migrations/0006_grace_objective_blocked_attention.sql
-- Component: CME
-- Revision: 1.0.0
-- Purpose: Permit append-only CME escalation decisions for durable Grace blocks
-- Execution Model: Explicit migration; monitor startup never applies DDL
-- Observability: Existing cme_monitor_events ledger
-- Authority: CME-owned event only; no Grace objective or execution mutation
-- =============================================================================
ALTER TABLE cme_monitor_events DROP CONSTRAINT cme_monitor_events_event_type_check;
ALTER TABLE cme_monitor_events ADD CONSTRAINT cme_monitor_events_event_type_check
    CHECK (event_type IN (
        'monitor_started','monitor_failed','assignment_stalled','deadline_missed',
        'assignment_attention','recovery_requested','attention_resolved',
        'grace_objective_blocked'));
