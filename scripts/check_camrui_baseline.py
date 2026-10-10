# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/check_camrui_baseline.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: Consolidated read-only SSH commissioning check
# Execution Model: Request-driven diagnostic, repeatable
# Observability: systemd unit result and sanitized probe JSON over authenticated SSH
# Dependencies: Python 3, OpenSSH, commissioned remote deployment
# Authority: Read-only sudo report consumer; no deployment, host-key acceptance or secret transport
# Changed: 2026-10-10 UTC | RV-M1.1-001 | Initial implementation
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py
# History: New file; no predecessor; Git
import argparse
import re
import subprocess
import sys

REMOTE_CHECK = "systemctl show riverview-baseline.service --property=User,Group,LoadState,Result,ExecMainStatus && sudo -n /usr/bin/python3 /opt/riverview-core/scripts/read_baseline_report.py"


def command(destination):
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@-]*", destination):
        raise ValueError("Use a provisioned SSH alias or user@hostname")
    return ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o",
            "ConnectTimeout=10", "-o", "ServerAliveInterval=5", "-o",
            "ServerAliveCountMax=2", destination, REMOTE_CHECK]


def main():
    parser = argparse.ArgumentParser(description="Read Camrui baseline evidence without commissioning")
    parser.add_argument("destination")
    args = parser.parse_args()
    try:
        completed = subprocess.run(command(args.destination), timeout=30)
        return completed.returncode
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(type(exc).__name__ + ": SSH validation could not complete", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
