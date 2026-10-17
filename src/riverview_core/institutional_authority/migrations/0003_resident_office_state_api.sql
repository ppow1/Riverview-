-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0003_resident_office_state_api.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.1
-- Purpose: Expose exact-grant office snapshot and CAS write to the restricted runtime role
-- Execution Model: Explicit additive SECURITY DEFINER functions
-- Observability: Writes append office_state_updated with principal and state revision
-- Dependencies: PostgreSQL 16; migrations 0001 and 0002; protected table owner
-- Authority: Active exact office.state.write grant and currently bound resident are mandatory
-- Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Add narrow resident office-state API
-- Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Disambiguate runtime state join
-- Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
-- Tests: tests/test_institutional_authority_boundary.py
-- History: .riverview-backups/manifest.jsonl and Git
-- =============================================================================
DO $migration$
DECLARE
    authority_schema text := current_schema();
BEGIN
    IF authority_schema IS NULL THEN
        RAISE EXCEPTION 'authority migration requires a selected schema';
    END IF;

    EXECUTE format($ddl$
        CREATE FUNCTION %I.read_authorized_office_state(
            p_credential_sha256 bytea, p_office_id text
        ) RETURNS jsonb
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
        DECLARE
            bound_principal text;
            authorized_principal text;
            snapshot jsonb;
        BEGIN
            IF p_credential_sha256 IS NULL
               OR pg_catalog.octet_length(p_credential_sha256) <> 32
               OR p_office_id IS NULL OR pg_catalog.length(p_office_id) = 0
               OR pg_catalog.length(p_office_id) > 256 THEN
                RETURN NULL;
            END IF;

            SELECT principal.principal_id INTO bound_principal
              FROM %I.office_bindings AS binding
              JOIN %I.resident_occupants AS occupant USING (occupant_id)
              JOIN %I.institutional_principals AS principal USING (principal_id)
             WHERE binding.office_id = p_office_id
               AND principal.status = 'active'
             FOR SHARE OF binding;
            IF bound_principal IS NULL THEN RETURN NULL; END IF;

            SELECT grant_check.principal_id INTO authorized_principal
              FROM %I.authorize_exact_grant(
                  p_credential_sha256, 'office.state.write', 'office:' || p_office_id
              ) AS grant_check;
            IF authorized_principal IS NULL OR authorized_principal <> bound_principal THEN
                RETURN NULL;
            END IF;

            SELECT pg_catalog.jsonb_build_object(
                'office_id', office.office_id,
                'office_role', office.office_role,
                'occupant_id', binding.occupant_id,
                'principal_id', bound_principal,
                'principal_kind', principal.principal_kind,
                'implementation_id', implementation.implementation_id,
                'implementation_kind', implementation.kind,
                'provider_ref', implementation.provider_ref,
                'implementation_revision', implementation.revision,
                'binding_revision', binding.binding_revision,
                'state', runtime_state.state,
                'state_revision', runtime_state.revision,
                'state_updated_at', runtime_state.updated_at
            ) INTO snapshot
              FROM %I.institutional_offices AS office
              JOIN %I.office_bindings AS binding USING (office_id)
              JOIN %I.resident_occupants AS occupant USING (occupant_id)
              JOIN %I.institutional_principals AS principal USING (principal_id)
              JOIN %I.resident_implementations AS implementation USING (implementation_id)
              JOIN %I.office_runtime_state AS runtime_state
                ON runtime_state.office_id = office.office_id
             WHERE office.office_id = p_office_id
               AND principal.principal_id = bound_principal;
            RETURN snapshot;
        END;
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema, authority_schema,
          authority_schema, authority_schema, authority_schema, authority_schema,
          authority_schema, authority_schema, authority_schema);

    EXECUTE format($ddl$
        CREATE FUNCTION %I.write_authorized_office_state(
            p_credential_sha256 bytea, p_office_id text, p_state jsonb,
            p_expected_revision bigint
        ) RETURNS bigint
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
        DECLARE
            bound_principal text;
            authorized_principal text;
            new_revision bigint;
        BEGIN
            IF p_credential_sha256 IS NULL
               OR pg_catalog.octet_length(p_credential_sha256) <> 32
               OR p_office_id IS NULL OR pg_catalog.length(p_office_id) = 0
               OR pg_catalog.length(p_office_id) > 256
               OR p_state IS NULL OR pg_catalog.jsonb_typeof(p_state) <> 'object'
               OR pg_catalog.octet_length(p_state::text) > 65536 THEN
                RAISE EXCEPTION 'invalid bounded office state request' USING ERRCODE='22023';
            END IF;

            SELECT principal.principal_id INTO bound_principal
              FROM %I.office_bindings AS binding
              JOIN %I.resident_occupants AS occupant USING (occupant_id)
              JOIN %I.institutional_principals AS principal USING (principal_id)
             WHERE binding.office_id = p_office_id
               AND principal.status = 'active'
             FOR UPDATE OF binding;
            IF bound_principal IS NULL THEN RETURN NULL; END IF;

            SELECT grant_check.principal_id INTO authorized_principal
              FROM %I.authorize_exact_grant(
                  p_credential_sha256, 'office.state.write', 'office:' || p_office_id
              ) AS grant_check;
            IF authorized_principal IS NULL OR authorized_principal <> bound_principal THEN
                RETURN NULL;
            END IF;

            UPDATE %I.office_runtime_state
               SET state=p_state, revision=revision+1, updated_at=pg_catalog.clock_timestamp()
             WHERE office_id=p_office_id
               AND (p_expected_revision IS NULL OR revision=p_expected_revision)
             RETURNING revision INTO new_revision;
            IF new_revision IS NULL THEN
                RAISE EXCEPTION 'office state revision conflict' USING ERRCODE='40001';
            END IF;

            INSERT INTO %I.institutional_authority_events
                (event_id,event_type,actor_id,office_id,payload)
            VALUES (pg_catalog.gen_random_uuid(),'office_state_updated',bound_principal,
                    p_office_id,pg_catalog.jsonb_build_object('revision',new_revision));
            RETURN new_revision;
        END;
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema, authority_schema,
          authority_schema, authority_schema, authority_schema);

    EXECUTE format('REVOKE ALL ON FUNCTION %I.read_authorized_office_state(bytea,text) FROM PUBLIC', authority_schema);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.write_authorized_office_state(bytea,text,jsonb,bigint) FROM PUBLIC', authority_schema);
END;
$migration$;
