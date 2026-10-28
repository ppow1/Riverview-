<!-- Controlled document revision 1.0.0 | 2026-10-28 -->
# Approved Grace source-worker update

Steward explicitly approved the exact source-only repin and three additional paths
in PR #369. This authorization is already recorded; do not request it again.
Current status: prepared and tested, not applied. Source-worker acceptance remains
unverified until the operator update and a fresh independently verified assignment.

## Operator command

Run once in the existing desktop-ja3rpnq\wille PowerShell session:

```powershell
& 'C:\Users\Public\Documents\Riverview\GraceSourceWorker\Update-RiverviewGraceSourceWorker.ps1'
```

The launcher uses the established camrui SSH alias with -n -T, checks the exact
script hash, invokes sudo -n for dry-run, and sends apply only after dry-run exits
zero. It displays and copies the full bounded report. It requires no TTY input.
Protected systemd operations use the established operator identity; the Gateway's
bounded Codex entry cannot perform them. This is an execution prerequisite, not
another approval request.

Windows launcher SHA256:
9F480F3C14163B90401833F728A7078F06302CA00444FFFCF01822519D9DE92A
Native Windows PowerShell parser: 0 errors. Its final pinned hash was independently
read back through Comms5 execution 10fe24eb-5c0d-4fbd-97ec-51165333a92a.

Prepared Camrui entry:
/home/admin1/.local/share/riverview/engineering/Riverview/scripts/update_grace_source_worker_20261028.py
Script revision 1.0.1 SHA256:
dfd631baa181b57aeca91bc157d633f3a1a72fe73bae18453656713bafabecc7

## Exact change

Existing unit: riverview-grace-execution-owner-session.service.
Only source repository path, source revision and source path allowlist change.
Repository: repo://ppow1/Riverview-.
Target: 9f56cb72f3bd2961babf2527a26bd843526e18ce.
Retained path: tests/test_local_reasoning_provider.py.
Added paths: src/riverview_core/resident_execution/pipeline.py,
src/riverview_core/resident_execution/service.py, tests/test_grace_execution.py.
Artifact repository settings, credentials, identities, grants and existing history
remain as configured. The admission-guard patch is not deployed by this updater.

The updater checks the exact declared/loaded source configuration and old checkout,
stages a clean clone of committed objects rather than workspace edits, preserves
owner/mode and rollback evidence, and checks the owner's cgroup before changes and
restart. Additional processes or unavailable process state block the update.
It requires the existing service-started event and stable PID/loaded values after
restart. Startup verification is distinct from actual source-task acceptance.

## Tests and records

The revised updater suite passed 12 cases, 0 skipped, on Camrui. The same 12 cases
also passed in Work using a dedicated synthetic fixture; these are not 24 distinct
cases. Test revision 1.0.2 uses tests/fixtures/grace_source_worker_predecessor.conf
so tests do not depend on the older published deployment template. That template
was not replaced. The runtime updater matches the exact tested Camrui bytes.

Test SHA256: 275875718b58d2ec3d9331bfb6b7ca3ca665e212fb88b7d333e31a3085a4491d
Fixture SHA256: f66c28146c558ec88eed056aedba3925ca279da94b36769b45e2ca8d0ed18e53

Camrui update-review execution: b8c42efe-9b92-43ee-a3e7-259d6ab0c849.
Final audit: 8d59c523-69ba-424b-8785-d0a841b1d728.
Exact Codex thread: 01a17fdf-6d58-7050-92cc-1762ac986518.
The sandbox dry-run stopped with systemd_bus_unavailable, exit 2; this is why the
operator entry is required. No live update has been performed.

## Rollback and continuation

The updater automatically attempts predecessor restoration on postcheck failure.
Keep the bounded failure report before any subsequent action.
After a successful apply, explicit rollback through the same operator alias is:

```powershell
ssh.exe -n -T -o BatchMode=yes camrui "sudo -n /usr/bin/python3 /home/admin1/.local/share/riverview/engineering/Riverview/scripts/update_grace_source_worker_20261028.py --rollback"
```

Keep both immutable releases and the exact backup/receipt identified by the result.
After UPDATED, independently verify the source-worker target and run one fresh
assignment restricted to the approved files/test target. Preserve its objective,
execution, patch digest and independent verifier evidence. Do not claim full Grace
autonomy from the updater or from Codex session success. Source execution returns
a scoped patch and tests; repository publication is still a separate capability.
