<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_IPHONE_DELIVERY.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.1
Purpose: Define local durable mobile push delivery using ntfy and Pushover
Authority: Push transport only; no assignment, approval, or decision authority
Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial mobile delivery contract
Changed: 2026-10-18 UTC | RV-NOTIFICATION-SELECTED-CREDENTIALS-20261018 | Document selected-provider preflight and actual status visibility boundaries
History: Git and .riverview-backups/manifest.jsonl
-->
# iPhone notification delivery

**Task:** RV-IPHONE-NOTIFICATIONS-001
**Component:** `NOTIFICATION-DELIVERY`
**Canonical workflow:** `rv:notification-delivery:iphone-push`
**Source:** `src/riverview_core/notifications/push.py`
**Execution:** A separately supervised Camrui worker reconciles existing
PostgreSQL `attention_notifications`, routes fixed summaries by severity, and
delivers through configured providers. The PostgreSQL queue is local durable
state; it is not a second source of institutional objectives or decisions.

## Contract and guarantees

The manager only consumes notification rows already created by the current CME
dispatcher. It emits fixed server-side summaries, not raw event details or
conversation content. Severity-to-provider routes and event-to-severity mapping
are configuration. Delivery rows are unique by `(notification_id, provider)`;
leases protect concurrent workers; attempts and exponential delays are bounded;
events are append-only. A worker restart recovers expired leases. Exhausted
leases become terminal failures rather than silently exceeding the attempt cap.

The state `accepted` means the provider returned a successful API response. It
does **not** mean an iPhone received, displayed, or announced the notification.
Pushover emergency priority returns a receipt which Riverview polls at a minimum
15-second interval. `acknowledged` is only recorded when Pushover reports a
user acknowledgment; `expired` means the provider's emergency retry window
elapsed. The ntfy publish API has no server-side handset acknowledgment contract.
The dashboard's existing browser receipt remains independent of these states.

If a network timeout happens after a provider accepted a message but before
Riverview persisted that result, a bounded retry can result in a duplicate push.
The local queue deduplicates logical notification/provider work and records a
stable idempotency key, but neither provider is claimed to offer transactional
exactly-once delivery. The fixed notice includes no sensitive source details.

## Providers and iPhone behavior

**ntfy:** Configure only a self-hosted endpoint with authenticated topic access;
the configuration loader rejects `ntfy.sh` and unencrypted non-loopback URLs.
Do not expose an ntfy listener publicly without a separately authorized network
and access-control deployment. The server should enable its auth database,
default access `deny-all`, grant the service account publish access to one
private topic, and grant the phone account read access only to that topic. Keep
the ntfy listener private or reachable only over an independently authorized
TLS/VPN route. For iOS background wake, current ntfy server
documentation describes forwarding an opaque poll request (hashed topic URL,
message ID, and generic text) to an upstream push relay; it does not forward the
notification body. Without that upstream, the app may receive messages later
when it polls. This optional upstream has a third-party metadata dependency and
must be evaluated as part of ntfy server configuration, outside this code.

**Pushover:** Uses the HTTPS message API. `info` maps to normal priority,
`warning` to high priority, and `critical` to emergency priority with configured
retry/expiry bounds (provider constraints: retry at least 30 seconds, expiration
no more than 10,800 seconds). Emergency receipts are persisted and polled for
acknowledgment/expiry. Pushover's API acceptance is not proof of phone display.

On iPhone, install/configure the relevant provider app, allow its iOS
notifications, and subscribe to the private ntfy topic or sign in to Pushover.
Bluetooth audio is handled by iOS: Siri's Announce Notifications can announce
supported third-party app notifications on compatible, paired AirPods/Beats
when the iOS conditions/settings are met. Riverview does not connect to a
headset or guarantee an audible announcement. See [Apple's setup requirements](https://support.apple.com/en-us/102536).

## Configuration and credentials

`deploy/notification-delivery.example.json` defines routes, severity mapping,
retry limits, ntfy endpoint/topic, and credential *names*. It contains no
secrets. systemd imports the provider credential directory using the `provider`
credential namespace. Each regular file under `/etc/riverview/notification/`
becomes a credential named `provider_<filename>` (for example,
`ntfy_token` becomes `provider_ntfy_token`); symlinks are ignored. The sample
configuration uses these names. Startup validates only providers selected by
the configured severity routes: ntfy requires its token; Pushover requires both
its app token and user key. Unselected provider files are not required. A
selected provider with a missing, unreadable, empty, or symlink credential
causes a sanitized startup failure before the delivery manager is constructed.
Pushover app token and user key are separate. ntfy uses an access token for its
private topic. Automated tests use temporary credentials and never call a live
provider.

The service uses existing PostgreSQL `riverview_core` identity and existing
notification data, plus the additive migration `0007_external_push_delivery`.
That migration grants only the notification queue/event/health operations it
needs. It does not change CME source rows, pending Steward decisions, or
assignments. It is explicit and is never run by service startup.

## Validation and limits

Unit tests cover config validation and provider request/response handling with
injected transports. PostgreSQL tests use unique disposable `rvtest_*` schemas
and verify deduplication, retry bounds, expired-lease recovery, audit events,
and Pushover acknowledgment persistence. Production commissioning remains
unverified until the reviewed migration/package is installed, the intended
providers and protected credentials are configured, and a handset test records
provider acceptance separately from actual iPhone display/acknowledgment.

## Runtime status and Steward visibility

The worker records `notification_delivery_health` with `healthy` or `degraded`,
heartbeat and cycle timestamps, a bounded error code, and aggregate counters.
`NotificationDeliveryManager.status()` is a read-only library query and returns
`not_initialized` when no health row exists. It does not calculate `stale` or
`unavailable`; when the worker stops, the last status and timestamp remain in
PostgreSQL. An observer must compare `last_heartbeat_at` with a freshness
threshold. This increment does not expose an authenticated Steward-facing live
status endpoint or dashboard panel. The database projection and systemd journal
are operator diagnostics, not a live Steward view. Component Definition of Done
is therefore **NOT DONE** until a real Steward view, unattended production
recovery evidence, and handset acceptance exist.

See `NOTIFICATION_IPHONE_DELIVERY_COOKBOOK.md` for setup, diagnostics, and
recovery; `NOTIFICATION_IPHONE_DELIVERY_FLOW.md` is generated from the canonical
graph.

## References

- [ntfy publishing API](https://docs.ntfy.sh/publish/)
- [ntfy server access control](https://docs.ntfy.sh/config/#access-control)
- [ntfy self-hosted iOS push configuration](https://docs.ntfy.sh/config/#ios-instant-notifications)
- [Pushover message API](https://pushover.net/api)
- [Pushover receipts API](https://pushover.net/api/receipts)
- [Existing durable Riverview dashboard notification contract](NOTIFICATION_DELIVERY.md)
