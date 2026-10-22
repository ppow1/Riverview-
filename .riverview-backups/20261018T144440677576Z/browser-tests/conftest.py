# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: browser-tests/conftest.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Capture bounded browser errors and an isolated run summary
# Execution Model: Pytest fixture and lifecycle hooks
# Observability: Private JSON reports; Playwright plugin stores screenshots and failure traces
# Dependencies: pytest-playwright; Python 3.10+
# Authority: Never loads an authenticated profile; network mutations are blocked in tests
# Changed: 2026-10-18 UTC | RV-LINUX-BROWSER-ACCEPTANCE-001 | Add redacted browser evidence capture
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: tests/browser/test_read_only_smoke.py
# History: Git
# =============================================================================
"""Shared safe evidence capture for Linux browser acceptance tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

import pytest


def _output_dir() -> Path:
    configured = os.environ.get("RIVERVIEW_BROWSER_OUTPUT_DIR")
    path = Path(configured) if configured else Path("test-results/browser-evidence")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    return path


def _safe_message(value: str) -> str:
    value = re.sub(r"https?://[^\s'\"]+", lambda match: _safe_url(match.group(0)), value)
    value = re.sub(r"(?i)(authorization|cookie|password|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]+",
                   r"\1=[redacted]", value)
    return value[:1000]


def _safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        host = f"[{host}]" if ":" in host else host
        return urlunsplit((parsed.scheme, host + port, parsed.path, "", ""))
    except ValueError:
        return "[url-redacted]"


@pytest.fixture
def browser_error_log(page, request):
    """Collect errors without recording request bodies, headers, or query strings."""
    errors: list[dict[str, str]] = []
    blocked_methods: list[str] = []

    def console_message(message):
        if message.type == "error":
            errors.append({"kind": "console_error", "message": _safe_message(message.text)})

    def page_error(error):
        errors.append({"kind": "page_error", "message": _safe_message(str(error))})

    def request_failed(browser_request):
        errors.append({"kind": "request_failed", "url": _safe_url(browser_request.url),
                       "method": browser_request.method})

    def block_non_get(route):
        method = route.request.method.upper()
        if method != "GET":
            blocked_methods.append(method)
            errors.append({"kind": "blocked_non_get", "method": method,
                           "url": _safe_url(route.request.url)})
            return route.abort("blockedbyclient")
        return route.continue_()

    page.on("console", console_message)
    page.on("pageerror", page_error)
    page.on("requestfailed", request_failed)
    page.route("**/*", block_non_get)
    yield errors

    output = _output_dir()
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.nodeid).strip("_.")[:100] or "browser-test"
    try:
        page.screenshot(path=str(output / f"{slug}.png"), full_page=True, timeout=10000)
    except Exception as error:  # Preserve the main test outcome; expose the sanitized capture failure.
        errors.append({"kind": "screenshot_error", "message": _safe_message(str(error))})
    report = {"test": request.node.nodeid, "errors": errors, "blocked_non_get_methods": blocked_methods}
    report_path = output / f"{slug}.errors.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(report_path, 0o600)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    results = getattr(item.config, "_riverview_browser_results", [])
    results.append({"test": item.nodeid, "status": "PASS" if report.passed else "FAIL" if report.failed else "SKIP"})
    item.config._riverview_browser_results = results


def pytest_sessionfinish(session, exitstatus):
    output = _output_dir()
    results = getattr(session.config, "_riverview_browser_results", [])
    summary = {"schema": "riverview.linux-browser-acceptance-results.v1",
               "status": "PASS" if exitstatus == 0 else "FAIL",
               "exit_code": exitstatus, "tests": results,
               "passed": sum(item["status"] == "PASS" for item in results),
               "failed": sum(item["status"] == "FAIL" for item in results),
               "skipped": sum(item["status"] == "SKIP" for item in results)}
    target = os.environ.get("RIVERVIEW_BROWSER_TARGET_ORIGIN", "")
    if target:
        summary["target_origin"] = target
    path = output / "browser-errors.json"
    error_reports = sorted(output.glob("*.errors.json"))
    summary["error_reports"] = [item.name for item in error_reports]
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
