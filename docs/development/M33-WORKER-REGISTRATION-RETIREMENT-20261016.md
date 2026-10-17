<!--
Riverview~ Controlled Document
File: docs/development/M33-WORKER-REGISTRATION-RETIREMENT-20261016.md
Component: WORKER-ADAPTER / INSTITUTIONAL-AUTHORITY
File Revision: 1.0.11
Purpose: Specify safe retirement of the two registrations for revoked M33 commissioning run e92ec515
Authority: Steward-authorized fixed-ID operation; production migrations 0008/0009 are applied and the two M33 registrations were retired on 2026-10-17 UTC
Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Document retirement controls, audit, recovery boundary, and operator procedure
Changed: 2026-10-17 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Add exact read-only postflight and match systemd preflight states
Changed: 2026-10-17 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Link the finalized controlled verification evidence
Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Correct immutable release path and document the 0008 prerequisite blocker
Changed: 2026-10-17 UTC | RV-M33-MIGRATION-CHAIN-0008-0009 | Record authorized preparation, exact migration effects, and remaining production gates
Changed: 2026-10-17 UTC | M33-0009-SYSTEMD-PARSER-FIX | Record corrected named-property stop verification and production manager-privilege blocker
Changed: 2026-10-17 UTC | M33-0009-PRODUCTION-CLOSEOUT | Record migration 0009 and fail-closed retirement blocker
Changed: 2026-10-17 UTC | M33-0009-PRODUCTION-CLOSEOUT | Clarify current live status and execution boundary
Changed: 2026-10-17 UTC | M33-REGISTRATION-RETIREMENT-AUTHORIZED | Record exact row-scoped permission window, guarded retirement, cleanup, audit events, and service acceptance
History: Git and evidence/checkouts/WORKER-REGISTRY-RETIREMENT/20261017T000450Z-e494478/
-->
# M33 worker registration retirement

## Scope and status

This procedure applies only to commissioning run `e92ec51590b34cd3b04d05c000f3eab4`, scope `work-order:m33-live-e92ec51590b34cd3`, and these two registration IDs:

- `worker:m33:executor:e92ec51590b34cd3`
- `worker:m33:verifier:e92ec51590b34cd3`

The operation preserves registration, assignment, attempt, result, and authority history. It changes only the two `worker_registry.active` flags and appends one `worker_registration_retired` authority event per worker in the same PostgreSQL transaction. It never deletes rows, reactivates a registration, restarts a service, alters Grace, or modifies MCP.

The source operation is implemented in `scripts/retire_revoked_m33_worker_registrations.py` and `src/riverview_core/worker_adapter/retirement.py`. Migration `0009_worker_registration_retirement_event.sql` only adds the required event type to the authority event constraint; it creates no grants. Registration retirement is not claimed complete until the guarded operation succeeds and the operator captures actual before/after evidence.

The fixed helper requires the existing manager connection to read its exact
preconditions and update the two registration flags. For the authorized 2026-10-17
execution, a time-bounded administration transaction granted schema `USAGE`,
column-only reads needed for the fixed inventory and M33 assignment/lease checks,
and registry table `UPDATE` guarded by row-level policies for only the two fixed
M33 IDs. Those temporary grants and policies were removed immediately after the
helper completed. Current manager access has no app-schema `USAGE`, registry
`UPDATE`, temporary policies, or enabled RLS from this operation. Check effective
privilege state read-only:

```sh
sudo -n env PGPASSFILE=/etc/riverview/authority/manager.pgpass \
  psql "host=127.0.0.1 port=5432 dbname=riverview user=riverview_authority_manager" \
  -X --set=ON_ERROR_STOP=1 -c \
  "BEGIN READ ONLY; SELECT current_user,has_table_privilege(current_user,'riverview_dev.worker_registry','UPDATE'); COMMIT;"
```

If it returns `false` or the role cannot connect, stop. Do not add a grant or
substitute `postgres`; that privilege boundary needs a separate reviewed
execution design before the registration write can occur.

## Fail-closed preconditions

The fixed helper requires root on Camrui, an exact mode-0600 root-owned revoked M33 state record, the protected current Steward credential, and the existing manager passfile. The database transaction verifies an active principal of kind `steward` with the exact `identity.manage` grant scoped to `institution`.

Before any write, it also verifies:

1. The two exact M33 registration rows are active and have the exact M33 scope.
2. There are seven rows and exactly five active rows: the two M33 registrations plus `worker:grace-engineering`, `worker:grace-engineering-source-change`, and `verifier:grace-engineering`.
3. Neither M33 principal has any currently effective grant or credential.
4. All three M33 units (`riverview-assignment-intake.service`, `riverview-m33-worker.service`, `riverview-m33-verifier.service`) report exactly `inactive` / `dead` with `MainPID=0`.
5. No unexpired lease belongs to either M33 worker, and no assignment in the M33 scope is queued, ready, running, awaiting verification, or rework-required.
6. The guarded helper requires the exact manager access needed to inspect its preconditions. The separately Steward-authorized temporary boundary used for the completed execution restricted registry updates to the two fixed M33 IDs and scoped assignment/lease reads to the M33 commissioning work; the helper itself did not grant privileges or assume another role.

Any mismatch aborts the helper transaction. The exact active-worker postcondition is the three Grace registrations only. Historical blocked M33 assignments and all execution evidence remain unchanged. An earlier 2026-10-17 attempt returned `InsufficientPrivilege` before writes; that state was superseded by the separately authorized, exact-ID row-scoped execution boundary described below. No unrestricted manager privilege, role substitution, or superuser helper execution was used.

## Controlled operator procedure

Camrui's actual active core path is `/opt/riverview-core`, a symlink directly to `/opt/riverview/releases/<40-character-source-commit>`; it has no `current` child. The M33 services use the separate `/opt/riverview-m33/current` package and must not be switched for this one-shot retirement utility. Install the reviewed package as a new, root-owned immutable directory under `/opt/riverview/releases/<commit>`, preserving the existing release. The controlled operator command must invoke files from that exact versioned directory, using the established Python environment at `/opt/riverview-core/.venv/bin/python`; it need not change either release pointer or restart any service.

The exact source hashes are: retirement command `scripts/retire_revoked_m33_worker_registrations.py` `9c8c95cfc2e998e9a10bbc1eb2af0c7bd30a2efd2147058a30e0527aee2051e9`; retirement module `src/riverview_core/worker_adapter/retirement.py` `e815894e0d9a138b45b510be088913f5474606d5cd7cbf927474bf7021c53f83`; migration `0009_worker_registration_retirement_event.sql` `0b5aa767a0209b22ec476721da02c47618443ee1b06e752aa1e416f6dbccaef6`.

Historical preparation note: 0009 declares migrations 0001–0008 as dependencies; at initial preflight the live ledger was 0000–0007. Since then the Steward authorized and migration 0008 was installed and verified, followed by authorized application of 0009. The current production ledger and checksums are recorded in the production closeout section below and in the linked evidence. Do not repeat either migration or run a migration sweep; the fixed runner rejects drift or extra entries.

Historical 0008 preparation gate (already satisfied): inspect the actual active runtime source and effective function ACLs before any migration change. The migration revokes `PUBLIC EXECUTE` on profile functions but does not grant runtime EXECUTE; the current authorizer calls its profile evaluator when it discovers the profile objects. If the exact runtime boundary is not already provisioned, stop and obtain separate review/authorization for that ACL change. Do not grant ad hoc or run the broad authority-boundary provisioner as part of this migration. At the time this historical note was written, the retirement helper was blocked by missing manager privileges; that blocker was later resolved by the separately authorized temporary row-scoped access recorded in the production result below. The direct `/opt/riverview-core` symlink and current 64e8 release must remain unchanged; install approved tooling in a new immutable `/opt/riverview/releases/<full-commit>` directory. Protected full-database backup, digest/list verification, and a disposable restore/count/ACL comparison are mandatory before DDL. The full step-by-step sequence is in the authority cookbook. Migration 0008 and 0009 are installed. Registration retirement had not yet occurred at the time of this historical preparation note; the later production result below is authoritative.

Historical execution sequence: 0008 was applied atomically with its runtime ACL correction after protected backup/restore and compatibility checks. Migration 0009 was subsequently applied through the exact single-migration runner. The migration chain is complete. At the time this note was written, registration retirement remained blocked by the manager authorization boundary; the later authorized operation and completion evidence are recorded below.

Historical package preparation instructions (completed for this run): build and verify the exact committed package with the controlled package builder and verifier. Install it into a new root-owned `/opt/riverview/releases/<commit>` directory without changing either `/opt/riverview-core` or `/opt/riverview-m33/current`; never overwrite `/opt/riverview/releases/64e8f14ad6d71102a864755739a1c8a61506235c`. Use the existing `/opt/riverview-core/.venv/bin/python` to run the candidate release's fixed migration preflight:

```sh
sudo -n -u postgres env PYTHONPATH=/opt/riverview/releases/<approved-commit>/src \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview/releases/<approved-commit>/scripts/apply_m33_retirement_migration.py --check
```

This was the initial preflight state and is superseded by the production closeout below: migrations 0008 and 0009 are now installed with their expected checksums. Do not reapply them. The retirement helper remains fail-closed until a separately reviewed narrow execution boundary exists.

After that dependency is resolved and every migration check passes, the Steward or authorized Camrui operator runs:

```sh
sudo -n env PYTHONPATH=/opt/riverview/releases/<approved-commit>/src:/opt/riverview/releases/<approved-commit>/scripts \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview/releases/<approved-commit>/scripts/retire_revoked_m33_worker_registrations.py --apply
```

The helper prints only redacted JSON: status, exact retired IDs, fixed run ID, remaining three Grace IDs, and verified stopped-unit states. It never prints the Steward token, credential digests, or database password. Do not retry an ambiguous response until the authority events, active flags, and assignment/lease postconditions are queried read-only.

Run the following read-only database diagnostic after the helper. It reports the seven registration rows and active set, M33 assignment/lease state, and retirement audit events without exposing credentials:

```sh
sudo -n -u postgres psql -d riverview -X --set=ON_ERROR_STOP=1 <<'SQL'
BEGIN READ ONLY;
SELECT worker_id,active,scope_ref FROM riverview_dev.worker_registry ORDER BY worker_id;
SELECT count(*) AS total_rows,
       count(*) FILTER (WHERE active) AS active_rows,
       array_agg(worker_id ORDER BY worker_id) FILTER (WHERE active) AS active_worker_ids
FROM riverview_dev.worker_registry;
SELECT id,state,workflow_step FROM riverview_dev.assignments
WHERE authority_ref='work-order:m33-live-e92ec51590b34cd3' ORDER BY id;
SELECT assignment_id,worker_id,expires_at FROM riverview_dev.assignment_leases
WHERE worker_id IN ('worker:m33:executor:e92ec51590b34cd3',
                    'worker:m33:verifier:e92ec51590b34cd3') ORDER BY assignment_id;
SELECT event_id,actor_id,subject_id,payload,recorded_at
FROM riverview_authority.institutional_authority_events
WHERE event_type='worker_registration_retired'
  AND subject_id IN ('worker:m33:executor:e92ec51590b34cd3',
                     'worker:m33:verifier:e92ec51590b34cd3')
ORDER BY recorded_at,event_id;
COMMIT;
SQL
sudo -n systemctl show riverview-assignment-intake.service riverview-m33-worker.service \
  riverview-m33-verifier.service --property=ActiveState,SubState,MainPID --no-pager
```

Acceptance requires seven rows total, exactly the three Grace IDs active, both exact M33 IDs inactive, two retirement events attributed to the Steward, no unexpired M33 lease, no executable M33 assignment, and all three M33 units still `inactive/dead` with PID 0. Confirm Grace, CME, event-processor, and dashboard service states were not changed. Preserve sanitized outputs and hashes under `evidence/checkouts/WORKER-REGISTRY-RETIREMENT/<timestamp>-<commit>/`.

## Troubleshooting and recovery

- `m33_service_not_stopped`: stop before running the helper. Do not stop any service as part of this operation; confirm the exact commissioned run's service shutdown through its separately authorized procedure.
- `worker_authority_not_fully_revoked` or `worker_credentials_not_revoked`: do not retire. Resolve only through the exact-run authority revocation workflow, then repeat read-only checks.
- `active_worker_lease_exists` or `executable_m33_assignment_exists`: stop; preserve the assignment and escalate to the work owner. Never clear or rewrite lease/assignment state to pass retirement.
- `registry_inventory_changed` or `active_registry_postcondition_failed`: stop and investigate the current inventory. The helper intentionally assumes the seven-row inventory stated in the live 2026-10-16 evidence and will not adapt automatically.
- Missing/mismatched migration or Steward authorization: do not bypass the registry boundary or issue direct SQL. Return to the controlled migration/authority procedure.
- If the helper returns an error, its single transaction rolls back both registration changes and audit events. No rollback write is needed.

After successful retirement, do not reactivate these old rows as rollback. Their credentials and grants are revoked. If M33 is commissioned again, use a new separately authorized run and fresh identities/credentials; retain the retired rows for audit.

## Migration and historical pre-retirement status — 2026-10-17

Migration 0009 was applied to Camrui after a checksum-pinned preflight and a
snapshot-consistent protected backup/restore rehearsal. Its ledger checksum is
`0b5aa767a0209b22ec476721da02c47618443ee1b06e752aa1e416f6dbccaef6`. The
migration only expands the authority event constraint; it does not retire
registrations.

Historical pre-retirement status: the initial production helper invocation falsely reported `m33_service_not_stopped` because Camrui's systemd property order differed from the assumed order. The parser was corrected to inspect named properties, then merged and installed in an immutable helper release. The next invocation verified stopped-unit state but failed closed with `InsufficientPrivilege` before database writes. That state was later resolved under the explicit Steward authorization and is superseded by the successful production result below.

The pre-retirement production inventory and migration result are recorded in the
M33-0009 execution evidence linked from the institutional authority cookbook;
the authoritative after-state is in the completed production result below.

## Source status

The implementation and regression tests are integrated in PR #80 at merge commit `bac5495c4b7d61fd250d88f6af4beead3c79ccfb`. Historical production migration, service, health, TLS, and failed-attempt results are recorded in `evidence/checkouts/M33-0009-PRODUCTION/20261017T032139Z/`; successful registration retirement is recorded in the later production result below.


## Historical production result before scoped authorization — 2026-10-17

The first helper attempts failed closed with `InsufficientPrivilege` and did not write. At that time the manager lacked `USAGE` on `riverview_dev`, registry reads, and registry updates; the two M33 registrations were still active and no retirement events existed. This was superseded by the Steward-authorized row-scoped operation below. The original evidence remains at `evidence/checkouts/M33-0009-PRODUCTION/20261017T032139Z/`.

## Production result — 2026-10-17 UTC

The existing protected backup/restore closeout remained applicable: authority migrations 0000–0009 were already committed and the retirement helper does not alter schema or the migration ledger. The backup archive at `/var/lib/postgresql/riverview-backup.m33-retire._mgw_b_2/riverview.dump` (SHA-256 `f50f82fc72d3e3f482fb9004cbc0e8cb73c9d2b8ad11cee8077643d7e8cbc29e`) was preserved and not overwritten.

Under the explicit Steward authorization, PostgreSQL administration temporarily granted `riverview_authority_manager` schema `USAGE`, column-only `SELECT` on `worker_registry(worker_id, active, scope_ref)`, `assignments(authority_ref, state)`, and `assignment_leases(worker_id, expires_at)`, plus table `UPDATE` on `worker_registry` because the existing helper checks that exact table privilege. RLS was temporarily enabled, not forced, on those three tables. The registry UPDATE policy admitted only `worker:m33:executor:e92ec51590b34cd3` and `worker:m33:verifier:e92ec51590b34cd3`; assignment and lease SELECT policies limited reads to the M33 scope and those IDs. The manager is non-superuser, NOINHERIT, has no memberships, and has no `riverview_core` membership. Existing `riverview_core` owner sessions bypassed these non-forced temporary policies, preserving service behavior. No PUBLIC grant, privilege escalation, or unrelated database role was used.

The installed guarded helper at immutable release `/opt/riverview/releases/bac5495c4b7d61fd250d88f6af4beead3c79ccfb` returned `RETIRED` (exit 0) for exactly the two authorized IDs. It recorded two append-only `worker_registration_retired` events, both actor `steward:camrui`, with zero active M33 leases, zero executable M33 assignments, and all three M33 units verified inactive/dead with PID 0. The registry retains all seven rows: the two M33 rows are inactive; all three Grace rows remain active; both historical M31 rows remain inactive.

Immediately after the helper, all four temporary policies were dropped, RLS disabled on the three tables, column/table privileges revoked, and schema `USAGE` revoked from the manager. Read-only catalog postflight confirmed no residual temporary policies, RLS, schema USAGE, or registry UPDATE. The authority migration ledger remains the same ten rows (0000–0009) with expected checksums. CME monitor, Grace CPU inference and execution session, status dashboard, event processor, and notification dispatcher remained active/running. The three M33 units remain inactive/dead. Strict-TLS GET `https://192.168.1.155/` returned HTTP 200.

Sanitized evidence: `evidence/checkouts/M33-REGISTRATION-RETIREMENT/20261017T0347Z-3da69dc/production-acceptance.json`.

**Status: COMPLETE.** The registrations were retired without deleting rows, altering migration history, changing Grace authority, restarting services, or reactivating M33 services.
