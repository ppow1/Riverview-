<!--
Riverview~ Controlled Document
File: docs/development/WORKER-REGISTRY-RETIREMENT-INVESTIGATION-20261016.md
Component: WORKER-ADAPTER / STEWARD-DASHBOARD
File Revision: 1.0.0
Purpose: Record bounded investigation of five dashboard worker registrations and retirement lifecycle
Authority: Read-only production investigation; no registry or service changes
Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIREMENT-001 | Record source findings, prior preserved inventory, access blocker, and safe next action
History: Git and evidence/checkouts/WORKER-REGISTRY-RETIREMENT/20261016T-current/
-->
# Worker registry retirement investigation

**Task:** RV-WORKER-REGISTRY-RETIREMENT-001

**Disposition:** Blocked before live five-row reconciliation or retirement. No production rows or services were changed.

**Evidence directory:** `evidence/checkouts/WORKER-REGISTRY-RETIREMENT/20261016T-current/`

## Findings and limits

The Steward reported a dashboard summary of 0 healthy, 2 stale, and 3 unknown workers. The dashboard source (`src/riverview_core/status_dashboard/projection.py`) derives health from the latest `assignment_leases.heartbeat_at`: missing heartbeat is `unknown`; age beyond the configured threshold is `stale`; only registrations with `worker_registry.active=true` contribute to active health counts. The per-worker API also returns active/inactive registration separately from lease-derived status. Thus these numbers are lease-observation categories, not proof that a process is alive, dead, or required.

The current execution environment could not authenticate to `admin1@192.168.1.155` using configured default SSH identities: `Permission denied (publickey,password)`. No key material was displayed. The current five-row registry, live assignments/leases, principal metadata, and per-worker health could therefore not be refreshed. The supplied aggregate is recorded as user-reported, not independently re-observed in this task.

The last preserved production database evidence is the M33 decommission record at `evidence/checkouts/M33-DECOMMISSION/20261016T231925Z-e92ec515/`. It records the two exact M33 worker IDs as still `active=true` after revoking that run's credentials and grants, with their five assignments unchanged (four completed and one blocked at `WAITING_FOR_EVIDENCE`). It also records all three Grace registrations as active after the decommission. This older evidence is not represented as a fresh inventory for the present task.

## Retirement lifecycle review

The worker adapter's public registration path is `PostgresWorkerAdapter.register_worker`, which inserts a registration; authentication rejects a row whose `active` flag is false. No supported retire, deactivate, unregister, or worker-registry lifecycle API/helper was found in the inspected source, scripts, and worker/dashboard contracts. The M33 `--revoke` helper is narrowly scoped to grants, credentials, protected run files, and run state; its documented postcondition explicitly leaves worker registration and assignment rows unchanged. Directly updating `worker_registry.active`, although technically possible for a sufficiently privileged database role and used in isolated test fixtures, would be an undocumented mechanism and is not authorized by this assignment.

Accordingly, no worker was retired. In particular, the two M33 registrations must remain as historical rows unless an existing, documented lifecycle path is identified; the three Grace workers must not be deactivated on the basis of unknown lease heartbeat. The current dashboard warnings may continue to include the M33 rows because they remain active registrations. Whether each Grace worker process is operational, idle, or disconnected remains unresolved pending fresh process and lease evidence.

## Preserved inventory from the latest available evidence

| Worker ID | Purpose / scope | Registration state in preserved evidence | Last known authority/work evidence | Present task disposition |
|---|---|---|---|---|
| `worker:m33:executor:e92ec51590b34cd3` | M33 executor; `work-order:m33-live-e92ec51590b34cd3` | Active row after run revocation | Run-specific credential and grants revoked; no ready/running/awaiting-verification assignment; four completed and one blocked historical assignment | Retain row pending a supported retirement lifecycle; exact live heartbeat not refreshed |
| `worker:m33:verifier:e92ec51590b34cd3` | M33 verifier; same exact run scope | Active row after run revocation | Run-specific credential and grants revoked; same preserved assignment inventory | Retain row pending a supported retirement lifecycle; exact live heartbeat not refreshed |
| `worker:grace-engineering` | Grace Engineering executor; `engineering.codex-cli-artifact.v1`, `work-order:engineering` | Active row after M33 decommission | Grace principal/credential/grants were reported active and non-expiring in prior read-only checks; must not infer process health from this | Retain; current assignment and process state not refreshed |
| `worker:grace-engineering-source-change` | Grace source-change executor; `engineering.codex-cli-source-change.v1`, `work-order:engineering` | Active row after M33 decommission | Same Grace scope and active authority in prior read-only checks | Retain; current assignment and process state not refreshed |
| `verifier:grace-engineering` | Grace independent verifier; `assignment.verify.v1`, `work-order:engineering` | Active row after M33 decommission | Grace principal/credential/grants were reported active and non-expiring in prior read-only checks | Retain; current assignment and process state not refreshed |

The prior M33 evidence confirms its three required services remained stopped after revocation. No service was restarted or otherwise changed here. Because the current SSH connection failed, the present service state and inventory are unverified.

## Required next safe action

An authorized operator must restore the already-approved read-only SSH access path for `admin1@192.168.1.155` (without weakening host policy or exposing a private key), then capture the current worker rows, bounded lease/assignment/verification associations, safe principal/grant metadata, and exact systemd process state. Before retiring either M33 registration, the integration owner must identify an existing audited lifecycle operation that marks only those exact rows inactive while preserving assignments, attempts, results, and audit history. If none exists, a separately reviewed lifecycle contract and implementation is required; do not substitute ad hoc SQL. Recheck the three Grace workers independently and retain them unless their owner establishes a different disposition.

## Source and evidence references

- Dashboard classification: `src/riverview_core/status_dashboard/projection.py`, worker summary and `workers()` read model.
- Registration/authentication: `src/riverview_core/worker_adapter/adapter.py`, `register_worker()` and `_authenticated_worker()`.
- Worker registry schema: `src/riverview_core/worker_adapter/migrations/0001_worker_attempts.sql` (`active` boolean, no lifecycle/audit field).
- Worker contract: `docs/components/WORKER_ADAPTER_COOKBOOK.md`.
- M33 exact-run revocation and preserved assignment evidence: `docs/development/M33-COMMISSIONING-DECOMMISSION-20261016.md` and linked evidence directory.
- This task's read-only source-search and SSH result: linked evidence directory.
