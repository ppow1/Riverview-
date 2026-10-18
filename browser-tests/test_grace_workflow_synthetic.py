# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: browser-tests/test_grace_workflow_synthetic.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Browser-check the visible Grace proposal and approval boundary in an isolated synthetic fixture
# Execution Model: Playwright test with in-memory API interception
# Observability: Pytest result, screenshot, error JSON, and failure trace
# Dependencies: pytest-playwright; local static fixture server
# Authority: Synthetic data only; intercepted calls never contact Riverview APIs or create real authority
# Changed: 2026-10-18 UTC | RV-C2-GRACE-WORKFLOW-BROWSER-002 | Add synthetic workflow acceptance
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: browser-tests/test_grace_workflow_synthetic.py
# History: Git
# =============================================================================
"""Demonstrate request-to-status UI flow without real services or authority."""

import json
from urllib.parse import urlsplit

import os
import pytest

from playwright.sync_api import Page, expect

pytestmark = pytest.mark.skipif(
    os.environ.get("RIVERVIEW_GRACE_STAGING_MODE") == "1",
    reason="synthetic fixture is not used in authenticated staging mode",
)


def test_synthetic_grace_request_stops_at_real_execution_authorization(
    page: Page, browser_error_log: list[dict], base_url: str
):
    calls: list[tuple[str, str, dict | None]] = []

    def synthetic_api(route):
        request = route.request
        path = urlsplit(request.url).path
        body = json.loads(request.post_data) if request.post_data else None
        calls.append((request.method, path, body))

        if request.method == "POST" and path == "/__synthetic__/requests":
            assert body == {"message": "Please summarize the sample status normalization workflow."}
            payload = {"proposal_id": "synthetic-proposal-001", "status": "awaiting_steward_approval"}
        elif request.method == "POST" and path == "/__synthetic__/proposals/synthetic-proposal-001/approve":
            payload = {"approval_id": "synthetic-approval-001", "status": "approved"}
        elif request.method == "POST" and path == "/__synthetic__/work-orders":
            assert body == {"proposal_id": "synthetic-proposal-001", "approval_id": "synthetic-approval-001"}
            payload = {"work_order_id": "synthetic-work-order-001", "status": "created"}
        elif request.method == "GET" and path == "/__synthetic__/work-orders/synthetic-work-order-001":
            payload = {"work_order_id": "synthetic-work-order-001",
                       "status": "awaiting_actual_execution_authorization"}
        else:
            route.abort("blockedbyclient")
            raise AssertionError(f"unexpected synthetic workflow request: {request.method} {path}")

        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    # Registered after the generic guard, so only this exact fixture API is intercepted.
    page.route("**/__synthetic__/**", synthetic_api)
    response = page.goto("/grace-workflow.html", wait_until="load")
    assert response is not None and response.status == 200
    assert urlsplit(page.url).netloc == urlsplit(base_url).netloc
    heading = page.get_by_role("heading", name="Talk with Grace — isolated workflow demonstration", exact=True)
    expect(heading).to_be_visible()
    expect(page.get_by_text("SYNTHETIC TEST FIXTURE.", exact=False)).to_be_visible()
    expect(page.get_by_role("button", name="Create synthetic work-order record")).to_be_disabled()

    page.get_by_role("button", name="Submit synthetic request").click()
    expect(page.locator("#proposal-status")).to_contain_text("awaiting_steward_approval")
    expect(page.locator("#approval-boundary")).to_contain_text("does not create an Engineering work order")
    expect(page.get_by_role("button", name="Create synthetic work-order record")).to_be_disabled()

    page.get_by_role("button", name="Record synthetic approval (test only)").click()
    expect(page.locator("#proposal-status")).to_contain_text("synthetic fixture")
    expect(page.locator("#approval-boundary")).to_contain_text("does not grant real authority")
    page.get_by_role("button", name="Create synthetic work-order record").click()
    expect(page.locator("#work-order-status")).to_contain_text(
        "awaiting_actual_execution_authorization"
    )
    expect(page.locator("#work-order-status")).to_contain_text("No execution was dispatched.")

    assert calls == [
        ("POST", "/__synthetic__/requests", {"message": "Please summarize the sample status normalization workflow."}),
        ("POST", "/__synthetic__/proposals/synthetic-proposal-001/approve", None),
        ("POST", "/__synthetic__/work-orders", {"proposal_id": "synthetic-proposal-001",
                                                   "approval_id": "synthetic-approval-001"}),
        ("GET", "/__synthetic__/work-orders/synthetic-work-order-001", None),
    ]
    assert browser_error_log == []
