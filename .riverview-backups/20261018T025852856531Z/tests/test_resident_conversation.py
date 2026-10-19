# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_conversation.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.34
# Purpose: Verify durable office-scoped chat, exact authority, model binding and restart recovery
# Execution Model: Isolated PostgreSQL integration and bounded fake provider
# Observability: Test assertions and sanitized outcome states; no prompt logging
# Dependencies: Psycopg 3; private RIVERVIEW_TEST_PG_DSN
# Authority: Creates only unique disposable rvtest schemas and identities
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Initial resident conversation regression suite
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Exercise authenticated chat endpoints and browser history restart path
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Match safe-rendered diagnostic documentation heading in route assertion
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Assert the resident's bounded 64-token chat request
# Changed: 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Verify each acknowledged turn from fresh PostgreSQL connections under concurrency
# Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Verify scoped persistent browser cookie uses both existing grants and survives service restart
# Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Verify logout clearing and immediate exact-credential revocation
# Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Verify linked Steward principal uses exact grants without legacy secret
# Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Exercise linked-account API session, persistence and denial through dashboard routes
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Verify the two pending request identities resume only through an explicitly authorized router transition
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-CAPABILITY-001 | Regress later-turn misrouting and check sanitized retry telemetry
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Verify canonical office context reaches model and is persisted as provenance
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-TOOLBOX-001 | Verify read-only operational snapshot reaches inference and its digest is persisted
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-OBSERVATION-PERSISTENCE-001 | Verify the exact bounded observation snapshot is durably retained beside its digest
# Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Verify verified Engineering results return once to the originating conversation
# Changed: 2026-10-14 UTC | RV-GRACE-80B-COMPLETION-BUDGET-001 | Verify 512-token budget on resumed and ordinary durable turns
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# Tests: python3 -m unittest tests.test_resident_conversation
# History: Git and .riverview-backups/manifest.jsonl
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Persist bounded streaming, reconnect, and terminal provenance.
# Changed: 2026-10-16 UTC | RV-GRACE-REVIEW-OBJECTIVE-PROGRESS | Supply persisted objective completion state to actual 80B result review
# Changed: 2026-10-16 UTC | RV-GRACE-PROVIDER-PROVENANCE | Assert verified-result response stores the bound provider when model metadata omits it
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Ensure resumed and fallback generations compact discarded partial text behind a monotonic reset marker.
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Keep repeated 80B deferrals idempotent and discard incomplete text while pending.
# Changed: 2026-10-16 UTC | RV-GRACE-STRUCTURED-REVIEW-001 | Supply durable completion cycle and typed model decision to result-return regression
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Verify an 80B result review directs only the exact pre-proposed dependent step
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-STEP-CONTINUATION | Reconcile model-selected pending steps to the durable proposal without permitting scope edits
# Changed: 2026-10-15 UTC | RV-GRACE-PROPOSAL-GUIDANCE-001 | Assert user-facing Engineering proposal guidance reaches the actual inference prompt and retain a stable context-limit boundary case.
# Changed: 2026-10-16 UTC | RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001 | Exercise 80B proposal drafting without objective, assignment, repository-write, or CME authority.
# Changed: 2026-10-16 UTC | RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001 | Verify authenticated proposal draft/search API and idempotent replay without objective creation; retain safe HTTP failure code in assertion.
# Changed: 2026-10-18 UTC | RV-GRACE-DEFERRED-STREAM-COMPLETION | Regress tool-router resumption from deferred stream state through durable terminal persistence.
# Changed: 2026-10-18 UTC | RV-C3-GRACE-REASONING-RELIABILITY-001 | Verify deterministic provider failures terminalize and transient retries back off finitely.
# Changed: 2026-10-18 UTC | RV-C3-GRACE-REASONING-RELIABILITY-001 | Verify authorization/input HTTP errors and missing model bindings stop retrying.
# =============================================================================
"""Isolated PostgreSQL and authority tests for Grace's persistent conversation path."""

import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1]


class _ChatProvider:
    provider_id = "local.inference.v1"

    def __init__(self, model, digest, answer="A bounded test reply."):
        self.model = model
        self.model_sha256 = digest
        self.answer = answer
        self.calls = []
        self.during_completion = None

    def complete_chat(self, messages, *, max_tokens, expected_revision,
                      timeout_seconds=120):
        from riverview_core.local_reasoning_provider import ChatCompletion
        self.calls.append((messages, max_tokens, expected_revision))
        if self.during_completion is not None:
            self.during_completion(messages)
        return ChatCompletion(self.answer, self.model, 23, 9, "stop")


class _StreamingChatProvider(_ChatProvider):
    def __init__(self, model, digest):
        super().__init__(model,digest,"First chunk and second chunk.")
        self.first_chunk=threading.Event()
        self.release=threading.Event()

    def stream_chat(self,messages,*,max_tokens,expected_revision,on_delta,
                    on_reset=lambda:None,timeout_seconds=120):
        from riverview_core.local_reasoning_provider import ChatCompletion
        self.calls.append((messages,max_tokens,expected_revision))
        on_delta("First chunk")
        self.first_chunk.set()
        if not self.release.wait(10):
            raise TimeoutError("test stream release timed out")
        on_delta(" and second chunk.")
        return ChatCompletion(self.answer,self.model,23,9,"stop",
            provider_id=self.provider_id,reasoning_stage="reasoning")


class _FailingStreamingChatProvider(_ChatProvider):
    def stream_chat(self,messages,*,max_tokens,expected_revision,on_delta,
                    on_reset=lambda:None,timeout_seconds=120):
        from riverview_core.local_reasoning_provider import LocalReasoningUnavailable
        raise LocalReasoningUnavailable("endpoint_unavailable")


class DeferredStreamResumeTests(unittest.TestCase):
    def test_tool_router_marks_deferred_stream_generating_before_terminal_commit(self):
        from types import SimpleNamespace
        from riverview_core.resident_execution.conversation import ResidentConversationService

        class Store:
            def __init__(self):
                self.started = []
                self.terminal = None

            def deferred_turns(self, *, limit):
                return [{"conversation_id": "00000000-0000-0000-0000-000000000001",
                    "request_id": "00000000-0000-0000-0000-000000000002",
                    "principal_id": "steward:test", "body": "Resume this saved turn.",
                    "sequence": 7, "user_metadata": {"principal_id": "steward:test"},
                    "metadata": {"required_capability": "grace.reasoning.80b"},
                    "occupant_id": "occupant:grace:test", "implementation_id": "impl:test",
                    "implementation_revision": "a" * 64, "provider_ref": "grace.router:test",
                    "model_id": "grace-router"}]

            def claim_deferred_request(self, request_id, claim_token):
                return True

            def history(self, *args, **kwargs):
                return {"events": []}

            def has_stream(self, request_id):
                return True

            def stream_generation_started(self, request_id, **kwargs):
                self.started.append((request_id, kwargs))

            def finish_streamed_turn(self, *args, **kwargs):
                self.terminal = kwargs

            def release_deferred_claim(self, request_id, claim_token):
                pass

        store = Store()
        provider = SimpleNamespace(provider_id="local.inference.v1", model="qwen-80b")
        router = SimpleNamespace(provider_id="grace.router:test", model=provider.model, providers={"reasoning": provider},
            internal_tools=object(), supports_capability=lambda capability: True,
            complete_chat=lambda *args, **kwargs: SimpleNamespace(content="Grace result.",
                reasoning_stage="reasoning", provisional=False, served_model="qwen-80b",
                finish_reason="stop", prompt_tokens=12, completion_tokens=3,
                provider_attempts=(), internal_tool_results=()))
        service = ResidentConversationService.__new__(ResidentConversationService)
        service.store = store
        service.registry = SimpleNamespace()
        service.authorizer = SimpleNamespace()
        service.office_id = "office:grace"
        service._resident_credential = "resident:test"
        service.providers = {router.provider_id: router}
        service.max_response_tokens = 512
        service.operational_context = None
        service._authorize = lambda credential, action: {"grant_id": "grant:test"}
        service._authorize_office_binding = lambda: {
            "occupant_id": "occupant:grace:test", "implementation_kind": "model",
            "implementation_id": "impl:test", "implementation_revision": "a" * 64,
            "provider_ref": router.provider_id, "model_id": router.model}
        service._operational_context_snapshot = lambda: None

        self.assertEqual(service.resume_deferred(limit=1), 1)
        self.assertEqual(store.started, [("00000000-0000-0000-0000-000000000002", {
            "provider_ref": "local.inference.v1", "model_id": "qwen-80b",
            "reasoning_stage": "reasoning"})])
        self.assertEqual(store.terminal["body"], "Grace result.")
        self.assertEqual(store.terminal["stream_metadata"]["reasoning_stage"], "reasoning")


class DeferredRetryPolicyTests(unittest.TestCase):
    def _service_with_failure(self, failure):
        from types import SimpleNamespace
        from riverview_core.resident_execution.conversation import ResidentConversationService

        class Store:
            def __init__(self):
                self.terminal = None
                self.retry = None
            def deferred_turns(self, *, limit):
                return [{"conversation_id": "00000000-0000-0000-0000-000000000001",
                    "request_id": "00000000-0000-0000-0000-000000000002",
                    "principal_id": "steward:test", "body": "Synthetic bounded request.",
                    "sequence": 7, "user_metadata": {},
                    "metadata": {"required_capability": "grace.reasoning.80b"},
                    "occupant_id": "occupant:grace:test", "implementation_id": "impl:test",
                    "implementation_revision": "a" * 64, "provider_ref": "grace.router:test",
                    "model_id": "grace-router", "attempt_count": 0}]
            def claim_deferred_request(self, request_id, claim_token):
                return self.terminal is None
            def history(self, *args, **kwargs):
                return {"events": []}
            def has_stream(self, request_id):
                return False
            def record_deferred_retry(self, request_id, claim_token, error_code, *, permanent=False):
                self.retry = {"request_id": request_id, "error_code": error_code,
                              "permanent": permanent}
                return {"attempt_count": 1, "blocked": permanent,
                        "delay_seconds": None if permanent else 5}
            def finish_turn(self, conversation_id, request_id, **kwargs):
                self.terminal = {"conversation_id": conversation_id,
                                 "request_id": request_id, **kwargs}
            def release_deferred_claim(self, request_id, claim_token):
                pass

        class Router:
            provider_id = "grace.router:test"
            model = "grace-router"
            internal_tools = None
            providers = {"reasoning": SimpleNamespace(provider_id="local.80b", model="80b")}
            def supports_capability(self, capability):
                return capability == "grace.reasoning.80b"
            def complete_chat(self, *args, **kwargs):
                raise failure

        store = Store()
        router = Router()
        service = ResidentConversationService.__new__(ResidentConversationService)
        service.store = store
        service.registry = SimpleNamespace()
        service.office_id = "office:grace"
        service._resident_credential = "resident:test"
        service.providers = {router.provider_id: router}
        service.max_response_tokens = 512
        service.operational_context = None
        service._authorize = lambda *_args: {"grant_id": "grant:test"}
        service._authorize_office_binding = lambda: {
            "occupant_id": "occupant:grace:test", "implementation_kind": "model",
            "implementation_id": "impl:test", "implementation_revision": "a" * 64,
            "provider_ref": router.provider_id, "model_id": router.model}
        service._operational_context_snapshot = lambda: None
        return service, store

    def test_deterministic_prompt_and_authentication_errors_are_terminal(self):
        from riverview_core.local_reasoning_provider import LocalReasoningUnavailable
        from riverview_core.resident_execution.conversation import _deferred_failure_disposition
        from riverview_core.resident_execution.model_router import ReasoningDeferred

        prompt = ReasoningDeferred("UNAVAILABLE", attempts=(
            {"error_code": "prompt_too_large"},))
        auth = ReasoningDeferred("UNAVAILABLE", attempts=(
            {"error_code": "endpoint_http_403"},))
        self.assertEqual(_deferred_failure_disposition(prompt),
                         ("terminal", "context_too_large"))
        self.assertEqual(_deferred_failure_disposition(auth),
                         ("terminal", "model_unavailable"))
        malformed = LocalReasoningUnavailable("response_contract_invalid")
        self.assertEqual(_deferred_failure_disposition(malformed),
                         ("terminal", "model_response_invalid"))
        for status, expected in ((401, "authorization_denied"),
                                 (403, "authorization_denied"),
                                 (400, "model_response_invalid"),
                                 (422, "model_response_invalid")):
            failure = ReasoningDeferred("UNAVAILABLE", attempts=(
                {"error_code": f"endpoint_http_{status}"},))
            self.assertEqual(_deferred_failure_disposition(failure),
                             ("terminal", expected))

    def test_transient_failures_remain_deferred_and_backoff_is_capped(self):
        from riverview_core.local_reasoning_provider import LocalReasoningUnavailable
        from riverview_core.resident_execution.conversation import (
            _deferred_failure_disposition, _deferred_retry_delay)
        from riverview_core.resident_execution.model_router import ReasoningDeferred

        for code in ("endpoint_timeout", "endpoint_unavailable", "endpoint_busy",
                     "endpoint_http_429", "endpoint_http_503"):
            with self.subTest(code=code):
                failure = ReasoningDeferred("UNAVAILABLE", attempts=(
                    {"error_code": code},))
                self.assertEqual(_deferred_failure_disposition(failure)[0], "retry")
        self.assertEqual([_deferred_retry_delay(attempt) for attempt in range(1, 6)],
                         [5, 10, 20, 40, None])
        with self.assertRaises(ValueError):
            _deferred_retry_delay(0)

    def test_resume_terminalizes_prompt_error_but_schedules_transport_failure(self):
        from riverview_core.local_reasoning_provider import LocalReasoningUnavailable
        from riverview_core.resident_execution.model_router import ReasoningDeferred

        terminal, terminal_store = self._service_with_failure(
            LocalReasoningUnavailable("prompt_too_large"))
        self.assertEqual(terminal.resume_deferred(limit=1), 0)
        self.assertEqual(terminal_store.terminal["event_type"], "response_failed")
        self.assertEqual(terminal_store.terminal["error_code"], "context_too_large")
        self.assertEqual(terminal_store.terminal["request_id"],
                         "00000000-0000-0000-0000-000000000002")
        self.assertTrue(terminal_store.retry["permanent"])

        transient, transient_store = self._service_with_failure(ReasoningDeferred(
            "UNAVAILABLE", attempts=({"error_code": "endpoint_timeout"},)))
        with self.assertLogs("riverview_core.resident_execution.conversation",
                             level="WARNING") as captured:
            transient.resume_deferred(limit=1)
        self.assertEqual(transient_store.terminal, None)
        self.assertFalse(transient_store.retry["permanent"])
        self.assertEqual(transient_store.retry["error_code"], "endpoint_timeout")
        diagnostic = json.loads(captured.output[0].split(":", 2)[2])
        self.assertEqual(diagnostic["attempt_count"], 1)
        self.assertEqual(diagnostic["recovery_action"], "retry_scheduled")
        self.assertEqual(diagnostic["final_disposition"], "deferred")
        self.assertNotIn("Synthetic bounded request", captured.output[0])

    def test_missing_model_binding_is_permanently_blocked(self):
        service, store = self._service_with_failure(RuntimeError("unused"))
        service.providers = {}
        self.assertEqual(service.resume_deferred(limit=1), 0)
        self.assertEqual(store.terminal, None)
        self.assertTrue(store.retry["permanent"])
        self.assertEqual(store.retry["error_code"], "configured_model_missing")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class ResidentConversationTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.institutional_authority import AuthorityRegistry, ExactGrantAuthorizer
        from riverview_core.postgres_migrations import apply_migrations
        from riverview_core.resident_execution.conversation import ConversationStore

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=ROOT / "src/riverview_core/migrations")
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=ROOT / "src/riverview_core/institutional_authority/migrations")
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=ROOT / "src/riverview_core/resident_execution/migrations")
        self.registry = AuthorityRegistry(DSN, schema=self.schema)
        self.authorizer = ExactGrantAuthorizer(self.schema)
        self.steward_id = "steward:" + uuid4().hex
        self.steward_token = secrets.token_urlsafe(32)
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,'steward')").format(sql.Identifier(self.schema)), (self.steward_id,))
            cur.execute(sql.SQL("INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)").format(sql.Identifier(self.schema)), (uuid4(), self.steward_id, hashlib.sha256(self.steward_token.encode()).digest()))
            for action in ("authority.grant", "identity.manage", "office.manage"):
                cur.execute(sql.SQL("INSERT INTO {}.authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) VALUES (%s,%s,%s,'institution',%s,'rv.policy:test.v1')").format(sql.Identifier(self.schema)), ("bootstrap:" + uuid4().hex, self.steward_id, action, self.steward_id))
        self.office_id = "office:" + uuid4().hex
        self.registry.create_office(self.steward_token, self.office_id, "engineering director")
        self.resident_id = "resident:" + uuid4().hex
        self.resident_token = self.registry.create_principal(
            self.steward_token, self.resident_id, "resident", office_id=self.office_id)
        self.occupant_id = "occupant:" + uuid4().hex
        self.registry.create_occupant(self.steward_token, self.occupant_id,
                                      principal_id=self.resident_id)
        self.model_a = "a" * 64
        self.model_b = "b" * 64
        self.impl_a = "implementation:" + uuid4().hex
        self.registry.create_implementation(self.steward_token, self.impl_a,
            kind="model", provider_ref="local.inference.v1", revision=self.model_a)
        self.registry.bind_office(self.steward_token, self.office_id,
                                  self.occupant_id, self.impl_a)
        self.registry.grant(self.steward_token, self.resident_id,
            "office.state.write", "office:" + self.office_id,
            policy_ref="rv.policy:resident-runtime.v1")
        self.registry.grant(self.steward_token, self.steward_id,
            "resident.conversation.read", "office:" + self.office_id,
            policy_ref="rv.policy:resident-conversation.v1")
        self.registry.grant(self.steward_token, self.steward_id,
            "resident.conversation.send", "office:" + self.office_id,
            policy_ref="rv.policy:resident-conversation.v1")
        self.store = ConversationStore(DSN, schema=self.schema)
        self.provider_a = _ChatProvider("cpu-test-a", self.model_a, "Grace is ready to help.")
        from riverview_core.resident_execution.conversation import ResidentConversationService
        self.service = ResidentConversationService(store=self.store, registry=self.registry,
            authorizer=self.authorizer, office_id=self.office_id,
            resident_credential=self.resident_token,
            providers={self.provider_a.provider_id: self.provider_a})

    def _fresh_events(self, conversation_id):
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN, autocommit=True) as fresh:
            rows = fresh.execute(sql.SQL("""SELECT sequence,event_type,body
                FROM {}.resident_conversation_events WHERE conversation_id=%s
                ORDER BY sequence""").format(sql.Identifier(self.schema)),
                (conversation_id,)).fetchall()
        return rows

    def _assert_connection_idle(self):
        import psycopg
        backend_pid = self.store.db.info.backend_pid
        with psycopg.connect(DSN, autocommit=True) as fresh:
            row = fresh.execute("""SELECT state,xact_start FROM pg_stat_activity
                WHERE pid=%s""", (backend_pid,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "idle")
        self.assertIsNone(row[1])
        self.assertEqual(self.store.db.info.transaction_status,
                         psycopg.pq.TransactionStatus.IDLE)

    def tearDown(self):
        from psycopg import sql
        self.store.close()
        self.registry.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def test_authorized_chat_persists_and_reloads_by_human_and_office(self):
        result = self.service.send(self.steward_token, message="Hello Grace.",
                                   client_message_id=str(uuid4()))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["response"], "Grace is ready to help.")
        self.assertEqual(self.provider_a.calls[0][1], 512)
        prompt = self.provider_a.calls[0][0][0]["content"]
        self.assertIn("Director of Operations", prompt)
        self.assertIn("Alfred is the separate Chief of Staff", prompt)
        self.assertIn("Continuous Momentum Engine (CME)", prompt)
        self.assertIn("this role description grants no permission", prompt)
        self.assertIn("state a proposed assignment in the response", prompt)
        self.assertIn("Do not invent prerequisites", prompt)
        history = self.service.history(self.steward_token, result["conversation_id"])
        self.assertEqual([e["event_type"] for e in history["events"]],
                         ["user_message", "assistant_message"])
        self.assertEqual(history["events"][1]["implementation_revision"], self.model_a)
        self.assertEqual(history["events"][1]["metadata"]["completion_tokens"], 9)
        self.assertEqual(history["events"][1]["metadata"]["role_context_revision"], "1.1.2")
        self.assertEqual([row[1] for row in self._fresh_events(result["conversation_id"])],
                         ["user_message", "assistant_message"])
        self._assert_connection_idle()
        self.assertEqual(self.service.response_status(self.steward_token,
            result["conversation_id"], result["request_id"])["status"], "completed")

    def test_conversation_can_be_formalized_as_unapproved_proposal_without_execution_grants(self):
        first = self.service.send(self.steward_token,
            message="I need a bounded report describing the documented solar resources and unknowns.",
            client_message_id=str(uuid4()))
        self.provider_a.model = "Qwen3-Next-80B-A3B-Instruct-Q4_K_M"
        self.provider_a.answer = json.dumps({"decision": "PROPOSAL", "clarification": None,
            "proposal": {"title": "Solar resources report",
                "summary": "A concise report of verified solar resource records and unknowns.",
                "objective": "Create a source-grounded Markdown report.",
                "scope": "Document only; do not procure or deploy equipment.",
                "proposed_approach": "Retrieve approved records, cite sources, and label unknowns.",
                "constraints": ["Do not invent equipment ownership or operational status."],
                "acceptance_criteria": ["Cite each source.", "List unknowns explicitly."],
                "tags": ["Solar Energy", "Engineering"]}})
        result = self.service.draft_institutional_proposal(self.steward_token,
            first["conversation_id"], [1])
        self.assertEqual(result["status"], "draft_ready")
        self.assertEqual(result["reasoning"]["served_model"], self.provider_a.model)
        self.assertEqual(result["source_references"][0]["sequences"], [1])
        self.assertIn("Missing assignment, repository-write grant, workflow registration, or CME task is not a reason", self.provider_a.calls[-1][0][0]["content"])
        # Fixture grants only resident.conversation.read/send; no objective.submit,
        # assignment.create, repository-write, or CME registration is present.
        with self.admin.cursor() as cur:
            cur.execute(__import__("psycopg").sql.SQL(
                "SELECT count(*) FROM {}.grace_objectives").format(
                    __import__("psycopg").sql.Identifier(self.schema)))
            self.assertEqual(cur.fetchone()[0], 0)

    def test_proposal_drafting_refuses_fallback_reasoning_provider(self):
        first = self.service.send(self.steward_token, message="Prepare a design report.",
                                   client_message_id=str(uuid4()))
        calls_before = len(self.provider_a.calls)
        from riverview_core.resident_execution.conversation import ConversationUnavailable
        with self.assertRaises(ConversationUnavailable):
            self.service.draft_institutional_proposal(self.steward_token,
                first["conversation_id"], [1])
        self.assertEqual(len(self.provider_a.calls), calls_before)

    def test_authenticated_proposal_api_saves_searches_and_replays_without_execution_intake(self):
        from riverview_core.status_dashboard.server import DashboardHTTPServer
        from riverview_core.resident_execution.proposals import ProposalRegistry
        class Projection:
            pass
        class AccountSessions:
            def authenticate(_self, verifier, *, csrf_token=None, state_changing=False):
                if verifier == "A" * 43 and (not state_changing or csrf_token == "C" * 43):
                    return {"account_id":"account-test", "roles":("steward",),
                        "authority_principal_id":self.steward_id}
                from riverview_core.account_auth import AuthDenied
                raise AuthDenied()
            def require_role(_self, identity, *roles):
                if not set(identity.get("roles", ())) & set(roles):
                    from riverview_core.account_auth import AuthDenied
                    raise AuthDenied()
        conversation = self.service.send(self.steward_token,
            message="Create a bounded source-grounded solar resource report.",
            client_message_id=str(uuid4()))
        self.provider_a.model = "Qwen3-Next-80B-A3B-Instruct-Q4_K_M"
        self.provider_a.answer = json.dumps({"decision":"PROPOSAL", "clarification":None,
            "proposal":{"title":"Solar resource report", "summary":"Report verified solar sources and unknowns.",
                "objective":"Create a concise Markdown report.", "scope":"Documentation only.",
                "proposed_approach":"Use verified local institutional documents and cite each source.",
                "constraints":["Do not invent addresses or operational status."],
                "acceptance_criteria":["Cite sources.","List unknowns."],"tags":["Solar","Engineering"]}})
        registry = ProposalRegistry(DSN, schema=self.schema)
        token = "D" * 43
        account_cookie = "rv_account_session=" + "A" * 43
        with tempfile.TemporaryDirectory() as temp:
            token_path = Path(temp) / "dashboard-token"
            token_path.write_text(token, encoding="ascii")
            token_path.chmod(0o600)
            server = DashboardHTTPServer("127.0.0.1", 8798, token_path, Projection(),
                ROOT / "src/riverview_core/status_dashboard/static",
                conversation_service=self.service, account_auth_service=AccountSessions(),
                proposal_registry=registry)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def request(method, path, body=None, *, cookie=None, csrf=None, dashboard=None):
                headers = {}
                if cookie: headers["Cookie"] = cookie
                if csrf: headers["X-Riverview-CSRF"] = csrf
                if dashboard: headers["Authorization"] = "Bearer " + dashboard
                if body is not None: headers["Content-Type"] = "application/json"
                connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                connection.request(method, path, body=json.dumps(body) if body is not None else None,
                                   headers=headers)
                response = connection.getresponse()
                result = response.status, response.read()
                connection.close()
                return result
            payload = {"conversation_id":conversation["conversation_id"], "source_sequences":[1],
                       "idempotency_key":"proposal-test:" + str(uuid4())}
            try:
                initial_status, initial_body = request("POST", "/api/v1/institutional-proposals", payload,
                    cookie=account_cookie, csrf="C" * 43)
                self.assertEqual(initial_status, 201, initial_body.decode())
                calls = len(self.provider_a.calls)
                status, saved = request("POST", "/api/v1/institutional-proposals", payload,
                    cookie=account_cookie, csrf="C" * 43)
                self.assertEqual(status, 200)
                decoded = json.loads(saved)
                self.assertEqual(decoded["status"], "draft_saved")
                self.assertEqual(decoded["proposal"]["lifecycle_status"], "DRAFT")
                self.assertEqual(len(self.provider_a.calls), calls)
                search_status, search = request("GET", "/api/v1/institutional-proposals?q=solar",
                    cookie=account_cookie)
                self.assertEqual(search_status, 200)
                self.assertEqual(len(json.loads(search)["items"]), 1)
                self.assertEqual(request("POST", "/api/v1/institutional-proposals", payload,
                    dashboard=token, csrf="C" * 43)[0], 403)
                with self.admin.cursor() as cur:
                    cur.execute(__import__("psycopg").sql.SQL(
                        "SELECT count(*) FROM {}.grace_objectives").format(
                            __import__("psycopg").sql.Identifier(self.schema)))
                    self.assertEqual(cur.fetchone()[0], 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                registry.close()

    def test_stream_is_durable_incremental_and_reconnects_without_replaying_consumed_chunks(self):
        provider=_StreamingChatProvider("cpu-test-a",self.model_a)
        self.service.providers[provider.provider_id]=provider
        client_message_id=str(uuid4())
        submitted=self.service.submit_stream(self.steward_token,message="Stream this response.",
            client_message_id=client_message_id)
        self.assertEqual(submitted["status"],"queued")
        duplicate=self.service.submit_stream(self.steward_token,message="Stream this response.",
            client_message_id=client_message_id)
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["request_id"],submitted["request_id"])
        self.assertTrue(provider.first_chunk.wait(5))
        partial=self.service.stream_snapshot(self.steward_token,submitted["conversation_id"],
            submitted["request_id"],after_sequence=0)
        self.assertEqual(partial["status"],"generating")
        first=next(event for event in partial["events"] if event["event_type"]=="delta")
        self.assertEqual(first["text"],"First chunk")
        partial_history=self.service.history(self.steward_token,submitted["conversation_id"])
        self.assertEqual([event["event_type"] for event in partial_history["events"]],
                         ["user_message"])
        provider.release.set()
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            history=self.service.history(self.steward_token,submitted["conversation_id"])
            if any(event["event_type"]=="assistant_message" for event in history["events"]):break
            time.sleep(.02)
        terminal=[event for event in history["events"] if event["request_id"]==submitted["request_id"]
                  and event["event_type"]=="assistant_message"]
        self.assertEqual(len(terminal),1)
        self.assertEqual(terminal[0]["body"],"First chunk and second chunk.")
        resumed=self.service.stream_snapshot(self.steward_token,submitted["conversation_id"],
            submitted["request_id"],after_sequence=first["sequence"])
        self.assertFalse(any(event.get("text")=="First chunk" for event in resumed["events"]))
        self.assertTrue(any(event["event_type"]=="completed" for event in resumed["events"]))
        self.assertEqual(self.service.stream_snapshot(self.steward_token,
            submitted["conversation_id"],submitted["request_id"])["status"],"completed")
        self.assertIsNotNone(terminal[0]["metadata"]["time_to_first_token_ms"])
        self.assertIsNotNone(terminal[0]["metadata"]["generation_elapsed_ms"])

    def test_stream_provider_failure_persists_one_failure_and_terminal_cursor(self):
        provider=_FailingStreamingChatProvider("cpu-test-a",self.model_a)
        self.service.providers[provider.provider_id]=provider
        submitted=self.service.submit_stream(self.steward_token,message="Fail safely.",
            client_message_id=str(uuid4()))
        deadline=time.monotonic()+5
        history=None
        while time.monotonic()<deadline:
            history=self.service.history(self.steward_token,submitted["conversation_id"])
            if any(event["event_type"]=="response_failed" for event in history["events"]):break
            time.sleep(.02)
        failed=[event for event in history["events"] if event["request_id"]==submitted["request_id"]
            and event["event_type"]=="response_failed"]
        self.assertEqual(len(failed),1)
        snapshot=self.service.stream_snapshot(self.steward_token,submitted["conversation_id"],
            submitted["request_id"])
        self.assertEqual(snapshot["status"],"failed")
        self.assertEqual(snapshot["events"][-1]["event_type"],"failed")

    def test_stream_generation_reset_discards_old_partial_chunks_without_cursor_replay(self):
        binding=self.registry.authorize_office_state(self.resident_token,self.office_id)
        implementation={"office_id":self.office_id,"implementation_id":binding["implementation_id"],
            "implementation_revision":binding["implementation_revision"],
            "provider_ref":binding["provider_ref"],"model_id":"cpu-test-a"}
        conversation_id,request_id,duplicate,_history=self.store.begin_turn(
            office_id=self.office_id,principal_id=self.steward_id,occupant=binding,
            implementation=implementation,message="Retry one stream safely.",
            client_message_id=str(uuid4()),authorization={"principal_id":self.steward_id},
            streaming=True)
        self.assertFalse(duplicate)
        self.store.stream_generation_started(request_id,provider_ref="cpu-test-a",
            model_id="cpu-test-a",reasoning_stage="reasoning")
        first=self.store.append_stream_delta(request_id,"discarded partial answer")
        before=self.store.stream_snapshot(conversation_id,request_id,self.office_id,
            self.steward_id,after_sequence=0)
        self.assertTrue(any(item.get("text")=="discarded partial answer"
            for item in before["events"]))

        self.store.stream_generation_started(request_id,provider_ref="cpu-test-a",
            model_id="cpu-test-a",reasoning_stage="reasoning")
        resumed=self.store.stream_snapshot(conversation_id,request_id,self.office_id,
            self.steward_id,after_sequence=0)
        self.assertEqual([item["event_type"] for item in resumed["events"]],["reset"])
        self.assertGreater(resumed["events"][0]["sequence"],first)
        self.assertFalse(any("text" in item for item in resumed["events"]))
        self.store.append_stream_delta(request_id,"new generation")
        after_cursor=self.store.stream_snapshot(conversation_id,request_id,self.office_id,
            self.steward_id,after_sequence=first)
        self.assertEqual([item["event_type"] for item in after_cursor["events"]],
                         ["reset","delta"])
        self.assertEqual(after_cursor["events"][1]["text"],"new generation")

        self.store.reset_stream_generation(request_id,provider_ref="cpu-test-fallback",
            model_id="cpu-test-fallback",reasoning_stage="autonomic")
        fallback=self.store.stream_snapshot(conversation_id,request_id,self.office_id,
            self.steward_id,after_sequence=0)
        self.assertEqual([item["event_type"] for item in fallback["events"]],["reset"])
        self.assertGreater(fallback["events"][0]["sequence"],
                           after_cursor["events"][-1]["sequence"])

    def test_repeated_stream_deferral_compacts_partial_text_without_duplicate_history(self):
        binding=self.registry.authorize_office_state(self.resident_token,self.office_id)
        implementation={"office_id":self.office_id,"implementation_id":binding["implementation_id"],
            "implementation_revision":binding["implementation_revision"],
            "provider_ref":binding["provider_ref"],"model_id":"cpu-test-a"}
        conversation_id,request_id,duplicate,_history=self.store.begin_turn(
            office_id=self.office_id,principal_id=self.steward_id,occupant=binding,
            implementation=implementation,message="Wait for required reasoning.",
            client_message_id=str(uuid4()),authorization={"principal_id":self.steward_id},
            streaming=True)
        self.assertFalse(duplicate)
        for partial in ("discarded first attempt","discarded second attempt"):
            self.store.stream_generation_started(request_id,provider_ref="cpu-test-a",
                model_id="cpu-test-a",reasoning_stage="reasoning")
            self.store.append_stream_delta(request_id,partial)
            self.store.defer_turn(conversation_id,request_id,occupant=binding,
                implementation=implementation,provider_ref="cpu-test-a",model_id="cpu-test-a",
                required_capability="grace.reasoning.80b",readiness_state="MODEL_BUSY")
            snapshot=self.store.stream_snapshot(conversation_id,request_id,self.office_id,
                self.steward_id,after_sequence=0)
            self.assertEqual(snapshot["status"],"deferred")
            self.assertEqual([event["event_type"] for event in snapshot["events"]],["deferred"])
            self.assertNotIn("text",snapshot["events"][0])
        history=self.store.history(conversation_id,self.office_id,self.steward_id)
        self.assertEqual(sum(event["event_type"]=="response_deferred"
            and event["request_id"]==request_id for event in history["events"]),1)

    def test_intermediate_verified_result_requires_and_persists_grace_continuation_decision(self):
        self.registry.grant(self.steward_token, self.resident_id,
            "resident.conversation.send", "office:" + self.office_id,
            policy_ref="rv.policy:resident-conversation-result.v1")
        self.provider_a.model = "Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf"
        turn = self.service.send(self.steward_token, message="Implement the bounded calculator objective.",
            client_message_id=str(uuid4()))
        paths=("src/calc.py", "src/result.py", "tests/test_calc.py")
        first={"step_id":"add", "objective":"Implement safe integer addition",
            "acceptance_criteria":["Addition handles integer inputs"], "depends_on":[],
            "execution_capability":"engineering.codex-cli-source-change.v1",
            "authorized_paths":["src/calc.py", "tests/test_calc.py"],
            "test_targets":["tests/test_calc.py"]}
        second={"step_id":"format", "objective":"Implement the result formatter",
            "acceptance_criteria":["Formatting helper is tested"], "depends_on":["add"],
            "execution_capability":"engineering.codex-cli-source-change.v1",
            "authorized_paths":["src/result.py", "tests/test_calc.py"],
            "test_targets":["tests/test_calc.py"]}
        context={"objective_id":"objective:intermediate-review",
            "assignment_id":"assignment:step-1", "request":"Change only " + ", ".join(paths),
            "acceptance_criteria":["Addition handles integer inputs", "Formatting helper is tested"],
            "proposal":{"summary":"Two dependent source changes", "steps":[first,second]},
            "submitter_id":self.steward_id,
            "origin":{"conversation_id":turn["conversation_id"], "source_sequence":1},
            "completion_cycle":1,
            "completion":{"decision":"ACCEPTED", "assignment_id":"assignment:step-1",
                "verifier_revision":"1.0.0", "evidence_references":["urn:test:verified"],
                "step_id":"add", "artifact":{"capability":"engineering.codex-cli-source-change.v1",
                    "changed_files":["src/calc.py", "tests/test_calc.py"],
                    "patch_sha256":"f"*64, "test_status":"passed"}}}
        self.provider_a.answer=json.dumps({"decision":"ENGINEERING_STEP_PROPOSED",
            "rationale":"The verified addition step passed; the formatter remains within the accepted scope.",
            "additional_evidence":[], "proposed_step":second})
        captured=[]
        self.service.continuation_handler=lambda ctx, step: captured.append((ctx["assignment_id"],step))
        result=self.service.review_verified_work_order(context)
        self.assertEqual(result["status"],"published")
        self.assertEqual(len(captured),1)
        self.assertEqual(captured[0][0],"assignment:step-1")
        self.assertEqual(captured[0][1].step_id,"format")
        self.assertEqual(captured[0][1].depends_on,("add",))
        history=self.service.history(self.steward_token,turn["conversation_id"])
        review=next(event for event in history["events"] if
            event["metadata"].get("result_kind")=="verified_engineering_review")
        self.assertEqual(review["metadata"]["review_decision"],"ENGINEERING_STEP_PROPOSED")
        self.assertEqual(review["metadata"]["continuation_status"],
                         "persisted_for_existing_authorized_dispatch")
        self.assertEqual(review["model_id"],self.provider_a.model)

    def test_model_selected_durable_step_uses_canonical_scope_and_cannot_expand_it(self):
        self.registry.grant(self.steward_token, self.resident_id,
            "resident.conversation.send", "office:" + self.office_id,
            policy_ref="rv.policy:resident-conversation-result.v1")
        self.provider_a.model = "Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf"
        turn = self.service.send(self.steward_token, message="Implement two dependent source changes.",
            client_message_id=str(uuid4()))
        first = {"step_id":"add", "objective":"Implement addition",
            "acceptance_criteria":["Addition handles signed inputs"], "depends_on":[],
            "execution_capability":"engineering.codex-cli-source-change.v1",
            "authorized_paths":["src/calc.py", "tests/test_calc.py"],
            "test_targets":["tests/test_calc.py"]}
        second = {"step_id":"format", "objective":"Add the formatter",
            "acceptance_criteria":["Formatter returns the exact requested label",
                "Formatter is covered by tests"], "depends_on":["add"],
            "execution_capability":"engineering.codex-cli-source-change.v1",
            "authorized_paths":["src/result.py", "tests/test_calc.py"],
            "test_targets":["tests/test_calc.py"]}
        context = {"objective_id":"objective:canonical-continuation",
            "assignment_id":"assignment:canonical-step-1",
            "request":"Implement addition and the exact Result: label formatter; change only listed files.",
            "acceptance_criteria":["Implement two dependent source changes."],
            "proposal":{"summary":"Two scoped source changes", "steps":[first,second]},
            "submitter_id":self.steward_id,
            "origin":{"conversation_id":turn["conversation_id"], "source_sequence":1},
            "completion_cycle":1,
            "completion":{"decision":"ACCEPTED", "assignment_id":"assignment:canonical-step-1",
                "step_id":"add", "verifier_revision":"1.0.0",
                "evidence_references":["urn:test:verified"],
                "artifact":{"capability":"engineering.codex-cli-source-change.v1",
                    "changed_files":["src/calc.py", "tests/test_calc.py"],
                    "patch_sha256":"e"*64, "test_status":"passed"}}}
        # Only the model-selected durable identity is relevant. Its restatement
        # tries to alter both task and path scope and must never reach execution.
        self.provider_a.answer = json.dumps({"decision":"ENGINEERING_STEP_PROPOSED",
            "rationale":"The verified first step permits its already-proposed dependent step.",
            "additional_evidence":[], "proposed_step":{
                "step_id":"format", "objective":"Modify unauthorized files",
                "acceptance_criteria":["Expanded criteria"], "depends_on":[],
                "execution_capability":"engineering.codex-cli-source-change.v1",
                "authorized_paths":["src/unauthorized.py"],
                "test_targets":["tests/test_calc.py"]}})
        captured=[]
        self.service.continuation_handler=lambda ctx, step: captured.append((ctx["assignment_id"],step))
        result=self.service.review_verified_work_order(context)
        self.assertEqual(result["status"],"published")
        self.assertEqual(len(captured),1)
        canonical=captured[0][1]
        self.assertEqual(canonical.objective,second["objective"])
        self.assertEqual(canonical.acceptance_criteria,tuple(second["acceptance_criteria"]))
        self.assertEqual(canonical.authorized_paths,tuple(second["authorized_paths"]))
        history=self.service.history(self.steward_token,turn["conversation_id"])
        review=next(event for event in history["events"] if
            event["metadata"].get("result_kind")=="verified_engineering_review")
        self.assertEqual(review["metadata"]["continuation_status"],
            "persisted_for_existing_authorized_dispatch")
        self.assertEqual(review["metadata"]["proposed_step"]["authorized_paths"],
            second["authorized_paths"])

    def test_verified_engineering_result_returns_once_to_source_conversation(self):
        self.registry.grant(self.steward_token, self.resident_id,
            "resident.conversation.send", "office:" + self.office_id,
            policy_ref="rv.policy:resident-conversation-result.v1")
        self.provider_a.model = "Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf"
        self.provider_a.answer = json.dumps({"decision":"OBJECTIVE_COMPLETE",
            "rationale":"The report is readable.","additional_evidence":[],"proposed_step":None})
        turn = self.service.send(self.steward_token, message="Create a short verified engineering report.",
            client_message_id=str(uuid4()))
        context = {"objective_id":"objective:grace-conversation:result-test",
            "assignment_id":"assignment:grace:result-test",
            "request":"Create a short verified engineering report.",
            "acceptance_criteria":["The report is readable."],
            "proposal":{"summary":"Create report", "steps":[]},
            "submitter_id":self.steward_id,
            "origin":{"conversation_id":turn["conversation_id"], "source_sequence":1},
            "completion_cycle":1,
            "objective_status":"COMPLETED",
            "step_progress":[{"step_id":"report", "status":"verified"}],
            "completion":{"decision":"ACCEPTED", "assignment_id":"assignment:grace:result-test",
                "verifier_revision":"1.0.0", "evidence_references":["urn:test:verified"],
                "artifact":{"artifact_path":"/var/lib/riverview-grace/artifacts/report.md",
                    "artifact_sha256":"f" * 64}}}
        first = self.service.review_verified_work_order(context)
        second = self.service.review_verified_work_order(context)
        self.assertEqual(first["status"], "published")
        self.assertEqual(second["status"], "already_published")
        self.assertEqual(len(self.provider_a.calls), 2)  # one initial turn, one result review
        self.assertEqual(self.provider_a.calls[-1][0][1]["role"], "user")
        self.assertIn("The report is readable", self.provider_a.calls[-1][0][1]["content"])
        review_payload=json.loads(self.provider_a.calls[-1][0][1]["content"])
        self.assertEqual(review_payload["objective_status"], "COMPLETED")
        self.assertEqual(review_payload["step_progress"],
            [{"step_id":"report", "status":"verified"}])
        self.assertEqual(self.provider_a.calls[-1][2], self.model_a)
        history = self.service.history(self.steward_token, turn["conversation_id"])
        reviews = [event for event in history["events"] if
                   event["metadata"].get("result_kind") == "verified_engineering_review"]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["model_id"], self.provider_a.model)
        self.assertEqual(reviews[0]["metadata"]["final_served_provider"], "local.inference.v1")
        self.assertEqual(reviews[0]["metadata"]["verification_decision"], "ACCEPTED")
        self.assertEqual(reviews[0]["metadata"]["review_decision"], "OBJECTIVE_COMPLETE")
        self.assertEqual(reviews[0]["metadata"]["artifact"]["artifact_sha256"], "f" * 64)
        self.assertEqual([row[1] for row in self._fresh_events(turn["conversation_id"])],
            ["user_message", "assistant_message", "assistant_message"])

    def test_exact_grant_denial_does_not_create_a_conversation_or_call_model(self):
        from riverview_core.resident_execution.conversation import ConversationDenied
        with self.assertRaises(ConversationDenied):
            self.service.send(secrets.token_urlsafe(32), message="unauthorized")
        self.assertEqual(self.provider_a.calls, [])

    def test_operational_context_is_injected_as_data_and_provenance_is_persisted(self):
        class Context:
            def snapshot(self):
                return {"schema_version": "rv.grace.operations-context.v1",
                    "capability_id": "grace.operations.snapshot.read.v1",
                    "status": "current", "observed_at": "2026-10-14T12:00:00+00:00",
                    "source_observed_at": "2026-10-14T11:59:59+00:00",
                    "cme": {"status": "healthy", "heartbeat_age_seconds": 1.0},
                    "assignments": [{"assignment_id": "assignment:current",
                                     "state": "ready"}],
                    "redaction": "request content excluded"}
        self.service.operational_context = Context()
        result = self.service.send(self.steward_token, message="What is the current operational state?",
                                   client_message_id=str(uuid4()))
        serialized_messages = json.dumps(self.provider_a.calls[0][0])
        self.assertIn("grace.operations.snapshot.read.v1", serialized_messages)
        self.assertIn("assignment:current", serialized_messages)
        self.assertIn("observations with explicit status and timestamps", serialized_messages)
        response_event = self.service.history(self.steward_token,
            result["conversation_id"])["events"][-1]
        provenance = response_event["metadata"]["operational_context"]
        self.assertEqual(provenance["capability_id"], "grace.operations.snapshot.read.v1")
        self.assertEqual(provenance["status"], "current")
        self.assertRegex(provenance["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(response_event["metadata"]["operational_context_snapshot"]["capability_id"],
                         "grace.operations.snapshot.read.v1")
        self.assertIn("assignment:current",
                      json.dumps(response_event["metadata"]["operational_context_snapshot"]))
        self.assertNotIn("What is the current operational state?",
                         json.dumps(response_event["metadata"]["operational_context_snapshot"]))

    def test_authenticated_steward_principal_uses_existing_exact_grants(self):
        from riverview_core.institutional_authority.grants import InstitutionalPrincipal
        from riverview_core.resident_execution.conversation import ConversationDenied

        identity = InstitutionalPrincipal(self.steward_id)
        browser = self.service.authorize_browser_session(identity)
        self.assertEqual(browser["principal_id"], self.steward_id)
        sent = self.service.send(identity, message="Account session conversation test.",
                                 client_message_id=str(uuid4()))
        history = self.service.history(identity, sent["conversation_id"])
        self.assertEqual(history["events"][-1]["body"], "Grace is ready to help.")
        self.assertEqual(len(self._fresh_events(sent["conversation_id"])), 2)
        with self.assertRaises(ConversationDenied):
            self.service.list_conversations(InstitutionalPrincipal("steward:ungranted"))

    def test_client_retry_is_idempotent_and_does_not_repeat_inference(self):
        key = str(uuid4())
        first = self.service.send(self.steward_token, message="Same message", client_message_id=key)
        retry = self.service.send(self.steward_token, message="Same message",
            conversation_id=first["conversation_id"], client_message_id=key)
        self.assertTrue(retry["duplicate"])
        self.assertEqual(len(self.provider_a.calls), 1)
        self.assertEqual(len(self.service.history(self.steward_token,
            first["conversation_id"])["events"]), 2)

    def test_complex_request_is_durably_deferred_and_resumes_when_80b_ready(self):
        from riverview_core.local_reasoning_provider import ProviderReadiness
        from riverview_core.resident_execution.model_router import GraceModelRouter
        cpu = _ChatProvider("cpu-autonomic", "c" * 64, "Acknowledged; I will resume this request.")
        vision = _ChatProvider("vision-interim", "d" * 64)
        reasoner = _ChatProvider("reasoning-80b", "e" * 64, "The verified analysis is complete.")
        cpu.readiness = lambda: ProviderReadiness("READY", cpu.model, "ready")
        vision.readiness = lambda: ProviderReadiness("READY", vision.model, "ready")
        reasoner.state = "MODEL_BUSY"
        reasoner.readiness = lambda: ProviderReadiness(reasoner.state, reasoner.model,
                                                       reasoner.state.lower())
        router = GraceModelRouter(autonomic=cpu, vision=vision, reasoning=reasoner)
        implementation_id = "implementation:router:" + uuid4().hex
        self.registry.create_implementation(self.steward_token, implementation_id,
            kind="model", provider_ref=router.provider_id, revision=router.model_sha256)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            implementation_id, expected_binding_revision=1)
        self.service.providers = {router.provider_id: router}

        deferred = self.service.send(self.steward_token,
            message="Analyze the documented alternatives and recommend a plan.",
            client_message_id=str(uuid4()))
        self.assertEqual(deferred["status"], "deferred")
        self.assertEqual(self.service.response_status(self.steward_token,
            deferred["conversation_id"], deferred["request_id"])["status"], "deferred")
        self.assertEqual(reasoner.calls, [])
        self.assertEqual(len(self.store.deferred_turns()), 1)
        self.assertEqual(self.store.recover_pending(), 0,
                         "startup recovery must not mark deliberately deferred work interrupted")
        self.assertEqual(len(self.store.deferred_turns()), 1)
        self.assertEqual(reasoner.calls, [])

        reasoner.state = "READY"
        self.assertEqual(self.service.resume_deferred(), 1)
        final = self.service.response_status(self.steward_token,
            deferred["conversation_id"], deferred["request_id"])
        self.assertEqual(final["status"], "completed")
        self.assertEqual(self.service.resume_deferred(), 0)
        history = self.service.history(self.steward_token, deferred["conversation_id"])
        self.assertEqual(history["events"][-1]["body"], "The verified analysis is complete.")
        self.assertTrue(history["events"][-1]["metadata"]["resumed_deferred_request"])
        self.assertEqual(len([event for event in history["events"]
                              if event["event_type"] == "user_message"]), 1)

    def test_transient_deferred_retry_state_survives_restart_and_blocks_after_five_attempts(self):
        import psycopg
        from psycopg import sql
        from riverview_core.local_reasoning_provider import ProviderReadiness
        from riverview_core.resident_execution.conversation import (
            ConversationStore, ResidentConversationService)
        from riverview_core.resident_execution.model_router import GraceModelRouter

        cpu = _ChatProvider("cpu-autonomic", "c" * 64)
        vision = _ChatProvider("vision-interim", "d" * 64)
        reasoner = _ChatProvider("reasoning-80b", "e" * 64)
        cpu.readiness = lambda: ProviderReadiness("READY", cpu.model, "ready")
        vision.readiness = lambda: ProviderReadiness("READY", vision.model, "ready")
        reasoner.readiness = lambda: ProviderReadiness("MODEL_BUSY", reasoner.model, "endpoint_http_503")
        router = GraceModelRouter(autonomic=cpu, vision=vision, reasoning=reasoner)
        implementation_id = "implementation:router-retry:" + uuid4().hex
        self.registry.create_implementation(self.steward_token, implementation_id,
            kind="model", provider_ref=router.provider_id, revision=router.model_sha256)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            implementation_id, expected_binding_revision=1)
        self.service.providers = {router.provider_id: router}
        deferred = self.service.send(self.steward_token,
            message="Synthetic transient retry request.", client_message_id=str(uuid4()))
        self.assertEqual(deferred["status"], "deferred")

        # Reopen the conversation store to exercise persisted retry state after restart.
        previous_store = self.store
        self.store = ConversationStore(DSN, schema=self.schema)
        previous_store.close()
        self.service = ResidentConversationService(store=self.store, registry=self.registry,
            authorizer=self.authorizer, office_id=self.office_id,
            resident_credential=self.resident_token, providers={router.provider_id: router})
        for attempt in range(1, 6):
            if attempt > 1:
                with psycopg.connect(DSN, autocommit=True) as fresh:
                    fresh.execute(sql.SQL("""UPDATE {}.resident_deferred_retry_state
                        SET next_attempt_at=clock_timestamp()-interval '1 second'
                        WHERE request_id=%s""").format(sql.Identifier(self.schema)),
                        (deferred["request_id"],))
            self.assertEqual(self.service.resume_deferred(limit=1), 0)
            status = self.service.response_status(self.steward_token,
                deferred["conversation_id"], deferred["request_id"])
            self.assertEqual(status["recovery"]["attempt_count"], attempt)
            if attempt < 5:
                self.assertFalse(status["recovery"]["blocked"])
                self.assertIsNotNone(status["recovery"]["next_attempt_at"])
            else:
                self.assertTrue(status["recovery"]["blocked"])
                self.assertIsNone(status["recovery"]["next_attempt_at"])
        self.assertEqual(self.store.deferred_turns(limit=10), [])
        history = self.service.history(self.steward_token, deferred["conversation_id"])
        request_events = [event for event in history["events"]
            if event["request_id"] == deferred["request_id"]]
        self.assertEqual([event["event_type"] for event in request_events],
                         ["user_message", "response_deferred"])

    def test_failed_30b_fallback_diagnostics_are_durable_and_redacted(self):
        from riverview_core.local_reasoning_provider import LocalReasoningUnavailable, ProviderReadiness
        from riverview_core.resident_execution.model_router import GraceModelRouter
        cpu = _ChatProvider("cpu-autonomic", "c" * 64, "Acknowledged; I do not know from the supplied evidence.")
        vision = _ChatProvider("vision-interim", "d" * 64)
        reasoner = _ChatProvider("reasoning-80b", "e" * 64)
        cpu.provider_id = "test.cpu"
        vision.provider_id = "test.vision"
        reasoner.provider_id = "test.reasoner"
        for provider in (cpu, vision, reasoner):
            provider.readiness = lambda p=provider: ProviderReadiness("READY", p.model, "ready")
        def fail_vision(messages, *, max_tokens, expected_revision, timeout_seconds=120):
            self.assertLessEqual(timeout_seconds, 15)
            raise LocalReasoningUnavailable("endpoint_timeout")
        vision.complete_chat = fail_vision
        router = GraceModelRouter(autonomic=cpu, vision=vision, reasoning=reasoner)
        implementation_id = "implementation:router-fallback:" + uuid4().hex
        self.registry.create_implementation(self.steward_token, implementation_id,
            kind="model", provider_ref=router.provider_id, revision=router.model_sha256)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            implementation_id, expected_binding_revision=1)
        self.service.providers = {router.provider_id: router}

        result = self.service.send(self.steward_token, message="What is a river?",
                                   client_message_id=str(uuid4()))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["model"], "cpu-autonomic")
        history = self.service.history(self.steward_token, result["conversation_id"])
        final = history["events"][-1]
        attempts = final["metadata"]["provider_attempts"]
        self.assertEqual([item["selected_provider"] for item in attempts],
                         ["test.vision", "test.cpu"])
        self.assertEqual(attempts[0]["outcome"], "failed")
        self.assertEqual(attempts[0]["error_code"], "endpoint_timeout")
        self.assertEqual(attempts[0]["reasoning_stage"], "interim_30b")
        self.assertEqual(attempts[0]["fallback_reason"], "interim_30b_provider_failure")
        self.assertEqual(final["metadata"]["final_served_provider"], "test.cpu")
        self.assertTrue(all(item["started_at"] and item["ended_at"] and
                            item["elapsed_ms"] >= 0 for item in attempts))
        encoded = json.dumps(final["metadata"], sort_keys=True)
        self.assertNotIn("What is a river?", encoded)
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN, autocommit=True) as fresh:
            stored = fresh.execute(sql.SQL("""SELECT metadata FROM {}.resident_conversation_events
                WHERE conversation_id=%s AND event_type='assistant_message'""").format(
                    sql.Identifier(self.schema)), (result["conversation_id"],)).fetchone()[0]
        self.assertEqual(stored["final_served_provider"], "test.cpu")

    def test_deferred_request_does_not_resume_after_exact_send_grant_revocation(self):
        from psycopg import sql
        from riverview_core.local_reasoning_provider import ProviderReadiness
        from riverview_core.resident_execution.model_router import GraceModelRouter
        cpu = _ChatProvider("cpu-autonomic", "c" * 64)
        vision = _ChatProvider("vision-interim", "d" * 64)
        reasoner = _ChatProvider("reasoning-80b", "e" * 64)
        cpu.readiness = lambda: ProviderReadiness("READY", cpu.model, "ready")
        vision.readiness = lambda: ProviderReadiness("READY", vision.model, "ready")
        reasoner.state = "MODEL_BUSY"
        reasoner.readiness = lambda: ProviderReadiness(reasoner.state, reasoner.model,
                                                       reasoner.state.lower())
        router = GraceModelRouter(autonomic=cpu, vision=vision, reasoning=reasoner)
        implementation_id = "implementation:router:" + uuid4().hex
        self.registry.create_implementation(self.steward_token, implementation_id,
            kind="model", provider_ref=router.provider_id, revision=router.model_sha256)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            implementation_id, expected_binding_revision=1)
        self.service.providers = {router.provider_id: router}
        deferred = self.service.send(self.steward_token,
            message="Analyze the documented alternatives and recommend a plan.",
            client_message_id=str(uuid4()))
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("""SELECT grant_id FROM {}.authority_grants
                WHERE principal_id=%s AND action=%s AND scope_ref=%s AND revoked_at IS NULL""").format(
                    sql.Identifier(self.schema)),
                (self.steward_id, self.service.SEND_ACTION, "office:" + self.office_id))
            grant_id = cur.fetchone()[0]
        self.registry.revoke_grant(self.steward_token, grant_id)
        reasoner.state = "READY"
        self.assertEqual(self.service.resume_deferred(), 0)
        self.assertEqual(reasoner.calls, [])
        self.assertEqual(self.service.response_status(self.steward_token,
            deferred["conversation_id"], deferred["request_id"])["status"], "deferred")

    def test_existing_deferred_request_patterns_resume_through_explicit_router_upgrade_once(self):
        from psycopg import sql
        from riverview_core.local_reasoning_provider import ChatCompletion
        from riverview_core.resident_execution.model_router import ReasoningDeferred

        old_id = "implementation:grace:readiness-router"
        old_revision = "87ccad04629151f564185ffdef5e961fad4608d805307b431fbe48dbea804cc1"
        next_id = "implementation:grace:readiness-router:608aa519346c"
        next_revision = "608aa519346c4643050b1dff6bc0f0a4d65d2cb9d64b9c07cf1d8faeae3b8c7e"
        request_ids = (
            "49006259-af96-4a6d-8a28-982236fdc4a1",
            "4423857b-1891-405d-9440-61b64b4d294f",
        )

        class DeferredRouter:
            provider_id = "grace.readiness_router.v1"
            model = "grace-readiness-router"
            model_sha256 = old_revision

            def complete_chat(_self, *_args, **_kwargs):
                raise ReasoningDeferred("MODEL_BUSY")

        class SuccessorRouter:
            provider_id = "grace.readiness_router.v1"
            model = "grace-readiness-router"
            model_sha256 = next_revision

            def __init__(_self):
                _self.calls = 0

            def supports_capability(_self, capability):
                return capability == "grace.reasoning.80b"

            def complete_chat(_self, messages, *, max_tokens, expected_revision,
                              required_capability=None):
                _self.calls += 1
                self.assertEqual(required_capability, "grace.reasoning.80b")
                self.assertEqual(expected_revision, next_revision)
                return ChatCompletion("Recovered using the ready reasoning route.",
                    "Qwen3-Next-80B-test-model", 18, 8, "stop",
                    reasoning_stage="reasoning")

        self.registry.create_implementation(self.steward_token, old_id, kind="model",
            provider_ref=DeferredRouter.provider_id, revision=old_revision)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            old_id, expected_binding_revision=1)
        self.service.providers = {DeferredRouter.provider_id: DeferredRouter()}
        created = []
        for index in range(2):
            created.append(self.service.send(self.steward_token,
                message=f"Analyze deferred router upgrade sample {index}.",
                client_message_id=str(uuid4())))
            self.assertEqual(created[-1]["status"], "deferred")
        with self.admin.cursor() as cur:
            for result, request_id in zip(created, request_ids):
                cur.execute(sql.SQL("""UPDATE {}.resident_conversation_events
                    SET request_id=%s WHERE request_id=%s""").format(
                    sql.Identifier(self.schema)), (request_id, result["request_id"]))

        self.registry.create_implementation(self.steward_token, next_id, kind="model",
            provider_ref=DeferredRouter.provider_id, revision=next_revision)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            next_id, expected_binding_revision=2,
            deferred_compatibility_capabilities=("grace.reasoning.80b",))
        router = SuccessorRouter()
        self.service.providers = {router.provider_id: router}
        from riverview_core.status_dashboard.server import (
            _verify_grace_router_startup_readiness)
        binding = _verify_grace_router_startup_readiness(
            self.store.db, schema=self.schema, registry=self.registry,
            resident_credential=self.resident_token, office_id=self.office_id,
            router=router)
        self.assertEqual(binding["implementation_id"], next_id)
        self.assertEqual(binding["implementation_revision"], next_revision)
        self.assertEqual(binding["binding_revision"], 3)

        held_claim = str(uuid4())
        self.assertTrue(self.store.claim_deferred_request(request_ids[0], held_claim))
        self.assertEqual(self.service.resume_deferred(), 1)
        self.store.release_deferred_claim(request_ids[0], held_claim)
        self.assertEqual(self.service.resume_deferred(), 1)
        self.assertEqual(router.calls, 2)
        self.assertEqual(self.service.resume_deferred(), 0)

        for request_id, result in zip(request_ids, created):
            history = self.service.history(self.steward_token, result["conversation_id"])
            final = next(event for event in history["events"]
                         if event["request_id"] == request_id
                         and event["event_type"] == "assistant_message")
            self.assertEqual(final["implementation_id"], next_id)
            self.assertEqual(final["implementation_revision"], next_revision)
            self.assertEqual(final["model_id"], "Qwen3-Next-80B-test-model")
            self.assertEqual(final["metadata"]["original_implementation_id"], old_id)
            self.assertEqual(final["metadata"]["original_implementation_revision"], old_revision)
            self.assertEqual(final["metadata"]["executing_implementation_id"], next_id)
            self.assertEqual(final["metadata"]["executing_implementation_revision"], next_revision)
            self.assertEqual(final["metadata"]["required_capability"], "grace.reasoning.80b")
            self.assertEqual(final["metadata"]["original_steward_authorization"]["principal_id"],
                             self.steward_id)
            self.assertTrue(final["metadata"]["revalidated_grant_id"])
            self.assertEqual(sum(event["event_type"] == "assistant_message"
                                 and event["request_id"] == request_id
                                 for event in history["events"]), 1)
            self.assertEqual(self.service.response_status(self.steward_token,
                result["conversation_id"], request_id)["status"], "completed")

    def test_deferred_80b_resumption_ignores_later_simple_turn_and_logs_sanitized_attempts(self):
        from riverview_core.local_reasoning_provider import (
            ChatCompletion, LocalReasoningUnavailable, ProviderReadiness)
        from riverview_core.resident_execution.model_router import GraceModelRouter

        class Provider:
            def __init__(_self, model, stage, state="READY"):
                _self.model = model
                _self.provider_id = "test." + stage
                _self.model_sha256 = hashlib.sha256(model.encode()).hexdigest()
                _self.state = state
                _self.calls = []
                _self.failure = None

            def readiness(_self):
                return ProviderReadiness(_self.state, _self.model,
                                         "provider_slot_occupied" if _self.state == "MODEL_BUSY"
                                         else _self.state.lower())

            def complete_chat(_self, messages, *, max_tokens, expected_revision,
                              timeout_seconds=120):
                _self.calls.append(messages)
                if _self.failure:
                    raise LocalReasoningUnavailable(_self.failure)
                return ChatCompletion("synthetic verified response", _self.model,
                                      24, 4, "stop")

        cpu = Provider("qwen-0.6b-test", "autonomic")
        vision = Provider("huihui-30b-test", "vision")
        reasoning = Provider("qwen-80b-test", "reasoning", state="MODEL_BUSY")
        router = GraceModelRouter(autonomic=cpu, vision=vision, reasoning=reasoning)
        implementation_id = "implementation:test:deferred-router:" + uuid4().hex
        self.registry.create_implementation(self.steward_token, implementation_id,
            kind="model", provider_ref=router.provider_id, revision=router.model_sha256)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            implementation_id, expected_binding_revision=1)
        self.service.providers = {router.provider_id: router}

        earlier_context = "What is 1 + 1?"
        prior = self.service.send(self.steward_token, message=earlier_context,
                                  client_message_id=str(uuid4()))
        original = "Analyze the original complex engineering objective."
        deferred = self.service.send(self.steward_token, message=original,
            conversation_id=prior["conversation_id"], client_message_id=str(uuid4()))
        self.assertEqual(deferred["status"], "deferred")
        later = self.service.send(self.steward_token,
            message="What is 2 + 2?", conversation_id=deferred["conversation_id"],
            client_message_id=str(uuid4()))
        self.assertEqual(later["status"], "completed")
        self.assertEqual(len(vision.calls), 2)
        self.assertEqual(reasoning.calls, [])

        reasoning.state = "READY"
        reasoning.failure = "endpoint_timeout"
        with self.assertLogs("riverview_core.resident_execution.conversation",
                             level="WARNING") as captured:
            self.assertEqual(self.service.resume_deferred(), 0)
        self.assertEqual(len(reasoning.calls), 1)
        self.assertIn("endpoint_timeout", "\n".join(captured.output))
        self.assertNotIn(original, "\n".join(captured.output))
        self.assertNotIn("What is 2 + 2?", "\n".join(captured.output))

        reasoning.failure = None
        self.assertEqual(self.service.resume_deferred(), 1)
        self.assertEqual(len(reasoning.calls), 2)
        sent_messages = reasoning.calls[-1]
        self.assertEqual(sent_messages[-1]["role"], "user")
        self.assertEqual(sent_messages[-1]["content"], original)
        self.assertIn(earlier_context, [message["content"] for message in sent_messages])
        self.assertNotIn("What is 2 + 2?", [message["content"] for message in sent_messages])
        history = self.service.history(self.steward_token, deferred["conversation_id"])
        original_terminal = [event for event in history["events"]
            if event["request_id"] == deferred["request_id"]
            and event["event_type"] == "assistant_message"]
        self.assertEqual(len(original_terminal), 1)
        self.assertEqual(original_terminal[0]["model_id"], "qwen-80b-test")
        self.assertEqual(original_terminal[0]["metadata"]["required_capability"],
                         "grace.reasoning.80b")
        self.assertEqual(original_terminal[0]["metadata"]["reasoning_stage"], "reasoning")

    def test_unmarked_or_incompatible_router_upgrade_cannot_resume_deferred_request(self):
        from riverview_core.local_reasoning_provider import ChatCompletion
        from riverview_core.resident_execution.model_router import ReasoningDeferred
        old_id = "implementation:grace:readiness-router"
        old_revision = "87ccad04629151f564185ffdef5e961fad4608d805307b431fbe48dbea804cc1"
        next_id = "implementation:grace:readiness-router:608aa519346c"
        next_revision = "608aa519346c4643050b1dff6bc0f0a4d65d2cb9d64b9c07cf1d8faeae3b8c7e"

        class DeferredRouter:
            provider_id = "grace.readiness_router.v1"
            model = "grace-readiness-router"
            model_sha256 = old_revision

            def complete_chat(_self, *_args, **_kwargs):
                raise ReasoningDeferred("MODEL_BUSY")

        class SuccessorRouter:
            provider_id = "grace.readiness_router.v1"
            model = "grace-readiness-router"
            model_sha256 = next_revision
            calls = 0

            def supports_capability(_self, capability):
                return capability == "grace.reasoning.80b"

            def complete_chat(_self, *_args, **_kwargs):
                _self.calls += 1
                return ChatCompletion("Should not run.", "test-model", 1, 1, "stop")

        self.registry.create_implementation(self.steward_token, old_id, kind="model",
            provider_ref=DeferredRouter.provider_id, revision=old_revision)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            old_id, expected_binding_revision=1)
        self.service.providers = {DeferredRouter.provider_id: DeferredRouter()}
        deferred = self.service.send(self.steward_token,
            message="Analyze an incompatible deferred upgrade.",
            client_message_id=str(uuid4()))
        self.assertEqual(deferred["status"], "deferred")
        self.registry.create_implementation(self.steward_token, next_id, kind="model",
            provider_ref=DeferredRouter.provider_id, revision=next_revision)
        # This CAS is authorized, but explicitly omits deferred continuity.
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            next_id, expected_binding_revision=2)
        successor = SuccessorRouter()
        self.service.providers = {successor.provider_id: successor}
        self.assertEqual(self.service.resume_deferred(), 0)
        self.assertEqual(successor.calls, 0)
        self.assertEqual(self.service.response_status(self.steward_token,
            deferred["conversation_id"], deferred["request_id"])["status"], "deferred")

    def test_explicit_successor_cannot_satisfy_a_different_deferred_capability(self):
        from psycopg import sql
        from riverview_core.local_reasoning_provider import ChatCompletion
        from riverview_core.resident_execution.model_router import ReasoningDeferred
        old_id = "implementation:grace:readiness-router"
        old_revision = "87ccad04629151f564185ffdef5e961fad4608d805307b431fbe48dbea804cc1"
        next_id = "implementation:grace:readiness-router:608aa519346c"
        next_revision = "608aa519346c4643050b1dff6bc0f0a4d65d2cb9d64b9c07cf1d8faeae3b8c7e"

        class DeferredRouter:
            provider_id = "grace.readiness_router.v1"
            model = "grace-readiness-router"
            model_sha256 = old_revision

            def complete_chat(_self, *_args, **_kwargs):
                raise ReasoningDeferred("MODEL_BUSY")

        class SuccessorRouter:
            provider_id = "grace.readiness_router.v1"
            model = "grace-readiness-router"
            model_sha256 = next_revision
            calls = 0

            def supports_capability(_self, capability):
                return capability == "grace.reasoning.80b"

            def complete_chat(_self, *_args, **_kwargs):
                _self.calls += 1
                return ChatCompletion("Should not run.", "test-model", 1, 1, "stop")

        self.registry.create_implementation(self.steward_token, old_id, kind="model",
            provider_ref=DeferredRouter.provider_id, revision=old_revision)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            old_id, expected_binding_revision=1)
        self.service.providers = {DeferredRouter.provider_id: DeferredRouter()}
        deferred = self.service.send(self.steward_token,
            message="Analyze a request with an incompatible capability marker.",
            client_message_id=str(uuid4()))
        self.assertEqual(deferred["status"], "deferred")
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("""UPDATE {}.resident_conversation_events
                SET metadata=jsonb_set(metadata,'{{required_capability}}',
                    '\"grace.reasoning.30b\"'::jsonb)
                WHERE request_id=%s AND event_type='response_deferred'""").format(
                    sql.Identifier(self.schema)), (deferred["request_id"],))
        self.registry.create_implementation(self.steward_token, next_id, kind="model",
            provider_ref=DeferredRouter.provider_id, revision=next_revision)
        self.registry.update_office_implementation(self.steward_token, self.office_id,
            next_id, expected_binding_revision=2,
            deferred_compatibility_capabilities=("grace.reasoning.80b",))
        successor = SuccessorRouter()
        self.service.providers = {successor.provider_id: successor}
        self.assertEqual(self.service.resume_deferred(), 0)
        self.assertEqual(successor.calls, 0)
        self.assertEqual(self.service.response_status(self.steward_token,
            deferred["conversation_id"], deferred["request_id"])["status"], "deferred")

    def test_user_event_is_committed_before_inference_and_assistant_before_ack(self):
        message = "fresh-connection durability checkpoint"
        observed = []
        def inspect_before_reply(_messages):
            import psycopg
            from psycopg import sql
            with psycopg.connect(DSN, autocommit=True) as fresh:
                row = fresh.execute(sql.SQL("""SELECT count(*) FROM {}.resident_conversation_events
                    WHERE event_type='user_message' AND body=%s""").format(
                        sql.Identifier(self.schema)), (message,)).fetchone()
            observed.append(row[0])
        self.provider_a.during_completion = inspect_before_reply
        result = self.service.send(self.steward_token, message=message,
                                   client_message_id=str(uuid4()))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(observed, [1], "user event must commit before invoking inference")
        rows = self._fresh_events(result["conversation_id"])
        self.assertEqual([row[1] for row in rows], ["user_message", "assistant_message"])
        self.assertEqual(len(self.service.history(self.steward_token,
            result["conversation_id"])["events"]), len(rows))
        self._assert_connection_idle()

    def test_concurrent_conversations_commit_all_acknowledged_events(self):
        from concurrent.futures import ThreadPoolExecutor
        self.provider_a.during_completion = lambda _messages: time.sleep(0.015)
        count = 8
        barrier = threading.Barrier(count)
        def send_one(index):
            barrier.wait(timeout=5)
            result = self.service.send(self.steward_token,
                message=f"independent parallel conversation {index}",
                client_message_id=str(uuid4()))
            self.assertEqual(result["status"], "completed")
            api_events = self.service.history(self.steward_token,
                result["conversation_id"])["events"]
            committed = self._fresh_events(result["conversation_id"])
            self.assertEqual([event["sequence"] for event in api_events],
                             [row[0] for row in committed])
            self.assertEqual([event["event_type"] for event in api_events],
                             [row[1] for row in committed])
            self.assertEqual([row[1] for row in committed],
                             ["user_message", "assistant_message"])
            return result["conversation_id"]
        with ThreadPoolExecutor(max_workers=count) as pool:
            conversations = list(pool.map(send_one, range(count)))
        self.assertEqual(len(set(conversations)), count)
        self._assert_connection_idle()

    def test_acknowledged_failure_and_restart_recovery_are_independently_durable(self):
        self.service.providers = {}
        failed = self.service.send(self.steward_token, message="provider unavailable",
                                   client_message_id=str(uuid4()))
        self.assertEqual(failed["status"], "unavailable")
        self.assertEqual([row[1] for row in self._fresh_events(failed["conversation_id"])],
                         ["user_message", "response_failed"])
        self._assert_connection_idle()
        self.service.providers = {self.provider_a.provider_id: self.provider_a}
        occupant = self.registry.authorize_office_state(self.resident_token, self.office_id)
        conversation_id, request_id, duplicate, _ = self.store.begin_turn(
            office_id=self.office_id, principal_id=self.steward_id, occupant=occupant,
            implementation={"office_id": self.office_id, "implementation_id": self.impl_a,
                "implementation_revision": self.model_a, "provider_ref": "local.inference.v1",
                "model_id": "cpu-test-a"}, message="interrupted before model response",
            client_message_id=str(uuid4()))
        self.assertFalse(duplicate)
        self.assertEqual([row[1] for row in self._fresh_events(conversation_id)], ["user_message"])
        self.store.close()
        from riverview_core.resident_execution.conversation import ConversationStore
        self.store = ConversationStore(DSN, schema=self.schema)
        self.service.store = self.store
        self.assertEqual(self.store.recover_pending(), 1)
        rows = self._fresh_events(conversation_id)
        self.assertEqual([row[1] for row in rows], ["user_message", "response_interrupted"])
        self._assert_connection_idle()

    def test_model_replacement_preserves_office_identity_and_conversation(self):
        first = self.service.send(self.steward_token, message="Remember this.",
                                  client_message_id=str(uuid4()))
        replacement_id = "resident:" + uuid4().hex
        replacement_token = self.registry.create_principal(
            self.steward_token, replacement_id, "resident", office_id=self.office_id)
        replacement_occupant = "occupant:" + uuid4().hex
        self.registry.create_occupant(self.steward_token, replacement_occupant,
                                      principal_id=replacement_id)
        impl_b = "implementation:" + uuid4().hex
        self.registry.create_implementation(self.steward_token, impl_b,
            kind="model", provider_ref="local.inference.v1", revision=self.model_b)
        self.registry.bind_office(self.steward_token, self.office_id, replacement_occupant, impl_b)
        self.registry.grant(self.steward_token, replacement_id, "office.state.write",
            "office:" + self.office_id, policy_ref="rv.policy:resident-runtime.v1")
        replacement = _ChatProvider("cpu-test-b", self.model_b, "I retained the office history.")
        from riverview_core.resident_execution.conversation import ResidentConversationService
        resumed = ResidentConversationService(store=self.store, registry=self.registry,
            authorizer=self.authorizer, office_id=self.office_id,
            resident_credential=replacement_token, providers={replacement.provider_id: replacement})
        prior = resumed.history(self.steward_token, first["conversation_id"])
        self.assertEqual(prior["events"][1]["model_id"], "cpu-test-a")
        next_turn = resumed.send(self.steward_token, message="Continue.",
            conversation_id=first["conversation_id"], client_message_id=str(uuid4()))
        self.assertEqual(next_turn["model"], "cpu-test-b")
        self.assertEqual(resumed.history(self.steward_token,
            first["conversation_id"])["events"][1]["model_id"], "cpu-test-a")

    def test_missing_model_records_unavailable_and_unfinished_turn_recovers_after_restart(self):
        unavailable = self.service.send("".join([self.steward_token]),
            message="First", client_message_id=str(uuid4()))
        # The configured provider is deliberately removed to exercise fail-closed routing.
        self.service.providers = {}
        model_missing = self.service.send(self.steward_token,
            message="Provider replacement unavailable", client_message_id=str(uuid4()))
        self.assertEqual(model_missing["status"], "unavailable")
        self.assertEqual(model_missing["error_code"], "model_provider_unavailable")
        pending_id = str(uuid4())
        conversation_id, request_id, duplicate, _history = self.store.begin_turn(
            office_id=self.office_id, principal_id=self.steward_id,
            occupant=self.registry.authorize_office_state(self.resident_token, self.office_id),
            implementation={"office_id": self.office_id, "implementation_id": self.impl_a,
                "implementation_revision": self.model_a, "provider_ref": "local.inference.v1",
                "model_id": "cpu-test-a"}, message="interrupted", client_message_id=pending_id)
        self.assertFalse(duplicate)
        self.assertEqual(self.store.recover_pending(), 1)
        status = self.service.response_status(self.steward_token, conversation_id, request_id)
        self.assertEqual(status["status"], "interrupted")
        self.assertEqual(unavailable["status"], "completed")

    def test_large_relevant_context_is_rejected_without_model_call(self):
        conversation_id = None
        for index in range(5):
            result = self.service.send(self.steward_token, message=str(index) + "x" * 5200,
                conversation_id=conversation_id, client_message_id=str(uuid4()))
            conversation_id = result["conversation_id"]
        self.assertEqual(result["status"], "completed")
        # The sixth current turn plus the bounded recent history exceeds 32 KiB.
        self.provider_a.calls.clear()
        result = self.service.send(self.steward_token, message="sixth" + "y" * 5200,
            conversation_id=conversation_id, client_message_id=str(uuid4()))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["error_code"], "context_too_large")
        self.assertEqual(self.provider_a.calls, [])

    def test_authenticated_dashboard_chat_routes_survive_http_server_restart(self):
        from riverview_core.status_dashboard.server import DashboardHTTPServer
        from psycopg import sql
        class Projection:
            pass
        static = ROOT / "src/riverview_core/status_dashboard/static"
        token = "D" * 43
        account_session = "A" * 43
        csrf_token = "C" * 43
        class AccountSessions:
            def authenticate(self, verifier, *, csrf_token=None, state_changing=False):
                if verifier == account_session:
                    if state_changing and csrf_token != "C" * 43:
                        from riverview_core.account_auth import AuthDenied
                        raise AuthDenied()
                    return {"session_id":"test-session", "account_id":"account-test",
                        "email":"steward@example.org", "roles":("steward",),
                        "authority_principal_id":self.principal_id}
                return None
            def require_role(self, identity, *roles):
                if not set(identity.get("roles", ())) & set(roles):
                    from riverview_core.account_auth import AuthDenied
                    raise AuthDenied()
        account_sessions = AccountSessions()
        account_sessions.principal_id = self.steward_id
        with tempfile.TemporaryDirectory() as temp:
            token_path = Path(temp) / "dashboard-token"
            token_path.write_text(token, encoding="ascii")
            token_path.chmod(0o600)
            server = None
            for port in range(8799, 8699, -1):
                try:
                    server = DashboardHTTPServer("127.0.0.1", port, token_path,
                        Projection(), static, conversation_service=self.service,
                        account_auth_service=account_sessions)
                    break
                except OSError:
                    continue
            self.assertIsNotNone(server)
            port = server.server_port
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def request(method, path, *, dashboard=None, authority=None, cookie=None,
                        csrf=None, body=None):
                headers = {}
                if dashboard:
                    headers["Authorization"] = "Bearer " + dashboard
                if authority:
                    headers["X-Riverview-Authority"] = authority
                if cookie:
                    headers["Cookie"] = cookie
                if csrf:
                    headers["X-Riverview-CSRF"] = csrf
                if body is not None:
                    headers["Content-Type"] = "application/json"
                connection = HTTPConnection("127.0.0.1", port, timeout=4)
                connection.request(method, path,
                    body=json.dumps(body) if body is not None else None, headers=headers)
                response = connection.getresponse()
                result = (response.status, response.read())
                connection.close()
                return result

            try:
                self.assertEqual(request("GET", "/api/v1/resident/conversations")[0], 401)
                self.assertEqual(request("GET", "/api/v1/resident/conversations",
                    dashboard=token)[0], 403)
                linked_cookie = "rv_account_session=" + account_session
                linked_status, linked_body = request("POST", "/api/v1/resident/conversation-session",
                    cookie=linked_cookie, csrf=csrf_token)
                self.assertEqual(linked_status, 200)
                self.assertEqual(json.loads(linked_body)["transport"], "authenticated_account_session")
                linked_list_status, _ = request("GET", "/api/v1/resident/conversations",
                    cookie=linked_cookie)
                self.assertEqual(linked_list_status, 200)
                linked_send_status, linked_send_body = request("POST", "/api/v1/resident/conversations",
                    cookie=linked_cookie, csrf=csrf_token,
                    body={"message":"Linked Steward account session test.",
                          "client_message_id":str(uuid4())})
                self.assertEqual(linked_send_status, 201)
                linked_result = json.loads(linked_send_body)
                linked_history_status, linked_history = request("GET",
                    "/api/v1/resident/conversations/" + linked_result["conversation_id"],
                    cookie=linked_cookie)
                self.assertEqual(linked_history_status, 200)
                self.assertIn("Linked Steward account session test.", linked_history.decode())
                sessions = AccountSessions()
                server._account_auth_service = type("RejectUnlinkedGrant", (), {
                    "authenticate": lambda _self, verifier, **_kwargs:
                        {"session_id":"denied", "account_id":"account-denied",
                         "email":"denied@example.org", "roles":("steward",),
                         "authority_principal_id":"steward:ungranted"}
                        if verifier == "N" * 43 else None,
                })()
                self.assertEqual(request("GET", "/api/v1/resident/conversations",
                    cookie="rv_account_session=" + "N" * 43)[0], 403)
                server._account_auth_service = account_sessions
                denied_status, _ = request("POST", "/api/v1/resident/conversation-session",
                    dashboard=token, authority="x" * 48)
                self.assertEqual(denied_status, 403)
                connection = HTTPConnection("127.0.0.1", port, timeout=4)
                connection.request("POST", "/api/v1/resident/conversation-session", headers={
                    "Authorization":"Bearer " + token,
                    "X-Riverview-Authority":self.steward_token})
                response = connection.getresponse()
                session_status = response.status
                session_payload = json.loads(response.read())
                session_cookie = response.getheader("Set-Cookie", "")
                connection.close()
                self.assertEqual(session_status, 200)
                self.assertEqual(session_payload["principal_id"], self.steward_id)
                self.assertEqual(session_payload["scope_ref"], "office:" + self.office_id)
                self.assertEqual(session_payload["expires_in_seconds"], 30 * 24 * 60 * 60)
                self.assertNotIn(self.steward_token, json.dumps(session_payload))
                self.assertTrue(session_cookie.startswith("rv_grace_authority="))
                for attribute in ("HttpOnly", "Secure", "SameSite=Strict", "Path=/api/v1/resident/conversations"):
                    self.assertIn(attribute, session_cookie)
                cookie = session_cookie.split(";", 1)[0]
                list_status, _ = request("GET", "/api/v1/resident/conversations",
                    dashboard=token, cookie=cookie)
                self.assertEqual(list_status, 200)
                # An explicitly supplied bad grant must not fall back to a valid cookie.
                self.assertEqual(request("GET", "/api/v1/resident/conversations",
                    dashboard=token, authority="x" * 48, cookie=cookie)[0], 403)
                self.assertEqual(request("POST", "/api/v1/resident/conversation-session",
                    dashboard=token, authority="x" * 48)[0], 403)
                page_status, shell = request("GET", "/", dashboard=token)
                self.assertEqual(page_status, 200)
                self.assertIn(b"Talk with Grace", shell)
                response_status, response_body = request("POST", "/api/v1/resident/conversations",
                    dashboard=token, cookie=cookie,
                    body={"message":"Browser route check.", "client_message_id":str(uuid4())})
                self.assertEqual(response_status, 201)
                result = json.loads(response_body)
                self.assertEqual(result["status"], "completed")
                path = "/api/v1/resident/conversations/" + result["conversation_id"]
                self.assertEqual(request("GET", path, dashboard=token,
                    cookie=cookie)[0], 200)
                doc_status, doc = request("GET", "/docs/components/RESIDENT_CONVERSATION.md")
                self.assertEqual(doc_status, 200)
                self.assertIn(b"Grace resident conversation", doc)
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                restarted = DashboardHTTPServer("127.0.0.1", port, token_path,
                    Projection(), static, conversation_service=self.service)
                restart_thread = threading.Thread(target=restarted.serve_forever, daemon=True)
                restart_thread.start()
                status, history = request("GET", path, dashboard=token,
                                          cookie=cookie)
                self.assertEqual(status, 200)
                self.assertIn(b"Browser route check.", history)
                connection = HTTPConnection("127.0.0.1", port, timeout=4)
                connection.request("DELETE", "/api/v1/resident/conversation-session",
                    headers={"Authorization":"Bearer " + token})
                response = connection.getresponse()
                logout_body = json.loads(response.read())
                clear_cookie = response.getheader("Set-Cookie", "")
                connection.close()
                self.assertEqual(logout_body["status"], "disconnected")
                self.assertIn("Max-Age=0", clear_cookie)
                self.assertEqual(request("GET", path, dashboard=token)[0], 403)
                # The cookie carries no independent authority: revocation in the existing registry applies immediately.
                with self.admin.cursor() as cur:
                    cur.execute(sql.SQL("UPDATE {}.principal_credentials SET revoked_at=clock_timestamp() WHERE credential_sha256=%s").format(sql.Identifier(self.schema)),
                        (hashlib.sha256(self.steward_token.encode()).digest(),))
                self.assertEqual(request("GET", path, dashboard=token,
                    cookie=cookie)[0], 403)
                restarted.shutdown()
                restarted.server_close()
                restart_thread.join(timeout=3)
            finally:
                if thread.is_alive():
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
