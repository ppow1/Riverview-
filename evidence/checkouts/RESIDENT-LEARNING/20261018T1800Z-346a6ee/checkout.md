<!-- Riverview~ Controlled Evidence
File: evidence/checkouts/RESIDENT-LEARNING/20261018T1800Z-346a6ee/checkout.md
Component: RESIDENT-LEARNING-GOVERNANCE
File Revision: 1.0.2
Purpose: Record exact-head controlled checkout evidence for the W2 bounded learning remediation
Execution Model: GitHub Actions Linux runner with ephemeral PostgreSQL 16 service
Observability: Immutable workflow runs, commit SHAs, test and validator outputs
Dependencies: Controlled checkout workflow; PR #128
Authority: Test-only; no production identity, permissions, stores, or runtime activation
Changed: 2026-10-18 UTC | RV-W2-DOD-001 | Record isolated test and predecessor-checkout evidence
Changed: 2026-10-18 UTC | RV-W2-PR-REVIEW-001 | Complete required checkout record fields and distinguish both tested commits
Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md; docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md; docs/standards/ENGINEERING_RECORDS_STANDARD.md
Tests: Runs 39152123829 and 39152236268; commands and outputs linked below
History: Git; GitHub Actions; .riverview-backups/manifest.jsonl
-->

# W2 resident learning controlled checkout

These records document software verification only. They do not establish component acceptance, Steward approval, production readiness, or permission to activate resident learning.

## Run 1 — initial focused PR head

- Workflow/run: [Controlled checkout 39152123829](https://github.com/ppow1/Riverview-/actions/runs/39152123829)
- PR: [#128](https://github.com/ppow1/Riverview-/pull/128)
- Source commit: `346a6ee27f128d5bed63dadf265ded805f847dac`
- Started/completed: 2026-10-18 18:00:08–18:00:49 UTC; exit code 0
- Target: GitHub-hosted Ubuntu 24.04; Python 3.12; ephemeral `postgres:16` service
- Runner/job: GitHub Actions `controlled-checkout`, job `117747748434`; triggering actor `ppow1`
- Result: full suite, graph synchronization, and pinned revision/predecessor verification all passed.
- Test command: `python -m unittest discover -s tests -v` with `PYTHONPATH=src` and the workflow's disposable `RIVERVIEW_TEST_PG_DSN`; **174 tests passed** in 16.296 seconds.
- PostgreSQL test: `tests.test_resident_learning_postgres.ResidentLearningPostgresTests.test_persist_and_resume_approved_shared_record` passed.
- Graph command: `python scripts/process_graph.py check`; **14 graphs / 266 nodes**, exit 0.
- Revision command: `python scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json`; no issues, exit 0.

## Run 2 — final initial-PR head, including the first evidence artifact

- Workflow/run: [Controlled checkout 39152236268](https://github.com/ppow1/Riverview-/actions/runs/39152236268)
- Source commit: `7bb5b2db73f11c14854d6b2fdbe9b1be0db43286`
- Started/completed: 2026-10-18 18:01:24–18:02:14 UTC; exit code 0
- Target: GitHub-hosted Ubuntu 24.04; Python 3.12.15; ephemeral `postgres:16` service
- Runner/job: GitHub Actions `controlled-checkout`, job `117748060161`; event `push`, actor `ppow1`, attempt 1
- Workflow dependencies: `psycopg[binary]==3.2.10`, `jsonschema==4.10.3`; the workflow run page preserves full stdout/stderr and step results.
- Test command: `python -m unittest discover -s tests -v` with `PYTHONPATH=src` and the workflow's disposable `RIVERVIEW_TEST_PG_DSN`; **174 tests passed, zero skipped** in 15.157 seconds.
- PostgreSQL test: `tests.test_resident_learning_postgres.ResidentLearningPostgresTests.test_persist_and_resume_approved_shared_record` passed against the ephemeral PostgreSQL 16 service.
- Graph command: `python scripts/process_graph.py check`; **14 graphs / 266 nodes**, exit 0.
- Revision command: `python scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json`; no issues, exit 0.

## Scope and limitations

Both runs verify isolated software behavior; no migration was applied outside each test's uniquely named disposable schema. No checkout failures remain. Learning runtime, an authoritative Steward view, live deployment, operational autonomy, and component acceptance remain uncommissioned. Local Windows execution with `core.autocrlf=true` produced line-ending-sensitive inventory differences; the linked Linux checkout logs are the authoritative repository-blob checks. The later W2 review evidence amendment does not change source behavior; its own exact-head CI result is reported in the PR and issue review record.
