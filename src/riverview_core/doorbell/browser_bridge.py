# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/doorbell/browser_bridge.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.2
# Purpose: Pass durable mailbox identities to the fixed local CDP wake operation
# Inputs/Outputs: UUID request lineage, bounded timeout, designated target / metadata-only bridge result
# Execution Model: Request-driven adapter invoked by the Comms5-owned caller
# Observability: Bounded DoorbellResult with request/correlation IDs and safe evidence reference
# Dependencies: Python standard library; Node.js; tools/riverview_doorbell_bridge.cjs
# Authority: Does not create mailbox state, read page output, or expose browser controls
# Changed: 2026-10-18 UTC | RV-C3-DOORBELL-DOD-001 | Complete controlled header and status/recovery contract
# Contracts: docs/components/CHATGPT_DOORBELL.md
# Tests: tests/test_chatgpt_doorbell.py
# History: Git and .riverview-revisions.json

"""Narrow New-Core adapter for the Riverview-owned ChatGPT wake bridge."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from .config import CONFIG_PATH, load_config

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BRIDGE = REPOSITORY_ROOT / "tools" / "riverview_doorbell_bridge.cjs"
DESIGNATED_SELECTOR = "riverview-designated"
MAILBOX_RESOURCE = "riverview://mailbox"


@dataclass(frozen=True, slots=True)
class DoorbellRequest:
    request_id: UUID
    correlation_id: UUID
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, UUID) or not isinstance(self.correlation_id, UUID):
            raise ValueError("RIV-PLY-0002: request and correlation identities must be UUID values.")
        if isinstance(self.timeout_seconds, bool) or not 1 <= self.timeout_seconds <= 120:
            raise ValueError("RIV-PLY-0002: doorbell timeout is outside the bounded range.")


@dataclass(frozen=True, slots=True)
class DoorbellResult:
    request_id: UUID
    correlation_id: UUID
    status: str
    failure_class: str | None = None
    evidence_ref: str | None = None
    designated_target_ref: str | None = None


@dataclass(frozen=True, slots=True)
class BrowserBridgeRunner:
    """Invoke only the named fixed-wake operation for the configured target."""

    bridge_path: Path = DEFAULT_BRIDGE
    node_executable: str = "/usr/bin/node"
    config_path: Path = CONFIG_PATH
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None

    def ring(self, request: DoorbellRequest, designated_conversation_id: str) -> DoorbellResult:
        config = load_config(self.config_path)
        if config.conversation_id != str(designated_conversation_id).lower():
            raise ValueError("RIV-COMMS5-DOORBELL-001: local doorbell target differs from active Comms5 binding.")
        payload = {
            "operation": "ring_riverview_doorbell",
            "request_id": str(request.request_id),
            "correlation_id": str(request.correlation_id),
            "timeout_seconds": request.timeout_seconds,
        }
        run = self.runner or subprocess.run
        try:
            completed = run(
                [self.node_executable, str(self.bridge_path), "--ring"],
                input=json.dumps(payload), capture_output=True, text=True,
                timeout=request.timeout_seconds + 5, check=False,
            )
        except subprocess.TimeoutExpired:
            return DoorbellResult(request.request_id, request.correlation_id, "failed", "RIV-PLY-0009")
        except OSError:
            return DoorbellResult(request.request_id, request.correlation_id, "failed", "RIV-PLY-0015")
        try:
            result: Any = json.loads(completed.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            result = {"failure_class": "RIV-PLY-0003"}
        status = result.get("status")
        if (result.get("request_id") != str(request.request_id)
                or result.get("correlation_id") != str(request.correlation_id)):
            return DoorbellResult(request.request_id, request.correlation_id, "failed", "RIV-PLY-0014")
        if completed.returncode == 0 and status in {"succeeded", "already_succeeded"}:
            return DoorbellResult(
                request.request_id, request.correlation_id, "succeeded",
                evidence_ref=result.get("evidence_ref"),
                designated_target_ref=result.get("designated_target_ref"),
            )
        return DoorbellResult(
            request.request_id, request.correlation_id, "failed",
            failure_class=result.get("failure_class", "RIV-PLY-0003"),
        )
