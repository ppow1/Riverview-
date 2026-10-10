# Riverview~ M1.1 checkout — live commissioning blocked

**Document Revision:** 1.0.0
**Task:** RV-M1.1-003
**Component:** RUNTIME-BASELINE
**Timestamp UTC:** 2026-10-10T03:41:42Z
**Source commit:** `892b4893a584bd5a6aefbcac7e73bedbc5f53314`
**Branch:** `codex/m1.1-runtime-commissioning`
**Execution host:** `admin1-Default-string`; Ubuntu 24.04.3; Linux x86_64; Python 3.12.3
**Outcome:** **BLOCKED** — development checkout verified; live Camrui commissioning unavailable; M1.1 not accepted.

## Scope and baseline

Reused the existing M1.1 commissioning implementation, repair history, and development evidence on the tracked feature branch. The checkout was clean before this record was added. PostgreSQL 16.15 cluster `16/main` is online and `pg_isready` reports accepting connections. The checkout is not identified as the commissioned Camrui host: its hostname is `admin1-Default-string`.

Read-only filesystem checks found no `/etc/riverview`, `/etc/riverview/pgpass`, `/var/lib/riverview`, or `/opt/riverview-core`. `getent passwd riverview_core` and `getent group riverview` returned no account/group. The M1.1 runtime identity specified by the component contract is `riverview`; no account was created. No database password was read, requested, reset, or delivered. The development checkout `/home/admin1/riverview-core` was not modified.

## Executed verification

| Command / check | Result |
| --- | --- |
| `hostnamectl --static; uname -a; id` | `admin1-Default-string`; Linux x86_64; caller `admin1` (uid 1000), no `riverview` account |
| `cat /etc/os-release` | Ubuntu 24.04.3 LTS |
| `pg_lsclusters; pg_config --version; pg_isready` | PostgreSQL 16.15; cluster `16/main` online; local socket accepts connections |
| `systemctl is-active postgresql` | `active` (Ubuntu aggregate unit reports `active (exited)`) |
| `PYTHONPATH=src python3 -m unittest discover -s tests -v` | Exit 0; 36 tests, 33 passed, 3 skipped (PostgreSQL DSN absent), 0 failed |
| `sh -n deploy/install_baseline.sh && sh -n deploy/rollback_baseline.sh` | Exit 0 |
| `python3 scripts/runtime_baseline.py` | Exit 2; sanitized JSON reports `IDENTITY_MISSING` at step `identity`; no credential read |
| `python3 scripts/read_baseline_report.py` | Exit 2; sanitized JSON reports `REPORT_UNAVAILABLE`; no report or state directory exists |

An initial `python3 -m unittest discover -s tests -v` invocation without the documented `PYTHONPATH=src` failed with one import error (`ModuleNotFoundError: riverview_core`), 30 passing tests and 3 PostgreSQL skips. Re-running with the documented import path passed. Both outputs are retained in this record; the initial failure was invocation configuration, not a code failure.

## Access and commissioning blockers

| Blocker | Observed signal | Owner / authority | Resume condition |
| --- | --- | --- | --- |
| `M11-HOST-IDENTITY` — execution host | Current host reports `admin1-Default-string`; it does not establish the documented Camrui identity | Operations; authorized host operator | Confirm target host identity and use its existing approved access path |
| `M11-CAMRUI-SSH` — dependency | `ssh ... camrui true` failed exit 255: hostname could not be resolved. The documented IP `192.168.1.155` failed strict host-key verification because no ED25519 key is known | Operations; administrator of Camrui / trusted host-key source | Restore/provide the established alias or verify the host key through a trusted channel; do not disable strict checking |
| `M11-LOCAL-PRIVILEGE` — permission | `sudo -n -u postgres ...` failed because a password is required | Operations; existing authorized sudo operator | Execute the read-only ownership checks and approved commissioning on the intended Camrui terminal |
| `M11-CREDENTIAL` — commissioning | Protected passfile and runtime state paths are absent on this checkout; no interactive secure credential prompt is available | Operations; existing database credential custodian | On Camrui, use the package’s non-echoing terminal provisioning flow only if the existing passfile is absent; never reset the DB role |

No remote shell command or privileged installation ran. A local `psql -d riverview` read-only identity query failed exit 2 because PostgreSQL has no local role named `admin1`. No schema, database, role, credential, service unit, or deployed file was changed. `riverview_dev` existence/ownership/privileges and authenticated TCP login remain **NOT VERIFIED in this execution**; historical readiness evidence cited in the existing cookbook remains historical evidence only.

## Acceptance and Definition of Done

M1.1 remains **BLOCKED / NOT DONE**. The local development package and shell syntax passed; actual Camrui runtime identity, persistent secure credential delivery, schema permissions, TCP authentication, systemd behavior, and rollback have not been exercised here. Steward acceptance is pending. Component live Steward visualization remains a documented M3.1 dependency; the JSON diagnostic is not described as a dashboard. No M1.2 work was started.

This record does not change the roadmap cursor. Continue M1.1 after the specific host identity, trusted SSH access, and authorized commissioning path are available. Existing branch records retain previous failures and packaging repair details.
