#!/usr/bin/env python3
# =============================================================================
# Riverview~ Controlled Source
# File: scripts/setup_v2_workspace_preview_auth.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.0
# Purpose: Create the local password hash for the LAN-only V2 preview
# Execution Model: One-shot interactive local setup
# Observability: Reports protected file path and setup outcome; never prints password
# Dependencies: Python 3.10+ standard library; serve_v2_workspace_preview password hashing
# Inputs/Outputs: Hidden password prompt; owner-only salted hash JSON file
# Authority: Local preview credential setup only; does not start a service or open a port
# Changed: 2026-10-20 UTC | RV-WEB-V2-LAN-PREVIEW-001 | Initial protected local password setup
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: tests/test_v2_workspace_shell.py
# History: Git and revision/backup manifest
# =============================================================================
"""Prompt locally for a preview password and save only its salted PBKDF2 hash."""
from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
import stat
from pathlib import Path

try:
    from .serve_v2_workspace_preview import create_password_record
except ImportError:
    from serve_v2_workspace_preview import create_password_record


def write_password_file(path: str | Path, password: str, *, replace: bool = False) -> Path:
    path = Path(path).expanduser()
    if path.exists() and not replace:
        raise FileExistsError("password hash file already exists; use --replace to choose a new password")
    if path.is_symlink():
        raise RuntimeError("password hash file must not be a symbolic link")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.stat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.geteuid() or parent.st_mode & 0o077:
        raise RuntimeError("password hash directory must be owner-owned and mode 0700")
    if path.exists():
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
            raise RuntimeError("existing password hash file must be owner-owned and private")
    record = create_password_record(password)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists() and not replace:
            raise FileExistsError("password hash file already exists")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=str(Path.home() / ".config/riverview/v2-preview-auth.json"))
    parser.add_argument("--replace", action="store_true", help="replace an existing protected hash file")
    args = parser.parse_args()
    try:
        password = getpass.getpass("Choose a simple V2 preview password (12-256 characters): ")
        confirmation = getpass.getpass("Confirm V2 preview password: ")
        if not secrets.compare_digest(password, confirmation):
            parser.error("password entries did not match")
        saved = write_password_file(args.path, password, replace=args.replace)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Password hash saved with owner-only permissions: {saved}")
    print("The password itself was not saved. Restart the preview with this file to enable LAN access.")


if __name__ == "__main__":
    main()
