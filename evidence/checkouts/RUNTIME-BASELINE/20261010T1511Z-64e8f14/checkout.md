# RV-M1.1-011 final installed-package evidence

**Document Revision:** 1.0.0
**Task:** RV-M1.1-011
**Component:** RUNTIME-BASELINE
**Host:** Camrui (`admin1-Default-string`), Ubuntu 24.04.3, user `admin1`
**UTC:** 2026-10-10 15:11Z
**Branch:** `codex/m1.1-runtime-commissioning`
**Source commit:** `64e8f14ad6d71102a864755739a1c8a61506235c`

A final package was rebuilt from the latest clean commit so the deployed release
includes the corrected runtime contract and acceptance instructions. The commit
adds documentation and evidence after the code fix; runtime code is unchanged
from a2b94e2. Archive SHA-256:
`0635519b4b3de40b5b10e6935fc370e6276ba685046dfdbc73c86e7f8a4c28a8`.
Package manifest and Linux shell compatibility passed. Installer rerun suite
passed; its three PostgreSQL ledger tests are intentionally skipped without a
DSN. All 45 tests, including those three, passed against isolated PostgreSQL in
the linked preceding checkout `20261010T1508Z-a2b94e2`.

Deployment created immutable release
`/opt/riverview/releases/64e8f14ad6d71102a864755739a1c8a61506235c` and set
`/opt/riverview-core` to it. `riverview-baseline.service` returned success/exit
0 and runs as `riverview`. The live report is fresh and ready, identifies
`riverview` host account, `riverview_core` database role, `riverview` database,
`riverview_dev` schema, and this source commit. Acceptance collector executed two
distinct successful observations and reported `PENDING_STEWARD`.

The broker helper, policy and registry are absent; no broker sudoers entry is
present. Owner-authorized unrestricted sudo remains effective. PostgreSQL and
credential state were not changed by this documentation-only redeployment.

**Disposition:** M1.1 technical roadmap acceptance PASS. Steward acceptance and
sequencing remain pending; M1.2 is gated. Full project and component DoD are not
claimed complete.
