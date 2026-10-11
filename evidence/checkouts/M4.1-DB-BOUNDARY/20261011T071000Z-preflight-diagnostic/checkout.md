# M4.1 preflight diagnostic and boundary integration checkpoint

- Task: `RV-M4.1-PREFLIGHT-DIAGNOSTIC`
- Source commit: `31aa3873d1247923ea523ebd4c503b8188d7d8cd`
- Branch: `codex/m4.1-db-privilege-boundary`; PR #20 open/draft/unmerged
- Isolated test command: `RIVERVIEW_TEST_PG_DSN=<private socket-only PostgreSQL 16.15 cluster> PYTHONPATH=src python3 -m unittest tests.test_institutional_authority_boundary -v` — 3 passed, 0 failures; cleanup left 0 `rvtest_*` schemas and roles.
- Safe diagnostics unit tests: included above; BoundaryPreflightError emits only static detail, PostgreSQL errors emit SQLSTATE only (no exception/connection data).
- Live read-only helper preflight for absent `riverview_authority` exits 1 with `{\"status\":\"ERROR\",\"failure_type\":\"BoundaryPreflightError\",\"detail\":\"selected schema does not exist\"}`. No `--apply` was used. Direct catalog output confirms the schema, roles and tables are absent; `riverview_dev` remains runtime-owned and untouched.
- `python3 scripts/process_graph.py check`: PASS, 12 workflows / 227 nodes.
- Controlled revision/predecessor audit: PASS, zero issues. Compileall exit 0.
- Exact-head GitHub CI run 38120458854: PASS (complete suite, process graph and controlled revision validation).
- No shared database, role, credential, schema, service, assignment, worker, or deployment changed.
