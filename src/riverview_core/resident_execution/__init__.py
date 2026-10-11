# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/__init__.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Export governed objective-to-work-order execution interfaces
# Execution Model: PostgreSQL-backed in-process orchestration
# Observability: Durable objective lifecycle events and artifact provenance
# Dependencies: assignment intake; worker adapter; PostgreSQL
# Authority: Exact grants required; proposed plans never grant execution rights
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Initial vertical-slice contract
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: tests/test_grace_execution.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Small governed bridge from Grace objectives into the existing CME."""

from .pipeline import (GraceExecutionPipeline, ObjectiveError,
                       ObjectiveNotAuthorized, ObjectiveStateError)

__all__ = ["GraceExecutionPipeline", "ObjectiveError",
           "ObjectiveNotAuthorized", "ObjectiveStateError"]
