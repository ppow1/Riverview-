<!--
Riverview Controlled Document
File: docs/components/COMMS5_CAMRUI_DEPLOYMENT.md
Component: COMMS5-CAMRUI-ADAPTER
File Revision: 1.0.7
Status: Deployment and recovery procedure
Date: 2026-10-17
History: New file; no predecessor existed.
Changed: 2026-10-17 UTC | RV-COMMS5-OAUTH-FORWARD-HEADERS-001 | Corrected trusted marker propagation and recorded live OAuth acceptance and Comms4 upstream status.
Changed: 2026-10-17 UTC | RV-COMMS5-DASHBOARD-READ-DEPLOY-001 | Record the merged loopback dashboard bridge deployment and rollback point.
Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Add migration 0012 preflight and non-destructive rollback handling for policy-aware Comms5 releases.
Previous: 2026-10-17 UTC | RV-COMMS5-SSH-HOSTKEY-CREDENTIAL-001 | Pass the pinned known-hosts file through systemd credentials for the unprivileged tunnel user.
-->

# Comms5 Camrui adapter deployment

## Intended request path

```text
ChatGPT OAuth client
  -> HTTPS Caddy on Ionoge (existing riverview-comms.ionoge.com)
  -> OAuth authorization service on Ionoge 127.0.0.1:11827
  -> authenticated forward_auth; Caddy copies the token-validated principal and overwrites the trusted backend marker
  -> reverse SSH listener on Ionoge 127.0.0.1:11826
  -> Camrui 127.0.0.1:11826 (Comms5 adapter)
```

The adapter does not listen on a LAN address and does not connect to the database. Its HTTP boundary requires the Caddy principal marker and the separate backend-hop bearer. OAuth access tokens are validated by the Ionoge OAuth service and are not forwarded as the backend credential. The OAuth fallback copies `X-Riverview-Comms5-Principal` only from a successful OAuth `/oauth/verify` response and sets `X-Riverview-Comms5: 1` on the backend hop. It must not delete that marker in the same `header_up` block: Caddy applies the delete after the set, causing backend authentication to fail. The original static-bearer path remains a separate compatibility route. Comms4 on `/mcp` and Comms5 on `/comms5/mcp` remain separate.

## Files and activation order

1. Stage the immutable package at `/opt/riverview-comms5-camrui/releases/<commit>` and verify the package manifest/checksum before creating `current`.
2. Install the protected Camrui credential `/etc/riverview/comms5/backend-auth` with mode `0600`, root ownership. Its value must match only `RIVERVIEW_COMMS5_UPSTREAM_AUTH` already consumed by the Ionoge Comms5 route. It is not an OAuth access token.
3. Install `riverview-comms5-camrui.service`; validate it using `systemd-analyze verify` before daemon reload/start.
4. Confirm the service only binds `127.0.0.1:11826`, and verify unauthenticated requests receive 401.
5. Install the dedicated restricted reverse-tunnel private key as a root-owned source credential at `/etc/riverview/comms5/ionoge-tunnel` and the pinned host-key file at `/etc/riverview/comms5/known_hosts`. The tunnel unit passes both files using `LoadCredential` into its private service credential directory because the `admin1` process cannot traverse root-private `/etc/riverview`. SSH must read the verified host key from `%d/known-hosts` with `StrictHostKeyChecking=yes`. Configure the Ionoge `authorized_keys` line for remote listen `127.0.0.1:11826` only. Preserve the existing deployment key and all other authorized keys.
6. Start the tunnel service, then test the Ionoge loopback path. Do not expose the service directly.
7. Install the OAuth service from historical PR #15 at immutable commit `048787f574d42ff073a9f94f571dc79943d60fa4`, using its existing protected login/proxy credentials and dedicated SQLite state. Keep the OAuth service bound to Ionoge loopback `127.0.0.1:11827`.
8. Replace only the existing Comms5 handler block inside the current Caddy site with `deploy/comms5/caddy-comms5-oauth-block.caddy`. The fragment retains the existing static Steward bearer path and adds OAuth discovery/forward-auth. Keep the existing Comms4 `/mcp` block byte-for-byte unchanged. Validate the full Caddyfile before reloading Caddy.

## Verification gates

- Camrui service active; loopback `/healthz` returns 200; `ss` confirms only `127.0.0.1:11826`.
- Direct unauthenticated POST to Camrui `/mcp` returns 401; malformed bearer/hop identity is rejected.
- Authenticated Caddy-hop MCP initialize, `notifications/initialized`, `ping`, `tools/list` and `tools/call` succeed.
- Tool list is byte-equivalent in the original 21 names, descriptions, input schemas and annotations to the checked-in source catalog (plus historical OAuth security metadata).
- A safe implemented operation such as `comms5_contract_info` returns the historical versioned result.
- A not-yet-migrated operation returns `isError=true`, `NOT_IMPLEMENTED`, `executed=false`, with no database or filesystem mutation.
- CME and objective read projections use the dashboard's existing bearer through a systemd `LoadCredential`; the adapter contacts only loopback `127.0.0.1:8767` and fixed read routes. Objective payload text and acceptance criteria are not returned. Never pass a caller-controlled URL or route to this backend.
- OAuth metadata/discovery, authorization-code PKCE, token exchange, unauthorized rejection, and authenticated MCP operation pass through the public Caddy endpoint.
- Existing `https://riverview-comms.ionoge.com/mcp` (Comms4) and prior authenticated Comms5 connector continue working.
- ChatGPT custom connector is authenticated, discovers all 21 tools, and invokes `comms5_contract_info` successfully. This account-side gate must be completed in the Steward's ChatGPT workspace; server-side tests cannot impersonate it.

## Rollback

Preserve current Caddyfile, systemd units, authorized_keys, release pointer, and credential-file metadata before mutation. On any failed gate: stop only `riverview-comms5-tunnel.service` and `riverview-comms5-camrui.service`; restore the prior Camrui `current` pointer and unit if changed; restore only the Comms5 site block and relevant Caddy environment entries from the preserved predecessor; run `caddy validate`; reload Caddy only after validation. Preserve SQLite OAuth state and historical Comms4/Comms5 records. Do not revert unrelated services or delete release/backup artifacts.

## Verified commissioning record — 2026-10-17 UTC

- Ionoge Caddy, OAuth, and Camrui Comms5 health were active. Public OAuth authorization-server and protected-resource discovery returned 200; public unauthenticated Comms4 and Comms5 MCP POSTs returned 401.
- A real authorization-code + PKCE S256 test client completed DCR, credential login through HTTPS, callback state validation, resource-bound token exchange, MCP initialize, notifications/initialized, `tools/list` (21 original tools), and the implemented read-only `comms5_contract_info` call. The call returned contract `riverview-comms-contract:5.0`. Token-family revocation succeeded; both unauthenticated and revoked MCP requests returned 401. Test output did not include credentials, codes, or tokens.
- A dedicated reverse-tunnel SSH session owning Ionoge `127.0.0.1:11826` was terminated for a bounded reconnect check; the listener and `/healthz` recovered in 6 seconds. The OAuth service was restarted; after its loopback listener was ready, an OAuth client registered before restart authorized and completed the MCP exchange, confirming SQLite-backed client persistence.
- Caddy reload initially failed because a staging copy had mode `0640` and lost Caddy's read permission. The running Caddy process remained active (`NRestarts=0`, health 200). File ownership/mode were restored from the preserved predecessor (`root:root 0644`), the full file revalidated, and reload then succeeded. The production Caddyfile backup and SHA-256 are recorded in the dated connection runbook.
- **Comms4 caveat:** The `/mcp` Caddy route and its authenticated routing block were preserved unchanged. The public unauthenticated request remains 401, but an authenticated `ping` returned 502 because Ionoge currently has no listener on `127.0.0.1:11825`. Comms4 backend operation is therefore not currently verified and needs its own existing upstream restored; no Comms4 config or service was modified.
- **ChatGPT account acceptance:** The full OAuth/MCP protocol was exercised using a real HTTPS client harness and the actual services, not ChatGPT's UI. ChatGPT workspace connection and invocation remain unverified until a Steward completes the connector authorization in ChatGPT.

See [`COMMS5_OAUTH_TROUBLESHOOTING.md`](COMMS5_OAUTH_TROUBLESHOOTING.md), [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md), and the dated machine-connection runbook in `docs/operations/` for exact evidence and recovery.

## Current deployment — 2026-10-17 22:16 UTC

The active immutable release is `c18b283ae7263b6fa708b80dbf179b8199ec4b64` (package SHA-256 `c2a7c5681d0f94097bed27f124a3666e6f5cc0d3959ebf4573535573fcd65371`). The service remains enabled and active on loopback. Only the Camrui Comms5 service was restarted; the reverse tunnel, Caddy, OAuth, dashboard, and inference services were not changed. A protected rollback point and exact smoke-test evidence are recorded in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md).

## Policy-aware release prerequisite — migration 0012

Releases implementing resource-policy status, mutation, lock enforcement or
scheduler selection require the additive
`0012_resource_selection_policy.sql` migration in the application schema.
Before deployment, verify the current migration record, take and restore-test a
fresh protected database backup, validate the migration on a disposable copy,
and confirm the `riverview_core` role receives only the declared policy and
event-table privileges. Then apply migration 0012 through the controlled
migration runner before switching the immutable application pointer. Do not
automatically treat a missing policy relation as an unset policy.

Rollback after migration 0012 is non-destructive: switch the application
pointer and service unit back to the protected predecessor, restart only the
Comms5 service, and verify its health/auth boundary. Preserve policy and event
tables and all records. The predecessor runtime ignores the new tables. Never
drop migration 0012 tables as part of release rollback. If migration
compatibility, ACL scope, or restore integrity is uncertain, do not activate.
