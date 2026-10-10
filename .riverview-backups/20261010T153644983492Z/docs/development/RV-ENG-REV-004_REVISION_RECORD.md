# Riverview~ RV-ENG-REV-004 CI checkout enforcement

**Document Revision:** 1.0.0
**Task:** RV-ENG-REV-004
**Component:** ENG-REVISION-CONTROL
**Date:** 2026-10-10 UTC
**Status:** IN PROGRESS — workflow implemented; remote run pending
**Starting commit:** e6a7ba0bcb66a5df3ab699b544c8223e6996972a

## Intake and authority

The Development Lifecycle Standard requires repository pre-commit/CI checkout
enforcement. The revision tool and tests existed, but `gh pr checks 2` reported
no checks on the authorized development branch. This task adds a GitHub Actions
CI gate. It does not change branch protection, merge authority, Steward approval,
production services, or database configuration.

## Design and acceptance criteria

- Run on pull requests to `main` and pushes to `main` or `codex/**`.
- Use read-only repository permissions.
- Run the full unit/integration suite against an ephemeral PostgreSQL 16 service
  with a CI-only trust-authenticated test database and the repository-pinned
  Psycopg version.
- Run the revision checker against the preserved RV-ENG-REV-003 baseline; fail
  the job on missing revisions, invalid predecessor backups, or revision
  regressions.
- Do not access Camrui, commissioned Riverview databases, secrets, or branch
  protection settings.

## Verification

Pending YAML/workflow validation and the external GitHub Actions run for PR #2.
An external run must report all test cases and revision checkout passing before
this task can be marked complete. Retain the run URL, commit SHA, and actual test
counts in checkout evidence. No formal project or milestone acceptance is
conferred by CI.

## Controlled-file record

New `.github/workflows/controlled-checkout.yml` starts at revision 1.0.0. This
task record starts at 1.0.0. Neither file contains credentials; the ephemeral
CI test database is isolated to its job.
