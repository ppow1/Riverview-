-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0016_reconciliation_guard_event_read.sql
-- Component: RESIDENT-ORCHESTRATION
-- Revision: 1.0.0
-- Purpose: Keep the audited criteria guard compatible with runtime event privileges
-- Execution Model: Narrow replacement of the installed revision-0015 trigger query
-- Observability: No change to audit data or reconciliation outcomes
-- Dependencies: Resident execution migration 0015
-- Authority: Preserve exact grant, objective, revision, and append-only audit checks
-- Tests: tests/test_grace_execution.py
-- =============================================================================
DO $$
DECLARE
    schema_name TEXT := current_schema();
    function_definition TEXT;
    old_projection TEXT := 'SELECT * FROM %I.grace_objective_events';
    new_projection TEXT := 'SELECT actor_id,payload FROM %I.grace_objective_events';
    old_lock TEXT := 'idempotency_key=$3 FOR SHARE';
BEGIN
    function_definition := pg_get_functiondef(
        to_regprocedure(format('%I.guard_grace_derived_objective_criteria()', schema_name)));
    IF function_definition IS NULL
       OR length(function_definition) - length(replace(function_definition, old_projection, ''))
            <> length(old_projection)
       OR length(function_definition) - length(replace(function_definition, old_lock, ''))
            <> length(old_lock) THEN
        RAISE EXCEPTION 'installed criteria guard does not match the audited revision-0015 definition';
    END IF;
    function_definition := replace(function_definition, old_projection, new_projection);
    function_definition := replace(function_definition, old_lock, 'idempotency_key=$3');
    IF position(new_projection IN function_definition) = 0
       OR position(old_lock IN function_definition) > 0 THEN
        RAISE EXCEPTION 'criteria guard privilege correction did not apply exactly';
    END IF;
    EXECUTE function_definition;
END;
$$;
