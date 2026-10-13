# M4.1 isolated database-boundary verification

- Task: `RV-M4.1-ROLE-SCOPE-REVIEW`
- Source commit: `1731bdfb470337158a920e1dbd4b80ffb7f66e79`
- Branch: `codex/m4.1-db-privilege-boundary`
- PR: https://github.com/ppow1/Riverview-/pull/20 (open, draft, unmerged)
- Target: Camrui; isolated PostgreSQL 16.15 temporary cluster, Unix socket only, no TCP listener.
- Shared operational DB/services: not modified.

## Verification

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`: **135 passed, 0 failures, 0 errors, 0 skips**; 58.972 seconds.
- Test cleanup query: **0 `rvtest_*` schemas, 0 `rvtest_*` roles**; temporary cluster stopped successfully.
- `python3 -m compileall -q src scripts tests`: exit 0.
- `python3 scripts/process_graph.py check`: PASS, 12 workflows / 227 nodes.
- `python3 scripts/revision_control.py check --baseline /tmp/rv_m41_boundary_baseline.json`: PASS, zero issues.
- Exact-head GitHub controlled-checkout CI: PASS, run 38119049973; see `github-ci.json`.

## Security and commissioning disposition

The isolated authority boundary now requires a dedicated schema, denies ordinary runtime schema/table access, and gives a no-membership NOINHERIT manager allowlisted DML only. Tests verify it cannot take owner membership or create/drop objects. This is isolated engineering only. No live roles, credentials, schema, migration, assignments, workers, or services were changed. Shared-schema migration, protected credential delivery, restore rehearsal, application/worker authorization integration, and live commissioning remain open.
