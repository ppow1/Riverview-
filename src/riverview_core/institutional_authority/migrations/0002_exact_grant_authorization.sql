-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0002_exact_grant_authorization.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.0
-- Purpose: Add a narrowly callable exact-grant check without exposing registry tables
-- Execution Model: Explicit additive migration; privilege boundary is applied separately
-- Observability: Function returns principal and exact matching grant identifiers only
-- Dependencies: PostgreSQL 16; migrations 0000 and 0001; dedicated authority schema
-- Authority: No registry rows are changed; function reveals no credential digest
-- Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT | Initial exact-grant SQL boundary
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
        CREATE FUNCTION %I.authorize_exact_grant(
            p_credential_sha256 bytea,
            p_action text,
            p_scope_ref text
        ) RETURNS TABLE(principal_id text, grant_id text)
        LANGUAGE plpgsql
        VOLATILE
        SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $function$
        BEGIN
            IF p_credential_sha256 IS NULL
               OR pg_catalog.octet_length(p_credential_sha256) <> 32
               OR p_action IS NULL OR pg_catalog.length(p_action) = 0
               OR pg_catalog.length(p_action) > 128
               OR p_scope_ref IS NULL OR pg_catalog.length(p_scope_ref) = 0
               OR pg_catalog.length(p_scope_ref) > 512 THEN
                RETURN;
            END IF;

            RETURN QUERY
            SELECT principal.principal_id, grant_row.grant_id
              FROM %I.principal_credentials AS credential
              JOIN %I.institutional_principals AS principal
                USING (principal_id)
              JOIN %I.authority_grants AS grant_row
                USING (principal_id)
             WHERE credential.credential_sha256 = p_credential_sha256
               AND credential.revoked_at IS NULL
               AND (credential.expires_at IS NULL
                    OR credential.expires_at > pg_catalog.clock_timestamp())
               AND principal.status = 'active'
               AND grant_row.action = p_action
               AND grant_row.scope_ref = p_scope_ref
               AND grant_row.revoked_at IS NULL
               AND grant_row.valid_from <= pg_catalog.clock_timestamp()
               AND (grant_row.valid_until IS NULL
                    OR grant_row.valid_until > pg_catalog.clock_timestamp())
             ORDER BY grant_row.created_at DESC
             LIMIT 1
             FOR SHARE OF credential, principal, grant_row;
        END;
        $function$
    $ddl$, authority_schema, authority_schema, authority_schema, authority_schema);

    EXECUTE format('REVOKE ALL ON FUNCTION %I.authorize_exact_grant(bytea,text,text) FROM PUBLIC',
                   authority_schema);
END;
$migration$;
