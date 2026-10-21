-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0010_steward_criteria_reconciliation_grant.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Register and grant one Steward-only criteria reconciliation action for one approved objective
-- Execution Model: Exact-scope additive capability and authority grant
-- Observability: Append-only authority_granted event identifies actor, action, scope, and approval basis
-- Dependencies: Authority migrations 0001-0009 and resident permission profiles
-- Authority: Explicitly approved by the Steward for the exact objective; no general criteria-edit permission
-- Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-RECONCILIATION | Register the one-objective grant and append its authority event.
-- =============================================================================
DO $$
DECLARE
    target_id TEXT := 'objective:grace-conversation:8416c5da-bde5-5294-9276-c0163418fae1';
    actor TEXT := 'steward:camrui';
    fixed_grant_id TEXT := 'grace-criteria-reconciliation:8416c5da-bde5-5294-9276-c0163418fae1';
    created_grant TEXT;
    existing authority_grants%ROWTYPE;
BEGIN
    INSERT INTO capability_catalog(capability_id,description,authority_action,owner_office,
        implementation_ref,dependencies,approval_default)
    VALUES ('steward.objective.criteria.reconcile',
        'Apply the Steward-approved single-objective structural-heading reconciliation',
        'objective.criteria.reconcile','office:steward',
        'grace.criteria-reconciliation.v1','["exact-objective","revision-cas","append-only-audit"]',true)
    ON CONFLICT (capability_id) DO NOTHING;
    IF NOT EXISTS (SELECT 1 FROM capability_catalog WHERE
        capability_id='steward.objective.criteria.reconcile'
        AND authority_action='objective.criteria.reconcile' AND enabled) THEN
        RAISE EXCEPTION 'criteria reconciliation capability identity conflict';
    END IF;
    INSERT INTO resource_catalog(resource_id,resource_kind,description,classification,owner_office,dependencies)
    VALUES (target_id,'institutional','One objective authorized for a single audited structural-heading correction',
        'confidential','office:steward','["steward-approval","revision-2-cas"]')
    ON CONFLICT (resource_id) DO NOTHING;
    INSERT INTO capability_resources(capability_id,resource_id,implementation_ref)
    VALUES ('steward.objective.criteria.reconcile',target_id,'grace.criteria-reconciliation.v1')
    ON CONFLICT (capability_id,resource_id) DO NOTHING;
    IF EXISTS (SELECT 1 FROM institutional_principals WHERE principal_id=actor
        AND principal_kind='steward' AND status='active') THEN
        INSERT INTO authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
        VALUES (fixed_grant_id,actor,'objective.criteria.reconcile',target_id,actor,
            'rv.policy:steward-approved-criteria-reconciliation.v1')
        ON CONFLICT (grant_id) DO NOTHING
        RETURNING grant_id INTO created_grant;
        SELECT * INTO existing FROM authority_grants WHERE grant_id=fixed_grant_id;
        IF NOT FOUND OR existing.principal_id<>actor OR existing.action<>'objective.criteria.reconcile'
           OR existing.scope_ref<>target_id OR existing.granted_by<>actor OR existing.revoked_at IS NOT NULL THEN
            RAISE EXCEPTION 'approved reconciliation grant conflicts with an existing grant';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM institutional_authority_events WHERE
            event_type='authority_granted' AND grant_id=fixed_grant_id) THEN
            INSERT INTO institutional_authority_events(event_id,event_type,actor_id,subject_id,grant_id,payload)
            VALUES (gen_random_uuid(),'authority_granted',actor,actor,fixed_grant_id,
                jsonb_build_object('action','objective.criteria.reconcile','scope_ref',target_id,
                    'policy_ref','rv.policy:steward-approved-criteria-reconciliation.v1',
                    'approval_basis','explicit Steward approval in W4 criteria reconciliation authorization'));
        END IF;
    END IF;
END;
$$;
