# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_w2_p0_integrated_review_acceptance.py
# Component: W2-P0-INTEGRATED-REVIEW-ACCEPTANCE
# Revision: 1.0.5
# Purpose: Verify typed Grace review subjects survive durable C3 exchange and C4 MCP round trips
# Execution Model: Isolated PostgreSQL schema, unittest, deterministic synthetic provider only
# Observability: Subject/revision digests, provider identity, exchange state, objective events
# Dependencies: RIVERVIEW_TEST_PG_DSN; C3 exact-subject exchange; C4 typed-subject MCP
# Authority: W2 acceptance only; no browser, external provider, production DB, or grants
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Initial C3/C4 integrated tests
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Register unrelated provider in isolated router fixture
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Accept privacy-concealed wrong-provider denial
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Import MCP denial type from its owning adapter module
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Assert tampered typed subject is rejected without binding to error wording
# Changed: 2026-10-18 UTC | RV-W2-P0-INTEGRATED-REVIEW-ACCEPTANCE | Exercise C2 synthetic wake through C3 fenced receipt and Grace owner hook
# Contracts: docs/development/W2_P0_CONTROLLED_ACCEPTANCE.md; issue #120 comment 6254574126
# History: Git and .riverview-revisions.json
# =============================================================================
"""Disposable PostgreSQL acceptance for Grace's exact proposal through provider MCP."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
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
            ExchangeNotFound,
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
        self.exchange_not_found = ExchangeNotFound
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

    def _run_synthetic_doorbell(self, grace, request_id, correlation_id):
        """Exercise C2's worker against the C3 disposable exchange through Grace's hook."""
        from riverview_core.doorbell.dispatcher import DoorbellWakeWorker, DoorbellWorkerConfig
        from riverview_core.doorbell.runtime import OWNER_ID

        class SyntheticBridge:
            def __init__(self):
                self.calls = []

            def ring(self, request, target):
                self.calls.append((request, target))
                return SimpleNamespace(status="succeeded", failure_class=None)

        target_id = "8af9333f-a59f-4a06-b572-e68b4d12b6c2"
        bridge = SyntheticBridge()
        grace.doorbell_worker = DoorbellWakeWorker(self.fixture.exchange, bridge,
            DoorbellWorkerConfig(provider_id=PROVIDER, owner_id=OWNER_ID,
                                 designated_conversation_id=target_id))
        self.assertEqual(grace._run_doorbell_worker(), {"status": "recorded"})
        self.assertEqual(len(bridge.calls), 1)
        wake_request, actual_target = bridge.calls[0]
        self.assertEqual((str(wake_request.request_id), str(wake_request.correlation_id)),
                         (request_id, correlation_id))
        self.assertEqual(actual_target, target_id)
        self.assertEqual(self.fixture.exchange.status(request_id, correlation_id)["delivery_state"],
                         "awaiting_external_claim")
        self.assertEqual(grace._run_doorbell_worker(), {"status": "idle"})
        self.assertEqual(len(bridge.calls), 1)

        fx = self.fixture
        receipt = fx.admin.execute(fx.sql.SQL("""SELECT count(*),min(actor_id)
            FROM {}.external_reasoning_exchange_events
            WHERE request_id=%s AND event_type='doorbell_receipt'""").format(
                fx.sql.Identifier(fx.schema)), (request_id,)).fetchone()
        self.assertEqual(receipt, (1, OWNER_ID))

    def _write_w1_trace_snapshot(self, subject, request_id, correlation_id):
        """Export only the W1 allowlisted synthetic trace fields from this PG fixture."""
        from riverview_core.doorbell.runtime import OWNER_ID

        fx = self.fixture
        exchange_status = fx.exchange.status(request_id, correlation_id)
        raw_exchange_events = fx.admin.execute(fx.sql.SQL("""SELECT event_type,actor_id,
                payload,occurred_at,request_id::text,correlation_id::text
            FROM {}.external_reasoning_exchange_events WHERE request_id=%s ORDER BY sequence""").format(
                fx.sql.Identifier(fx.schema)), (request_id,)).fetchall()
        allowed_exchange_types = {"delivery_claimed", "doorbell_receipt", "claimed",
                                  "response_received", "grace_consumed"}
        payload_keys = {
            "delivery_claimed": ("state", "fence"),
            "doorbell_receipt": ("outcome", "attempt_id", "fence", "safe_error_code"),
            "claimed": ("state",),
            "response_received": ("response_sha256",),
            "grace_consumed": (),
        }
        exchange_events = []
        event_times = {}
        for event_type, actor_id, payload, occurred_at, event_request, event_correlation in raw_exchange_events:
            if event_type not in allowed_exchange_types:
                continue
            safe_payload = {key: payload[key] for key in payload_keys[event_type]
                            if isinstance(payload, dict) and key in payload}
            event = {"event_type": event_type, "actor_id": actor_id,
                     "occurred_at": occurred_at.isoformat(), "payload": safe_payload,
                     "request_id": event_request, "correlation_id": event_correlation}
            exchange_events.append(event)
            if event_type in {"claimed", "response_received"}:
                event_times[event_type] = occurred_at.isoformat()

        raw_grace_events = fx.admin.execute(fx.sql.SQL("""SELECT event_type,actor_id,
                payload,created_at FROM {}.grace_objective_events
            WHERE objective_id=%s AND event_type IN
                ('resident.reasoning.external_proposal_reviewed',
                 'resident.reasoning.external_proposal_revised',
                 'resident.reasoning.external_proposal_review_blocked')
            ORDER BY created_at""").format(fx.sql.Identifier(fx.schema)),
            (fx.objective,)).fetchall()
        grace_keys = ("request_id", "correlation_id", "subject_id", "revision",
                      "subject_sha256", "response_sha256", "proposal_sha256", "decision",
                      "successor_request_id", "successor_correlation_id")
        grace_events = []
        for event_type, actor_id, payload, created_at in raw_grace_events:
            if payload.get("request_id") != request_id or payload.get("correlation_id") != correlation_id:
                continue
            grace_events.append({"event_type": event_type, "actor_id": actor_id,
                "occurred_at": created_at.isoformat(),
                "payload": {key: payload[key] for key in grace_keys if key in payload}})

        bundle = {"schema_version": "rv.external-review-trace-input.v1",
            "execution_kind": "synthetic", "doorbell_owner_id": OWNER_ID,
            "rounds": [{
                "review_subject": {key: subject[key] for key in
                    ("schema_version", "subject_id", "revision", "sha256")},
                "exchange": {"request_id": request_id, "correlation_id": correlation_id,
                    "state": exchange_status["delivery_state"],
                    "eligible_at": exchange_status["requested_at"],
                    "response_sha256": exchange_status["response_sha256"],
                    "events": exchange_events},
                "provider": {"request_id": request_id, "correlation_id": correlation_id,
                    "state": "response_received", "provider_id": PROVIDER,
                    "review_subject_sha256": exchange_status["review_subject_sha256"],
                    "response_sha256": exchange_status["response_sha256"],
                    "claimed_at": event_times.get("claimed"),
                    "response_received_at": event_times.get("response_received")},
                "grace": {"request_id": request_id, "correlation_id": correlation_id,
                    "events": grace_events},
            }]}
        from riverview_core.resident_execution.external_review_trace import build_report
        projected = build_report(bundle)
        self.assertEqual(projected["outcome"], "complete")
        self.assertEqual(projected["rounds"][0]["state"], "accepted")
        self.assertFalse(projected["rounds"][0]["doorbell_source_mismatch"])
        export_path = os.environ.get("RIVERVIEW_W2_TRACE_EXPORT")
        if export_path:
            path = Path(export_path)
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            descriptor, export_path = tempfile.mkstemp(prefix="rv-w2-review-trace-", suffix=".json")
            os.close(descriptor)
            path = Path(export_path)
        encoded = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        path.write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
        # This line contains only the allowlisted synthetic metadata bundle so W1 can
        # retrieve it from the controlled-run log if the runner temp file is gone.
        print("W2_TRACE_SNAPSHOT_PATH=" + str(path))
        print("W2_TRACE_SNAPSHOT_JSON=" + encoded)

    def _provider_round_trip(self, request_id, correlation_id, subject, *, idempotency_key,
                             owner_service=None):
        fx = self.fixture
        if owner_service is not None:
            self._run_synthetic_doorbell(owner_service, request_id, correlation_id)
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
        from riverview_core.resident_execution.external_reasoning import ExchangeUnauthorized
        with self.assertRaises((ExchangeUnauthorized, self.exchange_not_found)):
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
        with self.assertRaises(ValueError):
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
                                               idempotency_key="w2:finish:response",
                                               owner_service=grace)
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
        self.assertFalse(any(event["event_type"] == "work_order.dispatched"
                             for event in grace.pipeline.objective_events(fx.objective)))
        self._write_w1_trace_snapshot(subject, request_id, correlation_id)

    def test_exact_subject_expiry_rejects_late_provider_response_without_finalization(self):
        fx = self.fixture
        grace, row = self._start_grace_review()
        request_id, correlation_id, _state, payload, deadline = row
        subject = payload["review_subject"]
        self._run_synthetic_doorbell(grace, request_id, correlation_id)
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
                                  idempotency_key="w2:revise:response-1",
                                  owner_service=grace)

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
                                  idempotency_key="w2:revise:response-2",
                                  owner_service=grace)
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
