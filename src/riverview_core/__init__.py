# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/__init__.py
# Component: CORE-LEDGER
# Revision: 1.0.0
# Purpose: Public Python package exports for ledger prototype
# Execution Model: Imported library
# Observability: N/A; parent ledger component
# Dependencies: Python 3; local ledger module
# Authority: Exports only; no independent runtime
# Changed: 2026-10-09 UTC | ENG-REV-004 | Initial controlled header migration
# Contracts: docs/architecture/CORE_CONTRACT.md
# Tests: tests/test_ledger.py
# History: Git commit 6810e00374f50a81820be5f4e7714b329965ea66 and staged predecessor manifest
# =============================================================================

"""Riverview~ initial event-driven core (standard library, local prototype)."""
from .ledger import Ledger, TransitionError
__all__ = ["Ledger", "TransitionError"]
