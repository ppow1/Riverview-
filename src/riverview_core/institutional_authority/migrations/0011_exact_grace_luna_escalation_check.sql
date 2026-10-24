-- Expose only Grace's exact active Luna escalation grant to the bounded experiment path.
DO $migration$
DECLARE authority_schema text := current_schema();
BEGIN
    EXECUTE format($ddl$
        CREATE FUNCTION %I.active_grace_luna_escalation_grant()
        RETURNS text
        LANGUAGE sql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
            SELECT grant_row.grant_id
              FROM %I.authority_grants AS grant_row
              JOIN %I.institutional_principals AS principal
                ON principal.principal_id=grant_row.principal_id
             WHERE grant_row.principal_id='resident:grace'
               AND principal.principal_kind='resident' AND principal.status='active'
               AND grant_row.action='resident.reasoning.escalate'
               AND grant_row.scope_ref='provider:gpt-6-luna'
               AND grant_row.revoked_at IS NULL
               AND grant_row.valid_from <= pg_catalog.clock_timestamp()
               AND (grant_row.valid_until IS NULL
                    OR grant_row.valid_until > pg_catalog.clock_timestamp())
             ORDER BY grant_row.valid_from DESC, grant_row.grant_id
             LIMIT 1
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.active_grace_luna_escalation_grant() FROM PUBLIC',
                   authority_schema);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.active_grace_luna_escalation_grant() TO riverview_core',
                       authority_schema);
    END IF;

    EXECUTE format($ddl$
        CREATE FUNCTION %I.active_grace_autonomy_experiment_grant(
            p_grant_id text, p_scope_ref text
        ) RETURNS text
        LANGUAGE sql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
            SELECT grant_row.grant_id
              FROM %I.authority_grants AS grant_row
              JOIN %I.institutional_principals AS principal
                ON principal.principal_id=grant_row.principal_id
             WHERE p_grant_id IS NOT NULL
               AND p_scope_ref =
                    'grace-autonomy:objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2'
               AND grant_row.grant_id=p_grant_id
               AND grant_row.principal_id='resident:grace'
               AND principal.principal_kind='resident' AND principal.status='active'
               AND grant_row.action='grace.experiment.execute'
               AND grant_row.scope_ref=p_scope_ref
               AND grant_row.revoked_at IS NULL
               AND grant_row.valid_from <= pg_catalog.clock_timestamp()
               AND (grant_row.valid_until IS NULL
                    OR grant_row.valid_until > pg_catalog.clock_timestamp())
             LIMIT 1
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.active_grace_autonomy_experiment_grant(text,text) FROM PUBLIC',
                   authority_schema);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.active_grace_autonomy_experiment_grant(text,text) TO riverview_core',
                       authority_schema);
    END IF;

    -- Keep the issue operation fail-closed if the provider grant is revoked between
    -- the application's read and the experiment grant transaction.
    EXECUTE format($ddl$
        CREATE OR REPLACE FUNCTION %I.issue_grace_autonomy_experiment_grant(
            p_actor_id text, p_grant_id text, p_scope_ref text, p_valid_until timestamptz
        ) RETURNS text
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
        DECLARE
            existing %I.authority_grants%%ROWTYPE;
        BEGIN
            IF p_actor_id IS NULL OR pg_catalog.length(p_actor_id)=0
               OR p_grant_id IS NULL OR p_grant_id !~ '^grant:grace-autonomy:[0-9a-f-]{36}$'
               OR p_scope_ref IS NULL OR p_scope_ref !~
                    '^grace-autonomy:objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2$'
               OR p_valid_until IS NULL
               OR p_valid_until <= pg_catalog.clock_timestamp()
               OR p_valid_until > pg_catalog.clock_timestamp() + interval '24 hours' THEN
                RAISE EXCEPTION 'grace_experiment_grant_envelope_invalid';
            END IF;
            PERFORM 1 FROM %I.institutional_principals AS principal
             WHERE principal.principal_id=p_actor_id
               AND principal.principal_kind='steward' AND principal.status='active';
            IF NOT FOUND OR NOT EXISTS (
                SELECT 1 FROM %I.authorize_exact_principal_grant(
                    p_actor_id,'authority.grant','institution')) THEN
                RAISE EXCEPTION 'grace_experiment_steward_authority_required';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM %I.active_grace_luna_escalation_grant()) THEN
                RAISE EXCEPTION 'grace_experiment_luna_escalation_required';
            END IF;
            SELECT * INTO existing FROM %I.authority_grants WHERE grant_id=p_grant_id;
            IF FOUND THEN
                IF existing.principal_id <> 'resident:grace'
                   OR existing.action <> 'grace.experiment.execute'
                   OR existing.scope_ref <> p_scope_ref
                   OR existing.granted_by <> p_actor_id
                   OR existing.revoked_at IS NOT NULL
                   OR existing.valid_until <> p_valid_until THEN
                    RAISE EXCEPTION 'grace_experiment_grant_id_conflict';
                END IF;
                RETURN p_grant_id;
            END IF;
            INSERT INTO %I.authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref,valid_until)
            VALUES (p_grant_id,'resident:grace','grace.experiment.execute',p_scope_ref,
                p_actor_id,'rv.policy.grace-autonomy-experiment.v1',p_valid_until);
            INSERT INTO %I.institutional_authority_events
                (event_id,event_type,actor_id,subject_id,grant_id,payload)
            VALUES (pg_catalog.gen_random_uuid(),'authority_granted',p_actor_id,
                'resident:grace',p_grant_id,
                pg_catalog.jsonb_build_object('action','grace.experiment.execute',
                    'scope_ref',p_scope_ref,'policy_ref','rv.policy.grace-autonomy-experiment.v1',
                    'valid_until',p_valid_until));
            RETURN p_grant_id;
        END;
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema, authority_schema,
          authority_schema, authority_schema, authority_schema, authority_schema,
          authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.issue_grace_autonomy_experiment_grant(text,text,text,timestamptz) FROM PUBLIC',
                   authority_schema);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.issue_grace_autonomy_experiment_grant(text,text,text,timestamptz) TO riverview_core',
                       authority_schema);
    END IF;
END;
$migration$;
