# Riverview~ M1.1 runtime baseline commissioning

**Document Revision:** 1.0.0
**Component:** RUNTIME-BASELINE
**Task:** RV-M1.1-001 / GitHub Issue #1
**Owner:** office:operations; accepting authority: Steward
**Status:** implemented and development-tested; Camrui commissioning NOT VERIFIED
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
| Windows transport | existing `camrui` SSH alias; `admin1@192.168.1.155` |
| Runtime OS account | `riverview`, system account, nologin shell, no sudo grant |
| Versioned runtime code | root-owned `/opt/riverview/releases/<full-source-commit>` |
| Active code reference | root-controlled `/opt/riverview-core` symlink |
| Runtime Python | release-local `.venv`, Psycopg binary 3.2.10; root installs dependencies with TLS verification |
| State / diagnostic storage | `/var/lib/riverview`, riverview-owned mode 0700; no institutional state is stored here |
| Persistent credential source | `/etc/riverview/pgpass`, root:root mode 0600; parent mode 0700 |
| Runtime credential | systemd `LoadCredential=pgpass`; temporary, service-readable file in `CREDENTIALS_DIRECTORY` |
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
or checksum mismatch. It preserves old releases, unit bytes and rollback records.
Do not delete these until an explicitly approved retention decision; preserve a
second protected backup off-host before changing a critical deployed predecessor.
First-install rollback retains accounts, credentials and empty state directories.

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
reference. `heartbeat_at`, meaningful progress and event cursor are explicitly
null: this diagnostic cannot claim an institutional heartbeat or durable progress.

Authentication: OS permissions, root-owned source and SSH host-key verification.
Operators use existing authorized sudo for the read-only report consumer;
the package adds no sudoers entry and grants no remote API/control authority.
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

## Windows-to-Camrui installation

Prerequisites on Camrui: Ubuntu 24.04.3, PostgreSQL 16 baseline already commissioned,
systemd 250+, Python 3/venv/pip, Git test utility, sha256sum, flock, existing admin1
sudo authority. If venv is absent, an authorized operator installs `python3-venv`;
do not disable TLS verification. Installation requires PyPI package access on Camrui.

Build from the engineering branch's exact committed revision on Windows. Python
and Git must be available. The builder packages committed regular files only,
excluding untracked secrets and Git metadata, refuses a dirty tracked worktree or
existing output and emits the archive checksum. The package is self-contained in
code/docs/tests; it is not offline dependency distribution.

```powershell
Clear-Host
Set-Location A:\Riverview-New-Core
python scripts/build_camrui_package.py A:\riverview-M1.1.tar.gz
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
scp A:\riverview-M1.1.tar.gz camrui:/home/admin1/riverview-M1.1.tar.gz
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
ssh -tt camrui
```

On Camrui, use a newly created staging directory; do not extract over the existing
development checkout. Compare archive SHA-256 to the builder output before running
code. Record the unique staging path and rollback path printed by the installer.

```bash
sha256sum /home/admin1/riverview-M1.1.tar.gz
stage=$(mktemp -d /home/admin1/riverview-M1.1.XXXXXXXX)
tar -xzf /home/admin1/riverview-M1.1.tar.gz -C "$stage"
cd "$stage"
sha256sum --check --strict PACKAGE_SHA256SUMS
sudo sh deploy/install_baseline.sh
```

Enter the existing database password only into the non-echoed Camrui terminal
prompt if the protected credential file is absent. Then capture live outcomes:

```bash
cd /opt/riverview-core
stamp=$(date -u +%Y%m%dT%H%M%SZ)
sudo python3 scripts/capture_baseline_acceptance.py --output "/var/lib/riverview/acceptance-$stamp.json"
sudo cat "/var/lib/riverview/acceptance-$stamp.json"
```

The collector starts the probe twice with systemd, compares source commit and
distinct fresh observations, retains nonzero outcomes, and never accepts on behalf
of the Steward. Copy the sanitized JSON into the engineering evidence store via
an approved operator path, retain file SHA-256 and evaluate every DoD gate.
No institutional event processor or CME is enabled by this installer.

See [flowchart](RUNTIME_BASELINE_FLOW.md), [cookbook](RUNTIME_BASELINE_COOKBOOK.md)
and [development evidence](../development/M1.1_ACCEPTANCE.md). Steward acceptance
and any explicit sequencing decision remain required before M1.2.

## Revision history

- 1.0.0: Initial M1.1 commissioning package; all files newly introduced.
