-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0001_institutional_authority.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.1
-- Purpose: Persist principal credentials, exact grants, office bindings and state
-- Execution Model: Explicit additive migration; never run during application startup
-- Observability: Append-only identity, grant, binding and state events
-- Dependencies: PostgreSQL 16; selected Riverview schema
-- Authority: DDL limited to explicitly selected schema; no existing rows altered
-- Changed: 2026-10-11 UTC | RV-M4.1-001 | Add auditable credential issue and revoke event types
-- Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
-- Tests: tests/test_institutional_authority.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE institutional_offices (
    office_id TEXT PRIMARY KEY,
    office_role TEXT NOT NULL CHECK (length(office_role)>0),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE institutional_principals (
    principal_id TEXT PRIMARY KEY,
    principal_kind TEXT NOT NULL CHECK (principal_kind IN ('steward','resident','human','service','worker')),
    office_id TEXT REFERENCES institutional_offices(office_id),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX institutional_single_active_steward_idx
    ON institutional_principals(principal_kind) WHERE principal_kind='steward' AND status='active';

CREATE TABLE principal_credentials (
    credential_id UUID PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    credential_sha256 BYTEA NOT NULL UNIQUE CHECK (octet_length(credential_sha256)=32),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CHECK (expires_at IS NULL OR expires_at>issued_at)
);
CREATE INDEX principal_credentials_active_idx ON principal_credentials(principal_id,expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE authority_grants (
    grant_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    action TEXT NOT NULL CHECK (length(action)>0),
    scope_ref TEXT NOT NULL CHECK (length(scope_ref)>0),
    granted_by TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    policy_ref TEXT NOT NULL CHECK (length(policy_ref)>0),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    valid_until TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (valid_until IS NULL OR valid_until>valid_from)
);
CREATE INDEX authority_grants_lookup_idx
    ON authority_grants(principal_id,action,scope_ref,valid_from DESC)
    WHERE revoked_at IS NULL;

CREATE TABLE resident_occupants (
    occupant_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL UNIQUE REFERENCES institutional_principals(principal_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    retired_at TIMESTAMPTZ
);

CREATE TABLE resident_implementations (
    implementation_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('model','tool','human','other')),
    provider_ref TEXT NOT NULL CHECK (length(provider_ref)>0),
    revision TEXT NOT NULL CHECK (length(revision)>0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE office_bindings (
    office_id TEXT PRIMARY KEY REFERENCES institutional_offices(office_id),
    occupant_id TEXT NOT NULL REFERENCES resident_occupants(occupant_id),
    implementation_id TEXT NOT NULL REFERENCES resident_implementations(implementation_id),
    binding_revision BIGINT NOT NULL CHECK (binding_revision>0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE office_runtime_state (
    office_id TEXT PRIMARY KEY REFERENCES institutional_offices(office_id),
    state JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(state)='object'),
    revision BIGINT NOT NULL DEFAULT 1 CHECK (revision>0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE institutional_authority_events (
    event_id UUID PRIMARY KEY,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'steward_bootstrapped','principal_created','credential_issued','credential_revoked',
        'authority_granted','authority_revoked',
        'office_created','occupant_created','implementation_created',
        'office_binding_replaced','office_state_updated')),
    actor_id TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    subject_id TEXT REFERENCES institutional_principals(principal_id),
    grant_id TEXT REFERENCES authority_grants(grant_id),
    office_id TEXT REFERENCES institutional_offices(office_id),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload)='object'),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX institutional_authority_events_time_idx
    ON institutional_authority_events(recorded_at,event_id);

CREATE FUNCTION reject_institutional_authority_event_mutation()
RETURNS trigger LANGUAGE plpgsql AS $rv$
BEGIN
    RAISE EXCEPTION 'institutional_authority_events is append-only';
END;
$rv$;
CREATE TRIGGER institutional_authority_events_append_only
    BEFORE UPDATE OR DELETE ON institutional_authority_events
    FOR EACH ROW EXECUTE FUNCTION reject_institutional_authority_event_mutation();
