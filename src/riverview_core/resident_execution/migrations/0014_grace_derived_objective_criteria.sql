-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0014_grace_derived_objective_criteria.sql
-- Component: RESIDENT-ORCHESTRATION
-- Revision: 1.0.0
-- Purpose: Allow proposal-bound Grace-derived criteria to become the objective's effective criteria
-- Execution Model: Additive PostgreSQL migration
-- Observability: Criteria source and proposal are recorded in objective events
-- Dependencies: Resident execution migrations 0001-0013; PostgreSQL 16
-- Authority: Restrict criteria update to empty grounded objectives transitioning with their validated proposal
-- Changed: 2026-10-21 UTC | RV-W4-GRACE-OPTIONAL-CRITERIA-20261021 | Gate derived criteria updates on exact proposal content and lifecycle transition.
-- Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
-- Tests: tests/test_grace_execution.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
DO $$
DECLARE
    runtime_role TEXT := 'riverview_core';
    schema_name TEXT := current_schema();
BEGIN
    EXECUTE format($ddl$
        CREATE OR REPLACE FUNCTION %I.guard_grace_derived_objective_criteria()
        RETURNS trigger LANGUAGE plpgsql AS $function$
        DECLARE
            expected_criteria JSONB;
            total_count BIGINT;
            unique_count BIGINT;
        BEGIN
            IF NEW.acceptance_criteria IS DISTINCT FROM OLD.acceptance_criteria THEN
                IF OLD.acceptance_criteria <> '[]'::jsonb OR OLD.status <> 'GROUNDED'
                   OR NEW.status <> 'PROPOSED' OR OLD.proposal IS NOT NULL
                   OR NEW.proposal IS NULL THEN
                    RAISE EXCEPTION 'derived objective criteria require an empty GROUNDED objective and proposal';
                END IF;
                WITH criteria AS (
                    SELECT step.ordinality AS step_order, item.ordinality AS item_order,
                           item.value AS criterion
                    FROM jsonb_array_elements(NEW.proposal->'steps') WITH ORDINALITY AS step(value, ordinality)
                    CROSS JOIN LATERAL jsonb_array_elements(step.value->'acceptance_criteria')
                        WITH ORDINALITY AS item(value, ordinality)
                    UNION ALL
                    SELECT 2147483647, item.ordinality, item.value
                    FROM jsonb_array_elements(NEW.proposal->'system_owned_criteria')
                        WITH ORDINALITY AS item(value, ordinality)
                )
                SELECT jsonb_agg(criterion ORDER BY step_order, item_order),
                       count(*), count(DISTINCT criterion)
                INTO expected_criteria, total_count, unique_count FROM criteria;
                IF expected_criteria IS NULL OR NEW.acceptance_criteria <> expected_criteria
                   OR total_count <> unique_count OR total_count > 20 THEN
                    RAISE EXCEPTION 'objective criteria must exactly match unique bounded proposal criteria';
                END IF;
            END IF;
            RETURN NEW;
        END
        $function$
    $ddl$, schema_name);
    EXECUTE format('DROP TRIGGER IF EXISTS grace_derived_objective_criteria_guard ON %I.grace_objectives', schema_name);
    EXECUTE format('CREATE TRIGGER grace_derived_objective_criteria_guard BEFORE UPDATE ON %I.grace_objectives FOR EACH ROW EXECUTE FUNCTION %I.guard_grace_derived_objective_criteria()', schema_name, schema_name);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=runtime_role) THEN
        EXECUTE format('GRANT UPDATE (acceptance_criteria) ON %I.grace_objectives TO %I', schema_name, runtime_role);
    END IF;
END;
$$;
