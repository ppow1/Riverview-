# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_notifications.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.5
# Changed: 2026-10-25 UTC | RV-WEB-V2-GRACE-RECOVERY-SESSION-CAPABILITY | Assert an unlinked Steward session is denied before the decision service
# Changed: 2026-10-24 UTC | RV-DELIVER-GRACE-BLOCKED-ESCALATION-20261024 | Verify idempotent Grace block projection and non-authoritative receipt.
# Purpose: Verify durable visual notice projection, recovery, privacy, and receipt authority
# Execution Model: Isolated PostgreSQL integration tests against unique rvtest_* schemas
# Observability: CME source events, notification rows, receipt ledger, decision request status
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL 16 test database
# Authority: Creates and drops only unique rvtest_* schemas; no shared state
# Changed: 2026-10-11 UTC | RV-M3.2-001 | Normalize final file termination
# Contracts: docs/components/NOTIFICATION_DELIVERY.md
# Tests: This file
# History: New file; Git and revision/backup manifest
# =============================================================================
"""PostgreSQL integration tests for durable, non-authoritative notifications."""

import json
import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from riverview_core.cme import CMEPostgresMonitor
from riverview_core.notifications import (NotificationConflict, NotificationDispatcher,
                                          NotificationNotFound, NotificationService)
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.postgres_migrations import apply_migrations
from riverview_core.status_dashboard.server import DashboardHTTPServer

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


class _NoopProjection:
    pass


class _FakeNotificationService:
    settings = {"schema_version": "rv.notification_settings.v1", "status": "available",
        "level": "all", "quiet_hours": {"enabled": False, "start": "22:00",
        "end": "07:00", "timezone": "UTC"}, "critical_policy": {
        "deliver_during_paused": True, "deliver_during_quiet_hours": True},
        "updated_at": "2026-10-24T00:00:00+00:00"}

    def get_settings(self):
        return self.settings

    def update_settings(self, value):
        self.settings = {**self.settings, **value, "status": "available"}
        return self.settings

    def list_notifications(self, *, limit=25):
        return {"schema_version": "rv.notifications.v1", "status": "available",
                "observed_at": "2026-10-11T00:00:00+00:00", "dispatcher": {"status": "healthy"},
                "items": [], "limit": limit}

    def confirm_delivery(self, notice):
        return {"schema_version": "rv.notification_receipt.v1", "status": "delivered",
                "notification_id": notice, "recorded_at": "2026-10-11T00:00:00+00:00",
                "already_recorded": False, "decision_request_status": None,
                "authority_effect": "none"}

    def acknowledge_receipt(self, notice):
        return {"schema_version": "rv.notification_receipt.v1", "status": "acknowledged",
                "notification_id": notice, "recorded_at": "2026-10-11T00:00:00+00:00",
                "already_recorded": False,
                "decision_request_status": "pending", "authority_effect": "none"}


class NotificationHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token_path = Path(self.temp.name) / "token"
        self.token = "T" * 43
        self.token_path.write_text(self.token)
        self.token_path.chmod(0o600)
        self.server = None
        for port in range(8799, 8699, -1):
            try:
                self.server = DashboardHTTPServer("127.0.0.1", port, self.token_path,
                    _NoopProjection(), ROOT / "src/riverview_core/status_dashboard/static",
                    notification_service=_FakeNotificationService())
                break
            except OSError:
                continue
        self.assertIsNotNone(self.server)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, *, token=None, body=None, cookie=None, csrf=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        headers = {"Authorization": "Bearer " + token} if token else {}
        if cookie:
            headers["Cookie"] = cookie
        if csrf:
            headers["X-Riverview-CSRF"] = csrf
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        result = (response.status, json.loads(response.read()))
        conn.close()
        return result

    def test_notifications_are_authenticated_and_only_receipt_posts_are_allowed(self):
        notice = str(uuid4())
        self.assertEqual(self.request("GET", "/api/v1/notifications")[0], 401)
        status, body = self.request("GET", "/api/v1/notifications?limit=999", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(body["limit"], 50)
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / "docs/components/NOTIFICATION_DELIVERY_API.schema.json").read_text())
        Draft202012Validator(schema).validate(body)
        status, body = self.request("POST", f"/api/v1/notifications/{notice}/acknowledge", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(body["authority_effect"], "none")
        self.assertEqual(body["decision_request_status"], "pending")
        Draft202012Validator(schema).validate(body)
        self.assertEqual(self.request("POST", "/api/v1/status", token=self.token)[0], 405)
        status, body = self.request("POST", f"/api/v1/notifications/{notice}/delivered",
                                    token=self.token, body="x")
        self.assertEqual(status, 400)

    def test_recovery_decision_requires_steward_account_not_dashboard_bearer(self):
        body = json.dumps({"decision": "approve", "reason": "reviewed",
                           "idempotency_key": "test-key"})
        status, result = self.request("POST", f"/api/v1/grace-recovery/{uuid4()}/decision",
                                      token=self.token, body=body)
        self.assertEqual(status, 403)
        self.assertEqual(result["error"], "steward_account_session_required")

    def test_unlinked_steward_account_cannot_record_recovery_decision(self):
        class AccountAuth:
            def authenticate(_self, credential, *, csrf_token, state_changing):
                if credential != "unlinked-session" or (state_changing and csrf_token != "csrf"):
                    from riverview_core.account_auth import AuthDenied
                    raise AuthDenied("denied")
                return {"account_id": "unlinked-steward-test", "roles": ["steward"]}
            def require_role(_self, identity, *roles):
                if not set(identity.get("roles", ())).intersection(roles):
                    from riverview_core.account_auth import AuthDenied
                    raise AuthDenied("role required")
                return identity
        calls = []
        self.server._account_auth_service = AccountAuth()
        self.server._notification_service.decide_grace_recovery = lambda *args, **kwargs: calls.append((args, kwargs))
        body = json.dumps({"decision": "approve", "reason": "disposable denied-path test",
                           "idempotency_key": "unlinked-steward-must-not-write"})
        status, result = self.request("POST", f"/api/v1/grace-recovery/{uuid4()}/decision",
            body=body, cookie="rv_account_session=unlinked-session", csrf="csrf")
        self.assertEqual(status, 403)
        self.assertEqual(result["error"], "steward_account_session_required")
        self.assertEqual(calls, [])

    def test_notification_settings_api_requires_steward_and_persists_update(self):
        class AccountAuth:
            def authenticate(_self, credential, *, csrf_token, state_changing):
                from riverview_core.account_auth import AuthDenied
                if credential != "session" or (state_changing and csrf_token != "csrf"):
                    raise AuthDenied("denied")
                return {"account_id": "account-1", "roles": ["steward"]}
        self.server._account_auth_service = AccountAuth()
        self.assertEqual(self.request("GET", "/api/v1/notification-settings",
                                      token=self.token)[0], 403)
        status, body = self.request("GET", "/api/v1/notification-settings",
            token=self.token, cookie="rv_account_session=session")
        self.assertEqual(status, 200)
        self.assertEqual(body["level"], "all")
        update = json.dumps({"level": "critical_only", "quiet_hours": {
            "enabled": True, "start": "22:00", "end": "07:00", "timezone": "UTC"}})
        status, body = self.request("PUT", "/api/v1/notification-settings", token=self.token,
            cookie="rv_account_session=session", csrf="csrf", body=update)
        self.assertEqual(status, 200)
        self.assertEqual(body["level"], "critical_only")
        self.assertEqual(self.request("GET", "/api/v1/notification-settings", token=self.token,
            cookie="rv_account_session=session")[1]["quiet_hours"]["enabled"], True)

    def test_csrf_steward_recovery_decision_records_exact_request(self):
        class AccountAuth:
            def authenticate(_self, credential, *, csrf_token, state_changing):
                if credential != "session" or (state_changing and csrf_token != "csrf"):
                    from riverview_core.account_auth import AuthDenied
                    raise AuthDenied("denied")
                return {"account_id": "account-1", "roles": ["steward"],
                        "authority_principal_id": "steward:camrui"}
            def require_role(_self, identity, *roles):
                if not set(identity.get("roles", ())).intersection(roles):
                    raise PermissionError("role required")
        calls = []
        self.server._account_auth_service = AccountAuth()
        self.server._notification_service.decide_grace_recovery = lambda request_id, **values: (
            calls.append((request_id, values)) or {"status": "recorded", "retry_dispatched": False})
        request_id = str(uuid4())
        body = json.dumps({"decision": "defer", "reason": "inspect failure record",
                           "idempotency_key": "recovery-defer-once"})
        status, result = self.request("POST", f"/api/v1/grace-recovery/{request_id}/decision",
            body=body, cookie="rv_account_session=session", csrf="csrf")
        self.assertEqual(status, 200, result)
        self.assertEqual(calls[0][0], request_id)
        self.assertEqual(calls[0][1]["actor_principal_id"], "steward:camrui")
        self.assertEqual(calls[0][1]["decision"], "defer")
        self.assertEqual(calls[0][1]["authority_reference"],
                         "account-auth-session:account-1:steward")
        status, _ = self.request("POST", f"/api/v1/grace-recovery/{request_id}/decision",
            body=body, cookie="rv_account_session=session", csrf="wrong")
        self.assertEqual(status, 403)

    def test_dispatcher_unit_is_dedicated_credentialled_and_non_root(self):
        unit = (ROOT / "deploy/systemd/riverview-notification-dispatcher.service").read_text()
        self.assertIn("User=riverview", unit)
        self.assertIn("LoadCredential=pgpass:/etc/riverview/pgpass", unit)
        self.assertIn("NoNewPrivileges=yes", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("riverview-notification-dispatcher/current", unit)
        self.assertNotIn("sudo", unit.lower())


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class NotificationPostgresTests(unittest.TestCase):
    def setUp(self):
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        core = ROOT / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        for component in ("assignment_scheduler", "worker_adapter", "cme", "notifications"):
            apply_migrations(DSN, schema=self.schema,
                             migrations_dir=core / component / "migrations")
        self.admin.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
        self.admin.execute("""CREATE TABLE grace_objectives (
            objective_id TEXT PRIMARY KEY,status TEXT NOT NULL,revision INTEGER NOT NULL,
            assignment_id TEXT)""")
        self.admin.execute("""CREATE TABLE grace_objective_events (
            sequence BIGSERIAL PRIMARY KEY,objective_id TEXT NOT NULL,event_type TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,actor_id TEXT NOT NULL,
            payload JSONB NOT NULL,occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp())""")
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.monitor = CMEPostgresMonitor(DSN, schema=self.schema, stall_after_seconds=0.01)
        self.dispatcher = NotificationDispatcher(DSN, schema=self.schema, poll_interval=0.05)
        self.service = NotificationService(DSN, schema=self.schema)

    def tearDown(self):
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def create_assignment(self, label, *, awaiting=False):
        assignment_id = f"notify-{label}-{uuid4().hex}"
        self.ledger.create(assignment_id, "engineering", f"create:{assignment_id}",
                           authority_ref="grant:test", objective_ref="objective:notification-test",
                           actor_id="resident:test")
        self.ledger.transition(assignment_id, "ready", "ready", f"ready:{assignment_id}",
                               actor_id="event-processor")
        if awaiting:
            self.ledger.transition(assignment_id, "running", "dispatch", f"run:{assignment_id}",
                                   actor_id="worker:test")
            self.ledger.transition(assignment_id, "awaiting_steward", "needs-review",
                                   f"review:{assignment_id}", actor_id="worker:test")
        return assignment_id

    def stale_event(self, assignment_id):
        with self.admin.cursor() as cur:
            cur.execute("UPDATE assignments SET updated_at=clock_timestamp()-interval '10 seconds' "
                        "WHERE id=%s", (assignment_id,))
            cur.execute("UPDATE events SET recorded_at=clock_timestamp()-interval '10 seconds' "
                        "WHERE assignment_id=%s", (assignment_id,))
        observed = self.monitor.scan_once()
        self.assertEqual(observed["status"], "healthy")
        self.assertGreaterEqual(observed["stalled"], 1)

    def rows(self, table):
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("SELECT * FROM {}.{} ORDER BY 1").format(
                sql.Identifier(self.schema), sql.Identifier(table)))
            return cur.fetchall()

    def test_real_stall_event_projects_once_across_dispatcher_restart(self):
        assignment = self.create_assignment("restart")
        self.stale_event(assignment)
        first = self.dispatcher.scan_once()
        self.assertEqual(first["notifications_created"], 1)
        self.assertEqual(self.dispatcher.scan_once()["notifications_created"], 0)
        # A new dispatcher instance has no in-memory cursor; durable uniqueness is the fence.
        restarted = NotificationDispatcher(DSN, schema=self.schema)
        self.assertEqual(restarted.scan_once()["notifications_created"], 0)
        notice = self.rows("attention_notifications")
        self.assertEqual(len(notice), 1)
        self.assertEqual(notice[0]["assignment_id"], assignment)
        self.assertEqual(len(self.rows("notification_events")), 1)

    def test_paused_level_suppresses_routine_phone_delivery(self):
        class Phone:
            messages = []
            def publish(self, event_type, **_context):
                self.messages.append(event_type)
                return "test-message-id"
        self.service.update_settings({"level": "paused", "quiet_hours": {
            "enabled": False, "start": "22:00", "end": "07:00", "timezone": "UTC"}})
        assignment = self.create_assignment("paused")
        self.stale_event(assignment)
        phone = Phone()
        dispatcher = NotificationDispatcher(DSN, schema=self.schema, phone_publisher=phone)
        dispatcher.scan_once()
        self.assertEqual(phone.messages, [])
        self.assertEqual(self.rows("notification_phone_deliveries")[0]["delivery_state"], "suppressed")
        self.assertEqual(self.rows("notification_suppressions")[0]["reason"], "paused")

    def test_grace_block_escalation_projects_with_source_details_and_no_decision_authority(self):
        source_id = uuid4()
        objective_id = "objective:proposal:test:r2"
        details = {"objective_id": objective_id, "objective_revision": 2,
            "runtime_revision": "test-runtime", "failure_count": 33,
            "last_error_code": "PROPOSAL_CRITERIA_BINDING_REJECTED",
            "blocked_at": "2026-10-23T21:01:32-04:00",
            "last_failure_at": "2026-10-23T21:12:29-04:00",
            "decision": "escalate_to_steward",
            "recommended_action": "review_failure_evidence_before_authorizing_retry",
            "automatic_recovery": False}
        self.admin.execute("""INSERT INTO cme_monitor_events
            (event_id,event_key,service_id,event_type,details)
            VALUES (%s,%s,'cme.monitor.v1','grace_objective_blocked',%s::jsonb)""",
            (source_id, f"blocked:{objective_id}", json.dumps(details)))

        first = self.dispatcher.scan_once()
        self.assertEqual(first["notifications_created"], 1)
        self.assertEqual(first["decision_requests_created"], 0)
        notice = self.service.list_notifications(limit=10)["items"][0]
        self.assertEqual(notice["source_event_id"], str(source_id))
        self.assertEqual(notice["event_type"], "grace_objective_blocked")
        self.assertEqual(notice["source_details"], details)
        self.assertEqual(notice["delivery_status"], "queued")
        self.assertIsNone(notice["decision_request_id"])
        self.assertIsNotNone(notice["recovery_request_id"])
        self.assertEqual(notice["recovery_objective_id"], objective_id)
        self.assertEqual(notice["recovery_objective_revision"], 2)
        self.assertEqual(notice["recovery_action"], "retry_reasoning_once")
        self.assertEqual(notice["attempt_limit"], 1)
        self.assertEqual(notice["recovery_status"], "pending")
        self.assertEqual(self.dispatcher.scan_once()["notifications_created"], 0)
        self.assertEqual(len(self.rows("attention_notifications")), 1)
        self.assertEqual(len(self.rows("steward_decision_requests")), 0)

    def _create_recovery_fixture(self, label):
        objective_id = f"objective:recovery-test:{label}:r2"
        source_id = uuid4()
        details = {"objective_id": objective_id, "objective_revision": 2,
            "runtime_revision": "test-runtime", "failure_count": 33,
            "last_error_code": "PROPOSAL_CRITERIA_BINDING_REJECTED",
            "recommended_action": "review_failure_evidence_before_authorizing_retry",
            "automatic_recovery": False}
        self.admin.execute("INSERT INTO grace_objectives VALUES (%s,'GROUNDED',2)", (objective_id,))
        self.admin.execute("""INSERT INTO grace_objective_events
            (objective_id,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,'execution.reasoning_failed',%s,'service:test',%s::jsonb)""",
            (objective_id, f"failure:{label}",
             json.dumps({"status": "BLOCKED", "objective_revision": 2})))
        self.admin.execute("""INSERT INTO cme_monitor_events
            (event_id,event_key,service_id,event_type,details)
            VALUES (%s,%s,'cme.monitor.v1','grace_objective_blocked',%s::jsonb)""",
            (source_id, f"recovery:{label}", json.dumps(details)))
        self.dispatcher.scan_once()
        item = next(item for item in self.service.list_notifications(limit=50)["items"]
                    if item["source_event_id"] == str(source_id))
        return objective_id, source_id, item["recovery_request_id"]

    def test_steward_decision_is_exact_idempotent_and_never_dispatches(self):
        objective_id, source_id, request_id = self._create_recovery_fixture("approve")
        args = {"actor_principal_id": "steward:test",
                "authority_reference": "account-auth-session:test:steward",
                "reason": "Approve exactly one bounded diagnostic retry.",
                "idempotency_key": "recovery-approve-approve"}
        result = self.service.decide_grace_recovery(request_id, decision="approve", **args)
        self.assertEqual(result["objective_id"], objective_id)
        self.assertEqual(result["objective_revision"], 2)
        self.assertEqual(result["source_event_id"], str(source_id))
        self.assertEqual(result["attempt_limit"], 1)
        self.assertFalse(result["retry_dispatched"])
        replay = self.service.decide_grace_recovery(request_id, decision="approve", **args)
        self.assertTrue(replay["idempotent_replay"])
        with self.assertRaises(NotificationConflict):
            self.service.decide_grace_recovery(request_id, decision="approve",
                actor_principal_id=args["actor_principal_id"],
                authority_reference=args["authority_reference"],
                reason="different payload", idempotency_key=args["idempotency_key"])
        self.assertEqual(len(self.rows("grace_recovery_decision_events")), 1)
        self.assertEqual(self.rows("grace_recovery_decision_requests")[0]["status"], "approved")
        self.assertEqual(self.rows("grace_objective_events")[-1]["event_type"],
                         "execution.reasoning_failed")
        with self.assertRaises(NotificationConflict):
            self.service.decide_grace_recovery(request_id, decision="approve",
                actor_principal_id="steward:test",
                authority_reference="account-auth-session:test:steward",
                reason="second decision", idempotency_key="different-key")

    def test_approved_recovery_claim_is_single_use_and_exactly_correlated(self):
        import json
        from types import SimpleNamespace
        from riverview_core.resident_execution.service import GraceExecutionService
        objective_id, source_id, request_id = self._create_recovery_fixture("claim")
        self.service.decide_grace_recovery(request_id, decision="approve",
            actor_principal_id="steward:test",
            authority_reference="account-auth-session:test:steward",
            reason="test exact single-use claim", idempotency_key="recovery-claim")

        class Ledger:
            db = self.admin
            def _set_search_path(inner_self, cur):
                cur.execute("SELECT set_config('search_path', %s, true)", (self.schema,))
        service = object.__new__(GraceExecutionService)
        service.pipeline = SimpleNamespace(ledger=Ledger())
        claimed = service._claim_approved_recovery(objective_id, 2)
        self.assertEqual(claimed, request_id)
        self.assertIsNone(service._claim_approved_recovery(objective_id, 2))
        self.assertIsNone(service._claim_approved_recovery(objective_id + "-other", 2))
        request = next(row for row in self.rows("grace_recovery_decision_requests")
                       if str(row["request_id"]) == request_id)
        self.assertEqual(request["status"], "dispatched")
        recovery_event = next(row for row in self.rows("grace_objective_events")
                              if row["event_type"] == "execution.recovery_authorized")
        payload = recovery_event["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        self.assertEqual(payload["source_event_id"], str(source_id))
        self.assertEqual(payload["objective_id"], objective_id)
        self.assertEqual(payload["objective_revision"], 2)
        self.assertEqual(payload["attempt_limit"], 1)

    def test_defer_and_reject_record_decisions_without_retry(self):
        for label, decision, status in (("defer", "defer", "deferred"),
                                        ("reject", "reject", "rejected")):
            _objective, _event, request_id = self._create_recovery_fixture(label)
            result = self.service.decide_grace_recovery(request_id, decision=decision,
                actor_principal_id="steward:test",
                authority_reference="account-auth-session:test:steward",
                reason=f"Steward {decision}.", idempotency_key=f"recovery-{label}")
            self.assertEqual(result["decision"], decision)
            self.assertFalse(result["retry_dispatched"])
            row = self.admin.execute("SELECT status FROM grace_recovery_decision_requests WHERE request_id=%s",
                                     (request_id,)).fetchone()
            self.assertEqual(row["status"], status)

    def test_stale_revision_expired_request_and_attempt_limit_fail_closed(self):
        objective_id, _event, stale_request = self._create_recovery_fixture("stale")
        self.admin.execute("UPDATE grace_objectives SET revision=3 WHERE objective_id=%s",
                           (objective_id,))
        with self.assertRaises(NotificationConflict):
            self.service.decide_grace_recovery(stale_request, decision="approve",
                actor_principal_id="steward:test",
                authority_reference="account-auth-session:test:steward", reason="stale",
                idempotency_key="recovery-stale")
        _objective, _event, expired_request = self._create_recovery_fixture("expired")
        self.admin.execute("UPDATE grace_recovery_decision_requests SET expires_at=clock_timestamp()-interval '1 second' WHERE request_id=%s",
                           (expired_request,))
        expired = self.service.decide_grace_recovery(expired_request, decision="approve",
            actor_principal_id="steward:test",
            authority_reference="account-auth-session:test:steward", reason="expired",
            idempotency_key="recovery-expired")
        self.assertEqual(expired["status"], "expired")
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.admin.execute("UPDATE grace_recovery_decision_requests SET attempt_limit=2 WHERE request_id=%s",
                               (expired_request,))

    def test_receipt_states_are_ordered_idempotent_and_never_resolve_request(self):
        assignment = self.create_assignment("awaiting", awaiting=True)
        self.monitor.scan_once()
        with self.admin.cursor() as cur:
            cur.execute("SELECT event_id FROM cme_monitor_events WHERE assignment_id=%s "
                        "AND event_type='assignment_attention'", (assignment,))
            self.assertIsNotNone(cur.fetchone())
        self.dispatcher.scan_once()
        notices = self.service.list_notifications(limit=10)["items"]
        self.assertEqual(len(notices), 1)
        notice = notices[0]
        self.assertEqual(notice["delivery_status"], "queued")
        self.assertEqual(notice["decision_status"], "pending")
        with self.assertRaises(NotificationConflict):
            self.service.acknowledge_receipt(notice["notification_id"])
        delivered = self.service.confirm_delivery(notice["notification_id"])
        self.assertEqual(delivered["authority_effect"], "none")
        self.assertEqual(delivered["decision_request_status"], "pending")
        self.assertTrue(self.service.confirm_delivery(notice["notification_id"])["already_recorded"])
        ack = self.service.acknowledge_receipt(notice["notification_id"])
        self.assertEqual(ack["decision_request_status"], "pending")
        self.assertEqual(ack["authority_effect"], "none")
        self.assertTrue(self.service.acknowledge_receipt(notice["notification_id"])["already_recorded"])
        self.assertEqual(self.rows("steward_decision_requests")[0]["status"], "pending")
        self.assertEqual(len(self.rows("notification_events")), 3)

    def test_private_assignment_never_becomes_an_external_notice(self):
        assignment = self.create_assignment("private")
        with self.admin.cursor() as cur:
            cur.execute("UPDATE events SET privacy_domain='undercurrent' WHERE assignment_id=%s",
                        (assignment,))
        self.stale_event(assignment)
        self.assertEqual(self.dispatcher.scan_once()["notifications_created"], 0)
        self.assertEqual(self.service.list_notifications()["items"], [])

    def test_unknown_and_unavailable_states_are_not_success(self):
        with self.assertRaises(NotificationNotFound):
            self.service.confirm_delivery(str(uuid4()))
        missing = NotificationService(DSN, schema="rvtest_absent_notifications")
        page = missing.list_notifications()
        self.assertEqual(page["status"], "not_initialized")

    def test_receipt_history_is_append_only_and_stopped_dispatcher_becomes_stale(self):
        assignment = self.create_assignment("stale-health")
        self.stale_event(assignment)
        self.dispatcher.scan_once()
        notice = self.rows("attention_notifications")[0]
        with self.assertRaises(psycopg.errors.RaiseException):
            self.admin.execute("UPDATE notification_events SET event_type='delivery_confirmed'")
        with self.assertRaises(psycopg.errors.RaiseException):
            self.admin.execute("DELETE FROM notification_events")
        self.admin.execute("UPDATE notification_dispatcher_health SET last_heartbeat_at="
                           "clock_timestamp()-interval '30 seconds' "
                           "WHERE service_id='notification.dispatcher.v1'")
        page = self.service.list_notifications(limit=10)
        self.assertEqual(page["dispatcher"]["status"], "stale")
        self.assertGreater(page["dispatcher"]["heartbeat_age_seconds"], 15)
        self.assertEqual(page["items"][0]["notification_id"], str(notice["notification_id"]))
