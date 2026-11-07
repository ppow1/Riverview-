-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0017_resident_proposal_capability_resources.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Bind the existing resident proposal declarations to the central resource registry
-- Execution Model: Additive metadata migration followed by release declaration reconciliation
-- Authority: Creates no resident grants, profiles, proposal records, or approvals
-- =============================================================================
INSERT INTO resource_catalog
    (resource_id,resource_kind,description,classification,owner_office,dependencies)
VALUES
    ('riverview:institutional-proposals','institutional',
     'Durable institutional proposal drafts and bounded author receipts',
     'internal','office:steward','["institutional-proposal-registry"]'::jsonb)
ON CONFLICT (resource_id) DO NOTHING;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM resource_catalog
         WHERE resource_id='riverview:institutional-proposals'
           AND resource_kind='institutional'
           AND classification='internal'
           AND owner_office='office:steward'
    ) THEN
        RAISE EXCEPTION 'resident_proposal_resource_conflict';
    END IF;
END
$migration$;

-- Seed the referenced catalog identities before their resource links. The ordinary
-- release declaration reconciliation immediately following migrations owns the
-- executable schemas, descriptions, and authorization contracts for these rows.
INSERT INTO capability_catalog
    (capability_id,description,authority_action,owner_office,implementation_ref,
     dependencies,approval_default,enabled,input_schema,authorization_contract)
VALUES
    ('proposal.draft.submit','Resident proposal draft submission',
     'proposal.draft.submit','office:grace','institutional.proposal-registry.v1',
     '["institutional-proposal-registry"]'::jsonb,false,true,
     '{"type":"object","additionalProperties":false,"required":[],"properties":{}}'::jsonb,
     '{"mode":"exact_grant","action":"proposal.draft.submit","scope_policy":"exact_scope"}'::jsonb),
    ('proposal.status.read','Resident proposal status read',
     'proposal.status.read','office:grace','institutional.proposal-registry-status.v1',
     '["institutional-proposal-registry"]'::jsonb,false,true,
     '{"type":"object","additionalProperties":false,"required":[],"properties":{}}'::jsonb,
     '{"mode":"exact_grant","action":"proposal.status.read","scope_policy":"exact_scope"}'::jsonb)
ON CONFLICT (capability_id) DO NOTHING;

INSERT INTO capability_resources(capability_id,resource_id,implementation_ref)
VALUES
    ('proposal.draft.submit','riverview:institutional-proposals',
     'institutional.proposal-registry.v1'),
    ('proposal.status.read','riverview:institutional-proposals',
     'institutional.proposal-registry-status.v1')
ON CONFLICT (capability_id,resource_id) DO UPDATE
   SET implementation_ref=EXCLUDED.implementation_ref;
