<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_DELIVERY_COOKBOOK.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.1
Purpose: Diagnose notification projection, visual receipts, and provider queue status
Authority: Read-only diagnosis; receipt API records client receipt and no decision
Changed: 2026-10-11 UTC | RV-M3.2-001 | Initial operational procedure
Changed: 2026-10-18 UTC | RV-NOTIFICATION-STATUS-PROJECTION-20261018 | Document provider status API and state interpretation
History: Git and revision/backup manifest
-->
# Notification delivery troubleshooting cookbook

**Component:** NOTIFICATION-DELIVERY · **Channel:** dashboard visual ·
**Graph:** `rv:notification-delivery:visual-attention`.

## Safety boundary

The dispatcher does not change assignment state. Dashboard receipt does not
approve, reject, unblock, or resolve a Steward decision request. Do not edit
notification rows or delete records to make the UI look healthy. Do not expose
the dashboard token, PostgreSQL passfile, DSN, event details, or private task
content. Apply migration only using the backup/preflight procedure in the
[complete operations cookbook](RIVERVIEW_OPERATIONS_COOKBOOK.md).

## Observable states

| Symptom | Meaning | Initial checks |
| --- | --- | --- |
| API returns `not_initialized` | PostgreSQL is reachable, but migration 0006 is absent from this schema. | Check the selected schema and migration ledger read-only. |
| `push_delivery.status` is `not_initialized` | Migration 0007 or a worker health row is absent. | Check the configured schema and migration ledger read-only; do not apply a migration from the dashboard. |
| `push_delivery.status` is `stale` | Last recorded healthy heartbeat is older than 15 seconds. | Inspect only the notification delivery unit state and sanitized journal. |
| `push_delivery.status` is `degraded` | Worker recorded a failed cycle. | Use its bounded failure code and unit journal; the projection omits provider response bodies and secrets. |
| `push_delivery.status` is `unavailable` | Push status tables are inconsistent or its read failed; visual notice state may remain available. | Check migration 0007 and runtime SELECT grants read-only. |
| `push_delivery.recovery.state` is `retry_pending` or `lease_recovery_pending` | Durable retry or expired lease work exists. | Preserve queue rows; after the worker recovers it resumes using its lease and idempotency rules. |
| Notice stays `queued` | The persisted CME event was projected; no visible browser rendering receipt has been stored. | Open Notifications view; inspect browser error ring and dashboard journal. |
| Notice is `delivered` | An authenticated client reported successful visible rendering. This says nothing about human identity or decision. | Confirm the durable notification event exists. |
| Notice is `acknowledged` | An authenticated dashboard client recorded receipt acknowledgment. The linked request must remain pending. | Check both notice and request status. |
| Dispatcher health `degraded` or stale | Last reconciliation failed or last successful heartbeat is older than 15 seconds. | Check unit state and sanitized journal before restarting only this service. |
| `/api/v1/notifications` returns 503 | Database query failed; no new delivery is claimed. | Check dashboard and database health; do not mark rows delivered manually. |
| POST returns 401/405/409/404 | Missing bearer, unsupported operation, invalid order, or unknown notice. | Preserve response code and request ID; verify the exact allowed route. |

The provider projection is returned by the authenticated, read-only
`GET /api/v1/notifications?limit=1` response in `push_delivery`. Example
responses for healthy, stale, degraded, not-initialized and unavailable states
are in `../../tests/fixtures/notification_delivery_status_examples.json`.
It reports aggregate counts only. `accepted` means the provider accepted an
HTTP submission; it does not prove iPhone display. The API contract is not a
dashboard panel, and no Steward-facing UI integration is claimed by this
notification-owned increment.

## Exact read-only diagnostics

```sh
systemctl show riverview-notification-dispatcher.service \
  -p ActiveState -p SubState -p MainPID -p NRestarts
systemctl show riverview-status-dashboard.service \
  -p ActiveState -p SubState -p MainPID -p NRestarts
journalctl -u riverview-notification-dispatcher.service -n 60 --no-pager
journalctl -u riverview-status-dashboard.service -n 60 --no-pager
ss -ltn '( sport = :8766 )'
```

Expected: dispatcher `active/running`, dashboard `active/running`, bounded
restart count, and dashboard bound only to `127.0.0.1:8766`. Journal entries
contain fixed event/error-class fields, not source event details or credentials.
An inactive unit can mean migration has not yet been commissioned; do not
blindly start a unit against an uninitialized schema.

Use `psql` with the existing secured service credential mechanism and a
read-only transaction; never put a password in command arguments or chat:

```sql
BEGIN READ ONLY;
SELECT version, checksum FROM riverview_dev.schema_migrations ORDER BY version;
SELECT service_id, status, last_heartbeat_at, last_scan_at, last_error_type
FROM riverview_dev.notification_dispatcher_health;
SELECT notification_id, source_event_id, assignment_id, event_type,
       delivered_at, acknowledged_at
FROM riverview_dev.attention_notifications
ORDER BY created_at DESC, notification_id DESC LIMIT 25;
SELECT request_id, assignment_id, status, created_at
FROM riverview_dev.steward_decision_requests ORDER BY created_at DESC LIMIT 25;
SELECT notification_id, event_type, actor_type, recorded_at
FROM riverview_dev.notification_events ORDER BY recorded_at DESC LIMIT 50;
ROLLBACK;
```

Interpret timestamps as stored. A null `delivered_at` means no successful render
receipt. A null `acknowledged_at` means no receipt acknowledgment. An
`awaiting_steward` assignment may yield a pending request, but receipt events
must never change its status. The dashboard's shared bearer does not establish
individual Steward identity.

## Recovery

1. Record UTC time, unit state, source commit, exact request ID, and the fixed
   failure code/type. Capture read-only migration and health query results.
2. If PostgreSQL is unavailable, diagnose PostgreSQL using its own cookbook and
   preserve queued notices. Do not alter credentials.
3. If schema is not initialized, use the reviewed migration path only after
   backup and restore verification; dashboard startup never applies DDL.
4. If dispatcher alone is failed and database/schema/credential checks pass,
   restart only `riverview-notification-dispatcher.service`. Its durable scan
   replays source CME events; uniqueness prevents duplicate notices.
5. If dashboard alone is failed, follow its cookbook and restart only its unit.
   CME/event execution is independent. An unread notice remains queued; a later
   successful visible view may record delivery.
6. Repeat the read-only queries, load the authenticated Notifications view,
   and verify state/event counts. The `steward_decision_requests` row must remain
   `pending` after either receipt operation.

Never delete a notice, CME event, request, migration, or history row to clear an
error. Never drop notification tables to roll back. Keep additive schema state
and fix forward or restore a versioned dashboard release. Shared schema
restore, migration checksum repair, credential replacement, and requests to
decide a pending work item require an authorized recovery/authority process.

## Escalate when

- A source CME event is private or cannot be assigned a verified privacy scope.
- Dispatcher is healthy but a source event is omitted without a documented
  allowlist/filter reason.
- Duplicate source-event rows or conflicting migration checksums are observed.
- A receipt changed an assignment or pending-request state.
- The target of any restore or migration cannot be proven safe.
- A credential/identity mismatch or unexpected listener is present.

Preserve the data and capture evidence; do not guess at a destructive repair.
