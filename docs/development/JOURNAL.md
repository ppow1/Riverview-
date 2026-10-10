# Riverview~ development journal

**Document Revision:** 1.0.16
**Component:** ENG-RECORDS
**Date:** 2026-10-10 UTC

## 2026-10-10 UTC — RV-M1.1-001 / RUNTIME-BASELINE

Actor: Codex. Repository baseline: ppow1/Riverview-, branch work,
`7dd9d472ad3c44ea71f2914392dd2696943c943b`, initially clean. Loaded full campaign,
roadmap, AI hints, lifecycle/records/DoD and all checked-in architecture/component
and privacy contracts. Issue #1 API retrieval denied by the egress proxy; browser
path returned 404, not proof that issue does not exist. Git read authentication
works. No issue text has been claimed as read.

Decision: follow checked-in M1.1 assignment and the user's supplied Camrui
configuration; introduce only new revision-1.0.0 files. No controlled predecessor
is overwritten; baseline tracked-file hashes are compared before final handoff.
Deployment helpers preserve exact existing unit bytes/checksum and release link
before replacement; rollback remains live NOT VERIFIED.

Existing database readiness evidence is reused. Remote development checkout
`/home/admin1/riverview-core` remains untouched; root-owned immutable runtime
releases under /opt avoid letting an unprivileged service modify its own code.
Use OS riverview identity distinct from DB riverview_core, systemd credential
delivery, read-only connection/schema diagnostics and freshness-aware consumers.
The request-driven baseline check does not weaken persistent execution or CME.

Experiment: normal cloud SSH stopped at unsafe installed system SSH configuration.
An isolated `ssh -F /dev/null` check with strict host-key checking and BatchMode
then returned connection refused to admin1@192.168.1.155:22. No remote operation
ran. User directed continuation via a Windows-transferable package; no credentials
were requested in chat. Camrui live tests remain NOT VERIFIED.

Development tests exercise simulated DB contracts, credential/identity failures,
stale/unavailable observers, package bytes/checksums and acceptance failure
retention. They do not prove PostgreSQL TCP authentication or systemd credential
delivery on Camrui. Direct systemd template verification failed solely because
the deployment interpreter path is absent locally; a temporary path substitution
is used for structural validation and reported distinctly.

Next: build exact committed package, provide evidence and PR when API access
permits. Execute Camrui commissioning via existing Windows SSH, capture outcomes,
resolve dependent DoD/Steward acceptance; keep roadmap cursor at M1.1.

## 2026-10-10 UTC — RV-M1.1-001 / resolved GitHub access and delivery

Append-only correction to the initial blocker: GitHub API access subsequently
worked. Issue #1 was read in full and matches the scoped implementation and
Steward sequencing. Commit f76507801c7f438ad50f8b507ca5e49db9556a4b was pushed
to codex/m1.1-runtime-commissioning, and draft PR #2 was created and confirmed:
https://github.com/ppow1/Riverview-/pull/2. No merge or deployment was performed.
The first committed package extracted cleanly, all 50 manifest checksums passed,
and both extracted shell scripts passed syntax checks. Documentation updates
record resolved access and preserve exact predecessor bytes/hashes in docs/history
and M1.1_REVISION_RECORD.md before incrementing each file to 1.0.1. Rebuild the
final package from the updated committed PR head; SOURCE_COMMIT is authoritative.
Camrui commissioning, credential delivery and rollback remain NOT VERIFIED.

## 2026-10-10 UTC — RV-M1.1-002 / Windows archive repair

Read PR comment 6091930352: actual installation failed at set -eu, exit 2,
following successful SSH/sudo/commit/manifest checks; no acceptance ran. Original
Windows archive is not available in cloud (user confirmed), so do not claim its
bytes were inspected. Executed preserved old builder under core.autocrlf=true:
both packaged shell files acquire CRLF while their committed blobs are LF.
Linux /bin/sh executing line 15 reproduces the exact Illegal option error.
Manifest still passes because it hashes converted bytes. This demonstrates the
packaging defect independently of any conjectured transfer problem.

Decision: read immutable Git blob bytes in one cat-file batch, add LF Git
attributes for deployment files, reject unsafe shell bytes before output, and
provide read-only archive-byte verifier. Keep install/rollback source unchanged;
test actual tarball bytes, manifest agreement, Linux syntax and guarded execution
for both. Preserve predecessors before all revisions; retain failed attempt and
old builder as executable regression fixture. New uniquely named Windows archive
and fresh staging preserve failed artifacts. No manual host edits or database
changes. M1.1 remains NOT DONE, live retry and Steward acceptance pending.


## 2026-10-10 UTC — RV-M1.1-003 / current checkout verification

Actor: Codex. Reused the existing M1.1 commissioning branch at `892b4893a584bd5a6aefbcac7e73bedbc5f53314`; branch baseline was clean. Verified Ubuntu 24.04.3 and PostgreSQL 16.15 are present and the local cluster is online. The full suite passed with the documented `PYTHONPATH=src` (36 tests, 3 PostgreSQL integration skips, 0 failures); both deployment shell scripts passed `sh -n`. The initial suite invocation omitted `PYTHONPATH` and failed one import; corrected invocation passed. Exact host evidence is retained in `evidence/checkouts/RUNTIME-BASELINE/20261010T034142Z-892b489/checkout.md`.

The runtime probe truthfully reported `IDENTITY_MISSING`. The protected runtime paths and OS identity are absent on this execution host. `camrui` did not resolve; strict SSH to the documented IP stopped because its host key is not known. Local noninteractive sudo is unavailable, and local socket login as `admin1` is rejected because that database role does not exist. No remote/privileged operation, schema change, credential access/reset, or deployment ran. M1.1 remains BLOCKED pending verified host identity, trusted host-key/access path, and authorized Camrui terminal commissioning. Existing database readiness evidence is not upgraded by this run. Steward acceptance and M1.2 remain pending. Exact predecessor preservation is recorded in `M1.1-003_REVISION_RECORD.md`.


## 2026-10-10 UTC — RV-M1.1-004 / local Camrui execution review

Actor: Codex. Resumed at `6fc346e78198e6ce76642927f7edb9f9245341f2` on `codex/m1.1-runtime-commissioning`. The Steward confirms this process is running directly on Camrui; the reported OS hostname is `admin1-Default-string`. Ubuntu 24.04.3 and PostgreSQL 16.15 cluster `16/main` are present and PostgreSQL is accepting local connections.

Reviewed the roadmap, campaign, runtime contract, installer, acceptance collector and cookbook. Roadmap M1.1 requires a reproducible database/schema check on Camrui; neither it nor the campaign makes SSH a gate. The campaign asks for a consolidated SSH runner only if needed. The Windows alias is only a transfer/remote-observer convenience. Local package build, verified staging, local installer and local systemd acceptance collector are the correct path on the target host. SSH remains strict-host-key verified if a separate remote observer is used.

Read-only checks: `riverview` account and `/etc/riverview`, `/etc/riverview/pgpass`, `/var/lib/riverview`, `/opt/riverview-core` are absent; the runtime unit is `LoadState=not-found`; no `PGPASSFILE`, `RIVERVIEW_PG_DSN` or PostgreSQL test DSN is set. Read-only TCP login as `riverview_core` failed because no password was supplied; no credential file was inspected. No DB objects or privileged configuration were changed. Full local test suite is eligible because the PostgreSQL test DSN is unset and integration tests skip before creating temporary schemas.

Decision: document local build/install/acceptance commands and privilege effects. Do not run `sudo sh <verified-stage>/deploy/install_baseline.sh`: installer requires root to create/use service identity and write `/opt`, `/etc/riverview`, `/var/lib/riverview`, and systemd configuration, and may prompt to provision an absent secure passfile. User has not authorized privileged configuration changes. Do not run the root-only acceptance collector until authorized installation exists. Exact review and test evidence is retained under the RV-M1.1-004 checkout record. M1.1 is still blocked on authorized commissioning and database authentication; local SSH resolution/key failures are not blockers. Steward acceptance remains pending; do not advance to M1.2. Predecessors and checksums are in `M1.1-004_REVISION_RECORD.md`.

## 2026-10-10 UTC — RV-M1.1-006 / disposable PostgreSQL integration verification

Actor: Codex. Source commit `b459bf1691b9d92811185b0a5b7013a28ac40752`, branch
`codex/m1.1-runtime-commissioning`, target host Camrui (`admin1-Default-string`,
Ubuntu 24.04.3). To execute the three integration tests previously skipped for
lack of a test DSN, initialized a disposable PostgreSQL 16.15 cluster under
`/tmp/rv-pgtest.uEU8h2I0`, with trust authentication confined to its private Unix
socket and no TCP listeners. The installed `16/main` cluster was not used or
modified.

Executed `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN="host=/tmp/rv-pgtest.uEU8h2I0/socket port=5432 dbname=postgres user=admin1" python3 -m unittest discover -s tests -v`.
Result: 36 tests passed, 0 failures, 0 skipped; all three `test_postgres_ledger`
cases executed. After the run, restarted only the disposable cluster and queried
`server_version`, `listen_addresses`, and remaining `rvtest_%` schemas; result
`16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)||0`. The server was then stopped. Raw
initialization, test, server, cleanup, and shutdown logs are retained in the linked
checkout evidence directory. No credentials were logged.

This closes the skipped-test gap only. It does not verify authentication,
permissions or schema behavior against the installed service cluster, systemd
service installation, rollback, or external observation. M1.1 remains IN
PROGRESS/BLOCKED on the local privileged commissioning step and access to the
existing `riverview_core` database credential, then independent Steward acceptance.
No M1.2 work is started. Journal predecessor bytes were preserved and verified;
`M1.1-006_REVISION_RECORD.md` records the revision change.

## 2026-10-10 UTC — RV-M1.1-007 / hidden credential TTY and partial install repair

Actor: Codex on Camrui. Source commit `0cab252eb4aae6736433d71e154ea1e26b1426c5`,
branch `codex/m1.1-runtime-commissioning`. User reported the authorized M1.1
installer passed package verification and dependency installation, then failed in
`scripts/provision_pgpass.py` at `open("/dev/tty", "r+")` with
`io.UnsupportedOperation: File or stream is not seekable`. Reproduced this exact
failure locally in a pseudo-terminal with `open("/dev/tty", "r+")`; Python
3.12.3 raises the same exception.

Read-only host inspection found the `riverview` nologin account, root-owned
`/etc/riverview` mode 0700, and root-owned release directory
`/opt/riverview/releases/b15b093642f65f6de36c1b977571ae2b79f04850` mode 0700.
`/etc/riverview/pgpass`, `/var/lib/riverview`, `/opt/riverview-core`, and the
systemd unit are absent. PostgreSQL 16/main is online. No credential contents
were read. This state is safely rerunnable: the installer reuses the account
and versioned release; provisioning fails before creating the passfile, state
directory, active link, unit, or rollback record. Inspection also found that
`cp -a` copied the private staging root's 0700 mode onto the release root,
blocking the service account from traversing the code.

Implementation: call `getpass.getpass()` without a caller-supplied TTY stream,
and convert `GetPassWarning` to an error to fail closed if hidden input is not
available. Add a pseudo-terminal regression test that generates a runtime-only
sentinel, confirms the input is returned, and verifies it is not echoed. On
rerun, require an existing release to be a real root-owned directory with
root-owned contents; normalize files to readable and directories to traversable
while removing group/other write permission. This repairs the retained partial
release without changing file bytes or ownership and refuses an unsafe release.
Update the component contract, cookbook and flowchart with retry/error behavior.

Verification: the first pseudo-terminal test iteration found the harness assumed LF-only terminal output; PTY canonical mode emitted CRLF. The assertion now normalizes captured line endings. The focused runtime suite passed (19 tests); the full suite against the isolated local PostgreSQL cluster passed (38 tests, 0 failures, 0 skips), including all three PostgreSQL ledger tests. The temporary test schemas were absent after cleanup (`16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)||0`); the test cluster was stopped. Test, cleanup and lifecycle logs are retained in the RV-M1.1-007 checkout evidence.

Next: commit the corrected source and records, build and verify a new uniquely named package from that commit, then retry commissioning through the corrected package. The failed staged package remains untouched. M1.1 remains IN PROGRESS/BLOCKED pending live acceptance evidence and Steward acceptance; no M1.2 or later dependent milestone is claimed complete.

## 2026-10-10 UTC — RV-M1.1-008 / deployed storage-path failure diagnosis

Actor: Codex on Camrui (`admin1-Default-string`, Ubuntu 24.04.3). The active unit
is loaded from `/etc/systemd/system/riverview-baseline.service`, runs as static
`riverview` (UID 997/GID 984), sets `StateDirectory=riverview` and mode 0700,
`DynamicUser=no`, `ProtectSystem=strict`, `ProtectHome=yes`, and `PrivateTmp=yes`.
The active release source is commit `3d7e58fc19ae38b6fd378fd0f0421ebb36fdb266`;
the installed `runtime_baseline.py` SHA-256 matches this checkout's source.
Host-context checks show `/var/lib/riverview` is a non-symlink directory owned
997:984 with mode 0700; `Path.absolute()` and `Path.resolve()` both produce the
same path. `/opt/riverview-core` is a symlink to the versioned release, but the
storage check receives the fixed `/var/lib/riverview` default, so that symlink
is not itself evidence of the storage failure.

The installed sanitized report cannot be read by `admin1`; the unit journal
contains only status 2. `sudo -n -l` reports that a password is required, so no
service-context rerun or privileged state/configuration change was performed.
The precise source condition is one of `path.resolve() != path.absolute()`,
non-directory `lstat` type, or owner UID mismatch. Host-context evidence rules
out the latter two and the resolution mismatch on the host, but not within the
unit's mount namespace. The change adds safe `path_failure_reason` diagnostics
and tests for those predicates plus the deployed unit/storage contract; it does
not relax path validation. Live root-authorized confirmation and repair remain
open. No credential or database content was read; no services/configuration
were modified.

Verification: the focused runtime-baseline suite passed 22 tests. The full
checkout suite passed 41 tests: 38 passed, 3 PostgreSQL integration tests
skipped because `RIVERVIEW_TEST_PG_DSN` is unset. The three integration tests
were previously executed successfully against a disposable local PostgreSQL
cluster under RV-M1.1-006; this source-only path-diagnostic change does not
affect that database code. `sudo -n -l` confirmed no passwordless privilege, so
the protected live report and the new service-context predicate have not been
verified. No installation or service restart was attempted.

Next: record and commit this diagnostic change, build and verify a uniquely
named package from that commit, then arrange one authorized package install
with its scoped service start. Compare the service-context reason and correct
only a demonstrated mismatch. M1.1 and all dependent roadmap milestones remain
blocked pending root-cause repair, successful live acceptance and Steward
disposition.

Contract traceability review for RV-M1.1-008 added `path_failure_reason` to the
component specification (Rev 1.0.4). The initial diagnostic package at source
commit `e6b46c362326900c09f9e5c59d27d18137004847` predates this specification
update and is retained unchanged; it is superseded for deployment by a newly
built package from the next committed source. No system installation has run.

Privilege-path recheck during goal continuation: `sudo -n -l` reports a
password is required; `systemctl --no-ask-password start
riverview-baseline.service` returns “Interactive authentication required.” No
passwordless sudo or polkit route exists for the needed deployment. The
commit-addressed diagnostic package and exact local install command are ready;
an authorized interactive sudo session is the remaining external condition.
Roadmap M1.2 is sequenced after M1.1 acceptance, so there is no independent
numbered roadmap item to advance while M1.1 is blocked. Do not mark M1.1 DONE or
install the superseded `e6b46c3` package.

## 2026-10-10 UTC — RV-M1.1-009 / RUNTIME-BASELINE privileged path and UNSAFE_PATH

Actor: Codex on Camrui. The owner explicitly authorized root-level New
Riverview development operations; `sudo -n id` returned uid 0. Repository at
task intake was `3e60476` on `codex/m1.1-runtime-commissioning`, clean. The
deployed unit failed with `UNSAFE_PATH`, step `storage`, source `3d7e58f`.

Experiment: inspected the actual sanitized report, unit, host path metadata and
the deployed source predicate. `/var/lib/riverview` passed its service-context
private-state check. A transient unit reproducing the deployed systemd sandbox
showed PID 1 creates `CREDENTIALS_DIRECTORY` as root:root 0550 and `pgpass` as
root:root 0440, both readable/traversable to `riverview`. The probe incorrectly
reused its runtime-owned-directory validator on this systemd-managed parent;
it emitted `UNSAFE_PATH` with a misleading storage step. This is an ownership
contract mismatch, not a symlink or state-directory defect. The correction
validates the fixed systemd credential location, no symlink traversal, root
ownership, exact non-writable delivery modes and effective service read access,
while retaining the stricter runtime ownership/mode checks on state.

Decision: introduce a root-owned fixed-operation broker. It admits only an
exact registered package ID, fixed service actions, sanitized report, acceptance
capture, or a constrained rollback record ID. Its root policy pins the archive
digest and Git source commit. It rejects arbitrary paths/commands, unsafe tar
members and mutable/incorrect release content; only the exact hash-verified
archive is extracted root-owned, then its fixed installer is invoked. New
release digests need an explicit root-policy update. No user checkout script is
run as root. Bootstrap, installation and recovery are within the user's explicit
Camrui authorization; no credentials were read or changed.

Verification: privilege/runtime focused suite currently passes 28 tests; a
fixed-command construction test was added afterward and is pending rerun. Full
checkout suite and root deployment remain pending. The installed service failure
was reproduced. Transient systemd checks confirmed path metadata without
printing passfile contents. Prior M1.1 completion evidence, PostgreSQL checks,
optional SSH status, rollback and Steward gates remain unchanged. Next: rerun
verification, commit, build the exact package, bootstrap the broker, redeploy,
verify live database acceptance and rollback, then evaluate full M1.1 DoD.
Status remains IN PROGRESS; Steward acceptance and later live dashboard/autonomy
gates remain required.

## 2026-10-10 UTC — RV-M1.1-010 / libpq passfile mode mismatch

Live deployment of source commit a25aa71 corrected the prior misleading
UNSAFE_PATH report; the service then failed during database authentication.
The journal showed libpq rejected `/run/credentials/riverview-baseline.service/pgpass`
because systemd correctly delivered a root-owned mode-0440 credential. This is
not a reason to loosen the systemd source contract: libpq requires a passfile
mode of 0600 or stricter.

Implementation places an ephemeral, mode-0700 `RuntimeDirectory` under systemd
control. The unprivileged probe validates the fixed root-owned systemd source,
copies through O_NOFOLLOW and O_EXCL descriptors to a service-owned mode-0600
passfile, validates the copy, and passes only the copy to Psycopg. Existing
destination/symlink paths fail closed. systemd cleans the directory on service
stop. No credential bytes are logged, exposed in reports, or placed in source.

Task RV-M1.1-010 predecessor backups for runtime source, unit, tests, component
specification, cookbook, flowchart and this journal are listed in
`.riverview-backups/manifest.jsonl`; files were verified before edits. Regression
coverage checks the root-owned source contract, installed unit paths, exclusive
copy, owner/mode and symlink refusal. The focused runtime suite passed (26 tests).
The full suite passed (52 tests, zero failures/skips) against a temporary
socket-only PostgreSQL cluster, with zero leftover test schemas; cluster/data
were removed. At this checkpoint M1.1-010 remained IN PROGRESS pending package
and live deployment verification.

Checkout was repeated against commit b40c77fdca48c556af9d25a8cd25e7ca192b9748:
52 tests passed, including PostgreSQL integration; no schemas remained. The
exact package SHA-256 is
`bedf5f94e0ae0cb107fb7d2ce69eab37f8eb9cc709b0fa05d0933fe79e7025ab`, and
manifest/shell verification passed. Evidence is retained in
`evidence/checkouts/RUNTIME-BASELINE/20261010T1450Z-b40c77f/`. The installed
root-owned broker remains constrained to its original `initial-m11` package;
updating its allowlist requires authenticated sudo, which is not available
noninteractively in this execution context. Live deployment and rollback remain
pending that one bootstrap action.
The current package registry is still pinned to a25aa71. Steward acceptance
remains pending; M1.2 is not eligible.

## 2026-10-10 UTC — RV-M1.1-009 / predeployment checkout closure

After adding regression coverage for the four expected Python virtualenv
symlinks, the final checkout run executed 50 tests: 50 passed, zero failed,
zero skipped. The three PostgreSQL ledger integration tests ran against a fresh
PostgreSQL 16 cluster under a mode-0700 temporary directory, Unix socket only,
no TCP listener. All generated rvtest schemas were dropped; post-run count was
0; the temporary cluster was stopped and its directory removed. The live
commissioned PostgreSQL cluster and riverview database were not used.

Targeted runtime/broker tests: 31 passed; py_compile and git diff --check passed.
The changed-file revision subset passed: six existing controlled files each
incremented monotonically with an independently verified predecessor backup;
three new controlled files have revision 1.0.0. The repository-wide validator
still reports 30 unchanged legacy files with missing revisions, including
.gitignore, the unversioned Engineering Records Standard, and prior generated
evidence; it reports no changed-file revision or backup defect. Preserve that
FAIL as a pre-existing repository governance gap rather than modifying unrelated
files or claiming global checkout compliance.

Next: commit this source/docs/test increment, build and inspect its exact package,
bootstrap the hash-pinned helper and narrow the existing project sudoers rule,
then deploy and verify fresh live baseline/acceptance plus recovery. The package
is not yet approved or installed; M1.1 remains IN PROGRESS.

## 2026-10-10 UTC — RV-M1.1-011 / privilege broker retirement and PostgreSQL inet diagnosis

The owner restored unrestricted passwordless sudo. Verified `sudo -n id` and a
separate root operation returned UID 0; `sudo -n -l` confirmed `(ALL : ALL)
NOPASSWD: ALL`. `visudo -c` parsed `/etc/sudoers.d/90-riverview-codex` successfully.
This authorization file remains intact.

Before removing active broker state, preserved checksummed copies of the
root-owned helper, private policy and package registry under
`/var/backups/riverview-privctl-retired-20261010T150152068992Z`. Removed their
active copies; no broker-specific sudoers rule remained, and root access still
passed independent verification. Historical task records, predecessor copies,
and rollback records are retained.

Deployed the exact verified b40c77f package into its immutable release. The
private systemd passfile copy succeeded. A live read-only DB query showed the
identity check failed because `inet_server_addr()::text` yields
`127.0.0.1/32`; the configured endpoint and database role were correct. RV-M1.1-011
changes that projection to `host(inet_server_addr())` and adds regression coverage.
M1.1 remains IN PROGRESS pending corrected deployment, fresh acceptance evidence,
recovery verification, and Steward decision. M1.2 remains gated.


Correction to the superseded RV-M1.1-010 next-step note above: the owner has
restored unrestricted passwordless Camrui administration. No privilege broker
bootstrap or sudoers narrowing is authorized or required. RV-M1.1-011 retires
the broker and proceeds using the owner-authorized administrator. The full
source suite was executed with the documented `PYTHONPATH=src` and an isolated
socket-only PostgreSQL cluster: 45 tests passed, including all PostgreSQL ledger
integration tests; no `rvtest_%` schemas remained. The live baseline defect is
addressed by querying `host(inet_server_addr())`; package build/deployment and
live recovery evidence remain pending at this checkpoint.


RV-M1.1-011 live verification completed from package source commit
`a2b94e24715a670262859e1af31a0ea417ed37cb`. The package digest and source
manifest passed. Full suite passed 45/45 against an isolated socket-only
PostgreSQL cluster; installer suite passed 45 with its three DSN-dependent tests
skipped, which the separate full run covers. Live read-only PostgreSQL reported
`riverview_core` / `riverview` / `127.0.0.1` and transaction read-only `on`.
The systemd service ran as `riverview`, result success/exit 0, and returned a
fresh baseline-ready report for `riverview_dev`. Collector evidence includes two
distinct successful observations and explicitly remains `PENDING_STEWARD`.
Service restart passed. Rollback checksum and restoration passed, the known b40
predessor reproduced its database identity defect, and rerunning the corrected
package restored a2b94e2 readiness. No DB object or credential was modified.
The installed broker, policy and registry are absent; unrestricted sudo and
visudo checks still pass. Technical M1.1 acceptance is PASS; formal Steward
acceptance/sequencing remains pending and M1.2 is not started.
