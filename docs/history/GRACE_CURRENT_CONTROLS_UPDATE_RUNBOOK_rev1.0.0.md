<!-- Riverview Controlled Document
File: docs/operations/GRACE_CURRENT_CONTROLS_UPDATE_RUNBOOK.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.0
Changed: 2026-10-28 UTC
-->
# Install the current Grace development controls

This is a development-system update. Reuse the established Windows operator
desktop-ja3rpnq\wille and its camrui SSH alias (admin1), with non-interactive
sudo for protected service deployment. Existing Comms5 host grants remain
active/unlimited; this does not request or renew them.

The Gateway/Codex identity can edit/test the Engineering checkout but cannot
write protected service releases. The one operator command below performs
the already-authorized service update; it is not a new authorization request.

## Reviewed changes

- Comms5 backend 1.2.3 → 1.2.4: register canonical objective cancellation.
- Dashboard Comms5 operations 1.1.1 → 1.1.2: exact-grant cancellation plus bounded
  verifier summary, boolean criterion statuses and sanitized artifact references.
- Dashboard pipeline 1.1.45 → 1.1.46: trusted institutional principal uses the
  existing exact assignment.cancel check.
- Existing Comms5 command task/delegation/cancellation routes are retained.
- Four runtime files change. No migration, new credential, grant or service.

Actual bases: Comms5 b6b5ce715508590cc8e56051c00bf7ed17fdbf79 and Dashboard
8325d3ffe8e53f3deaab4c9e14e471467454a08b. The current PR base 0ae1aea is a
documentation successor with matching runtime bytes. Full hash manifest:
[GRACE_CURRENT_RUNTIME_PORT_MANIFEST_20261028.json](../development/GRACE_CURRENT_RUNTIME_PORT_MANIFEST_20261028.json).

## Execute from the documented Windows operator session

The launcher is already staged and parsed successfully on Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Public\Documents\Riverview\GraceControls\Update-RiverviewGraceControls.ps1"
```

[PowerShell source](../../scripts/Update-RiverviewGraceControls.ps1) clears the
console, verifies operator identity and the prepared Bash script SHA256,
runs dry-run before apply, captures SSH exit codes and copies the full report.
It uses the existing camrui alias without selecting another identity or key.
BatchMode and sudo -n fail instead of prompting for credentials.

The prepared Camrui entry is
/home/admin1/.local/share/riverview/engineering/Riverview/scripts/grace_current_controls_20261028.sh.
Reviewed SHA256:
f56ba6dc22717168c2caad0374a298b88f4e2eafb34157e2bf223b109462ef7d.
It uses the prepared candidate files in
.riverview-write-acceptance/grace-current-source-8325d3-stage/candidate/src
under that Engineering checkout, whose four hashes are pinned in the script.

Direct operator alternative:

```powershell
ssh -n -T -o BatchMode=yes camrui "sudo -n bash /home/admin1/.local/share/riverview/engineering/Riverview/scripts/grace_current_controls_20261028.sh --apply"
```

## Behavior, expected result and rollback

[Linux entry source](../../scripts/grace_current_controls_20261028.sh) rechecks
exact predecessor pointers/hashes and candidate hashes, creates separate release
copies, replaces four runtime files, verifies hashes and static compilation,
atomically changes the current pointers, restarts existing Comms5 and Dashboard
units, and checks service/HTTP responses. Failure after activation restores both
old pointers and restarts the old services. Candidate directories remain as
evidence; a subsequent attempt refuses the same candidate name.

Expected operator report: DRY_RUN_EXIT_CODE=0, APPLY_EXIT_CODE=0 and APPLY_OK.
A dry-run or hash failure stops before activation. Preserve the complete report.

Explicit rollback uses the same established operator identity:

```powershell
ssh -n -T -o BatchMode=yes camrui "sudo -n bash /home/admin1/.local/share/riverview/engineering/Riverview/scripts/grace_current_controls_20261028.sh --rollback"
```

Health checks cover active services and HTTP responsiveness. They do not establish
Grace objective acceptance. After activation, use the existing Comms5 objective
status tool to retrieve the actual verifier diagnostics. Confirm the new
comms5_cancel_objective tool is exposed before attempting the approved retirement
of the stale GROUNDED objective. Preserve all old events and same-objective/reason
idempotency. Do not substitute draft cancellation for objective cancellation.

## Verification and continuity

- 10 focused current-source offline tests passed on Camrui.
- 4 installer guard tests passed; real live dry-run matched pointers/hashes.
- 3 additional isolated lifecycle tests passed in Work scratch: apply/explicit
  rollback, failed-restart automatic rollback, and candidate-drift refusal.
  These used temporary release roots and fake service commands, not live services.
- Bash syntax, Python compilation and Windows PowerShell parsing passed.
- PostgreSQL integration and live deployment/cancellation remain unverified.
  Broader socket-binding checks were sandbox denied.
- Hash-verified source transfer raw diff:
  f4a9199eda7ca73c8bb0be9528df010e0179705bd1b771b248c9f47a3acbf3bd.

Exact Camrui Codex thread: 01a17fdf-6d58-7050-92cc-1762ac986518.
Port run grace-current-controls-port-20261028-01; result
fb573859-d625-452f-a936-9f95eb09c4d2,
audit badc6a28-041f-4394-be48-f4e163873fe2.
Package run grace-current-controls-package-20261028-01; result
108f255e-8800-4c7b-9630-ce95a33461a7,
audit 34fee871-31a8-414c-838f-8fe1fec36a83.
Windows final launcher staging e211b557-0f75-4e39-8f5e-da70ca31811f,
audit 555d832d-e1f8-471a-9525-e5d6010728cb; parse errors 0.

Fresh objective objective:proposal:f6af71cc-39f4-5457-99bd-de9110c23cd2:r2
reached Engineering attempt 8247d85c-30b6-4122-9f6e-a849985a7c72 succeeded,
then verifier 1.0.5 REJECTED. Assignment
assignment:grace:d391056762e0a6f718dd6489e8cdcc6bb367d46e is rework_required.
This is partial workflow progress, not full Autonomy Grace completion.
Old objective objective:proposal:4ab91570-c31a-5420-994b-33474fe567ed:r2
has not been cancelled yet.
