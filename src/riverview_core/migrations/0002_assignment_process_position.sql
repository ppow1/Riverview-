-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/migrations/0002_assignment_process_position.sql
-- Component: POSTGRES-LEDGER
-- Revision: 1.0.0
-- Purpose: Persist exact canonical graph/node position on assignment records
-- Execution Model: Explicit additive PostgreSQL migration
-- Observability: Assignment row and transition event carry process graph/node IDs
-- Dependencies: 0001_assignment_event_ledger; PostgreSQL 16
-- Authority: Additive columns only; no historical position is inferred
-- Changed: 2026-10-13 UTC | RV-LEDGER-GRAPH-POSITION | Add nullable canonical position fields
-- Contracts: docs/components/POSTGRES_LEDGER.md; process_graphs/postgres-ledger/assignment-lifecycle.json
-- Tests: tests/test_postgres_ledger.py
-- History: Git
-- =============================================================================
ALTER TABLE assignments
    ADD COLUMN process_graph_id TEXT,
    ADD COLUMN process_node_id TEXT,
    ADD CONSTRAINT assignments_process_position_pair
        CHECK ((process_graph_id IS NULL AND process_node_id IS NULL) OR
               (process_graph_id IS NOT NULL AND process_node_id IS NOT NULL));

CREATE INDEX assignments_process_position_idx
    ON assignments(process_graph_id, process_node_id, updated_at DESC)
    WHERE process_graph_id IS NOT NULL AND process_node_id IS NOT NULL;
