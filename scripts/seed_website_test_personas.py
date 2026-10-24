#!/usr/bin/env python3
"""Create reserved Riverview browser-test identities using account-auth's real roles.

Root-only and idempotent. Credentials are generated once into a protected file;
existing accounts are never reset. Test Steward is deliberately not linked to an
institutional principal and therefore cannot operate Grace or engineering authority.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import tempfile

import psycopg

EMAILS = {
    "steward": "codex-test-steward@riverview.invalid",
    "operator": "codex-test-operator@riverview.invalid",
    "engineering": "codex-test-engineering@riverview.invalid",
    "viewer": "codex-test-viewer@riverview.invalid",
}
ROLES = {"steward": "steward", "operator": "operator",
         "engineering": "operator", "viewer": "viewer"}


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    b64 = lambda data: base64.urlsafe_b64encode(data).decode().rstrip("=")
    return f"scrypt$16384$8$1${b64(salt)}${b64(derived)}"


def write_credentials(path: Path) -> dict[str, str]:
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise RuntimeError("credential_file_must_be_regular_mode_0600")
        data = json.loads(path.read_text())
        if set(data) != set(EMAILS) or any(not isinstance(v, str) or len(v) < 32 for v in data.values()):
            raise RuntimeError("credential_file_invalid")
        return data
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    data = {name: secrets.token_urlsafe(36) for name in EMAILS}
    fd, temp_name = tempfile.mkstemp(prefix=".personas-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, path)
    finally:
        try: os.unlink(temp_name)
        except FileNotFoundError: pass
    return data


def apply(dsn: str, path: Path) -> dict[str, str]:
    credentials = write_credentials(path)
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        for persona, email in EMAILS.items():
            cur.execute("""SELECT a.account_id,
                EXISTS (SELECT 1 FROM riverview_accounts.account_audit x
                        WHERE x.account_id=a.account_id
                          AND x.event_type='website_test_persona_seeded')
                FROM riverview_accounts.accounts a WHERE a.email=%s FOR UPDATE""", (email,))
            row = cur.fetchone()
            if row:
                if not row[1]:
                    raise RuntimeError("reserved_test_email_already_owned")
                cur.execute("""SELECT role FROM riverview_accounts.account_roles
                               WHERE account_id=%s""", (row[0],))
                roles = {r[0] for r in cur.fetchall()}
                if ROLES[persona] not in roles:
                    raise RuntimeError("seeded_persona_role_mismatch")
                continue
            cur.execute("""INSERT INTO riverview_accounts.accounts
                (email,email_verified_at,created_at,password_hash,grant_type)
                VALUES (%s,clock_timestamp(),clock_timestamp(),%s,'permanent')
                RETURNING account_id""", (email, password_hash(credentials[persona])))
            account_id = cur.fetchone()[0]
            cur.execute("INSERT INTO riverview_accounts.account_roles(account_id,role) VALUES (%s,%s)",
                        (account_id, ROLES[persona]))
            cur.execute("""INSERT INTO riverview_accounts.account_audit
                (event_type,account_id,subject_email) VALUES ('website_test_persona_seeded',%s,%s)""",
                        (account_id, email))
    return {name: ROLES[name] for name in EMAILS}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.environ.get("RIVERVIEW_DATABASE_DSN"))
    parser.add_argument("--credentials", type=Path,
                        default=Path("/etc/riverview/website-acceptance/personas.json"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("must_run_as_root")
    if not args.dsn:
        parser.error("database_dsn_required")
    if not args.apply:
        print(json.dumps({"status":"DRY_RUN", "personas":ROLES,
                          "credentials_file":str(args.credentials)}))
        return 0
    result = apply(args.dsn, args.credentials)
    print(json.dumps({"status":"PASS", "personas":result,
                      "credentials_file":str(args.credentials),
                      "steward_authority_linked":False}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {str(exc)[:120]}", file=sys.stderr)
        raise SystemExit(1)
