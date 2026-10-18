# =============================================================================
# RIVERVIEW~ CONTROLLED EVIDENCE UTILITY
# File: evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/verify_predecessors.py
# Component: RESIDENT-ORCHESTRATION / INSTITUTIONAL-PROPOSALS
# Revision: 1.0.1
# Purpose: Verify saved lifecycle-test predecessor bytes against their source Git commit/blob and temporary restore copies
# Execution Model: Request-driven, read-only checkout verification
# Observability: JSON stdout with exit status; no test content emitted
# Dependencies: Python 3.10+, Git, saved .riverview-backups files
# Authority: Reads Git/backups and writes only temporary files; no source, database, service or remote changes
# Changed: 2026-10-18 UTC | RV-C3-GRACE-ENGINEERING-E2E-001 | Persist repeatable predecessor recovery verification
# Changed: 2026-10-18 UTC | RV-C3-GRACE-ENGINEERING-E2E-001 | Correct repository-root resolution after the first recorded run exposed an off-by-one parent index
# Contracts: docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md
# Tests: Execute this script from repository root; result recorded in predecessor-restoration.log
# History: Git and linked checkout artifacts
# =============================================================================
"""Check exact predecessor hashes and a disposable file-copy restore without modifying the worktree."""
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ROWS = [
    {
        "revision": "1.1.3",
        "backup": ".riverview-backups/20261018T153214396336Z/tests/test_proposal_work_order_lifecycle.py",
        "source_commit": "64b2e022e99fd6b548cf30963b475e236066470d",
        "git_blob": "4fdee5fc9bbf8daa1ab76344f0e81bd877651c9c",
        "sha256": "c73d94baebc7c0d8580d69ad64c0931ba71cc3641956dc5fdd491b950aa60fda",
    },
    {
        "revision": "1.1.4",
        "backup": ".riverview-backups/20261018T160440033495Z/tests/test_proposal_work_order_lifecycle.py",
        "source_commit": "ea30f489aaed9545438364fc50561a075afbafe8",
        "git_blob": "ef75e87d2f90bf0913aabe4bf211b9271a586c43",
        "sha256": "6dd448fb966d411155757b62427d72675cccde5f0eecc1935ff45b1ee6f0737d",
    },
]

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

results = []
for row in ROWS:
    saved = (ROOT / row["backup"]).read_bytes()
    assert sha(saved) == row["sha256"], f"backup hash mismatch: {row['revision']}"
    source = subprocess.check_output([
        "git", "-C", str(ROOT), "show",
        f"{row['source_commit']}:tests/test_proposal_work_order_lifecycle.py",
    ])
    assert source == saved, f"saved bytes differ from source commit: {row['revision']}"
    blob = subprocess.check_output([
        "git", "-C", str(ROOT), "rev-parse",
        f"{row['source_commit']}:tests/test_proposal_work_order_lifecycle.py",
    ], text=True).strip()
    assert blob == row["git_blob"], f"Git blob mismatch: {row['revision']}"
    with tempfile.TemporaryDirectory(prefix="rv-c3-restore-") as temp:
        restored = Path(temp) / "tests/test_proposal_work_order_lifecycle.py"
        restored.parent.mkdir()
        shutil.copyfile(ROOT / row["backup"], restored)
        assert restored.read_bytes() == saved and sha(restored.read_bytes()) == row["sha256"]
    results.append({**row, "exact_git_match": True, "temporary_restore_verified": True})

print(json.dumps({"status": "PASS", "predecessors": results}, indent=2))
