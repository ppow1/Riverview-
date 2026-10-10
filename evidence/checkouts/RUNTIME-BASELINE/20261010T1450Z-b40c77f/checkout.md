# RV-M1.1-010 checkout evidence

**Document Revision:** 1.0.0
**Task:** RV-M1.1-010
**Component:** RUNTIME-BASELINE
**Host:** Camrui (local hostname: admin1-Default-string)
**OS:** Ubuntu 24.04.3 LTS
**User:** admin1
**Source commit:** `b40c77fdca48c556af9d25a8cd25e7ca192b9748`
**UTC evidence time:** 2026-10-10T14:51Z

## Verification

- Focused runtime suite: 26 tests passed.
- Full command: `RIVERVIEW_TEST_PG_DSN=<isolated Unix socket> PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- Full result: 52 tests passed; zero failures and skips. All three PostgreSQL integration tests ran.
- Test cluster: temporary PostgreSQL 16 under `/tmp`, private mode-0700 directory, socket-only (`listen_addresses=''`), no TCP listener.
- Cleanup: zero `rvtest_%` schemas remained; temporary cluster and data directory removed.
- `python3 -m py_compile scripts/runtime_baseline.py`: PASS.
- `systemd-analyze verify deploy/systemd/riverview-baseline.service`: PASS.
- `git diff --check`: PASS.
- Package source commit: `b40c77fdca48c556af9d25a8cd25e7ca192b9748`.
- Package SHA-256: `bedf5f94e0ae0cb107fb7d2ce69eab37f8eb9cc709b0fa05d0933fe79e7025ab`.
- Package manifest and shell compatibility: PASS.

The full test log and verifier JSON have checksums in the adjacent `artifacts.json`
sidecar. No live Riverview database, existing credential, or privileged configuration
was modified during this checkout. Live service commissioning remains pending the
root-authorized package-policy bootstrap.
