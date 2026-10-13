<!-- Riverview~ Controlled Document
File: docs/components/STATUS_DASHBOARD_COOKBOOK.md
Component: STEWARD-DASHBOARD
File Revision: 1.0.3
Purpose: Troubleshoot and recover the read-only status dashboard
Authority: Diagnostic and read-only operations only
Changed: 2026-10-10 UTC | RV-M3.1-001 | Record worker health and credential troubleshooting
History: Git and revision/backup manifest
-->
# Status dashboard read-only troubleshooting cookbook

**Task:** RV-M3.1-001 · **Component:** STEWARD-DASHBOARD · **Execution model:** request-driven.  
The dashboard does not own assignments, dispatch workers, mutate the ledger, or
gate CME execution.

## Credential delivery

The unit loads pgpass with systemd LoadCredential. Its root-owned read-only
0440 mount is validated with runtime_baseline.systemd_credential_path, then
copied with copy_systemd_credential to /run/riverview-status-dashboard/pgpass
inside the service-owned 0700 RuntimeDirectory. This produces the 0600 passfile
required by libpq. The token remains a separate credential and is never logged.

## Worker health

The overview shows a bounded worker page from GET /api/v1/workers. Health is
derived from each worker’s latest assignment-lease heartbeat; missing heartbeat
is unknown, future heartbeat is unverified, and expired lease does not mean a
worker is healthy. Pagination is keyset-bounded. A missing worker/lease relation
is not_initialized and does not fabricate worker health.

## Fast read-only checks

```sh
systemctl is-active riverview-status-dashboard.service
systemctl show riverview-status-dashboard.service -p ActiveState -p SubState -p MainPID
curl --fail --silent --show-error http://127.0.0.1:8766/
ss -ltn '( sport = :8766 )'
```

Use a browser Authorization token from the protected Steward credential for
`/api/v1/*`; never put it in a URL, shell history, report or log. The unit's
standard output records service identity/commit only; journald excludes request
URLs and headers. A dashboard credential may be rotated by updating its
owner-only source file and restarting only this unit. Do not read or replace the
existing PostgreSQL credential.

## State meanings

| Display | Meaning | First check / recovery |
| --- | --- | --- |
| `healthy` | A successful bounded read of the initialized ledger; a healthy CME/worker state additionally needs a fresh recorded heartbeat. | Check `observed_at`, source commit, service identity and component-specific heartbeat. |
| `stale` | A persisted heartbeat is older than the configured 30-second freshness window. | Check only the owning service's unit/journal and database reachability; do not restart unrelated services. |
| `degraded` | CME recorded a failure or missing successful scan while still reachable. | Use `systemctl status riverview-cme.service` if installed and the CME cookbook. Dashboard does not restart CME. |
| `not_initialized` | PostgreSQL is reachable but the requested component tables/health row do not exist. | Confirm selected database/schema/migration ledger. Never run DDL from dashboard startup. |
| `unavailable` | No trustworthy current read was returned. Browser last-known data is not labelled healthy. | Check PostgreSQL and dashboard journal; retry after cause is resolved. |
| `unknown` / `unverified` | No lease heartbeat exists or a timestamp is future-dated. | Preserve uncertainty; inspect source clock/lease evidence. |

## Process-first fault isolation

| Workflow node | Expected evidence | Failure signal | First diagnostic | Recovery and resume |
| --- | --- | --- | --- | --- |
| Request and authenticate | HTTP request ID and successful bearer comparison | HTTP 401, 400 invalid Host, 405 write method | Browser request state; verify loopback URL and protected token source | Re-enter authorized token; never relax loopback/verb checks. |
| Open read-only projection | PostgreSQL read transaction, schema and current observation timestamp | `projection_unavailable`/503 or status `unavailable` | `systemctl status riverview-status-dashboard.service`; inspect sanitized journal error type | Resolve DB/socket/credential availability; GET again. Dashboard makes no writes. |
| Detect initialization | relation and migration inventory | `not_initialized` | status `relations` and source schema | Correct service configuration or separately authorized migration; restart is not a migration. |
| Project lifecycle/events | bounded page, institution privacy filter, event cursor | empty/not found or page source error | assignment ID, event sequence and correlation ID | Inspect ledger contract; use next keyset/sequence cursor; no full history rebuild. |
| Render/update | local tab switch and localized view update | browser-local sanitized error entry | snapshot browser error ring and request ID | Refresh affected panel only; slow/unavailable DB must not hold navigation. |
| Export snapshot | bounded JSON file and explicit redaction metadata | snapshot bound exceeded or API failure | browser-local recent error code and captured timestamp | retry after page refresh; export includes no credentials or event payload. |
| Restart/reconnect | same release/port; current state re-read from PostgreSQL | systemd failed/inactive or authentication lost | `systemctl status` and `journalctl -u ... -n 50 --no-pager` | restart only the dashboard unit; reauthenticate; CME and assignments continue independently. |

## Deployment and rollback

1. Record current dashboard symlink and unit checksum before first install/change.
2. Verify package manifest against committed source and install only to a new
   versioned release directory owned by root and not writable by `riverview`.
3. Provision the bearer token through an owner-only file and systemd credential;
   preserve existing DB credentials and deliver them through the existing
   `LoadCredential=pgpass:/etc/riverview/pgpass` contract.
4. Configure only `riverview-status-dashboard.service`, bound to `127.0.0.1:8766`.
5. Check the versioned release/commit, service identity, loopback listener and
   authenticated status read. Restart this unit once and repeat the check.
6. On failure, stop only the dashboard service, restore its prior unit/link from
   the deployment record, reload systemd and restart only that unit. Confirm the
   event processor and baseline service did not change.

No shared database migration is required. Do not use the dashboard to apply one.
The default source returns truthful unavailable/not-initialized states if its
database tables are absent or unreadable.
