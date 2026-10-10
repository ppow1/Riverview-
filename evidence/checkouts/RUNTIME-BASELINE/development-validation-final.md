# Riverview~ final development verification

**Document Revision:** 1.0.0
**Component:** RUNTIME-BASELINE
**Task:** RV-M1.1-001
**Timestamp UTC:** 2026-10-10T00:51:47.188658+00:00
**Target:** cloud development; Camrui NOT VERIFIED

Command: `PYTHONPATH=src /workspace/riverview-venv/bin/python -m unittest discover -s tests -v`
Exit code: 0

```text
test_completion_requires_verification_flag (test_ledger.LedgerTests.test_completion_requires_verification_flag) ... ok
test_idempotent_event_and_illegal_transition (test_ledger.LedgerTests.test_idempotent_event_and_illegal_transition) ... ok
test_independent_assignments_and_reopen (test_ledger.LedgerTests.test_independent_assignments_and_reopen) ... ok
test_heading_revision_preserved (test_migrate_document_revisions.MigrationTests.test_heading_revision_preserved) ... ok
test_preserves_and_migrates (test_migrate_document_revisions.MigrationTests.test_preserves_and_migrates) ... ok
test_rejects_overwrite (test_migrate_document_revisions.MigrationTests.test_rejects_overwrite) ... ok
test_completion_requires_verification_flag (test_postgres_ledger.PostgresLedgerTests.test_completion_requires_verification_flag) ... skipped 'RIVERVIEW_TEST_PG_DSN not configured'
test_idempotency_and_illegal_transition (test_postgres_ledger.PostgresLedgerTests.test_idempotency_and_illegal_transition) ... skipped 'RIVERVIEW_TEST_PG_DSN not configured'
test_persistence_and_independent_assignments (test_postgres_ledger.PostgresLedgerTests.test_persistence_and_independent_assignments) ... skipped 'RIVERVIEW_TEST_PG_DSN not configured'
test_backup_exact_and_logged (test_revision_control.RevisionTests.test_backup_exact_and_logged) ... ok
test_backup_rejects_traversal (test_revision_control.RevisionTests.test_backup_rejects_traversal) ... ok
test_bump_with_backup_passes (test_revision_control.RevisionTests.test_bump_with_backup_passes) ... ok
test_bump_without_backup_fails (test_revision_control.RevisionTests.test_bump_without_backup_fails) ... ok
test_changed_without_bump_fails (test_revision_control.RevisionTests.test_changed_without_bump_fails) ... ok
test_inventory (test_revision_control.RevisionTests.test_inventory) ... ok
test_legacy_markdown_document_revision (test_revision_control.RevisionTests.test_legacy_markdown_document_revision) ... ok
test_legacy_markdown_revision (test_revision_control.RevisionTests.test_legacy_markdown_revision) ... ok
test_legacy_revision_comparison (test_revision_control.RevisionTests.test_legacy_revision_comparison) ... ok
test_tampered_backup_fails (test_revision_control.RevisionTests.test_tampered_backup_fails) ... ok
test_acceptance_requires_fresh_distinct_matching_observations (test_runtime_baseline.RuntimeBaselineTests.test_acceptance_requires_fresh_distinct_matching_observations) ... ok
test_driver_error_is_sanitized (test_runtime_baseline.RuntimeBaselineTests.test_driver_error_is_sanitized) ... ok
test_observer_fresh_stale_missing_and_failure (test_runtime_baseline.RuntimeBaselineTests.test_observer_fresh_stale_missing_and_failure) ... ok
test_observer_rejects_future_and_excess_ttl (test_runtime_baseline.RuntimeBaselineTests.test_observer_rejects_future_and_excess_ttl) ... ok
test_package_exact_commit_checksums_and_no_overwrite (test_runtime_baseline.RuntimeBaselineTests.test_package_exact_commit_checksums_and_no_overwrite) ... ok
test_pgpass_escaping_and_invalid_passwords (test_runtime_baseline.RuntimeBaselineTests.test_pgpass_escaping_and_invalid_passwords) ... ok
test_repeated_requests_are_independent (test_runtime_baseline.RuntimeBaselineTests.test_repeated_requests_are_independent) ... ok
test_role_and_schema_fail_closed (test_runtime_baseline.RuntimeBaselineTests.test_role_and_schema_fail_closed) ... ok
test_schema_owner_is_observed_without_inventing_an_ownership_migration (test_runtime_baseline.RuntimeBaselineTests.test_schema_owner_is_observed_without_inventing_an_ownership_migration) ... ok
test_secure_file_modes_symlink_empty_and_owner (test_runtime_baseline.RuntimeBaselineTests.test_secure_file_modes_symlink_empty_and_owner) ... ok
test_service_identity_and_ambient_password_rejected (test_runtime_baseline.RuntimeBaselineTests.test_service_identity_and_ambient_password_rejected) ... ok
test_ssh_command_and_injection_rejection (test_runtime_baseline.RuntimeBaselineTests.test_ssh_command_and_injection_rejection) ... ok
test_valid_baseline_is_not_institutional_health (test_runtime_baseline.RuntimeBaselineTests.test_valid_baseline_is_not_institutional_health) ... ok

----------------------------------------------------------------------
Ran 32 tests in 0.166s

OK (skipped=3)
```

Baseline tracked files with changed SHA-256: []
New staged files without revision 1.0.0: []

The whole-repository revision checker reports only pre-existing missing revisions in `.gitignore` and `docs/standards/ENGINEERING_RECORDS_STANDARD.md`. These remain unchanged; this is not whole-repository compliance PASS.

Schema-owner regression verifies owner is observed without demanding an invented ownership migration. Invalid/non-object JSON fails unavailable. Prior development output is retained separately.
