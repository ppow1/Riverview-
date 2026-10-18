<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_IPHONE_DELIVERY_COOKBOOK.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.0
Purpose: Set up and troubleshoot ntfy/Pushover push delivery without exposing secrets
Authority: Operational diagnosis and local setup only; no decision authority
Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial push recovery cookbook
History: Git and .riverview-backups/manifest.jsonl
-->
# iPhone push delivery setup and troubleshooting

**Component:** NOTIFICATION-DELIVERY · **Task:** RV-IPHONE-NOTIFICATIONS-001
**Graph:** `rv:notification-delivery:iphone-push`
**Production status:** Source-only in this assignment; no migration, credentials,
service installation, or provider calls have been made.

## Setup after separately authorized commissioning

1. Choose the private self-hosted ntfy URL and topic. Keep the listener private
   or behind authenticated TLS access. Do not use `ntfy.sh` as the service URL.
   On the ntfy server, enable its auth DB (`auth-file` or `database-url`), set
   `auth-default-access: deny-all`, and grant the publishing service and iPhone
   distinct least-privilege access to the exact private topic. Do not grant
   anonymous `everyone` access.
   If relying on ntfy iOS background wake, evaluate its optional upstream relay
   metadata behavior and configure `upstream-base-url` on the ntfy server only
   through that server's own reviewed deployment process.
2. Configure the iPhone app for the self-hosted server and private topic. Enable
   iOS notifications. For headset audio, pair the desired Bluetooth headset and
   enable iOS **Settings → Siri (or Apple Intelligence & Siri) → Announce
   Notifications** for the provider app where supported. Test the phone itself.
3. Create the protected JSON config from
   `deploy/notification-delivery.example.json`; replace the example URL/topic
   and severity routes. Do not commit the instance-specific config.
4. Place ntfy access token, Pushover application token, and Pushover user key in
   separate root-controlled files matching the names in the systemd template.
   Never put secret values in command arguments, source, or journal output.
5. Build an immutable release containing the source and migration 0007. Apply
   migrations only through Riverview's backup, disposable-restore, and reviewed
   migration procedure. Inspect the migration's narrow `riverview_core` grants.
6. Install the service unit and config, validate the effective unit and
   protected credential ownership/modes, then start only after a reviewed
   deployment authorization. Test a harmless notice and observe provider
   acceptance, iPhone display, headset announcement (if configured), and
   Pushover emergency acknowledgment as separate evidence.

The systemd unit template expects credentials named `pgpass`, `ntfy_token`,
`pushover_app_token`, and `pushover_user_key`. If a provider is intentionally
not configured, remove only that provider's `LoadCredential` line and ensure no
severity route selects it before enabling the unit. This source assignment does
not install or activate the unit.

## Read-only diagnostics

After commissioning, inspect without printing credentials or notification
message bodies:

```sh
systemctl show riverview-notification-delivery.service \
  -p ActiveState -p SubState -p MainPID -p NRestarts
journalctl -u riverview-notification-delivery.service -n 80 --no-pager
```

Use a read-only PostgreSQL transaction with the established secured service
credential mechanism:

```sql
BEGIN READ ONLY;
SELECT version, checksum FROM riverview_dev.schema_migrations
 WHERE version LIKE '0007_%';
SELECT state, provider, severity, count(*)
FROM riverview_dev.notification_delivery_queue GROUP BY state,provider,severity;
SELECT event_type, count(*) FROM riverview_dev.notification_delivery_events
 GROUP BY event_type ORDER BY event_type;
SELECT status,last_heartbeat_at,last_cycle_at,last_error_code,
       notices_scanned,deliveries_queued,provider_accepted,emergency_acknowledged
FROM riverview_dev.notification_delivery_health
WHERE service_id='notification.delivery.v1';
ROLLBACK;
```

Do not select `title`, `message`, credentials, or Pushover receipt contents in
general status evidence. Provider receipt identifiers are protected operational
data and should be queried only during an authorized individual incident.

## State interpretation and recovery

| Signal | Meaning | Safe response |
| --- | --- | --- |
| queue rows stay `queued` | No provider was claimed yet; routes/worker/config may be absent. | Check unit, config presence, and queue age. |
| `retry` | A provider call failed and a bounded retry is scheduled. | Inspect fixed error codes and provider/network health. |
| `accepted` | Provider API accepted the request. Handset display is unknown. | Check the provider app and phone; do not report delivery from HTTP alone. |
| `acknowledged` | Pushover receipt API reports user acknowledgment of an emergency notice. | Preserve receipt/event history; this does not authorize an institutional action. |
| `expired` | Pushover emergency retry interval ended without acknowledgment. | Escalate through existing Riverview attention procedures. |
| `failed` | Retry budget ended or a lease expired at its attempt limit. | Preserve row/events, inspect sanitized failure code, then use existing revalidation/requeue governance if a new notification is warranted. |
| health `degraded` | The worker recorded a failed cycle. | Check PostgreSQL, migration, credential file metadata, and provider reachability before restarting this unit alone. |

Retries are bounded and use increasing delays capped by configuration. If a
worker dies mid-request, its lease expires; the row is retried only within its
attempt budget. A provider may have accepted a request before a client timeout,
so duplicates remain possible across that ambiguous boundary. Stable internal
keys and notice identifiers make duplicates traceable but cannot create
provider-side exactly-once guarantees.

Rollback removes the new unit/release pointer only after stopping this
notification delivery unit. Keep migration 0007 and its durable records; do not
drop tables or delete events as rollback. The existing dashboard notification
dispatcher and visual receipt path are independently managed and must remain
unchanged.
