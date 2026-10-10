# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/provision_pgpass.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: One-time protected capture of the EXISTING database password
# Execution Model: Interactive commissioning only; never normal runtime restart
# Observability: Exit status; no secret output
# Dependencies: Python 3, root-owned /etc/riverview
# Authority: Creates absent credential only; never changes database passwords
# Changed: 2026-10-10 UTC | RV-M1.1-001 | Initial implementation
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py
# History: New file; no predecessor; Git
import getpass
import os
from pathlib import Path
import stat
import warnings


def pgpass_line(password):
    if not password or any(c in password for c in "\r\n\x00"):
        raise ValueError("A nonempty single-line password is required")
    escaped = password.replace("\\", "\\\\").replace(":", "\\:")
    return "127.0.0.1:5432:riverview:riverview_core:" + escaped + "\n"


def main():
    target = Path("/etc/riverview/pgpass")
    parent = target.parent
    info = parent.lstat()
    if os.geteuid() != 0 or parent.resolve() != parent or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise SystemExit("Require root and a root-owned mode-0700 /etc/riverview")
    # Explicit terminal required: do not allow getpass fallback to echoed stdin.
    warnings.simplefilter("error", getpass.GetPassWarning)
    with open("/dev/tty", "r+") as terminal:
        password = getpass.getpass("Existing riverview_core database password (not echoed): ", stream=terminal)
    line = pgpass_line(password)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
