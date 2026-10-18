# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/WORK_REGISTRY_COOKBOOK.md
# Component: UNIVERSAL-WORK-REGISTRY
# File Revision: 1.0.1
# Purpose: Provide safe read-only diagnosis and recovery for the observational work registry
# Execution Model: Operator-invoked diagnostic and explicit event replay
# Authority: Read-only inspection; replay records only an explicitly authorized event and grants no execution authority
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-DOD-REMEDIATION-001 | Add read-only diagnostics and safe receipt recovery steps.
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-DOD-REMEDIATION-001 | Document repository import paths for Windows and Linux diagnostic commands.
# History: New document; no predecessor
# =============================================================================
# Work Registry diagnostic and recovery cookbook

This cookbook applies to the development file-backed registry and explicit v4 receipt bridge. Commands below do not launch, stop, wake, or inject into sessions, and do not allocate resources or change production authority. Do not include prompts, credentials, secrets, or private reasoning in work-order fields.

## Read-only snapshot

Run from the repository root. The CLI emits the registry snapshot; the filter below displays only identifiers, lifecycle/activity, heartbeat, assignment state, milestone, and whether a blocker exists. It omits long evidence, detail, outcome, endpoint references, and worker capability data.

### Windows PowerShell

```powershell
$env:PYTHONPATH = 'src'
$registryPath = 'A:\AI\Riverview-Development\_control\work-registry-v1.json'
$snapshot = python scripts/register_work.py --registry $registryPath snapshot | ConvertFrom-Json
$snapshot.workers | Select-Object worker_id, worker_type, hostname
$snapshot.sessions | Select-Object session_id, worker_id, lifecycle, activity_state, availability, last_heartbeat_at, heartbeat_age_seconds
$snapshot.work_orders | Select-Object work_order_id, worker_id, session_id, status, milestone, milestones_total, @{Name='has_blocker';Expression={[bool]$_.blocker}}
```

### Linux shell

```bash
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
python scripts/register_work.py --registry "$RIVERVIEW_WORK_REGISTRY_PATH" snapshot |
python -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps({"workers":[{k:w.get(k) for k in ("worker_id","worker_type","hostname")} for w in d["workers"]],"sessions":[{k:s.get(k) for k in ("session_id","worker_id","lifecycle","activity_state","availability","last_heartbeat_at","heartbeat_age_seconds")} for s in d["sessions"]],"work_orders":[{k:w.get(k) for k in ("work_order_id","worker_id","session_id","status","milestone","milestones_total")} | {"has_blocker":bool(w.get("blocker"))} for w in d["work_orders"]]},indent=2))'
```

The read-only Windows board can also be run once with `scripts/Start-RiverviewControlBoard-Registry.ps1 -Once`. For long evidence/blocker detail, use `-Detailed` only in a trusted console. Registry heartbeat indicates a reporting process, not active model reasoning.

## Diagnose common outcomes

| Symptom / signal | First read-only check | Safe response and resume point |
| --- | --- | --- |
| Snapshot CLI returns `registry_snapshot_invalid` or JSON parse error | Preserve the registry file and hash it with `Get-FileHash -Algorithm SHA256` (Windows) or `sha256sum` (Linux); rerun the snapshot once to rule out an active atomic replacement. | Do not overwrite the file. Preserve a copy and report the file path, hash, timestamp, and error to the registry owner. Restore only from an identified valid backup with the owner’s authorization; then rerun the snapshot. |
| Bridge returns `work_order_state_conflict` | Read the canonical snapshot and compare the current work-order status with the event’s expected state. | Do not force or reset status. Ask the work-order owner to reconcile the current state; resume only with an explicitly valid event and source reference. |
| Bridge reports alias, owner, mapping, or status JSON validation error | Check the alias entry in `docs/operations/CONTROL_BOARD_V4_IMPORT_MAP.json`, registry IDs, and the mapped local v4 file read-only. | Correct the authoritative mapping/source through its owner. Do not substitute a guessed identity or remote path. Resume the same explicit event after the mapping and ownership agree. |
| Bridge waits/fails on `.bridge.lock` | Confirm the named bridge process is no longer running and check the file’s modification time; avoid removing it while any writer may be active. | Preserve the lock and affected files as evidence. The file owner may remove a confirmed abandoned lock only after verifying no writer remains. Retry the same explicit event after lock recovery. |
| Registry shows the new event but v4 JSON still shows the old status | Snapshot both sources; validate the v4 JSON parses and identify the exact event/source/work-order ID. | Registry write and v4 mirror are separate atomic writes, not one transaction. Once the registry record is confirmed, invoke the identical event again with the same alias, canonical work-order ID, source reference, and status path. The bridge accepts replay for that event state and deduplicates receipt evidence. Verify both snapshots afterward. |
| v4 file is invalid or its prior evidence is missing | Read and preserve the file plus hash; compare with its established source/backup and do not hand-edit status to hide the discrepancy. | Ask the status-file owner to restore/reconcile through the approved source. Resume only after the original schema and historical evidence are intact. |
| Dashboard says unavailable/not initialized/stale | Check registry path existence, read-only snapshot exit status, and displayed heartbeat timestamps. | Fix only the configured development path or owner-approved dependency. Do not interpret a fresh heartbeat as reasoning activity. Keep unavailable/stale state visible until the source reports fresh data. |

## Explicit event replay

First inspect the registry and v4 status using the read-only commands above. If a failure occurred after the registry transaction committed but before the v4 atomic replacement, replay the same event; do not invent a new event or alter session activity/heartbeat. Example:

```powershell
python scripts/record_work_assignment.py record `
  --registry $registryPath --alias W1 `
  --work-order-id work:issue120:example:w1 `
  --event blocked --blocker 'Use the already recorded blocker text' `
  --source 'https://github.com/ppow1/Riverview-/issues/120#issuecomment-6252352344'
```

Use the actual canonical ID, matching source reference, exact recorded blocker/outcome, and the mapped local status path for that alias. Do not use this example ID or blocker as real data. Confirm that registry and status JSON agree after replay. A receipt records an observation only; it does not authorize execution, commissioning, provider access, or a session wake.

## Rollback

The existing `Start-RiverviewControlBoard-v4.ps1` remains the fallback. Stop using the optional new registry board launcher and continue with v4; no session restart is needed. Do not delete registry history or edit other monitoring files as rollback. Reverting the reviewed feature commit is a source-level option; preserve new evidence and obtain normal review before changing the PR stack.
