# Riverview~ M1.1 local Camrui verification

**Document Revision:** 1.0.0
**Task:** RV-M1.1-004
**Component:** RUNTIME-BASELINE
**Timestamp UTC:** 2026-10-10T03:55:00Z
**Source commit:** `b15b093642f65f6de36c1b977571ae2b79f04850`
**Branch:** `codex/m1.1-runtime-commissioning`
**Target:** Camrui as confirmed by Steward; Ubuntu 24.04.3; login `admin1`; kernel hostname `admin1-Default-string`
**Outcome:** **BLOCKED — M1.1 not accepted**

## Execution-context finding

The SSH error was an incorrect execution assumption, not an M1.1 acceptance failure. The roadmap requires a reproducible database and schema test on Camrui. The Codex campaign requests a consolidated SSH runner “if needed”; no governing M1.1 criterion requires SSH back into the same host. The commissioning installer, systemd diagnostic, and acceptance collector can all run locally. SSH remains strict-host-key verified if an independent remote observer is used. The local alternative and separate Windows transfer path are documented in the component contract and cookbook.

## Host and read-only baseline

- `hostnamectl --static`: `admin1-Default-string`; `id`: `admin1`, uid 1000, in sudo group.
- Ubuntu 24.04.3 LTS; `systemd 255`; PostgreSQL 16.15, cluster `16/main` online; `pg_isready` accepts local socket connections; `systemctl is-active postgresql` is `active`.
- `riverview` OS account: absent. Runtime directories `/etc/riverview`, `/etc/riverview/pgpass`, `/var/lib/riverview`, `/opt/riverview-core`: absent. Runtime unit `LoadState=not-found`.
- No `RIVERVIEW_TEST_PG_DSN`, `RIVERVIEW_PG_DSN`, `PGPASSFILE`, or `/home/admin1/.pgpass` is available. No credential content was read.
- System Python has Psycopg 3.1.17; the installer provisions the declared 3.2.10 in a release-local venv.
- Read-only TCP identity/schema query as `riverview_core` failed with `fe_sendauth: no password supplied` (exit 2). Therefore database identity, role privileges, schema existence/owner/privileges, and authenticated TCP connectivity remain NOT VERIFIED. No database objects were changed.

## Verification evidence

| Activity | Result | Retained artifact |
| --- | --- | --- |
| `PYTHONPATH=src python3 -m unittest discover -s tests -v` | Exit 0; 36 total, 33 passed, 3 skipped, 0 failures | [combined test output](unittest-combined.log) |
| Skipped PostgreSQL tests | `RIVERVIEW_TEST_PG_DSN` is unset. Each test creates a unique `rvtest_<uuid>` schema, creates ledger tables, and drops the schema with `CASCADE` in teardown. No approved test DSN/credential is available; running these would modify database objects, so they were not forced. | `tests/test_postgres_ledger.py` |
| Deployment shell and Python compile checks | `sh -n` for installer/rollback and `py_compile` for commissioning scripts all exit 0 | Test command summary above; shell bytes are independently checked below |
| Exact package build | Exit 0 from committed source; package size 119070 bytes; SHA-256 `bdbc71e45512698611e5c78721c28871c67bdc19042f6b5c84b0b98c5fb94cf9` | [package](camrui-package.tar.gz) |
| Package verification | Manifest PASS; shell compatibility PASS; both shell files have zero CR bytes, CRLF, BOM and NUL | [verification JSON](package-verification.json) |
| Extracted-package preflight | All package checksums, both shell syntax checks pass; exit 0 | [preflight output](package-preflight.log) |
| Local runtime probe | Exit 2; sanitized `IDENTITY_MISSING` at step `identity`; it does not proceed to database access | [probe JSON](runtime-probe.json) |
| Independent report consumer | Exit 2; `REPORT_UNAVAILABLE` because no report exists | [observer JSON](observer.json) |

The raw test output, probe/observer JSON, package, package-verification JSON, and preflight output are preserved here. Their SHA-256 values and sizes are in [the sidecar artifact manifest](artifacts.json), whose manifest revision is 1.0.0.

## Authorization and remaining gates

No privileged configuration, credential, database object, or service was changed. Root is required for the exact commissioning command `sudo sh "$stage/deploy/install_baseline.sh"`: it creates/uses the `riverview` service identity, writes the versioned release under `/opt`, credential and state directories under `/etc/riverview` and `/var/lib/riverview`, installs the systemd unit, reloads systemd, and starts the diagnostic. It may install the pinned Python package. If the passfile is absent, it securely prompts for the existing DB password and creates the protected file; it does not reset that password. This command was not run because privileged system changes were not authorized.

After installation, root is also required for `sudo python3 /opt/riverview-core/scripts/capture_baseline_acceptance.py --output "/var/lib/riverview/acceptance-<UTC-stamp>.json"`; it starts the local unit twice and writes mode-0600 evidence. This was not run because the unit is absent. The actual rollback drill requires root and would stop/restore the systemd unit and release link; only its development tests and shell syntax were run.

**M1.1 step acceptance:** BLOCKED on authorized installation, secure use of the existing database credential, and successful live read-only database/schema checks. No external network observer is required by M1.1; the full component DoD external live-observer evidence remains PARTIAL because the independent consumer only observed `REPORT_UNAVAILABLE`.

**Full component Definition of Done:** NOT DONE. Live Steward dashboard (M3.1), persistent institutional processor (M1.3), and other component-level acceptance remain incomplete. No Steward acceptance is recorded. The roadmap cursor stays at M1.1; no M1.2 work was started.
