-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0018_delegated_host_scopes.sql
-- Purpose: Permit exact host-scoped delegated requests for registered hardware controllers.
-- Execution Model: Explicit additive migration; apply through guarded authority migration procedure.
-- Authority: Existing canonical requests, grants, and audit events are preserved.
-- =============================================================================
ALTER TABLE authority_grants
    DROP CONSTRAINT IF EXISTS authority_grants_delegated_scope_check;
ALTER TABLE authority_grants
    ADD CONSTRAINT authority_grants_delegated_scope_check
    CHECK (grant_kind='direct' OR
           scope_ref ~ '^project:[A-Za-z0-9._-]+$' OR
           scope_ref ~ '^issue:[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$' OR
           scope_ref ~ '^host:[a-z][a-z0-9-]{1,62}$');
