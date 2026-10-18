# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/grace_staging_browser.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.0
# Purpose: Fail closed on staging origin and browser-state scope for read-only Grace acceptance
# Execution Model: Request-driven validation library
# Observability: Stable validation error codes; never emits credential or account data
# Dependencies: Python standard library; browser runner target validator
# Authority: No authorization is granted; exact pre-existing staging session is required
# Changed: 2026-10-18 UTC | RV-C2-STAGING-GRACE-BROWSER-003 | Add staging origin and state checks
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: tests/test_linux_browser_runner.py
# History: Git
# =============================================================================
"""Validation helpers for the opt-in, read-only Grace staging browser test."""

from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import stat
from urllib.parse import urlsplit
from uuid import UUID

STAGING_CONFIRMATION = "I_CONFIRM_DISPOSABLE_GRACE_STAGING"


def validate_target(base_url: str, allow_remote: bool) -> tuple[str, str]:
    """Return a sanitized HTTP(S) origin and require explicit remote opt-in."""
    parsed = urlsplit(base_url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
        raise ValueError("target_must_be_http_origin_without_credentials_path_or_query")
    host = parsed.hostname.rstrip(".").lower()
    is_loopback = host == "localhost"
    try:
        is_loopback = is_loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if not is_loopback and not allow_remote:
        raise ValueError("non_loopback_target_requires_readonly_opt_in")
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("target_port_invalid") from None
    origin_host = f"[{host}]" if ":" in host else host
    origin = f"{parsed.scheme}://{origin_host}" + (f":{port}" if port else "")
    return origin, host


def validate_storage_state(path_value: str, *, expected_host: str) -> Path:
    """Require a private cookie-only Playwright state scoped to one exact host."""
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        raise ValueError("staging_storage_state_must_be_absolute")
    try:
        info = path.lstat()
    except OSError:
        raise ValueError("staging_storage_state_unavailable") from None
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid() or info.st_mode & 0o077
            or info.st_size < 2 or info.st_size > 1_048_576):
        raise ValueError("staging_storage_state_permissions_or_type_invalid")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("staging_storage_state_invalid_json") from None
    if not isinstance(state, dict) or not isinstance(state.get("cookies"), list):
        raise ValueError("staging_storage_state_cookies_required")
    if state.get("origins") not in (None, []):
        raise ValueError("staging_storage_state_local_storage_forbidden")
    if not state["cookies"]:
        raise ValueError("staging_storage_state_cookies_required")
    host = expected_host.rstrip(".").lower()
    for cookie in state["cookies"]:
        domain = cookie.get("domain") if isinstance(cookie, dict) else None
        if not isinstance(domain, str) or domain.lstrip(".").rstrip(".").lower() != host:
            raise ValueError("staging_storage_state_cookie_host_mismatch")
    return path


def validate_grace_staging_config(
    *,
    base_url: str,
    configured_origin: str,
    storage_state: str,
    test_account_label: str,
    conversation_id: str,
    seed_message_text: str,
    confirmation: str,
    allow_remote: bool,
) -> tuple[str, str, Path]:
    """Require a staging-named HTTPS origin (or confirmed disposable loopback) and scoped state."""
    origin, host = validate_target(base_url, allow_remote=allow_remote)
    if not configured_origin:
        raise ValueError("staging_origin_required")
    configured, _ = validate_target(configured_origin, allow_remote=True)
    if origin != configured:
        raise ValueError("staging_origin_mismatch")
    parsed = urlsplit(origin)
    is_loopback = host == "localhost"
    try:
        is_loopback = is_loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if is_loopback:
        if confirmation != STAGING_CONFIRMATION:
            raise ValueError("loopback_requires_disposable_staging_confirmation")
    else:
        if parsed.scheme != "https" or not (
            host.endswith(".test") or any(
                label == "staging" or label.endswith("-staging")
                for label in host.split(".")
            )
        ):
            raise ValueError("remote_target_must_be_https_staging_host")
        if not allow_remote:
            raise ValueError("remote_staging_requires_explicit_opt_in")
    if not test_account_label.strip():
        raise ValueError("staging_test_account_label_required")
    if not seed_message_text.strip() or len(seed_message_text) > 500:
        raise ValueError("staging_seed_message_text_required")
    try:
        UUID(conversation_id)
    except (ValueError, AttributeError):
        raise ValueError("staging_seed_conversation_uuid_required") from None
    state_path = validate_storage_state(storage_state, expected_host=host)
    return origin, host, state_path
