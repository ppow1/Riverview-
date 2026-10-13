# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_status_dashboard.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.0
# Purpose: Deliver PostgreSQL credentials safely before starting the dashboard
# Execution Model: systemd service launcher for riverview-status-dashboard.service
# Observability: Sanitized configuration failure codes; no credential material
# Dependencies: Python 3.10+; runtime_baseline credential validation
# Authority: Copies only the exact systemd pgpass to the private dashboard runtime dir
# Changed: 2026-10-10 UTC | RV-M3.1-001 | Initial service credential launcher
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_status_dashboard.py
# History: Git and revision/backup manifest
# =============================================================================
"""Prepare a private libpq passfile using the shared runtime credential helper."""

from __future__ import annotations

import json
import os
import pwd
import sys
from pathlib import Path

from runtime_baseline import (BaselineError, copy_systemd_credential,
                              systemd_credential_path)

SERVICE_UNIT = "riverview-status-dashboard.service"
PASSFILE = Path("/run/riverview-status-dashboard/pgpass")


def prepare_runtime_credential() -> None:
    if any(os.environ.get(name) for name in
           ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
        raise BaselineError("AMBIENT_DATABASE_OVERRIDE", "credential")
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if not credential_dir:
        raise BaselineError("CREDENTIAL_MISSING", "credential")
    source = Path(credential_dir) / "pgpass"
    systemd_credential_path(source, service_unit=SERVICE_UNIT)
    identity = pwd.getpwnam("riverview")
    if identity.pw_uid == 0 or os.geteuid() != identity.pw_uid:
        raise BaselineError("IDENTITY_MISMATCH", "credential")
    copy_systemd_credential(source, PASSFILE, identity.pw_uid)
    os.environ["PGPASSFILE"] = str(PASSFILE)


def main() -> int:
    try:
        prepare_runtime_credential()
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
