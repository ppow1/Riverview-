# RV-M1.1-007 terminal provisioning and safe retry checkout

**Document Revision:** 1.0.0
**Task / component:** RV-M1.1-007 / RUNTIME-BASELINE
**Timestamp UTC:** 2026-10-10T13:16:15Z
**Source commit:** `3d7e58fc19ae38b6fd378fd0f0421ebb36fdb266`
**Host:** `admin1-Default-string`, Ubuntu 24.04.3, Python 3.12.3, PostgreSQL 16.15
**Actor:** Codex on Camrui

## Verification

The prior installer failure and partial host state are captured in `commissioning-failure.md`. The defect was reproduced with a pseudo-terminal by opening `/dev/tty` in text `r+` mode; Python raised `io.UnsupportedOperation: File or stream is not seekable`. Source now uses `getpass.getpass()` without a supplied stream and promotes `GetPassWarning` to an error. `test_password_prompt_reads_nonseekable_tty_without_echo` ran against a real controlling pseudo-terminal, passed with a generated runtime-only sentinel, and confirmed the terminal output contains no sentinel.

`test_installer_reuses_only_root_owned_directory_and_restores_read_access` passed; it checks release type/ownership guards and verifies permission normalization changes a private 0700 staging root/directories to 0755 and source files to 0644. The installer checks package checksums before normalizing access, rejects non-directory/symlink or non-root-owned release content, and strips group/other write bits.

Exact command for the full committed-tree test suite:

```sh
PYTHONPATH=src:scripts RIVERVIEW_TEST_PG_DSN="host=/tmp/rv-pgtest.uEU8h2I0/socket port=5432 dbname=postgres user=admin1" python3 -m unittest discover -s tests -v
```

Exit 0: 38 tests passed, 0 failures, 0 skips, including all three PostgreSQL integration tests. They ran against a disposable PostgreSQL 16.15 cluster bound only to a private Unix socket. Cleanup query result was `16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)||0`: no TCP listener and zero remaining `rvtest_%` schemas. The temporary cluster stopped successfully. Logs are attached; no credentials are present.

The first test-authoring iteration failed only because the PTY harness expected LF while PTY output uses CRLF. `test-harness-correction.md` records the observed assertion and fix; subsequent focused and full runs passed.

## Package

Built a new archive from committed source `3d7e58fc19ae38b6fd378fd0f0421ebb36fdb266` into a unique directory. It did not overwrite or modify the prior staged package. Archive SHA-256: `2b8dd82e9aca9618fb773d01e84e94ed9e4d49f5eadbae260d834a50154fa4f3`. Package verification reports `manifest=PASS` and `shell_compatibility=PASS`; both deployment shell files have zero CR, CRLF, BOM, and NUL bytes. All 102 staged package checksum entries passed, and both install/rollback scripts passed `sh -n`.

New staged package path on Camrui: `/tmp/rv-m11-007-stage-20261010T131615Z.L29BgZ`.

## Remaining commissioning and acceptance

The existing partial installation is still unchanged: service account and protected config directory exist; passfile, state directory, active symlink, and systemd unit remain absent. The fixed installer has not yet been run on Camrui. This checkout verifies software tests and package construction only; it does not claim service installation, live database authentication, systemd execution, rollback, external observation, or Steward acceptance. M1.1 remains BLOCKED pending interactive authorized installation and its actual acceptance evidence.
