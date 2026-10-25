-- RIVERVIEW~ CONTROLLED MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0023_grace_supervisory_event_scoped_cme_retry.sql
-- Component: RESIDENT-ORCHESTRATION
-- Revision: 1.0.0
-- Purpose: Persist one-use event-scoped Luna CME retry authorization and consumption.
-- Authority: Existing supervision authorization; events remain append-only.
-- Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Allow two audited retry-exception event types.
-- Tests: tests/test_external_reasoning_exchange.py
-- History: Git migration ledger and .riverview-backups/manifest.jsonl

ALTER TABLE grace_supervisory_authorization_events
    DROP CONSTRAINT grace_supervisory_authorization_events_event_type_check;

ALTER TABLE grace_supervisory_authorization_events
    ADD CONSTRAINT grace_supervisory_authorization_events_event_type_check
    CHECK (event_type IN (
        'activated','luna_reserved','luna_settled','revoked','budget_exhausted',
        'cme_retry_authorized','cme_retry_consumed'));

CREATE UNIQUE INDEX grace_supervisory_cme_retry_grant_per_stall
    ON grace_supervisory_authorization_events
       ((payload->>'stall_event_id'))
    WHERE event_type='cme_retry_authorized';

CREATE UNIQUE INDEX grace_supervisory_cme_retry_consumption_per_stall
    ON grace_supervisory_authorization_events
       ((payload->>'stall_event_id'))
    WHERE event_type='cme_retry_consumed';
