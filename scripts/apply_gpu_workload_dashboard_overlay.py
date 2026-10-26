# Riverview~ Controlled Source
# File: scripts/apply_gpu_workload_dashboard_overlay.py
# Component: V2-GPU-WORKLOAD-CONTROLS
# Purpose: Add GPU route hooks to the currently installed composite Dashboard without replacing newer code
# Execution Model: Explicit file-in/file-out deployment preparation; never mutates live files
# Authority: Adds only fixed route dispatch and exact static asset names
"""Apply the narrow GPU-control route hooks to a newer composite Dashboard source."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


_DECLARATION_ANCHOR = '            conversation_session = (parsed.path == _CONVERSATION_SESSION\n'
_ALLOWLIST_ANCHOR = '                    and not delegation_revoke\n'
_ROUTE_ANCHOR = '            if snapshot_archive:\n                identity = getattr(self, "_account_identity", None)\n'
_STATIC_OLD = 'v2_asset = re.fullmatch(r"/v2/assets/(favicon\\.svg|workspace\\.css|fixtures\\.js|workspace\\.js|snapshot\\.js)", parsed.path)'
_STATIC_NEW = 'v2_asset = re.fullmatch(r"/v2/assets/(favicon\\.svg|workspace\\.css|fixtures\\.js|workspace\\.js|snapshot\\.js|gpu-workload-controls\\.css|gpu-workload-controls\\.js)", parsed.path)'
_DECLARATIONS = '''            gpu_workload_read = (parsed.path == "/api/v1/hardware/workloads" and self.command in {"GET", "HEAD"})  # capability-operation: hardware.gpu.workload.read
            gpu_workload_job = (re.fullmatch(r"^/api/v1/hardware/workloads/jobs/[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", parsed.path) is not None and self.command in {"GET", "HEAD"})  # capability-operation: hardware.gpu.workload.read
            gpu_workload_start = (parsed.path == "/api/v1/hardware/workloads/start" and self.command == "POST")  # capability-operation: hardware.gpu.workload.start
            gpu_workload_stop = (parsed.path == "/api/v1/hardware/workloads/stop" and self.command == "POST")  # capability-operation: hardware.gpu.workload.stop
            gpu_workload_switch = (parsed.path == "/api/v1/hardware/workloads/switch" and self.command == "POST")  # capability-operation: hardware.gpu.workload.switch
            gpu_workload_route = (gpu_workload_read or gpu_workload_job or gpu_workload_start
                                  or gpu_workload_stop or gpu_workload_switch)
'''
_ROUTE = '''            if gpu_workload_route:
                from riverview_core.status_dashboard.gpu_workload_routes import dispatch
                dispatch(self, parsed, request_id)
                return
'''


def apply(source: str) -> str:
    if not isinstance(source, str):
        raise TypeError("dashboard_source_must_be_text")
    already = "gpu_workload_routes import dispatch" in source
    if already:
        return source
    if "delegation_route = (" not in source or "if delegation_route:" not in source:
        raise ValueError("composite_dashboard_delegation_baseline_required")
    if source.count(_DECLARATION_ANCHOR) != 1:
        raise ValueError("dashboard_route_declaration_anchor_not_unique")
    if source.count(_ALLOWLIST_ANCHOR) != 1:
        raise ValueError("dashboard_post_allowlist_anchor_not_unique")
    if source.count(_ROUTE_ANCHOR) != 1:
        raise ValueError("dashboard_authenticated_route_anchor_not_unique")
    if source.count(_STATIC_OLD) != 1 or _STATIC_NEW in source:
        raise ValueError("dashboard_v2_asset_allowlist_anchor_not_unique")
    source = source.replace(_DECLARATION_ANCHOR, _DECLARATIONS + _DECLARATION_ANCHOR, 1)
    source = source.replace(_ALLOWLIST_ANCHOR,
                            _ALLOWLIST_ANCHOR + '                    and not gpu_workload_route\n', 1)
    source = source.replace(_ROUTE_ANCHOR, _ROUTE + _ROUTE_ANCHOR, 1)
    source = source.replace(_STATIC_OLD, _STATIC_NEW, 1)
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    original = args.source.read_text(encoding="utf-8")
    output = apply(original)
    compile(output, str(args.destination), "exec")
    args.destination.write_text(output, encoding="utf-8")
    manifest = {"schema":"rv.dashboard-source-overlay.v1",
                "source_sha256":hashlib.sha256(original.encode()).hexdigest(),
                "output_sha256":hashlib.sha256(output.encode()).hexdigest(),
                "overlay":"fixed OCTOMINER1 workload routes and static assets"}
    args.destination.with_suffix(args.destination.suffix + ".overlay.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
