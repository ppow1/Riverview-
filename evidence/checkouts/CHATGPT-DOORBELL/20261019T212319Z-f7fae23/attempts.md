<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/CHATGPT-DOORBELL/20261019T212319Z-f7fae23/attempts.md
Component: CHATGPT-DOORBELL
File Revision: 1.0.0
Purpose: Preserve failed validation attempts and their corrections
Execution Model: Test-run observation record
Observability: Sanitized failure causes and retained exact log where applicable
Dependencies: Combined C2/C3 PostgreSQL checkout
Authority: Disposable local test database only; no browser or production operation
Changed: 2026-10-19 UTC | RV-C2-DOORBELL-RESUME-20261019 | Record setup failures without treating them as product failures
History: New controlled evidence; adjacent artifacts.json
-->

# Retained validation attempts

These failed attempts are retained so the passing checkout does not hide its
environment and harness corrections.

1. The first combined-suite run used the local `admin1` PostgreSQL role. It ran
   49 tests and had one error in
   `test_steward_comms5_review_path_is_fenced_routed_and_audited_without_dispatch`:
   PostgreSQL denied `SET ROLE riverview_core` because `admin1` is not a member
   of that role. The unchanged suite then passed 49/49 when run as the local
   PostgreSQL superuser against the same disposable database. Exact failed
   output is `combined_suite_first_attempt_admin1.log`.
2. The first standalone harness import used a nonexistent `WakeResult` symbol;
   the bridge contract exports `DoorbellResult`. The harness was corrected to
   construct `DoorbellResult` with the claimed request and correlation IDs.
3. The first attempt to launch the standalone harness as OS user `postgres`
   referenced a file beneath `/home/admin1`, which that user cannot traverse.
   The final command streams the readable source file through stdin; this did
   not change repository permissions or the tested source.

None of these failures altered application code or relaxed the database
permission boundary.
