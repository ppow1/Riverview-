# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/doorbell/runtime.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.0
# Purpose: Build the opt-in local doorbell worker from the approved exchange and target binding
# Execution Model: Runtime composition helper; no polling or external actions
# Observability: Configuration failures use stable codes; values are not logged
# Dependencies: Existing durable exchange, BrowserBridgeRunner, private target config
# Authority: Disabled by default; existing exchange lease and fixed browser binding remain authoritative
# Changed: 2026-10-18 UTC | RV-C2-DOORBELL-RUNTIME-WIRING-001 | Initial implementation
# Contracts: docs/components/CHATGPT_DOORBELL_DISPATCH.md
# Tests: tests/test_grace_doorbell_runtime_wiring.py
# History: New file; Git and .riverview-revisions.json

"""Fail-closed composition for the existing Grace owner-session doorbell hook."""

from __future__ import annotations

from collections.abc import Mapping

from .browser_bridge import BrowserBridgeRunner
from .config import load_config
from .dispatcher import DoorbellWakeWorker, DoorbellWorkerConfig

OWNER_ID = "service:grace-chatgpt-doorbell"


class DoorbellRuntimeConfigurationError(ValueError):
    """A stable, non-secret runtime composition failure."""


def create_configured_doorbell_worker(environ, exchange, *, target_loader=load_config,
                                      bridge_factory=BrowserBridgeRunner,
                                      worker_factory=DoorbellWakeWorker):
    """Return the opt-in worker, or None when the feature is explicitly/default disabled.

    Enabling this composition only registers a worker with Grace's existing owner loop.
    The exchange must already be configured with the provider and its existing authority;
    the fixed target is read from the existing private doorbell config. No credential or
    grant is created here.
    """
    enabled = environ.get("RIVERVIEW_CHATGPT_DOORBELL_ENABLED", "0")
    if enabled not in {"0", "1"}:
        raise DoorbellRuntimeConfigurationError("doorbell_enable_flag_invalid")
    if enabled == "0":
        return None
    provider_id = environ.get("RIVERVIEW_CHATGPT_DOORBELL_PROVIDER_ID", "")
    if not isinstance(provider_id, str) or not provider_id.strip() or len(provider_id) > 160:
        raise DoorbellRuntimeConfigurationError("doorbell_provider_id_required")
    providers = getattr(getattr(exchange, "router", None), "providers", None)
    if (exchange is None or not isinstance(providers, Mapping) or
            provider_id not in providers or
            getattr(providers[provider_id], "provider_id", None) != provider_id):
        raise DoorbellRuntimeConfigurationError("doorbell_provider_not_registered")
    try:
        target = target_loader()
        config = DoorbellWorkerConfig(
            provider_id=provider_id,
            owner_id=OWNER_ID,
            designated_conversation_id=target.conversation_id,
        )
        bridge = bridge_factory()
        return worker_factory(exchange, bridge, config)
    except DoorbellRuntimeConfigurationError:
        raise
    except Exception as exc:
        raise DoorbellRuntimeConfigurationError("doorbell_target_or_worker_invalid") from None


__all__ = ["DoorbellRuntimeConfigurationError", "OWNER_ID",
           "create_configured_doorbell_worker"]
