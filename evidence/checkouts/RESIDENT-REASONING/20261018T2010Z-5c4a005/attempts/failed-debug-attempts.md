<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/RESIDENT-REASONING/20261018T2010Z-5c4a005/attempts/failed-debug-attempts.md
Component: RESIDENT-REASONING
File Revision: 1.0.0
Purpose: Record failed isolated implementation debug attempts and their corrections
Execution Model: Test-run observation log
Observability: Sanitized failure summaries with final passing rerun references
Dependencies: C3 isolated checkout evidence
Authority: No production or live provider operation
Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Record source and test-fixture corrections
History: Git and .riverview-backups/manifest.jsonl
-->

# Retained failed debug attempts

These were implementation-debug runs on the same isolated C3 checkout, not accepted checkout evidence. The original tool output was returned interactively and was not saved as a file at the time; this summary records the observed failure and correction transparently.

- **2026-10-18, approximately 20:04–20:05 UTC; exit 1.** Command: the same `pg_virtualenv -t sh -c ... unittest tests.test_external_reasoning_exchange tests.test_resident_reasoning -v` invocation as the passing artifact. Four tests errored in `has_terminal_review_for_objective`: psycopg `dict_row` was indexed by integer (`KeyError: 0`). Corrected by aliasing the SQL result as `has_terminal_review` and reading by key. Final exact-commit rerun: 33 passed, 0 failed.
- **2026-10-18, approximately 20:06–20:07 UTC; exit 1.** Command: `PYTHONPATH=src python3 -m unittest tests.test_local_reasoning_provider -v`. New subject-forwarding assertion compared tuple-valued Python data to the JSON-decoded list representation. Corrected the fixture assertion to compare against JSON-normalized data. Final exact-commit run: 31 passed, 0 failed.

The source-level failure was fixed before commit `5c4a00512e5acd6f72aa766ea866a8828184b151`; the fixture-only comparison failure was also fixed before that commit. The final passing logs below are the reproducible evidence.
- **2026-10-18, approximately 20:16 UTC; exit 1.** The first expanded disposable-PostgreSQL run of `tests.test_external_reasoning_exchange` plus `tests.test_resident_reasoning` reported three `NameError` errors because `uuid5`/`NAMESPACE_URL` were not imported by the new stable-attempt-ID path. Added the imports; the focused run was repeated.
- **2026-10-18, approximately 20:17 UTC; exit 1.** The first focused receipt rerun passed success and retry cases but the ambiguous-receipt test expected a wrong-token duplicate to be rejected. It was treated as idempotent solely by attempt identity. Added a one-way lease-token SHA-256 to receipt provenance and replay comparison; the raw token is never recorded. All three focused receipt tests then passed.
