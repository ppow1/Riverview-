-- =============================================================================
-- RIVERVIEW~ CONTROLLED MIGRATION
-- File: src/riverview_core/account_auth/migrations/0001_account_authentication.sql
-- Component: WEBSITE-ACCOUNT-AUTH
-- Revision: 1.0.1
-- Purpose: Durable email enrollment, role, challenge, session, rate-limit and audit state
-- Execution Model: Transactional PostgreSQL schema migration
-- Observability: Versioned migration ledger and append-only account audit
-- Dependencies: PostgreSQL 16; separately provisioned riverview_accounts schema
-- Authority: Additive account tables only; never changes public, riverview_dev or authority grants
-- Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Initial isolated account schema
-- Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Permit the locally authorized Steward bootstrap challenge
-- Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
-- Tests: tests/test_account_auth.py
-- History: Git and revision/backup manifest
-- =============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE enrollments (
    enrollment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('awaiting_email','pending','approved','rejected','disabled')),
    email_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    decided_at TIMESTAMPTZ,
    decided_by UUID
);

CREATE TABLE accounts (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    email_verified_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    disabled_at TIMESTAMPTZ,
    authority_principal_id TEXT UNIQUE
);

CREATE TABLE account_roles (
    account_id UUID NOT NULL REFERENCES accounts(account_id),
    role TEXT NOT NULL CHECK (role IN ('viewer','operator','steward')),
    granted_by UUID,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (account_id, role)
);

CREATE TABLE challenges (
    challenge_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('enrollment','login','steward_bootstrap')),
    token_hash BYTEA NOT NULL CHECK (octet_length(token_hash)=32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ
);
CREATE INDEX challenges_expiry_idx ON challenges (expires_at) WHERE consumed_at IS NULL;

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(account_id),
    token_hash BYTEA NOT NULL UNIQUE CHECK (octet_length(token_hash)=32),
    csrf_hash BYTEA NOT NULL CHECK (octet_length(csrf_hash)=32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX sessions_account_idx ON sessions (account_id) WHERE revoked_at IS NULL;

CREATE TABLE rate_limits (
    key_hash BYTEA PRIMARY KEY CHECK (octet_length(key_hash)=32),
    window_started_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL CHECK (attempts > 0)
);

CREATE TABLE account_audit (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type TEXT NOT NULL,
    account_id UUID,
    subject_email TEXT,
    actor_account_id UUID,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION reject_account_audit_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'account audit is append-only';
END
$$;
CREATE TRIGGER account_audit_append_only
BEFORE UPDATE OR DELETE ON account_audit
FOR EACH ROW EXECUTE FUNCTION reject_account_audit_mutation();

