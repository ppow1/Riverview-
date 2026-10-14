-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0006_authorized_implementation_successor.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Expose the one current, audited office implementation transition to the resident runtime
-- Execution Model: Additive SECURITY DEFINER query; runtime receives function execute only
-- Observability: Decision is tied to the immutable office_model_implementation_changed event
-- Dependencies: Authority migrations 0001-0005; protected authority boundary
-- Authority: Current bound resident credential with exact office.state.write scope; no mutation
-- Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Bounded predecessor compatibility check
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
        CREATE FUNCTION %I.authorized_office_implementation_successor(
            p_credential_sha256 bytea, p_office_id text,
            p_predecessor_id text, p_predecessor_revision text,
            p_successor_id text, p_successor_revision text,
            p_required_capability text
        ) RETURNS boolean
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
        DECLARE
            bound_principal text;
            authorized_principal text;
            current_binding_revision bigint;
        BEGIN
            IF p_credential_sha256 IS NULL
               OR pg_catalog.octet_length(p_credential_sha256) <> 32
               OR p_office_id IS NULL OR pg_catalog.length(p_office_id) = 0
               OR pg_catalog.length(p_office_id) > 256
               OR p_predecessor_id IS NULL OR pg_catalog.length(p_predecessor_id) > 256
               OR p_predecessor_revision IS NULL OR pg_catalog.length(p_predecessor_revision) > 256
               OR p_successor_id IS NULL OR pg_catalog.length(p_successor_id) > 256
               OR p_successor_revision IS NULL OR pg_catalog.length(p_successor_revision) > 256
               OR p_required_capability IS NULL OR p_required_capability<>'grace.reasoning.80b'
               OR p_predecessor_id = p_successor_id THEN
                RETURN false;
            END IF;

            SELECT principal.principal_id,binding.binding_revision
              INTO bound_principal,current_binding_revision
              FROM %I.office_bindings AS binding
              JOIN %I.resident_occupants AS occupant USING (occupant_id)
              JOIN %I.institutional_principals AS principal USING (principal_id)
              JOIN %I.resident_implementations AS successor
                ON successor.implementation_id=binding.implementation_id
             WHERE binding.office_id=p_office_id
               AND binding.implementation_id=p_successor_id
               AND successor.kind='model'
               AND successor.revision=p_successor_revision
               AND principal.status='active'
             FOR SHARE OF binding;
            IF bound_principal IS NULL THEN RETURN false; END IF;

            SELECT grant_check.principal_id INTO authorized_principal
              FROM %I.authorize_exact_grant(
                p_credential_sha256,'office.state.write','office:' || p_office_id
              ) AS grant_check;
            IF authorized_principal IS NULL OR authorized_principal<>bound_principal THEN
                RETURN false;
            END IF;

            RETURN EXISTS (
                SELECT 1
                  FROM %I.institutional_authority_events AS event
                  JOIN %I.resident_implementations AS predecessor
                    ON predecessor.implementation_id=p_predecessor_id
                  JOIN %I.resident_implementations AS successor
                    ON successor.implementation_id=p_successor_id
                 WHERE event.event_type='office_model_implementation_changed'
                   AND event.office_id=p_office_id
                   AND event.subject_id=bound_principal
                   AND event.payload->>'previous_implementation_id'=p_predecessor_id
                   AND event.payload->>'implementation_id'=p_successor_id
                   AND event.payload->>'binding_revision'=current_binding_revision::text
                   AND event.payload->>'implementation_revision'=p_successor_revision
                   AND event.payload->'deferred_compatibility_capabilities' ? p_required_capability
                   AND predecessor.kind='model'
                   AND predecessor.revision=p_predecessor_revision
                   AND predecessor.provider_ref=successor.provider_ref
                   AND successor.provider_ref='grace.readiness_router.v1'
            );
        END;
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema, authority_schema,
          authority_schema, authority_schema, authority_schema, authority_schema,
          authority_schema, authority_schema);

    EXECUTE format('REVOKE ALL ON FUNCTION %I.authorized_office_implementation_successor(bytea,text,text,text,text,text,text) FROM PUBLIC', authority_schema);
END;
$migration$;
