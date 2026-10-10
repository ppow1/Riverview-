# RV-M1.1-008 checkout evidence — deployed storage path diagnosis

**Document Revision:** 1.0.0  
**Task:** RV-M1.1-008  
**Component:** RUNTIME-BASELINE  
**Host:** Camrui, `admin1-Default-string`, Ubuntu 24.04.3  
**Repository baseline:** `0a0f1e1c02ca701ea880ae9bc2820036b7c69508`, branch `codex/m1.1-runtime-commissioning`  
**Date:** 2026-10-10 UTC

## Commands and observations

- `id`, `hostnamectl --static`, `/etc/os-release`: user `admin1` (UID 1000), host `admin1-Default-string`, Ubuntu 24.04.3.
- `systemctl show riverview-baseline.service ...`: unit loaded, failed with exit status 2; `User=riverview`, `Group=riverview`, `StateDirectory=riverview`, `StateDirectoryMode=0700`, `DynamicUser=no`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`; no root directory or bind path overrides.
- `getent passwd riverview`: UID 997, GID 984, nologin shell.
- `namei -l`, `stat`, and Python `lstat`/`resolve` on `/var/lib/riverview`: direct directory, owner 997:984, mode 0700, `resolve()==absolute()`.
- `namei -l /opt/riverview-core`: active code pointer is a symlink to the versioned release. The runtime storage check receives `/var/lib/riverview`, so this symlink is not used in the check.
- Installed `scripts/runtime_baseline.py` and checkout source SHA-256 both `dd043bfddb199189484b83f83a744f0595a498950576f4bbb5fe7ccbb77699b0`; active reported source commit is `3d7e58fc19ae38b6fd378fd0f0421ebb36fdb266`.
- `journalctl -u riverview-baseline.service`: only start/failure and `status=2/INVALIDARGUMENT`; the JSON diagnostic is mode-protected from `admin1`.
- `sudo -n -l`: `sudo: a password is required`. No attempt was made to bypass authentication, alter the service, or read protected report/credential files.

## Verification results

`PYTHONPATH=src python3 -m unittest discover -s tests -p test_runtime_baseline.py -v`: 22 passed, 0 failed.

`PYTHONPATH=src python3 -m unittest discover -s tests -v`: 41 run; 38 passed, 3 PostgreSQL integration tests skipped because `RIVERVIEW_TEST_PG_DSN` was not set. Prior RV-M1.1-006 evidence executed those integration tests successfully against an isolated disposable PostgreSQL cluster.

## Result and open gate

The currently deployed `UNSAFE_PATH` code has three possible causes. Host-context evidence eliminates wrong object type, wrong UID, and path-resolution mismatch outside the service namespace. The service-context predicate cannot be determined from the current coarse report or status-only journal. The change adds fixed, secret-free reason codes while preserving the `UNSAFE_PATH` contract and all security checks.

**M1.1 status: IN PROGRESS / BLOCKED.** The root cause is not yet proven or repaired; no new package has yet been installed. A scoped authorized install/run is required to obtain the enhanced service-context diagnostic. Do not advance to M1.2.
