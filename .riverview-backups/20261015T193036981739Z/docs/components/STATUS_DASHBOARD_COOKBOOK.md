<!-- Riverview~ Controlled Document
File: docs/components/STATUS_DASHBOARD_COOKBOOK.md
Component: STEWARD-DASHBOARD
File Revision: 1.1.0
Purpose: Troubleshoot and recover the read-only status dashboard
Authority: Diagnostic and read-only operations only
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Link consolidated recovery guide and correct CME unit name
Changed: 2026-10-11 UTC | RV-M3.2-001 | Link durable notification receipt diagnostics
Changed: 2026-10-11 UTC | RV-OPS-DASHBOARD-CURRENT-DOCS-RELEASE | Document immutable composite docs release provenance and verification
Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Require checksum-verified stream-delivery migration before enabling SSE
History: Git and revision/backup manifest
-->
# Status dashboard read-only troubleshooting cookbook

The dashboard links to the [complete Riverview operations and recovery guide](RIVERVIEW_OPERATIONS_COOKBOOK.md), covering PostgreSQL, migrations, CME, event processing, workers, verification, and backups.
The [notification delivery contract](NOTIFICATION_DELIVERY.md) and
[notification troubleshooting cookbook](NOTIFICATION_DELIVERY_COOKBOOK.md)
cover durable visual receipts. Receipt acknowledgment is not a Steward decision.

**Task:** RV-M3.1-001 · **Component:** STEWARD-DASHBOARD · **Execution model:** request-driven.  
The dashboard does not own assignments, dispatch workers, mutate the ledger, or
gate CME execution.

## Readable diagnostic documents and workflow viewer

Dashboard diagnostic-reference links open a formatted HTML presentation of
controlled component Markdown. The renderer formats headings, tables and code
blocks, hides file-metadata comments, escapes source HTML, and emits no scripts.
Only HTTPS, in-page anchors and component-document links are clickable. The
controlled Markdown remains the source; there is no parallel HTML document.

The **Workflows** view reads authenticated `GET /api/v1/graphs` and
`GET /api/v1/graphs/<graph_id>` projections from the deployed
`process_graphs/*/*.json` registry. It shows graph revision, stable node IDs,
node type, typed transitions and cross-workflow jump destinations. Selecting a
node shows its source, documentation and evidence references. The browser is
read-only. It highlights live execution only when the API supplies an exact
persisted process-node identity. Assignment records do not currently store that
identity; `unknown` with no highlighted node is expected, not a failure or an
inferred position.

An unknown graph ID returns `404 process_graph_not_found`. Source unavailability
is displayed as unavailable, with no stale highlight. Check the canonical source
and generated views locally:

```sh
python3 scripts/process_graph.py check
python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json
```

The service reads from its selected root-owned release. Deploy a new verified
full-SHA release to update code and graph data together; never hot-edit the
installation or copy an uncommitted graph.

Run the reproducible, read-only Firefox commissioning check on Camrui with an
assignment that has a completed worker attempt and independent verification:

```sh
python3 scripts/verify_status_dashboard_browser.py \
  --assignment-id <completed-assignment-id> \
  --output /tmp/riverview-dashboard-browser-check
```

The protected token path defaults to `/home/admin1/.config/riverview/status-dashboard.token`.
The utility refuses a permissive token file or existing output directory, never
prints the token, and writes a redacted JSON report and browser screenshots only
to the requested new directory. It verifies live status/attention/assignment
routes, browser JavaScript parseability, graph nodes/decisions/transitions/jumps,
formatted cookbook safety, navigation, and browser errors. It does not mutate
assignments or services.

## CME attention endpoint and 503 responses

Before the M2.4 migration, `/api/v1/attention` returned HTTP 503 when the
`cme_monitor_events` relation was absent. The projection correctly reported
`status=not_initialized`, but the HTTP status caused the browser to record a
request error on each refresh interval. A missing optional relation is now
returned as HTTP 200 with the explicit `not_initialized` domain status, and the
browser skips polling that endpoint until the status projection confirms the
relation exists. An actual database/query failure still returns HTTP 503.

Check relation and service state before diagnosing repeated errors:

```sql
SELECT to_regclass('riverview_dev.cme_monitor_events') AS attention_relation;
SELECT service_id,status,last_heartbeat_at,last_scan_at
FROM riverview_dev.cme_monitor_health;
```

Use `/api/v1/status` to distinguish a missing relation from an unavailable
source. Do not interpret HTTP success with `status=not_initialized` as evidence
that CME monitoring is operational.

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
| `degraded` | CME recorded a failure or missing successful scan while still reachable. | Use `systemctl status riverview-cme-monitor.service` if installed and the CME cookbook. Dashboard does not restart CME. |
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

The durable Grace conversation stream requires the resident-execution migration
`0008_resident_conversation_stream_delivery.sql`. Before activating an integrated
release that enables SSE, verify all earlier resident-execution migration checksums,
then apply only a missing reviewed migration through the established migration
runner after a protected backup and disposable restore. This migration adds one
stream-delivery table and grants the runtime role SELECT/INSERT/UPDATE on that
table only; it does not change authority permissions or canonical conversation
history. Dashboard startup never applies migrations. If the migration is absent,
has a checksum mismatch, or the runtime table ACL is incomplete, stop activation;
do not fall back to broad database privileges. The legacy non-streaming API remains
available for clients that cannot stream.

For a docs-only release, preserve the existing dashboard executable and static
assets; install updated component documents and synchronized canonical graph
views into a new root-owned immutable release directory. Preserve predecessor
releases. Record the dashboard code commit separately from the documentation
and graph commit in a release manifest and checksum list. Keep `source_commit`
bound to the code commit, set a unique deployment identifier, and change only
the dashboard systemd unit and `current` release link. Verify all documented
routes and process graphs against the candidate before switching; after restart
verify loopback HTTP, authenticated status, service health and dependent service
continuity. On failure restore only the prior dashboard link/unit and restart
only `riverview-status-dashboard.service`.
