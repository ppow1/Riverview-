<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/RESIDENT-REASONING/20261011T074000Z-isolated/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.1
Purpose: Record M4.2 isolated PostgreSQL runtime verification
Authority: Private disposable PostgreSQL only; no live authority state
Changed: 2026-10-11 UTC | RV-M4.2-001 | Record actual integration verification
Changed: 2026-10-11 UTC | RV-M4.2-VERIFY-CLOSEOUT | Record final focused/full-suite and cleanup results
History: predecessor in .riverview-backups/manifest.jsonl; artifacts.json SHA-256 manifest
-->
# M4.2 isolated resident reasoning verification

## Environment and execution

All PostgreSQL work used unique `rvtest_*` schemas on disposable, socket-only PostgreSQL 16.15 clusters. The shared `riverview_dev` database, deployed services, live authority state, credentials, and assignments were not changed. No live provider or resident service was invoked.

## Results

- Focused `tests.test_resident_reasoning`: **10/10 passed**, zero skips/errors/failures; 7.261 s. See `focused-postgresql-tests.log`.
- Complete applicable suite: **147/147 passed**, zero skips/errors/failures; 63.586 s. See `full-suite.log`.
- Fixture cleanup: zero `rvtest_*` schemas and zero `rvtest_*` roles. The disposable server stopped cleanly; the post-stop socket probe returned no response.
- Canonical graph validation: PASS, 13 graphs and 255 nodes. Controlled revision/predecessor audit: PASS, zero issues. Python compileall: exit 0.
- Test cases demonstrate persisted proposal/grounding across runtime replacement, nonverified evidence waiting, explicitly configured timeout fallback, provider swap without grant changes, no implicit fallback, credential-shaped field rejection, stale assignment revision rejection, exact-grant denial, and token budget enforcement.

This is isolated engineering verification only. M4.2 has no live reasoning provider, live authority schema/service, browser resident conversation, assignment creation, or action execution. The proposal API does not authorize work. Full component DoD, operational commissioning, and Steward acceptance remain open. M3.3 remains the earliest unaccepted roadmap step and its live authority/real-knowledge gates are not bypassed.
