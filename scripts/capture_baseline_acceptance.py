# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/capture_baseline_acceptance.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: Preserve actual Camrui commissioning outcomes including failures
# Execution Model: Request-driven acceptance runner; never accepts for the Steward
# Observability: Exclusive mode-0600 JSON artifact with commands, exits and DoD gaps
# Dependencies: Python 3, root, commissioned systemd unit
# Authority: Starts only the read-only baseline diagnostic twice; no DB mutations
# Changed: 2026-10-10 UTC | RV-M1.1-001 | Initial implementation
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py
# History: New file; no predecessor; Git
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

from read_baseline_report import read_report


def capture(run=subprocess.run, read=read_report, source_commit=None):
    report = dict(projection_version="rv.baseline-acceptance.v1", task_id="RV-M1.1-001",
                  component_id="RUNTIME-BASELINE", observed_at=datetime.now(timezone.utc).isoformat(),
                  target_host=os.uname().nodename, commands=[], observations=[],
                  steward_acceptance="pending", milestone="M1.1", full_component_dod="NOT_DONE",
                  dependencies={"persistent_processor": "M1.3", "CME": "M2.4", "live_dashboard": "M3.1"})
    commit_file = Path(__file__).resolve().parents[1] / "SOURCE_COMMIT"
    report["source_commit"] = source_commit or (commit_file.read_text().strip() if commit_file.exists() else None)
    success = True
    for _ in range(2):
        argv = ["systemctl", "start", "riverview-baseline.service"]
        try:
            process = run(argv, capture_output=True, text=True, timeout=30)
            record = dict(command=argv, exit_code=process.returncode,
                          stdout=process.stdout, stderr=process.stderr)
        except (OSError, subprocess.TimeoutExpired):
            record = dict(command=argv, exit_code=None, error_code="SERVICE_CHECK_UNAVAILABLE")
        report["commands"].append(record)
        snapshot, code = read(Path("/var/lib/riverview/baseline.json"))
        report["observations"].append(dict(exit_code=code, snapshot=snapshot))
        success = (success and record["exit_code"] == 0 and code == 0
                   and report["source_commit"] is not None
                   and snapshot.get("source_commit") == report["source_commit"])
    # Two identical old snapshots do not prove that the second invocation ran.
    times = [item["snapshot"].get("observed_at") for item in report["observations"]]
    success = success and all(times) and times[0] != times[1]
    report["commissioning_checks"] = "PASS" if success else "FAIL"
    report["step_acceptance"] = "PENDING_STEWARD" if success else "BLOCKED"
    return report, 0 if success else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Run with authorized sudo on Camrui")
    report, code = capture()
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print("Acceptance evidence saved; " + report["step_acceptance"])
    raise SystemExit(code)
