# Riverview~ M1.1 runtime baseline commissioning

**Document Revision:** 1.0.13
**Component:** RUNTIME-BASELINE
**Repair task:** RV-M1.1-011
**Task:** RV-M1.1-001 / GitHub Issue #1
**Owner:** office:operations; accepting authority: Steward
**Status:** libpq credential repair implemented; live commissioning and Steward acceptance in progress
**Date:** 2026-10-10 UTC

## Responsibility and declared execution model

M1.1 verifies the service identity, persistent credential delivery, storage ownership,
and existing isolated database baseline. It introduces a request-driven commissioning
diagnostic, not an institutional execution process. It can be invoked repeatedly;
there is no rearming flag, conversation dependency or single-use restriction.
Its explicit oneshot systemd type matches this diagnostic responsibility. It does
not replace the persistent event processor (M1.3), independent workers (M2.1),
always-on CME (M2.4) or live permission-filtered Steward dashboard (M3.1).

CME remains a first-class independent institutional service: meaningful progress
is distinct from process heartbeat; stalls must produce traceable recovery and
escalation events without conferring governing or worker authority. The internal
vision/visibility, durable event, API, spatial and privacy contracts remain in force.
No roadmap or architecture requirement is waived by this package.

## Identity, placement and ownership

| Resource | Declared owner / placement |
| --- | --- |
| Existing development checkout | admin1; `/home/admin1/riverview-core`; left untouched by installation |
| Optional Windows transport | existing `camrui` SSH alias; `admin1@192.168.1.155`; not used when commissioning directly on Camrui |
| Runtime OS account | `riverview`, system account, nologin shell, no sudo grant |
| Versioned runtime code | root-owned, service-readable /opt/riverview/releases/<full-source-commit>; directories traversable/read-only to the service |
| Active code reference | root-controlled `/opt/riverview-core` symlink |
| Runtime Python | release-local `.venv`, Psycopg binary 3.2.10; root installs dependencies with TLS verification |
| State / diagnostic storage | `/var/lib/riverview`, riverview-owned mode 0700; no institutional state is stored here |
| Persistent credential source | `/etc/riverview/pgpass`, root:root mode 0600; parent mode 0700 |
| Runtime credential source | systemd `LoadCredential=pgpass`; temporary, service-readable root-owned file in `CREDENTIALS_DIRECTORY` (file 0440, directory 0550) |
| Runtime libpq passfile | Copied without logging into `/run/riverview-credentials/pgpass`, service-owned mode 0600 in a systemd-managed mode-0700 runtime directory; removed when the oneshot service stops |
| Database | existing PostgreSQL 16, `riverview`, role `riverview_core`, TCP `127.0.0.1:5432` |
| Isolated schema | existing `riverview_dev`, actual owner reported, riverview_core USAGE/CREATE rights checked without DDL |
| Database files | PostgreSQL-managed storage; prior readiness evidence reused; new ownership inspection NOT VERIFIED |
| Predecessors | root-only `/var/backups/riverview-baseline.*`; exact previous unit bytes/checksum and previous symlink target |

The OS and database accounts have distinct responsibilities. No superuser,
CREATEDB, CREATEROLE, replication or BYPASSRLS privilege is acceptable for the
application database role. The current schema test checks privileges rather than
creating permanent ledger tables. Database credentials and `public` are unchanged.

The installer refuses an existing non-symlink deployment, unsafe credential or
state permissions, interactive/root runtime identity, overlapping commissioning,
a non-directory/symlink release, non-root-owned release content, or checksum
mismatch. It preserves old releases, unit bytes and rollback records. On a
verified root-owned release, every run enforces service-readable files and
traversable directories while removing group/other write access; this also repairs
the restrictive top-directory mode copied from a private staging directory.
Do not delete these until an explicitly approved retention decision; preserve a
second protected backup off-host before changing a critical deployed predecessor.
First-install rollback retains accounts, credentials and empty state directories.

## Privileged deployment and commissioning

Camrui's dedicated New Riverview development account `admin1` has
`admin1 ALL=(ALL:ALL) NOPASSWD: ALL` in
`/etc/sudoers.d/90-riverview-codex`. The file is root-owned mode 0440 and is
validated with `visudo`. This is host-level administration authority explicitly
granted by the owner; do not install a project-specific command broker, package
registry or competing sudoers rule. Preserve the sudoers file and verify
`sudo -n id`, `sudo -n -l`, and a root operation after any administrative change.

### Local release qualification (required)

Qualify the exact PR candidate on a Riverview-controlled machine before merge
and deployment. GitHub Actions is optional and informational; the local record
and separate independent review are authoritative. Do not reduce the test set
or treat skipped required PostgreSQL tests as passing.

Use a clean checkout at the full candidate commit, a disposable PostgreSQL 16
test instance, and the pinned dependencies in
`deploy/qualification-requirements.txt`. Set `CAPABILITY_DIFF_BASE` to the
actual PR base ref before running and retain the output of these checks:

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN="$DISPOSABLE_TEST_DSN" python3 -m unittest discover -s tests -v
python3 scripts/validate_capability_declaration_changes.py --base "$CAPABILITY_DIFF_BASE"
python3 scripts/process_graph.py check
python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json
```

The checkout record binds the full commit and Git tree SHA to the environment,
commands, timestamps, exit codes, test counts, skips, logs, and package hashes.
Also run focused PostgreSQL-backed tests for changed lifecycle behavior. The
independent reviewer must review that same full commit and report findings and
disposition before merge. A different commit, unrecorded local run, or
author-only review is not sufficient. A hosted Actions result does not override
the local result in either direction.

Build the package from an exact committed source revision and verify its
archive digest, source commit, file checksum manifest, safe regular-file members
and shell compatibility before commissioning. Extract only that verified
package into a fresh root-owned mode-0700 staging directory, verify checksums
again, and run its fixed installer from that staging directory. The installer
creates an immutable root-owned release, preserves the prior service unit and
release link in a protected rollback record, and starts only the baseline
service. Do not run from a mutable checkout or unverified staging content.
`scripts/build_camrui_package.py` produces byte-reproducible gzip/tar archives
from committed Git blobs: the gzip timestamp and embedded filename are fixed,
archive member metadata is normalized, and the manifest pins each file hash.
Build twice from the same clean commit and compare archive SHA-256 before
retaining the release artifact. The component-specific Comms5 archive uses
`scripts/package_comms5_camrui.py`; it remains a narrower package from the same
source commit and has its own manifest and archive digest.
Rollback uses the exact root-owned record emitted by the installer and the
versioned rollback script; it retains credentials, accounts, releases and prior
records and does not alter PostgreSQL.

The applicable controlled local qualification report and independent review
must be linked from the PR before this activation sequence. A red or unavailable
GitHub Actions status alone is not a reason to block an otherwise passing
locally qualified candidate; a failed local check, missing review, package
mismatch, backup/rollback failure, or unsuccessful service acceptance remains a
stop condition. Do not change branch protection or rulesets except for an
authorized Actions-specific status check; keep unrelated protections intact.

No database credentials are included in package bytes, command arguments,
evidence or logs. Commissioning reads only the existing protected passfile.

The runtime diagnostic validates private state as service-owned. It validates
systemd credential delivery separately: PID 1 creates
`/run/credentials/riverview-baseline.service` as root-owned mode 0550 and
`pgpass` as root-owned mode 0440, with service read/traverse access. Requiring
these systemd-managed objects to be owned by the runtime UID was a contract bug;
their root ownership and non-writable modes are security requirements.

Libpq independently requires a passfile with mode 0600 or stricter and rejects
the root-owned 0440 systemd source even when the service has read access. The
runtime therefore validates that fixed source, copies its bytes using no-follow
and exclusive-create file descriptors into the service-owned 0700
`RuntimeDirectory`, verifies the resulting service-owned 0600 regular file, and
passes only that private copy to Psycopg. A pre-existing destination or symlink
fails closed. The directory is ephemeral and systemd removes it after the
oneshot exits. The source remains root-owned and read-only; neither source nor
copy contents enter logs or diagnostics.

## Credential delivery and configuration

Use the existing database password. The terminal-only provisioning helper creates
an absent file exclusively, escapes libpq `:` and `\` characters and never emits
the value. It refuses empty, multiline and NUL-containing credentials and never
executes ALTER ROLE. No password appears in arguments, shell history, package,
Git, evidence, environment variables or the SSH transport. Existing credentials
are not overwritten or copied into rollback archives.

Non-secret libpq configuration template (the helper writes the actual file):

```text
host: 127.0.0.1
port: 5432
database: riverview
role: riverview_core
schema: riverview_dev
passfile record: 127.0.0.1:5432:riverview:riverview_core:<existing password, libpq-escaped>
```

The probe explicitly fixes this commissioned development endpoint, applies
`default_transaction_read_only=on`, verifies read-only mode and uses only SHOW/
SELECT. It rejects ambient password/service/options overrides. Do not use this
package to select another host silently: revise the controlled configuration and
tests for an authorized placement change. Password rotation is a separate
authorized operation; restart the probe afterward to reload systemd credentials.

## External observability contract

Transport: JSON stdout redirected to `/var/lib/riverview/baseline.json`; independent
consumer `scripts/read_baseline_report.py`, optionally over authenticated SSH.
Schema `rv.runtime-baseline.v1`: stable component/version, source commit, target
host, workflow/step, observation/expiry time, freshness, baseline readiness,
database/environment identities, blocker/error code, owner, recovery and diagnostic
reference. `path_failure_reason` is null except for `UNSAFE_PATH`; then it is a
fixed value such as `symlink_in_path`, `unexpected_file_type`,
`owner_uid_mismatch`, `unexpected_credential_location`,
`credential_directory_owner_mismatch`, or `credential_file_owner_mismatch`.
These values identify the rejected predicate without disclosing path contents or
weakening validation. `heartbeat_at`, meaningful progress and event cursor are explicitly
null: this diagnostic cannot claim an institutional heartbeat or durable progress.

Authentication: local OS permissions and root-owned source. A separate remote observer may use SSH with strict host-key verification; SSH is a transport option, not a commissioning acceptance requirement. Local administration runs through the owner-authorized Camrui administrator; this component installs no privilege broker and grants no remote API/control authority.
Ordinary clients cannot read protected files directly. Private Undercurrent
content is neither queried nor exported. Future CME/dashboard consumers must
use a policy-filtered owning service, not receive this credential or scrape DB internals.

Refresh: explicit diagnostic invocation, freshness TTL 60 seconds. No auto-refresh
or live dashboard is claimed. The observer rejects future timestamps and TTLs
over 60 seconds; missing/partial/invalid files are `unavailable`; expired reports
are `stale`, never ready. This is commissioning evidence, not a health history.
Retention: latest probe file replaced at each invocation; acceptance reports are
exclusive, timestamped files retained with successes and failures. Future durable
institutional monitoring events belong in the authoritative ledger (M1.3/M2.4),
not a parallel status database.

Probe exits: 0 baseline verified; 1 database unavailable; 2 configuration/security
blocker. Observer exits: 0 fresh ready; 1 fresh non-ready; 2 unavailable; 3 stale.
No driver exception text is exported because it can contain credentials.

## Local Camrui commissioning

The SSH alias is a Windows-side transport convenience. It is not required when the repository checkout and package builder are already running on Camrui. The installer, systemd probe and acceptance collector execute locally; using SSH to reconnect to the same host adds no acceptance evidence. The remote observer in `scripts/check_camrui_baseline.py` is optional and still requires strict host-key verification when used.

From a clean, committed engineering checkout on Camrui, build and verify the exact committed package, then extract it into a unique staging directory. Keep the archive outside the checkout; the builder refuses an existing output and uncommitted tracked changes.

```bash
cd /home/admin1/projects/Riverview-New-Core
stamp=$(date -u +%Y%m%dT%H%M%SZ)
commit=$(git rev-parse --short HEAD)
archive="/home/admin1/riverview-M1.1-$commit-$stamp.tar.gz"
python3 scripts/build_camrui_package.py "$archive"
python3 scripts/verify_camrui_package.py "$archive"
stage=$(mktemp -d /home/admin1/riverview-M1.1.XXXXXXXX)
tar -xzf "$archive" -C "$stage"
(cd "$stage" && sha256sum --check --strict PACKAGE_SHA256SUMS && \
 python3 scripts/verify_camrui_package.py "$archive" && \
 sh -n deploy/install_baseline.sh && sh -n deploy/rollback_baseline.sh)
```

After the package verifier passes, extract the immutable archive into a fresh
root-owned, non-writable staging directory, recheck its checksums, and run the
installer from that directory. Never run an installer from a mutable checkout.

```bash
sudo -n /bin/sh deploy/install_baseline.sh
```

The approved immutable installer may create/use the Riverview identity, release,
credential and state paths, and one systemd unit. It installs the pinned runtime
dependency only in the release runtime venv, then creates a distinct pinned
qualification venv and runs the documented pytest suite as the unprivileged
`riverview` user from a disposable, writable copy of the manifest-verified
release. The root-owned active release remains unchanged by qualification. It
does not reset the database password or initialize/alter database schemas. If
the passfile is absent, hidden terminal capture is used and fails closed if echo
cannot be disabled.

After authorized installation, capture two fresh local service observations with the acceptance collector:

```bash
cd /opt/riverview-core
stamp=$(date -u +%Y%m%dT%H%M%SZ)
sudo -n /opt/riverview-core/.venv/bin/python /opt/riverview-core/scripts/capture_baseline_acceptance.py \
  --output /var/lib/riverview/acceptance-rv-m11-011.json
```

The collector starts only the local unit and writes a mode-0600 report under protected state. Its probe makes only read-only PostgreSQL queries. The sanitized report is local Camrui evidence; neither an SSH round-trip nor the collector itself constitutes Steward acceptance.

## Windows-to-Camrui installation

Prerequisites on Camrui: Ubuntu 24.04.3, PostgreSQL 16 baseline already commissioned,
systemd 250+, Python 3/venv/pip, Git test utility, sha256sum, flock, existing admin1
sudo authority. If venv is absent, an authorized operator installs `python3-venv`;
do not disable TLS verification. Installation requires PyPI package access on Camrui.

Build from the engineering branch's exact committed revision on Windows. Python
and Git must be available. The builder reads exact committed regular-file blobs with `git cat-file`, bypassing
Windows checkout/`git archive` conversion. It rejects CRLF, BOM, NUL or invalid
shebang/final-newline bytes in `.sh` files before creating an archive. The package contains committed regular files only,
excluding untracked secrets and Git metadata, refuses a dirty tracked worktree or
existing output and emits the archive checksum. The package is self-contained in
code/docs/tests; it is not offline dependency distribution.

```powershell
Clear-Host
Set-Location A:\Riverview-New-Core
git fetch origin
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
git switch codex/m1.1-runtime-commissioning
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
git pull --ff-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$sourceCommit = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$artifactStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$deploymentOutput = Join-Path $env:USERPROFILE "Downloads\Riverview-M1.1-$artifactStamp"
New-Item -ItemType Directory -Path $deploymentOutput -ErrorAction Stop | Out-Null
$archiveName = "riverview-M1.1-$sourceCommit-$artifactStamp.tar.gz"
$archivePath = Join-Path $deploymentOutput $archiveName
python scripts/build_camrui_package.py $archivePath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$verificationReport = python scripts/verify_camrui_package.py $archivePath
$verificationExit = $LASTEXITCODE
$verificationReport | Set-Content (Join-Path $deploymentOutput 'package-verification.json') -Encoding UTF8
$verificationReport | Write-Output
Set-Clipboard -Value ($verificationReport -join [Environment]::NewLine)
if ($verificationExit -ne 0) { exit $verificationExit }
$remoteArchive = "/home/admin1/$archiveName"
scp $archivePath "camrui:$remoteArchive"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "Camrui archive: $remoteArchive"
ssh -tt camrui
```

Confirm `source_commit` equals the corrected PR commit, `manifest` and
`shell_compatibility` both PASS, and both `cr_bytes` are zero before transferring.
No global Git settings or manual host line-ending edits are required. Never use
PowerShell text pipelines to write tarballs or deployment scripts. The failed
Windows archive and `/home/admin1/riverview-M1.1.pyDz8Jfi` staging directory remain
untouched; do not overwrite `/home/admin1/riverview-M1.1.tar.gz`.

On Camrui, use the exact new archive path printed above and a newly created
staging directory; do not extract over the existing development checkout. Compare
archive SHA-256 to the builder output. Whether the engineer is already on Camrui
or connects from Windows, host-side operations are local to Camrui. Windows SSH
is only a transport to that host; it is unnecessary when execution is native.
Use the verified package archive and a newly created root-owned staging
directory; never extract over the development checkout.

```bash
archive=/home/admin1/<new-archive-name-printed-by-Windows>
sha256sum "$archive"
python3 scripts/verify_camrui_package.py "$archive"
stage=$(sudo -n mktemp -d /var/tmp/riverview-M1.1.XXXXXXXX)
sudo -n tar -xzf "$archive" -C "$stage"
sudo -n chown -R root:root "$stage"
sudo -n chmod -R go-w "$stage"
sudo -n /usr/bin/env -C "$stage" /bin/sh -c 'sha256sum --check --strict PACKAGE_SHA256SUMS && /bin/sh deploy/install_baseline.sh'
```

Enter the existing database password only into the non-echoed Camrui terminal
prompt if the protected credential file is absent. Then capture live outcomes:

```bash
sudo -n /opt/riverview-core/.venv/bin/python /opt/riverview-core/scripts/capture_baseline_acceptance.py \
  --output /var/lib/riverview/acceptance-rv-m11-011.json
```

The collector starts the probe twice with systemd, compares source commit and
distinct fresh observations, retains nonzero outcomes, and never accepts on behalf
of the Steward. Copy the sanitized JSON into the engineering evidence store via
an approved operator path, retain file SHA-256 and evaluate every DoD gate.
No institutional event processor or CME is enabled by this installer.

See [flowchart](RUNTIME_BASELINE_FLOW.md), [cookbook](RUNTIME_BASELINE_COOKBOOK.md)
and [development evidence](../development/M1.1_ACCEPTANCE.md). Steward acceptance
and any explicit sequencing decision remain required before M1.2 shared-schema
deployment and acceptance. Owner-authorized isolated M1.2 engineering may proceed
while that decision is pending; this component contract does not waive acceptance.

## Revision history

- **1.0.13 — 2026-10-25:** Make locally recorded exact-commit qualification and independent review the required release gate; document package activation only after those gates pass. Predecessor: `.riverview-backups/20261025T203827242610Z/docs/components/RUNTIME_BASELINE.md`.

- 1.0.12 — 2026-10-21: Run unprivileged qualification from a disposable writable copy while preserving the immutable release; predecessor recorded in `.riverview-backups/manifest.jsonl` under RV-180-QUALIFICATION-WORKSPACE-001.
- 1.0.6 — 2026-10-10: Document systemd source-to-libpq private passfile handling; predecessor is recorded under RV-M1.1-010 in `.riverview-backups/manifest.jsonl`.
- 1.0.9 — 2026-10-10: Remove stale scoped-helper claim and correct collector invocation; predecessor recorded in `.riverview-backups/manifest.jsonl` under RV-M1.1-011.
- 1.0.8 — 2026-10-10: Correct acceptance collector invocation with required output path; predecessor recorded in `.riverview-backups/manifest.jsonl` under RV-M1.1-011.
- 1.0.7 — 2026-10-10: Remove active broker instructions and document owner-authorized Camrui deployment; predecessor recorded under RV-M1.1-011.
- 1.0.3 — 2026-10-10: Document non-seeking hidden terminal input and safe rerun behavior for the root-owned partial release; preserve predecessor under docs/history/RV-M1.1-007/rev1.0.2/docs/components/RUNTIME_BASELINE.md.
- 1.0.5 — 2026-10-10: Pin the scoped root broker and correct the systemd credential-directory ownership contract; predecessor `.riverview-backups/20261010T142904371319Z/docs/components/RUNTIME_BASELINE.md`.

- 1.0.2: Add direct local Camrui packaging/commissioning path and clarify SSH is optional transport, not an acceptance gate; predecessor under docs/history/RV-M1.1-004/rev1.0.1/docs/components/RUNTIME_BASELINE.md.
- 1.0.1: Raw-blob packaging, archive-byte verification and preserved failure/new-path retry procedure; predecessor under docs/history/RV-M1.1-002/rev1.0.0.
- 1.0.0: Initial M1.1 commissioning package; all files newly introduced.
