-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0009_worker_registration_retirement_event.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Permit an append-only authority event for governed worker registration retirement
-- Execution Model: Explicit additive PostgreSQL migration; never applied by application startup
-- Observability: institutional_authority_events
-- Dependencies: Authority migrations 0001-0008
-- Authority: Expands the event-type constraint only; grants no new authority
-- Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Add the worker_registration_retired event type
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
ALTER TABLE institutional_authority_events
    DROP CONSTRAINT institutional_authority_events_event_type_check;

ALTER TABLE institutional_authority_events
    ADD CONSTRAINT institutional_authority_events_event_type_check CHECK (event_type IN (
        'steward_bootstrapped','principal_created','credential_issued','credential_revoked',
        'authority_granted','authority_revoked','office_created','occupant_created',
        'implementation_created','office_binding_replaced','office_state_updated',
        'office_model_implementation_changed','office_role_updated',
        'worker_registration_retired'));
