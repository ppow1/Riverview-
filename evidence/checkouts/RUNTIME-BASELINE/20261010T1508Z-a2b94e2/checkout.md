# RV-M1.1-011 checkout and live acceptance evidence

**Document Revision:** 1.0.0
**Task:** RV-M1.1-011
**Milestone:** M1.1, Camrui runtime baseline and PostgreSQL readiness
**Component:** RUNTIME-BASELINE
**Host:** Camrui (`admin1-Default-string`), Ubuntu 24.04.3, user `admin1`
**UTC:** 2026-10-10 15:08Z
**Branch:** `codex/m1.1-runtime-commissioning`
**Source commit:** `a2b94e24715a670262859e1af31a0ea417ed37cb`

## Package and code

Built with `python3 scripts/build_camrui_package.py` from the clean committed source.
Archive SHA-256: `069020e6e5e9a540cc7f063cc88a070b9cc54d0d27fd23ddedd01b1b8649a3eb`.
`verify_camrui_package.py`: manifest PASS, shell compatibility PASS, source commit
exact. Runtime now normalizes PostgreSQL inet host address with
`host(inet_server_addr())`; regression test asserts this expression. No password
is embedded or emitted.

## Tests

`PYTHONPATH=src RIVERVIEW_TEST_PG_DSN="host=<private temporary socket> port=55439 dbname=postgres user=admin1" python3 -m unittest discover -s tests -v`
passed 45/45 with zero skips against an isolated socket-only disposable PostgreSQL
16 cluster. No `rvtest_%` schemas remained; the cluster was stopped. The installer
repeat suite passed 45 tests with three PostgreSQL cases skipped because its test
DSN was deliberately unset; the isolated full run executes those cases.

`git diff --check`, Python bytecode compilation, package checksum verification,
and `systemd-analyze verify` passed.

## Live Camrui checks

- PostgreSQL service active; read-only SQL observed role `riverview_core`, database
  `riverview`, server address `127.0.0.1`, and transaction read-only `on`.
- Installed service ran as `riverview`; systemd result success, exit 0.
- Sanitized baseline: `baseline_ready=true`, step `ready`, schema `riverview_dev`,
  schema owner `riverview_core`, matching source commit.
- Acceptance collector executed the service twice and retained two distinct fresh
  successful observations; output status `PENDING_STEWARD`.
- Independent freshness-aware report consumer returned current ready JSON.
- systemd restart returned success and renewed the report.
- Rollback checksum passed; exact predecessor restoration and its expected failure
  were observed; package redeployment returned the host to current ready state.
- Broker helper, policy and registry are absent; no broker sudoers rule exists.
  Owner-authorized unrestricted sudo and `visudo -c` remain verified.
- Credential remains root:root mode 0600; state directory remains riverview:riverview
  mode 0700. No credential content was read or changed.

## Disposition and limitations

M1.1 roadmap's technical PASS criterion is satisfied. Steward acceptance and its
sequencing decision are pending; M1.2 is not started. Component Definition of Done
is NOT DONE: later persistent processing, independent institutional verification,
and live Steward dashboard are outside this commissioning slice and remain roadmap
work. This is not a claim of project completion.
