# M4.1 resident-runtime isolated checkout

- Evidence ID: RV-M4.1-RUNTIME-API-VERIFICATION-20261011T192400Z
- Branch: `codex/grace-persistent-execution`
- Source implementation commit: `79ec48140aca1111b4ccfb88b0dd845eec09fb7f`
- Test baseline commit: `27d18cc15fbc8d6c093014709f6cfe5c04b3cfb6`
- Full suite command: `RIVERVIEW_TEST_PG_DSN=<private socket-only PostgreSQL 16.15> PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Result: **214 passed, 0 skipped, 0 failures, 0 errors** in 75.839 seconds.
- The suite ran on the implementation tree later committed as the source commit above. The canonical graph then received one evidence-label update; the updated graph was checked and its 13 focused tests passed separately.
- PostgreSQL was a temporary private cluster under `/tmp`, not the shared or live Camrui database. See `isolated-postgres.log`.
- No model endpoint was called; no live credential, service, migration, or shared database was changed.
- Live resident-service commissioning and M4.1 acceptance are **not verified**.
