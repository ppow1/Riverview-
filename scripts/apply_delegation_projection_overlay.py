# Riverview~ Controlled Source
# File: scripts/apply_delegation_projection_overlay.py
# Component: STEWARD-DELEGATION-APPROVAL-API
# Revision: 1.0.0
# Purpose: Apply a narrow, fail-closed route overlay to a newer composite Dashboard source
# Execution Model: Explicit file-in/file-out deploy preparation; never mutates a live tree
# Observability: Deterministic error messages and SHA-256 deploy manifest
# Dependencies: Existing Dashboard server source with authenticated dispatch anchors
# Authority: No service control, database write, or authority mutation
# Changed: 2026-10-26 UTC | RV-V2-DELEGATION-PROJECTION-001 | Preserve current production server while adding the bounded Steward routes.
# Tests: tests/test_delegation_routes.py
# History: Initial controlled source
"""Apply the small delegation route hook to the current composite Dashboard file."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


_DECLARATION_ANCHOR = '            snapshot_archive = parsed.path == _SNAPSHOT_ARCHIVE and self.command == "POST"\n'
_ALLOWLIST_ANCHOR = '                    and not snapshot_archive\n'
_ROUTE_ANCHOR = '            if snapshot_archive:\n                identity = getattr(self, "_account_identity", None)\n'
_DECLARATION = '''            delegation_revoke = (re.fullmatch(
                r"^/api/v1/steward/delegated-grants/(grant:[A-Za-z0-9._:-]{1,128})/revoke$",
                parsed.path) if self.command == "POST" else None)  # capability-exclusion: Steward administrative revocation; not resident-invocable
            delegation_route = (
                self.command in {"GET", "HEAD"} and (
                    parsed.path in {"/api/v1/steward/delegation-grant-requests",  # capability-exclusion: Steward administrative projection; not resident-invocable
                                    "/api/v1/steward/delegated-grants"} or
                    re.fullmatch(r"^/api/v1/steward/delegation-grant-requests/"
                                 r"delegation-request:[A-Za-z0-9._:-]{1,128}$", parsed.path))  # capability-exclusion: Steward administrative projection; not resident-invocable
            ) or delegation_revoke is not None
'''
_ROUTE = '''            if delegation_route:
                from riverview_core.status_dashboard.delegation_routes import dispatch
                dispatch(self, parsed, request_id)
                return
'''


def apply(source: str) -> str:
    if not isinstance(source, str):
        raise TypeError("dashboard_source_must_be_text")
    if "delegation_route = (" in source and "delegation_routes import dispatch" in source:
        return source
    if source.count(_DECLARATION_ANCHOR) != 1:
        raise ValueError("dashboard_snapshot_dispatch_anchor_not_unique")
    if source.count(_ALLOWLIST_ANCHOR) != 1:
        raise ValueError("dashboard_post_allowlist_anchor_not_unique")
    if source.count(_ROUTE_ANCHOR) != 1:
        raise ValueError("dashboard_authenticated_route_anchor_not_unique")
    source = source.replace(_DECLARATION_ANCHOR, _DECLARATION_ANCHOR + _DECLARATION, 1)
    source = source.replace(_ALLOWLIST_ANCHOR,
                            '                    and not delegation_revoke\n' + _ALLOWLIST_ANCHOR, 1)
    source = source.replace(_ROUTE_ANCHOR, _ROUTE + _ROUTE_ANCHOR, 1)
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
    manifest = {
        "schema": "rv.dashboard-source-overlay.v1",
        "source_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "overlay": "Steward delegation reads and canonical revocation",
    }
    args.destination.with_suffix(args.destination.suffix + ".overlay.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
