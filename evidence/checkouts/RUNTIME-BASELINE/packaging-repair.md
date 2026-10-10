# Riverview~ Windows packaging repair evidence

**Document Revision:** 1.0.0
**Task:** RV-M1.1-002
**Component:** RUNTIME-BASELINE
**Timestamp UTC:** 2026-10-10T01:08:39.382172+00:00
**Target:** cloud Linux, Windows Git settings simulated; original artifact unavailable

## Retained actual Camrui failure

Source: https://github.com/ppow1/Riverview-/pull/2#issuecomment-6091930352
Reported run: 2026-10-10T01:00:02Z, SHA 11e09d88a6ee39d943d6222dd5f12c773b8a120b. Original archive SHA-256: 6af503497c1e4af052a26ddaafb39bdc6dcb78f40b9511b3c183487d08f4851e. SSH/sudo/package transfer/commit/manifest PASS. Installer line 15: set: Illegal option -, exit 2. Acceptance SKIPPED_INSTALL_FAILURE. Original archive/staging remains on user hosts, not inspected here.

## Root-cause reproduction

A temporary separate Git checkout of the exact failed commit used core.autocrlf=true and core.eol=crlf. Its unchanged original packaging script generated an actual tarball with Windows-converted shell bytes. This is a reproduction artifact, not the inaccessible original. Gzip wrapper filenames/time can change archive SHA even with identical file bytes. The verifier reports manifest PASS and incompatible shells; isolated execution of line 15 reproduces the exact error for both scripts. No privileged deployment or rollback ran.

### Command

`git clone --quiet --shared --no-checkout /workspace/Riverview- <temporary-clone>`

Exit code: 0

```text
(no output)
```

### Command

`git -C <temporary-clone> config core.autocrlf true`

Exit code: 0

```text
(no output)
```

### Command

`git -C <temporary-clone> config core.eol crlf`

Exit code: 0

```text
(no output)
```

### Command

`git -C <temporary-clone> checkout --quiet --detach 11e09d88a6ee39d943d6222dd5f12c773b8a120b`

Exit code: 0

```text
(no output)
```

### Command

`/workspace/riverview-venv/bin/python <temporary-clone> /tmp/riverview-M1.1-reproduced-Windows-11e09d8.tar.gz`

Exit code: 0

```text
source_commit=11e09d88a6ee39d943d6222dd5f12c773b8a120b
archive_sha256=fa6e97d673dc53ae133f59f543d968d40b7782a0d62f24579e23fb7964d2a8b1
```

### Command

`/workspace/riverview-venv/bin/python scripts/verify_camrui_package.py /tmp/riverview-M1.1-reproduced-Windows-11e09d8.tar.gz`

Exit code: 2

```text
{
  "archive_sha256": "fa6e97d673dc53ae133f59f543d968d40b7782a0d62f24579e23fb7964d2a8b1",
  "manifest": "PASS",
  "projection_version": "rv.package-verification.v1",
  "shell_compatibility": "FAIL",
  "shells": [
    {
      "compatible": false,
      "cr_bytes": 80,
      "crlf_pairs": 80,
      "line_15_hex": "736574202d65750d0a",
      "nul_bytes": 0,
      "path": "deploy/install_baseline.sh",
      "sha256": "1a9f159ae7087e46924bc5ec31e53ba234ad324ee2ce49a6439426fc7dd05eb4",
      "utf8_bom": false
    },
    {
      "compatible": false,
      "cr_bytes": 43,
      "crlf_pairs": 43,
      "line_15_hex": "736574202d65750d0a",
      "nul_bytes": 0,
      "path": "deploy/rollback_baseline.sh",
      "sha256": "e69528410038e130dc3f9039117d0c76fc18640c74928722c1bc380a12326ba5",
      "utf8_bom": false
    }
  ],
  "source_commit": "11e09d88a6ee39d943d6222dd5f12c773b8a120b"
}
```

### Command

`sh -c b'set -eu\r\n'`

Exit code: 2

```text
sh: 1: set: Illegal option -
```

### Command

`sh -c b'set -eu\r\n'`

Exit code: 2

```text
sh: 1: set: Illegal option -
```

### Command

`/workspace/riverview-venv/bin/python -m unittest discover -s tests -v`

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
test_committed_invalid_shell_bytes_fail_before_archive_creation (test_runtime_baseline.PackageShellCompatibilityTests.test_committed_invalid_shell_bytes_fail_before_archive_creation) ... ok
test_extracted_install_and_rollback_parse_and_execute_preamble (test_runtime_baseline.PackageShellCompatibilityTests.test_extracted_install_and_rollback_parse_and_execute_preamble) ... ok
test_packaged_bytes_ignore_windows_checkout_and_export_conversion (test_runtime_baseline.PackageShellCompatibilityTests.test_packaged_bytes_ignore_windows_checkout_and_export_conversion) ... ok
test_predecessor_windows_package_reproduces_reported_error (test_runtime_baseline.PackageShellCompatibilityTests.test_predecessor_windows_package_reproduces_reported_error) ... ok
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
Ran 36 tests in 0.385s

OK (skipped=3)
```

### Command

`sh -n deploy/install_baseline.sh`

Exit code: 0

```text
(no output)
```

### Command

`sh -n deploy/rollback_baseline.sh`

Exit code: 0

```text
(no output)
```

## Exact unchanged shell-source bytes

- deploy/install_baseline.sh: SHA-256 f702229b3f01a5b6192ce5b098d01632f89f0782e3b72a4126578c4e55fa77f6, CR count 0, identical to committed failed-revision blob.
- deploy/rollback_baseline.sh: SHA-256 6500e6696934bca4c791056047a0b51f14ee79f9373447aecb4437fc7a67ccda, CR count 0, identical to committed failed-revision blob.

## Outcome

36 tests discovered, 33 passed, 3 PostgreSQL integration skips, zero failures. New tests inspect real built tarballs, verify manifest/file bytes against Git blobs despite Windows conversion settings/attributes, reject committed CRLF/BOM/NUL before output, and parse/execute both extracted shells through the non-root guard. The historical-builder test retains manifest PASS + shell FAIL as a regression. Full host installation, runtime credential delivery, DB functionality, rollback, dashboard and Steward acceptance remain NOT VERIFIED. M1.1 remains NOT DONE; next step M1.2 only after M1.1 acceptance.
