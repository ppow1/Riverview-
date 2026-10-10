# Riverview~ M1.3 Camrui commissioning verification

**Document Revision:** 1.0.2
**Task:** RV-M1.3-002
**Component:** EVENT-PROCESSOR
**Milestone:** M1.3 technical commissioning
**Host:** `admin1-Default-string`, Ubuntu 24.04.3
**PostgreSQL:** 16.15
**Source commit:** `9ca7cb189d1e1f57c69395303a9367fabd979ff5`
**PR:** [#5](https://github.com/ppow1/Riverview-/pull/5), merged as `9ca7cb189d1e1f57c69395303a9367fabd979ff5`
**Status:** Scoped technical commissioning PASS; full component DoD OPEN

## Package and deployment

The package was built from the merged source commit. SHA-256:
`090d4d2965196db246b5f614d58e82cf692eb82216eea7d8f2c58acafb6d5750`.
Package manifest, archive membership, and shell-byte checks passed. The installed
release is root-owned at
`/opt/riverview/releases/9ca7cb189d1e1f57c69395303a9367fabd979ff5`; the separate
`/opt/riverview-event-processor` link points to that release. M1.1's
`/opt/riverview-core` link, release, unit, and credentials were not changed.

`riverview-event-processor.service` is enabled and running as `riverview`.
`systemd-analyze verify` passed. Systemd delivered the existing root-owned
credential using `LoadCredential`; the credential mount was mode 0550/0440, and
the private libpq passfile was `riverview:riverview`, mode 0600. No credential
contents were captured. The worker verifies source migration checksums before
processing.

## Database preflight, backup, and migration

Before M1.3 DDL, `riverview_dev` was owned by `riverview_core`, migration 0001
matched checksum
`7f3580aacc057b977f8dd6f880584d1fed678488523b0d2ce6737c1107487492`, and there
were zero assignments, zero events, and no cursor table. PostgreSQL was 16.15;
the runtime role had schema USAGE and CREATE.

Root-only backup:
`/var/backups/riverview/M1.3-20261010T165756Z/riverview-before-m13.dump`
SHA-256: `4bf7be54f98727855fadcdd4060ca9a71b670831a089f35488060ade7e7a8592`.
It was root-owned mode 0600 in a root-owned mode 0700 directory. `pg_restore
--list` passed. A restore to disposable database `rv_m13_restore_20261010165756`
reproduced schema ownership, migration 0001 checksum, three M1.2 tables, zero
ledger rows, and absent cursor table; that disposable database was dropped after
verification.

Only migration `0002_event_processor_cursor.sql` was applied through the
versioned runner as effective role `riverview_core`. Checksum:
`356c473027044429f403ca55da7a13fda86a4bfacc606d0727dc23ee98eafa3b`.
The cursor table owner is `riverview_core`; idempotent rerun returned `[]`.

## Live behavior and recovery

Three unique Camrui assignments advanced unattended from `queued` to `ready`,
with causally linked event sequence pairs 1/2, 3/4, and 5/6. Consumer
`assignment-intake.v1` ended at durable cursor 6. Exact assignment/event IDs are
in `runtime_acceptance.json`.

A systemd restart stopped at cursor 2; the new process resumed at cursor 2 and
advanced another assignment. The sole granted M1.3 advisory-lock backend was
identified and terminated. The worker logged sanitized failure type
`AdminShutdown`, retried, revalidated migrations, reacquired leadership as a new
backend, remained active, and retained cursor 4.

Rollback restored the prior absent M1.3 unit/link state while retaining
migration 0002 and cursor 4. M1.1 still reported ready at commit
`64e8f14ad6d71102a864755739a1c8a61506235c`. The release was staged again,
migration rerun returned `[]`, the unit was enabled/started, and a third
acceptance assignment advanced through sequence 6.

## Tests, CI, and scope

The exact merged tree was reverified locally: 74 tests, zero failures/errors/skips against an isolated PostgreSQL 16 UTF-8 cluster. The test cluster was restarted on a disposable port, every `rvtest_*` schema was removed (final count zero), and the cluster was stopped. PR #5 push and pull-request checks passed
as runs 38069688433 and 38069691322; post-merge main run 38069730995 passed.
See `test_results.json`, `ci_results.json`, and `package_verification.json`.

Scoped M1.3 technical commissioning is verified. Full component DoD remains
open, including the M3.1 dashboard, later autonomy, external status projection,
and whole-project completion obligations.
