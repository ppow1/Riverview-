-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/cme/migrations/0005_cme_monitoring.sql
-- Component: CME
-- Revision: 1.0.1
-- Purpose: Persist assignment deadlines, CME health, and idempotent attention events
-- Execution Model: Explicit PostgreSQL migration; never applied by monitor startup
-- Observability: cme_monitor_health and append-only cme_monitor_events
-- Dependencies: PostgreSQL 16; M1.2 ledger, M1.4 leases, M2.1-M2.3 worker tables
-- Authority: DDL limited to the explicitly selected schema
-- Changed: 2026-10-10 UTC | RV-M2.4-001 | Store CME deadlines, service health, and append-only attention records
-- Contracts: docs/components/CME_MONITOR.md; docs/ROADMAP.md
-- Tests: tests/test_cme_monitor.py
-- History: Git and revision sidecar
-- =============================================================================
CREATE TABLE cme_assignment_deadlines (
    assignment_id TEXT PRIMARY KEY REFERENCES assignments(id),
    deadline_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE cme_monitor_health (
    service_id TEXT PRIMARY KEY,
    instance_id UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('healthy','degraded')),
    last_heartbeat_at TIMESTAMPTZ NOT NULL,
    last_scan_at TIMESTAMPTZ,
    last_error TEXT,
    assignments_observed INTEGER NOT NULL CHECK (assignments_observed >= 0),
    workers_registered INTEGER NOT NULL CHECK (workers_registered >= 0),
    workers_enabled INTEGER NOT NULL CHECK (workers_enabled >= 0)
);

CREATE TABLE cme_monitor_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_key TEXT NOT NULL UNIQUE,
    service_id TEXT NOT NULL,
    assignment_id TEXT REFERENCES assignments(id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'monitor_started','monitor_failed','assignment_stalled','deadline_missed',
        'assignment_attention','recovery_requested','attention_resolved')),
    attention_key TEXT,
    details JSONB NOT NULL CHECK (jsonb_typeof(details)='object'),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX cme_monitor_events_assignment_idx
    ON cme_monitor_events(assignment_id,recorded_at,event_id);
CREATE INDEX cme_monitor_events_attention_idx
    ON cme_monitor_events(attention_key,event_type);
