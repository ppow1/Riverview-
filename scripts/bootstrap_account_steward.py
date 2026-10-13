#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/bootstrap_account_steward.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.2.0
# Purpose: Explicitly authorize and email-verify the first account linked to steward:camrui
# Execution Model: Interactive one-time commissioning command on local console or allocated SSH TTY
# Observability: Sanitized account audit rows; fixed status output
# Dependencies: PostgreSQL; protected /etc/riverview/pgpass; approved email transport
# Authority: Root local TTY, no SSH session, exact typed confirmation, active Steward principal
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Initial guarded Steward bootstrap procedure
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Require a physical/serial console TTY rather than a pseudo-terminal
# Changed: 2026-10-12 UTC | RV-ACCOUNT-AUTH-001 | Align local bootstrap authority boundary with account audit changes
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Use encrypted configurable email provider and password setup link
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SSH-COMMISSION | Permit root interactive SSH TTY and fail closed on getpass echo fallback
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: tests/test_account_auth.py
# History: Git and revision/backup manifest
# =============================================================================
"""Securely authorize the one-time Steward account bootstrap on Camrui."""

from __future__ import annotations

import getpass
import os
import sys
import re
import warnings
from pathlib import Path

from riverview_core.account_auth import (
    AccountAuthService,
    DisabledEmailTransport,
    FileDevelopmentEmailTransport,
)
from riverview_core.email_delivery import ConfiguredEmailTransport

DSN = "host=127.0.0.1 port=5432 dbname=riverview user=riverview_core application_name=riverview-account-bootstrap"
PRINCIPAL_ID = "steward:camrui"


def _interactive_root_tty():
    if os.name != "posix" or os.geteuid() != 0 or not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    try:
        terminal = os.ttyname(sys.stdin.fileno())
    except OSError:
        return False
    return bool(terminal == "/dev/console"
                or re.fullmatch(r"/dev/tty[0-9]+", terminal)
                or re.fullmatch(r"/dev/pts/[0-9]+", terminal))


def _hidden_input(prompt):
    """Fail closed instead of allowing getpass to fall back to echoed input."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


def _email_transport(connection_factory):
    mailbox = os.environ.get("RIVERVIEW_EMAIL_DEVELOPMENT_MAILBOX")
    if mailbox:
        return FileDevelopmentEmailTransport(mailbox)
    credential_directory = os.environ.get("CREDENTIALS_DIRECTORY", "")
    key_path=(Path(credential_directory)/"account-email-config-key" if credential_directory
              else Path("/etc/riverview/account-email-config.key"))
    if key_path.is_file():
        return ConfiguredEmailTransport(connection_factory,schema="riverview_accounts",
            key_path=key_path,
            public_origin=os.environ.get("RIVERVIEW_PUBLIC_ORIGIN","https://192.168.1.155"))
    return DisabledEmailTransport()


def main():
    if not _interactive_root_tty():
        print("Bootstrap requires root and an interactive TTY (use ssh -tt for SSH).", file=sys.stderr)
        return 2
    try:
        email = _hidden_input("Steward email address (input hidden): ")
    except getpass.GetPassWarning:
        print("Bootstrap needs a TTY that supports hidden input; no request was created.", file=sys.stderr)
        return 2
    confirmation = input("Type BOOTSTRAP steward:camrui to authorize this email: ")
    if confirmation != "BOOTSTRAP steward:camrui":
        print("Bootstrap was not authorized.", file=sys.stderr)
        return 2

    os.environ.setdefault("PGPASSFILE", "/etc/riverview/pgpass")
    import psycopg

    try:
        with psycopg.connect(DSN, connect_timeout=3) as conn, conn.cursor() as cur:
            cur.execute("SELECT status FROM riverview_authority.institutional_principals "
                        "WHERE principal_id=%s AND principal_kind='steward'", (PRINCIPAL_ID,))
            row = cur.fetchone()
            if not row or row[0] != "active":
                print("The existing Steward principal is not active; bootstrap stopped.", file=sys.stderr)
                return 3
            cur.execute("SELECT 1 FROM riverview_accounts.schema_migrations "
                        "WHERE version='0002_password_grants_and_email_provider'")
            if not cur.fetchone():
                print("The dedicated account schema migration is not applied; bootstrap stopped.", file=sys.stderr)
                return 3
        connect=lambda:psycopg.connect(DSN,connect_timeout=3)
        service = AccountAuthService(connect,
            _email_transport(connect), schema="riverview_accounts",
            public_origin=os.environ.get("RIVERVIEW_PUBLIC_ORIGIN","https://192.168.1.155"))
        service.request_steward_bootstrap(email, local_authorized=True,
                                          authority_principal_id=PRINCIPAL_ID)
    except Exception as exc:
        from riverview_core.account_auth import AccountAuthError
        if isinstance(exc, AccountAuthError):
            print(f"Bootstrap could not continue: {exc.code}.", file=sys.stderr)
        else:
            print(f"Bootstrap could not continue ({type(exc).__name__}).", file=sys.stderr)
        return 1
    print("A single-use email verification challenge was issued if delivery succeeded. "
          "The account receives Steward role only after verifying that email.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
