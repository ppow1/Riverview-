-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0006_deferred_execution_claims.sql
-- Component: RESIDENT-CONVERSATION
-- Revision: 1.0.0
-- Purpose: Serialize deferred-request execution across dashboard threads and service processes
-- Execution Model: Additive lease table; expired claims can be safely reclaimed
-- Observability: One request ID, opaque claim UUID and lease expiry; no conversation body
-- Dependencies: Resident execution migrations 0001-0005; PostgreSQL 16
-- Authority: Internal idempotency state only; all conversation authority remains separately checked
-- Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Add bounded durable claims for retries
-- Contracts: docs/components/RESIDENT_CONVERSATION.md
-- Tests: tests/test_resident_conversation.py
-- History: .riverview-backups/manifest.jsonl and Git
-- =============================================================================
CREATE TABLE resident_deferred_execution_claims (
    request_id UUID PRIMARY KEY,
    claim_token UUID NOT NULL,
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    claim_until TIMESTAMPTZ NOT NULL,
    CHECK (claim_until > claimed_at)
);

CREATE INDEX resident_deferred_claim_expiry
    ON resident_deferred_execution_claims(claim_until);
