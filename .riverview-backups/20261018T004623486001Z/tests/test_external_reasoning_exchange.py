# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_external_reasoning_exchange.py
# Component: RESIDENT-REASONING
# Revision: 1.0.6
# Purpose: Verify durable external advisory exchange, leases, recovery and idempotency
# Execution Model: Isolated PostgreSQL integration plus deterministic simulated provider
# Observability: State, correlation, event, digest and sanitized diagnostic assertions
# Dependencies: Private RIVERVIEW_TEST_PG_DSN; PostgreSQL 16; unittest
# Authority: Creates/drops only one unique rvtest_* schema; no production access
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Initial acceptance coverage
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Provision isolated runtime role for migration ACL regression
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Exercise actual ResidentReasoner on the consumed advisory
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Exercise provider-scoped MCP operations against isolated PostgreSQL
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Run the durable tool round-trip through an independent Streamable HTTP client
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Initiate the accepted exchange through Grace's persistent service and resume MCP replies through Grace after recovery.
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""PostgreSQL acceptance tests for the transport-neutral exchange contract."""

import os
import hashlib
import http.client
import json
import socket
import threading
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.postgres_migrations import apply_migrations
from riverview_core.reasoning_escalation import EscalationRequest, ReasoningEscalationRouter
from riverview_core.assignment_intake import AuthorizedAssignmentIntake
from riverview_core.resident_execution.external_reasoning import (
    DurableExternalReasoningExchange, ExchangeConflict, ExchangeExpired,
    ExchangeUnauthorized,
)
from riverview_core.resident_execution.external_reasoning_mcp import (
    ExternalReasoningMCPAdapter, ProviderTokenMap, create_server,
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
                (objective_id,request,scope_ref,submitter_id,acceptance_criteria,status,evidence,source_sha256)
                VALUES (%s,'bounded synthetic reasoning task','work-order:engineering',
                        'steward:test','[\"record a proposal only\"]'::jsonb,'GROUNDED',
                        %s::jsonb,%s)""").format(sql.Identifier(self.schema)),
                (objective, json.dumps({"status": "VERIFIED", "retrieval_complete": True,
                    "source_references": ["test://source"], "source_sha256": "d" * 64}), "d" * 64))
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

    def _grace_service(self, exchange):
        from riverview_core.institutional_authority import ExactGrantAuthorizer
        from riverview_core.resident_execution.pipeline import GraceExecutionPipeline, ObjectiveContextReader
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.resident_reasoning import ResidentReasoner
        authority = ExactGrantAuthorizer(self.schema)
        pipeline = GraceExecutionPipeline(self.ledger, authority,
            AuthorizedAssignmentIntake(self.ledger, authority), _ResumeKnowledge())
        reasoner = ResidentReasoner(registry=self.reasoning_state, office_id=RESIDENT,
            resident_credential="fixture-resident-credential", assignments=ObjectiveContextReader(pipeline),
            knowledge=_ResumeKnowledge(), providers={"reasoner:test": self.grace_provider},
            timeout_seconds=1)
        return GraceExecutionService(pipeline, object(), object(),
            dispatch_credential="unused-in-consumer-test", authority_ref="work-order:engineering",
            verifier_id="verifier:test", verifier_credential="unused", artifact_root="/tmp",
            verifier=object(), resident_reasoner=reasoner,
            external_reasoning_exchange=exchange,
            external_reasoning_authorize=self.authorized,
            external_reasoning_principal=RESIDENT)

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

    def _grace_submit(self, exchange, *, idem):
        grace = self._grace_service(exchange)
        return grace.request_external_reasoning(self.envelope, self.original,
            conversation_id=self.conversation_id, message_sequence=4,
            idempotency_key=idem, deadline_at=self.clock_value + timedelta(minutes=5),
            classification="institutional", source_references=("test://synthetic-context",))

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
        receipt = self._grace_submit(self.exchange, idem="roundtrip")
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
        # The production Grace cycle consumes the persisted exchange, reasons
        # over the typed advisory, atomically records the unapproved proposal,
        # and acknowledges only after that durable objective event exists.
        grace = self._grace_service(self.exchange)
        pipeline = grace.pipeline
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "grace_consumed")
        evaluation = [event for event in pipeline.objective_events(self.objective)
            if event["event_type"] == "resident.reasoning.external_advisory_evaluated"]
        self.assertEqual(len(evaluation), 1)
        self.assertEqual(evaluation[0]["payload"]["request_id"], receipt.request_id)
        self.assertEqual(evaluation[0]["payload"]["decision"],
                         "advisory_evaluated_as_unapproved_proposal")
        self.assertEqual(grace.consume_external_reasoning(), 0)
        again = self.exchange.consume(receipt.request_id, receipt.correlation_id,
            principal_id=RESIDENT, authorize=self.authorized)
        self.assertTrue(again.duplicate)
        self.assertEqual(again.advisory["advisory"], response["advisory"])
        self.assertEqual(grace.consume_external_reasoning(), 0)
        evaluation_key = evaluation[0]["idempotency_key"]
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
        self.assertEqual(objective[0], "PROPOSED")
        self.assertIsNone(objective[1])
        self.assertIsInstance(objective[2], dict)

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

    def test_mcp_provider_scoped_round_trip_uses_durable_exchange(self):
        from riverview_core.resident_execution.external_reasoning_mcp import ExternalProviderRegistration
        from riverview_core.resident_execution.external_reasoning_mcp import exchange_runtime_readiness

        self.assertEqual(exchange_runtime_readiness(self.ledger),
                         {"status": "healthy", "error_code": None})

        token = "isolated-postgres-mcp-provider-token-000000000001"
        token_map = ProviderTokenMap.from_document({
            "schema_version": ProviderTokenMap.SCHEMA,
            "tokens": [{"token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                "provider_id": PROVIDER, "principal_id": PROVIDER,
                "scopes": ["reasoning:exchange"],
                "expires_at": "2099-01-01T00:00:00Z"}]})
        provider = ExternalProviderRegistration(PROVIDER, PROVIDER)
        mcp_exchange = DurableExternalReasoningExchange(self.ledger,
            ReasoningEscalationRouter({PROVIDER: provider}), actor_id=RESIDENT,
            clock=lambda: self.clock_value)
        adapter = ExternalReasoningMCPAdapter(mcp_exchange, token_map)
        receipt = self._grace_submit(mcp_exchange, idem="mcp-round-trip")
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        server = create_server(adapter, host="127.0.0.1", port=port,
            resource_url="https://mcp.example.test/mcp",
            authorization_server_url="https://identity.example.test/")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def rpc(method, request_id, params=None):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            body = json.dumps({"jsonrpc": "2.0", "id": request_id,
                "method": method, "params": params or {}})
            headers = {"Host": "127.0.0.1", "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-11-25", "Mcp-Method": method}
            if method == "tools/call":
                headers["Mcp-Name"] = params["name"]
            connection.request("POST", "/mcp", body=body, headers=headers)
            response = connection.getresponse()
            raw, status = response.read(), response.status
            connection.close()
            self.assertEqual(status, 200)
            return json.loads(raw)

        try:
            initialized = rpc("initialize", "init", {
                "protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "postgres-exchange-independent-client", "version": "1.0"}})
            self.assertEqual(initialized["result"]["protocolVersion"], "2025-11-25")
            tools = rpc("tools/list", "tools", {})["result"]["tools"]
            self.assertEqual(len(tools), 4)

            def tool(name, request_id, arguments):
                result = rpc("tools/call", request_id, {"name": name,
                    "arguments": arguments})["result"]
                self.assertFalse(result["isError"])
                return json.loads(result["content"][0]["text"])

            listed = tool("reasoning_exchange_list_requests", "list", {"limit": 2})
            self.assertEqual(listed["count"], 1)
            self.assertEqual(listed["requests"][0]["request_id"], receipt.request_id)
            self.assertNotIn("delivery_token", listed["requests"][0])
            self.assertEqual(mcp_exchange.status(receipt.request_id,
                receipt.correlation_id)["delivery_state"], "awaiting_external_claim")

            claim = tool("reasoning_exchange_claim_request", "claim", {
                "request_id": receipt.request_id, "correlation_id": receipt.correlation_id})
            self.assertEqual(claim["fence"], 1)
            response = self._response(receipt, advisory="Bounded MCP synthetic advisory")
            submitted = tool("reasoning_exchange_submit_response", "submit", {
                "request_id": receipt.request_id, "correlation_id": receipt.correlation_id,
                "claim_token": claim["claim_token"], "fence": claim["fence"],
                "idempotency_key": "mcp-response-1", "response": response})
            self.assertEqual(submitted["state"], "response_received")
            status = tool("reasoning_exchange_status", "status", {
                "request_id": receipt.request_id, "correlation_id": receipt.correlation_id})
            self.assertEqual(status["delivery_state"], "response_received")
            self.assertEqual(status["response_sha256"], submitted["response_sha256"])
            self.assertNotIn("response_payload", status)
            self.assertNotIn("reasoning_exchange_consume", {x["name"] for x in tools})
            grace = self._grace_service(mcp_exchange)
            self.assertEqual(grace.consume_external_reasoning(), 1)
            self.assertEqual(mcp_exchange.status(receipt.request_id,
                receipt.correlation_id)["delivery_state"], "grace_consumed")
            records = [event for event in grace.pipeline.objective_events(self.objective)
                if event["event_type"] == "resident.reasoning.external_advisory_evaluated"]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["payload"]["provider_id"], PROVIDER)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
