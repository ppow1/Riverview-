# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_w2_p0_review_recovery.py
# Component: W2-P0-REVIEW-RECOVERY
# Revision: 1.0.0
# Purpose: Independently exercise delayed provider reply, duplicate delivery, restart and Grace recovery
# Execution Model: Isolated PostgreSQL fixture and synthetic wake/provider only
# Observability: Correlation, durable exchange state, event count and idempotency assertions
# Dependencies: RIVERVIEW_TEST_PG_DSN; tests.test_external_reasoning_exchange fixture
# Authority: Uses only the fixture-owned rvtest_* schema; never targets the live browser/provider
# Changed: 2026-10-18 UTC | RV-W2-P0-REVIEW-RECOVERY | Initial independent restart/recovery harness
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md; issue #120 comment 6254315364
# History: Git and .riverview-revisions.json
# =============================================================================
"""W2 integration scenarios across the existing Grace exchange and provider MCP."""

import hashlib
import os
import unittest

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


TOKEN = "synthetic-w2-review-provider-token"
PROVIDER = "simulated:chatgpt-reasoning"
PRINCIPAL = PROVIDER


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class W2P0ReviewRecoveryTests(unittest.TestCase):
    """Run one disposable exchange through duplicate wake, delay and process recovery."""

    def setUp(self):
        from tests.test_external_reasoning_exchange import (
            ExternalReasoningExchangePostgresTests,
        )
        from riverview_core.resident_execution.external_reasoning_mcp import (
            ExternalReasoningMCPAdapter,
            ProviderTokenMap,
        )

        # Reuse the repository's established disposable-schema fixture rather
        # than creating a second schema/migration/authority path in W2 tests.
        self.fixture = ExternalReasoningExchangePostgresTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.tokens = ProviderTokenMap.from_document({
            "schema_version": ProviderTokenMap.SCHEMA,
            "tokens": [{
                "token_sha256": hashlib.sha256(TOKEN.encode()).hexdigest(),
                "provider_id": PROVIDER,
                "principal_id": PRINCIPAL,
                "scopes": ["reasoning:exchange"],
                "expires_at": "2099-01-01T00:00:00Z",
            }],
        })
        self.identity = self.tokens.resolve(TOKEN)
        self.mcp_adapter_type = ExternalReasoningMCPAdapter

    def _mcp(self):
        return self.mcp_adapter_type(self.fixture.exchange, self.tokens)

    def test_duplicate_wake_and_delayed_mcp_reply_survive_exchange_restart(self):
        fx = self.fixture
        receipt = fx._submit(idem="w2-p0-delayed-reply")
        wake_calls = []

        # Synthetic C2 boundary: only IDs enter the fixed-wake caller. No
        # proposal/request body is accepted or forwarded by this fixture.
        def ring(request_id, correlation_id):
            wake_calls.append((request_id, correlation_id))
            return {"status": "succeeded", "submit_verified": True}

        delivery = fx.exchange.begin_delivery(receipt.request_id, PROVIDER,
            owner_id="w2:doorbell", lease_seconds=30)
        self.assertIsNotNone(delivery)
        wake = ring(receipt.request_id, receipt.correlation_id)
        self.assertTrue(wake["submit_verified"])
        self.assertEqual(fx.exchange.mark_delivered(receipt.request_id,
            receipt.correlation_id, PROVIDER, owner_id="w2:doorbell",
            delivery_token=delivery.claim_token, fence=delivery.fence),
            "awaiting_external_claim")
        self.assertEqual(wake_calls, [(receipt.request_id, receipt.correlation_id)])

        # A duplicate dispatcher pass cannot acquire a second delivery lease
        # after the same wake has been durably acknowledged.
        self.assertIsNone(fx.exchange.begin_delivery(receipt.request_id, PROVIDER,
            owner_id="w2:doorbell-replay", lease_seconds=30))
        self.assertEqual(len(wake_calls), 1)

        grace = fx._grace_service(fx.exchange)
        self.assertEqual(grace.consume_external_reasoning(), 0)  # provider is delayed

        # Recreate both adapters to model process loss while the mailbox waits.
        fx.ledger.close()
        fx.ledger = __import__("riverview_core.postgres_ledger",
            fromlist=["PostgresLedger"]).PostgresLedger(DSN, schema=fx.schema)
        fx.exchange = fx._service()
        self.assertEqual(fx.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "awaiting_external_claim")
        self.assertEqual(fx.exchange.begin_delivery(receipt.request_id, PROVIDER,
            owner_id="w2:doorbell-after-restart", lease_seconds=30), None)
        self.assertEqual(len(wake_calls), 1)

        mcp = self._mcp()
        listed = mcp.call_tool(self.identity, "reasoning_exchange_list_requests", {})
        row = next(item for item in listed["requests"]
                   if item["request_id"] == receipt.request_id)
        self.assertEqual(row["correlation_id"], receipt.correlation_id)
        self.assertEqual(row["delivery_state"], "awaiting_external_claim")

        claim = mcp.call_tool(self.identity, "reasoning_exchange_claim_request", {
            "request_id": receipt.request_id,
            "correlation_id": receipt.correlation_id,
        })
        self.assertTrue(claim["claimed"] if "claimed" in claim else claim.get("claim_token"))
        response = fx._response(receipt, advisory="Synthetic delayed external review")
        arguments = {
            "request_id": receipt.request_id,
            "correlation_id": receipt.correlation_id,
            "claim_token": claim["claim_token"],
            "fence": claim["fence"],
            "idempotency_key": "w2:p0:reply:one",
            "response": response,
        }
        submitted = mcp.call_tool(self.identity,
            "reasoning_exchange_submit_response", arguments)
        duplicate = mcp.call_tool(self.identity,
            "reasoning_exchange_submit_response", arguments)
        self.assertEqual(submitted, duplicate)
        self.assertEqual(submitted["state"], "response_received")

        # Restart before Grace consumes: PostgreSQL retains the response and
        # exchange event; Grace's existing consume fence owns the only close.
        fx.ledger.close()
        fx.ledger = __import__("riverview_core.postgres_ledger",
            fromlist=["PostgresLedger"]).PostgresLedger(DSN, schema=fx.schema)
        fx.exchange = fx._service()
        status = fx.exchange.status(receipt.request_id, receipt.correlation_id)
        self.assertEqual(status["delivery_state"], "response_received")
        self.assertEqual(status["response_sha256"], submitted["response_sha256"])

        grace = fx._grace_service(fx.exchange)
        acknowledge = fx.exchange.acknowledge_consumed

        def interrupt_acknowledgement(*_args, **_kwargs):
            raise RuntimeError("synthetic_crash_before_ack")

        fx.exchange.acknowledge_consumed = interrupt_acknowledgement
        self.assertEqual(grace.consume_external_reasoning(), 0)
        evaluations = [event for event in grace.pipeline.objective_events(fx.objective)
                       if event["event_type"] ==
                       "resident.reasoning.external_advisory_evaluated"]
        self.assertEqual(len(evaluations), 1)
        calls_after_evaluation = len(fx.grace_provider.requests)

        fx.exchange.acknowledge_consumed = acknowledge
        fx.ledger.close()
        fx.ledger = __import__("riverview_core.postgres_ledger",
            fromlist=["PostgresLedger"]).PostgresLedger(DSN, schema=fx.schema)
        fx.exchange = fx._service()
        grace = fx._grace_service(fx.exchange)
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(len(fx.grace_provider.requests), calls_after_evaluation)
        self.assertEqual(fx.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "grace_consumed")
        self.assertEqual(grace.consume_external_reasoning(), 0)
        events = fx.exchange.events(receipt.request_id, receipt.correlation_id)
        self.assertEqual(sum(event["event_type"] == "response_received"
                             for event in events), 1)
        self.assertEqual(sum(event["event_type"] == "grace_consumed"
                             for event in events), 1)


if __name__ == "__main__":
    unittest.main()
