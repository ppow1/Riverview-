# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_conversation.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.5
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
        history = self.service.history(self.steward_token, result["conversation_id"])
        self.assertEqual([e["event_type"] for e in history["events"]],
                         ["user_message", "assistant_message"])
        self.assertEqual(history["events"][1]["implementation_revision"], self.model_a)
        self.assertEqual(history["events"][1]["metadata"]["completion_tokens"], 9)
        self.assertEqual([row[1] for row in self._fresh_events(result["conversation_id"])],
                         ["user_message", "assistant_message"])
        self._assert_connection_idle()
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
        with tempfile.TemporaryDirectory() as temp:
            token_path = Path(temp) / "dashboard-token"
            token_path.write_text(token, encoding="ascii")
            token_path.chmod(0o600)
            server = None
            for port in range(8799, 8699, -1):
                try:
                    server = DashboardHTTPServer("127.0.0.1", port, token_path,
                        Projection(), static, conversation_service=self.service)
                    break
                except OSError:
                    continue
            self.assertIsNotNone(server)
            port = server.server_port
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def request(method, path, *, dashboard=None, authority=None, cookie=None, body=None):
                headers = {}
                if dashboard:
                    headers["Authorization"] = "Bearer " + dashboard
                if authority:
                    headers["X-Riverview-Authority"] = authority
                if cookie:
                    headers["Cookie"] = cookie
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
