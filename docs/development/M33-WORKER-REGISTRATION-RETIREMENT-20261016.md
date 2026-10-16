<!--
Riverview~ Controlled Document
File: docs/development/M33-WORKER-REGISTRATION-RETIREMENT-20261016.md
Component: WORKER-ADAPTER / INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Specify safe retirement of the two registrations for revoked M33 commissioning run e92ec515
Authority: Steward-authorized fixed-ID operation; production execution remains pending controlled release and live preflight
Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Document retirement controls, audit, recovery boundary, and operator procedure
History: Git and evidence/checkouts/WORKER-REGISTRY-RETIREMENT/20261016T-procedure/
-->
# M33 worker registration retirement

## Scope and status

This procedure applies only to commissioning run `e92ec51590b34cd3b04d05c000f3eab4`, scope `work-order:m33-live-e92ec51590b34cd3`, and these two registration IDs:

- `worker:m33:executor:e92ec51590b34cd3`
- `worker:m33:verifier:e92ec51590b34cd3`

The operation preserves registration, assignment, attempt, result, and authority history. It changes only the two `worker_registry.active` flags and appends one `worker_registration_retired` authority event per worker in the same PostgreSQL transaction. It never deletes rows, reactivates a registration, restarts a service, alters Grace, or modifies MCP.

The source operation is implemented in `scripts/retire_revoked_m33_worker_registrations.py` and `src/riverview_core/worker_adapter/retirement.py`. Migration `0009_worker_registration_retirement_event.sql` only adds the required event type to the authority event constraint; it creates no grants. Production execution is not claimed until the reviewed source is installed, migration 0009 is explicitly applied through the authority migration cookbook, and the operator captures actual before/after evidence.

The executing manager role must already have the precise worker-table update
privilege. Check that without changing anything:

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
4. All three M33 units (`riverview-assignment-intake.service`, `riverview-m33-worker.service`, `riverview-m33-verifier.service`) report inactive/failed with `MainPID=0`.
5. No unexpired lease belongs to either M33 worker, and no assignment in the M33 scope is queued, ready, running, awaiting verification, or rework-required.
6. The connected database role already has `UPDATE` on `riverview_dev.worker_registry`; the helper does not grant privileges or assume another role.

Any mismatch aborts the transaction. The exact active-worker postcondition is the three Grace registrations only. Historical blocked M33 assignments and all execution evidence remain unchanged. If the established authority-manager role lacks the required core-table `UPDATE` privilege, the operation reports `database_role_cannot_retire_registration` and makes no change. Do not grant it broader access or use a superuser workaround; an authorized database owner must provide/review a narrowly scoped execution boundary before production retirement can proceed.

## Controlled operator procedure

Run from an integrated Camrui release after review and exact-head CI. First follow `docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md` to verify the migration source checksum, migration prerequisites, backup, and migration procedure. Apply only the reviewed authority migration 0009; do not run website or worker migrations. Confirm the recorded 0009 checksum matches the released file.

The Steward or authorized Camrui operator then runs:

```sh
sudo -n env PYTHONPATH=/opt/riverview-core/current/src \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview-core/current/scripts/retire_revoked_m33_worker_registrations.py --apply
```

The helper prints only redacted JSON: status, exact retired IDs, fixed run ID, remaining three Grace IDs, and verified stopped-unit states. It never prints the Steward token, credential digests, or database password. Do not retry an ambiguous response until the authority events, active flags, and assignment/lease postconditions are queried read-only.

Postflight, using the documented read-only worker inventory query, must show seven registrations total, exactly three active (the three Grace IDs), both M33 rows inactive, and no changes to Grace registrations or assignments. Confirm exactly two new append-only `worker_registration_retired` events whose actors are the Steward and whose subjects are the two M33 worker principals. Confirm all three M33 services remain stopped and Grace/CME/event-processor/dashboard services unchanged. Preserve sanitized outputs and hashes under `evidence/checkouts/WORKER-REGISTRY-RETIREMENT/<timestamp>-<commit>/`.

## Troubleshooting and recovery

- `m33_service_not_stopped`: stop before running the helper. Do not stop any service as part of this operation; confirm the exact commissioned run's service shutdown through its separately authorized procedure.
- `worker_authority_not_fully_revoked` or `worker_credentials_not_revoked`: do not retire. Resolve only through the exact-run authority revocation workflow, then repeat read-only checks.
- `active_worker_lease_exists` or `executable_m33_assignment_exists`: stop; preserve the assignment and escalate to the work owner. Never clear or rewrite lease/assignment state to pass retirement.
- `registry_inventory_changed` or `active_registry_postcondition_failed`: stop and investigate the current inventory. The helper intentionally assumes the seven-row inventory stated in the live 2026-10-16 evidence and will not adapt automatically.
- Missing/mismatched migration or Steward authorization: do not bypass the registry boundary or issue direct SQL. Return to the controlled migration/authority procedure.
- If the helper returns an error, its single transaction rolls back both registration changes and audit events. No rollback write is needed.

After successful retirement, do not reactivate these old rows as rollback. Their credentials and grants are revoked. If M33 is commissioned again, use a new separately authorized run and fresh identities/credentials; retain the retired rows for audit.

## Source status

The implementation and isolated tests are review material. The previous production SSH path from this Linux execution environment was unavailable; no live retirement or production acceptance is claimed by this document. See the linked evidence and PR for the exact controlled source head and subsequent live operator outcome.
