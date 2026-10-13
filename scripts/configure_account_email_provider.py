#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/configure_account_email_provider.py
# Component: SHARED-EMAIL-DELIVERY
# Revision: 1.0.0
# Purpose: Securely provision initial SMTP settings before the first Steward portal account exists
# Execution Model: Root-only local-console CLI; no SSH and no pseudo-terminal
# Observability: Sanitized result only; never prints credentials or message bodies
# Dependencies: PostgreSQL account schema migration 0002; cryptography; private pgpass
# Authority: Exact typed console confirmation; writes only account email configuration and local key
# Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Add first-provider bootstrap commissioning helper
# Contracts: docs/components/ACCOUNT_AUTHENTICATION_COOKBOOK.md
# Tests: tests/test_email_delivery.py
# History: Git and revision/backup manifest
# =============================================================================
"""Provision the encrypted email provider before Steward account sign-in exists."""

from __future__ import annotations

import getpass
import os
from pathlib import Path
import re
import stat
import sys

from cryptography.fernet import Fernet

from riverview_core.email_delivery import ConfiguredEmailTransport, read_key
from riverview_core.account_auth import normalize_email

DSN="host=127.0.0.1 port=5432 dbname=riverview user=riverview_core application_name=riverview-email-provider-bootstrap"
KEY_PATH=Path("/etc/riverview/account-email-config.key")


def _local_console():
    try:
        tty=os.ttyname(sys.stdin.fileno())
    except OSError:
        return False
    return (os.geteuid()==0 and sys.stdin.isatty() and
            (tty=="/dev/console" or re.fullmatch(r"/dev/tty[0-9]+",tty)) and
            not os.environ.get("SSH_CONNECTION"))


def _key():
    KEY_PATH.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if KEY_PATH.exists() or KEY_PATH.is_symlink():
        info=KEY_PATH.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077:
            raise RuntimeError("email encryption key file is not a protected root-owned regular file")
        return read_key(KEY_PATH)
    raw=Fernet.generate_key()
    descriptor=os.open(KEY_PATH,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        os.write(descriptor,raw+b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chown(KEY_PATH,0,0)
    return raw


def main():
    if not _local_console():
        print("Email provider bootstrap requires the root-owned Camrui local console.",file=sys.stderr)
        return 2
    if input("Type CONFIGURE RIVERVIEW EMAIL to continue: ")!="CONFIGURE RIVERVIEW EMAIL":
        print("Email provider configuration was not authorized.",file=sys.stderr)
        return 2
    try:
        key=_key()
        host=input("SMTP host: ").strip()
        port_text=input("SMTP port (587 STARTTLS or 465 implicit TLS): ").strip()
        tls_mode=input("TLS mode (starttls or implicit): ").strip()
        sender=normalize_email(input("Sender email address: "))
        sender_name=input("Sender display name: ").strip()
        admin=normalize_email(input("Administrator notification email address: "))
        reply_to=input("Reply-to email address (optional): ").strip()
        reply_to=normalize_email(reply_to) if reply_to else ""
        username=input("SMTP mailbox username: ").strip()
        password=getpass.getpass("SMTP mailbox password: ")
        port=int(port_text)
        if (not re.fullmatch(r"[A-Za-z0-9.-]{1,253}",host) or not 1<=port<=65535
                or tls_mode not in {"starttls","implicit"} or not sender_name
                or len(sender_name)>120 or not username or len(username)>254
                or not password or len(password)>4096 or "\r" in password or "\n" in password):
            raise ValueError("smtp_configuration_invalid")
        encrypted=ConfiguredEmailTransport.encrypt_password(password,key)
        os.environ.setdefault("PGPASSFILE","/etc/riverview/pgpass")
        import psycopg
        with psycopg.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute("SELECT version FROM riverview_accounts.schema_migrations "
                        "WHERE version='0002_password_grants_and_email_provider'")
            if not cur.fetchone():
                raise RuntimeError("account email provider migration 0002 is not applied")
            cur.execute("INSERT INTO riverview_accounts.email_provider_config "
                "(singleton,smtp_host,smtp_port,tls_mode,sender_email,sender_name,admin_email,"
                "reply_to_email,smtp_username,password_ciphertext,updated_at) "
                "VALUES (TRUE,%s,%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp()) "
                "ON CONFLICT (singleton) DO UPDATE SET smtp_host=EXCLUDED.smtp_host,"
                "smtp_port=EXCLUDED.smtp_port,tls_mode=EXCLUDED.tls_mode,sender_email=EXCLUDED.sender_email,"
                "sender_name=EXCLUDED.sender_name,admin_email=EXCLUDED.admin_email,"
                "reply_to_email=EXCLUDED.reply_to_email,smtp_username=EXCLUDED.smtp_username,"
                "password_ciphertext=EXCLUDED.password_ciphertext,updated_at=clock_timestamp(),"
                "last_test_at=NULL,last_test_status=NULL,last_test_error=NULL",
                (host,port,tls_mode,sender,sender_name,admin,reply_to,username,encrypted))
        print("Email settings saved with an encrypted password. No test message was sent.")
        print("Install the documented systemd LoadCredential for account-email-config-key, then test delivery in the Steward interface.")
        return 0
    except Exception as exc:
        code=getattr(exc,"code",None)
        print("Email provider configuration failed"+(f" ({code})" if code else
              f" ({type(exc).__name__})")+".",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
