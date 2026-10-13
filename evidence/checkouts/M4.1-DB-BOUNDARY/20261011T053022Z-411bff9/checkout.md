# M4.1 isolated database boundary verification

- Task: `RV-M4.1-DB-BOUNDARY`
- Source commit: `411bff91f383f9a518cd5fda8116e6cbf7bc9c86`
- Branch: `codex/m4.1-db-privilege-boundary`
- Target: Camrui, Ubuntu 24.04; disposable PostgreSQL 16.15 cluster, Unix socket only, port 55482.
- Shared operational database: not targeted; no shared role, schema, migration, identity, grant, assignment, worker, or service changed.

## Commands and results

- `RIVERVIEW_TEST_PG_DSN='host=/tmp/rv-m33-knowledge-pg.wwN0Z0/socket port=55482 dbname=postgres user=admin1' PYTHONPATH=src python3 -m unittest discover -s tests -v` — **133 passed, 0 failures, 0 errors, 0 skips**.
- `python3 -m compileall -q src scripts tests` — exit 0.
- `python3 scripts/process_graph.py check` — **PASS**, 12 workflows / 226 nodes.
- `python3 scripts/revision_control.py check --baseline /tmp/rv-m33-baseline-inventory.json` — **PASS**, zero issues.
- Disposable cleanup query — `schemas=0`, `roles=0`; PostgreSQL cluster fast-stopped successfully.

The boundary integration test verifies a dry run, allowlisted transfer of nine authority relations to a NOLOGIN owner, safe reapplication, denial of runtime SELECT/INSERT/DROP with a distinct schema owner, manager authorization lookup, fail-closed runtime-schema-owner preflight, and a fixture-only proof that PostgreSQL allows schema-owner `DROP ... CASCADE`. It does not prove shared deployment, manager secret provisioning, live application integration, or assignment-path authorization.

## Operational disposition

**Isolated engineering: PASS. M4.1 live commissioning: NOT VERIFIED.** The shared Camrui schema remains owned by `riverview_core`, which fails the new schema-owner prerequisite. Do not run `--apply` against `riverview_dev`. A distinct migration/schema owner, protected authority-manager identity and service delivery, full protected backup plus restore rehearsal, and application compatibility plan remain required.
