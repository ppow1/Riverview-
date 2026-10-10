# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/assignment_scheduler/__init__.py
# Component: ASSIGNMENT-SCHEDULER
# Revision: 1.0.0
# Purpose: Isolated M1.4 fair assignment lease scheduling package
# Execution Model: PostgreSQL request-driven scheduler interface
# Observability: Durable lease generations and assignment transition events
# Dependencies: Python 3.10+; Psycopg 3; PostgreSQL 16; M1.2 ledger schema
# Authority: Scheduling only; does not authorize work or verify outcomes
# Changed: 2026-10-10 UTC | RV-M1.4-001 | Initial package
# Contracts: docs/ROADMAP.md; docs/architecture/EVENT_AND_ASSIGNMENT_CONTRACT_v0.1.md
# Tests: tests/test_assignment_scheduler.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Independent assignment scheduling and fencing."""
