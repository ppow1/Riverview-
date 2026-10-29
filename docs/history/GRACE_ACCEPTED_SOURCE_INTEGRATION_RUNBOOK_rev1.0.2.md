<!-- Controlled document revision 1.0.2 | 2026-10-28 -->
# Grace owner-session source overlay review

This code-only preparation uses the existing owner-session release pointer procedure in `docs/components/GRACE_EXECUTION_COOKBOOK.md`. It clones the exact `/opt/riverview-grace-execution/current` predecessor, overlays only `pipeline.py` and `service.py`, then switches that one `current` symlink. The candidate test, history, and review records stay in Engineering staging. No database migration, complete published Git release, grant, worker-policy, service-unit, drop-in, Comms5, Dashboard, or objective change is involved. This prepared work stays within the already authorized development scope; no live action was performed.

## Idle guard and apply

`owner-release-update.sh --dry-run` checks exact on-disk predecessor, staged runtime hashes, unit/drop-in hashes, current pointer, stable owner MainPID, and the recursive systemd ControlGroup process set. Its running-unit check calls `_check_idle_cgroup` and `_control_group_processes` from the approved `scripts/update_grace_source_worker_20261028.py`. Apply requires the owner unit active with only its stable MainPID in the complete cgroup tree before protected release staging. It repeats that check after staging, immediately before pointer switch/restart. Unknown state, inaccessible cgroup files, a changing PID, or any additional process fails closed before pointer activation.

The clone preserves the predecessor tree and file ownership/modes. Only `src/riverview_core/resident_execution/pipeline.py` and `service.py` are overlaid. It verifies every other predecessor path remains byte-identical, checks both candidate hashes, and compiles those two Python files in memory. The owner unit and knowledge/source-worker drop-in hashes are checked again before switching. Only the owner-session current symlink changes, and only the owner-session unit can be restarted. Candidate readiness requires the existing service-started journal event, stable active MainPID, and no source-worker-unavailable event.

## Rollback

Use `owner-release-update.sh --rollback`. It verifies the exact candidate current pointer and candidate/predecessor hashes, then checks the unit state and recursive cgroup; it does not require candidate health. A running unit requires the stable sole MainPID. An inactive/failed unit is allowed only when MainPID is 0 and systemd reports no cgroup, or the accessible cgroup tree has no processes. A stopped rollback restores the predecessor pointer and leaves the service stopped. A running rollback restores the predecessor pointer, restarts only the owner unit, and verifies predecessor health. If health fails, the candidate pointer is restored. Unknown/busy cgroup state blocks pointer changes. This permits recovery from an unhealthy candidate without interrupting any active Engineering subprocess.

## Provenance and revisions

The live owner pipeline baseline is revision 1.1.45, SHA256 `0d32ef4439890e37b32d0f186cda73c39d6ec171e4bb246dd298e02e7a9a0873`; candidate 1.1.46 is `dfab86a2b7dd91f9b16d444bea6b79210e3d0e3318f9f3496075617b5b27ff64`. The live owner service is 1.0.61 → 1.0.62. The staged regression test is 1.0.88 → 1.0.89. The owner pipeline candidate's header 1.1.46 is independent of the separate Dashboard pipeline that also reports 1.1.46; the source paths and file bytes differ.

The accepted source-worker patch SHA256 is `9f6ea0aa04b7f5367f66d133c2b75cde38925630ea198f7d745fa86b0d0b21cf`. Integration patch SHA256 is `215d34e8f7fed5a3098328de534abcbb3bdc9f9139088af8a510d67a286fd8ce`. The clone retains its 9f56 `SOURCE_COMMIT` marker and base `PACKAGE_SHA256SUMS`; those identify/check the predecessor contents, not the two-file overlay. Overlay identity is the candidate path and two exact runtime hashes in `review.json`.

## Tests and host boundary

The isolated suite command is:

```sh
PYTHONPATH=.riverview-write-acceptance/grace-accepted-forward-stage/tests python3 -m unittest -v test_grace_owner_release_update
```

Six tests pass: stopped units without a cgroup, recursive busy cgroup without staging writes, empty stopped rollback, rollback independent of candidate health, predecessor hash mismatch, and current-pointer mismatch. `bash -n` passes. The read-only dry run is blocked with `systemd_bus_unavailable` because this sandbox cannot connect to the systemd bus; active state and actual host readiness remain unconfirmed. No service writes, restarts, protected commands, inference, credentials, or database state were used.

## Operator command and continuation

The helper and its guard remain at the exact stage path in review.json. The launcher verifies helper SHA256 `554e968d4b807d74fbc7c96b40373a6d270918ad44e5f20314f4e6b3fd62043e`; the helper pins the guard and approved updater before executing either. Windows launcher SHA256 `1bd9f43a124b4f47989339086f584e6ac61f819734d10d670127ef2596916329`; native PowerShell parser: 0 errors.

In the established `desktop-ja3rpnq\wille` PowerShell session, run:

```powershell
& "C:\Users\Public\Documents\Riverview\GraceAdmission\Update-RiverviewGraceAdmission.ps1"
```

It clears the display, validates the operator, uses the existing `camrui` SSH alias with BatchMode and noninteractive sudo, checks the script hash, then runs dry-run and apply sequentially only on success. It displays and copies the report. It does not create SSH identities or grants. The Gateway Codex sandbox cannot perform the systemd operation, so the existing operator path supplies that boundary.

Status: APPLIED BY OPERATOR; INSTALLED POINTER AND FILE HASHES INDEPENDENTLY VERIFIED. Seven runtime diagnostic tests passed before the helper changes; six helper tests passed after the final changes. These are separate suites, not repeated acceptance claims. The source worker remains configured at 9f56; its completed direct task remains accepted. After UPDATED, independently verify the owner current pointer, two loaded source hashes and stable service startup, then proceed to a fresh appropriately approved Grace-generated source plan. Full autonomous planning, conversation completion and repository publication remain unverified. Do not repeat commissioning or the source-worker update.

## Applied update — October 28, 2026

Operator desktop-ja3rpnq\wille reported helper SHA256 554e968d4b807d74fbc7c96b40373a6d270918ad44e5f20314f4e6b3fd62043e, DRY_RUN_EXIT_CODE=0 and APPLY_EXIT_CODE=0 / UPDATED. Current pointer now names the publication-fence-20261028-r1 candidate. Independent existing-session inspection matched both installed runtime hashes and the unchanged source-worker drop-in/clean source checkout. Do not rerun the one-time apply.

The helper's successful apply includes its owner startup health checks. Independent Codex inspection cannot repeat systemd checks because its bus access is denied; no readable owner heartbeat was found. Separately, the authenticated CME projection reported healthy at 19:31:58 EDT, heartbeat age5.167seconds. CME health is not represented as proof of owner-process loaded code.

The exact next draft proposal:a72e49fe-4c04-4178-973f-f50250a2d4f3 revision2 was explicitly approved by Pat and promoted with key grace-exact-source-binding-promote-20261028-01. Its objective objective:proposal:ce65c8fc-fa3e-580c-a6fa-2df4d08f57c5:r2 is COMPLETED revision9. Grace generated the plan, dispatched3 dependent source-change steps once each, and all3 reached verified. Three external performance evaluations and feedback consumptions are in canonical lineage. Do not promote again or repeat the acceptance run.

Latest milestone and continuation: docs/development/GRACE_GENERATED_SOURCE_ACCEPTANCE_20261028.md. This new exact-target patch is NOT deployed. The earlier publication guard remains installed. Preserve the raw cumulative patch and reconcile controlled revision headers with the current deployed source before any later integration. Completion publication to a Grace conversation was not exercised by this Comms5-origin objective.
