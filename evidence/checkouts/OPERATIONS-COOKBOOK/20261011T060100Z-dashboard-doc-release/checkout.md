<!-- Riverview~ Controlled Evidence -->
<!-- File Revision: 1.0.0 -->
# Dashboard documentation package compatibility trial and rollback

- **Task:** RV-OPS-COOKBOOK-DASHBOARD-PACKAGE-ROLLBACK
- **Component:** STEWARD-DASHBOARD / OPERATIONS-COOKBOOK
- **Candidate source:** `6403e45d3489c1b3108b447eb1ebc0f1786bec0f`
- **Candidate archive SHA-256:** `ed63d9eb4ac05a4a236c82b40d7fd89078e3bfb6e58c022f02593256f0bb44fe`
- **Target:** Camrui loopback-only dashboard, 127.0.0.1:8766
- **Scope:** Versioned dashboard release trial; no database migration, credentials, authority, SSH or non-dashboard service changes.

## Candidate verification and observed failure

The exact-commit package passed manifest and shell compatibility checks. Its dashboard Python modules matched the installed release byte-for-byte; the only dashboard module difference was `static/index.html`. On installation, the service became active. Headless Firefox observed a healthy PostgreSQL/CME projection, six attention items, the existing completed assignment `m31-real-worker-2533f1c7dd1c433c95bd2cfa8a314d7c`, one independent verification, and zero browser errors. Nineteen links originating in the operations guide returned HTTP 200.

A separate check of the candidate's repository-knowledge shell link returned HTTP 404. Comparison proved the candidate package omitted three repository-knowledge documents available in the prior live release: the cookbook, provider contract page, and flow page. Their prior-release SHA-256 values and package membership comparison are in `package-content-diff.json`. The M4.1 source branch intentionally does not contain the M3.3 graph/doc set, so the candidate was not a compatible replacement despite its package checksum and startup checks passing.

## Rollback and post-rollback verification

Restored `/opt/riverview-status-dashboard/current` to the prior immutable release `7a9ff46e11edc54b1ffe46f63962754e6d2da765` using an atomic symlink replacement, then restarted only `riverview-status-dashboard.service`. After its readiness interval, the unit was active/running with `NRestarts=0`, loopback HTTP returned 200, and PostgreSQL, event processor, CME monitor, notification dispatcher and SSH remained active. The unit SHA-256 stayed `6fb11ab264ccbba74d0213f4e3e8d00eba8ca847fde046757d7906cc18cf88a0`. See `postrollback-state.txt`.

Firefox post-rollback verified the preserved live service: healthy projection and CME, the same completed persisted assignment and one independent verification, six attention items, valid workflow graph with no fabricated live node highlight, 21 documentation links all HTTP 200, readable guide with 17 headings / 2 tables / 17 code blocks, no unsafe links or scripts, and zero browser errors. Navigation call samples ranged from 81 to 267 ms. See `browser-postrollback/browser-acceptance.json` and screenshots.

## Decision

The candidate release remains installed but inactive, and the package archive is preserved under the root-only deployment evidence directory. The previous `7a9ff46` release remains authoritative and operational. Do not retry a dashboard package from this source branch until its package is reconciled with M3.3's repository-knowledge documents and canonical graph. The newly password-safe PostgreSQL cookbook and corrected scheduler migration status are source/CI verified but are not live in the preserved older release. That older cookbook still has placeholder `PGPASSWORD` and credential-DSN examples; no actual password was exposed.

This is a documented failed deployment trial followed by successful recovery, not a M3.1 acceptance change or M4.1 live commissioning.
