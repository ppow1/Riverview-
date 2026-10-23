<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_IPHONE_UPSTREAM_RELAY.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.0
Purpose: Operate and verify iOS background push relay for the existing private ntfy service
Authority: Notification transport only; no assignment, approval, or decision authority
Changed: 2026-10-24 UTC | RV-IPHONE-NTFY-UPSTREAM-001 | Record ntfy iOS poll relay commissioning and recovery
History: Git; protected Camrui configuration backup at /var/backups/riverview/ntfy-upstream-relay
-->
# iPhone background notification relay

## Configuration

Camrui runs ntfy v2.32.0 on `127.0.0.1:2586`, behind the existing authenticated
HTTPS Nginx `/ntfy/` route. Its iPhone subscription remains on the existing
`https://192.168.1.155/ntfy` server URL and private read-only topic. The
write-only Riverview publisher credentials and topic are held in root-only
files under `/etc/riverview/notification/`.

For iOS background wake, the ntfy server forwards a poll request to
`https://ntfy.sh`. That upstream request contains only the poll ID and a hash of
the self-hosted topic URL; the private message body remains on Camrui. The iOS
app receives the APNS notification from ntfy.sh and fetches the actual content
from the existing Camrui HTTPS subscription. No upstream access token is set;
the public relay does not require one at the configured rate. This introduces
no paid service.

The operator-hosted name `ntfy.home.arpa` is not needed for this upstream
protocol and is not substituted for `ntfy.sh`: the latter must be an
APNS-connected upstream. The existing IP URL and trusted LAN CA are retained so
the phone's current subscription is not silently replaced. A future hostname
migration would need a trusted certificate with that DNS SAN and an explicit
phone-side subscription update.

## Test command

On Camrui, run:

```sh
sudo /usr/local/sbin/riverview-ntfy-phone-test
```

It publishes one clearly titled, high-priority test to the existing topic using
the existing root-protected publisher token and topic files. It does not print
either value. High priority asks the app to alert audibly, subject to iOS
permissions, Focus/silent state, and the app's sound settings. The command
reports the local ntfy message ID only; it does not claim upstream or handset
delivery.

## Verification boundaries

Server checks establish all of the following separately: ntfy is active and
healthy; its configured upstream endpoint resolves and has valid TLS; the
existing HTTPS route reaches the loopback service; and a local publication is
accepted with the existing publisher credential. After the test command,
inspect `journalctl -u ntfy.service --since ...` for upstream errors. A local
HTTP 200, an ntfy message ID, or clean logs alone do not prove that APNS
delivered the push, that the notification appeared, or that sound played.

The Steward must confirm the notification while ntfy is backgrounded or closed,
then report separately whether the phone displayed it and played sound. The
ntfy server has no handset acknowledgment API. Phone permission, Focus, mute,
network state, and iOS notification settings remain handset-side factors.

## Rollback and recovery

The server configuration backup and checksum are kept under
`/var/backups/riverview/ntfy-upstream-relay/<UTC-run-id>/`. To disable only the
relay, restore the backed-up `/etc/ntfy/server.yml` byte-for-byte, verify its
recorded SHA-256, then restart only `ntfy.service` and check
`http://127.0.0.1:2586/v1/health`. Do not alter the Nginx route, auth database,
topic, credentials, dispatcher, or dashboard. If ntfy fails to restart, restore
the exact backup and verify the service and existing HTTPS route before further
diagnosis.

The upstream relay is an optional metadata wake path. Removing it leaves local
message publication and topic access intact; iOS may then receive messages only
on a later poll, with delays potentially lasting hours while the app is idle.
