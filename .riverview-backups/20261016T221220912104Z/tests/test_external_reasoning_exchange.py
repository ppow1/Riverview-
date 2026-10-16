# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_external_reasoning_exchange.py
# Component: RESIDENT-REASONING
# Revision: 1.0.3
# Purpose: Verify durable external advisory exchange, leases, recovery and idempotency
# Execution Model: Isolated PostgreSQL integration plus deterministic simulated provider
# Observability: State, correlation, event, digest and sanitized diagnostic assertions
# Dependencies: Private RIVERVIEW_TEST_PG_DSN; PostgreSQL 16; unittest
# Authority: Creates/drops only one unique rvtest_* schema; no production access
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Initial acceptance coverage
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Provision isolated runtime role for migration ACL regression
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Exercise actual ResidentReasoner on the consumed advisory
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""PostgreSQL acceptance tests for the transport-neutral exchange contract."""

import os
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.postgres_migrations import apply_migrations
from riverview_core.reasoning_escalation import EscalationRequest, ReasoningEscalationRouter
from riverview_core.resident_execution.external_reasoning import (
    DurableExternalReasoningExchange, ExchangeConflict, ExchangeExpired,
    ExchangeUnauthorized,
)
from riverview_core.resident_reasoning import ReasoningRequest


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
PROVIDER = "simulated:chatgpt-reasoning"
RESIDENT = "office:grace"


class _SimulatedExternalProvider:
    provider_id = PROVIDER
    calls = 0

    def propose(self, request):
        self.calls += 1
        raise AssertionError("durable admission must not synchronously invoke provider")


class _ReasoningState:
    def __init__(self):
        self.revision = 1
        self.state = {}

    def authorize_office_state(self, credential, office_id):
        return {"occupant_id": "occupant:grace-test", "provider_ref": "reasoner:test",
            "implementation_revision": "c" * 64, "binding_revision": 3,
            "state_revision": self.revision, "state": dict(self.state)}

    def set_office_state(self, credential, office_id, state, *, expected_revision):
        if expected_revision != self.revision:
            return "STATE_CONFLICT"
        self.state = dict(state)
        self.revision += 1
        return self.revision


class _ResumeAssignments:
    def read(self, assignment_id):
        return {"id": assignment_id, "revision": "2", "state": "grounded",
            "objective": "evaluate the external advisory",
            "acceptance_criteria": ["persist an unapproved reasoning proposal"]}


class _ResumeKnowledge:
    @staticmethod
    def _verified():
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
        return KnowledgeResult(KnowledgeStatus.VERIFIED, {"institutional_fact": "fixture"},
            ("repo://test/verified-institutional-context",), "1.0.0", "d" * 64, True)

    def ground_assignment(self, assignment):
        return self._verified()

    def reground_assignment(self, assignment, trigger):
        return self._verified()


class _GraceReasoningProvider:
    provider_id = "reasoner:test"

    def __init__(self):
        self.requests = []

    def propose(self, request):
        from riverview_core.resident_reasoning import PlanProposal, PlanStep
        self.requests.append(request)
        return PlanProposal("evaluate advisory", (PlanStep("review", "Review advice",
            ("record a proposal only",)),), 5, provider_id=self.provider_id,
            served_model="fixture-reasoner", model_revision="c" * 64,
            reasoning_stage="reasoning")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class ExternalReasoningExchangePostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql

        self.psycopg, self.sql = psycopg, sql
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {} ").format(sql.Identifier(self.schema)))
        role_exists = self.admin.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='riverview_core')"
        ).fetchone()[0]
        self.created_runtime_role = not role_exists
        if self.created_runtime_role:
            # The CI PostgreSQL service uses a disposable superuser. Creating
            # this exact NOLOGIN role lets the migration's production ACL
            # branch run instead of silently skipping its runtime grants.
            self.admin.execute("CREATE ROLE riverview_core NOLOGIN")
        apply_migrations(DSN, schema=self.schema)
        core = ROOT / "src/riverview_core"
        for component in ("assignment_scheduler", "worker_adapter", "cme",
                          "institutional_authority", "resident_execution"):
            apply_migrations(DSN, schema=self.schema,
                             migrations_dir=core / component / "migrations")
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.objective = "objective:" + uuid4().hex
        self.other_objective = "objective:" + uuid4().hex
        for objective in (self.objective, self.other_objective):
            self.admin.execute(sql.SQL("""INSERT INTO {}.grace_objectives
                (objective_id,request,scope_ref,submitter_id,acceptance_criteria,status)
                VALUES (%s,'bounded synthetic reasoning task','work-order:engineering',
                        'steward:test','[\"produce advisory\"]'::jsonb,'GROUNDED')""").format(
                sql.Identifier(self.schema)), (objective,))
        self.provider = _SimulatedExternalProvider()
        self.router = ReasoningEscalationRouter({PROVIDER: self.provider})
        self.clock_value = datetime.now(timezone.utc)
        self.exchange = self._service()
        self.original = ReasoningRequest(
            request_id=str(uuid4()), office_id="office:grace", assignment_id=self.objective,
            assignment_revision="2", binding_revision=9, implementation_revision="a" * 64,
            trigger="task_complexity", token_budget=512,
            assignment={"objective": "Bounded synthetic external reasoning"},
            verified_knowledge=({"status": "VERIFIED", "source": "test://fixture"},),
            prior_plan=None)
        self.conversation_id = str(uuid4())
        self.envelope = EscalationRequest.create(
            self.original, reason="task_complexity", target_provider_id=PROVIDER,
            max_tokens=128, timeout_seconds=30)
        self.authorized = lambda principal, action, scope: (
            principal == RESIDENT and action == ReasoningEscalationRouter.ACTION
            and scope == "provider:" + PROVIDER)
        self.reasoning_state = _ReasoningState()
        self.grace_provider = _GraceReasoningProvider()

    def _service(self, clock=None):
        return DurableExternalReasoningExchange(self.ledger, self.router,
            actor_id=RESIDENT, clock=clock or (lambda: self.clock_value))

    def tearDown(self):
        if getattr(self, "ledger", None) and not self.ledger.db.closed:
            self.ledger.close()
        if getattr(self, "admin", None) and not self.admin.closed:
            self.admin.execute(self.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                self.sql.Identifier(self.schema)))
            if getattr(self, "created_runtime_role", False):
                self.admin.execute("DROP ROLE IF EXISTS riverview_core")
            self.admin.close()

    def _submit(self, *, idem=None, deadline=None, authorize=None):
        envelope = EscalationRequest.create(
            self.original, reason="task_complexity", target_provider_id=PROVIDER,
            max_tokens=128, timeout_seconds=30)
        return self.exchange.submit(envelope, self.original, principal_id=RESIDENT,
            authorize=authorize or self.authorized, originating_resident_id=RESIDENT,
            objective_id=self.objective, conversation_id=self.conversation_id, message_sequence=4,
            idempotency_key=idem or "idem:" + uuid4().hex,
            classification="institutional",
            deadline_at=deadline or self.clock_value + timedelta(minutes=5),
            source_references=("test://synthetic-context",))

    def _deliver_and_claim(self, receipt, *, lease=120):
        delivery = self.exchange.begin_delivery(receipt.request_id, PROVIDER,
            owner_id="transport:test", lease_seconds=30)
        self.assertIsNotNone(delivery)
        self.assertEqual(self.exchange.mark_delivered(receipt.request_id,
            receipt.correlation_id, PROVIDER, owner_id="transport:test",
            delivery_token=delivery.claim_token, fence=delivery.fence), "awaiting_external_claim")
        self.assertEqual(self.exchange.mark_delivered(receipt.request_id,
            receipt.correlation_id, PROVIDER, owner_id="transport:test",
            delivery_token=delivery.claim_token, fence=delivery.fence), "awaiting_external_claim")
        return self.exchange.claim(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=PROVIDER, lease_seconds=lease)

    def _response(self, receipt, *, advisory="Consider the verified context and continue reasoning"):
        return {"schema_version": self.exchange.RESPONSE_SCHEMA,
            "request_id": receipt.request_id, "correlation_id": receipt.correlation_id,
            "response_id": "sim-response-1", "advisory": advisory,
            "evidence_references": ["test://synthetic-evidence"],
            "provider_id": PROVIDER, "provider_model": "simulated-reasoning-v1"}

    def _existing_reasoning_resume(self, consumption):
        """Run existing reasoning, then persist its result under the stable consume key."""
        existing = self.admin.execute(self.sql.SQL("""SELECT 1 FROM {}.grace_objective_events
            WHERE idempotency_key=%s""").format(self.sql.Identifier(self.schema)),
            (f"{consumption.consumption_key}:reasoned",)).fetchone()
        if existing:
            return False, f"{consumption.consumption_key}:reasoned"
        from riverview_core.resident_reasoning import ReasoningStatus, ResidentReasoner

        reasoner = ResidentReasoner(registry=self.reasoning_state, office_id=RESIDENT,
            resident_credential="fixture-resident-credential", assignments=_ResumeAssignments(),
            knowledge=_ResumeKnowledge(), providers={"reasoner:test": self.grace_provider},
            timeout_seconds=1)
        result = reasoner.propose(consumption.original_request.assignment_id,
            trigger="external_reasoning_resume", token_budget=64,
            external_advisory=consumption.advisory)
        if result.status is not ReasoningStatus.PROPOSED or result.proposal is None:
            raise AssertionError(f"Grace reasoning returned {result.status.value}:{result.detail_code}")
        request = self.grace_provider.requests[-1]
        self.assertEqual(request.assignment_id, consumption.original_request.assignment_id)
        self.assertEqual(request.external_advisory, consumption.advisory)
        self.assertNotIn(consumption.advisory["advisory"], str(request.verified_knowledge))
        event_key = f"{consumption.consumption_key}:reasoned"
        payload = {"exchange_request_id": consumption.request_id,
            "correlation_id": consumption.correlation_id,
            "advisory_sha256": __import__("hashlib").sha256(
                __import__("json").dumps(consumption.advisory, sort_keys=True,
                    separators=(",", ":")).encode()).hexdigest(),
            "decision": "advisory_evaluated_as_unapproved_proposal",
            "reasoning_request_id": result.request_id,
            "reasoning_status": result.status.value,
            "reasoning_provider_id": result.provider_id,
            "proposal_summary": result.proposal.summary}
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'resident.reasoning.external_advisory_evaluated',%s,%s,%s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING""",
                    (self.objective, event_key, RESIDENT,
                     __import__("json").dumps(payload, sort_keys=True)))
                return cur.rowcount == 1, event_key

    def test_authorized_round_trip_restart_and_unrelated_assignment_progress(self):
        receipt = self._submit(idem="roundtrip")
        self.assertEqual(receipt.delivery_state, "awaiting_delivery")
        self.assertEqual(self.provider.calls, 0)
        # Work in the existing independent assignment ledger proceeds while the
        # exchange waits; no caller or CME loop is held by remote reasoning.
        self.ledger.create("assignment:unrelated-exchange-test", "worker:test",
            "assignment-create-unrelated", authority_ref="work-order:engineering",
            objective_ref=self.other_objective, actor_id="steward:test")
        self.ledger.transition("assignment:unrelated-exchange-test", "ready", "intake",
            "assignment-ready-unrelated", actor_id="event-processor:test")
        self.assertEqual(self.ledger.get("assignment:unrelated-exchange-test")["state"], "ready")
        claim = self._deliver_and_claim(receipt)
        duplicate_claim = self.exchange.claim(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=PROVIDER)
        self.assertTrue(duplicate_claim.duplicate)
        self.assertEqual(duplicate_claim.claim_token, claim.claim_token)
        response = self._response(receipt)
        digest = self.exchange.submit_response(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=PROVIDER, claim_token=claim.claim_token,
            fence=claim.fence, idempotency_key="response:roundtrip", response=response)
        self.assertEqual(self.exchange.submit_response(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=PROVIDER, claim_token=claim.claim_token,
            fence=claim.fence, idempotency_key="response:roundtrip", response=response), digest)

        # Recreate the process-facing adapter after response persistence, before
        # Grace consumes the result. PostgreSQL is the recovery point.
        self.ledger.close()
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.exchange = self._service()
        self.assertEqual(self.exchange.status(receipt.request_id, receipt.correlation_id)["delivery_state"],
                         "response_received")
        consumption = self.exchange.consume(receipt.request_id, receipt.correlation_id,
            principal_id=RESIDENT, authorize=self.authorized)
        self.assertEqual(consumption.original_request.request_id, self.original.request_id)
        self.assertEqual(consumption.advisory["advisory"], response["advisory"])
        # The existing reasoning/objective event contract receives original
        # context and advice separately; retries use one durable idempotency key.
        self.assertEqual(consumption.original_request.request_id, self.original.request_id)
        self.assertEqual(consumption.consumption_key,
                         f"external-reasoning-consumed:{receipt.request_id}")
        inserted, evaluation_key = self._existing_reasoning_resume(consumption)
        self.assertTrue(inserted)
        self.assertEqual(self.exchange.acknowledge_consumed(receipt.request_id,
            receipt.correlation_id, principal_id=RESIDENT,
            consumption_key=consumption.consumption_key,
            consumption_token=consumption.consumption_token, fence=consumption.fence,
            result_reference="grace-state:external-advisory-evaluated:1",
            authorize=self.authorized), "grace_consumed")
        again = self.exchange.consume(receipt.request_id, receipt.correlation_id,
            principal_id=RESIDENT, authorize=self.authorized)
        self.assertTrue(again.duplicate)
        self.assertEqual(again.advisory["advisory"], response["advisory"])
        retry_inserted, retry_key = self._existing_reasoning_resume(again)
        self.assertFalse(retry_inserted)
        self.assertEqual(retry_key, evaluation_key)
        status = self.exchange.status(receipt.request_id, receipt.correlation_id)
        self.assertEqual(status["diagnostic_state"], "Grace consumed")
        self.assertEqual(status["response_sha256"], digest)
        self.assertEqual(len([e for e in self.exchange.events(receipt.request_id,
            receipt.correlation_id) if e["event_type"] == "response_received"]), 1)
        self.assertEqual(self.admin.execute(self.sql.SQL("""SELECT count(*)
            FROM {}.grace_objective_events WHERE idempotency_key=%s""").format(
                self.sql.Identifier(self.schema)), (evaluation_key,)).fetchone()[0], 1)
        objective = self.admin.execute(self.sql.SQL("""SELECT status,assignment_id,proposal
            FROM {}.grace_objectives WHERE objective_id=%s""").format(
                self.sql.Identifier(self.schema)), (self.objective,)).fetchone()
        self.assertEqual(objective, ("GROUNDED", None, None))

    def test_exact_grant_is_required_before_persistence_and_rechecked_on_consume(self):
        with self.assertRaises(ExchangeUnauthorized):
            self._submit(idem="denied", authorize=lambda *_: False)
        self.assertEqual(self.admin.execute(self.sql.SQL(
            "SELECT count(*) FROM {}.external_reasoning_exchanges").format(
                self.sql.Identifier(self.schema))).fetchone()[0], 0)
        receipt = self._submit(idem="auth-recheck")
        claim = self._deliver_and_claim(receipt)
        self.exchange.submit_response(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=PROVIDER, claim_token=claim.claim_token,
            fence=claim.fence, idempotency_key="response:auth-recheck",
            response=self._response(receipt))
        with self.assertRaises(ExchangeUnauthorized):
            self.exchange.consume(receipt.request_id, receipt.correlation_id,
                principal_id=RESIDENT, authorize=lambda *_: False)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "response_received")

    def test_restricted_material_and_conflicting_idempotency_are_rejected(self):
        with self.assertRaises(ValueError):
            self.exchange.submit(self.envelope, self.original, principal_id=RESIDENT,
                authorize=self.authorized, originating_resident_id=RESIDENT,
                objective_id=self.objective, conversation_id=self.conversation_id,
                message_sequence=4, idempotency_key="local-only", classification="local_only",
                deadline_at=self.clock_value + timedelta(minutes=1))
        first = self._submit(idem="collision-key")
        changed = ReasoningRequest(**{**self.original.__dict__,
            "trigger": "different bounded trigger"})
        changed_envelope = EscalationRequest.create(changed, reason="task_complexity",
            target_provider_id=PROVIDER, max_tokens=128, timeout_seconds=30)
        with self.assertRaises(ExchangeConflict):
            self.exchange.submit(changed_envelope, changed, principal_id=RESIDENT,
                authorize=self.authorized, originating_resident_id=RESIDENT,
                objective_id=self.objective, conversation_id=self.conversation_id,
                message_sequence=4, idempotency_key="collision-key",
                classification="institutional",
                deadline_at=self.clock_value + timedelta(minutes=5))
        self.assertEqual(self.exchange.status(first.request_id,
            first.correlation_id)["delivery_state"], "awaiting_delivery")

    def test_delivery_failure_retries_with_bounded_backoff(self):
        receipt = self._submit(idem="delivery-retry")
        delivery = self.exchange.begin_delivery(receipt.request_id, PROVIDER,
            owner_id="transport:test", lease_seconds=30)
        self.assertEqual(self.exchange.fail_delivery(receipt.request_id,
            receipt.correlation_id, PROVIDER, owner_id="transport:test",
            delivery_token=delivery.claim_token, fence=delivery.fence,
            error_code="connector_temporarily_unavailable"), "awaiting_delivery")
        self.assertEqual(self.exchange.eligible_requests(PROVIDER, principal_id=PROVIDER), [])
        self.clock_value += timedelta(seconds=3)
        self.assertEqual(len(self.exchange.eligible_requests(PROVIDER, principal_id=PROVIDER)), 1)
        retry = self.exchange.begin_delivery(receipt.request_id, PROVIDER,
            owner_id="transport:test", lease_seconds=30)
        self.assertGreater(retry.fence, delivery.fence)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_attempts"], 2)

    def test_migration_grants_only_exchange_runtime_access(self):
        result = self.admin.execute(self.sql.SQL("""SELECT
            has_table_privilege('riverview_core',%s,'SELECT'),
            has_table_privilege('riverview_core',%s,'DELETE'),
            has_column_privilege('riverview_core',%s,'delivery_state','UPDATE'),
            has_column_privilege('riverview_core',%s,'request_payload','UPDATE'),
            has_table_privilege('riverview_core',%s,'SELECT')"""), (
                f"{self.schema}.external_reasoning_exchanges",
                f"{self.schema}.external_reasoning_exchanges",
                f"{self.schema}.external_reasoning_exchanges",
                f"{self.schema}.external_reasoning_exchanges",
                f"{self.schema}.schema_migrations")).fetchone()
        self.assertEqual(result, (True, False, True, False, False))

    def test_idempotency_claim_fencing_and_response_correlation(self):
        receipt = self._submit(idem="same-request")
        duplicate = self._submit(idem="same-request")
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(receipt.request_id, duplicate.request_id)
        self.assertEqual(receipt.correlation_id, duplicate.correlation_id)
        claim = self._deliver_and_claim(receipt, lease=30)
        with self.assertRaises(ExchangeUnauthorized):
            self.exchange.claim(receipt.request_id, receipt.correlation_id,
                provider_id=PROVIDER, principal_id="other-provider")
        bad = self._response(receipt)
        bad["correlation_id"] = str(uuid4())
        with self.assertRaises(ValueError):
            self.exchange.submit_response(receipt.request_id, receipt.correlation_id,
                provider_id=PROVIDER, principal_id=PROVIDER, claim_token=claim.claim_token,
                fence=claim.fence, idempotency_key="bad-correlation", response=bad)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "awaiting_response")

    def test_expired_claim_is_fenced_and_late_response_expires_once(self):
        receipt = self._submit(idem="lease-expiry")
        claim = self._deliver_and_claim(receipt, lease=1)
        self.clock_value += timedelta(seconds=2)
        reclaimed = self.exchange.claim(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=PROVIDER, lease_seconds=30)
        self.assertGreater(reclaimed.fence, claim.fence)
        with self.assertRaises(ExchangeConflict):
            self.exchange.submit_response(receipt.request_id, receipt.correlation_id,
                provider_id=PROVIDER, principal_id=PROVIDER, claim_token=claim.claim_token,
                fence=claim.fence, idempotency_key="stale-response",
                response=self._response(receipt))

        expired = self._submit(idem="late-response", deadline=self.clock_value + timedelta(seconds=1))
        claim2 = self._deliver_and_claim(expired, lease=30)
        self.clock_value += timedelta(seconds=2)
        self.assertEqual(self.exchange.submit_response(expired.request_id, expired.correlation_id,
            provider_id=PROVIDER, principal_id=PROVIDER, claim_token=claim2.claim_token,
            fence=claim2.fence, idempotency_key="late-response-key",
            response=self._response(expired)), "expired")
        self.assertEqual(self.exchange.status(expired.request_id,
            expired.correlation_id)["delivery_state"], "expired")
        self.assertEqual(len([event for event in self.exchange.events(expired.request_id,
            expired.correlation_id) if event["event_type"] == "request_expired"]), 1)

    def test_process_restart_before_delivery_keeps_request_eligible(self):
        receipt = self._submit(idem="restart-before-delivery")
        self.ledger.close()
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.exchange = self._service()
        with self.assertRaises(ExchangeUnauthorized):
            self.exchange.eligible_requests(PROVIDER, principal_id="other-provider")
        eligible = self.exchange.eligible_requests(PROVIDER, principal_id=PROVIDER)
        self.assertEqual([str(item["request_id"]) for item in eligible], [receipt.request_id])


if __name__ == "__main__":
    unittest.main()
