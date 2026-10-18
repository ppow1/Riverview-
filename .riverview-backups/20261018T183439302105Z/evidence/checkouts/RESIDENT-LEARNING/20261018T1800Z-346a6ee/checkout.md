<!-- Riverview~ Controlled Evidence
File: evidence/checkouts/RESIDENT-LEARNING/20261018T1800Z-346a6ee/checkout.md
Component: RESIDENT-LEARNING-GOVERNANCE
File Revision: 1.0.1
Purpose: Record exact-head controlled checkout evidence for the W2 bounded learning remediation
Execution Model: GitHub Actions Linux runner with ephemeral PostgreSQL 16 service
Observability: Immutable workflow run, commit SHA, test and validator summaries
Dependencies: Controlled checkout workflow; PR #128
Authority: Test-only; no production identity, permissions, stores, or runtime activation
Changed: 2026-10-18 UTC | RV-W2-DOD-001 | Record exact-head isolated test and predecessor-checkout evidence
Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md; docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md
Tests: Runs 39152123829 and 39152236268; exact commands and outputs linked below
History: Git and GitHub Actions
-->

# W2 resident learning controlled checkout

## Exact run

- Workflow: [Controlled checkout run 39152123829](https://github.com/ppow1/Riverview-/actions/runs/39152123829)
- Pull request: [#128](https://github.com/ppow1/Riverview-/pull/128)
- Tested commit: `346a6ee27f128d5bed63dadf265ded805f847dac`
- Result: **PASS**, completed 2026-10-18 18:00:49 UTC
- Environment: Ubuntu 24.04, Python 3.12, ephemeral PostgreSQL 16 service
- Runner: GitHub Actions (`controlled-checkout`, job `117748060161`)
- Source commit: `7bb5b2db73f11c14854d6b2fdbe9b1be0db43286`
- Trigger: push by `ppow1` to `codex/w2-resident-learning-dod-remediation-20261018`; workflow execution identity: GitHub Actions
- Run URL: [final-head controlled checkout 39152236268](https://github.com/ppow1/Riverview-/actions/runs/39152236268)

## Results

- `python -m unittest discover -s tests -v` (`PYTHONPATH=src`, ephemeral `RIVERVIEW_TEST_PG_DSN`): **174 tests passed**, zero skipped, in 15.157 seconds; exit code 0.
- `tests.test_resident_learning_postgres.ResidentLearningPostgresTests.test_persist_and_resume_approved_shared_record`: **PASS** against the ephemeral PostgreSQL 16 database.
- `python scripts/process_graph.py check`: **PASS**, 14 graphs and 266 nodes; exit code 0.
- `python scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json`: **PASS**, no issues; exit code 0.
- Tool pins: Python 3.12; `psycopg[binary]==3.2.10`; `jsonschema==4.10.3`; PostgreSQL service image `postgres:16`.
- The workflow run page above preserves complete stdout/stderr and step results; all three verification steps completed successfully. GitHub API recorded actor `ppow1`, event `push`, attempt 1.
- Decision: this is a successful isolated software checkout only. It is not deployment evidence or Steward acceptance. No checkout failures remain; learning runtime, Steward view and operational autonomy remain uncommissioned.

This run tests software behavior in an isolated checkout. It does not authorize a resident, Steward, private retention grant, institutional share, production migration, runtime integration, or deployment. Local Windows execution with `core.autocrlf=true` produced line-ending-sensitive inventory differences; the Linux run above is the authoritative checkout result.
