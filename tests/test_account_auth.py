# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_account_auth.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.4.0
# Purpose: Verify account input, transport, and role boundary behavior
# Execution Model: Request-driven unit tests; no Camrui service or database mutation
# Observability: unittest assertions and exit status
# Dependencies: Python 3.10+; temporary filesystem
# Authority: Temporary test files only; no credentials, network, or PostgreSQL access
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Initial auth boundary tests
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Verify PostgreSQL lifecycle, replay, rate limits and revocation
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Verify local-authorized Steward bootstrap and single-use confirmation
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Reject email header delimiters and malformed dot segments
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Cover password reset, scoped grants and administrator notification links
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Verify SMTP settings encryption, redaction and test delivery audit
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SYSTEMD-KEY-ACL | Cover systemd credential ACL acceptance
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SYSTEMD-KEY-ACL-TEST-FIX | Create fixture before making directory read-only
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: This file
# History: Git and revision/backup manifest
# =============================================================================
"""Unit tests for account authentication primitives and safe mail configuration."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from riverview_core.account_auth import (
    AccountAuthService,
    AuthDenied,
    ChallengeInvalid,
    DisabledEmailTransport,
    EmailTransportUnavailable,
    FileDevelopmentEmailTransport,
    _digest,
    _new_token,
    normalize_email,
)
from riverview_core.email_delivery import ConfiguredEmailTransport, read_key
from riverview_core.postgres_migrations import apply_migrations

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1]


class AccountPrimitiveTests(unittest.TestCase):
    def test_email_is_normalized_and_bounded(self):
        self.assertEqual(normalize_email("  Steward@Example.org "), "steward@example.org")
        for invalid in ("", "bad", "a@@example.org", "a b@example.org", "x" * 255 + "@example.org",
                        "attacker@example.org\r\nBcc:evil@example.net", "<a@example.org>", "a..b@example.org"):
            with self.subTest(invalid=invalid[:16]), self.assertRaises(ValueError):
                normalize_email(invalid)

    def test_random_tokens_are_strong_format_and_only_digest_is_stored(self):
        first, second = _new_token(), _new_token()
        self.assertRegex(first, r"^[A-Za-z0-9_-]{43}$")
        self.assertNotEqual(first, second)
        self.assertEqual(len(_digest(first)), 32)
        self.assertNotEqual(_digest(first), first.encode())

    def test_disabled_transport_never_claims_delivery(self):
        with self.assertRaises(EmailTransportUnavailable):
            DisabledEmailTransport().send_verification(
                "person@example.org", purpose="login", challenge_id="x", token="x")

    def test_development_mailbox_requires_owner_only_regular_file(self):
        with tempfile.TemporaryDirectory() as directory:
            mailbox = Path(directory) / "mailbox.jsonl"
            mailbox.touch(mode=0o600)
            mailbox.chmod(0o600)
            transport = FileDevelopmentEmailTransport(mailbox)
            transport.send_verification("person@example.org", purpose="login",
                                         challenge_id="id", token="token")
            content = mailbox.read_text()
            self.assertIn('"purpose":"login"', content)
            self.assertIn('"token":"token"', content)
            self.assertEqual(mailbox.stat().st_mode & 0o077, 0)
            mailbox.chmod(0o644)
            with self.assertRaises(ValueError):
                FileDevelopmentEmailTransport(mailbox)

    def test_steward_boundary_is_enforced_server_side(self):
        service = AccountAuthService(lambda: None, DisabledEmailTransport())
        with self.assertRaises(AuthDenied):
            service.require_role({"roles": ["operator"]}, "steward")
        with self.assertRaises(AuthDenied):
            service.require_role(None, "viewer", "operator", "steward")
        self.assertEqual(service.require_role({"roles": ["viewer"]}, "viewer")["roles"], ["viewer"])

    def test_scrypt_password_hash_is_salted_and_password_policy_is_enforced(self):
        first=AccountAuthService._password_hash("correct horse battery staple")
        second=AccountAuthService._password_hash("correct horse battery staple")
        self.assertNotEqual(first,second)
        self.assertTrue(AccountAuthService._password_matches("correct horse battery staple",first))
        self.assertFalse(AccountAuthService._password_matches("incorrect password",first))
        with self.assertRaises(ValueError):
            AccountAuthService._password_hash("short")

    def test_email_encryption_key_requires_private_regular_file(self):
        from cryptography.fernet import Fernet
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"key"
            key=Fernet.generate_key()
            path.write_bytes(key+b"\n");path.chmod(0o600)
            self.assertEqual(read_key(path),key)
            encrypted=ConfiguredEmailTransport.encrypt_password("provider secret",key)
            self.assertNotIn(b"provider secret",encrypted)
            path.chmod(0o644)
            with self.assertRaises(EmailTransportUnavailable):
                read_key(path)

    def test_systemd_email_key_requires_exact_private_credential_location_and_acl_mode(self):
        from types import SimpleNamespace
        from riverview_core.email_delivery import _is_systemd_email_key

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credentials = root / "riverview-status-dashboard.service"
            credentials.mkdir(mode=0o700)
            key = credentials / "account-email-config-key"
            key.write_bytes(b"test-only-not-an-email-key")
            key.chmod(0o440)
            credentials.chmod(0o500)
            directory_info = SimpleNamespace(st_mode=stat.S_IFDIR | 0o500, st_uid=0)
            allowed_info = SimpleNamespace(st_mode=stat.S_IFREG | 0o440, st_uid=0)
            with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": str(credentials)}), \
                 patch("riverview_core.email_delivery.SYSTEMD_CREDENTIALS_ROOT", root), \
                 patch.object(Path, "stat", return_value=directory_info):
                self.assertTrue(_is_systemd_email_key(key, allowed_info))
                self.assertFalse(_is_systemd_email_key(key, SimpleNamespace(
                    st_mode=stat.S_IFREG | 0o640, st_uid=0)))
                self.assertFalse(_is_systemd_email_key(root / "outside-key", allowed_info))


class _MemoryEmailTransport:
    is_available = True

    def __init__(self):
        self.messages = []

    def send_verification(self, email, *, purpose, challenge_id, token):
        self.messages.append({"email": email, "purpose": purpose,
                              "challenge_id": challenge_id, "token": token})

    def send_message(self,email,*,subject,body):
        self.messages.append({"email":email,"subject":subject,"body":body})


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class AccountAuthPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.psycopg = psycopg
        self.schema = "rvtest_accountauth_" + uuid4().hex[:16]
        with psycopg.connect(DSN, autocommit=True) as conn:
            conn.execute(f'CREATE SCHEMA "{self.schema}"')
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=ROOT / "src/riverview_core/account_auth/migrations")
        self.mail = _MemoryEmailTransport()
        self.service = AccountAuthService(lambda: self.psycopg.connect(DSN), self.mail,
                                          schema=self.schema)
        self.steward_id = str(uuid4())
        with self.psycopg.connect(DSN) as conn:
            conn.execute(f'INSERT INTO "{self.schema}".accounts '
                         "(account_id,email,email_verified_at) VALUES (%s,%s,clock_timestamp())",
                         (self.steward_id, "steward@example.org"))
            conn.execute(f'INSERT INTO "{self.schema}".account_roles (account_id,role) '
                         "VALUES (%s,'steward')", (self.steward_id,))
        self.steward = {"account_id":self.steward_id, "roles":["steward"]}

    def tearDown(self):
        with self.psycopg.connect(DSN, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA "{self.schema}" CASCADE')

    def test_enroll_verify_approval_login_replay_logout_disable_and_revoke(self):
        self.service.request_access("Applicant@Example.org", source_key="127.0.0.1")
        enrollment = self.mail.messages[-1]
        self.assertEqual(enrollment["purpose"], "enrollment")
        self.assertEqual(self.service.verify_enrollment(enrollment["challenge_id"], enrollment["token"]),
                         {"status":"pending_steward_review"})
        with self.assertRaises(ChallengeInvalid):
            self.service.verify_enrollment(enrollment["challenge_id"], enrollment["token"])
        queue = self.service.review_enrollments(self.steward)
        self.assertEqual(queue[0]["email"], "applicant@example.org")
        self.assertEqual(self.service.decide_enrollment(self.steward, queue[0]["enrollment_id"],
            "approve",role="operator",grant_type="one_time")["status"],"approved")
        setup=self.mail.messages[-1]
        self.assertEqual(setup["purpose"],"password_setup")
        self.service.set_password(setup["challenge_id"],setup["token"],"correct horse battery staple")
        with self.psycopg.connect(DSN) as conn:
            stored=conn.execute(f'SELECT password_hash FROM "{self.schema}".accounts '
                                 "WHERE email='applicant@example.org'").fetchone()[0]
        self.assertNotIn("correct horse battery staple",stored)
        session = self.service.authenticate_password("applicant@example.org",
            "correct horse battery staple",source_key="127.0.0.1")
        self.assertEqual(session.expires_in,24*60*60)
        self.assertEqual(session.roles, ("operator",))
        self.assertEqual(self.service.authenticate(session.session_token)["email"], "applicant@example.org")
        with self.assertRaises(AuthDenied):
            self.service.authenticate(session.session_token, csrf_token="X"*43, state_changing=True)
        identity = self.service.authenticate(session.session_token, csrf_token=session.csrf_token,
                                             state_changing=True)
        self.assertIn("operator", identity["roles"])
        self.assertTrue(self.service.logout(session.session_token))
        self.assertIsNone(self.service.authenticate(session.session_token))
        applicant_id = session.account_id
        with self.assertRaises(AuthDenied):
            self.service.authenticate_password("applicant@example.org",
                "correct horse battery staple",source_key="127.0.0.1")
        with self.assertRaises(AuthDenied):
            self.service.revoke_access_grant({"account_id":applicant_id,"roles":["viewer"]},applicant_id)
        self.service.revoke_access_grant(self.steward,applicant_id)
        self.assertIsNone(self.service.authenticate(session.session_token))
        self.service.revoke_sessions(self.steward, applicant_id)
        self.assertIsNone(self.service.authenticate(session.session_token))
        self.service.set_account_state(self.steward, applicant_id, disabled=True)
        self.assertIsNone(self.service.authenticate(session.session_token))

    def test_disposable_account_state_toggle_revokes_sessions_and_writes_audit(self):
        with self.assertRaises(AuthDenied):
            self.service.set_account_state(self.steward, self.steward_id, disabled=True)
        self.service.request_access("state-test@example.org", source_key="127.0.0.9")
        enrollment = self.mail.messages[-1]
        self.service.verify_enrollment(enrollment["challenge_id"], enrollment["token"])
        item = self.service.review_enrollments(self.steward)[0]
        self.service.decide_enrollment(self.steward, item["enrollment_id"],
            "approve", role="operator", grant_type="permanent")
        setup = self.mail.messages[-1]
        self.service.set_password(setup["challenge_id"], setup["token"], "disposable test password")
        session = self.service.authenticate_password("state-test@example.org",
            "disposable test password", source_key="127.0.0.9")
        applicant_id = session.account_id
        applicant = {"account_id":applicant_id, "roles":["operator"]}
        with self.assertRaises(AuthDenied):
            self.service.set_account_state(applicant, applicant_id, disabled=True)

        self.assertEqual(self.service.set_account_state(self.steward, applicant_id,
            disabled=True), {"status":"disabled"})
        self.assertIsNone(self.service.authenticate(session.session_token))
        with self.psycopg.connect(DSN) as conn:
            disabled_at = conn.execute(f'SELECT disabled_at FROM "{self.schema}".accounts '
                "WHERE account_id=%s", (applicant_id,)).fetchone()[0]
            events = conn.execute(f'SELECT event_type FROM "{self.schema}".account_audit '
                "WHERE account_id=%s ORDER BY recorded_at", (applicant_id,)).fetchall()
        self.assertIsNotNone(disabled_at)
        self.assertEqual(events[-1][0], "account_disabled")

        self.assertEqual(self.service.set_account_state(self.steward, applicant_id,
            disabled=False), {"status":"enabled"})
        with self.psycopg.connect(DSN) as conn:
            disabled_at = conn.execute(f'SELECT disabled_at FROM "{self.schema}".accounts '
                "WHERE account_id=%s", (applicant_id,)).fetchone()[0]
            events = conn.execute(f'SELECT event_type FROM "{self.schema}".account_audit '
                "WHERE account_id=%s ORDER BY recorded_at", (applicant_id,)).fetchall()
        self.assertIsNone(disabled_at)
        self.assertEqual(events[-1][0], "account_enabled")
        restored = self.service.authenticate_password("state-test@example.org",
            "disposable test password", source_key="127.0.0.9")
        self.assertEqual(restored.account_id, applicant_id)

    def test_unverified_and_unknown_email_do_not_login_and_rate_limit(self):
        self.service.request_access("new@example.org", source_key="127.0.0.1")
        for _ in range(4):
            self.service.request_access("new@example.org", source_key="127.0.0.1")
        with self.assertRaises(AuthDenied):
            self.service.request_access("new@example.org", source_key="127.0.0.1")
        self.service.request_password_reset("missing@example.org", source_key="127.0.0.2")
        self.assertFalse(any(message["email"] == "missing@example.org" for message in self.mail.messages))

    def test_admin_pending_link_requires_steward_queue_and_denial_notifies_applicant(self):
        with self.psycopg.connect(DSN) as conn:
            conn.execute(f'INSERT INTO "{self.schema}".email_provider_config '
                "(singleton,smtp_host,smtp_port,tls_mode,sender_email,sender_name,admin_email,"
                "reply_to_email,smtp_username,password_ciphertext) "
                "VALUES (TRUE,'smtp.example.org',587,'starttls','sender@example.org','Riverview',"
                "'admin@example.org','','sender@example.org',%s)",(b"encrypted",))
        self.service.request_access("link@example.org",source_key="127.0.0.1")
        challenge=self.mail.messages[-1]
        result=self.service.verify_enrollment(challenge["challenge_id"],challenge["token"])
        self.assertEqual(result["status"],"pending_steward_review")
        notice=next(item for item in reversed(self.mail.messages) if item.get("subject"))
        self.assertEqual(notice["email"],"admin@example.org")
        self.assertIn("#account-approval?enrollment_id=",notice["body"])
        self.assertIn("does not approve or deny",notice["body"])
        pending=self.service.review_enrollments(self.steward)[0]
        self.service.decide_enrollment(self.steward,pending["enrollment_id"],"deny")
        self.assertEqual(self.mail.messages[-1]["email"],"link@example.org")
        self.assertIn("not approved",self.mail.messages[-1]["body"])

    def test_email_settings_encrypt_secret_redact_readback_and_record_test(self):
        from cryptography.fernet import Fernet
        with tempfile.TemporaryDirectory() as directory:
            key_path=Path(directory)/"email-key"
            key_path.write_bytes(Fernet.generate_key()+b"\n")
            key_path.chmod(0o600)
            settings={"smtp_host":"smtp.example.org","smtp_port":587,"tls_mode":"starttls",
                "sender_email":"sender@example.org","sender_name":"Riverview",
                "admin_email":"admin@example.org","reply_to_email":"reply@example.org",
                "smtp_username":"sender@example.org","password":"private smtp password"}
            saved=self.service.save_email_settings(self.steward,settings,key_path=key_path)
            self.assertTrue(saved["password_configured"])
            self.assertNotIn("password",saved)
            with self.psycopg.connect(DSN) as conn:
                ciphertext=conn.execute(f'SELECT password_ciphertext FROM "{self.schema}".'
                    "email_provider_config WHERE singleton=TRUE").fetchone()[0]
            self.assertNotIn(b"private smtp password",bytes(ciphertext))
            settings["password"]=""
            self.service.save_email_settings(self.steward,settings,key_path=key_path)
            with self.psycopg.connect(DSN) as conn:
                self.assertEqual(conn.execute(f'SELECT password_ciphertext FROM "{self.schema}".'
                    "email_provider_config WHERE singleton=TRUE").fetchone()[0],ciphertext)
            status=self.service.test_email_settings(self.steward,key_path=key_path,
                public_origin="https://riverview.example.org")
            self.assertEqual(status["delivery_status"],"sent")
            self.assertEqual(self.mail.messages[-1]["email"],"admin@example.org")

    def test_non_steward_cannot_read_approval_queue_or_change_role(self):
        applicant = {"account_id":str(uuid4()), "roles":["viewer"]}
        with self.assertRaises(AuthDenied):
            self.service.review_enrollments(applicant)
        with self.assertRaises(AuthDenied):
            self.service.change_role(applicant, self.steward_id, "operator", grant=True)

    def test_steward_bootstrap_requires_local_authorization_and_verified_email(self):
        with self.assertRaises(AuthDenied):
            self.service.request_steward_bootstrap(
                "steward@example.org", local_authorized=False,
                authority_principal_id="steward:camrui")
        self.service.request_steward_bootstrap(
            "bootstrap@example.org", local_authorized=True,
            authority_principal_id="steward:camrui")
        challenge = self.mail.messages[-1]
        self.assertEqual(challenge["purpose"], "steward_bootstrap")
        result = self.service.verify_steward_bootstrap(
            challenge["challenge_id"], challenge["token"],
            authority_principal_id="steward:camrui")
        self.assertEqual(result["status"], "steward_account_created")
        self.assertIn("bootstrap@example.org",
                      [account["email"] for account in self.service.list_accounts(self.steward)])
        with self.assertRaises(ChallengeInvalid):
            self.service.verify_steward_bootstrap(
                challenge["challenge_id"], challenge["token"],
                authority_principal_id="steward:camrui")


if __name__ == "__main__":
    unittest.main()
