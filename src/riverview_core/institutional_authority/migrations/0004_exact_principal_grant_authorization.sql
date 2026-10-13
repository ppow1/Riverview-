-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0004_exact_principal_grant_authorization.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.1
-- Purpose: Check exact grants for an identity authenticated by a linked Riverview account
-- Execution Model: Additive SECURITY DEFINER function; runtime receives execute only
-- Observability: Returns only the exact matching principal and grant identifiers
-- Dependencies: PostgreSQL 16; migrations 0001-0003 and protected authority boundary
-- Authority: Does not authenticate callers, issue grants, or expose registry rows
-- Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Add exact-grant decision by server-authenticated principal
-- Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Restrict linked-account authorization to active institutional Stewards
-- =============================================================================
DO $migration$
DECLARE
    authority_schema text := current_schema();
BEGIN
    IF authority_schema IS NULL THEN
        RAISE EXCEPTION 'authority migration requires a selected schema';
    END IF;

    EXECUTE format($ddl$
        CREATE FUNCTION %I.authorize_exact_principal_grant(
            p_principal_id text,
            p_action text,
            p_scope_ref text
        ) RETURNS TABLE(principal_id text, grant_id text)
        LANGUAGE plpgsql VOLATILE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
        BEGIN
            IF p_principal_id IS NULL OR pg_catalog.length(p_principal_id)=0
               OR pg_catalog.length(p_principal_id)>256
               OR p_action IS NULL OR pg_catalog.length(p_action)=0
               OR pg_catalog.length(p_action)>128
               OR p_scope_ref IS NULL OR pg_catalog.length(p_scope_ref)=0
               OR pg_catalog.length(p_scope_ref)>512 THEN
                RETURN;
            END IF;

            RETURN QUERY
            SELECT principal.principal_id, grant_row.grant_id
              FROM %I.institutional_principals AS principal
              JOIN %I.authority_grants AS grant_row USING (principal_id)
             WHERE principal.principal_id=p_principal_id
               AND principal.principal_kind='steward'
               AND principal.status='active'
               AND grant_row.action=p_action
               AND grant_row.scope_ref=p_scope_ref
               AND grant_row.revoked_at IS NULL
               AND grant_row.valid_from<=pg_catalog.clock_timestamp()
               AND (grant_row.valid_until IS NULL
                    OR grant_row.valid_until>pg_catalog.clock_timestamp())
             ORDER BY grant_row.created_at DESC
             LIMIT 1
             FOR SHARE OF principal, grant_row;
        END;
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema);

    EXECUTE format('REVOKE ALL ON FUNCTION %I.authorize_exact_principal_grant(text,text,text) FROM PUBLIC',
                   authority_schema);
END;
$migration$;
