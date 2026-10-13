# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/account_auth/__init__.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.3.0
# Purpose: Durable email enrollment, Steward review, role and browser session lifecycle
# Execution Model: Request-driven API service
# Observability: PostgreSQL account audit events and fixed HTTP outcome codes
# Dependencies: PostgreSQL 16; DB-API connection factory; email transport interface
# Authority: Website roles grant dashboard access only; exact engineering grants remain separate
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Initial account lifecycle and security primitives
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Add local-authorized, email-verified Steward bootstrap
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Audit request and delivery outcomes without exposing challenges
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Allow realistic shared-source login volume within throttled windows
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Expose truthful bounded account readiness and delivery configuration
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Keep absent schema counts explicitly unknown
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Restrict email syntax to prevent header injection
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Add scoped approval grants, passwords and shared mail settings
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: tests/test_account_auth.py
# History: Git and revision/backup manifest
# =============================================================================
"""Account enrollment and browser authentication, separate from engineering grants."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone

_EMAIL = re.compile(r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@"
                    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
                    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
_ROLES = frozenset({"viewer", "operator", "steward"})
_CHALLENGE_TTL = 15 * 60
_SESSION_TTL = 30 * 24 * 60 * 60
_SCRYPT_N = 16384
_DUMMY_SCRYPT_SALT = secrets.token_bytes(16)


class AccountAuthError(Exception):
    """Base error exposing only a stable, non-sensitive code."""

    code = "account_auth_failed"


class AuthDenied(AccountAuthError):
    code = "not_authorized"


class AuthUnavailable(AccountAuthError):
    code = "account_auth_unavailable"


class ChallengeInvalid(AccountAuthError):
    code = "challenge_invalid_or_expired"


class EmailTransportUnavailable(AccountAuthError):
    code = "email_delivery_unavailable"


@dataclass(frozen=True)
class IssuedSession:
    account_id: str
    email: str
    roles: tuple[str, ...]
    session_token: str
    csrf_token: str
    expires_in: int = _SESSION_TTL


def normalize_email(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("email_invalid")
    candidate = value.strip().casefold()
    local = candidate.partition("@")[0]
    if (len(candidate) > 254 or not _EMAIL.fullmatch(candidate)
            or local.startswith(".") or local.endswith(".") or ".." in local):
        raise ValueError("email_invalid")
    return candidate


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _digest(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()


class AccountAuthService:
    """PostgreSQL-backed login and Steward account workflow.

    ``email_transport.send_verification`` must deliver out of band. The service
    never returns challenge tokens from public methods and never logs request data.
    """

    def __init__(self, connection_factory, email_transport, *, schema="riverview_accounts",
                 clock=time.time, public_origin="https://192.168.1.155"):
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
            raise ValueError("invalid account schema")
        self._connect = connection_factory
        self._email = email_transport
        self._schema = schema
        self._clock = clock
        if not isinstance(public_origin,str) or not public_origin.startswith("https://"):
            raise ValueError("account_public_https_origin_required")
        self._public_origin = public_origin.rstrip("/")

    def _table(self, name):
        if name not in {"enrollments", "accounts", "account_roles", "challenges",
                        "sessions", "account_audit", "rate_limits", "email_provider_config"}:
            raise ValueError("invalid relation")
        return f'"{self._schema}"."{name}"'

    @staticmethod
    def _password_hash(password):
        if not isinstance(password, str) or not 12 <= len(password) <= 1024:
            raise ValueError("password_policy_failed")
        import base64
        salt = secrets.token_bytes(16)
        derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=8, p=1, dklen=32)
        return f"scrypt${_SCRYPT_N}$8$1$" + base64.urlsafe_b64encode(salt).decode().rstrip("=") \
            + "$" + base64.urlsafe_b64encode(derived).decode().rstrip("=")

    @staticmethod
    def _password_matches(password, encoded):
        import base64
        try:
            algorithm, n, r, p, salt_text, expected_text = encoded.split("$")
            if algorithm != "scrypt" or (n, r, p) != (str(_SCRYPT_N), "8", "1"):
                return False
            salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
            expected = base64.urlsafe_b64decode(expected_text + "=" * (-len(expected_text) % 4))
            actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=8, p=1, dklen=32)
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError, AttributeError):
            return False

    def _execute(self, operation):
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    return operation(cur)
        except AccountAuthError:
            raise
        except Exception:
            raise AuthUnavailable() from None

    def _rate_limit(self, cur, key, *, limit=5, window=900):
        now = int(self._clock())
        digest = _digest(key)
        cur.execute(
            f"INSERT INTO {self._table('rate_limits')} (key_hash, window_started_at, attempts) "
            "VALUES (%s, to_timestamp(%s), 1) ON CONFLICT (key_hash) DO UPDATE SET "
            "window_started_at = CASE WHEN "
            f"{self._table('rate_limits')}.window_started_at <= to_timestamp(%s) "
            "THEN to_timestamp(%s) ELSE "
            f"{self._table('rate_limits')}.window_started_at END, attempts = CASE WHEN "
            f"{self._table('rate_limits')}.window_started_at <= to_timestamp(%s) "
            "THEN 1 ELSE "
            f"{self._table('rate_limits')}.attempts + 1 END RETURNING attempts, "
            f"window_started_at + interval '{int(window)} seconds' > to_timestamp(%s)",
            (digest, now, now - window, now, now - window, now))
        attempts, in_window = cur.fetchone()
        if in_window and attempts > limit:
            raise AuthDenied()

    def request_access(self, email: str, *, source_key: str):
        address = normalize_email(email)
        if not isinstance(source_key, str) or not 1 <= len(source_key) <= 128:
            raise ValueError("source_invalid")
        if not getattr(self._email, "is_available", False):
            raise EmailTransportUnavailable()
        token = _new_token()
        challenge_id = secrets.token_urlsafe(18)
        expires = int(self._clock()) + _CHALLENGE_TTL

        def create(cur):
            self._rate_limit(cur, "email:" + address)
            self._rate_limit(cur, "source:" + source_key, limit=60)
            cur.execute(f"SELECT status FROM {self._table('enrollments')} WHERE email=%s FOR UPDATE",
                        (address,))
            row = cur.fetchone()
            if row and row[0] in {"approved", "pending", "rejected", "disabled"}:
                return False
            cur.execute(
                f"INSERT INTO {self._table('enrollments')} "
                "(email, status, created_at, updated_at) VALUES (%s, 'awaiting_email', "
                "clock_timestamp(), clock_timestamp()) ON CONFLICT (email) DO UPDATE SET "
                "status='awaiting_email', updated_at=clock_timestamp()",
                (address,))
            cur.execute(
                f"INSERT INTO {self._table('challenges')} "
                "(challenge_id, email, purpose, token_hash, expires_at, created_at) "
                "VALUES (%s, %s, 'enrollment', %s, to_timestamp(%s), clock_timestamp())",
                (challenge_id, address, _digest(token), expires))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type, subject_email, recorded_at) "
                        "VALUES ('enrollment_requested', %s, clock_timestamp())", (address,))
            return True

        should_send = self._execute(create)
        if should_send:
            try:
                self._email.send_verification(address, purpose="enrollment",
                                              challenge_id=challenge_id, token=token)
            except Exception:
                self._record_delivery(address, "email_delivery_failed")
            else:
                self._record_delivery(address, "email_challenge_delivered")
        return {"status": "if_eligible_check_email", "expires_in": _CHALLENGE_TTL}

    def verify_enrollment(self, challenge_id: str, token: str):
        if not isinstance(challenge_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,32}", challenge_id):
            raise ChallengeInvalid()
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise ChallengeInvalid()

        def verify(cur):
            cur.execute(
                f"UPDATE {self._table('challenges')} SET consumed_at=clock_timestamp() "
                "WHERE challenge_id=%s AND purpose='enrollment' AND consumed_at IS NULL "
                "AND expires_at > clock_timestamp() AND token_hash=%s RETURNING email",
                (challenge_id, _digest(token)))
            row = cur.fetchone()
            if not row:
                raise ChallengeInvalid()
            email = row[0]
            cur.execute(f"UPDATE {self._table('enrollments')} SET status='pending', "
                        "email_verified_at=clock_timestamp(), updated_at=clock_timestamp() "
                        "WHERE email=%s AND status='awaiting_email' RETURNING enrollment_id",
                        (email,))
            enrollment = cur.fetchone()
            if not enrollment:
                raise ChallengeInvalid()
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type, subject_email, recorded_at) "
                        "VALUES ('enrollment_email_verified', %s, clock_timestamp())", (email,))
            return {"status": "pending_steward_review", "enrollment_id":str(enrollment[0]),
                    "email":email}
        result=self._execute(verify)
        self._notify_admin_pending(result["enrollment_id"],result["email"])
        return {"status":result["status"]}

    def _record_delivery(self, email, event_type):
        def record(cur):
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type, subject_email, recorded_at) VALUES (%s, %s, clock_timestamp())",
                        (event_type, email))
            failed=event_type.endswith("failed")
            cur.execute(f"UPDATE {self._table('email_provider_config')} "
                "SET last_delivery_at=clock_timestamp(),last_delivery_status=%s,last_delivery_error=%s "
                "WHERE singleton=TRUE",("failed" if failed else "sent",
                                         "smtp_delivery_failed" if failed else None))
        self._execute(record)

    def _challenge(self, email, purpose):
        challenge_id, token = secrets.token_urlsafe(18), _new_token()
        expires = int(self._clock()) + _CHALLENGE_TTL
        def create(cur):
            cur.execute(f"INSERT INTO {self._table('challenges')} "
                        "(challenge_id,email,purpose,token_hash,expires_at,created_at) "
                        "VALUES (%s,%s,%s,%s,to_timestamp(%s),clock_timestamp())",
                        (challenge_id,email,purpose,_digest(token),expires))
        self._execute(create)
        try:
            self._email.send_verification(email, purpose=purpose,
                                          challenge_id=challenge_id, token=token)
        except Exception:
            self._record_delivery(email, "email_delivery_failed")
            raise EmailTransportUnavailable() from None
        self._record_delivery(email, "email_challenge_delivered")

    def _send_notice(self, recipient, subject, body, event_type):
        try:
            if not hasattr(self._email, "send_message"):
                raise EmailTransportUnavailable()
            self._email.send_message(recipient, subject=subject, body=body)
        except Exception:
            self._record_delivery(recipient, "email_delivery_failed")
            return False
        self._record_delivery(recipient, event_type)
        return True

    def _notify_admin_pending(self, enrollment_id, email):
        try:
            def lookup(cur):
                cur.execute(f"SELECT admin_email FROM {self._table('email_provider_config')} "
                            "WHERE singleton=TRUE")
                row=cur.fetchone()
                return row[0] if row else None
            recipient=self._execute(lookup)
            if not recipient:
                raise EmailTransportUnavailable()
            link=f"{self._public_origin}/#account-approval?enrollment_id={enrollment_id}"
            sent=self._send_notice(recipient,"Riverview access request pending",
                f"A verified access request is pending for {email}.\n\n"
                f"Open the pending request in Riverview: {link}\n\n"
                "Sign in as a Steward to review it. Opening this link does not approve or deny access.",
                "admin_approval_notice_sent")
            if not sent:
                return False
            return True
        except Exception:
            self._record_delivery(email,"admin_approval_notice_failed")
            return False

    def request_password_reset(self, email, *, source_key):
        address = normalize_email(email)
        if not isinstance(source_key, str) or not 1 <= len(source_key) <= 128:
            raise ValueError("source_invalid")
        if not getattr(self._email, "is_available", False):
            raise EmailTransportUnavailable()
        def find(cur):
            self._rate_limit(cur, "password-reset-email:" + address)
            self._rate_limit(cur, "password-reset-source:" + source_key, limit=60)
            cur.execute(f"SELECT 1 FROM {self._table('accounts')} WHERE email=%s "
                        "AND disabled_at IS NULL AND password_hash IS NOT NULL", (address,))
            return cur.fetchone() is not None
        if self._execute(find):
            self._challenge(address, "password_reset")
        return {"status":"if_eligible_check_email", "expires_in":_CHALLENGE_TTL}

    def set_password(self, challenge_id, token, password):
        if (not isinstance(challenge_id, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{20,32}", challenge_id)
                or not isinstance(token, str) or not _TOKEN.fullmatch(token)):
            raise ChallengeInvalid()
        password_hash = self._password_hash(password)
        def update(cur):
            cur.execute(f"UPDATE {self._table('challenges')} SET consumed_at=clock_timestamp() "
                        "WHERE challenge_id=%s AND purpose IN ('password_setup','password_reset') "
                        "AND consumed_at IS NULL AND expires_at>clock_timestamp() AND token_hash=%s "
                        "RETURNING email,purpose", (challenge_id,_digest(token)))
            row = cur.fetchone()
            if not row:
                raise ChallengeInvalid()
            email,purpose = row
            predicate = "password_hash IS NULL" if purpose == "password_setup" else "password_hash IS NOT NULL"
            cur.execute(f"UPDATE {self._table('accounts')} SET password_hash=%s "
                        f"WHERE email=%s AND disabled_at IS NULL AND {predicate} RETURNING account_id",
                        (password_hash,email))
            account = cur.fetchone()
            if not account:
                raise ChallengeInvalid()
            if purpose == "password_reset":
                cur.execute(f"UPDATE {self._table('sessions')} SET revoked_at=clock_timestamp() "
                            "WHERE account_id=%s AND revoked_at IS NULL", (account[0],))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type,account_id,subject_email,recorded_at) "
                        "VALUES (%s,%s,%s,clock_timestamp())",
                        ("password_set" if purpose == "password_setup" else "password_reset",
                         account[0],email))
            return {"status":"password_set"}
        return self._execute(update)

    def authenticate_password(self, email, password, *, source_key):
        address = normalize_email(email)
        if (not isinstance(password,str) or len(password)>1024
                or not isinstance(source_key,str) or not 1<=len(source_key)<=128):
            raise AuthDenied()
        session_token, csrf_token = _new_token(), _new_token()
        def login(cur):
            self._rate_limit(cur,"password-login-email:"+address,limit=10)
            self._rate_limit(cur,"password-login-source:"+source_key,limit=60)
            cur.execute(f"SELECT account_id,password_hash,grant_type,grant_expires_at,grant_revoked_at,"
                        f"one_time_session_created_at FROM {self._table('accounts')} "
                        "WHERE email=%s AND disabled_at IS NULL FOR UPDATE",(address,))
            account=cur.fetchone()
            if not account or not account[1]:
                hashlib.scrypt(password.encode("utf-8"),salt=_DUMMY_SCRYPT_SALT,
                               n=_SCRYPT_N,r=8,p=1,dklen=32)
                raise AuthDenied()
            if not self._password_matches(password,account[1]):
                raise AuthDenied()
            account_id,password_hash,grant_type,grant_expiry,grant_revoked,one_time_used=account
            if grant_revoked or (grant_expiry and grant_expiry.timestamp()<=self._clock()):
                raise AuthDenied()
            if grant_type=="one_time":
                if one_time_used:
                    raise AuthDenied()
                cur.execute(f"UPDATE {self._table('accounts')} "
                            "SET one_time_session_created_at=clock_timestamp() "
                            "WHERE account_id=%s AND one_time_session_created_at IS NULL",(account_id,))
                if cur.rowcount!=1:
                    raise AuthDenied()
            cur.execute(f"SELECT role FROM {self._table('account_roles')} "
                        "WHERE account_id=%s ORDER BY role",(account_id,))
            roles=tuple(row[0] for row in cur.fetchall())
            if not roles:
                raise AuthDenied()
            session_ttl=24*60*60 if grant_type=="one_time" else _SESSION_TTL
            expiry_sql=("LEAST(clock_timestamp() + (%s * interval '1 second'), a.grant_expires_at)"
                        if grant_expiry else "clock_timestamp() + (%s * interval '1 second')")
            cur.execute(f"INSERT INTO {self._table('sessions')} "
                        f"(account_id,token_hash,csrf_hash,created_at,expires_at) "
                        f"SELECT %s,%s,%s,clock_timestamp(),{expiry_sql} "
                        f"FROM {self._table('accounts')} a WHERE a.account_id=%s",
                        (account_id,_digest(session_token),_digest(csrf_token),session_ttl,account_id))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type,account_id,subject_email,recorded_at) "
                        "VALUES ('session_created',%s,%s,clock_timestamp())",(account_id,address))
            return IssuedSession(str(account_id),address,roles,session_token,csrf_token,session_ttl)
        return self._execute(login)

    def email_settings(self, actor):
        self.require_role(actor,"steward")
        def read(cur):
            cur.execute(f"SELECT smtp_host,smtp_port,tls_mode,sender_email,sender_name,admin_email,"
                        f"reply_to_email,smtp_username,password_ciphertext,last_test_at,last_test_status,"
                        f"last_test_error,last_delivery_at,last_delivery_status,last_delivery_error "
                        f"FROM {self._table('email_provider_config')} WHERE singleton=TRUE")
            row=cur.fetchone()
            if not row:
                return {"configured":False,"password_configured":False,"delivery_status":"not_configured"}
            keys=("smtp_host","smtp_port","tls_mode","sender_email","sender_name","admin_email",
                  "reply_to_email","smtp_username")
            result=dict(zip(keys,row[:8]))
            result.update({"configured":True,"password_configured":bool(row[8]),
                           "last_test_at":row[9].isoformat() if row[9] else None,
                           "delivery_status":row[10] or "not_tested","last_test_error":row[11],
                           "last_delivery_at":row[12].isoformat() if row[12] else None,
                           "last_delivery_status":row[13] or "not_tested",
                           "last_delivery_error":row[14]})
            return result
        return self._execute(read)

    def save_email_settings(self, actor, settings, *, key_path):
        self.require_role(actor,"steward")
        if not isinstance(settings,dict):
            raise ValueError("smtp_configuration_invalid")
        from ..email_delivery import ConfiguredEmailTransport, read_key
        from email.utils import parseaddr
        required={"smtp_host","smtp_port","tls_mode","sender_email","sender_name",
                  "admin_email","reply_to_email","smtp_username"}
        if set(settings)-required-{"password"} or not required.issubset(settings):
            raise ValueError("smtp_configuration_invalid")
        host=settings["smtp_host"]
        port=settings["smtp_port"]
        tls_mode=settings["tls_mode"]
        if not isinstance(host,str) or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}",host):
            raise ValueError("smtp_configuration_invalid")
        if type(port) is not int or not 1<=port<=65535 or tls_mode not in {"starttls","implicit"}:
            raise ValueError("smtp_configuration_invalid")
        sender=normalize_email(settings["sender_email"])
        admin=normalize_email(settings["admin_email"])
        reply_to=settings["reply_to_email"].strip()
        if reply_to:
            reply_to=normalize_email(reply_to)
        sender_name=settings["sender_name"]
        username=settings["smtp_username"].strip()
        if (not isinstance(sender_name,str) or not sender_name.strip() or len(sender_name)>120
                or "\r" in sender_name or "\n" in sender_name or not username or len(username)>254):
            raise ValueError("smtp_configuration_invalid")
        password=settings.get("password","")
        key=read_key(key_path)
        def save(cur):
            cur.execute(f"SELECT password_ciphertext FROM {self._table('email_provider_config')} "
                        "WHERE singleton=TRUE")
            old=cur.fetchone()
            if not password and not old:
                raise ValueError("smtp_password_required")
            encrypted=(ConfiguredEmailTransport.encrypt_password(password,key)
                       if password else bytes(old[0]))
            cur.execute(f"INSERT INTO {self._table('email_provider_config')} "
                        "(singleton,smtp_host,smtp_port,tls_mode,sender_email,sender_name,admin_email,"
                        "reply_to_email,smtp_username,password_ciphertext,updated_by,updated_at,last_test_at,"
                        "last_test_status,last_test_error) VALUES (TRUE,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                        "clock_timestamp(),NULL,NULL,NULL) ON CONFLICT (singleton) DO UPDATE SET "
                        "smtp_host=EXCLUDED.smtp_host,smtp_port=EXCLUDED.smtp_port,tls_mode=EXCLUDED.tls_mode,"
                        "sender_email=EXCLUDED.sender_email,sender_name=EXCLUDED.sender_name,"
                        "admin_email=EXCLUDED.admin_email,reply_to_email=EXCLUDED.reply_to_email,"
                        "smtp_username=EXCLUDED.smtp_username,password_ciphertext=EXCLUDED.password_ciphertext,"
                        "updated_by=EXCLUDED.updated_by,updated_at=clock_timestamp(),last_test_at=NULL,"
                        "last_test_status=NULL,last_test_error=NULL",
                        (host,port,tls_mode,sender,sender_name.strip(),admin,reply_to,username,encrypted,
                         actor["account_id"]))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type,actor_account_id,recorded_at) "
                        "VALUES ('email_provider_configured',%s,clock_timestamp())",(actor["account_id"],))
        self._execute(save)
        return self.email_settings(actor)

    def test_email_settings(self, actor, *, key_path, public_origin):
        self.require_role(actor,"steward")
        settings=self.email_settings(actor)
        if not settings.get("configured"):
            raise EmailTransportUnavailable()
        transport=getattr(self._email,"send_message",None)
        if transport is None:
            raise EmailTransportUnavailable()
        recipient=settings["admin_email"]
        try:
            transport(recipient,subject="Riverview email configuration test",
                      body="This is a test message initiated by an authenticated Riverview Steward.")
            status,error="sent",None
        except Exception:
            status,error="failed","smtp_delivery_failed"
        def record(cur):
            cur.execute(f"UPDATE {self._table('email_provider_config')} SET last_test_at=clock_timestamp(),"
                        "last_test_status=%s,last_test_error=%s,last_delivery_at=clock_timestamp(),"
                        "last_delivery_status=%s,last_delivery_error=%s WHERE singleton=TRUE",
                        (status,error,status,error))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type,actor_account_id,recorded_at) VALUES (%s,%s,clock_timestamp())",
                        ("email_test_"+status,actor["account_id"]))
        self._execute(record)
        return {"delivery_status":status,"error":error}

    def request_steward_bootstrap(self, email: str, *, local_authorized: bool,
                                  authority_principal_id: str):
        """Issue a verified-email bootstrap challenge after explicit local authorization."""
        address = normalize_email(email)
        if local_authorized is not True or authority_principal_id != "steward:camrui":
            raise AuthDenied()
        if not getattr(self._email, "is_available", False):
            raise EmailTransportUnavailable()
        challenge_id, token = secrets.token_urlsafe(18), _new_token()
        expires = int(self._clock()) + _CHALLENGE_TTL

        def create(cur):
            self._rate_limit(cur, "email:" + address)
            cur.execute(f"SELECT 1 FROM {self._table('accounts')} "
                        "WHERE email=%s OR authority_principal_id=%s FOR UPDATE",
                        (address, authority_principal_id))
            if cur.fetchone():
                raise AuthDenied()
            cur.execute(f"INSERT INTO {self._table('challenges')} "
                        "(challenge_id, email, purpose, token_hash, expires_at, created_at) "
                        "VALUES (%s, %s, 'steward_bootstrap', %s, to_timestamp(%s), clock_timestamp())",
                        (challenge_id, address, _digest(token), expires))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type, subject_email, recorded_at) "
                        "VALUES ('steward_bootstrap_requested', %s, clock_timestamp())", (address,))
        self._execute(create)
        try:
            self._email.send_verification(address, purpose="steward_bootstrap",
                                          challenge_id=challenge_id, token=token)
        except Exception:
            self._record_delivery(address, "email_delivery_failed")
        else:
            self._record_delivery(address, "email_challenge_delivered")
        return {"status": "if_delivered_check_email", "expires_in": _CHALLENGE_TTL}

    def verify_steward_bootstrap(self, challenge_id: str, token: str, *,
                                 authority_principal_id: str):
        if authority_principal_id != "steward:camrui":
            raise AuthDenied()
        if not isinstance(challenge_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,32}", challenge_id):
            raise ChallengeInvalid()
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise ChallengeInvalid()
        def create(cur):
            cur.execute(f"UPDATE {self._table('challenges')} SET consumed_at=clock_timestamp() "
                        "WHERE challenge_id=%s AND purpose='steward_bootstrap' AND consumed_at IS NULL "
                        "AND expires_at > clock_timestamp() AND token_hash=%s RETURNING email",
                        (challenge_id, _digest(token)))
            challenge = cur.fetchone()
            if not challenge:
                raise ChallengeInvalid()
            email = challenge[0]
            cur.execute(f"INSERT INTO {self._table('accounts')} "
                        "(email, email_verified_at, created_at, authority_principal_id) "
                        "VALUES (%s, clock_timestamp(), clock_timestamp(), %s) RETURNING account_id",
                        (email, authority_principal_id))
            account_id = cur.fetchone()[0]
            cur.execute(f"INSERT INTO {self._table('account_roles')} "
                        "(account_id, role) VALUES (%s, 'steward')", (account_id,))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type, account_id, subject_email, recorded_at) "
                        "VALUES ('steward_bootstrap_verified', %s, %s, clock_timestamp())",
                        (account_id, email))
            return {"status": "steward_account_created", "email": email}
        result=self._execute(create)
        try:
            self._challenge(result["email"],"password_setup")
        except Exception:
            self._record_delivery(result["email"],"applicant_approval_notice_failed")
        return {"status":result["status"]}

    def authenticate(self, session_token: str, *, csrf_token: str | None = None,
                     state_changing=False):
        if not isinstance(session_token, str) or not _TOKEN.fullmatch(session_token):
            return None
        if state_changing and (not isinstance(csrf_token, str) or not _TOKEN.fullmatch(csrf_token)):
            raise AuthDenied()

        def read(cur):
            cur.execute(f"SELECT s.session_id, a.account_id, a.email, s.csrf_hash "
                        f"FROM {self._table('sessions')} s JOIN {self._table('accounts')} a USING (account_id) "
                        "WHERE s.token_hash=%s AND s.revoked_at IS NULL "
                        "AND s.expires_at > clock_timestamp() AND a.disabled_at IS NULL "
                        "AND a.grant_revoked_at IS NULL "
                        "AND (a.grant_expires_at IS NULL OR a.grant_expires_at>clock_timestamp())",
                        (_digest(session_token),))
            row = cur.fetchone()
            if not row:
                return None
            session_id, account_id, email, csrf_hash = row
            if state_changing and not hmac.compare_digest(bytes(csrf_hash), _digest(csrf_token)):
                raise AuthDenied()
            cur.execute(f"SELECT role FROM {self._table('account_roles')} WHERE account_id=%s ORDER BY role",
                        (account_id,))
            roles = tuple(item[0] for item in cur.fetchall())
            if not roles:
                return None
            return {"session_id": str(session_id), "account_id": str(account_id),
                    "email": email, "roles": roles}
        return self._execute(read)

    def status(self):
        """Return a bounded, PII-free readiness projection for the owning dashboard."""
        def read(cur):
            observed = datetime.fromtimestamp(self._clock(), timezone.utc).isoformat()
            cur.execute("SELECT to_regclass(%s) IS NOT NULL",
                        (f"{self._schema}.schema_migrations",))
            if not cur.fetchone()[0]:
                return {"component_id":"WEBSITE-ACCOUNT-AUTH", "status":"not_initialized",
                        "email_delivery":"configured_unverified" if getattr(self._email, "is_available", False) else "disabled",
                        "accounts":None, "pending_enrollments":None, "pending_email":None,
                        "observed_at":observed}
            cur.execute(f"SELECT count(*) FILTER (WHERE disabled_at IS NULL), "
                        f"(SELECT count(*) FROM {self._table('enrollments')} WHERE status='pending'), "
                        f"(SELECT count(*) FROM {self._table('enrollments')} WHERE status='awaiting_email') "
                        f"FROM {self._table('accounts')}")
            active, pending, awaiting = cur.fetchone()
            configured = bool(getattr(self._email, "is_available", False))
            return {"component_id":"WEBSITE-ACCOUNT-AUTH",
                    "status":"degraded",
                    "email_delivery":"configured_unverified" if configured else "disabled",
                    "accounts":int(active), "pending_enrollments":int(pending),
                    "pending_email":int(awaiting), "observed_at":observed}
        try:
            return self._execute(read)
        except AuthUnavailable:
            return {"component_id":"WEBSITE-ACCOUNT-AUTH", "status":"unavailable",
                    "email_delivery":"configured_unverified" if getattr(self._email, "is_available", False) else "disabled",
                    "accounts":None, "pending_enrollments":None, "pending_email":None,
                    "observed_at":datetime.fromtimestamp(self._clock(), timezone.utc).isoformat()}

    def logout(self, session_token: str):
        if not isinstance(session_token, str) or not _TOKEN.fullmatch(session_token):
            return False
        def revoke(cur):
            cur.execute(f"UPDATE {self._table('sessions')} SET revoked_at=clock_timestamp() "
                        "WHERE token_hash=%s AND revoked_at IS NULL RETURNING account_id",
                        (_digest(session_token),))
            row = cur.fetchone()
            if row:
                cur.execute(f"INSERT INTO {self._table('account_audit')} "
                            "(event_type, account_id, recorded_at) "
                            "VALUES ('session_revoked', %s, clock_timestamp())", (row[0],))
            return bool(row)
        return self._execute(revoke)

    def review_enrollments(self, actor, *, limit=50):
        if "steward" not in actor.get("roles", ()):
            raise AuthDenied()
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit_invalid")
        def read(cur):
            cur.execute(f"SELECT enrollment_id, email, status, email_verified_at, created_at "
                        f"FROM {self._table('enrollments')} WHERE status='pending' "
                        "ORDER BY created_at, enrollment_id LIMIT %s", (limit,))
            return [{"enrollment_id": str(row[0]), "email": row[1], "status": row[2],
                     "email_verified_at": row[3].isoformat() if row[3] else None,
                     "created_at": row[4].isoformat()} for row in cur.fetchall()]
        return self._execute(read)

    def list_accounts(self, actor, *, limit=50):
        if "steward" not in actor.get("roles", ()):
            raise AuthDenied()
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit_invalid")
        def read(cur):
            cur.execute(f"SELECT a.account_id,a.email,a.disabled_at,r.role,a.grant_type,"
                        "a.grant_expires_at,a.grant_revoked_at,a.one_time_session_created_at "
                        f"FROM {self._table('accounts')} a LEFT JOIN {self._table('account_roles')} r "
                        "USING (account_id) ORDER BY a.created_at DESC, a.account_id LIMIT %s", (limit,))
            rows = cur.fetchall()
            grouped = {}
            for account_id,email,disabled_at,role,grant_type,grant_expiry,grant_revoked,one_time_used in rows:
                key = str(account_id)
                if key not in grouped:
                    grouped[key] = {"account_id": key, "email": email,
                                    "disabled": disabled_at is not None, "roles": [],
                                    "grant_type":grant_type,
                                    "grant_expires_at":grant_expiry.isoformat() if grant_expiry else None,
                                    "grant_revoked":grant_revoked is not None,
                                    "one_time_used":one_time_used is not None}
                if role:
                    grouped[key]["roles"].append(role)
            return list(grouped.values())
        return self._execute(read)

    def decide_enrollment(self, actor, enrollment_id, decision, *, role="viewer",
                          grant_type=None):
        self.require_role(actor,"steward")
        if decision not in {"approve","deny"}:
            raise ValueError("decision_invalid")
        if decision=="approve" and (role not in _ROLES or grant_type not in
                                     {"one_time","90_days","one_year","permanent"}):
            raise ValueError("approval_grant_invalid")
        def decide(cur):
            cur.execute(f"SELECT email FROM {self._table('enrollments')} "
                        "WHERE enrollment_id=%s AND status='pending' FOR UPDATE",(enrollment_id,))
            row=cur.fetchone()
            if not row:
                raise ChallengeInvalid()
            email=row[0]
            account_id=None
            if decision=="approve":
                cur.execute(f"INSERT INTO {self._table('accounts')} "
                    "(email,email_verified_at,created_at,grant_type,grant_expires_at,grant_revoked_at,"
                    "one_time_session_created_at) VALUES (%s,clock_timestamp(),clock_timestamp(),%s,"
                    "CASE %s WHEN 'one_time' THEN clock_timestamp()+interval '24 hours' "
                    "WHEN '90_days' THEN clock_timestamp()+interval '90 days' "
                    "WHEN 'one_year' THEN clock_timestamp()+interval '1 year' ELSE NULL END,NULL,NULL) "
                    "ON CONFLICT (email) DO UPDATE SET email_verified_at=EXCLUDED.email_verified_at,"
                    "grant_type=EXCLUDED.grant_type,grant_expires_at=EXCLUDED.grant_expires_at,"
                    "grant_revoked_at=NULL,one_time_session_created_at=NULL "
                    "WHERE accounts.disabled_at IS NULL RETURNING account_id",
                    (email,grant_type,grant_type))
                account=cur.fetchone()
                if not account:
                    raise AuthDenied()
                account_id=account[0]
                cur.execute(f"INSERT INTO {self._table('account_roles')} "
                    "(account_id,role,granted_by) VALUES (%s,%s,%s) "
                    "ON CONFLICT (account_id,role) DO UPDATE SET granted_by=EXCLUDED.granted_by,"
                    "granted_at=clock_timestamp()",(account_id,role,actor["account_id"]))
                cur.execute(f"UPDATE {self._table('sessions')} SET revoked_at=clock_timestamp() "
                            "WHERE account_id=%s AND revoked_at IS NULL",(account_id,))
                cur.execute(f"UPDATE {self._table('enrollments')} SET status='approved',granted_role=%s,"
                    "grant_type=%s,decided_at=clock_timestamp(),decided_by=%s,updated_at=clock_timestamp() "
                    "WHERE enrollment_id=%s",(role,grant_type,actor["account_id"],enrollment_id))
            else:
                cur.execute(f"UPDATE {self._table('enrollments')} SET status='rejected',granted_role=NULL,"
                    "grant_type=NULL,decided_at=clock_timestamp(),decided_by=%s,updated_at=clock_timestamp() "
                    "WHERE enrollment_id=%s",(actor["account_id"],enrollment_id))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                "(event_type,account_id,subject_email,actor_account_id,recorded_at) "
                "VALUES (%s,%s,%s,%s,clock_timestamp())",
                ("enrollment_approved" if decision=="approve" else "enrollment_denied",
                 account_id,email,actor["account_id"]))
            return {"email":email,"account_id":str(account_id) if account_id else None}
        result=self._execute(decide)
        if decision=="deny":
            self._send_notice(result["email"],"Riverview access request update",
                "Your Riverview access request was not approved. Contact the Riverview Steward if you believe this was an error.",
                "applicant_denial_notice_sent")
        else:
            try:
                self._challenge(result["email"],"password_setup")
            except Exception:
                self._record_delivery(result["email"],"applicant_approval_notice_failed")
        return {"status":"approved" if decision=="approve" else "denied",
                "account_id":result["account_id"]}

    def revoke_access_grant(self, actor, account_id):
        self.require_role(actor,"steward")
        if actor.get("account_id")==str(account_id):
            raise AuthDenied()
        def revoke(cur):
            cur.execute(f"UPDATE {self._table('accounts')} SET grant_revoked_at=clock_timestamp() "
                        "WHERE account_id=%s AND grant_revoked_at IS NULL RETURNING email",
                        (account_id,))
            row=cur.fetchone()
            if not row:
                raise ChallengeInvalid()
            cur.execute(f"UPDATE {self._table('sessions')} SET revoked_at=clock_timestamp() "
                        "WHERE account_id=%s AND revoked_at IS NULL",(account_id,))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type,account_id,subject_email,actor_account_id,recorded_at) "
                        "VALUES ('access_grant_revoked',%s,%s,%s,clock_timestamp())",
                        (account_id,row[0],actor["account_id"]))
            return {"status":"grant_revoked"}
        return self._execute(revoke)

    def set_account_state(self, actor, account_id, *, disabled):
        if "steward" not in actor.get("roles", ()):
            raise AuthDenied()
        if type(disabled) is not bool:
            raise ValueError("disabled_invalid")
        if disabled and actor["account_id"] == str(account_id):
            raise AuthDenied()
        def update(cur):
            cur.execute(f"UPDATE {self._table('accounts')} SET disabled_at="
                        "CASE WHEN %s THEN clock_timestamp() ELSE NULL END "
                        "WHERE account_id=%s RETURNING email", (disabled, account_id))
            row = cur.fetchone()
            if not row:
                raise ChallengeInvalid()
            if disabled:
                cur.execute(f"UPDATE {self._table('sessions')} SET revoked_at=clock_timestamp() "
                            "WHERE account_id=%s AND revoked_at IS NULL", (account_id,))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type, account_id, subject_email, actor_account_id, recorded_at) "
                        "VALUES (%s, %s, %s, %s, clock_timestamp())",
                        ("account_disabled" if disabled else "account_enabled", account_id, row[0], actor["account_id"]))
            return {"status": "disabled" if disabled else "enabled"}
        return self._execute(update)

    def change_role(self, actor, account_id, role, *, grant):
        if "steward" not in actor.get("roles", ()):
            raise AuthDenied()
        if role not in _ROLES or type(grant) is not bool:
            raise ValueError("role_invalid")
        if role == "steward" and actor["account_id"] == str(account_id):
            raise AuthDenied()
        def update(cur):
            if role == "steward" and not grant:
                cur.execute(f"SELECT account_id FROM {self._table('account_roles')} "
                            "WHERE role='steward' ORDER BY account_id FOR UPDATE")
                if len(cur.fetchall()) <= 1:
                    raise AuthDenied()
            cur.execute(f"SELECT email FROM {self._table('accounts')} WHERE account_id=%s "
                        "AND disabled_at IS NULL FOR UPDATE", (account_id,))
            row = cur.fetchone()
            if not row:
                raise ChallengeInvalid()
            if grant:
                cur.execute(f"INSERT INTO {self._table('account_roles')} (account_id, role, granted_by) "
                            "VALUES (%s, %s, %s) ON CONFLICT (account_id, role) DO NOTHING",
                            (account_id, role, actor["account_id"]))
            else:
                cur.execute(f"DELETE FROM {self._table('account_roles')} WHERE account_id=%s AND role=%s",
                            (account_id, role))
                cur.execute(f"UPDATE {self._table('sessions')} SET revoked_at=clock_timestamp() "
                            "WHERE account_id=%s AND revoked_at IS NULL", (account_id,))
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type, account_id, subject_email, actor_account_id, recorded_at) "
                        "VALUES (%s, %s, %s, %s, clock_timestamp())",
                        ("role_granted" if grant else "role_revoked", account_id, row[0], actor["account_id"]))
            return {"status": "updated"}
        return self._execute(update)

    def revoke_sessions(self, actor, account_id):
        if "steward" not in actor.get("roles", ()):
            raise AuthDenied()
        def revoke(cur):
            cur.execute(f"SELECT email FROM {self._table('accounts')} WHERE account_id=%s FOR UPDATE",
                        (account_id,))
            row = cur.fetchone()
            if not row:
                raise ChallengeInvalid()
            cur.execute(f"UPDATE {self._table('sessions')} SET revoked_at=clock_timestamp() "
                        "WHERE account_id=%s AND revoked_at IS NULL", (account_id,))
            count = cur.rowcount
            cur.execute(f"INSERT INTO {self._table('account_audit')} "
                        "(event_type, account_id, subject_email, actor_account_id, recorded_at) "
                        "VALUES ('sessions_revoked', %s, %s, %s, clock_timestamp())",
                        (account_id, row[0], actor["account_id"]))
            return {"status": "revoked", "sessions_revoked": count}
        return self._execute(revoke)

    @staticmethod
    def require_role(identity, *roles):
        if identity is None or not set(identity.get("roles", ())).intersection(roles):
            raise AuthDenied()
        return identity


class DisabledEmailTransport:
    """Fail closed until an approved delivery provider is configured."""

    is_available = False

    def send_verification(self, email, *, purpose, challenge_id, token):
        raise EmailTransportUnavailable()


class SMTPEmailTransport:
    """TLS-only SMTP delivery using an externally approved relay configuration."""

    is_available = True

    def __init__(self, *, host, port, sender, public_origin, tls_mode="starttls",
                 username=None, password_file=None, sender_name="Riverview",
                 reply_to=None, timeout=10):
        from email.utils import parseaddr
        from pathlib import Path
        import re as _re
        if (not isinstance(host, str) or not _re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host)
                or not 1 <= int(port) <= 65535):
            raise ValueError("smtp_configuration_invalid")
        if tls_mode not in {"starttls", "implicit"}:
            raise ValueError("smtp_tls_required")
        if parseaddr(sender)[1] != sender or "\r" in sender or "\n" in sender:
            raise ValueError("smtp_sender_invalid")
        if (not isinstance(sender_name, str) or len(sender_name) > 120
                or "\r" in sender_name or "\n" in sender_name):
            raise ValueError("smtp_sender_name_invalid")
        if reply_to is not None and (parseaddr(reply_to)[1] != reply_to
                                     or "\r" in reply_to or "\n" in reply_to):
            raise ValueError("smtp_reply_to_invalid")
        if (not isinstance(public_origin, str) or not public_origin.startswith("https://")
                or any(character in public_origin for character in "?#\r\n")):
            raise ValueError("account_public_https_origin_required")
        self.host = host
        self.port = int(port)
        self.sender = sender
        self.sender_name = sender_name
        self.reply_to = reply_to
        self.public_origin = public_origin.rstrip("/")
        self.tls_mode = tls_mode
        self.username = username
        self.password_file = Path(password_file) if password_file else None
        self.timeout = timeout
        if bool(username) != bool(self.password_file):
            raise ValueError("smtp_credentials_incomplete")

    def _password(self):
        if self.password_file is None:
            return None
        import os
        import stat
        try:
            descriptor = os.open(self.password_file,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(descriptor, "r", encoding="utf-8") as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                    raise EmailTransportUnavailable()
                value = source.read(4097).rstrip("\r\n")
        except (OSError, UnicodeError):
            raise EmailTransportUnavailable() from None
        if not value or len(value) > 4096 or "\r" in value or "\n" in value:
            raise EmailTransportUnavailable()
        return value

    def send_message(self, email, *, subject, body, password_override=None):
        from email.message import EmailMessage
        import ssl
        import smtplib
        from email.utils import formataddr
        if (not isinstance(subject, str) or not subject or len(subject) > 200
                or "\r" in subject or "\n" in subject
                or not isinstance(body, str) or len(body) > 20000):
            raise EmailTransportUnavailable()
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.sender_name, self.sender))
        message["To"] = email
        if self.reply_to:
            message["Reply-To"] = self.reply_to
        message.set_content(body)
        password = (self._password() if password_override is None else password_override)
        try:
            context = ssl.create_default_context()
            if self.tls_mode == "implicit":
                connection = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout,
                                              context=context)
            else:
                connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
                connection.ehlo()
                connection.starttls(context=context)
                connection.ehlo()
            try:
                if self.username:
                    connection.login(self.username, password)
                refused = connection.send_message(message)
                if refused:
                    raise EmailTransportUnavailable()
            finally:
                connection.quit()
        except EmailTransportUnavailable:
            raise
        except Exception:
            raise EmailTransportUnavailable() from None

    def send_verification(self, email, *, purpose, challenge_id, token):
        from urllib.parse import urlencode
        if purpose not in {"login", "enrollment", "steward_bootstrap", "password_setup", "password_reset"}:
            raise EmailTransportUnavailable()
        fragment = urlencode({"purpose": purpose, "challenge_id": challenge_id, "token": token})
        link = f"{self.public_origin}/#account-verify?{fragment}"
        subject = ("Riverview email verification" if purpose == "enrollment" else
                   "Riverview Steward email verification" if purpose == "steward_bootstrap" else
                   "Your Riverview request was approved — set your password" if purpose == "password_setup" else
                   "Reset your Riverview password" if purpose == "password_reset" else
                   "Riverview sign-in link")
        lead=("Your Riverview access request was approved. Set your password to sign in.\n\n"
              if purpose=="password_setup" else
              "This is the local bootstrap verification for the existing Riverview Steward identity.\n\n"
              if purpose=="steward_bootstrap" else "")
        self.send_message(email, subject=subject,
            body=lead + "Use this single-use link within 15 minutes:\n\n" + link +
                 "\n\nIf you did not request this, you can ignore this message.")


class FileDevelopmentEmailTransport:
    """Local-only test mailbox; writes token links to a private file, never logs.

    The directory must already exist, be owned by the current UID, and have no
    group/other permissions. Production deployments must use DisabledEmailTransport
    until an approved provider is commissioned.
    """

    is_available = True

    def __init__(self, path):
        from pathlib import Path
        import os
        import stat
        self._path = Path(path)
        info = self._path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise ValueError("development mailbox must be an owner-only regular file")

    def send_verification(self, email, *, purpose, challenge_id, token):
        import json
        import os
        import stat
        info = self._path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise EmailTransportUnavailable()
        payload = (json.dumps({"email": email, "purpose": purpose,
                               "challenge_id": challenge_id, "token": token},
                              separators=(",", ":")) + "\n").encode()
        descriptor = os.open(self._path, os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0))
        try:
            os.write(descriptor, payload)
        finally:
            os.close(descriptor)

    def send_message(self, email, *, subject, body):
        import json
        import os
        import stat
        info = self._path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise EmailTransportUnavailable()
        payload=(json.dumps({"email":email,"subject":subject,"body":body},
                            separators=(",",":"))+"\n").encode()
        descriptor=os.open(self._path,os.O_WRONLY|os.O_APPEND|getattr(os,"O_NOFOLLOW",0))
        try:
            os.write(descriptor,payload)
        finally:
            os.close(descriptor)
