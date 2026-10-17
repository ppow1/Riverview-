<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/M4.1-DB-BOUNDARY/20261011T080100Z-owner-schema-usage/checkout.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Preserve M4.1 table-owner FK ACL defect diagnosis and isolated verification
Authority: Private socket-only PostgreSQL test cluster; no Steward identity or shared app rows written
Source: Working tree based on 9b5dc84bf452c16d9bf46dc5884dc5ace529b0c4
History: artifacts.json SHA-256 manifest
-->
# M4.1 protected owner schema USAGE correction

## Finding

On Camrui's additive `riverview_authority` installation, the manager had schema
`USAGE` and SELECT/INSERT/UPDATE/DELETE on the nine authority tables. The
separate NOLOGIN relation owner owned those tables but did not have schema
`USAGE`. A rollback-only `AuthorityRegistry.bootstrap_steward` attempt failed
at credential insertion; it rolled back and wrote no identity, grant or token.
The exact SQLSTATE was 42501 on PostgreSQL's FK check of
`institutional_principals`. A same-transaction raw FK insert reproduced it.

The least-privilege correction grants the protected table owner schema `USAGE`
only. Runtime usage remains denied; manager DML remains table-allowlisted; the
manager is not a member of the owner; schema CREATE remains denied to manager
and owner. The provisioner verifies these conditions after apply.

## Isolated verification

The test used a disposable socket-only PostgreSQL 16.15 cluster at a unique
temporary path. It did not connect to the shared `riverview` database. The
test covers credential, grant and authority-event FK checks through the
manager, runtime denial, manager DDL denial, role isolation, and idempotent
provisioner apply.

- Focused boundary module: **3/3 passed**, zero skips/errors after a test SQL
  template correction. The first run exposed an unescaped JSON object literal
  in Psycopg's SQL formatter; the test fixture was corrected and rerun.
- Complete applicable suite: **147/147 passed**, zero skips/failures/errors in
  64.183 seconds. See `full-suite.log`.
- Fixture cleanup: **0** `rvtest_*` schemas and **0** `rvtest_*` roles. See
  `fixture-cleanup.txt`.
- Canonical graph check: **13 workflows, 255 nodes, PASS**; graph validate PASS.
- Controlled revision audit against the repository baseline: PASS, zero issues.
- Python compileall: PASS.
- PostgreSQL test cluster was stopped and `pg_ctl status` confirmed no process.

## Live deployment boundary

The corrected live re-apply, final runtime denial checks, and one-time Steward
bootstrap have not yet been run. The live bootstrap token remains absent. The
previous deployed M1.1/M1.2/M2 services and shared operational data were not
modified by the isolated test. Do not treat this evidence as M4.1 commissioning
or authorization-service acceptance.

## Changed controlled source SHA-256

- `src/riverview_core/institutional_authority/db_boundary.py`:
  `36c57e9304be6d497d8f3faf077199ec5d230034de7c518da6c09ab9bf2f2695`
- `tests/test_institutional_authority_boundary.py`:
  `1211ae044167ae14e4e8e1cf1f4f88ba32b5ebcab0c5f682bde8605db96faa44`
- `docs/components/INSTITUTIONAL_AUTHORITY.md`:
  `2b2c717e2293cb6be64385cee98c92ca5a9ecf0799f147f0ca62165ede26d77f`
- `docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md`:
  `30a22d204efa586c0f23b26da5c9b15eb9b179289883a01b83194a2b4431cede`
- `docs/development/M4.1-001_REVISION_RECORD.md`:
  `c186ffe3713aa4cc469cdb29e07aba1c2d42733ca575ccd4cb39f5af2fab9bf7`
