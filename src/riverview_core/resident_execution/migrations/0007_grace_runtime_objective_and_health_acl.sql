-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/resident_execution/migrations/0007_grace_runtime_objective_and_health_acl.sql
-- Component: RESIDENT-ORCHESTRATION
-- Revision: 1.0.0
-- Purpose: Grant the restricted runtime only the objective and health columns it uses
-- Execution Model: Additive, checksum-pinned PostgreSQL ACL migration
-- Observability: Durable objective lifecycle and Grace health; no unrelated tables
-- Dependencies: Resident execution migrations 0001-0006; PostgreSQL 16
-- Authority: Column-scoped DML on Grace objective/event/health relations only
-- Changed: 2026-10-15 UTC | RV-GRACE-HEALTH-WRITER-ACL-001 | Correct missing owner-session runtime ACLs
-- Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md
-- Tests: tests/test_grace_execution_health_acl.py
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
DO $$
DECLARE
    runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = runtime_role) THEN
        EXECUTE format(
            'GRANT SELECT (objective_id, request, scope_ref, submitter_id, acceptance_criteria, status, evidence, proposal, assignment_id, source_revision, source_sha256, revision, created_at, updated_at), INSERT (objective_id, request, scope_ref, submitter_id, acceptance_criteria, status), UPDATE (status, evidence, proposal, assignment_id, source_revision, source_sha256, revision, updated_at) ON %I.grace_objectives TO %I',
            current_schema(), runtime_role);
        EXECUTE format(
            'GRANT SELECT (sequence, objective_id, event_type, idempotency_key, actor_id, payload, occurred_at), INSERT (objective_id, event_type, idempotency_key, actor_id, payload) ON %I.grace_objective_events TO %I',
            current_schema(), runtime_role);
        EXECUTE format(
            'GRANT USAGE ON SEQUENCE %I.grace_objective_events_sequence_seq TO %I',
            current_schema(), runtime_role);
        EXECUTE format(
            'GRANT INSERT (service_id, instance_id, status, last_heartbeat_at, last_cycle_at, last_error_type, cycles_completed), UPDATE (instance_id, status, last_heartbeat_at, last_cycle_at, last_error_type, cycles_completed) ON %I.grace_execution_health TO %I',
            current_schema(), runtime_role);
    END IF;
END;
$$;
