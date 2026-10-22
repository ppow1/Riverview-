# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: browser-tests/test_grace_staging_readonly.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Inspect the authenticated Grace conversation and work-order approval boundary in disposable staging
# Execution Model: Opt-in Playwright staging test; all browser writes except empty session initialization are blocked
# Observability: Private screenshots/error report; tracing disabled to avoid retaining authenticated conversation traffic
# Dependencies: pytest-playwright; staging-named HTTPS or explicitly confirmed loopback dashboard
# Authority: Caller-supplied test-only cookie state and existing conversation access; never submits a message/objective
# Changed: 2026-10-18 UTC | RV-C2-STAGING-GRACE-BROWSER-004 | Verify redaction before staging screenshot
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: browser-tests/test_grace_staging_readonly.py; tests/test_linux_browser_runner.py
# History: Git
# =============================================================================
"""Read the actual Grace UI in staging, open its work-order boundary, and stop before submission."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Page, expect

from scripts.grace_staging_browser import validate_grace_staging_config


pytestmark = pytest.mark.skipif(
    os.environ.get("RIVERVIEW_GRACE_STAGING_MODE") != "1",
    reason="requires the explicit, host-scoped Grace staging runner configuration",
)


def test_staged_grace_conversation_and_work_order_authority_boundary(
    page: Page, browser_error_log: list[dict], base_url: str
):
    env = os.environ
    origin, _, _ = validate_grace_staging_config(
        base_url=base_url,
        configured_origin=env.get("RIVERVIEW_GRACE_STAGING_ORIGIN", ""),
        storage_state=env.get("RIVERVIEW_GRACE_STAGING_STORAGE_STATE", ""),
        test_account_label=env.get("RIVERVIEW_GRACE_STAGING_TEST_ACCOUNT_LABEL", ""),
        conversation_id=env.get("RIVERVIEW_GRACE_STAGING_CONVERSATION_ID", ""),
        seed_message_text=env.get("RIVERVIEW_GRACE_STAGING_SEED_MESSAGE_TEXT", ""),
        confirmation=env.get("RIVERVIEW_GRACE_STAGING_CONFIRMATION", ""),
        allow_remote=env.get("RIVERVIEW_GRACE_STAGING_ALLOW_REMOTE") == "1",
    )
    expected_account = env["RIVERVIEW_GRACE_STAGING_TEST_ACCOUNT_LABEL"].strip().casefold()
    conversation_id = env["RIVERVIEW_GRACE_STAGING_CONVERSATION_ID"]
    expected_seed_message = env["RIVERVIEW_GRACE_STAGING_SEED_MESSAGE_TEXT"].strip()
    target = urlsplit(origin)

    # Select only the explicitly seeded staging conversation; do not create one.
    page.add_init_script("localStorage.setItem('rv.grace.conversation', "
                         + json.dumps(conversation_id) + ");")
    response = page.goto("/", wait_until="load")
    assert response is not None and response.status == 200, "staging dashboard did not load"
    actual = urlsplit(page.url)
    assert (actual.scheme, actual.hostname, actual.port) == (target.scheme, target.hostname, target.port), \
        "dashboard navigated away from the exact staging origin"

    account_label = page.locator("#account-label")
    expect(account_label).to_be_visible(timeout=20000)
    account_text = (account_label.text_content() or "").casefold()
    assert expected_account in account_text, "configured staging test account is not the displayed account"
    assert "steward" in account_text, "configured test account is not displayed with the Steward website role"

    page.locator('button[data-view="grace-chat"]').click()
    expect(page.locator("#chat-title")).to_contain_text(conversation_id, timeout=20000)
    promote = None
    rows = page.locator("#chat-history [data-message-row]")
    expect(rows.first).to_be_visible(timeout=20000)
    for index in range(rows.count()):
        row = rows.nth(index)
        message_text = (row.locator(".message-content").text_content() or "").strip()
        candidate = row.locator("[data-message-work-order]")
        if message_text == expected_seed_message and candidate.count():
            promote = candidate.first
            break
    assert promote is not None, "pre-seeded harmless Steward message was not found"
    expect(promote).to_be_visible()
    promote.locator("xpath=ancestor::details[1]").locator("summary").click()
    promote.click()

    dialog = page.locator("#work-order-dialog")
    expect(dialog).to_be_visible()
    dialog_text = (dialog.text_content() or "").casefold()
    assert "requires the exact steward grant" in dialog_text, "work-order authority boundary is not visible"
    assert "does not approve execution" in dialog_text, "approval and execution boundaries are conflated"
    expect(page.locator("#work-order-submit")).to_be_visible()

    # The code deliberately stops here: no message send, objective submission, approval, or execution.
    dialog.locator("[data-close-dialog]").click()
    page.locator('button[data-view="objectives"]').click()
    expect(page.locator("#objective-state")).to_contain_text("Source available", timeout=15000)
    objective_note = page.locator("#view-objectives .note")
    expect(objective_note).to_contain_text("objective.submit on work-order:engineering")
    assert browser_error_log == [], "browser errors, cross-origin requests, or blocked mutations were observed"

    # Evidence from staging must not retain account labels or conversation/objective content.
    page.locator("#account-label").evaluate("element => element.textContent = '[test account redacted]'")
    page.locator("#chat-title").evaluate("element => element.textContent = 'Grace test conversation [redacted]'")
    page.locator("#chat-history").evaluate(
        "element => element.replaceChildren(document.createTextNode('[conversation content redacted]'))"
    )
    page.locator("#work-order-source").evaluate(
        "element => element.replaceChildren(document.createTextNode('[message content redacted]'))"
    )
    page.locator("#objective-list").evaluate(
        "element => element.replaceChildren(document.createTextNode('[objective details redacted]'))"
    )
    page.locator("#chat-message").evaluate("element => element.value = ''")
    rendered_after_redaction = page.locator("body").inner_text()
    for private_value in (expected_account, conversation_id.casefold(), expected_seed_message.casefold(),
                          "private fixture input", "synthetic fixture objective details"):
        assert private_value not in rendered_after_redaction.casefold(), \
            "private staging content remained visible before screenshot capture"
    output = Path(os.environ["RIVERVIEW_BROWSER_OUTPUT_DIR"])
    screenshot_dir = output / "playwright"
    screenshot_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(screenshot_dir, 0o700)
    screenshot = screenshot_dir / "grace-staging-redacted.png"
    page.screenshot(path=str(screenshot), full_page=True)
    screenshot.chmod(stat.S_IRUSR | stat.S_IWUSR)
