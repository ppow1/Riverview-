# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/import_issue_120_work_inventory.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Seed observational work orders from issue #120 without claiming live sessions.
# Purpose: Idempotently import the cited issue's initial work inventory
# Execution Model: One-shot local file import; supports dry-run
# Observability: Proposed owners and last-known statuses remain explicitly labeled
# Authority: Creates no worker session and grants no execution authority
# Contracts: docs/components/WORK_REGISTRY.md; docs/operations/ISSUE_120_INITIAL_WORK_INVENTORY.json
# Tests: tests/test_work_registry.py
# =============================================================================
"""Seed issue #120's initial inventory without synthesizing workers or sessions."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from riverview_core.work_registry import SCHEMA_VERSION, WorkRegistry  # noqa: E402


def import_inventory(inventory_path: Path, registry_path: Path, *, dry_run=False):
    if inventory_path.is_symlink():
        raise ValueError("inventory symlinks are not accepted")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if (inventory.get("schema_version") != "rv.work-registry.issue-inventory.v1"
            or not isinstance(inventory.get("items"), list)):
        raise ValueError("unsupported issue inventory schema")
    registry = WorkRegistry(registry_path)
    existing = {item["work_order_id"] for item in registry.snapshot()["work_orders"]}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    work_orders = {}
    for item in inventory["items"]:
        work_id = "work:issue120:" + item["id"]
        if work_id in existing:
            continue
        work = {
            "work_order_id": work_id, "session_id": None, "worker_id": None,
            "owner_label": item.get("owner_label"),
            "ownership_state": item["ownership_state"], "title": item["title"],
            "detail": item.get("detail"), "status": item["status"],
            "milestone": item.get("milestone"),
            "milestones_total": item.get("milestones_total"), "milestones": [],
            "dependencies": item.get("dependencies", []), "blocker": item.get("blocker"),
            "next_action": item.get("next_action"),
            "evidence": [inventory["source"]], "outcome": None,
            "repository": item.get("repository"), "branch": None,
            "pull_request": item.get("pull_request"), "deliverable": None,
            "local_ai_job": None, "created_at": now, "updated_at": now,
            "started_at": None, "completed_at": None,
        }
        WorkRegistry._validate_work_order(work)
        work_orders[work_id] = work
    result = {"status": "dry_run" if dry_run else "imported",
              "source": inventory["source"], "items_added": len(work_orders),
              "workers_added": 0, "sessions_added": 0,
              "message": inventory["observability_note"]}
    if not dry_run and work_orders:
        registry.import_document({"schema_version": SCHEMA_VERSION,
                                  "workers": {}, "sessions": {},
                                  "work_orders": work_orders})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path,
        default=ROOT / "docs/operations/ISSUE_120_INITIAL_WORK_INVENTORY.json")
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    import os
    registry_path = args.registry or Path(os.environ.get("RIVERVIEW_WORK_REGISTRY_PATH",
        str(Path.home() / ".local/state/riverview/work-registry.json")))
    try:
        print(json.dumps(import_inventory(args.inventory, registry_path,
                                          dry_run=args.dry_run), sort_keys=True))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status":"error", "code":str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
