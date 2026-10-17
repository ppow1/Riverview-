# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/doorbell/config.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.0
# Purpose: Store the single exact ChatGPT target and local browser executable
# Execution Model: Request-driven configuration library
# Observability: Stable failure classes; config values are not emitted
# Dependencies: Python standard library; Riverview-owned user profile
# Authority: One configured conversation and localhost CDP port only
# Changed: 2026-10-17 UTC | RV-C3-DOORBELL-001 | Add Ubuntu and XDG runtime paths
# Contracts: docs/components/CHATGPT_DOORBELL.md
# Tests: tests/test_chatgpt_doorbell.py
# History: Git and .riverview-revisions.json

"""Linux user-session configuration for the bounded ChatGPT doorbell."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path

CHATGPT_CONVERSATION_ID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _xdg_path(variable: str, fallback: str) -> Path:
    value = os.environ.get(variable)
    return Path(value).expanduser() if value else Path.home() / fallback


CONFIG_PATH = Path(
    os.environ.get(
        "RIVERVIEW_DOORBELL_CONFIG",
        _xdg_path("XDG_CONFIG_HOME", ".config") / "riverview" / "doorbell.json",
    )
).expanduser()
PROFILE_PATH = Path(
    os.environ.get(
        "RIVERVIEW_BROWSER_PROFILE",
        _xdg_path("XDG_DATA_HOME", ".local/share") / "riverview" / "browser" / "profile",
    )
).expanduser()
RUNTIME_ROOT = Path(
    os.environ.get(
        "RIVERVIEW_RUNTIME_ROOT",
        _xdg_path("XDG_STATE_HOME", ".local/state") / "riverview",
    )
).expanduser()


@dataclass(frozen=True, slots=True)
class DoorbellRuntimeConfig:
    conversation_id: str
    browser_executable: Path
    cdp_port: int = 9225
    adapter_version: str = "1.0.0"


def discover_browser_executable() -> Path:
    """Find an installed Linux Chrome/Chromium binary without starting it."""
    for command in (
        "google-chrome-stable",
        "google-chrome",
        "chromium",
        "chromium-browser",
    ):
        found = shutil.which(command)
        if found:
            candidate = Path(found).resolve()
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
    raise ValueError("RIV-PLY-0013: no supported local Chromium executable was found.")


def load_config(path: Path = CONFIG_PATH) -> DoorbellRuntimeConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("RIV-PLY-0010: Riverview doorbell configuration is unavailable.") from exc
    if not isinstance(raw, dict) or set(raw) != {
        "conversation_id", "browser_executable", "cdp_port", "adapter_version"
    }:
        raise ValueError("RIV-PLY-0011: configuration contains unsupported or missing fields.")
    conversation_id = raw["conversation_id"]
    executable = Path(str(raw["browser_executable"])).expanduser()
    port = raw["cdp_port"]
    if (
        not isinstance(conversation_id, str)
        or not CHATGPT_CONVERSATION_ID.fullmatch(conversation_id)
        or not executable.is_absolute()
    ):
        raise ValueError("RIV-PLY-0011: configuration target or executable is invalid.")
    if not isinstance(port, int) or isinstance(port, bool) or not 9225 <= port <= 9325:
        raise ValueError("RIV-PLY-0011: CDP port is outside the Riverview localhost range.")
    adapter_version = raw["adapter_version"]
    if not isinstance(adapter_version, str) or not adapter_version.strip():
        raise ValueError("RIV-PLY-0011: adapter version is invalid.")
    return DoorbellRuntimeConfig(conversation_id.lower(), executable, port, adapter_version)


def bootstrap_config(
    conversation_id: str,
    browser_executable: str | None = None,
    path: Path = CONFIG_PATH,
    *,
    replace: bool = False,
) -> Path:
    """Create the private config; changing a binding requires an explicit replace."""
    if not isinstance(conversation_id, str) or not CHATGPT_CONVERSATION_ID.fullmatch(conversation_id):
        raise ValueError("RIV-PLY-0011: conversation ID must match the configured target format.")
    executable = Path(browser_executable).expanduser() if browser_executable else discover_browser_executable()
    if not executable.is_absolute():
        raise ValueError("RIV-PLY-0011: browser executable must be an absolute local path.")
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError("RIV-PLY-0013: configured browser executable is unavailable.")
    path = Path(path).expanduser()
    if path.exists() and not replace:
        raise FileExistsError("RIV-PLY-0016: existing target binding was preserved; use explicit replace after verification.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    payload = {
        "conversation_id": conversation_id.lower(),
        "browser_executable": str(executable.resolve()),
        "cdp_port": 9225,
        "adapter_version": "1.0.0",
    }
    temporary = path.with_suffix(".tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path
