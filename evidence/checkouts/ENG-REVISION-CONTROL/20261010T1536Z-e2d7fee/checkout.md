# Riverview~ RV-ENG-REV-004 external CI checkout

**Document Revision:** 1.0.0
**Task:** RV-ENG-REV-004
**Component:** ENG-REVISION-CONTROL
**Timestamp UTC:** 2026-10-10T15:36Z
**Source commit:** `e2d7fee8baa137a6ebf16466a5a1354d04fc0c74`
**Branch:** `codex/m1.1-runtime-commissioning`
**Target:** GitHub-hosted `ubuntu-24.04`; Python 3.12.15; ephemeral PostgreSQL 16 service
**Outcome:** PASS, independently executed by GitHub Actions

Both independently triggered runs for this commit passed:

- Push: [run 38064245175](https://github.com/ppow1/Riverview-/actions/runs/38064245175)
- Pull request: [run 38064247105](https://github.com/ppow1/Riverview-/actions/runs/38064247105)

Each ran the complete suite: 53 tests, 53 passed, zero failed, zero skipped;
all six PostgreSQL tests executed against the temporary service. Each then ran
`python scripts/revision_control.py check --baseline
evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json`
and returned `passed=true`, `issues=[]`. The PostgreSQL service and its data
were job-scoped and discarded after completion. No project or Camrui database
was used.

The workflow uses `actions/checkout@v7` and `actions/setup-python@v7` on pinned
Ubuntu 24.04. The final run has no Node runtime deprecation warning. Complete
push-run output is retained in `github-actions-push.log` and checksummed by the
sidecar manifest. CI validates the engineering checkout; it is not Steward
acceptance, runtime external observability, or permission to merge.
