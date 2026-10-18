# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_doorbell_runtime_wiring.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.0
# Purpose: Verify fail-closed composition into the Grace owner-session runtime
# Execution Model: Isolated configuration fakes; no PostgreSQL, browser or provider calls
# Authority: Synthetic identities only; never sends a live wake

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import unittest

from riverview_core.doorbell.runtime import (
    DoorbellRuntimeConfigurationError, OWNER_ID, create_configured_doorbell_worker,
)


PROVIDER_ID = "synthetic-chatgpt-provider"
TARGET_ID = "8af9333f-a59f-4a06-b572-e68b4d12b6c2"


@dataclass(frozen=True)
class Provider:
    provider_id: str = PROVIDER_ID


@dataclass(frozen=True)
class Router:
    providers: dict


@dataclass(frozen=True)
class Exchange:
    router: Router


@dataclass(frozen=True)
class Target:
    conversation_id: str = TARGET_ID


@dataclass(frozen=True)
class Claim:
    request_id: str = "d29d0112-9346-4d8a-879d-021af1a4d089"
    correlation_id: str = "ea24ed05-dc18-4a51-9904-ef96f2ac4840"
    provider_id: str = PROVIDER_ID
    attempt_id: str = "synthetic-attempt"
    lease_token: str = "synthetic-lease"
    fence: int = 1
    lease_until: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(seconds=120)
    )


class ExchangeWithClaim(Exchange):
    def __init__(self):
        super().__init__(Router({PROVIDER_ID: Provider()}))
        self.receipts = []

    def claim_next_doorbell_request(self, provider_id, owner_id, lease_seconds):
        self.claim_args = (provider_id, owner_id, lease_seconds)
        return Claim()

    def record_doorbell_receipt(self, *args):
        self.receipts.append(args)
        return "awaiting_external_claim"


class Bridge:
    def __init__(self):
        self.calls = []

    def ring(self, request, target):
        self.calls.append((request, target))
        return type("Wake", (), {"status": "succeeded", "failure_class": None})()


class CapturingFactory:
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return args


class DoorbellRuntimeWiringTests(unittest.TestCase):
    def setUp(self):
        self.exchange = Exchange(Router({PROVIDER_ID: Provider()}))

    def test_default_is_disabled_without_loading_target_or_creating_worker(self):
        loader = CapturingFactory()
        worker = CapturingFactory()
        result = create_configured_doorbell_worker({}, self.exchange,
            target_loader=loader, worker_factory=worker)
        self.assertIsNone(result)
        self.assertEqual(loader.calls, [])
        self.assertEqual(worker.calls, [])

    def test_enabled_worker_uses_registered_provider_and_existing_exact_target(self):
        worker = CapturingFactory()
        result = create_configured_doorbell_worker({
            "RIVERVIEW_CHATGPT_DOORBELL_ENABLED": "1",
            "RIVERVIEW_CHATGPT_DOORBELL_PROVIDER_ID": PROVIDER_ID,
        }, self.exchange, target_loader=lambda: Target(), bridge_factory=object,
            worker_factory=worker)
        self.assertIs(result, worker.calls[0])
        exchange, bridge, config = worker.calls[0]
        self.assertIs(exchange, self.exchange)
        self.assertIsInstance(bridge, object)
        self.assertEqual(config.provider_id, PROVIDER_ID)
        self.assertEqual(config.owner_id, OWNER_ID)
        self.assertEqual(config.designated_conversation_id, TARGET_ID)

    def test_invalid_flag_missing_provider_and_unregistered_provider_fail_closed(self):
        for environ in (
            {"RIVERVIEW_CHATGPT_DOORBELL_ENABLED": "yes"},
            {"RIVERVIEW_CHATGPT_DOORBELL_ENABLED": "1"},
            {"RIVERVIEW_CHATGPT_DOORBELL_ENABLED": "1",
             "RIVERVIEW_CHATGPT_DOORBELL_PROVIDER_ID": "not-registered"},
        ):
            with self.subTest(environ=environ):
                with self.assertRaises(DoorbellRuntimeConfigurationError):
                    create_configured_doorbell_worker(environ, self.exchange,
                        target_loader=lambda: Target())

    def test_enabled_worker_requires_configured_exchange(self):
        with self.assertRaisesRegex(DoorbellRuntimeConfigurationError,
                                    "doorbell_provider_not_registered"):
            create_configured_doorbell_worker({
                "RIVERVIEW_CHATGPT_DOORBELL_ENABLED": "1",
                "RIVERVIEW_CHATGPT_DOORBELL_PROVIDER_ID": PROVIDER_ID,
            }, None)

    def test_enabled_runtime_worker_runs_one_claim_and_records_one_receipt(self):
        exchange, bridge = ExchangeWithClaim(), Bridge()
        worker = create_configured_doorbell_worker({
            "RIVERVIEW_CHATGPT_DOORBELL_ENABLED": "1",
            "RIVERVIEW_CHATGPT_DOORBELL_PROVIDER_ID": PROVIDER_ID,
        }, exchange, target_loader=lambda: Target(), bridge_factory=lambda: bridge)
        result = worker.run_once()
        self.assertEqual((result.status, result.outcome, result.receipt_recorded),
                         ("recorded", "submitted", True))
        self.assertEqual(exchange.claim_args, (PROVIDER_ID, OWNER_ID, 90))
        self.assertEqual(bridge.calls[0][1], TARGET_ID)
        self.assertEqual(len(exchange.receipts), 1)
        self.assertEqual(exchange.receipts[0][3], OWNER_ID)


if __name__ == "__main__":
    unittest.main()
