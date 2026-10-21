<!-- Riverview~ Controlled Evidence
File: evidence/checkouts/RESIDENT-LEARNING/20261018T1800Z-346a6ee/checkout.md
Component: RESIDENT-LEARNING-GOVERNANCE
File Revision: 1.0.0
Purpose: Record exact-head controlled checkout evidence for the W2 bounded learning remediation
Execution Model: GitHub Actions Linux runner with ephemeral PostgreSQL 16 service
Observability: Immutable workflow run, commit SHA, test and validator summaries
Dependencies: Controlled checkout workflow; PR #128
Authority: Test-only; no production identity, permissions, stores, or runtime activation
Changed: 2026-10-18 UTC | RV-W2-DOD-001 | Record exact-head isolated test and predecessor-checkout evidence
Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md; docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md
Tests: Run 39152123829; repeat exact final head after this evidence is added
History: Git and GitHub Actions
-->

# W2 resident learning controlled checkout

## Exact run

- Workflow: [Controlled checkout run 39152123829](https://github.com/ppow1/Riverview-/actions/runs/39152123829)
- Pull request: [#128](https://github.com/ppow1/Riverview-/pull/128)
- Tested commit: `346a6ee27f128d5bed63dadf265ded805f847dac`
- Result: **PASS**, completed 2026-10-18 18:00:49 UTC
- Environment: Ubuntu 24.04, Python 3.12, ephemeral PostgreSQL 16 service

## Results

- Complete unittest discovery: **174 tests passed** in 16.296 seconds.
- `tests.test_resident_learning_postgres.ResidentLearningPostgresTests.test_persist_and_resume_approved_shared_record`: **PASS** against the ephemeral PostgreSQL 16 database.
- Canonical process graph validation and generated projections: **PASS**, 14 graphs and 266 nodes.
- Controlled revision and preserved-predecessor verification against the pinned repository baseline: **PASS**, no issues.

This run tests software behavior in an isolated checkout. It does not authorize a resident, Steward, private retention grant, institutional share, production migration, runtime integration, or deployment. Local Windows execution with `core.autocrlf=true` produced line-ending-sensitive inventory differences; the Linux run above is the authoritative checkout result.
