# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/start_riverview_codex.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Wrap an explicitly launched Codex CLI session with observational heartbeat reporting.
# Purpose: Register Codex process sessions without altering existing sessions or prompts
# Execution Model: Request-driven child process with periodic heartbeat
# Observability: Worker/session records and safe work-order metadata in the file registry
# Dependencies: Python 3.10+; local Codex CLI; riverview_core.work_registry
# Authority: Starts only when explicitly invoked; registry does not grant work execution authority
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: tests/test_work_registry.py
# =============================================================================
"""Start one Codex CLI child and report only its process/session observation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from riverview_core.work_registry import WorkRegistry  # noqa: E402


def _default_registry():
    configured = os.environ.get("RIVERVIEW_WORK_REGISTRY_PATH")
    if configured:
        return Path(configured)
    local = os.environ.get("LOCALAPPDATA")
    return (Path(local) / "Riverview" / "work-registry.json" if local else
            Path.home() / ".local" / "state" / "riverview" / "work-registry.json")


def _git_value(*arguments):
    try:
        result = subprocess.run(["git", *arguments], cwd=Path.cwd(),
            capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value[:512] if result.returncode == 0 and value else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=_default_registry())
    parser.add_argument("--worker-id")
    parser.add_argument("--session-id")
    parser.add_argument("--work-title", help="Safe summary only; do not pass a prompt here")
    parser.add_argument("--work-order-id", help="A work-order ID assigned to this session")
    parser.add_argument("--model", help="Pass an explicit Codex model choice through unchanged")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh", "max"))
    parser.add_argument("--full-permissions", action="store_true",
        help="Explicitly use --sandbox danger-full-access and --ask-for-approval never")
    parser.add_argument("--heartbeat-seconds", type=int, default=15)
    parser.add_argument("codex_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    codex_args = list(args.codex_args)
    if codex_args and codex_args[0] == "--":
        codex_args.pop(0)
    if not codex_args:
        parser.error("supply Codex CLI arguments after --; an interactive command is required")
    if not 5 <= args.heartbeat_seconds <= 60:
        parser.error("heartbeat interval must be between 5 and 60 seconds")
    if args.work_title and args.work_order_id:
        parser.error("use either --work-title or --work-order-id")

    host = socket.gethostname()
    host_key = re.sub(r"[^A-Za-z0-9._-]+", "-", host).strip("-.")[:80] or "unknown-host"
    os_label = "Windows" if os.name == "nt" else "Linux" if sys.platform.startswith("linux") else sys.platform
    worker_id = args.worker_id or f"worker:codex:{os_label.lower()}:{host_key}"
    session_id = args.session_id or f"session:codex:{uuid4().hex}"
    command = ["codex"]
    model = args.model
    if model:
        command.extend(["--model", model])
    if args.reasoning_effort:
        command.extend(["--config", f'model_reasoning_effort="{args.reasoning_effort}"'])
    if args.full_permissions:
        command.extend(["--sandbox", "danger-full-access", "--ask-for-approval", "never"])
    command.extend(codex_args)

    registry = WorkRegistry(args.registry)
    registry.register_worker(worker_id=worker_id, worker_type="codex", hostname=host,
        os_name=os_label, capabilities=["interactive-coding", "work-status"])
    session = registry.start_session(worker_id, session_id=session_id, hostname=host,
        os_name=os_label, repository=_git_value("rev-parse", "--show-toplevel"),
        branch=_git_value("branch", "--show-current"),
        pull_request=os.environ.get("RIVERVIEW_PULL_REQUEST"), model_identity=model)
    work = None
    if args.work_order_id:
        work = registry.acknowledge_work_order(args.work_order_id, worker_id, session_id)
    elif args.work_title:
        work = registry.create_work_order(session_id, title=args.work_title, status="active")
    print(f"Registered observational Codex session {session_id}", flush=True)
    if work:
        print(f"Registered work order {work['work_order_id']}", flush=True)

    process = None
    try:
        process = subprocess.Popen(command, cwd=Path.cwd())
        while process.poll() is None:
            time.sleep(args.heartbeat_seconds)
            if process.poll() is None:
                registry.heartbeat(session_id, activity_state="unknown")
        exit_code = process.returncode
        registry.end_session(session_id, lifecycle="completed")
        if work:
            registry.update_work_order(work["work_order_id"], status="unknown",
                blocker="Session ended before a work-order outcome was reported")
        return int(exit_code or 0)
    except KeyboardInterrupt:
        if process is not None and process.poll() is None:
            try:
                process.send_signal(getattr(__import__("signal"), "SIGINT"))
                process.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass
        registry.end_session(session_id, lifecycle="disconnected")
        if work:
            registry.update_work_order(work["work_order_id"], status="unknown",
                blocker="Session was interrupted before a work-order outcome was reported")
        return 130
    except OSError:
        registry.end_session(session_id, lifecycle="disconnected")
        if work:
            registry.update_work_order(work["work_order_id"], status="unknown",
                blocker="Codex process could not be started; no work-order outcome was reported")
        print('{"status":"error","code":"codex_start_failed"}', file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
