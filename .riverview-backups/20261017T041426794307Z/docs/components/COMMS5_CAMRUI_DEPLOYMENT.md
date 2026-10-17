<!--
Riverview Controlled Document
File: docs/components/COMMS5_CAMRUI_DEPLOYMENT.md
Component: COMMS5-CAMRUI-ADAPTER
File Revision: 1.0.1
Status: Deployment and recovery procedure
Date: 2026-10-16
History: New file; no predecessor existed.
-->

# Comms5 Camrui adapter deployment

## Intended request path

```text
ChatGPT OAuth client
  -> HTTPS Caddy on Ionoge (existing riverview-comms.ionoge.com)
  -> OAuth authorization service on Ionoge 127.0.0.1:11827
  -> authenticated forward_auth; Caddy injects the trusted Steward marker
  -> reverse SSH listener on Ionoge 127.0.0.1:11826
  -> Camrui 127.0.0.1:11826 (Comms5 adapter)
```

The adapter does not listen on a LAN address and does not connect to the database. Its HTTP boundary requires the Caddy principal marker and the separate backend-hop bearer. OAuth access tokens are validated by the Ionoge OAuth service and are not forwarded as the backend credential. The original static-bearer path remains a separate compatibility route. Comms4 on `/mcp` and Comms5 on `/comms5/mcp` remain separate.

## Files and activation order

1. Stage the immutable package at `/opt/riverview-comms5-camrui/releases/<commit>` and verify the package manifest/checksum before creating `current`.
2. Install the protected Camrui credential `/etc/riverview/comms5/backend-auth` with mode `0600`, root ownership. Its value must match only `RIVERVIEW_COMMS5_UPSTREAM_AUTH` already consumed by the Ionoge Comms5 route. It is not an OAuth access token.
3. Install `riverview-comms5-camrui.service`; validate it using `systemd-analyze verify` before daemon reload/start.
4. Confirm the service only binds `127.0.0.1:11826`, and verify unauthenticated requests receive 401.
5. Install the dedicated restricted reverse-tunnel key and host-key file under `/etc/riverview/comms5`; configure the Ionoge `authorized_keys` line for remote listen `127.0.0.1:11826` only. Preserve the existing deployment key and all other authorized keys.
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
- OAuth metadata/discovery, authorization-code PKCE, token exchange, unauthorized rejection, and authenticated MCP operation pass through the public Caddy endpoint.
- Existing `https://riverview-comms.ionoge.com/mcp` (Comms4) and prior authenticated Comms5 connector continue working.
- ChatGPT custom connector is authenticated, discovers all 21 tools, and invokes `comms5_contract_info` successfully. This account-side gate must be completed in the Steward's ChatGPT workspace; server-side tests cannot impersonate it.

## Rollback

Preserve current Caddyfile, systemd units, authorized_keys, release pointer, and credential-file metadata before mutation. On any failed gate: stop only `riverview-comms5-tunnel.service` and `riverview-comms5-camrui.service`; restore the prior Camrui `current` pointer and unit if changed; restore only the Comms5 site block and relevant Caddy environment entries from the preserved predecessor; run `caddy validate`; reload Caddy only after validation. Preserve SQLite OAuth state and historical Comms4/Comms5 records. Do not revert unrelated services or delete release/backup artifacts.

## Current status

This source document specifies the commissioned implementation. The live services and public route remain unverified until the recorded deployment procedure is executed. See `COMMS5_CAMRUI_MIGRATION.md` for per-tool status.
