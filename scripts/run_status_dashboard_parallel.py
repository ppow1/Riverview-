# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_status_dashboard_parallel.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.0
# Purpose: Start a separately credentialed parallel Dashboard candidate
# Execution Model: Dedicated systemd service launcher
# Observability: Sanitized startup errors; no credential material
# Dependencies: Python 3.10+; systemd credentials; runtime_baseline validation
# Authority: Uses only the existing protected Dashboard and Command Gateway credentials
# Changed: 2026-10-27 UTC | RV-ISSUE-359-PARALLEL-DASHBOARD | Isolate the parallel service unit's credential mount and private passfile.
# Contracts: docs/operations/ISSUE_359_PARALLEL_DASHBOARD_RUNBOOK.md
# Tests: tests/test_parallel_dashboard_service.py
# History: Git and revision backup manifest
# =============================================================================
"""Prepare the parallel Dashboard's private libpq passfile, then run Dashboard."""

from __future__ import annotations

import json
import sys

from runtime_baseline import BaselineError
from run_status_dashboard import prepare_runtime_credential


SERVICE_UNIT = "riverview-status-dashboard-parallel.service"
PASSFILE = "/run/riverview-status-dashboard-parallel/pgpass"


def main() -> int:
    try:
        from pathlib import Path
        prepare_runtime_credential(service_unit=SERVICE_UNIT, passfile=Path(PASSFILE))
        from riverview_core.status_dashboard.server import main as dashboard_main
        dashboard_main()
        return 0
    except BaselineError as exc:
        print(json.dumps({"event": "dashboard_configuration_failed",
                          "blocker_code": exc.code, "step_id": exc.step}),
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
