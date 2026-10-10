# Riverview~ RV-ENG-REV-004 CI checkout enforcement

**Document Revision:** 1.0.1
**Task:** RV-ENG-REV-004
**Component:** ENG-REVISION-CONTROL
**Date:** 2026-10-10 UTC
**Status:** DONE — push and pull-request CI runs pass
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

The workflow passed on source commit
`e2d7fee8baa137a6ebf16466a5a1354d04fc0c74`, pushed as the PR #2 head. Both
external event types passed:

- Push run [38064245175](https://github.com/ppow1/Riverview-/actions/runs/38064245175)
- Pull-request run [38064247105](https://github.com/ppow1/Riverview-/actions/runs/38064247105)

Each run executed all 53 tests: 53 passed, zero failed, zero skipped, including
all six PostgreSQL integration cases. The controlled revision checkout passed
with zero issues. Complete output and run metadata are preserved in
[`ENG-REVISION-CONTROL external CI evidence`](../../evidence/checkouts/ENG-REVISION-CONTROL/20261010T1536Z-e2d7fee/checkout.md).

The first successful workflow version used Node 20 actions and floating
`ubuntu-latest`. Based on actual runner warnings, the final workflow now uses
Node 24 compatible action majors and pins Ubuntu 24.04. Both final runs passed
without Node-runtime or image-migration warnings. No secrets, Camrui database,
branch protection, or privileged operation is involved. CI verifies software;
it does not confer milestone acceptance or merge permission.

## Controlled-file record

`.github/workflows/controlled-checkout.yml` is revision 1.0.2; the task record is
revision 1.0.1. Exact previous content/checksums are in
`.riverview-backups/manifest.jsonl`. CI evidence files and manifest have revision
1.0.0 via the evidence sidecar. Neither file contains credentials; the ephemeral
CI database exists only inside each GitHub Actions job.
