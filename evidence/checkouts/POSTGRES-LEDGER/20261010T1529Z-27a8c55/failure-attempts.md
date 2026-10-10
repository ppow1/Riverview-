# Riverview~ RV-M1.2-001 failed-attempt record

**Document Revision:** 1.0.0
**Task:** RV-M1.2-001
**Component:** POSTGRES-LEDGER
**Source under test:** pre-commit M1.2 working tree based on `c24d760`
**Environment:** Camrui; disposable PostgreSQL 16 cluster; no shared-schema writes

## Attempt 1 — migration runner row shape

**Result:** FAIL; all five then-existing PostgreSQL cases errored before schema
migration. `apply_migrations()` indexed cursor results by column name but opened a
connection with Psycopg's default tuple row factory. Exact exception:

`TypeError: tuple indices must be integers or slices, not str`

**Correction:** use `psycopg.rows.dict_row` for the migration connection. The
six-test suite subsequently exercised the migration path successfully.

## Attempt 2 — disposable test cluster encoding

**Result:** FAIL; the cluster was initialized with `initdb --no-locale` and no
explicit encoding, so it used SQL_ASCII. Psycopg returned PostgreSQL text as
`bytes`, causing one assertion mismatch (`b'grant:engineering'` vs
`'grant:engineering'`), byte-key state lookup errors (`KeyError: b'queued'`),
an idempotency replay collision from byte-valued JSON strings, and a migration
checksum comparison between `bytes` and text. This was an invalid test
configuration, not the commissioned Camrui database encoding.

**Correction:** create the disposable cluster with explicit `--encoding=UTF8`.
The final committed-source run passed all 53 repository tests with all six
PostgreSQL tests executing. Both temporary clusters and all per-test schemas
were removed. No run touched `riverview_dev`.
