# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/browser/test_read_only_smoke.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.0
# Purpose: Confirm a selected Riverview page renders in Linux headless Chromium
# Execution Model: Read-only browser acceptance test
# Observability: Test result, screenshot, error JSON, and failure trace
# Dependencies: pytest-playwright; local or explicitly authorized staging target
# Authority: Navigation is GET-only; no login, form submission, or live mutation
# Changed: 2026-10-18 UTC | RV-LINUX-BROWSER-ACCEPTANCE-001 | Add safe page-load smoke
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# History: Git
# =============================================================================
"""Read-only smoke check: one HTTP GET followed by visible document checks."""

import os
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect


def test_page_loads_without_browser_errors(page: Page, browser_error_log: list[dict], base_url: str):
    smoke_path = os.environ.get("RIVERVIEW_BROWSER_SMOKE_PATH", "/")
    response = page.goto(smoke_path, wait_until="load", timeout=30000)

    assert response is not None, "navigation returned no HTTP response"
    assert 200 <= response.status < 400, f"smoke GET returned HTTP {response.status}"
    assert urlsplit(page.url).netloc.lower() == urlsplit(base_url).netloc.lower(), \
        "smoke navigation redirected outside the approved origin"
    expect(page.locator("body")).to_be_visible()
    assert page.title().strip(), "page title is empty"

    expected_heading = os.environ.get("RIVERVIEW_BROWSER_EXPECT_HEADING")
    if expected_heading:
        expect(page.get_by_role("heading", name=expected_heading, exact=True)).to_be_visible()

    page.wait_for_timeout(200)
    assert not browser_error_log, f"browser errors or blocked non-GET requests were recorded: {browser_error_log}"
