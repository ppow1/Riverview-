# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_conversation.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.18
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
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# Tests: python3 -m unittest tests.test_resident_conversation
# History: Git and .riverview-backups/manifest.jsonl
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
        self.assertEqual(self.provider_a.calls[0][1], 64)
        prompt = self.provider_a.calls[0][0][0]["content"]
        self.assertIn("Director of Operations", prompt)
        self.assertIn("Alfred is the separate Chief of Staff", prompt)
        self.assertIn("Continuous Momentum Engine (CME)", prompt)
        self.assertIn("this role description grants no permission", prompt)
        history = self.service.history(self.steward_token, result["conversation_id"])
        self.assertEqual([e["event_type"] for e in history["events"]],
                         ["user_message", "assistant_message"])
        self.assertEqual(history["events"][1]["implementation_revision"], self.model_a)
        self.assertEqual(history["events"][1]["metadata"]["completion_tokens"], 9)
        self.assertEqual(history["events"][1]["metadata"]["role_context_revision"], "1.0.0")
        self.assertEqual([row[1] for row in self._fresh_events(result["conversation_id"])],
                         ["user_message", "assistant_message"])
        self._assert_connection_idle()
        self.assertEqual(self.service.response_status(self.steward_token,
            result["conversation_id"], result["request_id"])["status"], "completed")

    def test_verified_engineering_result_returns_once_to_source_conversation(self):
        self.registry.grant(self.steward_token, self.resident_id,
            "resident.conversation.send", "office:" + self.office_id,
            policy_ref="rv.policy:resident-conversation-result.v1")
        self.provider_a.model = "Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf"
        self.provider_a.answer = "The verified report is ready at the recorded path."
        turn = self.service.send(self.steward_token, message="Create a short verified engineering report.",
            client_message_id=str(uuid4()))
        context = {"objective_id":"objective:grace-conversation:result-test",
            "assignment_id":"assignment:grace:result-test",
            "request":"Create a short verified engineering report.",
            "acceptance_criteria":["The report is readable."],
            "proposal":{"summary":"Create report", "steps":[]},
            "submitter_id":self.steward_id,
            "origin":{"conversation_id":turn["conversation_id"], "source_sequence":1},
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
        self.assertEqual(self.provider_a.calls[-1][2], self.model_a)
        history = self.service.history(self.steward_token, turn["conversation_id"])
        reviews = [event for event in history["events"] if
                   event["metadata"].get("result_kind") == "verified_engineering_review"]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["model_id"], self.provider_a.model)
        self.assertEqual(reviews[0]["metadata"]["verification_decision"], "ACCEPTED")
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
        history = self.service.history(self.steward_token, deferred["conversation_id"])
        self.assertEqual(history["events"][-1]["body"], "The verified analysis is complete.")
        self.assertTrue(history["events"][-1]["metadata"]["resumed_deferred_request"])
        self.assertEqual(len([event for event in history["events"]
                              if event["event_type"] == "user_message"]), 1)

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
            result = self.service.send(self.steward_token, message=str(index) + "x" * 6000,
                conversation_id=conversation_id, client_message_id=str(uuid4()))
            conversation_id = result["conversation_id"]
        self.assertEqual(result["status"], "completed")
        # The sixth current turn plus the bounded recent history exceeds 32 KiB.
        self.provider_a.calls.clear()
        result = self.service.send(self.steward_token, message="sixth" + "y" * 6000,
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
