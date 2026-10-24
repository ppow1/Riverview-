# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_external_reasoning_exchange.py
# Component: RESIDENT-REASONING
# Revision: 1.1.2
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Preserve and digest-bind lifecycle criteria in externally reviewed proposals
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Verify sanitized C2 exception receipts terminate without duplicate wake retries.
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Verify duplicate receipt replay remains bound to the original lease token.
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Verify deterministic doorbell attempt identity using disposable PostgreSQL.
# Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Verify body-free doorbell claims, single-use receipts, retries, and ambiguity fencing.
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
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Exercise restart after proposal/evaluation persistence but before exchange acknowledgement.
# Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Exercise typed reasoning initiation and distinguish active office from resident principal identities.
# Changed: 2026-10-18 UTC | RV-C3-EXACT-PROPOSAL-REVIEW-001 | Verify digest enforcement, exact finish/revision, and successor crash recovery.
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Exercise Steward discovery, delivery, fenced claim and advisory submission using the actual restricted runtime role.
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Fix JSONB path escaping and verify durable Steward response provenance.
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""PostgreSQL acceptance tests for the transport-neutral exchange contract."""

import os
import hashlib
import http.client
import json
import secrets
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
from riverview_core.resident_reasoning import ExternalEscalationIntent, ReasoningRequest


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
PROVIDER = "simulated:chatgpt-reasoning"
OFFICE = "office:grace"
RESIDENT = "resident:grace-test"


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

    def __init__(self, *, initiate_external=False):
        self.requests = []
        self.initiate_external = initiate_external
        self.revise_once = False

    def propose(self, request):
        from riverview_core.resident_reasoning import PlanProposal, PlanStep
        self.requests.append(request)
        if request.review_subject is not None:
            reviewed = request.review_subject["proposal"]
            steps = []
            for item in reviewed["steps"]:
                item = dict(item)
                for key in ("acceptance_criteria", "depends_on", "authorized_paths", "test_targets"):
                    item[key] = tuple(item[key])
                steps.append(PlanStep(**item))
            summary = reviewed["summary"]
            if self.revise_once:
                self.revise_once = False
                summary = "synthetic reviewed revision"
            return PlanProposal(summary, tuple(steps), 5,
                provider_id=self.provider_id, served_model="fixture-reasoner",
                model_revision="c" * 64, reasoning_stage="reasoning")
        return PlanProposal("evaluate advisory", (PlanStep("review", "Review advice",
            ("record a proposal only",)),), 5, provider_id=self.provider_id,
            served_model="fixture-reasoner", model_revision="c" * 64,
            reasoning_stage="reasoning",
            external_escalation=(ExternalEscalationIntent("task_complexity", PROVIDER)
                if self.initiate_external and request.external_advisory is None else None))


class ReviewSubjectUnitTests(unittest.TestCase):
    def test_direct_luna_normalizes_database_uuid_before_response_and_idempotency(self):
        from riverview_core.resident_execution.direct_luna import _response_ids
        request_id, correlation_id = uuid4(), uuid4()
        normalized = _response_ids({"request_id": request_id, "correlation_id": correlation_id})
        self.assertEqual(normalized, (str(request_id), str(correlation_id)))
        self.assertEqual("luna:" + normalized[0], "luna:" + str(request_id))

    def test_event_origin_exchange_is_typed_and_conversation_hash_shape_is_unchanged(self):
        from riverview_core.resident_execution.external_reasoning import DurableExternalReasoningExchange
        request = ReasoningRequest(request_id=str(uuid4()), office_id=OFFICE,
            assignment_id="objective:" + uuid4().hex, assignment_revision="6",
            binding_revision=1, implementation_revision="a" * 64,
            trigger="cme_diagnostic_recovery", token_budget=32,
            assignment={"cme_event_id": str(uuid4())}, verified_knowledge=(), prior_plan=None)
        validate = DurableExternalReasoningExchange._validate_origin
        validate(request, originating_resident_id=RESIDENT,
            objective_id=request.assignment_id, conversation_id=None, message_sequence=None,
            proposal_id="proposal:test", proposal_revision=2,
            classification="institutional", source_kind="cme_diagnostic_recovery",
            request_type="cme_diagnostic_recovery")
        with self.assertRaisesRegex(ValueError, "request type and source kind"):
            validate(request, originating_resident_id=RESIDENT,
                objective_id=request.assignment_id, conversation_id=None, message_sequence=None,
                proposal_id="proposal:test", proposal_revision=2,
                classification="institutional", source_kind="performance_evaluation",
                request_type="cme_diagnostic_recovery")
        with self.assertRaisesRegex(ValueError, "conversation_id must be a UUID"):
            validate(request, originating_resident_id=RESIDENT,
                objective_id=request.assignment_id, conversation_id="not-a-uuid", message_sequence=1,
                proposal_id="proposal:test", proposal_revision=2,
                classification="institutional", source_kind="conversation",
                request_type="objective_reasoning")

    def test_subject_uses_agreed_canonical_hash_and_rejects_tampering(self):
        from riverview_core.resident_execution.external_reasoning import (
            build_review_subject, validate_review_subject)
        from riverview_core.resident_reasoning import PlanProposal, PlanStep
        subject_id = str(uuid4())
        proposal = PlanProposal("bounded proposal", (PlanStep("step-1", "review",
            ("keep advisory unapproved",)),), 19, provider_id="model:local",
            served_model="fixture", model_revision="c" * 64, reasoning_stage="reasoning",
            system_owned_criteria=("The objective is completed.",))
        subject = build_review_subject(subject_id, 1, proposal)
        self.assertEqual(subject["proposal"]["system_owned_criteria"],
                         ["The objective is completed."])
        canonical = json.dumps({"subject_id": subject_id, "revision": 1,
            "proposal": subject["proposal"]}, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")
        self.assertEqual(subject["sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(validate_review_subject(subject), subject)
        routed = ExternalReasoningMCPAdapter._review_subject(
            {}, {"review_subject": subject})
        self.assertEqual(routed, subject,
                         "the provider-facing MCP contract preserves digest-bound lifecycle criteria")
        changed = {**subject, "proposal": {**subject["proposal"], "summary": "changed"}}
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            validate_review_subject(changed)
        malformed = {**subject, "proposal": {**subject["proposal"],
            "steps": [{**subject["proposal"]["steps"][0], "unexpected": "x"}]}}
        with self.assertRaisesRegex(ValueError, "review subject content is invalid"):
            validate_review_subject(malformed)

    def test_grace_execution_service_polls_optional_doorbell_worker(self):
        from riverview_core.resident_execution.service import GraceExecutionService

        class Worker:
            def run_once(self):
                return {"status": "SUBMITTED", "request_id": "private-id"}

        service = GraceExecutionService(None, None, object(), dispatch_credential="d",
            authority_ref="work-order:test", verifier_id="v", verifier_credential="v",
            artifact_root="/tmp/unused", doorbell_worker=Worker())
        self.assertEqual(service._run_doorbell_worker(), {"status": "SUBMITTED"})
        service.doorbell_worker = None
        self.assertEqual(service._run_doorbell_worker(), {"status": "NOT_CONFIGURED"})


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
        self.real_authority_fixture = None
        self.admin.execute(sql.SQL("""INSERT INTO {}.grace_objective_events
            (objective_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,'objective.received',%s,'steward:test',%s::jsonb)""").format(
                sql.Identifier(self.schema)),
            (self.objective, "test-origin:" + self.objective,
             json.dumps({"origin": {"conversation_id": self.conversation_id,
                                    "source_sequence": 4}})))

    def _service(self, clock=None):
        return DurableExternalReasoningExchange(self.ledger, self.router,
            actor_id=RESIDENT, clock=clock or (lambda: self.clock_value))

    def _grace_service(self, exchange, *, initiate_external=False, targets=()):
        from riverview_core.institutional_authority import ExactGrantAuthorizer
        from riverview_core.resident_execution.pipeline import GraceExecutionPipeline, ObjectiveContextReader
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.resident_reasoning import ResidentReasoner
        authority = ExactGrantAuthorizer(self.schema)
        pipeline = GraceExecutionPipeline(self.ledger, authority,
            AuthorizedAssignmentIntake(self.ledger, authority), _ResumeKnowledge())
        self.grace_provider.initiate_external = initiate_external
        reasoner = ResidentReasoner(registry=self.reasoning_state, office_id=OFFICE,
            resident_credential="fixture-resident-credential", assignments=ObjectiveContextReader(pipeline),
            knowledge=_ResumeKnowledge(), providers={"reasoner:test": self.grace_provider},
            external_reasoning_targets=tuple(targets),
            timeout_seconds=1)
        return GraceExecutionService(pipeline, object(), object(),
            dispatch_credential="unused-in-consumer-test", authority_ref="work-order:engineering",
            verifier_id="verifier:test", verifier_credential="unused", artifact_root="/tmp",
            verifier=object(), resident_reasoner=reasoner,
            external_reasoning_exchange=exchange,
            external_reasoning_authorize=self.authorized,
            external_reasoning_principal=RESIDENT)

    def _real_exchange_authority(self):
        """Build the production AuthorityRegistry contract in this disposable schema."""
        from riverview_core.institutional_authority import AuthorityRegistry

        if self.real_authority_fixture is not None:
            return self.real_authority_fixture
        registry = AuthorityRegistry(DSN, schema=self.schema)
        steward_id = "steward:" + uuid4().hex
        steward_token = secrets.token_urlsafe(32)
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.institutional_principals
            (principal_id,principal_kind) VALUES (%s,'steward')""").format(
                self.sql.Identifier(self.schema)), (steward_id,))
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.principal_credentials
            (credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)""").format(
                self.sql.Identifier(self.schema)), (uuid4(), steward_id,
                hashlib.sha256(steward_token.encode()).digest()))
        for action in ("authority.grant", "identity.manage", "office.manage"):
            self.admin.execute(self.sql.SQL("""INSERT INTO {}.authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                VALUES (%s,%s,%s,'institution',%s,'rv.policy:test-bootstrap.v1')""").format(
                    self.sql.Identifier(self.schema)),
                ("bootstrap:" + action + ":" + uuid4().hex, steward_id, action, steward_id))
        registry.create_office(steward_token, OFFICE, "Director of Operations")
        resident_token = registry.create_principal(steward_token, RESIDENT, "resident",
                                                   office_id=OFFICE)
        occupant_id = "occupant:" + uuid4().hex
        implementation_id = "implementation:" + uuid4().hex
        registry.create_occupant(steward_token, occupant_id, principal_id=RESIDENT)
        registry.create_implementation(steward_token, implementation_id, kind="model",
            provider_ref="reasoner:test", revision="model-revision:test")
        registry.bind_office(steward_token, OFFICE, occupant_id, implementation_id)
        registry.grant(steward_token, RESIDENT, "office.state.write", "office:" + OFFICE,
            policy_ref="rv.policy:test-runtime.v1")
        registry.grant(steward_token, RESIDENT, ReasoningEscalationRouter.ACTION,
            "provider:" + PROVIDER, policy_ref="rv.policy:test-escalation.v1")
        self.real_authority_fixture = (registry, resident_token)
        return self.real_authority_fixture

    def _real_authorizer(self, *, provider_id=PROVIDER):
        from riverview_core.institutional_authority import ExactGrantAuthorizer
        from scripts.run_grace_execution_service import (
            active_resident_principal, external_exchange_configuration)

        registry, credential = self._real_exchange_authority()
        snapshot = registry.authorize_office_state(credential, OFFICE)
        principal = active_resident_principal(snapshot)
        exchange, authorize = external_exchange_configuration({
            "RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP":
                json.dumps({provider_id: "provider:external-test"})},
            ledger=self.ledger, authorizer=ExactGrantAuthorizer(self.schema),
            authority_registry=registry, resident_credential=credential,
            office_id=OFFICE, principal_id=principal)
        self.assertIsNotNone(exchange)
        return registry, credential, principal, exchange, authorize, snapshot

    def tearDown(self):
        if self.real_authority_fixture is not None:
            registry = self.real_authority_fixture[0]
            if not registry.db.closed:
                registry.db.close()
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

    def _deliver_and_claim(self, receipt, *, lease=120, exchange=None,
                           principal_id=PROVIDER):
        exchange = exchange or self.exchange
        delivery = exchange.begin_delivery(receipt.request_id, PROVIDER,
            owner_id="transport:test", lease_seconds=30)
        self.assertIsNotNone(delivery)
        self.assertEqual(exchange.mark_delivered(receipt.request_id,
            receipt.correlation_id, PROVIDER, owner_id="transport:test",
            delivery_token=delivery.claim_token, fence=delivery.fence), "awaiting_external_claim")
        self.assertEqual(exchange.mark_delivered(receipt.request_id,
            receipt.correlation_id, PROVIDER, owner_id="transport:test",
            delivery_token=delivery.claim_token, fence=delivery.fence), "awaiting_external_claim")
        return exchange.claim(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=principal_id, lease_seconds=lease)

    def _real_grace_service(self, *, authority=None):
        from riverview_core.institutional_authority import ExactGrantAuthorizer
        from riverview_core.resident_execution.pipeline import (
            GraceExecutionPipeline, ObjectiveContextReader)
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.resident_reasoning import ResidentReasoner

        if authority is None:
            registry, credential, principal, exchange, authorize, _snapshot = (
                self._real_authorizer())
        else:
            from riverview_core.institutional_authority import ExactGrantAuthorizer
            from scripts.run_grace_execution_service import (
                active_resident_principal, external_exchange_configuration)
            registry, credential = authority
            snapshot = registry.authorize_office_state(credential, OFFICE)
            principal = active_resident_principal(snapshot)
            exchange, authorize = external_exchange_configuration({
                "RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP":
                    json.dumps({PROVIDER: "provider:external-test"})},
                ledger=self.ledger, authorizer=ExactGrantAuthorizer(self.schema),
                authority_registry=registry, resident_credential=credential,
                office_id=OFFICE, principal_id=principal)
        pipeline = GraceExecutionPipeline(self.ledger, ExactGrantAuthorizer(self.schema),
            AuthorizedAssignmentIntake(self.ledger, ExactGrantAuthorizer(self.schema)),
            _ResumeKnowledge())
        self.grace_provider.initiate_external = True
        reasoner = ResidentReasoner(registry=registry, office_id=OFFICE,
            resident_credential=credential, assignments=ObjectiveContextReader(pipeline),
            knowledge=_ResumeKnowledge(), providers={"reasoner:test": self.grace_provider},
            external_reasoning_targets=(PROVIDER,), timeout_seconds=1)
        grace = GraceExecutionService(pipeline, object(), object(),
            dispatch_credential="unused-in-consumer-test", authority_ref="work-order:engineering",
            verifier_id="verifier:test", verifier_credential="unused", artifact_root="/tmp",
            verifier=object(), resident_reasoner=reasoner,
            external_reasoning_exchange=exchange,
            external_reasoning_authorize=authorize,
            external_reasoning_principal=principal)
        return registry, credential, principal, exchange, authorize, grace

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

        reasoner = ResidentReasoner(registry=self.reasoning_state, office_id=OFFICE,
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
        # The production Grace cycle consumes the persisted exchange, reasons
        # over the typed advisory and atomically records the unapproved proposal.
        # Simulate process loss after that commit but before exchange ack.
        grace = self._grace_service(self.exchange)
        pipeline = grace.pipeline
        acknowledge = self.exchange.acknowledge_consumed
        def fail_first_ack(*args, **kwargs):
            raise RuntimeError("simulated_acknowledgement_interruption")
        self.exchange.acknowledge_consumed = fail_first_ack
        self.assertEqual(grace.consume_external_reasoning(), 0)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "response_received")
        evaluation = [event for event in pipeline.objective_events(self.objective)
            if event["event_type"] == "resident.reasoning.external_advisory_evaluated"]
        self.assertEqual(len(evaluation), 1)
        self.assertEqual(evaluation[0]["payload"]["request_id"], receipt.request_id)
        self.assertEqual(evaluation[0]["payload"]["decision"],
                         "advisory_evaluated_as_unapproved_proposal")
        self.assertEqual(self.grace_provider.requests[-1].external_advisory["advisory"],
                         response["advisory"])
        self.assertNotIn(response["advisory"], str(self.grace_provider.requests[-1].verified_knowledge))
        reasoner_calls = len(self.grace_provider.requests)
        # A restarted exchange/service sees the durable evaluation and performs
        # only the fenced acknowledgement, without invoking the reasoner again.
        self.exchange.acknowledge_consumed = acknowledge
        self.ledger.close()
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.exchange = self._service()
        grace = self._grace_service(self.exchange)
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(len(self.grace_provider.requests), reasoner_calls)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "grace_consumed")
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

    def test_grounded_reasoning_decision_initiates_and_consumes_durable_exchange(self):
        grace = self._grace_service(self.exchange, initiate_external=True,
                                    targets=(PROVIDER,))
        self.assertTrue(grace.reason_one_grounded_objective(self.objective))
        self.assertEqual(grace.pipeline.get_objective(self.objective)["status"], "GROUNDED")
        self.assertTrue(self.exchange.has_active_for_objective(self.objective))
        row = self.admin.execute(self.sql.SQL("""SELECT request_id,correlation_id,
                delivery_state,originating_resident_id,conversation_id,message_sequence,request_payload
            FROM {}.external_reasoning_exchanges WHERE objective_id=%s""").format(
                self.sql.Identifier(self.schema)), (self.objective,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[3], RESIDENT)
        self.assertEqual(str(row[4]), self.conversation_id)
        self.assertEqual(row[5], 4)
        subject = row[6]["review_subject"]
        self.assertEqual(subject["revision"], 1)
        self.assertEqual(self.exchange.status(str(row[0]), str(row[1]))[
            "review_subject_sha256"], subject["sha256"])
        self.assertNotIn(self.objective,
            self.reasoning_state.state.get("resident_reasoning_v1", {}).get("plans", {}))
        receipt = type("Receipt", (), {"request_id": str(row[0]),
            "correlation_id": str(row[1]), "delivery_state": row[2]})()
        claim = self._deliver_and_claim(receipt)
        response = self._response(receipt)
        with self.assertRaisesRegex(ExchangeConflict, "review_subject_digest_mismatch"):
            self.exchange.submit_response(receipt.request_id, receipt.correlation_id,
                provider_id=PROVIDER, principal_id=PROVIDER, claim_token=claim.claim_token,
                fence=claim.fence, idempotency_key="response:missing-review-digest",
                response=response)
        self.exchange.submit_response(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=PROVIDER, claim_token=claim.claim_token,
            fence=claim.fence, idempotency_key="response:reasoning-initiated",
            response=response, review_subject_sha256=subject["sha256"])
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "grace_consumed")
        self.assertEqual(grace.pipeline.get_objective(self.objective)["status"], "PROPOSED")
        self.assertFalse(self.exchange.has_active_for_objective(self.objective))
        events = grace.pipeline.objective_events(self.objective)
        reviewed = [event for event in events if event["event_type"] ==
                    "resident.reasoning.external_proposal_reviewed"]
        self.assertEqual(len(reviewed), 1)
        self.assertEqual(reviewed[0]["payload"]["subject_sha256"], subject["sha256"])
        self.assertEqual(reviewed[0]["payload"]["decision"], "finish")

    def test_exact_review_can_revise_then_finish_with_a_new_correlated_subject(self):
        grace = self._grace_service(self.exchange, initiate_external=True,
                                    targets=(PROVIDER,))
        self.grace_provider.revise_once = True
        self.assertTrue(grace.reason_one_grounded_objective(self.objective))
        first = self.admin.execute(self.sql.SQL("""SELECT request_id::text,correlation_id::text,
                request_payload FROM {}.external_reasoning_exchanges WHERE objective_id=%s""").format(
                    self.sql.Identifier(self.schema)), (self.objective,)).fetchone()
        self.assertEqual(first[2]["review_subject"]["revision"], 1)
        receipt = type("Receipt", (), {"request_id": first[0], "correlation_id": first[1]})()
        claim = self._deliver_and_claim(receipt)
        self.exchange.submit_response(first[0], first[1], provider_id=PROVIDER,
            principal_id=PROVIDER, claim_token=claim.claim_token, fence=claim.fence,
            idempotency_key="response:review-revise-1", response=self._response(receipt),
            review_subject_sha256=first[2]["review_subject"]["sha256"])
        record_decision = grace.pipeline.record_external_review_decision
        def interrupt_after_child_admission(*args, **kwargs):
            raise RuntimeError("synthetic_restart_after_successor_admission")
        grace.pipeline.record_external_review_decision = interrupt_after_child_admission
        self.assertEqual(grace.consume_external_reasoning(), 0)
        grace.pipeline.record_external_review_decision = record_decision
        reasoner_calls = len(self.grace_provider.requests)
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(len(self.grace_provider.requests), reasoner_calls)
        child = self.admin.execute(self.sql.SQL("""SELECT request_id::text,correlation_id::text,
                request_payload FROM {}.external_reasoning_exchanges
            WHERE request_payload->'review_parent'->>'request_id'=%s""").format(
                self.sql.Identifier(self.schema)), (first[0],)).fetchone()
        self.assertIsNotNone(child)
        self.assertEqual(child[2]["review_subject"]["revision"], 2)
        self.assertFalse(self.exchange.has_terminal_review_for_objective(self.objective))
        revised_events = [event for event in grace.pipeline.objective_events(self.objective)
            if event["event_type"] == "resident.reasoning.external_proposal_revised"]
        self.assertEqual(len(revised_events), 1)
        child_receipt = type("Receipt", (), {"request_id": child[0],
            "correlation_id": child[1]})()
        child_claim = self._deliver_and_claim(child_receipt)
        self.exchange.submit_response(child[0], child[1], provider_id=PROVIDER,
            principal_id=PROVIDER, claim_token=child_claim.claim_token,
            fence=child_claim.fence, idempotency_key="response:review-revise-2",
            response=self._response(child_receipt, advisory="synthetic second review"),
            review_subject_sha256=child[2]["review_subject"]["sha256"])
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(grace.pipeline.get_objective(self.objective)["status"], "PROPOSED")
        final_events = [event for event in grace.pipeline.objective_events(self.objective)
            if event["event_type"] == "resident.reasoning.external_proposal_reviewed"]
        self.assertEqual(len(final_events), 1)
        self.assertEqual(final_events[0]["payload"]["revision"], 2)
        self.assertTrue(self.exchange.has_terminal_review_for_objective(self.objective))

    def test_real_authority_registry_allows_only_bound_principal_and_exact_provider_scope(self):
        from riverview_core.institutional_authority import GrantDenied
        from riverview_core.reasoning_escalation import EscalationStatus

        _registry, _credential, principal, _exchange, authorize, _snapshot = self._real_authorizer()
        self.assertEqual(principal, RESIDENT)
        self.assertIs(authorize(principal, ReasoningEscalationRouter.ACTION,
                                "provider:" + PROVIDER), True)
        with self.assertRaises(GrantDenied):
            authorize("resident:unbound", ReasoningEscalationRouter.ACTION,
                      "provider:" + PROVIDER)
        with self.assertRaises(GrantDenied):
            authorize(principal, ReasoningEscalationRouter.ACTION, "provider:other")

        other_provider = "provider:ungranted"
        _registry, _credential, principal, other_exchange, authorize, _snapshot = (
            self._real_authorizer(provider_id=other_provider))
        other_envelope = EscalationRequest.create(self.original,
            reason="task_complexity", target_provider_id=other_provider,
            max_tokens=64, timeout_seconds=10)
        decision = other_exchange.router.authorize_for_durable_exchange(
            other_envelope, self.original, principal_id=principal, authorize=authorize)
        self.assertIs(decision.status, EscalationStatus.DENIED)

    def test_real_authority_registry_admits_durable_exchange_only_with_exact_grant(self):
        registry, credential, principal, exchange, authorize, snapshot = self._real_authorizer()
        original = self.original.__class__(**{**self.original.__dict__,
            "binding_revision": snapshot["binding_revision"],
            "implementation_revision": snapshot["implementation_revision"]})
        envelope = EscalationRequest.create(original, reason="task_complexity",
            target_provider_id=PROVIDER, max_tokens=64, timeout_seconds=10)
        receipt = exchange.submit(envelope, original, principal_id=principal,
            authorize=authorize, originating_resident_id=principal,
            objective_id=self.objective, conversation_id=self.conversation_id,
            message_sequence=4, idempotency_key="authority-approved:" + uuid4().hex,
            classification="institutional", deadline_at=self.clock_value + timedelta(minutes=5),
            source_references=("test://verified-evidence",))
        self.assertEqual(receipt.delivery_state, "awaiting_delivery")
        row = self.admin.execute(self.sql.SQL("""SELECT originating_resident_id,provider_id,
            delivery_state FROM {}.external_reasoning_exchanges WHERE request_id=%s""").format(
                self.sql.Identifier(self.schema)), (receipt.request_id,)).fetchone()
        self.assertEqual(row, (RESIDENT, PROVIDER, "awaiting_delivery"))

        # A registered second provider has no exact grant. It is rejected before
        # any outbox row is written, even though the resident has another grant.
        other_provider = "provider:ungranted"
        _registry, _credential, _principal, denied_exchange, denied_authorize, _snapshot = (
            self._real_authorizer(provider_id=other_provider))
        denied_original = original.__class__(**{**original.__dict__,
            "request_id": str(uuid4())})
        denied_envelope = EscalationRequest.create(denied_original,
            reason="task_complexity", target_provider_id=other_provider,
            max_tokens=64, timeout_seconds=10)
        with self.assertRaises(ExchangeUnauthorized):
            denied_exchange.submit(denied_envelope, denied_original,
                principal_id=principal, authorize=denied_authorize,
                originating_resident_id=principal, objective_id=self.objective,
                conversation_id=self.conversation_id, message_sequence=4,
                idempotency_key="authority-denied:" + uuid4().hex,
                classification="institutional",
                deadline_at=self.clock_value + timedelta(minutes=5))

    def test_real_authority_registry_grace_initiates_and_consumes_exchange(self):
        (registry, credential, principal, exchange, _authorize, grace) = (
            self._real_grace_service())
        self.exchange = exchange
        self.assertTrue(grace.reason_one_grounded_objective(self.objective))
        row = self.admin.execute(self.sql.SQL("""SELECT request_id,correlation_id,provider_id,
            delivery_state,originating_resident_id,conversation_id,message_sequence,request_payload
            FROM {}.external_reasoning_exchanges WHERE objective_id=%s""").format(
                self.sql.Identifier(self.schema)), (self.objective,)).fetchone()
        self.assertEqual(row[2:5], (PROVIDER, "awaiting_delivery", principal))
        self.assertEqual(str(row[5]), self.conversation_id)
        self.assertEqual(row[6], 4)
        self.assertIn("review_subject", row[7])
        receipt = type("Receipt", (), {"request_id": str(row[0]),
            "correlation_id": str(row[1]), "delivery_state": row[3]})()
        provider_principal = "provider:external-test"
        claim = self._deliver_and_claim(receipt, exchange=exchange,
                                        principal_id=provider_principal)
        response = self._response(receipt)
        exchange.submit_response(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=provider_principal,
            claim_token=claim.claim_token, fence=claim.fence,
            idempotency_key="response:real-authority:" + uuid4().hex,
            response=response, review_subject_sha256=exchange.status(
                receipt.request_id, receipt.correlation_id)["review_subject_sha256"])
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "grace_consumed")
        events = grace.pipeline.objective_events(self.objective)
        evaluation = [event for event in events if event["event_type"] ==
                      "resident.reasoning.external_advisory_evaluated"]
        self.assertEqual(len(evaluation), 1)
        self.assertEqual(evaluation[0]["payload"]["request_id"], receipt.request_id)
        self.assertEqual(grace.pipeline.get_objective(self.objective)["status"], "PROPOSED")

    def test_real_authority_registry_exchange_survives_restart_before_grace_consumption(self):
        (registry, credential, principal, exchange, _authorize, grace) = (
            self._real_grace_service())
        self.exchange = exchange
        self.assertTrue(grace.reason_one_grounded_objective(self.objective))
        row = self.admin.execute(self.sql.SQL("""SELECT request_id,correlation_id,request_payload
            FROM {}.external_reasoning_exchanges WHERE objective_id=%s""").format(
                self.sql.Identifier(self.schema)), (self.objective,)).fetchone()
        receipt = type("Receipt", (), {"request_id": str(row[0]),
            "correlation_id": str(row[1]), "delivery_state": "awaiting_delivery"})()
        provider_principal = "provider:external-test"
        claim = self._deliver_and_claim(receipt, exchange=exchange,
                                        principal_id=provider_principal)
        exchange.submit_response(receipt.request_id, receipt.correlation_id,
            provider_id=PROVIDER, principal_id=provider_principal,
            claim_token=claim.claim_token, fence=claim.fence,
            idempotency_key="response:restart-before-consume:" + uuid4().hex,
            response=self._response(receipt),
            review_subject_sha256=row[2]["review_subject"]["sha256"])

        self.ledger.close()
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        registry, credential, principal, exchange, _authorize, grace = (
            self._real_grace_service(authority=(registry, credential)))
        self.exchange = exchange
        self.assertEqual(grace.consume_external_reasoning(), 1)
        self.assertEqual(exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "grace_consumed")
        self.assertTrue(any(event["event_type"] ==
            "resident.reasoning.external_advisory_evaluated"
            for event in grace.pipeline.objective_events(self.objective)))
        self.assertEqual(principal, RESIDENT)

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

    def test_doorbell_claim_is_body_free_and_receipt_is_idempotent(self):
        receipt = self._submit(idem="doorbell-receipt-success")
        claim = self.exchange.claim_next_doorbell_request(PROVIDER, "doorbell:test", 90)
        self.assertIsNotNone(claim)
        self.assertEqual((claim.request_id, claim.correlation_id, claim.provider_id),
                         (receipt.request_id, receipt.correlation_id, PROVIDER))
        self.assertTrue(claim.attempt_id)
        self.assertNotIn("request_payload", repr(claim))
        self.assertEqual(self.exchange.claim_next_doorbell_request(
            PROVIDER, "other-doorbell", 90), None)
        transition = self.exchange.record_doorbell_receipt(
            claim.request_id, claim.correlation_id, PROVIDER, "doorbell:test",
            claim.attempt_id, claim.lease_token, claim.fence, "submitted", None)
        self.assertEqual(transition, "awaiting_external_claim")
        self.assertEqual(self.exchange.record_doorbell_receipt(
            claim.request_id, claim.correlation_id, PROVIDER, "doorbell:test",
            claim.attempt_id, claim.lease_token, claim.fence, "submitted", None), transition)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "awaiting_external_claim")
        with self.ledger.db.cursor() as cur:
            self.exchange._set_path(cur)
            cur.execute("""SELECT count(*) AS count FROM external_reasoning_exchange_events
                WHERE request_id=%s AND event_type='doorbell_receipt'""", (receipt.request_id,))
            self.assertEqual(cur.fetchone()["count"], 1)
        with self.assertRaises(ExchangeConflict):
            self.exchange.record_doorbell_receipt(claim.request_id, claim.correlation_id,
                PROVIDER, "doorbell:test", claim.attempt_id, claim.lease_token,
                claim.fence, "ambiguous", "RIV-PLY-0009")

    def test_doorbell_known_pre_send_failure_uses_existing_bounded_retry(self):
        receipt = self._submit(idem="doorbell-pre-send-failure")
        claim = self.exchange.claim_next_doorbell_request(PROVIDER, "doorbell:test", 90)
        self.assertEqual(self.exchange.record_doorbell_receipt(
            claim.request_id, claim.correlation_id, PROVIDER, "doorbell:test",
            claim.attempt_id, claim.lease_token, claim.fence, "failed", "RIV-PLY-0007"),
            "awaiting_delivery")
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["last_error_code"], "riv_ply_0007")
        self.assertIsNone(self.exchange.claim_next_doorbell_request(
            PROVIDER, "doorbell:test", 90))
        self.clock_value += timedelta(seconds=3)
        retried = self.exchange.claim_next_doorbell_request(PROVIDER, "doorbell:test", 90)
        self.assertGreater(retried.fence, claim.fence)
        self.assertNotEqual(retried.attempt_id, claim.attempt_id)

    def test_doorbell_ambiguous_failure_is_terminal_and_fenced(self):
        receipt = self._submit(idem="doorbell-ambiguous")
        claim = self.exchange.claim_next_doorbell_request(PROVIDER, "doorbell:test", 90)
        self.assertEqual(self.exchange.record_doorbell_receipt(
            claim.request_id, claim.correlation_id, PROVIDER, "doorbell:test",
            claim.attempt_id, claim.lease_token, claim.fence, "ambiguous", "RIV-PLY-0009"),
            "failed")
        self.assertIsNone(self.exchange.claim_next_doorbell_request(
            PROVIDER, "doorbell:test", 90))
        status = self.exchange.status(receipt.request_id, receipt.correlation_id)
        self.assertEqual((status["delivery_state"], status["last_error_code"]),
                         ("failed", "riv_ply_0009"))
        with self.assertRaises(ExchangeConflict):
            self.exchange.record_doorbell_receipt(claim.request_id, claim.correlation_id,
                PROVIDER, "doorbell:test", claim.attempt_id, "wrong-token",
                claim.fence, "ambiguous", "RIV-PLY-0009")

    def test_doorbell_sanitized_bridge_exception_codes_are_terminal(self):
        for error_code in ("doorbell_exception", "doorbell_failure"):
            with self.subTest(error_code=error_code):
                receipt = self._submit(idem="doorbell-exception:" + error_code)
                claim = self.exchange.claim_next_doorbell_request(PROVIDER, "doorbell:test", 90)
                self.assertEqual(self.exchange.record_doorbell_receipt(
                    claim.request_id, claim.correlation_id, PROVIDER, "doorbell:test",
                    claim.attempt_id, claim.lease_token, claim.fence,
                    "ambiguous", error_code), "failed")
                status = self.exchange.status(receipt.request_id, receipt.correlation_id)
                self.assertEqual(status["last_error_code"], error_code)
                self.assertIsNone(self.exchange.claim_next_doorbell_request(
                    PROVIDER, "doorbell:test", 90))

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

    def test_steward_comms5_review_path_is_fenced_routed_and_audited_without_dispatch(self):
        receipt = self._submit(idem="comms5-steward-review")
        subject_digest = "e" * 64
        self.admin.execute(self.sql.SQL("""UPDATE {}.external_reasoning_exchanges
            SET request_payload=jsonb_set(request_payload,'{{review_subject}}',
                %s::jsonb,true) WHERE request_id=%s""").format(
                    self.sql.Identifier(self.schema)),
            (json.dumps({"schema_version": "rv.grace.proposal-review-subject.v1",
                "subject_id": str(uuid4()), "revision": 2, "sha256": subject_digest,
                "proposal": {"summary": "synthetic", "steps": []}}), receipt.request_id))

        steward = "steward:camrui"
        with self.ledger.db.cursor() as cur:
            cur.execute("SET ROLE riverview_core")
        try:
            rows = self.exchange.steward_eligible_requests(principal_id=steward, limit=5)
            row = next(item for item in rows if str(item["request_id"]) == receipt.request_id)
            self.assertEqual(row["provider_id"], PROVIDER)
            self.assertEqual(row["delivery_state"], "awaiting_delivery")
            delivery = self.exchange.begin_delivery(receipt.request_id, row["provider_id"],
                owner_id=steward, lease_seconds=30)
            self.assertIsNotNone(delivery)
            self.assertEqual(self.exchange.mark_delivered(receipt.request_id,
                receipt.correlation_id, row["provider_id"], owner_id=steward,
                delivery_token=delivery.claim_token, fence=delivery.fence),
                "awaiting_external_claim")
            claim = self.exchange.steward_claim(receipt.request_id,
                receipt.correlation_id, principal_id=steward, lease_seconds=60)
            with self.assertRaises(ExchangeConflict):
                self.exchange.claim(receipt.request_id, receipt.correlation_id,
                    provider_id=PROVIDER, principal_id=PROVIDER)
            with self.assertRaises(ExchangeUnauthorized):
                self.exchange.steward_claim(receipt.request_id, receipt.correlation_id,
                    principal_id=PROVIDER)
            response = self._response(receipt)
            misrouted = dict(response, provider_id="untrusted:other")
            with self.assertRaises(ExchangeUnauthorized):
                self.exchange.steward_submit_response(receipt.request_id,
                    receipt.correlation_id, principal_id=steward,
                    claim_token=claim.claim_token, fence=claim.fence,
                    idempotency_key="wrong-provider-route", response=misrouted,
                    review_subject_sha256=subject_digest)
            with self.assertRaises(ExchangeUnauthorized):
                self.exchange.steward_submit_response(receipt.request_id,
                    receipt.correlation_id, principal_id=steward,
                    claim_token=claim.claim_token, fence=claim.fence,
                    idempotency_key="wrong-review-digest", response=response,
                    review_subject_sha256="0" * 64)
            response_digest = self.exchange.steward_submit_response(receipt.request_id,
                receipt.correlation_id, principal_id=steward,
                claim_token=claim.claim_token, fence=claim.fence,
                idempotency_key="comms5-steward-response", response=response,
                review_subject_sha256=subject_digest)
            status = self.exchange.steward_status(receipt.request_id,
                receipt.correlation_id, principal_id=steward)
            self.assertEqual(status["delivery_state"], "response_received")
            self.assertEqual(status["review_subject_sha256"], subject_digest)
            self.assertEqual(status["response_sha256"], response_digest)
            self.assertEqual(status["response_provenance"]["reviewer_kind"], "steward")
            self.assertEqual(status["response_provenance"]["reviewer_id"], steward)
        finally:
            with self.ledger.db.cursor() as cur:
                cur.execute("RESET ROLE")

        event_actors = [event["actor_id"] for event in self.exchange.events(
            receipt.request_id, receipt.correlation_id)]
        self.assertIn(steward, event_actors)
        self.assertNotIn("provider:" + PROVIDER, event_actors)
        objective = self.exchange.ledger.db.execute(
            "SELECT status FROM " + self.schema + ".grace_objectives WHERE objective_id=%s",
            (self.objective,)).fetchone()["status"]
        self.assertEqual(objective, "GROUNDED")
        dispatched = self.exchange.ledger.db.execute(
            "SELECT count(*) FROM " + self.schema + ".grace_objective_events "
            "WHERE objective_id=%s AND event_type='work_order.dispatched'",
            (self.objective,)).fetchone()["count"]
        self.assertEqual(dispatched, 0)

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

    def test_paid_response_submission_failure_keeps_sanitized_durable_detail(self):
        receipt = self._submit(idem="paid-submission-diagnostic")
        claim = self._deliver_and_claim(receipt)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.exchange._set_path(cur)
                row = self.exchange._lock(cur, receipt.request_id,
                                          receipt.correlation_id)
                self.exchange._event(cur, row, "provider_attempt_settled",
                    "fixture-paid-attempt", PROVIDER,
                    {"status": "settled", "usage": {"cost_usd": 0.001}})
        detail = "TypeError: can only concatenate str (not 'UUID') to str"
        self.assertTrue(self.exchange.fail_provider_response_submission(
            receipt.request_id, receipt.correlation_id, provider_id=PROVIDER,
            principal_id=PROVIDER, claim_token=claim.claim_token, fence=claim.fence,
            failure_type="TypeError", failure_detail=detail))
        events = self.exchange.events(receipt.request_id, receipt.correlation_id)
        failed = [event for event in events if event["event_type"] ==
                  "provider_response_submission_failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["payload"]["failure_type"], "TypeError")
        self.assertEqual(failed[0]["payload"]["failure_detail"], detail)
        self.assertEqual(self.exchange.status(receipt.request_id,
            receipt.correlation_id)["delivery_state"], "failed")

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
