<!--
Riverview Controlled Document
File: docs/components/COMMS5_OAUTH_TROUBLESHOOTING.md
Component: COMMS5-OAUTH-IONOGE
File Revision: 1.0.0
Status: Operational troubleshooting record
Date: 2026-10-17
Purpose: Diagnose and recover Comms5 OAuth-to-Camrui authenticated MCP forwarding.
Changed: 2026-10-17 UTC | RV-COMMS5-OAUTH-FORWARD-HEADERS-001 | Record verified principal/marker defect, recovery, and acceptance evidence.
History: New file; no predecessor existed.
Authority: Existing OAuth and Steward authority boundaries; no grant changes.
-->

# Comms5 OAuth and authenticated forwarding troubleshooting

## Symptom and cause

OAuth discovery, login, PKCE exchange, and `/oauth/verify` succeeded, but `POST /comms5/mcp` with the issued access token returned HTTP 401 from the Camrui adapter. A successful OAuth verification returned `X-Riverview-Comms5-Principal: steward`. The backend requires that principal, `X-Riverview-Comms5: 1`, and the protected hop bearer.

The Caddy OAuth fallback contained both `header_up -X-Riverview-Comms5` and `header_up X-Riverview-Comms5 1`. The installed Caddy adaptation retained the delete and dropped the marker before proxying, so the backend rejected the request. A loopback-only isolated Caddy/HTTP fixture reproduced this: OAuth principal arrived as `steward`, Authorization was present, and the deleted/set marker arrived absent. Removing only the delete directive made the marker arrive as `1`.

## Corrective procedure

1. Back up the live `/etc/caddy/Caddyfile`, record SHA-256, and verify the backup before editing.
2. Remove only the OAuth fallback's marker deletion. Keep `header_up X-Riverview-Comms5 1`; it overwrites client-supplied values. Keep `copy_headers X-Riverview-Comms5-Principal` under successful `forward_auth`. Keep the legacy static-bearer route unchanged.
3. Preserve Caddyfile ownership/mode when installing a candidate. The file was accidentally staged at `0640`, which prevented the unprivileged Caddy reload process from reading it. Caddy remained active and `NRestarts=0`; restore metadata from the preserved predecessor (this host: `root:root 0644`).
4. Validate the complete Caddyfile with the same protected `EnvironmentFile` set used by `caddy.service`, then reload Caddy. Never print environment values.
5. Poll OAuth loopback `/healthz` after an OAuth service restart before probing the public path. A request during the brief listener startup gap can return 502; verify recovery by health/discovery rather than treating systemd `active` alone as readiness.
6. Run DCR, authorization-code + PKCE S256, resource-bound token exchange, MCP initialize, `tools/list`, and one implemented read-only tool call. Revoke the issued refresh token and confirm unauthenticated and revoked access return 401.

## 2026-10-17 verification record

- Candidate and full live Caddy configuration validated. Caddyfile predecessor backup: `/var/backups/riverview/comms5-oauth-marker-fix-20261017T114013Z/Caddyfile`; predecessor SHA-256 `da1490f09427831aca79329d365a09f1c610e9792ba112a8929a7ca31202d97c`. Final live Caddyfile SHA-256 is recorded in the dated machine-connection runbook.
- Caddy reload succeeded after restoring original file mode. Caddy active; no restart (`NRestarts=0`). Public health/discovery/resource metadata returned 200; unauthenticated `/mcp` and `/comms5/mcp` returned 401.
- Real HTTPS PKCE harness: DCR 201; authorization page 200; credential submission 302 with verified state; token exchange 200 bound to the exact MCP resource. MCP initialize 200 (`2025-11-25`); initialized notification 202; tools/list 200 with 21 tools; `comms5_contract_info` returned `riverview-comms-contract:5.0`; token family revoked 200; revoked and unauthenticated calls returned 401. The test did not log credentials, codes, or tokens.
- OAuth unit restart preserved a DCR client created before restart. The first public discovery probe immediately after `systemctl restart` saw 502 before the new loopback listener was ready; loopback `/healthz` then returned 200, and the persisted-client authorization and full MCP tool test passed.
- Controlled reverse SSH disconnect/reconnect: terminated only the sshd process owning Ionoge's `127.0.0.1:11826` forward; the listener and Camrui `/healthz` recovered in 6 seconds. No inference/model services were touched.
- Comms4 `/mcp` route is unchanged and unauthenticated access returns 401. An authenticated `ping` returned 502 because no process currently listens on Ionoge `127.0.0.1:11825`. This is an unresolved upstream availability issue, not changed by the Comms5 route correction.
- ChatGPT account-side connector sign-in/invocation remains unverified; the protocol acceptance used a test client against the actual public HTTPS services.

## Fast read-only checks

```sh
systemctl is-active caddy riverview-comms5-oauth.service
curl -fsS https://riverview-comms.ionoge.com/.well-known/oauth-authorization-server >/dev/null
curl -fsS https://riverview-comms.ionoge.com/.well-known/oauth-protected-resource >/dev/null
curl -fsS http://127.0.0.1:11826/healthz
ss -ltnp | grep -E '127.0.0.1:11826|127.0.0.1:11827'
```

For a blocked authenticated MCP call, inspect the Caddy adapted route without emitting environment values. The OAuth-to-backend proxy headers must have a set for marker `1`, no delete for that marker, and a principal copied from the successful OAuth `/oauth/verify` response. Keep OAuth `/oauth/verify` loopback-only.
