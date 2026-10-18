#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/report_external_review.py
# Component: EXTERNAL-REVIEW-OBSERVABILITY
# Revision: 1.0.0
# Purpose: Render a bounded redacted report from an operator metadata snapshot
# Execution Model: One-shot local read-only CLI
# Observability: JSON output contains stage state and sanitized lineage only
# Dependencies: Python standard library and repository source package
# Authority: No database, network, browser, mailbox, or mutation access
# Changed: 2026-10-18 UTC | RV-EXTERNAL-REVIEW-TRACE-001 | Initial operator CLI
# Tests: tests/test_external_review_trace.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Render an external-review lineage report from a metadata-only JSON snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from riverview_core.resident_execution.external_review_trace import (
    MAX_INPUT_BYTES, TraceInputError, parse_bundle,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="metadata-only JSON snapshot from an authorized read-only source")
    args = parser.parse_args(argv)
    try:
        with args.snapshot.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        report = parse_bundle(raw)
    except TraceInputError as exc:
        print(json.dumps({"schema_version": "rv.external-review-trace-report.v1",
                          "outcome": "invalid_input", "error": str(exc)}, sort_keys=True))
        return 2
    except OSError:
        print(json.dumps({"schema_version": "rv.external-review-trace-report.v1",
                          "outcome": "input_unavailable", "error": "snapshot_unavailable"}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["outcome"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
