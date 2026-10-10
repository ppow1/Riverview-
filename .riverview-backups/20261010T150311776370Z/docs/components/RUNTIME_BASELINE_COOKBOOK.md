# Riverview~ runtime baseline troubleshooting and recovery

**Document Revision:** 1.0.6
**Component:** RUNTIME-BASELINE
**Repair task:** RV-M1.1-010
**Task:** RV-M1.1-001
**Owner:** office:operations
**Status:** systemd credential ownership cause corrected; live commissioning and rollback NOT VERIFIED

## Consolidated read-only diagnostic

On Camrui, inspect only the selected unit properties and sanitized JSON. Run these commands in a local Camrui terminal; an SSH session is unnecessary when already on the host:

```bash
systemctl show riverview-baseline.service --property=User,Group,LoadState,Result,ExecMainStatus
sudo -n /usr/local/sbin/riverview-privctl report
sudo -n /usr/local/sbin/riverview-privctl service status
```

The report operation invokes the fixed sanitized reader from the root-owned
active release. Never invoke a checkout/staging script through sudo.

Optional remote diagnostic from a connected authorized development machine with a known SSH host key and noninteractive approved sudo for the reader (not a milestone acceptance requirement):

```bash
python scripts/check_camrui_baseline.py camrui
```

The optional runner is bounded to 30 seconds, uses BatchMode and strict host-key checking, rejects shell syntax in destinations and preserves remote failure status. A remote connection failure is not a Camrui commissioning failure when local execution is available. Do not weaken host-key checking or add broad sudo rights to make the optional path pass.
An expired report is intentionally stale: a request-driven baseline check does
not provide continuous health. Refresh only with `sudo -n
/usr/local/sbin/riverview-privctl service start`; no institution is dispatched.

M1.1 acceptance is based on local execution on Camrui: after authorized
installation, `sudo -n /usr/local/sbin/riverview-privctl accept` runs the unit
twice and retains sanitized results. SSH only transports a request from another
machine; it does not provide an independent database or runtime verification gate.

## Node-to-fault mapping

| Step | Expected input / action / evidence | Failure code or signal | First read-only diagnostic | Recovery / resume |
| --- | --- | --- | --- | --- |
| Package | Exact committed revision; checksums match | Dirty tree, unsafe archive path, checksum mismatch | Compare builder source SHA/archive SHA and `sha256sum -c PACKAGE_SHA256SUMS` | Rebuild from intended commit; never override checksums; restart package stage |
| Shell preflight | LF-only exact blob bytes and Linux syntax | `set: Illegal option -`, CRLF/BOM/NUL or shell parse error | `python3 scripts/verify_camrui_package.py <archive>` and `sh -n` for both scripts | Keep failed artifact; update PR branch and rebuild with repaired builder; new staging directory, no host text edits |
| Commissioning | Authorized root; exact package manifest; reusable release root-owned and service-readable | Existing non-symlink deployment, lock held, non-root-owned/invalid partial release | Inspect active link and root-only rollback record/checksums; stat the release path without reading credentials | Preserve invalid/untrusted release; do not delete it automatically. For a verified root-owned release, use the corrected installer to normalize read/traverse permissions and continue; it retains file bytes and rejects ownership mismatch |
| identity | OS riverview, nonroot, nologin, systemd User=riverview | IDENTITY_MISSING / IDENTITY_MISMATCH / INTERACTIVE_SERVICE_ACCOUNT | `getent passwd riverview`; selected unit properties | Correct authorized commissioning; never run institution as root; restart probe |
| storage | Private directory owned by runtime account | PATH_UNAVAILABLE / UNSAFE_PATH / UNSAFE_MODE; sanitized `path_failure_reason` distinguishes `symlink_in_path`, `unexpected_file_type`, and `owner_uid_mismatch` | `stat -c '%U:%G %a %F' /var/lib/riverview`; compare with the fresh probe report from inside the service unit | Do not infer the failing predicate from host metadata alone. Compare the service-context reason with systemd's `User`, `Group`, `StateDirectory`, and `StateDirectoryMode`; repair only the demonstrated mismatch, preserve path checks, then rerun |
| credential | Fresh systemd credential from protected root source; absent passfile is captured through getpass controlling TTY with echo disabled | CREDENTIAL_MISSING / CREDENTIAL_UNREADABLE / UNSAFE_PATH / UNSAFE_MODE / AMBIENT_DATABASE_OVERRIDE; TTY I/O error fails before file creation | Stat only metadata; never read credential contents | Validate PID 1 source as root-owned 0550/0440; copy through no-follow/exclusive descriptors into private runtime storage as service-owned 0700/0600; pass only that copy to libpq |
| database | Read-only TCP connection, expected DB/role and scoped privileges | DATABASE_UNAVAILABLE / DATABASE_IDENTITY_MISMATCH / EXCESS_DATABASE_PRIVILEGE / READ_ONLY_REQUIRED / DEPENDENCY_MISSING | `systemctl is-active postgresql`; `pg_lsclusters`; `.venv/bin/python -c 'import psycopg; print(psycopg.__version__)'` | Restore dependency or reviewed permissions; no password resets or public schema changes; restart probe |
| schema | Existing riverview_dev owner and USAGE/CREATE | SCHEMA_MISSING / SCHEMA_AUTHORITY_MISMATCH | Authorized DBA queries pg_namespace/has_schema_privilege; do not initialize via PostgresLedger constructor | Reconcile with prior baseline evidence; reviewed schema repair only; restart probe |
| ready / observer | Fresh rv.runtime-baseline.v1 with observed/expiry time | REPORT_UNAVAILABLE / stale / nonzero probe | Independent report consumer; check clock and unit result | Diagnose missing/partial report, then refresh probe; never call expired evidence healthy |
| Acceptance | Two successful fresh distinct observations from package SHA | BLOCKED / source mismatch / repeated old timestamp | Read saved acceptance JSON and SOURCE_COMMIT | Repair same step, capture a new uniquely named report, retain failed artifacts |
| Steward hold | Explicit decision on acceptance and later dependent DoD gates | PENDING_STEWARD; full DoD NOT_DONE | Review acceptance matrix and blocker register | Steward decision recorded; do not move cursor automatically |

Database exceptions deliberately expose no raw text. If authentication needs
deeper inspection, use an approved DBA channel on Camrui, not chat or ordinary
logs. Do not print pgpass, dump environments, collect full credential-bearing
unit environments, delete WAL or modify assignments to make diagnostics pass.

## Failed terminal prompt and safe commissioning retry

RV-M1.1-007 reproduced io.UnsupportedOperation: File or stream is not seekable when a text wrapper was opened on /dev/tty and passed as getpass output. The helper now calls getpass.getpass() without a caller-supplied stream; Python opens and controls the terminal directly. GetPassWarning is treated as an error, so input never falls back to echoed stdin. A failed prompt occurs before exclusive passfile creation; do not inspect or print credential contents.

## UNSAFE_PATH root cause and correction

The persisted `UNSAFE_PATH` / `step_id=storage` report was misleading about which
path had failed. The service-owned `/var/lib/riverview` passed its exact lstat,
resolve, owner, type and mode checks inside the service sandbox. The later call
checked `CREDENTIALS_DIRECTORY`'s parent using the same runtime-UID directory
rule. On this host PID 1 creates that directory root-owned mode 0550 and the
credential file root-owned mode 0440; systemd grants the service read/traverse
access. The generic directory helper therefore rejected the expected owner.

The corrected implementation keeps private state UID/mode checks unchanged and
uses a separate systemd-credential validator: fixed credential location, no
symlinked path, root-owned directory mode 0550, root-owned regular file mode
0440, nonempty content, and actual service read access. It does not read or log
credential bytes. Regression tests cover the observed ownership contract and
reject an unexpected credential location. Host execution must still verify the
real unit and database result before M1.1 acceptance.

Libpq rejects systemd's correctly root-owned 0440 source because it requires
mode 0600 or stricter. The service therefore copies it without logging into its
service-owned, mode-0700 systemd RuntimeDirectory as a service-owned 0600 file.
Creation is exclusive and rejects symlinks or an existing destination;
systemd removes the directory after the oneshot stops. Password contents never
enter logs or diagnostics.

A retry after that prompt failure is safe when read-only inspection confirms the known partial state: the riverview system account exists with a non-login shell; /etc/riverview is root-owned mode 0700; /etc/riverview/pgpass is absent; the attempted versioned release is a root-owned directory; /var/lib/riverview, /opt/riverview-core, and the service unit are absent. Use a fresh, verified package and rerun the installer. It reuses the account and exact release, rejects a symlink/non-directory or non-root-owned release, makes files readable and directories traversable for the service, and strips group/other write access before continuing. It does not overwrite an existing passfile. Never edit the failed staged package or delete the partial release. If ownership differs, stop and retain it for diagnosis.

The installer creates the state directory, unit, active symlink and rollback record only after credential provisioning succeeds. If a later service start fails, retain the emitted rollback record and use the documented verified-predecessor recovery procedure; a new authorized run will preserve the current unit/link as its rollback predecessor.

## Failed Windows package diagnosis

A manifest PASS proves agreement with archived bytes, not Linux compatibility.
The old builder called `git archive`, which converts LF blobs to CRLF under
`core.autocrlf=true`. `set -eu\r\n` makes dash interpret CR as an invalid option.
Read actual archived bytes with `scripts/verify_camrui_package.py` on Windows or
Linux; it reports manifest status separately from shell compatibility and prints
line 15 in hex. Expected `set -eu` with LF: `736574202d65750a`; the reproduced
failure is `736574202d65750d0a`. Both installer and rollback are affected by the
old packaging path. Do not run rollback from a known-invalid package. Rebuild the
corrected committed package; do not edit files after manifest verification.

## Verified-predecessor rollback procedure

Use the exact root-owned backup directory printed by the installer. The helper
checks the saved unit SHA-256 before restoring it, serializes against installation,
stops only this diagnostic, restores the prior code link/unit (or removes those
introduced by a first install), and reloads systemd. It retains accounts,
credentials, releases, state and backups; never touches PostgreSQL.

```bash
sudo -n /usr/local/sbin/riverview-privctl rollback riverview-baseline.XXXXXXXX
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

- 1.0.5: Record proven systemd credential ownership mismatch, safe predicate split and scoped broker usage; predecessor `.riverview-backups/20261010T142904528427Z/docs/components/RUNTIME_BASELINE_COOKBOOK.md`.
- 1.0.6: Document libpq mode-0600 requirement and isolated runtime copy; predecessor is recorded under RV-M1.1-010 in `.riverview-backups/manifest.jsonl`.

- 1.0.3: Explain non-seeking hidden TTY capture and validated partial-install retry; predecessor under docs/history/RV-M1.1-007/rev1.0.2/docs/components/RUNTIME_BASELINE_COOKBOOK.md.

- 1.0.2: Document local Camrui diagnostics and distinguish optional SSH transport from milestone acceptance; predecessor under docs/history/RV-M1.1-004/rev1.0.1/docs/components/RUNTIME_BASELINE_COOKBOOK.md.
- 1.0.1: Add artifact-byte diagnosis and package preflight; preserve original under docs/history/RV-M1.1-002/rev1.0.0.
- 1.0.0: Initial node diagnostics, recovery, bounded waits and preserved rollback.
