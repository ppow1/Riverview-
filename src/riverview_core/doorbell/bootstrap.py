# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/doorbell/bootstrap.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.1
# Purpose: Create the user-owned exact-target config without credential material
# Inputs/Outputs: Exact target ID and executable / private config path or stable failure class
# Execution Model: Interactive commissioning CLI
# Observability: Prints only the config path or a stable failure class
# Dependencies: Python standard library; installed Chrome/Chromium
# Authority: Refuses to replace an existing binding unless --replace is explicit
# Changed: 2026-10-18 UTC | RV-C3-DOORBELL-DOD-001 | Complete controlled header and status/recovery contract
# Contracts: docs/components/CHATGPT_DOORBELL.md
# Tests: tests/test_chatgpt_doorbell.py
# History: Git and .riverview-revisions.json

"""Create the Riverview-owned Linux browser target configuration."""

from __future__ import annotations

import argparse

from .config import bootstrap_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure Riverview's fixed ChatGPT doorbell target.")
    parser.add_argument("--conversation-id", required=True)
    parser.add_argument("--browser-executable")
    parser.add_argument("--replace", action="store_true", help="replace an existing target after checking the active binding")
    args = parser.parse_args()
    try:
        print(bootstrap_config(args.conversation_id, args.browser_executable, replace=args.replace))
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
