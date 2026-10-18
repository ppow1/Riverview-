# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: browser-tests/test_grace_staging_network_guard.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Prove authenticated staging blocks work-order mutations and cross-origin requests
# Execution Model: Playwright test against a loopback-only synthetic authenticated fixture
# Observability: Sanitized browser request errors, no body or cookie capture
# Dependencies: pytest-playwright; test_grace_staging_browser_fixture.py
# Authority: Synthetic cookie only; denied requests never reach the fixture server
# Changed: 2026-10-18 UTC | RV-C2-DOD-REMEDIATION-001 | Assert adversarial browser text and private URL data are omitted
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
    page.evaluate("console.error('Private failure conversation 269535bd-8556-4f12-9d42-3b722837fbab cookie=private-cookie token=private-token')")
    page.evaluate("""async origin => {
      try { await fetch('/api/v1/resident/conversations/private-conversation-id?token=private-query-token', {method: 'POST', body: 'private-post-body-must-not-be-logged'}); }
      catch (_) {}
      try { await fetch(origin.replace('127.0.0.1', 'localhost') + '/conversation/cross-origin-private-id?key=private-cross-origin-token', {method: 'GET'}); }
      catch (_) {}
    }""", base_url)
    page.wait_for_timeout(100)
    assert {error["kind"] for error in browser_error_log} >= {"blocked_non_get", "blocked_cross_origin"}
    assert all("private-post-body-must-not-be-logged" not in str(error) for error in browser_error_log)
    assert all(error.get("url") == "[request URL redacted]" for error in browser_error_log if "url" in error)
    assert all(error.get("message") == "Browser error details redacted" for error in browser_error_log
               if error["kind"] == "console_error")
    report = str(browser_error_log)
    for private_marker in ("269535bd", "private-cookie", "private-token", "private-conversation-id",
                          "private-query-token", "cross-origin-private-id", "private-cross-origin-token"):
        assert private_marker not in report
