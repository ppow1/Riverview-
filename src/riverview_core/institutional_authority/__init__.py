# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/__init__.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.2
# Purpose: Export the durable identity and scoped authority registry
# Execution Model: Request-driven, PostgreSQL-backed authority checks
# Observability: Durable identity, grant and office-binding events
# Dependencies: Python 3.10+; Psycopg 3; explicit authority migration
# Authority: No implicit grants; bootstrap is a trusted local provisioning action
# Changed: 2026-10-11 UTC | RV-M4.1-001 | Initial institutional authority registry
# Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT | Export fail-closed runtime grant adapter
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_institutional_authority.py
# History: .riverview-backups/manifest.jsonl and Git
"""Persistent, fail-closed institutional identity and authority."""

from .registry import (AuthorityDenied, AuthorityRegistry, IdentityConflict,
                       RegistryUnavailable)
from .grants import ExactGrantAuthorizer, GrantCheckUnavailable, GrantDenied
from .permission_profiles import (PermissionDecision, ResidentPermissionStore,
                                  evaluate_profile)

__all__ = ["AuthorityDenied", "AuthorityRegistry", "IdentityConflict",
           "RegistryUnavailable", "ExactGrantAuthorizer",
           "GrantCheckUnavailable", "GrantDenied", "PermissionDecision",
           "ResidentPermissionStore", "evaluate_profile"]
