-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0013_grace_capability_registry_read.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Expose the existing capability catalog through narrow runtime projections
-- Execution Model: Explicit additive migration; SECURITY DEFINER read functions
-- Authority: Catalog discovery grants no authority; invocation remains exact-grant checked
-- =============================================================================
DO $migration$
DECLARE authority_schema text := current_schema();
BEGIN
    EXECUTE format('ALTER TABLE %I.capability_catalog ADD COLUMN IF NOT EXISTS input_schema JSONB',
                   authority_schema);
    EXECUTE format($ddl$
        ALTER TABLE %I.capability_catalog
        ADD CONSTRAINT capability_catalog_input_schema_object
        CHECK (input_schema IS NULL OR
               (jsonb_typeof(input_schema)='object'
                AND pg_catalog.octet_length(input_schema::text)<=16384))
    $ddl$, authority_schema);

    -- This is the only currently grant-authorized capability with a registered,
    -- typed operation. Other rows remain discoverable and explicitly non-invocable
    -- until their existing implementation publishes its input contract.
    EXECUTE format($ddl$
        UPDATE %I.capability_catalog
           SET input_schema = '{
             "type":"object",
             "additionalProperties":false,
             "required":["expected_revision","state"],
             "properties":{
               "expected_revision":{"type":"integer","minimum":1},
               "state":{"type":"object"}
             }
           }'::jsonb
         WHERE capability_id='resident.office.state.write'
           AND implementation_ref='AuthorityRegistry.set_office_state.v1'
    $ddl$, authority_schema);
    EXECUTE format($ddl$
        UPDATE %I.capability_catalog
           SET input_schema = '{
             "type":"object",
             "additionalProperties":false,
             "required":["objective_id","request","acceptance_criteria"],
             "properties":{
               "objective_id":{"type":"string","minLength":1,"maxLength":128},
               "request":{"type":"string","minLength":1,"maxLength":8192},
               "acceptance_criteria":{"type":"array","minItems":1,"maxItems":20,
                 "items":{"type":"string","minLength":1,"maxLength":1000}}
             }
           }'::jsonb
         WHERE capability_id='engineering.work_order.submit'
           AND implementation_ref='grace.execution-pipeline.v1'
    $ddl$, authority_schema);

    EXECUTE format($ddl$
        CREATE FUNCTION %I.list_capability_registry()
        RETURNS JSONB LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path=pg_catalog,pg_temp AS $function$
          SELECT COALESCE(jsonb_agg(
            jsonb_build_object(
              'capability_id',c.capability_id,
              'description',c.description,
              'authority_action',c.authority_action,
              'owner_office',c.owner_office,
              'implementation_ref',c.implementation_ref,
              'dependencies',c.dependencies,
              'approval_default',c.approval_default,
              'enabled',c.enabled,
              'input_schema',c.input_schema,
              'resources',COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                  'resource_id',r.resource_id,
                  'resource_kind',r.resource_kind,
                  'description',r.description,
                  'classification',r.classification,
                  'owner_office',r.owner_office,
                  'implementation_ref',cr.implementation_ref
                ) ORDER BY r.resource_id)
                FROM %I.capability_resources cr
                JOIN %I.resource_catalog r USING (resource_id)
                WHERE cr.capability_id=c.capability_id
              ),'[]'::jsonb)
            ) ORDER BY c.capability_id
          ),'[]'::jsonb)
          FROM %I.capability_catalog c
        $function$
    $ddl$,authority_schema,authority_schema,authority_schema,authority_schema);

    EXECUTE format($ddl$
        CREATE FUNCTION %I.list_capability_grants(p_credential_sha256 BYTEA)
        RETURNS TABLE(principal_id TEXT,action TEXT,scope_ref TEXT)
        LANGUAGE sql VOLATILE SECURITY DEFINER
        SET search_path=pg_catalog,pg_temp AS $function$
          SELECT p.principal_id,g.action,g.scope_ref
            FROM %I.principal_credentials c
            JOIN %I.institutional_principals p USING (principal_id)
            JOIN %I.authority_grants g USING (principal_id)
           WHERE p_credential_sha256 IS NOT NULL
             AND pg_catalog.octet_length(p_credential_sha256)=32
             AND c.credential_sha256=p_credential_sha256
             AND p.principal_kind='resident' AND p.status='active'
             AND (c.expires_at IS NULL OR c.expires_at>pg_catalog.clock_timestamp())
             AND c.revoked_at IS NULL
             AND g.revoked_at IS NULL
             AND g.valid_from<=pg_catalog.clock_timestamp()
             AND (g.valid_until IS NULL OR g.valid_until>pg_catalog.clock_timestamp())
           ORDER BY g.action,g.scope_ref
        $function$
    $ddl$,authority_schema,authority_schema,authority_schema,authority_schema);

    EXECUTE format('ALTER FUNCTION %I.list_capability_registry() SET search_path=%I,pg_catalog,pg_temp',
                   authority_schema,authority_schema);
    EXECUTE format('ALTER FUNCTION %I.list_capability_grants(BYTEA) SET search_path=%I,pg_catalog,pg_temp',
                   authority_schema,authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.list_capability_registry() FROM PUBLIC',authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.list_capability_grants(BYTEA) FROM PUBLIC',authority_schema);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.list_capability_registry() TO riverview_core',authority_schema);
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.list_capability_grants(BYTEA) TO riverview_core',authority_schema);
    END IF;
END
$migration$;
