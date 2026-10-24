<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_IPHONE_UPSTREAM_RELAY.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.1
Purpose: Operate and verify iOS background push relay for the existing private ntfy service
Authority: Notification transport only; no assignment, approval, or decision authority
Changed: 2026-10-24 UTC | RV-IPHONE-NTFY-UPSTREAM-001 | Record ntfy iOS poll relay commissioning and recovery
Changed: 2026-10-24 UTC | RV-IPHONE-NTFY-HOSTNAME-001 | Align iOS poll hash with a root-host subscription and add LAN DNS/TLS route
History: Git; protected Camrui configuration backup at /var/backups/riverview/ntfy-upstream-relay
-->
# iPhone background notification relay

## Configuration

Camrui runs ntfy v2.32.0 on `127.0.0.1:2586`. The original authenticated
HTTPS `/ntfy/` route remains in place for existing clients. The relay-compatible
iOS endpoint is the new authenticated HTTPS virtual host
`https://ntfy.home.arpa` with no path prefix. Both routes lead to the same
service, private topic, and auth database. The write-only Riverview publisher
token and topic remain in root-only files under `/etc/riverview/notification/`.

For iOS background wake, the ntfy server forwards a poll request to
`https://ntfy.sh`. That upstream request contains only the poll ID and a hash of
the self-hosted topic URL; the private message body remains on Camrui. The iOS
app receives the APNS notification from ntfy.sh and fetches the actual content
from Camrui. No upstream access token is set; the public relay does not require
one at the configured rate. This introduces no paid service.

The hostname is required to make the iOS poll hash match. ntfy v2.32.0 hashes
`base-url + "/" + topic`; it rejects a path in `base-url`. The old app URL
`https://192.168.1.155/ntfy` includes a path that Nginx strips, so its hash
cannot match the server's poll URL. Camrui now uses
`base-url: "https://ntfy.home.arpa"` and serves that DNS name at the root of a
dedicated TLS virtual host. Keep the old `/ntfy/` route and subscription while
adding the same private topic and read-only credentials to the new hostname;
remove the old subscription only after the new one passes phone acceptance.

The upstream remains `https://ntfy.sh`; it is not replaced by the local
hostname because it must be connected to APNS. `ntfy.home.arpa` resolves to
`192.168.1.155` through Camrui's `systemd-resolved` LAN listener. The router's
DNS at `192.168.1.254` currently returns NXDOMAIN for this local name. For the
phone-side test, set the Riverview Wi-Fi DNS server to `192.168.1.155` (only;
remove alternate DNS entries that could answer the name differently). The
LAN-only firewall allows TCP/UDP DNS from `192.168.1.0/24` and loopback only.
The hostname certificate has SAN `ntfy.home.arpa` and is signed by the existing
Riverview Camrui LAN Root CA; the phone must continue to trust that CA.

**Current phone state:** the server-side alias, DNS listener, trusted TLS route,
and matching ntfy `base-url` are deployed. The Steward has not yet changed the
iPhone's Wi-Fi DNS or added the new hostname subscription, so background wake
and sound remain unverified. The earlier test sent before this hostname
correction is not a valid handset acceptance result.

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
healthy; `ntfy.home.arpa` resolves from the LAN listener to Camrui; the DNS SAN
certificate verifies under the existing LAN CA; the root HTTPS virtual host
and old `/ntfy/` route both reach the loopback service; and a local publication
is accepted with the existing publisher credential. After the acceptance test,
inspect `journalctl -u ntfy.service --since ...` for upstream errors. A local
HTTP 200, an ntfy message ID, or clean logs alone do not prove that APNS
delivered the push, that the notification appeared, or that sound played.

After setting Wi-Fi DNS to Camrui, add the existing topic in the ntfy app under
`https://ntfy.home.arpa`, using its existing read-only credentials. Keep the
old subscription until this one is confirmed. Then have the Steward background
or close ntfy, run the test command on Camrui, and report separately whether the
phone displayed the notification and played sound. The ntfy server has no
handset acknowledgment API. Phone permission, Focus, mute, network state, and
iOS notification settings remain handset-side factors.

## Rollback and recovery

The pre-hostname configuration and checksum are under
`/var/backups/riverview/ntfy-upstream-relay/20261024T000423Z-hostname/`. To roll
back only the hostname migration, restore its exact predecessors for
`/etc/ntfy/server.yml`, `/etc/nginx/sites-available/riverview-lan`,
`/etc/nginx/conf.d/00-riverview-origin.conf`, `/etc/nftables.conf`, `/etc/hosts`,
and `/etc/riverview/pki/lan-ca.srl`; remove the added resolver drop-in and the
new `ntfy-home-arpa` certificate/key; validate with `nginx -t` and `nft -c -f
/etc/nftables.conf`; then reload Nginx, nftables, systemd-resolved, and restart
ntfy. Verify the old HTTPS `/ntfy/` route, loopback health, and dispatcher. This
restores the previous IP `base-url` while retaining the upstream relay setting.
To disable the upstream relay itself, additionally restore the earlier backup
under `/var/backups/riverview/ntfy-upstream-relay/20261023T235658Z/` and restart
only `ntfy.service`. Never change the auth database, topic, publisher/reader
credentials, dispatcher, or dashboard during rollback.

The upstream relay is an optional metadata wake path. Removing it leaves local
message publication and topic access intact; iOS may then receive messages only
on a later poll, with delays potentially lasting hours while the app is idle.
