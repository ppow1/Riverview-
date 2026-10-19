-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0012_resource_selection_policy.sql
-- Component: COMMS5-RESOURCE-POLICY
-- Revision: 1.0.0
-- Purpose: Persist audited Engineering worker selection preferences and locks
-- Authority: Comms5 authenticated Steward operation; scheduler consumes preference only
-- Rollback: Disable policy reads; preserve policy and event history. No destructive downgrade.
-- =============================================================================
CREATE TABLE resource_selection_policies (
    policy_key TEXT PRIMARY KEY CHECK (policy_key='engineering'),
    revision INTEGER NOT NULL CHECK (revision>0),
    mode TEXT NOT NULL CHECK (mode IN ('automatic','priority','target','balanced')),
    parameters JSONB NOT NULL CHECK (jsonb_typeof(parameters)='object'),
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    changed_by TEXT NOT NULL CHECK (length(changed_by) BETWEEN 1 AND 256),
    authority_reference TEXT NOT NULL CHECK (length(authority_reference) BETWEEN 1 AND 256),
    rationale TEXT NOT NULL CHECK (length(rationale)<=1000),
    last_selected_worker TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE resource_selection_policy_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_key TEXT NOT NULL REFERENCES resource_selection_policies(policy_key),
    revision INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('policy_set','policy_locked','policy_unlocked','worker_selected')),
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 240),
    actor_id TEXT NOT NULL CHECK (length(actor_id) BETWEEN 1 AND 256),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload)='object'),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX resource_selection_policy_events_history
    ON resource_selection_policy_events(policy_key,revision,occurred_at,event_id);

DO $$
DECLARE runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=runtime_role) THEN
        EXECUTE format('GRANT SELECT,INSERT,UPDATE (revision,mode,parameters,locked,changed_by,authority_reference,rationale,last_selected_worker,updated_at) ON %I.resource_selection_policies TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT SELECT,INSERT ON %I.resource_selection_policy_events TO %I',current_schema(),runtime_role);
    END IF;
END;
$$;
