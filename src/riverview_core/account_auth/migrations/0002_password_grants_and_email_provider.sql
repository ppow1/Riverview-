-- =============================================================================
-- RIVERVIEW~ CONTROLLED MIGRATION
-- File: src/riverview_core/account_auth/migrations/0002_password_grants_and_email_provider.sql
-- Component: WEBSITE-ACCOUNT-AUTH
-- Revision: 1.0.0
-- Purpose: Add password login, scoped approval grants, password challenges and encrypted SMTP settings
-- Execution Model: Transactional additive PostgreSQL migration
-- Observability: Versioned migration ledger and bounded delivery status
-- Dependencies: PostgreSQL 16; separately provisioned account schema
-- Authority: Account state only; engineering grants remain separate
-- Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Add password, grant and provider state
-- Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
-- Tests: tests/test_account_auth.py
-- History: Git and revision/backup manifest
-- =============================================================================
ALTER TABLE accounts ADD COLUMN password_hash TEXT;
ALTER TABLE accounts ADD COLUMN grant_type TEXT NOT NULL DEFAULT 'permanent'
    CHECK (grant_type IN ('one_time','90_days','one_year','permanent'));
ALTER TABLE accounts ADD COLUMN grant_expires_at TIMESTAMPTZ;
ALTER TABLE accounts ADD COLUMN grant_revoked_at TIMESTAMPTZ;
ALTER TABLE accounts ADD COLUMN one_time_session_created_at TIMESTAMPTZ;
ALTER TABLE enrollments ADD COLUMN granted_role TEXT
    CHECK (granted_role IS NULL OR granted_role IN ('viewer','operator','steward'));
ALTER TABLE enrollments ADD COLUMN grant_type TEXT
    CHECK (grant_type IS NULL OR grant_type IN ('one_time','90_days','one_year','permanent'));
ALTER TABLE challenges DROP CONSTRAINT challenges_purpose_check;
ALTER TABLE challenges ADD CONSTRAINT challenges_purpose_check
    CHECK (purpose IN ('enrollment','login','steward_bootstrap','password_setup','password_reset'));

CREATE TABLE email_provider_config (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    smtp_host TEXT NOT NULL,
    smtp_port INTEGER NOT NULL CHECK (smtp_port BETWEEN 1 AND 65535),
    tls_mode TEXT NOT NULL CHECK (tls_mode IN ('starttls','implicit')),
    sender_email TEXT NOT NULL,
    sender_name TEXT NOT NULL,
    admin_email TEXT NOT NULL,
    reply_to_email TEXT NOT NULL,
    smtp_username TEXT NOT NULL,
    password_ciphertext BYTEA NOT NULL,
    updated_by UUID,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    last_test_at TIMESTAMPTZ,
    last_test_status TEXT CHECK (last_test_status IS NULL OR last_test_status IN ('sent','failed')),
    last_test_error TEXT,
    last_delivery_at TIMESTAMPTZ,
    last_delivery_status TEXT CHECK (last_delivery_status IS NULL OR last_delivery_status IN ('sent','failed')),
    last_delivery_error TEXT
);
REVOKE ALL ON email_provider_config FROM PUBLIC;
