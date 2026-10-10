# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/cme/__init__.py
# Component: CME
# Revision: 1.0.0
# Purpose: Export the PostgreSQL-backed continuous monitoring service
# Execution Model: Package interface for scheduled continuous monitoring
# Observability: CME monitor health and durable attention events
# Dependencies: Psycopg 3; PostgreSQL ledger, scheduler, and worker migrations
# Authority: Observe assignments and write CME-owned records; never execute work
# Changed: 2026-10-10 UTC | RV-M2.4-001 | Initial CME monitoring package
# Contracts: docs/components/CME_MONITOR.md
# Tests: tests/test_cme_monitor.py
# History: Git and revision/backup manifest
# =============================================================================
"""Continuous Motion Engine monitoring interfaces."""

from .monitor import CMEPostgresMonitor, MonitorAlreadyRunning

__all__ = ["CMEPostgresMonitor", "MonitorAlreadyRunning"]
