# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: browser-tests/conftest.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.4
# Purpose: Capture bounded errors and safely provision optional host-scoped staging browser state
# Execution Model: Pytest fixture and lifecycle hooks
# Observability: Private JSON reports; Playwright plugin stores screenshots and failure traces
# Dependencies: pytest-playwright; Python 3.10+
# Authority: Loads only explicitly supplied exact-host cookie state in staging mode; all mutations remain blocked
# Changed: 2026-10-18 UTC | RV-C2-STAGING-GRACE-BROWSER-003 | Add opt-in staging cookie state and exact session gate
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: browser-tests/test_grace_staging_readonly.py; browser-tests/test_read_only_smoke.py
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

from scripts.grace_staging_browser import validate_storage_state


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


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Load host-bound cookie state only when the guarded staging runner enables it."""
    if os.environ.get("RIVERVIEW_GRACE_STAGING_MODE") != "1":
        return browser_context_args
    origin = os.environ.get("RIVERVIEW_BROWSER_TARGET_ORIGIN", "")
    host = urlsplit(origin).hostname or ""
    state = validate_storage_state(
        os.environ.get("RIVERVIEW_GRACE_STAGING_STORAGE_STATE", ""), expected_host=host
    )
    return {**browser_context_args, "storage_state": str(state)}


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
        request = route.request
        method = request.method.upper()
        parsed = urlsplit(request.url)
        same_origin = (parsed.scheme + "://" + parsed.netloc).rstrip("/") == os.environ.get(
            "RIVERVIEW_BROWSER_TARGET_ORIGIN", ""
        )
        safe_session_init = (
            os.environ.get("RIVERVIEW_GRACE_STAGING_MODE") == "1"
            and same_origin
            and method == "POST"
            and parsed.path == "/api/v1/resident/conversation-session"
            and not parsed.query and not parsed.fragment
            and request.post_data in (None, "")
        )
        if method not in {"GET", "HEAD"} and not safe_session_init:
            blocked_methods.append(method)
            errors.append({"kind": "blocked_non_get", "method": method,
                           "url": _safe_url(request.url)})
            return route.abort("blockedbyclient")
        if os.environ.get("RIVERVIEW_GRACE_STAGING_MODE") == "1" and not same_origin:
            errors.append({"kind": "blocked_cross_origin", "method": method,
                           "url": _safe_url(request.url)})
            return route.abort("blockedbyclient")
        return route.continue_()

    page.on("console", console_message)
    page.on("pageerror", page_error)
    page.on("requestfailed", request_failed)
    page.route("**/*", block_non_get)
    yield errors

    output = _output_dir()
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.nodeid).strip("_.")[:100] or "browser-test"
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
    playwright_output = output / "playwright"
    summary["screenshots"] = sorted(path.relative_to(output).as_posix()
                                    for path in playwright_output.rglob("*.png")) if playwright_output.exists() else []
    summary["traces"] = sorted(path.relative_to(output).as_posix()
                               for path in playwright_output.rglob("trace.zip")) if playwright_output.exists() else []
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
