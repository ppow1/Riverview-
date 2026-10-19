# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_external_reasoning_doorbell_dispatcher.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.4
# Changed: 2026-10-18 UTC | RV-C2-DOORBELL-INTEGRATED-CI-FIX | Construct bounded fake claims per exchange so full-suite runtime cannot expire their lease before test use.
# Purpose: Verify the durable exchange to fixed browser wake adapter
# Execution Model: Isolated fake exchange and bridge; no browser or provider access
# Authority: Synthetic identities only; never sends a live wake

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import unittest
from uuid import UUID

from riverview_core.doorbell.dispatcher import DoorbellWakeWorker, DoorbellWorkerConfig


REQUEST_ID = "d29d0112-9346-4d8a-879d-021af1a4d089"
CORRELATION_ID = "ea24ed05-dc18-4a51-9904-ef96f2ac4840"
CONVERSATION_ID = "8af9333f-a59f-4a06-b572-e68b4d12b6c2"
PROVIDER_ID = "synthetic-chatgpt-provider"
OWNER_ID = "test-doorbell-worker"
_DEFAULT_CLAIM = object()


@dataclass(frozen=True)
class Claim:
    request_id: str = REQUEST_ID
    correlation_id: str = CORRELATION_ID
    provider_id: str = PROVIDER_ID
    attempt_id: str = "attempt-1"
    lease_token: str = "opaque-test-lease"
    fence: int = 1
    lease_until: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(seconds=80)
    )


@dataclass(frozen=True)
class WakeResult:
    status: str
    failure_class: str | None = None


class FakeExchange:
    def __init__(self, claim=_DEFAULT_CLAIM, *, receipt_error=False):
        # Claims carry a short lease; construct the default at exchange creation,
        # not module import, so a long full-suite run cannot age it before use.
        self.claim = Claim() if claim is _DEFAULT_CLAIM else claim
        self.receipt_error = receipt_error
        self.claim_calls = []
        self.receipts = []

    def claim_next_doorbell_request(self, provider_id, owner_id, lease_seconds):
        self.claim_calls.append((provider_id, owner_id, lease_seconds))
        result, self.claim = self.claim, None
        return result

    def record_doorbell_receipt(self, *args):
        if self.receipt_error:
            raise RuntimeError("synthetic database exception containing private details")
        self.receipts.append(args)


class FakeBridge:
    def __init__(self, result=WakeResult("succeeded"), *, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def ring(self, request, designated_conversation_id):
        self.calls.append((request, designated_conversation_id))
        if self.error:
            raise self.error
        return self.result


def make_worker(exchange=None, bridge=None):
    exchange = exchange or FakeExchange()
    bridge = bridge or FakeBridge()
    config = DoorbellWorkerConfig(PROVIDER_ID, OWNER_ID, CONVERSATION_ID)
    return DoorbellWakeWorker(exchange, bridge, config), exchange, bridge


class DoorbellDispatcherTests(unittest.TestCase):
    def test_success_uses_exact_claim_lineage_fixed_target_and_metadata_receipt(self):
        exchange, bridge = FakeExchange(), FakeBridge()
        worker, _, _ = make_worker(exchange, bridge)
        result = worker.run_once()

        self.assertEqual(result.status, "recorded")
        self.assertEqual(result.trigger_status, "ready")
        self.assertEqual(result.outcome, "submitted")
        self.assertTrue(result.receipt_recorded)
        self.assertEqual(exchange.claim_calls, [(PROVIDER_ID, OWNER_ID, 90)])
        request, target = bridge.calls[0]
        self.assertEqual(request.request_id, UUID(REQUEST_ID))
        self.assertEqual(request.correlation_id, UUID(CORRELATION_ID))
        self.assertEqual(target, CONVERSATION_ID)
        self.assertEqual(exchange.receipts, [(
            REQUEST_ID, CORRELATION_ID, PROVIDER_ID, OWNER_ID, "attempt-1",
            "opaque-test-lease", 1, "submitted", None,
        )])

    def test_no_eligible_request_does_not_call_browser_or_write_receipt(self):
        worker, exchange, bridge = make_worker(FakeExchange(claim=None))
        result = worker.run_once()
        self.assertEqual((result.status, result.trigger_status), ("idle", "ready"))
        self.assertFalse(bridge.calls)
        self.assertFalse(exchange.receipts)

    def test_bridge_replay_of_prior_verified_success_records_submitted_idempotently(self):
        worker, exchange, bridge = make_worker(bridge=FakeBridge(WakeResult("already_succeeded")))
        result = worker.run_once()
        self.assertEqual((result.outcome, result.trigger_status), ("submitted", "ready"))
        self.assertEqual(exchange.receipts[0][-2:], ("submitted", None))
        self.assertEqual(len(bridge.calls), 1)

    def test_claim_is_provider_fenced_and_invalid_provider_never_rings(self):
        worker, exchange, bridge = make_worker(FakeExchange(claim=Claim(provider_id="other")))
        result = worker.run_once()
        self.assertEqual((result.status, result.trigger_status), ("invalid_claim", "blocked"))
        self.assertEqual(result.safe_error_code, "claim_metadata_invalid")
        self.assertFalse(bridge.calls)
        self.assertFalse(exchange.receipts)

    def test_claim_with_expired_or_insufficient_lease_never_rings(self):
        for expiry in (
            datetime.now(timezone.utc) - timedelta(seconds=1),
            datetime.now(timezone.utc) + timedelta(seconds=20),
        ):
            with self.subTest(expiry=expiry):
                worker, exchange, bridge = make_worker(
                    FakeExchange(claim=Claim(lease_until=expiry))
                )
                result = worker.run_once()
                self.assertEqual(result.status, "invalid_claim")
                self.assertFalse(bridge.calls)
                self.assertFalse(exchange.receipts)

    def test_known_pre_send_failures_are_reported_for_bounded_exchange_backoff(self):
        for code in ("RIV-PLY-0007", "RIV-PLY-0013", "RIV-PLY-0015"):
            with self.subTest(code=code):
                worker, exchange, bridge = make_worker(
                    bridge=FakeBridge(WakeResult("failed", code))
                )
                result = worker.run_once()
                self.assertEqual(result.outcome, "failed")
                self.assertEqual(result.safe_error_code, code)
                self.assertEqual(exchange.receipts[0][-2:], ("failed", code))
                self.assertEqual(len(bridge.calls), 1)

    def test_uncertain_or_unrecognized_result_is_ambiguous_and_never_auto_retried(self):
        for code in (
            "RIV-PLY-0003", "RIV-PLY-0004", "RIV-PLY-0009", "RIV-PLY-0014",
            "untrusted details/token",
        ):
            with self.subTest(code=code):
                worker, exchange, _ = make_worker(
                    bridge=FakeBridge(WakeResult("failed", code))
                )
                result = worker.run_once()
                expected = code if code.startswith("RIV-PLY-") else "doorbell_failure"
                self.assertEqual(result.outcome, "ambiguous")
                self.assertEqual(result.trigger_status, "blocked")
                self.assertEqual(result.safe_error_code, expected)
                self.assertEqual(exchange.receipts[0][-2:], ("ambiguous", expected))

    def test_unexpected_bridge_exception_is_redacted_and_recorded_ambiguous(self):
        worker, exchange, _ = make_worker(
            bridge=FakeBridge(error=RuntimeError("private proposal text and token"))
        )
        result = worker.run_once()
        self.assertEqual(result.outcome, "ambiguous")
        self.assertEqual(result.safe_error_code, "doorbell_exception")
        self.assertNotIn("private", repr(result))
        self.assertEqual(exchange.receipts[0][-2:], ("ambiguous", "doorbell_exception"))

    def test_claim_payload_is_never_forwarded_to_browser_or_result(self):
        claim = {
            **Claim().__dict__,
            "request_payload": {"proposal": "private synthetic body"},
            "review_subject": {"proposal": "private subject"},
        }
        exchange, bridge = FakeExchange(claim=claim), FakeBridge()
        worker, _, _ = make_worker(exchange, bridge)
        result = worker.run_once()
        self.assertEqual(result.status, "recorded")
        self.assertNotIn("private synthetic", repr(bridge.calls))
        self.assertNotIn("private synthetic", repr(result))

    def test_claim_once_then_idle_prevents_sequential_duplicate_wake(self):
        worker, exchange, bridge = make_worker()
        first, second = worker.run_once(), worker.run_once()
        self.assertEqual(first.outcome, "submitted")
        self.assertEqual(second.status, "idle")
        self.assertEqual(len(bridge.calls), 1)
        self.assertEqual(len(exchange.receipts), 1)

    def test_receipt_write_failure_is_redacted_and_reported_unavailable(self):
        worker, _, _ = make_worker(FakeExchange(receipt_error=True))
        result = worker.run_once()
        self.assertEqual((result.status, result.trigger_status),
                         ("receipt_unavailable", "unavailable"))
        self.assertFalse(result.receipt_recorded)
        self.assertEqual(result.safe_error_code, "receipt_write_failed")
        self.assertNotIn("private details", repr(result))

    def test_worker_configuration_fails_closed(self):
        cases = (
            {"provider_id": "", "owner_id": OWNER_ID, "designated_conversation_id": CONVERSATION_ID},
            {"provider_id": PROVIDER_ID, "owner_id": "", "designated_conversation_id": CONVERSATION_ID},
            {"provider_id": PROVIDER_ID, "owner_id": OWNER_ID, "designated_conversation_id": "bad"},
            {"provider_id": PROVIDER_ID, "owner_id": OWNER_ID,
             "designated_conversation_id": CONVERSATION_ID, "lease_seconds": True},
            {"provider_id": PROVIDER_ID, "owner_id": OWNER_ID,
             "designated_conversation_id": CONVERSATION_ID, "lease_seconds": 60},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    DoorbellWorkerConfig(**kwargs)


if __name__ == "__main__":
    unittest.main()
