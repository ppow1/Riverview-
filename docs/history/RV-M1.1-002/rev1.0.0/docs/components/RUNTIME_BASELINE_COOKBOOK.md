# Riverview~ runtime baseline troubleshooting and recovery

**Document Revision:** 1.0.0
**Component:** RUNTIME-BASELINE
**Task:** RV-M1.1-001
**Owner:** office:operations
**Status:** procedure implemented; live commissioning and rollback NOT VERIFIED

## Consolidated read-only diagnostic

On Camrui, inspect only the selected unit properties and sanitized JSON:

```bash
systemctl show riverview-baseline.service --property=User,Group,LoadState,Result,ExecMainStatus
sudo python3 /opt/riverview-core/scripts/read_baseline_report.py
```

From a connected authorized development machine with known SSH host key and
noninteractive approved sudo for the reader:

```bash
python scripts/check_camrui_baseline.py camrui
```

The runner is bounded to 30 seconds, uses BatchMode and strict host-key checking,
rejects shell syntax in destinations and preserves remote failure status. Without
noninteractive sudo, use the existing `ssh -tt camrui` connection and run the
read-only commands on Camrui. Do not add broad sudo rights to make this pass.
An expired report is intentionally stale: a request-driven baseline check does
not provide continuous health. Refresh only the diagnostic with authorized
`sudo systemctl start riverview-baseline.service`; no institution is dispatched.

## Node-to-fault mapping

| Step | Expected input / action / evidence | Failure code or signal | First read-only diagnostic | Recovery / resume |
| --- | --- | --- | --- | --- |
| Package | Exact committed revision; checksums match | Dirty tree, unsafe archive path, checksum mismatch | Compare builder source SHA/archive SHA and `sha256sum -c PACKAGE_SHA256SUMS` | Rebuild from intended commit; never override checksums; restart package stage |
| Commissioning | Authorized root, new immutable release, backups readable | Existing non-symlink deployment, lock held, partial release | `readlink /opt/riverview-core`; inspect root-only rollback record/checksums | Resolve existing deployment ownership; preserve partial artifacts; retry installer after diagnosis |
| identity | OS riverview, nonroot, nologin, systemd User=riverview | IDENTITY_MISSING / IDENTITY_MISMATCH / INTERACTIVE_SERVICE_ACCOUNT | `getent passwd riverview`; selected unit properties | Correct authorized commissioning; never run institution as root; restart probe |
| storage | Private directory owned by runtime account | PATH_UNAVAILABLE / UNSAFE_PATH / UNSAFE_MODE | `stat -c '%U:%G %a %F' /var/lib/riverview` | Identify existing owner before repair; no deletion; restart probe |
| credential | Fresh systemd credential from protected root source | CREDENTIAL_MISSING / CREDENTIAL_UNREADABLE / UNSAFE_PATH / UNSAFE_MODE / AMBIENT_DATABASE_OVERRIDE | `sudo stat -c '%U:%G %a %F' /etc/riverview /etc/riverview/pgpass`; `systemctl cat riverview-baseline.service` (no credential contents) | Correct path/owner/mode under existing authority; provision only an absent file using secure terminal helper; clear conflicting environment; restart probe |
| database | Read-only TCP connection, expected DB/role and scoped privileges | DATABASE_UNAVAILABLE / DATABASE_IDENTITY_MISMATCH / EXCESS_DATABASE_PRIVILEGE / READ_ONLY_REQUIRED / DEPENDENCY_MISSING | `systemctl is-active postgresql`; `pg_lsclusters`; `.venv/bin/python -c 'import psycopg; print(psycopg.__version__)'` | Restore dependency or reviewed permissions; no password resets or public schema changes; restart probe |
| schema | Existing riverview_dev owner and USAGE/CREATE | SCHEMA_MISSING / SCHEMA_AUTHORITY_MISMATCH | Authorized DBA queries pg_namespace/has_schema_privilege; do not initialize via PostgresLedger constructor | Reconcile with prior baseline evidence; reviewed schema repair only; restart probe |
| ready / observer | Fresh rv.runtime-baseline.v1 with observed/expiry time | REPORT_UNAVAILABLE / stale / nonzero probe | Independent report consumer; check clock and unit result | Diagnose missing/partial report, then refresh probe; never call expired evidence healthy |
| Acceptance | Two successful fresh distinct observations from package SHA | BLOCKED / source mismatch / repeated old timestamp | Read saved acceptance JSON and SOURCE_COMMIT | Repair same step, capture a new uniquely named report, retain failed artifacts |
| Steward hold | Explicit decision on acceptance and later dependent DoD gates | PENDING_STEWARD; full DoD NOT_DONE | Review acceptance matrix and blocker register | Steward decision recorded; do not move cursor automatically |

Database exceptions deliberately expose no raw text. If authentication needs
deeper inspection, use an approved DBA channel on Camrui, not chat or ordinary
logs. Do not print pgpass, dump environments, collect full credential-bearing
unit environments, delete WAL or modify assignments to make diagnostics pass.

## Verified-predecessor rollback procedure

Use the exact root-owned backup directory printed by the installer. The helper
checks the saved unit SHA-256 before restoring it, serializes against installation,
stops only this diagnostic, restores the prior code link/unit (or removes those
introduced by a first install), and reloads systemd. It retains accounts,
credentials, releases, state and backups; never touches PostgreSQL.

```bash
sudo sh /opt/riverview-core/deploy/rollback_baseline.sh /var/backups/riverview-baseline.XXXXXXXX
```

If a prior baseline unit existed, explicitly start it and inspect its result.
Verify the restored unit bytes against the recorded checksum and confirm the
symlink equals `previous.release`. No prior baseline means the unit should be
absent. Do not claim a live rollback drill until these operations actually run
on Camrui. Take an approved second protected off-host copy of critical deployment
predecessors before replacement; no secrets are included in the rollback archive.

## Blocker handling and resume policy

Every diagnostic returns or times out within its declared bounds: DB connect 5s,
systemd start 20s, SSH 30s. Operations owns configuration and dependency blockers;
Steward owns acceptance and sequencing. Durable commissioning blockers are retained
in timestamped acceptance files; operator sees terminal outcome, no automatic SMS
delivery is claimed. Credential renewal requires secure authorized update, not
a chat secret. After correction, repeat the same probe and retain a new report.
The later M1.3/M2.4/M3.2 components must supply institutional event persistence,
continuous monitoring and notification/resume contracts; this commissioning CLI
does not substitute for them.

## Revision history

- 1.0.0: Initial node diagnostics, recovery, bounded waits and preserved rollback.
