# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/email_delivery.py
# Component: SHARED-EMAIL-DELIVERY
# Revision: 1.1.0
# Purpose: Reusable SMTP delivery backed by encrypted PostgreSQL settings and a systemd key credential
# Execution Model: Request-driven SMTP submission; no autonomous sending loop
# Observability: Stable outcomes without credential or message logging
# Dependencies: Python standard library; cryptography; PostgreSQL DB-API; TLS SMTP relay
# Authority: Explicit caller supplies each recipient and message
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Add reusable configured SMTP sender
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: tests/test_account_auth.py; tests.test_account_auth.AccountAuthPostgresTests.test_email_settings_encrypt_secret_redact_readback_and_record_test
# History: Git and revision/backup manifest
# =============================================================================
"""Reusable SMTP transport with encrypted credentials and explicit delivery calls."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .account_auth import EmailTransportUnavailable, SMTPEmailTransport


def read_key(path: str | Path) -> bytes:
    """Read an owner-only Fernet key, refusing symlinks and permissive files."""
    key_path = Path(path)
    descriptor = os.open(key_path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                         | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise EmailTransportUnavailable()
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(256).strip()
    finally:
        os.close(descriptor)
    try:
        Fernet(raw)
    except (ValueError, TypeError):
        raise EmailTransportUnavailable() from None
    return raw


class ConfiguredEmailTransport:
    """Load encrypted SMTP settings from the account schema for each explicit send."""

    def __init__(self, connection_factory, *, schema, key_path, public_origin):
        self._connect = connection_factory
        self._schema = schema
        self._key_path = Path(key_path)
        self._public_origin = public_origin

    @property
    def is_available(self):
        try:
            read_key(self._key_path)
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(f'SELECT 1 FROM "{self._schema}"."email_provider_config" '
                            "WHERE singleton=TRUE")
                return cur.fetchone() is not None
        except Exception:
            return False

    @staticmethod
    def encrypt_password(password: str, key: bytes) -> bytes:
        if not isinstance(password, str) or not password or len(password) > 4096:
            raise ValueError("smtp_password_invalid")
        if "\r" in password or "\n" in password:
            raise ValueError("smtp_password_invalid")
        return Fernet(key).encrypt(password.encode("utf-8"))

    def _transport(self):
        key = read_key(self._key_path)
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    f'SELECT smtp_host,smtp_port,tls_mode,sender_email,sender_name,'
                    f'admin_email,reply_to_email,smtp_username,password_ciphertext '
                    f'FROM "{self._schema}"."email_provider_config" WHERE singleton=TRUE')
                row = cur.fetchone()
            if not row:
                raise EmailTransportUnavailable()
            (host, port, tls_mode, sender, sender_name, _admin, reply_to,
             username, ciphertext) = row
            password = Fernet(key).decrypt(bytes(ciphertext)).decode("utf-8")
        except (EmailTransportUnavailable, InvalidToken):
            raise EmailTransportUnavailable() from None
        except Exception:
            raise EmailTransportUnavailable() from None
        transport = object.__new__(SMTPEmailTransport)
        transport.host, transport.port, transport.sender = host, int(port), sender
        transport.sender_name, transport.reply_to = sender_name, reply_to or None
        transport.public_origin = self._public_origin.rstrip("/")
        transport.tls_mode, transport.username, transport.timeout = tls_mode, username, 10
        transport.password_file = None
        return transport, password

    def send_message(self, recipient, *, subject, body):
        transport, password = self._transport()
        transport.send_message(recipient, subject=subject, body=body,
                               password_override=password)

    def send_verification(self, email, *, purpose, challenge_id, token):
        transport, password = self._transport()
        from urllib.parse import urlencode
        if purpose not in {"login", "enrollment", "steward_bootstrap", "password_setup", "password_reset"}:
            raise EmailTransportUnavailable()
        link = f"{self._public_origin.rstrip('/')}/#account-verify?" + urlencode(
            {"purpose":purpose,"challenge_id":challenge_id,"token":token})
        subject = ("Riverview email verification" if purpose == "enrollment" else
                   "Riverview Steward email verification" if purpose == "steward_bootstrap" else
                   "Your Riverview request was approved — set your password" if purpose == "password_setup" else
                   "Reset your Riverview password" if purpose == "password_reset" else
                   "Riverview sign-in link")
        lead=("Your Riverview access request was approved. Set your password to sign in.\n\n"
              if purpose=="password_setup" else
              "This is the local bootstrap verification for the existing Riverview Steward identity.\n\n"
              if purpose=="steward_bootstrap" else "")
        transport.send_message(email, subject=subject,
            body=lead+"Use this single-use link within 15 minutes:\n\n" + link +
                 "\n\nIf you did not request this, you can ignore this message.",
            password_override=password)
