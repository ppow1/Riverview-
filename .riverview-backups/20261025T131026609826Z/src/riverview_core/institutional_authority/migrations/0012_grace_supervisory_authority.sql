-- File Revision: 1.0.0
-- Steward-gated Luna grant for the two bounded Grace supervisory functions.
DO $migration$
DECLARE authority_schema text := current_schema();
BEGIN
    EXECUTE format($ddl$
        CREATE FUNCTION %I.issue_grace_supervisory_luna_grant(
            p_actor_id text, p_grant_id text, p_valid_until timestamptz
        ) RETURNS text
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
        BEGIN
            IF p_actor_id IS NULL OR p_grant_id IS NULL
               OR p_grant_id !~ '^grant:grace-supervision:[0-9a-f-]{36}$'
               OR (p_valid_until IS NOT NULL AND p_valid_until <= pg_catalog.clock_timestamp()) THEN
                RAISE EXCEPTION 'grace_supervision_grant_envelope_invalid';
            END IF;
            PERFORM 1 FROM %I.institutional_principals AS principal
             WHERE principal.principal_id=p_actor_id
               AND principal.principal_kind='steward' AND principal.status='active';
            IF NOT FOUND OR NOT EXISTS (
                SELECT 1 FROM %I.authorize_exact_principal_grant(
                    p_actor_id,'authority.grant','institution')) THEN
                RAISE EXCEPTION 'grace_supervision_steward_authority_required';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM %I.institutional_principals
                WHERE principal_id='resident:grace' AND principal_kind='resident' AND status='active') THEN
                RAISE EXCEPTION 'grace_supervision_resident_unavailable';
            END IF;
            IF EXISTS (SELECT 1 FROM %I.authority_grants WHERE grant_id=p_grant_id) THEN
                IF EXISTS (SELECT 1 FROM %I.authority_grants WHERE grant_id=p_grant_id
                    AND principal_id='resident:grace' AND action='resident.reasoning.escalate'
                    AND scope_ref='provider:gpt-6-luna' AND granted_by=p_actor_id
                    AND revoked_at IS NULL AND valid_until IS NOT DISTINCT FROM p_valid_until) THEN
                    RETURN p_grant_id;
                END IF;
                RAISE EXCEPTION 'grace_supervision_grant_id_conflict';
            END IF;
            INSERT INTO %I.authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref,valid_until)
            VALUES (p_grant_id,'resident:grace','resident.reasoning.escalate',
                'provider:gpt-6-luna',p_actor_id,'rv.policy.grace-supervisory-luna.v1',p_valid_until);
            INSERT INTO %I.institutional_authority_events
                (event_id,event_type,actor_id,subject_id,grant_id,payload)
            VALUES (pg_catalog.gen_random_uuid(),'authority_granted',p_actor_id,
                'resident:grace',p_grant_id,pg_catalog.jsonb_build_object(
                    'action','resident.reasoning.escalate','scope_ref','provider:gpt-6-luna',
                    'policy_ref','rv.policy.grace-supervisory-luna.v1','valid_until',p_valid_until,
                    'functions',pg_catalog.jsonb_build_array('cme_diagnostic_recovery','performance_evaluation')));
            RETURN p_grant_id;
        END;
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema, authority_schema,
          authority_schema, authority_schema, authority_schema, authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.issue_grace_supervisory_luna_grant(text,text,timestamptz) FROM PUBLIC', authority_schema);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.issue_grace_supervisory_luna_grant(text,text,timestamptz) TO riverview_core', authority_schema);
    END IF;
END
$migration$;

DO $migration$
DECLARE authority_schema text := current_schema();
BEGIN
    EXECUTE format($ddl$
        CREATE FUNCTION %I.active_grace_supervisory_luna_grant(p_grant_id text)
        RETURNS text LANGUAGE sql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp AS $function$
            SELECT g.grant_id FROM %I.authority_grants g
            JOIN %I.institutional_principals p USING (principal_id)
            WHERE g.grant_id=p_grant_id AND g.principal_id='resident:grace'
              AND p.principal_kind='resident' AND p.status='active'
              AND g.action='resident.reasoning.escalate' AND g.scope_ref='provider:gpt-6-luna'
              AND g.policy_ref='rv.policy.grace-supervisory-luna.v1'
              AND g.revoked_at IS NULL AND g.valid_from<=pg_catalog.clock_timestamp()
              AND (g.valid_until IS NULL OR g.valid_until>pg_catalog.clock_timestamp()) LIMIT 1
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.active_grace_supervisory_luna_grant(text) FROM PUBLIC',authority_schema);
    EXECUTE format($ddl$
        CREATE FUNCTION %I.revoke_grace_supervisory_luna_grant(p_actor_id text,p_grant_id text)
        RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp AS $function$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM %I.institutional_principals p
                WHERE p.principal_id=p_actor_id AND p.principal_kind='steward' AND p.status='active')
               OR NOT EXISTS (SELECT 1 FROM %I.authorize_exact_principal_grant(
                    p_actor_id,'authority.grant','institution')) THEN
                RAISE EXCEPTION 'grace_supervision_steward_authority_required';
            END IF;
            UPDATE %I.authority_grants SET revoked_at=pg_catalog.clock_timestamp()
              WHERE grant_id=p_grant_id AND principal_id='resident:grace'
                AND action='resident.reasoning.escalate' AND scope_ref='provider:gpt-6-luna'
                AND policy_ref='rv.policy.grace-supervisory-luna.v1' AND revoked_at IS NULL;
            IF FOUND THEN
                INSERT INTO %I.institutional_authority_events
                    (event_id,event_type,actor_id,subject_id,grant_id,payload)
                VALUES (pg_catalog.gen_random_uuid(),'authority_revoked',p_actor_id,'resident:grace',p_grant_id,
                    pg_catalog.jsonb_build_object('action','resident.reasoning.escalate',
                        'scope_ref','provider:gpt-6-luna','reason_code','steward_revoked'));
                RETURN true;
            END IF;
            RETURN EXISTS (SELECT 1 FROM %I.authority_grants WHERE grant_id=p_grant_id AND revoked_at IS NOT NULL);
        END
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema,
          authority_schema, authority_schema, authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.revoke_grace_supervisory_luna_grant(text,text) FROM PUBLIC',authority_schema);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core') THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.active_grace_supervisory_luna_grant(text) TO riverview_core',authority_schema);
        EXECUTE format('GRANT EXECUTE ON FUNCTION %I.revoke_grace_supervisory_luna_grant(text,text) TO riverview_core',authority_schema);
    END IF;
END
$migration$;
