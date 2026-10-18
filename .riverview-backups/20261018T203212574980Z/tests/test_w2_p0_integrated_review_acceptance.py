# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_w2_p0_integrated_review_acceptance.py
# Component: W2-P0-INTEGRATED-REVIEW-ACCEPTANCE
# Revision: 1.0.2
# Purpose: Verify typed Grace review subjects survive durable C3 exchange and C4 MCP round trips
# Execution Model: Isolated PostgreSQL schema, unittest, deterministic synthetic provider only
# Observability: Subject/revision digests, provider identity, exchange state, objective events
# Dependencies: RIVERVIEW_TEST_PG_DSN; C3 exact-subject exchange; C4 typed-subject MCP
# Authority: W2 acceptance only; no browser, external provider, production DB, or grants
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Initial C3/C4 integrated tests
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Register unrelated provider in isolated router fixture
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Accept privacy-concealed wrong-provider denial
# Contracts: docs/development/W2_P0_CONTROLLED_ACCEPTANCE.md; issue #120 comment 6254574126
# History: Git and .riverview-revisions.json
# =============================================================================
"""Disposable PostgreSQL acceptance for Grace's exact proposal through provider MCP."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import unittest
from datetime import timedelta
from types import SimpleNamespace

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
TOKEN = "synthetic-w2-integrated-provider-token"
OTHER_TOKEN = "synthetic-w2-other-provider-token"
PROVIDER = "simulated:chatgpt-reasoning"
OTHER_PROVIDER = "simulated:unrelated-provider"


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class W2IntegratedReviewAcceptanceTests(unittest.TestCase):
    """Use the repository C3 schema fixture and the actual C4 MCP adapter."""

    def setUp(self):
        fixture_path = Path(__file__).with_name("test_external_reasoning_exchange.py")
        spec = importlib.util.spec_from_file_location("w2_integrated_exchange_fixture", fixture_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("existing external reasoning PostgreSQL fixture is unavailable")
        fixture_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture_module)
        self.fixture_module = fixture_module
        from riverview_core.resident_execution.external_reasoning_mcp import (
            ExternalProviderRegistration,
            ExternalReasoningMCPAdapter,
            ProviderTokenMap,
        )

        self.fixture = fixture_module.ExternalReasoningExchangePostgresTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        # C4 validates every configured token-map provider against the durable
        # exchange router. Register the negative-test provider only in this
        # disposable fixture; it has no production identity or grant.
        self.fixture.router.providers[OTHER_PROVIDER] = ExternalProviderRegistration(
            OTHER_PROVIDER, OTHER_PROVIDER)
        self.mcp_adapter_type = ExternalReasoningMCPAdapter
        self.token_map = ProviderTokenMap.from_document({
            "schema_version": ProviderTokenMap.SCHEMA,
            "tokens": [
                self._token_entry(TOKEN, PROVIDER, PROVIDER),
                self._token_entry(OTHER_TOKEN, OTHER_PROVIDER, OTHER_PROVIDER),
            ],
        })
        self.provider = self.token_map.resolve(TOKEN)
        self.other_provider = self.token_map.resolve(OTHER_TOKEN)
        self.adapter = self.mcp_adapter_type(self.fixture.exchange, self.token_map)

    @staticmethod
    def _token_entry(token, provider_id, principal_id):
        return {
            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "provider_id": provider_id,
            "principal_id": principal_id,
            "scopes": ["reasoning:exchange"],
            "expires_at": "2099-01-01T00:00:00Z",
        }

    def _restart_exchange(self):
        from riverview_core.postgres_ledger import PostgresLedger

        self.fixture.ledger.close()
        self.fixture.ledger = PostgresLedger(DSN, schema=self.fixture.schema)
        self.fixture.exchange = self.fixture._service()
        self.adapter = self.mcp_adapter_type(self.fixture.exchange, self.token_map)

    def _start_grace_review(self):
        fx = self.fixture
        grace = fx._grace_service(fx.exchange, initiate_external=True,
                                  targets=(PROVIDER,))
        self.assertTrue(grace.reason_one_grounded_objective(fx.objective))
        row = fx.admin.execute(fx.sql.SQL("""SELECT request_id::text,correlation_id::text,
                delivery_state,request_payload,deadline_at FROM {}.external_reasoning_exchanges
            WHERE objective_id=%s""").format(fx.sql.Identifier(fx.schema)),
            (fx.objective,)).fetchone()
        self.assertIsNotNone(row)
        self.assertIn("review_subject", row[3])
        self.assertEqual(row[3]["review_subject"]["revision"], 1)
        self.assertEqual(fx.exchange.status(row[0], row[1])["review_subject_sha256"],
                         row[3]["review_subject"]["sha256"])
        return grace, row

    def _provider_round_trip(self, request_id, correlation_id, subject, *, idempotency_key):
        fx = self.fixture
        listed = self.adapter.call_tool(self.provider,
            "reasoning_exchange_list_requests", {})
        request = next(item for item in listed["requests"]
                       if item["request_id"] == request_id)
        provider_subject = request["review_subject"]
        self.assertEqual(request["review_subject_sha256"], subject["sha256"])
        self.assertEqual(json.dumps(provider_subject, sort_keys=True),
                         json.dumps(subject, sort_keys=True))
        from riverview_core.resident_reasoning import PlanStep
        self.assertEqual(set(provider_subject["proposal"]["steps"][0]),
                         set(PlanStep.__dataclass_fields__))

        # A provider with another configured identity cannot claim this request.
        state_before_wrong_provider = self.fixture.exchange.status(
            request_id, correlation_id)["delivery_state"]
        with self.assertRaises((self.fixture_module.ExchangeUnauthorized,
                                self.fixture_module.ExchangeNotFound)):
            self.adapter.call_tool(self.other_provider,
                "reasoning_exchange_claim_request", {
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                })
        self.assertEqual(self.fixture.exchange.status(
            request_id, correlation_id)["delivery_state"], state_before_wrong_provider)

        tampered = json.loads(json.dumps(provider_subject))
        tampered["proposal"]["steps"][0]["authorized_paths"].append("test://altered-scope")
        from riverview_core.resident_execution.external_reasoning import validate_review_subject
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            validate_review_subject(tampered)

        claim = self.adapter.call_tool(self.provider,
            "reasoning_exchange_claim_request", {
                "request_id": request_id,
                "correlation_id": correlation_id,
            })
        receipt = SimpleNamespace(request_id=request_id,
                                  correlation_id=correlation_id)
        response = fx._response(receipt)
        common = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "claim_token": claim["claim_token"],
            "fence": claim["fence"],
            "idempotency_key": idempotency_key,
            "response": response,
        }
        with self.assertRaisesRegex(ValueError, "review_subject_digest_mismatch"):
            self.adapter.call_tool(self.provider,
                "reasoning_exchange_submit_response", common)
        wrong_hash = {**common, "review_subject_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "review_subject_digest_mismatch"):
            self.adapter.call_tool(self.provider,
                "reasoning_exchange_submit_response", wrong_hash)
        self.assertIsNone(self.fixture.exchange.status(request_id,
            correlation_id)["response_sha256"])

        valid = {**common, "review_subject_sha256": subject["sha256"]}
        first = self.adapter.call_tool(self.provider,
            "reasoning_exchange_submit_response", valid)
        duplicate = self.adapter.call_tool(self.provider,
            "reasoning_exchange_submit_response", valid)
        self.assertEqual(first, duplicate)
        self.assertEqual(first["state"], "response_received")
        return first

    def test_typed_subject_mcp_digest_provider_isolation_and_finish_survive_restart(self):
        from riverview_core.resident_execution.external_reasoning import validate_review_subject

        fx = self.fixture
        grace, row = self._start_grace_review()
        request_id, correlation_id, _state, payload, _deadline = row
        subject = validate_review_subject(payload["review_subject"])

        # A candidate remains non-final until an exact-subject provider response is consumed.
        self.assertEqual(grace.pipeline.get_objective(fx.objective)["status"], "GROUNDED")
        self.assertFalse(fx.exchange.has_terminal_review_for_objective(fx.objective))
        self.assertEqual(grace.consume_external_reasoning(), 0)

        submitted = self._provider_round_trip(request_id, correlation_id, subject,
                                               idempotency_key="w2:finish:response")
        self._restart_exchange()
        status = self.adapter.call_tool(self.provider, "reasoning_exchange_status", {
            "request_id": request_id, "correlation_id": correlation_id,
        })
        self.assertEqual(status["response_sha256"], submitted["response_sha256"])
        self.assertEqual(status["review_subject_sha256"], subject["sha256"])

        grace = fx._grace_service(fx.exchange)
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(grace.pipeline.get_objective(fx.objective)["status"], "PROPOSED")
        events = grace.pipeline.objective_events(fx.objective)
        reviewed = [event for event in events if event["event_type"] ==
                    "resident.reasoning.external_proposal_reviewed"]
        self.assertEqual(len(reviewed), 1)
        self.assertEqual(reviewed[0]["payload"]["subject_sha256"], subject["sha256"])
        self.assertEqual(reviewed[0]["payload"]["decision"], "finish")
        self.assertTrue(fx.exchange.has_terminal_review_for_objective(fx.objective))

    def test_exact_subject_expiry_rejects_late_provider_response_without_finalization(self):
        fx = self.fixture
        grace, row = self._start_grace_review()
        request_id, correlation_id, _state, payload, deadline = row
        subject = payload["review_subject"]
        listed = self.adapter.call_tool(self.provider,
            "reasoning_exchange_list_requests", {})
        self.assertTrue(any(item["request_id"] == request_id
                            for item in listed["requests"]))
        claim = self.adapter.call_tool(self.provider,
            "reasoning_exchange_claim_request", {
                "request_id": request_id, "correlation_id": correlation_id,
            })
        fx.clock_value = deadline + timedelta(seconds=1)
        late = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "claim_token": claim["claim_token"],
            "fence": claim["fence"],
            "idempotency_key": "w2:expiry:late-response",
            "review_subject_sha256": subject["sha256"],
            "response": fx._response(SimpleNamespace(request_id=request_id,
                                                     correlation_id=correlation_id)),
        }
        result = self.adapter.call_tool(self.provider,
            "reasoning_exchange_submit_response", late)
        self.assertEqual(result["state"], "expired")
        self.assertNotIn("response_sha256", result)
        self.assertEqual(fx.exchange.status(request_id,
            correlation_id)["delivery_state"], "expired")
        self.assertEqual(grace.consume_external_reasoning(), 0)
        self.assertEqual(grace.pipeline.get_objective(fx.objective)["status"], "GROUNDED")
        self.assertFalse(fx.exchange.has_terminal_review_for_objective(fx.objective))

    def test_typed_subject_revision_survives_restart_and_finishes_new_revision(self):
        fx = self.fixture
        grace, first_row = self._start_grace_review()
        first_id, first_correlation, _state, first_payload, _deadline = first_row
        first_subject = first_payload["review_subject"]
        fx.grace_provider.revise_once = True
        self._provider_round_trip(first_id, first_correlation, first_subject,
                                  idempotency_key="w2:revise:response-1")

        # Restart with a durable response, then simulate failure after the successor is
        # admitted but before the parent's revision event is committed.
        self._restart_exchange()
        grace = fx._grace_service(fx.exchange)
        record_decision = grace.pipeline.record_external_review_decision

        def fail_after_successor(*_args, **_kwargs):
            raise RuntimeError("synthetic crash after successor admission")

        grace.pipeline.record_external_review_decision = fail_after_successor
        self.assertEqual(grace.consume_external_reasoning(), 0)
        grace.pipeline.record_external_review_decision = record_decision
        calls_after_admission = len(fx.grace_provider.requests)
        child = fx.admin.execute(fx.sql.SQL("""SELECT request_id::text,correlation_id::text,
                request_payload FROM {}.external_reasoning_exchanges
            WHERE request_payload->'review_parent'->>'request_id'=%s""").format(
                fx.sql.Identifier(fx.schema)), (first_id,)).fetchone()
        self.assertIsNotNone(child)
        self.assertEqual(child[2]["review_subject"]["revision"], 2)
        self.assertNotEqual(child[2]["review_subject"]["subject_id"],
                            first_subject["subject_id"])
        self.assertNotEqual(child[2]["review_subject"]["sha256"], first_subject["sha256"])
        self.assertFalse(fx.exchange.has_terminal_review_for_objective(fx.objective))

        self._restart_exchange()
        grace = fx._grace_service(fx.exchange)
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(len(fx.grace_provider.requests), calls_after_admission)
        revised = [event for event in grace.pipeline.objective_events(fx.objective)
                   if event["event_type"] == "resident.reasoning.external_proposal_revised"]
        self.assertEqual(len(revised), 1)
        self.assertEqual(revised[0]["payload"]["successor_request_id"], child[0])
        self.assertEqual(revised[0]["payload"]["successor_correlation_id"], child[1])

        child_subject = child[2]["review_subject"]
        self._provider_round_trip(child[0], child[1], child_subject,
                                  idempotency_key="w2:revise:response-2")
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(grace.pipeline.get_objective(fx.objective)["status"], "PROPOSED")
        final = [event for event in grace.pipeline.objective_events(fx.objective)
                 if event["event_type"] == "resident.reasoning.external_proposal_reviewed"]
        self.assertEqual(len(final), 1)
        self.assertEqual(final[0]["payload"]["revision"], 2)
        self.assertEqual(final[0]["payload"]["subject_sha256"], child_subject["sha256"])
        self.assertTrue(fx.exchange.has_terminal_review_for_objective(fx.objective))


if __name__ == "__main__":
    unittest.main()
