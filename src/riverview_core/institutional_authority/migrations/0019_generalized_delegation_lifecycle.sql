-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0019_generalized_delegation_lifecycle.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Purpose: Persist typed grant lifetimes, unlimited grants, and change lineage.
-- Execution Model: Explicit additive migration; never run during application startup.
-- Authority: Existing grants, reservations, request decisions, and audit history remain intact.
-- =============================================================================
ALTER TABLE authority_grants
    ADD COLUMN duration_spec JSONB,
    ADD COLUMN supersedes_grant_id TEXT REFERENCES authority_grants(grant_id),
    ADD CONSTRAINT authority_grants_duration_spec_object
        CHECK (duration_spec IS NULL OR jsonb_typeof(duration_spec) = 'object');

ALTER TABLE delegated_grant_requests
    ADD COLUMN duration_spec JSONB,
    ADD COLUMN change_kind TEXT,
    ADD CONSTRAINT delegated_grant_requests_duration_spec_object
        CHECK (duration_spec IS NULL OR jsonb_typeof(duration_spec) = 'object'),
    ADD CONSTRAINT delegated_grant_requests_change_kind
        CHECK ((request_kind = 'grant' AND change_kind IS NULL) OR
               (request_kind = 'change' AND change_kind IN ('extend','upgrade','extend_upgrade')));

-- Migration 0017 required every request to have a count or absolute expiry.
-- A typed indefinite duration explicitly represents a grant with neither.
DO $$
DECLARE c RECORD;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'delegated_grant_requests'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%max_uses%valid_until%'
    LOOP
        EXECUTE format('ALTER TABLE delegated_grant_requests DROP CONSTRAINT %I', c.conname);
    END LOOP;
END $$;

ALTER TABLE delegated_grant_requests
    ADD CONSTRAINT delegated_grant_requests_lifetime_check
    CHECK (max_uses IS NOT NULL OR valid_until IS NOT NULL OR duration_spec IS NOT NULL);

ALTER TABLE institutional_authority_events
    DROP CONSTRAINT institutional_authority_events_event_type_check,
    ADD CONSTRAINT institutional_authority_events_event_type_check
        CHECK (event_type IN (
            'steward_bootstrapped','principal_created','credential_issued','credential_revoked',
            'authority_granted','authority_revoked','authority_grant_used',
            'authority_grant_reserved','authority_grant_reservation_released',
            'authority_grant_reservation_expired','authority_grant_expired',
            'authority_grant_surrendered','authority_delegation_request_created',
            'authority_delegation_request_decided','authority_delegation_grant_extended',
            'authority_delegation_grant_upgraded',
            'office_created','occupant_created','implementation_created',
            'office_binding_replaced','office_state_updated',
            'office_model_implementation_changed','office_role_updated',
            'worker_registration_retired'));
