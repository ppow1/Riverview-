# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/register_work.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Provide a common Python CLI for worker/session/work-order observations.
# Purpose: Register observational records through the versioned file registry
# Execution Model: Request-driven command line
# Observability: Safe JSON receipts; no prompt or credential fields accepted
# Dependencies: Python 3.10+; riverview_core.work_registry
# Authority: Registry writes confer no execution authority
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: tests/test_work_registry.py
# =============================================================================
"""Common registry CLI usable by Windows PowerShell, Linux shell and services."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from riverview_core.work_registry import WorkRegistry, WorkRegistryError  # noqa: E402


def default_path():
    configured = os.environ.get("RIVERVIEW_WORK_REGISTRY_PATH")
    if configured:
        return Path(configured)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Riverview" / "work-registry.json"
    return Path.home() / ".local" / "state" / "riverview" / "work-registry.json"


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--registry", type=Path, default=default_path())
    commands = result.add_subparsers(dest="command", required=True)
    worker = commands.add_parser("register-worker")
    worker.add_argument("--worker-id")
    worker.add_argument("--worker-type", required=True)
    worker.add_argument("--hostname", default=os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME"))
    worker.add_argument("--os", dest="os_name", default=os.name)
    worker.add_argument("--capability", action="append", default=[])
    worker.add_argument("--model-identity")
    worker.add_argument("--endpoint-ref")

    start = commands.add_parser("start-session")
    start.add_argument("--worker-id", required=True)
    start.add_argument("--session-id")
    start.add_argument("--hostname")
    start.add_argument("--os", dest="os_name")
    start.add_argument("--repository")
    start.add_argument("--branch")
    start.add_argument("--pull-request")
    start.add_argument("--model-identity")
    start.add_argument("--endpoint-ref")

    beat = commands.add_parser("heartbeat")
    beat.add_argument("--session-id", required=True)
    beat.add_argument("--activity-state", choices=("unknown", "idle", "working", "waiting"))

    end = commands.add_parser("end-session")
    end.add_argument("--session-id", required=True)
    end.add_argument("--lifecycle", choices=("completed", "disconnected"), default="completed")

    acknowledge = commands.add_parser("acknowledge-work-order",
        help="Record an assignment receipt from the existing dispatcher; grants no authority")
    acknowledge.add_argument("--work-order-id", required=True)
    acknowledge.add_argument("--worker-id", required=True)
    acknowledge.add_argument("--session-id", required=True)

    create = commands.add_parser("create-work-order")
    create.add_argument("--session-id")
    create.add_argument("--worker-id")
    create.add_argument("--owner-label")
    create.add_argument("--ownership-state", choices=("unassigned", "proposed", "assigned", "acknowledged"))
    create.add_argument("--title", required=True)
    create.add_argument("--status", choices=("unknown", "queued", "active", "blocked", "completed", "failed", "cancelled"), default="queued")
    create.add_argument("--fields-json", help="JSON object containing allowed work-order metadata; never include prompts or traces")

    update = commands.add_parser("update-work-order")
    update.add_argument("--work-order-id", required=True)
    update.add_argument("--fields-json", required=True, help="JSON object containing allowed work-order metadata")

    show = commands.add_parser("snapshot")
    show.add_argument("--json-file", action="store_true", help="Write the full observation snapshot to stdout")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    registry = WorkRegistry(args.registry)
    try:
        if args.command == "register-worker":
            result = registry.register_worker(worker_id=args.worker_id,
                worker_type=args.worker_type, hostname=args.hostname,
                os_name=args.os_name, capabilities=args.capability,
                model_identity=args.model_identity, endpoint_ref=args.endpoint_ref)
        elif args.command == "start-session":
            result = registry.start_session(args.worker_id, session_id=args.session_id,
                hostname=args.hostname, os_name=args.os_name, repository=args.repository,
                branch=args.branch, pull_request=args.pull_request,
                model_identity=args.model_identity, endpoint_ref=args.endpoint_ref)
        elif args.command == "heartbeat":
            result = registry.heartbeat(args.session_id, activity_state=args.activity_state)
        elif args.command == "end-session":
            result = registry.end_session(args.session_id, lifecycle=args.lifecycle)
        elif args.command == "acknowledge-work-order":
            result = registry.acknowledge_work_order(args.work_order_id,
                args.worker_id, args.session_id)
        elif args.command == "create-work-order":
            fields = json.loads(args.fields_json) if args.fields_json else {}
            if not isinstance(fields, dict):
                raise ValueError("fields-json must be an object")
            allowed = {"work_order_id", "detail", "milestone", "milestones_total", "milestones",
                "dependencies", "blocker", "next_action", "evidence", "outcome", "repository",
                "branch", "pull_request", "deliverable", "local_ai_job"}
            if set(fields) - allowed:
                raise ValueError("fields-json contains unsupported create fields")
            result = registry.create_work_order(args.session_id, worker_id=args.worker_id,
                owner_label=args.owner_label, ownership_state=args.ownership_state,
                title=args.title, status=args.status, **fields)
        elif args.command == "update-work-order":
            fields = json.loads(args.fields_json)
            if not isinstance(fields, dict):
                raise ValueError("fields-json must be an object")
            result = registry.update_work_order(args.work_order_id, **fields)
        else:
            result = registry.snapshot()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ValueError, WorkRegistryError) as exc:
        print(json.dumps({"status": "error", "code": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
