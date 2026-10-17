# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/doorbell/__init__.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.0
# Purpose: Export the bounded local ChatGPT wake adapter
# Execution Model: Request-driven adapter
# Observability: Parent Comms5 caller receives metadata-only DoorbellResult
# Dependencies: Python standard library
# Authority: Fixed wake to one configured conversation; no browser response access
# Changed: 2026-10-17 UTC | RV-C3-DOORBELL-001 | Initial New-Core doorbell package
# Contracts: docs/components/CHATGPT_DOORBELL.md
# Tests: tests/test_chatgpt_doorbell.py
# History: Git and .riverview-revisions.json

"""Bounded Riverview ChatGPT doorbell adapter."""

from .browser_bridge import BrowserBridgeRunner, DoorbellRequest, DoorbellResult
from .config import DoorbellRuntimeConfig, bootstrap_config, load_config

__all__ = [
    "BrowserBridgeRunner",
    "DoorbellRequest",
    "DoorbellResult",
    "DoorbellRuntimeConfig",
    "bootstrap_config",
    "load_config",
]
