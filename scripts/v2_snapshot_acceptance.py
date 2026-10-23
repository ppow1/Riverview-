# Riverview~ Controlled Source
# File: scripts/v2_snapshot_acceptance.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.0
# Purpose: Validate the V2 full diagnostic ZIP contract for browser acceptance
# Execution Model: Read-only ZIP and manifest inspection
# Observability: Stable acceptance failure codes
# Dependencies: Python 3.10+ standard library
# Authority: Local archive validation only; does not authenticate or upload
# Tests: tests/test_v2_workspace_shell.py, scripts/verify_v2_full_diagnostic_snapshot_browser.py
# History: Git and revision/backup manifest
"""Validation contract for a successful full V2 diagnostic ZIP."""
import hashlib
import io
import json
import zipfile


def validate_v2_full_diagnostic_archive(data):
    """Reject preview-only ZIPs and verify full V2 member evidence."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        if "manifest.json" not in names:
            raise ValueError("v2_snapshot_manifest_missing")
        manifest = json.loads(archive.read("manifest.json"))
        if (manifest.get("schema_version") != "rv.website.diagnostic-snapshot.v2"
                or manifest.get("dashboard_version") != "v2"
                or manifest.get("capture_mode") != "authenticated-dashboard"
                or manifest.get("capture_complete") is not True):
            raise ValueError("v2_preview_zip_is_not_full_diagnostic")
        expected = manifest.get("expected", {})
        exported = manifest.get("exported", {})
        if (expected.get("screens", 0) < 5
                or exported.get("screens") != expected.get("screens")
                or exported.get("workflows", 0) < 1
                or exported.get("workflows") != expected.get("workflows")):
            raise ValueError("v2_diagnostic_inventory_incomplete")
        required = {
            "website/v2/workspace-state.json",
            "website/v2/control-inventory.json",
            "diagnostics/dashboard-status.json",
            "diagnostics/operational-snapshot.json",
            "diagnostics/workflow-index.json",
            "diagnostics/graph-index.json",
        }
        if not required.issubset(names):
            raise ValueError("v2_diagnostic_members_missing")
        screen_paths = manifest.get("capture", {}).get("v2_screens", [])
        if len(screen_paths) != expected.get("screens") or not all(path in names for path in screen_paths):
            raise ValueError("v2_screen_capture_inventory_incomplete")
        workflow_paths = [name for name in names if name.startswith("diagnostics/workflows/")]
        if len(workflow_paths) != expected.get("workflows"):
            raise ValueError("v2_workflow_capture_inventory_incomplete")
        file_entries = {entry.get("path"): entry for entry in manifest.get("files", [])}
        for name in names - {"manifest.json"}:
            entry = file_entries.get(name)
            content = archive.read(name)
            if (entry is None or entry.get("size_bytes") != len(content)
                    or entry.get("sha256") != hashlib.sha256(content).hexdigest()):
                raise ValueError("v2_diagnostic_member_hash_mismatch")
        return manifest
