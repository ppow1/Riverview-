-- File Revision: 1.0.0
-- Task: RV-GRACE-MULTISTAGE-ROUTING-001
-- Purpose: Permit audited implementation updates without replacing an office occupant.
ALTER TABLE institutional_authority_events
    DROP CONSTRAINT institutional_authority_events_event_type_check;
ALTER TABLE institutional_authority_events
    ADD CONSTRAINT institutional_authority_events_event_type_check CHECK (event_type IN (
        'steward_bootstrapped','principal_created','credential_issued','credential_revoked',
        'authority_granted','authority_revoked','office_created','occupant_created',
        'implementation_created','office_binding_replaced','office_state_updated',
        'office_model_implementation_changed'));
