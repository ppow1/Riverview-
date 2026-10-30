<!-- Controlled document revision 1.0.1 | 2026-10-28 -->
# Approved Grace source-worker update

Steward explicitly approved the exact source-only repin and three additional paths
in PR #369. This authorization is already recorded; do not request it again.
Current status: operator update completed and independently checked. The fresh direct
Engineering source-change objective completed with independent verification ACCEPTED.
Grace-generated planning and repository publication are not established by this run.

## Operator command

Initial operator command (already completed; do not rerun after UPDATED):

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
operator entry is required. The operator has since applied the update successfully; see the acceptance record below.

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

## Verified source-change acceptance — October 28, 2026

Operator apply exited 0 with UPDATED. New configuration SHA256:
832d11c8c9ac7c759e8a4c0ed603a36988ee500a24fff82857650065db347749.
Independent Camrui inspection matched that hash, target HEAD and clean tracked tree.

Fresh objective: objective:addb10e0-fa77-5d49-92ae-efaf710d81f7.
Assignment: assignment:grace:c97ba87c1fc684d83ae24ff3f17705ae6bb55d8a.
Attempt: 7b66e0e6-32e7-4c75-96b8-959b09450ff7.
Existing worker: worker:grace-engineering-source-change.
Capability: engineering.codex-cli-source-change.v1.
Canonical objective and assignment both COMPLETED. Independent verifier 1.0.1
ACCEPTED at 17:41:05 EDT: authorized changed paths, offline named tests and independent
patch replay all true. This used direct Engineering submission, bypassing Grace's
reasoning; it is not full autonomous workflow acceptance.

Actual worker-produced patch SHA256:
9f6ea0aa04b7f5367f66d133c2b75cde38925630ea198f7d745fa86b0d0b21cf (6837 bytes).
Retained at patches/grace_artifact_publication_admission_worker_ACCEPTED_20261028.patch.
The raw patch is receipt evidence. Source revision headers/predecessor archives must
be reconciled during forward integration before deployment. Do not apply it together
with the earlier manually prepared patch. Neither admission fix is deployed yet.

The current status endpoint omits the source result's base-revision field and patch
reference. Recorded requested target and the inspected source checkout are pinned to
9f56cb72f3bd2961babf2527a26bd843526e18ce. Filesystem inspection found the patch by the
exact assignment-key convention and independently hash-checked it; application to
the target passes, but applicability alone is not claimed as proof of origin.

Full receipt, payload and safe provenance are in evidence/checkouts/GRACE-AUTONOMY/
20261028T2141Z/. Next stage: forward-integrate the accepted correction through the
existing release/review process and exercise Grace-generated planning with full
repository/path/test scope. Preserve all completed records and existing sessions.
