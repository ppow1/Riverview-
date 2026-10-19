<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_IPHONE_DELIVERY_COOKBOOK.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.1.1
Purpose: Set up and troubleshoot ntfy/Pushover push delivery without exposing secrets
Authority: Operational diagnosis and local setup only; no decision authority
Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial push recovery cookbook
Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATION-COMMISSIONING-READINESS-001 | Add checksum-pinned operator commissioning and phone acceptance steps
Changed: 2026-10-18 UTC | RV-NOTIFICATION-QUEUE-RETRY-ACCEPTANCE-20261018 | Document disposable PostgreSQL queue/retry acceptance command
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

## Ordered Camrui commissioning procedure

Everything in this section is an operator procedure for a separately authorized
commissioning window. None of these production commands was run for PR #122.
Stop before a database write, secret provisioning, service-file replacement,
release-pointer switch, or service start unless the Steward has authorized that
specific commissioning. Do not change the existing visual notification
dispatcher.

### 1. Select providers and configure the iPhone

Choose one of these routes in `deploy/notification-delivery.example.json` (copy
it to `/etc/riverview/notification-delivery.json`, then edit with `sudoedit`):

| Route | Provider | Phone evidence |
| --- | --- | --- |
| `info` | `ntfy` | ntfy app displays the message; Riverview cannot read a phone acknowledgment. |
| `warning` | `ntfy`, `pushover` | Both provider submissions are tracked independently; confirm the intended duplicate alert on the phone. |
| `critical` | `pushover` | Pushover emergency receipt may become `acknowledged` only after the user acknowledges it in the app. |

For ntfy, the chosen endpoint must be an existing self-hosted ntfy server
reachable from Camrui and the iPhone over an already authorized private or TLS
route. Do not expose a new listener or make its topic anonymous. Create a
dedicated ntfy publishing identity for Camrui and a separate read identity for
the iPhone, with default access denied and access limited to the configured
topic. If no authorized self-hosted endpoint exists, leave ntfy out of every
route; the loader rejects `ntfy.sh`.

For Pushover, the operator needs the application's API token and the user's
account key from the existing Pushover account, plus the Pushover iPhone app
signed into that account with iOS notifications enabled. This procedure does
not purchase an app, subscription, or service. If an account or required app
purchase is missing, stop and obtain that decision separately.

Install the selected provider app on the iPhone, allow iOS notifications, and
subscribe to the exact private ntfy topic or sign in to Pushover. Bluetooth
audio is provided by iOS notification announcement; Riverview does not connect
to Bluetooth. Pair a compatible headset, enable **Settings → Siri (or Apple
Intelligence & Siri) → Announce Notifications** for the provider app, then
confirm audio on the physical phone. Focus, mute, lock, and device support can
affect announcement. A successful provider call is not this confirmation.

### 2. Build and stage the immutable release

After PR #122 is reviewed and integrated, use the exact integrated commit, not
the PR branch head, as `COMMIT`. Run from a clean Riverview checkout:

```bash
COMMIT=<integrated-40-character-commit>
WORKTREE="/tmp/rv-notification-release-$COMMIT"
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)-$$
PACKAGE="/tmp/riverview-notification-delivery-$COMMIT-$RUN_ID.tar.gz"
test ! -e "$WORKTREE" && test ! -e "$PACKAGE"
git worktree add --detach "$WORKTREE" "$COMMIT"
python3 "$WORKTREE/scripts/build_camrui_package.py" "$PACKAGE"
python3 "$WORKTREE/scripts/verify_camrui_package.py" "$PACKAGE"
sha256sum "$PACKAGE"
```

Require the package verifier's `manifest` and `shell_compatibility` fields to
be `PASS`, and `source_commit` to equal `$COMMIT`. From Windows PowerShell 5.1,
the existing `camrui` SSH alias can transfer the package without copying SSH
keys or credentials:

```powershell
# Run from the Riverview repository checkout after fetching the integrated commit.
$Repo = (git rev-parse --show-toplevel).Trim()
$Commit = '<integrated-40-character-commit>'
$RunId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$Worktree = Join-Path $env:TEMP "rv-notification-release-$Commit"
$Package = Join-Path $env:TEMP "riverview-notification-delivery-$Commit-$RunId.tar.gz"
git -C $Repo worktree add --detach $Worktree $Commit
$BuildResult = python (Join-Path $Worktree 'scripts/build_camrui_package.py') $Package
if ($LASTEXITCODE -ne 0) { throw 'Immutable package build failed' }
$VerifyResult = python (Join-Path $Worktree 'scripts/verify_camrui_package.py') $Package | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $VerifyResult.manifest -ne 'PASS' -or
    $VerifyResult.shell_compatibility -ne 'PASS' -or $VerifyResult.source_commit -ne $Commit) {
  throw 'Package verification failed or source commit mismatch'
}
$Hash = (Get-FileHash -Algorithm SHA256 $Package).Hash.ToLowerInvariant()
$RemoteName = [IO.Path]::GetFileName($Package)
ssh.exe -o BatchMode=yes camrui "test ! -e /tmp/$RemoteName"
if ($LASTEXITCODE -ne 0) { throw 'Remote archive path exists or Camrui preflight failed' }
scp.exe $Package "camrui:/tmp/$RemoteName"
if ($LASTEXITCODE -ne 0) { throw 'Package transfer failed' }
ssh.exe -o BatchMode=yes camrui "echo $Hash  /tmp/$RemoteName | sha256sum -c -"
if ($LASTEXITCODE -ne 0) { throw 'Camrui archive checksum verification failed' }
Write-Host "package=$RemoteName sha256=$Hash"
git -C $Repo worktree remove $Worktree
if ($LASTEXITCODE -ne 0) { throw 'Temporary source worktree cleanup failed' }
```

Require package verification to report `manifest=PASS`,
`shell_compatibility=PASS`, and the exact `$Commit`. On Camrui, install only to
a new `/opt/riverview-notification-delivery/releases/$COMMIT` directory; abort
if it already exists. Preserve root ownership and non-writable runtime source,
then verify from the release root:

```bash
COMMIT=<integrated-40-character-commit>
RUN_ID=<UTC-run-id-in-package-name>
RELEASE="/opt/riverview-notification-delivery/releases/$COMMIT"
ARCHIVE="/tmp/riverview-notification-delivery-$COMMIT-$RUN_ID.tar.gz"
EXPECTED_SHA256=<recorded-64-character-package-sha256>
printf '%s  %s\n' "$EXPECTED_SHA256" "$ARCHIVE" | sha256sum -c -
sudo install -d -o root -g root -m 0755 \
  "/opt/riverview-notification-delivery/releases"
sudo mkdir -m 0755 "$RELEASE"
sudo tar --no-same-owner -xzf "$ARCHIVE" \
  -C "$RELEASE"
sudo chown -R root:root "$RELEASE"
sudo find "$RELEASE" \
  -type d -exec chmod 0755 {} +
cd "$RELEASE"
sudo sha256sum -c PACKAGE_SHA256SUMS
test "$(cat SOURCE_COMMIT)" = "$COMMIT"
```

The archive hash printed by `Get-FileHash` must match `$EXPECTED_SHA256`;
the Camrui check proves transfer integrity. Release installation must fail if
the immutable destination already exists.

Before changing `current`, record `readlink -f
/opt/riverview-notification-delivery/current` and the existing unit's checksum
and active state. Keep that predecessor in the commissioning record. Check that
`/usr/bin/python3 -c 'import psycopg'` succeeds and that the immutable release
contains `src/riverview_core/notifications/migrations/0007_external_push_delivery.sql`,
`scripts/run_notification_delivery.py`, and
`deploy/systemd/riverview-notification-delivery.service`.

### 3. Protect provider credentials and the configuration

Create the directory with owner-only access. For each selected provider, run
the following helper once per credential file, substituting only the path and
prompt label. `getpass` disables terminal echo; `O_EXCL` refuses to overwrite
an existing credential. It writes no secret to shell history, command
arguments, or standard output:

```bash
sudo install -d -o root -g root -m 0700 /etc/riverview/notification
sudo python3 -c 'import getpass,os,sys; p=sys.argv[1]; v=getpass.getpass(sys.argv[2]); fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); f=os.fdopen(fd,"w"); f.write(v); f.flush(); os.fsync(f.fileno()); f.close()' "/etc/riverview/notification/ntfy_token" "ntfy publish token: "
sudo python3 -c 'import getpass,os,sys; p=sys.argv[1]; v=getpass.getpass(sys.argv[2]); fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); f=os.fdopen(fd,"w"); f.write(v); f.flush(); os.fsync(f.fileno()); f.close()' "/etc/riverview/notification/pushover_app_token" "Pushover application token: "
sudo python3 -c 'import getpass,os,sys; p=sys.argv[1]; v=getpass.getpass(sys.argv[2]); fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); f=os.fdopen(fd,"w"); f.write(v); f.flush(); os.fsync(f.fileno()); f.close()' "/etc/riverview/notification/pushover_user_key" "Pushover user key: "
```

Run only the commands for selected providers. If a path already exists, do not
overwrite or inspect its contents; stop and use the established credential
rotation process. Verify metadata only:

```bash
sudo stat -c '%U:%G %a %n' /etc/riverview/notification/*
```

The output must show `root:root 600`. Install the copied JSON as
`root:riverview` mode `0640` so the service can read its non-secret routes:

```bash
sudo install -o root -g riverview -m 0640 \
  /opt/riverview-notification-delivery/releases/$COMMIT/deploy/notification-delivery.example.json \
  /etc/riverview/notification-delivery.json
sudoedit /etc/riverview/notification-delivery.json
sudo -u riverview test -r /etc/riverview/notification-delivery.json
```

Replace the `.example.invalid` endpoint and topic, remove unselected provider
routes, and make `LoadCredential` entries match only selected providers. Keep
the `pgpass` entry. Validate without displaying secrets:

```bash
sudo -u riverview env \
  PYTHONPATH="/opt/riverview-notification-delivery/releases/$COMMIT/src" \
  /usr/bin/python3 -c 'from riverview_core.notifications.push import PushConfig; c=PushConfig.load("/etc/riverview/notification-delivery.json"); print({"routes":c.routes,"retry_limit":c.retry_limit})'
```

### 4. Backup, restore-check, and apply migration 0007

Follow the protected full-dump and disposable-restore commands in
[`RIVERVIEW_OPERATIONS_COOKBOOK.md`](RIVERVIEW_OPERATIONS_COOKBOOK.md),
section 3.
Do not migrate unless checksum, archive listing, disposable restore, and
pre-migration schema/count comparison all pass. Confirm notification migration
0006 is present and its checksum matches the release source; 0007 is absent.
Read the ledger without selecting unrelated data:

```bash
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c \
  "SELECT version,checksum FROM riverview_dev.schema_migrations WHERE version IN ('0006_durable_notifications','0007_external_push_delivery') ORDER BY version;"
sha256sum "$RELEASE/src/riverview_core/notifications/migrations/0006_durable_notifications.sql" \
  "$RELEASE/src/riverview_core/notifications/migrations/0007_external_push_delivery.sql"
```

From the verified release, the repository's checksum-pinned runner applies the
notification migration directory atomically and rejects drift. The expected
result is only `0007_external_push_delivery` because 0006 is a prerequisite:

```bash
MIGRATIONS_DIR="$RELEASE/src/riverview_core/notifications/migrations"
sudo -n -u postgres env \
  PYTHONPATH="$RELEASE/src" MIGRATIONS_DIR="$MIGRATIONS_DIR" \
  /opt/riverview-core/.venv/bin/python - <<'PY'
import os
from riverview_core.postgres_migrations import apply_migrations
print(apply_migrations("dbname=riverview user=postgres", schema="riverview_dev",
                       migrations_dir=os.environ["MIGRATIONS_DIR"]))
PY
```

Verify the recorded checksum against the release file and inspect effective
`riverview_core` table/column grants from `information_schema` before service
installation. Abort on an unexpected migration, absent 0006, checksum mismatch,
or broader privilege than migration 0007 specifies. Never apply this from
service startup. A compact privilege check is:

```sql
BEGIN READ ONLY;
SELECT table_name,privilege_type,column_name
FROM information_schema.column_privileges
WHERE table_schema='riverview_dev' AND grantee='riverview_core'
  AND table_name IN ('attention_notifications','events','notification_delivery_queue',
                     'notification_delivery_events','notification_delivery_health',
                     'notification_delivery_settings')
ORDER BY table_name,privilege_type,column_name;
ROLLBACK;
```

### 5. Install and validate the separate service

Capture a protected predecessor copy of
`/etc/systemd/system/riverview-notification-delivery.service` if it exists, the
active release pointer, and the unit/service state. If an unreviewed unit or
unexpected current pointer already exists, stop. The service template runs as
`riverview`, reads the immutable release via `/opt/riverview-notification-delivery/current`,
uses the existing `/etc/riverview/pgpass`, and does not touch the notification
dispatcher.

The following captures a unique protected filesystem rollback record before
any systemd or release-pointer change:

```bash
BACKUP_DIR=$(sudo -n mktemp -d /var/lib/riverview/notification-delivery.XXXXXXXX)
sudo chmod 0700 "$BACKUP_DIR"
CURRENT=/opt/riverview-notification-delivery/current
UNIT=/etc/systemd/system/riverview-notification-delivery.service
PREVIOUS_RELEASE=$(readlink -f "$CURRENT" 2>/dev/null || true)
printf '%s\n' "$PREVIOUS_RELEASE" | sudo tee "$BACKUP_DIR/current-target.txt" >/dev/null
systemctl show riverview-notification-delivery.service \
  -p LoadState -p ActiveState -p SubState -p UnitFileState \
  | sudo tee "$BACKUP_DIR/unit-state.txt" >/dev/null
if sudo test -f "$UNIT"; then
  sudo cp -a "$UNIT" "$BACKUP_DIR/unit.predecessor"
  sudo sha256sum "$BACKUP_DIR/unit.predecessor" \
    | sudo tee "$BACKUP_DIR/unit.predecessor.sha256" >/dev/null
fi
```

Record `BACKUP_DIR`, its permissions, the prior target, and unit state in the
commissioning record. Preserve the configuration predecessor similarly before
replacing `/etc/riverview/notification-delivery.json`; never copy provider
credential contents into this report.

After approval, switch the dedicated release pointer atomically by creating a
unique sibling symlink then renaming it with `mv -Tf`; install the unit
`root:root 0644`; validate it; and daemon-reload. Confirm `systemd-analyze
verify` and `systemctl show` before starting. Start only
`riverview-notification-delivery.service` after confirming every configured
`LoadCredential` source exists and is `root:root 0600`. Initially leave it
disabled unless persistent boot activation is separately included in the
Steward's commissioning approval. On startup, require a fresh healthy row in
`notification_delivery_health`, not merely `systemd active`.

For first installation, after writing down the exact previous pointer and unit
state, the reviewed file operations are:

```bash
UNIT=/etc/systemd/system/riverview-notification-delivery.service
ROOT=/opt/riverview-notification-delivery
NEXT="$ROOT/.current-$COMMIT"
CURRENT="$ROOT/current"
test ! -e "$NEXT" && test -d "$RELEASE"
if [ -e "$CURRENT" ] && [ ! -L "$CURRENT" ]; then
  echo "current is not a symlink; stop" >&2; exit 1
fi
sudo ln -s "$RELEASE" "$NEXT"
sudo mv -Tf "$NEXT" "$CURRENT"
sudo install -o root -g root -m 0644 \
  "$RELEASE/deploy/systemd/riverview-notification-delivery.service" "$UNIT"
sudo systemd-analyze verify "$UNIT"
sudo systemctl daemon-reload
```

These commands do not start or enable the service. Before applying, check that
`$RELEASE` is the exact verified directory and `$NEXT` does not exist. Record
the prior `readlink -f "$CURRENT"` output and protect a byte-exact copy of an
existing unit/config before replacement. If first install, the recorded prior
pointer and unit must say absent; never infer that from a missing command
output.

Only after the migration, credential, config, package, and systemd checks pass
and the Steward has approved activation, start this unit (do not enable it
unless boot activation was also authorized):

```bash
sudo systemctl start riverview-notification-delivery.service
systemctl is-active riverview-notification-delivery.service
```

Read-only checks after start:

```bash
systemd-analyze verify /etc/systemd/system/riverview-notification-delivery.service
systemctl show riverview-notification-delivery.service \
  -p ActiveState -p SubState -p MainPID -p NRestarts
journalctl -u riverview-notification-delivery.service -n 80 --no-pager
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c \
  "BEGIN READ ONLY; SELECT status,last_heartbeat_at,last_cycle_at,last_error_code FROM riverview_dev.notification_delivery_health WHERE service_id='notification.delivery.v1'; SELECT state,provider,severity,count(*) FROM riverview_dev.notification_delivery_queue GROUP BY state,provider,severity ORDER BY state,provider,severity; ROLLBACK;"
```

### 6. Non-destructive phone acceptance and severity tests

These tests create only explicitly labeled, unassigned CME monitor test events,
their derived attention notifications, and push-delivery audit rows. They do not
create or alter assignments, objectives, decisions, or authority. Each test
row is durable; delivery events are append-only. Retain them as test evidence.
Run only in a Steward-
approved acceptance window with the phone owner ready to receive notices.

Use the following `psql` block once, in the approved acceptance window. It
generates a unique run ID and adds one explicitly labeled event for each
severity. The rows are deliberately marked with
`service_id='notification_acceptance_test'` and `details.test_only=true`:

```bash
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview <<'SQL'
BEGIN;
SELECT replace(gen_random_uuid()::text,'-','') AS run_id \gset
INSERT INTO riverview_dev.cme_monitor_events
    (event_key,service_id,assignment_id,event_type,details)
VALUES
    ('iphone-test:' || :'run_id' || ':info','notification_acceptance_test',NULL,
     'attention_resolved',jsonb_build_object('test_only',true,'test_id',:'run_id' || ':info')),
    ('iphone-test:' || :'run_id' || ':warning','notification_acceptance_test',NULL,
     'assignment_stalled',jsonb_build_object('test_only',true,'test_id',:'run_id' || ':warning')),
    ('iphone-test:' || :'run_id' || ':critical','notification_acceptance_test',NULL,
     'monitor_failed',jsonb_build_object('test_only',true,'test_id',:'run_id' || ':critical'))
RETURNING event_key,event_id;
COMMIT;
\echo Notification test run ID: :run_id
SQL
```

Commit the test rows (do not delete them). The existing
`riverview-notification-dispatcher.service` projects
these unassigned supported events into `attention_notifications`. The new
delivery worker then applies configured severity routing. Wait for the
dispatcher poll and the configured push poll interval before diagnosing a
missing row.

Set `RUN_ID` in the read-only query below to the value printed by `psql`:

Correlate test rows without reading message text or provider receipt values:

```sql
BEGIN READ ONLY;
SELECT e.event_key,e.event_id,n.notification_id,q.delivery_id,
       q.provider,q.severity,q.state,q.attempt_count,q.max_attempts,
       q.last_error_code,q.provider_accepted_at,q.acknowledged_at
FROM riverview_dev.cme_monitor_events e
JOIN riverview_dev.attention_notifications n ON n.source_event_id=e.event_id
JOIN riverview_dev.notification_delivery_queue q ON q.notification_id=n.notification_id
WHERE e.event_key LIKE 'iphone-test:<RUN_ID>:%'
ORDER BY e.event_key,q.provider;
ROLLBACK;
```

Check that each configured provider has exactly one row per notification and
that provider/severity pairs match the selected routes. `accepted` proves only
that the provider API accepted the request. Confirm app display directly on the
iPhone. For a Pushover `critical` test, wait until the user is ready, then
acknowledge the emergency in the Pushover app; allow the receipt poll interval
and verify `state='acknowledged'` plus non-null `acknowledged_at`. Do not run an
emergency test as a routine health check. ntfy has no corresponding handset
acknowledgment signal.

Retry and lease-recovery tests belong to the disposable PostgreSQL suite; do
not create a production provider outage just to force a retry. The queue/retry
acceptance case creates a unique schema, persists one eligible notice and one
provider delivery, observes a bounded provider failure and scheduled retry,
creates a fresh worker instance, then verifies the same delivery and
idempotency key are accepted exactly once. Provider acceptance does not prove
handset delivery. Run the focused suite against an ephemeral PostgreSQL 16
cluster with:

```bash
pg_virtualenv -v 16 bash -c 'export PYTHONPATH="$PWD/src"; export RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER password=$PGPASSWORD"; pytest -q tests/test_notification_push.py tests/test_notifications.py'
```

This command starts and drops a disposable cluster; it does not connect to the
Camrui production database. The queue/retry test must report PASS rather than
SKIP. The prior isolated
acceptance command and expected counts are in
[`RV-IPHONE-NOTIFICATIONS-001_REVISION_RECORD.md`](../development/RV-IPHONE-NOTIFICATIONS-001_REVISION_RECORD.md).

### 7. Rollback

If a provider or new service fails, stop only
`riverview-notification-delivery.service`. Restore the recorded predecessor
`current` pointer with a unique sibling symlink plus atomic `mv -Tf`; restore
the protected previous unit/config only if this commissioning replaced them;
then daemon-reload. Restart this notification delivery unit only if it was
previously active and its predecessor is known healthy. Leave
`riverview-notification-dispatcher.service`, dashboard, CME, Comms4, and all
other services untouched. Keep migration 0007, its tables, outbox rows, and
append-only events; never roll back by dropping schema objects or deleting
delivery history. Record the failed code, release IDs, and restored pointer.

Use the exact recorded predecessor values, not a guessed release:

```bash
sudo systemctl stop riverview-notification-delivery.service || true
# If PREVIOUS_RELEASE was present:
sudo ln -s "$PREVIOUS_RELEASE" "/opt/riverview-notification-delivery/.rollback-$COMMIT"
sudo mv -Tf "/opt/riverview-notification-delivery/.rollback-$COMMIT" \
  /opt/riverview-notification-delivery/current
# If this was first install instead, remove only the new current symlink:
# sudo rm /opt/riverview-notification-delivery/current
# If a protected predecessor existed:
# sudo install -o root -g root -m 0644 "$BACKUP_DIR/unit.predecessor" \
#   /etc/systemd/system/riverview-notification-delivery.service
# If this was first install instead:
# sudo rm /etc/systemd/system/riverview-notification-delivery.service
# Restore the protected config predecessor if it was replaced, then:
sudo systemctl daemon-reload
```

The comments are alternatives: execute only the branch matching the recorded
pre-change state. Restore the previous unit/config from the protected backup
before daemon reload. Do not restart or enable the predecessor unless it was
active before this change.

The Steward must explicitly approve the fresh backup/restore, migration 0007,
provider credentials/configuration, release/unit installation, service start
(and boot enablement if desired), and test messages. Any public or network
exposure for ntfy is a separate decision. No approval for those production
actions is implied by this runbook.

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
