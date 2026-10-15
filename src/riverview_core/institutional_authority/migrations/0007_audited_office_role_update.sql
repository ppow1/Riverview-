-- File Revision: 1.0.0
-- Task: RV-GRACE-DOPS-ROLE-CONTEXT-001
-- Purpose: Record Steward-authorized stable office-role corrections in the append-only authority ledger.
ALTER TABLE institutional_authority_events
    DROP CONSTRAINT institutional_authority_events_event_type_check;
ALTER TABLE institutional_authority_events
    ADD CONSTRAINT institutional_authority_events_event_type_check CHECK (event_type IN (
        'steward_bootstrapped','principal_created','credential_issued','credential_revoked',
        'authority_granted','authority_revoked','office_created','occupant_created',
        'implementation_created','office_binding_replaced','office_state_updated',
        'office_model_implementation_changed','office_role_updated'));
