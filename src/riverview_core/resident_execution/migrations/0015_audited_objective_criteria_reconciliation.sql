-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0015_audited_objective_criteria_reconciliation.sql
-- Component: RESIDENT-ORCHESTRATION
-- Revision: 1.0.0
-- Purpose: Permit only the approved revision-2 structural-heading correction with same-transaction audit evidence
-- Execution Model: Additive PostgreSQL trigger replacement
-- Observability: Immutable objective.criteria_reconciled event records the exact before/after transition
-- Dependencies: Resident execution migrations 0001-0014
-- Authority: Exact objective, revision, state, evidence, proposal, assignment, criteria, and actor checks
-- Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-RECONCILIATION | Enforce one approved audited heading removal and append-only event storage.
-- =============================================================================
DO $$
DECLARE
    schema_name TEXT := current_schema();
    authority_schema TEXT;
    target_id TEXT := 'objective:grace-conversation:8416c5da-bde5-5294-9276-c0163418fae1';
    actor TEXT := 'steward:camrui';
    fixed_grant_id TEXT := 'grace-criteria-reconciliation:8416c5da-bde5-5294-9276-c0163418fae1';
    active_actor BOOLEAN;
    valid_grant BOOLEAN;
BEGIN
    authority_schema := schema_name;
    IF to_regclass('riverview_authority.authority_grants') IS NOT NULL THEN
        authority_schema := 'riverview_authority';
    END IF;
    IF to_regclass(format('%I.authority_grants', authority_schema)) IS NOT NULL
       AND to_regclass(format('%I.capability_catalog', authority_schema)) IS NOT NULL THEN
        EXECUTE format($grant$
            INSERT INTO %I.capability_catalog(capability_id,description,authority_action,
                owner_office,implementation_ref,dependencies,approval_default)
            VALUES ('steward.objective.criteria.reconcile',
                'Apply the Steward-approved single-objective structural-heading reconciliation',
                'objective.criteria.reconcile','office:steward',
                'grace.criteria-reconciliation.v1',
                '["exact-objective","revision-cas","append-only-audit"]',true)
            ON CONFLICT (capability_id) DO NOTHING;
            INSERT INTO %I.resource_catalog(resource_id,resource_kind,description,
                classification,owner_office,dependencies)
            VALUES (%L,'institutional',
                'One objective authorized for a single audited structural-heading correction',
                'confidential','office:steward','["steward-approval","revision-2-cas"]')
            ON CONFLICT (resource_id) DO NOTHING;
            INSERT INTO %I.capability_resources(capability_id,resource_id,implementation_ref)
            VALUES ('steward.objective.criteria.reconcile',%L,
                'grace.criteria-reconciliation.v1') ON CONFLICT DO NOTHING
        $grant$, authority_schema, authority_schema, target_id, authority_schema, target_id);
    END IF;
    IF to_regclass(format('%I.authority_grants', authority_schema)) IS NOT NULL
       AND to_regclass(format('%I.institutional_authority_events', authority_schema)) IS NOT NULL THEN
    EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.institutional_principals
        WHERE principal_id=$1 AND principal_kind=''steward'' AND status=''active'')',
        authority_schema) INTO active_actor USING actor;
    IF active_actor THEN
        EXECUTE format('INSERT INTO %I.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES ($1,$2,''objective.criteria.reconcile'',$3,$2,
              ''rv.policy:steward-approved-criteria-reconciliation.v1'')
            ON CONFLICT (grant_id) DO NOTHING', authority_schema)
            USING fixed_grant_id, actor, target_id;
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.authority_grants
            WHERE grant_id=$1 AND principal_id=$2
              AND action=''objective.criteria.reconcile'' AND scope_ref=$3
              AND granted_by=$2 AND revoked_at IS NULL)', authority_schema)
            INTO valid_grant USING fixed_grant_id, actor, target_id;
        IF NOT valid_grant THEN
            RAISE EXCEPTION 'approved criteria reconciliation grant conflicts with existing authority';
        END IF;
        EXECUTE format('INSERT INTO %I.institutional_authority_events
            (event_id,event_type,actor_id,subject_id,grant_id,payload)
            SELECT gen_random_uuid(),''authority_granted'',$2,$2,$1,
              jsonb_build_object(''action'',''objective.criteria.reconcile'',
                ''scope_ref'',$3,''policy_ref'',
                ''rv.policy:steward-approved-criteria-reconciliation.v1'',
                ''approval_basis'',
                ''explicit Steward approval in W4 criteria reconciliation authorization'')
            WHERE NOT EXISTS (SELECT 1 FROM %I.institutional_authority_events
                WHERE event_type=''authority_granted'' AND grant_id=$1)',
            authority_schema, authority_schema)
            USING fixed_grant_id, actor, target_id;
    END IF;
    END IF;
    EXECUTE format($ddl$
        CREATE OR REPLACE FUNCTION %I.reject_grace_objective_event_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $function$
        BEGIN
            RAISE EXCEPTION 'grace objective events are append-only';
        END
        $function$
    $ddl$, schema_name);
    EXECUTE format('DROP TRIGGER IF EXISTS grace_objective_events_append_only ON %I.grace_objective_events', schema_name);
    EXECUTE format('CREATE TRIGGER grace_objective_events_append_only BEFORE UPDATE OR DELETE ON %I.grace_objective_events FOR EACH ROW EXECUTE FUNCTION %I.reject_grace_objective_event_mutation()', schema_name, schema_name);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON %I.grace_objective_events FROM riverview_core', schema_name);
    END IF;
    EXECUTE format($ddl$
        CREATE OR REPLACE FUNCTION %I.guard_grace_derived_objective_criteria()
        RETURNS trigger LANGUAGE plpgsql AS $function$
        DECLARE audit_event RECORD;
                grant_schema TEXT;
                checked_grant TEXT;
                expected_criteria JSONB;
                total_count BIGINT;
                unique_count BIGINT;
        BEGIN
            IF NEW.acceptance_criteria IS DISTINCT FROM OLD.acceptance_criteria THEN
                IF OLD.acceptance_criteria='[]'::jsonb AND OLD.status='GROUNDED'
                   AND NEW.status='PROPOSED' AND OLD.proposal IS NULL
                   AND NEW.proposal IS NOT NULL THEN
                    WITH criteria AS (
                        SELECT step.ordinality AS step_order,item.ordinality AS item_order,
                               item.value AS criterion
                        FROM jsonb_array_elements(NEW.proposal->'steps') WITH ORDINALITY AS step(value,ordinality)
                        CROSS JOIN LATERAL jsonb_array_elements(step.value->'acceptance_criteria')
                            WITH ORDINALITY AS item(value,ordinality)
                        UNION ALL
                        SELECT 2147483647,item.ordinality,item.value
                        FROM jsonb_array_elements(NEW.proposal->'system_owned_criteria')
                            WITH ORDINALITY AS item(value,ordinality)
                    )
                    SELECT jsonb_agg(criterion ORDER BY step_order,item_order),count(*),
                           count(DISTINCT criterion)
                    INTO expected_criteria,total_count,unique_count FROM criteria;
                    IF expected_criteria IS NULL OR NEW.acceptance_criteria<>expected_criteria
                       OR total_count<>unique_count OR total_count>20 THEN
                        RAISE EXCEPTION 'objective criteria must exactly match unique bounded proposal criteria';
                    END IF;
                    RETURN NEW;
                END IF;
                IF OLD.objective_id <> 'objective:grace-conversation:8416c5da-bde5-5294-9276-c0163418fae1'
                   OR OLD.revision <> 2 OR NEW.revision <> 3
                   OR OLD.status <> 'GROUNDED' OR NEW.status <> 'GROUNDED'
                   OR OLD.proposal IS NOT NULL OR NEW.proposal IS DISTINCT FROM OLD.proposal
                   OR OLD.assignment_id IS NOT NULL OR NEW.assignment_id IS DISTINCT FROM OLD.assignment_id
                   OR OLD.scope_ref <> 'work-order:engineering'
                   OR OLD.evidence->>'status' IS DISTINCT FROM 'VERIFIED'
                   OR OLD.evidence->>'retrieval_complete' IS DISTINCT FROM 'true'
                   OR NEW.request IS DISTINCT FROM OLD.request
                   OR NEW.scope_ref IS DISTINCT FROM OLD.scope_ref
                   OR NEW.submitter_id IS DISTINCT FROM OLD.submitter_id
                   OR NEW.evidence IS DISTINCT FROM OLD.evidence
                   OR NEW.source_revision IS DISTINCT FROM OLD.source_revision
                   OR NEW.source_sha256 IS DISTINCT FROM OLD.source_sha256
                   OR NEW.created_at IS DISTINCT FROM OLD.created_at
                   OR OLD.acceptance_criteria <> '[
                       "Requirements:",
                       "- Create exactly one Engineering assignment for the file.",
                       "- Use the authorized artifact destination recorded in the work order.",
                       "- Independently verify the actual file contents.",
                       "- Close the objective only after successful verification."
                   ]'::jsonb
                   OR NEW.acceptance_criteria <> '[
                       "- Create exactly one Engineering assignment for the file.",
                       "- Use the authorized artifact destination recorded in the work order.",
                       "- Independently verify the actual file contents.",
                       "- Close the objective only after successful verification."
                   ]'::jsonb THEN
                    RAISE EXCEPTION 'objective criteria change is outside approved reconciliation';
                END IF;
                EXECUTE format('SELECT * FROM %%I.grace_objective_events
                    WHERE objective_id=$1 AND event_type=$2 AND idempotency_key=$3 FOR SHARE',
                    TG_TABLE_SCHEMA)
                    INTO audit_event
                    USING OLD.objective_id, 'objective.criteria_reconciled',
                        'grace-criteria-reconciled:' || OLD.objective_id || ':r2';
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'objective criteria reconciliation audit event is missing';
                END IF;
                IF audit_event.actor_id IS DISTINCT FROM OLD.submitter_id THEN
                    RAISE EXCEPTION 'objective criteria reconciliation actor mismatch';
                END IF;
                IF audit_event.payload->'before_criteria' IS DISTINCT FROM OLD.acceptance_criteria
                   OR audit_event.payload->'after_criteria' IS DISTINCT FROM NEW.acceptance_criteria THEN
                    RAISE EXCEPTION 'objective criteria reconciliation criteria snapshot mismatch';
                END IF;
                IF audit_event.payload->>'reason' IS NULL
                   OR length(btrim(audit_event.payload->>'reason'))=0
                   OR audit_event.payload->>'authorized_actor' IS DISTINCT FROM audit_event.actor_id
                   OR audit_event.payload->>'authorization_action' IS DISTINCT FROM 'objective.criteria.reconcile'
                   OR audit_event.payload->>'authorization_scope' IS DISTINCT FROM OLD.objective_id
                   OR audit_event.payload->>'authorization_grant_id' IS NULL
                   OR audit_event.payload->>'expected_revision' IS DISTINCT FROM '2'
                   OR audit_event.payload->>'new_revision' IS DISTINCT FROM '3' THEN
                    RAISE EXCEPTION 'objective criteria reconciliation audit metadata mismatch';
                END IF;
                grant_schema := TG_TABLE_SCHEMA;
                IF to_regprocedure('riverview_authority.authorize_exact_principal_grant(text,text,text)') IS NOT NULL THEN
                    grant_schema := 'riverview_authority';
                END IF;
                EXECUTE format('SELECT grant_id FROM %%I.authorize_exact_principal_grant($1,$2,$3)',
                    grant_schema)
                    INTO checked_grant
                    USING audit_event.actor_id, 'objective.criteria.reconcile', OLD.objective_id;
                IF checked_grant IS NULL OR checked_grant IS DISTINCT FROM
                    audit_event.payload->>'authorization_grant_id' THEN
                    RAISE EXCEPTION 'objective criteria reconciliation lacks its exact active Steward grant';
                END IF;
            END IF;
            RETURN NEW;
        END
        $function$
    $ddl$, schema_name);
    EXECUTE format('DROP TRIGGER IF EXISTS grace_derived_objective_criteria_guard ON %I.grace_objectives', schema_name);
    EXECUTE format('CREATE TRIGGER grace_derived_objective_criteria_guard BEFORE UPDATE ON %I.grace_objectives FOR EACH ROW EXECUTE FUNCTION %I.guard_grace_derived_objective_criteria()', schema_name, schema_name);
END;
$$;
