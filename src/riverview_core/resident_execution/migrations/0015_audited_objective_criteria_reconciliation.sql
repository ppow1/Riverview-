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
DECLARE schema_name TEXT := current_schema();
BEGIN
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
                authority_schema TEXT;
                checked_grant TEXT;
        BEGIN
            IF NEW.acceptance_criteria IS DISTINCT FROM OLD.acceptance_criteria THEN
                IF OLD.objective_id <> 'objective:grace-conversation:8416c5da-bde5-5294-9276-c0163418fae1'
                   OR OLD.revision <> 2 OR NEW.revision <> 3
                   OR OLD.status <> 'GROUNDED' OR NEW.status <> 'GROUNDED'
                   OR OLD.proposal IS NOT NULL OR NEW.proposal IS DISTINCT FROM OLD.proposal
                   OR OLD.assignment_id IS NOT NULL OR NEW.assignment_id IS DISTINCT FROM OLD.assignment_id
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
                IF NOT FOUND OR audit_event.actor_id<>OLD.submitter_id
                   OR audit_event.payload->'before_criteria' IS DISTINCT FROM OLD.acceptance_criteria
                   OR audit_event.payload->'after_criteria' IS DISTINCT FROM NEW.acceptance_criteria
                   OR audit_event.payload->>'reason' IS NULL
                   OR length(btrim(audit_event.payload->>'reason'))=0
                   OR audit_event.payload->>'authorized_actor' IS DISTINCT FROM audit_event.actor_id
                   OR audit_event.payload->>'authorization_action' IS DISTINCT FROM 'objective.criteria.reconcile'
                   OR audit_event.payload->>'authorization_scope' IS DISTINCT FROM OLD.objective_id
                   OR audit_event.payload->>'authorization_grant_id' IS NULL
                   OR audit_event.payload->>'expected_revision' IS DISTINCT FROM '2'
                   OR audit_event.payload->>'new_revision' IS DISTINCT FROM '3' THEN
                    RAISE EXCEPTION 'objective criteria reconciliation audit event is missing or invalid';
                END IF;
                authority_schema := TG_TABLE_SCHEMA;
                IF to_regprocedure('riverview_authority.authorize_exact_principal_grant(text,text,text)') IS NOT NULL THEN
                    authority_schema := 'riverview_authority';
                END IF;
                EXECUTE format('SELECT grant_id FROM %%I.authorize_exact_principal_grant($1,$2,$3)',
                    authority_schema)
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
