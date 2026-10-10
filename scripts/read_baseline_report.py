# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/read_baseline_report.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: Independent freshness-aware consumer of commissioning evidence
# Execution Model: Request-driven diagnostic
# Observability: Sanitized rv.runtime-baseline.v1 JSON, nonzero on stale or blocked
# Dependencies: Python 3.10+
# Authority: Read-only; never supplies control authority or reads credentials
# Changed: 2026-10-10 UTC | RV-M1.1-001 | Initial implementation
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py
# History: New file; no predecessor; Git
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def read_report(path, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        report = json.loads(path.read_text())
        if not isinstance(report, dict) or report.get("projection_version") != "rv.runtime-baseline.v1":
            raise ValueError("schema")
        observed = datetime.fromisoformat(report["observed_at"])
        expires = datetime.fromisoformat(report["expires_at"])
        if observed.tzinfo is None or expires.tzinfo is None or expires <= observed:
            raise ValueError("timestamps")
        if (expires - observed).total_seconds() > 60 or observed > now:
            raise ValueError("freshness")
        if now >= expires:
            report.update(freshness="stale", status="stale", baseline_ready=False)
            return report, 3
        if report.get("baseline_ready") is True and report.get("status") == "baseline_ready":
            return report, 0
        return report, 1
    except (OSError, ValueError, KeyError, TypeError):
        return {"projection_version": "rv.runtime-baseline.v1", "component_id": "RUNTIME-BASELINE",
                "freshness": "unavailable", "status": "unavailable", "baseline_ready": False,
                "blocker_code": "REPORT_UNAVAILABLE"}, 2


if __name__ == "__main__":
    report, code = read_report(Path("/var/lib/riverview/baseline.json"))
    print(json.dumps(report, sort_keys=True, indent=2))
    sys.exit(code)
