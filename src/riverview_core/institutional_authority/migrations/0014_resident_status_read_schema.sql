-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0014_resident_status_read_schema.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Publish the zero-input contract for the existing bounded status projection
-- Execution Model: Additive catalog metadata only; no grants or permissions are changed
-- Authority: resident.status.read remains protected by an exact live grant
-- =============================================================================
DO $migration$
DECLARE authority_schema text := current_schema();
        affected_rows integer;
BEGIN
    EXECUTE format($ddl$
        UPDATE %I.capability_catalog
           SET input_schema = '{
             "type":"object",
             "additionalProperties":false,
             "required":[],
             "properties":{}
           }'::jsonb
         WHERE capability_id='resident.status.read'
           AND authority_action='resident.status.read'
           AND implementation_ref='dashboard.projection.v1'
    $ddl$, authority_schema);
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    IF affected_rows <> 1 THEN
        RAISE EXCEPTION 'resident.status.read capability row is missing or incompatible';
    END IF;
END
$migration$;
