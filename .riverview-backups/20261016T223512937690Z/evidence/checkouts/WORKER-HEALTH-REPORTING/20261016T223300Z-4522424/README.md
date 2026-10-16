# RV-WORKER-HEALTH-REPORTING-001 isolated checkout evidence

Source baseline: integration commit `4522424e625ea1754d0b94ab0b4f89bc4646529d`.
Environment: isolated local checkout, Firefox fixture (synthetic responses; no production mutation).

- `browser-acceptance.json`: detailed browser checks, request boundaries, worker row text, and errors.
- `worker-inventory.png`: isolated rendered dashboard evidence.
- `status-dashboard-tests.log`: dashboard suite output; PostgreSQL-backed tests skipped because `RIVERVIEW_TEST_PG_DSN` was not configured.
- `process-graph-check.json`: canonical graph validation result.
- `revision-audit.json`: controlled revision audit result.

Production observation on 2026-10-16: five active registry rows had two stale latest lease heartbeats and three missing lease heartbeats, with no current active leases. API evidence cannot establish individual process liveness. Read-only SSH to `admin1@192.168.1.155` was denied, so per-unit state, worker journals, and event-processor durable cursor remain unverified. The latest event sequence is not the consumer cursor. No production data, service, migration, or release was changed.

The isolated browser uses synthetic workers to verify that lease status is labeled distinctly and does not claim process liveness. It is not production acceptance.
