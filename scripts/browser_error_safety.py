# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/browser_error_safety.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.0
# Purpose: Produce privacy-safe browser error evidence without retaining input text or URLs
# Execution Model: Request-driven pure helper
# Observability: Fixed diagnostic strings consumed by browser report generation
# Dependencies: Python standard library only
# Authority: Redaction only; does not authorize browser requests or access target data
# Changed: 2026-10-18 UTC | RV-C2-DOD-REMEDIATION-001 | Initial dependency-free redaction helpers
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: tests/test_linux_browser_runner.py; browser-tests/test_grace_staging_network_guard.py
# History: Git and revision/backup manifest
# =============================================================================
"""Privacy-safe, deliberately lossy browser error fields."""


def safe_message(value: object) -> str:
    """Return a fixed diagnostic; arbitrary browser text can contain user data."""
    del value
    return "Browser error details redacted"


def safe_url(value: object) -> str:
    """Remove origin, path, query, and fragment from browser evidence."""
    del value
    return "[request URL redacted]"
