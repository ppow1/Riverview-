<!--
Riverview~ Controlled Document
File: docs/development/M33-COMMISSIONING-DECOMMISSION-20261016.md
Component: WORKER-ADAPTER / INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Record controlled decommission of the expired M33 test commissioning run
Authority: Steward-authorized exact-run revocation; no assignment or schema changes
Changed: 2026-10-16 UTC | RV-M33-DECOMMISSION-001 | Record exact-run production decommission, verification, and recovery boundary
History: Git and evidence/checkouts/M33-DECOMMISSION/20261016T231925Z-e92ec515/
-->
# M33 expired commissioning decommission

**Task:** RV-M33-DECOMMISSION-001  
**Result:** Decommissioned; no worker reactivation authorized or performed.  
**Environment:** Camrui production, 2026-10-16 UTC  
**Evidence:** `evidence/checkouts/M33-DECOMMISSION/20261016T231925Z-e92ec515/`

## Exact run and preconditions

The target was the single run recorded in `/etc/riverview/worker/m33-commissioning.json`:

- Run ID: `e92ec51590b34cd3b04d05c000f3eab4`
- Source commit: `47a79adafe1524b3e819148b70c02a1857f50dbf`
- Scope: `work-order:m33-live-e92ec51590b34cd3`
- Executor: `worker:m33:executor:e92ec51590b34cd3`
- Verifier: `worker:m33:verifier:e92ec51590b34cd3`
- Run state before revocation: `provisioned`
- Exact grant and current worker credential expiry: `2026-10-11 16:43:30 EDT`

The run was a bounded `m33-live-engineering-test` commissioning with an eight-hour grant lifetime. Before stopping services, the production assignment ledger showed four completed assignments, one assignment blocked at `WAITING_FOR_EVIDENCE`, and zero ready, running, or awaiting-verification assignments. The blocked assignment and all five assignment records were preserved unchanged.

The three required services were active. Their systemd reverse-dependency listings contained no dependent service. The intake exposed only its expected loopback listener on port 8768 and had no established client connections. These checks, the pre-revocation service state, the exact grant/credential metadata, the assignment state, and the run metadata are preserved in the evidence directory. The complete pre-change state JSON was also preserved at:

`/var/lib/riverview-m33-worker/m33-commissioning.pre-decommission-20261016T231925Z-e92ec515.json`

Its SHA-256 is `b6867d74417333b55b855d6b34a717c2bf7a0b7e93fdca27e521a98e056da1b6`. No credential value or credential digest was copied.

## Decommission operation

The deployed helper at `/opt/riverview-m33/current/scripts/provision_m33_runtime_credentials.py` matched the repository helper byte-for-byte (SHA-256 `185160041dabd9f8d363c55911be136b0c952a001e0f1a1cb7a95347b0cad3ab`). Its release source was the recorded M33 commit above.

After confirming the exact three units were inactive, the existing guarded procedure was run:

```text
sudo -n env PYTHONPATH=/opt/riverview-m33/current/src:/opt/riverview-m33/current/scripts \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview-m33/current/scripts/provision_m33_runtime_credentials.py --revoke
```

It exited 0 and returned `status=REVOKED` for the exact run and scope. It revoked the five recorded grants (`assignment.create`, the two `worker.register` grants, `assignment.execute`, and `assignment.verify`) and all credentials attached to the two run-specific worker principals. The already-revoked initial credentials remained revoked. It did not edit expiry timestamps, revoke other identities, or change worker registration or assignment rows.

The helper removed only the expected protected files:

- `/etc/riverview/worker/m33-worker.credential`
- `/etc/riverview/worker/m33-verifier.credential`
- `/etc/riverview/m33-worker.env`
- `/etc/riverview/m33-verifier.env`

It retained the mode-0600 commissioning state file and set its status to `revoked`, recording `revoked_at=2026-10-16T23:19:59.370835Z`.

## Post-checks

All three target units remain `inactive/dead` with `MainPID=0`:

- `riverview-assignment-intake.service`
- `riverview-m33-worker.service`
- `riverview-m33-verifier.service`

Read-only PostgreSQL checks confirmed all five exact grants have `revoked_at` values, all four recorded credential rows are revoked, and the five assignments retain their pre-decommission IDs, states, workflow steps, and timestamps. A read-only `SELECT 1` succeeded.

Post-checks also confirmed these unrelated services remain active/running: PostgreSQL database access, CME monitor, event processor, Grace CPU inference, Grace Engineering owner session, notification dispatcher, and status dashboard. All three active Grace worker registrations remain active. No Grace identity, grant, objective, assignment, or worker configuration was changed.

## Recovery and rollback boundary

The expired credentials and grants are not a rollback target. Do not restore their files, extend their old timestamps, or reactivate the old registrations for execution. The M33 registrations remain recorded as active rows, but their run credentials and exact authority are revoked, so they cannot authorize work.

The current M33 helper does not provide a repeat-commissioning path after the state record is marked revoked; it rejects that state rather than overwriting it. If the Steward later commissions M33 again, prepare and review a versioned run-specific provisioning path that preserves this run record, uses fresh finite credentials and exact grants, and accounts for the worker registry’s credential-digest binding. Keep all three services stopped until that separately authorized commissioning is complete. The previous blocked assignment remains `WAITING_FOR_EVIDENCE`; it was not resumed or modified.

The executor’s pre-existing rapid retry behavior for `WorkerAuthorizationError` was not changed in this operational task. The services are stopped, so it is no longer generating retries. Address that behavior in a separately reviewed source change before a future M33 activation.

## Evidence inventory

The linked evidence folder contains pre/post service and dependency snapshots, the protected state-record digest, redacted state metadata, read-only PostgreSQL pre/post outputs, unchanged assignment row comparison, removed-file checks, the revoker result, and SHA-256 inventory. No bearer values, credential digests, assignment bodies, or unrelated private data are included.
