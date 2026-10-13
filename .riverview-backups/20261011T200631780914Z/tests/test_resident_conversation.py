# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_conversation.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.0
# Purpose: Verify durable office-scoped chat, exact authority, model binding and restart recovery
# Execution Model: Isolated PostgreSQL integration and bounded fake provider
# Observability: Test assertions and sanitized outcome states; no prompt logging
# Dependencies: Psycopg 3; private RIVERVIEW_TEST_PG_DSN
# Authority: Creates only unique disposable rvtest schemas and identities
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Initial resident conversation regression suite
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# Tests: python3 -m unittest tests.test_resident_conversation
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Isolated PostgreSQL and authority tests for Grace's persistent conversation path."""

import hashlib
import os
from pathlib import Path
import secrets
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

    def complete_chat(self, messages, *, max_tokens, expected_revision,
                      timeout_seconds=120):
        from riverview_core.local_reasoning_provider import ChatCompletion
        self.calls.append((messages, max_tokens, expected_revision))
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
        history = self.service.history(self.steward_token, result["conversation_id"])
        self.assertEqual([e["event_type"] for e in history["events"]],
                         ["user_message", "assistant_message"])
        self.assertEqual(history["events"][1]["implementation_revision"], self.model_a)
        self.assertEqual(history["events"][1]["metadata"]["completion_tokens"], 9)
        self.assertEqual(self.service.response_status(self.steward_token,
            result["conversation_id"], result["request_id"])["status"], "completed")

    def test_exact_grant_denial_does_not_create_a_conversation_or_call_model(self):
        from riverview_core.resident_execution.conversation import ConversationDenied
        with self.assertRaises(ConversationDenied):
            self.service.send(secrets.token_urlsafe(32), message="unauthorized")
        self.assertEqual(self.provider_a.calls, [])

    def test_client_retry_is_idempotent_and_does_not_repeat_inference(self):
        key = str(uuid4())
        first = self.service.send(self.steward_token, message="Same message", client_message_id=key)
        retry = self.service.send(self.steward_token, message="Same message",
            conversation_id=first["conversation_id"], client_message_id=key)
        self.assertTrue(retry["duplicate"])
        self.assertEqual(len(self.provider_a.calls), 1)
        self.assertEqual(len(self.service.history(self.steward_token,
            first["conversation_id"])["events"]), 2)

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


if __name__ == "__main__":
    unittest.main()
