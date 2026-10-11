<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/M4.1-RESIDENT-RUNTIME/20261011T191004Z-27d18cc/checkout.md
Component: INSTITUTIONAL-AUTHORITY / RESIDENT-ORCHESTRATION
File Revision: 1.0.0
Purpose: Record isolated M4.1 persistent resident-runtime integration verification
Changed: 2026-10-11 UTC | RV-M4.1-PERSISTENT-RESIDENT-RUNTIME | Preserve exact test and gate outcomes
Authority: Isolated test fixtures only; no shared-state commissioning
-->
# M4.1 persistent resident-runtime integration evidence

**Status:** PASS — isolated engineering verification only; live commissioning NOT VERIFIED.

- Starting source commit: `27d18cc15fbc8d6c093014709f6cfe5c04b3cfb6`
- Branch: `codex/grace-persistent-execution`
- Environment: Camrui Ubuntu 24.04, Python 3.12.3, PostgreSQL 16.15
- Test command: `RIVERVIEW_TEST_PG_DSN='host=<private-socket> port=55493 dbname=postgres user=admin1' PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Result: 213 tests passed, zero failures/errors/skips, 73.539 seconds.
- Test DB: socket-only private PostgreSQL cluster under `/tmp`; post-run `rvtest_*` schema count was 0; cluster stopped.
- New regression: persistent service was reconstructed with the replacement office occupant/provider; it recovered the office-keyed prior plan and updated binding revision. A deliberately re-issued exact grant to the former occupant was rejected before provider invocation and its direct office-state write was denied.
- Existing test suite also exercised stale binding, revoked grants, state CAS, objective persistence, service restart, execution retry and independent verification.
- Process graph: 16 workflows / 333 nodes, check PASS.
- Controlled revision audit: PASS, zero findings.
- Python compileall and `git diff --check`: PASS.

This is test evidence, not live resident service deployment, real model inference, Camrui credential provisioning, live restart/replacement commissioning, external observation, M4.1 acceptance, or full Component DoD. No OCTO1/model endpoint, shared PostgreSQL schema, shared service, or credential was accessed or modified.
