# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/bootstrap_authority_steward.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Safely bootstrap the first Steward identity with write-ahead token persistence
# Execution Model: Root-only local operation using the protected authority manager passfile
# Observability: Redacted JSON status; never prints or logs the bearer token
# Dependencies: Python 3.10+; Psycopg 3; root-owned Riverview source
# Authority: Fixed database, schema, manager role and token path; no user-selected SQL or paths
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: tests/test_institutional_authority.py
# History: Git and .riverview-backups/manifest.jsonl
"""Create the initial Steward token durably before committing its database digest."""

from __future__ import annotations

import json
import os
import secrets
import stat
import sys
from pathlib import Path

from riverview_core.institutional_authority import (
    AuthorityDenied,
    AuthorityRegistry,
    IdentityConflict,
    RegistryUnavailable,
)


TOKEN_FILE = Path("/etc/riverview/authority/steward.token")
MANAGER_PASSFILE = "/etc/riverview/authority/manager.pgpass"
MANAGER_DSN = "host=127.0.0.1 port=5432 dbname=riverview user=riverview_authority_manager"
SCHEMA = "riverview_authority"
PRINCIPAL_ID = "steward:camrui"


def _write_token_before_bootstrap(token: str) -> None:
    """Create an exclusive root-only token file and sync it before database use."""
    parent = TOKEN_FILE.parent
    parent_stat = parent.stat(follow_symlinks=False)
    if parent.is_symlink() or parent_stat.st_uid != 0 or stat.S_IMODE(parent_stat.st_mode) != 0o700:
        raise PermissionError("authority secret directory ownership or mode is unsafe")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(TOKEN_FILE, flags, 0o600)
    try:
        file_stat = os.fstat(fd)
        if file_stat.st_uid != 0 or stat.S_IMODE(file_stat.st_mode) != 0o600:
            raise PermissionError("new Steward token file ownership or mode is unsafe")
        payload = token.encode("ascii") + b"\n"
        offset = 0
        while offset < len(payload):
            offset += os.write(fd, payload[offset:])
        os.fsync(fd)
    except Exception:
        os.close(fd)
        TOKEN_FILE.unlink(missing_ok=True)
        raise
    else:
        os.close(fd)
    directory_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _load_existing_token() -> str:
    if TOKEN_FILE.is_symlink():
        raise PermissionError("Steward token path must not be a symbolic link")
    info = TOKEN_FILE.stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
        raise PermissionError("existing Steward token file ownership or mode is unsafe")
    token = TOKEN_FILE.read_text(encoding="ascii").strip()
    if len(token) < 32:
        raise ValueError("existing Steward token file is incomplete")
    return token


def main() -> int:
    if os.geteuid() != 0:
        print(json.dumps({"status": "ERROR", "detail": "root-local operation required"}))
        return 2
    if len(sys.argv) != 1:
        print(json.dumps({"status": "ERROR", "detail": "no arguments are accepted"}))
        return 2
    os.environ["PGPASSFILE"] = MANAGER_PASSFILE
    created_file = False
    try:
        if TOKEN_FILE.exists() or TOKEN_FILE.is_symlink():
            token = _load_existing_token()
        else:
            token = secrets.token_urlsafe(32)
            _write_token_before_bootstrap(token)
            created_file = True
        registry = AuthorityRegistry(MANAGER_DSN, schema=SCHEMA)
        try:
            try:
                registry.bootstrap_steward(PRINCIPAL_ID, token=token)
                status = "BOOTSTRAPPED"
            except IdentityConflict:
                registry.authorize(token, "identity.manage", "institution")
                status = "ALREADY_BOOTSTRAPPED"
        finally:
            registry.close()
        info = TOKEN_FILE.stat(follow_symlinks=False)
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            raise PermissionError("Steward token file changed ownership or mode")
        print(json.dumps({"status": status, "principal_id": PRINCIPAL_ID,
                          "token_file": str(TOKEN_FILE), "token_file_mode": "0600"}, sort_keys=True))
        return 0
    except (AuthorityDenied, RegistryUnavailable, IdentityConflict, OSError, ValueError) as exc:
        # The token file is retained after an ambiguous database result so a
        # retry can use the same pre-persisted token without exposing it.
        print(json.dumps({"status": "ERROR", "failure_type": type(exc).__name__,
                          "token_file_retained": TOKEN_FILE.exists(),
                          "new_file_created": created_file}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
