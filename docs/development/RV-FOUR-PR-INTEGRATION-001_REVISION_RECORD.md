# RIVERVIEW Four-PR Integration Candidate

**Document Revision:** 1.0.0  
**Task:** RV-FOUR-PR-INTEGRATION-001  
**Component:** ENG-RECORDS  
**Status:** Integration candidate; not merged, installed, or deployed  
**Branch:** `codex/riverview-four-pr-integration-20261018`  
**Base:** `codex/grace-conversation-ui-refinement`

## Dependency map

| Change | Depends on | Integrated contract |
|---|---|---|
| PR #109 Comms5 completion and durable external reasoning | Base branch | Durable, correlated external reasoning exchange with exact authorization; advice is input to Grace reasoning and never assignment authority. |
| PR #110 Grace external-reasoning initiation | #109 | Grace may initiate and consume an authorized exchange through the same resident service and persisted principal binding. |
| PR #111 bounded deferred-reasoning recovery | Base branch | Transient failures use persisted capped backoff; deterministic failures terminalize; lease and idempotent terminal event prevent duplicate publication. |
| PR #112 concurrent Engineering capabilities and proposal UI | Base branch; integrated with #109/#110 service | One resident service can poll artifact and source-change workers concurrently; source work requires a pinned repository and commit, bounded authorized paths, and independent verification. Proposal approval/promotion remains the only route into execution intake and results return to the originating conversation. |

All changes retain one persistent Grace resident with 0.6B, 30B, and 80B model capabilities.

## Integration and migration assessment

The live implementation uses one ordered migration directory and the shared `schema_migrations` ledger. PR #109 and PR #111 both supplied a migration numbered `0012`; they are not independent migration ledgers. The resource-selection migration remains `0012_resource_selection_policy.sql`; bounded deferred-retry state is sequenced as `0013_bounded_deferred_retries.sql`. The retry migration header now depends on the complete preceding sequence. No production migration was run. Test migrations ran only in an isolated disposable PostgreSQL 16 cluster.

The combined execution service routes attempts and verification by the persisted capability. Source-change dispatch is fail-closed until the configured source worker validates the original repository reference, immutable revision, and allowed paths. Source execution uses a distinct worker identity and verifier. External reasoning authorization is checked against the active resident principal and exact provider scope; external output remains advisory. Proposal state transitions and promotion still pass through the durable institutional lifecycle.

## Validation evidence

- Full suite: `RIVERVIEW_TEST_PG_DSN='host=/tmp/rv-fourpr-pg port=55449 dbname=riverview_test user=admin1' PYTHONPATH=src python3 -m unittest discover -s tests -v` — **615 passed, 0 failed, 0 errors, 0 skipped** (569.088 seconds), against isolated UTF-8 PostgreSQL 16 with disposable fixtures.
- Focused external reasoning: `tests.test_external_reasoning_exchange` — **14 passed** (54.073 seconds).
- Cross-component cases in the full run include concurrent scoped worker progress, artifact/source capability separation, independent verification, exact external-reasoning grants, durable bounded delivery/recovery, proposal approval and promotion gating, deferred retry caps, and conversation return idempotency.
- `python3 scripts/process_graph.py check` — **PASS**, 22 graphs / 564 nodes.
- `python3 scripts/revision_control.py check --baseline /tmp/rv-fourpr-revision-baseline.json` — **PASS** against the integration base revision inventory.
- The audit initially found twelve source-PR files without a verifiable copy of the exact integration-base predecessor. Their bytes were recovered from the base commit, SHA-256 checked against the baseline inventory, and preserved under `.riverview-backups/20261018T-integration-predecessors/`; the manifest-backed audit then passed.
- `python3 -m compileall -q src scripts` and `git diff --check` — **PASS**.
- Deployment package build and independent package verification: pending final commit, digest to be added before PR creation. The package is for inspection and is not installed.

## Remaining blockers and risks

- Production commissioning remains blocked on Steward review, exact production authority/provider grants, and an approved production migration and service change window. None of those were performed by this integration task.
- Production repository credentials and deployment identities were not exercised; tests use disposable credentials and repository fixtures.
- No merge or deployment is authorized by this record.

## Rollback plan

Before production commissioning, snapshot the deployed commit, package digest, migration ledger, and current runtime configuration. If commissioning fails before migration, restore the prior package and service configuration. If the `0012`/`0013` migrations have been applied, do not drop durable retry or resource-selection state; stop new dispatch, restore the prior application package only if its schema compatibility is confirmed, and use a separately reviewed forward repair for incompatible schema state. Preserve exchange, objective, proposal, assignment, verification, and conversation records for audit. Any rollback requires a new approved production change plan.

## Production commissioning checklist

- Steward reviews this integration PR, test evidence, migration ordering, and package digest.
- Confirm production source repository identity and immutable starting revision, allowed paths, and independent verifier configuration.
- Confirm distinct artifact and source worker principals, least-privilege grants, credential custody, and revocation procedures.
- Review exact external-reasoning provider/principal grants; verify responses cannot create or authorize work.
- Review proposal approval, promotion, and conversation-return lifecycle with production identities.
- Approve migration `0012` then `0013` in the production change record; verify backup and restore readiness.
- Stage the reviewed package and configuration in a non-production environment; run health, retry-bound, deduplication, and rollback drills.
- Approve a production work order and maintenance window; capture pre-change state and post-change verification evidence.
- Verify operational graphs, revision inventory, service health, worker isolation, and authorization audit records after commissioning.
- This integration candidate itself does not authorize installation, migration, service restart, or deployment.
