#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/test_stackmail_mailbox.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.2.0
# Purpose: Privately test Stackmail SMTP authentication, self-delivery and inbox receipt
# Execution Model: Explicit one-shot interactive TTY test over local console or SSH; no application database or service use
# Observability: Sanitized outcome only; never logs credentials or server response text
# Dependencies: Python 3.10+; SMTP_SSL and IMAP4_SSL; Stackmail mailbox authorization
# Authority: Sends one explicit test message from and to the configured mailbox
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SSH-TTY | Allow hidden password entry through an allocated SSH TTY
# Contracts: docs/components/ACCOUNT_AUTHENTICATION_COOKBOOK.md
# Tests: py_compile; manual provider test requires Steward-entered local mailbox password
# History: Git and revision/backup manifest
# =============================================================================
"""Test the authorized mailbox without touching dashboard settings or PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid
import getpass
import imaplib
import os
import smtplib
import ssl
import sys
import time


SMTP_HOST = "smtp.stackmail.com"
SMTP_PORT = 465
IMAP_HOST = "imap.stackmail.com"
IMAP_PORT = 993


def _local_tty() -> bool:
    """Require an interactive Unix terminal; SSH is safe when it allocates a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty() and os.name == "posix"


def _receipt_seen(mailbox: str, password: str, message_id: str) -> bool:
    client = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ssl.create_default_context(), timeout=15)
    try:
        client.login(mailbox, password)
        status, _ = client.select("INBOX", readonly=True)
        if status != "OK":
            return False
        for _ in range(12):
            status, data = client.search(None, "HEADER", "Message-ID", message_id)
            if status == "OK" and data and data[0].strip():
                return True
            time.sleep(5)
        return False
    finally:
        try:
            client.logout()
        except Exception:
            pass


def main() -> int:
    if not _local_tty():
        print("Run this test in an interactive terminal (for SSH, allocate a TTY with ssh -tt).", file=sys.stderr)
        return 2
    if input("Type SEND ONE STACKMAIL TEST EMAIL to continue: ") != "SEND ONE STACKMAIL TEST EMAIL":
        print("No test email sent.")
        return 2

    mailbox = input("Authorized Stackmail mailbox address: ").strip()
    if (not mailbox or len(mailbox) > 254 or "\r" in mailbox or "\n" in mailbox
            or mailbox.count("@") != 1 or " " in mailbox):
        print("Mailbox address is invalid; no test email sent.")
        return 2
    password = getpass.getpass(f"Password for {mailbox} (input hidden): ")
    if not password:
        print("No password entered; no test email sent.")
        return 2

    message_id = make_msgid(domain="cuemastery.com")
    message = EmailMessage()
    message["From"] = mailbox
    message["To"] = mailbox
    message["Subject"] = "Riverview Stackmail SMTP verification " + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    message["Message-ID"] = message_id
    message.set_content("This one-time message verifies Riverview's proposed Stackmail transport. It contains no credentials.")

    smtp_authenticated = False
    relay_accepted = False
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20,
                              context=ssl.create_default_context()) as smtp:
            smtp.login(mailbox, password)
            smtp_authenticated = True
            refused = smtp.send_message(message)
            relay_accepted = not refused
    except smtplib.SMTPAuthenticationError as exc:
        print(f"SMTP authentication: FAILED (server reply {exc.smtp_code}).")
        password = ""
        return 1
    except Exception as exc:
        print(f"SMTP connection/authentication/submission: FAILED ({type(exc).__name__}).")
        password = ""
        return 1

    password = ""
    print("SMTP authentication: PASS.")
    if not relay_accepted:
        print("SMTP relay did not accept the message for the mailbox.")
        return 1
    print("SMTP relay accepted one test message to the same mailbox.")

    try:
        received = _receipt_seen(mailbox, getpass.getpass(
            "Re-enter mailbox password to check INBOX over read-only IMAP (input hidden): "), message_id)
    except Exception as exc:
        print(f"Inbox receipt: NOT VERIFIED ({type(exc).__name__}); check the mailbox manually.")
        return 2
    if received:
        print("Inbox receipt: PASS (unique test Message-ID found in read-only INBOX search).")
        return 0
    print("Inbox receipt: NOT VERIFIED within 60 seconds; check Inbox and Junk manually.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
