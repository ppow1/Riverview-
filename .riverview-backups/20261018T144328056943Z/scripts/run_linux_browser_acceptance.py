# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_linux_browser_acceptance.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Run bounded, read-only browser smoke checks with private evidence output
# Execution Model: Request-driven local test runner
# Observability: Pytest summary, sanitized error JSON, screenshots, failure traces
# Dependencies: Python 3.10+, .venv with browser-tests/requirements.txt, Chromium
# Authority: Loopback target by default; remote targets require explicit read-only opt-in
# Changed: 2026-10-18 UTC | RV-LINUX-BROWSER-ACCEPTANCE-001 | Add Linux Playwright runner
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: tests/test_linux_browser_runner.py; tests/browser/test_read_only_smoke.py
# History: Git
# =============================================================================
"""Run the Linux Chromium browser acceptance smoke test."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from urllib.parse import urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8766"


def validate_target(base_url: str, allow_remote: bool) -> tuple[str, str]:
    """Return a sanitized origin and require explicit approval for non-loopback."""
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


def validate_smoke_path(path: str) -> str:
    if not path.startswith("/") or path.startswith("//") or "?" in path or "#" in path:
        raise ValueError("smoke_path_must_be_absolute_path_without_query_or_fragment")
    if "\\" in path or any(ord(char) < 32 for char in path):
        raise ValueError("smoke_path_invalid")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("RIVERVIEW_BROWSER_BASE_URL", DEFAULT_BASE_URL),
                        help="HTTP(S) origin; loopback only unless --allow-remote-readonly is supplied")
    parser.add_argument("--smoke-path", default="/", help="Read-only GET path under the selected origin")
    parser.add_argument("--expect-heading", help="Require this visible heading on the smoke page")
    parser.add_argument("--allow-remote-readonly", action="store_true",
                        help="Permit a non-loopback target; tests still block all non-GET requests")
    parser.add_argument("--output", type=Path,
                        help="New evidence directory (default: private user state directory)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        origin, host = validate_target(args.base_url, args.allow_remote_readonly)
        smoke_path = validate_smoke_path(args.smoke_path)
    except ValueError as error:
        print(f"browser_target_rejected: {error}", file=sys.stderr)
        return 2

    venv_python = ROOT / ".venv" / "bin" / "python"
    if not venv_python.is_file():
        print("browser_venv_missing: create .venv and install browser-tests/requirements.txt",
              file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or (Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
                             / "riverview/browser-acceptance" / f"{stamp}-{uuid4().hex[:8]}")
    output = output.expanduser().resolve()
    if output.exists():
        print("evidence_directory_must_not_exist", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.mkdir(mode=0o700)
    os.chmod(output, 0o700)
    playwright_output = output / "playwright"

    env = os.environ.copy()
    env["RIVERVIEW_BROWSER_OUTPUT_DIR"] = str(output)
    env["RIVERVIEW_BROWSER_SMOKE_PATH"] = smoke_path
    env["RIVERVIEW_BROWSER_TARGET_ORIGIN"] = origin
    if args.expect_heading:
        env["RIVERVIEW_BROWSER_EXPECT_HEADING"] = args.expect_heading
    else:
        env.pop("RIVERVIEW_BROWSER_EXPECT_HEADING", None)

    command = [str(venv_python), "-m", "pytest", "-q", "tests/browser",
               "--browser", "chromium", "--base-url", origin,
               "--output", str(playwright_output), "--tracing", "retain-on-failure",
               "--screenshot", "on", "--full-page-screenshot"]
    summary = {
        "schema": "riverview.linux-browser-acceptance-run.v1",
        "target_origin": origin,
        "target_host": host,
        "smoke_path": smoke_path,
        "http_methods_allowed": ["GET"],
        "browser": "Playwright Chromium headless",
        "command": shlex.join(command),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "evidence_directory": str(output),
    }
    (output / "run-start.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    os.chmod(output / "run-start.json", 0o600)
    print(f"browser_acceptance_target={origin}{smoke_path}")
    print(f"browser_acceptance_evidence={output}")
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    summary["completed_at"] = datetime.now(timezone.utc).isoformat()
    summary["exit_code"] = result.returncode
    summary["status"] = "PASS" if result.returncode == 0 else "FAIL"
    summary_path = output / "runner-result.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    os.chmod(summary_path, 0o600)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
