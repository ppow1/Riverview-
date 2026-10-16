# Riverview~ controlled test
# File: tests/test_grace_runtime_provider_wiring.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.2
# Purpose: Verify persistent Grace reasoning follows the authorized office binding
# Execution Model: Deterministic provider factory; no database or inference service
# Observability: Assert provider identities and router model digest
# Authority: This test does not provision grants or change bindings
# Changed: 2026-10-15 UTC | RV-GRACE-PROPOSAL-TIMEOUT-001 | Verify the 80B proposal client uses the shared bounded timeout
# Changed: 2026-10-16 UTC | RV-GRACE-RECOVERY-HOOK-001 | Verify persistent-service startup invokes the current bounded Codex recovery hook
"""Tests for the persistent executor's model-provider wiring."""

import unittest

from scripts.run_grace_execution_service import (
    configured_resident_providers, reconcile_codex_startup_recovery,
)
from riverview_core.local_reasoning_provider import LocalReasoningProvider
from riverview_core.resident_execution.model_router import GraceModelRouter
from riverview_core.worker_adapter.service import WorkerServiceConfigurationError


class FakeProvider:
    provider_id = "local.inference.v1"

    def __init__(self, endpoint, model, digest, **_kwargs):
        self.endpoint = endpoint
        self.model = model
        self.model_sha256 = digest
        self.kwargs = _kwargs


def make_router(environ):
    autonomic = FakeProvider(environ["RIVERVIEW_REASONING_ENDPOINT"],
        environ["RIVERVIEW_REASONING_MODEL"],
        environ["RIVERVIEW_REASONING_MODEL_SHA256"])
    model_map = LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS
    vision_endpoint, vision_model = next(
        (url, model) for url, model in model_map.items() if "30B" in model)
    reasoning_endpoint, reasoning_model = next(
        (url, model) for url, model in model_map.items() if "80B" in model)
    vision = FakeProvider(vision_endpoint, vision_model,
        environ["RIVERVIEW_GRACE_30B_MODEL_SHA256"])
    reasoning = FakeProvider(reasoning_endpoint, reasoning_model,
        environ["RIVERVIEW_GRACE_80B_MODEL_SHA256"])
    return GraceModelRouter(autonomic=autonomic, vision=vision, reasoning=reasoning)


class GraceRuntimeProviderWiringTests(unittest.TestCase):
    def test_startup_recovery_uses_current_retryable_codex_hook(self):
        recovery = object()

        class Action:
            def __init__(self):
                self.received = None

            def reconcile_retryable_no_artifact_failures(self, supplied):
                self.received = supplied
                return [{"decision": "retry_safe"}]

        action = Action()
        self.assertEqual(reconcile_codex_startup_recovery(action, recovery),
                         [{"decision": "retry_safe"}])
        self.assertIs(action.received, recovery)

    def test_startup_recovery_fails_closed_when_hook_is_missing(self):
        with self.assertRaisesRegex(WorkerServiceConfigurationError,
                                    "codex_recovery_hook_unavailable"):
            reconcile_codex_startup_recovery(object(), object())

    def setUp(self):
        self.env = {
            "RIVERVIEW_REASONING_ENDPOINT": "http://127.0.0.1:18796/v1",
            "RIVERVIEW_REASONING_MODEL": "qwen3-0.6b-q8_0-local",
            "RIVERVIEW_REASONING_MODEL_SHA256": "a" * 64,
            "RIVERVIEW_GRACE_ALLOW_APPROVED_OCTO1": "1",
            "RIVERVIEW_GRACE_ENABLE_MODEL_ROUTER": "1",
            "RIVERVIEW_GRACE_30B_MODEL_SHA256": "b" * 64,
            "RIVERVIEW_GRACE_80B_MODEL_SHA256": "c" * 64,
        }

    def test_router_binding_builds_one_router_provider_with_matching_digest(self):
        router = make_router(self.env)
        providers, model = configured_resident_providers({
            "provider_ref": router.provider_id,
            "implementation_revision": router.model_sha256,
        }, self.env, FakeProvider)
        self.assertEqual(tuple(providers), (router.provider_id,))
        self.assertEqual(providers[router.provider_id].model_sha256, router.model_sha256)
        self.assertEqual(model, router.providers["reasoning"].model)
        self.assertEqual(providers[router.provider_id].providers["reasoning"].kwargs["timeout_seconds"], 60)

    def test_reasoning_timeout_is_shared_and_bounded(self):
        from scripts.run_grace_execution_service import resident_reasoning_timeout
        self.assertEqual(resident_reasoning_timeout({"RIVERVIEW_RESIDENT_REASONING_TIMEOUT": "45"}), 45)
        with self.assertRaises(WorkerServiceConfigurationError):
            resident_reasoning_timeout({"RIVERVIEW_RESIDENT_REASONING_TIMEOUT": "60.1"})
        with self.assertRaises(WorkerServiceConfigurationError):
            resident_reasoning_timeout({"RIVERVIEW_RESIDENT_REASONING_TIMEOUT": "invalid"})

    def test_direct_binding_still_uses_existing_local_provider(self):
        providers, model = configured_resident_providers({
            "provider_ref": "local.inference.v1",
            "implementation_revision": "a" * 64,
        }, self.env, FakeProvider)
        self.assertEqual(tuple(providers), ("local.inference.v1",))
        self.assertEqual(model, "qwen3-0.6b-q8_0-local")

    def test_router_binding_requires_explicit_private_lan_opt_in(self):
        router = make_router(self.env)
        env = {**self.env, "RIVERVIEW_GRACE_ALLOW_APPROVED_OCTO1": "0"}
        with self.assertRaises(WorkerServiceConfigurationError):
            configured_resident_providers({"provider_ref": router.provider_id,
                "implementation_revision": router.model_sha256}, env, FakeProvider)

    def test_binding_digest_mismatch_fails_closed(self):
        router = make_router(self.env)
        with self.assertRaises(WorkerServiceConfigurationError):
            configured_resident_providers({"provider_ref": router.provider_id,
                "implementation_revision": "d" * 64}, self.env, FakeProvider)


if __name__ == "__main__":
    unittest.main()
