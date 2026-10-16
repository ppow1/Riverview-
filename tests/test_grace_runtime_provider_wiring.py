# Riverview~ controlled test
# File: tests/test_grace_runtime_provider_wiring.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.7
# Purpose: Verify persistent Grace reasoning follows the authorized office binding
# Execution Model: Deterministic provider factory; no database or inference service
# Observability: Assert provider identities and router model digest
# Authority: This test does not provision grants or change bindings
# Changed: 2026-10-15 UTC | RV-GRACE-PROPOSAL-TIMEOUT-001 | Verify the 80B proposal client uses the shared bounded timeout
# Changed: 2026-10-16 UTC | RV-GRACE-RECOVERY-HOOK-001 | Verify persistent-service startup invokes the current bounded Codex recovery hook
# Changed: 2026-10-16 UTC | RV-GRACE-OWNER-CODEX-HOME-001 | Reproduce service HOME versus configured CODEX_HOME and fail closed on path escape
# Changed: 2026-10-16 UTC | RV-GRACE-SCOPE-LEASE-RECONCILE-001 | Require authenticated-scope context for startup recovery
# Changed: 2026-10-16 UTC | RV-GRACE-RESULT-RETURN-DIAGNOSTICS-001 | Require default 512-token review budget and reject invalid overrides
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Parse an explicit owner-configured source-change path ceiling fail-closed
# Changed: 2026-10-16 UTC | RV-PR62-SOURCE-CHANGE-MODE | Reproduce source-change mode being rejected before adapter setup
"""Tests for the persistent executor's model-provider wiring."""

import unittest

from scripts.run_grace_execution_service import (
    configured_resident_providers, is_codex_adapter_mode, persistent_owner_codex_home,
    reconcile_codex_startup_recovery, resident_result_review_tokens,
    source_change_path_allowlist,
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
    def test_source_change_mode_enters_registered_codex_adapter_path(self):
        self.assertTrue(is_codex_adapter_mode("codex-cli"))
        self.assertTrue(is_codex_adapter_mode("codex-source-change"))
        self.assertFalse(is_codex_adapter_mode("bounded-artifact"))
        self.assertFalse(is_codex_adapter_mode("unexpected"))

    def test_result_review_budget_defaults_to_512_and_rejects_out_of_bounds(self):
        self.assertEqual(resident_result_review_tokens({}), 512)
        self.assertEqual(resident_result_review_tokens({
            "RIVERVIEW_GRACE_RESULT_REVIEW_TOKENS": "256"}), 256)
        for invalid in ("15", "513", "invalid"):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(WorkerServiceConfigurationError,
                        "resident_result_review_tokens_invalid"):
                    resident_result_review_tokens({
                        "RIVERVIEW_GRACE_RESULT_REVIEW_TOKENS": invalid})

    def test_owner_session_uses_explicit_service_codex_home_not_home_dot_codex(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            codex_home = state / "codex-home"
            codex_home.mkdir(parents=True)
            configured = persistent_owner_codex_home({
                "HOME": str(state),
                "RIVERVIEW_CODEX_HOME": str(codex_home),
            }, state)
            self.assertEqual(configured, str(codex_home))
            self.assertNotEqual(configured, str(state / ".codex"))

    def test_owner_session_rejects_codex_home_outside_service_state(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            state.mkdir()
            outside = Path(temporary) / "personal-codex"
            with self.assertRaisesRegex(WorkerServiceConfigurationError,
                                        "codex_service_home_outside_state_directory"):
                persistent_owner_codex_home({"RIVERVIEW_CODEX_HOME": str(outside)}, state)

    def test_source_change_runtime_ceiling_is_explicit_and_bounded(self):
        self.assertEqual(source_change_path_allowlist({
            "RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS":
                '["src/a.py","tests/test_a.py"]'}),
            ("src/a.py", "tests/test_a.py"))
        for raw in (None, "not-json", "{}", "[]", '["src/../outside"]',
                    '["src/a.py","src/a.py"]'):
            env = {} if raw is None else {"RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS": raw}
            with self.subTest(raw=raw), self.assertRaisesRegex(
                    WorkerServiceConfigurationError, "source_change_allowlist_invalid"):
                source_change_path_allowlist(env)

    def test_startup_recovery_uses_current_retryable_codex_hook(self):
        recovery = object()

        class Action:
            def __init__(self):
                self.received = None

            def reconcile_retryable_no_artifact_failures(self, supplied, *, scope_ref, worker_id):
                self.received = (supplied, scope_ref, worker_id)
                return [{"decision": "retry_safe"}]

        action = Action()
        self.assertEqual(reconcile_codex_startup_recovery(
            action, recovery, scope_ref="work-order:test", worker_id="worker:test"),
                         [{"decision": "retry_safe"}])
        self.assertEqual(action.received, (recovery, "work-order:test", "worker:test"))

    def test_startup_recovery_fails_closed_when_hook_is_missing(self):
        with self.assertRaisesRegex(WorkerServiceConfigurationError,
                                    "codex_recovery_hook_unavailable"):
            reconcile_codex_startup_recovery(object(), object(),
                scope_ref="work-order:test", worker_id="worker:test")

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
