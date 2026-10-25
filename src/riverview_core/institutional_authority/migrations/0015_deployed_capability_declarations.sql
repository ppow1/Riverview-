-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0015_deployed_capability_declarations.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Reconcile release-shipped executable capability declarations into the existing catalog
-- Execution Model: Privileged deployment caller invokes a bounded SECURITY INVOKER function
-- Authority: Does not create, alter, or revoke AuthorityRegistry grants
-- =============================================================================
DO $migration$
DECLARE authority_schema text := current_schema();
        role_name text;
BEGIN
    EXECUTE format($ddl$
        ALTER TABLE %I.capability_catalog
          ADD COLUMN IF NOT EXISTS registration_blocker TEXT,
          ADD COLUMN IF NOT EXISTS declaration_source TEXT,
          ADD COLUMN IF NOT EXISTS declaration_source_commit TEXT,
          ADD COLUMN IF NOT EXISTS authorization_contract JSONB,
          ADD COLUMN IF NOT EXISTS availability_policy TEXT NOT NULL
            DEFAULT 'executor_and_worker_health'
    $ddl$, authority_schema);
    EXECUTE format($ddl$
        UPDATE %I.capability_catalog
           SET authorization_contract=jsonb_build_object(
             'mode','exact_grant','action',authority_action,'scope_policy','exact_scope')
         WHERE authorization_contract IS NULL
    $ddl$, authority_schema);
    EXECUTE format($ddl$
        ALTER TABLE %I.capability_catalog
          ALTER COLUMN authorization_contract SET NOT NULL,
          ADD CONSTRAINT capability_catalog_authorization_contract_object
          CHECK (jsonb_typeof(authorization_contract)='object'
                 AND pg_catalog.octet_length(authorization_contract::text)<=4096)
    $ddl$, authority_schema);
    EXECUTE format($ddl$
        ALTER TABLE %I.capability_catalog
          ADD CONSTRAINT capability_catalog_availability_policy
          CHECK (availability_policy IN ('executor_and_worker_health'))
    $ddl$, authority_schema);

    EXECUTE format($ddl$
        CREATE OR REPLACE FUNCTION %I.list_capability_registry()
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
              'authorization_contract',c.authorization_contract,
              'availability_policy',c.availability_policy,
              'registration_blocker',c.registration_blocker,
              'declaration_source',c.declaration_source,
              'declaration_source_commit',c.declaration_source_commit,
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
    EXECUTE format('ALTER FUNCTION %I.list_capability_registry() SET search_path=pg_catalog,pg_temp',
                   authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.list_capability_registry() FROM PUBLIC',authority_schema);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_authority_owner') THEN
        EXECUTE format('ALTER FUNCTION %I.list_capability_registry() OWNER TO riverview_authority_owner',authority_schema);
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.list_capability_registry() TO riverview_core',authority_schema);
    END IF;

    EXECUTE format($ddl$
        CREATE FUNCTION %I.reconcile_capability_declarations(p_declarations JSONB,
                                                              p_source_commit TEXT)
        RETURNS INTEGER LANGUAGE plpgsql VOLATILE
        AS $function$
        DECLARE item JSONB;
                affected INTEGER := 0;
                cap_id TEXT;
                operation TEXT;
                blocker TEXT;
                declaration_name TEXT;
        BEGIN
          IF jsonb_typeof(p_declarations)<>'array'
             OR pg_catalog.jsonb_array_length(p_declarations)>512
             OR p_source_commit IS NULL OR length(p_source_commit)>128 THEN
            RAISE EXCEPTION 'capability_declaration_batch_invalid';
          END IF;
          FOR item IN SELECT value FROM pg_catalog.jsonb_array_elements(p_declarations)
          LOOP
            IF jsonb_typeof(item)<>'object'
               OR NOT (item ?& ARRAY['capability_id','description','operation',
                    'implementation_ref','dependencies','approval_default','enabled',
                    'input_schema','authorization_contract','registration_blocker',
                    'availability_policy','declaration_source'])
               OR jsonb_typeof(item->'capability_id')<>'string'
               OR jsonb_typeof(item->'description')<>'string'
               OR jsonb_typeof(item->'operation')<>'string'
               OR jsonb_typeof(item->'implementation_ref')<>'string'
               OR jsonb_typeof(item->'dependencies')<>'array'
               OR jsonb_typeof(item->'approval_default')<>'boolean'
               OR jsonb_typeof(item->'enabled')<>'boolean'
               OR jsonb_typeof(item->'input_schema')<>'object'
               OR jsonb_typeof(item->'authorization_contract')<>'object'
               OR jsonb_typeof(item->'availability_policy')<>'string'
               OR (item->>'registration_blocker' IS NOT NULL
                   AND jsonb_typeof(item->'registration_blocker')<>'string')
               OR jsonb_typeof(item->'declaration_source')<>'string' THEN
              RAISE EXCEPTION 'capability_declaration_shape_invalid';
            END IF;
            cap_id := item->>'capability_id';
            operation := item->>'operation';
            blocker := NULLIF(item->>'registration_blocker','');
            declaration_name := item->>'declaration_source';
            IF length(cap_id) NOT BETWEEN 1 AND 256
               OR cap_id !~ '^[A-Za-z0-9._:-]+$'
               OR length(operation) NOT BETWEEN 1 AND 256
               OR operation !~ '^[A-Za-z0-9._:-]+$'
               OR length(item->>'description') NOT BETWEEN 1 AND 1000
               OR length(item->>'implementation_ref') NOT BETWEEN 1 AND 256
               OR length(declaration_name) NOT BETWEEN 1 AND 128
               OR item->>'availability_policy'<>'executor_and_worker_health'
               OR (blocker IS NOT NULL AND length(blocker)>256)
               OR (blocker IS NOT NULL AND (item->>'enabled')::boolean) THEN
              RAISE EXCEPTION 'capability_declaration_value_invalid';
            END IF;
            IF pg_catalog.octet_length((item->'input_schema')::text)>16384
               OR pg_catalog.octet_length((item->'authorization_contract')::text)>4096 THEN
              RAISE EXCEPTION 'capability_input_schema_too_large';
            END IF;
            IF item->'authorization_contract'->>'mode'='exact_grant'
               AND (item->'authorization_contract'->>'action'<>operation
                    OR NULLIF(item->'authorization_contract'->>'scope_policy','') IS NULL) THEN
              RAISE EXCEPTION 'capability_authorization_action_mismatch';
            END IF;
            IF item->'authorization_contract'->>'mode'<>'exact_grant'
               AND blocker IS NULL THEN
              RAISE EXCEPTION 'unsupported_authorization_requires_blocker';
            END IF;

            EXECUTE format($upsert$
              INSERT INTO %%I.capability_catalog
                (capability_id,description,authority_action,owner_office,implementation_ref,
                 dependencies,approval_default,enabled,input_schema,registration_blocker,
                 declaration_source,declaration_source_commit,authorization_contract,
                 availability_policy)
              VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
              ON CONFLICT (capability_id) DO UPDATE SET
                description=EXCLUDED.description,
                authority_action=EXCLUDED.authority_action,
                owner_office=EXCLUDED.owner_office,
                implementation_ref=EXCLUDED.implementation_ref,
                dependencies=EXCLUDED.dependencies,
                approval_default=EXCLUDED.approval_default,
                enabled=EXCLUDED.enabled,
                input_schema=EXCLUDED.input_schema,
                registration_blocker=EXCLUDED.registration_blocker,
                declaration_source=EXCLUDED.declaration_source,
                declaration_source_commit=EXCLUDED.declaration_source_commit,
                authorization_contract=EXCLUDED.authorization_contract,
                availability_policy=EXCLUDED.availability_policy
            $upsert$, current_schema())
            USING cap_id,item->>'description',operation,item->>'owner_office',
              item->>'implementation_ref',item->'dependencies',
              (item->>'approval_default')::boolean,(item->>'enabled')::boolean,
              item->'input_schema',blocker,declaration_name,p_source_commit,
              item->'authorization_contract',item->>'availability_policy';
            affected := affected + 1;
          END LOOP;
          RETURN affected;
        END
        $function$
    $ddl$,authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.reconcile_capability_declarations(JSONB,TEXT) FROM PUBLIC',
                   authority_schema);
    FOR role_name IN SELECT rolname FROM pg_roles WHERE rolname<>current_user LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %I.reconcile_capability_declarations(JSONB,TEXT) FROM %I',
                       authority_schema,role_name);
    END LOOP;
END
$migration$;
