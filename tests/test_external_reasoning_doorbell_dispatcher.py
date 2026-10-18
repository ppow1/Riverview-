# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_external_reasoning_doorbell_dispatcher.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.0
# Purpose: Verify the durable exchange to fixed browser wake adapter
# Execution Model: Isolated fake exchange and bridge; no browser or provider access
# Authority: Synthetic identities only; never sends a live wake

from dataclasses import dataclass
from uuid import UUID

import pytest

from riverview_core.doorbell.dispatcher import DoorbellWakeWorker, DoorbellWorkerConfig


REQUEST_ID = "d29d0112-9346-4d8a-879d-021af1a4d089"
CORRELATION_ID = "ea24ed05-dc18-4a51-9904-ef96f2ac4840"
CONVERSATION_ID = "8af9333f-a59f-4a06-b572-e68b4d12b6c2"
PROVIDER_ID = "synthetic-chatgpt-provider"
OWNER_ID = "test-doorbell-worker"


@dataclass(frozen=True)
class Claim:
    request_id: str = REQUEST_ID
    correlation_id: str = CORRELATION_ID
    provider_id: str = PROVIDER_ID
    attempt_id: str = "attempt-1"
    lease_token: str = "opaque-test-lease"
    fence: int = 1


@dataclass(frozen=True)
class WakeResult:
    status: str
    failure_class: str | None = None


class FakeExchange:
    def __init__(self, claim=Claim(), *, receipt_error=False):
        self.claim = claim
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


def test_success_uses_exact_claim_lineage_fixed_target_and_metadata_receipt():
    exchange = FakeExchange()
    bridge = FakeBridge()
    worker, _, _ = make_worker(exchange, bridge)

    result = worker.run_once()

    assert result.status == "recorded"
    assert result.trigger_status == "ready"
    assert result.outcome == "submitted"
    assert result.receipt_recorded is True
    assert exchange.claim_calls == [(PROVIDER_ID, OWNER_ID, 30)]
    request, target = bridge.calls[0]
    assert request.request_id == UUID(REQUEST_ID)
    assert request.correlation_id == UUID(CORRELATION_ID)
    assert target == CONVERSATION_ID
    assert len(exchange.receipts) == 1
    assert exchange.receipts[0] == (
        REQUEST_ID, CORRELATION_ID, PROVIDER_ID, OWNER_ID, "attempt-1",
        "opaque-test-lease", 1, "submitted", None,
    )


def test_no_eligible_request_does_not_call_browser_or_write_receipt():
    worker, exchange, bridge = make_worker(FakeExchange(claim=None))
    result = worker.run_once()
    assert result.status == "idle"
    assert result.trigger_status == "ready"
    assert not bridge.calls
    assert not exchange.receipts


def test_bridge_replay_of_prior_verified_success_records_submitted_idempotently():
    worker, exchange, bridge = make_worker(bridge=FakeBridge(WakeResult("already_succeeded")))
    result = worker.run_once()
    assert result.outcome == "submitted"
    assert result.trigger_status == "ready"
    assert exchange.receipts[0][-2:] == ("submitted", None)
    assert len(bridge.calls) == 1


def test_claim_is_provider_fenced_and_invalid_provider_never_rings():
    claim = Claim(provider_id="different-provider")
    worker, exchange, bridge = make_worker(FakeExchange(claim=claim))
    result = worker.run_once()
    assert result.status == "invalid_claim"
    assert result.trigger_status == "blocked"
    assert result.safe_error_code == "claim_metadata_invalid"
    assert not bridge.calls
    assert not exchange.receipts


@pytest.mark.parametrize("failure_class", [
    "RIV-PLY-0007", "RIV-PLY-0013", "RIV-PLY-0015",
])
def test_known_pre_send_failures_are_reported_safely_for_exchange_backoff(failure_class):
    worker, exchange, bridge = make_worker(
        bridge=FakeBridge(WakeResult("failed", failure_class))
    )
    result = worker.run_once()
    assert result.outcome == "failed"
    assert result.safe_error_code == failure_class
    assert exchange.receipts[0][-2:] == ("failed", failure_class)
    assert len(bridge.calls) == 1


@pytest.mark.parametrize("failure_class", [
    "RIV-PLY-0003", "RIV-PLY-0004", "RIV-PLY-0009", "RIV-PLY-0014", "untrusted details/token",
])
def test_uncertain_or_unrecognized_results_are_ambiguous_and_never_auto_retried(failure_class):
    worker, exchange, _ = make_worker(
        bridge=FakeBridge(WakeResult("failed", failure_class))
    )
    result = worker.run_once()
    expected = failure_class if failure_class.startswith("RIV-PLY-") else "doorbell_failure"
    assert result.outcome == "ambiguous"
    assert result.trigger_status == "blocked"
    assert result.safe_error_code == expected
    assert exchange.receipts[0][-2:] == ("ambiguous", expected)


def test_unexpected_bridge_exception_is_redacted_and_durably_marked_ambiguous():
    worker, exchange, _ = make_worker(
        bridge=FakeBridge(error=RuntimeError("private proposal text and token"))
    )
    result = worker.run_once()
    assert result.outcome == "ambiguous"
    assert result.safe_error_code == "doorbell_exception"
    assert "private" not in repr(result)
    assert exchange.receipts[0][-2:] == ("ambiguous", "doorbell_exception")


def test_claim_payload_is_never_forwarded_to_browser_or_result():
    claim = {
        **Claim().__dict__,
        "request_payload": {"proposal": "private synthetic body"},
        "review_subject": {"proposal": "private subject"},
    }
    exchange = FakeExchange(claim=claim)
    bridge = FakeBridge()
    worker, _, _ = make_worker(exchange, bridge)
    result = worker.run_once()
    assert result.status == "recorded"
    assert "private synthetic" not in repr(bridge.calls)
    assert "private synthetic" not in repr(result)


def test_claim_once_then_idle_prevents_duplicate_wake_in_sequential_replay():
    worker, exchange, bridge = make_worker()
    first = worker.run_once()
    second = worker.run_once()
    assert first.outcome == "submitted"
    assert second.status == "idle"
    assert len(bridge.calls) == 1
    assert len(exchange.receipts) == 1


def test_receipt_write_failure_is_reported_without_exposing_database_exception():
    worker, _, _ = make_worker(FakeExchange(receipt_error=True))
    result = worker.run_once()
    assert result.status == "receipt_unavailable"
    assert result.trigger_status == "unavailable"
    assert result.receipt_recorded is False
    assert result.safe_error_code == "receipt_write_failed"
    assert "private details" not in repr(result)


@pytest.mark.parametrize("kwargs", [
    {"provider_id": "", "owner_id": OWNER_ID, "designated_conversation_id": CONVERSATION_ID},
    {"provider_id": PROVIDER_ID, "owner_id": "", "designated_conversation_id": CONVERSATION_ID},
    {"provider_id": PROVIDER_ID, "owner_id": OWNER_ID, "designated_conversation_id": "not-a-uuid"},
    {"provider_id": PROVIDER_ID, "owner_id": OWNER_ID, "designated_conversation_id": CONVERSATION_ID,
     "lease_seconds": True},
])
def test_worker_configuration_fails_closed(kwargs):
    with pytest.raises(ValueError):
        DoorbellWorkerConfig(**kwargs)
