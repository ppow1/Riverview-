<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/EXTERNAL-MCP-CAMRUI-COMMISSION/20261016T232220Z-e5a373/checkout.md
File Revision: 1.0.0
Task: RV-EXTERNAL-MCP-ADAPTER-001
Source commit: e5a373e43594785c885c6972baecccbc37c6ec34
Environment: Camrui Ubuntu / PostgreSQL 16 production, 2026-10-16 UTC
Authority: Authorized bounded commissioning; external route and ChatGPT setup not authorized
Data: Sanitized; no credentials or conversation contents
-->

# Camrui External MCP commissioning — partial / NO-GO for listener activation

## Release and backup evidence

- Merged integration source: `e5a373e43594785c885c6972baecccbc37c6ec34`.
- Independently checked deployment archive: `/tmp/riverview-camrui-e5a373e43594785c885c6972baecccbc37c6ec34.tar.gz`.
- Archive SHA-256: `42b6cb7af93a42884fb1a05357e37690e8e8e0adc678cc91f4d5627487ebdc0d`.
- Archive `SOURCE_COMMIT` matched the merge commit; package manifest verification passed.
- Immutable staged source: `/opt/riverview-external-reasoning-mcp/releases/e5a373e43594785c885c6972baecccbc37c6ec34`. No `current` symlink or service activation was made.
- Protected backup: `/var/lib/postgresql/riverview-mcp-backup.SVHWj6dv/riverview.dump`, owner `postgres:postgres`, mode `0600`, 301288 bytes; SHA-256 `4b5eefefbe2cad7eeb335b14de639bbf19b1907591a9bc842407c6c78c8bacce`.
- `pg_restore --list` passed. Disposable restore `rv_restore_mcp_20261016T231000Z` succeeded and reported 21 migration rows, 10 assignments, and 58 events. The test database was removed after verification; production was not restored over or altered by that test.
- Original dashboard and core release pointers were not changed.

## Migration 0011

- Read-only preflight established migration `0011_external_reasoning_exchange` was absent and its required predecessor migrations and relations were present. The predecessor checksums matched the production ledger.
- The approved migration was applied through `apply_migrations` from the exact merged source tree. It is now recorded once with checksum `93e2603dd92237b95700356f723e21553bcafdee5314800bb04cd18469163b30`.
- Runtime ACL verification passed for the migration's intended narrow access: schema usage; exchange select/insert and only the required column-level updates; event select/insert and sequence usage. Table-level exchange UPDATE remains false. No authority-ledger or unrelated-table permissions were granted.
- Exchange table count after migration: zero. No synthetic production request or response was created.

## Tests and runtime checks

The exact staged release source was used for both tests below. PostgreSQL integration ran only against the disposable restored database and its test-created `rvtest_*` schema.

1. `sudo -u postgres env PYTHONPATH=/opt/riverview-external-reasoning-mcp/releases/e5a373e43594785c885c6972baecccbc37c6ec34/src RIVERVIEW_TEST_PG_DSN='dbname=rv_restore_mcp_20261016T231000Z user=postgres' /opt/riverview-core/.venv/bin/python /tmp/riverview-mcp-e5a373/tests/test_external_reasoning_exchange.py ExternalReasoningExchangePostgresTests.test_mcp_provider_scoped_round_trip_uses_durable_exchange -v` — **1 passed**. The independent HTTP client completed initialize, tool discovery, authenticated list, claim, response submit, and status over the actual packaged adapter, with durable state in the disposable database.
2. `sudo -u postgres env PYTHONPATH=/opt/riverview-external-reasoning-mcp/releases/e5a373e43594785c885c6972baecccbc37c6ec34/src /opt/riverview-core/.venv/bin/python /tmp/riverview-mcp-e5a373/tests/test_external_reasoning_mcp.py -v` — **4 passed**. Covers initialization/tool discovery, invalid-token denial, protected-resource metadata, Host/Origin checks, Accept negotiation, and provider identity binding.

These tests are isolated; they do not prove that a production MCP daemon or an internet route is active.

## Production baseline and regressions

- Dashboard release pointer: `/opt/riverview-status-dashboard/current` -> release `50e1e44b498927e5df67e5c08aec3cda8267dd72`; service active, `NRestarts=0`.
- Core source pointer remains `/opt/riverview-core` -> release `64e8f14ad6d71102a864755739a1c8a61506235c`.
- Dashboard root returned HTTP 200; unauthenticated `/api/v1/status` returned HTTP 401.
- CME monitor and event processor are active with `NRestarts=0`.
- At 2026-10-16 19:19:50 EDT, systemd stopped assignment-intake, Grace owner-session, M33 worker, and M33 verifier. They are currently inactive. M33 worker logs immediately before stop show repeated `WorkerAuthorizationError`; this is recorded as the known pre-existing expired-authorization failure and was not changed. The common stop time is preserved as an observed external/service-management event; this commissioning did not issue stop/restart commands for those units.
- `riverview-external-reasoning-mcp.service` is not installed; no process listens on port 11827. No MCP-specific environment file or protected provider token-map credential exists.

## Blockers and prepared deployment boundaries

The merged unit template expects `/opt/riverview-core/current`, but the deployed core path is a symlink to `/opt/riverview/releases/64e8f14...` and has no `current` child. The staged MCP source is under its own immutable release root. A narrowly scoped unit path override (or reviewed unit correction) is therefore required; the shared core pointer must not be changed.

The source token map authenticates a preloaded bearer digest to a fixed provider/principal and expiry. It does not issue OAuth credentials or validate JWT issuer/audience. The source's example `RIVERVIEW_MCP_AUTHORIZATION_SERVER_URL` is a placeholder. Production has no approved MCP issuer URL/provider credential mapping, and the documented workflow requires an issuer grant before provisioning the identity. No values were guessed and no token was generated. Consequently the daemon was not started, and production initialize/auth/list/claim/submit/status were not attempted. The isolated tests above are the live-operation evidence available without manufacturing an identity.

Proposed external hostname: `riverview-comms.ionoge.com`, using the new path `/mcp` only after a separate route review. Existing historical `/comms5/mcp` is a different service/schema and must not be repointed. Camrui has no active Caddy service or local Caddyfile; no public route, tunnel, firewall, or DNS change was made. Public exposure is **not ready** until the actual authorization server and ChatGPT-compatible OAuth flow are provisioned and verified, the service unit is corrected for the separate release root, and the loopback daemon passes authenticated production-path checks.

## Rollback and data preservation

No dashboard/core release pointer, unrelated service, external route, or credential was changed. The staged immutable MCP release and protected backup are retained. Migration 0011 is additive and its production data must be retained; rollback is to leave the MCP unit stopped/disabled and preserve its tables/events, not drop the migration or rows. No MCP unit was installed, so service rollback is not needed. The previously verified dashboard/core release pointers remain the production rollback targets.
