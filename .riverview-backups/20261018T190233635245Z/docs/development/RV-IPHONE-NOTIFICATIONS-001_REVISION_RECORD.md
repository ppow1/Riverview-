<!--
Riverview~ Controlled Document
File: docs/development/RV-IPHONE-NOTIFICATIONS-001_REVISION_RECORD.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.2
Purpose: Record implementation scope and reproducible validation for iPhone push delivery
Authority: Development evidence only; no production commissioning claim
Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial implementation record
Changed: 2026-10-18 UTC | RV-NOTIFICATION-SELECTED-CREDENTIALS-20261018 | Record reviewed C1 remediation and scoped acceptance evidence
Changed: 2026-10-18 UTC | RV-NOTIFICATION-SELECTED-CREDENTIALS-20261018 | Append full isolated suite result: 640 passed
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

## C1 reviewed remediation — selected provider credential startup

**Scope:** Existing PR #122 only, branch
`codex/iphone-notification-manager-20261018`. This correction does not alter the
database migrations, authority, provider credentials, production services, or
other residents' work.

The pre-remediation systemd unit unconditionally named all three provider
credential files, while the operator procedure allowed ntfy-only or Pushover-
only configuration. Since a missing `LoadCredential` source fails unit setup,
the documented single-provider install could not start. The corrected unit
imports the protected provider directory with ID `provider`; systemd names each
regular file `provider_<filename>`. The application validates only credentials
for providers selected by configured severity routes before it constructs the
delivery manager. A selected missing/empty/unreadable/symlink credential returns
exit code 2 and a fixed sanitized `failure_code`; no credential value/path is
logged. Unselected provider credentials are not required. PostgreSQL `pgpass`
remains a separate mandatory credential.

### Evidence

The original PR #122 head `79483fa41a3f4c20bd2d488789d6337c28191af7` had
GitHub CI run 39145769868 pass: 635 passed, 3 skipped, 23 graphs / 576 nodes,
and revision checks passed. The prior isolated PostgreSQL 16 notification test
run recorded in issue #120 comment 6252405149 passed 19 tests. These are
pre-remediation baseline evidence, not validation of the change below.

| Command on this remediation worktree | Result |
| --- | --- |
| `PYTHONPATH=.:src:scripts pytest -q tests/test_notification_push.py -k 'startup or systemd_unit_imports'` | 5 passed, 12 deselected; ntfy-only, Pushover-only, both selected-missing cases, and unit credential mapping. |
| `pg_virtualenv bash -c 'export RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER"; export PYTHONPATH=.:src:scripts; pytest -q tests/test_notification_push.py tests/test_notifications.py'` | 24 passed on disposable PostgreSQL 16; temporary cluster dropped afterward; no live provider call. |
| `systemd-analyze verify deploy/systemd/riverview-notification-delivery.service` | Passed with directory credential import. |
| `python3 -m compileall -q src/riverview_core/notifications scripts/run_notification_delivery.py tests/test_notification_push.py` | Passed. |
| `python3 scripts/process_graph.py validate` / `check` | Passed; 23 graphs, 580 nodes; selected-credential startup and recovery paths registered. |
| `python3 scripts/revision_control.py check --baseline /tmp/rv-iphone-baseline-inventory.json` | Passed; changed existing files have incremented revisions and restorable predecessor backups. |
| `pg_virtualenv bash -c 'export RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER"; export PYTHONPATH=.:src:scripts; pytest -q tests/'` | 640 passed in 559.73 seconds on disposable PostgreSQL 16; cluster dropped afterward. |

### Remaining blockers and status

The structured source-only blocker register is in
`docs/components/NOTIFICATION_IPHONE_DELIVERY_COOKBOOK.md`. It records the
commissioning authorization, selected-provider credentials, phone-side
acceptance, and missing Steward-facing live view, including detection, owner,
authority, timeout/state, alert destination, resume condition, and evidence.

The health projection and `NotificationDeliveryManager.status()` are internal
read-only diagnostics. They report `not_initialized`, `healthy`, or `degraded`
and preserve heartbeat/cycle timestamps; they do not classify stale or
unavailable states and are not exposed through a live Steward dashboard/API.
The component remains **NOT DONE** under the active main DoD Rev 1.6. The
checked-out feature branch contains DoD Rev 1.7 and AI_HINTS Rev 1.0.5; this
increment follows the dispatch clarification to use active main Rev 1.6 and does
not change either standard.

No production service, database, migration, credential, provider, phone, or
Bluetooth headset was changed or exercised by this remediation. No merge or
deployment was performed.
