<!--
Riverview Controlled Document
File: docs/components/GRACE_COMMISSIONING_COOKBOOK.md
Component: GRACE-COMMISSIONING
File Revision: 1.0.0
Task: RV-C4-PR115-119-READINESS-001-REMEDIATION
Purpose: Operator-safe isolated readiness checks and blocker response
Authority: Nonproduction preparation only; no production activation authority
Changed: 2026-10-18 UTC | RV-C4-PR115-119-READINESS-001-REMEDIATION | Add bounded isolated preflight and blocker workflow
-->

# Grace commissioning preflight cookbook

This cookbook covers isolated evidence gathering for the PR #115/#119 candidate. It does not authorize deployment, migration, service changes, provider activation, grants, or Engineering execution.

## Candidate and package checks

1. Confirm the checked-out candidate SHA and clean/expected worktree. Confirm the dependency ancestry and current PR heads on GitHub.
2. Verify the exact deployment archive against its signed or controlled manifest with `python3 scripts/verify_camrui_package.py <archive>`; preserve the output and archive digest.
3. Run `python3 scripts/process_graph.py check` and the repository revision check. Record the exact commands, exit codes, and output.
4. Use only a disposable PostgreSQL instance restored from a preserved snapshot copy. Never point `RIVERVIEW_TEST_PG_DSN` at production. Apply candidate migration sets in their declared order and check ledger idempotency, existing row counts, and restricted runtime-role allow/deny behavior.
5. Stop and destroy only the disposable instance after capturing logs and verifying cleanup.

## Isolated execution and pointer recovery

Run the focused worker and lifecycle suites using synthetic identities and a private disposable database. The durable 2026-10-18 run is recorded at `evidence/checkouts/GRACE-COMMISSIONING/20261018T1756Z-e38368e/acceptance.json` with adjacent logs and a hash inventory.

The pointer experiment in `rollback-pointer.log` tests only atomic symlink replacement between synthetic release directories. It is not the production rollback procedure. It does not prove database downgrade safety, service ordering, snapshot integrity, a maintenance window, or operator authority. A production run requires a separately verified protected snapshot, restore test, release-specific steps, and written change approval.

## Blocker register and resume rules

| Blocker | Required evidence before resuming | Resume trigger |
|---|---|---|
| External ChatGPT provider | Approved provider identity; verified issuer, subject/client mapping, audience/resource and HTTPS route; protected credential custody/renewal; exact provider-scoped `resident.reasoning.escalate` grant | Read-only identity and grant verification, followed by authorized isolated exchange testing |
| Source worker | Distinct source-worker principal; bound credential; exact worker registration and `assignment.execute` scope; repository provenance and independent verifier identity | Read-only authorization checks pass and Steward approves the exact harmless objective |
| Objective | Durable approval of pinned repository, allowed paths, expected artifact, verifier and cleanup | Approval is recorded for this exact objective and both executor/verifier identities are revalidated |
| Deployment | Fresh protected snapshot and restore evidence; reviewed migration compatibility; release-specific service sequence; tested rollback; maintenance window and named operator; separate change authorization | Every readiness gate has evidence and separate deployment authorization is recorded |

No blocker is cleared by a plan, a passing isolated test, or a PR review. Current state remains commissioning milestone 1/5, BLOCKED, capability NOT_COMMISSIONED. There is no automated live alert or resume mechanism; report evidence and decisions through issue #120 and the controlled monitor.

## Production boundary

The current assignment permits isolated fixtures, documentation, graph and revision updates, Git commits, pushes, and PR review. It does not permit production reads involving secrets, credentials/grants changes, service activation, migration, deployment, live provider calls, new work orders, or Engineering execution. Use a new explicit authorization after all readiness gates pass. If any gate is absent or ambiguous, preserve the evidence, leave state blocked, and stop before the dependent operation.
