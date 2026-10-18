# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: browser-tests/test_grace_staging_network_guard.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.0
# Purpose: Prove authenticated staging blocks work-order mutations and cross-origin requests
# Execution Model: Playwright test against a loopback-only synthetic authenticated fixture
# Observability: Sanitized browser request errors, no body or cookie capture
# Dependencies: pytest-playwright; test_grace_staging_browser_fixture.py
# Authority: Synthetic cookie only; denied requests never reach the fixture server
# Changed: 2026-10-18 UTC | RV-C2-STAGING-GRACE-BROWSER-004 | Add staging network-denial proof
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: tests/test_grace_staging_browser_fixture.py
# History: Git
# =============================================================================
"""Exercise the staging network fence with harmless, deliberately denied requests."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Page


pytestmark = pytest.mark.skipif(
    os.environ.get("RIVERVIEW_GRACE_STAGING_FIXTURE") != "1",
    reason="only run in the disposable local authenticated fixture",
)


def test_fixture_mode_blocks_mutation_and_cross_origin(page: Page, browser_error_log: list[dict], base_url: str):
    page.goto("/", wait_until="load")
    page.evaluate("""async origin => {
      try { await fetch('/api/v1/resident/conversations', {method: 'POST', body: 'private-post-body-must-not-be-logged'}); }
      catch (_) {}
      try { await fetch(origin.replace('127.0.0.1', 'localhost') + '/', {method: 'GET'}); }
      catch (_) {}
    }""", base_url)
    page.wait_for_timeout(100)
    assert {error["kind"] for error in browser_error_log} >= {"blocked_non_get", "blocked_cross_origin"}
    assert all("private-post-body-must-not-be-logged" not in str(error) for error in browser_error_log)
