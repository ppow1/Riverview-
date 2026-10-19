# =============================================================================
# RIVERVIEW~ CONTROLLED EVIDENCE TEST
# File: evidence/checkouts/CHATGPT-DOORBELL/20261019T212319Z-f7fae23/combined_c2_doorbell_postgres.py
# Component: CHATGPT-DOORBELL
# File Revision: 1.0.1
# Purpose: Compose the C2 worker with the published C3 exchange on a disposable PostgreSQL database
# Execution Model: One-shot acceptance test; no production service or browser access
# Observability: Exact request lineage, bridge calls, fenced receipt events, retries, and restart status
# Dependencies: C2 dispatcher; C3 exchange; tests/test_external_reasoning_exchange.py fixture; PostgreSQL 16
# Authority: Synthetic identities and bridge only; never sends a live ChatGPT wake
# Changed: 2026-10-19 UTC | RV-C2-DOORBELL-RESUME-20261019 | Assert both receipt outcomes and retry fencing explicitly
# History: New controlled evidence test; .riverview-revisions.json and adjacent artifacts.json
# =============================================================================
"""Combined C2/C3 disposable PostgreSQL acceptance test."""

import importlib.util
import os
from datetime import timedelta
from pathlib import Path
import unittest

SOURCE_ROOT = Path(os.environ.get("RIVERVIEW_TEST_SOURCE_ROOT", Path.cwd())).resolve()
FIXTURE_PATH = SOURCE_ROOT / "tests" / "test_external_reasoning_exchange.py"
spec = importlib.util.spec_from_file_location("c2_pg_fixture", FIXTURE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("combined-source external reasoning fixture is unavailable")
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)

from riverview_core.doorbell.browser_bridge import DoorbellResult
from riverview_core.doorbell.dispatcher import DoorbellWakeWorker, DoorbellWorkerConfig
from riverview_core.postgres_ledger import PostgresLedger

PROVIDER = fixture_module.PROVIDER
OWNER = "c2:synthetic-owner"


class SyntheticRetryBridge:
    """Deterministic bridge double: one known pre-send error, then success."""

    def __init__(self):
        self.calls = []

    def ring(self, request, designated_conversation_id):
        self.calls.append((request, designated_conversation_id))
        if len(self.calls) == 1:
            return DoorbellResult(request.request_id, request.correlation_id,
                                  "failed", "RIV-PLY-0007")
        return DoorbellResult(request.request_id, request.correlation_id, "succeeded")


class CombinedC2DoorbellPostgresTests(unittest.TestCase):
    def test_request_claim_bridge_fenced_receipt_retry_dedup_and_restart(self):
        fx = fixture_module.ExternalReasoningExchangePostgresTests()
        fx.setUp()
        try:
            receipt = fx._submit(idem="c2-pg-combined-doorbell")
            bridge = SyntheticRetryBridge()
            config = DoorbellWorkerConfig(PROVIDER, OWNER, str(fx.conversation_id))
            worker = DoorbellWakeWorker(fx.exchange, bridge, config)
            durable_receipts = []
            record = fx.exchange.record_doorbell_receipt

            def record_and_capture(*args):
                durable_receipts.append(args)
                return record(*args)

            fx.exchange.record_doorbell_receipt = record_and_capture

            first = worker.run_once()
            self.assertEqual((first.status, first.outcome, first.safe_error_code),
                             ("recorded", "failed", "RIV-PLY-0007"))
            self.assertEqual(len(bridge.calls), 1)
            request, target = bridge.calls[0]
            self.assertEqual((str(request.request_id), str(request.correlation_id)),
                             (receipt.request_id, receipt.correlation_id))
            self.assertEqual(target, str(fx.conversation_id))

            # The exchange owns backoff; an immediate owner-loop pass must not wake again.
            self.assertEqual(worker.run_once().status, "idle")
            self.assertEqual(len(bridge.calls), 1)
            fx.clock_value += timedelta(seconds=3)

            second = worker.run_once()
            self.assertEqual((second.status, second.outcome, second.trigger_status),
                             ("recorded", "submitted", "ready"))
            self.assertEqual(len(bridge.calls), 2)
            self.assertEqual(str(bridge.calls[1][0].request_id), receipt.request_id)
            self.assertEqual(str(bridge.calls[1][0].correlation_id), receipt.correlation_id)
            self.assertEqual(len(durable_receipts), 2)
            self.assertEqual(durable_receipts[0][7:], ("failed", "RIV-PLY-0007"))
            self.assertEqual(durable_receipts[1][7:], ("submitted", None))
            self.assertEqual(durable_receipts[1][3], OWNER)
            self.assertGreater(durable_receipts[1][6], durable_receipts[0][6])
            self.assertNotEqual(durable_receipts[1][4], durable_receipts[0][4])

            # The same successful fenced receipt is idempotent and adds no event.
            self.assertEqual(record(*durable_receipts[1]), "awaiting_external_claim")
            self.assertIsNone(fx.exchange.claim_next_doorbell_request(PROVIDER, OWNER, 90))
            state = fx.exchange.status(receipt.request_id, receipt.correlation_id)
            self.assertEqual(state["delivery_state"], "awaiting_external_claim")
            with fx.ledger.db.cursor() as cur:
                fx.exchange._set_path(cur)
                cur.execute("""SELECT count(*) AS count FROM external_reasoning_exchange_events
                    WHERE request_id=%s AND event_type='doorbell_receipt'
                      AND actor_id=%s""", (receipt.request_id, OWNER))
                self.assertEqual(cur.fetchone()["count"], 2)

            # Reopen the ledger and exchange on the same isolated schema after success.
            fx.ledger.close()
            fx.ledger = PostgresLedger(fixture_module.DSN, schema=fx.schema)
            fx.exchange = fx._service()
            restarted = DoorbellWakeWorker(fx.exchange, bridge, config)
            self.assertEqual(restarted.run_once().status, "idle")
            self.assertEqual(len(bridge.calls), 2)
            self.assertEqual(fx.exchange.status(receipt.request_id,
                receipt.correlation_id)["delivery_state"], "awaiting_external_claim")
        finally:
            fx.tearDown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
