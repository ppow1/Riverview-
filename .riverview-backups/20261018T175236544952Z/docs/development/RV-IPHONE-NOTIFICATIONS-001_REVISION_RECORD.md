<!--
Riverview~ Controlled Document
File: docs/development/RV-IPHONE-NOTIFICATIONS-001_REVISION_RECORD.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.0
Purpose: Record implementation scope and reproducible validation for iPhone push delivery
Authority: Development evidence only; no production commissioning claim
Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial implementation record
History: Git + .riverview-backups/manifest.jsonl
-->
# RV-IPHONE-NOTIFICATIONS-001 — implementation record

**Repository:** `ppow1/Riverview-`
**Branch:** `codex/iphone-notification-manager-20261018`
**Base:** `94592f26` — `codex/riverview-final-reasoning-integration-20261018`
**Target:** Camrui source and isolated validation only. No production service,
database, credential, network route, or iPhone was changed or tested.

## Recovered predecessor and reuse

The prior Python notification implementation was found in the local historical
development checkout `Riverview-SSH-Runbooks` at source commit
`ccefc034c7ae9e812948c73fd2272b30355554f1`, file
`src/riverview/notifications_audio.py`. It consumes the older `NotificationStore`
and delegates to an Estate `WindowsPresenter` using Windows `winsound` and
PowerShell/System.Speech. It marks a notice delivered only after the presenter
returns successfully and does not acknowledge or accept it. This is an audio
adapter for an interactive Windows session, not an iPhone push implementation;
it was read for behavioral recovery and left unchanged.

The current Camrui component already has durable CME-to-dashboard notice
projection, privacy filtering, receipt events, and PostgreSQL migration 0006.
This implementation adds a provider outbox consuming those same
`attention_notifications`. It does not replace the dispatcher, dashboard
receipts, assignment records, or the old Windows presenter.

## Implementation

- Added the `notification_delivery_queue`, append-only delivery event ledger,
  operational health projection, and migration-time enable cutoff in explicit
  notification migration 0007.
- Added severity routing, configurable event mapping, deduplicated PostgreSQL
  outbox, bounded exponential retries, `SKIP LOCKED` claim leases, worker restart
  recovery, and sanitized state reporting.
- Added HTTPS ntfy and Pushover API adapters. Provider credentials are read from
  systemd `LoadCredential` files and are absent from configuration templates.
- Pushover critical notices use bounded emergency retry parameters and durable
  receipt polling for provider-reported acknowledgment or expiry. ntfy has no
  server-side phone-acknowledgment state in this contract.
- A provider HTTP/API success is recorded as `accepted`; it does not claim the
  iPhone displayed or announced the notice. Ambiguous timeouts may cause a
  bounded duplicate because the provider APIs do not participate in Riverview's
  database transaction.
- Added a separate, inactive systemd unit template and protected-credential
  setup/recovery instructions. No service was installed or enabled.
- Added a versioned canonical process graph and generated graph views.

## Verification

Commands ran from the isolated worktree with a temporary PostgreSQL 16 cluster.
The cluster was dropped by `pg_virtualenv` after each run.

| Command | Result |
| --- | --- |
| `pg_virtualenv bash -c 'export RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER"; export PYTHONPATH=.:src:scripts; pytest -q tests/test_notification_push.py tests/test_notifications.py'` | 16 passed; 0 failed; no real provider credentials/network calls. |
| `pg_virtualenv bash -c 'export RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER"; export PYTHONPATH=.:src:scripts; pytest -q tests/'` | 632 passed; 0 failed; completed in 402.88 seconds. |
| `python3 -m compileall -q src/riverview_core/notifications scripts/run_notification_delivery.py tests/test_notification_push.py` | Passed. |
| `systemd-analyze verify deploy/systemd/riverview-notification-delivery.service` | Passed. |
| `python3 scripts/process_graph.py validate` / `generate` / `check` | Passed; 23 graphs, 576 nodes. |
| `python3 scripts/revision_control.py check --baseline /tmp/rv-iphone-baseline-inventory.json` | Passed; all changed existing files have revision increments and verified predecessor backups. |
| `git diff --check` | Passed. |

The PostgreSQL tests verify routing, duplicate reconciliation, provider
acceptance versus unverified handset state, retry scheduling and terminal
failure, lease recovery using a newly constructed manager, Pushover emergency
acknowledgment persistence, and least-column runtime grants. Provider HTTP
payloads use an injected fake transport and temporary test-only credential
files; no provider was called.

An initial `pytest -q` command also attempted to collect archived tests under
`docs/history/` and failed at collection because that command omitted the
repository root/scripts from `PYTHONPATH`. The supported repository suite
command above scopes collection to `tests/` and passed. The archive collection
failure did not execute test cases and did not modify repository files.

## Acceptance and remaining work

**Source implementation:** implemented and isolated-test verified.
**Production migration/service:** not installed or activated.
**Provider/phone delivery:** not live-tested; no ntfy or Pushover credentials
were provisioned and no phone was used.
**Bluetooth audio:** depends on the iOS app notification settings and supported
headset/Siri Announce Notifications; Riverview cannot confirm audible output.

Production commissioning would require a reviewed merge, protected provider
credentials, private authenticated ntfy service configuration if selected,
explicit migration approval, immutable package and rollback preparation, and a
real iPhone acceptance test. Do not treat provider `accepted` as handset
delivery evidence.
