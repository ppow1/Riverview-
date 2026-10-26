-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0017_reusable_scoped_grants.sql
-- Component: INSTITUTIONAL-AUTHORITY
-- Revision: 1.0.4
-- Purpose: Add optional use quotas and auditable Steward-approved delegated grants
-- Execution Model: Explicit additive migration; never run during application startup
-- Observability: Append-only approval, use, expiry, revocation and surrender events
-- Dependencies: PostgreSQL 16; institutional authority migration 0015
-- Authority: DDL limited to explicitly selected schema; preserves existing grant behavior
-- Changed: 2026-10-25 UTC | C1-REUSABLE-DELEGATION-GRANTS-20261025 | Add reusable scoped grant controls
-- Changed: 2026-10-25 UTC | C1-REUSABLE-DELEGATION-GRANTS-20261025 | Add digest-bound requests and idempotent reservation generations
-- Changed: 2026-10-25 UTC | C1-REUSABLE-DELEGATION-GRANTS-20261025 | Persist surrender idempotency and reservation operation lineage
-- Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
-- Tests: tests/test_institutional_authority.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
-- Add bounded, auditable grants without changing the behavior of existing rows.
ALTER TABLE authority_grants
    ADD COLUMN max_uses BIGINT CHECK (max_uses IS NULL OR max_uses > 0),
    ADD COLUMN used_count BIGINT NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    ADD COLUMN grant_kind TEXT NOT NULL DEFAULT 'direct'
        CHECK (grant_kind IN ('direct','delegated')),
    ADD COLUMN approval_ref TEXT,
    ADD COLUMN proposal_ref TEXT,
    ADD COLUMN proposal_digest TEXT,
    ADD COLUMN surrender_idempotency_key TEXT,
    ADD COLUMN surrender_reason_code TEXT,
    ADD COLUMN surrendered_by TEXT REFERENCES institutional_principals(principal_id),
    ADD COLUMN surrendered_at TIMESTAMPTZ,
    ADD COLUMN approved_by TEXT REFERENCES institutional_principals(principal_id),
    ADD COLUMN approved_at TIMESTAMPTZ,
    ADD COLUMN expired_audited_at TIMESTAMPTZ,
    ADD CONSTRAINT authority_grants_use_limit_check
        CHECK (max_uses IS NULL OR used_count <= max_uses),
    ADD CONSTRAINT authority_grants_delegated_approval_check
        CHECK (grant_kind = 'direct' OR
               (approval_ref IS NOT NULL AND length(approval_ref) > 0 AND
                proposal_ref IS NOT NULL AND length(proposal_ref) > 0 AND
                proposal_digest IS NOT NULL AND length(proposal_digest) > 0 AND
                approved_by IS NOT NULL AND approved_at IS NOT NULL));
ALTER TABLE authority_grants
    ADD CONSTRAINT authority_grants_delegated_scope_check
        CHECK (grant_kind='direct' OR
               (scope_ref ~ '^project:[A-Za-z0-9._-]+$' OR
                scope_ref ~ '^issue:[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$')),
    ADD CONSTRAINT authority_grants_delegated_action_check
        CHECK (grant_kind='direct' OR
               (action NOT LIKE '%*%' AND action NOT IN ('authority.grant','identity.manage','office.manage')));

CREATE TABLE delegated_grant_reservations (
    reservation_id UUID PRIMARY KEY,
    grant_id TEXT NOT NULL REFERENCES authority_grants(grant_id),
    grantee_id TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 256),
    generation INTEGER NOT NULL CHECK (generation > 0),
    operation_ref TEXT NOT NULL CHECK (length(operation_ref) BETWEEN 1 AND 256),
    action TEXT NOT NULL CHECK (length(action)>0),
    scope_ref TEXT NOT NULL CHECK (length(scope_ref)>0),
    proposal_ref TEXT NOT NULL CHECK (length(proposal_ref)>0),
    status TEXT NOT NULL CHECK (status IN ('reserved','consumed','released','expired')),
    lease_expires_at TIMESTAMPTZ NOT NULL,
    result_ref TEXT,
    reason_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (grant_id,grantee_id,idempotency_key,generation),
    CHECK ((status='consumed') = (result_ref IS NOT NULL)),
    CHECK ((status='released') = (reason_code IS NOT NULL))
);
CREATE INDEX delegated_grant_reservations_live_idx
    ON delegated_grant_reservations(grant_id,lease_expires_at)
    WHERE status='reserved';

CREATE TABLE delegated_grant_requests (
    request_id TEXT PRIMARY KEY,
    request_kind TEXT NOT NULL CHECK (request_kind IN ('grant','change')),
    requester_id TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    grantee_id TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    change_grant_id TEXT REFERENCES authority_grants(grant_id),
    action TEXT NOT NULL CHECK (length(action)>0),
    scope_ref TEXT NOT NULL CHECK (length(scope_ref)>0),
    policy_ref TEXT NOT NULL CHECK (length(policy_ref)>0),
    request_ref TEXT NOT NULL CHECK (length(request_ref)>0),
    max_uses BIGINT CHECK (max_uses IS NULL OR max_uses>0),
    valid_until TIMESTAMPTZ,
    request_sha256 TEXT NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 200),
    status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')),
    decision TEXT CHECK (decision IN ('approve','reject')),
    decision_by TEXT REFERENCES institutional_principals(principal_id),
    decision_at TIMESTAMPTZ,
    decision_idempotency_key TEXT,
    approval_ref TEXT,
    grant_id TEXT REFERENCES authority_grants(grant_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (requester_id,request_kind,idempotency_key),
    CHECK ((request_kind='grant' AND change_grant_id IS NULL) OR
           (request_kind='change' AND change_grant_id IS NOT NULL)),
    CHECK ((status='pending' AND decision IS NULL AND decision_by IS NULL AND decision_at IS NULL) OR
           (status<>'pending' AND decision IS NOT NULL AND decision_by IS NOT NULL AND decision_at IS NOT NULL)),
    CHECK (max_uses IS NOT NULL OR valid_until IS NOT NULL)
);
CREATE INDEX delegated_grant_requests_grantee_idx
    ON delegated_grant_requests(grantee_id,created_at DESC);

ALTER TABLE institutional_authority_events
    DROP CONSTRAINT institutional_authority_events_event_type_check,
    ADD CONSTRAINT institutional_authority_events_event_type_check
        CHECK (event_type IN (
            'steward_bootstrapped','principal_created','credential_issued','credential_revoked',
            'authority_granted','authority_revoked','authority_grant_used',
            'authority_grant_reserved','authority_grant_reservation_released',
            'authority_grant_reservation_expired','authority_grant_expired',
            'authority_grant_surrendered','authority_delegation_request_created',
            'authority_delegation_request_decided',
            'office_created','occupant_created','implementation_created',
            'office_binding_replaced','office_state_updated',
            'office_model_implementation_changed','office_role_updated',
            'worker_registration_retired'));
