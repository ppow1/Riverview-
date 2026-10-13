<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/M4.1-DB-BOUNDARY/20261011T072000Z-fresh-schema-ledger/checkout.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Record fresh-schema authority migration defect correction and isolated verification
Authority: Isolated test evidence only; live authority provisioning remains unperformed
Changed: 2026-10-11 UTC | RV-M4.1-FRESH-SCHEMA-MIGRATION-LEDGER | Record empty-schema acceptance and full-suite evidence
History: artifacts.json SHA-256 manifest
-->
# Fresh-schema authority migration verification

- Task: `RV-M4.1-FRESH-SCHEMA-MIGRATION-LEDGER`
- Code base before fix: `2efaedf115ce7bef5d7fa25bc57d99f43e96f8a1` on `codex/m4.1-db-privilege-boundary`.
- Defect: authority migration tests previously reused a Core migration ledger. A fresh dedicated authority-only schema has none, while the authority migration runner requires checksums.
- Change: idempotent `0000_authority_migration_ledger.sql` creates the checksum ledger before `0001_institutional_authority.sql`; fixture now starts from an empty schema and checks rerun idempotency.
- Focused contract: `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN=<private socket-only PostgreSQL 16.15> python3 -m unittest tests.test_institutional_authority -v` — 7 passed, zero failures/errors/skips (see complete suite log).
- Full suite: `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN=<private socket-only PostgreSQL 16.15> python3 -m unittest discover -s tests -v` — 137 passed, zero failures/errors/skips in 57.235 s.
- Isolated PostgreSQL fixture cleanup: 0 disposable schemas and 0 fixture roles; private server stopped; its socket is absent. No Camrui shared schema/role/credential/service changed.
- Canonical graph generation/check: PASS, 12 workflows / 228 nodes. Controlled revision audit: PASS, zero findings. Compileall: PASS.
- Evidence artifacts and SHA-256 values: `artifacts.json`.
- Live M4.1 commissioning remains open: current read-only catalog has no dedicated authority schema/roles; no shared apply or deployment was performed. M3.3 stays the earliest unaccepted roadmap milestone.
