<!-- Riverview~ Controlled Document
File: docs/components/RESIDENT_LEARNING_COOKBOOK.md
Component: RESIDENT-LEARNING-GOVERNANCE
File Revision: 1.0.1
Purpose: Give implementers and reviewers a bounded, dormant learning lifecycle walkthrough
Execution Model: Documentation only; no runtime wiring or production operation
Observability: Commands and expected fail-closed behavior are recorded below
Dependencies: RESIDENT_LEARNING_GOVERNANCE.md; resident_learning.py; isolated checkout workflow
Authority: Grants no permission and supplies no resident identity or approval
Changed: 2026-10-18 UTC | RV-W2-DOD-001 | Add implementation cookbook and safe recovery instructions
Changed: 2026-10-18 UTC | RV-W2-DOD-001 | Align backup verification instructions with available checkout validation
Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md; docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md
Tests: See focused and controlled-checkout commands below
History: Git and .riverview-backups/manifest.jsonl
-->

# Resident learning implementation cookbook

## Status and boundaries

This is a dormant, request-driven library with an additive SQL migration. Nothing in this cookbook enables a runtime caller, grants permission, identifies a resident, or appoints a Steward. Use only a synthetic identity and an explicitly disposable database in local tests. Never put credentials in command history, evidence, or documentation.

The service accepts caller-supplied evidence references and provenance. It does not extract facts from conversation, validate facts by itself, or promote model output. The integrating owner must supply current identity binding and exact authorization. A denial, missing evidence, unavailable authority service, or stale approval must fail closed and leave the candidate out of retrieval.

## Lifecycle walkthrough

1. Keep request context in the request. Record operational observations through their existing owning component.
2. Create an evidence-bearing candidate only after the caller's current resident binding and exact scope authorization succeed.
3. Validate against cited evidence through an authorized independent reviewer. Insufficient or contradicted evidence stays non-retrievable; reject or defer it with an event.
4. For private durable knowledge, require explicit resident confirmation and the existing private-write grant. For institutional scope, require the exact approval from an already-authorized Steward. No API call or capability registration creates that authority.
5. Retrieve only approved, current records for the exact authorized scope. Preserve status and provenance with each result.
6. Correct by creating a new candidate and linking a correction/supersession event. Revalidate and reapprove the replacement. Roll back only through a new authorized decision that cites fresh evidence and checks the prior revision is still valid.

The service API and transition contract are in `src/riverview_core/resident_execution/resident_learning.py`. The canonical graph and generated view are in `process_graphs/resident-learning/lifecycle.json` and `RESIDENT_LEARNING_FLOW.md`.

## Local, isolated checks

From the repository root, run:

```powershell
python -m unittest tests.test_resident_learning tests.test_resident_learning_contract tests.test_revision_control tests.test_process_graph -v
python scripts/process_graph.py validate
python scripts/process_graph.py check
python scripts/revision_control.py inventory
```

The PostgreSQL test is skipped unless `RIVERVIEW_TEST_PG_DSN` points to an explicitly disposable database. In a disposable test job only, set that variable to the test database and run `python -m unittest tests.test_resident_learning_postgres -v`. The test creates a unique schema and drops only that schema. A local DSN must not point at a production or shared database.

Expected behavior: authorization or evidence errors raise the service's typed denial/validation error; no durable record becomes retrievable. A process restart resumes approved rows from the store while preserving event history. The test suite does not establish that any real resident or Steward has authority.

## Controlled checkout and diagnosis

Use the repository's `Controlled checkout` GitHub Actions workflow on a review branch to run the full suite against its ephemeral PostgreSQL 16 service. Review the exact commit SHA and workflow run before citing results. A failed graph check means canonical JSON, references, sidecar hashes, or generated projections disagree; regenerate only with `python scripts/process_graph.py generate`, inspect the diff, then re-run `check`.

For a failed unit test, retain its exact output and commit SHA. For PostgreSQL failures, confirm the workflow service health and test database name; do not point the test at a shared database to work around an unavailable ephemeral service. If authority is unavailable in an eventual caller, preserve the candidate as pending or return a denial; do not bypass authorization or retry with a broader scope.

## Backup verification and restoration

Before changing a controlled source or generated projection, create a revision-control backup with the next revision and task reference. The manifest entry records the original SHA-256, prospective revision, source commit, and a restore procedure. Verify the manifest entry and backup file hashes independently; the controlled checkout workflow runs the repository's predecessor check against its pinned baseline.

If a local change must be restored, first preserve the current target as a separate review artifact and record its hash. Select the backup manifest row by exact target path, task, and source commit; verify the backup file against its recorded SHA-256. Restore that exact byte copy, then verify the restored target hash equals the recorded original SHA-256 and inspect `git diff`. Do not restore an older copy over later reviewed work. If the predecessor is ambiguous or the current target contains later work, stop and report the conflict for review.

PowerShell example after selecting and independently verifying the correct manifest row:

```powershell
$target = Join-Path (Get-Location) 'docs/components/RESIDENT_LEARNING_FLOW.md'
$backup = 'REPLACE_WITH_VERIFIED_BACKUP_PATH'
$currentCopy = "$target.before-restore"
Copy-Item -LiteralPath $target -Destination $currentCopy
Get-FileHash -Algorithm SHA256 -LiteralPath $currentCopy
Get-FileHash -Algorithm SHA256 -LiteralPath $backup
Copy-Item -LiteralPath $backup -Destination $target
Get-FileHash -Algorithm SHA256 -LiteralPath $target
git diff -- $target
```

Replace the placeholder only with a path whose manifest checksum was independently matched. Do not run a restore against production or a commissioned store. Database rollback is an append-only learning decision through the authorized API; it is not SQL deletion or migration reversal. No production rollback has been performed.

## Known integration blockers

The repository does not define a resident-learning grant mapping, active Steward principal, private retention grant, or commissioned retention/purge owner. Those are authority and policy inputs for a later authorized integration; this library does not invent them. No real identity, grant, approval, runtime, database, or service was changed for this work.
